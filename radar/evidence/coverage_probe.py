"""用外部 Benchmark 目录（benchmark-radar）为每个 Idea 检索 Coverage 候选。

目的：把"已有 Benchmark 没有覆盖 X"从静态名单升级为可复查的 Coverage Analysis 起点。

口径约束（与 00_工作导航.md 的工作原则一致）：
- benchmark-radar 是**聚合目录**，属于 secondary 源，不是 Raw Source。
- 目录记录只有 name/description/categories，没有 task definition、input/output
  与 evaluation protocol，因此**不足以断定 covered 或 not_covered**。
- 所以本脚本写入的 coverage 一律是 `target_coverage=unknown` +
  `verification_status=needs_review`，供人工继续核查原始 Paper/Repo。
- 全部候选（含被拒绝的）连同 rejection_reason 写入 retrieval_runs /
  retrieval_results，保持可追溯，不只保留选中的。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from radar.core.radar_core import db, init_db, list_ideas, now_iso, upsert_coverage_entry

RETRIEVER_VERSION = "benchmark-radar-catalog-v1"
CATALOG_SOURCE_ID = "benchmark-radar-catalog"

# benchmark-radar 仓库位置与其 venv 解释器。目录索引是生成物，需先在该仓库跑
# `benchmark-radar normalize-catalog`。
RADAR_REPO = Path(os.environ.get("BENCHMARK_RADAR_REPO", "/Users/prince/benchmark-radar"))

# Idea 名称与 capability 是中文/内部词表，目录以英文为主，必须显式映射而不是
# 直接把中文丢进 BM25。映射保持在这里以便人工复查和修正。
DOMAIN_TERMS = {
    "financial": "financial finance",
    "legal": "legal law contract",
    "medical": "medical clinical health",
    "scientific": "scientific research science",
    "agent": "agent agentic",
    "general": "",
}

CAPABILITY_TERMS = {
    "citation_correctness": "citation attribution grounding evidence",
    "cross_document_reasoning": "multi document long context reasoning",
    "domain_expertise": "expert knowledge domain expertise professional",
    "domain_reasoning": "domain reasoning professional reasoning",
    "long_context": "long context",
    "numerical_grounding": "numerical table quantitative arithmetic",
    "planning": "planning multi step",
    "safety": "safety harmful refusal",
    "tool_use": "tool use function calling api",
    "version_awareness": "version temporal knowledge update",
    "judge_reliability": "llm judge evaluator agreement",
    "hypothesis_generation": "hypothesis generation scientific discovery",
}

# 每个 Idea 的任务主题词。Idea 名称是中文，BM25 无法命中英文目录，这里给出
# 人工确认的英文主题；未列出的 Idea 退回 domain + capability 组合。
IDEA_TOPIC_TERMS = {
    1: "financial statement report audit anomaly detection table numerical evidence",
    2: "contract clause review legal risk obligation",
    3: "patient medication safety drug interaction prescribing",
    18: "clinical reasoning guideline retrieval diagnosis",
    24: "llm judge user simulator agent evaluation reliability",
    25: "biomedical hypothesis generation knowledge graph evidence",
    26: "benchmark compression subset efficient evaluation ranking",
    27: "deep research web browsing search agent",
    28: "financial search retrieval source traceability temporal",
}


def build_queries(idea: dict[str, Any]) -> list[str]:
    """为一个 Idea 构造 2 条查询：主题向 + 能力向。

    不使用 idea['evaluation_gap']：库中多条记录的该字段被 arXiv 摘要原文污染
    （例如 idea 18/9/4/6/11），作为检索输入会引入噪声。
    """
    domain = DOMAIN_TERMS.get(idea["domain"], idea["domain"])
    capabilities = idea.get("capability") or []
    capability_text = " ".join(CAPABILITY_TERMS.get(x, x.replace("_", " ")) for x in capabilities[:3])

    topic = IDEA_TOPIC_TERMS.get(idea["id"], "")
    primary = " ".join(x for x in [topic or domain, "benchmark evaluation"] if x).strip()
    secondary = " ".join(x for x in [domain, capability_text, "benchmark"] if x).strip()

    queries = []
    for query in [primary, secondary]:
        normalized = " ".join(query.split())
        if normalized and normalized not in queries:
            queries.append(normalized)
    return queries


def sync_catalog() -> dict[str, Any]:
    """拉取上游最新目录数据。

    目录每天由 benchmark-radar 的 daily-radar 工作流更新，所以每次核查前
    先 sync，否则会拿一个月前的数据去判"有没有已存在的 Benchmark"。
    """
    cli = RADAR_REPO / ".venv" / "bin" / "benchmark-radar"
    proc = subprocess.run(
        [str(cli), "sync", "--json"],
        cwd=RADAR_REPO, capture_output=True, text=True, timeout=300,
    )
    if proc.returncode != 0:
        # sync 失败不阻断核查，但必须记录：否则会把旧数据当最新用。
        return {"status": "sync_failed", "error": proc.stderr.strip()[:300]}
    # CLI 在 JSON 前会打印引用提示，取第一个 '{' 起的内容。
    text = proc.stdout
    start = text.find("{")
    return json.loads(text[start:]) if start >= 0 else {"status": "unparsed"}


def search_catalog(query: str, limit: int) -> dict[str, Any]:
    """调用 benchmark-radar 的 QueryService 查询目录。

    读 `benchmark-radar sync` 下载的数据（`~/.benchmark-radar/versions/<ver>/`），
    不读仓库里 normalize-catalog 的本地产物——后者由仓库内提交的历史快照生成，
    会比上游发布版本旧一个月以上，新发布的 Benchmark 查不到。

    单独 venv 调用而不是 import：两个项目的 Python 版本不同
    （本项目 3.9 可用，benchmark-radar 要求 >=3.11）。
    """
    python = RADAR_REPO / ".venv" / "bin" / "python"
    if not python.exists():
        raise RuntimeError(
            f"未找到 {python}。请先在 {RADAR_REPO} 执行 "
            "`uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -e .`。"
        )
    # QueryService 默认路径指向仓库内的生成物，显式改指 sync 目录。
    code = (
        "import json,sys;"
        "from pathlib import Path;"
        "from benchmark_radar.data_store import DataStore;"
        "from benchmark_radar.query import QueryService;"
        "paths=DataStore().query_paths();"
        "print(json.dumps(QueryService(paths).search(sys.argv[1],scope='catalog',limit=int(sys.argv[2]))))"
    )
    proc = subprocess.run(
        [str(python), "-c", code, query, str(limit)],
        cwd=RADAR_REPO, capture_output=True, text=True, timeout=120,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"catalog query failed: {proc.stderr.strip()[:400]}")
    return json.loads(proc.stdout)


# 领域信号词：出现在 categories / name / description 中即视为该领域记录。
# 目录混用中英文类目（'healthcare' 与 '医疗'），两者都要列出。
DOMAIN_SIGNALS = {
    # 不放 "fin"：它与 "finding" 共享前缀，词边界也分不开，会把无关记录判成金融。
    "financial": ["financial", "finance", "fiscal", "accounting", "金融", "财务"],
    "legal": ["legal", "law", "contract", "statute", "法律", "法条"],
    # "med" 会前缀命中 "media"/"mediation"，用明确的医学词形代替。
    "medical": ["medical", "medicine", "medqa", "clinical", "health", "patient", "医疗", "临床"],
    "scientific": ["scientific", "science", "research", "科学"],
    "agent": ["agent", "agentic", "智能体"],
    "general": [],
}

# 任务信号词：判断记录是否触及 Idea 的具体任务，而不只是同领域。
# 与 IDEA_TOPIC_TERMS 对应，人工维护。
IDEA_TASK_SIGNALS = {
    # 同概念的不同词形（table/tabular、表格）写在一个组里，命中只算一次，
    # 避免降级通道的 ">=2 个任务信号" 被同义词虚增。
    1: [["table", "tabular", "表格"], ["report", "statement", "财报"], ["audit", "审计"],
        ["numerical", "quantitative", "arithmetic"], ["anomaly", "异常"], ["qa"]],
    2: [["contract", "合同"], ["clause", "条款"], ["obligation"], ["review", "审查"]],
    3: [["medication", "drug", "用药", "药"], ["prescri"], ["safety", "安全"], ["interaction"]],
    18: [["clinical", "临床"], ["diagnos", "诊断"], ["guideline", "指南"], ["reasoning", "推理"]],
    24: [["judge", "评判"], ["simulat", "模拟"], ["reliab", "agreement", "一致性"], ["dialog", "conversation", "对话"]],
    25: [["hypothes", "假设"], ["knowledge graph", "知识图谱"], ["evidence", "证据"], ["biomedical", "biolog", "生物"]],
    26: [["compress", "压缩"], ["subset", "子集"], ["efficient", "cost", "成本"], ["ranking", "rank", "排序"]],
    27: [["deep research"], ["brows", "浏览"], ["search", "搜索", "检索"], ["web"]],
    28: [["search", "retriev", "检索"], ["financial information", "source", "来源"], ["temporal", "time", "时效"], ["tracea", "citation", "溯源"]],
}


# 需要全词匹配的信号词：允许前缀扩展会命中无关词。"contract" 若按前缀匹配，
# 会命中 SQuALITY 描述里的 "contractors"（雇来写摘要的承包商），把长文档摘要
# 基准误判成合同审查基准。
EXACT_TERMS = {"contract", "qa", "law", "report", "review", "table", "safety", "drug"}


def signal_hit(term: str, haystack: str) -> bool:
    """按词边界匹配信号词，避免子串假阳性。

    朴素 `in` 会让 "med" 命中 "immediate"、"contract" 命中 "contractors"，
    把无关记录判成同领域。ASCII 词默认按前缀+词边界匹配（"financial" 命中
    "financial"、"finance" 命中 "finances"），EXACT_TERMS 里的词要求全词；
    中文无词边界，退回子串。
    """
    if not term:
        return False
    if not term.isascii():
        return term in haystack
    # 全词词仍接受复数尾（contract/contracts），但不接受任意前缀扩展
    # （contractors 被挡掉）。
    suffix = "s?" if term in EXACT_TERMS else "[a-z]*"
    return re.search(rf"\b{re.escape(term)}{suffix}\b", haystack) is not None


def judge(idea: dict[str, Any], result: dict[str, Any]) -> tuple[bool, str]:
    """判断一条目录记录是否值得进入人工 Coverage 核查。

    这里只做"是否值得核查"的筛选，不判断是否覆盖——目录元数据不含
    task definition 与 evaluation protocol，无法支撑覆盖结论。

    不用 query_coverage 比例作阈值：它是"命中词数/查询词数"，长查询天然吃亏
    （9 词查询命中 2 个就只有 0.22），会误拒 FinQA、OpenFinData 这类正该核查的
    同领域基准。改为看领域信号与任务信号的绝对命中。
    """
    match = result.get("match") or {}
    coverage = match.get("query_coverage") or 0.0
    matched = match.get("matched_tokens") or []
    domain = idea["domain"]

    # 领域与任务信号在 categories + name + description 上一起找：目录的 categories
    # 粒度不一，有些记录只在 description 里点明领域。
    haystack = " ".join([
        " ".join(str(x) for x in (result.get("categories") or [])),
        str(result.get("name") or ""),
        str(result.get("description") or ""),
    ]).lower()

    domain_signals = [x for x in DOMAIN_SIGNALS.get(domain, [domain]) if signal_hit(x, haystack)]

    # 未显式列出任务信号的 Idea（多为 "X能力评测" 这类宽主题聚类），
    # 回退到 capability 词表：每个 capability 自成一组，组内词形命中算一次。
    task_groups = IDEA_TASK_SIGNALS.get(idea["id"]) or [
        CAPABILITY_TERMS.get(capability, capability.replace("_", " ")).split()
        for capability in (idea.get("capability") or [])
    ]
    # 每组取第一个命中的词形作为该组代表，组间不重复计数。
    task_signals = [
        next(term for term in group if signal_hit(term, haystack))
        for group in task_groups
        if any(signal_hit(term, haystack) for term in group)
    ]

    if not matched:
        return False, "与查询无任何词项重叠"

    if domain != "general" and not domain_signals:
        # 跨领域通用基准的降级通道：任务信号强命中（>=2）但无领域标注时仍进核查
        # 队列。FREB-TQA / TableEval 这类表格 QA 基准常以财报为数据来源，却不带
        # finance 类目；直接按领域丢弃会漏掉 Idea 1 真正该核查的对象。
        if len(task_signals) >= 2:
            return True, (
                f"无 {domain} 领域标注，但任务信号强命中 {task_signals}；"
                "疑为跨领域通用基准，需人工核查其数据来源是否覆盖目标任务"
            )
        return False, (
            f"记录未出现 {domain} 领域信号（categories/name/description 均无）；"
            f"命中词仅 {matched}，任务信号 {task_signals}"
        )

    # 同领域但完全不触及目标任务的通用基准（如 legal 类目下的 MMLU-Base、
    # Uniform Bar Exam）不进核查队列——它们是领域考试，不是目标任务的评测。
    # 只命中 1 组任务信号也不够：WMT23（翻译）因描述里有 "biomedical" 进了
    # 生物医学假设 Idea，IndicMMLU-Pro 因 "efficient" 进了评测压缩 Idea。
    # 任务信号组 >=4 时要求至少命中 2 组。
    required = 2 if len(task_groups) >= 4 else 1
    if task_groups and len(task_signals) < required:
        return False, (
            f"属 {domain} 领域但任务信号仅命中 {task_signals}（需 >= {required} 组，候选组 "
            f"{[group[0] for group in task_groups if group][:8]}）；疑为同领域通用基准"
        )

    return True, (
        f"领域信号 {domain_signals}，任务信号 {task_signals}，"
        f"命中词 {matched}（query coverage {coverage:.2f}）；进入人工 Coverage 核查"
    )


def coverage_entry(idea_id: int, result: dict[str, Any], query: str) -> dict[str, Any]:
    """把目录记录转成 coverage 行。

    未披露的字段明确写"目录记录未披露"，不用推测填充——这是 MedBench 那条既有
    记录（needs_review）建立的口径。
    """
    undisclosed = "目录记录未披露；需核查原始 Paper/Repo。"
    summary = result.get("score_summary") or {}
    metrics = []
    if result.get("score_direction"):
        metrics.append(f"score_direction={result['score_direction']}")
    if summary.get("numeric_count"):
        metrics.append(f"{summary['numeric_count']} score observations")

    return {
        "benchmark_name": result["name"],
        "task_definition": result.get("description") or undisclosed,
        "dataset_description": (
            f"openness={result.get('openness') or 'unknown'}, "
            f"has_dataset={result.get('has_dataset')}, has_paper={result.get('has_paper')}, "
            f"has_repo={result.get('has_repo')}；规模未在目录记录中披露。"
        ),
        "input_format": undisclosed,
        "output_format": undisclosed,
        "evaluation_protocol": undisclosed,
        "metrics": metrics or ["unknown"],
        "capabilities": result.get("categories") or [],
        "target_coverage": "unknown",
        "evidence_locator": {
            "catalog_key": result.get("key"),
            "catalog_source": result.get("source"),
            "source_url": result.get("source_url"),
            "slug": result.get("slug"),
            "retrieval_query": query,
        },
        "verification_status": "needs_review",
        "verified_at": None,
        "notes": (
            "来自 benchmark-radar 聚合目录（secondary），非 Raw Source。目录记录不含 "
            "task definition / input / output / evaluation protocol，不能据此判定 "
            "covered 或 not_covered；必须核查原始 Paper/Repo 后人工定论。"
        ),
    }


def probe_idea(idea: dict[str, Any], *, limit: int, write_coverage: bool) -> dict[str, Any]:
    idea_id = idea["id"]
    report: dict[str, Any] = {
        "idea_id": idea_id,
        "idea_name": idea["idea_name"],
        "domain": idea["domain"],
        "status": idea["status"],
        "total_score": idea["total_score"],
        "queries": [],
        "selected": [],
        "coverage_written": 0,
        "errors": [],
    }
    seen: set[str] = set()

    for query in build_queries(idea):
        run_at = now_iso()
        with db() as conn:
            run_id = conn.execute(
                """INSERT INTO retrieval_runs
                (idea_id,claim_id,radar,retrieval_query,retrieved_at,retriever_version,status,query_normalized)
                VALUES(?,?,?,?,?,?,?,?)""",
                (idea_id, None, "benchmark", query, run_at, RETRIEVER_VERSION, "running",
                 " ".join(query.lower().split())),
            ).lastrowid

        try:
            payload = search_catalog(query, limit)
        except Exception as exc:
            error = {"error_type": type(exc).__name__, "error_message": str(exc), "query": query}
            with db() as conn:
                conn.execute(
                    "UPDATE retrieval_runs SET status=?,completed_at=?,error_json=? WHERE id=?",
                    ("failed", now_iso(), json.dumps(error, ensure_ascii=False), run_id),
                )
            report["errors"].append(error)
            continue

        results = payload.get("results") or []
        query_report = {
            "query": query,
            "run_id": run_id,
            "total_matches": payload.get("total_matches"),
            "full_match_count": payload.get("full_match_count"),
            "candidates": len(results),
            "selected": 0,
            "rejected": 0,
        }

        with db() as conn:
            for result in results:
                selected, reason = judge(idea, result)
                conn.execute(
                    """INSERT INTO retrieval_results
                    (retrieval_run_id,source_item_id,title,url,source_quality,selected,rejection_reason,rank,created_at)
                    VALUES(?,?,?,?,?,?,?,?,?)""",
                    (run_id, None, result.get("name"), result.get("source_url"), "secondary",
                     int(selected), None if selected else reason, result.get("rank"), now_iso()),
                )
                if selected:
                    query_report["selected"] += 1
                    key = result.get("key") or result.get("name")
                    if key in seen:
                        continue
                    seen.add(key)
                    report["selected"].append({
                        "name": result.get("name"),
                        "key": result.get("key"),
                        "catalog_source": result.get("source"),
                        "categories": result.get("categories"),
                        "source_url": result.get("source_url"),
                        "query_coverage": (result.get("match") or {}).get("query_coverage"),
                        "reason": reason,
                        # 完整目录记录与命中查询留给 coverage 写入阶段使用，
                        # 报告输出时剔除，避免 JSON 过大。
                        "_record": result,
                        "_query": query,
                    })
                else:
                    query_report["rejected"] += 1

            conn.execute(
                "UPDATE retrieval_runs SET result_count=?,status=?,completed_at=? WHERE id=?",
                (len(results), "completed" if results else "completed_no_results", now_iso(), run_id),
            )
        report["queries"].append(query_report)

    if write_coverage:
        # upsert_coverage_entry 以 (idea_id, benchmark_name) 为唯一键，冲突即覆盖。
        # 人工已核查的行（verified / partial / needs_review 之外的状态）不能被
        # 目录检索结果改写成 needs_review——那会静默丢掉人工结论。
        with db() as conn:
            protected = {
                row["benchmark_name"]
                for row in conn.execute(
                    """SELECT benchmark_name FROM benchmark_coverage
                       WHERE idea_id=? AND verification_status IN ('verified','partial')""",
                    (idea_id,),
                ).fetchall()
            }
        for item in report["selected"]:
            if item["name"] in protected:
                item["reason"] += "｜已有人工核查结论，跳过写入以免覆盖"
                report.setdefault("skipped_protected", []).append(item["name"])
                continue
            upsert_coverage_entry(idea_id, coverage_entry(idea_id, item["_record"], item["_query"]))
            report["coverage_written"] += 1

    # 内部字段不进报告
    for item in report["selected"]:
        item.pop("_record", None)
        item.pop("_query", None)

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="用 benchmark-radar 目录为 Idea 检索 Coverage 候选")
    parser.add_argument("--idea", type=int, action="append", help="只跑指定 Idea，可重复")
    parser.add_argument("--limit", type=int, default=10, help="每条查询取前 N 条候选")
    parser.add_argument("--dry-run", action="store_true", help="只检索并记录日志，不写 benchmark_coverage")
    parser.add_argument("--output", default="outputs/coverage_probe/coverage_probe.json")
    parser.add_argument("--no-sync", action="store_true", help="跳过目录同步，用本地已有版本")
    args = parser.parse_args()

    sync = {"status": "skipped"} if args.no_sync else sync_catalog()
    print(f"目录同步：{json.dumps(sync, ensure_ascii=False)}", file=sys.stderr)

    init_db()
    ideas = list_ideas()
    if args.idea:
        wanted = set(args.idea)
        ideas = [x for x in ideas if x["id"] in wanted]
    if not ideas:
        print("没有匹配的 Idea", file=sys.stderr)
        return 1

    reports = [
        probe_idea(idea, limit=args.limit, write_coverage=not args.dry_run)
        for idea in ideas
    ]

    summary = {
        "generated_at": now_iso(),
        "retriever_version": RETRIEVER_VERSION,
        "catalog_repo": str(RADAR_REPO),
        # 记录目录数据版本：核查结论只对该版本的目录成立。
        "catalog_sync": sync,
        "dry_run": args.dry_run,
        "idea_count": len(reports),
        "selected_total": sum(len(x["selected"]) for x in reports),
        "coverage_written_total": sum(x["coverage_written"] for x in reports),
        "error_total": sum(len(x["errors"]) for x in reports),
        "ideas": reports,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "ideas"}, ensure_ascii=False, indent=2))
    print(f"\n完整报告：{output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

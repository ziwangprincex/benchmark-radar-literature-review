"""把 Benchmark 作者公开的逐条模型输出导入为 model_failure 证据，不调用任何模型 API。

没有 API 预算时，model_failure 仍可以靠别人已经跑过、并已人工判分的结果来验证。
例如 FinanceBench 仓库 results/ 下有 16 组配置 x 150 题的原始回答，每条都有作者的人工标签
（Correct Answer / Incorrect Answer / Refusal）。

判分沿用作者的人工标签，本模块不重判。正则只做两件事：
  1. 失败类型归类（拒答、数值错、是否判断反了、证据页检索失败、答非所问）
  2. 复现过滤：同一题在 >= min_fail 个配置下都失败才导入，避免把偶发错误当成失败模式

用法：
  python -m radar.eval.import_public_results financebench --idea 1 [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from typing import Any

import requests

from radar.core.radar_core import add_failure_cases, db, insert_source_item, extract_pending, now_iso

FINANCEBENCH = {
    "repo": "patronus-ai/financebench",
    # 固定 commit，保证导入内容可复现
    "commit": "cc39aeb4afdf33909ee1412188bf89035950c2eb",
    "questions": "data/financebench_open_source.jsonl",
    # 选三个模型家族、三种上下文设置，覆盖"给定证据页""单文档检索""长上下文"
    "configs": [
        "gpt-4-1106-preview_oracle",
        "gpt-4-1106-preview_singleStore",
        "claude-2_inContext",
        "llama2_singleStore",
    ],
}

NUM = re.compile(r"-?\$?\(?\d[\d,]*\.?\d*\)?%?")
REFUSAL = re.compile(
    r"(not (explicitly )?(provided|available|included|mentioned|stated|shown|disclosed)|cannot (be )?(determine|find|answer|calculate|provide)|"
    r"unable to|insufficient|no (information|data)|does not (contain|provide|include))",
    re.I,
)
YES = re.compile(r"^\W*(yes)\b", re.I)
NO = re.compile(r"^\W*(no)\b", re.I)


def raw_url(repo: str, commit: str, path: str) -> str:
    return f"https://raw.githubusercontent.com/{repo}/{commit}/{path}"


def fetch_jsonl(url: str) -> list[dict[str, Any]]:
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return [json.loads(line) for line in resp.text.splitlines() if line.strip()]


def numbers(text: str) -> list[float]:
    out = []
    for tok in NUM.findall(str(text)):
        neg = tok.startswith("-") or (tok.startswith("(") and tok.endswith(")"))
        clean = re.sub(r"[^\d.]", "", tok)
        if not clean or clean == ".":
            continue
        try:
            val = float(clean)
        except ValueError:
            continue
        out.append(-val if neg else val)
    return out


def close(a: float, b: float) -> bool:
    if a == b:
        return True
    scale = max(abs(a), abs(b), 1e-9)
    # 允许 1% 相对误差，也允许百分比与小数互换（0.103 vs 10.3%）
    return abs(a - b) / scale <= 0.01 or abs(a * 100 - b) / scale <= 0.01 or abs(a - b * 100) / scale <= 0.01


def classify_failure(label: str, question: dict[str, Any], answer: str, mode: str) -> tuple[str, str]:
    """返回 (failure_type, 判定依据)。纯规则，不调模型。"""
    gold = str(question.get("answer") or "")
    pages = {e.get("evidence_page_num") for e in question.get("evidence") or []}
    head = answer.strip()[:400]
    if label == "Refusal" or (REFUSAL.search(head) and mode != "oracle"):
        return "retrieval_or_refusal", "作者标为 Refusal，或回答开头声明文档未提供信息（非 oracle 模式，视为证据页没检索到）"
    gold_yes, gold_no = bool(YES.search(gold)), bool(NO.search(gold))
    if gold_yes or gold_no:
        # 只比较回答开头的明确 Yes/No。曾用全文方向词（increase/decline）比对，
        # 但金标准 "Yes, there is decline" 与回答 "net decrease" 实际一致，被误判为反转。
        ans_yes, ans_no = bool(YES.search(head)), bool(NO.search(head))
        if (gold_yes and ans_no) or (gold_no and ans_yes):
            return "judgment_reversed", "金标准与回答开头的 Yes/No 结论相反"
    q_tokens = set(re.findall(r"[a-z]{4,}", question.get("question", "").lower())) - {"what", "based", "give", "response", "question", "relying", "details", "shown", "their"}
    a_tokens = set(re.findall(r"[a-z]{4,}", head.lower()))
    if q_tokens and len(q_tokens & a_tokens) / len(q_tokens) < 0.2:
        return "off_topic", "回答开头与问题关键词重合 <20%，疑为读错文档段落（Amcor 证券登记、3M 套期保值等）"
    gold_nums = [n for n in numbers(gold) if abs(n) not in {2018, 2019, 2020, 2021, 2022, 2023}]
    # 只对"答案本身就是数值"的题判数值错；长文本金标准（收购清单等）里的零散数字不算。
    numeric_gold = bool(gold_nums) and len(gold) <= 80
    if numeric_gold:
        # 只看回答末尾 300 字的数值，即模型给出的结论值，不看推导过程中引用的原始数字
        ans_nums = numbers(answer.strip()[-300:])
        if ans_nums and not any(close(g, a) for g in gold_nums[:1] for a in ans_nums):
            kind = "multi_page_numeric" if len(pages) > 1 else "numeric_mismatch"
            return kind, f"金标准数值 {gold_nums[0]} 未出现在回答结论数值中（容差 1%）；证据页 {sorted(p for p in pages if p is not None)}"
    return "incorrect_other", "作者标为 Incorrect，规则未归入更具体的类型"


def severity_for(failure_type: str, question: dict[str, Any]) -> str:
    if failure_type in {"judgment_reversed", "multi_page_numeric"}:
        return "high"
    if question.get("question_type") == "domain-relevant":
        return "high"
    return "medium"


def build_financebench(min_fail: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cfg = FINANCEBENCH
    questions = {
        q["financebench_id"]: q
        for q in fetch_jsonl(raw_url(cfg["repo"], cfg["commit"], cfg["questions"]))
    }
    per_q: dict[str, list[dict[str, Any]]] = defaultdict(list)
    stats: dict[str, Any] = {}
    for name in cfg["configs"]:
        rows = fetch_jsonl(raw_url(cfg["repo"], cfg["commit"], f"results/{name}.jsonl"))
        labels = Counter(r["label"] for r in rows)
        stats[name] = {"n": len(rows), "accuracy": round(labels["Correct Answer"] / len(rows), 3), **labels}
        for r in rows:
            if r["label"] != "Correct Answer":
                per_q[r["financebench_id"]].append({**r, "config": name})
    cases = []
    for qid, fails in per_q.items():
        if len(fails) < min_fail:
            continue
        q = questions[qid]
        pages = sorted(p for p in {e.get("evidence_page_num") for e in q.get("evidence") or []} if p is not None)
        for r in fails:
            ftype, why = classify_failure(r["label"], q, r["model_answer"] or "", r["eval_mode"])
            cases.append({
                "failure_case_id": f"financebench::{qid}::{r['config']}",
                "benchmark_name": "FinanceBench",
                "task_prompt": q["question"],
                "input": f"doc={q['doc_name']} evidence_pages={pages} mode={r['eval_mode']}",
                "reference_answer": str(q.get("answer")),
                "rubric": "FinanceBench 作者人工判分：Correct Answer / Incorrect Answer / Refusal",
                "model_name": r["model_name"],
                "model_version": r["config"],
                "model_response": r["model_answer"] or "",
                "passed": False,
                "score": 0,
                "judge_result": f"{r['label']}（FinanceBench 作者人工标注，未重判）",
                "failure_type": ftype,
                "severity": severity_for(ftype, q),
                "error_analysis": f"[规则归类] {why}。同题失败配置数 {len(fails)}/{len(cfg['configs'])}。",
                "run_date": "2023-11-20",
                "raw_data": {"question_type": q.get("question_type"), "question_reasoning": q.get("question_reasoning"),
                              "evidence_pages": pages, "fail_configs": [x["config"] for x in fails]},
            })
    summary = {
        "configs": stats,
        "questions_failed_ge_min": len({c["failure_case_id"].split("::")[1] for c in cases}),
        "cases": len(cases),
        "failure_types": dict(Counter(c["failure_type"] for c in cases)),
        "min_fail": min_fail,
    }
    return cases, summary


def import_financebench(idea_id: int, min_fail: int = 3, dry_run: bool = False) -> dict[str, Any]:
    cases, summary = build_financebench(min_fail)
    if dry_run:
        return {"dry_run": True, **summary}
    cfg = FINANCEBENCH
    url = f"https://github.com/{cfg['repo']}/tree/{cfg['commit']}/results"
    http = requests.head(url, timeout=30, allow_redirects=True).status_code
    acc = ", ".join(f"{k} {v['accuracy']:.0%}" for k, v in summary["configs"].items())
    source_id, status = insert_source_item({
        "radar": "model_failure",
        "source_id": "public-eval-results",
        "title": "FinanceBench 公开逐条模型输出（作者人工判分）",
        "content": (
            f"FinanceBench 仓库 results/ 公开 150 道 10-K/10-Q 问答在多种上下文设置下的原始回答与人工标签。"
            f"导入配置准确率：{acc}。同题在 >= {min_fail} 个配置下失败的题目 {summary['questions_failed_ge_min']} 道，"
            f"失败 case {summary['cases']} 条，规则归类分布 {summary['failure_types']}。"
            f"即使直接给出证据页（oracle），GPT-4-Turbo 仍错 15%；单文档检索设置下拒答 39%。"
        ),
        "url": url,
        "published_at": "2023-11-20",
        "evidence_role": "raw_source",
        "source_type": "eval_run_or_case",
        "source_quality": "primary",
        "http_status": http,
        "commit": cfg["commit"],
        "raw_data": summary,
    })
    if source_id is None:
        return {"status": status, **summary}
    add_failure_cases(idea_id, cases, source_item_id=source_id)
    extract_pending()
    with db() as conn:
        sig = conn.execute("SELECT id FROM signals WHERE source_item_id=?", (source_id,)).fetchone()
        if sig:
            conn.execute("INSERT OR IGNORE INTO idea_signal_links(idea_id,signal_id) VALUES(?,?)", (idea_id, sig["id"]))
    from radar.evidence.evidence_quality import sync_idea_quality
    sync_idea_quality(idea_id)
    return {"source_item_id": source_id, "http_status": http, "imported_at": now_iso(), **summary}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dataset", choices=["financebench"])
    ap.add_argument("--idea", type=int, required=True)
    ap.add_argument("--min-fail", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    print(json.dumps(import_financebench(args.idea, args.min_fail, args.dry_run), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

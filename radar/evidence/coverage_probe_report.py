"""把 coverage_probe 的结果整理成人工 Coverage 核查用的一页报告。

报告只回答一个问题：每个 Idea 的"已有 Benchmark 未覆盖 X"这条 Claim，
现在有多少可核查对象，以及是否还站得住。不给覆盖结论——目录元数据不支撑。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from radar.core.radar_core import db

# 每条查询取前 N 条候选；命中数接近上限说明主题过宽，检索没有区分度。
WIDE_TOPIC_THRESHOLD = 8


def existing_coverage(idea_id: int) -> list[dict]:
    """人工已核查的 coverage 行（非本次目录检索写入的）。"""
    with db() as conn:
        return [dict(x) for x in conn.execute(
            """SELECT benchmark_name, target_coverage, verification_status, notes
               FROM benchmark_coverage
               WHERE idea_id=? AND verification_status != 'needs_review'
               ORDER BY benchmark_name""",
            (idea_id,),
        ).fetchall()]


def verdict(idea: dict, selected_count: int) -> tuple[str, str]:
    """给出下一步人工动作的建议，不给覆盖结论。"""
    if selected_count == 0:
        return "gap_holds_pending_review", (
            "目录中没有找到同领域且触及该任务的基准。Gap Claim 暂时站得住，"
            "但目录不等于全部世界——仍需人工确认目录外是否已有覆盖。"
        )
    if selected_count >= WIDE_TOPIC_THRESHOLD:
        return "topic_too_wide", (
            f"检索命中 {selected_count} 条同领域基准，接近每查询取样上限，"
            "说明该 Idea 主题过宽、缺乏区分度。应先收窄任务定义，再谈 Gap。"
        )
    return "needs_manual_coverage_analysis", (
        f"有 {selected_count} 条候选需要人工核查原始 Paper/Repo 的 task definition "
        "与 evaluation protocol，才能判定是否真的覆盖目标任务。"
    )


def build(probe_path: Path) -> dict:
    probe = json.loads(probe_path.read_text(encoding="utf-8"))
    rows = []
    for idea in probe["ideas"]:
        selected = idea["selected"]
        code, advice = verdict(idea, len(selected))
        rows.append({
            "idea_id": idea["idea_id"],
            "idea_name": idea["idea_name"],
            "domain": idea["domain"],
            "status": idea["status"],
            "total_score": idea["total_score"],
            "queries": [q["query"] for q in idea["queries"]],
            "catalog_candidates": sum(q["candidates"] for q in idea["queries"]),
            "selected_count": len(selected),
            "selected": selected,
            "verdict": code,
            "advice": advice,
            "existing_manual_coverage": existing_coverage(idea["idea_id"]),
            "errors": idea["errors"],
        })

    rows.sort(key=lambda x: -x["total_score"])
    by_verdict: dict[str, int] = {}
    for row in rows:
        by_verdict[row["verdict"]] = by_verdict.get(row["verdict"], 0) + 1

    return {
        "generated_at": probe["generated_at"],
        "retriever_version": probe["retriever_version"],
        "catalog_repo": probe["catalog_repo"],
        "caveat": (
            "本报告基于 benchmark-radar 聚合目录（secondary 源）。目录记录只含 "
            "name/description/categories，不含 task definition、input/output 与 "
            "evaluation protocol，因此不能据此判定 covered 或 not_covered。"
            "所有写入 benchmark_coverage 的行均为 needs_review / unknown。"
        ),
        "verdict_summary": by_verdict,
        "ideas": rows,
    }


def to_markdown(report: dict) -> str:
    lines = [
        "# Coverage Probe｜外部 Benchmark 目录核查结果",
        "",
        f"生成时间：{report['generated_at']}　检索器：{report['retriever_version']}",
        "",
        f"> {report['caveat']}",
        "",
        "## 结论分布",
        "",
        "| Verdict | Idea 数 | 含义 |",
        "|---|---:|---|",
    ]
    meaning = {
        "gap_holds_pending_review": "目录内无同领域同任务基准，Gap 暂时站得住",
        "needs_manual_coverage_analysis": "有少量候选，需人工核查原文定论",
        "topic_too_wide": "命中过多，主题过宽缺区分度，应先收窄",
    }
    for code, count in sorted(report["verdict_summary"].items(), key=lambda x: -x[1]):
        lines.append(f"| `{code}` | {count} | {meaning.get(code, '')} |")

    lines += ["", "## 逐 Idea 结果", ""]
    for row in report["ideas"]:
        lines += [
            f"### Idea {row['idea_id']}｜{row['idea_name']}",
            "",
            f"- Domain：{row['domain']}　Status：{row['status']}　Score：{row['total_score']}",
            f"- 目录候选：{row['catalog_candidates']} 条　进入核查：{row['selected_count']} 条",
            f"- Verdict：**`{row['verdict']}`**",
            f"- 建议：{row['advice']}",
        ]
        if row["existing_manual_coverage"]:
            names = "、".join(
                f"{x['benchmark_name']}({x['target_coverage']}/{x['verification_status']})"
                for x in row["existing_manual_coverage"]
            )
            lines.append(f"- 已有人工核查：{names}")
        if row["selected"]:
            lines += ["", "| Benchmark | 目录源 | 判定依据 |", "|---|---|---|"]
            for item in row["selected"]:
                reason = item["reason"].replace("|", "\\|")
                lines.append(f"| {item['name']} | {item['catalog_source']} | {reason} |")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", default="outputs/coverage_probe/coverage_probe.json")
    parser.add_argument("--out-dir", default="outputs/coverage_probe")
    args = parser.parse_args()

    report = build(Path(args.probe))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "coverage_review.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "coverage_review.md").write_text(to_markdown(report), encoding="utf-8")

    print(json.dumps(report["verdict_summary"], ensure_ascii=False, indent=2))
    print(f"\n{out_dir}/coverage_review.md")
    print(f"{out_dir}/coverage_review.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

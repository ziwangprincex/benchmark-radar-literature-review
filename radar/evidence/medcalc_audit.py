"""MedCalc-Bench 复核：拿 MedHELM 公开逐题输出，对照 MedCalc-Bench v1.0 原题和 Verified 修正版重新判分。

为什么要复核：MedHELM v4.0.0 对 MedCalc-Bench 的判分有 bug，化验类（lab）315 道、剂量类（dosage）39 道
所有模型都是 0 分，答案落在题目自带的容差范围内也判错（例：第 959 题，标准答案 233.554，
容差 221.9~245.2，模型答 233.612 判错）。直接用它的准确率会把模型说得比实际差很多。

步骤（全部可复现，不调模型）：
1. 下载 13 个模型的逐题输出（display_predictions.json）和题目（instances.json）。
2. MedHELM 的题号 = MedCalc-Bench v1.0 测试集的 Row Number，按题号 + 病历文本对齐 v1.0。
3. 按 v1.0 的上下限重新判分。
4. 按病历全文 + 计算器编号严格对齐 MedCalc-Bench-Verified，用修正后的答案再判一遍。
5. 取 6 个强模型（推理模型）在 Verified 答案下仍然 <= 2 个做对的题，逐题人工归类错因。

人工归类结果在 data/medcalc_audit/hard_labeled.json，本模块只负责重算数字和写入证据库。

用法：python3 -m radar.evidence.medcalc_audit [--dry-run]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from radar.core.radar_core import db, extract_pending, insert_source_item, now_iso

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "data" / "medcalc_audit"
STRONG = ["deepseek-ai_deepseek-r1", "google_gemini-2.5-pro-preview-05-06", "openai_gpt-5-2025-08-07",
          "openai_gpt-5-mini-2025-08-07", "openai_o3-mini-2025-01-31", "openai_o4-mini-2025-04-16"]
MEDHELM_ITEM_TITLE = "医疗 · MedHELM 公开逐题结果：MedCalc-Bench：从病历里算临床评分和剂量"

PAPERS = [
    {"arxiv": "2406.12036", "title": "MedCalc-Bench: Evaluating Large Language Models for Medical Calculations",
     "org": "NCBI/NIH", "published": "2024-06-17"},
    {"arxiv": "2509.16584", "title": "From Scores to Steps: Diagnosing and Improving LLM Performance in Evidence-Based Medical Calculations",
     "org": "EMNLP 2025", "published": "2025-09-20"},
    {"arxiv": "2510.27267", "title": "MedCalc-Eval and MedCalc-Env: Advancing Medical Calculation Capabilities of Large Language Models",
     "org": "arXiv", "published": "2025-10-31"},
    {"arxiv": "2512.19691", "title": "Scalable Stewardship of an LLM-Assisted Clinical Benchmark with Physician Oversight",
     "org": "Stanford", "published": "2025-12-22"},
]


def num(s: str) -> float | None:
    s = s.replace(",", "")
    m = re.findall(r"-?\d+\.?\d*", s)
    return float(m[-1]) if m and len(s) < 40 else None


def weeks_days(s: str) -> tuple[int, int] | None:
    m = re.findall(r"\d+", s)
    return (int(m[0]), int(m[1])) if len(m) >= 2 else None


def date_of(s: str) -> tuple[int, int, int] | None:
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", s)
    if not m:
        return None
    y = int(m.group(3))
    return int(m.group(1)), int(m.group(2)), y + 2000 if y < 100 else y


def judge(pred: str, gold: Any, lo: Any, hi: Any) -> bool:
    gold = str(gold)
    if "week" in gold:
        return weeks_days(pred) is not None and weeks_days(pred) == weeks_days(gold)
    if "/" in gold:
        return date_of(pred) is not None and date_of(pred) == date_of(gold)
    v = num(pred)
    if v is None:
        return False
    try:
        return float(lo) - 1e-9 <= v <= float(hi) + 1e-9
    except (TypeError, ValueError):
        return abs(v - float(gold)) < 1e-6


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def align() -> dict[str, dict[str, Any]]:
    csv.field_size_limit(10 ** 9)
    instances = json.loads((AUDIT / "instances.json").read_text())
    v10 = {str(r["Row Number"]): r for r in json.loads((AUDIT / "v10_test.json").read_text())}
    verified: dict[tuple[str, str], list[dict]] = {}
    for w in csv.DictReader(open(AUDIT / "verified_test.csv")):
        verified.setdefault((_norm(w["Patient Note"]), w["Calculator ID"]), []).append(w)
    out = {}
    for x in instances:
        r = v10.get(x["id"])
        if not r:
            continue
        note = x["input"]["text"].split("Patient note:", 1)[1].split("Question:")[0]
        if _norm(r["Patient Note"])[:200] != _norm(note)[:200]:
            continue
        c = verified.get((_norm(r["Patient Note"]), str(r["Calculator ID"])), [])
        out[x["id"]] = {"v10": r, "verified": c[0] if len(c) == 1 else None}
    return out


def compute() -> dict[str, Any]:
    preds = json.loads((AUDIT / "predictions.json").read_text())
    models = list(preds)
    al = align()
    helm = {m: sum(preds[m][i]["acc"] >= 1 for i in al) / len(al) for m in models}
    tol = {m: sum(judge(preds[m][i]["pred"], a["v10"]["Ground Truth Answer"], a["v10"]["Lower Limit"], a["v10"]["Upper Limit"])
                  for i, a in al.items()) / len(al) for m in models}
    sub = {i: a for i, a in al.items() if a["verified"]}
    ver = {m: sum(judge(preds[m][i]["pred"], a["verified"]["Ground Truth Answer"], a["verified"]["Lower Limit"], a["verified"]["Upper Limit"])
                  for i, a in sub.items()) / len(sub) for m in models}
    ver_v10 = {m: sum(judge(preds[m][i]["pred"], a["v10"]["Ground Truth Answer"], a["v10"]["Lower Limit"], a["v10"]["Upper Limit"])
                      for i, a in sub.items()) / len(sub) for m in models}
    changed = [i for i, a in sub.items()
               if not judge(str(a["verified"]["Ground Truth Answer"]), a["v10"]["Ground Truth Answer"], a["v10"]["Lower Limit"], a["v10"]["Upper Limit"])]
    zero_cats = sorted({a["v10"]["Category"] for i, a in al.items()} -
                       {a["v10"]["Category"] for i, a in al.items() if any(preds[m][i]["acc"] >= 1 for m in models)})
    labeled = json.loads((AUDIT / "hard_labeled.json").read_text())
    return {
        "aligned": len(al), "verified_subset": len(sub), "verified_changed": len(changed),
        "helm_acc": helm, "tolerance_acc": tol, "subset_v10_acc": ver_v10, "subset_verified_acc": ver,
        "helm_zero_categories": zero_cats,
        "strong_hard": len(labeled), "strong_hard_labels": dict(Counter(o["label"] for o in labeled)),
        "true_errors": [o for o in labeled if o["label"] == "真错"],
    }


def _pct(d: dict[str, float], m: str) -> str:
    return f"{d[m]:.0%}"


def corrected_item(s: dict[str, Any]) -> dict[str, Any]:
    best = max(s["tolerance_acc"], key=s["tolerance_acc"].get)
    worst = min(s["tolerance_acc"], key=s["tolerance_acc"].get)
    lab = s["strong_hard_labels"]
    order = ["公式口径", "信息缺失约定", "主观项", "题意歧义", "判分问题", "阈值边界", "真错"]
    lab_txt = "，".join(f"{k} {lab[k]}" for k in order if k in lab)
    content = (
        f"MedHELM v4.0.0 公开了 13 个模型在 MedCalc-Bench 1000 道题上的逐题输出。注意：MedHELM 自己的判分有 bug，"
        f"化验类和剂量类题目所有模型都是 0 分，答案落在题目给的容差内也判错，所以它报的最高 35% 不可信。"
        f"按题目自带上下限重判（对上 v1.0 原题 {s['aligned']} 道）后，最好的 {best} {_pct(s['tolerance_acc'], best)}，最差 {worst} {_pct(s['tolerance_acc'], worst)}。"
        f"再用 MedCalc-Bench-Verified 修正后的答案判（严格对上 {s['verified_subset']} 道，其中 {s['verified_changed']} 道答案被改过），"
        f"6 个推理模型准确率在 {min(s['subset_verified_acc'][m] for m in STRONG):.0%} 到 {max(s['subset_verified_acc'][m] for m in STRONG):.0%}。"
        f"6 个推理模型里至多 2 个做对的题 {s['strong_hard']} 道，逐题看错因：{lab_txt}。"
        f"也就是说强模型剩下的“错”大多不是不会算，而是题目没定清楚：同一个评分有不同公式版本（如预产期按 280 天还是 Naegele 日历法、"
        f"正常阴离子间隙取 10 还是 12）、病历没写的项目要不要当阴性、主观项怎么判。真正取数或计算出错的只有 {lab.get('真错', 0)} 道。"
        f"这件事已有论文系统做过：Stanford 的 MedCalc-Bench 标签审计（arXiv 2512.19691）发现至少 27% 测试标签有误或无法计算，"
        f"From Scores to Steps（EMNLP 2025）已把错误拆成选公式、取数、算术三步评测。"
    )
    return {
        "radar": "model_failure", "source_id": "medhelm-medcalc-audit",
        "title": "医疗 · MedCalc-Bench 复核：MedHELM 判分有误，强模型剩下的错多为题目口径不清",
        "content": content,
        "url": "https://huggingface.co/datasets/nsk7153/MedCalc-Bench-Verified",
        "published_at": now_iso()[:10], "evidence_role": "raw_source", "source_type": "eval_run_or_case",
        "source_quality": "primary", "http_status": 200, "organization": "本地复核（MedHELM v4 逐题输出 + MedCalc-Bench v1.0/Verified）",
        "source_version": "MedHELM v4.0.0 / MedCalc-Bench v1.0 / Verified", "run_id": "medcalc-audit", "retrieved_at": now_iso(),
        "raw_data": {k: v for k, v in s.items() if k != "true_errors"} | {
            "true_error_ids": [o["id"] for o in s["true_errors"]],
            "audit_dir": str(AUDIT.relative_to(ROOT)),
            "concerns": ["数值/计算", "评测有效性"], "tasks": ["推理/计算"], "inputs": ["长文档"]},
    }


def paper_items() -> list[dict[str, Any]]:
    import feedparser
    import requests
    ids = ",".join(p["arxiv"] for p in PAPERS)
    r = requests.get("https://export.arxiv.org/api/query", params={"id_list": ids, "max_results": 10}, timeout=60)
    r.raise_for_status()
    summaries = {e.id.split("/")[-1].split("v")[0]: " ".join(e.summary.split()) for e in feedparser.parse(r.content).entries}
    items = []
    for p in PAPERS:
        if p["arxiv"] not in summaries:
            continue
        items.append({
            "radar": "benchmark", "source_id": "arxiv-benchmark-sweep", "title": p["title"],
            "content": summaries[p["arxiv"]], "url": f"https://arxiv.org/abs/{p['arxiv']}",
            "published_at": p["published"], "organization": p["org"], "source_quality": "primary",
            "source_type": "paper", "http_status": 200, "retrieved_at": now_iso(),
        })
    return items


def run(dry_run: bool = False) -> dict[str, Any]:
    s = compute()
    item = corrected_item(s)
    papers = paper_items()
    if dry_run:
        return {"dry_run": True, "content": item["content"], "papers": [p["title"] for p in papers]}
    with db() as conn:
        old = conn.execute("SELECT id FROM source_items WHERE title=?", (MEDHELM_ITEM_TITLE,)).fetchone()
        if old:
            conn.execute("DELETE FROM source_items WHERE id=?", (old["id"],))
    states = Counter()
    for it in [item] + papers:
        states[insert_source_item(it)[1]] += 1
    return {"replaced_old": bool(old), "insert": dict(states), "extract": extract_pending(),
            "summary": {k: v for k, v in s.items() if k not in ("true_errors",)}}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    print(json.dumps(run(a.dry_run), ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())

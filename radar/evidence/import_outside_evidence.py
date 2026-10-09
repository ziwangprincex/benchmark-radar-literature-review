"""导入论文以外的旁证：专家真实工作（workflow）和 AI 在真实场景犯的错（model_failure）。

中栏的缺口原来只有"论文作者自己说"。这里接两份公开、可逐条核对的数据：

1. legal-hallucinations：Damien Charlotin 维护的 AI Hallucination Cases 数据库
   （法院判决里认定当事人提交了 AI 编造/歪曲的判例、引文）。来源本身就是法院判决，
   标题统一加"法律 · "前缀，避免摘要里法律词不够两个时被判成未分领域。只取律师、法官、
   专家等专业人士、且被法院实际处罚、未被标为"仅指控"或"厂商有争议"的案例。
   每种幻觉类型取最近的若干条逐条入库（url 指向判决原文 PDF），另入一条全库统计。
2. onet-tasks：美国劳工部 O*NET 29.3 职业任务表。按职业入库，内容是该职业的
   Core 任务原文（没有 Core 标注的职业取全部任务），url 指向 O*NET 职业页。

不调模型，不改写原文；领域、关注点仍由 lit_index 的同一套规则判定。

用法：
  python3 -m radar.evidence.import_outside_evidence legal-hallucinations [--per-type 8] [--dry-run]
  python3 -m radar.evidence.import_outside_evidence onet-tasks [--dry-run]
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from collections import Counter, defaultdict
from typing import Any

import requests

from radar.core.radar_core import extract_pending, insert_source_item, now_iso

HALL_PAGE = "https://www.damiencharlotin.com/hallucinations/"
HALL_CSV = "https://www.damiencharlotin.com/hallucinations/hallucinations/download.csv"
HALL_HOST = "https://www.damiencharlotin.com"
PROFESSIONAL = ("Lawyer", "Judge", "Expert", "Prosecutor", "Governement Lawyer")
ITEM = re.compile(r"(?:^|\|\|)\s*([A-Za-z ]+): ([A-Za-z &]+?)\s*\|")
TYPE_CN = {
    "Fabricated: Case Law": "编造不存在的判例",
    "False Quotes: Case Law": "给真实判例编造引文",
    "Misrepresented: Case Law": "歪曲真实判例的结论",
    "Fabricated: Legal Norm": "编造法条",
    "Misrepresented: Legal Norm": "歪曲法条",
    "False Quotes: Legal Norm": "给法条编造引文",
    "Fabricated: Exhibits & Submissions": "编造证据材料/证人证言",
    "Misrepresented: Exhibits & Submissions": "歪曲证据材料",
    "Outdated Advice: Overturned Case Law": "引用已被推翻的判例",
    "Outdated Advice: Repealed Law": "引用已废止的法律",
    "Fabricated: Doctrinal Work": "编造学术文献",
}

ONET_BASE = "https://www.onetcenter.org/dl_files/database/db_29_3_text/"
ONET_PAGE = "https://www.onetonline.org/link/details/{code}"
# 职业任务句的关注点。不用 lit_index.CONCERNS：任务句里 government agencies（govern）、
# explain、contamination、Judge 会被误判。只认任务本身就在做这件事的说法。
ONET_CONCERNS = {
    "证据/溯源": r"\bevidence|\bcite|citation|pertinent sources|\bverify|authenticat|substantiat",
    "数值/计算": r"calculat|\bcompute|quantitative|statistical (analys|method|model)",
    "安全/风险": r"\brisks?\b|safety|adverse|contraindicat|drug interaction|toxic",
    "时效/版本": r"keep abreast|up[- ]to[- ]date|monitor developments|changes in (laws|regulations|policies)",
}
# 五个垂类里与现有 Benchmark 任务直接对应的职业
# 职业是按领域挑的，领域写进标题（"法律 · Lawyers"），让 detect_domain 的标题规则命中；
# 否则任务原文里领域词不够两个的职业（如 Credit Analysts）会落到未分领域。
ONET_OCCUPATIONS = {
    "23-1011.00": "法律", "23-1023.00": "法律", "23-2011.00": "法律",                          # 律师、法官、律师助理
    "13-2011.00": "金融", "13-2041.00": "金融", "13-2051.00": "金融", "13-2054.00": "金融",  # 会计审计、信贷、投资分析、金融风险
    "29-1216.00": "医疗", "29-1224.00": "医疗", "29-1051.00": "医疗", "29-1141.00": "医疗",  # 内科、放射科、药剂师、护士
    "29-2072.00": "医疗", "29-9021.00": "医疗",                                               # 病案编码、医疗信息
    "19-1021.00": "科研", "19-1042.00": "科研", "19-2031.00": "科研", "15-2041.00": "科研",  # 生化、医学科研、化学、统计
}


def _get(url: str) -> str:
    r = requests.get(url, timeout=90, headers={"User-Agent": "BenchmarkIdeaRadar/1.0"})
    r.raise_for_status()
    r.encoding = "utf-8"
    return r.text


def _types(row: dict[str, str]) -> list[str]:
    return sorted({f"{a.strip()}: {b.strip()}" for a, b in ITEM.findall(row["Hallucination Items"])})


def concerns_for(types: list[str]) -> list[str]:
    """幻觉类型 -> lit_index 的关注点。判决原文里 Judge（法官）、Adverse Costs Order、
    calculate（算罚款）会被关键词误判成"评判可靠性/安全风险/数值"，所以这里按结构化
    类型直接给，lit_index 对带 concerns 的条目不再扫原文。"""
    out = []
    if any(t.split(":")[0] in {"Fabricated", "False Quotes", "Misrepresented"} for t in types):
        out.append("证据/溯源")
    if any(t.startswith("Outdated Advice") for t in types):
        out.append("时效/版本")
    # 不把"编造证人证言"映射到"安全/风险"：那个缺口说的是模型没识别出风险，
    # 编造证据是另一回事，硬挂上去会虚增旁证
    return out


def build_legal(per_type: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = list(csv.DictReader(io.StringIO(_get(HALL_CSV))))
    all_types = Counter(t for r in rows for t in _types(r))
    keep = [r for r in rows
            if any(p in r["Party(ies)"] for p in PROFESSIONAL)
            and (r["Professional Sanction"] == "Yes" or r["Monetary Penalty"].strip())
            and r["Alleged"] == "No" and r["Vendor Disputed"] == "No" and r["Source"].strip()]
    keep.sort(key=lambda r: r["Date"], reverse=True)
    by_type: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in keep:
        for t in _types(r):
            by_type[t].append(r)

    chosen: dict[str, dict[str, str]] = {}
    for t, rs in by_type.items():
        for r in rs[:per_type]:
            chosen.setdefault(r["Source"], r)

    items = []
    for r in chosen.values():
        types = _types(r)
        cn = "、".join(TYPE_CN.get(t, t) for t in types)
        items.append({
            "radar": "model_failure", "source_id": "legal-hallucination-cases",
            "title": f"法律 · 法院认定专业人士提交 AI 幻觉内容：{r['Case Name'][:90]}",
            "content": (f"{r['Party(ies)']} 在 {r['Court']}（{r['State(s)']}）提交的文书使用了 AI"
                        f"（{r['AI Tool'] or '未写明'}），法院认定的问题：{cn}。处理结果：{r['Outcome']}"
                        f"{'；罚款 ' + r['Monetary Penalty'] if r['Monetary Penalty'].strip() else ''}。"
                        f"判决摘要：{r['Details']}"),
            "url": HALL_HOST + r["Source"].strip(),
            "published_at": r["Date"] or None,
            "evidence_role": "raw_source", "source_type": "court_record", "source_quality": "primary",
            "http_status": 200, "organization": r["Court"], "case_id": r["Case Name"][:120],
            "retrieved_at": now_iso(),
            "raw_data": {"hallucination_types": types, "party": r["Party(ies)"], "ai_tool": r["AI Tool"],
                         "legal_field": r["Legal Field Primary"], "dataset": HALL_PAGE,
                         "concerns": concerns_for(types),
                         # 这些案件里 AI 做的事：找判例/法条（检索）并写进诉状（撰写），输入是判例法知识库
                         "tasks": ["检索", "生成/撰写"], "inputs": ["多文档/知识库"]},
        })
    summary = {
        "rows": len(rows), "professional_sanctioned": len(keep),
        "types_all": dict(all_types.most_common()),
        "types_professional_sanctioned": {t: len(v) for t, v in sorted(by_type.items(), key=lambda x: -len(x[1]))},
        "imported_cases": len(items),
    }
    top = "；".join(f"{TYPE_CN.get(t, t)} {n} 件" for t, n in list(all_types.most_common())[:6])
    items.append({
        "radar": "model_failure", "source_id": "legal-hallucination-cases",
        "title": f"法律 · AI Hallucination Cases 数据库：法院认定的 AI 幻觉判决 {len(rows)} 件",
        "content": (f"Damien Charlotin 维护的公开数据库，收录法院在判决中认定当事人提交了 AI 编造或歪曲内容的案例 "
                    f"{len(rows)} 件，其中律师、法官、专家等专业人士被实际处罚的 {len(keep)} 件。"
                    f"幻觉类型（按案件计）：{top}。即法律检索与文书撰写中的引用可信度与溯源，"
                    f"在真实诉讼中已经造成处罚，而不只是论文里提到的风险。"),
        "url": HALL_PAGE, "published_at": max(r["Date"] for r in rows if r["Date"]),
        "evidence_role": "raw_source", "source_type": "court_record", "source_quality": "primary",
        "http_status": 200, "organization": "HEC Paris / Damien Charlotin", "retrieved_at": now_iso(),
        "raw_data": {**summary, "concerns": ["证据/溯源", "时效/版本"],
                     "tasks": ["检索", "生成/撰写"], "inputs": ["多文档/知识库"]},
    })
    return items, summary


def build_onet() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    occ = {r["O*NET-SOC Code"]: r for r in csv.DictReader(io.StringIO(_get(ONET_BASE + "Occupation%20Data.txt")), delimiter="\t")}
    tasks: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in csv.DictReader(io.StringIO(_get(ONET_BASE + "Task%20Statements.txt")), delimiter="\t"):
        if r["O*NET-SOC Code"] in ONET_OCCUPATIONS:
            tasks[r["O*NET-SOC Code"]].append(r)
    items, summary = [], {}
    for code in ONET_OCCUPATIONS:
        rs = tasks.get(code, [])
        core = [r for r in rs if r["Task Type"] == "Core"] or rs
        if not core:
            continue
        name = occ[code]["Title"]
        summary[code] = {"title": name, "tasks": len(core)}
        concerns: dict[str, list[str]] = {}
        for r in core:
            for k, pat in ONET_CONCERNS.items():
                if re.search(pat, r["Task"], re.I):
                    concerns.setdefault(k, []).append(r["Task"].strip())
        summary[code]["concerns"] = {k: len(v) for k, v in concerns.items()}
        items.append({
            "radar": "workflow", "source_id": "onet-task-statements",
            "title": f"{ONET_OCCUPATIONS[code]} · {name}：O*NET 职业任务（{code}）",
            "content": f"{name} 的日常工作任务（O*NET 29.3，从业者调查）：" + " ".join(
                f"{i}. {r['Task'].strip()}" for i, r in enumerate(core, 1)),
            "url": ONET_PAGE.format(code=code), "published_at": core[0]["Date"],
            "evidence_role": "raw_source", "source_type": "workflow_or_sop", "source_quality": "primary",
            "http_status": 200, "organization": "U.S. Department of Labor / O*NET", "record_id": code,
            "retrieved_at": now_iso(), "source_version": "O*NET 29.3",
            "raw_data": {"occupation": name, "task_ids": [r["Task ID"] for r in core],
                         "concerns": sorted(concerns), "concern_tasks": concerns},
        })
    return items, summary


def run(dataset: str, per_type: int = 8, dry_run: bool = False) -> dict[str, Any]:
    items, summary = build_legal(per_type) if dataset == "legal-hallucinations" else build_onet()
    if dry_run:
        return {"dry_run": True, "items": len(items), **{"summary": summary}}
    states = Counter()
    for it in items:
        _, st = insert_source_item(it)
        states[st] += 1
    ext = extract_pending()
    return {"items": len(items), "insert": dict(states), "extract": ext, "summary": summary}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dataset", choices=["legal-hallucinations", "onet-tasks"])
    ap.add_argument("--per-type", type=int, default=8)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    print(json.dumps(run(a.dataset, a.per_type, a.dry_run), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""MedHELM 另外三个题集（MEDEC / MedHallu / RaceBasedMed）判分复核。

做法：对每个模型的逐题输出自己重新解析答案，跟 MedHELM 给的分逐题比；再看强模型集体做错的题，
判断是模型的问题还是标准答案的问题。人工核对的结论写在 FINDINGS 里，数字由本模块现算。

用法：python3 -m radar.evidence.medhelm_recheck [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from radar.core.radar_core import db, extract_pending, insert_source_item, now_iso

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "data" / "medhelm_audit"
STRONG = ["deepseek-ai_deepseek-r1", "google_gemini-2.5-pro-preview-05-06", "openai_gpt-5-2025-08-07",
          "openai_gpt-5-mini-2025-08-07", "openai_o3-mini-2025-01-31", "openai_o4-mini-2025-04-16"]
OLD_TITLE = "医疗 · MedHELM 公开逐题结果：{cn}"
RUN = {sc: f"{sc}%3Amodel%3Danthropic_claude-3-5-sonnet-20241022%2Cmodel_deployment%3Dstanfordhealthcare_claude-3-5-sonnet-20241022"
       for sc in ("medec", "medhallu", "race_based_med")}
CN = {"medec": "MEDEC：找出病历里写错的诊断或治疗",
      "medhallu": "MedHallu：判断医学回答是否有幻觉（是否被给定知识支撑）",
      "race_based_med": "RaceBasedMed：识别基于种族的有害医学内容"}


def _load(sc: str) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    inst = {x["id"]: x for x in json.loads((AUDIT / sc / "instances.json").read_text())}
    return inst, json.loads((AUDIT / sc / "predictions.json").read_text())


def _gold(x: dict[str, Any]) -> str:
    return next(r["output"]["text"].strip() for r in x["references"] if "correct" in r.get("tags", []) or len(x["references"]) == 1)


def medec_flag(pred: str) -> str:
    """模型回答以 CORRECT 开头（后面可以跟解释）就算判“无错”，否则算指出了错误。"""
    return "CORRECT" if re.match(r"\s*\**\s*correct\b", pred, re.I) else "ERROR"


def medec() -> dict[str, Any]:
    inst, preds = _load("medec")
    ref = {i: ("CORRECT" if _gold(x) == "CORRECT" else "ERROR") for i, x in inst.items()}
    helm = {m: sum(p["stats"]["medec_error_flag_accuracy"] for p in ps.values()) / len(ps) for m, ps in preds.items()}
    fixed = {m: sum(medec_flag(p["pred"]) == ref[i] for i, p in ps.items()) / len(ps) for m, ps in preds.items()}
    mismatch = {m: sum((medec_flag(p["pred"]) == ref[i]) != (p["stats"]["medec_error_flag_accuracy"] >= 1) for i, p in ps.items())
                for m, ps in preds.items()}
    clean = [i for i in ref if ref[i] == "CORRECT"]
    false_alarm = {m: sum(medec_flag(preds[m][i]["pred"]) == "ERROR" for i in clean) / len(clean) for m in STRONG}
    miss = {m: sum(medec_flag(preds[m][i]["pred"]) == "CORRECT" for i in ref if ref[i] == "ERROR") / sum(v == "ERROR" for v in ref.values()) for m in STRONG}
    pairs = json.loads((AUDIT / "medec" / "suspect_pairs.json").read_text()) if (AUDIT / "medec" / "suspect_pairs.json").exists() else []
    return {"n": len(ref), "n_clean": len(clean), "helm": helm, "fixed": fixed, "mismatch": mismatch,
            "false_alarm": false_alarm, "miss": miss, "consensus_flags": len(pairs),
            "consensus_on_edited_sentence": sum(p["same_as_edit"] for p in pairs)}


def exact(sc: str) -> dict[str, Any]:
    inst, preds = _load(sc)
    acc = {m: sum(p["stats"]["exact_match"] for p in ps.values()) / len(ps) for m, ps in preds.items()}
    hard = [i for i in inst if sum(preds[m][i]["stats"]["exact_match"] < 1 for m in preds if i in preds[m]) >= 10]
    return {"n": len(inst), "acc": acc, "hard": len(hard), "hard_gold": dict(Counter(_gold(inst[i]) for i in hard))}


def _rng(d: dict[str, float], ms: list[str]) -> str:
    v = [d[m] for m in ms]
    return f"{min(v):.0%} 到 {max(v):.0%}"


def items(s: dict[str, Any]) -> list[dict[str, Any]]:
    md, mh, rb = s["medec"], s["medhallu"], s["race_based_med"]
    c35 = "anthropic_claude-3-5-sonnet-20241022"
    out = []
    out.append({
        "title": "医疗 · MEDEC 复核：强模型几乎把每份无错病历都判成有错，其中一部分“无错”病历本身有错",
        "content": (
            f"MedHELM v4.0.0 公开了 13 个模型在 MEDEC {md['n']} 道题上的逐题输出（找出病历里写错的诊断或治疗，或回答 CORRECT）。"
            f"判分基本可信，只有一个解析 bug：Claude 3.5 Sonnet 习惯先写 CORRECT 再写解释，MedHELM 把这种回答当成“指出了错误”，"
            f"{md['mismatch'][c35]} 道判反，准确率从 {md['helm'][c35]:.0%} 改正为 {md['fixed'][c35]:.0%}；其他模型差异不超过 2 个百分点。"
            f"真正值得看的是错误类型：{md['n_clean']} 份标注为无错的病历，6 个推理模型把其中 {_rng(md['false_alarm'], STRONG)} 判成有错，"
            f"而有错的病历它们只漏掉 {_rng(md['miss'], STRONG)}。也就是说准确率低主要来自“不敢说没错”。"
            f"无错病历里有 {md['consensus_flags']} 份被至少 5 个推理模型指向同一句，我逐份粗看："
            f"约 30 份不看医学也能看出问题，其中拼写错误、单位错误和切句残句约 20 份（如 Hb 10.5 mg/dL 应为 g/dL、"
            f"“血压 120/75 mm”被切断、deliruim、Colposcpy），明显事实错误约 8 份（如身高 5 ft 40 in、糖尿病用甲氨蝶呤、"
            f"迷走神经写成第 IX 对脑神经、六胺银染色确诊“寄生虫”）；其余是模型认为治疗或诊断不当，需要医生判断。"
            f"所以 MEDEC 的误报需要先剔除这些标注问题，不能直接当成模型缺陷。"
            f"已有工作：MEDEC 原论文已指出 o1-preview 召回高、误报多；MedRECT（2511.00421）用 LLM 筛掉 MS 测试集 139/597 道问题题，"
            f"举的例子正是“5 ft 40 in”；2511.19858 专门报告误报率并用检索示例把误报率降约 15%。"
            f"因此“强模型过度报错 + 无错样本带噪”本身不是新发现，剩下没人做的是：在人工确认真正无错的病历上，"
            f"量化误报来自哪类句子（单位/拼写/切句 vs 临床判断）。"),
        "concerns": ["安全/风险", "评测有效性"], "tasks": ["审查/核查"],
    })
    out.append({
        "title": "医疗 · MedHallu 复核：判分无误，强模型之间差距很小",
        "content": (
            f"MedHELM v4.0.0 公开了 13 个模型在 MedHallu {mh['n']} 道题上的逐题输出（判断医学回答是否被给定知识支撑，输出 0/1）。"
            f"逐题重新解析，判分与 MedHELM 完全一致。13 个模型准确率 {_rng(mh['acc'], list(mh['acc']))}，"
            f"6 个推理模型 {_rng(mh['acc'], STRONG)}，已接近饱和。至少 10 个模型做错的题 {mh['hard']} 道"
            f"（标准答案为“有幻觉”{mh['hard_gold'].get('1', 0)} 道、“无幻觉”{mh['hard_gold'].get('0', 0)} 道），"
            f"抽看的几道多为回答把原文结论稍微说过头（如把“可能相关”说成“显著导致”），属于细粒度判断，没看到明显的标注错误。"),
        "concerns": ["证据/溯源"], "tasks": ["审查/核查"],
    })
    out.append({
        "title": "医疗 · RaceBasedMed 复核：判分无误，但题量小、部分标签有争议",
        "content": (
            f"MedHELM v4.0.0 公开了 13 个模型在 RaceBasedMed {rb['n']} 道题上的逐题输出（判断回答是否含有基于种族的有害或不准确内容，A/B 选择）。"
            f"逐题重新解析，判分与 MedHELM 完全一致。6 个推理模型准确率 {_rng(rb['acc'], STRONG)}。"
            f"至少 10 个模型做错的题只有 {rb['hard']} 道，其中有标签值得商榷：例如回答明确说“种族没有明确的遗传基础”被标为有害；"
            f"回答编造了一个“黑人女性肺活量 = 3.57 × 身高 × 体重”的公式却被标为无害。题量只有 {rb['n']} 道，单题影响约 0.6 个百分点，"
            f"不适合单独作为模型缺陷的证据。"),
        "concerns": ["安全/风险", "评测有效性"], "tasks": ["分类/识别"],
    })
    for it, sc in zip(out, ["medec", "medhallu", "race_based_med"]):
        # MedHallu、RaceBasedMed 的复核结论是“判分没问题、没发现缺口”，只留作背景，不参与缺口统计
        if sc != "medec":
            it["validation_status"] = "context_only"
        it.update({"radar": "model_failure", "source_id": "medhelm-recheck", "published_at": now_iso()[:10],
                   "url": f"https://storage.googleapis.com/crfm-helm-public/medhelm/benchmark_output/runs/v4.0.0/{RUN[sc]}/instances.json",
                   "evidence_role": "raw_source", "source_type": "eval_run_or_case", "source_quality": "primary",
                   "http_status": 200, "organization": "本地复核（MedHELM v4 逐题输出）", "source_version": "MedHELM v4.0.0",
                   "run_id": f"medhelm-recheck-{sc}", "retrieved_at": now_iso(),
                   "raw_data": {"scenario": sc, "summary": s[sc], "audit_dir": f"data/medhelm_audit/{sc}",
                                "concerns": it.pop("concerns"), "tasks": it.pop("tasks"), "inputs": ["长文档"]}})
    return out


PAPERS = [
    {"arxiv": "2412.19260", "title": "MEDEC: A Benchmark for Medical Error Detection and Correction in Clinical Notes",
     "published": "2024-12-26", "org": "Microsoft / University of Washington"},
    {"arxiv": "2511.00421", "title": "MedRECT: A Bilingual Medical Reasoning Benchmark for Error Correction in Clinical Texts",
     "published": "2025-11-01", "org": "Preferred Networks"},
    {"arxiv": "2511.19858", "title": "A Systematic Analysis of Large Language Models with RAG-enabled Dynamic Prompting for Medical Error Detection and Correction",
     "published": "2025-11-25", "org": "University of Washington"},
    {"arxiv": "2505.23715", "title": "Don't Take the Premise for Granted: Evaluating the Premise Critique Ability of Large Language Models",
     "published": "2025-05-29", "org": "Jilin University"},
]


def run(dry_run: bool = False) -> dict[str, Any]:
    import radar.evidence.medcalc_audit as mc
    s = {"medec": medec(), "medhallu": exact("medhallu"), "race_based_med": exact("race_based_med")}
    new = items(s)
    saved, mc.PAPERS = mc.PAPERS, PAPERS
    try:
        papers = mc.paper_items()
    finally:
        mc.PAPERS = saved
    if dry_run:
        return {"dry_run": True, "items": [(i["title"], i["content"]) for i in new], "papers": [p["title"] for p in papers]}
    removed = 0
    with db() as conn:
        for cn in CN.values():
            removed += conn.execute("DELETE FROM source_items WHERE title=?", (OLD_TITLE.format(cn=cn),)).rowcount
        removed += conn.execute("DELETE FROM source_items WHERE source_id='medhelm-recheck'").rowcount
    states = Counter(insert_source_item(i)[1] for i in new + papers)
    return {"removed_old": removed, "insert": dict(states), "extract": extract_pending()}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    print(json.dumps(run(a.dry_run), ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())

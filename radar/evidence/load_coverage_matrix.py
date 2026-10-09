from __future__ import annotations

import json

from radar.evidence.evidence_import import verify_result
from radar.core.radar_core import canonicalize_url, coverage_matrix, db, extract_pending, generate_ideas, init_db, insert_source_item, now_iso, upsert_coverage_entry

IDEA_ID = 18

SOURCES = [
    {
        "benchmark_name": "CMB",
        "title": "CMB: A Comprehensive Medical Benchmark in Chinese",
        "url": "https://github.com/FreedomIntelligence/CMB",
        "organization": "FreedomIntelligence",
        "source_type": "official_github",
        "task_definition": "CMB-Exam医学考试问答；CMB-Clin复杂中文临床病例分析。",
        "dataset_description": "CMB-Exam含6大类、28子类；CMB-Clin含74个复杂临床病例。",
        "input_format": "考试题干与选项，或病例描述+临床问题。",
        "output_format": "选择题答案，或自由文本临床回答。",
        "evaluation_protocol": "Exam按标准选项匹配；Clin由GPT-4按流畅性、相关性、完整性、医学专业性1–5分评审。",
        "metrics": ["choice accuracy-like score", "fluency", "relevance", "completeness", "medical proficiency"],
        "capabilities": ["medical knowledge", "clinical case reasoning", "diagnosis", "treatment planning"],
        "target_coverage": "not_covered",
        "evidence_locator": {"file": "README.md", "section": "CMB-Exam / CMB-Clin / Evaluation"},
        "verification_status": "verified",
        "notes": "未提供临床指南语料库、指南检索指标、结构化引用字段或citation correctness。"
    },
    {
        "benchmark_name": "MedQA",
        "title": "MedQA: Code and data for Medical Question Answering",
        "url": "https://github.com/jind11/MedQA",
        "organization": "MedQA authors",
        "source_type": "official_github",
        "task_definition": "美国、中国大陆及台湾医学考试多项选择问答；包含基于医学教材的BM25/PMI检索基线。",
        "dataset_description": "医学考试QA及英文/简体中文医学教材语料，含官方train/dev/test划分。",
        "input_format": "题干+候选答案；检索基线将问题与候选答案拼接查询教材。",
        "output_format": "答案选项及候选匹配分数。",
        "evaluation_protocol": "官方随机划分；检索教材后对候选答案排序。README未完整披露聚合公式。",
        "metrics": ["answer accuracy (inferred from answer matching)", "BM25 candidate ranking"],
        "capabilities": ["medical exam QA", "textbook retrieval", "answer selection"],
        "target_coverage": "not_covered",
        "evidence_locator": {"file": "README.md", "section": "Data / Information Retrieval Baseline"},
        "verification_status": "verified",
        "notes": "检索语料为教材而非临床指南；无指南版本、条款定位、citation correctness或claim-evidence entailment。"
    },
    {
        "benchmark_name": "CliMedBench",
        "title": "CliMedBench: A Large-Scale Chinese Benchmark for Evaluating Medical Large Language Models in Clinical Scenarios",
        "url": "https://aclanthology.org/2024.emnlp-main.480/",
        "organization": "ACL Anthology",
        "source_type": "paper",
        "task_definition": "14个专家指导的核心临床场景，按7个维度评估医疗LLM。",
        "dataset_description": "33,735个问题，来自三甲医院真实医疗报告和考试练习题。",
        "input_format": "临床问题、医疗报告相关问题或考试题；摘要未披露完整模板。",
        "output_format": "回答生成或选择；摘要未披露引用字段。",
        "evaluation_protocol": "摘要称以多种方式验证可靠性，但未披露完整Prompt、生成参数及统计流程。",
        "metrics": ["not disclosed on landing page"],
        "capabilities": ["clinical knowledge", "medical reasoning", "factual consistency", "diagnostic accuracy"],
        "target_coverage": "unknown",
        "evidence_locator": {"section": "Abstract", "pages": "8428–8438", "doi": "10.18653/v1/2024.emnlp-main.480"},
        "verification_status": "partial",
        "notes": "摘要未显示指南检索、引用真实性、引用支持度指标；需核查全文协议后才能确认Negative Claim。"
    },
    {
        "benchmark_name": "LLMEval-Med",
        "title": "LLMEval-Med: A Real-world Clinical Benchmark for Medical LLMs with Physician Validation",
        "url": "https://github.com/llmeval/LLMEval-Med",
        "organization": "LLMEval-Med authors",
        "source_type": "official_github",
        "task_definition": "真实EHR/专家临床场景的开放式问答，覆盖知识、理解、推理、安全、文本生成。",
        "dataset_description": "完整2996题；公开仓库dataset.json含667题，含参考答案与医生checklist。",
        "input_format": "问题、临床场景和可选多轮历史。",
        "output_format": "自由文本医学回答；不要求输出指南名称、版本或证据引用。",
        "evaluation_protocol": "模型生成回答；GPT-4类Judge结合专家答案与checklist三次评分并聚合。",
        "metrics": ["1–5 score", "Usability Rate", "Overall Performance"],
        "capabilities": ["medical knowledge", "medical reasoning", "medical safety", "text generation"],
        "target_coverage": "not_covered",
        "evidence_locator": {"file": "README.md", "section": "Dataset / Answer / Evaluate / Aggregate", "doi": "10.18653/v1/2025.findings-emnlp.263"},
        "verification_status": "verified",
        "notes": "无指南库、检索金标准、引用字段、Citation Precision/Recall或Claim-Evidence Entailment。"
    },
    {
        "benchmark_name": "MedBench",
        "title": "MedBench",
        "url": "https://medbench.opencompass.org.cn/docs",
        "organization": "OpenCompass",
        "source_type": "official_documentation",
        "task_definition": "公开介绍为中文医疗大模型综合评测，覆盖知识问答、语言理解、推理生成及安全伦理。",
        "dataset_description": "动态文档页面未能可靠提取完整任务表与数据规模。",
        "input_format": "未知，待核查动态文档或论文。",
        "output_format": "未知，待核查动态文档或论文。",
        "evaluation_protocol": "未知，当前抓取仅得到前端SPA壳。",
        "metrics": ["unknown"],
        "capabilities": ["medical QA", "language understanding", "reasoning", "safety"],
        "target_coverage": "unknown",
        "evidence_locator": {"url": "https://medbench.opencompass.org.cn/docs", "section": "dynamic SPA; content not extracted"},
        "verification_status": "needs_review",
        "notes": "不能因页面未显示而判定不覆盖指南检索/引用；必须进一步核查论文、代码或动态正文。"
    }
]


def find_or_create_source(entry):
    verified = verify_result({
        "title": entry["title"], "url": entry["url"], "content": entry["task_definition"],
        "radar": "benchmark", "source_id": "coverage-matrix", "source_type": entry["source_type"],
        "source_quality": "primary", "organization": entry["organization"], "selected": True,
        "locator": entry["evidence_locator"],
    })
    source_id, _ = insert_source_item({
        "radar": "benchmark", "source_id": "coverage-matrix", "title": verified["title"],
        "content": verified.get("content") or entry["task_definition"], "url": entry["url"],
        "published_at": verified.get("published_at"), "source_type": entry["source_type"],
        "source_quality": "primary", "organization": entry["organization"],
        "authors": verified.get("authors"), "source_version": verified.get("source_version"),
        "locator": {**entry["evidence_locator"], **(verified.get("locator") or {})},
        "retrieved_at": verified.get("retrieved_at"), "last_verified_at": verified.get("last_verified_at"),
        "http_status": verified.get("http_status"), "validation_status": verified.get("validation_status"),
        "provenance": {"coverage_matrix_idea_id": IDEA_ID},
    })
    with db() as conn:
        if source_id is None:
            row = conn.execute("SELECT id FROM source_items WHERE canonical_url=? OR url=? ORDER BY id LIMIT 1", (canonicalize_url(entry["url"]), entry["url"])).fetchone()
            source_id = row["id"] if row else None
        if source_id:
            conn.execute(
                """UPDATE source_items SET published_at=COALESCE(?,published_at),retrieved_at=?,last_verified_at=COALESCE(?,last_verified_at),
                   source_version=COALESCE(?,source_version),locator_json=?,validation_status=? WHERE id=?""",
                (verified.get("published_at"), verified.get("retrieved_at") or now_iso(), verified.get("last_verified_at"),
                 verified.get("source_version"), json.dumps({**entry["evidence_locator"], **(verified.get("locator") or {})}, ensure_ascii=False),
                 verified.get("validation_status", "unverified"), source_id),
            )
    return source_id


def main():
    init_db()
    ids = []
    for entry in SOURCES:
        source_id = find_or_create_source(entry)
        payload = dict(entry)
        payload["source_item_id"] = source_id
        payload["verified_at"] = now_iso()
        ids.append(upsert_coverage_entry(IDEA_ID, payload))
    extract_pending()
    generate_ideas()
    with db() as conn:
        for source_id in [x["source_item_id"] for x in coverage_matrix(IDEA_ID) if x.get("source_item_id")]:
            signal = conn.execute("SELECT id FROM signals WHERE source_item_id=?", (source_id,)).fetchone()
            if signal:
                conn.execute("INSERT OR IGNORE INTO idea_signal_links(idea_id,signal_id) VALUES(?,?)", (IDEA_ID, signal["id"]))
    print(json.dumps({"idea_id": IDEA_ID, "entries": len(ids), "coverage_ids": ids}, ensure_ascii=False))


if __name__ == "__main__":
    main()

from __future__ import annotations

import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
SRC = BASE / "data" / "mini_eval_sources"
OUT = BASE / "data" / "mini_eval_cases"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows):
    path.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in rows) + "\n", encoding="utf-8")


def build_medical():
    path = SRC / "cmb" / "CMB-Clin-qa.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for case in data[:10]:
        qa = case["QA_pairs"][0]
        rows.append({
            "case_id": f"CMB-CLIN-{case['id']}-Q1",
            "idea_id": 18,
            "idea_name": "临床推理与指南溯源",
            "sub_capability": "clinical_reasoning",
            "benchmark_name": "CMB-Clin",
            "task_prompt": qa["question"],
            "input": case["description"],
            "reference_answer": qa.get("answer") or qa.get("solution"),
            "rubric": {
                "grading": "reference_answer_checklist",
                "dimensions": ["diagnosis_correctness", "reasoning_completeness", "medical_proficiency", "safety"],
                "status": "derived_from_official_reference_pending_expert_review"
            },
            "source": {
                "repository": "https://github.com/FreedomIntelligence/CMB",
                "file": "data/CMB-Clin/CMB-Clin-qa.json",
                "source_record_id": case["id"],
                "source_file_sha256": sha256(path),
                "license": "Apache-2.0"
            }
        })
    return rows


def build_finance():
    qpath = SRC / "financebench" / "financebench_open_source.jsonl"
    dpath = SRC / "financebench" / "financebench_document_information.jsonl"
    questions = read_jsonl(qpath)
    docs = {x["doc_name"]: x for x in read_jsonl(dpath)}
    chosen, seen_docs = [], set()
    for item in questions:
        if item["doc_name"] in seen_docs:
            continue
        seen_docs.add(item["doc_name"])
        ev = item.get("evidence") or []
        chosen.append({
            "case_id": item["financebench_id"],
            "idea_id": 1,
            "idea_name": "PDF财报异常识别与证据引用",
            "sub_capability": item.get("question_reasoning") or "financial_document_reasoning",
            "benchmark_name": "FinanceBench",
            "task_prompt": item["question"],
            "input": "\n\n".join(f"[Document {x.get('evidence_doc_name') or x.get('doc_name') or item['doc_name']}, Page {int(x.get('evidence_page_num', 0)) + 1}]\n{x.get('evidence_text_full_page') or x.get('evidence_text') or ''}" for x in ev),
            "reference_answer": item["answer"],
            "rubric": {
                "grading": "exact_answer_plus_evidence",
                "answer": item["answer"],
                "justification": item.get("justification"),
                "required_evidence": [{"doc_name": x.get("evidence_doc_name") or x.get("doc_name") or item["doc_name"], "page_num_zero_based": x.get("evidence_page_num"), "text": x.get("evidence_text")} for x in ev],
                "status": "official_annotation"
            },
            "source": {
                "repository": "https://github.com/patronus-ai/financebench",
                "data_url": "https://raw.githubusercontent.com/patronus-ai/financebench/main/data/financebench_open_source.jsonl",
                "document_url": docs.get(item["doc_name"], {}).get("doc_link"),
                "source_record_id": item["financebench_id"],
                "source_file_sha256": sha256(qpath),
                "license_status": "repository page does not state a clear license; confirm before redistribution"
            }
        })
        if len(chosen) == 10:
            break
    return chosen


def build_bfcl():
    qpath = SRC / "bfcl" / "BFCL_v3_simple.json"
    apath = SRC / "bfcl" / "BFCL_v3_simple_answers.json"
    questions = {x["id"]: x for x in read_jsonl(qpath)}
    answers = read_jsonl(apath)
    rows = []
    for answer in answers[:10]:
        item = questions[answer["id"]]
        rows.append({
            "case_id": f"BFCL-{answer['id']}",
            "idea_id": 11,
            "idea_name": "General Tool Use能力评测",
            "sub_capability": "single_turn_function_calling",
            "benchmark_name": "BFCL v3",
            "task_prompt": item["question"][0][0]["content"],
            "input": {"messages": item["question"][0], "functions": item["function"]},
            "reference_answer": answer["ground_truth"],
            "rubric": {
                "grading": "ast_function_call_match",
                "requirements": ["correct_function_name", "required_arguments_present", "argument_values_match", "valid_structure"],
                "status": "official_ground_truth"
            },
            "source": {
                "dataset": "https://huggingface.co/datasets/gorilla-llm/Berkeley-Function-Calling-Leaderboard",
                "repository": "https://github.com/ShishirPatil/gorilla/tree/main/berkeley-function-call-leaderboard",
                "dataset_revision": "61fc0608cfd831fcfbbaa676ebdfef0ed963eeda",
                "source_record_id": answer["id"],
                "question_file_sha256": sha256(qpath),
                "answer_file_sha256": sha256(apath),
                "license": "Apache-2.0"
            }
        })
    return rows


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    packs = {
        "idea-18-cmb-clin.jsonl": build_medical(),
        "idea-1-financebench.jsonl": build_finance(),
        "idea-11-bfcl.jsonl": build_bfcl(),
    }
    for name, rows in packs.items():
        write_jsonl(OUT / name, rows)

    # 保留已有 manifest 中记录执行进展的字段：重新生成 Case 包不代表离线执行
    # 状态回退。之前这里无条件写 execution_status="pending_model_credentials"，
    # 会抹掉 offline_package / human_workbench / expected_offline_results 和
    # 真实的执行进展。
    manifest_path = OUT / "manifest.json"
    preserved = {}
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        preserved = {
            key: existing[key]
            for key in ["execution_status", "offline_package", "human_workbench", "expected_offline_results"]
            if key in existing
        }

    manifest = {
        "created_at": "2026-09-15",
        "total_cases": sum(len(x) for x in packs.values()),
        "case_packs": [
            {"file": name, "count": len(rows), "idea_id": rows[0]["idea_id"], "benchmark": rows[0]["benchmark_name"]}
            for name, rows in packs.items()
        ],
        "integrity": "All cases retain source record IDs and source-file SHA256. No synthetic cases included.",
        "execution_status": "pending_model_credentials",
        **preserved,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

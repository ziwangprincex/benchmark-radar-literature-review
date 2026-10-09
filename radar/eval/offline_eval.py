from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from radar.eval.mini_eval_runner import objective_grade, prompt_for
from radar.eval.offline_workbench import render_workbench
from radar.core.radar_core import BASE_DIR, add_mini_eval, db

CASE_DIR = BASE_DIR / "data" / "mini_eval_cases"
PACKAGE_ROOT = BASE_DIR / "data" / "offline_eval_packages"
RUN_ROOT = BASE_DIR / "data" / "mini_eval_runs"
PACKS = {
    "financebench": CASE_DIR / "idea-1-financebench.jsonl",
    "bfcl": CASE_DIR / "idea-11-bfcl.jsonl",
}
PLACEHOLDER_MODELS = ["REPLACE_MODEL_1", "REPLACE_MODEL_2", "REPLACE_MODEL_3"]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def task_id(case: dict[str, Any]) -> str:
    return f"{case['benchmark_name']}::{case['case_id']}"


def manual_instructions(package_id: str) -> str:
    return f"""Offline Mini Eval 人工执行包：{package_id}

最快使用方式
1. 双击「打开人工执行台.bat」。
2. 在模型 Slot 1 填写 Provider、精确 Model Name 和 Model Version。
3. 逐题点击“复制完整 Prompt”，到外部模型产品中执行，再把回答原样粘回。
4. 每题点击“保存并下一题”。工作台会自动记录时间并保存在浏览器本地。
5. 20题全部完成后，点击“导出当前模型 JSONL”。
6. 对另外两个真实模型重复以上步骤。
7. 将三个 model-slot-*.jsonl 放回本目录，双击「合并并校验结果.bat」。
8. 校验通过后得到 completed_responses.jsonl 和 validation_report.json。

执行范围
- FinanceBench 10题：Idea #1，PDF财报分析与证据引用。
- BFCL v3 10题：Idea #11，单轮函数调用。
- 每题由3个不同的真实模型执行，共60条结果。
- CMB-Clin 暂不执行，等待医生校准Rubric。

人工执行纪律
- 每个模型使用独立Slot；填写官方界面显示的精确版本，不使用“GPT/Claude”等泛称。
- 建议每题开启新会话，不带入前题上下文；关闭非必要联网、记忆和个性化。
- 不向模型提供Reference Answer、Rubric或私有答案文件。
- 模型输出必须原样保存，不得根据参考答案人工修正。
- BFCL输出整理为JSON数组仅允许做格式转写，不得更改函数名或参数语义；任何整理必须写入操作员备注。
- FinanceBench回答必须包含答案及明确的[Document ..., Page N]引用。
- 若外部产品不能导出Provider Raw JSON，可将Raw Response留空；工作台会明确记录manual_external_ui和verbatim_response，不冒充API原始响应。
- 建议每完成5题导出一次“工作台备份 JSON”，防止浏览器数据丢失。

文件说明
- workbench.html：无需安装、无需API的人工执行台。
- tasks/：只含任务与来源，不含答案。
- responses_template.jsonl：高级用户可直接填写的60行模板。
- response_schema.json：结果字段与约束。
- completed_responses.jsonl：三个模型合并后的正式待评分文件。
- validation_report.json：合并与完整性检查结果。

命令行备用方式
python offline_eval.py combine --package-dir data/offline_eval_packages/{package_id} --input-dir data/offline_eval_packages/{package_id} --output data/offline_eval_packages/{package_id}/completed_responses.jsonl
python offline_eval.py import --package-dir data/offline_eval_packages/{package_id} --responses data/offline_eval_packages/{package_id}/completed_responses.jsonl

正式回流前必须先人工审阅Dry-run评分结果；确认后才可加 --ingest。企业微信推送当前保持暂停。
"""


def export_package(package_id: str) -> dict[str, Any]:
    package_dir = PACKAGE_ROOT / package_id
    if package_dir.exists():
        raise FileExistsError(f"package already exists: {package_dir}")
    tasks_dir = package_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    manifest_packs = []
    all_task_ids = []
    all_tasks = []
    for pack_name, case_path in PACKS.items():
        cases = load_jsonl(case_path)
        tasks = []
        for case in cases:
            tid = task_id(case)
            all_task_ids.append(tid)
            tools = case.get("input", {}).get("functions") if case["benchmark_name"] == "BFCL v3" else None
            tasks.append({
                "package_id": package_id,
                "task_id": tid,
                "idea_id": case["idea_id"],
                "idea_name": case["idea_name"],
                "benchmark_name": case["benchmark_name"],
                "messages": [{"role": "user", "content": prompt_for(case)}],
                "tools": tools or [],
                "temperature": 0,
                "response_contract": (
                    "Return a JSON array of objects with fields name and arguments; no explanation."
                    if case["benchmark_name"] == "BFCL v3"
                    else "Return the answer and explicit [Document ..., Page N] citation from the supplied excerpt."
                ),
                "source_provenance": case["source"],
            })
        task_path = tasks_dir / f"{pack_name}_tasks.jsonl"
        write_jsonl(task_path, tasks)
        all_tasks.extend(tasks)
        manifest_packs.append({
            "pack": pack_name,
            "idea_id": cases[0]["idea_id"],
            "benchmark_name": cases[0]["benchmark_name"],
            "task_count": len(tasks),
            "task_file": str(task_path.relative_to(package_dir)),
            "task_file_sha256": file_hash(task_path),
            "private_answer_key": str(case_path.relative_to(BASE_DIR)),
            "private_answer_key_sha256": file_hash(case_path),
        })
    template = []
    for model in PLACEHOLDER_MODELS:
        for tid in all_task_ids:
            template.append({
                "package_id": package_id,
                "task_id": tid,
                "model_name": model,
                "model_version": "REPLACE_EXACT_MODEL_VERSION",
                "provider": "REPLACE_PROVIDER",
                "started_at": "REPLACE_ISO_8601",
                "completed_at": "REPLACE_ISO_8601",
                "latency_seconds": None,
                "response_text": "",
                "raw_response": {},
                "request_metadata": {"temperature": 0, "request_id": "REPLACE_IF_AVAILABLE"},
            })
    response_path = package_dir / "responses_template.jsonl"
    write_jsonl(response_path, template)
    schema = {
        "required_fields": [
            "package_id", "task_id", "model_name", "model_version", "provider", "started_at",
            "completed_at", "latency_seconds", "response_text", "raw_response", "request_metadata"
        ],
        "constraints": {
            "models": "exactly 3 distinct real models; placeholders forbidden",
            "coverage": "each model must answer every exported task exactly once",
            "raw_response": "provider/local raw output when available; otherwise a transparent manual_external_ui record whose verbatim_response exactly matches response_text",
            "bfcl_response_text": "canonical JSON array [{name, arguments}]",
            "finance_response_text": "answer plus explicit document/page citation",
        },
    }
    (package_dir / "response_schema.json").write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
    (package_dir / "workbench.html").write_text(render_workbench(package_id, all_tasks), encoding="utf-8")
    (package_dir / "INSTRUCTIONS.txt").write_text(manual_instructions(package_id), encoding="utf-8")
    (package_dir / "打开人工执行台.bat").write_text('@echo off\r\nstart "" "%~dp0workbench.html"\r\n', encoding="utf-8")
    (package_dir / "合并并校验结果.bat").write_text(
        '@echo off\r\nset "PY=C:\\Users\\vegavjzhang\\AppData\\Local\\Python\\bin\\python3.exe"\r\n'
        '"%PY%" "%~dp0..\\..\\..\\offline_eval.py" combine --package-dir "%~dp0" --input-dir "%~dp0" --output "%~dp0completed_responses.jsonl"\r\n'
        'pause\r\n', encoding="utf-8"
    )
    manifest = {
        "package_id": package_id,
        "created_at": now_iso(),
        "mode": "offline_result_import",
        "execution_scope": "FinanceBench + BFCL only; CMB-Clin deferred pending physician rubric calibration",
        "required_distinct_models": 3,
        "total_tasks": len(all_task_ids),
        "expected_response_records": len(all_task_ids) * 3,
        "packs": manifest_packs,
        "response_template": response_path.name,
        "response_template_sha256": file_hash(response_path),
        "human_workbench": "workbench.html",
        "per_model_export_pattern": "model-slot-*.jsonl",
        "combined_output": "completed_responses.jsonl",
        "status": "awaiting_external_model_results",
        "integrity_statement": "Task prompts come from official benchmark data. Answer keys are not included in exported task files. No synthetic model response is allowed.",
    }
    manifest_path = package_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    zip_path = PACKAGE_ROOT / f"{package_id}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in package_dir.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(package_dir.parent))
    return {"package_dir": str(package_dir), "zip": str(zip_path), **manifest}


def validate_timestamp(value: str, field: str) -> None:
    if not value or value.startswith("REPLACE"):
        raise ValueError(f"{field} must be a real ISO-8601 timestamp")
    datetime.fromisoformat(value.replace("Z", "+00:00"))


def package_context(package_dir: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]], list[str]]:
    manifest = json.loads((package_dir / "manifest.json").read_text(encoding="utf-8"))
    task_map = {}
    integrity_errors = []
    for pack in manifest["packs"]:
        task_path = package_dir / pack["task_file"]
        if not task_path.exists():
            integrity_errors.append(f"任务文件不存在：{task_path}")
            continue
        if file_hash(task_path) != pack["task_file_sha256"]:
            integrity_errors.append(f"任务文件哈希不匹配：{task_path.name}")
        task_map.update({row["task_id"]: row for row in load_jsonl(task_path)})
    return manifest, task_map, integrity_errors


def audit_responses(package_dir: Path, responses: list[dict[str, Any]], require_three_models: bool = True) -> dict[str, Any]:
    manifest, task_map, errors = package_context(package_dir)
    required = json.loads((package_dir / "response_schema.json").read_text(encoding="utf-8"))["required_fields"]
    warnings, seen, coverage, models = [], set(), defaultdict(set), set()
    for index, row in enumerate(responses, 1):
        label = f"第{index}行"
        missing_fields = [field for field in required if field not in row]
        if missing_fields:
            errors.append(f"{label}缺少字段：{', '.join(missing_fields)}")
            continue
        task = task_map.get(row["task_id"])
        if row["package_id"] != manifest["package_id"]:
            errors.append(f"{label} package_id错误：{row['package_id']}")
        if not task:
            errors.append(f"{label}未知task_id：{row['task_id']}")
        if any(str(row[field]).startswith("REPLACE") for field in ["provider", "model_name", "model_version"]):
            errors.append(f"{label}仍包含模型占位信息")
        response_text = str(row["response_text"] or "").strip()
        if not response_text:
            errors.append(f"{label}响应为空：{row['task_id']}")
        raw = row["raw_response"]
        if raw in ({}, [], "", None):
            errors.append(f"{label}缺少Raw Response：{row['task_id']}")
        elif isinstance(raw, dict) and raw.get("capture_mode") == "manual_external_ui":
            if raw.get("verbatim_response") != response_text:
                errors.append(f"{label}人工捕获的verbatim_response与response_text不一致")
            if not raw.get("provider_raw_unavailable"):
                warnings.append(f"{label}人工捕获未明确provider_raw_unavailable")
        for field in ["started_at", "completed_at"]:
            try:
                validate_timestamp(row[field], field)
            except (TypeError, ValueError):
                errors.append(f"{label} {field}不是有效ISO-8601时间")
        key = (row["task_id"], row["provider"], row["model_name"], row["model_version"])
        if key in seen:
            errors.append(f"重复响应：{key}")
        seen.add(key)
        model_key = f"{row['provider']}::{row['model_name']}::{row['model_version']}"
        models.add(model_key)
        coverage[model_key].add(row["task_id"])
        if task and response_text:
            if task["benchmark_name"] == "BFCL v3":
                try:
                    value = json.loads(response_text)
                    if not isinstance(value, list) or not value or not all(isinstance(x, dict) and x.get("name") and isinstance(x.get("arguments"), dict) for x in value):
                        raise ValueError
                except (TypeError, ValueError, json.JSONDecodeError):
                    errors.append(f"{label} BFCL响应不是规范的[name, arguments] JSON数组：{row['task_id']}")
            elif task["benchmark_name"] == "FinanceBench" and not re.search(r"\[Document .+?, Page \d+\]", response_text, re.I):
                errors.append(f"{label} FinanceBench响应缺少明确[Document ..., Page N]引用：{row['task_id']}")
    expected = set(task_map)
    for model, completed in coverage.items():
        missing_tasks, extra_tasks = expected - completed, completed - expected
        if missing_tasks:
            errors.append(f"模型 {model} 缺少 {len(missing_tasks)} 题：{', '.join(sorted(missing_tasks))}")
        if extra_tasks:
            errors.append(f"模型 {model} 包含未知任务：{', '.join(sorted(extra_tasks))}")
    expected_model_count = manifest["required_distinct_models"] if require_three_models else 1
    if len(models) != expected_model_count:
        errors.append(f"需要{expected_model_count}个不同的真实模型，实际为{len(models)}个")
    expected_records = len(expected) * expected_model_count
    if len(responses) != expected_records:
        errors.append(f"需要{expected_records}条响应，实际为{len(responses)}条")
    return {
        "ok": not errors, "package_id": manifest["package_id"], "records": len(responses),
        "expected_records": expected_records, "tasks": len(task_map), "models": sorted(models),
        "model_progress": {model: {"completed": len(done), "expected": len(expected)} for model, done in coverage.items()},
        "errors": errors, "warnings": warnings,
    }


def error_summary(title: str, errors: list[str], limit: int = 25) -> str:
    visible = errors[:limit]
    remaining = len(errors) - len(visible)
    suffix = f"\n- ……另有{remaining}项，请修复后重新校验" if remaining else ""
    return title + "：\n- " + "\n- ".join(visible) + suffix


def validate_responses(package_dir: Path, response_file: Path) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    responses = load_jsonl(response_file)
    report = audit_responses(package_dir, responses, require_three_models=True)
    if not report["ok"]:
        raise ValueError(error_summary("离线结果校验失败", report["errors"]))
    manifest, task_map, _ = package_context(package_dir)
    return manifest, responses, task_map


def combine_results(package_dir: Path, input_dir: Path, output: Path) -> dict[str, Any]:
    files = sorted(input_dir.glob("model-slot-*.jsonl"))
    if len(files) != 3:
        raise ValueError(f"需要3个model-slot-*.jsonl文件，实际找到{len(files)}个：{[x.name for x in files]}")
    combined, file_reports = [], []
    for path in files:
        rows = load_jsonl(path)
        report = audit_responses(package_dir, rows, require_three_models=False)
        file_reports.append({"file": path.name, **report})
        if not report["ok"]:
            raise ValueError(error_summary(f"{path.name}校验失败", report["errors"]))
        combined.extend(rows)
    report = audit_responses(package_dir, combined, require_three_models=True)
    if not report["ok"]:
        raise ValueError(error_summary("三模型合并校验失败", report["errors"]))
    output.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(output, combined)
    receipt = {"ok": True, "output": str(output), "output_sha256": file_hash(output), "files": file_reports, **report}
    (output.parent / "validation_report.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    return receipt


def severity_for(failure_type: str | None) -> str:
    return {
        "wrong_function": "high", "financial_answer_error": "high",
        "wrong_arguments": "medium", "citation_error": "medium",
    }.get(failure_type or "", "low")


def import_results(package_dir: Path, response_file: Path, ingest: bool) -> dict[str, Any]:
    manifest, responses, _ = validate_responses(package_dir, response_file)
    answer_keys = {}
    for pack in manifest["packs"]:
        key_path = BASE_DIR / pack["private_answer_key"]
        if file_hash(key_path) != pack["private_answer_key_sha256"]:
            raise ValueError(f"private answer key checksum mismatch: {key_path}")
        answer_keys.update({task_id(row): row for row in load_jsonl(key_path)})
    run_parent = RUN_ROOT / manifest["package_id"]
    run_parent.mkdir(parents=True, exist_ok=True)
    copied_response = run_parent / "offline_responses.jsonl"
    shutil.copy2(response_file, copied_response)
    by_benchmark = defaultdict(list)
    for row in responses:
        case = answer_keys[row["task_id"]]
        grade = objective_grade(case, row["response_text"])
        if grade is None:
            raise ValueError(f"no objective grader for {case['benchmark_name']}")
        failure_type = grade.get("failure_type") or "none"
        result = {
            "failure_case_id": f"{case['case_id']}::{row['model_name']}::{row['model_version']}",
            "case_id": case["case_id"],
            "benchmark_name": case["benchmark_name"],
            "task_prompt": case["task_prompt"],
            "input": case["input"],
            "reference_answer": case["reference_answer"],
            "rubric": json.dumps(case["rubric"], ensure_ascii=False),
            "model_name": row["model_name"],
            "model_version": row["model_version"],
            "model_response": row["response_text"],
            "score": float(grade["score"]),
            "passed": bool(grade["passed"]),
            "failure_type": failure_type,
            "severity": severity_for(failure_type),
            "error_analysis": "Objective deterministic grader: " + failure_type,
            "judge_result": grade["judge_result"],
            "run_date": row["completed_at"],
            "attachments": [
                {"name": "Offline raw response package", "path": str(copied_response.relative_to(BASE_DIR))},
                {"name": "Original benchmark source", "url": case["source"].get("data_url") or case["source"].get("dataset") or case["source"].get("repository")},
            ],
            "raw_data": {
                "package_id": manifest["package_id"], "provider": row["provider"],
                "started_at": row["started_at"], "completed_at": row["completed_at"],
                "latency_seconds": row["latency_seconds"], "request_metadata": row["request_metadata"],
                "raw_response": row["raw_response"], "source": case["source"],
            },
        }
        by_benchmark[case["benchmark_name"]].append((case, result))
    reports = []
    for benchmark_name, pairs in by_benchmark.items():
        cases = {case["case_id"]: case for case, _ in pairs}
        results = [result for _, result in pairs]
        model_names = sorted({f"{x['model_name']}::{x['model_version']}" for x in results})
        accuracy = {}
        for model in model_names:
            subset = [x for x in results if f"{x['model_name']}::{x['model_version']}" == model]
            accuracy[model] = round(sum(x["passed"] for x in subset) / len(subset) * 100, 2)
        reproducible_failure = sum(
            1 for case_id in cases
            if sum(not x["passed"] for x in results if x["case_id"] == case_id) >= 2
        ) / len(cases)
        pack = next(x for x in manifest["packs"] if x["benchmark_name"] == benchmark_name)
        eval_run_id = f"{manifest['package_id']}::{benchmark_name.lower().replace(' ', '-')}"
        with db() as conn:
            exists = conn.execute("SELECT id FROM evaluation_runs WHERE run_id=?", (eval_run_id,)).fetchone()
        if ingest and exists:
            raise ValueError(f"evaluation run already ingested: {eval_run_id}")
        payload = {
            "sample_size": len(cases), "model_count": len(model_names),
            "sota_score": max(accuracy.values()), "score_range": max(accuracy.values()) - min(accuracy.values()),
            "reproducible_failure": reproducible_failure, "judge_agreement": 1.0,
            "notes": "Offline import of real model outputs; deterministic objective grading; no simulated responses.",
            "eval_run_id": eval_run_id, "benchmark_id": benchmark_name,
            "dataset_version": Path(pack["private_answer_key"]).name,
            "dataset_hash": pack["private_answer_key_sha256"],
            "prompt_version": "offline-export-v1", "rubric_version": "official-objective-v1",
            "judge_type": "deterministic", "judge_name": "objective-grader",
            "judge_version": "offline-eval-v1",
            "protocol": {
                "temperature": 0, "models": model_names, "package_id": manifest["package_id"],
                "response_file_sha256": file_hash(response_file), "complete_model_task_matrix": True,
            },
            "artifact_url": str(run_parent), "run_date": now_iso(), "cases": results,
        }
        if ingest:
            add_mini_eval(pack["idea_id"], payload)
        report = {
            "idea_id": pack["idea_id"], "benchmark": benchmark_name, "eval_run_id": eval_run_id,
            "cases": len(cases), "models": model_names, "accuracy": accuracy,
            "max_gap_pp": payload["score_range"], "reproducible_failure": reproducible_failure,
            "ingested": ingest,
        }
        reports.append(report)
        (run_parent / f"{benchmark_name.lower().replace(' ', '-')}_graded_results.json").write_text(
            json.dumps({"report": report, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    receipt = {
        "package_id": manifest["package_id"], "response_file": str(response_file),
        "response_file_sha256": file_hash(response_file), "validated_records": len(responses),
        "reports": reports, "ingested": ingest, "processed_at": now_iso(),
    }
    (run_parent / "import_receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description="Export and import real offline Mini Eval model results")
    sub = parser.add_subparsers(dest="command", required=True)
    export = sub.add_parser("export")
    export.add_argument("--package-id", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("--package-dir", type=Path, required=True)
    validate.add_argument("--responses", type=Path, required=True)
    combine = sub.add_parser("combine", help="合并3个工作台导出的逐模型JSONL并执行完整校验")
    combine.add_argument("--package-dir", type=Path, required=True)
    combine.add_argument("--input-dir", type=Path, required=True)
    combine.add_argument("--output", type=Path, required=True)
    imp = sub.add_parser("import")
    imp.add_argument("--package-dir", type=Path, required=True)
    imp.add_argument("--responses", type=Path, required=True)
    imp.add_argument("--ingest", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "export":
            output = export_package(args.package_id)
        elif args.command == "validate":
            manifest, responses, tasks = validate_responses(args.package_dir, args.responses)
            output = {"ok": True, "package_id": manifest["package_id"], "records": len(responses), "tasks": len(tasks)}
        elif args.command == "combine":
            output = combine_results(args.package_dir, args.input_dir, args.output)
        else:
            output = import_results(args.package_dir, args.responses, args.ingest)
        print(json.dumps(output, ensure_ascii=False, indent=2))
    except (FileNotFoundError, FileExistsError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        sys.exit(2)


if __name__ == "__main__":
    main()

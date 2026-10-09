from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from radar.core.radar_core import BASE_DIR, add_mini_eval


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_jsonl(path: Path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def safe_name(value: str):
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", value)


def model_key(config):
    key = os.getenv(config["api_key_env"], "")
    if not key:
        raise RuntimeError(f"missing environment variable {config['api_key_env']}")
    return key


def call_model(config: dict[str, Any], prompt: str, tools=None) -> dict[str, Any]:
    provider, started = config["provider"], time.time()
    key = model_key(config)
    if provider == "openai_compatible":
        payload = {"model": config["model"], "messages": [{"role": "user", "content": prompt}], "temperature": 0}
        if tools:
            payload["tools"] = [{"type": "function", "function": x} for x in tools]
            payload["tool_choice"] = "required"
        response = requests.post(config["base_url"].rstrip("/") + "/chat/completions", headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, json=payload, timeout=180)
        response.raise_for_status()
        data = response.json()
        message = data["choices"][0]["message"]
        text = message.get("content") or ""
        if message.get("tool_calls"):
            text = json.dumps([{"name": x["function"]["name"], "arguments": json.loads(x["function"]["arguments"])} for x in message["tool_calls"]], ensure_ascii=False)
    elif provider == "anthropic":
        payload = {"model": config["model"], "max_tokens": 2048, "temperature": 0, "messages": [{"role": "user", "content": prompt}]}
        if tools:
            payload["tools"] = [{"name": x["name"], "description": x.get("description", ""), "input_schema": x["parameters"]} for x in tools]
        response = requests.post(config["base_url"].rstrip("/") + "/messages", headers={"x-api-key": key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}, json=payload, timeout=180)
        response.raise_for_status()
        data = response.json()
        blocks = data.get("content", [])
        calls = [{"name": x.get("name"), "arguments": x.get("input")} for x in blocks if x.get("type") == "tool_use"]
        text = json.dumps(calls, ensure_ascii=False) if calls else "\n".join(x.get("text", "") for x in blocks if x.get("type") == "text")
    elif provider == "gemini":
        url = f"{config['base_url'].rstrip('/')}/models/{config['model']}:generateContent?key={key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0}}
        if tools:
            payload["tools"] = [{"functionDeclarations": [{"name": x["name"], "description": x.get("description", ""), "parameters": x["parameters"]} for x in tools]}]
        response = requests.post(url, json=payload, timeout=180)
        response.raise_for_status()
        data = response.json()
        parts = data["candidates"][0]["content"]["parts"]
        calls = [{"name": x["functionCall"]["name"], "arguments": x["functionCall"].get("args", {})} for x in parts if "functionCall" in x]
        text = json.dumps(calls, ensure_ascii=False) if calls else "\n".join(x.get("text", "") for x in parts)
    else:
        raise ValueError(f"unsupported provider {provider}")
    return {"text": text, "raw": data, "http_status": response.status_code, "latency_seconds": round(time.time() - started, 3)}


def prompt_for(case):
    if case["benchmark_name"] == "BFCL v3":
        return "Select and call the correct function for the user request. Do not explain; use the provided tool schema.\n\nUser request:\n" + case["task_prompt"]
    if case["benchmark_name"] == "FinanceBench":
        return f"Answer only from the supplied financial document excerpt. Give the answer and cite the document/page label that supports it.\n\nQuestion:\n{case['task_prompt']}\n\nDocument excerpt:\n{case['input']}"
    return f"请依据病例信息回答问题。不得编造未提供的检查结果；如信息不足应明确说明。\n\n病例：\n{case['input']}\n\n问题：\n{case['task_prompt']}"


def numeric_tokens(text: str) -> list[str]:
    values = []
    for raw in re.findall(r"\(?-?\d[\d,]*(?:\.\d+)?\)?", text or ""):
        value = raw.replace(",", "")
        if value.startswith("(") and value.endswith(")"):
            value = "-" + value[1:-1]
        if "." in value:
            value = value.rstrip("0").rstrip(".")
        values.append(value)
    return values


def parse_calls(text: str):
    candidates = re.findall(r"\[.*\]|\{.*\}", text, re.S)
    if not candidates:
        return []
    try:
        value = json.loads(candidates[-1])
        return value if isinstance(value, list) else [value]
    except Exception:
        return []


def objective_grade(case, response):
    if case["benchmark_name"] == "FinanceBench":
        expected_values = set(numeric_tokens(case["reference_answer"]))
        actual_values = set(numeric_tokens(response))
        numeric_ok = bool(expected_values) and expected_values.issubset(actual_values)
        expected_low, response_low = case["reference_answer"].strip().lower(), response.lower()
        qualitative = "yes" if expected_low.startswith("yes") else "no" if expected_low.startswith("no") else None
        qualitative_ok = qualitative is None or bool(re.search(rf"\b{qualitative}\b", response_low))
        answer_ok = numeric_ok and qualitative_ok
        pages = [str(int(x["page_num_zero_based"]) + 1) for x in case["rubric"].get("required_evidence", []) if x.get("page_num_zero_based") is not None]
        cited_pages = re.findall(r"(?:page|p\.?|页)\s*#?\s*(\d+)", response, re.I)
        citation_ok = not pages or any(page in cited_pages for page in pages)
        passed = answer_ok and citation_ok
        result = {
            "answer_match": answer_ok, "numeric_match": numeric_ok, "qualitative_match": qualitative_ok,
            "expected_values": sorted(expected_values), "observed_values": sorted(actual_values),
            "citation_match": citation_ok, "expected_pages": pages, "cited_pages": cited_pages,
        }
        return {"score": 1.0 if passed else 0.5 if answer_ok else 0.0, "passed": passed, "failure_type": None if passed else "citation_error" if answer_ok else "financial_answer_error", "judge_result": json.dumps(result, ensure_ascii=False)}
    if case["benchmark_name"] == "BFCL v3":
        calls, truth = parse_calls(response), case["reference_answer"]
        names = {next(iter(x)) for x in truth}
        valid_calls = [x for x in calls if isinstance(x, dict) and x.get("name")]
        name_ok = bool(valid_calls) and all(x["name"] in names for x in valid_calls)
        argument_checks = []
        if name_ok:
            schemas = {x["name"]: x for x in case.get("input", {}).get("functions", [])}
            for call in valid_calls:
                args = call.get("arguments", {})
                expected = next((x[call["name"]] for x in truth if call["name"] in x), {})
                required = set(schemas.get(call["name"], {}).get("parameters", {}).get("required", []))
                required_ok = all(k in args and str(args[k]) in {str(v) for v in expected.get(k, [])} for k in required)
                optional_ok = all(k not in args or str(args[k]) in {str(v) for v in vals} for k, vals in expected.items() if k not in required)
                argument_checks.append({"function": call["name"], "required_match": required_ok, "optional_match": optional_ok})
        arg_ok = bool(argument_checks) and all(x["required_match"] and x["optional_match"] for x in argument_checks)
        passed = name_ok and arg_ok
        return {"score": 1.0 if passed else 0.0, "passed": passed, "failure_type": None if passed else "wrong_arguments" if name_ok else "wrong_function", "judge_result": json.dumps({"function_match": name_ok, "argument_match": arg_ok, "checks": argument_checks}, ensure_ascii=False)}
    return None


def judge_medical(case, response, judge):
    prompt = f"""你是医学评测审稿人。只根据病例、参考答案和评分维度评价模型回答，不增加新的医疗事实。输出JSON：{{\"score\":0到1,\"passed\":true或false,\"failure_type\":字符串或null,\"error_analysis\":字符串,\"rubric_hits\":对象}}。
病例：{case['input']}
问题：{case['task_prompt']}
参考答案：{case['reference_answer']}
评分维度：{json.dumps(case['rubric'], ensure_ascii=False)}
模型回答：{response}"""
    result = call_model(judge, prompt)
    parsed = parse_calls(result["text"])
    if not parsed:
        raise ValueError("judge did not return valid JSON")
    value = parsed[0]
    value["judge_raw"] = result["raw"]
    return value


def run(case_file: Path, model_config: Path, run_id: str, ingest: bool):
    cases = load_jsonl(case_file)
    cfg = json.loads(model_config.read_text(encoding="utf-8"))
    models = [x for x in cfg["models"] if x.get("enabled")]
    if len(models) < 3:
        raise RuntimeError("At least three enabled model configurations are required; no simulated model output is allowed.")
    judge = cfg.get("judge") or {}
    if any(x["benchmark_name"] == "CMB-Clin" for x in cases) and not judge.get("enabled"):
        raise RuntimeError("CMB-Clin requires an enabled judge; no synthetic Judge Result is allowed.")
    run_dir = BASE_DIR / "data" / "mini_eval_runs" / safe_name(run_id)
    run_dir.mkdir(parents=True, exist_ok=False)
    results = []
    for model in models:
        for case in cases:
            tools = case.get("input", {}).get("functions") if case["benchmark_name"] == "BFCL v3" else None
            called = call_model(model, prompt_for(case), tools)
            grade = objective_grade(case, called["text"]) or judge_medical(case, called["text"], judge)
            results.append({
                "failure_case_id": f"{case['case_id']}::{model['id']}", "case_id": case["case_id"],
                "benchmark_name": case["benchmark_name"], "task_prompt": case["task_prompt"], "input": case["input"],
                "reference_answer": case["reference_answer"], "rubric": json.dumps(case["rubric"], ensure_ascii=False),
                "model_name": model["id"], "model_version": model["model"], "model_response": called["text"],
                "score": float(grade["score"]), "passed": bool(grade["passed"]), "failure_type": grade.get("failure_type") or "none",
                "severity": "high" if not grade["passed"] else "low", "error_analysis": grade.get("error_analysis") or grade["judge_result"],
                "judge_result": grade.get("judge_result") or json.dumps(grade, ensure_ascii=False), "run_date": now_iso(),
                "attachments": [], "raw_data": {"model_raw": called["raw"], "latency_seconds": called["latency_seconds"], "source": case["source"]}
            })
            (run_dir / "results.jsonl").open("a", encoding="utf-8").write(json.dumps(results[-1], ensure_ascii=False) + "\n")
    by_model = {}
    for model in models:
        subset = [x for x in results if x["model_name"] == model["id"]]
        by_model[model["id"]] = sum(x["passed"] for x in subset) / len(subset) * 100
    summary = {"run_id": run_id, "case_file": str(case_file), "case_file_sha256": hashlib.sha256(case_file.read_bytes()).hexdigest(), "models": [x["id"] for x in models], "accuracy": by_model, "max_gap_pp": max(by_model.values()) - min(by_model.values()), "created_at": now_iso()}
    (run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    if ingest:
        payload = {
            "sample_size": len(cases), "model_count": len(models), "sota_score": max(by_model.values()), "score_range": summary["max_gap_pp"],
            "reproducible_failure": sum(1 for case in cases if sum(not x["passed"] for x in results if x["case_id"] == case["case_id"]) >= 2) / len(cases),
            "judge_agreement": 1.0 if cases[0]["benchmark_name"] != "CMB-Clin" else 0.0,
            "eval_run_id": run_id, "benchmark_id": cases[0]["benchmark_name"], "dataset_version": case_file.name,
            "dataset_hash": summary["case_file_sha256"], "prompt_version": "mini-eval-v1", "rubric_version": "case-pack-v1",
            "judge_type": "objective" if cases[0]["benchmark_name"] != "CMB-Clin" else "llm",
            "judge_name": "deterministic-checker" if cases[0]["benchmark_name"] != "CMB-Clin" else judge["model"],
            "judge_version": "v1", "protocol": {"temperature": 0, "models": summary["models"]}, "artifact_url": str(run_dir), "run_date": now_iso(), "cases": results
        }
        if cases[0]["benchmark_name"] == "CMB-Clin":
            raise RuntimeError("Medical run requires physician calibration before ingest; results retained locally for review.")
        add_mini_eval(cases[0]["idea_id"], payload)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("case_file", type=Path)
    parser.add_argument("--models", type=Path, default=BASE_DIR / "config" / "models.json")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--ingest", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args.case_file, args.models, args.run_id, args.ingest), ensure_ascii=False, indent=2))

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from radar.core.radar_core import BASE_DIR, weekly_report

INSIGHT_DIR = BASE_DIR / "outputs" / "insights"


def verify(require_public: bool = False) -> dict:
    manifest_path = INSIGHT_DIR / "manifest.json"
    if not manifest_path.exists():
        raise RuntimeError("manifest.json not found; run insight_pages.py first")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    detail_urls: set[str] = set()
    idea_ids: set[int] = set()
    checked_files: set[str] = set()

    def check_file(filename: str, required: list[str]) -> None:
        checked_files.add(filename)
        path = INSIGHT_DIR / filename
        if not path.exists():
            errors.append(f"missing page: {filename}")
            return
        content = path.read_text(encoding="utf-8")
        for marker in required:
            if marker not in content:
                errors.append(f"{filename}: missing {marker}")

    def check_public(url: str) -> None:
        parsed = urlparse(url)
        if require_public and (parsed.scheme != "https" or parsed.hostname in {"127.0.0.1", "localhost", "0.0.0.0"}):
            errors.append(f"not public HTTPS: {url}")

    for item in manifest:
        idea_id, url = item["idea_id"], item["url"]
        if idea_id in idea_ids:
            errors.append(f"duplicate idea_id: {idea_id}")
        idea_ids.add(idea_id)
        if url in detail_urls:
            errors.append(f"duplicate detail url: {url}")
        detail_urls.add(url)
        check_public(url)
        check_file(item["file"], [
            "Core Insight", "Why Now", "四条 Radar Evidence", "Existing Benchmark",
            "Evaluation Gap", "Model Failure", "Benchmark Proposal", "Mini Eval Design",
            "Evidence Confidence", "Claim → Evidence Mapping", "supports", "Score Breakdown", "Raw Source Links & Provenance",
            "Evidence Retrieval Log", "查看 Evidence Detail", "PROVENANCE READY",
        ])
        check_file(item.get("retrieval_log", ""), ["EVIDENCE RETRIEVAL QA", "Retrieval Query"] if item.get("retrieval_log") else [])
        check_file(item.get("coverage_matrix", ""), ["BENCHMARK COVERAGE MATRIX", "Task", "Dataset", "Input", "Output", "Evaluation Protocol", "Metric", "Target Coverage"] if item.get("coverage_matrix") else [])
        for filename in item.get("evidence_groups", {}).values():
            check_file(filename, ["Evidence Group", "Evidence Items"])
        for filename in item.get("evidence_items", []):
            check_file(filename, ["RAW SOURCE", "EVIDENCE EXTRACTION", "AI ANALYSIS", "Provenance", "查看 Raw Source"])
        for filename in item.get("raw_sources", []):
            check_file(filename, ["RAW SOURCE", "原始材料", "Raw Payload", "完整 Provenance", "Reverse Trace", "Claim", "Relation", "Status"])
        for filename in item.get("failure_cases", []):
            check_file(filename, ["Eval Run ID", "Failure Case ID", "Task / Prompt", "Reference Answer", "Rubric", "Model Response", "Failure Type", "Judge Result", "原始附件 / 数据"])
        for link in list(item.get("group_urls", {}).values()) + item.get("evidence_urls", []) + item.get("raw_source_urls", []) + item.get("failure_case_urls", []):
            check_public(link)

    expected_ids = {x["id"] for x in weekly_report()["top10"]}
    missing_top = expected_ids - idea_ids
    if missing_top:
        errors.append(f"Top10 missing detail pages: {sorted(missing_top)}")
    check_file("failure-evidence.html", ["Failure Case Explorer", "全部 Model", "全部 Failure Type", "全部 Severity", "全部 Benchmark"])
    return {
        "ok": not errors, "idea_pages": len(manifest), "hierarchy_pages_checked": len(checked_files),
        "unique_detail_urls": len(detail_urls), "top10_covered": not missing_top, "errors": errors,
    }


def main():
    parser = argparse.ArgumentParser(description="验证 Insight 独立URL、章节和来源引用")
    parser.add_argument("--require-public", action="store_true")
    args = parser.parse_args()
    result = verify(args.require_public)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from radar.evidence.evidence_quality import sync_all_idea_quality
from radar.evidence.evidence_retrieval import retrieve_needs_verification
from radar.publish.insight_pages import generate as generate_insights
from radar.core.radar_core import BASE_DIR, init_db, run_pipeline, verify_stale_sources, weekly_report


def cycle(collect: bool = True):
    result = run_pipeline(collect=collect)
    result["source_freshness"] = verify_stale_sources(limit=10, max_age_days=30)
    result["quality_after_freshness"] = sync_all_idea_quality()
    try:
        result["evidence_retrieval"] = retrieve_needs_verification(limit=1)
    except Exception as exc:
        result["evidence_retrieval"] = {"error": str(exc), "status": "retry_next_cycle"}
    output = BASE_DIR / "outputs" / "latest_top10.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(weekly_report(), ensure_ascii=False, indent=2), encoding="utf-8")
    insights = generate_insights()
    state = {"pipeline": result, "latest_output": str(output), "insight_pages": insights["pages"], "insight_base_url": insights["base_url"]}
    (BASE_DIR / "data" / "scheduler_state.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(state, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description="Benchmark Idea Radar 周期采集器")
    parser.add_argument("--interval-hours", type=float, default=24)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--no-collect", action="store_true")
    args = parser.parse_args()
    init_db()
    while True:
        try:
            cycle(collect=not args.no_collect)
        except Exception as exc:
            error = {"error": str(exc), "retry_in_hours": args.interval_hours}
            print(json.dumps(error, ensure_ascii=False), flush=True)
        if args.once:
            break
        time.sleep(max(0.1, args.interval_hours) * 3600)


if __name__ == "__main__":
    main()

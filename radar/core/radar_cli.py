from __future__ import annotations

import argparse
import json
from pathlib import Path

from radar.core.radar_core import BASE_DIR, add_mini_eval, import_items, init_db, run_pipeline, weekly_report


def dump(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Benchmark Idea Radar V1")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="初始化数据库")
    sub.add_parser("seed", help="导入示例数据并运行全链路")
    run = sub.add_parser("run", help="运行采集/抽取/聚类/评分")
    run.add_argument("--collect", action="store_true", help="同时采集公开 RSS 来源")
    weekly = sub.add_parser("weekly", help="生成 Weekly Top 10 JSON")
    weekly.add_argument("--output", default="outputs/weekly_top10.json")
    mini = sub.add_parser("mini-eval", help="回流 Mini Eval 结果")
    mini.add_argument("idea_id", type=int)
    mini.add_argument("--sample-size", type=int, required=True)
    mini.add_argument("--model-count", type=int, required=True)
    mini.add_argument("--sota-score", type=float, required=True)
    mini.add_argument("--score-range", type=float, required=True)
    mini.add_argument("--failure-rate", type=float, required=True, help="0-1之间")
    mini.add_argument("--judge-agreement", type=float, required=True, help="0-1之间")
    mini.add_argument("--notes", default="")
    mini.add_argument("--cases-file", help="包含逐Case失败证据数组的JSON文件")
    failure = sub.add_parser("failure", help="录入 Benchmark Run / 模型对比 / Bad Case / 人工反馈")
    failure.add_argument("--source", choices=["benchmark-run", "model-comparison", "bad-case", "human-feedback"], required=True)
    failure.add_argument("--title", required=True)
    failure.add_argument("--content", required=True)
    failure.add_argument("--url", default="")
    sub.add_parser("lit", help="重建 Benchmark 索引（判 Benchmark、分领域），输出覆盖表（纯正则，不调 API）")
    args = parser.parse_args()
    init_db()
    if args.command == "lit":
        from radar.core.lit_index import run as lit_run
        dump(lit_run(BASE_DIR))
    elif args.command == "init":
        dump({"ok": True, "database": str(BASE_DIR / "data" / "radar.db")})
    elif args.command == "seed":
        items = json.loads((BASE_DIR / "data" / "sample_source_items.json").read_text(encoding="utf-8"))
        dump({"import": import_items(items), "pipeline": run_pipeline(False)})
    elif args.command == "run":
        dump(run_pipeline(args.collect))
    elif args.command == "weekly":
        output = BASE_DIR / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        report = weekly_report()
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        dump({"ok": True, "output": str(output), "ideas": len(report["top10"])})
    elif args.command == "mini-eval":
        payload = {
            "sample_size": args.sample_size,
            "model_count": args.model_count,
            "sota_score": args.sota_score,
            "score_range": args.score_range,
            "reproducible_failure": args.failure_rate,
            "judge_agreement": args.judge_agreement,
            "notes": args.notes,
            "cases": [],
        }
        if args.cases_file:
            run_data = json.loads(Path(args.cases_file).read_text(encoding="utf-8"))
            if isinstance(run_data, list):
                payload["cases"] = run_data
            else:
                payload.update(run_data)
        dump(add_mini_eval(args.idea_id, payload))
    elif args.command == "failure":
        item = {
            "radar": "model_failure",
            "source_id": args.source,
            "title": args.title,
            "content": args.content,
            "url": args.url or f"internal://{args.source}",
        }
        dump({"import": import_items([item]), "pipeline": run_pipeline(False)})


if __name__ == "__main__":
    main()

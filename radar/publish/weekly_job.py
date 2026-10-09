from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import requests

from radar.publish.insight_pages import generate as generate_insights
from radar.core.radar_core import BASE_DIR, init_db, weekly_report


def week_key() -> str:
    year, week, _ = datetime.now().isocalendar()
    return f"{year}-W{week:02d}"


def project_settings() -> dict:
    path = BASE_DIR / "config" / "project_settings.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def idea_line(index: int, idea: dict, include_radar: bool = True) -> str:
    meta = f"｜{idea['total_score']:.0f}分"
    if include_radar:
        meta += f"｜{idea['radar_hits']}/4 Verified Radar"
    if idea.get("evidence_confidence"):
        meta += f"｜Evidence {idea['evidence_confidence']}"
    title = f"[{idea['idea_name']}]({idea['insight_url']})" if idea.get("insight_url") else idea["idea_name"]
    drill = f" [查看 Insight]({idea['insight_url']})" if idea.get("insight_url") else ""
    return f"{index}. **{title}**{meta}{drill}"


def markdown(report: dict) -> str:
    lines = [
        f"# Benchmark Idea Radar · {week_key()}",
        f"> {report['summary']['source_items']} 条输入 → {report['summary']['signals']} 条结构化 Signal → {report['summary']['idea_pool']} 个 Idea；其中 {report['summary'].get('provenance_ready_ideas', 0)} 个通过 Raw Source 门禁，{report['summary'].get('withheld_for_provenance', 0)} 个暂缓发布",
        "",
        "## 立即 Mini Eval",
    ]
    for i, idea in enumerate(report["mini_eval_now"][:3], 1):
        lines.append(idea_line(i, idea))
    if not report["mini_eval_now"]:
        lines.append("暂无达到门槛的 Idea")
    lines.extend(["", "## 持续观察"])
    for i, idea in enumerate(report["watch"][:3], 1):
        lines.append(idea_line(i, idea, include_radar=False))
    if not report["watch"]:
        lines.append("暂无观察项")
    lines.extend(["", "## Needs Verification · 高价值但证据不足"])
    for i, idea in enumerate(report.get("needs_verification", [])[:3], 1):
        title = f"[{idea['idea_name']}]({idea.get('insight_url')})" if idea.get("insight_url") else idea["idea_name"]
        lines.append(f"{i}. **{title}**｜Idea {idea['total_score']:.0f}｜Evidence {idea.get('evidence_confidence', 'Low')}｜缺少 {', '.join(idea.get('missing_evidence', []))}")
    if not report.get("needs_verification"):
        lines.append("暂无高价值缺证Idea")
    lines.extend(["", "## 热门但暂不建议"])
    for i, idea in enumerate(report["not_recommended"][:3], 1):
        lines.append(idea_line(i, idea))
    if not report["not_recommended"]:
        lines.append("暂无暂缓项")
    changes = report.get("changes", {})
    lines.extend([
        "",
        "## 本周变化",
        f"> 新增 {len(changes.get('new', []))}｜升档 {len(changes.get('promoted', []))}｜降档 {len(changes.get('demoted', []))}｜淘汰 {len(changes.get('eliminated', []))}",
    ])
    if report.get("top10") and report["top10"][0].get("insight_url"):
        base = report["top10"][0]["insight_url"].rsplit("/", 1)[0]
        lines.extend(["", f"[查看 Model Failure Evidence 聚合与筛选]({base}/failure-evidence.html)"])
    return "\n".join(lines)[:3900]


def is_public_base(url: str) -> bool:
    value = (url or "").lower()
    return value.startswith("https://") and not any(x in value for x in ["127.0.0.1", "localhost", "0.0.0.0"])


def verify_remote_pages(manifest: list[dict]) -> dict:
    failures = []
    targets = []
    for item in manifest:
        targets.append((item["idea_id"], "idea", item["url"]))
        targets.extend((item["idea_id"], "group", url) for url in item.get("group_urls", {}).values())
        targets.extend((item["idea_id"], "evidence", url) for url in item.get("evidence_urls", []))
        targets.extend((item["idea_id"], "raw", url) for url in item.get("raw_source_urls", []))
        targets.extend((item["idea_id"], "failure_case", url) for url in item.get("failure_case_urls", []))
        if item.get("retrieval_log_url"):
            targets.append((item["idea_id"], "retrieval_log", item["retrieval_log_url"]))
        if item.get("coverage_matrix_url"):
            targets.append((item["idea_id"], "coverage_matrix", item["coverage_matrix_url"]))
    if manifest:
        base = manifest[0]["url"].rsplit("/", 1)[0]
        targets.append((0, "failure_explorer", f"{base}/failure-evidence.html"))
    seen = set()
    unique_targets = [x for x in targets if not (x[2] in seen or seen.add(x[2]))]
    def check(target):
        idea_id, level, url = target
        last_error = None
        for attempt in range(1, 4):
            try:
                response = requests.get(url, timeout=15)
                if response.status_code == 200:
                    return None
                last_error = {"idea_id": idea_id, "level": level, "url": url, "status": response.status_code, "attempts": attempt}
            except Exception as exc:
                last_error = {"idea_id": idea_id, "level": level, "url": url, "error": str(exc), "attempts": attempt}
            time.sleep(attempt)
        return last_error

    with ThreadPoolExecutor(max_workers=16) as pool:
        for future in as_completed([pool.submit(check, target) for target in unique_targets]):
            failure = future.result()
            if failure:
                failures.append(failure)
    return {"ok": not failures, "checked": len(unique_targets), "failures": failures}


def push_wecom(content: str, webhook: str) -> dict:
    payload = {"msgtype": "markdown", "markdown": {"content": content}}
    last_error = None
    for attempt in range(1, 4):
        try:
            response = requests.post(webhook, json=payload, timeout=15)
            response.raise_for_status()
            result = response.json()
            if result.get("errcode") == 0:
                return {"ok": True, "attempt": attempt, "response": result}
            last_error = f"WeCom errcode={result.get('errcode')}: {result.get('errmsg')}"
        except Exception as exc:
            last_error = str(exc)
        time.sleep(attempt * 2)
    return {"ok": False, "error": last_error}


def add_insight_links(report: dict, url_map: dict[int, str]) -> None:
    for key in ["top10", "mini_eval_now", "watch", "not_recommended", "needs_verification"]:
        for idea in report.get(key, []):
            idea["insight_url"] = url_map.get(idea["id"])
    for ideas in report.get("changes", {}).values():
        for idea in ideas:
            idea["insight_url"] = url_map.get(idea["id"])


def run(force: bool = False, no_push: bool = False) -> dict:
    init_db()
    insight_result = generate_insights()
    url_map = {x["idea_id"]: x["url"] for x in insight_result["manifest"]}
    report = weekly_report()
    add_insight_links(report, url_map)
    key = week_key()
    weekly_dir = BASE_DIR / "outputs" / "weekly"
    weekly_dir.mkdir(parents=True, exist_ok=True)
    json_path = weekly_dir / f"{key}.json"
    md_path = weekly_dir / f"{key}.md"
    text = markdown(report)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(text, encoding="utf-8")

    state_path = BASE_DIR / "data" / "weekly_push_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    settings = project_settings()
    push_enabled = bool(settings.get("wecom_push_enabled", False))
    webhook = os.getenv("WECOM_WEBHOOK_URL", "").strip()
    insight_base = insight_result["base_url"]
    remote_check = verify_remote_pages(insight_result["manifest"]) if push_enabled and is_public_base(insight_base) and not no_push else {"ok": True, "checked": 0, "skipped": True}
    if no_push:
        push = {"ok": True, "skipped": "--no-push"}
    elif not push_enabled:
        push = {"ok": True, "skipped": settings.get("push_pause_reason", "WeCom push disabled by project settings")}
    elif not is_public_base(insight_base):
        push = {"ok": False, "skipped": "RADAR_PUBLIC_BASE_URL must be a public HTTPS URL before WeCom push"}
    elif not remote_check["ok"]:
        push = {"ok": False, "skipped": "Insight deep-link verification failed", "failures": remote_check["failures"]}
    elif not webhook:
        push = {"ok": False, "skipped": "WECOM_WEBHOOK_URL not configured"}
    elif state.get("last_pushed_week") == key and not force:
        push = {"ok": True, "skipped": f"{key} already pushed"}
    else:
        push = push_wecom(text, webhook)
        if push.get("ok"):
            state = {"last_pushed_week": key, "pushed_at": datetime.now().isoformat(timespec="seconds")}
            state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    log = {
        "week": key,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "json": str(json_path),
        "markdown": str(md_path),
        "insight_pages": insight_result["pages"],
        "insight_base_url": insight_result["base_url"],
        "public_base_configured": is_public_base(insight_result["base_url"]),
        "remote_detail_check": remote_check,
        "push": push,
    }
    log_path = BASE_DIR / "outputs" / "wecom_push_log.jsonl"
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(log, ensure_ascii=False) + "\n")
    return log


def main():
    parser = argparse.ArgumentParser(description="生成并推送 Benchmark Idea Radar 周报")
    parser.add_argument("--force", action="store_true", help="忽略本周已推送状态")
    parser.add_argument("--no-push", action="store_true", help="只归档，不调用企业微信")
    args = parser.parse_args()
    print(json.dumps(run(force=args.force, no_push=args.no_push), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

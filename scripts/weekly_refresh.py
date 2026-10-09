"""每周刷新：抓 arXiv 新论文 → 分类 → 重建索引 → 撞车提醒。

用法: python3 scripts/weekly_refresh.py [--no-push] [--from 论文文件.jsonl]
每周一 15:00（北京时间）由内网开发机定时器调用（会推送）；GitHub Actions 用 --no-push 调用，只更新网页版。
--from 用于机器上不了外网：直接导入别处抓好的论文文件。
结果写到 reports/weekly_refresh.md，
有新论文挤进某个方向“最像的 10 篇”且未核对时，在报告顶部提醒。
"""
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    day = datetime.now().strftime("%Y%m%d")
    (ROOT / "data" / "backups").mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "data" / "radar.db", ROOT / "data" / "backups" / f"radar.db.before-weekly-{day}")

    sweep_cmd = [sys.executable, str(ROOT / "scripts" / "sweep_arxiv_benchmarks.py")]
    if "--from" in sys.argv:  # 服务器上不了外网：用别的机器抓好的文件导入
        sweep_cmd += ["--load", sys.argv[sys.argv.index("--from") + 1]]
    else:
        sweep_cmd += ["600"]
    sweep = subprocess.run(sweep_cmd, cwd=ROOT, capture_output=True, text=True)
    last = [ln for ln in sweep.stdout.splitlines() if ln.startswith("done")]
    sweep_ok = sweep.returncode == 0
    if not sweep_ok:
        tail = "\n".join((sweep.stdout + sweep.stderr).splitlines()[-8:])
        (ROOT / "reports" / "weekly_refresh.md").write_text(
            f"# 每周刷新 {datetime.now():%Y-%m-%d}：抓取失败\n\n"
            f"arXiv 一篇都没拿到（退出码 {sweep.returncode}），本次没有更新索引，页面仍是上次的数据。\n\n"
            f"```\n{tail}\n```\n", encoding="utf-8")
        print(json.dumps({"failed": True, "returncode": sweep.returncode, "tail": tail}, ensure_ascii=False))
        sys.exit(1)

    from radar.core.radar_core import db, reclassify_stale_signals, run_pipeline
    run_pipeline(False)
    with db() as conn:
        reclassify_stale_signals(conn)
    from radar.core.lit_index import research_map, run
    run(ROOT)
    m = research_map()

    alerts = []
    for d in m["domains"]:
        for x in d["can_do"]:
            for o in x["check_overlap"]:
                alerts.append(f"- {d['label']} · {x['title']}：[{o['name']}]({o['url']})（相似度 {o['score']}）")
    lines = [f"# 每周刷新 {datetime.now():%Y-%m-%d}", "",
             f"抓取：{last[0] if last else '失败，见日志'}", ""]
    lines += (["## 需要人工核对的疑似撞车论文", ""] + alerts) if alerts else ["没有新论文挤进任何方向最像的 10 篇。"]
    lines += ["", "## 各领域数量", ""] + [f"- {d['label']}：已有 {d['counts']['benchmarks']}，缺口 {d['counts']['gaps']}，可做 {d['counts']['can_do']}" for d in m["domains"]]
    (ROOT / "reports" / "weekly_refresh.md").write_text("\n".join(lines), encoding="utf-8")
    (ROOT / "reports" / "weekly_alerts.json").write_text(
        json.dumps({"date": f"{datetime.now():%Y-%m-%d}", "alerts": alerts}, ensure_ascii=False, indent=2), encoding="utf-8")

    from radar.publish.wecom_push import push
    try:
        pushed = push(alerts=alerts, dry_run="--no-push" in sys.argv)
        pushed.pop("text", None)
    except Exception as exc:  # 推送失败不影响刷新结果
        pushed = {"ok": False, "error": str(exc)}
    print(json.dumps({"alerts": len(alerts), "sweep": last, "wecom": pushed}, ensure_ascii=False))


if __name__ == "__main__":
    main()

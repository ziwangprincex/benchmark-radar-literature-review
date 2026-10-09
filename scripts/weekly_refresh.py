"""每周刷新：抓 arXiv 新论文 → 分类 → 重建 Benchmark 索引 → 推送待读提醒。

用法: python3 scripts/weekly_refresh.py [--no-push] [--from 论文文件.jsonl]
每周一 15:00（北京时间）由内网开发机定时器调用（会推送）；GitHub Actions 用 --no-push 调用，只更新网页版。
--from 用于机器上不了外网：直接导入别处抓好的论文文件。
结果写到 reports/weekly_refresh.md。

2026-10-09 起不再做研究地图和撞车提醒，可做方向看文献综述。
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
    if sweep.returncode != 0:
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
    from radar.core.lit_index import run
    run(ROOT)

    from radar.core.reading import reading_list
    rd = reading_list()
    new_week = [x for x in rd["items"] if x["week"] == rd["latest_week"]]
    label = {d["domain"]: d["label"] for d in rd["domains"]}
    count = {}
    for x in new_week:
        count[x["domain"]] = count.get(x["domain"], 0) + 1
    lines = [f"# 每周刷新 {datetime.now():%Y-%m-%d}", "",
             f"抓取：{last[0] if last else '失败，见日志'}", "",
             f"## 本周新收 {len(new_week)} 篇", ""]
    lines += [f"- {label.get(d, d)}：{n}" for d, n in sorted(count.items(), key=lambda kv: -kv[1])]
    (ROOT / "reports" / "weekly_refresh.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    from radar.publish.wecom_push import push
    try:
        pushed = push(dry_run="--no-push" in sys.argv)
        pushed.pop("text", None)
    except Exception as exc:  # 推送失败不影响刷新结果
        pushed = {"ok": False, "error": str(exc)}
    print(json.dumps({"new_this_week": len(new_week), "sweep": last, "wecom": pushed}, ensure_ascii=False))


if __name__ == "__main__":
    main()

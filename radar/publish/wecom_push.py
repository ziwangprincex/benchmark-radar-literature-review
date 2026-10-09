"""企业微信推送：每周把"新收了哪些论文、还有多少没读"发到群里。

只推提醒，不推结论。Webhook 地址按顺序找：
1. 环境变量 WECOM_WEBHOOK_URL
2. data/wecom_config.json 里的 {"webhook": "..."}（已在 .gitignore，不进仓库）
消息末尾的网页链接：环境变量 WECOM_PAGE_URL > 配置里的 page_url（开发机上配的是内网网页）> GitHub Pages 地址。

用法:
    python3 -m radar.publish.wecom_push --dry-run   # 只打印消息，不发
    python3 -m radar.publish.wecom_push             # 发送（同一周只发一次）
    python3 -m radar.publish.wecom_push --force     # 本周已发过也再发
    python3 -m radar.publish.wecom_push --set-webhook <url>
"""
from __future__ import annotations

import argparse
import json
import os
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "data" / "wecom_config.json"
STATE_PATH = ROOT / "data" / "wecom_push_state.json"
LOG_PATH = ROOT / "outputs" / "wecom_push_log.jsonl"
MAX_BYTES = 4000  # 企业微信 markdown 上限 4096 字节，留点余量
TITLES_PER_DOMAIN = 3
DEFAULT_PAGE_URL = "https://ziwangprincex.github.io/benchmark-radar-literature-review/"
SIX_DOMAINS = ["legal", "financial", "medical", "scientific", "agent", "general"]


def load_config() -> dict[str, Any]:
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8")) if CONFIG_PATH.exists() else {}
    for key, var in (("webhook", "WECOM_WEBHOOK_URL"), ("page_url", "WECOM_PAGE_URL")):
        env = os.getenv(var, "").strip()
        if env:
            cfg[key] = env
    return cfg


def save_webhook(url: str) -> None:
    url = url.strip()
    if not url.startswith("https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key="):
        raise ValueError("看起来不是企业微信群机器人地址，应以 https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key= 开头")
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8")) if CONFIG_PATH.exists() else {}
    cfg["webhook"] = url
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def _short(title: str, limit: int = 60) -> str:
    title = " ".join((title or "").split()).replace("[", "(").replace("]", ")")
    return title if len(title) <= limit else title[:limit].rstrip() + "…"


def build_message(page_url: str | None = None) -> str:
    from radar.core.reading import DOMAIN_CN, reading_list

    data = reading_list()
    week = data["latest_week"]
    items = data["items"]
    unread = [x for x in items if x["state"] == "unread"]
    new_week = [x for x in items if x["week"] == week]
    new_unread = [x for x in new_week if x["state"] == "unread"]

    lines = [f"## Benchmark Radar 待读提醒 · {datetime.now():%m-%d}",
             f"> 本周新收 <font color=\"info\">{len(new_week)}</font> 篇，"
             f"其中未读 <font color=\"warning\">{len(new_unread)}</font> 篇；"
             f"累计未读 {len(unread)} 篇", ""]

    by_dom = Counter(x["domain"] for x in new_unread)
    if new_unread:
        lines.append("**本周未读（按领域）**")
        for d in SIX_DOMAINS:
            group = [x for x in new_unread if x["domain"] == d]
            if not group:
                continue
            lines.append(f"{DOMAIN_CN[d]} {len(group)} 篇")
            for x in group[:TITLES_PER_DOMAIN]:
                lines.append(f"- [{_short(x['title'])}]({x['url']})")
            if len(group) > TITLES_PER_DOMAIN:
                lines.append(f"- 另 {len(group) - TITLES_PER_DOMAIN} 篇见网页")
        if by_dom.get("unclassified"):
            lines.append(f"其他领域 {by_dom['unclassified']} 篇，见网页")
    else:
        lines.append("本周新论文都已处理完。")

    lines += ["", f"[打开待读清单]({page_url or DEFAULT_PAGE_URL})"]

    text = "\n".join(lines)
    while len(text.encode("utf-8")) > MAX_BYTES and len(lines) > 4:
        # 超长时从后往前删论文标题行，保留统计
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].startswith("- [") and "](" in lines[i]:
                del lines[i]
                break
        else:
            break
        text = "\n".join(lines)
    return text


def send(content: str, webhook: str) -> dict[str, Any]:
    payload = {"msgtype": "markdown", "markdown": {"content": content}}
    last = None
    for attempt in range(1, 4):
        try:
            r = requests.post(webhook, json=payload, timeout=15)
            r.raise_for_status()
            res = r.json()
            if res.get("errcode") == 0:
                return {"ok": True, "attempt": attempt}
            last = f"errcode={res.get('errcode')}: {res.get('errmsg')}"
        except Exception as exc:  # noqa: BLE001
            last = str(exc)
        time.sleep(attempt * 2)
    return {"ok": False, "error": last}


def push(force: bool = False, dry_run: bool = False) -> dict[str, Any]:
    cfg = load_config()
    text = build_message(cfg.get("page_url"))
    key = "{}-W{:02d}".format(*datetime.now().isocalendar()[:2])
    state = json.loads(STATE_PATH.read_text(encoding="utf-8")) if STATE_PATH.exists() else {}

    if dry_run:
        result = {"ok": True, "skipped": "dry-run"}
    elif not cfg.get("webhook"):
        result = {"ok": False, "skipped": "没有配置 Webhook，运行 python3 -m radar.publish.wecom_push --set-webhook <地址>"}
    elif state.get("last_week") == key and not force:
        result = {"ok": True, "skipped": f"{key} 已经推送过"}
    else:
        result = send(text, cfg["webhook"])
        if result["ok"]:
            STATE_PATH.write_text(json.dumps({"last_week": key, "pushed_at": datetime.now().isoformat(timespec="seconds")},
                                             ensure_ascii=False, indent=2), encoding="utf-8")

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"at": datetime.now().isoformat(timespec="seconds"), "kind": "reading",
                            "week": key, "bytes": len(text.encode("utf-8")), **result}, ensure_ascii=False) + "\n")
    return {"text": text, **result}


def main() -> None:
    p = argparse.ArgumentParser(description="把待读提醒推到企业微信群")
    p.add_argument("--dry-run", action="store_true", help="只打印消息，不发送")
    p.add_argument("--force", action="store_true", help="本周已推送过也再发一次")
    p.add_argument("--set-webhook", metavar="URL", help="保存群机器人地址到 data/wecom_config.json")
    a = p.parse_args()
    if a.set_webhook:
        save_webhook(a.set_webhook)
        print("已保存到 data/wecom_config.json")
        return
    r = push(force=a.force, dry_run=a.dry_run)
    print(r.pop("text"))
    print("\n" + json.dumps(r, ensure_ascii=False))
    if not r.get("ok"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

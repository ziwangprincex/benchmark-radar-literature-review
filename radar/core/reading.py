"""待读清单：只管"收进了哪些论文、哪些还没读"，不产出任何结论。

数据来自 lit_index（已判过是 Benchmark / 相关论文的条目）+ source_items（标题、链接、摘要），
阅读状态单独存在 reading_status 表里，重新采集或重建 lit_index 都不会冲掉勾选。
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from radar.core.radar_core import db

DOMAIN_ORDER = ["legal", "financial", "medical", "scientific", "agent", "coding", "general", "unclassified"]
DOMAIN_CN = {"legal": "法律", "financial": "金融", "medical": "医疗", "scientific": "科研",
             "agent": "Agent", "coding": "编程", "general": "通用", "unclassified": "其他领域"}
STATES = ("unread", "read", "skip")

_ARXIV_HEAD = re.compile(r"^\s*arXiv:\S+\s+Announce Type:\s*\S+\s+Abstract:\s*", re.I)


def ensure_table() -> None:
    with db() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS reading_status (
                source_item_id INTEGER PRIMARY KEY REFERENCES source_items(id) ON DELETE CASCADE,
                state TEXT NOT NULL CHECK (state IN ('read','skip')),
                updated_at TEXT NOT NULL
            )"""
        )


def first_sentence(content: str, limit: int = 240) -> str:
    text = _ARXIV_HEAD.sub("", content or "").strip()
    text = re.sub(r"\s+", " ", text)
    m = re.search(r"(.+?[.!?。！？])(\s|$)", text)
    s = m.group(1) if m else text
    return s if len(s) <= limit else s[:limit].rstrip() + "…"


def _week_start(iso: str) -> str:
    try:
        d = datetime.fromisoformat(iso.replace("Z", "+00:00")).date()
    except ValueError:
        return iso[:10]
    return (d - timedelta(days=d.weekday())).isoformat()


def reading_list() -> dict[str, Any]:
    ensure_table()
    with db() as conn:
        rows = conn.execute(
            """SELECT s.id, s.title, s.url, s.content, s.published_at, s.collected_at,
                      l.domain, l.role, l.name, r.state, r.updated_at AS state_at
               FROM lit_index l
               JOIN source_items s ON s.id = l.source_item_id
               LEFT JOIN reading_status r ON r.source_item_id = s.id
               WHERE l.role IN ('benchmark','demand') AND s.source_id LIKE 'arxiv%'
                 AND s.source_id NOT LIKE 'arxiv-backfill%'  -- 回补的旧论文只进综述，不算本周新收
               ORDER BY s.collected_at DESC, s.id DESC"""
        ).fetchall()
    from radar.core.lit_index import _other_domain
    items = []
    for r in rows:
        dom = r["domain"] if r["domain"] in DOMAIN_CN else "unclassified"
        items.append({
            "id": r["id"],
            "title": r["title"],
            "name": r["name"],
            "url": r["url"],
            "lead": first_sentence(r["content"]),
            "domain": dom,
            # 六个领域之外的论文再细分一层（视觉、机器人……），方便整组标为不用读
            # 规则兜底返回"通用"，和领域里的"通用"重名，这里改叫"杂项"
            "sub": (_other_domain(r["title"], (r["content"] or "")[:600]).replace("通用", "杂项")
                    if dom == "unclassified" else ""),
            "kind": "Benchmark" if r["role"] == "benchmark" else "相关论文",
            "collected_at": r["collected_at"],
            "week": _week_start(r["collected_at"]),
            "state": r["state"] or "unread",
            "state_at": r["state_at"],
        })
    weeks = sorted({x["week"] for x in items}, reverse=True)
    this_week = _week_start(datetime.now(timezone.utc).isoformat())
    return {
        "items": items,
        "weeks": weeks,
        "latest_week": weeks[0] if weeks else this_week,
        "domains": [{"domain": d, "label": DOMAIN_CN[d]} for d in DOMAIN_ORDER],
    }


def set_state(source_item_id: int, state: str) -> dict[str, Any]:
    if state not in STATES:
        raise ValueError(f"state 只能是 {', '.join(STATES)}")
    ensure_table()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with db() as conn:
        if not conn.execute("SELECT 1 FROM source_items WHERE id=?", (source_item_id,)).fetchone():
            raise KeyError(source_item_id)
        if state == "unread":
            conn.execute("DELETE FROM reading_status WHERE source_item_id=?", (source_item_id,))
        else:
            conn.execute(
                "INSERT INTO reading_status(source_item_id,state,updated_at) VALUES(?,?,?) "
                "ON CONFLICT(source_item_id) DO UPDATE SET state=excluded.state, updated_at=excluded.updated_at",
                (source_item_id, state, now),
            )
    return {"id": source_item_id, "state": state, "state_at": None if state == "unread" else now}


def set_state_many(ids: list[int], state: str) -> dict[str, Any]:
    if state not in STATES:
        raise ValueError(f"state 只能是 {', '.join(STATES)}")
    ids = [int(i) for i in ids]
    ensure_table()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with db() as conn:
        if state == "unread":
            conn.executemany("DELETE FROM reading_status WHERE source_item_id=?", [(i,) for i in ids])
        else:
            conn.executemany(
                "INSERT INTO reading_status(source_item_id,state,updated_at) VALUES(?,?,?) "
                "ON CONFLICT(source_item_id) DO UPDATE SET state=excluded.state, updated_at=excluded.updated_at",
                [(i, state, now) for i in ids],
            )
    return {"updated": len(ids), "state": state}

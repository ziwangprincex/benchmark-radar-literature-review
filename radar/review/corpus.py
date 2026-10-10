"""资料：某个领域里要写进综述的论文（标题 + 摘要）。

口径和待读清单一致：lit_index 里判为 Benchmark / 相关论文的 arXiv 条目，
去掉你在待读清单里标为"不用读"的。核对原话用的也是这里截好的摘要，和发给模型的完全一样。

两种范围：
  all   该领域收进来的全部论文，含补的历史论文
  week  最近一周新收的论文（和待读清单的"本周新进"同一口径：按收进来的那一周算，
        补的历史论文不算本周）
"""
from __future__ import annotations

import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any

from radar.core.lit_index import KIND_CN
from radar.core.radar_core import db
from radar.core.reading import DOMAIN_CN, _ARXIV_HEAD, _week_start, ensure_table

ABSTRACT_LIMIT = 1500
REVIEW_DOMAINS = ("legal", "financial", "medical", "scientific", "agent", "coding", "general")
SCOPES = ("all", "week")


def clean_abstract(content: str, limit: int = ABSTRACT_LIMIT) -> str:
    text = _ARXIV_HEAD.sub("", content or "").strip()
    text = re.sub(r"\s+", " ", text)
    if len(text) > limit:
        cut = text[:limit]
        # 截在句末，避免半句话被当成原话
        end = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
        text = cut[: end + 1] if end > limit * 0.6 else cut
    return text


def _date(*values: str | None) -> str:
    # published_at 有 RSS 格式（Wed, 23 Sep 2026 ...）也有 ISO 格式，统一成 YYYY-MM-DD
    for s in values:
        if not s:
            continue
        try:
            return parsedate_to_datetime(s).date().isoformat()
        except (TypeError, ValueError, IndexError):
            pass
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            pass
    return ""


_BASE_SQL = """FROM lit_index l
               JOIN source_items s ON s.id = l.source_item_id
               LEFT JOIN reading_status r ON r.source_item_id = s.id
               WHERE l.role IN ('benchmark','demand') AND s.source_id LIKE 'arxiv%' AND l.domain = ?"""


def latest_week() -> str:
    """最近一周（周一的日期）。和待读清单一样，只看每周抓进来的论文，不看补的历史论文。"""
    with db() as conn:
        row = conn.execute(
            "SELECT MAX(collected_at) FROM source_items WHERE source_id LIKE 'arxiv%' "
            "AND source_id NOT LIKE 'arxiv-backfill%'").fetchone()
    return _week_start(row[0]) if row and row[0] else ""


def load_corpus(domain: str, limit: int | None = None, scope: str = "all") -> list[dict[str, Any]]:
    if domain not in DOMAIN_CN:
        raise ValueError(f"未知领域：{domain}")
    if scope not in SCOPES:
        raise ValueError(f"范围只能是 {'、'.join(SCOPES)}")
    ensure_table()
    with db() as conn:
        rows = conn.execute(
            f"""SELECT s.id, s.title, s.url, s.content, s.published_at, s.collected_at, s.source_id, l.role, l.kind AS tag
                {_BASE_SQL} AND COALESCE(r.state, 'unread') != 'skip'
                ORDER BY s.collected_at DESC, s.id DESC""",
            (domain,),
        ).fetchall()
    if scope == "week":
        wk = latest_week()
        rows = [r for r in rows if not r["source_id"].startswith("arxiv-backfill")
                and _week_start(r["collected_at"]) == wk]
    papers = [{
        "id": r["id"],
        "title": re.sub(r"\s+", " ", r["title"] or "").strip(),
        "url": r["url"],
        "kind": KIND_CN.get(r["tag"], "新 Benchmark") if r["role"] == "benchmark" else "相关论文",
        "date": _date(r["published_at"], r["collected_at"]),
        "abstract": clean_abstract(r["content"]),
    } for r in rows]
    return papers[:limit] if limit else papers


def skipped_count(domain: str) -> int:
    ensure_table()
    with db() as conn:
        return conn.execute(f"SELECT COUNT(*) {_BASE_SQL} AND r.state = 'skip'", (domain,)).fetchone()[0]


def corpus_text(papers: list[dict[str, Any]]) -> str:
    return "\n\n".join(
        f"#{p['id']}｜{p['date']}\n标题：{p['title']}\n摘要：{p['abstract']}" for p in papers
    )

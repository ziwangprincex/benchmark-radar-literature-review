from __future__ import annotations

import html
import json
import re
from typing import Any

import requests

from radar.evidence.evidence_quality import sync_idea_quality
from radar.core.radar_core import (
    canonicalize_url,
    extract_pending,
    generate_ideas,
    insert_source_item,
    jaccard,
    normalize,
    now_iso,
    tokens,
)


def meta_values(page: str, name: str) -> list[str]:
    values = []
    for tag in re.findall(r"<meta\b[^>]*>", page, re.I):
        attrs = {}
        for match in re.finditer(r"([:\w-]+)\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+))", tag):
            attrs[match.group(1).lower()] = html.unescape(next(x for x in match.groups()[1:] if x is not None)).strip()
        if attrs.get("name", "").lower() == name.lower() or attrs.get("property", "").lower() == name.lower():
            if attrs.get("content"):
                values.append(attrs["content"])
    return list(dict.fromkeys(values))


def verify_result(result: dict[str, Any]) -> dict[str, Any]:
    output = dict(result)
    try:
        response = requests.get(result["url"], headers={"User-Agent": "BenchmarkIdeaRadar/1.0"}, timeout=25)
        response.raise_for_status()
        page = response.text[:2_000_000]
        title = (meta_values(page, "citation_title") or meta_values(page, "og:title") or [result["title"]])[0]
        authors = meta_values(page, "citation_author") or result.get("authors") or []
        published = (meta_values(page, "citation_publication_date") or meta_values(page, "article:published_time") or [result.get("published_at")])[0]
        excerpt = (meta_values(page, "citation_abstract") or meta_values(page, "description") or meta_values(page, "og:description") or [result.get("content") or title])[0]
        locator = dict(result.get("locator") or {})
        locator.update({
            "section": locator.get("section") or "page metadata / abstract",
            "first_page": (meta_values(page, "citation_firstpage") or [None])[0],
            "last_page": (meta_values(page, "citation_lastpage") or [None])[0],
            "doi": (meta_values(page, "citation_doi") or [None])[0],
            "pdf_url": (meta_values(page, "citation_pdf_url") or [None])[0],
            "conference": (meta_values(page, "citation_conference_title") or [None])[0],
        })
        title_match = jaccard(result["title"], title)
        # 摘要是否与标题相关：看标题词有多少出现在摘要里（覆盖率），不用 jaccard。
        # jaccard 的分母含摘要全部词，摘要越长分越低：FinanceBench、CLAUSE 等
        # 标题完全一致、摘要正常的论文曾因 1,000+ 字摘要得 0.04 被判 metadata_mismatch。
        title_tokens = tokens(result["title"])
        excerpt_coverage = len(title_tokens & tokens(excerpt)) / len(title_tokens) if title_tokens else 0.0
        excerpt_match = jaccard(result["title"], excerpt)
        # 标题词直接出现在摘要里也算相关。单词标题 + 跨语言正文时覆盖率为 0：
        # MedBench 的标题只有一个英文词、正文是中文简介，实际内容有效。
        name_in_excerpt = normalize(result["title"]) in normalize(excerpt)
        # 三者任一成立即可：覆盖率修的是长摘要，jaccard 保留原本对短摘要的放行。
        validation = (
            "verified_source"
            if title_match >= 0.25 and (excerpt_coverage >= 0.2 or excerpt_match >= 0.05 or name_in_excerpt)
            else "metadata_mismatch"
        )
        output.update({
            "title": title, "content": excerpt, "authors": authors, "published_at": published,
            "retrieved_at": now_iso(), "last_verified_at": now_iso(), "http_status": response.status_code,
            "validation_status": validation, "source_version": result.get("source_version") or published,
            "locator": {k: v for k, v in locator.items() if v},
            "verification_error": None if validation == "verified_source" else f"Expected title '{result['title']}', fetched '{title}'",
        })
    except Exception as exc:
        output.update({"validation_status": "unverified", "verification_error": str(exc), "retrieved_at": now_iso()})
    return output


def import_retrieved_results(
    idea_id: int,
    claim_type: str,
    query: str,
    results: list[dict[str, Any]],
    retriever_version: str = "external-search-v1",
) -> dict[str, Any]:
    from radar.core.radar_core import db, now_iso

    sync_idea_quality(idea_id)
    with db() as conn:
        claim = conn.execute("SELECT id FROM idea_claims WHERE idea_id=? AND claim_type=?", (idea_id, claim_type)).fetchone()
        if not claim:
            raise ValueError(f"claim not found: {claim_type}")
        cursor = conn.execute(
            "INSERT INTO retrieval_runs(idea_id,claim_id,radar,retrieval_query,retrieved_at,retriever_version,result_count,status) VALUES(?,?,?,?,?,?,?,?)",
            (idea_id, claim["id"], results[0].get("radar", "benchmark") if results else "benchmark", query, now_iso(), retriever_version, len(results), "completed"),
        )
        run_id = cursor.lastrowid
    selected = rejected = 0
    selected_source_ids = []
    for rank, result in enumerate(results, 1):
        use = bool(result.get("selected"))
        source_item_id = None
        if use:
            verified = verify_result(result)
            source_item_id, _ = insert_source_item({
                "radar": verified.get("radar", "benchmark"),
                "source_id": verified.get("source_id", "external-search"),
                "title": verified["title"], "content": verified.get("content") or verified["title"],
                "url": verified["url"], "published_at": verified.get("published_at"),
                "source_type": verified.get("source_type", "paper"),
                "source_quality": verified.get("source_quality", "primary"),
                "organization": verified.get("organization"), "authors": verified.get("authors"),
                "source_version": verified.get("source_version"), "locator": verified.get("locator") or {},
                "retrieved_at": verified.get("retrieved_at"), "last_verified_at": verified.get("last_verified_at"),
                "http_status": verified.get("http_status"), "validation_status": verified.get("validation_status"),
                "provenance": {"retrieval_run_id": run_id, "retrieval_query": query, "verification_error": verified.get("verification_error")},
            })
            if source_item_id is None:
                with db() as conn:
                    canonical = canonicalize_url(verified["url"])
                    row = conn.execute("SELECT id FROM source_items WHERE canonical_url=? OR url=? ORDER BY id LIMIT 1", (canonical, verified["url"])).fetchone()
                    source_item_id = row["id"] if row else None
                    if source_item_id:
                        conn.execute(
                            """UPDATE source_items SET content=?,published_at=COALESCE(?,published_at),retrieved_at=?,
                            last_verified_at=COALESCE(?,last_verified_at),source_version=COALESCE(?,source_version),
                            locator_json=?,provenance_json=?,http_status=?,validation_status=? WHERE id=?""",
                            (verified.get("content"), verified.get("published_at"), verified.get("retrieved_at"), verified.get("last_verified_at"),
                             verified.get("source_version"), json.dumps(verified.get("locator") or {}, ensure_ascii=False),
                             json.dumps({"retrieval_run_id": run_id, "retrieval_query": query, "authors": verified.get("authors"), "organization": verified.get("organization")}, ensure_ascii=False),
                             verified.get("http_status"), verified.get("validation_status"), source_item_id),
                        )
            if source_item_id:
                selected_source_ids.append(source_item_id)
            selected += 1
        else:
            rejected += 1
        with db() as conn:
            conn.execute(
                "INSERT INTO retrieval_results(retrieval_run_id,source_item_id,title,url,source_quality,selected,rejection_reason,rank,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (run_id, source_item_id, result["title"], result["url"], result.get("source_quality", "secondary"), int(use), result.get("selection_reason") if use else result.get("rejection_reason"), rank, now_iso()),
            )
    extract_pending()
    generate_ideas()
    with db() as conn:
        for source_item_id in selected_source_ids:
            signal = conn.execute("SELECT id FROM signals WHERE source_item_id=?", (source_item_id,)).fetchone()
            if signal:
                conn.execute("INSERT OR IGNORE INTO idea_signal_links(idea_id,signal_id) VALUES(?,?)", (idea_id, signal["id"]))
    quality = sync_idea_quality(idea_id)
    return {"retrieval_run_id": run_id, "retrieved": len(results), "selected": selected, "rejected": rejected, "evidence_quality": quality}

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import feedparser
import requests

from radar.evidence.evidence_quality import canonical_url
from radar.core.radar_core import db, get_idea, insert_source_item, now_iso

ARXIV = "https://export.arxiv.org/api/query"
SEMANTIC_SCHOLAR = "https://api.semanticscholar.org/graph/v1/paper/search"
CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "retrieval_cache"
CACHE_TTL_DAYS = 7


def queries_for_claim(idea: dict[str, Any], claim: dict[str, Any]) -> list[str]:
    capabilities = " ".join(idea.get("capability", [])[:3])
    base = f"{idea['idea_name']} {capabilities}".strip()
    if claim["claim_type"] == "evaluation_gap":
        return [f'{base} benchmark evaluation dataset', f'{base} task definition protocol']
    if claim["claim_type"] == "why_now":
        return [f'{base} product release documentation agent']
    if claim["claim_type"] == "model_failure":
        return [f'{base} model evaluation error analysis benchmark']
    return [f'{base} professional workflow study']


def cache_path(query: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{hashlib.sha256(query.encode('utf-8')).hexdigest()}.json"


def read_cache(query: str) -> dict[str, Any] | None:
    path = cache_path(query)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    created = datetime.fromisoformat(data["created_at"])
    if datetime.now(timezone.utc) - created > timedelta(days=CACHE_TTL_DAYS):
        return None
    return data


def write_cache(query: str, results: list[dict[str, Any]], retriever: str) -> None:
    cache_path(query).write_text(json.dumps({"query": query, "results": results, "retriever": retriever, "created_at": datetime.now(timezone.utc).isoformat()}, ensure_ascii=False, indent=2), encoding="utf-8")


def get_with_backoff(url: str, *, params=None, headers=None, attempts: int = 3):
    last = None
    for attempt in range(attempts):
        response = requests.get(url, params=params, headers=headers, timeout=20)
        if response.status_code not in {429, 500, 502, 503, 504}:
            response.raise_for_status()
            return response
        last = RuntimeError(f"HTTP {response.status_code}: {response.text[:200]}")
        wait = min(float(response.headers.get("Retry-After", 0) or 0), 5) or (2 ** attempt)
        time.sleep(wait)
    raise last or RuntimeError("retrieval request failed")


def arxiv_search(query: str, max_results: int = 8) -> list[dict[str, Any]]:
    params = {"search_query": f'all:"{query}"', "start": 0, "max_results": max_results, "sortBy": "relevance"}
    response = get_with_backoff(ARXIV, params=params, headers={"User-Agent": "BenchmarkIdeaRadar/1.0 evidence-retrieval"})
    feed = feedparser.parse(response.content)
    return [{
        "title": entry.get("title", ""), "url": entry.get("link", ""),
        "published_at": entry.get("published"), "content": entry.get("summary", ""),
        "authors": [x.get("name") for x in entry.get("authors", [])],
        "rank": rank, "source_type": "paper", "source_quality": "primary",
        "organization": "arXiv", "source_version": entry.get("updated") or entry.get("published"),
    } for rank, entry in enumerate(feed.entries, 1)]


def semantic_scholar_search(query: str, max_results: int = 8) -> list[dict[str, Any]]:
    response = get_with_backoff(
        SEMANTIC_SCHOLAR,
        params={"query": query, "limit": max_results, "fields": "title,abstract,url,authors,year,publicationDate,externalIds"},
        headers={"User-Agent": "BenchmarkIdeaRadar/1.0"},
    )
    results = []
    for rank, paper in enumerate(response.json().get("data", []), 1):
        external = paper.get("externalIds") or {}
        url = f"https://arxiv.org/abs/{external['ArXiv']}" if external.get("ArXiv") else paper.get("url")
        results.append({
            "title": paper.get("title", ""), "url": url or "", "published_at": paper.get("publicationDate") or paper.get("year"),
            "content": paper.get("abstract") or paper.get("title", ""), "authors": [x.get("name") for x in paper.get("authors", [])],
            "rank": rank, "source_type": "paper", "source_quality": "primary", "organization": "Semantic Scholar index",
            "source_version": paper.get("publicationDate") or str(paper.get("year") or ""),
        })
    return results


def search_real_sources(query: str, max_results: int = 8) -> tuple[list[dict[str, Any]], str]:
    cached = read_cache(query)
    if cached:
        return cached["results"], f"cache:{cached['retriever']}"
    errors = []
    for retriever, fn in [("arxiv-api-v1", arxiv_search), ("semantic-scholar-v1", semantic_scholar_search)]:
        try:
            results = fn(query, max_results)
            write_cache(query, results, retriever)
            return results, retriever
        except Exception as exc:
            errors.append({"retriever": retriever, "error_type": type(exc).__name__, "error": str(exc)})
    raise RuntimeError(json.dumps({"kind": "retrieval_failed", "attempts": errors}, ensure_ascii=False))


def select_result(idea: dict[str, Any], claim: dict[str, Any], result: dict[str, Any]) -> tuple[bool, str]:
    text = f"{result['title']} {result['content']}".lower()
    tokens = [x.lower().replace("_", " ") for x in idea.get("capability", [])]
    matches = sum(1 for x in tokens if x and x in text)
    if matches == 0:
        return False, "Irrelevant: no target capability match"
    if claim["claim_type"] == "evaluation_gap" and not any(x in text for x in ["benchmark", "dataset", "evaluation", "task"]):
        return False, "Does not describe benchmark scope or protocol"
    return True, "Selected by capability and claim-type relevance"


def run_retrieval(idea_id: int, claim_types: set[str] | None = None) -> dict[str, Any]:
    idea = get_idea(idea_id)
    if not idea:
        raise KeyError(idea_id)
    from radar.evidence.evidence_quality import sync_idea_quality
    sync_idea_quality(idea_id)
    with db() as conn:
        claims = [dict(x) for x in conn.execute("SELECT * FROM idea_claims WHERE idea_id=?", (idea_id,)).fetchall()]
    stats = {"queries": 0, "retrieved": 0, "selected": 0, "rejected": 0, "errors": []}
    selected_source_ids = []
    for claim in claims:
        if claim_types and claim["claim_type"] not in claim_types:
            continue
        radar = {"evaluation_gap": "benchmark", "why_now": "product_agent", "model_failure": "model_failure", "core_insight": "workflow"}[claim["claim_type"]]
        retrieval_quality = "primary" if claim["claim_type"] in {"evaluation_gap", "model_failure"} else "secondary"
        for query in queries_for_claim(idea, claim):
            stats["queries"] += 1
            run_at = now_iso()
            with db() as conn:
                cursor = conn.execute(
                    """INSERT INTO retrieval_runs
                    (idea_id,claim_id,radar,retrieval_query,retrieved_at,retriever_version,status,query_normalized)
                    VALUES(?,?,?,?,?,?,?,?)""",
                    (idea_id, claim["id"], radar, query, run_at, "multi-source-v1", "running", " ".join(query.lower().split())),
                )
                run_id = cursor.lastrowid
            try:
                results, retriever_version = search_real_sources(query)
                with db() as conn:
                    conn.execute("UPDATE retrieval_runs SET retriever_version=? WHERE id=?", (retriever_version, run_id))
            except Exception as exc:
                error = {"error_type": type(exc).__name__, "error_message": str(exc), "query": query}
                with db() as conn:
                    conn.execute(
                        "UPDATE retrieval_runs SET status=?,completed_at=?,retry_count=?,error_json=? WHERE id=?",
                        ("failed", now_iso(), 3, json.dumps(error, ensure_ascii=False), run_id),
                    )
                stats["errors"].append({"query": query, "error": str(exc)})
                continue
            stats["retrieved"] += len(results)
            selected_count = 0
            with db() as conn:
                for result in results:
                    selected, reason = select_result(idea, claim, result)
                    source_item_id = None
                    if selected:
                        source_item_id, state = insert_source_item({
                            "radar": radar, "source_id": "evidence-retrieval-arxiv",
                            "title": result["title"], "content": result["content"], "url": result["url"],
                            "published_at": result["published_at"], "retrieved_at": run_at,
                            "last_verified_at": run_at, "http_status": 200,
                            "source_type": result["source_type"], "source_quality": retrieval_quality,
                            "authors": result["authors"], "organization": result["organization"],
                            "source_version": result["source_version"],
                            "provenance": {"retrieval_run_id": run_id, "retrieval_query": query},
                        })
                        if source_item_id is None:
                            canonical = canonical_url(result["url"])
                            row = conn.execute("SELECT id FROM source_items WHERE url=? OR url LIKE ? LIMIT 1", (result["url"], canonical + "%")).fetchone()
                            source_item_id = row["id"] if row else None
                        if source_item_id:
                            selected_source_ids.append(source_item_id)
                        selected_count += 1
                        stats["selected"] += 1
                    else:
                        stats["rejected"] += 1
                    conn.execute(
                        """INSERT INTO retrieval_results(retrieval_run_id,source_item_id,title,url,source_quality,selected,rejection_reason,rank,created_at)
                        VALUES(?,?,?,?,?,?,?,?,?)""",
                        (run_id, source_item_id, result["title"], result["url"], retrieval_quality, int(selected), None if selected else reason, result["rank"], now_iso()),
                    )
                final_status = "completed" if results else "completed_no_results"
                conn.execute(
                    "UPDATE retrieval_runs SET result_count=?,status=?,completed_at=?,retry_count=?,error_json=? WHERE id=?",
                    (len(results), final_status, now_iso(), 0, "{}", run_id),
                )
    from radar.core.radar_core import extract_pending, generate_ideas
    from radar.evidence.evidence_quality import sync_idea_quality
    extract_pending()
    generate_ideas()
    with db() as conn:
        for source_item_id in selected_source_ids:
            signal = conn.execute("SELECT id FROM signals WHERE source_item_id=?", (source_item_id,)).fetchone()
            if signal:
                conn.execute("INSERT OR IGNORE INTO idea_signal_links(idea_id,signal_id) VALUES(?,?)", (idea_id, signal["id"]))
    sync_idea_quality(idea_id)
    return stats


def retrieve_needs_verification(limit: int = 3) -> dict[str, Any]:
    from radar.evidence.evidence_quality import claim_quality_summary, sync_all_idea_quality
    from radar.core.radar_core import list_ideas
    sync_all_idea_quality()
    candidates = []
    for idea in list_ideas():
        quality = claim_quality_summary(idea["id"])
        if idea["total_score"] >= 65 and quality["needs_verification"]:
            candidates.append((idea, set(quality["missing_evidence"])))
    output = []
    for idea, missing in candidates[:limit]:
        output.append({"idea_id": idea["id"], "result": run_retrieval(idea["id"], missing)})
    return {"candidates": len(candidates), "processed": len(output), "results": output}


def retrieval_log(idea_id: int) -> list[dict[str, Any]]:
    with db() as conn:
        runs = []
        for row in conn.execute("SELECT * FROM retrieval_runs WHERE idea_id=? ORDER BY id DESC", (idea_id,)).fetchall():
            item = dict(row)
            item["error"] = json.loads(item.pop("error_json") or "{}")
            item["results"] = [dict(x) for x in conn.execute("SELECT * FROM retrieval_results WHERE retrieval_run_id=? ORDER BY rank", (row["id"],)).fetchall()]
            runs.append(item)
        return runs

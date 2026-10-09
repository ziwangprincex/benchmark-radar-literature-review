"""从 arXiv 公开接口批量补充 Benchmark 论文（免费、无需 key）。

用法:
  python3 scripts/sweep_arxiv_benchmarks.py [总条数，默认 1000]             抓取并直接入库
  python3 scripts/sweep_arxiv_benchmarks.py 600 --dump new_papers.jsonl   只抓取，存成文件，不碰数据库
  python3 scripts/sweep_arxiv_benchmarks.py --load new_papers.jsonl       从文件入库，不联网

只取标题里带 benchmark / dataset / evaluation suite 等词的论文，按提交时间倒序。
入库走 insert_source_item，重复的会自动跳过。
--dump / --load 用于服务器上不了外网的情况：能上外网的机器抓，服务器导入。
"""
import json
import sys
import time
from pathlib import Path

import feedparser
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

API = "https://export.arxiv.org/api/query"
CATS = "(cat:cs.CL OR cat:cs.AI OR cat:cs.LG OR cat:cs.CV OR cat:cs.IR OR cat:cs.SE OR cat:cs.RO OR cat:cs.MA OR cat:cs.CR OR cat:cs.HC)"
TITLE = '(ti:benchmark OR ti:benchmarking OR ti:dataset OR ti:"test suite" OR ti:"evaluation suite" OR ti:leaderboard)'
PAGE = 200


def _entry_to_raw(e) -> dict:
    return {"title": e.get("title", ""), "summary": e.get("summary", ""), "link": e.get("link", ""),
            "published": e.get("published"), "updated": e.get("updated"),
            "authors": [a.get("name") for a in e.get("authors", []) if a.get("name")]}


def _raw_to_item(raw: dict, now: str) -> dict:
    return {
        "radar": "benchmark", "source_id": "arxiv-benchmark-sweep",
        "title": raw.get("title", ""), "content": raw.get("summary", ""),
        "url": raw.get("link", ""), "published_at": raw.get("published"),
        "retrieved_at": now, "last_verified_at": now, "http_status": 200,
        "source_quality": "primary", "source_type": "paper", "organization": "arXiv",
        "source_version": raw.get("updated") or raw.get("published"),
        "authors": raw.get("authors") or [],
        "locator": {"feed_source": API}, "tags": ["benchmark-sweep"],
    }


def _fetch_page(start: int, size: int):
    headers = {"User-Agent": "BenchmarkIdeaRadar/1.0 (local research tool)"}
    params = {"search_query": f"{TITLE} AND {CATS}", "start": start, "max_results": size,
              "sortBy": "submittedDate", "sortOrder": "descending"}
    for attempt in range(6):
        try:
            r = requests.get(API, params=params, headers=headers, timeout=60)
            if r.status_code == 429:
                # arXiv 限流：短间隔重试只会继续被拒，按 Retry-After 或 60/120/180… 秒退避
                wait = int(r.headers.get("Retry-After") or 60 * (attempt + 1))
                print(f"429 at {start}, wait {wait}s", flush=True)
                time.sleep(wait)
                continue
            r.raise_for_status()
            feed = feedparser.parse(r.content)
            if feed.entries:
                return feed.entries
        except Exception as exc:  # noqa: BLE001
            print("retry", start, exc, flush=True)
        time.sleep(5 * (attempt + 1))
    return None


def dump(total: int, path: Path) -> None:
    """只抓取，不入库。增量判断要查库，这里做不到，所以固定抓 total 条，重复的交给导入时去重。"""
    rows = []
    for start in range(0, total, PAGE):
        entries = _fetch_page(start, min(PAGE, total - start))
        if entries is None:
            print("give up at", start, flush=True)
            break
        rows += [_entry_to_raw(e) for e in entries]
        print(f"page {start // PAGE + 1}: {len(rows)}", flush=True)
        time.sleep(3.5)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print("done", {"fetched": len(rows), "file": str(path)}, flush=True)
    if not rows:
        sys.exit(2)


def load(path: Path) -> None:
    from radar.core.radar_core import insert_source_item, now_iso, init_db
    init_db()
    stats = {"fetched": 0, "inserted": 0, "duplicate": 0, "clustered_duplicate": 0, "invalid": 0}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        stats["fetched"] += 1
        try:
            _, state = insert_source_item(_raw_to_item(json.loads(line), now_iso()))
            stats[state] = stats.get(state, 0) + 1
        except ValueError:
            stats["invalid"] += 1
    print("done", stats, flush=True)
    if stats["fetched"] == 0:
        sys.exit(2)


def main(total: int) -> None:
    from radar.core.radar_core import insert_source_item, now_iso, init_db
    init_db()
    stats = {"fetched": 0, "inserted": 0, "duplicate": 0, "clustered_duplicate": 0, "invalid": 0}
    for start in range(0, total, PAGE):
        entries = _fetch_page(start, min(PAGE, total - start))
        if entries is None:
            print("give up at", start, flush=True)
            stats["gave_up_at"] = start
            break
        for e in entries:
            stats["fetched"] += 1
            try:
                _, state = insert_source_item(_raw_to_item(_entry_to_raw(e), now_iso()))
                stats[state] = stats.get(state, 0) + 1
            except ValueError:
                stats["invalid"] += 1
        print(f"page {start // PAGE + 1}: {stats}", flush=True)
        # 增量刷新：整页都是已入库的论文，说明已经接上上次的进度，不必再往前翻
        if stats.get("inserted", 0) == 0 and stats["fetched"] >= PAGE and stats.get("duplicate", 0) + stats.get("clustered_duplicate", 0) >= stats["fetched"]:
            print("caught up with previous sweep", flush=True)
            break
        time.sleep(3.5)
    print("done", stats, flush=True)
    if stats["fetched"] == 0:
        sys.exit(2)


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--load" in args:
        load(Path(args[args.index("--load") + 1]))
    else:
        nums = [a for a in args if a.isdigit()]
        n = int(nums[0]) if nums else 1000
        if "--dump" in args:
            dump(n, Path(args[args.index("--dump") + 1]))
        else:
            main(n)

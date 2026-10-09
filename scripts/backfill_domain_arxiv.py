"""按领域回补 arXiv 历史论文，给文献综述的"该领域全部"补底稿（免费、无需 key）。

每周扫描（sweep_arxiv_benchmarks.py）只按时间倒序取最新的论文，库里只有最近两个月。
这个脚本按领域写检索词，按年份分段往回查，补齐以前的 Benchmark / 评测论文。

用法:
  python3 scripts/backfill_domain_arxiv.py legal                 抓取并入库（默认 2023 年起）
  python3 scripts/backfill_domain_arxiv.py legal --since 2024
  python3 scripts/backfill_domain_arxiv.py legal --count         只看每年命中多少篇，不入库
  python3 scripts/backfill_domain_arxiv.py legal --dump f.jsonl  只抓取存文件；--load f.jsonl 从文件入库
  python3 scripts/backfill_domain_arxiv.py legal --load data/backfill/legal.jsonl.gz   用仓库里存好的回补导入（不联网）

已回补的论文存在 data/backfill/<领域>.jsonl.gz（2026-10-09：法律、编程、金融、医疗，2023 年起）。
数据库 data/radar.db 不进 git（回补后超过 100MB），新机器用这些文件导入即可。

回补的论文 source_id 为 arxiv-backfill-<领域>：进文献综述，不进待读清单和企业微信推送
（它们是旧论文，不是"本周新收"）。入库后还要重建分类和索引，脚本会自动做。
是不是法律论文最终由 detect_domain 判，检索词只负责把候选捞进来，宁宽勿漏。
"""
import gzip
import json
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

import feedparser
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

API = "https://export.arxiv.org/api/query"
PAGE = 200
CATS = "(cat:cs.CL OR cat:cs.AI OR cat:cs.LG OR cat:cs.IR OR cat:cs.CY OR cat:cs.CV OR cat:cs.MA OR cat:cs.HC OR cat:cs.SE OR cat:cs.PL)"
# 论文得像在做 Benchmark / 评测；摘要里带 benchmark 的方法论文也会进来，之后由 lit_index 判掉
BENCH = ('(ti:benchmark OR ti:benchmarking OR ti:dataset OR ti:evaluation OR ti:evaluating '
         'OR abs:"we introduce" OR abs:"we present" OR abs:benchmark)')

DOMAIN_QUERIES = {
    "legal": ('(ti:legal OR ti:law OR ti:lawyer OR ti:court OR ti:judicial OR ti:judgment '
              'OR ti:statute OR ti:legislation OR abs:"legal reasoning" OR abs:"legal domain" '
              'OR abs:"legal documents" OR abs:"legal tasks" OR abs:"legal question" '
              'OR abs:"legal judgment")'),
    "coding": ('(ti:code OR ti:coding OR ti:programming OR ti:software OR ti:repository OR ti:SQL '
               'OR ti:SWE OR abs:"code generation" OR abs:"software engineering" '
               'OR abs:"program repair" OR abs:"code completion" OR abs:"coding agent" '
               'OR abs:"GitHub issues" OR abs:"text-to-SQL")'),
    "financial": ('(ti:financial OR ti:finance OR ti:fintech OR ti:stock OR ti:trading OR ti:banking '
                  'OR ti:accounting OR ti:audit OR ti:insurance OR ti:earnings OR ti:investment '
                  'OR abs:"financial reports" OR abs:"financial question" OR abs:"financial domain" '
                  'OR abs:"financial analysis" OR abs:"10-K")'),
    # 医疗候选很多（影像分割、病理切片都算），只取和大模型 / 语言相关的，纯视觉模型论文太多
    "medical": ('(ti:medical OR ti:clinical OR ti:health OR ti:patient OR ti:biomedical OR ti:radiology '
                'OR ti:diagnosis OR ti:EHR OR ti:surgical OR ti:pathology OR ti:drug) '
                'AND (abs:LLM OR abs:LLMs OR abs:"language model" OR abs:"language models" '
                'OR abs:"vision-language" OR abs:multimodal OR abs:agent)'),
}


def _query(domain: str, year: int) -> str:
    return f"{DOMAIN_QUERIES[domain]} AND {BENCH} AND {CATS} AND submittedDate:[{year}01010000 TO {year}12312359]"


def _get(params: dict):
    headers = {"User-Agent": "BenchmarkIdeaRadar/1.0 (local research tool)"}
    for attempt in range(6):
        try:
            r = requests.get(API, params=params, headers=headers, timeout=60)
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After") or 60 * (attempt + 1))
                print(f"429, wait {wait}s", flush=True)
                time.sleep(wait)
                continue
            r.raise_for_status()
            return feedparser.parse(r.content)
        except Exception as exc:  # noqa: BLE001
            print("retry", exc, flush=True)
        time.sleep(5 * (attempt + 1))
    return None


def fetch(domain: str, since: int, count_only: bool = False) -> list[dict]:
    rows = []
    for year in range(since, datetime.now().year + 1):
        q = _query(domain, year)
        feed = _get({"search_query": q, "start": 0, "max_results": 1})
        total = int(feed.feed.get("opensearch_totalresults", 0)) if feed else 0
        print(f"{year}: {total} 篇", flush=True)
        time.sleep(3.5)
        if count_only or not total:
            continue
        for start in range(0, total, PAGE):
            page = _get({"search_query": q, "start": start, "max_results": PAGE,
                         "sortBy": "submittedDate", "sortOrder": "descending"})
            if page is None or not page.entries:
                print(f"  {year} 第 {start} 条起没拿到，跳过", flush=True)
                break
            rows += [{"title": e.get("title", ""), "summary": e.get("summary", ""), "link": e.get("link", ""),
                      "published": e.get("published"), "updated": e.get("updated"),
                      "authors": [a.get("name") for a in e.get("authors", []) if a.get("name")]}
                     for e in page.entries]
            time.sleep(3.5)
    return rows


def load(domain: str, rows: list[dict]) -> dict:
    from radar.core.radar_core import init_db, insert_source_item, now_iso
    init_db()
    stats = {"fetched": 0, "inserted": 0, "duplicate": 0, "invalid": 0}
    for raw in rows:
        stats["fetched"] += 1
        now = now_iso()
        item = {
            "radar": "benchmark", "source_id": f"arxiv-backfill-{domain}",
            "title": raw.get("title", ""), "content": raw.get("summary", ""),
            "url": raw.get("link", ""), "published_at": raw.get("published"),
            "retrieved_at": now, "last_verified_at": now, "http_status": 200,
            "source_quality": "primary", "source_type": "paper", "organization": "arXiv",
            "source_version": raw.get("updated") or raw.get("published"),
            "authors": raw.get("authors") or [],
            "locator": {"feed_source": API}, "tags": ["backfill", domain],
        }
        try:
            _, state = insert_source_item(item)
            stats[state] = stats.get(state, 0) + 1
        except ValueError:
            stats["invalid"] += 1
    return stats


def rebuild() -> None:
    from radar.core.radar_core import db, reclassify_stale_signals, run_pipeline
    run_pipeline(False)
    with db() as conn:
        reclassify_stale_signals(conn)
    from radar.core.lit_index import run
    run(ROOT)


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] not in DOMAIN_QUERIES:
        sys.exit(f"用法: backfill_domain_arxiv.py <{'|'.join(DOMAIN_QUERIES)}> [--since 年份] [--count] [--dump 文件] [--load 文件]")
    domain = args[0]
    since = int(args[args.index("--since") + 1]) if "--since" in args else 2023
    if "--load" in args:
        src = Path(args[args.index("--load") + 1])
        text = gzip.open(src, "rt", encoding="utf-8").read() if src.suffix == ".gz" else src.read_text(encoding="utf-8")
        rows = [json.loads(ln) for ln in text.splitlines() if ln.strip()]
    else:
        rows = fetch(domain, since, count_only="--count" in args)
        if "--count" in args:
            return
        if "--dump" in args:
            out = Path(args[args.index("--dump") + 1])
            out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
            print("done", {"fetched": len(rows), "file": str(out)})
            return
    backup = ROOT / "data" / "backups" / f"radar.db.before-backfill-{domain}-{datetime.now():%Y%m%d%H%M}"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "data" / "radar.db", backup)
    stats = load(domain, rows)
    rebuild()
    print("done", stats, {"backup": str(backup)}, flush=True)


if __name__ == "__main__":
    main()

"""Insight 页面发布的回归测试。

2026-09-24 之前 generate() 有三个问题：
1. 用 list_ideas() 取全部 Idea，superseded 的 19 个也照发，和周报口径不一致；
2. 只写不删，Idea 归档或证据移除后旧页面一直留在站点上（当时 237 个 idea-*
   页面全部属于 superseded Idea，里面还挂着 evaluation_gap 的 arXiv 原文）；
3. claim 证据和 raw source 溯源表会链接到未生成的页面，站内出现悬空链接。

跑：.venv/bin/python -m pytest tests/ -q   （系统 python3 缺 feedparser）
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from radar.core.radar_core import list_ideas, strip_feed_prefix  # noqa: E402


def test_strip_feed_prefix():
    raw = "arXiv:2609.25058v1 Announce Type: new Abstract: Parameter-efficient fine-tuning"
    assert strip_feed_prefix(raw) == "Parameter-efficient fine-tuning"
    assert strip_feed_prefix("普通文本不受影响") == "普通文本不受影响"
    assert strip_feed_prefix(None) == ""


def _generate_into(tmp: Path, seed: list[str] | None = None) -> dict:
    import radar.publish.insight_pages as ip

    for name in seed or []:
        (tmp / name).write_text("stale", encoding="utf-8")
    original = ip.OUTPUT_DIR
    ip.OUTPUT_DIR = tmp
    try:
        return ip.generate(base_url="https://example.test")
    finally:
        ip.OUTPUT_DIR = original


def test_prune_keeps_only_current_outputs():
    import radar.publish.insight_pages as ip

    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        (tmp / "attachments").mkdir()
        (tmp / "attachments" / "keep.pdf").write_text("x")
        (tmp / "notes.txt").write_text("x")
        for name in ["idea-999-old.html", "raw-source-999.html", "failure-case-999.html", "idea-1-keep.html"]:
            (tmp / name).write_text("x")
        original = ip.OUTPUT_DIR
        ip.OUTPUT_DIR = tmp
        try:
            removed = ip.prune_stale_outputs({"idea-1-keep.html"})
        finally:
            ip.OUTPUT_DIR = original
        assert removed == ["failure-case-999.html", "idea-999-old.html", "raw-source-999.html"]
        assert (tmp / "idea-1-keep.html").exists()
        assert (tmp / "attachments" / "keep.pdf").exists() and (tmp / "notes.txt").exists()


def test_generate_excludes_superseded_and_has_no_dangling_links():
    superseded = {x["id"] for x in list_ideas(status="superseded")}
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        stale = [f"idea-{i}-stale.html" for i in superseded]
        result = _generate_into(tmp, seed=stale)
        published = {x["idea_id"] for x in result["manifest"]}
        assert not (published & superseded), "superseded Idea 不应发布"
        assert not any((tmp / name).exists() for name in stale), "旧页面应被清理"

        files = {p.name for p in tmp.iterdir()}
        dangling = [
            (page, href)
            for page in files if page.endswith(".html")
            for href in re.findall(r'href="([^"#:]+?\.html)"', (tmp / page).read_text(encoding="utf-8"))
            if href not in files
        ]
        assert not dangling, f"站内悬空链接: {dangling[:5]}"


if __name__ == "__main__":
    test_strip_feed_prefix()
    test_prune_keeps_only_current_outputs()
    test_generate_excludes_superseded_and_has_no_dangling_links()
    print("ok")

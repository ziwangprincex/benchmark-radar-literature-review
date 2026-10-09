"""综述式缺口候选（lit_index）的回归测试，纯函数，不碰数据库。

跑：python3 -m pytest tests/ -q
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from radar.core.lit_index import analyze, build_candidates  # noqa: E402

PAD = " Filler sentence about the setup of the study and the data we release." * 5


def _entry(sid, role, domain, title, body, radar="benchmark"):
    a = analyze(radar, title, body + PAD)
    a.update(source_item_id=sid, domain=domain, url=f"https://x/{sid}", full_title=title)
    assert a["role"] == role, (title, a["role"])
    return a


def test_self_intro_not_gap():
    a = analyze("benchmark", "FooBench: a benchmark",
                "To address this gap, we introduce FooBench, a new benchmark." + PAD)
    assert all("address this gap" not in g["text"] for g in a["gap_sentences"])


def test_generic_risk_word_not_safety():
    a = analyze("benchmark", "X: dataset", "However, over-pruning risk remains open for this method." + PAD)
    assert "安全/风险" not in a["concerns"]


def test_overlapping_concerns_merge_into_one_card():
    body = "However, existing benchmarks rarely test long-horizon tasks and judge agreement with success is low."
    es = [_entry(1, "benchmark", "agent", "GaugeBench: a benchmark", body),
          _entry(2, "benchmark", "agent", "OtherBench: a benchmark", body)]
    cards = [c for c in build_candidates(es) if c["origin"] == "缺口句"]
    assert len(cards) == 1 and len(cards[0]["concerns"]) >= 2


def test_empty_cell_only_watch():
    es = [_entry(i, "demand", "scientific", f"Tool review workflow {i}",
                 "Researchers review papers with tools in a web environment.", radar="workflow")
          for i in range(1, 5)]
    cards = build_candidates(es)
    assert cards and all(c["status"] == "观察" for c in cards if c["origin"] == "覆盖空格")


def test_review_quotes_verbatim_in_sources():
    """综述方向的每句原话都必须能在原文里逐字找到；对不上就不该出现在页面上。"""
    from radar.core.lit_index import research_map
    m = research_map()
    assert m["unverified"] == [], m["unverified"]
    dirs = [x for d in m["domains"] for x in d["can_do"]]
    assert dirs and all(len(x["evidence"]) >= 2 and len(x["differs_from"]) >= 2 for x in dirs)


def test_domain_terms_no_false_hits():
    from radar.core.radar_core import detect_domain
    assert detect_domain("We define a new pathological case for numeric parsing benchmark") != "medical"
    assert detect_domain("SurgSkill-Bench: multimodal surgical skill assessment") == "medical"
    assert detect_domain("MCPGen: benchmarking LLMs on executable MCP workflow development") == "agent"
    assert detect_domain("Embodied memory for long-horizon stock of objects in trading rooms") != "financial"


def test_overlap_check_finds_contractscrub():
    """2026-10-08：合同审查方向曾漏查 ContractScrub。相似度检查必须把它排进前 10。"""
    from radar.core.lit_index import _Similar, load_index, _toks
    from radar.core.radar_core import db
    with db() as conn:
        es = [e for e in load_index(conn) if e["role"] == "benchmark"]
        sim = _Similar(conn, es)
        sid = conn.execute("SELECT id FROM source_items WHERE title LIKE 'ContractScrub%'").fetchone()
    if sid:
        top = [s for s, _ in sim.rank("contract review risky clauses errors inconsistencies full contracts", 10)]
        assert sid[0] in top

def test_bench_name_not_sentence():
    from radar.core.lit_index import bench_name
    assert bench_name("Are Benchmarks Reliable? Toward Structural Diagnosis")[1] is False
    assert bench_name("ContractScrub: A benchmark for final review of legal contracts")[0] == "ContractScrub"
    assert bench_name("Benchmarking LLM Inference at Scale with AIPerf")[0] == "AIPerf"

def test_arxiv_versions_dedup():
    from radar.core.lit_index import dedup_key
    assert dedup_key("x", "https://arxiv.org/abs/2609.28230v1") == dedup_key("y", "https://arxiv.org/abs/2609.28230v2")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("ok")


def _built_cards():
    import json
    from pathlib import Path
    p = Path(__file__).resolve().parents[1] / "outputs" / "gap_candidates.json"
    return json.loads(p.read_text(encoding="utf-8"))["cards"]


def _near_names(card):
    return [b["name"] for b in card["nearby_benchmarks"]]


def _card_with(paper):
    return next(c for c in _built_cards() if c["origin"] == "缺口句"
                and any(paper in b["name"] for b in c["supporting_benchmarks"]))


def test_nearby_known_pairs():
    """已知对应关系：这些 Benchmark 必须挂在对应缺口的附近列表里。"""
    expect = {"MedCalc-Eval": "MedCalc-Bench", "ContractEval": "ContractScrub"}
    for paper, bench in expect.items():
        c = _card_with(paper)
        assert any(bench in n for n in _near_names(c)), (paper, _near_names(c))


def test_nearby_excludes_off_topic():
    """修之前挂错的条目不能再出现。"""
    bad = ["Spatial Transcriptomics", "Lesion-centered 3D mapping", "Cyber Incident Response", "TrafficImag"]
    for c in _built_cards():
        for b in c["nearby_benchmarks"]:
            title = b.get("title", b["name"])
            assert not any(x in title for x in bad), (c["name"], title)


def test_unrelated_quotes_not_merged():
    """说的不是一件事的原话不能装进一张卡（2026-10-08 前按关注点标签分组时会）。"""
    es = [_entry(1, "benchmark", "medical", "StrokeBench: a benchmark",
                 "However, existing benchmarks rarely test stroke history taking and urgency triage in emergency departments."),
          _entry(2, "benchmark", "medical", "ToxPathBench: a benchmark",
                 "However, existing benchmarks overlook toxicologic pathology slides from laboratory animals.")]
    cards = [c for c in build_candidates(es) if c["origin"] == "缺口句"]
    assert len(cards) == 2 and all(c["status"] == "观察" for c in cards)


def test_every_strong_gap_judged_by_a_human():
    """地图上每个多篇支撑的缺口都要有人工判定；标签也不能指向已经消失的分组。"""
    from radar.core.lit_index import load_labels, match_label
    labels = load_labels()
    strong = [c for c in _built_cards() if c["origin"] == "缺口句" and c["status"] == "候选"]
    missing = [c["name"] for c in strong if not match_label(c, labels)]
    assert not missing, missing
    used = {id(match_label(c, labels)) for c in strong}
    stale = [l["title"] for l in labels if id(l) not in used]
    assert not stale, stale


def test_label_findings_numbers_in_source():
    """人工写的“实测发现”里出现的数字必须能在支撑论文摘要里找到，防止编数。"""
    import re
    from radar.core.lit_index import load_labels
    from radar.core.radar_core import db
    with db() as conn:
        for lab in load_labels():
            if not lab.get("finding"):
                continue
            sids = {int(k.split(":")[0]) for k in lab["quote_keys"]}
            text = " ".join((conn.execute("SELECT content FROM source_items WHERE id=?", (s,)).fetchone() or [""])[0]
                            for s in sids)
            for num in re.findall(r"\d+(?:\.\d+)?", lab["finding"]):
                assert num in text, (lab["title"], num)


def test_gap_direction_links_valid():
    """缺口标签里写的方向必须存在且原话已核对；还没测完的能力缺陷要么有方向，要么写明剩什么。"""
    import json
    from radar.core.lit_index import load_labels, load_directions, load_index
    from radar.core.radar_core import db
    with db() as conn:
        _, dirs, _ = load_directions(conn, load_index(conn))
    ok = {d["id"] for d in dirs if d["verified"]}
    for lab in load_labels():
        if lab.get("direction"):
            assert lab["direction"] in ok, lab["title"]
            assert lab.get("left_open"), ("有方向就要写清还剩什么没测", lab["title"])
        if lab.get("left_open"):
            assert lab.get("direction"), ("还没测的缺口要配一个方向", lab["title"])


def test_research_map_open_count_matches():
    from radar.core.lit_index import research_map
    for d in research_map()["domains"]:
        assert d["counts"]["gaps"] == sum(g["open"] for g in d["not_yet"])
        for g in d["not_yet"]:
            if g["direction"]:
                assert any(x["id"] == g["direction"]["id"] for x in d["can_do"]), g["gap"]

"""Benchmark 索引（lit_index）的回归测试：是不是 Benchmark、分到哪个领域、名字和去重。

2026-10-09 研究地图、缺口聚类、撞车检查停用，对应测试归档在
archive/research_map_2026-10-09/code/test_lit_index_full.py。

跑：python3 -m pytest tests/ -q
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from radar.core.lit_index import analyze, bench_name, dedup_key, _other_domain  # noqa: E402

PAD = " Filler sentence about the setup of the study and the data we release." * 5


def test_benchmark_vs_method_paper():
    assert analyze("benchmark", "FooBench: a benchmark for X", "We introduce FooBench." + PAD)["role"] == "benchmark"
    assert analyze("benchmark", "A faster optimizer", "We propose a new optimizer." + PAD)["role"] == "not_benchmark"
    assert analyze("benchmark", "A survey of agent benchmarks", "We review." + PAD)["role"] == "not_benchmark"


def test_generic_risk_word_not_safety():
    a = analyze("benchmark", "X: dataset", "However, over-pruning risk remains open for this method." + PAD)
    assert "安全/风险" not in a["concerns"]


def test_domain_terms_no_false_hits():
    from radar.core.radar_core import detect_domain
    assert detect_domain("We define a new pathological case for numeric parsing benchmark") != "medical"
    assert detect_domain("SurgSkill-Bench: multimodal surgical skill assessment") == "medical"
    assert detect_domain("MCPGen: benchmarking LLMs on executable MCP workflow development") == "agent"
    assert detect_domain("Embodied memory for long-horizon stock of objects in trading rooms") != "financial"


def test_coding_domain():
    from radar.core.radar_core import detect_domain
    assert detect_domain("SWE-Lancer: resolving GitHub issues with agentic coding in real codebases") == "coding"
    assert detect_domain("RepoBench: repository-level code completion benchmark") == "coding"
    assert detect_domain("Text-to-SQL evaluation on enterprise databases") == "coding"
    # 非编程语境的 coding / programming / code
    assert detect_domain("Automated ICD medical coding of clinical notes for patients") == "medical"
    assert detect_domain("A dynamic programming approach to trajectory planning. Code is available.") != "coding"
    # 浏览型 Agent 仍归 Agent
    assert detect_domain("WebShop-X: a web agent benchmark for browsing and tool calling") == "agent"


def test_bench_name_not_sentence():
    assert bench_name("Are Benchmarks Reliable? Toward Structural Diagnosis")[1] is False
    assert bench_name("ContractScrub: A benchmark for final review of legal contracts")[0] == "ContractScrub"
    assert bench_name("Benchmarking LLM Inference at Scale with AIPerf")[0] == "AIPerf"


def test_arxiv_versions_dedup():
    assert dedup_key("x", "https://arxiv.org/abs/2609.28230v1") == dedup_key("y", "https://arxiv.org/abs/2609.28230v2")


def test_other_domain_subgroups():
    """待读清单里"其他领域"按这个细分；判不出的归"通用"（页面上显示为杂项）。"""
    assert _other_domain("RoboArena: embodied manipulation benchmark", "") == "机器人/具身"
    assert _other_domain("A benchmark for something", "") == "通用"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("ok")

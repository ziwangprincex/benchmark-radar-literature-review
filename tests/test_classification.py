"""信号分类的回归测试。

分类决定每条信号归入哪个 Idea，是 Idea Pool 的入口。2026-09-23 之前
`detect_domain` 和 `detect_capabilities` 都会兜底（分别归 general 和
domain_expertise），两个兜底叠加把 103 条信号里的 37 条塞进同一个
"General Domain Expertise能力评测"——里面混着 OpenAI 产品公告、乌克兰新闻
捐款和 Navier-Stokes 数学论文。这批断言防止兜底行为回归。

跑：python3 -m pytest tests/ -q   或   python3 tests/test_classification.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from radar.core.radar_core import (  # noqa: E402
    PENDING_THEME,
    UNCLASSIFIED,
    detect_capabilities,
    detect_domain,
    detect_theme,
)


def classify(text: str) -> tuple[str, list[str], str]:
    domain = detect_domain(text)
    capabilities = detect_capabilities(text)
    return domain, capabilities, detect_theme(domain, text, capabilities)


# --- 垂类信号应归入对应主题 ---

def test_medical_clinical_maps_to_theme():
    domain, _, theme = classify("CMB: A Comprehensive Medical Benchmark in Chinese 临床病例诊断")
    assert domain == "medical"
    assert theme == "临床推理与指南溯源"


def test_legal_contract_maps_to_theme():
    domain, _, theme = classify("合同条款风险审查 contract clause review benchmark")
    assert domain == "legal"
    assert theme == "合同跨条款风险审查"


def test_financial_report_maps_to_theme():
    domain, _, theme = classify("10-K 财报数字勾稽与页码引用 long context")
    assert domain == "financial"
    assert theme == "PDF财报异常识别与证据引用"


# --- 噪声必须落到 UNCLASSIFIED，不能伪装成 Idea ---

def test_consumer_product_news_is_unclassified():
    """生活类产品资讯不是 benchmark 信号。"""
    domain, _, theme = classify("5 ways to upgrade your home decor with Google Search")
    assert domain == UNCLASSIFIED
    assert theme == UNCLASSIFIED


def test_corporate_news_is_unclassified():
    """人事与公司动态不是 benchmark 信号。"""
    _, _, theme = classify("Paul Christiano joins OpenAI Foundation Board")
    assert theme == UNCLASSIFIED


def test_model_training_paper_is_unclassified():
    """模型压缩/蒸馏属于训练方法，不是评测议题。"""
    _, _, theme = classify("Breaking the Token Ceiling: Distilling Smaller, Stronger Byte Models")
    assert theme == UNCLASSIFIED


# --- general 域必须能被显式识别，不能只靠兜底 ---

def test_fact_checking_is_general_not_unclassified():
    """R2VC 这类跨垂类事实核查研究属于 general，此前会落到 unclassified。"""
    domain, capabilities, theme = classify(
        "R2VC: Modular Fact-Checking with Retrieval, Verification and Correction"
    )
    assert domain == "general"
    assert "citation_correctness" in capabilities
    assert theme == PENDING_THEME


def test_judge_reliability_is_recognized():
    """LLM-as-a-Judge 可靠性本身是可评测能力。"""
    domain, capabilities, theme = classify("GAUGE: When Not to Trust LLM-as-a-Judge")
    assert domain == "general"
    assert "judge_reliability" in capabilities
    assert theme == PENDING_THEME


def test_vertical_domain_wins_over_general():
    """同时命中垂类和 general 时，垂类优先——临床事实核查应归 medical。"""
    domain, _, _ = classify("临床诊断中的 hallucination 与 fact-check 评测 clinical")
    assert domain == "medical"


# --- 兜底行为不得回归 ---

def test_no_domain_expertise_fallback():
    """无能力词命中时返回空列表，不能兜底成 domain_expertise。"""
    assert detect_capabilities("Supporting independent journalism in Ukraine") == []


def test_unclassified_domain_never_becomes_general():
    """判不出垂类时返回 UNCLASSIFIED，不能混进 general。"""
    assert detect_domain("Recreating a 70-year love story frame by frame") == UNCLASSIFIED


def test_theme_requires_both_domain_and_capability():
    """缺 domain 或 capability 任一，都不能生成主题名。"""
    assert detect_theme(UNCLASSIFIED, "任意文本", ["tool_use"]) == UNCLASSIFIED
    assert detect_theme("medical", "任意文本", []) == UNCLASSIFIED


# --- 2026-09-23 新增主题：每条都核对过原始摘要，并锁住实测出的误判 ---

def test_benchmark_compression_theme():
    """Zipbench 类评测集压缩研究。文本取自实际摘要。"""
    _, _, theme = classify(
        "Zipbench: Low-Cost Framework for Compressing Comprehensive Benchmarks. "
        "Comprehensive benchmark suites are essential for improving large language "
        "models, but many widely used benchmarks are redundant, making evaluation "
        "unnecessarily expensive. research experiment 版本"
    )
    assert theme == "评测集压缩后的结论保真度"


def test_judge_gate_reliability_theme():
    """GAUGE 类研究：Agent 选型门禁自身的判据可靠性。"""
    _, _, theme = classify(
        "GAUGE: When Not to Trust LLM-as-a-Judge in User-Simulated Evaluation of agents"
    )
    assert theme == "Agent选型门禁的判据可靠性"


def test_biomedical_hypothesis_theme():
    """HypoKG 类研究：假设是否真有证据支持。文本取自实际摘要。

    注意不含"诊断/病例"——真实摘要讲的是从生物数据库推理，
    不是临床决策，所以不应落到"临床推理与指南溯源"。
    """
    _, _, theme = classify(
        "HypoKG: Evidence-Disciplined Biomedical Hypothesis Generation. Large "
        "language models can generate biomedical hypotheses, but it remains unclear "
        "whether they truly reason from scientific evidence. 药 医疗 hypothesis generation"
    )
    assert theme == "生物医学假设的证据支持度"


def test_clinical_keyword_alone_does_not_match_theme():
    """'clinical' 常作举例出现，单独命中它不能归入临床推理主题。

    SynthSentry 讲数据污染检测，只在 "legal, clinical, source code" 里
    提到 clinical；此前会被误归入"临床推理与指南溯源"。
    """
    text = ("SynthSentry: Detecting Synthetic Data Contamination. A domain-stratified "
            "study measures false positives on naturally repetitive human text "
            "(legal, clinical, source code). 推理 analysis")
    _, _, theme = classify(text)
    assert theme != "临床推理与指南溯源"


def test_biomedical_keyword_alone_does_not_match_hypothesis_theme():
    """单独的 'biomedical' 不能归入假设生成主题。

    LatentVerse 讲多模态表征，只是提到 biomedical embeddings。
    """
    text = ("LatentVerse: A Framework for Understanding Shared and Modality-specific "
            "representations, clinical text, medical images, biomedical embeddings 推理")
    _, _, theme = classify(text)
    assert theme != "生物医学假设的证据支持度"


def test_credit_assignment_is_not_financial():
    """'credit assignment' 是强化学习术语，不是金融信贷。

    TelecomGPT-R1（电信领域后训练）曾因裸 "credit" 命中而被判为 financial，
    再经特判规则归入"PDF财报异常识别与证据引用"。
    """
    text = ("TelecomGPT-R1: Unified Post-Training for Reasoning. combine grounded "
            "dense process credit with outcome correctness, allowing RL to learn. "
            "citation 推理 judge")
    domain, _, theme = classify(text)
    assert domain != "financial"
    assert theme != "PDF财报异常识别与证据引用"


def test_financial_theme_requires_report_document():
    """金融 + 引用能力但未提财报文档时，不归入财报主题。"""
    text = "金融 investment portfolio optimization with citation 引用 推理 long context 长文档"
    _, _, theme = classify(text)
    assert theme != "PDF财报异常识别与证据引用"


def test_product_announcement_does_not_match_computer_use_theme():
    """产品公告不应命中 Computer-Use Agent 主题。

    GPT-6 Astra 公告泛泛提到 agent 与 multi-step，此前因 'environment'
    和 'multi-step task' 过泛而被误归。
    """
    text = ("GPT-6 Astra: The next generation in intelligence for work. agent tool use "
            "reasoning across environments and multi-step tasks")
    _, _, theme = classify(text)
    assert theme != "Computer-Use Agent多步工作流完成度"


def test_medical_retrieval_benchmark_maps_to_clinical_theme():
    """R2MED 真实摘要应归入临床推理主题。

    该条曾因抓取到 nerfies 学术模板自带的 meta description（"Deformable
    Neural Radiance Fields creates free-viewpoint portraits"）而内容错误，
    系统标记了 metadata_mismatch 但 generate_ideas 未检查该字段，使它成为
    idea 18 的唯一支撑信号。
    """
    _, _, theme = classify(
        "R2MED: A Benchmark for Reasoning-Driven Medical Retrieval. We introduce "
        "R2MED, comprising 876 queries spanning Q&A reference retrieval, clinical "
        "evidence retrieval, and clinical case retrieval. 检索 推理"
    )
    assert theme == "临床推理与指南溯源"


def test_nerfies_template_text_is_not_medical():
    """抓错的模板文案不应命中任何医学主题。"""
    _, _, theme = classify(
        "Deformable Neural Radiance Fields creates free-viewpoint portraits "
        "(nerfies) from casually captured videos."
    )
    assert theme == UNCLASSIFIED


# --- 2026-09-24：子串误命中与主题词过泛 ---

def test_tensor_contraction_is_not_legal():
    """ChainDoRA 的 "TT contractions" 不能命中 contract。

    它曾因此被判为 legal 并成为"合同跨条款风险审查"唯一的 Raw Source。
    """
    text = ("ChainDoRA: Tensor-Train Factorized Low-Rank Adaptation. the adapter rank "
            "forms the boundary rank between input- and output-side TT contractions")
    assert detect_domain(text) != "legal"


def test_contract_plural_still_matches():
    assert detect_domain("Reviewing commercial contracts for indemnity risk") == "legal"


def test_recitation_is_not_citation():
    assert "citation_correctness" not in detect_capabilities("Annotating Recitation Events in Quran")


def test_average_is_not_rag():
    assert detect_domain("models achieve higher average solve rates") == UNCLASSIFIED


def test_agentic_browser_use_is_not_deep_research():
    """模型发布稿列举 "agentic browser-use" 不等于 Deep Research 评测议题。"""
    _, _, theme = classify(
        "Qwen3-Coder: Agentic Coding. state-of-the-art on Agentic Coding, "
        "Agentic Browser-Use, and Agentic Tool-Use"
    )
    assert theme != "垂类Deep Research任务完成度"


def test_search_agent_benchmark_is_deep_research():
    _, _, theme = classify("LoHoSearch 搜索智能体评测基准：BrowseComp 已饱和，Search Agent 检索")
    assert theme == "垂类Deep Research任务完成度"


def test_every_theme_has_gap_statement():
    """THEMES 新增主题时必须同步撰写 Gap 陈述，否则会退回原文截断。"""
    from radar.core.radar_core import THEME_GAPS, THEMES
    missing = {theme for _, _, theme in THEMES} - set(THEME_GAPS)
    assert not missing, missing


def test_gap_statement_fallback_is_marked():
    from radar.core.radar_core import gap_statement
    text = gap_statement(["arXiv:1 Announce Type: new Abstract: Some abstract text here long enough"], [], "未知主题")
    assert not text.startswith("arXiv")
    assert "待人工" in text



def test_long_abstract_does_not_fail_verification(monkeypatch=None):
    """标题一致、摘要很长时不应判 metadata_mismatch。

    jaccard 分母含摘要全部词，FinanceBench 等 1,000+ 字摘要曾得 0.04 被误判。
    """
    import radar.evidence.evidence_import as ei

    title = "FinanceBench: A New Benchmark for Financial Question Answering"
    abstract = "FinanceBench is a first-of-its-kind test suite for evaluating financial question answering. " + " ".join(
        f"filler{i}" for i in range(300)
    )
    page = (f'<meta name="citation_title" content="{title}">'
            f'<meta name="citation_abstract" content="{abstract}">')

    class Resp:
        status_code = 200
        text = page
        def raise_for_status(self):
            pass

    original = ei.requests.get
    ei.requests.get = lambda *a, **k: Resp()
    try:
        result = ei.verify_result({"title": title, "url": "https://arxiv.org/abs/2311.11944"})
    finally:
        ei.requests.get = original
    assert result["validation_status"] == "verified_source"


# --- 2026-10-08：rules-v10 法律/金融严格领域 ---

def test_single_legal_word_in_abstract_is_not_legal():
    """交通数据集只在摘要里提了一次 legal，不能算法律 Benchmark。"""
    t = "Privacy-Preserving Dataset Curation for Urban Traffic"
    text = t + ". We release a traffic dataset and discuss legal constraints on camera footage."
    assert detect_domain(text, t) != "legal"


def test_legal_title_still_legal():
    t = "ContractScrub: A benchmark for final review of legal contracts"
    assert detect_domain(t + ". Contract scrubbing is routine work.", t) == "legal"


def test_two_legal_words_in_abstract_is_legal():
    t = "UK-PRBENCH: A Paragraph-Level Precedent Retrieval Benchmark"
    text = t + ". We retrieve paragraphs from UK case law judgments of the court."
    assert detect_domain(text, t) == "legal"


def test_listing_many_domains_is_general():
    t = "SteerBench-Work: A Benchmark for Agent Steering"
    text = t + ". Tasks span finance, legal and medical settings."
    assert detect_domain(text, t) not in ("legal", "financial")


def test_executable_contract_is_not_legal():
    t = "Do Agent Benchmarks Do What They Say? An Executable-Contract Audit"
    assert detect_domain(t + ". We audit tool-using agent environments.", t) != "legal"


if __name__ == "__main__":
    failures = []
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"ok   {name}")
            except AssertionError as exc:
                failures.append(name)
                print(f"FAIL {name}: {exc}")
    print(f"\n{len(failures)} failed" if failures else "\nALL PASS")
    raise SystemExit(1 if failures else 0)

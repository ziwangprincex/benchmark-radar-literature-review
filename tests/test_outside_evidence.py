"""论文外旁证导入的回归测试，纯函数，不联网、不碰数据库。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from radar.evidence.import_outside_evidence import ONET_CONCERNS, _types, concerns_for  # noqa: E402

import re  # noqa: E402


def test_hallucination_types_parsed_from_items():
    row = {"Hallucination Items": "Fabricated: Case Law | Smith v. Jones does not exist. || "
                                  "Outdated Advice: Overturned Case Law | Roe was overturned."}
    assert _types(row) == ["Fabricated: Case Law", "Outdated Advice: Overturned Case Law"]


def test_concerns_from_types_not_from_judgment_text():
    # 判决原文里的 Judge / Adverse Costs Order 不应产生"评判可靠性/安全风险"
    assert concerns_for(["Fabricated: Case Law"]) == ["证据/溯源"]
    assert concerns_for(["Outdated Advice: Repealed Law"]) == ["时效/版本"]
    assert concerns_for(["Fabricated: Exhibits & Submissions"]) == ["证据/溯源"]


def test_onet_concerns_skip_false_friends():
    hit = lambda s: [k for k, p in ONET_CONCERNS.items() if re.search(p, s, re.I)]
    assert hit("Represent clients before government agencies.") == []
    assert hit("Explain the processes to patients.") == []
    assert hit("Follow procedures to avoid contamination.") == []
    assert hit("Gather evidence to formulate defense.") == ["证据/溯源"]
    assert hit("Monitor patients for adverse drug interaction.") == ["安全/风险"]


def test_medhelm_model_parsed_from_run_name():
    from radar.evidence.import_medhelm import model_of
    assert model_of("medec:model=openai_gpt-4o-2024-05-13,model_deployment=x") == "openai_gpt-4o-2024-05-13"
    assert model_of("medcalc_bench:num_output_tokens=4000,model=deepseek-ai_deepseek-r1,model_deployment=y") == "deepseek-ai_deepseek-r1"


def test_medcalc_judge_uses_tolerance_and_formats():
    from radar.evidence.medcalc_audit import judge
    assert judge("233.612", "233.554", "221.8763", "245.2317")
    assert not judge("250", "233.554", "221.8763", "245.2317")
    assert judge("(4, 3)", "('4 weeks', '3 days')", "", "")
    assert judge("4/7/2009", "04/07/2009", "", "")
    assert not judge("I cannot calculate", "9", "9", "9")


def test_medec_flag_accepts_correct_with_explanation():
    from radar.evidence.medhelm_recheck import medec_flag
    assert medec_flag("CORRECT\n\nThe narrative is consistent.") == "CORRECT"
    assert medec_flag("**CORRECT**") == "CORRECT"
    assert medec_flag("8 Group A Streptococcus is the causative agent.") == "ERROR"
    assert medec_flag("Correction: sentence 4") == "ERROR"

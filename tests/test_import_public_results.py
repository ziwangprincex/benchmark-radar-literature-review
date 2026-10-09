"""import_public_results 的规则归类测试（纯离线，不联网）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from radar.eval.import_public_results import classify_failure  # noqa: E402


def q(answer, question="What is the FY2020 DPO for Corning?", pages=(69,)):
    return {"answer": answer, "question": question, "evidence": [{"evidence_page_num": p} for p in pages]}


def test_refusal_label():
    t, _ = classify_failure("Refusal", q("63.86"), "I cannot determine this.", "singleStore")
    assert t == "retrieval_or_refusal"


def test_not_explicitly_stated_is_refusal():
    t, _ = classify_failure("Incorrect Answer", q("$1577.00", "What is the FY2018 capital expenditure for 3M?"),
                            "The FY2018 capital expenditure amount is not explicitly stated.", "singleStore")
    assert t == "retrieval_or_refusal"


def test_multi_page_numeric():
    t, _ = classify_failure("Incorrect Answer", q("63.86", pages=(69, 71)),
                            "Corning FY2020 DPO: $1,381 / $7,890 = 50 days. Corning's DPO is 50 days.", "oracle")
    assert t == "multi_page_numeric"


def test_percent_decimal_equivalent_not_mismatch():
    t, _ = classify_failure("Incorrect Answer", q("10.3%", "What is Corning 3-year average operating margin?"),
                            "Corning average operating margin is 0.103.", "oracle")
    assert t != "numeric_mismatch"


def test_same_direction_not_reversed():
    """金标准 "Yes, there is decline" 与回答描述下降一致，不能算判断反转。"""
    t, _ = classify_failure("Incorrect Answer",
                            q("Yes, there is decline in number stores", "Did Best Buy store count decline?"),
                            "Best Buy store count declined, a net decrease of 23 stores.", "oracle")
    assert t != "judgment_reversed"


def test_explicit_reversal():
    t, _ = classify_failure("Incorrect Answer", q("No. Verizon's debt decreased", "Has Verizon increased its debt?"),
                            "Yes, Verizon has increased its debt on balance sheet.", "oracle")
    assert t == "judgment_reversed"


def test_off_topic():
    t, _ = classify_failure("Incorrect Answer", q("-3.7", "What is General Mills cash conversion cycle FY2019?"),
                            "Here is a summary of the key information in the exhibit: subsidiaries across the world.", "inContext")
    assert t == "off_topic"


if __name__ == "__main__":
    failures = []
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"ok {name}")
            except AssertionError as exc:
                failures.append(name)
                print(f"FAIL {name}: {exc}")
    print(f"\n{len(failures)} failed" if failures else "\nALL PASS")
    raise SystemExit(1 if failures else 0)

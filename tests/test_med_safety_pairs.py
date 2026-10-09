"""med_safety_pairs 的对抗测试（纯离线）。"""
import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from radar.eval import med_safety_pairs as m  # noqa: E402

CASES = json.loads(m.SOURCE.read_text(encoding="utf-8"))


def built():
    return m.build_items(CASES)


def test_every_anchor_unique_in_real_source():
    tasks, keys = built()
    assert len(tasks) == 2 * len(m.PAIRS) == len(keys)


def test_variant_differs_from_base_only_by_edit():
    tasks, keys = built()
    by = {t["task_id"]: t["messages"][0]["content"] for t in tasks}
    for k in keys:
        if k["arm"] != "variant":
            continue
        base = by[k["task_id"].replace("::variant", "::base")]
        var = by[k["task_id"]]
        assert var != base
        assert var.replace(k["edit"]["replacement"], k["edit"]["anchor"], 1) == base


def test_tasks_leak_no_answer_key():
    tasks, keys = built()
    blob = json.dumps(tasks, ensure_ascii=False)
    for k in keys:
        for kind in ("required", "unsafe", "fatal"):
            for x in k["rubric"][kind]:
                assert x["id"] not in blob
    for t in tasks:
        assert set(t) == {"package_id", "task_id", "messages", "temperature"}


def test_missing_anchor_rejected():
    with pytest.raises(ValueError):
        m.apply_variant("abc", "zzz", "y")


def test_duplicate_anchor_rejected():
    with pytest.raises(ValueError):
        m.apply_variant("既往体健。既往体健。", "既往体健。", "x")


def test_duplicate_rubric_id_rejected():
    pairs = copy.deepcopy(m.PAIRS)
    pairs[1]["base"]["required"].append(pairs[0]["base"]["required"][0])
    with pytest.raises(ValueError):
        m.build_items(CASES, pairs)


def _labels(model, overrides=None):
    """默认：诊断全对、只命中全部 required（即完全安全且完整）。"""
    _, keys = built()
    overrides = overrides or {}
    out = []
    for k in keys:
        hit = [x["id"] for x in k["rubric"]["required"]]
        dx = True
        if k["task_id"] in overrides:
            hit, dx = overrides[k["task_id"]]
        out.append({"task_id": k["task_id"], "model": model, "diagnosis_correct": dx, "hit": hit})
    return keys, out


def test_perfect_model():
    keys, labels = _labels("A")
    r = m.score(keys, labels)["A"]
    assert r["advice_safety_rate"] == 1.0 and r["fatal_error_count"] == 0 and r["failed_to_adapt"] == 0


def test_fatal_vetoes_even_when_required_all_present():
    tid = "MedSafety::P1-carbuncle-pcn-allergy::variant"
    _, keys = built()
    k = next(x for x in keys if x["task_id"] == tid)
    hit = [x["id"] for x in k["rubric"]["required"]] + ["P1v-f1"]
    keys, labels = _labels("A", {tid: (hit, True)})
    r = m.score(keys, labels)["A"]
    assert r["fatal_error_count"] == 1
    assert r["answers_with_fatal"] == 1
    assert r["failed_to_adapt"] == 1
    assert r["unsafe_given_correct_dx"] > 0


def test_missing_required_is_incomplete_not_unsafe():
    tid = "MedSafety::P3-alkalosis-oliguria::base"
    keys, labels = _labels("A", {tid: ([], True)})
    r = m.score(keys, labels)["A"]
    assert r["advice_safety_rate"] == 1.0
    assert r["completeness_rate"] < 1.0


def test_unsafe_with_wrong_dx_not_counted_in_conditional_rate():
    tid = "MedSafety::P2-hand-infection-ceph-allergy::variant"
    keys, labels = _labels("A", {tid: (["P2v-f1"], False)})
    r = m.score(keys, labels)["A"]
    assert r["diagnosis_accuracy"] < 1.0
    assert r["unsafe_given_correct_dx"] == 0.0
    assert r["fatal_error_count"] == 1


def test_base_unsafe_pair_excluded_from_adapt_denominator():
    base = "MedSafety::P5-dissection-asthma::base"
    var = "MedSafety::P5-dissection-asthma::variant"
    keys, labels = _labels("A", {base: (["P5b-f1"], True), var: (["P5v-f1"], True)})
    r = m.score(keys, labels)["A"]
    assert r["pairs_base_safe"] == len(m.PAIRS) - 1
    assert r["failed_to_adapt"] == 0


def test_rubric_id_from_other_task_rejected():
    tid = "MedSafety::P1-carbuncle-pcn-allergy::base"
    keys, labels = _labels("A", {tid: (["P1v-f1"], True)})
    with pytest.raises(ValueError):
        m.score(keys, labels)


def test_string_hit_rejected():
    keys, labels = _labels("A")
    labels[0]["hit"] = "P1b-r1"
    with pytest.raises(ValueError):
        m.score(keys, labels)


def test_non_bool_dx_rejected():
    keys, labels = _labels("A")
    labels[0]["diagnosis_correct"] = "yes"
    with pytest.raises(ValueError):
        m.score(keys, labels)


def test_missing_and_duplicate_labels_rejected():
    keys, labels = _labels("A")
    with pytest.raises(ValueError):
        m.score(keys, labels[:-1])
    with pytest.raises(ValueError):
        m.score(keys, labels + [labels[0]])


def test_models_scored_independently():
    tid = "MedSafety::P4-pheo-beta-first::variant"
    keys, a = _labels("A", {tid: (["P4v-f1"], True)})
    _, b = _labels("B")
    r = m.score(keys, a + b)
    assert r["A"]["fatal_error_count"] == 1 and r["B"]["fatal_error_count"] == 0

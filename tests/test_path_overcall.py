"""med-overcall 试测包：结构和判分的确定性检查（不调用模型）。"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from radar.eval import path_overcall as P  # noqa: E402


def _key():
    return [json.loads(l) for l in P.KEY_FILE.read_text(encoding="utf-8").splitlines()]


def test_package_balanced_and_unique():
    k = _key()
    assert len(k) == 100
    assert sum(x["label"] == P.NEG for x in k) == 50
    assert len({x["sha1"] for x in k}) == 100, "有重复图片"
    tasks = [json.loads(l) for l in (P.PACKAGE_DIR / "tasks.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(tasks) == 200
    for t in tasks:
        assert (P.PACKAGE_DIR / t["image"]).exists()
        assert "label" not in t, "题目里不能带答案"
    # 两版提示词只差一句病史
    assert P.ARMS["history"] == P.HISTORY + P.ARMS["neutral"]


def test_parse_first_line_only():
    assert P.parse("无转移\n可见淋巴细胞") == P.NEG
    assert P.parse("**有转移**\n异型细胞成团") == P.POS
    assert P.parse("从图像看，未见明确转移") is None
    assert P.parse("") is None


def test_score_counts():
    k = _key()
    neg = [x["image_id"] for x in k if x["label"] == P.NEG]
    pos = [x["image_id"] for x in k if x["label"] == P.POS]
    rows = []
    # 假模型：neutral 全判无转移；history 把前 10 张正常切片改判有转移，其余照旧
    for i in neg:
        rows.append({"task_id": f"{i}-neutral", "model": "m", "answer": "无转移"})
        rows.append({"task_id": f"{i}-history", "model": "m", "answer": "有转移" if i in neg[:10] else "无转移"})
    for i in pos:
        rows.append({"task_id": f"{i}-neutral", "model": "m", "answer": "有转移"})
        rows.append({"task_id": f"{i}-history", "model": "m", "answer": "看不清"})
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        f.write("\n".join(json.dumps(r, ensure_ascii=False) for r in rows))
    out = {r["arm"]: r for r in P.score(Path(f.name))}
    assert out["neutral"]["正常切片报成阳性"].startswith("0/50")
    assert out["neutral"]["转移切片检出"].startswith("50/50")
    assert out["history"]["正常切片报成阳性"].startswith("10/50")
    assert out["history"]["格式不对"] == 50
    assert out["neutral→history"]["正常切片加一句病史后改判阳性"].startswith("10/50")


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f()
    print("ok")

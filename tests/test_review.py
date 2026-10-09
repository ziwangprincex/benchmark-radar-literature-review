"""文献综述：防编造核对 + 三步流程 + 批注改稿。不连真实模型，用假的 chat 函数。"""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from radar.review import check as C  # noqa: E402
from radar.review import pipeline as P  # noqa: E402

PAPERS = [
    {"id": 1, "title": "LawQA: legal exam questions", "url": "u1", "date": "2026-09-01",
     "abstract": "We build LawQA. Existing benchmarks ignore citation validity in legal answers."},
    {"id": 2, "title": "ContractEval", "url": "u2", "date": "2026-09-02",
     "abstract": "ContractEval tests clause review. We do not evaluate cross-document conflicts."},
    {"id": 3, "title": "CaseRet", "url": "u3", "date": "2026-09-03",
     "abstract": "CaseRet evaluates precedent retrieval over court decisions."},
    {"id": 4, "title": "LoRA tricks", "url": "u4", "date": "2026-09-04",
     "abstract": "We propose a fine-tuning method and test it on legal tasks."},
]

TAX = {"categories": [{"name": "问答与检索", "tests": "答题和找判例", "why": "", "ids": [1, 3]},
                      {"name": "合同审查", "tests": "审合同条款", "why": "", "ids": [2]}],
       "outside": [{"id": 4, "reason": "方法论文"}]}

BODY = """## 二、各类做到哪、共同短板
### 问答与检索
- 短板：作者说现有评测不看引用「Existing benchmarks ignore citation validity in legal answers」 [#1]
### 合同审查
- 短板：只看单份合同 [#2]
### 跨类的共同问题
- 都只看最终答案 [#1][#2]
## 三、大家还没研究什么
- 跨文件冲突没人测：「We do not evaluate cross-document conflicts」 [#2]
## 四、我们能研究什么
### 主协议和附件的冲突检测
- 证据：直接 [#2]
"""


class CheckTest(unittest.TestCase):
    def test_good_body(self):
        r = C.check_body(BODY, PAPERS, TAX)
        self.assertTrue(r["ok"], r["problems"])
        self.assertEqual(r["quotes_ok"], 2)
        self.assertEqual(r["warnings"]["categories_not_discussed"], [])

    def test_fake_quote(self):
        r = C.check_body(BODY.replace("ignore citation validity", "never check citations"), PAPERS, TAX)
        self.assertFalse(r["ok"])
        self.assertEqual(len(r["problems"]["fake_quotes"]), 1)
        self.assertIn("never check citations", C.problems_text(r))

    def test_quote_attributed_to_wrong_paper(self):
        r = C.check_body(BODY.replace("legal answers」 [#1]", "legal answers」 [#3]"), PAPERS, TAX)
        self.assertFalse(r["ok"])

    def test_unknown_id_and_missing_section(self):
        r = C.check_body(BODY.replace("[#2]\n### 跨类", "[#2][#99]\n### 跨类").split("## 四、")[0], PAPERS, TAX)
        self.assertEqual(r["problems"]["invalid_ids"], [99])
        self.assertEqual(r["problems"]["missing_sections"], ["四、我们能研究什么"])

    def test_category_not_discussed_is_only_a_warning(self):
        r = C.check_body(BODY.replace("### 合同审查\n", ""), PAPERS, TAX)
        self.assertTrue(r["ok"])
        self.assertEqual(r["warnings"]["categories_not_discussed"], ["合同审查"])


class TaxonomyTest(unittest.TestCase):
    def test_normalize_drops_unknown_and_duplicate_ids(self):
        t = P.normalize_taxonomy({"categories": [{"name": "A", "ids": [1, 1, 99]}, {"name": "B", "ids": [1]},
                                                 {"name": "C", "ids": ["#2"]}],
                                  "outside": [{"id": 3, "reason": "x"}]}, {1, 2, 3, 4})
        self.assertEqual([c["name"] for c in t["categories"]], ["A", "C"])
        self.assertEqual(t["categories"][0]["ids"], [1])
        self.assertEqual(t["missing"], [4])

    def test_section1_counts_come_from_taxonomy(self):
        md = P.render_section1({**TAX, "by": "model"}, {p["id"]: p for p in PAPERS}, {})
        self.assertIn("### 问答与检索（2 篇）", md)
        self.assertIn("### 合同审查（1 篇）", md)
        self.assertIn("### 没算进来的（1 篇）", md)
        self.assertIn("3 篇分 2 类", md)


def fake_model(log):
    """按提示词判断是哪一步，返回对应的假结果。故意制造：一个假原话卡片、分类漏一篇、综述编一句原话。"""
    def chat(msgs):
        t = msgs[-1]["content"]
        log.append(t)
        if "做一张卡片" in t:
            ids = [int(x) for x in re.findall(r"^#(\d+)｜", t, re.M)]
            out = []
            for i in ids:
                q = {1: "Existing benchmarks ignore citation validity", 2: "We never test long contracts"}.get(i, "")
                out.append({"id": i, "kind": "方法" if i == 4 else "Benchmark", "task": f"任务{i}", "input": "文本",
                            "scoring": "准确率", "data": "", "finding": f"发现{i}", "limit_quote": q, "limit_cn": "中文"})
            return "```json\n" + json.dumps(out, ensure_ascii=False) + "\n```"
        if "给它们分类" in t:
            if "一次都没出现" in t:
                return json.dumps(TAX, ensure_ascii=False)
            return "好的：" + json.dumps({"categories": TAX["categories"], "outside": []}, ensure_ascii=False)
        if "写第二、三、四节" in t:
            if "程序核对发现这些问题" in t:
                return BODY
            if "读者的批注" in t:
                return BODY.replace("都只看最终答案", "都只看最终答案，批注已改")
            return "## 一、我多写的\n不要\n\n" + BODY.replace("ignore citation validity", "never check citations")
        raise AssertionError("没认出是哪一步")
    return chat


class PipelineTest(unittest.TestCase):
    def test_three_steps_then_notes(self):
        log = []
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(P, "OUT_ROOT", Path(tmp)), \
                mock.patch.object(P, "load_corpus", lambda d, limit=None: PAPERS), \
                mock.patch.object(P, "skipped_count", lambda d: 2), \
                mock.patch.object(P, "load_config", lambda: {"model": "fake"}):
            st = P.run("legal", chat_fn=fake_model(log))
            self.assertEqual(st["state"], "done")
            d = Path(tmp) / "legal"

            cards = json.loads((d / "cards.json").read_text(encoding="utf-8"))["cards"]
            self.assertEqual(len(cards), 4)
            self.assertEqual(cards["1"]["limit_quote"], "Existing benchmarks ignore citation validity")
            self.assertEqual(cards["2"]["limit_quote"], "")             # 对不上摘要的原话被删掉
            self.assertEqual(cards["2"]["quote_dropped"], "We never test long contracts")

            tax = json.loads((d / "taxonomy.json").read_text(encoding="utf-8"))
            self.assertEqual(tax["outside"], [{"id": 4, "reason": "方法论文"}])  # 漏的那篇第二次补上了
            self.assertEqual(tax["by"], "model")

            md = (d / "review.md").read_text(encoding="utf-8")
            meta = json.loads((d / "review.json").read_text(encoding="utf-8"))
            self.assertTrue(meta["check"]["ok"])                      # 编的原话被打回改掉了
            self.assertTrue(meta["fixed_once"])
            self.assertNotIn("never check citations", md)
            self.assertNotIn("我多写的", md)                          # 模型多写的第一节被丢掉
            self.assertIn("## 一、大家在研究什么：3 篇分 2 类", md)
            self.assertIn("## 五、这份综述的边界", md)
            self.assertIn("标为\"不用读\"的 2 篇", md)
            self.assertLess(md.index("## 一、"), md.index("## 二、"))
            self.assertLess(md.index("## 四、"), md.index("## 五、"))

            # 再跑一次：卡片已缓存，不应再抽卡
            n = len(log)
            P.run("legal", start="cards", chat_fn=fake_model(log))
            self.assertFalse(any("做一张卡片" in t for t in log[n:]))

            # 你改了分类 → 提示综述过期；按批注改稿
            P.save_taxonomy("legal", {"categories": [{"name": "全部", "tests": "", "ids": [1, 2, 3]}], "outside": []})
            self.assertTrue(P.load_result("legal")["pending"]["taxonomy_newer"])
            P.run("legal", notes="跨类问题写得太短", chat_fn=fake_model(log))
            meta = json.loads((d / "review.json").read_text(encoding="utf-8"))
            self.assertEqual([x["text"] for x in meta["notes"]], ["跨类问题写得太短"])
            self.assertIn("批注已改", (d / "review.md").read_text(encoding="utf-8"))
            self.assertIn("跨类问题写得太短", log[-1])
            self.assertIn("上一版的第二到四节", log[-1])
            self.assertFalse(P.load_result("legal")["pending"]["taxonomy_newer"])
            self.assertIn("第一节的分类你调整过", (d / "review.md").read_text(encoding="utf-8"))

    def test_all_card_batches_failing_reports_error(self):
        def boom(msgs):
            raise RuntimeError("接口返回 401")
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(P, "OUT_ROOT", Path(tmp)), \
                mock.patch.object(P, "load_corpus", lambda d, limit=None: PAPERS), \
                mock.patch.object(P, "load_config", lambda: {"model": "fake"}):
            with self.assertRaisesRegex(RuntimeError, "401"):
                P.run("legal", chat_fn=boom)


if __name__ == "__main__":
    unittest.main()

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
    def test_retry_when_categories_have_no_ids(self):
        """2026-10-10 开发机实测：模型第一次只写了类名和说明，没写 ids，结果 5 篇全被放进"不算"。"""
        sent = []
        replies = iter([
            json.dumps({"categories": [{"name": "问答与检索", "tests": "x", "why": "y"}], "outside": []}, ensure_ascii=False),
            json.dumps(TAX, ensure_ascii=False),
        ])

        def chat(msgs):
            sent.append(msgs[-1]["content"])
            return next(replies)
        tax = P._ask_taxonomy("legal", "分类", {1, 2, 3, 4}, chat)
        self.assertEqual(len(tax["categories"]), 2)
        self.assertIn("这些类没有写 ids", sent[1])
        self.assertIn("问答与检索", sent[1])
        self.assertIn('"tests": "x"', sent[1])  # 带上了模型原始回复

    def test_all_empty_raises(self):
        bad = json.dumps({"categories": [{"name": "A"}], "outside": []})
        with self.assertRaisesRegex(ValueError, "分类失败"):
            P._ask_taxonomy("legal", "分类", {1, 2}, lambda m: bad)

    def test_normalize_drops_unknown_and_duplicate_ids(self):
        t = P.normalize_taxonomy({"categories": [{"name": "A", "ids": [1, 1, 99]}, {"name": "B", "ids": [1]},
                                                 {"name": "C", "ids": ["#2"]}],
                                  "outside": [{"id": 3, "reason": "x"}]}, {1, 2, 3, 4})
        self.assertEqual([c["name"] for c in t["categories"]], ["A", "C"])
        self.assertEqual(t["categories"][0]["ids"], [1])
        self.assertEqual(t["missing"], [4])

    def test_section1_counts_come_from_taxonomy(self):
        md = P.render_section1({**TAX, "by": "model"}, {p["id"]: p for p in PAPERS}, {})
        self.assertIn("#### 问答与检索（2 篇）", md)
        self.assertIn("#### 合同审查（1 篇）", md)
        self.assertIn("### 没算进来的（1 篇）", md)
        self.assertIn("3 篇，QA 类 3 篇（2 个主题），Agent 类 0 篇（0 个主题）", md)

    def test_two_levels_qa_then_agent(self):
        """2026-10-10：先分 QA / Agent，再分主题。模型写乱顺序、写成小写或中文，都整理成 QA 在前。"""
        t = P.normalize_taxonomy({"categories": [
            {"group": "agent", "name": "网页办事", "ids": [3]},
            {"group": "QA", "name": "法条问答", "ids": [1]},
            {"group": "智能体", "name": "多智能体协作", "ids": [2]},
            {"name": "没写大类", "ids": [4]}], "outside": []}, {1, 2, 3, 4})
        self.assertEqual([(c["group"], c["name"]) for c in t["categories"]],
                         [("QA", "法条问答"), ("QA", "没写大类"), ("Agent", "网页办事"), ("Agent", "多智能体协作")])
        md = P.render_section1(t, {p["id"]: p for p in PAPERS}, {})
        self.assertIn("| 大类 | 主题 | 篇数 | 测什么 |", md)
        self.assertIn("### QA 类：2 篇，2 个主题", md)
        self.assertIn("### Agent 类：2 篇，2 个主题", md)
        self.assertLess(md.index("#### 没写大类"), md.index("### Agent 类"))
        # 第二节写成 ### 大类 / #### 主题 也算写到了
        body = BODY.replace("### 问答与检索", "### QA 类\n#### 问答与检索").replace("### 合同审查", "#### 合同审查")
        self.assertEqual(C.check_body(body, PAPERS, TAX)["warnings"]["categories_not_discussed"], [])

    def test_week_copies_group_from_full_review(self):
        base = {"categories": [{"group": "Agent", "name": "网页办事", "ids": [1]}]}
        t = P._mark_new({"categories": [{"group": "QA", "name": "网页办事", "ids": [5]},
                                        {"group": "QA", "name": "新主题", "ids": [6]}]}, base)
        self.assertEqual([(c["group"], c["name"], c["new"]) for c in t["categories"]],
                         [("QA", "新主题", True), ("Agent", "网页办事", False)])


class SessionTest(unittest.TestCase):
    """2026-10-10：每次打开页面一个会话，结果互不可见；卡片缓存共用。"""

    def test_sessions_are_isolated_and_cards_shared(self):
        log = []
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(P, "OUT_ROOT", Path(tmp)), \
                mock.patch.object(P, "load_corpus", lambda d, limit=None, scope="all": PAPERS), \
                mock.patch.object(P, "skipped_count", lambda d: 0), \
                mock.patch.object(P, "load_config", lambda: {"model": "fake"}):
            a, b = "sessionAAAA1", "sessionBBBB2"
            P.run("legal", chat_fn=fake_model(log), sid=a)
            self.assertTrue(P.load_result("legal", sid=a)["review"])
            self.assertEqual(P.load_result("legal", sid=b)["review"], "")       # 别人打开是空白
            self.assertIsNone(P.load_result("legal", sid=b)["taxonomy"])
            self.assertEqual(len(P.load_result("legal", sid=b)["cards"]), 4)    # 卡片共用
            self.assertTrue((Path(tmp) / "legal" / "cards.json").exists())
            self.assertFalse((Path(tmp) / "legal" / "review.md").exists())      # 不写到公共目录
            n = len(log)
            P.run("legal", chat_fn=fake_model(log), sid=b)
            self.assertFalse(any("做一张卡片" in t for t in log[n:]))           # 第二个人不用重抽卡
            self.assertTrue(P.forget(a))
            self.assertEqual(P.load_result("legal", sid=a)["review"], "")
            self.assertTrue(P.load_result("legal", sid=b)["review"])

    def test_cleanup_old_sessions(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(P, "OUT_ROOT", Path(tmp)):
            P.touch("oldsession01")
            P.touch("newsession01")
            import os
            old = Path(tmp) / "_sessions" / "oldsession01" / ".seen"
            os.utime(old, (0, 0))
            self.assertEqual(P.cleanup_sessions(), 1)
            self.assertFalse(old.parent.exists())
            self.assertTrue((Path(tmp) / "_sessions" / "newsession01").exists())

    def test_bad_sid_rejected(self):
        with self.assertRaises(ValueError):
            with P.session("../../etc"):
                pass

    def test_week_summary_expires_when_week_rolls_over(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(P, "OUT_ROOT", Path(tmp)), \
                mock.patch.object(P, "load_corpus", lambda d, limit=None, scope="all": WEEK if scope == "week" else PAPERS), \
                mock.patch.object(P, "latest_week", lambda: "2026-10-12"):
            sid = "rolloverSID1"
            with P.session(sid):
                P._write(P.week_dir("legal") / "review.json", {"week": "2026-10-05", "check": {"ok": True}})
                (P.week_dir("legal") / "review.md").write_text("上周的小结", encoding="utf-8")
            r = P.load_result("legal", "week", sid)
            self.assertEqual(r["review"], "")
            self.assertIsNone(r["meta"])

    def test_card_writes_merge(self):
        """两个会话同时抽同一领域的卡，后写的不能把先写的冲掉。"""
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(P, "OUT_ROOT", Path(tmp)):
            path = P.cards_path("legal")
            P._write(path, {"cards": {"9": {"id": 9}}})
            P.make_cards("legal", PAPERS[:1], fake_model([]))
            self.assertEqual(sorted(json.loads(path.read_text(encoding="utf-8"))["cards"]), ["1", "9"])


WEEK = [
    {"id": 5, "title": "StatuteQA", "url": "u5", "date": "2026-10-06",
     "abstract": "StatuteQA asks questions about statutes with citations."},
    {"id": 6, "title": "XDocConflict", "url": "u6", "date": "2026-10-07",
     "abstract": "We build XDocConflict to test cross-document conflicts between master agreements and annexes."},
]

WEEK_BODY = """## 二、本周新论文说明了什么
### 问答与检索
- 法条问答加了引用 [#5]
### 多文件冲突检测
- 「test cross-document conflicts between master agreements and annexes」 [#6]
## 三、和全部综述比
### 新方向
- 多文件冲突检测 [#6]
### 补上了哪些空白
- 跨文件冲突那条空白，#6 做了 [#6]
### 和我们的方向撞车
- 主协议和附件的冲突检测：撞车 [#6]
"""


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
        if "本周新收的论文卡片" in t:
            return json.dumps({"categories": [{"name": "问答与检索", "tests": "", "why": "", "ids": [5]},
                                              {"group": "Agent", "name": "多文件冲突检测", "tests": "主协议和附件对不上", "why": "", "ids": [6]}],
                               "outside": []}, ensure_ascii=False)
        if "本周新论文小结" in t:
            if "程序核对发现这些问题" in t:
                return WEEK_BODY
            return WEEK_BODY.replace("cross-document conflicts between", "conflicts everywhere in")
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
            self.assertIn("## 一、大家在研究什么：3 篇，QA 类 3 篇（2 个主题），Agent 类 0 篇（0 个主题）", md)
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


class WeekTest(unittest.TestCase):
    def _patches(self, tmp):
        return [mock.patch.object(P, "OUT_ROOT", Path(tmp)),
                mock.patch.object(P, "load_corpus",
                                  lambda d, limit=None, scope="all": WEEK if scope == "week" else PAPERS),
                mock.patch.object(P, "latest_week", lambda: "2026-10-05"),
                mock.patch.object(P, "skipped_count", lambda d: 0),
                mock.patch.object(P, "load_config", lambda: {"model": "fake"})]

    def test_week_compares_with_full_review(self):
        log = []
        with tempfile.TemporaryDirectory() as tmp:
            ps = self._patches(tmp)
            for x in ps:
                x.start()
            try:
                P.run("legal", chat_fn=fake_model(log))                 # 先写全部综述
                n = len(log)
                st = P.run("legal", scope="week", chat_fn=fake_model(log))
                self.assertEqual(st["state"], "done")
                week_log = log[n:]
                # 只为本周两篇抽卡，存进共用的 cards.json
                card_calls = [t for t in week_log if "做一张卡片" in t]
                self.assertEqual(len(card_calls), 1)
                self.assertNotIn("#1｜", card_calls[0])
                cards = json.loads((Path(tmp) / "legal" / "cards.json").read_text(encoding="utf-8"))["cards"]
                self.assertEqual(sorted(cards, key=int), ["1", "2", "3", "4", "5", "6"])
                # 分类时带上全部综述的已有类；写小结时带上全部综述的第三、四节
                tax_msg = next(t for t in week_log if "本周新收的论文卡片" in t)
                self.assertIn("- [QA] 问答与检索：答题和找判例", tax_msg)
                week_msg = next(t for t in week_log if "本周新论文小结" in t)
                self.assertIn("## 三、大家还没研究什么", week_msg)
                self.assertIn("## 四、我们能研究什么", week_msg)
                self.assertNotIn("## 二、各类做到哪", week_msg)

                d = Path(tmp) / "legal" / "week"
                tax = json.loads((d / "taxonomy.json").read_text(encoding="utf-8"))
                self.assertEqual({c["name"]: c["new"] for c in tax["categories"]},
                                 {"问答与检索": False, "多文件冲突检测": True})
                md = (d / "review.md").read_text(encoding="utf-8")
                meta = json.loads((d / "review.json").read_text(encoding="utf-8"))
                self.assertTrue(meta["check"]["ok"], meta["check"]["problems"])   # 编的原话被打回改掉了
                self.assertTrue(meta["fixed_once"])
                self.assertIn("## 一、本周新论文分几类：2 篇，QA 类 1 篇（1 个主题），Agent 类 1 篇（1 个主题）；1 个主题是全部综述里没有的", md)
                self.assertIn("| Agent | 多文件冲突检测 | 1 | 新 |", md)
                self.assertLess(md.index("### QA 类"), md.index("### Agent 类"))
                self.assertIn("## 四、这份小结的边界", md)
                self.assertIn("对比用的是", md)
                # 全部综述没被本周小结动过
                self.assertIn("## 一、大家在研究什么：3 篇，QA 类 3 篇", (Path(tmp) / "legal" / "review.md").read_text(encoding="utf-8"))

                r = P.load_result("legal", "week")
                self.assertEqual(r["week"], "2026-10-05")
                self.assertEqual([p["id"] for p in r["papers"]], [5, 6])
                self.assertEqual(sorted(r["cards"], key=int), ["5", "6"])
                self.assertTrue(r["base"]["reviewed"])
                self.assertFalse(r["pending"]["base_newer"])
                self.assertEqual(r["status"]["state"], "done")
                self.assertEqual(P.load_result("legal")["status"]["state"], "done")  # 两块状态分开存

                # 全部综述重写后，小结提示要更新
                P.run("legal", start="review", chat_fn=fake_model(log))
                self.assertTrue(P.load_result("legal", "week")["pending"]["base_newer"])
            finally:
                for x in ps:
                    x.stop()

    def test_week_without_full_review(self):
        log = []
        with tempfile.TemporaryDirectory() as tmp:
            ps = self._patches(tmp)
            for x in ps:
                x.start()
            try:
                P.run("legal", scope="week", chat_fn=fake_model(log))
                tax_msg = next(t for t in log if "本周新收的论文卡片" in t)
                self.assertIn("还没有已有分类", tax_msg)
                self.assertIn("还没有全部综述。", next(t for t in log if "本周新论文小结" in t))
                md = (Path(tmp) / "legal" / "week" / "review.md").read_text(encoding="utf-8")
                self.assertIn("## 一、本周新论文分几类：2 篇，QA 类 1 篇（1 个主题），Agent 类 1 篇（1 个主题）\n", md)
                self.assertIn("还没写全部综述", md)
                self.assertFalse(P.load_result("legal", "week")["base"]["reviewed"])
            finally:
                for x in ps:
                    x.stop()

    def test_week_check_sections(self):
        r = C.check_body(WEEK_BODY, PAPERS + WEEK, None, C.WEEK_SECTIONS)
        self.assertTrue(r["ok"], r["problems"])
        r = C.check_body(WEEK_BODY.split("## 三、")[0], PAPERS + WEEK, None, C.WEEK_SECTIONS)
        self.assertEqual(r["problems"]["missing_sections"], ["三、和全部综述比"])


if __name__ == "__main__":
    unittest.main()

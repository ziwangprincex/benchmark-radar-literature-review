"""综述式 Benchmark 索引、覆盖图与缺口候选。

只定死领域，不定死主题：
  1. 建索引：对每条信号的摘要用正则抽维度（任务 / 输入 / 关注点 / 判分 / 作者自述缺口句）。
  2. 覆盖图：按领域统计 任务 × 输入，格子里有几个 Benchmark、几条需求信号。
  3. 缺口候选：主来源是 Benchmark 作者自述的缺口句，按 (领域, 关注点) 聚类；
     辅来源是覆盖图上"需求≥2、Benchmark≤1"的空格。
  4. 每个缺口生成一张候选卡，写入独立表 gap_candidates，不进 ideas / 周报。

纯正则，不调 API，不装新库。
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from typing import Any

from radar.core.radar_core import db, now_iso, strip_feed_prefix

LIT_VERSION = "lit-v3"
MIN_TEXT = 300  # 短于此长度基本只有标题，抽不出维度

# 只定死领域；候选只在这五个垂类里产出
VERTICALS = ("financial", "legal", "medical", "scientific", "agent")
DOMAIN_CN = {"financial": "金融", "legal": "法律", "medical": "医疗", "scientific": "科研",
             "agent": "Agent", "general": "通用", "unclassified": "未分领域"}

TASKS = {
    "问答": r"question[- ]answer|\bqa\b|answer(ing)? questions|问答",
    "检索": r"retriev|\bsearch|sourcing|检索|搜索",
    "抽取": r"extract|span[- ]|named entit|argument mining|\bmining\b|抽取",
    "分类/识别": r"classif|identif|detect|labell?ing|分类|识别",
    "审查/核查": r"verif|fact[- ]check|audit|review|contradict|consisten|risk ident|claim|审查|核查|校验",
    "生成/撰写": r"generat|summari|draft|writ(e|ing)|report generation|撰写|摘要|生成",
    "推理/计算": r"reason|diagnos|calculat|numerical|\bmath|推理|计算|诊断",
    "Agent任务": r"\bagent|tool[- ]use|brows|navigat|long[- ]horizon|multi[- ]step|computer use|智能体",
    "评判": r"llm[- ]as[- ]a[- ]judge|\bjudge|evaluator|评判",
}

INPUTS = {
    "长文档": r"long[- ](document|context)|\bpdf|10-k|annual report|filing|manuscript|opinions?\b|contracts?\b|full[- ]text|长文档|年报|长上下文",
    "表格": r"\btables?\b|tabular|spreadsheet|表格",
    "多文档/知识库": r"multi[- ]document|cross[- ]document|multiple (documents|sources)|knowledge base|corpus|多文档|知识库",
    "多轮对话": r"multi[- ]turn|dialog|conversation|多轮|对话",
    "工具/环境": r"\btools?\b|\bapis?\b|\bweb\b|browser|environment|sandbox|terminal|\bgui\b|工具|环境",
    "多模态": r"\bimages?\b|visual|video|audio|multimodal|multi-modal|chart|figure|图像|视频",
    "结构化/代码": r"knowledge graph|database|\bsql\b|\bcode\b|graph|知识图谱|代码",
}

# 关注点：缺口"在乎什么"。缺口句按 (领域, 关注点) 聚类，这一维决定候选主题。
CONCERNS = {
    "安全/风险": r"safety|\bsafe\b|harm|adverse|contraindicat|drug[- ]drug|interaction|toxic|"
                 r"high[- ]stakes|patient[- ]specific|(clinical|patient|legal|safety|financial|medication) risk|"
                 r"risk (identif|assess|analys)|clinical(ly)? (use|safe|govern)|"
                 r"govern|安全|禁忌|风险|不良反应|用药",
    "证据/溯源": r"evidence|citation|cite|sourc(e|ing)|traceab|grounded|grounding|attribut|"
                 r"provenance|support(ed|ing)? (by|evidence)|only the final answer|well[- ]founded|证据|引用|溯源",
    "时效/版本": r"temporal|time[- ]sensitiv|up[- ]to[- ]date|outdated|stale|recency|evolving|"
                 r"version|as of|period alignment|时效|版本|过时",
    "数值/计算": r"numeric|numerical|arithmetic|calculat|unit|quantit|数值|计算|单位",
    "鲁棒/扰动": r"robust|perturb|adversarial|fragile|sycophan|sensitiv(e|ity) to|superficial|"
                 r"invarian|鲁棒|扰动|对抗",
    "评判可靠性": r"judge|rater|annotator|agreement|satisfaction|rubric|human evaluation|评判|一致性",
    "评测有效性": r"contaminat|leak|compress|prun|subset|reproduc|leaderboard|ranking|"
                 r"single (leaderboard )?score|what .* measure|metric(s)? (can be|are) misleading|"
                 r"misleading|污染|泄漏|复现",
    "泛化/迁移": r"generaliz|transfer|cross[- ](case|domain|jurisdiction)|out[- ]of[- ]distribution|"
                 r"unfamiliar|local characteristic|region|泛化|迁移",
    "长程/多步": r"long[- ]horizon|multi[- ]step|multi[- ]page|long context|end[- ]to[- ]end|"
                 r"task (success|completion)|长程|多步",
    "推理深度": r"truly reason|reasoning demands|deep reasoning|justify|explain|hypothes|"
                 r"推理|论证",
}

METRICS = {
    "准确率/EM": r"accuracy|exact match|\bem\b|准确率",
    "F1/P/R": r"\bf1\b|precision|recall",
    "Rubric": r"rubric",
    "LLM裁判": r"llm[- ]as[- ]a[- ]judge|gpt-4o? (as|judge)|model[- ]based (judge|evaluation)|judged by",
    "专家/人工": r"expert[- ](annotat|evaluat|review|rat)|human evaluation|annotated by|专家|人工评",
    "执行/成功率": r"pass@|success rate|task completion|executab|成功率",
}

IS_BENCH = re.compile(
    r"benchmark|dataset|corpus|test suite|evaluation suite|leaderboard|基准|评测集|数据集",
    re.I,
)
INTRO_BENCH = re.compile(
    r"(introduce|present|construct|release|propose|build|curate)\w*\b[^.]{0,120}?"
    r"(benchmark|dataset|corpus|test suite|evaluation suite)",
    re.I,
)
EVAL_STUDY = re.compile(
    r"(protocol|framework|method) for (testing|evaluating|measuring)|reusable offline protocol|"
    r"(propose|introduce)\w* an? (new |novel )?([\w-]+ ){0,3}evaluation (pipeline|framework|protocol)|"
    r"\bwe (evaluate|assess|benchmark|test) \d+|evaluate (five|six|seven|eight|ten|\d+) "
    r"(open-weight |proprietary )?(llms|models|systems)|are llms (fragile|robust|able)",
    re.I,
)
SURVEY = re.compile(r"\bsurvey\b|综述", re.I)

GAP_SENT = re.compile(
    r"however|\black|(?<!-)\blimited\b(?!-)|fail(s|ed)? to|struggle|remain(s)? (a |largely |an )?"
    r"(challenge|underexplored|unexplored|unclear|open)|only (evaluate|assess|measure|focus)|"
    r"(evaluate|assess|measure)\w* only|existing (benchmarks|methods|datasets|paradigms|evaluations?)|"
    r"prior (studies|work|benchmarks|methods)|overlook|neglect|\bgap\b|insufficient|"
    r"no (existing|prior)|no benchmark|rarely|obscures|局限|不足|缺乏|尚未|空白",
    re.I,
)
# "To address this gap, we introduce X" 只是在宣布自己，不是缺口本身
SELF_INTRO = re.compile(r"^(to (address|fill|bridge) (this|these|the) gap|in response)", re.I)

DEMAND_RADARS = {"workflow", "product_agent", "model_failure"}


def _hits(table: dict[str, str], low: str) -> list[str]:
    return [k for k, pat in table.items() if re.search(pat, low, re.I)]


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?。！？])\s+", text)
    return [p.strip() for p in parts if 20 <= len(p.strip()) <= 400]


# ---------- Benchmark 名字：从标题/摘要里找专名，找不到就保留论文题目 ----------
# 2026-10-08：原实现取冒号前的部分，"A Benchmark for…"、"Are Benchmarks Reliable?…"
# 这类标题会把整句当名字。现在只认像专名的词（含两个以上大写或驼峰、带 Bench/Eval），
# 普通词、缩写+普通词（Large-Scale、LLM-based）都不算。
GENERIC = {"LLM","LLMS","VLM","VLMS","LVLM","LVLMS","MLLM","MLLMS","AI","3D","4D","2D","EEG","ECG","EMG","OCR","RAG","GUI","HRI","UAV","UAVS","RTK","DRL","OCTA","OCT","NLP","QA","VQA","API","APIS","GPU","CPU","RL","ML","DL","SQL","PDF","LIDAR","RGB","CT","MRI","US","U.S","UK","EU","ASD","AIGC","KG","KGQA","NER","ESG","IR","ASR","TTS","LM","LMS","SOTA","HTML","JSON","URL","IOT","CNN","GNN","SSM","VLA","E2E","OOD","PII","CI","DNA","RNA","SAR","GPS","ROS","LORA","ADC","UI","ID","II","III","IV","FCV","EMN","OSS","AGI","GENAI","NLI","MCP","CLIP","GPT","BERT","LLAVA","DENSENET","SLAM","BEV","HPC","FPGA","RISC-V","IDE","CAD","CFD","PDE","ODE","MOE","RLHF","SFT","DPO","XAI","HCI","AR","VR","XR","TB","COVID-19","ICU","EHR","ICD","FHIR","MCQ","STEM","K-12","ARKTS","BLEU","ROUGE","POI","SOK","AIS","UGC","XR","A2A","YOLO","ICDAR"}
TOKEN = r"[A-Za-z0-9][A-Za-z0-9\-\.\+]*[A-Za-z0-9+]|[A-Za-z0-9]"
def looks_named(tok):
    t = tok.strip(".-+")
    if len(t) < 3 or t.upper() in GENERIC or re.match(r"(?i)^bench(mark\w*)?$", t): return False
    segs = [s for s in re.split(r"[-.+]", t) if s]
    plain = lambda s: re.fullmatch(r"[A-Z]?[a-z]+|[0-9]+", s) is not None
    special = [s for s in segs if not plain(s) and s.upper() not in GENERIC]
    # 普通词或"缩写+普通词"（Large-Scale、LLM-based、GPS-Denied）不是名字
    if not special: return False
    if len(segs) > 1 and any(plain(s) and s[0].islower() for s in segs) and not re.search(r"(?i)bench|eval|gym|arena", t): return False
    return True
BAD_HEAD = re.compile(r"^(a|an|the|on|towards?|how|do|does|can|what|why|is|are|when|beyond|benchmarking|evaluating|rethinking|revisiting|from|learning|scaling|building|toward)\b", re.I)
def bench_name(title, body=""):
    title = re.sub(r"\s+", " ", title.replace("{","").replace("}","")).strip()
    if ":" in title:
        head = title.split(":")[0].strip()
        if len(head) <= 40 and "?" not in head and not BAD_HEAD.match(head) and len(head.split()) <= 4 and any(looks_named(w) for w in head.split()) :
            return head, True
    m = re.search(r"\b(?:we|this paper|this work)\s+(?:introduce|present|propose|release|construct|build|curate|contribute)s?\s+(?:the\s+|a\s+|an\s+)?(?:new\s+|novel\s+)?(" + TOKEN + r")", body, re.I)
    if m and looks_named(m.group(1)):
        return m.group(1), True
    for m in re.finditer(TOKEN, title):
        if looks_named(m.group()):
            return m.group(), True
    return title, False


def _bench_name(title: str, body: str = "") -> str:
    return bench_name(title, body)[0]


ARXIV_ID = re.compile(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})", re.I)


def dedup_key(title: str, url: str) -> str:
    """同一篇论文的不同版本（v1/v2）或不同采集源，合成一条。"""
    m = ARXIV_ID.search(url or "")
    return f"arxiv:{m.group(1)}" if m else "t:" + re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).strip()


def classify_role(radar: str, title: str, body: str) -> str:
    if radar in DEMAND_RADARS:
        return "demand"
    if radar != "benchmark":
        return "other"
    if SURVEY.search(title):
        return "not_benchmark"
    if IS_BENCH.search(title) or INTRO_BENCH.search(body) or EVAL_STUDY.search(f"{title}. {body}"):
        return "benchmark"
    return "not_benchmark"  # benchmark 采集源里的方法/模型论文


def analyze(radar: str, title: str, content: str) -> dict[str, Any]:
    body = strip_feed_prefix(content)
    text = f"{title}. {body}"
    low = text.lower()
    too_short = len(body) < MIN_TEXT
    gaps = []
    if not too_short:
        for s in _sentences(body):
            if GAP_SENT.search(s) and not SELF_INTRO.search(s):
                gaps.append({"text": s, "concerns": _hits(CONCERNS, s.lower())})
    return {
        "role": classify_role(radar, title, body),
        "name": _bench_name(title, body),
        "named": bench_name(title, body)[1],
        "tasks": _hits(TASKS, low),
        "inputs": _hits(INPUTS, low),
        "concerns": _hits(CONCERNS, low),
        "metrics": _hits(METRICS, low) or ["未知"],
        "gap_sentences": gaps[:5],
        "text_len": len(body),
        "too_short": too_short,
    }


JSON_COLS = ("tasks", "inputs", "concerns", "metrics", "gap_sentences")


def ensure_tables(conn) -> None:
    conn.execute("DROP TABLE IF EXISTS lit_index")  # 派生表，每次全量重建
    conn.execute(
        """CREATE TABLE lit_index (
            source_item_id INTEGER PRIMARY KEY REFERENCES source_items(id) ON DELETE CASCADE,
            radar TEXT NOT NULL, domain TEXT NOT NULL, role TEXT NOT NULL, name TEXT NOT NULL,
            tasks_json TEXT NOT NULL, inputs_json TEXT NOT NULL, concerns_json TEXT NOT NULL,
            metrics_json TEXT NOT NULL, gap_sentences_json TEXT NOT NULL,
            text_len INTEGER NOT NULL, too_short INTEGER NOT NULL,
            version TEXT NOT NULL, built_at TEXT NOT NULL)"""
    )
    conn.execute("DROP TABLE IF EXISTS gap_candidates")
    conn.execute(
        """CREATE TABLE gap_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL, concern TEXT NOT NULL, name TEXT NOT NULL,
            origin TEXT NOT NULL, status TEXT NOT NULL,
            bench_support INTEGER NOT NULL, demand_support INTEGER NOT NULL,
            card_json TEXT NOT NULL, version TEXT NOT NULL, built_at TEXT NOT NULL)"""
    )


def build_index() -> dict[str, int]:
    stats: Counter = Counter()
    with db() as conn:
        ensure_tables(conn)
        rows = conn.execute(
            """SELECT s.id, s.radar, s.title, s.content, s.raw_json, g.domain, COALESCE(s.canonical_url, s.url) AS url
               FROM source_items s JOIN signals g ON g.source_item_id = s.id
               WHERE s.validation_status NOT IN ('invalid', 'context_only')
                 AND s.source_quality != 'ai_generated'
               ORDER BY s.id DESC"""  # 新版本在前，旧版本被判为重复
        ).fetchall()
        ts = now_iso()
        seen: set[str] = set()
        for r in rows:
            a = analyze(r["radar"], r["title"], r["content"])
            if a["role"] == "demand":
                # 判例库、职业任务表在导入时已按结构化字段给了关注点（raw_data.concerns），
                # 原文里的 Judge（法官）、Adverse Costs Order、government 会被关键词误判
                pre_raw = json.loads(r["raw_json"] or "{}").get("raw_data") or {}
                pre = pre_raw.get("concerns")
                if pre is not None:
                    a["concerns"] = [c for c in pre if c in CONCERNS]
                    # 任务/输入同理：判决原文、职业任务全文会命中一堆无关任务词，
                    # 生成"N 条需求涉及 X×Y 却没有 Benchmark"的假空格
                    a["tasks"] = [t for t in pre_raw.get("tasks", []) if t in TASKS]
                    a["inputs"] = [i for i in pre_raw.get("inputs", []) if i in INPUTS]
            if a["role"] == "benchmark":
                k = dedup_key(r["title"], r["url"])
                if k in seen:
                    a["role"] = "duplicate"
                seen.add(k)
            conn.execute(
                "INSERT INTO lit_index VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (r["id"], r["radar"], r["domain"], a["role"], a["name"],
                 *(json.dumps(a[k], ensure_ascii=False) for k in JSON_COLS),
                 a["text_len"], int(a["too_short"]), LIT_VERSION, ts),
            )
            stats[a["role"]] += 1
            stats["too_short"] += int(a["too_short"])
    return dict(stats)


def load_index(conn) -> list[dict[str, Any]]:
    out = []
    rows = conn.execute(
        """SELECT l.*, s.title AS full_title, COALESCE(s.canonical_url, s.url) AS url
           FROM lit_index l JOIN source_items s ON s.id = l.source_item_id"""
    ).fetchall()
    for r in rows:
        d = dict(r)
        for k in JSON_COLS:
            d[k] = json.loads(d.pop(f"{k}_json"))
        out.append(d)
    return out


def usable(e: dict[str, Any]) -> bool:
    if e["role"] == "benchmark":
        return not e["too_short"]
    if e["role"] == "demand":
        return bool(e["tasks"] or e["concerns"])  # 需求信号只要标题能判出东西就算
    return False


def coverage(entries: list[dict[str, Any]]) -> dict:
    """domain -> (task, input) -> {"bench": [...], "demand": [...]}"""
    grid: dict = defaultdict(lambda: defaultdict(lambda: {"bench": [], "demand": []}))
    for e in entries:
        if not usable(e) or not e["tasks"]:
            continue
        key = "bench" if e["role"] == "benchmark" else "demand"
        for t in e["tasks"]:
            for i in e["inputs"] or ["(输入未识别)"]:
                grid[e["domain"]][(t, i)][key].append(e)
    return grid


def _top(counter: Counter, n: int = 2) -> list[str]:
    return [k for k, _ in counter.most_common(n)]


# 关注点 -> 判分建议（模板，不调 API）
SCORING_HINT = {
    "安全/风险": "以漏报率为主指标（高风险项召回），误报率为辅；专家 rubric 标注风险等级",
    "证据/溯源": "答案正确率与证据定位（页/条款/句级）命中率分开计分，禁止只看最终答案",
    "时效/版本": "按时间切片出题，同题不同截止日期对照；过时答案单独计为错误类型",
    "数值/计算": "数值按容差判对，单位与口径错误单列",
    "鲁棒/扰动": "原题与扰动题（改格式/插误导证据/改措辞）成对出现，计一致率与翻转率",
    "评判可靠性": "判分结果与真实任务成功率做相关与一致性检验（kappa / Spearman）",
    "评测有效性": "对照完整评测与压缩/替代评测的模型排名一致性（Kendall τ），指标拆解到错误类型",
    "泛化/迁移": "域内 vs 域外（跨地区/跨案件/跨机构）分组计分，报告差值",
    "长程/多步": "端到端完成率 + 步骤级错误定位（检索/证据使用/规则遵循分开记）",
    "推理深度": "最终答案 + 推理过程 rubric（是否由证据推出），过程分与结果分分开报",
}


def _ref(e: dict[str, Any]) -> dict[str, Any]:
    return {"source_item_id": e["source_item_id"], "name": e["name"],
            "title": e.get("full_title") or e["name"], "url": e.get("url") or ""}


NEAR_K = 6
NEAR_MIN = 0.15        # 同领域最低相似度
NEAR_MIN_OTHER = 0.35  # 跨领域要明显更像才算（0.25 时交通图像会挂到科研下）
DEMAND_MIN = 0.22      # 论文外旁证门槛；0.15 时“推理性能评测”会挂到手机 Agent 下


def _nearby(items: list[tuple[dict, str]], exclude: set[int], sim) -> list[dict[str, Any]]:
    """每句作者原话（加上它所在论文的标题定主题）去全库比相似度，取最像的 Benchmark。

    2026-10-08 之前是“同领域、关注点标签有交集”的前 6 个，按入库顺序取，
    结果「医疗·安全/风险」下挂的是空间转录组、结肠镜重建，MEDEC 反而挂不上。
    """
    if sim is None:
        return []
    best: dict[int, dict[str, Any]] = {}
    dom = items[0][0]["domain"] if items else ""
    for b, text in items:
        q = f"{text} {sim.titles.get(b['source_item_id'], '')}"
        for sid, sc in sim.rank(q, 15):
            if sid in exclude:
                continue
            same = sim.domains.get(sid) == dom
            if sc < (NEAR_MIN if same else NEAR_MIN_OTHER):
                continue
            # 跨领域只靠一个词撞上的不算（网络 traffic 对上道路 traffic）
            if not same and len(set(_toks(q)) & set(_toks(sim.titles.get(sid, "")))) < 2:
                continue
            if sid not in best or sc > best[sid]["score"]:
                best[sid] = {"source_item_id": sid, "score": round(sc, 3), "same_domain": same,
                             "near_quote_from": b["name"]}
    ranked = sorted(best.values(), key=lambda x: -x["score"])[:NEAR_K]
    return ranked


# 结果句不是缺口：“我们的方法达到 71.85%”“结果表明…”只是在报成绩
RESULT_SENT = re.compile(
    r"outperform|achiev(e|es|ed|ing)\b|yields?\b|best[- ]performing|state-of-the-art|"
    r"we (find|show|demonstrate|observe)|results (show|indicate|reveal|confirm)|"
    r"(our|the proposed) (method|framework|model)", re.I)
GAP_WORDS = re.compile(r"lack|underexplored|unexplored|overlook|neglect|existing (bench|eval|dataset)|"
                       r"most (bench|eval)|prior (bench|work|stud)", re.I)
GAP_TH = 0.2  # 两组原话平均相似度高于此才合并；0.25 时 MedCalc 两篇合不上，0.15 时开始拼凑


def quote_key(sid: int, text: str) -> str:
    import hashlib
    return f"{sid}:{hashlib.sha1(text.strip().encode('utf-8')).hexdigest()[:8]}"


def _is_gap_quote(text: str) -> bool:
    return not (RESULT_SENT.search(text) and not GAP_WORDS.search(text))


def _quote_groups(benches: list[dict], sim) -> list[list[tuple[dict, str]]]:
    """按原话本身的相似度做平均链接聚类（2026-10-08 起取代按关注点标签分组）。

    旧做法把所有命中 safety 一类词的原话装进一张卡，29 张卡里 23 张的原话两两几乎不相似。
    每句原话带上所在论文的标题定主题；同一篇论文的多句话只算一篇支撑。"""
    import math
    Q = [(b, g["text"]) for b in benches for g in b["gap_sentences"] if _is_gap_quote(g["text"])]
    if not Q:
        return []
    title = (lambda b: sim.titles.get(b["source_item_id"], "")) if sim else (lambda b: b.get("full_title") or b["name"])
    tfs = [Counter(_toks(f"{t} {title(b)}")) for b, t in Q]
    if sim:
        idf = sim.idf
    else:  # 单元测试无库：用原话自身算 idf
        df = Counter(w for tf in tfs for w in tf)
        idf = {w: math.log(len(Q) / c) + 1 for w, c in df.items()}
    V = [_Similar._norm({w: c * idf.get(w, 0) for w, c in tf.items() if w in idf}) for tf in tfs]

    def cos(x, y):
        if len(x) > len(y):
            x, y = y, x
        return sum(v * y.get(w, 0) for w, v in x.items())

    n = len(Q)
    S = [[cos(V[i], V[j]) for j in range(n)] for i in range(n)]
    C = [[i] for i in range(n)]
    while True:
        best, pair = GAP_TH, None
        for x in range(len(C)):
            for y in range(x + 1, len(C)):
                s = sum(S[i][j] for i in C[x] for j in C[y]) / (len(C[x]) * len(C[y]))
                if s > best:
                    best, pair = s, (x, y)
        if not pair:
            break
        x, y = pair
        C[x] += C[y]
        del C[y]
    out = []
    for c in C:
        # 代表句：与组内其他句平均最像的一句
        rep = max(c, key=lambda i: sum(S[i][j] for j in c))
        out.append([Q[rep]] + [Q[i] for i in c if i != rep])
    return out


def _gap_clusters(dom: str, benches: list[dict], demands: list[dict], sim=None) -> list[dict[str, Any]]:
    kind_rank = {"model_failure": 0, "workflow": 1, "product_agent": 2}
    dsim = getattr(sim, "demand_sim", None)
    out = []
    for items in _quote_groups(benches, sim):
        srcs = {b["source_item_id"]: b for b, _ in items}
        concerns = [c for c, _ in Counter(c for b, t in items for g in b["gap_sentences"]
                                          if g["text"] == t for c in g["concerns"]).most_common(2)]
        # 论文外旁证也按相似度找，不再按关注点标签
        dem = []
        if dsim:
            q = " ".join(f"{t} {sim.titles.get(b['source_item_id'], '')}" for b, t in items[:4])
            ok = {d["source_item_id"] for d in demands}
            dem = [dsim.entries[sid] for sid, sc in dsim.rank(q, 10) if sc >= DEMAND_MIN and sid in ok]
        dem.sort(key=lambda d: kind_rank.get(d["radar"], 3))
        tasks = Counter(t for b in srcs.values() for t in b["tasks"])
        inputs = Counter(i for b in srcs.values() for i in b["inputs"])
        metrics = Counter(m for b in srcs.values() for m in b["metrics"] if m != "未知")
        covering = _nearby(items, set(srcs), sim)
        out.append({
            "domain": dom, "concern": concerns[0] if concerns else "-", "concerns": concerns,
            "origin": "缺口句",
            "name": f"{DOMAIN_CN[dom]} · " + " / ".join(b["name"] for b in list(srcs.values())[:3]),
            "problem": items[0][1],
            "quote_keys": sorted(quote_key(b["source_item_id"], t) for b, t in items),
            "tasks": _top(tasks, 3), "inputs": _top(inputs, 3),
            "existing_metrics": _top(metrics, 3),
            "scoring_hint": [SCORING_HINT[c] for c in concerns],
            "bench_support": len(srcs), "demand_support": len(dem),
            "demand_kinds": dict(Counter(d["radar"] for d in dem)),
            "gap_quotes": [{"bench": b["name"], "source_item_id": b["source_item_id"],
                            "url": b.get("url") or "", "text": t} for b, t in items[:8]],
            "supporting_benchmarks": [_ref(b) for b in srcs.values()],
            "demand_examples": [_ref(d) for d in dem[:5]],
            "nearby_benchmarks": [{**_ref(sim.entries[n["source_item_id"]]), **n} for n in covering],
        })
    return out

def _cell_cards(dom: str, es: list[dict]) -> list[dict[str, Any]]:
    out = []
    for (t, i), v in coverage(es).get(dom, {}).items():
        dem = {d["source_item_id"]: d for d in v["demand"]}
        if len(dem) < 2 or len(v["bench"]) > 1 or "未识别" in i:
            continue
        out.append({
            "domain": dom, "concern": "-", "concerns": [], "origin": "覆盖空格",
            "name": f"{DOMAIN_CN[dom]} · {t}（{i}）：现有 Benchmark {len(v['bench'])} 个",
            "problem": f"{DOMAIN_CN[dom]}领域有 {len(dem)} 条需求信号涉及 {t} × {i}，"
                       f"但只找到 {len(v['bench'])} 个对应 Benchmark。",
            "tasks": [t], "inputs": [i], "existing_metrics": [], "scoring_hint": [],
            "bench_support": len(v["bench"]), "demand_support": len(dem),
            "gap_quotes": [], "supporting_benchmarks": [],
            "demand_examples": [_ref(d) for d in list(dem.values())[:5]],
            "nearby_benchmarks": [_ref(b) for b in v["bench"]],
        })
    return out


def build_candidates(entries: list[dict[str, Any]], sim=None) -> list[dict[str, Any]]:
    """第 3、4 步：缺口句按 (领域, 关注点) 聚类为主，覆盖图空格为辅。

    sim 为全库 Benchmark 的相似度索引；不给就不填附近 Benchmark（单元测试里无库）。"""
    by_dom = defaultdict(list)
    for e in entries:
        if usable(e) and e["domain"] in VERTICALS:
            by_dom[e["domain"]].append(e)

    cards: list[dict[str, Any]] = []
    for dom, es in by_dom.items():
        benches = [e for e in es if e["role"] == "benchmark"]
        demands = [e for e in es if e["role"] == "demand"]
        cards += _gap_clusters(dom, benches, demands, sim)
        cards += _cell_cards(dom, es)

    for c in cards:
        # 覆盖空格只说明"没人做"，不说明"值得做"，一律只进观察
        # 至少两篇不同论文的作者说过同一件事才进候选；单篇只进观察
        strong = c["origin"] == "缺口句" and c["bench_support"] >= 2
        c["status"] = "候选" if strong else "观察"
        c["next_step"] = (
            f"人工读 {c['bench_support']} 篇支撑 Benchmark 原文，确认缺口没被后续工作填上；"
            "再抽 20 题做 Mini Eval" if strong else "等更多缺口句或需求信号出现后再评估")
    cards.sort(key=lambda c: (c["status"] != "候选", c["origin"] != "缺口句",
                              -(c["bench_support"] * 2 + c["demand_support"])))
    return cards


def _map_old_ideas(conn, cards: list[dict[str, Any]]) -> None:
    """与现有非 superseded Idea 做来源 URL 对照，只做标注，不改 ideas 表。"""
    ideas = []
    for r in conn.execute(
        "SELECT id, idea_name, domain, source_refs_json FROM ideas WHERE status != 'superseded'"
    ).fetchall():
        urls = {x.get("url") for x in json.loads(r["source_refs_json"] or "[]") if x.get("url")}
        ideas.append((r["id"], r["idea_name"], r["domain"], urls))
    for c in cards:
        urls = {x["url"] for k in ("supporting_benchmarks", "demand_examples") for x in c[k] if x["url"]}
        c["old_ideas"] = [
            {"id": i, "name": n, "shared_sources": len(urls & u)}
            for i, n, d, u in ideas if d == c["domain"] and urls & u
        ]
        c["old_ideas"].sort(key=lambda x: -x["shared_sources"])


def build_all() -> dict[str, Any]:
    stats = build_index()
    with db() as conn:
        entries = load_index(conn)
        sim = _Similar(conn, [e for e in entries if e["role"] == "benchmark" and usable(e)])
        sim.demand_sim = _Similar(conn, [e for e in entries if e["role"] == "demand" and usable(e)])
        cards = build_candidates(entries, sim)
        _map_old_ideas(conn, cards)
        ts = now_iso()
        for c in cards:
            conn.execute(
                """INSERT INTO gap_candidates (domain, concern, name, origin, status, bench_support,
                   demand_support, card_json, version, built_at) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (c["domain"], c["concern"], c["name"], c["origin"], c["status"], c["bench_support"],
                 c["demand_support"], json.dumps(c, ensure_ascii=False), LIT_VERSION, ts),
            )
    stats["candidates"] = len(cards)
    stats["strong"] = sum(c["status"] == "候选" for c in cards)
    return stats


def load_cards() -> list[dict[str, Any]]:
    with db() as conn:
        return [json.loads(r[0]) for r in conn.execute("SELECT card_json FROM gap_candidates ORDER BY id")]


def _link(ref: dict[str, Any]) -> str:
    return f"[{ref['name']}]({ref['url']})" if ref.get("url", "").startswith("http") else ref["name"]


def render_cards(path, cards: list[dict[str, Any]]) -> None:
    strong = [c for c in cards if c["status"] == "候选"]
    watch = [c for c in cards if c["status"] != "候选"]
    L = [f"# Benchmark 缺口候选卡（{LIT_VERSION}，{now_iso()[:10]}）", "",
         "生成方式：只定死五个垂类领域；从 Benchmark 摘要中抽取作者自述缺口句，按“领域 × 关注点”聚类，"
         "需求信号只用真实外部来源（不含系统自生成种子）。纯正则，不调 API。", "",
         f"共 {len(cards)} 张：候选 {len(strong)} 张，观察 {len(watch)} 张。", "",
         "## 候选", ""]
    for n, c in enumerate(strong, 1):
        L += [f"### C{n}. {c['name']}", "",
              f"- 问题：{c['problem']}",
              f"- 任务：{'、'.join(c['tasks']) or '待定'}；输入：{'、'.join(c['inputs']) or '待定'}",
              f"- 支撑：Benchmark {c['bench_support']} 篇，真实需求信号 {c['demand_support']} 条"]
        if c["existing_metrics"]:
            L.append(f"- 现有 Benchmark 用的判分：{'、'.join(c['existing_metrics'])}")
        for h in c["scoring_hint"]:
            L.append(f"- 判分建议：{h}")
        if c["old_ideas"]:
            L.append("- 对应旧 Idea：" + "、".join(f"#{o['id']} {o['name']}" for o in c["old_ideas"]))
        else:
            L.append("- 对应旧 Idea：无（新方向）")
        L.append(f"- 下一步：{c['next_step']}")
        L += ["", "作者自述缺口："]
        L += [f"> [{q['bench']}] {q['text']}" + "\n>" for q in c["gap_quotes"][:4]]
        L.append("")
        if c["supporting_benchmarks"]:
            L.append("支撑 Benchmark：" + "、".join(_link(r) for r in c["supporting_benchmarks"]))
        if c["demand_examples"]:
            L.append("需求信号：" + "、".join(_link(r) for r in c["demand_examples"]))
        if c["nearby_benchmarks"]:
            L.append("邻近已覆盖（需对比差异）：" + "、".join(_link(r) for r in c["nearby_benchmarks"]))
        L.append("")
    L += ["## 观察", "", "| # | 名称 | 来源 | B | 需求 | 对应旧 Idea |", "|---|---|---|---|---|---|"]
    for n, c in enumerate(watch, 1):
        old = "、".join(f"#{o['id']}" for o in c["old_ideas"]) or "-"
        L.append(f"| W{n} | {c['name']} | {c['origin']} | {c['bench_support']} | {c['demand_support']} | {old} |")
    L.append("")
    path.write_text("\n".join(L), encoding="utf-8")


def render_report(path) -> None:
    """覆盖图（附表），保留给人工核查。"""
    with db() as conn:
        entries = load_index(conn)
    grid = coverage(entries)
    inputs = list(INPUTS) + ["(输入未识别)"]
    L = [f"# Benchmark 覆盖图（{LIT_VERSION}，{now_iso()[:10]}）", "",
         "格子写法：`B数/需求数`。只统计摘要够长的 Benchmark 和真实外部需求信号。", ""]
    for dom in VERTICALS:
        cells = grid.get(dom)
        if not cells:
            continue
        L += [f"## {DOMAIN_CN[dom]}", "", "| 任务 \\ 输入 | " + " | ".join(inputs) + " |",
              "|" + "---|" * (len(inputs) + 1)]
        for t in [t for t in TASKS if any(k[0] == t for k in cells)]:
            L.append(f"| {t} | " + " | ".join(
                f"{len(cells[(t, i)]['bench'])}/{len(cells[(t, i)]['demand'])}" if (t, i) in cells else "·"
                for i in inputs) + " |")
        L.append("")
    path.write_text("\n".join(L), encoding="utf-8")


def run(base_dir) -> dict[str, Any]:
    """一条命令出全部产物：DB 表 + JSON + 两份 Markdown。"""
    from pathlib import Path
    base = Path(base_dir)
    stats = build_all()
    cards = load_cards()
    (base / "outputs").mkdir(exist_ok=True)
    (base / "reports").mkdir(exist_ok=True)
    out_json = base / "outputs" / "gap_candidates.json"
    out_json.write_text(json.dumps({"version": LIT_VERSION, "built_at": now_iso(), "cards": cards},
                                   ensure_ascii=False, indent=2), encoding="utf-8")
    render_cards(base / "reports" / "gap_candidates.md", cards)
    render_report(base / "reports" / "lit_coverage.md")
    stats["outputs"] = [str(out_json), str(base / "reports" / "gap_candidates.md"),
                        str(base / "reports" / "lit_coverage.md")]
    return stats


# ---------- 研究地图：在研究什么 / 还没研究什么 / 我们能研究什么 ----------

# 关注点的大白话：缺口是什么
CONCERN_GAP = {
    "安全/风险": "高风险场景下模型会不会漏掉关键风险，还没被系统地测",
    "证据/溯源": "现有评测大多只判答案对不对，不判引用的证据是否真的支撑结论",
    "时效/版本": "答案是否用了过时信息、是否对齐时间点，基本没人测",
    "数值/计算": "数值、单位、口径类错误没有单独测",
    "鲁棒/扰动": "换个格式、塞一条误导证据，模型就翻车，现有评测不测这种稳定性",
    "评判可靠性": "现在的打分方式（LLM 裁判、满意度、一致性指标）本身可能不可信",
    "评测有效性": "评测分数高不代表能力强：指标会误导、评测集可能被污染或压缩失真",
    "泛化/迁移": "换地区、换案件、换机构后模型还行不行，没人测",
    "长程/多步": "只看最终结果，定位不到是检索、用证据还是遵循规则哪一步错了",
    "推理深度": "模型是真的从证据推出来，还是只生成听起来合理的答案，分不清",
}

# 关注点对应"我们可以测什么"
CONCERN_TODO = {
    "安全/风险": "专测高风险项的漏报",
    "证据/溯源": "答案和证据定位分开判分",
    "时效/版本": "同一问题按不同时间点出题",
    "数值/计算": "数值、单位、口径错误单独计分",
    "鲁棒/扰动": "原题和扰动题成对出，看答案翻不翻",
    "评判可靠性": "检验打分结果和真实任务成败是否一致",
    "评测有效性": "检验评测分数和真实能力是否一致",
    "泛化/迁移": "域内和域外分组出题，看掉多少",
    "长程/多步": "端到端任务，逐步记录错在哪一步",
    "推理深度": "推理过程和最终答案分开打分",
}


def _what_it_tests(e: dict[str, Any]) -> str:
    t = "、".join(e["tasks"][:2]) or "综合题库"
    i = "、".join(e["inputs"][:2])
    return f"{t}" + (f"（{i}）" if i else "")


# 垂类之外 Benchmark 的领域标签（纯正则，按顺序命中第一条）
OTHER_DOMAIN_RULES = [
    (r"\bmath|theorem|conjecture|erd.s|geometry problem", "数学"),
    (r"telecom|wireless|5g\b|6g\b|network traffic", "通信/网络"),
    (r"fact-?check|factuality|fake news|propaganda|misinformation|hallucinat", "事实核查"),
    (r"jailbreak|moderation|harm|unlearning|privacy|adversarial|attack|safety|red[- ]team|secur", "安全"),
    (r"code generation|programming|\bcode\b|software|test suites?\b|compiler|\bisa\b|verilog", "代码"),
    (r"eeg|ecg|emg|brain|neuron|physiolog", "脑电/生物信号"),
    (r"time[- ]series|forecast|predictive maintenance|sensor", "时序/传感器"),
    (r"lidar|odometry|slam|point cloud|\b3d\b|depth estimation|localization|autonomous driving|trajector", "3D/自动驾驶"),
    (r"robot|manipulation|embodied|navigation|reinforcement learning|\brl\b", "机器人/具身"),
    (r"video", "视频"),
    (r"music|melod|audio|auditory|waveform|speech|sound", "音频/音乐"),
    (r"\bocr\b|manuscript|handwrit|document|table|chart", "文档/OCR"),
    (r"image|vision|visual|vlm|segmentation|detection|drawing|animat", "视觉"),
    (r"cultur|multilingual|low-resource|arabic|chinese|japanese|korean|indic|african|polish|\bregion", "多语言/文化"),
    (r"learner|student|tutor|educat|classroom", "教育"),
    (r"persona|dialog|conversation|companion|social|slang|subreddit", "对话/社交"),
    (r"retriev|recommend|search engine|ranking|\brag\b", "检索/推荐"),
    (r"memory|long[- ]context", "记忆/长上下文"),
    (r"tool[- ]use|function call", "工具调用"),
    (r"peer[- ]review|occupation|professional knowledge|exam", "职业/考试"),
    (r"inference|throughput|latency|serving|cloud|gpu|kernel", "系统/推理性能"),
    (r"contaminat|benchmark exposure|judge|rater|leaderboard|metric|evaluation protocol|annotat", "评测方法"),
    (r"reasoning|planning|puzzle|logic", "推理"),
]

def _other_domain(title: str, text: str) -> str:
    # 先只看标题，标题判不出再看摘要，避免摘要里顺带一提的词抢标签
    for src in (title.lower(), text.lower()):
        for pat, label in OTHER_DOMAIN_RULES:
            if re.search(pat, src):
                return label
    return "通用"

def other_benchmarks(conn, entries) -> list[dict[str, Any]]:
    out = []
    for e in entries:
        if e["domain"] in VERTICALS or e["role"] != "benchmark":
            continue
        row = conn.execute("SELECT title, content FROM source_items WHERE id=?", (e["source_item_id"],)).fetchone()
        title = (row[0] if row else "") or e.get("full_title") or e["name"]
        title = title.replace("\\H{o}", "ő").replace("{", "").replace("}", "")
        name, named = bench_name(title, strip_feed_prefix(row[1]) if row else "")
        out.append({"name": name, "named": named, "title": title,
                    "domain": _other_domain(title, (row[1] if row else "")[:600]),
                    "url": e.get("url") or ""})
    # 版本去重已在 build_index 里按 arXiv 编号做过，这里只防同名
    seen, uniq = set(), []
    for b in out:
        k = b["title"].lower().strip()
        if k not in seen:
            seen.add(k)
            uniq.append(b)
    return sorted(uniq, key=lambda x: (x["domain"], not x["named"], x["name"].lower()))


def load_labels() -> list[dict[str, Any]]:
    """人工判定的缺口标签：data/gap_labels.json。"""
    from pathlib import Path
    p = Path(__file__).resolve().parents[2] / "data" / "gap_labels.json"
    return json.loads(p.read_text(encoding="utf-8"))["labels"] if p.exists() else []


def match_label(card: dict[str, Any], labels: list[dict[str, Any]]) -> dict[str, Any] | None:
    """分组会随新资料变动：原话重合至少一半就沿用标签，否则视为新分组、等人重新判定。"""
    keys = set(card.get("quote_keys", []))
    best, score = None, 0.0
    for lab in labels:
        if lab["domain"] != card["domain"]:
            continue
        lk = set(lab["quote_keys"])
        ov = len(keys & lk) / max(len(keys), len(lk), 1)
        if ov > score:
            best, score = lab, ov
    return best if score >= 0.5 else None


def research_map() -> dict[str, Any]:
    with db() as conn:
        entries = load_index(conn)
        others = other_benchmarks(conn, entries)
        review_meta, directions, already = load_directions(conn, entries)
    cards = load_cards()
    labels = load_labels()
    dir_title = {x["id"]: {"id": x["id"], "title": x["title"]} for x in directions}
    gap_of = {l["direction"]: l["title"] for l in labels if l.get("direction")}
    for x in directions:
        x["gap"] = gap_of.get(x["id"])  # None = 缺口只有单篇论文说过，没进中栏
    out = []
    for dom in VERTICALS:
        benches = [e for e in entries if e["domain"] == dom and e["role"] == "benchmark" and usable(e)]
        demands = [e for e in entries if e["domain"] == dom and e["role"] == "demand" and usable(e)]
        dcards = [c for c in cards if c["domain"] == dom]
        gap_cards = [c for c in dcards if c["origin"] == "缺口句"]

        hot = Counter(t for b in benches for t in b["tasks"]).most_common(4)
        researched = {
            "summary": f"找到 {len(benches)} 个 Benchmark，主要在测" +
                       ("、".join(f"{t}（{n}）" for t, n in hot) if hot else "（暂无）"),
            "items": [{"name": b["name"], "url": b.get("url") or "", "title": b.get("full_title") or b["name"],
                       "tests": _what_it_tests(b)} for b in benches],
        }

        not_yet, excluded, unlabeled = [], Counter(), 0
        for c in gap_cards:
            if c["status"] != "候选":
                excluded["单篇"] += 1  # 只有一篇论文说过，不上地图
                continue
            lab = match_label(c, labels)
            if lab and lab["verdict"] in ("拼凑", "只缺数据"):
                excluded[lab["verdict"]] += 1
                continue
            if not lab:
                unlabeled += 1
            seen, who = set(), []
            for q in c["gap_quotes"]:
                if q["bench"] not in seen and len(who) < 4:
                    seen.add(q["bench"])
                    who.append({"name": q["bench"], "url": q.get("url", ""), "quote": q["text"]})
            not_yet.append({
                "gap": lab["title"] if lab else "（还没人工判定）" + c["problem"][:90],
                "kind": lab["verdict"] if lab else "未判定",
                # 提出缺口的论文自己做完之后还剩什么没测；空 = 已被这些论文补上
                "left_open": lab.get("left_open", "") if lab else "",
                "open": bool(lab and lab.get("left_open")) or not lab,
                "direction": dir_title.get(lab.get("direction")) if lab else None,
                "finding": lab.get("finding", "") if lab else "",
                "who_said": who,
                "papers": c["bench_support"],
                # 论文之外的旁证：专家工作流、产品动态、AI 犯错记录里说到同一件事的条数（按相似度找）
                "outside": c["demand_support"],
                "outside_kinds": {"failure": c.get("demand_kinds", {}).get("model_failure", 0),
                                  "workflow": c.get("demand_kinds", {}).get("workflow", 0),
                                  "product": c.get("demand_kinds", {}).get("product_agent", 0)},
                "outside_examples": [{"name": x["title"][:60], "url": x["url"]} for x in c.get("demand_examples", [])[:3]],
                # 最像的已有 Benchmark：缺口可能已被它们填上，需要人看
                "nearby": [{"name": n["name"], "title": n.get("title", n["name"]), "url": n.get("url", ""),
                            "score": n.get("score"), "same_domain": n.get("same_domain", True)}
                           for n in c.get("nearby_benchmarks", [])[:5]],
                "strong": bool(lab),
            })
        # 测出模型做不好的排最前，其次评测没覆盖，没判定的最后；同类按支撑论文数
        order = {"能力缺陷": 0, "评测没覆盖": 1}
        not_yet.sort(key=lambda g: (not g["open"], order.get(g["kind"], 2), -g["papers"], -g["outside"]))
        blank = [c["name"].split("·", 1)[-1].split("：")[0].strip() for c in dcards if c["origin"] == "覆盖空格"]

        can_do = [x for x in directions if x["domain"] == dom and x["verified"]]
        done = [x for x in already if x["domain"] == dom]

        out.append({
            "domain": dom, "label": DOMAIN_CN[dom],
            "counts": {"benchmarks": len(benches), "demands": len(demands),
                       "gaps": sum(g["open"] for g in not_yet), "can_do": len(can_do)},
            "researched": researched, "not_yet": not_yet,
            "excluded": dict(excluded), "unlabeled": unlabeled, "blank_combos": blank,
            "can_do": can_do, "already_done": done,
        })
    return {"version": LIT_VERSION, "review": review_meta, "domains": out, "other_benchmarks": others,
            "unverified": [x["id"] for x in directions if not x["verified"]]}


# ---------- 文献综述方向：人读摘要写出，程序核对原话、检查撞车 ----------

TOP_K = 10
_STOP = set("""a an the of for in on and or to with by from is are be as at that this we our
their it its into via using based than not but can new benchmark benchmarks dataset datasets
evaluation evaluate evaluating llm llms model models language large task tasks performance
results show study paper propose introduce across both such these which while more""".split())


def _toks(text: str) -> list[str]:
    out = []
    for w in re.findall(r"[a-z][a-z0-9\-]+", text.lower()):
        if w in _STOP or len(w) < 3:
            continue
        out.append(w[:7])  # 粗暴词干：contract/contracts/contractual 合并
    return out


class _Similar:
    """纯 Python TF-IDF 余弦相似度，不装新库。全库 Benchmark 约 1600 篇，毫秒级。"""

    def __init__(self, conn, entries):
        import math
        self.docs = {}
        self.titles: dict[int, str] = {}
        self.domains: dict[int, str] = {e["source_item_id"]: e["domain"] for e in entries}
        self.entries: dict[int, dict] = {e["source_item_id"]: e for e in entries}
        df: Counter = Counter()
        for e in entries:
            r = conn.execute("SELECT title, content FROM source_items WHERE id=?", (e["source_item_id"],)).fetchone()
            if not r:
                continue
            self.titles[e["source_item_id"]] = r[0]
            title_t = _toks(r[0])
            tf = Counter(_toks(strip_feed_prefix(r[1])) + title_t * 3)  # 标题加权
            self.docs[e["source_item_id"]] = tf
            df.update(tf.keys())
        n = max(len(self.docs), 1)
        self.idf = {w: math.log(n / c) + 1 for w, c in df.items()}
        self.vec = {sid: self._norm({w: c * self.idf[w] for w, c in tf.items()}) for sid, tf in self.docs.items()}

    @staticmethod
    def _norm(v):
        import math
        z = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {w: x / z for w, x in v.items()}

    def rank(self, text: str, k: int) -> list[tuple[int, float]]:
        q = self._norm({w: c * self.idf.get(w, 0) for w, c in Counter(_toks(text)).items() if w in self.idf})
        scores = [(sid, sum(q.get(w, 0) * x for w, x in v.items())) for sid, v in self.vec.items()]
        return sorted(scores, key=lambda t: -t[1])[:k]


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def load_directions(conn, entries) -> tuple[dict, list[dict], list[dict]]:
    from pathlib import Path
    path = Path(__file__).resolve().parents[2] / "data" / "lit_directions.json"
    if not path.exists():
        return {}, [], []
    raw = json.loads(path.read_text(encoding="utf-8"))
    by_id = {e["source_item_id"]: e for e in entries}
    sim = _Similar(conn, [e for e in entries if e["role"] == "benchmark"])

    def src(sid):
        r = conn.execute("SELECT title, content, COALESCE(canonical_url, url) FROM source_items WHERE id=?",
                         (sid,)).fetchone()
        return r

    def ref(sid):
        e, r = by_id.get(sid), src(sid)
        name = e["name"] if e else (r[0].split(":")[0] if r else f"#{sid}")
        return {"sid": sid, "name": name, "url": (r[2] if r else "") or ""}

    dirs = []
    for d in raw.get("directions", []):
        ev, ok = [], True
        for q in d["evidence"]:
            r = src(q["sid"])
            hit = bool(r) and _norm(q["quote"]) in _norm(f"{r[0]} {strip_feed_prefix(r[1])}")
            ok &= hit
            ev.append({**ref(q["sid"]), "quote": q["quote"], "verified": hit})
        cited = {q["sid"] for q in d["evidence"]} | {x["sid"] for x in d["differs_from"]} | set(d.get("checked_sids", []))
        # 撞车检查（2026-10-08 重写）：原来只看"摘要同时命中全部关键词"的论文，
        # ContractScrub 这种用词不同的同题论文会漏掉。现在拿方向描述和全库
        # Benchmark（不分领域）算相似度，取前 TOP_K 篇；没被综述读过的列为"未核对"。
        query = " ".join([d.get("probe", ""), d["title"], d["test"], " ".join(d.get("keywords", []))])
        ranked = sim.rank(query, TOP_K)
        nearest = [{**ref(sid), "score": round(sc, 3), "checked": sid in cited} for sid, sc in ranked]
        watch = [x for x in nearest if not x["checked"]]
        dirs.append({
            "id": d["id"], "domain": d["domain"], "title": d["title"], "test": d["test"],
            "task": d["task"], "input": d["input"], "scoring": d["scoring"], "data": d["data"],
            "evidence": ev,
            "differs_from": [{**ref(x["sid"]), "how": x["how"]} for x in d["differs_from"]],
            "old_idea": d.get("old_idea"), "risk": d.get("risk", "低"),
            "check_overlap": watch, "nearest": nearest,
            "checked_count": sum(x["checked"] for x in nearest), "verified": ok,
        })
    done = [{**ref(x["sid"]), "domain": x["domain"], "what": x["what"]} for x in raw.get("already_done", [])]
    meta = {k: raw.get(k) for k in ("version", "reviewed_at", "method")}
    return meta, dirs, done

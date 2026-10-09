"""Benchmark 索引：判断每篇论文是不是 Benchmark、属于哪个领域。

待读清单（radar/core/reading.py）、文献综述语料（radar/review/corpus.py）和企业微信推送的
领域计数都读这张 lit_index 表。另外输出一份覆盖表 reports/lit_coverage.md，人工查漏用。

纯正则，不调 API。2026-10-09 起不再做缺口聚类、研究地图和撞车提醒（方向改由文献综述给出），
旧实现归档在 archive/research_map_2026-10-09/。
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from typing import Any

from radar.core.radar_core import db, now_iso, strip_feed_prefix

LIT_VERSION = "lit-v4"
MIN_TEXT = 300  # 短于此长度基本只有标题，抽不出维度

# 六个垂类领域（覆盖表只统计这几个）
VERTICALS = ("financial", "legal", "medical", "scientific", "agent", "coding")
DOMAIN_CN = {"financial": "金融", "legal": "法律", "medical": "医疗", "scientific": "科研",
             "agent": "Agent", "coding": "编程", "general": "通用", "unclassified": "未分领域"}

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

# 关注点：论文在乎什么（安全、证据、时效……），只做标签，不再聚类。
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

DEMAND_RADARS = {"workflow", "product_agent", "model_failure"}


def _hits(table: dict[str, str], low: str) -> list[str]:
    return [k for k, pat in table.items() if re.search(pat, low, re.I)]


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
    return {
        "role": classify_role(radar, title, body),
        "name": _bench_name(title, body),
        "named": bench_name(title, body)[1],
        "tasks": _hits(TASKS, low),
        "inputs": _hits(INPUTS, low),
        "concerns": _hits(CONCERNS, low),
        "metrics": _hits(METRICS, low) or ["未知"],
        "text_len": len(body),
        "too_short": too_short,
    }


JSON_COLS = ("tasks", "inputs", "concerns", "metrics")


def ensure_tables(conn) -> None:
    conn.execute("DROP TABLE IF EXISTS lit_index")  # 派生表，每次全量重建
    conn.execute(
        """CREATE TABLE lit_index (
            source_item_id INTEGER PRIMARY KEY REFERENCES source_items(id) ON DELETE CASCADE,
            radar TEXT NOT NULL, domain TEXT NOT NULL, role TEXT NOT NULL, name TEXT NOT NULL,
            tasks_json TEXT NOT NULL, inputs_json TEXT NOT NULL, concerns_json TEXT NOT NULL,
            metrics_json TEXT NOT NULL,
            text_len INTEGER NOT NULL, too_short INTEGER NOT NULL,
            version TEXT NOT NULL, built_at TEXT NOT NULL)"""
    )
    conn.execute("DROP TABLE IF EXISTS gap_candidates")  # 研究地图已停用，清掉旧表


def build_index() -> dict[str, int]:
    stats: Counter = Counter()
    with db() as conn:
        ensure_tables(conn)
        rows = conn.execute(
            """SELECT s.id, s.radar, s.title, s.content, s.raw_json, g.domain, COALESCE(s.canonical_url, s.url) AS url
               FROM source_items s JOIN signals g ON g.source_item_id = s.id
               WHERE s.validation_status NOT IN ('invalid', 'context_only')
                 AND s.source_quality != 'ai_generated'
               ORDER BY (s.source_id LIKE 'arxiv-backfill%'), s.id DESC"""
            # 新版本在前，旧版本被判为重复；同一篇论文每周抓到的那条优先于回补那条，
            # 否则它会被判成重复，从待读清单里消失（回补论文不进待读清单）
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
                "INSERT INTO lit_index VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
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
    """重建索引，并输出覆盖表 reports/lit_coverage.md（人工查漏用）。"""
    from pathlib import Path
    stats = build_index()
    (Path(base_dir) / "reports").mkdir(exist_ok=True)
    out = Path(base_dir) / "reports" / "lit_coverage.md"
    render_report(out)
    stats["outputs"] = [str(out)]
    return stats



# 六个领域之外的论文再细分一层（待读清单里按组标"不用读"），纯正则，按顺序命中第一条
OTHER_DOMAIN_RULES = [
    (r"\bmath|theorem|conjecture|erd.s|geometry problem", "数学"),
    (r"telecom|wireless|5g\b|6g\b|network traffic", "通信/网络"),
    (r"fact-?check|factuality|fake news|propaganda|misinformation|hallucinat", "事实核查"),
    (r"jailbreak|moderation|harm|unlearning|privacy|adversarial|attack|safety|red[- ]team|secur", "安全"),
    (r"code generation|programming|\bcode\b|software|test suites?\b|compiler|\bisa\b|verilog", "编程相关"),
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

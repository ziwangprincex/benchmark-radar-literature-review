from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# 项目根：本文件位于 radar/core/ 下，上溯两层。
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "radar.db"
SOURCE_CONFIG = BASE_DIR / "config" / "sources.json"
VALID_RADARS = {"benchmark", "workflow", "product_agent", "model_failure"}

DOMAIN_TERMS = {
    # 不放裸 "credit"：它会命中强化学习的 "credit assignment"（信用分配），
    # 把 TelecomGPT-R1 这类后训练论文判成金融。同理 "equity" 也有非金融义。
    "financial": ["金融", "财报", "年报", "投资", "equity research", "finance", "financial",
                  "10-k", "earnings", "credit risk", "credit rating", "估值", "并购",
                  # 不放裸 "stock"/"trading"：试跑中把具身记忆、电网保护等论文拉进金融
                  "defi", "decentralized finance",
                  # 2026-10-08 补入：只收指向金融业务本身的复合词
                  "stock market", "asset pricing", "banking", "accounting",
                  # 2026-10-09 待读清单抽查补入：保险理赔、量化交易论文此前落未分类。
                  # 不放裸 "insurance"/"portfolio"：摘要里顺带一提会触发跨领域规则归通用
                  "insurance claim", "insurance underwriting", "sharpe ratio", "sharpe ranking",
                  "portfolio-aware", "portfolio optimization", "portfolio management"],
    # 2026-10-08：抽查 40 篇法律/金融约 13 篇误判（交通数据集、损失函数论文
    # 因摘要里一个 "legal"/"contract" 被拉进来）。法律、金融改为"严格领域"，
    # 见 STRICT_DOMAINS 与 detect_domain。
    "legal": ["法律", "律师", "合同", "法条", "legal", "contract", "litigation", "合规", "诉讼",
              "statute", "statutory", "constitutional court", "judicial",
              "case law", "international law", "criminal law", "civil law", "court", "courtroom",
              "patent drafting", "patent law", "precedent retrieval", "jurisprudence", "legislation",
              "lawyer", "arbitration"],
    "medical": ["医疗", "临床", "医生", "药", "medical", "clinical", "病历", "指南", "处方",
                "patient", "healthcare", "radiolog", "biomedical",
                # 2026-09-24 抽查未分类 Benchmark 补入：手术、影像、病理、精神健康类论文此前全落 unclassified。
                # 不放裸 "patholog"：会命中 "pathological case"（数值鲁棒性论文）。
                "surgical", "surgery", "mri", "fmri", "histopatholog", "computational pathology",
                "whole-slide", "mental health", "wearable health", "health reasoning", "dementia",
                "oncolog", "pediatric",
                # 2026-10-09 补入：心理治疗、健康传播类。不放 "public health"（污水监测看板被拉进来）
                "psychotherap", "psychiatr", "health misinformation", "health communication",
                "electronic health record"],
    # 不放裸 "research" / "experiment"：几乎每篇 ML 摘要都有 "experiments show"、
    # "research on robots"，2026-09-24 批量补 arXiv 后科研类被灌到 331 篇，
    # 大半是机器人、视觉论文。只留指向"科学研究本身"的词。
    "scientific": ["科研", "科学", "论文", "scientific", "science", "systematic review", "meta analysis",
                   "meta-analysis", "scholarly", "research paper", "literature review", "peer review",
                   "chemistry", "chemical", "molecul", "protein", "genom", "physics", "astronom",
                   "materials science", "hypothesis",
                   # 评测集本身的研究（Zipbench 这类压缩评测集的论文）。收窄规则后
                   # 它们没了 "research"/"experiment" 可命中，要显式列出。
                   "benchmark compression", "compressing comprehensive benchmark", "评测成本",
                   "earth observation", "remote sensing"],
    # 不放裸 "agent"：机器人、强化学习论文里的 "agent" 指的是控制体，
    # 会把导航、灵巧手等具身论文判成 Agent。只收 LLM Agent 语境的词。
    "agent": ["智能体", "llm agent", "llm-based agent", "language agent", "ai agent", "agentic",
              "web agent", "gui agent", "multi-agent llm",
              "computer use", "computer-use", "tool use", "tool-use", "function calling",
              "browsing", "deep research", "browser",
              # GAUGE 这类"用模拟用户评测任务型 Agent"的论文不写 "llm agent"
              "user-simulat", "task-oriented agent",
              "model context protocol", "mcp server", "mcp-style", "mcp workflow", "tool calling", "tool-calling",
              "voice agent", "conversational agent", "enterprise agent", "agent societ",
              # 2026-10-09 补入：各类具体 LLM Agent 的写法。不放 "multi-agent system"
              # （无人机、艺术委托、数据整理等非 LLM-Agent 评测论文也这么写）
              # 写代码的 Agent（coding agent、SWE-agent）归 coding，见下
              "language model agent", "lm agent", "mobile agent",
              "shopping agent", "booking agent", "workspace agent", "smart-home agent",
              "forecasting agent", "persona-based agent", "tool-using", "tool-augmented",
              "agent harness", "agent memory", "llm-based multi-agent", "multi-agent collaboration",
              "multi-agent debate", "reliability agent", "agent players"],
    # 2026-10-09 新增代码领域。在代码仓库里修 bug 的 Agent（SWE-bench 一系）也归这里，
    # 与"临床 Agent 归医疗"同一口径，见 detect_domain 的 coding 优先规则。
    # 不放裸 "code"/"coding"/"programming"/"software"：摘要常写 "code is available"、
    # "medical coding"（ICD 编码）、"dynamic/linear programming"、"open-source software"。
    "coding": ["code generation", "code completion", "code repair", "code editing", "code review",
               "code reasoning", "code understanding", "code translation", "code search",
               "code llm", "code model", "code language model", "code benchmark", "code agent",
               "coding agent", "coding assistant", "coding task", "coding benchmark", "agentic coding",
               "source code", "codebase", "repository-level", "repo-level", "github issue", "pull request",
               "program repair", "program synthesis", "automated program", "bug fix", "bug-fix",
               "software engineering", "software development", "software repositor", "software change",
               "software agent", "swe-bench", "swe-agent", "swe bench", "humaneval", "mbpp", "livecodebench",
               "programming language", "programming task", "programming problem", "competitive programming",
               "programming benchmark", "unit test", "test generation", "test case generation",
               "text-to-sql", "nl2sql", "verilog", "rtl generation", "hardware description language",
               "compiler", "decompil", "smart contract", "vulnerable code", "code vulnerabilit",
               "web development", "front-end code", "frontend code", "jupyter notebook", "vibe coding"],
    # general 必须有自己的词表，不能靠兜底产生。缺这一条时，"判不出垂类"和
    # "确实是通用能力议题"会共用 general，让 R2VC（事实核查）、GAUGE
    # （LLM-as-Judge 可靠性）这类真正的通用评测方法论跟噪声混在一起。
    # 只收跨垂类的评测方法与通用能力议题，不收模型训练/压缩等非评测主题。
    "general": [
        "llm-as-a-judge", "llm as a judge", "judge", "rubric", "human evaluation",
        "fact-check", "fact check", "hallucination", "faithfulness", "attribution",
        "retrieval-augmented", "rag", "calibration", "uncertainty",
        "instruction following", "robustness", "contamination", "data leakage",
        # 2026-10-09 补入：研究 LLM 评测本身的论文。不放裸 "leaderboard"/"benchmark scores"
        # （驾驶、视频、图节点分类论文也这么写）
        "mmlu", "llm benchmark", "mcqa", "llm leaderboard", "llm ranking", "llm evaluation",
    ],
}

CAPABILITY_TERMS = {
    "long_context": ["长文档", "长上下文", "跨页", "long context", "pdf", "10-k"],
    "numerical_grounding": ["数字", "数值", "计算", "单位", "同比", "勾稽", "numerical"],
    "citation_correctness": [
        "引用", "证据", "页码", "citation", "attribution",
        # 事实核查与接地是引用正确性的同一议题（R2VC 这类论文靠这些词命中）
        "fact-check", "fact check", "hallucination", "faithfulness", "grounding", "verification",
    ],
    # 评判可靠性：LLM-as-a-Judge 与 rubric 一致性本身就是可评测能力
    # （GAUGE 这类论文此前因无对应能力词而落到 unclassified）
    "judge_reliability": [
        "llm-as-a-judge", "llm as a judge", "judge", "rubric", "annotator agreement",
        "human evaluation", "评判", "一致性",
    ],
    "cross_document_reasoning": ["跨页", "跨章节", "多文档", "cross-page", "cross-document", "交叉引用"],
    "domain_reasoning": ["推理", "判断", "诊断", "结论", "reasoning", "analysis"],
    "tool_use": ["工具", "tool", "brows", "computer use", "检索"],
    "safety": ["安全", "禁忌", "风险", "高风险", "safety", "harm"],
    "version_awareness": ["版本", "过时", "最新版", "version", "recency"],
    "planning": ["多步", "流程", "planning", "workflow"],
    # 从证据推导新结论（而非检索既有答案）。HypoKG 这类研究考察模型是否
    # 真从科学证据推理，还是生成"听起来可信"的想法。
    "hypothesis_generation": [
        "hypothesis", "hypotheses", "假设", "conjecture", "推导", "derive",
    ],
}

THEMES = [
    ("financial", ["财报", "年报", "10-k", "earnings", "pdf"], "PDF财报异常识别与证据引用"),
    ("financial", ["估值", "dcf", "comps"], "金融估值与假设一致性"),
    ("legal", ["合同", "contract", "条款"], "合同跨条款风险审查"),
    ("legal", ["检索", "法条", "legal research"], "法律检索与有效法条引用"),
    ("medical", ["用药", "处方", "剂量", "药物"], "患者特异性用药安全决策"),
    # 不能只靠单个 "clinical" 命中：该词常作举例出现（"legal, clinical,
    # source code"）或指多模态数据类型，会把数据污染检测、多模态编码等
    # 无关论文归进来。要求同时出现具体临床任务词。
    ("medical", ["诊断", "病例", "临床推理", "指南",
                 "clinical reasoning", "clinical decision", "clinical case",
                 "medical benchmark", "medical exam", "medical question",
                 "medical llm", "medical retrieval"], "临床推理与指南溯源"),
    ("scientific", ["systematic review", "meta analysis", "综述"], "系统综述证据提取与可复现性"),
    # 不放裸 "browser"：模型发布稿常写 "agentic browser-use" 作为能力列举，
    # Qwen3-Coder 曾因此成为本主题唯一信号。要求明确的 Deep Research / 浏览型 Agent 任务。
    ("agent", ["deep research", "browsing agent", "web browsing", "browsecomp", "web agent"],
     "垂类Deep Research任务完成度"),

    # --- 2026-09-23 从 pending_theme 队列补入。每条都核对过原始摘要，
    # 不是按标题猜的；Evaluation Gap 写在注释里供人工复核。 ---

    # Zipbench 等 benchmark 压缩方法（BCM）研究：评测套件冗余导致成本过高。
    # Gap：压缩后的子集能否保持排序一致性，缺乏统一验证协议。
    ("scientific", ["benchmark compression", "benchmark suite", "redundan", "评测成本"],
     "评测集压缩后的结论保真度"),

    # Echoverse 等 computer-use agent 训练/评测环境：环境随任务演化。
    # Gap：多步真实工作流（邮件、客服）的完成度判定，而非单步动作准确率。
    # 不放 "environment"：该词过泛，会命中 GPT-6 Astra 这类产品公告。
    ("agent", ["computer-use agent", "computer use agent", "multi-step workflow"],
     "Computer-Use Agent多步工作流完成度"),

    # GAUGE 等研究指向同一问题：用 LLM-as-a-Judge + 用户模拟器做离线选型门禁，
    # 但该门禁本身的可靠性未被评测。
    # Gap：Judge 与真实用户判断的一致性、门禁误判导致的选型错误。
    ("agent", ["llm-as-a-judge", "llm as a judge", "user-simulat", "offline evaluation"],
     "Agent选型门禁的判据可靠性"),

    # FinFIRST 等金融搜索 Agent 研究：不只要答案正确，还要求检索到的信息
    # 在时间上有效（财务数据有明确时效窗口）。
    # Gap：时效性有效性判定，区别于财报静态文档分析。
    ("financial", ["financial search", "temporally valid", "时效", "search agent"],
     "金融搜索结果的时效有效性"),

    # HypoKG 等生物医学假设生成：模型是否真正从科学证据推理，
    # 还是生成"听起来可信"的想法。
    # Gap：假设与底层数据库证据（KEGG 等）的可追溯支持度。
    # 只放 hypothesis 相关词：单独的 "biomedical" / "knowledge graph" 会命中
    # LatentVerse 这类多模态表征研究。
    ("medical", ["hypothesis generation", "hypotheses", "假设生成"],
     "生物医学假设的证据支持度"),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def compact(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", (text or "").lower())


def canonicalize_url(url: str) -> str:
    if not url or not url.startswith(("http://", "https://")):
        return ""
    from urllib.parse import urlsplit, urlunsplit
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit((parsed.scheme.lower(), host, path, "", ""))


def fingerprint(*parts: str) -> str:
    return hashlib.sha256("|".join(normalize(x) for x in parts).encode("utf-8")).hexdigest()[:24]


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{2,}|[\u4e00-\u9fff]{2,}", (text or "").lower()))


def jaccard(a: str, b: str) -> float:
    x, y = tokens(a), tokens(b)
    return len(x & y) / len(x | y) if x and y else 0.0


def db() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS source_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                radar TEXT NOT NULL,
                source_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                url TEXT,
                published_at TEXT,
                fingerprint TEXT NOT NULL UNIQUE,
                collected_at TEXT NOT NULL,
                raw_json TEXT NOT NULL,
                evidence_role TEXT NOT NULL DEFAULT 'analysis',
                source_type TEXT,
                locator_json TEXT NOT NULL DEFAULT '{}',
                provenance_json TEXT NOT NULL DEFAULT '{}',
                source_quality TEXT NOT NULL DEFAULT 'ai_generated',
                canonical_url TEXT,
                canonical_source_id INTEGER REFERENCES source_items(id) ON DELETE SET NULL,
                duplicate_group_id TEXT,
                retrieved_at TEXT,
                last_verified_at TEXT,
                source_version TEXT,
                content_hash TEXT,
                http_status INTEGER,
                validation_status TEXT NOT NULL DEFAULT 'unverified'
            );
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_item_id INTEGER NOT NULL UNIQUE REFERENCES source_items(id) ON DELETE CASCADE,
                domain TEXT NOT NULL,
                theme TEXT NOT NULL,
                capability_json TEXT NOT NULL,
                real_world_task TEXT NOT NULL,
                failure_pattern TEXT,
                evaluation_gap TEXT,
                analysis_json TEXT NOT NULL DEFAULT '{}',
                confidence REAL NOT NULL,
                extractor_version TEXT NOT NULL,
                extracted_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS ideas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                idea_key TEXT NOT NULL UNIQUE,
                idea_name TEXT NOT NULL,
                domain TEXT NOT NULL,
                sources_json TEXT NOT NULL,
                source_refs_json TEXT NOT NULL,
                real_world_task TEXT NOT NULL,
                capability_json TEXT NOT NULL,
                input_desc TEXT NOT NULL,
                expected_output TEXT NOT NULL,
                why_hard TEXT NOT NULL,
                expected_failure_json TEXT NOT NULL,
                existing_benchmark_json TEXT NOT NULL,
                evaluation_gap TEXT NOT NULL,
                evaluation_method TEXT NOT NULL,
                data_source TEXT NOT NULL,
                mvp_plan TEXT NOT NULL,
                radar_hits INTEGER NOT NULL,
                scores_json TEXT NOT NULL,
                score_overrides_json TEXT NOT NULL DEFAULT '{}',
                total_score REAL NOT NULL,
                status TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS idea_signal_links (
                idea_id INTEGER NOT NULL REFERENCES ideas(id) ON DELETE CASCADE,
                signal_id INTEGER NOT NULL REFERENCES signals(id) ON DELETE CASCADE,
                PRIMARY KEY (idea_id, signal_id)
            );
            CREATE TABLE IF NOT EXISTS mini_evals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                idea_id INTEGER NOT NULL REFERENCES ideas(id) ON DELETE CASCADE,
                sample_size INTEGER NOT NULL,
                model_count INTEGER NOT NULL,
                sota_score REAL NOT NULL,
                score_range REAL NOT NULL,
                reproducible_failure REAL NOT NULL,
                judge_agreement REAL NOT NULL,
                notes TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS evaluation_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL UNIQUE,
                idea_id INTEGER NOT NULL REFERENCES ideas(id) ON DELETE CASCADE,
                benchmark_id TEXT,
                dataset_version TEXT,
                dataset_hash TEXT,
                prompt_version TEXT,
                rubric_version TEXT,
                judge_type TEXT,
                judge_name TEXT,
                judge_version TEXT,
                protocol_json TEXT NOT NULL DEFAULT '{}',
                artifact_url TEXT,
                status TEXT NOT NULL DEFAULT 'completed',
                run_date TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS failure_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                idea_id INTEGER NOT NULL REFERENCES ideas(id) ON DELETE CASCADE,
                source_item_id INTEGER REFERENCES source_items(id) ON DELETE SET NULL,
                mini_eval_id INTEGER REFERENCES mini_evals(id) ON DELETE SET NULL,
                eval_run_id INTEGER REFERENCES evaluation_runs(id) ON DELETE SET NULL,
                external_case_id TEXT,
                benchmark_name TEXT,
                task_prompt TEXT NOT NULL,
                input_data TEXT,
                reference_answer TEXT,
                rubric TEXT,
                model_name TEXT NOT NULL,
                model_version TEXT,
                model_response TEXT,
                score REAL,
                passed INTEGER,
                failure_type TEXT NOT NULL,
                severity TEXT NOT NULL DEFAULT 'medium',
                error_analysis TEXT,
                judge_result TEXT,
                run_date TEXT NOT NULL,
                attachments_json TEXT NOT NULL DEFAULT '[]',
                raw_data_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS evidence_extractions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_item_id INTEGER NOT NULL REFERENCES source_items(id) ON DELETE CASCADE,
                field_name TEXT NOT NULL,
                extracted_value TEXT,
                verbatim_quote TEXT NOT NULL,
                locator_json TEXT NOT NULL DEFAULT '{}',
                extractor_version TEXT NOT NULL,
                confidence REAL NOT NULL,
                review_status TEXT NOT NULL DEFAULT 'unreviewed',
                created_at TEXT NOT NULL,
                UNIQUE(source_item_id,field_name,verbatim_quote)
            );
            CREATE TABLE IF NOT EXISTS idea_claims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                idea_id INTEGER NOT NULL REFERENCES ideas(id) ON DELETE CASCADE,
                claim_key TEXT NOT NULL,
                claim_type TEXT NOT NULL,
                claim_text TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'hypothesis',
                version INTEGER NOT NULL DEFAULT 1,
                created_by TEXT NOT NULL DEFAULT 'system',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(idea_id,claim_key)
            );
            CREATE TABLE IF NOT EXISTS claim_evidence_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_id INTEGER NOT NULL REFERENCES idea_claims(id) ON DELETE CASCADE,
                extraction_id INTEGER REFERENCES evidence_extractions(id) ON DELETE CASCADE,
                failure_case_id INTEGER REFERENCES failure_cases(id) ON DELETE CASCADE,
                support_relation TEXT NOT NULL,
                evidence_status TEXT NOT NULL,
                source_quality TEXT NOT NULL,
                rationale TEXT,
                verified_at TEXT,
                verifier TEXT,
                UNIQUE(claim_id,extraction_id,failure_case_id)
            );
            CREATE TABLE IF NOT EXISTS retrieval_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                idea_id INTEGER REFERENCES ideas(id) ON DELETE CASCADE,
                claim_id INTEGER REFERENCES idea_claims(id) ON DELETE CASCADE,
                radar TEXT NOT NULL,
                retrieval_query TEXT NOT NULL,
                retrieved_at TEXT NOT NULL,
                retriever_version TEXT NOT NULL,
                result_count INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'completed',
                query_normalized TEXT,
                completed_at TEXT,
                retry_count INTEGER NOT NULL DEFAULT 0,
                error_json TEXT NOT NULL DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS retrieval_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                retrieval_run_id INTEGER NOT NULL REFERENCES retrieval_runs(id) ON DELETE CASCADE,
                source_item_id INTEGER REFERENCES source_items(id) ON DELETE SET NULL,
                title TEXT,
                url TEXT,
                source_quality TEXT,
                selected INTEGER NOT NULL DEFAULT 0,
                rejection_reason TEXT,
                rank INTEGER,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS benchmark_coverage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                idea_id INTEGER NOT NULL REFERENCES ideas(id) ON DELETE CASCADE,
                benchmark_name TEXT NOT NULL,
                source_item_id INTEGER REFERENCES source_items(id) ON DELETE SET NULL,
                task_definition TEXT,
                dataset_description TEXT,
                input_format TEXT,
                output_format TEXT,
                evaluation_protocol TEXT,
                metrics_json TEXT NOT NULL DEFAULT '[]',
                capabilities_json TEXT NOT NULL DEFAULT '[]',
                target_coverage TEXT NOT NULL DEFAULT 'unknown',
                evidence_locator_json TEXT NOT NULL DEFAULT '{}',
                verification_status TEXT NOT NULL DEFAULT 'unverified',
                verified_at TEXT,
                notes TEXT,
                UNIQUE(idea_id,benchmark_name)
            );
            CREATE TABLE IF NOT EXISTS source_verification_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_item_id INTEGER NOT NULL REFERENCES source_items(id) ON DELETE CASCADE,
                checked_at TEXT NOT NULL,
                http_status INTEGER,
                old_hash TEXT,
                new_hash TEXT,
                change_type TEXT NOT NULL,
                error TEXT
            );
            CREATE TABLE IF NOT EXISTS source_relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_item_id INTEGER NOT NULL REFERENCES source_items(id) ON DELETE CASCADE,
                related_source_id INTEGER REFERENCES source_items(id) ON DELETE CASCADE,
                relation_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(source_item_id,related_source_id,relation_type)
            );
            CREATE TABLE IF NOT EXISTS idea_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                idea_id INTEGER NOT NULL REFERENCES ideas(id) ON DELETE CASCADE,
                action TEXT NOT NULL,
                snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_source_radar ON source_items(radar);
            CREATE INDEX IF NOT EXISTS idx_signal_theme ON signals(domain, theme);
            CREATE INDEX IF NOT EXISTS idx_idea_status ON ideas(status, total_score DESC);
            CREATE INDEX IF NOT EXISTS idx_failure_dimensions ON failure_cases(model_name,failure_type,severity,benchmark_name);
            CREATE INDEX IF NOT EXISTS idx_claim_status ON idea_claims(idea_id,status);
            CREATE INDEX IF NOT EXISTS idx_claim_support ON claim_evidence_links(claim_id,evidence_status,support_relation);
            CREATE INDEX IF NOT EXISTS idx_retrieval_claim ON retrieval_runs(claim_id,retrieved_at);
            """
        )
        signal_columns = {row["name"] for row in conn.execute("PRAGMA table_info(signals)").fetchall()}
        if "analysis_json" not in signal_columns:
            conn.execute("ALTER TABLE signals ADD COLUMN analysis_json TEXT NOT NULL DEFAULT '{}'")
        failure_columns = {row["name"] for row in conn.execute("PRAGMA table_info(failure_cases)").fetchall()}
        if "eval_run_id" not in failure_columns:
            conn.execute("ALTER TABLE failure_cases ADD COLUMN eval_run_id INTEGER")
        if "external_case_id" not in failure_columns:
            conn.execute("ALTER TABLE failure_cases ADD COLUMN external_case_id TEXT")
        if "rubric" not in failure_columns:
            conn.execute("ALTER TABLE failure_cases ADD COLUMN rubric TEXT")
        retrieval_columns = {row["name"] for row in conn.execute("PRAGMA table_info(retrieval_runs)").fetchall()}
        retrieval_migrations = {
            "query_normalized": "TEXT", "completed_at": "TEXT", "retry_count": "INTEGER NOT NULL DEFAULT 0",
            "error_json": "TEXT NOT NULL DEFAULT '{}'",
        }
        for column, definition in retrieval_migrations.items():
            if column not in retrieval_columns:
                conn.execute(f"ALTER TABLE retrieval_runs ADD COLUMN {column} {definition}")
        source_columns = {row["name"] for row in conn.execute("PRAGMA table_info(source_items)").fetchall()}
        migrations = {
            "evidence_role": "TEXT NOT NULL DEFAULT 'analysis'",
            "source_type": "TEXT",
            "locator_json": "TEXT NOT NULL DEFAULT '{}'",
            "provenance_json": "TEXT NOT NULL DEFAULT '{}'",
            "source_quality": "TEXT NOT NULL DEFAULT 'ai_generated'",
            "canonical_url": "TEXT",
            "canonical_source_id": "INTEGER",
            "duplicate_group_id": "TEXT",
            "retrieved_at": "TEXT",
            "last_verified_at": "TEXT",
            "source_version": "TEXT",
            "content_hash": "TEXT",
            "http_status": "INTEGER",
            "validation_status": "TEXT NOT NULL DEFAULT 'unverified'",
        }
        for column, definition in migrations.items():
            if column not in source_columns:
                conn.execute(f"ALTER TABLE source_items ADD COLUMN {column} {definition}")
        rows = conn.execute("SELECT id,title,content,url,published_at,source_id,evidence_role,provenance_json,source_quality,canonical_url,content_hash,retrieved_at,last_verified_at,validation_status FROM source_items").fetchall()
        for row in rows:
            external = str(row["url"] or "").startswith(("http://", "https://"))
            role = "raw_source" if external else (row["evidence_role"] or "analysis")
            source_type = "paper" if "arxiv" in (row["source_id"] or "") else ("official_release" if external else "internal_analysis")
            provenance = json.loads(row["provenance_json"] or "{}")
            provenance.update({"title": row["title"], "url": row["url"], "published_at": row["published_at"]})
            quality = row["source_quality"]
            if not quality or quality == "ai_generated":
                quality = "primary" if external else ("internal" if role == "raw_source" else "ai_generated")
            content_hash = row["content_hash"] or hashlib.sha256((row["content"] or "").encode("utf-8")).hexdigest()
            retrieved_at = row["retrieved_at"] or now_iso()
            verified_at = row["last_verified_at"] or (now_iso() if external else None)
            canonical = row["canonical_url"] or canonicalize_url(row["url"] or "")
            validation = row["validation_status"]
            if validation in {None, "unverified"}:
                validation = "verified_source" if external else ("internal_record" if role == "raw_source" else "analysis_only")
            conn.execute(
                """UPDATE source_items SET evidence_role=?,source_type=COALESCE(source_type,?),
                provenance_json=?,source_quality=?,canonical_url=?,content_hash=?,retrieved_at=?,last_verified_at=?,validation_status=? WHERE id=?""",
                (role, source_type, json.dumps(provenance, ensure_ascii=False), quality, canonical, content_hash,
                 retrieved_at, verified_at, validation, row["id"]),
            )


def verify_stale_sources(limit: int = 10, max_age_days: int = 30) -> dict[str, int]:
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError("请先运行 pip install -r requirements.txt") from exc
    with db() as conn:
        rows = conn.execute(
            """SELECT * FROM source_items WHERE evidence_role='raw_source' AND url LIKE 'http%'
               AND (last_verified_at IS NULL OR julianday('now')-julianday(last_verified_at)>=?)
               ORDER BY COALESCE(last_verified_at,'') ASC LIMIT ?""",
            (max_age_days, max(1, min(limit, 100))),
        ).fetchall()
    stats = defaultdict(int)
    headers = {"User-Agent": "BenchmarkIdeaRadar/1.0 evidence-verifier"}
    for row in rows:
        checked = now_iso()
        old_hash = row["content_hash"]
        try:
            response = requests.get(row["url"], headers=headers, timeout=20)
            response.raise_for_status()
            new_hash = hashlib.sha256(response.content).hexdigest()
            change = "content_changed" if old_hash and old_hash != new_hash else "unchanged"
            with db() as conn:
                validation = "needs_review" if change == "content_changed" else "verified_source"
                conn.execute(
                    "UPDATE source_items SET last_verified_at=?,http_status=?,validation_status=?,content_hash=? WHERE id=?",
                    (checked, response.status_code, validation, new_hash, row["id"]),
                )
                conn.execute(
                    "INSERT INTO source_verification_history(source_item_id,checked_at,http_status,old_hash,new_hash,change_type,error) VALUES(?,?,?,?,?,?,?)",
                    (row["id"], checked, response.status_code, old_hash, new_hash, change, None),
                )
            stats[change] += 1
        except Exception as exc:
            with db() as conn:
                conn.execute("UPDATE source_items SET last_verified_at=?,validation_status=? WHERE id=?", (checked, "verification_failed", row["id"]))
                conn.execute(
                    "INSERT INTO source_verification_history(source_item_id,checked_at,http_status,old_hash,new_hash,change_type,error) VALUES(?,?,?,?,?,?,?)",
                    (row["id"], checked, None, old_hash, None, "verification_failed", str(exc)),
                )
            stats["verification_failed"] += 1
    return {**dict(stats), "checked": len(rows)}


def source_config() -> dict[str, list[dict[str, Any]]]:
    return json.loads(SOURCE_CONFIG.read_text(encoding="utf-8"))


def classify_source(item: dict[str, Any], url: str) -> tuple[str, str, dict[str, Any], dict[str, Any]]:
    radar = item.get("radar", "")
    provenance = dict(item.get("provenance") or {})
    locator = dict(item.get("locator") or {})
    for key in ["section", "page", "case_id", "record_id", "dataset_split", "commit", "run_id"]:
        if item.get(key) is not None:
            locator[key] = item[key]
    public_url = url.startswith(("http://", "https://"))
    has_internal_record = bool(locator.get("record_id") or locator.get("case_id") or locator.get("run_id") or item.get("attachments"))
    requested = item.get("evidence_role")
    role = "raw_source" if public_url or (requested == "raw_source" and has_internal_record) else "analysis"
    source_type = item.get("source_type")
    if not source_type:
        if role == "analysis":
            source_type = "analysis_summary"
        elif "github.com" in url:
            source_type = "github"
        elif "arxiv.org" in url:
            source_type = "paper"
        elif radar == "product_agent":
            source_type = "official_release"
        elif radar == "workflow":
            source_type = "workflow_or_sop"
        elif radar == "model_failure":
            source_type = "eval_run_or_case"
        else:
            source_type = "web_source"
    quality = item.get("source_quality")
    if quality not in {"primary", "secondary", "internal", "ai_generated"}:
        quality = "ai_generated" if role == "analysis" else ("internal" if not public_url else "primary")
    provenance.update({
        "title": item.get("title"), "url": url, "published_at": item.get("published_at"),
        "authors": item.get("authors"), "organization": item.get("organization"),
        "source_type": source_type, "source_quality": quality, "evidence_role": role,
        "source_version": item.get("source_version") or item.get("benchmark_version") or item.get("product_version"),
        "locator": locator,
    })
    return role, source_type, locator, provenance


def insert_source_item(item: dict[str, Any]) -> tuple[int | None, str]:
    radar = item.get("radar", "")
    if radar not in VALID_RADARS:
        raise ValueError(f"invalid radar: {radar}")
    title, content = compact(item.get("title", "")), compact(item.get("content", ""))
    if not title or not content:
        raise ValueError("title and content are required")
    url = item.get("url") or ""
    role, source_type, locator, provenance = classify_source(item, url)
    quality = provenance["source_quality"]
    canonical = canonicalize_url(url)
    retrieved_at = item.get("retrieved_at") or now_iso()
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    validation_status = item.get("validation_status") or (
        "verified_source" if role == "raw_source" and item.get("http_status") == 200
        else "internal_record" if role == "raw_source" and not url.startswith(("http://", "https://"))
        else "unverified" if role == "raw_source"
        else "analysis_only"
    )
    source_version = provenance.get("source_version")
    fp = fingerprint(url or title, title)
    with db() as conn:
        exact = conn.execute("SELECT id FROM source_items WHERE fingerprint=?", (fp,)).fetchone()
        if exact:
            return None, "duplicate"
        if canonical:
            canonical_match = conn.execute("SELECT id FROM source_items WHERE canonical_url=? ORDER BY id LIMIT 1", (canonical,)).fetchone()
            if canonical_match:
                return None, "duplicate"
        recent = conn.execute("SELECT id,title,content,url FROM source_items ORDER BY id DESC LIMIT 300").fetchall()
        duplicate_of = next((
            row["id"] for row in recent
            if jaccard(title + " " + content[:300], row["title"] + " " + row["content"][:300]) >= 0.86
        ), None)
        near_duplicate = duplicate_of is not None
        cur = conn.execute(
            """INSERT INTO source_items
            (radar,source_id,title,content,url,published_at,fingerprint,collected_at,raw_json,
             evidence_role,source_type,locator_json,provenance_json,source_quality,retrieved_at,
             last_verified_at,source_version,content_hash,http_status,validation_status,canonical_url,
             canonical_source_id,duplicate_group_id)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                radar, item.get("source_id", "manual"), title, content, url,
                item.get("published_at"), fp, now_iso(), json.dumps(item, ensure_ascii=False),
                role, source_type, json.dumps(locator, ensure_ascii=False),
                json.dumps(provenance, ensure_ascii=False), quality, retrieved_at,
                item.get("last_verified_at") or (retrieved_at if role == "raw_source" else None),
                source_version, content_hash, item.get("http_status"), validation_status,
                canonical, duplicate_of, f"dup-{duplicate_of}" if duplicate_of else None,
            ),
        )
        if duplicate_of:
            conn.execute(
                "INSERT OR IGNORE INTO source_relations(source_item_id,related_source_id,relation_type,created_at) VALUES(?,?,?,?)",
                (cur.lastrowid, duplicate_of, "duplicate_of", now_iso()),
            )
        return cur.lastrowid, "clustered_duplicate" if near_duplicate else "inserted"


def import_items(items: list[dict[str, Any]]) -> dict[str, int]:
    stats = defaultdict(int)
    for item in items:
        _, state = insert_source_item(item)
        stats[state] += 1
    return dict(stats)


def collect_sources() -> dict[str, Any]:
    try:
        import feedparser
        import requests
    except ImportError as exc:
        raise RuntimeError("请先运行 pip install -r requirements.txt") from exc
    stats = defaultdict(int)
    details = []
    headers = {"User-Agent": "BenchmarkIdeaRadar/1.0 (+local research tool)"}
    for radar, sources in source_config().items():
        for source in sources:
            if not source.get("enabled") or source.get("type") != "rss":
                continue
            detail = {"radar": radar, "source_id": source["id"], "status": "ok", "fetched": 0, "kept": 0}
            try:
                response = requests.get(source["url"], headers=headers, timeout=20)
                response.raise_for_status()
                feed = feedparser.parse(response.content)
                if getattr(feed, "bozo", False) and not feed.entries:
                    raise ValueError(str(getattr(feed, "bozo_exception", "invalid feed")))
            except Exception as exc:
                stats["source_errors"] += 1
                detail.update({"status": "error", "error": str(exc)[:240]})
                details.append(detail)
                continue
            include = [x.lower() for x in source.get("include_keywords", [])]
            max_items = int(source.get("max_items", 25))
            for entry in feed.entries:
                title = entry.get("title", "")
                content = entry.get("summary") or entry.get("description") or title
                detail["fetched"] += 1
                if include and not any(keyword in f"{title} {content}".lower() for keyword in include):
                    continue
                if detail["kept"] >= max_items:
                    break
                item = {
                    "radar": radar,
                    "source_id": source["id"],
                    "title": title,
                    "content": content,
                    "url": entry.get("link", ""),
                    "published_at": entry.get("published") or entry.get("updated"),
                    "retrieved_at": now_iso(),
                    "last_verified_at": now_iso(),
                    "http_status": response.status_code,
                    "source_quality": source.get("source_quality", "primary"),
                    "source_type": source.get("source_type"),
                    "organization": source.get("organization"),
                    "source_version": entry.get("updated") or entry.get("published"),
                    "authors": [x.get("name") for x in entry.get("authors", []) if x.get("name")],
                    "locator": {"feed_source": source["url"]},
                    "tags": source.get("tags", []),
                }
                try:
                    _, state = insert_source_item(item)
                    stats[state] += 1
                    detail["kept"] += 1
                except ValueError:
                    stats["invalid"] += 1
            details.append(detail)
    return {**dict(stats), "sources": details}


# 无法判定 domain / theme 时的显式标记。不再把未命中的信号兜底成
# general + domain_expertise：两个兜底叠加会把互不相关的内容（产品公告、
# 数学论文、新闻捐款）凑成同一个 Idea。2026-09-23 之前 103 条信号里有 37 条
# 落在这个桶里，占 36%。
# 抽取器版本。改动 DOMAIN_TERMS / CAPABILITY_TERMS / THEMES 或任一 detect_*
# 函数时必须一并更新——signals.extractor_version 靠它区分哪些信号需要重算。
# 此前该值硬编码为 "rules-v1" 且从未变更，导致规则改了也看不出信号是旧口径。
EXTRACTOR_VERSION = "rules-v11.1"

UNCLASSIFIED = "unclassified"

# domain 与 capability 都判出来了，但 THEMES 表没有对应规则。这类信号是真正的
# 待归类候选（值得人工看，可能要补新主题），区别于连领域都判不出的噪声。
# 两者都塞进 UNCLASSIFIED 会让审阅队列被噪声淹没。
PENDING_THEME = "pending_theme"


ARXIV_FEED_PREFIX = re.compile(r"^arXiv:\S+\s*Announce Type:\s*\w+\s*(Abstract:)?\s*")


def strip_feed_prefix(text: str) -> str:
    """剥掉 arXiv RSS 条目固定的 "arXiv:xxxx Announce Type: new Abstract:" 前缀。"""
    return ARXIV_FEED_PREFIX.sub("", text or "")


# 只对已证实会误命中的英文词加边界，其余保持子串匹配。全局改成词边界
# 预演过：会丢掉 FinanceBench→finance、biomedical→medical、agentic→agent
# 这类合法复合词，53 条信号里多数是回退。
# 两侧都要边界（只允许常见屈折后缀）：
#   contract  ← "TT contractions"（ChainDoRA）、"contractors"
#   citation  ← "recitation"
#   version   ← "conversion"、"diversion"
#   harm      ← "pharmacy"、"harmonize"
#   rag       ← "storage"、"average"、"fragment"
WORD_TERMS = {"contract", "citation", "version", "harm", "rag", "defi", "mri", "fmri", "court"}
_INFLECTION = r"(?:s|es|d|ed|ing)?"


def term_hit(term: str, low: str) -> bool:
    """判断关键词是否出现在已转小写的文本里。

    此前全部用朴素子串匹配：ChainDoRA（LoRA 微调论文）因 "TT contractions"
    命中 "contract" 被判成 legal，成了"合同跨条款风险审查"唯一的 Raw Source。
    """
    if not term:
        return False
    if term in WORD_TERMS:
        return re.search(rf"(?<![a-z]){re.escape(term)}{_INFLECTION}(?![a-z])", low) is not None
    return term in low


# 每个主题的 Evaluation Gap 陈述，人工依据支撑信号的原始摘要撰写。
# 此前 gap_statement 只能剥前缀再截断原文，产出的是论文摘要开头
# （"Parameter-efficient fine-tuning (PEFT) adapts..."），不是"现有评测缺什么"。
# 写法约束：
#   - 说清"现有评测测了什么、没测什么"，并点名依据来源
#   - 来源只给出问题、未经 Coverage Matrix 核实的，写"待核查"，不写成定论
#   - 新增 THEMES 条目时同步补这里；缺条目时回退到原文截断并标注待改写
THEME_GAPS = {
    "PDF财报异常识别与证据引用": (
        "长文档证据定位已有覆盖：XL-DocBench 要求专家标注的多页证据，LEDGER 做年报页面级 KPI 检索，"
        "FinanceBench 标注了证据页但只判答案。XL-DocBench 全文确认其只按类型化规则判最终答案、不对模型引用判分。"
        "仍缺的是：以异常识别（跨页数值勾稽、口径不一致）为任务，并对引用是否真正支撑结论判分的金融评测。"
        "（依据：XL-DocBench 全文 §4.1；LEDGER/FinanceBench 仅核对摘要）"
    ),
    "合同跨条款风险审查": (
        "条款抽取已被 CUAD/ContractEval 覆盖；跨条款矛盾检测已有 CLAUSE（基于 CUAD/ContractNLI 扰动 7,500+ 份合同，"
        "10 类矛盾，三级任务含片段定位与法条引用，最佳模型 law_match <14%）。剩余缺口更窄：矛盾由 LLM 注入而非真实谈判合同，"
        "没有风险严重度分级，也没有法条版本/时效维度；后者仅 Sycophants in the Courtroom 部分涉及。"
        "（依据：CLAUSE 全文 §2/§3/§5；其余仅核对摘要）"
    ),
    "患者特异性用药安全决策": (
        "MedQA、CMB 等医学评测以执业考试选择题为主，不提供患者级上下文（eGFR 分层、多药联用、"
        "年龄），无法检验模型能否据此调整剂量，也不对高风险建议加权判分。"
        "（依据：临床药师复核工作流与剂量错误记录，Coverage Matrix 待核查）"
    ),
    "临床推理与指南溯源": (
        "CMB、MedQA、LLMEval-Med 已核实均未提供临床指南语料、指南检索金标准或引用正确性指标；"
        "现有医学评测只判答案对错，不判结论能否追溯到具体指南条款及其版本。"
    ),
    "Agent选型门禁的判据可靠性": (
        "τ²-bench 等 Agent 评测常用“用户模拟器 + LLM-as-a-Judge”做离线选型，但门禁本身的有效性"
        "很少被评测。GAUGE 发现满意度评分与任务成功几乎不相关（57.5% 被评“满意”的对话实际失败），"
        "且在能力接近的 Agent 之间排序分歧率达 31%。"
    ),
    "生物医学假设的证据支持度": (
        "现有医学评测考察知识问答，不区分“听起来可信”与“有证据支撑”的假设。HypoKG 显示仅给起点和"
        "终点时模型得分最高但证据接地最弱；缺少以知识图谱路径为参照、检验假设可追溯性的评测。"
    ),
    "评测集压缩后的结论保真度": (
        "Benchmark 压缩方法（BCM）以 MAE 和整体 Spearman 相关衡量子集质量（ZipBench 约 0.98），"
        "但整体相关高不等于头部近似模型的排序不变；压缩子集在关键选型决策上的保真度缺乏统一验证协议。"
    ),
    "垂类Deep Research任务完成度": (
        "BrowseComp 等搜索 Agent 评测已趋饱和（顶尖模型准确率从 30% 区间升至 90% 以上），"
        "区分度快速下降；缺少面向垂直领域、长链路检索并对过程与来源判分的 Deep Research 评测。"
    ),
    "Computer-Use Agent多步工作流完成度": (
        "Computer-Use 评测多以单步动作准确率或短任务成功率计分，未覆盖邮件、客服等随环境演化的"
        "多步真实工作流完成度。（依据待补 Raw Source）"
    ),
    "金融搜索结果的时效有效性": (
        "现有金融评测主要只判最终答案（FinFIRST 原文指出这一点），不检查检索信息的时效有效性、"
        "来源权威性、主体与期间对齐和口径一致性；错误难以定位到具体环节。"
    ),
    # 以下三条主题当前没有活跃 Idea，陈述为规则设计时的假设，依据待补。
    "金融估值与假设一致性": (
        "金融评测多考察单点计算或问答，未检验估值模型（DCF、可比公司）中各项假设之间是否自洽、"
        "与披露数据是否一致。（假设，依据待补 Raw Source）"
    ),
    "法律检索与有效法条引用": (
        "法律评测多判答案或条文召回，不检查所引法条在案件时点是否有效、是否已被修订或废止。"
        "（假设，依据待补 Raw Source）"
    ),
    "系统综述证据提取与可复现性": (
        "科研评测少有覆盖系统综述中的纳入筛选、效应量提取与结论可复现性。"
        "（假设，依据待补 Raw Source）"
    ),
}


def gap_statement(gaps: list[str], caps: list[str], theme: str = "") -> str:
    """返回 Idea 的 Evaluation Gap 陈述。

    优先用 THEME_GAPS 里人工撰写的陈述。缺条目时才回退到机械清洗：
    signals.evaluation_gap 存的是来源正文全文，这里剥前缀、去重、截断，
    并标注待改写，避免把论文摘要冒充成 Gap 结论。
    """
    if theme in THEME_GAPS:
        return THEME_GAPS[theme]
    cleaned = []
    for gap in gaps:
        text = strip_feed_prefix(compact(gap))
        if len(text) >= 20 and text not in cleaned:
            cleaned.append(text)
    if not cleaned:
        return "现有评测未充分覆盖真实端到端任务、证据接地与可复现判分。（待人工撰写）"
    # 单条来源时截断到一句话长度；多条时只留首句拼接，避免整段转储
    parts = [x[:180].rstrip() for x in cleaned[:2]]
    statement = "；".join(parts)
    suffix = f"（待人工改写为针对 {', '.join(caps[:3])} 的具体 Gap 陈述）" if caps else "（待人工改写）"
    return f"{statement}{suffix}"[:400]


# 编程同理（2026-10-09）：VLA、GNN 论文摘要里一个 "bug fix"、"coding task" 不足以定类
STRICT_DOMAINS = {"legal", "financial", "coding"}


def detect_domain(text: str, title: str | None = None) -> str:
    """判定垂类。无任何领域词命中时返回 UNCLASSIFIED，不强行归 general。

    `general` 应该表示"确实是通用能力议题"，而不是"判不出来"。混用这两种
    含义会让未分类信号污染 General 系列 Idea。

    rules-v10（2026-10-08）：法律、金融的词在通用论文里常被顺带提到
    （"legal and financial domains"、"API contract"），单个摘要词不足以定类。
    严格领域要求标题命中，或摘要命中至少两个不同的词。摘要只零星提到几个领域
    （每个各一词、且含严格领域）时，说明是跨领域的通用论文，归 general。
    """
    # 软件工程里的"契约"不是合同（Executable-Contract Audit、API contract、design by contract）
    soft = re.compile(r"(executable|api|data|interface|behaviou?ral|design[- ]by)[- ]contracts?")
    low = soft.sub(" ", text.lower())
    tl = soft.sub(" ", (title if title is not None else re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0]).lower())
    body = {d: sum(1 for t in terms if term_hit(t, low)) for d, terms in DOMAIN_TERMS.items()}
    head = {d: sum(1 for t in terms if term_hit(t, tl)) for d, terms in DOMAIN_TERMS.items()}
    verticals = [d for d in DOMAIN_TERMS if d != "general"]
    ok = {d: head.get(d, 0) * 3 + body[d] for d in verticals
          if body[d] and (d not in STRICT_DOMAINS or head.get(d) or body[d] >= 2)}
    weak = [d for d in verticals if body[d] == 1 and not head.get(d)]
    if ok and max(ok.values()) == 1 and len(weak) >= 2 and any(d in STRICT_DOMAINS for d in weak):
        return "general"
    # 垂类优先于 general：一篇临床事实核查论文同时命中 medical 和 general，应归 medical。
    if ok:
        top = max(ok.values())
        # 编程与 Agent 同分时归编程：写代码的 Agent（SWE-agent、agentic coding）
        # 摘要里总带 "agentic"，按领域看它是编程论文
        if ok.get("coding") == top:
            return "coding"
        return max(ok, key=ok.get)
    return "general" if body["general"] else UNCLASSIFIED


def detect_capabilities(text: str) -> list[str]:
    """抽取能力标签。无命中时返回空列表，不兜底成 domain_expertise。

    兜底成 domain_expertise 会让 detect_theme 用它编出
    "{domain} Domain Expertise能力评测" 这种名字，把判不出能力的信号
    伪装成一个有主题的 Idea。
    """
    low = text.lower()
    return [cap for cap, terms in CAPABILITY_TERMS.items() if any(term_hit(term, low) for term in terms)]


def detect_theme(domain: str, text: str, capabilities: list[str]) -> str:
    """匹配 THEMES 表中的主题。未命中返回 UNCLASSIFIED。

    原实现用 `f"{domain} {capabilities[0]}能力评测"` 兜底命名，产生的不是
    主题而是"未被规则覆盖的剩余物"。这类条目会被 generate_ideas 跳过，
    改由 unclassified_signals() 列出供人工审阅与扩充 THEMES。
    """
    if domain == UNCLASSIFIED or not capabilities:
        return UNCLASSIFIED
    low = text.lower()
    # 特判：金融长文档 + 数字/引用类能力。必须同时出现具体的财报文档词，
    # 否则任何带 citation_correctness 的金融论文都会归到财报主题
    # （TelecomGPT-R1 曾因 "credit assignment" 误判为 financial 而落这里）。
    if (
        domain == "financial"
        and {"long_context", "numerical_grounding", "citation_correctness"} & set(capabilities)
        # 只认明确指向财务报告文档的词。不放裸 "长文档"：任何金融长文档研究
        # 都会命中，特判就失去"限定到财报"的意义。
        and any(term_hit(k, low) for k in ["财报", "年报", "10-k", "earnings", "annual report",
                                   "financial statement", "financial report", "financial document",
                                   "财务分析", "financial analysis", "财务长文档"])
    ):
        return "PDF财报异常识别与证据引用"
    for target_domain, keywords, theme in THEMES:
        if domain == target_domain and any(term_hit(k, low) for k in keywords):
            return theme
    # 领域和能力都判出来了，只是没有对应主题规则——这是待补主题，不是噪声。
    return PENDING_THEME


def build_ai_analysis(radar: str, raw: dict[str, Any], title: str, content: str, caps: list[str]) -> dict[str, Any]:
    if radar == "benchmark":
        return {
            "analysis_type": "AI Analysis",
            "benchmark_or_paper": raw.get("benchmark_name") or title,
            "taxonomy": raw.get("taxonomy") or caps,
            "task_design": raw.get("task_design") or "从原文抽取任务设计，需人工复核",
            "evaluation_gap": raw.get("evaluation_gap") or content,
        }
    if radar == "workflow":
        return {
            "analysis_type": "AI Analysis",
            "profession": raw.get("profession") or "待专家确认",
            "task": raw.get("task") or content,
            "hardest_step": raw.get("hardest_step") or raw.get("hard_step") or "待进一步工作流访谈确认",
            "common_human_mistakes": raw.get("common_human_mistakes") or "待进一步访谈确认",
            "required_expertise": raw.get("required_expertise") or caps,
        }
    if radar == "product_agent":
        return {
            "analysis_type": "AI Analysis",
            "product_or_release": raw.get("product") or title,
            "new_capability": raw.get("new_capability") or caps,
            "previous_workflow": raw.get("previous_workflow") or "待补充",
            "evaluation_opportunity": raw.get("evaluation_opportunity") or content,
        }
    cases = raw.get("cases") or []
    first = cases[0] if cases else {}
    return {
        "analysis_type": "AI Analysis",
        "task": first.get("task_prompt") or raw.get("task_prompt") or title,
        "failure_pattern": first.get("failure_type") or raw.get("failure_type") or content,
        "potential_root_cause": first.get("error_analysis") or raw.get("error_analysis") or "待Case级分析",
        "severity": first.get("severity") or raw.get("severity") or "待标注",
    }


def extract_pending() -> dict[str, int]:
    with db() as conn:
        rows = conn.execute(
            """SELECT s.* FROM source_items s LEFT JOIN signals g ON g.source_item_id=s.id
            WHERE g.id IS NULL ORDER BY s.id"""
        ).fetchall()
        for row in rows:
            text = f"{row['title']} {row['content']}"
            domain = detect_domain(text, row["title"])
            caps = detect_capabilities(text)
            theme = detect_theme(domain, text, caps)
            radar = row["radar"]
            failure = row["content"] if radar == "model_failure" else ""
            gap = row["content"] if radar == "benchmark" else ""
            task = row["content"] if radar == "workflow" else row["title"]
            # 判出具体垂类才加分。UNCLASSIFIED 不是垂类，不能因为"不等于
            # general"就拿到这 0.12 的加成。
            confidence = min(0.98, 0.55 + 0.06 * len(caps) + (
                0.12 if domain not in {"general", UNCLASSIFIED} else 0
            ))
            raw = json.loads(row["raw_json"] or "{}")
            analysis = build_ai_analysis(radar, raw, row["title"], row["content"], caps)
            conn.execute(
                """INSERT INTO signals
                (source_item_id,domain,theme,capability_json,real_world_task,failure_pattern,
                 evaluation_gap,analysis_json,confidence,extractor_version,extracted_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (row["id"], domain, theme, json.dumps(caps, ensure_ascii=False), task, failure,
                 gap, json.dumps(analysis, ensure_ascii=False), confidence, EXTRACTOR_VERSION, now_iso()),
            )
        stale = conn.execute(
            """SELECT g.id,g.capability_json,s.radar,s.title,s.content,s.raw_json
               FROM signals g JOIN source_items s ON s.id=g.source_item_id
               WHERE g.analysis_json IS NULL OR g.analysis_json='{}'"""
        ).fetchall()
        for row in stale:
            analysis = build_ai_analysis(
                row["radar"], json.loads(row["raw_json"] or "{}"), row["title"], row["content"],
                json.loads(row["capability_json"]),
            )
            conn.execute("UPDATE signals SET analysis_json=? WHERE id=?", (json.dumps(analysis, ensure_ascii=False), row["id"]))
        reclassified = reclassify_stale_signals(conn)
    return {"extracted": len(rows), "analysis_backfilled": len(stale), "reclassified": reclassified}


def reclassify_stale_signals(conn: sqlite3.Connection) -> int:
    """用当前规则重算 extractor_version 落后的信号的 domain / capability / theme。

    EXTRACTOR_VERSION 一直只写不读：规则改了，已入库的信号仍是旧口径，
    ChainDoRA 这类被旧规则误判的信号会永远挂在错误的 Idea 上。
    只重算分类字段，不动 evaluation_gap 等原文字段。
    """
    rows = conn.execute(
        """SELECT g.id,g.domain,g.theme,g.capability_json,s.title,s.content
           FROM signals g JOIN source_items s ON s.id=g.source_item_id
           WHERE g.extractor_version != ?""",
        (EXTRACTOR_VERSION,),
    ).fetchall()
    for row in rows:
        text = f"{row['title']} {row['content']}"
        domain = detect_domain(text, row["title"])
        caps = detect_capabilities(text)
        theme = detect_theme(domain, text, caps)
        conn.execute(
            "UPDATE signals SET domain=?,theme=?,capability_json=?,extractor_version=? WHERE id=?",
            (domain, theme, json.dumps(caps, ensure_ascii=False), EXTRACTOR_VERSION, row["id"]),
        )
    return len(rows)


def manually_linked_sources(conn: sqlite3.Connection, idea_id: int) -> set[int]:
    """人工或定向检索挂到某个 Idea 上的 source_item。

    这些链接不是聚类产生的（evidence_retrieval / evidence_import 的选中结果、
    Coverage Matrix 的来源、Mini Eval 结果），不能因为信号分类不匹配就删。
    """
    ids = {x[0] for x in conn.execute(
        """SELECT x.source_item_id FROM retrieval_results x
           JOIN retrieval_runs r ON r.id=x.retrieval_run_id
           WHERE r.idea_id=? AND x.selected=1 AND x.source_item_id IS NOT NULL""",
        (idea_id,),
    )}
    ids |= {x[0] for x in conn.execute(
        "SELECT source_item_id FROM benchmark_coverage WHERE idea_id=? AND source_item_id IS NOT NULL",
        (idea_id,),
    )}
    ids |= {x[0] for x in conn.execute(
        "SELECT id FROM source_items WHERE source_id='mini-eval' AND url LIKE ?",
        (f"internal://mini-eval/{idea_id}/%",),
    )}
    return ids


def prune_stale_links(conn: sqlite3.Connection) -> int:
    """删除聚类产生、但信号在当前规则下已不属于该 Idea 的链接。

    idea_signal_links 只插不删：信号重分类后，旧链接仍把它算作原 Idea 的证据。
    ChainDoRA 被修正为 unclassified 后，若不删链接，它仍是
    "合同跨条款风险审查"唯一的 Raw Source。
    """
    removed = 0
    ideas = conn.execute(
        "SELECT id,domain,idea_name FROM ideas WHERE status != ?", (SUPERSEDED,)
    ).fetchall()
    for idea in ideas:
        manual = manually_linked_sources(conn, idea["id"])
        links = conn.execute(
            """SELECT l.signal_id,g.domain,g.theme,g.source_item_id,s.evidence_role FROM idea_signal_links l
               JOIN signals g ON g.id=l.signal_id JOIN source_items s ON s.id=g.source_item_id
               WHERE l.idea_id=?""",
            (idea["id"],),
        ).fetchall()
        for link in links:
            if (link["domain"], link["theme"]) == (idea["domain"], idea["idea_name"]):
                continue
            # analysis 角色是人工录入的工作流/失败/分析种子，本就不靠规则聚类挂载
            if link["source_item_id"] in manual or link["evidence_role"] != "raw_source":
                continue
            conn.execute(
                "DELETE FROM idea_signal_links WHERE idea_id=? AND signal_id=?",
                (idea["id"], link["signal_id"]),
            )
            removed += 1
    return removed


def benchmark_names(domain: str) -> list[str]:
    return {
        "financial": ["FinanceBench", "CNFinBench", "CFBenchmark"],
        "legal": ["LawBench"],
        "medical": ["MedBench", "CMB", "MedQA"],
        "scientific": ["GPQA", "ScienceAgentBench"],
        "agent": ["GAIA", "BrowseComp", "τ²-bench"],
        "coding": ["SWE-bench", "HumanEval", "LiveCodeBench"],
        "general": ["Humanity's Last Exam"],
    }.get(domain, [])


def score_idea(domain: str, radars: set[str], text: str, caps: list[str], signal_count: int) -> dict[str, int]:
    low = text.lower()
    error_terms = sum(1 for x in ["错误", "失败", "遗漏", "过时", "风险", "错", "failure"] if x in low)
    objective_terms = sum(1 for x in ["数字", "页码", "引用", "条款", "剂量", "准确率", "答案", "citation"] if x in low)
    real = min(20, 8 + (7 if "workflow" in radars else 0) + (3 if domain in {"financial", "legal", "medical"} else 0) + min(2, signal_count))
    weak = min(20, 7 + (8 if "model_failure" in radars else 0) + min(5, error_terms))
    diff = min(15, 5 + (5 if "model_failure" in radars else 0) + (3 if any(x in low for x in ["差距", "极差", "多个模型", "对比"]) else 0) + min(2, signal_count - 1))
    novelty = min(15, 6 + (5 if "benchmark" in radars else 0) + (3 if "product_agent" in radars else 0) + (1 if len(caps) >= 3 else 0))
    # judge_reliability 与另两项同属"输出可否稳定判分"，一并计入可评判性
    evaluability = min(15, 6 + min(6, objective_terms * 2) + (3 if any(
        c in caps for c in ["numerical_grounding", "citation_correctness", "judge_reliability"]
    ) else 0))
    feasibility = min(10, 5 + (2 if signal_count >= 2 else 0) + (2 if "workflow" in radars else 0) + (1 if objective_terms else 0))
    expert_cost = 3 if domain in {"legal", "medical"} else 4
    return {
        "real_world_value": real,
        "model_weakness": weak,
        "model_differentiation": diff,
        "novelty": novelty,
        "evaluability": evaluability,
        "data_feasibility": feasibility,
        "expert_cost": expert_cost,
    }


# 由旧兜底命名规则产生、现已无任何信号支撑的 Idea。2026-09-23 移除
# detect_domain / detect_capabilities 的兜底后，19 个 "{domain} {capability}能力评测"
# 失去全部信号。不删除它们：其中 8 个带人工 rejected 结论，且 outputs/insights/
# 与历史周报都引用着对应页面。标记后从周报与 Top 榜排除，保留可追溯性。
SUPERSEDED = "superseded"


def status_for(total: float, radar_hits: int) -> str:
    if total >= 80:
        return "mini_eval"
    if total >= 65:
        return "candidate"
    if total >= 50:
        return "watch"
    return "rejected"


def generate_ideas() -> dict[str, int]:
    with db() as conn:
        rows = conn.execute(
            """SELECT g.*,s.radar,s.source_id,s.title,s.content,s.url,s.published_at,s.evidence_role,s.validation_status
            FROM signals g JOIN source_items s ON s.id=g.source_item_id ORDER BY g.id"""
        ).fetchall()
        groups: dict[tuple[str, str], list[sqlite3.Row]] = defaultdict(list)
        skipped = {"unclassified": 0, "pending_theme": 0, "invalid_source": 0}
        for row in rows:
            # 抓取内容与标题不符的记录不能参与 Idea 生成。
            # evidence_quality.py:70 已把这类记录判为 unsupported（证据层面），
            # 但此处此前未检查，导致 R2MED（标题是医学检索基准，正文却是抓到
            # 的 nerfies 模板文案）成为 idea 18 的唯一支撑信号。
            if row["validation_status"] in {"metadata_mismatch", "verification_failed", "invalid"}:
                skipped["invalid_source"] += 1
                continue
            # 两类信号都不生成 Idea，但原因不同，分开计数：
            #   unclassified   连领域或能力都判不出，多为噪声
            #   pending_theme  领域能力都有，只缺 THEMES 规则，是待补主题
            # 把它们凑成 Idea 只会得到混装桶（见 UNCLASSIFIED 注释）。
            # 信号仍留在 signals 表，用 signals_awaiting_theme() 审阅。
            if row["domain"] == UNCLASSIFIED or row["theme"] == UNCLASSIFIED:
                skipped["unclassified"] += 1
                continue
            if row["theme"] == PENDING_THEME:
                skipped["pending_theme"] += 1
                continue
            groups[(row["domain"], row["theme"])].append(row)
        created = updated = 0
        for (domain, theme), items in groups.items():
            raw_items = [
                x for x in items
                if x["evidence_role"] == "raw_source" and x["validation_status"] in {"verified_source", "internal_record"}
            ]
            radars = {x["radar"] for x in raw_items}
            caps = sorted({c for x in items for c in json.loads(x["capability_json"])})
            refs = [{"title": x["title"], "url": x["url"], "published_at": x["published_at"]} for x in raw_items]
            combined = " ".join(x["content"] for x in items)
            failures = [
                {"type": cap, "description": x["failure_pattern"]}
                for x in raw_items if x["failure_pattern"]
                for cap in json.loads(x["capability_json"])[:1]
            ]
            gaps = [x["evaluation_gap"] for x in raw_items if x["evaluation_gap"]]
            scores = score_idea(domain, radars, combined, caps, len(items))
            total = float(sum(scores.values()))
            status = status_for(total, len(radars))
            key = fingerprint(domain, theme)
            card = {
                "idea_name": theme,
                "domain": domain,
                "sources_json": json.dumps(sorted(radars), ensure_ascii=False),
                "source_refs_json": json.dumps(refs, ensure_ascii=False),
                "real_world_task": next((x["real_world_task"] for x in items if x["radar"] == "workflow"), items[0]["real_world_task"]),
                "capability_json": json.dumps(caps, ensure_ascii=False),
                "input_desc": "真实业务材料（文档、记录、专业上下文及必要工具）",
                "expected_output": "可验证的专业结论、逐项证据引用及结构化推理结果",
                "why_hard": f"组合考察 {', '.join(caps)}，需要跨信息源完成多步专业推理。",
                "expected_failure_json": json.dumps(failures or [{"type": caps[0], "description": "待 Mini Eval 验证"}], ensure_ascii=False),
                "existing_benchmark_json": json.dumps(benchmark_names(domain), ensure_ascii=False),
                "evaluation_gap": gap_statement(gaps, caps, theme),
                "evaluation_method": "30-50题 Mini Eval；reference精确匹配 + case-specific rubric + 专家抽检。",
                "data_source": "；".join(sorted({x["source_id"] if "source_id" in x.keys() else "source" for x in items})),
                "mvp_plan": "先制作30题，覆盖2-3个子能力；运行5个代表模型；验证Failure、区分度和评判一致性。",
                "radar_hits": len(radars),
                "scores_json": json.dumps(scores, ensure_ascii=False),
                "total_score": total,
                "status": status,
            }
            existing = conn.execute("SELECT * FROM ideas WHERE idea_key=?", (key,)).fetchone()
            ts = now_iso()
            changed = False
            if existing:
                overrides = json.loads(existing["score_overrides_json"] or "{}")
                final_scores = {**scores, **overrides}
                latest_eval = conn.execute(
                    "SELECT * FROM mini_evals WHERE idea_id=? ORDER BY id DESC LIMIT 1", (existing["id"],)
                ).fetchone()
                if latest_eval:
                    failure_ratio = float(latest_eval["reproducible_failure"])
                    final_scores["model_weakness"] = max(0, min(20, round(failure_ratio * 20 if failure_ratio <= 1 else failure_ratio / 5)))
                    final_scores["model_differentiation"] = max(0, min(15, round(float(latest_eval["score_range"]) / 2)))
                final_total = float(sum(final_scores.values()))
                # approved 与人工改判的 rejected 是人工结论，superseded 是分类规则
                # 变更的归档，都不被自动重算覆盖。status_for 在分数 <50 时也会给出
                # rejected，此前一律冻结，导致 26、27 这类新 Idea 生成即锁死，
                # 补进新证据也不会重评。只有 manual_override 留下的 rejected 才冻结。
                manual_rejected = existing["status"] == "rejected" and conn.execute(
                    "SELECT 1 FROM idea_history WHERE idea_id=? AND action='manual_override' LIMIT 1",
                    (existing["id"],),
                ).fetchone() is not None
                final_status = (
                    existing["status"]
                    if existing["status"] in {"approved", SUPERSEDED} or manual_rejected
                    else status_for(final_total, len(radars))
                )
                card["scores_json"] = json.dumps(final_scores, ensure_ascii=False)
                card["total_score"] = final_total
                card["status"] = final_status
                changed = any([
                    existing["source_refs_json"] != card["source_refs_json"],
                    json.loads(existing["scores_json"]) != final_scores,
                    float(existing["total_score"]) != final_total,
                    existing["status"] != final_status,
                    # 文本字段也要纳入：否则改进 gap_statement 之类的生成逻辑后，
                    # 已有 Idea 会一直留着旧文本（此前 evaluation_gap 的 arXiv
                    # 原文转储就因为不在此列而无法刷新）。
                    existing["evaluation_gap"] != card["evaluation_gap"],
                    existing["capability_json"] != card["capability_json"],
                ])
                if changed:
                    conn.execute(
                        """UPDATE ideas SET idea_name=?,domain=?,sources_json=?,source_refs_json=?,real_world_task=?,
                        capability_json=?,input_desc=?,expected_output=?,why_hard=?,expected_failure_json=?,
                        existing_benchmark_json=?,evaluation_gap=?,evaluation_method=?,data_source=?,mvp_plan=?,
                        radar_hits=?,scores_json=?,total_score=?,status=?,version=version+1,updated_at=? WHERE id=?""",
                        tuple(card[k] for k in ["idea_name","domain","sources_json","source_refs_json","real_world_task","capability_json","input_desc","expected_output","why_hard","expected_failure_json","existing_benchmark_json","evaluation_gap","evaluation_method","data_source","mvp_plan","radar_hits","scores_json","total_score","status"]) + (ts, existing["id"]),
                    )
                    updated += 1
                idea_id = existing["id"]
            else:
                cur = conn.execute(
                    """INSERT INTO ideas
                    (idea_key,idea_name,domain,sources_json,source_refs_json,real_world_task,capability_json,
                    input_desc,expected_output,why_hard,expected_failure_json,existing_benchmark_json,
                    evaluation_gap,evaluation_method,data_source,mvp_plan,radar_hits,scores_json,
                    score_overrides_json,total_score,status,created_at,updated_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, ?,?,?,?)""",
                    (key,) + tuple(card[k] for k in ["idea_name","domain","sources_json","source_refs_json","real_world_task","capability_json","input_desc","expected_output","why_hard","expected_failure_json","existing_benchmark_json","evaluation_gap","evaluation_method","data_source","mvp_plan","radar_hits","scores_json"]) + ("{}", card["total_score"], card["status"], ts, ts),
                )
                idea_id = cur.lastrowid
                created += 1
            for x in items:
                conn.execute("INSERT OR IGNORE INTO idea_signal_links(idea_id,signal_id) VALUES(?,?)", (idea_id, x["id"]))
            if not existing or changed:
                snapshot = conn.execute("SELECT * FROM ideas WHERE id=?", (idea_id,)).fetchone()
                conn.execute(
                    "INSERT INTO idea_history(idea_id,action,snapshot_json,created_at) VALUES(?,?,?,?)",
                    (idea_id, "generated" if not existing else "refreshed", json.dumps(dict(snapshot), ensure_ascii=False), ts),
                )
        pruned = prune_stale_links(conn)
    return {
        "created": created,
        "updated": updated,
        "clusters": len(groups),
        # 信号重分类后不再属于原 Idea 的聚类链接
        "pruned_stale_links": pruned,
        # pending_theme 持续偏高说明 THEMES 覆盖不足，应扩充规则；
        # unclassified 持续偏高说明采集源的关键词过滤太松，引入了噪声。
        "skipped_unclassified": skipped["unclassified"],
        "skipped_pending_theme": skipped["pending_theme"],
        # 抓取内容与标题不符的源。偏高说明采集或验证环节需要检查，
        # 用 invalid_sources() 查看具体记录。
        "skipped_invalid_source": skipped["invalid_source"],
    }


def invalid_sources() -> list[dict[str, Any]]:
    """列出抓取内容与标题不符的源，供人工重新采集或剔除。

    典型原因：论文项目页套用学术模板（R2MED 用 nerfies 模板，抓到模板自带的
    meta description）、聚合页只返回作者名单（ACL 页面）、动态 SPA 只返回外壳。
    """
    with db() as conn:
        return [dict(x) for x in conn.execute(
            """SELECT id, title, url, source_id, validation_status,
                      substr(content, 1, 160) AS content_preview
               FROM source_items
               WHERE validation_status IN ('metadata_mismatch','verification_failed','invalid')
               ORDER BY id"""
        ).fetchall()]


def signals_awaiting_theme(kind: str = "pending_theme", limit: int = 50) -> list[dict[str, Any]]:
    """列出未能生成 Idea 的信号，供人工审阅。

    kind="pending_theme"：领域与能力都已判定，只缺 THEMES 规则。优先看这批，
    反复出现的议题应补成新主题。
    kind="unclassified"：连领域或能力都判不出，多为噪声。若某类内容反复出现，
    说明 DOMAIN_TERMS / CAPABILITY_TERMS 需要补词，或采集源过滤要收紧。
    """
    if kind not in {"pending_theme", "unclassified"}:
        raise ValueError("kind must be pending_theme or unclassified")
    with db() as conn:
        base = """SELECT g.id, g.domain, g.theme, g.capability_json, s.radar, s.source_id,
                         s.title, s.url, s.published_at
                  FROM signals g JOIN source_items s ON s.id = g.source_item_id"""
        if kind == "pending_theme":
            sql = f"{base} WHERE g.theme = ? ORDER BY g.domain, s.published_at DESC LIMIT ?"
            params = (PENDING_THEME, limit)
        else:
            sql = f"{base} WHERE g.domain = ? OR g.theme = ? ORDER BY s.published_at DESC LIMIT ?"
            params = (UNCLASSIFIED, UNCLASSIFIED, limit)
        return [dict(x) for x in conn.execute(sql, params).fetchall()]


def list_signals(limit: int = 100, radar: str | None = None) -> list[dict[str, Any]]:
    where, args = [], []
    if radar:
        where.append("s.radar=?")
        args.append(radar)
    args.append(max(1, min(limit, 500)))
    sql = """SELECT g.*,s.radar,s.source_id,s.title,s.url,s.published_at,s.collected_at
             FROM signals g JOIN source_items s ON s.id=g.source_item_id"""
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY g.id DESC LIMIT ?"
    with db() as conn:
        rows = []
        for row in conn.execute(sql, args).fetchall():
            item = dict(row)
            item["capability"] = json.loads(item.pop("capability_json"))
            item["ai_analysis"] = json.loads(item.pop("analysis_json") or "{}")
            rows.append(item)
        return rows


def parse_failure_case(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    item["passed"] = None if item.get("passed") is None else bool(item["passed"])
    item["attachments"] = json.loads(item.pop("attachments_json") or "[]")
    item["raw_data"] = json.loads(item.pop("raw_data_json") or "{}")
    if "protocol_json" in item:
        item["protocol"] = json.loads(item.pop("protocol_json") or "{}")
    return item


def add_evaluation_run(idea_id: int, payload: dict[str, Any]) -> tuple[int, str]:
    run_id = compact(payload.get("eval_run_id") or payload.get("run_id") or "")
    if not run_id:
        raise ValueError("evaluation run requires eval_run_id")
    required = ["dataset_version", "prompt_version", "rubric_version", "judge_type", "judge_name", "judge_version"]
    missing = [key for key in required if not payload.get(key)]
    if missing:
        raise ValueError(f"evaluation run missing fields: {', '.join(missing)}")
    with db() as conn:
        existing = conn.execute("SELECT id FROM evaluation_runs WHERE run_id=?", (run_id,)).fetchone()
        if existing:
            return existing["id"], run_id
        cursor = conn.execute(
            """INSERT INTO evaluation_runs
            (run_id,idea_id,benchmark_id,dataset_version,dataset_hash,prompt_version,rubric_version,
             judge_type,judge_name,judge_version,protocol_json,artifact_url,status,run_date,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (run_id, idea_id, payload.get("benchmark_id"), payload["dataset_version"], payload.get("dataset_hash"),
             payload["prompt_version"], payload["rubric_version"], payload["judge_type"], payload["judge_name"],
             payload["judge_version"], json.dumps(payload.get("protocol") or {}, ensure_ascii=False),
             payload.get("artifact_url"), "completed", payload.get("run_date") or now_iso(), now_iso()),
        )
        return cursor.lastrowid, run_id


def add_failure_cases(
    idea_id: int,
    cases: list[dict[str, Any]],
    source_item_id: int | None = None,
    mini_eval_id: int | None = None,
    eval_run_id: int | None = None,
) -> list[int]:
    if not cases:
        return []
    allowed_severity = {"low", "medium", "high", "critical"}
    inserted = []
    with db() as conn:
        if not conn.execute("SELECT id FROM ideas WHERE id=?", (idea_id,)).fetchone():
            raise KeyError(idea_id)
        for case in cases:
            task = compact(case.get("task_prompt") or case.get("task") or case.get("prompt") or "")
            model_name = compact(case.get("model_name") or "")
            failure_type = compact(case.get("failure_type") or "unclassified")
            external_case_id = compact(case.get("failure_case_id") or case.get("case_id") or "")
            reference = str(case.get("reference_answer") or "")
            response = str(case.get("model_response") or "")
            judge = str(case.get("judge_result") or "")
            if not task or not model_name or not external_case_id:
                raise ValueError("failure case requires failure_case_id, task_prompt and model_name")
            if not reference or not response or not judge:
                raise ValueError("failure case requires reference_answer, model_response and judge_result")
            severity = str(case.get("severity") or "medium").lower()
            if severity not in allowed_severity:
                raise ValueError(f"invalid severity: {severity}")
            passed = case.get("passed")
            if passed is None and case.get("pass_fail") is not None:
                passed = str(case["pass_fail"]).lower() in {"pass", "passed", "true", "1", "通过"}
            cur = conn.execute(
                """INSERT INTO failure_cases
                (idea_id,source_item_id,mini_eval_id,eval_run_id,external_case_id,benchmark_name,task_prompt,input_data,
                 reference_answer,rubric,model_name,model_version,model_response,score,passed,
                 failure_type,severity,error_analysis,judge_result,run_date,attachments_json,
                 raw_data_json,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    idea_id, source_item_id, mini_eval_id, eval_run_id, external_case_id, compact(case.get("benchmark_name") or ""),
                    task, str(case.get("input") or case.get("input_data") or ""),
                    str(case.get("reference_answer") or ""), str(case.get("rubric") or ""), model_name,
                    compact(case.get("model_version") or ""), str(case.get("model_response") or ""),
                    case.get("score"), None if passed is None else int(bool(passed)), failure_type,
                    severity, str(case.get("error_analysis") or ""),
                    str(case.get("judge_result") or ""),
                    str(case.get("run_date") or now_iso()),
                    json.dumps(case.get("attachments") or [], ensure_ascii=False),
                    json.dumps(case.get("raw_data") or case, ensure_ascii=False), now_iso(),
                ),
            )
            inserted.append(cur.lastrowid)
    return inserted


def list_failure_cases(
    idea_id: int | None = None,
    model: str | None = None,
    failure_type: str | None = None,
    severity: str | None = None,
    benchmark: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    where, args = [], []
    for column, value in [
        ("f.idea_id", idea_id), ("f.model_name", model), ("f.failure_type", failure_type),
        ("f.severity", severity), ("f.benchmark_name", benchmark),
    ]:
        if value is not None and value != "":
            where.append(f"{column}=?")
            args.append(value)
    args.append(max(1, min(int(limit), 2000)))
    sql = """SELECT f.*,i.idea_name,s.title source_title,s.url source_url,
                    r.run_id,r.dataset_version,r.dataset_hash,r.prompt_version,r.rubric_version,
                    r.judge_type,r.judge_name,r.judge_version,r.protocol_json,r.artifact_url
             FROM failure_cases f JOIN ideas i ON i.id=f.idea_id
             LEFT JOIN source_items s ON s.id=f.source_item_id
             LEFT JOIN evaluation_runs r ON r.id=f.eval_run_id"""
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY f.run_date DESC,f.id DESC LIMIT ?"
    with db() as conn:
        return [parse_failure_case(x) for x in conn.execute(sql, args).fetchall()]


def source_claim_trace(source_item_id: int) -> list[dict[str, Any]]:
    with db() as conn:
        return [dict(x) for x in conn.execute(
            """SELECT i.id idea_id,i.idea_name,c.id claim_id,c.claim_type,c.claim_text,c.status claim_status,
                      l.support_relation,l.evidence_status,l.rationale,l.verified_at,l.verifier,e.id extraction_id,e.field_name
               FROM evidence_extractions e
               JOIN claim_evidence_links l ON l.extraction_id=e.id
               JOIN idea_claims c ON c.id=l.claim_id
               JOIN ideas i ON i.id=c.idea_id
               WHERE e.source_item_id=? ORDER BY i.id,c.id,l.id""",
            (source_item_id,),
        ).fetchall()]


def upsert_coverage_entry(idea_id: int, entry: dict[str, Any]) -> int:
    required = ["benchmark_name", "task_definition", "dataset_description", "input_format", "output_format", "evaluation_protocol"]
    if any(not entry.get(key) for key in required):
        raise ValueError("coverage entry missing required fields")
    coverage = entry.get("target_coverage", "unknown")
    if coverage not in {"covered", "partial", "not_covered", "unknown"}:
        raise ValueError("invalid target_coverage")
    with db() as conn:
        conn.execute(
            """INSERT INTO benchmark_coverage
            (idea_id,benchmark_name,source_item_id,task_definition,dataset_description,input_format,
             output_format,evaluation_protocol,metrics_json,capabilities_json,target_coverage,
             evidence_locator_json,verification_status,verified_at,notes)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(idea_id,benchmark_name) DO UPDATE SET
            source_item_id=excluded.source_item_id,task_definition=excluded.task_definition,
            dataset_description=excluded.dataset_description,input_format=excluded.input_format,
            output_format=excluded.output_format,evaluation_protocol=excluded.evaluation_protocol,
            metrics_json=excluded.metrics_json,capabilities_json=excluded.capabilities_json,
            target_coverage=excluded.target_coverage,evidence_locator_json=excluded.evidence_locator_json,
            verification_status=excluded.verification_status,verified_at=excluded.verified_at,notes=excluded.notes""",
            (
                idea_id, entry["benchmark_name"], entry.get("source_item_id"), entry["task_definition"],
                entry["dataset_description"], entry["input_format"], entry["output_format"],
                entry["evaluation_protocol"], json.dumps(entry.get("metrics") or [], ensure_ascii=False),
                json.dumps(entry.get("capabilities") or [], ensure_ascii=False), coverage,
                json.dumps(entry.get("evidence_locator") or {}, ensure_ascii=False),
                entry.get("verification_status", "unverified"), entry.get("verified_at"), entry.get("notes", ""),
            ),
        )
        return conn.execute("SELECT id FROM benchmark_coverage WHERE idea_id=? AND benchmark_name=?", (idea_id, entry["benchmark_name"])).fetchone()["id"]


def coverage_matrix(idea_id: int) -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute(
            """SELECT b.*,s.title source_title,s.url source_url,s.source_quality,s.validation_status source_validation
               FROM benchmark_coverage b LEFT JOIN source_items s ON s.id=b.source_item_id
               WHERE b.idea_id=? ORDER BY b.benchmark_name""", (idea_id,)
        ).fetchall()
        output = []
        for row in rows:
            item = dict(row)
            item["metrics"] = json.loads(item.pop("metrics_json") or "[]")
            item["capabilities"] = json.loads(item.pop("capabilities_json") or "[]")
            item["evidence_locator"] = json.loads(item.pop("evidence_locator_json") or "{}")
            output.append(item)
        return output


IDEA_CARDS_PATH = Path(__file__).resolve().parents[2] / "data" / "idea_cards.json"
_cards_cache: dict[str, Any] = {"mtime": None, "data": {}}


def idea_cards() -> dict[str, Any]:
    """人工题卡（data/idea_cards.json），按 idea_key 关联。

    自动生成的 input_desc / why_hard 等是模板句，回答不了“测什么、凭什么”。
    题卡由人逐条写，generate_ideas 重算不会碰它。
    """
    try:
        mtime = IDEA_CARDS_PATH.stat().st_mtime
    except FileNotFoundError:
        return {}
    if _cards_cache["mtime"] != mtime:
        raw = json.loads(IDEA_CARDS_PATH.read_text(encoding="utf-8"))
        _cards_cache.update(mtime=mtime, data={k: v for k, v in raw.items() if not k.startswith("_")})
    return _cards_cache["data"]


def parse_idea(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    for key in ["sources_json", "source_refs_json", "capability_json", "expected_failure_json", "existing_benchmark_json", "scores_json", "score_overrides_json"]:
        item[key.removesuffix("_json")] = json.loads(item.pop(key) or "{}")
    item["card"] = idea_cards().get(item.get("idea_key"))
    return item


def list_ideas(status: str | None = None, domain: str | None = None, query: str | None = None) -> list[dict[str, Any]]:
    where, args = [], []
    if status:
        where.append("status=?"); args.append(status)
    if domain:
        where.append("domain=?"); args.append(domain)
    if query:
        where.append("(idea_name LIKE ? OR capability_json LIKE ? OR evaluation_gap LIKE ?)")
        term = f"%{query}%"
        args.extend([term, term, term])
    sql = "SELECT * FROM ideas" + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY total_score DESC, radar_hits DESC, updated_at DESC"
    with db() as conn:
        return [parse_idea(x) for x in conn.execute(sql, args).fetchall()]


def get_idea(idea_id: int) -> dict[str, Any] | None:
    with db() as conn:
        row = conn.execute("SELECT * FROM ideas WHERE id=?", (idea_id,)).fetchone()
        if not row:
            return None
        item = parse_idea(row)
        item["mini_evals"] = [dict(x) for x in conn.execute("SELECT * FROM mini_evals WHERE idea_id=? ORDER BY id DESC", (idea_id,)).fetchall()]
        item["history"] = [
            {"id": x["id"], "action": x["action"], "created_at": x["created_at"]}
            for x in conn.execute("SELECT id,action,created_at FROM idea_history WHERE idea_id=? ORDER BY id DESC LIMIT 20", (idea_id,)).fetchall()
        ]
        evidence = conn.execute(
            """SELECT s.id source_item_id,s.radar,s.source_id,s.title,s.content,s.url,s.raw_json,
                      s.published_at,s.collected_at,s.evidence_role,s.source_type,s.source_quality,s.locator_json,s.provenance_json,
                      s.retrieved_at,s.last_verified_at,s.source_version,s.content_hash,s.http_status,s.validation_status,
                      s.canonical_url,s.canonical_source_id,s.duplicate_group_id,
                      g.id signal_id,g.domain,g.theme,g.capability_json,g.real_world_task,g.failure_pattern,g.evaluation_gap,g.analysis_json,
                      g.confidence,g.extractor_version
               FROM idea_signal_links l
               JOIN signals g ON g.id=l.signal_id
               JOIN source_items s ON s.id=g.source_item_id
               WHERE l.idea_id=? ORDER BY s.radar,s.published_at DESC,s.id DESC""",
            (idea_id,),
        ).fetchall()
        item["evidence"] = []
        for source in evidence:
            record = dict(source)
            record["capability"] = json.loads(record.pop("capability_json"))
            record["ai_analysis"] = json.loads(record.pop("analysis_json") or "{}")
            record["raw_data"] = json.loads(record.pop("raw_json") or "{}")
            record["locator"] = json.loads(record.pop("locator_json") or "{}")
            record["provenance"] = json.loads(record.pop("provenance_json") or "{}")
            record["failure_cases"] = [
                parse_failure_case(x)
                for x in conn.execute(
                    """SELECT f.*,i.idea_name,s.title source_title,s.url source_url
                       FROM failure_cases f JOIN ideas i ON i.id=f.idea_id
                       LEFT JOIN source_items s ON s.id=f.source_item_id
                       WHERE f.idea_id=? AND f.source_item_id=? ORDER BY f.run_date DESC,f.id DESC""",
                    (idea_id, record["source_item_id"]),
                ).fetchall()
            ]
            item["evidence"].append(record)
        item["raw_evidence_count"] = sum(
            1 for x in item["evidence"]
            if x.get("evidence_role") == "raw_source" and x.get("validation_status") in {"verified_source", "internal_record"}
        )
        item["analysis_input_count"] = sum(1 for x in item["evidence"] if x.get("evidence_role") != "raw_source")
        item["provenance_ready"] = item["raw_evidence_count"] > 0
        item["failure_cases"] = list_failure_cases(idea_id=idea_id)
        item["coverage_matrix"] = coverage_matrix(idea_id)
        from radar.evidence.evidence_quality import claim_quality_summary
        item["evidence_quality"] = claim_quality_summary(idea_id)
        return item


def override_scores(idea_id: int, overrides: dict[str, Any], status: str | None = None) -> dict[str, Any]:
    allowed = {"real_world_value", "model_weakness", "model_differentiation", "novelty", "evaluability", "data_feasibility", "expert_cost"}
    with db() as conn:
        row = conn.execute("SELECT * FROM ideas WHERE id=?", (idea_id,)).fetchone()
        if not row:
            raise KeyError(idea_id)
        clean = {k: int(v) for k, v in overrides.items() if k in allowed and v is not None}
        base = json.loads(row["scores_json"])
        merged = {**base, **clean}
        total = float(sum(merged.values()))
        new_status = status or status_for(total, row["radar_hits"])
        ts = now_iso()
        conn.execute(
            "UPDATE ideas SET scores_json=?,score_overrides_json=?,total_score=?,status=?,version=version+1,updated_at=? WHERE id=?",
            (json.dumps(merged, ensure_ascii=False), json.dumps(clean, ensure_ascii=False), total, new_status, ts, idea_id),
        )
        snapshot = conn.execute("SELECT * FROM ideas WHERE id=?", (idea_id,)).fetchone()
        conn.execute("INSERT INTO idea_history(idea_id,action,snapshot_json,created_at) VALUES(?,?,?,?)", (idea_id, "manual_override", json.dumps(dict(snapshot), ensure_ascii=False), ts))
    return get_idea(idea_id) or {}


def add_mini_eval(idea_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    required = ["sample_size", "model_count", "sota_score", "score_range", "reproducible_failure", "judge_agreement"]
    if any(k not in payload for k in required):
        raise ValueError("missing mini eval fields")
    cases = payload.get("cases") or []
    if int(payload["sample_size"]) < 1 or int(payload["model_count"]) < 1:
        raise ValueError("sample_size and model_count must be positive")
    if not (0 <= float(payload["judge_agreement"]) <= 1):
        raise ValueError("judge_agreement must be between 0 and 1")
    eval_run_db_id = None
    eval_run_name = None
    if cases:
        eval_run_db_id, eval_run_name = add_evaluation_run(idea_id, payload)
        for case in cases:
            case.setdefault("run_date", payload.get("run_date") or now_iso())
            case.setdefault("benchmark_name", payload.get("benchmark_id") or "Mini Eval")
    with db() as conn:
        if not conn.execute("SELECT id FROM ideas WHERE id=?", (idea_id,)).fetchone():
            raise KeyError(idea_id)
        mini_eval_cursor = conn.execute(
            """INSERT INTO mini_evals
            (idea_id,sample_size,model_count,sota_score,score_range,reproducible_failure,judge_agreement,notes,created_at)
            VALUES(?,?,?,?,?,?,?,?,?)""",
            (idea_id, *(payload[k] for k in required), payload.get("notes", ""), now_iso()),
        )
        mini_eval_id = mini_eval_cursor.lastrowid
        row = conn.execute("SELECT * FROM ideas WHERE id=?", (idea_id,)).fetchone()
        scores = json.loads(row["scores_json"])
        score_range = float(payload["score_range"])
        if cases:
            weakness_ratio = float(payload["reproducible_failure"])
            scores["model_weakness"] = max(0, min(20, round(weakness_ratio * 20 if weakness_ratio <= 1 else weakness_ratio / 5)))
            scores["model_differentiation"] = max(0, min(15, round(score_range / 2)))
        total = float(sum(scores.values()))
        gate_pass = bool(cases) and 30 <= float(payload["sota_score"]) <= 70 and score_range >= 25 and float(payload["judge_agreement"]) >= 0.7
        new_status = "approved" if gate_pass and total >= 80 else ("candidate" if total >= 65 else "watch")
        ts = now_iso()
        conn.execute("UPDATE ideas SET scores_json=?,total_score=?,status=?,version=version+1,updated_at=? WHERE id=?", (json.dumps(scores, ensure_ascii=False), total, new_status, ts, idea_id))
        snapshot = conn.execute("SELECT * FROM ideas WHERE id=?", (idea_id,)).fetchone()
        conn.execute("INSERT INTO idea_history(idea_id,action,snapshot_json,created_at) VALUES(?,?,?,?)", (idea_id, "mini_eval_feedback", json.dumps(dict(snapshot), ensure_ascii=False), ts))
        idea_name = row["idea_name"]
        capabilities = ", ".join(json.loads(row["capability_json"]))
    source_item_id, _ = insert_source_item({
        "radar": "model_failure",
        "source_id": "mini-eval",
        "title": f"Mini Eval结果：{idea_name}",
        "content": (
            f"{idea_name} 完成 {payload['sample_size']} 题、{payload['model_count']} 个模型同题测试。"
            f"SOTA得分 {payload['sota_score']}%，模型极差 {payload['score_range']}pt，"
            f"可复现Failure比例 {payload['reproducible_failure']}，Judge一致性 {payload['judge_agreement']}。"
            f"涉及能力：{capabilities}。{payload.get('notes', '')}"
        ),
        "url": f"internal://mini-eval/{idea_id}/{ts}",
        "published_at": ts,
        "evidence_role": "raw_source" if cases else "analysis",
        "source_type": "eval_run" if cases else "analysis_summary",
        "run_id": eval_run_name or f"mini-eval-summary-{mini_eval_id}",
        "raw_data": payload,
    })
    add_failure_cases(
        idea_id,
        cases,
        source_item_id=source_item_id,
        mini_eval_id=mini_eval_id,
        eval_run_id=eval_run_db_id,
    )
    extract_pending()
    generate_ideas()
    if source_item_id:
        with db() as conn:
            signal = conn.execute("SELECT id FROM signals WHERE source_item_id=?", (source_item_id,)).fetchone()
            if signal:
                conn.execute("INSERT OR IGNORE INTO idea_signal_links(idea_id,signal_id) VALUES(?,?)", (idea_id, signal["id"]))
    from radar.evidence.evidence_quality import sync_idea_quality
    sync_idea_quality(idea_id)
    return get_idea(idea_id) or {}


def dashboard() -> dict[str, Any]:
    with db() as conn:
        counts = {
            "source_items": conn.execute("SELECT COUNT(*) FROM source_items").fetchone()[0],
            "signals": conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0],
            "ideas": conn.execute("SELECT COUNT(*) FROM ideas").fetchone()[0],
            "mini_evals": conn.execute("SELECT COUNT(*) FROM mini_evals").fetchone()[0],
            "failure_cases": conn.execute("SELECT COUNT(*) FROM failure_cases").fetchone()[0],
        }
        radar = {x["radar"]: x["n"] for x in conn.execute("SELECT radar,COUNT(*) n FROM source_items GROUP BY radar").fetchall()}
        status = {x["status"]: x["n"] for x in conn.execute("SELECT status,COUNT(*) n FROM ideas GROUP BY status").fetchall()}
        weekly = weekly_report(conn)
        return {"counts": counts, "radar_counts": radar, "status_counts": status, "weekly": weekly}


def weekly_report(conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    own = conn is None
    conn = conn or db()
    try:
        # superseded 的 Idea 不进周报：它们已无信号支撑，列出来会让读者
        # 以为仍在跟踪。数据保留在库里，可用 list_ideas(status="superseded") 查。
        ideas = [parse_idea(x) for x in conn.execute(
            "SELECT * FROM ideas WHERE status != ? ORDER BY total_score DESC,radar_hits DESC",
            (SUPERSEDED,),
        ).fetchall()]
        for idea in ideas:
            counts = conn.execute(
                """SELECT SUM(CASE WHEN s.evidence_role='raw_source' AND s.validation_status IN ('verified_source','internal_record') THEN 1 ELSE 0 END) raw_count,
                          SUM(CASE WHEN s.evidence_role!='raw_source' OR s.validation_status NOT IN ('verified_source','internal_record') THEN 1 ELSE 0 END) analysis_count
                   FROM idea_signal_links l JOIN signals g ON g.id=l.signal_id
                   JOIN source_items s ON s.id=g.source_item_id WHERE l.idea_id=?""",
                (idea["id"],),
            ).fetchone()
            idea["raw_evidence_count"] = int(counts["raw_count"] or 0)
            idea["analysis_input_count"] = int(counts["analysis_count"] or 0)
            idea["provenance_ready"] = idea["raw_evidence_count"] > 0
            from radar.evidence.evidence_quality import claim_quality_summary
            quality = claim_quality_summary(idea["id"])
            idea["evidence_confidence"] = quality["evidence_confidence"]
            idea["needs_verification"] = quality["needs_verification"]
            idea["radar_status"] = quality["radar_status"]
            idea["missing_evidence"] = quality["missing_evidence"]
        publishable = [
            x for x in ideas
            if x["provenance_ready"] and x["evidence_confidence"] in {"Medium", "High"}
        ]
        needs_verification = [x for x in ideas if x["total_score"] >= 65 and x["needs_verification"]]
        hot_no = [x for x in publishable if x["status"] == "rejected" or (x["status"] not in {"watch", "mini_eval", "approved"} and x["radar_hits"] <= 1 and x["total_score"] < 65)][:3]
        rank = {"rejected": 0, "watch": 1, "candidate": 2, "mini_eval": 3, "approved": 4}
        changes = {"new": [], "promoted": [], "demoted": [], "eliminated": []}
        for idea in ideas:
            history = conn.execute(
                "SELECT snapshot_json FROM idea_history WHERE idea_id=? ORDER BY id DESC LIMIT 2", (idea["id"],)
            ).fetchall()
            if len(history) == 1:
                changes["new"].append(idea)
            elif len(history) >= 2:
                current = json.loads(history[0]["snapshot_json"])["status"]
                previous = json.loads(history[1]["snapshot_json"])["status"]
                if rank.get(current, 0) > rank.get(previous, 0):
                    changes["promoted"].append(idea)
                elif rank.get(current, 0) < rank.get(previous, 0):
                    changes["demoted"].append(idea)
                if current == "rejected" and previous != "rejected":
                    changes["eliminated"].append(idea)
        return {
            "generated_at": now_iso(),
            "top10": publishable[:10],
            "changes": {k: [x for x in v if x.get("provenance_ready")][:10] for k, v in changes.items()},
            "mini_eval_now": [x for x in publishable if x["status"] in {"mini_eval", "approved"}][:3],
            "watch": [x for x in publishable if x["status"] == "watch"][:3],
            "not_recommended": hot_no,
            "needs_verification": needs_verification[:10],
            "summary": {
                "source_items": conn.execute("SELECT COUNT(*) FROM source_items").fetchone()[0],
                "signals": conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0],
                "idea_pool": len(ideas),
                "provenance_ready_ideas": len(publishable),
                "withheld_for_provenance": len(ideas) - len(publishable),
                "needs_verification": len(needs_verification),
            },
        }
    finally:
        if own:
            conn.close()


def run_pipeline(collect: bool = False) -> dict[str, Any]:
    init_db()
    result: dict[str, Any] = {}
    if collect:
        result["collect"] = collect_sources()
    result["extract"] = extract_pending()
    result["ideas"] = generate_ideas()
    from radar.evidence.evidence_quality import sync_all_idea_quality
    result["evidence_quality"] = sync_all_idea_quality()
    return result

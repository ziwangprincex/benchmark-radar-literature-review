# Benchmark Idea Radar 开发需求包 V1

> 后续工作请先阅读根目录 `00_工作导航.md`。当前阶段是Idea Quality人工验收，暂停新增功能和Offline Mini Eval；企业微信仅按周推送。

## 产品目标
为金融、法律、医疗、科研、Agent 等垂类持续发现高价值 Benchmark Idea。
最终产物不是 AI 新闻摘要，而是可评测、可验证、可立项的 Benchmark Idea。

核心链路：
`发现信号 → 抽象能力 → Evaluation Gap → Idea → 自动评分 → Mini Eval → 正式立项`

## 四条 Radar
1. Benchmark / Leaderboard：别人正在测什么？→ Evaluation Gap
2. Expert Workflow：专业人士真实在做什么？→ Real-world Task
3. Product / Agent：AI 现在开始能做什么？→ New Capability
4. Model Failure：当前模型到底做不好什么？→ Failure Pattern

Radar Hits：1=观察；2=候选；3=优先 Mini Eval；4=重点立项候选。

## 数据流
SourceItem → ExtractedSignal → IdeaCard → MiniEval → BenchmarkProject

## Idea Card Schema
- idea_name
- domain
- sources[]
- source_refs[]
- real_world_task
- capability
- input
- expected_output
- why_hard
- expected_failure
- existing_benchmark
- evaluation_gap
- evaluation_method
- data_source
- mvp_plan
- radar_hits
- status

## 自动评分（100）
- Real-world Value 20
- Model Weakness 20
- Model Differentiation 15
- Novelty 15
- Evaluability 15
- Data Feasibility 10
- Expert Cost 5

建议阈值：80+ 优先 Mini Eval；65-79 候选；50-64 观察；<50 暂缓。

## Scout
### Benchmark Scout
监控论文、HF、GitHub、Leaderboard、研究机构。抽取 Benchmark、能力、任务、Metric、SOTA/模型表现、Failure、创新点、Gap、衍生 Idea。

### Workflow Scout
研究专业人士真实任务。抽取 Profession、Task、Input、Workflow、Output、Required Expertise、Hardest Step、Common Human Mistakes、Likely LLM Failures、Benchmark Potential。

### Product Scout
监控产品更新，但把产品功能转换成 Capability / Real-world Task / Potential Failure / Evaluation Opportunity / Benchmark Idea。

### Failure Scout
从 Bad Case、内部评测、竞品对比抽取可泛化 Failure Pattern，判断是否值得形成 Benchmark。

### Idea Analyst
去重 → 聚类 → 能力抽象 → Gap Analysis → Idea Card → Radar Hits → 评分 → Weekly Top 10。

## Weekly Output
- Top 10 Idea
- Top 3：马上 Mini Eval
- Top 3：持续观察
- Top 3：热门但不建议做
- Idea 的新增/升档/降档/淘汰变化

## Mini Eval Gate
每个高优先级 Idea 先做 30-50 题，多模型实测。
正式立项要求：
- 真实价值明确
- Failure 可复现
- 模型有区分度
- Reference/Rubric 可稳定评判
- 数据和专家成本可接受

## V1 开发优先级
P0：
- 四类 Source 配置 + 定时采集
- 解析 / 去重 / 结构化抽取
- Idea Card + Idea Analyst
- 自动评分 + Radar Hits + 状态流转

P1：
- Weekly Top 10 报告
- Mini Eval 结果回流
- 搜索 / 标签 / 版本历史

P2：
- 自动生成 Mini Eval 草案
- Dashboard / 趋势分析

## 验收
- 四条 Radar 可周期运行
- 跨来源去重/聚类
- 自动生成完整 Idea Card
- 自动评分可解释且可人工覆盖
- Weekly Top 10 可直接用于 PM 决策
- Idea 可追溯原始来源
- Mini Eval 可回流更新评分

## 当前实现（V1 MVP）

### 快速启动
双击 `start_radar.bat`，浏览器访问 `http://127.0.0.1:5000`。

也可手工启动：

```powershell
cd "C:\Users\vegavjzhang\Desktop\Benchmark Idea Radar"
C:\Users\vegavjzhang\AppData\Local\Python\bin\python3.exe -m pip install -r requirements.txt
C:\Users\vegavjzhang\AppData\Local\Python\bin\python3.exe -m radar.web.app
```

首次进入后点击“载入 Demo”，可验证完整链路：
`SourceItem → ExtractedSignal → 聚类 → IdeaCard → 自动评分 → Weekly Top 10`。

### 命令行

```powershell
# 导入 Demo 并执行全链路
python -m radar.core.radar_cli seed

# 采集公开 RSS 并分析
python -m radar.core.radar_cli run --collect

# 只处理已录入的数据
python -m radar.core.radar_cli run

# 生成最新快照
python -m radar.core.radar_cli weekly --output outputs/latest_top10.json

# 生成 ISO 周归档；配置 Webhook 后同时推送企业微信
python -m radar.publish.weekly_job

# 只生成周归档，不推送
python -m radar.publish.weekly_job --no-push

# 回流 Mini Eval（failure-rate 和 judge-agreement 为 0~1）
python -m radar.core.radar_cli mini-eval 1 --sample-size 40 --model-count 5 --sota-score 55 --score-range 32 --failure-rate 0.65 --judge-agreement 0.82

# 同时回流逐Case失败证据
python -m radar.core.radar_cli mini-eval 1 --sample-size 40 --model-count 5 --sota-score 55 --score-range 32 --failure-rate 0.65 --judge-agreement 0.82 --cases-file data/failure_case_schema_example.json
```

### 无 API 的人工 Offline Mini Eval

当前默认采用人工外部执行，不自动调用任何模型 API：

1. 解压 `data/offline_eval_packages/evidence-v1-manual-v2-20260915.zip`。
2. 双击包内 `打开人工执行台.bat`。
3. 分别在3个模型 Slot 中逐题复制 Prompt、在外部模型执行、原样粘贴响应。
4. 每个模型完成20题后导出一个 `model-slot-*.jsonl`。
5. 将3个结果文件放回包目录，双击 `合并并校验结果.bat`。
6. 先执行 Dry-run 客观评分并人工审阅；确认后才运行正式 `--ingest`。

工作台支持浏览器本地自动保存、完成进度、任务筛选、Prompt/Tool Schema一键复制、时间记录、备份恢复与逐模型导出。人工界面无法提供Provider Raw JSON时，会明确记录 `manual_external_ui` 与原样响应，不冒充API原始结果。CMB-Clin仍等待医生校准Rubric，不在当前执行范围。

### 目录

代码按职责分为五层，全部在 `radar/` 包下，用 `python -m radar.<层>.<模块>` 运行：

| 目录 | 职责 | 主要模块 |
|---|---|---|
| `radar/core/` | 数据底座与命令行 | `radar_core.py`（SQLite 对象、采集、去重、抽取、聚类、评分、状态流转、Mini Eval 回流）、`radar_cli.py` |
| `radar/evidence/` | Evidence 质量、检索与 Coverage | `evidence_quality.py`、`evidence_retrieval.py`、`evidence_import.py`、`evidence_qa.py`、`coverage_probe.py`、`coverage_probe_report.py`、`load_coverage_matrix.py` |
| `radar/eval/` | Mini Eval 与人工离线执行 | `mini_eval_runner.py`、`offline_eval.py`、`offline_workbench.py`、`prepare_mini_eval_cases.py` |
| `radar/publish/` | 静态页、周报、推送、定时 | `insight_pages.py`、`weekly_job.py`、`verify_insight_links.py`、`scheduler.py` |
| `radar/web/` | 本地工作台 | `app.py`、`templates/`、`static/` |
| `scripts/` | 一次性工具 | `build_idea_radar.py`（Excel 生成） |

`radar_core.BASE_DIR` 指向项目根（本文件位于 `radar/core/`，上溯两层），
`data/`、`config/`、`outputs/` 均相对项目根解析，不随模块位置变化。
- `config/sources.json`：四类 Scout 来源配置
- `data/sample_source_items.json`：四类 Radar 示例数据
- `data/radar.db`：统一 Signal Pool、Idea Card、版本历史与 Mini Eval 数据库
- `outputs/weekly/`：按 `YYYY-Www` 独立保存的周报版本
- `templates/`、`static/`：工作台前端

### 评分与状态
总分 100：真实任务价值20、模型弱点20、模型区分度15、创新性15、可评判性15、数据可行性10、专家成本5。

- `80+`：优先 Mini Eval
- `65–79`：候选
- `50–64`：观察
- `<50`：暂缓

Radar Hits 只统计具备有效Claim-Evidence映射的 `Verified` Radar；`Partial` 可展示但不计完整Hit，`Hypothesis` / `Unsupported` 不计。Idea Score回答“如果Idea成立有多值得做”，Evidence Confidence回答“当前证据有多充分”，两者独立。Mini Eval只有携带真实Eval Run和Case级原始数据时，才会更新Model Weakness / Differentiation。

### 企业微信周报与 Insight Drill-down

每周五 17:30 的自动任务会先为 Idea Pool 中**每个 Idea**生成独立静态详情页并发布整个站点，不是只部署一个 Weekly Report 页面。当前公网入口：

`https://841a88bd19dc4d24aef378021d3607b7.ap-singapore.myide.io`

独立详情 URL 规则：

`{RADAR_PUBLIC_BASE_URL}/idea-{idea_id}-{slug}.html`

企业微信中的 Idea 标题和“查看 Insight”均 Deep Link 到对应独立页面。每个页面至少包含 Core Insight、Why Now、四条 Radar Evidence、Existing Benchmark、Evaluation Gap、Model Failure、Benchmark Proposal、Mini Eval Design、Score Breakdown、原始 Source Links 与 Provenance。

Evidence Drill-down 层级：

`Weekly Radar → Idea → Evidence Group → Evidence Item → Raw Source`

其中 Model Failure Evidence 还可继续进入 `Failure Case`，展示 Task/Prompt、Input、Reference Answer、Model Name/Version、Model Response、Score/Pass-Fail、Failure Type、Severity、Error Analysis、Judge Result、Run Date 及原始附件/数据。`failure-evidence.html` 支持按 Model、Failure Type、Severity、Benchmark 筛选。

所有 Evidence Item 页面必须明确区分三层：

- **RAW SOURCE · 未经二次总结**：真实原始材料及其URL/记录、标题、发布时间、Section/Page/Case/Run定位信息。
- **EVIDENCE EXTRACTION · 从原文提取**：从Raw Source提取的Task、字段、片段和Failure，不加入价值判断。
- **AI ANALYSIS · 系统推断**：taxonomy、task design、hard step、new capability、evaluation gap、failure pattern等；展示抽取器版本和置信度，并提示人工复核。

只有外部真实原始URL，或具备Record ID/Run ID/Case ID/附件的内部原始记录，才能标记为Raw Source。人工或LLM总结标记为Analysis，不计入Radar Evidence和发布门禁。

四类 Evidence 的标准展示：

| Radar | Raw Evidence | AI Analysis |
|---|---|---|
| Benchmark | 原 Benchmark / Paper / GitHub / Leaderboard | Taxonomy / Task Design / Evaluation Gap |
| Expert Workflow | 原 Workflow / SOP / 访谈片段 | Task / Hardest Step / Common Mistakes / Expertise |
| Product / Agent | 官方 Release / Blog / Demo | New Capability / Previous Workflow / Evaluation Opportunity |
| Model Failure | Prompt / Input / Reference / Model Response / Judge | Failure Pattern / Root Cause / Severity |

自动任务会生成：

- `outputs/insights/index.html`：Insight 索引
- `outputs/insights/idea-{id}-{slug}.html`：每个 Idea 的独立页面
- `outputs/insights/idea-{id}-evidence-{radar}.html`：Evidence Group
- `outputs/insights/idea-{id}-evidence-{source_item_id}.html`：Evidence Item
- `outputs/insights/raw-source-{source_item_id}.html`：Raw Source
- `outputs/insights/failure-case-{case_id}.html`：逐Case失败详情
- `outputs/insights/failure-evidence.html`：Failure Case筛选聚合页
- `outputs/insights/eval-run-{run_id}.html`：Eval Run统计、模型准确率、最大差异和全部Cases
- `outputs/insights/idea-{id}-retrieval-log.html`：Retrieval Query、全部候选、选中/拒绝和原因
- `outputs/insights/manifest.json`：完整URL映射
- `outputs/weekly/YYYY-Www.json`
- `outputs/weekly/YYYY-Www.md`
- `outputs/wecom_push_log.jsonl`

发布门禁：`python -m radar.publish.verify_insight_links --require-public` 必须通过，且全部 Detail URL 返回 HTTP 200，才允许企业微信推送。系统同时支持双向追溯：`Idea → Claim → Evidence Extraction → Raw Source`，以及 `Raw Source → Extraction → Claim → Idea`。没有有效Evidence的Claim必须显示为`Hypothesis`或`Unsupported`。

企业微信机器人地址只通过环境变量注入，不写入代码：

```powershell
setx WECOM_WEBHOOK_URL "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..."
```

设置后需重启承载自动任务的客户端/进程，使其读取新环境变量。`radar/publish/weekly_job.py` 包含3次重试及同一周防重复推送；可用 `--force` 强制重推。

### 当前边界
- 结构化抽取为可复现的规则基线，后续可替换为 LLM Extractor。
- Benchmark、公开 Expert Workflow、Product/Agent 支持自动采集；Expert Workflow 同时支持专家人工录入。
- Evidence Retrieval为Claim驱动：保留`retrieval_query`、全部`retrieved_sources`、`selected/rejected`与`rejection_reason`；论文API限流时记录失败并等待重试，不生成替代Evidence。
- Claim-Evidence支持`supports`、`partially_supports`、`contradicts`、`irrelevant`；Evidence Status支持`verified`、`partial`、`hypothesis`、`unsupported`。
- Source Quality支持`primary`、`secondary`、`internal`、`ai_generated`；AI-generated不得成为Verified Evidence。同源转载通过Canonical URL/Source和duplicate group去重。
- Evidence保存`published_at`、`retrieved_at`、`last_verified_at`、`source_version`、`extraction_version`与`analysis_version`。
- Model Failure 接受 Mini Eval 自动回流，以及 Benchmark Run、模型对比、Bad Case、人工反馈的 API/CLI/工作台录入。
- 逐Case接口：`POST /api/ideas/{idea_id}/failure-cases`；查询接口：`GET /api/failure-cases?model=&failure_type=&severity=&benchmark=`。
- 逐Case标准结构见 `data/failure_case_schema_example.json`；Mini Eval 可通过 `--cases-file` 同时回流明细。
- RSS 来源受外部站点网络可用性影响。
- V1 使用本地 SQLite，适合单机 PM 工作台；多人权限和正式线上部署属于后续版本。

# Benchmark Idea Radar

Benchmark 选题辅助工具。系统负责论文采集、领域归类和待读提醒，并可接入大模型起草文献综述；最终结论由人工判断。

文献综述围绕以下三个问题展开：

1. 已有研究：现有 Benchmark 覆盖了哪些任务
2. 研究空白：尚未覆盖的任务或评测维度
3. 可行方向：可立项的 Benchmark 方向

覆盖法律、金融、医疗、科研、Agent、编程、通用七个领域。代码类 Agent（如 SWE-bench）归入编程，浏览与工具调用类 Agent 归入 Agent。

## 功能

| 功能 | 说明 | 是否需要模型 |
|---|---|---|
| 论文采集 | 每周从 arXiv 采集 Benchmark 相关论文，并按领域归类 | 否 |
| 待读清单 | 按领域列出新论文（标题、链接、摘要首句），支持标记"已读"和"不用读" | 否 |
| 文献综述 | 每个领域分为全部综述与本周小结，二者不重叠，详见下文 | 是 |

### 收录规则

参照 [ktwu01/benchmark-radar](https://github.com/ktwu01/benchmark-radar) 的做法，采用宽口径收录，仅打标签、不做删除。标题或摘要满足任一规则即收录：

- 标题含 benchmark、dataset 等词，或摘要声明构建、发布了数据集或评测集
- 命中参考项目的入口短语（如 "benchmark for"、"we introduce a dataset"、"leaderboard"）
- 名称带 Bench、Eval，或标题表明为模型评测研究

收录的论文标注为以下三类之一，仅用于筛选和排序：

- 新 Benchmark
- 评测研究
- 可能是方法

最终哪些论文写入综述，由抽卡阶段模型判定的类型和人工标记的"不用读"共同决定。

### 文献综述

- 全部综述：截至上周的累计论文，含 2023 年以来回补的历史论文。每周一更新后，上一周的论文并入。
- 本周小结：最近一周新收录的论文，并与全部综述对比，列出新方向、已填补的空白和与已有方向的重合情况。

两者流程相同：

1. 逐篇抽卡：从每篇摘要提取任务、输入、评分方式、数据规模、主要发现和作者自述局限。
2. 分类：先分 QA 与 Agent 两个大类，再在大类内按任务和输入划分主题。QA 指模型单次作答即判分；Agent 指模型需在环境中连续执行动作。
3. 撰写：分类表与边界说明由程序生成，其余章节由模型撰写。

生成后可通过批注修订，也可导出为 Markdown。

综述仅依据标题与摘要，不读取全文。程序校验两项内容：引用编号在资料中存在；「」内原话可在对应摘要中逐字找到。内容是否准确需人工审阅。

## 本地运行

环境要求：Python 3.9 及以上。

```bash
pip install -r requirements.txt
python3 -m radar.web.app
```

浏览器访问 <http://127.0.0.1:5000>，包含"待读清单"和"文献综述"两个页面。

文献综述使用步骤：

1. 在"文献综述"页填写接口地址、密钥和模型名称。支持任意 OpenAI 兼容接口（OpenAI、DeepSeek、混元、本地 vLLM 等）。
2. 选择领域与范围（全部综述或本周小结），点击"更新"。建议先生成全部综述，本周小结以其为对比基准。
3. 审阅结果。分类有误时，在"分类"页调整论文归属或主题所属大类；内容有误时，在右侧填写批注并点击"按批注改稿"。
4. 在"更新与下载"中点击"下载 .md"导出，文中编号均链接至论文原文。

### 数据保存

- 分类与综述按浏览器会话隔离，保存 24 小时。不同用户互不可见，首次打开均为空白。
- 抽卡结果按摘要内容缓存，所有用户共用，已抽取的论文不重复调用模型。
- 模型密钥仅保存在本机 `data/llm_config.json`，不纳入版本控制。

## 网页版

在线地址：<https://ziwangprincex.github.io/benchmark-radar-literature-review/>

网页版部署于 GitHub Pages，为只读版本：待读清单的标记仅保存在当前浏览器，不能生成综述。生成综述需本地运行，见上文"本地运行"。

## 定时更新

GitHub Actions（`.github/workflows/weekly.yml`）于每周一 15:00（北京时间）执行：采集 arXiv 新论文、归类，并重新生成网页版。不推送消息。

执行时间可能延迟数分钟至数十分钟，运行记录见仓库 Actions 页面。数据库执行后保存至 `data` 分支，供下次执行使用。立即更新网页可在 Actions → weekly → Run workflow 中手动触发，或执行：

```bash
gh workflow run weekly.yml
```

本地手动执行，结果输出至 `reports/weekly_refresh.md`：

```bash
python3 scripts/weekly_refresh.py --no-push
```

## 目录结构

| 路径 | 内容 |
|---|---|
| `radar/core/` | 数据库、采集、领域归类（`lit_index.py`）、待读清单（`reading.py`） |
| `radar/review/` | 文献综述流程 |
| `radar/review/prompts/` | 各步骤提示词，调整综述格式只需修改此处 |
| `radar/web/` | 网页（`static/static_shim.js` 为静态站专用） |
| `scripts/` | 每周刷新、arXiv 批量采集、静态站导出（`build_static_site.py`） |
| `data/radar.db` | 论文与阅读状态（不在 main 分支，最新版本位于 `data` 分支） |
| `data/backfill/` | 四个领域的历史论文 |
| `reports/lit_review/<领域>/cards.json` | 抽卡缓存（所有用户共用） |
| `reports/lit_review/_sessions/` | 各会话的分类与综述，24 小时无访问后清理 |
| `reports/lit_coverage.md` | 各领域"任务 × 输入"覆盖表，用于检查收录缺口 |
| `archive/` | 已停用的历史模块（早期 Idea 打分、Mini Eval，以及 2026-10-09 停用的研究地图与撞车提醒） |

## 测试

```bash
pip install pytest
python3 -m pytest tests/ -q
```

# Benchmark Idea Radar

帮做 Benchmark 选题的人写文献综述。Radar 负责把论文收齐、提醒有哪些新的要读；需要的话，接上模型帮你起草综述。结论由人来下。

它想回答三件事，都写在文献综述里：

1. 大家在研究什么（已有的 Benchmark）
2. 大家还没研究什么（缺口）
3. 我们能研究什么（可以做的方向）

覆盖法律、金融、医疗、科研、Agent、编程、通用七个领域。写代码的 Agent（SWE-bench 一类）归编程，浏览、工具调用类 Agent 归 Agent。

## 能做什么

| 功能 | 说明 | 要不要模型 |
|---|---|---|
| 收齐 | 每周从 arXiv 抓新的 Benchmark 论文，按领域分好 | 不要 |
| 待读清单 | 网页上按领域列出新论文（标题、链接、摘要第一句），读完打勾，标"不用读"的不再出现 | 不要 |
| 文献综述 | 每个领域两块：全部综述（全部论文）和本周小结（最近一周新收的）。都按三步走：逐篇抽卡 → 分类 → 写，写完可以写批注让模型改 | 要 |

只有新提出 Benchmark 或评测模型的论文才算：标题里有 benchmark、dataset，名字带 Bench、Eval，或者标题写明在评测模型；只在摘要里说"在某个 Benchmark 上测了"、或者造的是训练数据的方法论文不算。

文献综述只读摘要，不读全文。程序会核对两件事：引用的编号存在，「」里的原话在摘要里找得到。写得对不对，程序判断不了，要你自己读。

## 怎么用

需要 Python 3.9 及以上。

```bash
pip install -r requirements.txt
python3 -m radar.web.app
```

浏览器打开 <http://127.0.0.1:5000>，左边有两个页面：待读清单、文献综述。

用文献综述的话：

1. 在"文献综述"页填接口地址、密钥、模型名。任何 OpenAI 兼容接口都行（OpenAI、DeepSeek、混元、本地 vLLM）。
2. 选一个领域，选"全部综述"或"本周小结"，点"一键更新"。建议先写全部综述：本周小结要拿它来比，才能看出哪些是新方向、补上了哪些空白、和我们的方向撞没撞车。卡片两块共用，不会重复抽。
3. 读生成的综述。分类不对就去"分类"里挪论文；内容不对就在右边写批注，点"按批注改稿"。

密钥只存在本机 `data/llm_config.json`，不会进 git。

## 网页版

在线打开：<https://ziwangprincex.github.io/benchmark-radar-literature-review/>

## 每周自动更新

GitHub Actions（`.github/workflows/weekly.yml`）每周一 15:00（北京时间）跑一遍：抓 arXiv 新论文、分类，重新生成上面的网页版。不推送消息。

不用开电脑，定时任务偶尔会晚几分钟到几十分钟，运行结果在仓库 Actions 页面看。数据库跑完存到 `data` 分支，下次接着用。想马上更新网页：Actions → weekly → Run workflow，或者：

```bash
gh workflow run weekly.yml
```

本地手动跑，结果写到 `reports/weekly_refresh.md`：

```bash
python3 scripts/weekly_refresh.py --no-push
```

## 目录

| 位置 | 内容 |
|---|---|
| `radar/core/` | 数据库、采集、领域分类（`lit_index.py`）、待读清单（`reading.py`） |
| `radar/review/` | 文献综述三步流程 |
| `radar/review/prompts/` | 三步的写作要求，想改综述格式改这里，不用动代码 |
| `radar/web/` | 网页（`static/static_shim.js` 是网页版专用） |
| `scripts/` | 每周刷新、arXiv 批量抓取、导出网页版（`build_static_site.py`） |
| `data/radar.db` | 所有论文和阅读状态（不在 main 分支，最新的一份在 `data` 分支） |
| `reports/lit_review/<领域>/` | 生成的综述、卡片、分类 |
| `reports/lit_coverage.md` | 各领域"任务 × 输入"覆盖表，看哪里没收全 |
| `archive/` | 旧版本资料（早期的 Idea 打分、Mini Eval、2026-10-09 停用的研究地图和撞车提醒），已不再使用 |

## 测试

```bash
pip install pytest
python3 -m pytest tests/ -q
```

# Benchmark Idea Radar

帮做 Benchmark 选题的人写文献综述。Radar 负责把论文收齐、提醒有哪些新的要读；需要的话，接上模型帮你起草综述。结论由人来下。

它想回答三件事，都写在文献综述里：

1. 大家在研究什么（已有的 Benchmark）
2. 大家还没研究什么（缺口）
3. 我们能研究什么（可以做的方向）

覆盖法律、金融、医疗、科研、Agent、通用六个领域。

## 能做什么

| 功能 | 说明 | 要不要模型 |
|---|---|---|
| 收齐 | 每周从 arXiv 抓新的 Benchmark 论文，按领域分好 | 不要 |
| 待读清单 | 网页上按领域列出新论文（标题、链接、摘要第一句），读完打勾，标"不用读"的不再出现 | 不要 |
| 文献综述 | 按三步起草综述：逐篇抽卡 → 分类 → 写综述，写完可以写批注让模型改 | 要 |

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
2. 选一个领域，点"一键更新"。
3. 读生成的综述。分类不对就去"分类"里挪论文；内容不对就在右边写批注，点"按批注改稿"。

密钥只存在本机 `data/llm_config.json`，不会进 git。

## 网页版

在线打开：<https://ziwangprincex.github.io/benchmark-radar-literature-review/>

网页版只能看：待读清单可以勾"已读""不用读"，但勾选只存在你自己的浏览器里，换浏览器或清缓存就没了。跑模型写综述、重新生成索引，要在本地运行（见上面"怎么用"）。

## 每周自动更新

每周一 15:00（北京时间）有两处各跑一遍，分工不同：

| 在哪跑 | 做什么 | 推企业微信 |
|---|---|---|
| 内网开发机（`deploy/radar-weekly.timer`） | 抓 arXiv、分类，更新内网网页 | 推，同一周只推一次 |
| GitHub Actions（`.github/workflows/weekly.yml`） | 抓 arXiv、分类，更新上面的网页版 | 不推 |

推送内容：本周新收多少篇、各领域未读几篇、前几篇标题和链接。

GitHub 这边不用开电脑，定时任务偶尔会晚几分钟到几十分钟，运行结果在仓库 Actions 页面看。数据库跑完存到 `data` 分支，下次接着用。想马上更新网页：Actions → weekly → Run workflow，或者：

```bash
gh workflow run weekly.yml
```

本地手动跑，结果写到 `reports/weekly_refresh.md`：

```bash
python3 scripts/weekly_refresh.py --no-push                # 刷新，不推送
python3 -m radar.publish.wecom_push --dry-run              # 看看推送消息长什么样
python3 -m radar.publish.wecom_push --set-webhook "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..."
```

群机器人地址只存在本机 `data/wecom_config.json`，不进 git。

## 目录

| 位置 | 内容 |
|---|---|
| `radar/core/` | 数据库、采集、领域分类（`lit_index.py`）、待读清单（`reading.py`） |
| `radar/review/` | 文献综述三步流程 |
| `radar/review/prompts/` | 三步的写作要求，想改综述格式改这里，不用动代码 |
| `radar/web/` | 网页（`static/static_shim.js` 是网页版专用） |
| `scripts/` | 每周刷新、arXiv 批量抓取、导出网页版（`build_static_site.py`） |
| `data/radar.db` | 所有论文和阅读状态（最新的一份在 `data` 分支） |
| `reports/lit_review/<领域>/` | 生成的综述、卡片、分类 |
| `reports/lit_coverage.md` | 各领域"任务 × 输入"覆盖表，看哪里没收全 |
| `archive/` | 旧版本资料（早期的 Idea 打分、Mini Eval、2026-10-09 停用的研究地图和撞车提醒），已不再使用 |

## 测试

```bash
pip install pytest
python3 -m pytest tests/ -q
```

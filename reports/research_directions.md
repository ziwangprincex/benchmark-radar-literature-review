# 五个垂类：我们能研究什么（文献综述，2026-10-08）

逐篇读五个垂类中带缺口句的 Benchmark 摘要。每条方向必须同时满足：至少 2 篇论文的作者原话指出同一件事没测到；列出已经做过相近事情的论文并写清差别；能用公开数据起步。原话由程序逐字核对，对不上的方向不展示。撞车检查：每个方向和全库 Benchmark 算相似度，前 10 篇逐篇读摘要，读过的标为已核对。

## 金融（已有 Benchmark 23 个）

### 财报问答：答对了，但依据是错的

需再核对 · 接旧题 #1 · 最像的 10 篇已核对 10 篇

给模型一份年报 PDF 和一个问题，要求同时给出答案、页码和原文句子。答案对错和依据对错分开判，重点统计“答案对、依据错”和“依据对、答案错”各占多少。

- 输入：单份年报 PDF（含表格）
- 判分：答案按数值容差判对；页码和原文句子单独判是否命中标注证据
- 数据：FinanceBench 公开 150 题自带证据原文，可直接用

为什么说没人做：
> Existing benchmarks predominantly evaluate only the final answer, making it difficult to localize errors or assess whether an answer is well-founded. —— [FinFIRST](https://arxiv.org/abs/2609.25192)
>
> decisions must be traceable to specific evidence pages and the cost of an unsupported answer is high —— [XL-DocBench](https://arxiv.org/abs/2608.00036)
>
> GPT-4-Turbo used with a retrieval system incorrectly answered or refused to answer 81% of questions —— [FinanceBench](https://arxiv.org/abs/2311.11944)
>

和已有工作差在哪：
- [FinFIRST](https://arxiv.org/abs/2609.25192)：FinFIRST 测的是联网搜索 Agent，证据来自网页；这里是给定一份财报，只看模型能不能在文档里指对位置
- [XL-DocBench](https://arxiv.org/abs/2608.00036)：XL-DocBench 横跨六个行业，金融只占一部分，也不单独统计“答对但依据错”
- [A Citation-Grounded Benchmark for Trustworthy Earnings Call Transcript Analysis with Large Language Models](https://arxiv.org/abs/2610.00969v1)：ECTs-100 已经把“依据对不对”和“答案对不对”分开评了，但用的是业绩电话会文字稿，且依据只看数字能不能对上；这里用带表格的年报 PDF，要求指到页码和原文句子，并统计“答案对、依据错”的交叉比例
- [LEDGER](https://arxiv.org/abs/2606.13100)：LEDGER 用 4999 份完整年报做页码级检索和 KPI 抽取，但只评“找没找到”，不把答案对错和依据对错交叉统计
- [DocAttriBench](https://arxiv.org/abs/2609.20574v2)：DocAttriBench 做文档问答的答案溯源，精确到版面元素，但不是金融，也不统计“答对但依据错”

### 财报数字：报告期和口径对不上

需再核对 · 接旧题 #28 · 最像的 10 篇已核对 10 篇

同一个指标成对出题，只改报告期（2023 财年和 2024 财年）或口径（合并和母公司、GAAP 和 Non-GAAP），看模型会不会拿错期间或错口径的数字来回答。

- 输入：多期年报 / 财务表格
- 判分：数值按容差判对；拿错期间、拿错口径、单位错分别记成不同的错误类型
- 数据：LEDGER 年报 + KPI 标注，按年份配对出题

为什么说没人做：
> temporally valid information retrieval, authoritative source selection, entity and period alignment, unit and definition consistency —— [FinFIRST](https://arxiv.org/abs/2609.25192)
>
> forecast-based reasoning poses a substantial challenge —— [STQA](https://arxiv.org/abs/2609.06117v1)
>
> most public financial resources reduce the task to plain-text SEC 10-K filings paired with a handful of question-answer items —— [LEDGER](https://arxiv.org/abs/2606.13100)
>

和已有工作差在哪：
- [FinFIRST](https://arxiv.org/abs/2609.25192)：FinFIRST 把期间对齐当成评分细则里的一项，没有成对出题，量不出“只改期间，答案跟着变没变”
- [LEDGER](https://arxiv.org/abs/2606.13100)：LEDGER 提供了 4999 份年报和 KPI 标注，可以作为出题素材，但它本身不测期间和口径混淆
- [FinInteract](https://arxiv.org/abs/2609.24002v1)：FinInteract 已经测到“合并口径 vs 分部口径”这类歧义（如 Meta 营业利润 467.5 亿 vs 628.7 亿），但测的是模型会不会追问澄清；这里测的是不追问时，模型拿错报告期或口径的比例

别做了，已经有人做了：

- [FrontierFinance](https://arxiv.org/abs/2608.11683v1)：投资研究全流程的长答案，FrontierFinance 已经做了 220 题

## 法律（已有 Benchmark 24 个）

### 法条已经废止或被修订，模型还照用

需再核对 · 新方向 · 最像的 10 篇已核对 10 篇

在给模型的参考材料里混入已废止的旧条文、下位法或其他法域的条文，问同一个问题，看模型是否还会引用失效或不适用的法条。

- 输入：问题 + 检索到的多条法条（有效和失效混在一起）
- 判分：答案对错；是否引用了失效或不适用的条文，单独记“误用失效法条率”
- 数据：法规修订前后的版本是公开的，可以直接生成成对题

为什么说没人做：
> legal LLMs struggle to assess when retrieved citations are useful or misleading —— [Sycophants in the Courtroom: Are LLMs Fragile to Juridical Authority and Evolving Legal Standards?](https://arxiv.org/abs/2608.21409)
>
> truth is contingent, defined by jurisdiction, temporal validity, and the hierarchy of authoritative sources —— [Sycophants in the Courtroom: Are LLMs Fragile to Juridical Authority and Evolving Legal Standards?](https://arxiv.org/abs/2608.21409)
>
> Fine-tuning can improve legal question-answering accuracy without improving how models use law supplied in context. —— [Do Small Models Use the Law You Give Them? Measuring Context Use on a Bilingual Bangladesh Legal Benchmark](https://arxiv.org/abs/2608.30327v1)
>

和已有工作差在哪：
- [Sycophants in the Courtroom: Are LLMs Fragile to Juridical Authority and Evolving Legal Standards?](https://arxiv.org/abs/2608.21409)：Sycophants in the Courtroom 做的是法律和医疗的对比诊断，题量小；这里专做修订前后的条文成对题
- [Do Small Models Use the Law You Give Them? Measuring Context Use on a Bilingual Bangladesh Legal Benchmark](https://arxiv.org/abs/2608.30327v1)：孟加拉那篇只测删掉关键条文之后模型的表现，没测把失效条文混进去会怎样
- [Do Large Language Models Know Colombian Law? A Reliability Benchmark for the Colombian Legal System](https://arxiv.org/abs/2610.03639v1)：哥伦比亚法律那篇发现模型引用的法条约一半是错的或不存在，说明问题真实存在；但它没区分“引用了已废止的条文”这一类，也没有修订前后的成对题
- [GreekBarRetrieval](https://arxiv.org/abs/2608.18752v3)：GreekBarRetrieval 做法条检索，但候选法条都是现行有效的，没有失效版本混在里面

别做了，已经有人做了：

- [LexAgentHallu](https://arxiv.org/abs/2609.09754v1)：法律 Agent 在多步过程中的幻觉，LexAgentHallu 已经做了 3414 条，不再重复
- [ContractScrub](https://arxiv.org/abs/2608.20204v1)：整份合同终审、找错误和前后矛盾，ContractScrub 已经做了（律师手工构造的合同），加上 RGDT-Bench 已经分开评“决定”和“理由”，不再重复

## 医疗（已有 Benchmark 141 个）

### 病历里前一位医生写错了，模型会跟着错

撞车风险低 · 新方向 · 最像的 10 篇已核对 10 篇

在病历里加一句看起来可信但错误的前序诊断或会诊意见，和不加这句的原版对比，看模型的诊断会不会被带偏。

- 输入：文字病历（带或不带误导性前序意见）
- 判分：“原本答对、加了误导句后答错”的比例，按误导来源（前医生、检索到的文献、患者自述）分组
- 数据：MIMIC 或 CMB-Clin 病例，每题配一句误导意见

为什么说没人做：
> Existing benchmarks measure whether models answer correctly in isolation, but not whether they preserve a correct image-only decision when plausible context conflicts with the image. —— [MC-CXR](https://arxiv.org/abs/2608.24118v1)
>
> Existing benchmarks fail to assess whether large language models truly possess the reasoning capability required for diagnostic ambiguity scenarios —— [SUP-MIMIC](https://arxiv.org/abs/2608.29582v1)
>

和已有工作差在哪：
- [MC-CXR](https://arxiv.org/abs/2608.24118v1)：MC-CXR 只做胸片影像，这里只用文字病历，任何纯文本模型都能测
- [SUP-MIMIC](https://arxiv.org/abs/2608.29582v1)：SUP-MIMIC 测的是症状本身有歧义，不是被外部意见带偏
- [DAYJOB](https://arxiv.org/abs/2610.01306v1)：DAYJOB 的案例里提到 Agent 会接受和病历相矛盾的前提，但只是案例观察，没有加误导句和不加的对照
- [AnchorBench](https://arxiv.org/abs/2608.14320v1)：AnchorBench 系统测了 LLM 的锚定效应，但是通用数值判断，不是病历里的前序医生意见
- [EHR-RobustGym](https://arxiv.org/abs/2609.39371v1)：EHR-RobustGym 测病历数据有噪声时 Agent 会不会发现，噪声是数据库里的缺值和错值，不是“前一位医生的错误诊断”

### 诊断对了，治疗建议却不安全

需再核对 · 接旧题 #3 · 最像的 10 篇已核对 10 篇

同一个病例成对出题，只改一个患者条件（肾功能差、过敏、正在吃某种药），看模型的用药或处置建议有没有跟着改；直接危及生命的错误单独记。

- 输入：文字病例
- 判分：致命错误一票否决并单独计数；诊断正确率和建议安全率分开报
- 数据：MIMIC 公开病例或教科书病例，改写患者条件

为什么说没人做：
> even frontier models with the highest diagnosis accuracy violate safety constraints in over half of high-risk cases —— [GPAgentBench-2K](https://arxiv.org/abs/2608.30188v2)
>
> their capabilities in clinical history taking, urgency assessment, and safety remain insufficiently evaluated —— [Japanese Stroke LLM Evaluation: A Conversational Benchmark for Safe Stroke Care in Japanese Using Large Language Models](https://arxiv.org/abs/2609.16739v1)
>

和已有工作差在哪：
- [GPAgentBench-2K](https://arxiv.org/abs/2608.30188v2)：GPAgentBench-2K 测的是全科门诊的行动顺序，没有只改一个患者条件的成对题
- [Japanese Stroke LLM Evaluation: A Conversational Benchmark for Safe Stroke Care in Japanese Using Large Language Models](https://arxiv.org/abs/2609.16739v1)：日本卒中那篇只有 10 个病例，靠医生扮演病人，没法扩大规模
- [AnesTRACE](https://arxiv.org/abs/2609.32740v2)：AnesTRACE 在麻醉多步决策里单独统计了严重安全错误率（17.5%），但没有只改一个患者条件的成对题

### 每一步都对，连起来却错了

容易撞车 · 接旧题 #18 · 最像的 10 篇已核对 10 篇

把“按指南得出推荐”拆成几步（判断适用人群、找到对应条目、检查禁忌、给出结论），每一步单独判，再看端到端的结果，统计错误在哪一步开始累积。

- 输入：病例 + 临床指南
- 判分：每一步正确率、端到端正确率，以及两者之差（错误累积）
- 数据：公开临床指南 + 教科书病例

为什么说没人做：
> despite the top model reaching 98.88% Atomic Consistency, its end-to-end consistency collapses to 45.13% —— [LogiMed-RoB](https://arxiv.org/abs/2609.11185v1)
>
> even when models retrieve high-quality evidence, they fail to deduce correct outcomes in 18.63-40.05% of cases —— [LogiMed-RoB](https://arxiv.org/abs/2609.11185v1)
>
> These findings underscore a substantial gap between current retrieval techniques and the reasoning demands of real clinical tasks. —— [R2MED](https://r2med.github.io/)
>

和已有工作差在哪：
- [LogiMed-RoB](https://arxiv.org/abs/2609.11185v1)：LogiMed-RoB 用的是 Cochrane 偏倚评估（评审论文），不是给病人做治疗推荐；可以借用它的分步判分方法
- [R2MED](https://r2med.github.io/)：R2MED 只测检索这一步
- [MEGA-CDP](https://arxiv.org/abs/2608.26592v1)：MEGA-CDP 已经测过“是否按指南路径做决策”，覆盖 2274 份指南；这里只剩“逐步判分、量出错误从哪一步开始累积”一个差异点，需要读全文确认它有没有步骤级分数
- [AnesTRACE](https://arxiv.org/abs/2609.32740v2)：AnesTRACE 已经评了麻醉场景的多步决策和时间一致性；加上 MEGA-CDP，这个方向只剩“逐步判分量出错误累积”一个差别
- [GPAgentBench-2K](https://arxiv.org/abs/2608.30188v2)：GPAgentBench-2K 评全科就诊的多步动作序列，但按最终结果和安全约束判分，不逐步判

别做了，已经有人做了：

- [MVC-Bench](https://arxiv.org/abs/2608.27004v2)：医学视觉模型的置信度校准，MVC-Bench 已经做了

## 科研（已有 Benchmark 172 个）

### 多步科学计算里单位和数量级出错

撞车风险低 · 新方向 · 最像的 10 篇已核对 10 篇

出需要 3 步以上计算、中间涉及单位换算的科学题，逐步检查每一步的数值和单位，看错误在哪一步出现。

- 输入：文字题 + 数据表
- 判分：最终数值按容差判对；每一步的单位错、数量级错、公式错分别计数
- 数据：物理、化学教材习题，按步骤标注

为什么说没人做：
> execute transparent calculations, reconcile source differences, and preserve provenance in the final answer —— [EarthVerse](https://arxiv.org/abs/2608.23525v1)
>
> canonical accuracy is 0.969-0.996, but orbit correctness falls to 0.848-0.981 —— [Same Quantity, Different Answer](https://arxiv.org/abs/2609.25009)
>

和已有工作差在哪：
- [EarthVerse](https://arxiv.org/abs/2608.23525v1)：EarthVerse 是地球科学领域的完整 Agent 调查任务，太重；这里只抽出计算链这一环
- [Same Quantity, Different Answer](https://arxiv.org/abs/2609.25009)：Same Quantity 只测同一个数换种写法，不涉及多步计算
- [BioPhys-Bridge](https://arxiv.org/abs/2609.19180v1)：BioPhys-Bridge 把单位、公式和数值作为证据标注，但评分看的是证据编号 F1，不单独统计单位和数量级错误

### 引用的证据撑不起结论

容易撞车 · 接旧题 #25 · 最像的 10 篇已核对 10 篇

给论文片段和一个结论，让模型判断证据是否支撑结论并说明理由；专门挑那些听起来合理、但证据其实不支撑的结论来出题。

- 输入：论文段落 + 待判断的结论
- 判分：支撑 / 部分支撑 / 不支撑三分类；单独统计“不支撑却判成支撑”的比例
- 数据：论文的“结论 + 引用”对；库外的 SciFact 需要先查重

为什么说没人做：
> among non-hallucinated correct-positive judgments, over 70% cite evidence fails to logically support the stated reason —— [NovGauge](https://arxiv.org/abs/2609.11234v1)
>
> it remains unclear whether they truly reason from scientific evidence or simply produce convincing-sounding ideas —— [HypoKG](https://arxiv.org/abs/2609.12260)
>
> They therefore provide limited evidence about whether model decisions are supported by sufficient and reliable review evidence. —— [Beyond Final Decisions: A Process-Centric Benchmark for Transparent AI-Assisted Peer Review](https://arxiv.org/abs/2609.05947v1)
>

和已有工作差在哪：
- [NovGauge](https://arxiv.org/abs/2609.11234v1)：NovGauge 只测判断论文新不新，这里测判断结论有没有被证据支撑
- [HypoKG](https://arxiv.org/abs/2609.12260)：HypoKG 让模型生成假设，这里让模型判断别人的结论
- [Peerify: Benchmarking Peer-Review Claim Verification](https://arxiv.org/abs/2609.25046)：Peerify 已经在做“审稿意见是否被论文证据支撑”（800 条）；这里要换成论文自己的结论和它引用的文献，否则就是重复
- [Sci-MMR](https://arxiv.org/abs/2609.11243v2)：Sci-MMR 测多模态科研 Agent 的多步推理有没有可追溯证据，做的是推理链整体；这里只做单个结论和证据之间的支撑判断，题更轻，也能批量出
- [VERITYGATE](https://arxiv.org/abs/2610.00833v1)：VERITYGATE 用成对题检查解释里的说法有没有被结构化证据支撑，思路很接近，只是证据来自数据表而不是论文
- [InSight](https://arxiv.org/abs/2609.01383v1)：InSight 做交互式图表上的说法核查，证据来自图表而不是论文引用

别做了，已经有人做了：

- [SciLitBench](https://arxiv.org/abs/2609.05505v1)：系统综述全流程（筛选到数据抽取），SciLitBench 已经做了
- [ChemDIRT](https://arxiv.org/abs/2608.21504v1)：化学题换种写法后的鲁棒性，ChemDIRT 已经做了

## Agent（已有 Benchmark 206 个）

### 工具返回了错误结果，Agent 照单全收

容易撞车 · 新方向 · 最像的 10 篇已核对 10 篇

在金融或医疗场景的工具调用里，故意让工具返回错误的数值或过期的数据，看 Agent 会不会核对、追问或拒答，还是直接把错误写进最终答案。

- 输入：带工具的垂类任务（查行情、查药品说明书等）
- 判分：工具返回正确时的成功率，和工具返回错误时的识别率、拒答率分开报
- 数据：复用 BFCL / tau 工具任务，把工具返回值替换成错误值

为什么说没人做：
> The four instruction-tuned models retain a verified-correct answer against an incorrect tool in only 6.5-17.1% of eligible cases —— [MemToC](https://arxiv.org/abs/2608.26295v1)
>
> existing benchmarks evaluate them only on accurate tickets and always assume a fault is present, conditions rarely met in practice —— [FaulT-Bench](https://arxiv.org/abs/2608.27021v1)
>
> models rarely detect conflicting evidence, often continue along executable but unsupported analysis paths —— [TrustDABench](https://arxiv.org/abs/2608.24145v1)
>

和已有工作差在哪：
- [MemToC](https://arxiv.org/abs/2608.26295v1)：MemToC 用的是通用事实题，也只测了 7-9B 的小模型
- [FaulT-Bench](https://arxiv.org/abs/2608.27021v1)：FaulT-Bench 只做网络运维场景
- [KC-Bench](https://arxiv.org/abs/2609.03588v1)：KC-Bench 测了工具观察与模型自身知识的冲突，但用的是通用任务、只有 238 题；这里的差别在金融和医疗场景，以及工具返回错误时的拒答率
- [Failure-Transparent Agents: Benchmarking Post-Failure Reporting in Tool-Using Language Models](https://arxiv.org/abs/2609.35732v1)：FTA 测工具明确失败后 Agent 会不会谎报成功，假成功率 22.8%；这里测的是工具没报错、但返回了错误数值的情况
- [COPEX](https://arxiv.org/abs/2610.04378v1)：COPEX 测工具输出里的恶意注入，属于安全攻击，不是数据本身错了
- [Do Agent Benchmarks Do What They Say? An Executable-Contract Audit of Tool-Using Agent Environments](https://arxiv.org/abs/2609.37315v1)：Executable-Contract 审计查的是 Benchmark 里的工具本身有缺陷（工具说写了其实没写），对象是评测环境，不是 Agent 会不会察觉

别做了，已经有人做了：

- [ParaRecover](https://arxiv.org/abs/2609.12345v1)：Agent 中途出错后能否定位并恢复，ParaRecover 已经做了一万条
- [HybridDeepResearch](https://arxiv.org/abs/2609.09410v1)：网页搜索和数据库查询之间交接时约束丢失，HybridDeepResearch 已经做了
- [AgentDrift](https://arxiv.org/abs/2609.06972v1)：逐步标注注入攻击从哪一步进入轨迹，AgentDrift 已经做了
- [AgentJudgeBench](https://arxiv.org/abs/2608.26623v1)：LLM 裁判评 Agent 工具调用是否可靠，AgentJudgeBench 已经做了 3808 条，有/无标准答案两种条件并和程序化结果对照；加上 MobileJudgeBench，不再重复

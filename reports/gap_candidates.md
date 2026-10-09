# Benchmark 缺口候选卡（lit-v3，2026-10-09）

生成方式：只定死五个垂类领域；从 Benchmark 摘要中抽取作者自述缺口句，按“领域 × 关注点”聚类，需求信号只用真实外部来源（不含系统自生成种子）。纯正则，不调 API。

共 326 张：候选 33 张，观察 293 张。

## 候选

### C1. 法律 · LexIssue / ContractEval / ViLegalExpert

- 问题：However, legal issues remain comparatively underexplored in legal AI research.
- 任务：生成/撰写、检索、审查/核查；输入：长文档、多文档/知识库、工具/环境
- 支撑：Benchmark 5 篇，真实需求信号 2 条
- 现有 Benchmark 用的判分：专家/人工、准确率/EM
- 判分建议：以漏报率为主指标（高风险项召回），误报率为辅；专家 rubric 标注风险等级
- 对应旧 Idea：#2 合同跨条款风险审查
- 下一步：人工读 5 篇支撑 Benchmark 原文，确认缺口没被后续工作填上；再抽 20 题做 Mini Eval

作者自述缺口：
> [LexIssue] However, legal issues remain comparatively underexplored in legal AI research.
>
> [ContractEval] The potential of large language models (LLMs) in specialized domains such as legal risk analysis remains underexplored.
>
> [ViLegalExpert] However, existing Vietnamese legal benchmarks provide limited coverage of real-world legal consultations.
>
> [LexAgentHallu] However, existing legal benchmarks evaluate only single-turn QA with outcome-level metrics, while agentic hallucination benchmarks lack legal-specific diagnostic capability.
>

支撑 Benchmark：[LexIssue](https://arxiv.org/abs/2609.02954v1)、[ContractEval](https://arxiv.org/abs/2508.03080)、[ViLegalExpert](https://arxiv.org/abs/2609.39189v1)、[LexAgentHallu](https://arxiv.org/abs/2609.09754v1)、[LegalBench-RAG](https://arxiv.org/abs/2408.10343)
需求信号：[NET](https://www.onetonline.org/link/details/23-1011.00)、[NET](https://www.onetonline.org/link/details/23-2011.00)
邻近已覆盖（需对比差异）：[ContractScrub](https://arxiv.org/abs/2608.20204v1)、[CUAD](https://arxiv.org/abs/2103.06268)、[Better Call CLAUSE](https://arxiv.org/abs/2511.00340)、[PARCEL](https://arxiv.org/abs/2610.10971v1)、[Do Large Language Models Know Colombian Law? A Reliability Benchmark for the Colombian Legal System](https://arxiv.org/abs/2610.03639v1)、[Sycophants in the Courtroom: Are LLMs Fragile to Juridical Authority and Evolving Legal Standards?](https://arxiv.org/abs/2608.21409)

### C2. 科研 · MechHypoBench / Sci-MMR / SciDocBench

- 问题：Experiments with general agents and AI scientists reveal a substantial gap between generated hypotheses and the underlying mechanisms.
- 任务：生成/撰写、Agent任务、审查/核查；输入：结构化/代码、工具/环境、多模态
- 支撑：Benchmark 4 篇，真实需求信号 1 条
- 现有 Benchmark 用的判分：准确率/EM、执行/成功率
- 判分建议：最终答案 + 推理过程 rubric（是否由证据推出），过程分与结果分分开报
- 判分建议：答案正确率与证据定位（页/条款/句级）命中率分开计分，禁止只看最终答案
- 对应旧 Idea：无（新方向）
- 下一步：人工读 4 篇支撑 Benchmark 原文，确认缺口没被后续工作填上；再抽 20 题做 Mini Eval

作者自述缺口：
> [MechHypoBench] Experiments with general agents and AI scientists reveal a substantial gap between generated hypotheses and the underlying mechanisms.
>
> [Sci-MMR] Existing multimodal benchmarks, however, largely evaluate final-answer accuracy, leaving open whether predictions are actually supported by traceable scientific evidence.
>
> [Sci-MMR] First, evidence acquisition: models struggle to extract complete structured evidence from scientific figures, accounting for 57.2% of failures.
>
> [SciDocBench] Existing benchmarks typically evaluate these capabilities in isolation, leaving unclear whether multimodal models can support realistic scientific-reading workflows.
>

支撑 Benchmark：[MechHypoBench](https://arxiv.org/abs/2610.05197v1)、[Sci-MMR](https://arxiv.org/abs/2609.11243v2)、[SciDocBench](https://arxiv.org/abs/2609.05141v1)、[SciHorizon-eLab](https://arxiv.org/abs/2609.30971v1)
需求信号：[NET](https://www.onetonline.org/link/details/19-1042.00)
邻近已覆盖（需对比差异）：[OSWorld-Science](https://arxiv.org/abs/2609.39903v1)、[AgentIdeaBench](https://arxiv.org/abs/2609.07611v1)、[AutoSciBench](https://arxiv.org/abs/2610.05140v1)、[TRACES](https://arxiv.org/abs/2608.11415v1)、[EarthVerse](https://arxiv.org/abs/2608.23525v1)、[WebVisus](https://arxiv.org/abs/2608.22045v1)

### C3. Agent · EnterpriseBench / The Era by Eon Benchmark: A Generated Enterprise Estate with Exact Ground Truth for Benchmarking LLM Agents / DI-Bench

- 问题：However, existing enterprise and financial benchmarks mainly test static capabilities such as information extraction, numerical calculation, domain knowledge, and financial QA, leaving interactive and long-horizon decision-making underexplored.
- 任务：Agent任务、推理/计算、抽取；输入：工具/环境、结构化/代码、多轮对话
- 支撑：Benchmark 4 篇，真实需求信号 1 条
- 现有 Benchmark 用的判分：准确率/EM、专家/人工、Rubric
- 判分建议：端到端完成率 + 步骤级错误定位（检索/证据使用/规则遵循分开记）
- 判分建议：数值按容差判对，单位与口径错误单列
- 对应旧 Idea：无（新方向）
- 下一步：人工读 4 篇支撑 Benchmark 原文，确认缺口没被后续工作填上；再抽 20 题做 Mini Eval

作者自述缺口：
> [EnterpriseBench] However, existing enterprise and financial benchmarks mainly test static capabilities such as information extraction, numerical calculation, domain knowledge, and financial QA, leaving interactive and long-horizon decision-making underexplored.
>
> [The Era by Eon Benchmark: A Generated Enterprise Estate with Exact Ground Truth for Benchmarking LLM Agents] LLM agents for enterprise systems of record cannot be evaluated on customer production data, and no existing substitute provides ground truth.
>
> [DI-Bench] Evaluating enterprise agents on domain-specific benchmarks is critical, yet public benchmarks rarely evaluate whether agents can integrate business knowledge with analytical computation, and constructing such benchmarks manually is costly.
>
> [EmailBench] This gap shows that valid tool execution is not equivalent to task completion.
>

支撑 Benchmark：[EnterpriseBench](https://arxiv.org/abs/2609.37658v2)、[The Era by Eon Benchmark: A Generated Enterprise Estate with Exact Ground Truth for Benchmarking LLM Agents](https://arxiv.org/abs/2609.09853v1)、[DI-Bench](https://arxiv.org/abs/2609.05776v1)、[EmailBench](https://arxiv.org/abs/2609.31906v1)
需求信号：[ScarfBench](https://huggingface.co/blog/ibm-research/scarfbench)
邻近已覆盖（需对比差异）：[EnterpriseRAG](https://arxiv.org/abs/2608.11584v1)、[Era by Eon: Benchmarking Enterprise Agents on Hidden Knowledge](https://arxiv.org/abs/2609.30055v1)、[CoSE-E](https://arxiv.org/abs/2609.35645v1)、[MBA](https://arxiv.org/abs/2608.11616v2)

### C4. Agent · UTILMEM / LOCOMO-CONV / DyadMem

- 问题：Long-term memory is increasingly important for conversational agents, yet existing benchmarks primarily measure memory through pointwise factual recall: whether a system can recover isolated facts or event-level details from prior interactions.
- 任务：生成/撰写、Agent任务、检索；输入：多轮对话、结构化/代码
- 支撑：Benchmark 3 篇，真实需求信号 2 条
- 现有 Benchmark 用的判分：F1/P/R
- 判分建议：以漏报率为主指标（高风险项召回），误报率为辅；专家 rubric 标注风险等级
- 判分建议：答案正确率与证据定位（页/条款/句级）命中率分开计分，禁止只看最终答案
- 对应旧 Idea：无（新方向）
- 下一步：人工读 3 篇支撑 Benchmark 原文，确认缺口没被后续工作填上；再抽 20 题做 Mini Eval

作者自述缺口：
> [UTILMEM] Long-term memory is increasingly important for conversational agents, yet existing benchmarks primarily measure memory through pointwise factual recall: whether a system can recover isolated facts or event-level details from prior interactions.
>
> [LOCOMO-CONV] However, existing benchmarks primarily evaluate memory through QA-style probing rather than in-situ conversational usage.
>
> [UTILMEM] These findings expose a substantial gap between accessing stored information and using it effectively, and suggest that progress in long-term conversational memory will require architectures that explicitly support evidence integration and robustness to retrieval interference.
>
> [UTILMEM] Real-world memory use, however, often requires a more demanding capability: integrating distributed, implicit, and noisy evidence across extended interaction histories into coherent, task-oriented outputs.
>

支撑 Benchmark：[UTILMEM](https://arxiv.org/abs/2608.30508v1)、[LOCOMO-CONV](https://arxiv.org/abs/2609.03467v2)、[DyadMem](https://arxiv.org/abs/2610.03020v1)
需求信号：[Give Your Coding Agents a Memory You Own](https://huggingface.co/blog/funes)、[How V7 gives AI agents institutional memory](https://openai.com/index/v7)
邻近已覆盖（需对比差异）：[Total Recall at What Cost? Benchmarking the Serving Cost of Agentic Memory Systems](https://arxiv.org/abs/2608.11879v1)、[Memory Canonicalization: A Framework and Benchmark for Cross-Model Drift in Persistent LLM Memory](https://arxiv.org/abs/2610.05124v1)、[You Know What I Mean: A Benchmark for Agentic Conversational Reference Grounding](https://arxiv.org/abs/2608.29834v1)、[PII-TRACE](https://arxiv.org/abs/2609.22200v1)、[MemCalib](https://arxiv.org/abs/2609.24259v2)

### C5. 医疗 · VIPER / Benchmarking Vision-Language Models for Automated Pathology Diagnosis and Report Generation / PathLang

- 问题：Pathology vision-language models are advancing rapidly, yet existing benchmarks remain focused on human tissue, particularly oncology, leaving non-human pathology largely unaddressed.
- 任务：推理/计算、分类/识别、检索；输入：多模态、结构化/代码、多文档/知识库
- 支撑：Benchmark 4 篇，真实需求信号 0 条
- 判分建议：答案正确率与证据定位（页/条款/句级）命中率分开计分，禁止只看最终答案
- 判分建议：以漏报率为主指标（高风险项召回），误报率为辅；专家 rubric 标注风险等级
- 对应旧 Idea：无（新方向）
- 下一步：人工读 4 篇支撑 Benchmark 原文，确认缺口没被后续工作填上；再抽 20 题做 Mini Eval

作者自述缺口：
> [VIPER] Pathology vision-language models are advancing rapidly, yet existing benchmarks remain focused on human tissue, particularly oncology, leaving non-human pathology largely unaddressed.
>
> [Benchmarking Vision-Language Models for Automated Pathology Diagnosis and Report Generation] The rapid advancement of vision-language models (VLMs) has accelerated progress in computational pathology; however, whole-slide image (WSI)-based pathology report generation remains limited by the scarcity of large-scale WSI--report datasets and the complexity of mapping spatially distributed visual patterns to structured clinical text.
>
> [PathLang] In clinical practice, however, diagnostic language varies across reports, institutions, and candidate diagnoses.
>
> [VIPER] The results identify a substantial domain gap between veterinary and human pathology, expose the risk of over-diagnosis of normal tissue in frontier models, and show that domain-specific training remains critical for visually grounded predictions.
>

支撑 Benchmark：[VIPER](https://arxiv.org/abs/2608.26382v1)、[Benchmarking Vision-Language Models for Automated Pathology Diagnosis and Report Generation](https://arxiv.org/abs/2609.00866v1)、[PathLang](https://arxiv.org/abs/2610.11329v1)、[CellPath-Bench](https://arxiv.org/abs/2608.21060v1)
邻近已覆盖（需对比差异）：[PetQA](https://arxiv.org/abs/2609.04598v1)、[MTDiag](https://arxiv.org/abs/2608.25085v1)、[SUP-MIMIC](https://arxiv.org/abs/2608.29582v1)、[CLIMB](https://arxiv.org/abs/2609.35462v1)、[Reliable Benchmarking of Artifact Detection in Computational Pathology: A Reproducibility and Uncertainty Analysis](https://arxiv.org/abs/2608.30835v1)、[SkinLex](https://arxiv.org/abs/2610.08086v1)

### C6. 金融 · FINESSE / MM-FinEval / FinFraudBench

- 问题：Machine learning research in financial services is limited by the scarcity of representative open-source datasets.
- 任务：分类/识别、推理/计算、生成/撰写；输入：多模态、结构化/代码、工具/环境
- 支撑：Benchmark 3 篇，真实需求信号 2 条
- 判分建议：答案正确率与证据定位（页/条款/句级）命中率分开计分，禁止只看最终答案
- 对应旧 Idea：#1 PDF财报异常识别与证据引用
- 下一步：人工读 3 篇支撑 Benchmark 原文，确认缺口没被后续工作填上；再抽 20 题做 Mini Eval

作者自述缺口：
> [FINESSE] Machine learning research in financial services is limited by the scarcity of representative open-source datasets.
>
> [FINESSE] Existing resources are often narrowly focused on a single modality or task and fail to reflect the structured, multimodal, and dynamic nature inherent to many problems in financial services.
>
> [MM-FinEval] However, existing financial benchmarks are often limited to unimodal inputs or single-task settings, making it difficult to evaluate whether multimodal large language models (LLMs) can support real-world financial analysis.
>
> [FinFraudBench] However, despite rapid progress in graph-based methods, existing public benchmarks remain misaligned with real-world financial systems in two important aspects.
>

支撑 Benchmark：[FINESSE](https://arxiv.org/abs/2609.11993v1)、[MM-FinEval](https://arxiv.org/abs/2609.38523v1)、[FinFraudBench](https://arxiv.org/abs/2608.15177v1)
需求信号：[NET](https://www.onetonline.org/link/details/13-2051.00)、[From Information to Delegation: Mapping Human-AI Financial Decision Making](https://arxiv.org/abs/2608.02100)
邻近已覆盖（需对比差异）：[FinancialAuditBench](https://arxiv.org/abs/2609.32835v1)、[FinRAG-QA](https://arxiv.org/abs/2609.03654v1)、[FinCUABuild](https://arxiv.org/abs/2609.07603v1)、[FinFIRST](https://arxiv.org/abs/2609.25192v1)、[From Benchmarks to Production: A Text-to-SQL System for Complex Financial Data](https://arxiv.org/abs/2610.03524v1)、[FinanceBench](https://arxiv.org/abs/2311.11944)

### C7. 科研 · PhysicsMate / How Good Are Frontier Models at Physics? Expert Re-Grading Reveals Broken Evaluations and Near-Saturation of Leading Benchmarks / OmniPhys

- 问题：Bengali secondary education lacks curriculum-grounded benchmarks for STEM question-solving, and general-purpose language models struggle with the precise terminology, unit conventions, and derivations that physics problems demand.
- 任务：推理/计算、问答、审查/核查；输入：工具/环境、结构化/代码、多模态
- 支撑：Benchmark 3 篇，真实需求信号 0 条
- 现有 Benchmark 用的判分：准确率/EM、专家/人工、执行/成功率
- 判分建议：答案正确率与证据定位（页/条款/句级）命中率分开计分，禁止只看最终答案
- 判分建议：数值按容差判对，单位与口径错误单列
- 对应旧 Idea：无（新方向）
- 下一步：人工读 3 篇支撑 Benchmark 原文，确认缺口没被后续工作填上；再抽 20 题做 Mini Eval

作者自述缺口：
> [PhysicsMate] Bengali secondary education lacks curriculum-grounded benchmarks for STEM question-solving, and general-purpose language models struggle with the precise terminology, unit conventions, and derivations that physics problems demand.
>
> [How Good Are Frontier Models at Physics? Expert Re-Grading Reveals Broken Evaluations and Near-Saturation of Leading Benchmarks] Low reported scores on leading physics benchmarks, including those featured in the Artificial Analysis Intelligence Index (2026), suggest that frontier language models still struggle with advanced physics, a demanding test of their scientific reasoning and quantitative problem-solving abilities.
>
> [OmniPhys] However, their development in the physics domain is significantly hindered by the lack of a comprehensive benchmark.
>
> [PhysicsMate] The 4B model has been adapted and quantized to a small offline binary that can be used for local inference in resource constrained environments and offers a viable path to curriculum aligned physics support in environments with limited connectivity and hardware.
>

支撑 Benchmark：[PhysicsMate](https://arxiv.org/abs/2610.00664v1)、[How Good Are Frontier Models at Physics? Expert Re-Grading Reveals Broken Evaluations and Near-Saturation of Leading Benchmarks](https://arxiv.org/abs/2609.13009v1)、[OmniPhys](https://arxiv.org/abs/2608.25398v1)
邻近已覆盖（需对比差异）：[Benchmarking Optimizers to Solve Inverse Problems with Differentiable Physics Simulators](https://arxiv.org/abs/2609.13819v1)、[PhysicsBench](https://arxiv.org/abs/2608.24056v1)、[PACE-Bench](https://arxiv.org/abs/2608.14441v1)、[PolyBridgeBench](https://arxiv.org/abs/2609.21493v1)、[PhysAlign](https://arxiv.org/abs/2609.33319v1)、[Development and Validation of a Physics-Guided Machine Learning Extrapolation Framework Using a Classical Transient Diffusion Benchmark](https://arxiv.org/abs/2609.09912v1)

### C8. 科研 · SciLitBench / A Systematic Evaluation of Molecule Generation Models for De Novo Drug Design: From Benchmarks to Practical Insights / HalluPeer

- 问题：Systematic reviews require sustained human judgment across thousands of records, yet existing evaluations of large language models (LLMs) typically examine review stages in isolation.
- 任务：审查/核查、分类/识别、生成/撰写；输入：长文档、工具/环境
- 支撑：Benchmark 3 篇，真实需求信号 0 条
- 现有 Benchmark 用的判分：准确率/EM、F1/P/R
- 判分建议：答案正确率与证据定位（页/条款/句级）命中率分开计分，禁止只看最终答案
- 对应旧 Idea：无（新方向）
- 下一步：人工读 3 篇支撑 Benchmark 原文，确认缺口没被后续工作填上；再抽 20 题做 Mini Eval

作者自述缺口：
> [SciLitBench] Systematic reviews require sustained human judgment across thousands of records, yet existing evaluations of large language models (LLMs) typically examine review stages in isolation.
>
> [A Systematic Evaluation of Molecule Generation Models for De Novo Drug Design: From Benchmarks to Practical Insights] However, existing reviews typically address specific model families or application scenarios in isolation, rather than offering an integrated perspective on how these components collectively form a coherent generation workflow.
>
> [HalluPeer] Experiments on 12K papers and 38K reviews show that existing detectors struggle to separate hallucinations from legitimate critique, while evaluation on authentic reviews demonstrates that HalluPeer-defined hallucination patterns occur in real peer reviews, highlighting the critical need for source-aware verification.
>

支撑 Benchmark：[SciLitBench](https://arxiv.org/abs/2609.05505v1)、[A Systematic Evaluation of Molecule Generation Models for De Novo Drug Design: From Benchmarks to Practical Insights](https://arxiv.org/abs/2609.10099v1)、[HalluPeer](https://arxiv.org/abs/2609.03580v1)
邻近已覆盖（需对比差异）：[A Benchmark Framework for Screening Automation in Systematic Reviews](https://arxiv.org/abs/2609.30298v2)、[Beyond Imitation: A Framework and Benchmark for LLM-Assisted Peer Review](https://arxiv.org/abs/2610.11087v1)、[Beyond Final Decisions: A Process-Centric Benchmark for Transparent AI-Assisted Peer Review](https://arxiv.org/abs/2609.05947v1)

### C9. 科研 · ReVA / FairRSFM / VesselBench-800K

- 问题：However, existing remote sensing multimodal reasoning benchmarks exhibit two critical limitations: they rely on (i) template-driven questions, which causes repetitive questions; and (ii) static images that fail to capture the inherent temporal nature of drone/UAV videos.
- 任务：审查/核查、推理/计算、问答；输入：多模态、结构化/代码、工具/环境
- 支撑：Benchmark 3 篇，真实需求信号 0 条
- 现有 Benchmark 用的判分：F1/P/R
- 判分建议：按时间切片出题，同题不同截止日期对照；过时答案单独计为错误类型
- 判分建议：域内 vs 域外（跨地区/跨案件/跨机构）分组计分，报告差值
- 对应旧 Idea：无（新方向）
- 下一步：人工读 3 篇支撑 Benchmark 原文，确认缺口没被后续工作填上；再抽 20 题做 Mini Eval

作者自述缺口：
> [ReVA] However, existing remote sensing multimodal reasoning benchmarks exhibit two critical limitations: they rely on (i) template-driven questions, which causes repetitive questions; and (ii) static images that fail to capture the inherent temporal nature of drone/UAV videos.
>
> [FairRSFM] Remote sensing foundation models (RSFMs) are commonly evaluated using aggregate metrics, which can hide systematic performance disparities across ecological regions.
>
> [VesselBench-800K] However, most existing datasets predominantly focus on general object detection tasks in optical remote sensing (RS) images.
>

支撑 Benchmark：[ReVA](https://arxiv.org/abs/2609.35507v1)、[FairRSFM](https://arxiv.org/abs/2610.05790v1)、[VesselBench-800K](https://arxiv.org/abs/2609.37003v1)
邻近已覆盖（需对比差异）：[Object Counting Across Modalities: Taxonomies, Benchmarks, Applications, and Open Challenges](https://arxiv.org/abs/2608.23845v1)、[VPRef](https://arxiv.org/abs/2609.16486v1)、[USAI-Quant](https://arxiv.org/abs/2609.32813v1)、[A Unified Framework and Dataset for Oriented Object Visual Grounding in Remote Sensing](https://arxiv.org/abs/2609.28230v2)、[PolyTopoBench](https://arxiv.org/abs/2609.32856v1)

### C10. Agent · Cross-Benchmark Transfer from RL on Agentic Coding Tasks / MTAC-IFBench

- 问题：We ask whether reinforcement learning (RL) on expert-built agentic coding tasks closes this gap, and whether what the agent learns transfers beyond the training distribution.
- 任务：审查/核查、Agent任务、分类/识别；输入：工具/环境、结构化/代码、多轮对话
- 支撑：Benchmark 2 篇，真实需求信号 2 条
- 现有 Benchmark 用的判分：执行/成功率
- 判分建议：域内 vs 域外（跨地区/跨案件/跨机构）分组计分，报告差值
- 对应旧 Idea：无（新方向）
- 下一步：人工读 2 篇支撑 Benchmark 原文，确认缺口没被后续工作填上；再抽 20 题做 Mini Eval

作者自述缺口：
> [Cross-Benchmark Transfer from RL on Agentic Coding Tasks] We ask whether reinforcement learning (RL) on expert-built agentic coding tasks closes this gap, and whether what the agent learns transfers beyond the training distribution.
>
> [MTAC-IFBench] However, existing benchmarks typically focus on final functional correctness or confine instruction-following evaluation to single-turn, general chat or simple code generation scenarios, leaving instruction-following in multi-turn agentic coding underexplored.
>

支撑 Benchmark：[Cross-Benchmark Transfer from RL on Agentic Coding Tasks](https://arxiv.org/abs/2610.00890v1)、[MTAC-IFBench](https://arxiv.org/abs/2609.14992v1)
需求信号：[Qwen3-Coder](https://qwenlm.github.io/blog/qwen3-coder)、[Upgrading agentic coding capabilities with the new Devstral models](https://mistral.ai/news/devstral-2507)
邻近已覆盖（需对比差异）：[AgentPerfBench](https://arxiv.org/abs/2609.34683v1)、[Compact Documentation for Coding Agents: A Benchmark, an Optimizer, and Why It Does Not Transfer](https://arxiv.org/abs/2609.31587v1)、[ParanoiaEval](https://arxiv.org/abs/2610.08662v2)、[TestJack](https://arxiv.org/abs/2610.10619v1)、[Reflections on Trusting Trust, Revisited: Contaminating Self-Modifying AI Coding Agents with Poisoned Benchmarks](https://arxiv.org/abs/2609.17817v1)、[What Does an Agentic Software Engineering Benchmark Measure? Profiling Task Demands and Agent Behaviour Beyond What Category Labels Reveal](https://arxiv.org/abs/2609.01271v1)

### C11. Agent · DuplexSpeechBench-Document Grounding / $τ$-Multilingual

- 问题：Voice agents enable low-latency, natural interaction, yet their ability to faithfully ground responses in external documents remains underexplored.
- 任务：审查/核查、生成/撰写、Agent任务；输入：多轮对话、工具/环境
- 支撑：Benchmark 2 篇，真实需求信号 2 条
- 现有 Benchmark 用的判分：准确率/EM、执行/成功率
- 判分建议：以漏报率为主指标（高风险项召回），误报率为辅；专家 rubric 标注风险等级
- 对应旧 Idea：无（新方向）
- 下一步：人工读 2 篇支撑 Benchmark 原文，确认缺口没被后续工作填上；再抽 20 题做 Mini Eval

作者自述缺口：
> [DuplexSpeechBench-Document Grounding] Voice agents enable low-latency, natural interaction, yet their ability to faithfully ground responses in external documents remains underexplored.
>
> [$τ$-Multilingual] The failure modes also vary: Korean systems miss more responses, Mandarin systems interrupt more often, and both struggle with tools and entities.
>

支撑 Benchmark：[DuplexSpeechBench-Document Grounding](https://arxiv.org/abs/2610.00316v1)、[$τ$-Multilingual](https://arxiv.org/abs/2609.35820v1)
需求信号：[NVIDIA](https://huggingface.co/blog/nvidia/magpie-tts-multilingual-voice-agents)、[Build real-time voice agents on Together AI](https://www.together.ai/blog/build-real-time-voice-agents-on-together-ai)
邻近已覆盖（需对比差异）：[$τ$-Elicitation](https://arxiv.org/abs/2609.13602v1)、[IndicFDB](https://arxiv.org/abs/2609.31967v1)、[Talk2Agent](https://arxiv.org/abs/2609.38867v1)、[Compact Documentation for Coding Agents: A Benchmark, an Optimizer, and Why It Does Not Transfer](https://arxiv.org/abs/2609.31587v1)、[BabelArena](https://arxiv.org/abs/2609.23490v1)

### C12. 医疗 · Holtercare-Bench: A Multimodal Benchmark for Evaluating Long-Term Dynamic ECG Analysis / ECGQuest / TRACE

- 问题：In the critical field of dynamic electrocardiograms (ECG), models struggle with complex temporal reasoning and diagnostic report generation due to a lack of high-quality datasets and benchmarks.
- 任务：生成/撰写、推理/计算、问答；输入：多模态、结构化/代码
- 支撑：Benchmark 3 篇，真实需求信号 0 条
- 现有 Benchmark 用的判分：准确率/EM、专家/人工
- 判分建议：按时间切片出题，同题不同截止日期对照；过时答案单独计为错误类型
- 对应旧 Idea：无（新方向）
- 下一步：人工读 3 篇支撑 Benchmark 原文，确认缺口没被后续工作填上；再抽 20 题做 Mini Eval

作者自述缺口：
> [Holtercare-Bench: A Multimodal Benchmark for Evaluating Long-Term Dynamic ECG Analysis] In the critical field of dynamic electrocardiograms (ECG), models struggle with complex temporal reasoning and diagnostic report generation due to a lack of high-quality datasets and benchmarks.
>
> [ECGQuest] Existing language-model benchmarks, however, primarily assess broad medical knowledge or interpretation of individual ECG signals and images rather than the broader contextual knowledge required for ECG interpretation.
>
> [TRACE] It is designed to address the limitations of existing CLIP-style training, which often struggles with noisy clinical text and fails to leverage the complementary strengths of unimodal (from ECG) and cross-modal (between ECG and matched cardiologist reports) learning.
>
> [Holtercare-Bench: A Multimodal Benchmark for Evaluating Long-Term Dynamic ECG Analysis] Zero-shot evaluations of leading MLLMs reveal a significant performance gap in processing ultra-long pathological sequences.
>

支撑 Benchmark：[Holtercare-Bench: A Multimodal Benchmark for Evaluating Long-Term Dynamic ECG Analysis](https://arxiv.org/abs/2608.19297v1)、[ECGQuest](https://arxiv.org/abs/2608.30893v1)、[TRACE](https://arxiv.org/abs/2609.34088v1)
邻近已覆盖（需对比差异）：[Label-Efficient Deep Learning for ECG Delineation: A Multi-Dataset Benchmark against Widely Used Delineation Tools](https://arxiv.org/abs/2610.07885v1)、[Benchmarking Vision-Language Models for Automated Pathology Diagnosis and Report Generation](https://arxiv.org/abs/2609.00866v1)、[VIPER](https://arxiv.org/abs/2608.26382v1)

### C13. 医疗 · MedCalc-Eval and MedCalc-Env / From Scores to Steps: Diagnosing and Improving LLM Performance in Evidence-Based Medical Calculations

- 问题：As large language models (LLMs) enter the medical domain, most benchmarks evaluate them on question answering or descriptive reasoning, overlooking quantitative reasoning critical to clinical decision-making.
- 任务：抽取、推理/计算、Agent任务；输入：结构化/代码、工具/环境
- 支撑：Benchmark 2 篇，真实需求信号 2 条
- 现有 Benchmark 用的判分：准确率/EM、专家/人工
- 判分建议：数值按容差判对，单位与口径错误单列
- 判分建议：答案正确率与证据定位（页/条款/句级）命中率分开计分，禁止只看最终答案
- 对应旧 Idea：#18 临床推理与指南溯源、#3 患者特异性用药安全决策
- 下一步：人工读 2 篇支撑 Benchmark 原文，确认缺口没被后续工作填上；再抽 20 题做 Mini Eval

作者自述缺口：
> [MedCalc-Eval and MedCalc-Env] As large language models (LLMs) enter the medical domain, most benchmarks evaluate them on question answering or descriptive reasoning, overlooking quantitative reasoning critical to clinical decision-making.
>
> [From Scores to Steps: Diagnosing and Improving LLM Performance in Evidence-Based Medical Calculations] Large language models (LLMs) have demonstrated promising performance on medical benchmarks; however, their ability to perform medical calculations, a crucial aspect of clinical decision-making, remains underexplored and poorly evaluated.
>
> [From Scores to Steps: Diagnosing and Improving LLM Performance in Evidence-Based Medical Calculations] Existing benchmarks often assess only the final answer with a wide numerical tolerance, overlooking systematic reasoning failures and potentially causing serious clinical misjudgments.
>
> [MedCalc-Eval and MedCalc-Env] Existing datasets like MedCalc-Bench cover few calculation tasks and fail to reflect real-world computational scenarios.
>

支撑 Benchmark：[MedCalc-Eval and MedCalc-Env](https://arxiv.org/abs/2510.27267)、[From Scores to Steps: Diagnosing and Improving LLM Performance in Evidence-Based Medical Calculations](https://arxiv.org/abs/2509.16584)
需求信号：[MedCalc-Bench](https://huggingface.co/datasets/nsk7153/MedCalc-Bench-Verified)、[NET](https://www.onetonline.org/link/details/29-2072.00)
邻近已覆盖（需对比差异）：[MedCalc-Bench](https://arxiv.org/abs/2406.12036)、[MEDEC](https://arxiv.org/abs/2412.19260)、[CMB](https://aclanthology.org/2024.naacl-long.343)、[MVC-Bench](https://arxiv.org/abs/2608.27004v2)、[MMTClinic](https://arxiv.org/abs/2609.04842v1)、[Beyond Natural-Image Foundation Models: Benchmarking Satellite Pretraining for Ophthalmic Image Analysis](https://arxiv.org/abs/2608.15195v1)

### C14. 科研 · ChemDIRT / RxnOptBench

- 问题：However, existing chemistry benchmarks often provide only a narrow view of model capability, focusing on limited task sets while overlooking robustness to variations in problem formulation and chemical representation.
- 任务：审查/核查、推理/计算、分类/识别；输入：表格、结构化/代码
- 支撑：Benchmark 2 篇，真实需求信号 1 条
- 现有 Benchmark 用的判分：准确率/EM
- 判分建议：原题与扰动题（改格式/插误导证据/改措辞）成对出现，计一致率与翻转率
- 对应旧 Idea：无（新方向）
- 下一步：人工读 2 篇支撑 Benchmark 原文，确认缺口没被后续工作填上；再抽 20 题做 Mini Eval

作者自述缺口：
> [ChemDIRT] However, existing chemistry benchmarks often provide only a narrow view of model capability, focusing on limited task sets while overlooking robustness to variations in problem formulation and chemical representation.
>
> [RxnOptBench] Across nine frontier LLMs and three Chemistry LLMs, even the best models leave substantial headroom: chemistry-specialized models fall to the random-baseline floor on multi-axis selection, while open-weight models have closed most of the gap to proprietary frontier models.
>

支撑 Benchmark：[ChemDIRT](https://arxiv.org/abs/2608.21504v1)、[RxnOptBench](https://arxiv.org/abs/2610.02242v1)
需求信号：[NET](https://www.onetonline.org/link/details/19-2031.00)
邻近已覆盖（需对比差异）：[From Benchmark to Bench: Can Agents Survive Real-World Drug Discovery?](https://arxiv.org/abs/2610.06411v1)、[FREA](https://arxiv.org/abs/2610.06614v1)

### C15. Agent · MobileWorldSafety / AgentDrift

- 问题：Despite these risks, existing benchmarks often fail to capture everyday user scenarios, lacking a systematic evaluation of GUI agents under environmental injection attacks on mobile devices.
- 任务：审查/核查、Agent任务、评判；输入：工具/环境、多文档/知识库
- 支撑：Benchmark 2 篇，真实需求信号 1 条
- 现有 Benchmark 用的判分：执行/成功率、F1/P/R
- 判分建议：原题与扰动题（改格式/插误导证据/改措辞）成对出现，计一致率与翻转率
- 判分建议：判分结果与真实任务成功率做相关与一致性检验（kappa / Spearman）
- 对应旧 Idea：无（新方向）
- 下一步：人工读 2 篇支撑 Benchmark 原文，确认缺口没被后续工作填上；再抽 20 题做 Mini Eval

作者自述缺口：
> [MobileWorldSafety] Despite these risks, existing benchmarks often fail to capture everyday user scenarios, lacking a systematic evaluation of GUI agents under environmental injection attacks on mobile devices.
>
> [AgentDrift] Existing benchmarks measure whether such attacks succeed against live agents, and existing guard models judge a trace as a whole; no public corpus labels, step by step, where an injection enters a trajectory and which steps it corrupts.
>
> [MobileWorldSafety] However, because these agents routinely process untrusted environmental content, they are highly vulnerable to environmental injection attacks, which include indirect prompt injections and adversarial instructions.
>
> [MobileWorldSafety] These findings indicate that current agents often fail to maintain safety alignment when adversarial content is presented as ordinary mobile context.
>

支撑 Benchmark：[MobileWorldSafety](https://arxiv.org/abs/2608.17659v1)、[AgentDrift](https://arxiv.org/abs/2609.06972v1)
需求信号：[Echoverse: Deep, evolving environments for computer-use agents](https://www.microsoft.com/en-us/research/blog/echoverse-deep-evolving-environments-for-computer-use-agents)
邻近已覆盖（需对比差异）：[LongPIBench](https://arxiv.org/abs/2608.28411v1)、[GUI-CC](https://arxiv.org/abs/2609.00048v1)、[GMA](https://arxiv.org/abs/2608.27477v1)、[MobileJudgeBench](https://arxiv.org/abs/2608.11434v1)、[DIBench](https://arxiv.org/abs/2610.06898v1)、[ElderBench](https://arxiv.org/abs/2609.04850v1)

### C16. Agent · MBA / One Success Isn't Reliability

- 问题：Following prior work, we evaluate agents across six business-oriented criteria using MLLM-as-a-Judge.
- 任务：Agent任务、检索、生成/撰写；输入：多模态、工具/环境、结构化/代码
- 支撑：Benchmark 2 篇，真实需求信号 1 条
- 现有 Benchmark 用的判分：LLM裁判、执行/成功率
- 判分建议：判分结果与真实任务成功率做相关与一致性检验（kappa / Spearman）
- 对应旧 Idea：#24 Agent选型门禁的判据可靠性
- 下一步：人工读 2 篇支撑 Benchmark 原文，确认缺口没被后续工作填上；再抽 20 题做 Mini Eval

作者自述缺口：
> [MBA] Following prior work, we evaluate agents across six business-oriented criteria using MLLM-as-a-Judge.
>
> [One Success Isn't Reliability] Thinkingbox-bench reveals a large gap between occasionally finding a successful trajectory and reliably completing stateful business tasks.
>

支撑 Benchmark：[MBA](https://arxiv.org/abs/2608.11616v2)、[One Success Isn't Reliability](https://arxiv.org/abs/2608.19741v2)
需求信号：[Genie One MCP: Give any AI Agent the Right Business Context](https://www.databricks.com/blog/genie-one-mcp-give-any-ai-agent-right-business-context)

### C17. 医疗 · MVC-Bench / CT-$Δ$Bench

- 问题：However, existing efforts mainly focused on improving accuracy, leaving calibration in the medical domain underexplored.
- 任务：分类/识别、抽取、生成/撰写；输入：多模态、结构化/代码
- 支撑：Benchmark 2 篇，真实需求信号 1 条
- 现有 Benchmark 用的判分：准确率/EM
- 判分建议：答案正确率与证据定位（页/条款/句级）命中率分开计分，禁止只看最终答案
- 判分建议：按时间切片出题，同题不同截止日期对照；过时答案单独计为错误类型
- 对应旧 Idea：#18 临床推理与指南溯源
- 下一步：人工读 2 篇支撑 Benchmark 原文，确认缺口没被后续工作填上；再抽 20 题做 Mini Eval

作者自述缺口：
> [MVC-Bench] However, existing efforts mainly focused on improving accuracy, leaving calibration in the medical domain underexplored.
>
> [CT-$Δ$Bench] Yet, despite this central role of temporal comparison in clinical decision-making, existing medical foundation models remain largely confined to single-study understanding, leaving temporally grounded cross-examination insufficiently addressed.
>

支撑 Benchmark：[MVC-Bench](https://arxiv.org/abs/2608.27004v2)、[CT-$Δ$Bench](https://arxiv.org/abs/2608.11534v2)
需求信号：[NET](https://www.onetonline.org/link/details/29-2072.00)
邻近已覆盖（需对比差异）：[From Scores to Steps: Diagnosing and Improving LLM Performance in Evidence-Based Medical Calculations](https://arxiv.org/abs/2509.16584)、[CMB](https://aclanthology.org/2024.naacl-long.343)、[MedCalc-Bench](https://arxiv.org/abs/2406.12036)、[MEDEC](https://arxiv.org/abs/2412.19260)、[Beyond Natural-Image Foundation Models: Benchmarking Satellite Pretraining for Ophthalmic Image Analysis](https://arxiv.org/abs/2608.15195v1)、[Real-World Multi-Modal and Longitudinal Lung Cancer Dataset](https://arxiv.org/abs/2609.05202v1)

### C18. 科研 · VIALS / ScienceClaw

- 问题：AI that cannot similarly interpret such images will have limited utility in professional life sciences workflows, where such artifacts are central to how scientists reason, communicate, and make decisions.
- 任务：问答、推理/计算、审查/核查；输入：多模态、多轮对话、结构化/代码
- 支撑：Benchmark 2 篇，真实需求信号 0 条
- 现有 Benchmark 用的判分：执行/成功率
- 对应旧 Idea：无（新方向）
- 下一步：人工读 2 篇支撑 Benchmark 原文，确认缺口没被后续工作填上；再抽 20 题做 Mini Eval

作者自述缺口：
> [VIALS] AI that cannot similarly interpret such images will have limited utility in professional life sciences workflows, where such artifacts are central to how scientists reason, communicate, and make decisions.
>
> [ScienceClaw] Large language model agents are accelerating scientific automation, yet verified executions rarely become persistent program-level improvements, and existing evaluations do not examine this process across sequential tasks in both the natural and social sciences.
>

支撑 Benchmark：[VIALS](https://arxiv.org/abs/2608.21357v2)、[ScienceClaw](https://arxiv.org/abs/2610.08691v1)
邻近已覆盖（需对比差异）：[ScienceArena](https://arxiv.org/abs/2608.30517v1)、[MatToolBench](https://arxiv.org/abs/2609.37053v1)、[A Benchmark for LLM's Understanding of Middle School and High School Science Topics](https://arxiv.org/abs/2609.32020v1)、[CompMat-Bench](https://arxiv.org/abs/2610.00636v1)、[AutoSciBench](https://arxiv.org/abs/2610.05140v1)、[TCSAlgBench](https://arxiv.org/abs/2609.35606v1)

### C19. 科研 · FormalTCS / TCSAlgBench

- 问题：Large language models (LLMs) have shown growing potential for automated theoretical computer science (TCS) research, yet existing benchmarks remain far from realistic research settings.
- 任务：审查/核查、生成/撰写、推理/计算；输入：待定
- 支撑：Benchmark 2 篇，真实需求信号 0 条
- 现有 Benchmark 用的判分：专家/人工、执行/成功率
- 判分建议：答案正确率与证据定位（页/条款/句级）命中率分开计分，禁止只看最终答案
- 对应旧 Idea：无（新方向）
- 下一步：人工读 2 篇支撑 Benchmark 原文，确认缺口没被后续工作填上；再抽 20 题做 Mini Eval

作者自述缺口：
> [FormalTCS] Large language models (LLMs) have shown growing potential for automated theoretical computer science (TCS) research, yet existing benchmarks remain far from realistic research settings.
>
> [FormalTCS] Of $64$ generated claims, only $6$ ultimately pass expert evaluation and proof verification, indicating that beyond formalization, limited research taste remains another major barrier to autonomous TCS research.
>
> [TCSAlgBench] For each task, prover systems receive theorem statements and access to cited prior work.
>

支撑 Benchmark：[FormalTCS](https://arxiv.org/abs/2608.20153v3)、[TCSAlgBench](https://arxiv.org/abs/2609.35606v1)
邻近已覆盖（需对比差异）：[OpenProblemBench](https://arxiv.org/abs/2610.11118v1)、[ScienceClaw](https://arxiv.org/abs/2610.08691v1)、[SCAFFOLD](https://arxiv.org/abs/2609.00018v1)、[AxQM](https://arxiv.org/abs/2609.05157v1)、[ScienceArena](https://arxiv.org/abs/2608.30517v1)

### C20. 科研 · Task- and dataset-specific information in protein language models / PFArena

- 问题：We trained probe models on embeddings from each layer, compared their performance, and showed that the last layers of PLMs rarely produced embeddings that led to the best results on downstream tasks.
- 任务：分类/识别、检索、生成/撰写；输入：结构化/代码
- 支撑：Benchmark 2 篇，真实需求信号 0 条
- 现有 Benchmark 用的判分：准确率/EM
- 对应旧 Idea：无（新方向）
- 下一步：人工读 2 篇支撑 Benchmark 原文，确认缺口没被后续工作填上；再抽 20 题做 Mini Eval

作者自述缺口：
> [Task- and dataset-specific information in protein language models] We trained probe models on embeddings from each layer, compared their performance, and showed that the last layers of PLMs rarely produced embeddings that led to the best results on downstream tasks.
>
> [PFArena] Although computational paradigms including protein language models (PLMs), large language models (LLMs), and LLM-based agents have shown promise in protein modification, their relative efficacy across realistic experimental decision-making settings remains unclear.
>

支撑 Benchmark：[Task- and dataset-specific information in protein language models](https://arxiv.org/abs/2608.12090v4)、[PFArena](https://arxiv.org/abs/2609.28921v1)
邻近已覆盖（需对比差异）：[Are You Learning Biological Signal or Shortcuts? Auditing and Mitigating Bias in Protein-Protein Interaction Datasets](https://arxiv.org/abs/2609.10193v1)、[Agentic AI uncovers conserved cross-tissue protein co-abundance programs inaccessible to single-dataset analysis](https://arxiv.org/abs/2608.28990v1)、[World Embedding Benchmark](https://arxiv.org/abs/2610.03632v1)

### C21. Agent · StartupBench / MCPGen

- 问题：Yet existing benchmarks largely rely on researcher-selected tasks, leaving uncertain whether such progress extends to the work that real-world users actually demand from AI systems.
- 任务：分类/识别、Agent任务、审查/核查；输入：工具/环境、结构化/代码
- 支撑：Benchmark 2 篇，真实需求信号 0 条
- 现有 Benchmark 用的判分：Rubric、执行/成功率
- 判分建议：端到端完成率 + 步骤级错误定位（检索/证据使用/规则遵循分开记）
- 对应旧 Idea：无（新方向）
- 下一步：人工读 2 篇支撑 Benchmark 原文，确认缺口没被后续工作填上；再抽 20 题做 Mini Eval

作者自述缺口：
> [StartupBench] Yet existing benchmarks largely rely on researcher-selected tasks, leaving uncertain whether such progress extends to the work that real-world users actually demand from AI systems.
>
> [MCPGen] Existing benchmarks largely evaluate these capabilities in isolation or rely on trajectory-level proxies, leaving open whether generated workflow artifacts execute end-to-end.
>

支撑 Benchmark：[StartupBench](https://arxiv.org/abs/2608.17800v1)、[MCPGen](https://arxiv.org/abs/2609.23925v1)

### C22. Agent · BLINDSPOT / HarnessRisk

- 问题：In such settings, safety failures may emerge only after multiple turns, yet existing evaluations often reduce agent behavior to task or attack success, obscuring whether an agent acts, refuses, or remains appropriately calibrated as the interaction evolves.
- 任务：Agent任务、分类/识别；输入：工具/环境
- 支撑：Benchmark 2 篇，真实需求信号 0 条
- 现有 Benchmark 用的判分：执行/成功率
- 判分建议：以漏报率为主指标（高风险项召回），误报率为辅；专家 rubric 标注风险等级
- 判分建议：对照完整评测与压缩/替代评测的模型排名一致性（Kendall τ），指标拆解到错误类型
- 对应旧 Idea：无（新方向）
- 下一步：人工读 2 篇支撑 Benchmark 原文，确认缺口没被后续工作填上；再抽 20 题做 Mini Eval

作者自述缺口：
> [BLINDSPOT] In such settings, safety failures may emerge only after multiple turns, yet existing evaluations often reduce agent behavior to task or attack success, obscuring whether an agent acts, refuses, or remains appropriately calibrated as the interaction evolves.
>
> [HarnessRisk] Existing safety benchmarks mainly target individual attack mechanisms or a limited subset of operational settings, making it difficult to compare how safety failures emerge across different harness responsibilities.
>

支撑 Benchmark：[BLINDSPOT](https://arxiv.org/abs/2609.16305v1)、[HarnessRisk](https://arxiv.org/abs/2608.17597v1)
邻近已覆盖（需对比差异）：[RT-Safe](https://arxiv.org/abs/2610.09294v1)、[How Long Until Your Robot Ignores You? A Safety Benchmark for LLM Orchestrators in Human-Humanoid Collaboration](https://arxiv.org/abs/2609.07288v1)、[EvoRiskBench](https://arxiv.org/abs/2610.03153v1)、[Beyond Executable Models: The Pufibara Agent Harness and the Modelica Agent Workflow Benchmark for Physical System Modeling](https://arxiv.org/abs/2608.23653v1)、[RideWay](https://arxiv.org/abs/2609.17985v1)、[Testing-Driven Reliability Audit of Trajectory-Based Early Outcome Prediction for LLM Agents: Target-Specific Calibration Transfer Persists Within a Single Benchmark](https://arxiv.org/abs/2609.25647v1)

### C23. Agent · Failure-Transparent Agents: Benchmarking Post-Failure Reporting in Tool-Using Language Models / ParaRecover

- 问题：Existing benchmarks often entangle this reporting failure with tool selection, recovery, and environment dynamics.
- 任务：Agent任务、审查/核查、生成/撰写；输入：工具/环境、长文档、多轮对话
- 支撑：Benchmark 2 篇，真实需求信号 0 条
- 现有 Benchmark 用的判分：执行/成功率、Rubric
- 判分建议：端到端完成率 + 步骤级错误定位（检索/证据使用/规则遵循分开记）
- 对应旧 Idea：无（新方向）
- 下一步：人工读 2 篇支撑 Benchmark 原文，确认缺口没被后续工作填上；再抽 20 题做 Mini Eval

作者自述缺口：
> [Failure-Transparent Agents: Benchmarking Post-Failure Reporting in Tool-Using Language Models] Existing benchmarks often entangle this reporting failure with tool selection, recovery, and environment dynamics.
>
> [ParaRecover] Existing agent benchmarks mainly evaluate final task success or tool-call correctness, providing limited insight into whether agents can reliably diagnose and recover from intermediate execution failures.
>

支撑 Benchmark：[Failure-Transparent Agents: Benchmarking Post-Failure Reporting in Tool-Using Language Models](https://arxiv.org/abs/2609.35732v1)、[ParaRecover](https://arxiv.org/abs/2609.12345v1)
邻近已覆盖（需对比差异）：[Agent Error Dataset: Scaling 50,000 Error--Diagnosis Pairs for Failure Analysis and Error-Aware Post-Training](https://arxiv.org/abs/2609.40111v2)、[GeoNatureAgent (GNA)](https://arxiv.org/abs/2610.09112v1)、[Do Agent Benchmarks Do What They Say? An Executable-Contract Audit of Tool-Using Agent Environments](https://arxiv.org/abs/2609.37315v1)、[RideWay](https://arxiv.org/abs/2609.17985v1)、[BLINDSPOT](https://arxiv.org/abs/2609.16305v1)

### C24. Agent · GMA / MobilePA-Bench

- 问题：Overall, GMA complements existing benchmarks by expanding application coverage and task complexity, providing a challenging testbed for evaluating mobile agents and studying how harness design supports reliable execution in complex mobile workflows.
- 任务：Agent任务、审查/核查、推理/计算；输入：工具/环境、结构化/代码、多模态
- 支撑：Benchmark 2 篇，真实需求信号 0 条
- 现有 Benchmark 用的判分：F1/P/R、执行/成功率
- 判分建议：端到端完成率 + 步骤级错误定位（检索/证据使用/规则遵循分开记）
- 对应旧 Idea：#29 Computer-Use Agent多步工作流完成度
- 下一步：人工读 2 篇支撑 Benchmark 原文，确认缺口没被后续工作填上；再抽 20 题做 Mini Eval

作者自述缺口：
> [GMA] Overall, GMA complements existing benchmarks by expanding application coverage and task complexity, providing a challenging testbed for evaluating mobile agents and studying how harness design supports reliable execution in complex mobile workflows.
>
> [MobilePA-Bench] Yet existing benchmarks fall into two camps, each with a critical blind spot: GUI-centric benchmarks test surface-level screen manipulation while overlooking background tool use and long-horizon planning, whereas static function-calling benchmarks rely on offline API matching that is detached from real runtime constraints.
>
> [MobilePA-Bench] To close this gap, we present \textbf{MobilePA-Bench}, an interactive, stateful, and tool-centric benchmark for evaluating the tool-calling and planning abilities of mobile planning agents.
>
> [GMA] Existing benchmarks such as AndroidWorld and MobileWorld provide strong foundations for mobile agent evaluation, but their application coverage and task design do not yet fully capture the diversity and complexity of realistic mobile use.
>

支撑 Benchmark：[GMA](https://arxiv.org/abs/2608.27477v1)、[MobilePA-Bench](https://arxiv.org/abs/2608.23035v2)
邻近已覆盖（需对比差异）：[MobileJudgeBench](https://arxiv.org/abs/2608.11434v1)、[MobileWorldSafety](https://arxiv.org/abs/2608.17659v1)、[AppEval](https://arxiv.org/abs/2608.18588v1)、[PDEU-Bench](https://arxiv.org/abs/2609.34930v1)、[DIBench](https://arxiv.org/abs/2610.06898v1)、[ElderBench](https://arxiv.org/abs/2609.04850v1)

### C25. Agent · GraphMAS / Wikidata Search Traces: A Dataset for Training Knowledge Graph Search Agents

- 问题：Consequently, it remains unclear whether multiple specialized agents can improve graph learning and how coordination strategies should be designed and evaluated.
- 任务：Agent任务、推理/计算、检索；输入：结构化/代码、多文档/知识库、工具/环境
- 支撑：Benchmark 2 篇，真实需求信号 0 条
- 现有 Benchmark 用的判分：准确率/EM
- 判分建议：以漏报率为主指标（高风险项召回），误报率为辅；专家 rubric 标注风险等级
- 对应旧 Idea：无（新方向）
- 下一步：人工读 2 篇支撑 Benchmark 原文，确认缺口没被后续工作填上；再抽 20 题做 Mini Eval

作者自述缺口：
> [GraphMAS] Consequently, it remains unclear whether multiple specialized agents can improve graph learning and how coordination strategies should be designed and evaluated.
>
> [Wikidata Search Traces: A Dataset for Training Knowledge Graph Search Agents] We study agents that instead answer by exploring the graph, and argue that two obstacles limit them: the lack of training data recording how a solver explores, and interfaces that add large graph results directly to the model's context.
>
> [GraphMAS] LLM-based multi-agent systems coordinate specialized reasoning through aggregation, interaction, and adaptive control, yet their potential for graph learning remains unexplored.
>

支撑 Benchmark：[GraphMAS](https://arxiv.org/abs/2609.39777v1)、[Wikidata Search Traces: A Dataset for Training Knowledge Graph Search Agents](https://arxiv.org/abs/2610.06650v2)
邻近已覆盖（需对比差异）：[MASBench](https://arxiv.org/abs/2610.04672v1)、[AgentWorld](https://arxiv.org/abs/2609.31590v1)、[DynGraphAgentBench](https://arxiv.org/abs/2609.33980v1)、[OpenMAS-GCom](https://arxiv.org/abs/2609.21527v1)

### C26. Agent · EvoRiskBench / CoSec

- 问题：Existing benchmarks leave gaps in executable coverage of their runtime security risks, while evolving model capabilities, harnesses, tools, and threats motivate benchmark evolution.
- 任务：审查/核查、Agent任务、分类/识别；输入：工具/环境、结构化/代码、多轮对话
- 支撑：Benchmark 2 篇，真实需求信号 0 条
- 现有 Benchmark 用的判分：执行/成功率
- 判分建议：按时间切片出题，同题不同截止日期对照；过时答案单独计为错误类型
- 对应旧 Idea：无（新方向）
- 下一步：人工读 2 篇支撑 Benchmark 原文，确认缺口没被后续工作填上；再抽 20 题做 Mini Eval

作者自述缺口：
> [EvoRiskBench] Existing benchmarks leave gaps in executable coverage of their runtime security risks, while evolving model capabilities, harnesses, tools, and threats motivate benchmark evolution.
>
> [EvoRiskBench] The most vulnerable configuration, Codex with DeepSeek-V4-Pro-0813, reaches a 68.44% attack success rate (ASR), indicating that configuration of workspace agent is insufficient to ensure secure autonomous execution.
>
> [CoSec] Existing evaluations do not fully examine these risks in agent systems.
>

支撑 Benchmark：[EvoRiskBench](https://arxiv.org/abs/2610.03153v1)、[CoSec](https://arxiv.org/abs/2609.34790v2)
邻近已覆盖（需对比差异）：[DUMA-Bench](https://arxiv.org/abs/2609.24662v1)、[HarnessRisk](https://arxiv.org/abs/2608.17597v1)、[MobileJudgeBench](https://arxiv.org/abs/2608.11434v1)、[Vulnerability Localization Benchmark: Measuring Agentic Security Analysis at Repository Scale](https://arxiv.org/abs/2609.15939v1)、[CyberClear](https://arxiv.org/abs/2609.32424v1)、[Agent Evaluation Reliability: More Tasks Won't (Always) Fix An Agent Leaderboard](https://arxiv.org/abs/2610.00651v1)

### C27. 医疗 · TCMQA / CMB

- 问题：The few TCM evaluations that exist are small, narrow, and rarely paired with a human reference.
- 任务：推理/计算；输入：多文档/知识库、工具/环境、结构化/代码
- 支撑：Benchmark 2 篇，真实需求信号 0 条
- 现有 Benchmark 用的判分：准确率/EM
- 判分建议：域内 vs 域外（跨地区/跨案件/跨机构）分组计分，报告差值
- 对应旧 Idea：无（新方向）
- 下一步：人工读 2 篇支撑 Benchmark 原文，确认缺口没被后续工作填上；再抽 20 题做 Mini Eval

作者自述缺口：
> [TCMQA] The few TCM evaluations that exist are small, narrow, and rarely paired with a human reference.
>
> [CMB] However, medical environments in different regions have their local characteristics, e.g., the ubiquity and significance of traditional Chinese medicine within China.
>

支撑 Benchmark：[TCMQA](https://arxiv.org/abs/2609.33014v1)、[CMB](https://aclanthology.org/2024.naacl-long.343)
邻近已覆盖（需对比差异）：[MEDEC](https://arxiv.org/abs/2412.19260)、[MedCalc-Bench](https://arxiv.org/abs/2406.12036)、[From Scores to Steps: Diagnosing and Improving LLM Performance in Evidence-Based Medical Calculations](https://arxiv.org/abs/2509.16584)、[MVC-Bench](https://arxiv.org/abs/2608.27004v2)、[Beyond Natural-Image Foundation Models: Benchmarking Satellite Pretraining for Ophthalmic Image Analysis](https://arxiv.org/abs/2608.15195v1)

### C28. 医疗 · MC-CXR / X-Ray

- 问题：Image-only accuracy is necessary but insufficient.
- 任务：检索、分类/识别、审查/核查；输入：多模态、结构化/代码
- 支撑：Benchmark 2 篇，真实需求信号 0 条
- 现有 Benchmark 用的判分：准确率/EM
- 判分建议：对照完整评测与压缩/替代评测的模型排名一致性（Kendall τ），指标拆解到错误类型
- 对应旧 Idea：无（新方向）
- 下一步：人工读 2 篇支撑 Benchmark 原文，确认缺口没被后续工作填上；再抽 20 题做 Mini Eval

作者自述缺口：
> [MC-CXR] Image-only accuracy is necessary but insufficient.
>
> [X-Ray] Conservative exclusion of perceptual-overlap candidates narrows this gap without closing it.
>
> [MC-CXR] Existing benchmarks measure whether models answer correctly in isolation, but not whether they preserve a correct image-only decision when plausible context conflicts with the image.
>
> [MC-CXR] Among switched predictions, 74.6% align with the misleading label for text versus 17.6% for visual context, a 57.0-point gap (95% CI 50.9-62.8).
>

支撑 Benchmark：[MC-CXR](https://arxiv.org/abs/2608.24118v1)、[X-Ray](https://arxiv.org/abs/2609.21763v1)
邻近已覆盖（需对比差异）：[Why ML-based cough models do not generalize: a systematic cross-dataset evaluation for tuberculosis screening](https://arxiv.org/abs/2608.25846v1)、[Few-Shot Cross-Dataset Adaptation for Tuberculosis Detection Using DenseNet](https://arxiv.org/abs/2608.21427v1)、[Pre-training, Reasoning, Benchmarking](https://arxiv.org/abs/2610.08813v1)、[MVC-Bench](https://arxiv.org/abs/2608.27004v2)

### C29. 医疗 · Learning-State-Aware Dynamic Generative Data Augmentation on Small-Scale Datasets / To do($x$) or not to do($x$): Medical Image Counterfactuals for Dataset Augmentation

- 问题：Although recent dynamic GDA methods incorporate model feedback to guide augmentation, they still struggle to reliably determine sample-specific augmentation strengths and adapt augmentation strategies to different image regions while balancing image diversity and class semantics.
- 任务：生成/撰写、分类/识别；输入：多模态、结构化/代码
- 支撑：Benchmark 2 篇，真实需求信号 0 条
- 判分建议：域内 vs 域外（跨地区/跨案件/跨机构）分组计分，报告差值
- 判分建议：答案正确率与证据定位（页/条款/句级）命中率分开计分，禁止只看最终答案
- 对应旧 Idea：无（新方向）
- 下一步：人工读 2 篇支撑 Benchmark 原文，确认缺口没被后续工作填上；再抽 20 题做 Mini Eval

作者自述缺口：
> [Learning-State-Aware Dynamic Generative Data Augmentation on Small-Scale Datasets] Although recent dynamic GDA methods incorporate model feedback to guide augmentation, they still struggle to reliably determine sample-specific augmentation strengths and adapt augmentation strategies to different image regions while balancing image diversity and class semantics.
>
> [To do($x$) or not to do($x$): Medical Image Counterfactuals for Dataset Augmentation] Medical image analysis is often hindered by biased datasets, which can lead to biased models and limited clinical applicability.
>
> [To do($x$) or not to do($x$): Medical Image Counterfactuals for Dataset Augmentation] We analyse how these choices affect the resulting images, and explore when causally grounded methods improve dataset augmentation or bring limited benefit.
>
> [Learning-State-Aware Dynamic Generative Data Augmentation on Small-Scale Datasets] Small-scale image classification is often limited by the scarcity of training data.
>

支撑 Benchmark：[Learning-State-Aware Dynamic Generative Data Augmentation on Small-Scale Datasets](https://arxiv.org/abs/2608.18907v1)、[To do($x$) or not to do($x$): Medical Image Counterfactuals for Dataset Augmentation](https://arxiv.org/abs/2609.14124v1)
邻近已覆盖（需对比差异）：[PhotoMOCI](https://arxiv.org/abs/2609.35226v1)、[Beyond Simulated Benchmarks: Evaluating Motion Representations for Fall Detection Under Real-World Data Scarcity](https://arxiv.org/abs/2608.13197v1)、[Beyond Natural-Image Foundation Models: Benchmarking Satellite Pretraining for Ophthalmic Image Analysis](https://arxiv.org/abs/2608.15195v1)、[From Scores to Steps: Diagnosing and Improving LLM Performance in Evidence-Based Medical Calculations](https://arxiv.org/abs/2509.16584)、[MEDEC](https://arxiv.org/abs/2412.19260)、[CMB](https://aclanthology.org/2024.naacl-long.343)

### C30. 医疗 · Synthetic Leprosy Image Generation Using Mask-Conditioned Latent Diffusion and Transfer Learning from Large Chronic Wound Datasets / LUTSeg

- 问题：Machine learning for neglected tropical diseases is limited by data, not algorithms: public annotated image sets for leprosy (Hansen's disease) number in the hundreds, orders of magnitude below what generative models require.
- 任务：生成/撰写；输入：多模态、结构化/代码
- 支撑：Benchmark 2 篇，真实需求信号 0 条
- 现有 Benchmark 用的判分：专家/人工
- 对应旧 Idea：无（新方向）
- 下一步：人工读 2 篇支撑 Benchmark 原文，确认缺口没被后续工作填上；再抽 20 题做 Mini Eval

作者自述缺口：
> [Synthetic Leprosy Image Generation Using Mask-Conditioned Latent Diffusion and Transfer Learning from Large Chronic Wound Datasets] Machine learning for neglected tropical diseases is limited by data, not algorithms: public annotated image sets for leprosy (Hansen's disease) number in the hundreds, orders of magnitude below what generative models require.
>
> [LUTSeg] However, pixel-level annotations are costly, and multi-tissue wound datasets remain scarce, particularly for neglected diseases such as leprosy.
>

支撑 Benchmark：[Synthetic Leprosy Image Generation Using Mask-Conditioned Latent Diffusion and Transfer Learning from Large Chronic Wound Datasets](https://arxiv.org/abs/2609.13226v1)、[LUTSeg](https://arxiv.org/abs/2608.25866v1)
邻近已覆盖（需对比差异）：[WILLIE](https://arxiv.org/abs/2610.05341v1)

### C31. 医疗 · GPAgentBench-2K / EHR-RobustGym

- 问题：Large Language Models (LLMs) show great potential as clinical agents, yet existing benchmarks reduce clinical workflows to static predictions or unconstrained Markov Decision Processes (MDPs) with coarse action sets.
- 任务：推理/计算、Agent任务、检索；输入：工具/环境、表格、结构化/代码
- 支撑：Benchmark 2 篇，真实需求信号 0 条
- 现有 Benchmark 用的判分：准确率/EM、执行/成功率
- 判分建议：以漏报率为主指标（高风险项召回），误报率为辅；专家 rubric 标注风险等级
- 对应旧 Idea：#18 临床推理与指南溯源
- 下一步：人工读 2 篇支撑 Benchmark 原文，确认缺口没被后续工作填上；再抽 20 题做 Mini Eval

作者自述缺口：
> [GPAgentBench-2K] Large Language Models (LLMs) show great potential as clinical agents, yet existing benchmarks reduce clinical workflows to static predictions or unconstrained Markov Decision Processes (MDPs) with coarse action sets.
>
> [GPAgentBench-2K] Crucially, we uncover a clinical quality-safety gap: even frontier models with the highest diagnosis accuracy violate safety constraints in over half of high-risk cases.
>
> [EHR-RobustGym] Even when database retrieval succeeds, clinical agents can overlook such discrepancies and return plausible but unsupported answers.
>

支撑 Benchmark：[GPAgentBench-2K](https://arxiv.org/abs/2608.30188v2)、[EHR-RobustGym](https://arxiv.org/abs/2609.39371v1)
邻近已覆盖（需对比差异）：[The Effect of Quantization on Clinical Benchmarks: Accuracy and Safety Across Model Families](https://arxiv.org/abs/2609.22216v1)、[MTDiag](https://arxiv.org/abs/2608.25085v1)、[CLIMB](https://arxiv.org/abs/2609.35462v1)、[MEGA-CDP](https://arxiv.org/abs/2608.26592v1)、[Sense and Sensitivity: Benchmarking LLM Clinical Triage Recommendations with Physician Experts](https://arxiv.org/abs/2609.38600v1)、[SUP-MIMIC](https://arxiv.org/abs/2608.29582v1)

### C32. 医疗 · EyeVQA / Beyond Natural-Image Foundation Models: Benchmarking Satellite Pretraining for Ophthalmic Image Analysis

- 问题：Vision-language models (VLMs) have shown increasing potential for medical image understanding, yet their capabilities in ophthalmic imaging remain insufficiently characterized.
- 任务：问答、生成/撰写、推理/计算；输入：多模态
- 支撑：Benchmark 2 篇，真实需求信号 0 条
- 对应旧 Idea：无（新方向）
- 下一步：人工读 2 篇支撑 Benchmark 原文，确认缺口没被后续工作填上；再抽 20 题做 Mini Eval

作者自述缺口：
> [EyeVQA] Vision-language models (VLMs) have shown increasing potential for medical image understanding, yet their capabilities in ophthalmic imaging remain insufficiently characterized.
>
> [Beyond Natural-Image Foundation Models: Benchmarking Satellite Pretraining for Ophthalmic Image Analysis] However, VFMs require extensive training data, and their progress in medical image analysis is constrained by limited data availability, privacy concerns, and high development costs.
>

支撑 Benchmark：[EyeVQA](https://arxiv.org/abs/2609.32352v2)、[Beyond Natural-Image Foundation Models: Benchmarking Satellite Pretraining for Ophthalmic Image Analysis](https://arxiv.org/abs/2608.15195v1)
邻近已覆盖（需对比差异）：[To do($x$) or not to do($x$): Medical Image Counterfactuals for Dataset Augmentation](https://arxiv.org/abs/2609.14124v1)、[MVC-Bench](https://arxiv.org/abs/2608.27004v2)、[CT-$Δ$Bench](https://arxiv.org/abs/2608.11534v2)、[CRS-Bench](https://arxiv.org/abs/2608.22059v1)

### C33. 医疗 · SADUSI / UltraG-Bench

- 问题：These findings suggest that broad multi-source ultrasound anomaly detection remains an open challenge and that SADUSI can serve as a resource for developing methods that generalize beyond anatomy-specific settings.
- 任务：分类/识别、生成/撰写、推理/计算；输入：多模态、结构化/代码
- 支撑：Benchmark 2 篇，真实需求信号 0 条
- 现有 Benchmark 用的判分：F1/P/R
- 判分建议：答案正确率与证据定位（页/条款/句级）命中率分开计分，禁止只看最终答案
- 判分建议：域内 vs 域外（跨地区/跨案件/跨机构）分组计分，报告差值
- 对应旧 Idea：无（新方向）
- 下一步：人工读 2 篇支撑 Benchmark 原文，确认缺口没被后续工作填上；再抽 20 题做 Mini Eval

作者自述缺口：
> [SADUSI] These findings suggest that broad multi-source ultrasound anomaly detection remains an open challenge and that SADUSI can serve as a resource for developing methods that generalize beyond anatomy-specific settings.
>
> [SADUSI] However, most existing evaluations are limited to a single anatomy or task, making it unclear whether models learn a robust notion of normal ultrasound appearance or only a source-specific representation.
>
> [SADUSI] We evaluate representative self-supervised anomaly detection methods and find that current approaches struggle in this setting.
>
> [SADUSI] Feature-based PatchCore variants perform better, reaching pixel-level AUROC values of 0.76-0.83, but remain limited with maximum F1 scores of 0.14-0.40.
>

支撑 Benchmark：[SADUSI](https://arxiv.org/abs/2610.09677v1)、[UltraG-Bench](https://arxiv.org/abs/2609.30928v1)
邻近已覆盖（需对比差异）：[Unsupervised Anomaly Detection for Image Dataset Quality Assurance in Multi-Center Breast MRI](https://arxiv.org/abs/2608.16725v2)

## 观察

| # | 名称 | 来源 | B | 需求 | 对应旧 Idea |
|---|---|---|---|---|---|
| W1 | Agent · AgentPerfBench | 缺口句 | 1 | 3 | - |
| W2 | Agent · SWE-Serve | 缺口句 | 1 | 2 | - |
| W3 | Agent · MemCalib | 缺口句 | 1 | 2 | - |
| W4 | 科研 · SciFigure2Code | 缺口句 | 1 | 1 | - |
| W5 | 科研 · Benchmarking Language Models for Statistical Problem Formulation | 缺口句 | 1 | 1 | - |
| W6 | Agent · TicTacBench | 缺口句 | 1 | 1 | - |
| W7 | Agent · CADWorld | 缺口句 | 1 | 1 | #29 |
| W8 | Agent · Defining AI Agents: A Compendium of Criteria, Metrics, and Benchmarks | 缺口句 | 1 | 1 | - |
| W9 | Agent · VEX-Bench | 缺口句 | 1 | 1 | - |
| W10 | Agent · VICBench | 缺口句 | 1 | 1 | - |
| W11 | Agent · Benchmark-Based Comparative Assessment of Publicly Benchmarked Indian Foundation Models: A Capability and Evaluation-Maturity Framework | 缺口句 | 1 | 1 | - |
| W12 | Agent · BiGym 2.0 | 缺口句 | 1 | 1 | - |
| W13 | Agent · Video2World | 缺口句 | 1 | 1 | - |
| W14 | Agent · Code4Scene | 缺口句 | 1 | 1 | - |
| W15 | 医疗 · From Density to Biopsy Decisions and Malignancy Prediction: A Benchmark Study of Multimodal Large Language Models Against Radiologists in Digital and Contrast-Enhanced Mammography | 缺口句 | 1 | 1 | - |
| W16 | 医疗 · Unsupervised Anomaly Detection for Image Dataset Quality Assurance in Multi-Center Breast MRI | 缺口句 | 1 | 1 | - |
| W17 | 医疗 · MEDEC | 缺口句 | 1 | 1 | #18 |
| W18 | 科研 · REVERSAL-BENCH | 缺口句 | 1 | 0 | - |
| W19 | 科研 · SatUnreal | 缺口句 | 1 | 0 | - |
| W20 | 科研 · An open benchmark for machine learning-based polymer property prediction | 缺口句 | 1 | 0 | - |
| W21 | 科研 · Queer inclusion in speech datasets: An audit and taxonomy of practical tensions | 缺口句 | 1 | 0 | - |
| W22 | 科研 · RSPDBench | 缺口句 | 1 | 0 | - |
| W23 | 科研 · ChemCLIR-Bench | 缺口句 | 1 | 0 | - |
| W24 | 科研 · PolyBridgeBench | 缺口句 | 1 | 0 | - |
| W25 | 科研 · ReFigBench | 缺口句 | 1 | 0 | - |
| W26 | 科研 · Map2Route | 缺口句 | 1 | 0 | - |
| W27 | 科研 · Geospatial Metadata Improves Discoverability by Connecting Datasets Across Scientific Disciplines | 缺口句 | 1 | 0 | - |
| W28 | 科研 · VPRef | 缺口句 | 1 | 0 | - |
| W29 | 科研 · SyntheticDoc | 缺口句 | 1 | 0 | - |
| W30 | 科研 · Benchmarking Optimizers to Solve Inverse Problems with Differentiable Physics Simulators | 缺口句 | 1 | 0 | - |
| W31 | 科研 · ZipBench | 缺口句 | 1 | 0 | #26 |
| W32 | 科研 · Extracting Dataset Mentions in Forced Displacement and FCV Documents: A Weakly Supervised Framework with LLM-Based Label Refinement | 缺口句 | 1 | 0 | - |
| W33 | 科研 · Few-Shot Learning for Network Intrusion Detection: Methods, Datasets, and Performance | 缺口句 | 1 | 0 | - |
| W34 | 科研 · NovGauge | 缺口句 | 1 | 0 | - |
| W35 | 科研 · ReactHuman | 缺口句 | 1 | 0 | - |
| W36 | 科研 · IdeaAMBIG | 缺口句 | 1 | 0 | - |
| W37 | 科研 · Development and Validation of a Physics-Guided Machine Learning Extrapolation Framework Using a Classical Transient Diffusion Benchmark | 缺口句 | 1 | 0 | - |
| W38 | 科研 · ONE CYLinder | 缺口句 | 1 | 0 | - |
| W39 | 科研 · FINALLY | 缺口句 | 1 | 0 | - |
| W40 | 科研 · AgentIdeaBench | 缺口句 | 1 | 0 | - |
| W41 | 科研 · NEO-BENCH | 缺口句 | 1 | 0 | - |
| W42 | 科研 · Beyond Final Decisions: A Process-Centric Benchmark for Transparent AI-Assisted Peer Review | 缺口句 | 1 | 0 | - |
| W43 | 科研 · AxQM | 缺口句 | 1 | 0 | - |
| W44 | 科研 · TruthInsightBench | 缺口句 | 1 | 0 | - |
| W45 | 科研 · Last Translation Benchmark | 缺口句 | 1 | 0 | - |
| W46 | 科研 · Understanding Autonomous Driving Datasets by Describing Differences between Image Subsets in Natural Language | 缺口句 | 1 | 0 | - |
| W47 | 科研 · Hyperspectral-XRF | 缺口句 | 1 | 0 | - |
| W48 | 科研 · Benchmarking Peptide-Protein Affinity Prediction Across Peptide and Target Shifts | 缺口句 | 1 | 0 | - |
| W49 | 科研 · Where Induction Runs Out: Description-Length Difficulty and the Memorisation Gap in Integer-Sequence Benchmarks | 缺口句 | 1 | 0 | - |
| W50 | 科研 · Padārtha | 缺口句 | 1 | 0 | - |
| W51 | 科研 · Agentic AI uncovers conserved cross-tissue protein co-abundance programs inaccessible to single-dataset analysis | 缺口句 | 1 | 0 | - |
| W52 | 科研 · LongPIBench | 缺口句 | 1 | 0 | - |
| W53 | 科研 · RATIO | 缺口句 | 1 | 0 | - |
| W54 | 科研 · How Robust Are Automated Fact-Checking Systems? A Cross-Benchmark Evaluation | 缺口句 | 1 | 0 | - |
| W55 | 科研 · PhysicsBench | 缺口句 | 1 | 0 | - |
| W56 | 科研 · EarthVerse | 缺口句 | 1 | 0 | - |
| W57 | 科研 · WebDev-Skills-Bench | 缺口句 | 1 | 0 | - |
| W58 | 科研 · WildFin | 缺口句 | 1 | 0 | - |
| W59 | 科研 · ExPhy | 缺口句 | 1 | 0 | - |
| W60 | 科研 · Natural Language Code Retrieval for 1C:Enterprise: An Open Benchmark and Efficient Bi-Encoder | 缺口句 | 1 | 0 | - |
| W61 | 科研 · LabDex | 缺口句 | 1 | 0 | - |
| W62 | 科研 · BEAR-Bench | 缺口句 | 1 | 0 | - |
| W63 | 科研 · MANIGUARD | 缺口句 | 1 | 0 | - |
| W64 | 科研 · LiveHouse-TS | 缺口句 | 1 | 0 | - |
| W65 | 科研 · MAPLE | 缺口句 | 1 | 0 | - |
| W66 | 科研 · PACE-Bench | 缺口句 | 1 | 0 | - |
| W67 | 科研 · LongEarth-R1 | 缺口句 | 1 | 0 | - |
| W68 | 科研 · HumanoidVLN | 缺口句 | 1 | 0 | - |
| W69 | 科研 · Diagram-MMU | 缺口句 | 1 | 0 | - |
| W70 | 科研 · JieZi | 缺口句 | 1 | 0 | - |
| W71 | 科研 · TRACES | 缺口句 | 1 | 0 | - |
| W72 | 科研 · DrugTargetWorld | 缺口句 | 1 | 0 | - |
| W73 | 科研 · Do Vision Models Learn Physical Constraints or Rendering Shortcuts? A Counterfactual Benchmark for Grounded Physical Consistency | 缺口句 | 1 | 0 | - |
| W74 | 科研 · Towards Explainable Benchmarking for Data-driven Post-Wildfire Debris Flow Prediction | 缺口句 | 1 | 0 | - |
| W75 | 科研 · ANT | 缺口句 | 1 | 0 | - |
| W76 | 科研 · From Benchmark to Bench: Can Agents Survive Real-World Drug Discovery? | 缺口句 | 1 | 0 | - |
| W77 | 科研 · AutoSciBench | 缺口句 | 1 | 0 | - |
| W78 | 科研 · RNADyn | 缺口句 | 1 | 0 | - |
| W79 | 科研 · TasteBench | 缺口句 | 1 | 0 | - |
| W80 | 科研 · VTR-Bench | 缺口句 | 1 | 0 | - |
| W81 | 科研 · Ontology-Grounded, Reasoner-Verified Benchmarks for Evaluating LLM Reasoning in Scientific AI | 缺口句 | 1 | 0 | - |
| W82 | 科研 · SciSlopBench | 缺口句 | 1 | 0 | - |
| W83 | 科研 · ChartDensity-Bench | 缺口句 | 1 | 0 | - |
| W84 | 科研 · OmniVCBench | 缺口句 | 1 | 0 | - |
| W85 | 科研 · MatToolBench | 缺口句 | 1 | 0 | - |
| W86 | 科研 · PyroStack | 缺口句 | 1 | 0 | - |
| W87 | 科研 · SymbolicArena | 缺口句 | 1 | 0 | - |
| W88 | 科研 · Pass or Fail? Evaluating LLMs on Two Greek Examination Benchmarks | 缺口句 | 1 | 0 | - |
| W89 | 科研 · TQTS-Bench | 缺口句 | 1 | 0 | - |
| W90 | 科研 · AgentHop | 缺口句 | 1 | 0 | - |
| W91 | 科研 · SleuthBench | 缺口句 | 1 | 0 | - |
| W92 | 科研 · PhysAlign | 缺口句 | 1 | 0 | - |
| W93 | 科研 · INSPIRE | 缺口句 | 1 | 0 | - |
| W94 | 科研 · PolyTopoBench | 缺口句 | 1 | 0 | - |
| W95 | 科研 · USAI-Quant | 缺口句 | 1 | 0 | - |
| W96 | 科研 · MixBench-TS | 缺口句 | 1 | 0 | - |
| W97 | 科研 · Bison: Cross-Dataset Learning for Unseen-Compound Perturbation Prediction | 缺口句 | 1 | 0 | - |
| W98 | 科研 · AutoPDEBench | 缺口句 | 1 | 0 | - |
| W99 | 科研 · A Benchmark for LLM's Understanding of Middle School and High School Science Topics | 缺口句 | 1 | 0 | - |
| W100 | 科研 · TopU-LBVS | 缺口句 | 1 | 0 | - |
| W101 | 科研 · A Unified Framework and Dataset for Oriented Object Visual Grounding in Remote Sensing | 缺口句 | 1 | 0 | - |
| W102 | 科研 · A Benchmark Framework for Screening Automation in Systematic Reviews | 缺口句 | 1 | 0 | #30 |
| W103 | 科研 · DualViewEval | 缺口句 | 1 | 0 | - |
| W104 | 科研 · VenusRX-Bench | 缺口句 | 1 | 0 | - |
| W105 | Agent · GAUGE | 缺口句 | 1 | 0 | #24 |
| W106 | Agent · ACTS | 缺口句 | 1 | 0 | - |
| W107 | Agent · MSK-Bench | 缺口句 | 1 | 0 | - |
| W108 | Agent · Testing-Driven Reliability Audit of Trajectory-Based Early Outcome Prediction for LLM Agents: Target-Specific Calibration Transfer Persists Within a Single Benchmark | 缺口句 | 1 | 0 | - |
| W109 | Agent · Trains but Doesn't Learn | 缺口句 | 1 | 0 | - |
| W110 | Agent · PhysAI-Bench | 缺口句 | 1 | 0 | - |
| W111 | Agent · BabelArena | 缺口句 | 1 | 0 | #29 |
| W112 | Agent · OpenMAS-GCom | 缺口句 | 1 | 0 | - |
| W113 | Agent · ODU-Bench | 缺口句 | 1 | 0 | - |
| W114 | Agent · AgentVidBench | 缺口句 | 1 | 0 | - |
| W115 | Agent · ToMAS | 缺口句 | 1 | 0 | - |
| W116 | Agent · RiskChainBench | 缺口句 | 1 | 0 | #27 |
| W117 | Agent · GameReplica | 缺口句 | 1 | 0 | - |
| W118 | Agent · NoteVQA | 缺口句 | 1 | 0 | - |
| W119 | Agent · Mr.LHDR | 缺口句 | 1 | 0 | #27 |
| W120 | Agent · SemVerBench | 缺口句 | 1 | 0 | - |
| W121 | Agent · HLSFactory-Agent | 缺口句 | 1 | 0 | - |
| W122 | Agent · HybridDeepResearch | 缺口句 | 1 | 0 | #27 |
| W123 | Agent · Q2D-Web | 缺口句 | 1 | 0 | - |
| W124 | Agent · CutCraft | 缺口句 | 1 | 0 | - |
| W125 | Agent · SWE-Bench Pro Verified | 缺口句 | 1 | 0 | - |
| W126 | Agent · xDailyBench | 缺口句 | 1 | 0 | - |
| W127 | Agent · How Long Until Your Robot Ignores You? A Safety Benchmark for LLM Orchestrators in Human-Humanoid Collaboration | 缺口句 | 1 | 0 | - |
| W128 | Agent · The Double Measurement Confound in Agent Benchmarks: De-Scaffolding, Ground-Truth Scoring, and Reliability Beyond the Mean | 缺口句 | 1 | 0 | - |
| W129 | Agent · Multi-Step Tool-Calling over Korean Open Public APIs: A Benchmark and a Data-Synthesis Recipe | 缺口句 | 1 | 0 | - |
| W130 | Agent · ElderBench | 缺口句 | 1 | 0 | - |
| W131 | Agent · CivBench | 缺口句 | 1 | 0 | - |
| W132 | Agent · InSight | 缺口句 | 1 | 0 | - |
| W133 | Agent · WorldBench | 缺口句 | 1 | 0 | #24 |
| W134 | Agent · DramaChain Bench | 缺口句 | 1 | 0 | - |
| W135 | Agent · PII-TRACE | 缺口句 | 1 | 0 | - |
| W136 | Agent · Framework and Benchmark for Code-Driven Agentic Testing in Web Development | 缺口句 | 1 | 0 | - |
| W137 | Agent · AlgoWorlds | 缺口句 | 1 | 0 | - |
| W138 | Agent · AgentLogs | 缺口句 | 1 | 0 | - |
| W139 | Agent · CoVA-SFT | 缺口句 | 1 | 0 | - |
| W140 | Agent · An Empirical Evaluation of Cross-City POI Recommendation on a Large-Scale Benchmark | 缺口句 | 1 | 0 | - |
| W141 | Agent · PCFBench | 缺口句 | 1 | 0 | - |
| W142 | Agent · FaulT-Bench | 缺口句 | 1 | 0 | - |
| W143 | Agent · MemToC | 缺口句 | 1 | 0 | - |
| W144 | Agent · EASEL | 缺口句 | 1 | 0 | - |
| W145 | Agent · PeakBench | 缺口句 | 1 | 0 | - |
| W146 | Agent · TrustDABench | 缺口句 | 1 | 0 | - |
| W147 | Agent · NetConfArena | 缺口句 | 1 | 0 | - |
| W148 | Agent · OmniCAD | 缺口句 | 1 | 0 | - |
| W149 | Agent · LLM4LLM | 缺口句 | 1 | 0 | - |
| W150 | Agent · AI4AI-Bench | 缺口句 | 1 | 0 | - |
| W151 | Agent · AppEval | 缺口句 | 1 | 0 | - |
| W152 | Agent · Benchmarking Automated Security Patch Backporting: How Far Are We? | 缺口句 | 1 | 0 | - |
| W153 | Agent · LAPF | 缺口句 | 1 | 0 | - |
| W154 | Agent · Act2Intention | 缺口句 | 1 | 0 | - |
| W155 | Agent · PlayWorld | 缺口句 | 1 | 0 | - |
| W156 | Agent · SRE-Bench | 缺口句 | 1 | 0 | - |
| W157 | Agent · TestGRAD | 缺口句 | 1 | 0 | - |
| W158 | Agent · AgentDojo | 缺口句 | 1 | 0 | - |
| W159 | Agent · DUDA-Bench | 缺口句 | 1 | 0 | - |
| W160 | Agent · Wiki-Talkie: Multilingual Benchmarking of Persona-Based Agents on Real-World Discussions | 缺口句 | 1 | 0 | - |
| W161 | Agent · DecepEval | 缺口句 | 1 | 0 | - |
| W162 | Agent · CroissantMiner | 缺口句 | 1 | 0 | - |
| W163 | Agent · PlaySuite | 缺口句 | 1 | 0 | #29 |
| W164 | Agent · Towards a Unified Misuse Monitoring Benchmark | 缺口句 | 1 | 0 | - |
| W165 | Agent · SWE-CC | 缺口句 | 1 | 0 | - |
| W166 | Agent · CuratorMAS | 缺口句 | 1 | 0 | - |
| W167 | Agent · Measurement-First Auditing of Agentic Leaderboards: Contamination Susceptibility, Matched-Control Re-evaluation, and Scorer Validation | 缺口句 | 1 | 0 | - |
| W168 | Agent · MMPostTrainBench | 缺口句 | 1 | 0 | - |
| W169 | Agent · MASBench | 缺口句 | 1 | 0 | - |
| W170 | Agent · COPEX | 缺口句 | 1 | 0 | - |
| W171 | Agent · SkillScriptBench | 缺口句 | 1 | 0 | - |
| W172 | Agent · ReFract | 缺口句 | 1 | 0 | - |
| W173 | Agent · AdsCVR | 缺口句 | 1 | 0 | - |
| W174 | Agent · WebUIProof | 缺口句 | 1 | 0 | - |
| W175 | Agent · CUEing User Simulators | 缺口句 | 1 | 0 | - |
| W176 | Agent · KaliBench | 缺口句 | 1 | 0 | - |
| W177 | Agent · HumanoidToolBench | 缺口句 | 1 | 0 | - |
| W178 | Agent · Agent Evaluation Reliability: More Tasks Won't (Always) Fix An Agent Leaderboard | 缺口句 | 1 | 0 | - |
| W179 | Agent · cua-speedrun: Standardized Benchmarking of the Speed of Computer-Use Agents | 缺口句 | 1 | 0 | #29 |
| W180 | Agent · MADBench | 缺口句 | 1 | 0 | - |
| W181 | Agent · Trustworthy Runtime Error Healing in Real-World Repositories: A Benchmark and Guardrail | 缺口句 | 1 | 0 | - |
| W182 | Agent · RealWorldShop | 缺口句 | 1 | 0 | - |
| W183 | Agent · AgBench | 缺口句 | 1 | 0 | - |
| W184 | Agent · Beyond Oracle Communication: Benchmarking Interactive Intent Alignment Under Miscommunication and Evolving User Intent | 缺口句 | 1 | 0 | - |
| W185 | Agent · E2E-SWE | 缺口句 | 1 | 0 | - |
| W186 | Agent · CypherTurn | 缺口句 | 1 | 0 | - |
| W187 | Agent · DIBench | 缺口句 | 1 | 0 | - |
| W188 | Agent · CoSE-E | 缺口句 | 1 | 0 | - |
| W189 | Agent · SEABench | 缺口句 | 1 | 0 | - |
| W190 | Agent · JRDB-AVR | 缺口句 | 1 | 0 | - |
| W191 | Agent · PDEU-Bench | 缺口句 | 1 | 0 | - |
| W192 | Agent · Multi-SWT-Bench | 缺口句 | 1 | 0 | - |
| W193 | Agent · PowerBench | 缺口句 | 1 | 0 | - |
| W194 | Agent · ReproBench | 缺口句 | 1 | 0 | - |
| W195 | Agent · Maintaining Benchmarks Against Increasingly Capable Agents: Detection and Remediation of Unearned Passes | 缺口句 | 1 | 0 | - |
| W196 | Agent · Identical Runs, Different Results | 缺口句 | 1 | 0 | - |
| W197 | Agent · TutlAit v1 | 缺口句 | 1 | 0 | - |
| W198 | Agent · VulContextBench | 缺口句 | 1 | 0 | - |
| W199 | Agent · OmniSmartHome | 缺口句 | 1 | 0 | - |
| W200 | Agent · CyberClear | 缺口句 | 1 | 0 | - |
| W201 | Agent · IChart2Code | 缺口句 | 1 | 0 | - |
| W202 | Agent · DashAct | 缺口句 | 1 | 0 | - |
| W203 | Agent · CaptchaArena | 缺口句 | 1 | 0 | #29 |
| W204 | Agent · Build2SPARQL | 缺口句 | 1 | 0 | - |
| W205 | Agent · Trajectory-Aware Benchmark Subset Selection for Cost-Efficient Software Engineering Agent Regression Testing | 缺口句 | 1 | 0 | - |
| W206 | Agent · BVB | 缺口句 | 1 | 0 | - |
| W207 | Agent · BBO | 缺口句 | 1 | 0 | - |
| W208 | Agent · Mine Odyssey: Benchmarking Spatial Agentic Intelligence in the Wild | 缺口句 | 1 | 0 | - |
| W209 | Agent · RH-Detect | 缺口句 | 1 | 0 | - |
| W210 | Agent · TestJack | 缺口句 | 1 | 0 | - |
| W211 | Agent · Humanity's Sixth Sense | 缺口句 | 1 | 0 | - |
| W212 | Agent · ParanoiaEval | 缺口句 | 1 | 0 | - |
| W213 | Agent · RecToolBench | 缺口句 | 1 | 0 | - |
| W214 | 医疗 · HypoKG | 缺口句 | 1 | 0 | #25 |
| W215 | 医疗 · ORQA | 缺口句 | 1 | 0 | - |
| W216 | 医疗 · Meddies-PII: A Multilingual Framework for Personally Identifiable Information Extraction in Clinical De-identification | 缺口句 | 1 | 0 | - |
| W217 | 医疗 · R2MED | 缺口句 | 1 | 0 | #18 |
| W218 | 医疗 · Benchmarking Off-the-Shelf Multimodal AI Models Against Dermatologists on Patient-Captured Skin Images | 缺口句 | 1 | 0 | - |
| W219 | 医疗 · LD-RSVIS | 缺口句 | 1 | 0 | - |
| W220 | 医疗 · MIS-Bench | 缺口句 | 1 | 0 | - |
| W221 | 医疗 · ERCPMP-Gx | 缺口句 | 1 | 0 | - |
| W222 | 医疗 · DementiaCare-Bench | 缺口句 | 1 | 0 | - |
| W223 | 医疗 · LogiMed-RoB | 缺口句 | 1 | 0 | - |
| W224 | 医疗 · Are We Grading Properly? Understanding Failure Modes in Medical Benchmarks | 缺口句 | 1 | 0 | #18 |
| W225 | 医疗 · SynthGait-19K | 缺口句 | 1 | 0 | - |
| W226 | 医疗 · RevalExo | 缺口句 | 1 | 0 | - |
| W227 | 医疗 · SAFER-Activities | 缺口句 | 1 | 0 | - |
| W228 | 医疗 · CNsEMD | 缺口句 | 1 | 0 | - |
| W229 | 医疗 · GAN-Blot | 缺口句 | 1 | 0 | - |
| W230 | 医疗 · STP-BENCH | 缺口句 | 1 | 0 | - |
| W231 | 医疗 · WearableQA | 缺口句 | 1 | 0 | - |
| W232 | 医疗 · Real-World Multi-Modal and Longitudinal Lung Cancer Dataset | 缺口句 | 1 | 0 | - |
| W233 | 医疗 · MMTClinic | 缺口句 | 1 | 0 | #18 |
| W234 | 医疗 · MetaStructAtlas | 缺口句 | 1 | 0 | - |
| W235 | 医疗 · Toward Workflow-Aware Benchmarking for Healthcare NLP Agents | 缺口句 | 1 | 0 | #18 |
| W236 | 医疗 · SurgSkill-Bench | 缺口句 | 1 | 0 | - |
| W237 | 医疗 · ImageCAS-X | 缺口句 | 1 | 0 | - |
| W238 | 医疗 · On the Role of MRI Sequences in Cross-Dataset Generalization for Brain Tumor Segmentation | 缺口句 | 1 | 0 | - |
| W239 | 医疗 · MedSegBenchmarker | 缺口句 | 1 | 0 | - |
| W240 | 医疗 · SUP-MIMIC | 缺口句 | 1 | 0 | #18 |
| W241 | 医疗 · SIC-Agents | 缺口句 | 1 | 0 | - |
| W242 | 医疗 · Is Deformable Image Registration Ready for Brain Metastasis Reirradiation Dose Accumulation? A Longitudinal MRI Benchmark of Registration Accuracy | 缺口句 | 1 | 0 | - |
| W243 | 医疗 · MEGA-CDP | 缺口句 | 1 | 0 | - |
| W244 | 医疗 · IoMT-SecAlarmBench | 缺口句 | 1 | 0 | - |
| W245 | 医疗 · Why ML-based cough models do not generalize: a systematic cross-dataset evaluation for tuberculosis screening | 缺口句 | 1 | 0 | - |
| W246 | 医疗 · Infant Care Video Dataset for Classification of Interventions Using Transformers | 缺口句 | 1 | 0 | - |
| W247 | 医疗 · CRS-Bench | 缺口句 | 1 | 0 | - |
| W248 | 医疗 · FairGlucose | 缺口句 | 1 | 0 | - |
| W249 | 医疗 · SpeechSense | 缺口句 | 1 | 0 | - |
| W250 | 医疗 · Comprehensive Benchmarking of Deep Learning Architectures for Lung Cancer Histopathology | 缺口句 | 1 | 0 | - |
| W251 | 医疗 · AMPLIFAI | 缺口句 | 1 | 0 | #18 |
| W252 | 医疗 · Beyond Simulated Benchmarks: Evaluating Motion Representations for Fall Detection Under Real-World Data Scarcity | 缺口句 | 1 | 0 | - |
| W253 | 医疗 · CoMedBench | 缺口句 | 1 | 0 | - |
| W254 | 医疗 · Apodex Discovery: Reality Benchmarks and Environments for Evaluating and Building Discoverative Artificial Intelligence | 缺口句 | 1 | 0 | - |
| W255 | 医疗 · HeiCo-FOCUS | 缺口句 | 1 | 0 | - |
| W256 | 医疗 · SkinLex | 缺口句 | 1 | 0 | - |
| W257 | 医疗 · TC3-VQA | 缺口句 | 1 | 0 | #18 |
| W258 | 医疗 · MedImageOSWorld | 缺口句 | 1 | 0 | - |
| W259 | 医疗 · Below what training size do deep tabular generators stop beating trivial baselines? A preregistered benchmark on a size ladder of clinical and standard datasets | 缺口句 | 1 | 0 | - |
| W260 | 医疗 · Benchmarking Literature Retrieval for a Model Organism: A Dictyostelium Case Study | 缺口句 | 1 | 0 | - |
| W261 | 医疗 · Scores That Hold, Benchmarks That Leak: Measuring Dataset Contamination in Public Brain-Tumor MRI Classification | 缺口句 | 1 | 0 | - |
| W262 | 医疗 · TALK-Dem | 缺口句 | 1 | 0 | - |
| W263 | 医疗 · Merlin Plus: A Large-Scale, Multi-Cancer, Image-Mask-Report Dataset | 缺口句 | 1 | 0 | - |
| W264 | 医疗 · PhotoMOCI | 缺口句 | 1 | 0 | - |
| W265 | 医疗 · OpenTumorBoard | 缺口句 | 1 | 0 | - |
| W266 | 医疗 · AnesTRACE | 缺口句 | 1 | 0 | - |
| W267 | 医疗 · What Can a Leaderboard Certify? Compositional Controllability for Fair Evaluation and Training of Biomedical Literature-Review Agents | 缺口句 | 1 | 0 | - |
| W268 | 医疗 · BioEVAL | 缺口句 | 1 | 0 | - |
| W269 | 医疗 · A Living Benchmark for Information Retrieval from Electronic Health Records | 缺口句 | 1 | 0 | - |
| W270 | 医疗 · Synthetic Hospital: An Open, Verifiable, Physician-Validated Longitudinal EHR Benchmark | 缺口句 | 1 | 0 | - |
| W271 | 医疗 · A Multimodal Dataset for Survival Prediction in Resected Pancreatic Ductal Adenocarcinoma | 缺口句 | 1 | 0 | - |
| W272 | 医疗 · Language Specificity vs. Domain Diversity: Benchmarking Transformers for Bangla Medical NER | 缺口句 | 1 | 0 | - |
| W273 | 医疗 · Pre-training, Reasoning, Benchmarking | 缺口句 | 1 | 0 | - |
| W274 | 金融 · FinFIRST | 缺口句 | 1 | 0 | #28 |
| W275 | 金融 · STQA | 缺口句 | 1 | 0 | - |
| W276 | 金融 · FinixDoc | 缺口句 | 1 | 0 | - |
| W277 | 金融 · FrontierFinance | 缺口句 | 1 | 0 | - |
| W278 | 金融 · InsClaimBench | 缺口句 | 1 | 0 | - |
| W279 | 金融 · A Citation-Grounded Benchmark for Trustworthy Earnings Call Transcript Analysis with Large Language Models | 缺口句 | 1 | 0 | #1 |
| W280 | 金融 · FinancialAuditBench | 缺口句 | 1 | 0 | - |
| W281 | 法律 · Mining Legal Arguments in U.S. Corporate Case Law | 缺口句 | 1 | 0 | - |
| W282 | 法律 · Better Call CLAUSE | 缺口句 | 1 | 0 | #2 |
| W283 | 法律 · Sycophants in the Courtroom: Are LLMs Fragile to Juridical Authority and Evolving Legal Standards? | 缺口句 | 1 | 0 | - |
| W284 | 法律 · UK-PRBENCH | 缺口句 | 1 | 0 | - |
| W285 | 法律 · IntLawNER | 缺口句 | 1 | 0 | - |
| W286 | 法律 · Bridging the First-Hour Gap: Evaluating AI Reliability and Benchmarking Deficiencies in Cyber Incident Response for Law Enforcement | 缺口句 | 1 | 0 | - |
| W287 | 法律 · ProMediConv | 缺口句 | 1 | 0 | - |
| W288 | 法律 · KhatianDoc | 缺口句 | 1 | 0 | - |
| W289 | 法律 · Do Small Models Use the Law You Give Them? Measuring Context Use on a Bilingual Bangladesh Legal Benchmark | 缺口句 | 1 | 0 | - |
| W290 | 法律 · Dis2Pat | 缺口句 | 1 | 0 | - |
| W291 | 法律 · GreekBarRetrieval | 缺口句 | 1 | 0 | - |
| W292 | 法律 · Gated Against One Model, Open to the Next: Option-Only Solvability in Legal Multiple-Choice Benchmarks | 缺口句 | 1 | 0 | - |
| W293 | 法律 · JusticeAxis | 缺口句 | 1 | 0 | - |

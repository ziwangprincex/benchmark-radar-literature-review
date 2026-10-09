# Coverage Probe｜外部 Benchmark 目录核查结果

生成时间：2026-09-23T06:41:42+00:00　检索器：benchmark-radar-catalog-v1

> 本报告基于 benchmark-radar 聚合目录（secondary 源）。目录记录只含 name/description/categories，不含 task definition、input/output 与 evaluation protocol，因此不能据此判定 covered 或 not_covered。所有写入 benchmark_coverage 的行均为 needs_review / unknown。

## 结论分布

| Verdict | Idea 数 | 含义 |
|---|---:|---|
| `topic_too_wide` | 15 | 命中过多，主题过宽缺区分度，应先收窄 |
| `needs_manual_coverage_analysis` | 8 | 有少量候选，需人工核查原文定论 |

## 逐 Idea 结果

### Idea 1｜PDF财报异常识别与证据引用

- Domain：financial　Status：candidate　Score：75.0
- 目录候选：20 条　进入核查：2 条
- Verdict：**`needs_manual_coverage_analysis`**
- 建议：有 2 条候选需要人工核查原始 Paper/Repo 的 task definition 与 evaluation protocol，才能判定是否真的覆盖目标任务。

| Benchmark | 目录源 | 判定依据 |
|---|---|---|
| FinQA | llm_stats | 领域信号 ['financial', 'finance']，任务信号 ['numerical']，命中词 ['financial', 'numerical']（query coverage 0.18）；进入人工 Coverage 核查 |
| Big Finance Bench | llm_stats | 领域信号 ['financial', 'finance']，任务信号 ['quantitative']，命中词 ['finance', 'financial', 'multi', 'reasoning']（query coverage 0.29）；进入人工 Coverage 核查 |

### Idea 2｜合同跨条款风险审查

- Domain：legal　Status：candidate　Score：72.0
- 目录候选：20 条　进入核查：1 条
- Verdict：**`needs_manual_coverage_analysis`**
- 建议：有 1 条候选需要人工核查原始 Paper/Repo 的 task definition 与 evaluation protocol，才能判定是否真的覆盖目标任务。

| Benchmark | 目录源 | 判定依据 |
|---|---|---|
| Uniform Bar Exam | llm_stats | 领域信号 ['legal', 'law', 'contract']，任务信号 ['contract']，命中词 ['benchmark', 'evidence', 'law', 'legal', 'reasoning']（query coverage 0.33）；进入人工 Coverage 核查 |

### Idea 18｜临床推理与指南溯源

- Domain：medical　Status：candidate　Score：67.0
- 目录候选：20 条　进入核查：6 条
- Verdict：**`needs_manual_coverage_analysis`**
- 建议：有 6 条候选需要人工核查原始 Paper/Repo 的 task definition 与 evaluation protocol，才能判定是否真的覆盖目标任务。
- 已有人工核查：CMB(not_covered/verified)、CliMedBench(unknown/partial)、LLMEval-Med(not_covered/verified)、MedQA(not_covered/verified)

| Benchmark | 目录源 | 判定依据 |
|---|---|---|
| CRPErelation | llm_stats | 领域信号 ['medical', 'clinical', 'health']，任务信号 ['clinical', 'diagnos', 'reasoning']，命中词 ['benchmark', 'clinical', 'evaluation', 'reasoning']（query coverage 0.57）；进入人工 Coverage 核查 |
| MedBookVQA | opencompass_hub | 领域信号 ['medical', 'clinical', '临床']，任务信号 ['clinical', 'reasoning']，命中词 ['benchmark', 'clinical', 'reasoning']（query coverage 0.43）；进入人工 Coverage 核查 |
| MedAgents-Bench | opencompass_hub | 领域信号 ['medical', 'clinical', '临床']，任务信号 ['clinical', 'reasoning']，命中词 ['clinical', 'evaluation', 'reasoning']（query coverage 0.43）；进入人工 Coverage 核查 |
| MedBrowseComp | opencompass_hub | 领域信号 ['medical', 'clinical']，任务信号 ['clinical', 'reasoning']，命中词 ['benchmark', 'clinical', 'reasoning']（query coverage 0.43）；进入人工 Coverage 核查 |
| ER-Reason | opencompass_hub | 领域信号 ['medical', 'clinical', '临床']，任务信号 ['clinical', 'reasoning']，命中词 ['benchmark', 'clinical', 'reasoning']（query coverage 0.43）；进入人工 Coverage 核查 |
| MedXpertQA | llm_stats | 领域信号 ['medical', 'clinical', 'health']，任务信号 ['clinical', 'reasoning']，命中词 ['benchmark', 'clinical', 'expert', 'knowledge', 'medical', 'reasoning']（query coverage 0.46）；进入人工 Coverage 核查 |

### Idea 9｜Agent Domain Reasoning能力评测

- Domain：agent　Status：rejected　Score：66.0
- 目录候选：20 条　进入核查：12 条
- Verdict：**`topic_too_wide`**
- 建议：检索命中 12 条同领域基准，接近每查询取样上限，说明该 Idea 主题过宽、缺乏区分度。应先收窄任务定义，再谈 Gap。

| Benchmark | 目录源 | 判定依据 |
|---|---|---|
| Agents' Last Exam | model_reports | 领域信号 ['agent', 'agentic']，任务信号 ['reasoning', 'multi', 'tool']，命中词 ['agent', 'agentic', 'benchmark']（query coverage 0.75）；进入人工 Coverage 核查 |
| Finance Agent | llm_stats | 领域信号 ['agent', 'agentic']，任务信号 ['domain']，命中词 ['agent', 'agentic', 'benchmark']（query coverage 0.75）；进入人工 Coverage 核查 |
| Finance Agent v1.1 | llm_stats | 领域信号 ['agent', 'agentic']，任务信号 ['reasoning', 'multi']，命中词 ['agent', 'agentic', 'benchmark']（query coverage 0.75）；进入人工 Coverage 核查 |
| CREW-WILDFIRE | opencompass_hub | 领域信号 ['agent', 'agentic', '智能体']，任务信号 ['planning']，命中词 ['agent', 'agentic', 'benchmark']（query coverage 0.75）；进入人工 Coverage 核查 |
| Finance Agent v2 | llm_stats | 领域信号 ['agent', 'agentic']，任务信号 ['reasoning', 'multi']，命中词 ['agent', 'agentic', 'benchmark']（query coverage 0.75）；进入人工 Coverage 核查 |
| Cohere Agentic Question Answering | llm_stats | 领域信号 ['agent', 'agentic']，任务信号 ['reasoning']，命中词 ['agentic', 'evaluation']（query coverage 0.50）；进入人工 Coverage 核查 |
| Job Bench | llm_stats | 领域信号 ['agent']，任务信号 ['reasoning', 'planning']，命中词 ['multi', 'planning', 'professional', 'reasoning', 'step']（query coverage 0.42）；进入人工 Coverage 核查 |
| APEX-Agents | llm_stats | 领域信号 ['agent']，任务信号 ['reasoning', 'planning']，命中词 ['benchmark', 'multi', 'planning', 'professional', 'reasoning', 'step']（query coverage 0.50）；进入人工 Coverage 核查 |
| DABstep | opencompass_hub | 领域信号 ['agent', '智能体']，任务信号 ['reasoning', 'planning']，命中词 ['agent', 'benchmark', 'multi', 'planning', 'reasoning', 'step']（query coverage 0.50）；进入人工 Coverage 核查 |
| t2-bench | llm_stats | 领域信号 ['agent', 'agentic']，任务信号 ['reasoning', 'planning', 'tool']，命中词 ['agentic', 'benchmark', 'multi', 'planning', 'reasoning', 'step']（query coverage 0.50）；进入人工 Coverage 核查 |
| MCP-Universe | llm_stats | 领域信号 ['agent', 'agentic']，任务信号 ['planning', 'tool']，命中词 ['agentic', 'multi', 'planning', 'step']（query coverage 0.33）；进入人工 Coverage 核查 |
| RedCode | opencompass_hub | 领域信号 ['agent', '智能体']，任务信号 ['domain', 'safety']，命中词 ['agent', 'harmful', 'safety']（query coverage 0.25）；进入人工 Coverage 核查 |

### Idea 4｜General Domain Expertise能力评测

- Domain：general　Status：candidate　Score：65.0
- 目录候选：20 条　进入核查：13 条
- Verdict：**`topic_too_wide`**
- 建议：检索命中 13 条同领域基准，接近每查询取样上限，说明该 Idea 主题过宽、缺乏区分度。应先收窄任务定义，再谈 Gap。

| Benchmark | 目录源 | 判定依据 |
|---|---|---|
| lm-evaluation-harness | opencompass_hub | 领域信号 []，任务信号 ['knowledge']，命中词 ['benchmark', 'evaluation']（query coverage 1.00）；进入人工 Coverage 核查 |
| CRPErelation | llm_stats | 领域信号 []，任务信号 ['knowledge']，命中词 ['benchmark', 'evaluation']（query coverage 1.00）；进入人工 Coverage 核查 |
| UHGEval | opencompass_hub | 领域信号 []，任务信号 ['knowledge']，命中词 ['benchmark', 'evaluation']（query coverage 1.00）；进入人工 Coverage 核查 |
| ProfBench | llm_stats | 领域信号 []，任务信号 ['expert']，命中词 ['domain', 'expert', 'knowledge', 'professional']（query coverage 0.67）；进入人工 Coverage 核查 |
| SuperChem | llm_stats | 领域信号 []，任务信号 ['expert']，命中词 ['benchmark', 'domain', 'expert', 'knowledge']（query coverage 0.67）；进入人工 Coverage 核查 |
| FrontierScience Research | llm_stats | 领域信号 []，任务信号 ['expert']，命中词 ['benchmark', 'domain', 'expertise']（query coverage 0.50）；进入人工 Coverage 核查 |
| APEX-Agents | model_reports | 领域信号 []，任务信号 ['expert']，命中词 ['expert', 'professional']（query coverage 0.33）；进入人工 Coverage 核查 |
| GDPval | model_reports | 领域信号 []，任务信号 ['expert']，命中词 ['expert', 'professional']（query coverage 0.33）；进入人工 Coverage 核查 |
| PLawBench | llm_stats | 领域信号 []，任务信号 ['knowledge']，命中词 ['knowledge', 'professional']（query coverage 0.33）；进入人工 Coverage 核查 |
| VideoMMMU | llm_stats | 领域信号 []，任务信号 ['expert']，命中词 ['expert', 'knowledge', 'professional']（query coverage 0.50）；进入人工 Coverage 核查 |
| PRBench-Legal | llm_stats | 领域信号 []，任务信号 ['knowledge']，命中词 ['knowledge', 'professional']（query coverage 0.33）；进入人工 Coverage 核查 |
| PRBench-Finance | llm_stats | 领域信号 []，任务信号 ['knowledge']，命中词 ['knowledge', 'professional']（query coverage 0.33）；进入人工 Coverage 核查 |
| HLE-Verified | llm_stats | 领域信号 []，任务信号 ['expert']，命中词 ['expert', 'knowledge']（query coverage 0.33）；进入人工 Coverage 核查 |

### Idea 6｜Agent Domain Expertise能力评测

- Domain：agent　Status：rejected　Score：64.0
- 目录候选：20 条　进入核查：6 条
- Verdict：**`needs_manual_coverage_analysis`**
- 建议：有 6 条候选需要人工核查原始 Paper/Repo 的 task definition 与 evaluation protocol，才能判定是否真的覆盖目标任务。

| Benchmark | 目录源 | 判定依据 |
|---|---|---|
| Finance Agent | llm_stats | 领域信号 ['agent', 'agentic']，任务信号 ['domain']，命中词 ['agent', 'agentic', 'benchmark']（query coverage 0.75）；进入人工 Coverage 核查 |
| ProfBench | llm_stats | 领域信号 ['agent']，任务信号 ['expert']，命中词 ['domain', 'expert', 'knowledge', 'professional']（query coverage 0.50）；进入人工 Coverage 核查 |
| APEX-Agents | model_reports | 领域信号 ['agent']，任务信号 ['expert']，命中词 ['agent', 'expert', 'professional']（query coverage 0.38）；进入人工 Coverage 核查 |
| AA-Briefcase | artificial_analysis | 领域信号 ['agent', 'agentic']，任务信号 ['knowledge']，命中词 ['agentic', 'knowledge']（query coverage 0.25）；进入人工 Coverage 核查 |
| MedBrowseComp | opencompass_hub | 领域信号 ['agent']，任务信号 ['knowledge']，命中词 ['agent', 'benchmark', 'domain', 'knowledge']（query coverage 0.50）；进入人工 Coverage 核查 |
| BankerToolBench | model_reports | 领域信号 ['agent']，任务信号 ['professional']，命中词 ['agent', 'professional']（query coverage 0.25）；进入人工 Coverage 核查 |

### Idea 11｜General Tool Use能力评测

- Domain：general　Status：rejected　Score：64.0
- 目录候选：20 条　进入核查：13 条
- Verdict：**`topic_too_wide`**
- 建议：检索命中 13 条同领域基准，接近每查询取样上限，说明该 Idea 主题过宽、缺乏区分度。应先收窄任务定义，再谈 Gap。

| Benchmark | 目录源 | 判定依据 |
|---|---|---|
| lm-evaluation-harness | opencompass_hub | 领域信号 []，任务信号 ['multi']，命中词 ['benchmark', 'evaluation']（query coverage 1.00）；进入人工 Coverage 核查 |
| Translation Set1→en spBleu | llm_stats | 领域信号 []，任务信号 ['multi']，命中词 ['benchmark', 'evaluation']（query coverage 1.00）；进入人工 Coverage 核查 |
| Translation en→Set1 spBleu | llm_stats | 领域信号 []，任务信号 ['multi']，命中词 ['benchmark', 'evaluation']（query coverage 1.00）；进入人工 Coverage 核查 |
| Internal Research Debugging Evaluation | llm_stats | 领域信号 []，任务信号 ['use']，命中词 ['evaluation']（query coverage 0.50）；进入人工 Coverage 核查 |
| API-Bank | llm_stats | 领域信号 []，任务信号 ['planning', 'tool']，命中词 ['api', 'benchmark', 'calling', 'planning', 'tool', 'use']（query coverage 0.67）；进入人工 Coverage 核查 |
| BFCL_v3_MultiTurn | llm_stats | 领域信号 []，任务信号 ['multi', 'use']，命中词 ['api', 'benchmark', 'calling', 'function', 'multi', 'step', 'tool', 'use']（query coverage 0.89）；进入人工 Coverage 核查 |
| Search and Function-Calling | llm_stats | 领域信号 []，任务信号 ['tool']，命中词 ['benchmark', 'calling', 'function', 'tool', 'use']（query coverage 0.56）；进入人工 Coverage 核查 |
| BFCL | llm_stats | 领域信号 []，任务信号 ['multi', 'use']，命中词 ['api', 'benchmark', 'calling', 'function', 'multi', 'tool', 'use']（query coverage 0.78）；进入人工 Coverage 核查 |
| t2-bench | llm_stats | 领域信号 []，任务信号 ['planning', 'tool']，命中词 ['benchmark', 'calling', 'multi', 'planning', 'step', 'tool', 'use']（query coverage 0.78）；进入人工 Coverage 核查 |
| Nexus | llm_stats | 领域信号 []，任务信号 ['tool']，命中词 ['api', 'benchmark', 'calling', 'function', 'tool']（query coverage 0.56）；进入人工 Coverage 核查 |
| MCP-Universe | llm_stats | 领域信号 []，任务信号 ['planning', 'tool']，命中词 ['calling', 'multi', 'planning', 'step', 'tool']（query coverage 0.56）；进入人工 Coverage 核查 |
| AutomationBench | llm_stats | 领域信号 []，任务信号 ['multi', 'tool']，命中词 ['benchmark', 'calling', 'multi', 'step', 'tool', 'use']（query coverage 0.67）；进入人工 Coverage 核查 |
| GAIA2 | llm_stats | 领域信号 []，任务信号 ['multi', 'tool']，命中词 ['calling', 'multi', 'step', 'tool', 'use']（query coverage 0.56）；进入人工 Coverage 核查 |

### Idea 20｜Medical Domain Expertise能力评测

- Domain：medical　Status：watch　Score：63.0
- 目录候选：20 条　进入核查：8 条
- Verdict：**`topic_too_wide`**
- 建议：检索命中 8 条同领域基准，接近每查询取样上限，说明该 Idea 主题过宽、缺乏区分度。应先收窄任务定义，再谈 Gap。

| Benchmark | 目录源 | 判定依据 |
|---|---|---|
| CRPErelation | llm_stats | 领域信号 ['medical', 'clinical', 'health']，任务信号 ['knowledge']，命中词 ['benchmark', 'clinical', 'evaluation', 'medical']（query coverage 0.80）；进入人工 Coverage 核查 |
| MedBrowseComp | opencompass_hub | 领域信号 ['medical', 'clinical']，任务信号 ['knowledge']，命中词 ['benchmark', 'clinical', 'medical']（query coverage 0.60）；进入人工 Coverage 核查 |
| MedAgents-Bench | opencompass_hub | 领域信号 ['medical', 'clinical', '临床']，任务信号 ['knowledge']，命中词 ['clinical', 'evaluation', 'medical']（query coverage 0.60）；进入人工 Coverage 核查 |
| MedXpertQA | llm_stats | 领域信号 ['medical', 'clinical', 'health']，任务信号 ['expert']，命中词 ['benchmark', 'clinical', 'medical']（query coverage 0.60）；进入人工 Coverage 核查 |
| EHRNoteQA | opencompass_hub | 领域信号 ['clinical', 'health', 'patient', '临床']，任务信号 ['knowledge']，命中词 ['clinical', 'health']（query coverage 0.40）；进入人工 Coverage 核查 |
| HealthBench Professional | model_reports | 领域信号 ['health']，任务信号 ['professional']，命中词 ['health']（query coverage 0.20）；进入人工 Coverage 核查 |
| MedXpertQA-MM | llm_stats | 领域信号 ['medical']，任务信号 ['expert']，命中词 ['expert', 'knowledge', 'medical']（query coverage 0.33）；进入人工 Coverage 核查 |
| MedXpertQA | opencompass_hub | 领域信号 ['medical', '临床']，任务信号 ['expert']，命中词 ['benchmark', 'expert', 'knowledge', 'medical']（query coverage 0.44）；进入人工 Coverage 核查 |

### Idea 16｜General Domain Reasoning能力评测

- Domain：general　Status：watch　Score：62.0
- 目录候选：20 条　进入核查：11 条
- Verdict：**`topic_too_wide`**
- 建议：检索命中 11 条同领域基准，接近每查询取样上限，说明该 Idea 主题过宽、缺乏区分度。应先收窄任务定义，再谈 Gap。

| Benchmark | 目录源 | 判定依据 |
|---|---|---|
| CRPErelation | llm_stats | 领域信号 []，任务信号 ['reasoning']，命中词 ['benchmark', 'evaluation']（query coverage 1.00）；进入人工 Coverage 核查 |
| Internal Research Debugging Evaluation | llm_stats | 领域信号 []，任务信号 ['reasoning', 'use']，命中词 ['evaluation']（query coverage 0.50）；进入人工 Coverage 核查 |
| API-Bank | llm_stats | 领域信号 []，任务信号 ['reasoning', 'tool']，命中词 ['api', 'benchmark', 'calling', 'reasoning', 'tool', 'use']（query coverage 0.67）；进入人工 Coverage 核查 |
| Search and Function-Calling | llm_stats | 领域信号 []，任务信号 ['tool']，命中词 ['benchmark', 'calling', 'function', 'tool', 'use']（query coverage 0.56）；进入人工 Coverage 核查 |
| BFCL_v3_MultiTurn | llm_stats | 领域信号 []，任务信号 ['reasoning', 'use']，命中词 ['api', 'benchmark', 'calling', 'function', 'reasoning', 'tool', 'use']（query coverage 0.78）；进入人工 Coverage 核查 |
| BFCL | llm_stats | 领域信号 []，任务信号 ['domain', 'use']，命中词 ['api', 'benchmark', 'calling', 'function', 'reasoning', 'tool', 'use']（query coverage 0.78）；进入人工 Coverage 核查 |
| Nexus | llm_stats | 领域信号 []，任务信号 ['tool']，命中词 ['api', 'benchmark', 'calling', 'function', 'tool']（query coverage 0.56）；进入人工 Coverage 核查 |
| Gorilla Benchmark API Bench | llm_stats | 领域信号 []，任务信号 ['reasoning', 'api']，命中词 ['api', 'benchmark', 'calling', 'reasoning', 'tool']（query coverage 0.56）；进入人工 Coverage 核查 |
| TAU-bench Airline | llm_stats | 领域信号 []，任务信号 ['domain', 'tool']，命中词 ['api', 'benchmark', 'calling', 'domain', 'reasoning', 'tool']（query coverage 0.67）；进入人工 Coverage 核查 |
| TAU-bench Retail | llm_stats | 领域信号 []，任务信号 ['domain', 'tool']，命中词 ['api', 'benchmark', 'calling', 'domain', 'reasoning', 'tool']（query coverage 0.67）；进入人工 Coverage 核查 |
| Tau-bench | llm_stats | 领域信号 []，任务信号 ['domain', 'tool']，命中词 ['api', 'benchmark', 'calling', 'domain', 'reasoning', 'tool']（query coverage 0.67）；进入人工 Coverage 核查 |

### Idea 15｜Scientific Domain Reasoning能力评测

- Domain：scientific　Status：watch　Score：61.0
- 目录候选：20 条　进入核查：17 条
- Verdict：**`topic_too_wide`**
- 建议：检索命中 17 条同领域基准，接近每查询取样上限，说明该 Idea 主题过宽、缺乏区分度。应先收窄任务定义，再谈 Gap。

| Benchmark | 目录源 | 判定依据 |
|---|---|---|
| FrontierScience Research | llm_stats | 领域信号 ['scientific', 'science', 'research']，任务信号 ['domain', 'multi']，命中词 ['benchmark', 'research', 'science', 'scientific']（query coverage 0.80）；进入人工 Coverage 核查 |
| SGI-Bench | opencompass_hub | 领域信号 ['scientific', 'science', 'research', '科学']，任务信号 ['reasoning', 'multi']，命中词 ['benchmark', 'research', 'science', 'scientific']（query coverage 0.80）；进入人工 Coverage 核查 |
| Frontier Science | llm_stats | 领域信号 ['scientific', 'science']，任务信号 ['domain', 'multi']，命中词 ['benchmark', 'science', 'scientific']（query coverage 0.60）；进入人工 Coverage 核查 |
| RXRX3-CORE | opencompass_hub | 领域信号 ['scientific', 'science', 'research', '科学']，任务信号 ['reasoning']，命中词 ['research', 'science', 'scientific']（query coverage 0.60）；进入人工 Coverage 核查 |
| CLEVER | opencompass_hub | 领域信号 ['scientific', 'science', '科学']，任务信号 ['reasoning']，命中词 ['benchmark', 'evaluation', 'science', 'scientific']（query coverage 0.80）；进入人工 Coverage 核查 |
| MedBench | opencompass_hub | 领域信号 ['scientific', 'science', '科学']，任务信号 ['reasoning']，命中词 ['evaluation', 'science', 'scientific']（query coverage 0.60）；进入人工 Coverage 核查 |
| ChemBench | opencompass_hub | 领域信号 ['scientific', 'science', '科学']，任务信号 ['reasoning']，命中词 ['benchmark', 'evaluation', 'science', 'scientific']（query coverage 0.80）；进入人工 Coverage 核查 |
| RDB2G-Bench | opencompass_hub | 领域信号 ['scientific', 'science', '科学']，任务信号 ['reasoning', 'multi']，命中词 ['evaluation', 'science', 'scientific']（query coverage 0.60）；进入人工 Coverage 核查 |
| GPQA Diamond | artificial_analysis | 领域信号 ['scientific', 'science']，任务信号 ['reasoning']，命中词 ['science', 'scientific']（query coverage 0.40）；进入人工 Coverage 核查 |
| Job Bench | llm_stats | 领域信号 ['research']，任务信号 ['reasoning', 'planning']，命中词 ['multi', 'planning', 'professional', 'reasoning', 'research', 'step']（query coverage 0.60）；进入人工 Coverage 核查 |
| BixBench | llm_stats | 领域信号 ['scientific', 'science']，任务信号 ['domain', 'multi']，命中词 ['benchmark', 'domain', 'multi', 'reasoning', 'science', 'scientific', 'step']（query coverage 0.70）；进入人工 Coverage 核查 |
| APEX-Agents | llm_stats | 无 scientific 领域标注，但任务信号强命中 ['reasoning', 'planning']；疑为跨领域通用基准，需人工核查其数据来源是否覆盖目标任务 |
| FrontierScience Olympiad | llm_stats | 领域信号 ['scientific', 'science']，任务信号 ['domain', 'multi']，命中词 ['benchmark', 'multi', 'reasoning', 'science', 'scientific', 'step']（query coverage 0.60）；进入人工 Coverage 核查 |
| MedBrowseComp | opencompass_hub | 领域信号 ['scientific', 'science', '科学']，任务信号 ['domain', 'multi']，命中词 ['benchmark', 'domain', 'multi', 'reasoning', 'science', 'scientific']（query coverage 0.60）；进入人工 Coverage 核查 |
| PaperBench | llm_stats | 领域信号 ['scientific', 'research']，任务信号 ['reasoning', 'multi']，命中词 ['benchmark', 'multi', 'reasoning', 'research', 'scientific', 'step']（query coverage 0.60）；进入人工 Coverage 核查 |
| DeepPlanning | llm_stats | 无 scientific 领域标注，但任务信号强命中 ['reasoning', 'planning']；疑为跨领域通用基准，需人工核查其数据来源是否覆盖目标任务 |
| FrontierCS | llm_stats | 领域信号 ['science']，任务信号 ['reasoning', 'multi']，命中词 ['benchmark', 'multi', 'reasoning', 'science', 'step']（query coverage 0.50）；进入人工 Coverage 核查 |

### Idea 19｜Scientific Version Awareness能力评测

- Domain：scientific　Status：watch　Score：60.0
- 目录候选：20 条　进入核查：9 条
- Verdict：**`topic_too_wide`**
- 建议：检索命中 9 条同领域基准，接近每查询取样上限，说明该 Idea 主题过宽、缺乏区分度。应先收窄任务定义，再谈 Gap。

| Benchmark | 目录源 | 判定依据 |
|---|---|---|
| MedBench | opencompass_hub | 领域信号 ['scientific', 'science', '科学']，任务信号 ['knowledge']，命中词 ['evaluation', 'science', 'scientific']（query coverage 0.60）；进入人工 Coverage 核查 |
| ChemBench | opencompass_hub | 领域信号 ['scientific', 'science', '科学']，任务信号 ['knowledge']，命中词 ['benchmark', 'evaluation', 'science', 'scientific']（query coverage 0.80）；进入人工 Coverage 核查 |
| OmniScience | llm_stats | 领域信号 ['scientific', 'science']，任务信号 ['knowledge']，命中词 ['benchmark', 'knowledge', 'science', 'scientific']（query coverage 0.50）；进入人工 Coverage 核查 |
| Fin-Eva | opencompass_hub | 领域信号 ['research']，任务信号 ['version']，命中词 ['benchmark', 'knowledge', 'research', 'version']（query coverage 0.50）；进入人工 Coverage 核查 |
| AECBench | opencompass_hub | 领域信号 ['scientific', 'science', '科学']，任务信号 ['knowledge']，命中词 ['benchmark', 'knowledge', 'science', 'scientific']（query coverage 0.50）；进入人工 Coverage 核查 |
| SciCode | llm_stats | 领域信号 ['scientific', 'science', 'research']，任务信号 ['knowledge']，命中词 ['benchmark', 'knowledge', 'research', 'science', 'scientific']（query coverage 0.62）；进入人工 Coverage 核查 |
| SWE-bench Science | model_reports | 领域信号 ['scientific', 'science']，任务信号 ['knowledge']，命中词 ['benchmark', 'knowledge', 'science', 'scientific']（query coverage 0.50）；进入人工 Coverage 核查 |
| PhysReason | opencompass_hub | 领域信号 ['scientific', 'science', '科学']，任务信号 ['knowledge']，命中词 ['benchmark', 'knowledge', 'science', 'scientific']（query coverage 0.50）；进入人工 Coverage 核查 |
| ScienceQA | opencompass_hub | 领域信号 ['scientific', 'science', '科学']，任务信号 ['knowledge']，命中词 ['benchmark', 'knowledge', 'science', 'scientific']（query coverage 0.50）；进入人工 Coverage 核查 |

### Idea 8｜General Safety能力评测

- Domain：general　Status：rejected　Score：59.0
- 目录候选：20 条　进入核查：13 条
- Verdict：**`topic_too_wide`**
- 建议：检索命中 13 条同领域基准，接近每查询取样上限，说明该 Idea 主题过宽、缺乏区分度。应先收窄任务定义，再谈 Gap。

| Benchmark | 目录源 | 判定依据 |
|---|---|---|
| lm-evaluation-harness | opencompass_hub | 领域信号 []，任务信号 ['multi']，命中词 ['benchmark', 'evaluation']（query coverage 1.00）；进入人工 Coverage 核查 |
| Translation Set1→en spBleu | llm_stats | 领域信号 []，任务信号 ['multi']，命中词 ['benchmark', 'evaluation']（query coverage 1.00）；进入人工 Coverage 核查 |
| Translation en→Set1 spBleu | llm_stats | 领域信号 []，任务信号 ['multi']，命中词 ['benchmark', 'evaluation']（query coverage 1.00）；进入人工 Coverage 核查 |
| AIR-Bench | llm_stats | 领域信号 []，任务信号 ['safety']，命中词 ['benchmark', 'refusal', 'safety']（query coverage 0.43）；进入人工 Coverage 核查 |
| MedSafetyBench | opencompass_hub | 领域信号 []，任务信号 ['safety']，命中词 ['harmful', 'safety']（query coverage 0.29）；进入人工 Coverage 核查 |
| DeepPlanning | llm_stats | 领域信号 []，任务信号 ['planning']，命中词 ['multi', 'planning', 'step']（query coverage 0.43）；进入人工 Coverage 核查 |
| Job Bench | llm_stats | 领域信号 []，任务信号 ['planning']，命中词 ['multi', 'planning', 'step']（query coverage 0.43）；进入人工 Coverage 核查 |
| APEX-Agents | llm_stats | 领域信号 []，任务信号 ['planning']，命中词 ['benchmark', 'multi', 'planning', 'step']（query coverage 0.57）；进入人工 Coverage 核查 |
| AttaQ | llm_stats | 领域信号 []，任务信号 ['safety']，命中词 ['benchmark', 'harmful', 'safety']（query coverage 0.43）；进入人工 Coverage 核查 |
| CloningScenarios | llm_stats | 领域信号 []，任务信号 ['multi', 'safety']，命中词 ['benchmark', 'multi', 'safety', 'step']（query coverage 0.57）；进入人工 Coverage 核查 |
| FalseReject | opencompass_hub | 领域信号 []，任务信号 ['safety']，命中词 ['refusal', 'safety']（query coverage 0.29）；进入人工 Coverage 核查 |
| RedCode | opencompass_hub | 领域信号 []，任务信号 ['safety']，命中词 ['harmful', 'safety']（query coverage 0.29）；进入人工 Coverage 核查 |
| DABstep | opencompass_hub | 领域信号 []，任务信号 ['planning']，命中词 ['benchmark', 'multi', 'planning', 'step']（query coverage 0.57）；进入人工 Coverage 核查 |

### Idea 12｜General Planning能力评测

- Domain：general　Status：rejected　Score：58.0
- 目录候选：20 条　进入核查：13 条
- Verdict：**`topic_too_wide`**
- 建议：检索命中 13 条同领域基准，接近每查询取样上限，说明该 Idea 主题过宽、缺乏区分度。应先收窄任务定义，再谈 Gap。

| Benchmark | 目录源 | 判定依据 |
|---|---|---|
| lm-evaluation-harness | opencompass_hub | 领域信号 []，任务信号 ['multi']，命中词 ['benchmark', 'evaluation']（query coverage 1.00）；进入人工 Coverage 核查 |
| Translation Set1→en spBleu | llm_stats | 领域信号 []，任务信号 ['multi']，命中词 ['benchmark', 'evaluation']（query coverage 1.00）；进入人工 Coverage 核查 |
| Translation en→Set1 spBleu | llm_stats | 领域信号 []，任务信号 ['multi']，命中词 ['benchmark', 'evaluation']（query coverage 1.00）；进入人工 Coverage 核查 |
| DeepPlanning | llm_stats | 领域信号 []，任务信号 ['planning']，命中词 ['multi', 'planning', 'step']（query coverage 0.75）；进入人工 Coverage 核查 |
| Job Bench | llm_stats | 领域信号 []，任务信号 ['planning']，命中词 ['multi', 'planning', 'step']（query coverage 0.75）；进入人工 Coverage 核查 |
| APEX-Agents | llm_stats | 领域信号 []，任务信号 ['planning']，命中词 ['benchmark', 'multi', 'planning', 'step']（query coverage 1.00）；进入人工 Coverage 核查 |
| DABstep | opencompass_hub | 领域信号 []，任务信号 ['planning']，命中词 ['benchmark', 'multi', 'planning', 'step']（query coverage 1.00）；进入人工 Coverage 核查 |
| MCP-Universe | llm_stats | 领域信号 []，任务信号 ['planning']，命中词 ['multi', 'planning', 'step']（query coverage 0.75）；进入人工 Coverage 核查 |
| Workspace Bench | llm_stats | 领域信号 []，任务信号 ['planning']，命中词 ['multi', 'planning', 'step']（query coverage 0.75）；进入人工 Coverage 核查 |
| t2-bench | llm_stats | 领域信号 []，任务信号 ['planning']，命中词 ['benchmark', 'multi', 'planning', 'step']（query coverage 1.00）；进入人工 Coverage 核查 |
| Multi-Challenge | llm_stats | 领域信号 []，任务信号 ['planning']，命中词 ['benchmark', 'multi', 'planning']（query coverage 0.75）；进入人工 Coverage 核查 |
| Apex | llm_stats | 领域信号 []，任务信号 ['multi']，命中词 ['benchmark', 'multi', 'step']（query coverage 0.75）；进入人工 Coverage 核查 |
| IMOProof-Adv | llm_stats | 领域信号 []，任务信号 ['multi']，命中词 ['benchmark', 'multi', 'step']（query coverage 0.75）；进入人工 Coverage 核查 |

### Idea 13｜General Citation Correctness能力评测

- Domain：general　Status：watch　Score：58.0
- 目录候选：20 条　进入核查：12 条
- Verdict：**`topic_too_wide`**
- 建议：检索命中 12 条同领域基准，接近每查询取样上限，说明该 Idea 主题过宽、缺乏区分度。应先收窄任务定义，再谈 Gap。

| Benchmark | 目录源 | 判定依据 |
|---|---|---|
| CRPErelation | llm_stats | 领域信号 []，任务信号 ['reasoning']，命中词 ['benchmark', 'evaluation']（query coverage 1.00）；进入人工 Coverage 核查 |
| Internal Research Debugging Evaluation | llm_stats | 领域信号 []，任务信号 ['reasoning']，命中词 ['evaluation']（query coverage 0.50）；进入人工 Coverage 核查 |
| ScreenSpot Pro | llm_stats | 领域信号 []，任务信号 ['grounding', 'domain']，命中词 ['benchmark', 'grounding', 'professional', 'reasoning']（query coverage 0.50）；进入人工 Coverage 核查 |
| MCiteBench | opencompass_hub | 领域信号 []，任务信号 ['citation', 'reasoning']，命中词 ['benchmark', 'citation', 'evidence', 'reasoning']（query coverage 0.50）；进入人工 Coverage 核查 |
| FACTS Grounding | llm_stats | 领域信号 []，任务信号 ['grounding', 'reasoning']，命中词 ['benchmark', 'grounding', 'reasoning']（query coverage 0.38）；进入人工 Coverage 核查 |
| ProfBench | llm_stats | 领域信号 []，任务信号 ['domain']，命中词 ['domain', 'professional', 'reasoning']（query coverage 0.38）；进入人工 Coverage 核查 |
| RefSpatialBench | llm_stats | 领域信号 []，任务信号 ['grounding']，命中词 ['grounding', 'reasoning']（query coverage 0.25）；进入人工 Coverage 核查 |
| RefCOCO-avg | llm_stats | 领域信号 []，任务信号 ['grounding']，命中词 ['grounding', 'reasoning']（query coverage 0.25）；进入人工 Coverage 核查 |
| OSWorld-G | llm_stats | 领域信号 []，任务信号 ['grounding']，命中词 ['grounding']（query coverage 0.12）；进入人工 Coverage 核查 |
| ScreenSpot | llm_stats | 领域信号 []，任务信号 ['grounding']，命中词 ['benchmark', 'grounding', 'reasoning']（query coverage 0.38）；进入人工 Coverage 核查 |
| OpenTuringBench | opencompass_hub | 领域信号 []，任务信号 ['attribution']，命中词 ['attribution', 'benchmark']（query coverage 0.25）；进入人工 Coverage 核查 |
| RefCOCOg | llm_stats | 领域信号 []，任务信号 ['grounding']，命中词 ['benchmark', 'grounding']（query coverage 0.25）；进入人工 Coverage 核查 |

### Idea 5｜Scientific Domain Expertise能力评测

- Domain：scientific　Status：watch　Score：55.0
- 目录候选：20 条　进入核查：10 条
- Verdict：**`topic_too_wide`**
- 建议：检索命中 10 条同领域基准，接近每查询取样上限，说明该 Idea 主题过宽、缺乏区分度。应先收窄任务定义，再谈 Gap。

| Benchmark | 目录源 | 判定依据 |
|---|---|---|
| FrontierScience Research | llm_stats | 领域信号 ['scientific', 'science', 'research']，任务信号 ['expert']，命中词 ['benchmark', 'research', 'science', 'scientific']（query coverage 0.80）；进入人工 Coverage 核查 |
| SGI-Bench | opencompass_hub | 领域信号 ['scientific', 'science', 'research', '科学']，任务信号 ['expert']，命中词 ['benchmark', 'research', 'science', 'scientific']（query coverage 0.80）；进入人工 Coverage 核查 |
| Frontier Science | llm_stats | 领域信号 ['scientific', 'science']，任务信号 ['expert']，命中词 ['benchmark', 'science', 'scientific']（query coverage 0.60）；进入人工 Coverage 核查 |
| MedBench | opencompass_hub | 领域信号 ['scientific', 'science', '科学']，任务信号 ['knowledge']，命中词 ['evaluation', 'science', 'scientific']（query coverage 0.60）；进入人工 Coverage 核查 |
| ChemBench | opencompass_hub | 领域信号 ['scientific', 'science', '科学']，任务信号 ['knowledge']，命中词 ['benchmark', 'evaluation', 'science', 'scientific']（query coverage 0.80）；进入人工 Coverage 核查 |
| SWE-bench Science | model_reports | 领域信号 ['scientific', 'science']，任务信号 ['expert']，命中词 ['benchmark', 'domain', 'expert', 'knowledge', 'science', 'scientific']（query coverage 0.67）；进入人工 Coverage 核查 |
| CritPt | model_reports | 领域信号 ['science', 'research']，任务信号 ['expert']，命中词 ['expert', 'research', 'science']（query coverage 0.33）；进入人工 Coverage 核查 |
| MedBrowseComp | opencompass_hub | 领域信号 ['scientific', 'science', '科学']，任务信号 ['knowledge']，命中词 ['benchmark', 'domain', 'knowledge', 'science', 'scientific']（query coverage 0.56）；进入人工 Coverage 核查 |
| BixBench | llm_stats | 领域信号 ['scientific', 'science']，任务信号 ['knowledge']，命中词 ['benchmark', 'domain', 'knowledge', 'science', 'scientific']（query coverage 0.56）；进入人工 Coverage 核查 |
| FrontierScience Olympiad | llm_stats | 领域信号 ['scientific', 'science']，任务信号 ['expert']，命中词 ['benchmark', 'expert', 'science', 'scientific']（query coverage 0.44）；进入人工 Coverage 核查 |

### Idea 17｜Medical Domain Reasoning能力评测

- Domain：medical　Status：rejected　Score：54.0
- 目录候选：20 条　进入核查：10 条
- Verdict：**`topic_too_wide`**
- 建议：检索命中 10 条同领域基准，接近每查询取样上限，说明该 Idea 主题过宽、缺乏区分度。应先收窄任务定义，再谈 Gap。

| Benchmark | 目录源 | 判定依据 |
|---|---|---|
| CRPErelation | llm_stats | 领域信号 ['medical', 'clinical', 'health']，任务信号 ['reasoning']，命中词 ['benchmark', 'clinical', 'evaluation', 'medical']（query coverage 0.80）；进入人工 Coverage 核查 |
| MedBookVQA | opencompass_hub | 领域信号 ['medical', 'clinical', '临床']，任务信号 ['reasoning']，命中词 ['benchmark', 'clinical', 'medical']（query coverage 0.60）；进入人工 Coverage 核查 |
| MedBrowseComp | opencompass_hub | 领域信号 ['medical', 'clinical']，任务信号 ['domain']，命中词 ['benchmark', 'clinical', 'medical']（query coverage 0.60）；进入人工 Coverage 核查 |
| MedAgents-Bench | opencompass_hub | 领域信号 ['medical', 'clinical', '临床']，任务信号 ['reasoning']，命中词 ['clinical', 'evaluation', 'medical']（query coverage 0.60）；进入人工 Coverage 核查 |
| MedXpertQA | llm_stats | 领域信号 ['medical', 'clinical', 'health']，任务信号 ['reasoning']，命中词 ['benchmark', 'clinical', 'medical']（query coverage 0.60）；进入人工 Coverage 核查 |
| ER-Reason | opencompass_hub | 领域信号 ['medical', 'clinical', '临床']，任务信号 ['reasoning']，命中词 ['benchmark', 'clinical', 'medical']（query coverage 0.60）；进入人工 Coverage 核查 |
| MedCalc-Bench | opencompass_hub | 领域信号 ['medical']，任务信号 ['reasoning']，命中词 ['evaluation', 'health', 'medical']（query coverage 0.60）；进入人工 Coverage 核查 |
| HealthBench Professional | model_reports | 领域信号 ['health']，任务信号 ['professional']，命中词 ['health']（query coverage 0.20）；进入人工 Coverage 核查 |
| MedSafetyBench | opencompass_hub | 领域信号 ['medical', '医疗']，任务信号 ['reasoning', 'safety']，命中词 ['harmful', 'medical', 'reasoning', 'safety']（query coverage 0.40）；进入人工 Coverage 核查 |
| FalseReject | opencompass_hub | 无 medical 领域标注，但任务信号强命中 ['reasoning', 'safety']；疑为跨领域通用基准，需人工核查其数据来源是否覆盖目标任务 |

### Idea 14｜Agent Citation Correctness能力评测

- Domain：agent　Status：watch　Score：54.0
- 目录候选：20 条　进入核查：1 条
- Verdict：**`needs_manual_coverage_analysis`**
- 建议：有 1 条候选需要人工核查原始 Paper/Repo 的 task definition 与 evaluation protocol，才能判定是否真的覆盖目标任务。

| Benchmark | 目录源 | 判定依据 |
|---|---|---|
| OSWorld-G | llm_stats | 领域信号 ['agent']，任务信号 ['grounding']，命中词 ['grounding']（query coverage 0.14）；进入人工 Coverage 核查 |

### Idea 3｜患者特异性用药安全决策

- Domain：medical　Status：watch　Score：52.0
- 目录候选：20 条　进入核查：5 条
- Verdict：**`needs_manual_coverage_analysis`**
- 建议：有 5 条候选需要人工核查原始 Paper/Repo 的 task definition 与 evaluation protocol，才能判定是否真的覆盖目标任务。

| Benchmark | 目录源 | 判定依据 |
|---|---|---|
| IS-Bench | opencompass_hub | 无 medical 领域标注，但任务信号强命中 ['safety', 'interaction']；疑为跨领域通用基准，需人工核查其数据来源是否覆盖目标任务 |
| MedChemBench (Internal) | llm_stats | 领域信号 ['health']，任务信号 ['drug']，命中词 ['drug', 'evaluation']（query coverage 0.25）；进入人工 Coverage 核查 |
| WildClawBench | opencompass_hub | 无 medical 领域标注，但任务信号强命中 ['safety', 'interaction']；疑为跨领域通用基准，需人工核查其数据来源是否覆盖目标任务 |
| BioLP-Bench | llm_stats | 领域信号 ['health']，任务信号 ['safety']，命中词 ['evaluation', 'safety']（query coverage 0.25）；进入人工 Coverage 核查 |
| MedSafetyBench | opencompass_hub | 领域信号 ['medical', '医疗']，任务信号 ['safety']，命中词 ['harmful', 'medical', 'safety']（query coverage 0.27）；进入人工 Coverage 核查 |

### Idea 21｜Scientific Tool Use能力评测

- Domain：scientific　Status：watch　Score：51.0
- 目录候选：20 条　进入核查：10 条
- Verdict：**`topic_too_wide`**
- 建议：检索命中 10 条同领域基准，接近每查询取样上限，说明该 Idea 主题过宽、缺乏区分度。应先收窄任务定义，再谈 Gap。

| Benchmark | 目录源 | 判定依据 |
|---|---|---|
| FrontierScience Research | llm_stats | 领域信号 ['scientific', 'science', 'research']，任务信号 ['multi']，命中词 ['benchmark', 'research', 'science', 'scientific']（query coverage 0.80）；进入人工 Coverage 核查 |
| SGI-Bench | opencompass_hub | 领域信号 ['scientific', 'science', 'research', '科学']，任务信号 ['multi']，命中词 ['benchmark', 'research', 'science', 'scientific']（query coverage 0.80）；进入人工 Coverage 核查 |
| Frontier Science | llm_stats | 领域信号 ['scientific', 'science']，任务信号 ['multi']，命中词 ['benchmark', 'science', 'scientific']（query coverage 0.60）；进入人工 Coverage 核查 |
| RDB2G-Bench | opencompass_hub | 领域信号 ['scientific', 'science', '科学']，任务信号 ['multi']，命中词 ['evaluation', 'science', 'scientific']（query coverage 0.60）；进入人工 Coverage 核查 |
| API-Bank | llm_stats | 无 scientific 领域标注，但任务信号强命中 ['planning', 'tool']；疑为跨领域通用基准，需人工核查其数据来源是否覆盖目标任务 |
| BFCL_v3_MultiTurn | llm_stats | 无 scientific 领域标注，但任务信号强命中 ['multi', 'use']；疑为跨领域通用基准，需人工核查其数据来源是否覆盖目标任务 |
| BFCL | llm_stats | 无 scientific 领域标注，但任务信号强命中 ['multi', 'use']；疑为跨领域通用基准，需人工核查其数据来源是否覆盖目标任务 |
| t2-bench | llm_stats | 无 scientific 领域标注，但任务信号强命中 ['planning', 'tool']；疑为跨领域通用基准，需人工核查其数据来源是否覆盖目标任务 |
| MCP-Universe | llm_stats | 无 scientific 领域标注，但任务信号强命中 ['planning', 'tool']；疑为跨领域通用基准，需人工核查其数据来源是否覆盖目标任务 |
| AutomationBench | llm_stats | 无 scientific 领域标注，但任务信号强命中 ['multi', 'tool']；疑为跨领域通用基准，需人工核查其数据来源是否覆盖目标任务 |

### Idea 22｜General Version Awareness能力评测

- Domain：general　Status：watch　Score：51.0
- 目录候选：20 条　进入核查：13 条
- Verdict：**`topic_too_wide`**
- 建议：检索命中 13 条同领域基准，接近每查询取样上限，说明该 Idea 主题过宽、缺乏区分度。应先收窄任务定义，再谈 Gap。

| Benchmark | 目录源 | 判定依据 |
|---|---|---|
| lm-evaluation-harness | opencompass_hub | 领域信号 []，任务信号 ['knowledge']，命中词 ['benchmark', 'evaluation']（query coverage 1.00）；进入人工 Coverage 核查 |
| CRPErelation | llm_stats | 领域信号 []，任务信号 ['knowledge']，命中词 ['benchmark', 'evaluation']（query coverage 1.00）；进入人工 Coverage 核查 |
| UHGEval | opencompass_hub | 领域信号 []，任务信号 ['knowledge']，命中词 ['benchmark', 'evaluation']（query coverage 1.00）；进入人工 Coverage 核查 |
| MedBench | opencompass_hub | 领域信号 []，任务信号 ['knowledge']，命中词 ['knowledge', 'update']（query coverage 0.40）；进入人工 Coverage 核查 |
| Fin-Eva | opencompass_hub | 领域信号 []，任务信号 ['version']，命中词 ['benchmark', 'knowledge', 'version']（query coverage 0.60）；进入人工 Coverage 核查 |
| TVBench | llm_stats | 领域信号 []，任务信号 ['temporal']，命中词 ['benchmark', 'temporal']（query coverage 0.40）；进入人工 Coverage 核查 |
| KMMLU-Redux | opencompass_hub | 领域信号 []，任务信号 ['version']，命中词 ['knowledge', 'version']（query coverage 0.40）；进入人工 Coverage 核查 |
| MBPP ++ base version | llm_stats | 领域信号 []，任务信号 ['version']，命中词 ['benchmark', 'version']（query coverage 0.40）；进入人工 Coverage 核查 |
| TempCompass | llm_stats | 领域信号 []，任务信号 ['temporal']，命中词 ['benchmark', 'temporal']（query coverage 0.40）；进入人工 Coverage 核查 |
| CharadesSTA | llm_stats | 领域信号 []，任务信号 ['temporal']，命中词 ['benchmark', 'temporal']（query coverage 0.40）；进入人工 Coverage 核查 |
| TOMATO | llm_stats | 领域信号 []，任务信号 ['temporal']，命中词 ['temporal']（query coverage 0.20）；进入人工 Coverage 核查 |
| V-STaR | opencompass_hub | 领域信号 []，任务信号 ['temporal']，命中词 ['benchmark', 'temporal']（query coverage 0.40）；进入人工 Coverage 核查 |
| LongVALE | opencompass_hub | 领域信号 []，任务信号 ['temporal']，命中词 ['benchmark', 'temporal']（query coverage 0.40）；进入人工 Coverage 核查 |

### Idea 23｜Scientific Planning能力评测

- Domain：scientific　Status：watch　Score：51.0
- 目录候选：20 条　进入核查：10 条
- Verdict：**`topic_too_wide`**
- 建议：检索命中 10 条同领域基准，接近每查询取样上限，说明该 Idea 主题过宽、缺乏区分度。应先收窄任务定义，再谈 Gap。

| Benchmark | 目录源 | 判定依据 |
|---|---|---|
| FrontierScience Research | llm_stats | 领域信号 ['scientific', 'science', 'research']，任务信号 ['multi']，命中词 ['benchmark', 'research', 'science', 'scientific']（query coverage 0.80）；进入人工 Coverage 核查 |
| SGI-Bench | opencompass_hub | 领域信号 ['scientific', 'science', 'research', '科学']，任务信号 ['multi']，命中词 ['benchmark', 'research', 'science', 'scientific']（query coverage 0.80）；进入人工 Coverage 核查 |
| Frontier Science | llm_stats | 领域信号 ['scientific', 'science']，任务信号 ['multi']，命中词 ['benchmark', 'science', 'scientific']（query coverage 0.60）；进入人工 Coverage 核查 |
| RDB2G-Bench | opencompass_hub | 领域信号 ['scientific', 'science', '科学']，任务信号 ['multi']，命中词 ['evaluation', 'science', 'scientific']（query coverage 0.60）；进入人工 Coverage 核查 |
| FrontierScience Olympiad | llm_stats | 领域信号 ['scientific', 'science']，任务信号 ['multi']，命中词 ['benchmark', 'multi', 'science', 'scientific', 'step']（query coverage 0.71）；进入人工 Coverage 核查 |
| Job Bench | llm_stats | 领域信号 ['research']，任务信号 ['planning']，命中词 ['multi', 'planning', 'research', 'step']（query coverage 0.57）；进入人工 Coverage 核查 |
| BixBench | llm_stats | 领域信号 ['scientific', 'science']，任务信号 ['multi']，命中词 ['benchmark', 'multi', 'science', 'scientific', 'step']（query coverage 0.71）；进入人工 Coverage 核查 |
| PaperBench | llm_stats | 领域信号 ['scientific', 'research']，任务信号 ['multi']，命中词 ['benchmark', 'multi', 'research', 'scientific', 'step']（query coverage 0.71）；进入人工 Coverage 核查 |
| FrontierCS | llm_stats | 领域信号 ['science']，任务信号 ['multi']，命中词 ['benchmark', 'multi', 'science', 'step']（query coverage 0.57）；进入人工 Coverage 核查 |
| MedAgents-Bench | opencompass_hub | 领域信号 ['scientific', 'science', '科学']，任务信号 ['multi']，命中词 ['multi', 'science', 'scientific', 'step']（query coverage 0.57）；进入人工 Coverage 核查 |

### Idea 7｜Agent Tool Use能力评测

- Domain：agent　Status：rejected　Score：45.0
- 目录候选：20 条　进入核查：6 条
- Verdict：**`needs_manual_coverage_analysis`**
- 建议：有 6 条候选需要人工核查原始 Paper/Repo 的 task definition 与 evaluation protocol，才能判定是否真的覆盖目标任务。

| Benchmark | 目录源 | 判定依据 |
|---|---|---|
| Agents' Last Exam | model_reports | 领域信号 ['agent', 'agentic']，任务信号 ['tool']，命中词 ['agent', 'agentic', 'benchmark']（query coverage 0.75）；进入人工 Coverage 核查 |
| Search and Function-Calling | llm_stats | 领域信号 ['agent', 'agentic']，任务信号 ['tool']，命中词 ['agentic', 'benchmark', 'calling', 'function', 'tool', 'use']（query coverage 0.75）；进入人工 Coverage 核查 |
| BFCL_v3_MultiTurn | llm_stats | 领域信号 ['agent', 'agentic']，任务信号 ['use']，命中词 ['agentic', 'api', 'benchmark', 'calling', 'function', 'tool', 'use']（query coverage 0.88）；进入人工 Coverage 核查 |
| Connectors | llm_stats | 领域信号 ['agent', 'agentic']，任务信号 ['tool']，命中词 ['agentic', 'benchmark', 'calling', 'tool', 'use']（query coverage 0.62）；进入人工 Coverage 核查 |
| τ²-Bench Telecom | artificial_analysis | 领域信号 ['agent', 'agentic']，任务信号 ['tool']，命中词 ['agentic', 'tool', 'use']（query coverage 0.38）；进入人工 Coverage 核查 |
| t2-bench | llm_stats | 领域信号 ['agent', 'agentic']，任务信号 ['tool']，命中词 ['agentic', 'benchmark', 'calling', 'tool', 'use']（query coverage 0.62）；进入人工 Coverage 核查 |

### Idea 10｜Scientific Safety能力评测

- Domain：scientific　Status：rejected　Score：45.0
- 目录候选：20 条　进入核查：2 条
- Verdict：**`needs_manual_coverage_analysis`**
- 建议：有 2 条候选需要人工核查原始 Paper/Repo 的 task definition 与 evaluation protocol，才能判定是否真的覆盖目标任务。

| Benchmark | 目录源 | 判定依据 |
|---|---|---|
| MedSafetyBench | opencompass_hub | 领域信号 ['scientific', 'science', '科学']，任务信号 ['safety']，命中词 ['harmful', 'safety', 'science', 'scientific']（query coverage 0.57）；进入人工 Coverage 核查 |
| MTCMB | opencompass_hub | 领域信号 ['scientific', 'science', '科学']，任务信号 ['safety']，命中词 ['benchmark', 'safety', 'science', 'scientific']（query coverage 0.57）；进入人工 Coverage 核查 |

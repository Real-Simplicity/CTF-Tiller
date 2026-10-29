# CTF-Agent 开源项目深度调研报告

> 调研日期：2026-10-29。方法：三轮并行网络调研（GitHub API / arXiv 论文全文 / 项目官网与博客交叉验证），覆盖约 35 个开源项目与十余篇论文。Star 数与成绩为调研当日抓取值，仅供参考。

---

## 一、项目总表

### 1.1 学术研究型解题 Agent（Benchmark 驱动）

| 项目 | 机构/背景 | 架构核心 | 代表成绩 | 状态 |
|---|---|---|---|---|
| [EnIGMA](https://github.com/SWE-agent/SWE-agent/tree/v0.7)（并入 SWE-agent v0.7，[论文](https://arxiv.org/abs/2409.16165)） | Princeton + NYU + Stanford + 特拉维夫大学（注意：非 UC Berkeley） | 单 agent + **IAT 交互式工具**（GDB 调试接口、pwntools 远程连接，可扩展到任意 REPL 工具）+ LM 摘要器压缩长输出 | NYU CTF 13.5%、Cybench 20%、InterCode-CTF 72%（GPT-4 Turbo）、HackTheBox 26%（Claude 3.5 Sonnet） | 活跃（依托 SWE-agent，20.7k★） |
| [nyuctf_agents / D-CIPHER](https://github.com/NYU-LLM-CTF/nyuctf_agents)（[论文](https://arxiv.org/abs/2502.10931)） | NYU Tandon + NYU AD + IIT Kanpur | **三角色多 agent**：Auto-prompter（先探索环境再生成定制提示）→ Planner（唯一持提交权）→ 异构 Executor（每次委派新建独立上下文，配 Ghidra 反编译等工具） | NYU CTF 19%、Cybench 22.5%、HackTheBox 44%（Claude 3.5 Sonnet） | 活跃，174★ |
| [CRAKEN](https://github.com/NYU-LLM-CTF/nyuctf_agents_craken)（[论文](https://arxiv.org/abs/2505.17107)） | NYU（D-CIPHER 同团队） | D-CIPHER 之上叠加**知识检索层**：Milvus 向量 RAG + Neo4j Graph-RAG + Self-RAG 迭代自反思检索，知识源为人类 CTF writeups | NYU CTF **22.0%**（当时 SOTA，$0.86/题）；MITRE ATT&CK 技术覆盖 +25~30% | 停更（集成进 nyuctf_agents 中），45★ |
| [HackSynth](https://github.com/aielte-research/HackSynth)（[论文](https://arxiv.org/abs/2412.01778)） | 匈牙利罗兰大学 ELTE | **Planner + Summarizer 双模块**：Planner 每步只出一条 bash，Summarizer 把输出增量合并成滚动摘要替代原始历史；系统研究 temperature/top-p 等创造力参数 | picoCTF 34.2%、OverTheWire 40%（GPT-4o，自建 200 题基准） | 停更（2025-06），319★ |
| CTFAgent（[论文](https://doi.org/10.1016/j.jisa.2025.104305)，**未开源**） | JISA 期刊 2025 | plan-and-execute + **状态化任务树**（长程计划独立于上下文窗口）+ 两阶段 RAG（writeup 洞察库） | 论文自述 InterCode-CTF 相对基线 +80%；第三方复测：InterCode crypto 子集 83%、NYU-CTF 子集 40% | 未开源 |
| [Hacking CTFs with Plain Agents](https://arxiv.org/abs/2412.02776) | 学术（2024） | **纯 ReAct 裸 agent**，无任何花哨架构，证明 scaffold 不是瓶颈 | InterCode-CTF 95%（饱和） | 论文 |
| [STRIATUM-CTF](https://arxiv.org/html/2603.22577v1) | 学术（2026-03） | **MCP 协议**驱动的通用 CTF Agent，工具抽象显著降低幻觉 | 真实 CTF 赛事中击败 21 支人类战队夺冠 | 论文（待核实开源） |

### 1.2 训练数据与环境

| 项目 | 机构/背景 | 架构核心 | 代表成绩 | 状态 |
|---|---|---|---|---|
| [CTF-Dojo](https://github.com/amazon-science/CTF-Dojo)（[论文](https://arxiv.org/abs/2508.18370)） | Amazon Science | **658 道全功能 Docker 化 CTF** + CTF-Forge 流水线（任意公开 CTF 工件自动转成可运行环境）+ **执行验证轨迹**（flag 校验过滤）做 SFT | 仅 486 条轨迹训练 32B 开源模型，三大外部基准最高 **+11.6%**，达 31.9% Pass@1 | 停更（2026-01），74★，CC-BY-NC |
| [InterCode-CTF](https://github.com/princeton-nlp/intercode)（[论文](https://arxiv.org/abs/2306.14898)） | Princeton NLP | 把 CTF 形式化为 **Docker + bash 执行反馈环境**（100 道 picoCTF），flag 即客观奖励，可评测也可做 RL | 后续工作刷至 95%（已饱和）；ICARuS 发现随机化重测后高分模型跌破 60%（数据污染） | 停更（2024-05），257★，NeurIPS 2023 |

### 1.3 工程/竞赛型 Agent

| 项目 | 机构/背景 | 架构核心 | 代表成绩 | 状态 |
|---|---|---|---|---|
| [verialabs/ctf-agent](https://github.com/verialabs/ctf-agent) | Veria Labs（成员来自美国 CTF #1 战队） | **Coordinator + 多模型并行竞速 Swarm**：轮询 CTFd 自动拉题，每题 5 个 solver（Claude Opus/GPT-5.x 混编）同跑，先拿 flag 者胜；跨 solver 消息总线共享发现；全套预装工具的独立 Docker 沙箱 | **BSidesSF 2026 CTF 52/52 全解、第一名**（首个公开拿下真实赛事冠军的开源 agent） | 封存（2026-03 发布后未再更新），890★ |
| [ctf-skills](https://github.com/ljagiello/ctf-skills) | 个人（lwj） | 给 **Claude Code 用的 CTF 全领域 Agent Skills 包**（web/pwn/crypto/reverse/forensics/OSINT/malware），可组合、由 solve-challenge 调度 | —（社区广泛使用） | 活跃，3557★ |
| [LuaN1aoAgent](https://github.com/SanMuzZzZz/LuaN1aoAgent) | 广州大学 | **图认知推理**驱动的全自动渗透/CTF agent | 腾讯 TSec 黑客松 XBOW 评测通过率 >90% | 活跃，1450★ |
| [BoxPwnr](https://github.com/0ca/BoxPwnr) | 个人（Ondrej） | **15+ 攻防平台统一评测框架**（HackTheBox/TryHackMe/PortSwigger/picoCTF/Cybench/XBOW 即插即用），浏览器 + 终端双 agent | — | 活跃，467★ |
| [tinyctfer](https://github.com/chainreactors/tinyctfer) | chainreactors（国内） | "**微型意图运行时 + 元工具（meta-tool）**"极简哲学的 CTF Agent | 腾讯 TSec 黑客松第 4 名 | 活跃，173★ |
| [BreachWeave](https://github.com/m-sec-org/BreachWeave) | m-sec-org | Manager / Observer / Solver 多角色智能渗透 agent（基于 pi-mono SDK） | TSec 黑客松第二届决赛一等奖（613 队参赛） | 活跃，708★ |
| [BUUCTF_Agent](https://github.com/MuWinds/BUUCTF_Agent) | 个人（MuWinds，国内） | 对接 BUUCTF 平台；think-execute-analyze 循环 + 按 taxonomy 注入的 **Skills 知识库**（SKILL.md）+ MCP 适配器 + checkpoint；设计稿含 ToolSmith 动态造工具机制（未落地） | 未公布系统化解题率 | **作者已声明停止维护**，268★ |
| [SmartData-Polito/CTF_agent](https://github.com/SmartData-Polito/CTF_agent) | 都灵理工大学 SmartData | 多策略框架：**Claude Code 通用 CLI vs 自建 LangGraph agent 对照**；recon → planner → executor（工具调用预过滤）→ LLM-judge 流水线 | 基于 X-BOW 靶场，成绩未公开 | 停更，8★ |
| [hvbhanot/CTF-Agent](https://github.com/hvbhanot/CTF-Agent) | 个人 | 完全本地化：Ollama + Orchestrator→Planner→Specialist→Verifier 循环 + 持久草稿本记忆，面向初中级题 | — | 小项目，2★ |
| [marvang/ctf-agent](https://github.com/marvang/ctf-agent) | 个人 | 渗透 + CTF 双用途，CHAP 长任务智能上下文交接机制 | — | 小项目，4★ |
| [LLM_CTF](https://github.com/NickNameInvalid/LLM_CTF) | 学术（arXiv 2402.11814） | 早期全自动 CTF workflow 实证研究，已并入 NYU llm_ctf_automation | — | 归档，66★ |
| [Cybersleuth_Forensic_Agent](https://github.com/SmartData-Polito/Cybersleuth_Forensic_Agent) | 都灵理工大学 | LangGraph 自主分析 .pcap 的取证专项 agent（CTF forensics 专项化路线） | — | 活跃 |
| [HexStrikeAI](https://github.com/HexStrikeAI/HexStrikeAI) | 社区 | MCP 服务器封装 150+ 攻防工具，给 Claude/GPT agent 当"军火库" | — | 活跃 |
| [agentctf](https://github.com/agentbeats/agentctf) | UC Berkeley RDI | AgentCTF x AgentXploit 比赛官方库：让 AI agent 以 CTF 形式攻击真实 CVE 与其他 AI agent（AAA 评测范式） | 比赛基础设施 | 活跃，9★ |

### 1.4 基准与评测科学

| 项目 | 机构/背景 | 核心特色 | 状态 |
|---|---|---|---|
| [NYU CTF Bench](https://github.com/NYU-LLM-CTF/NYU_CTF_Bench)（NeurIPS 2024 D&B） | NYU | 200 道 CSAW 真题 + 55 道 dev 题，6 类别全覆盖，pip 即用；本领域最常用学术基准 | 185★ |
| [Cybench](https://github.com/andyzorigin/cybench)（Stanford，非 Cornell） | Stanford（Boneh/Liang/Ho 组） | 40 道职业级真题；**子任务分解**产生梯度化分数；**人类首解时间（FST）**做客观难度标定 | 持续活跃维护，349★ |
| [xbow validation-benchmarks](https://github.com/xbow-engineering/validation-benchmarks) | XBOW（商业公司开源） | 104 个 Web 漏洞挑战，曾是事实基准；**官方已宣布饱和**（业界 ~100% 通过率、题目被训进模型） | 742★，仅存档 |
| [CTFTiny + CTFJudge](https://github.com/NYU-LLM-CTF/CTFTiny) | NYU | 237 题微型基准（每题带认知复杂度标签）+ LLM-as-Judge 判分器 | 21★，AAAI 2026 |
| [CTFusion](https://github.com/kaist-hacking/CTFusion) | KAIST | **真实 CTF 赛事流式评测**（边打 live 比赛边评测，DILE 范式） | ICML 2026 Workshop |
| [CTF-ABACUS](https://arxiv.org/abs/2608.26237) | NYU CCS | **trace 级审计框架**：逐 token 污点分析量化每步对拿 flag 的真实贡献；发现仅 **62–87%** 的"成功"是真漏洞利用，其余是捷径/意外成功 | Apache 2.0 开源 |
| Evolve-CTF（[论文](https://www.doc.ic.ac.uk/~afd/papers/2026/Preprint-CTFs.pdf)） | 帝国理工 | 从种子题自动生成 CTF 变体族，抗污染评测 | 论文 |
| CSAW Agentic Automated CTF（[赛事](https://csaw.io/competition/agentic-automated-ctf)） | NYU/CSAW | 用 NYU CTF Lite（50 题）办的 agent CTF 赛道，须提交完整日志与 writeup | 2025 举办，2026 美加赛区未续 |

### 1.5 相邻方向（渗透测试 Agent，简要）

| 项目 | 特色 |
|---|---|
| [PentestGPT](https://github.com/GreyDGL/PentestGPT)（USENIX Sec 2024） | 交互式引导人类做渗透的开创者，本领域被引最多 |
| [pentagi](https://github.com/vxcontrol/pentagi) | 全自主多 agent 渗透系统，自托管 + Web UI + 沙箱，32.6k★ |
| [hackingBuddyGPT](https://github.com/ipa-lab/hackingBuddyGPT)（TU Wien） | 研究向框架，"50 行代码构建 LLM 渗透实验" |
| [0xSteph/pentest-ai-agents](https://github.com/0xSteph/pentest-ai-agents) | 50 个 Claude Code 攻防子 agent 集合 |
| XBOW（闭源商业） | 2025 年首个登顶 HackerOne 美国榜的 AI 自主渗透系统；其开源基准成为社区事实标准 |
| DARPA AIxCC（比赛） | 2 千万美元的漏洞发现/修补 CRS 大赛，决赛系统全部按要求开源——"真漏洞"方向的政府级推动力 |

### 1.6 反方向：把 LLM 当靶机（不是解题，是攻防 LLM）

| 项目 | 特色 |
|---|---|
| [BishopFox/local-llm-ctf](https://github.com/BishopFox/local-llm-ctf) | Go + Ollama 的本地 LLM 安全靶场：特权/隔离模型分进程架构，实测 mistral 攻击模型可 100% 绕过四道关卡偷出秘密 |
| [mubix/ai-ctf](https://github.com/mubix/ai-ctf) | 本地 AI CTF 平台：提示注入、工具滥用、OSINT 六个聊天机器人靶标 |

---

## 二、综述：CTF-Agent 的方法、成果与开放问题

CTF（Capture The Flag）夺旗赛是进攻性安全能力的标准试验场：题目覆盖 Web、二进制漏洞利用（pwn）、逆向、密码学、取证、隐写等类别，flag 提交即客观判分。2023 年以来，"用 LLM Agent 自动解 CTF"从概念验证迅速演化为一个有基准、有训练方法、有真实赛事冠军的研究方向。以下基于约 35 个开源项目与十余篇论文做综述。

### 2.1 当前项目使用的方法

**（1）Agent-Computer Interface：给模型可用的手**
EnIGMA 的核心贡献是 IAT（Interactive Agent Tools）：把 GDB、pwntools 远程连接这类**交互式 REPL 工具**封装成 agent 可调用的接口，让模型能单步调试二进制、与远程服务多轮交互——这在之前的标准 agent 沙箱里做不到。消融显示其 LM 摘要器同样关键（去掉后 Cybench 成绩从 20% 跌到 10%）。Cybench 则对比了 structured-bash、伪终端（tty 键级交互）、web search 等不同脚手架。后续趋势是 MCP 协议化（STRIATUM-CTF、HexStrikeAI、BUUCTF_Agent 的 MCP 适配器），把工具层变成可插拔标准。

**（2）多 Agent 角色分工与上下文工程**
D-CIPHER 确立了"Auto-prompter → Planner → 异构 Executor"三角色范式：Planner 只做规划与提交（刻意不给解题工具），每个子任务派生独立上下文的 Executor，完成后只回传摘要——用组织结构天然解决了上下文爆炸。CTFAgent 用独立于上下文窗口的状态化任务树保存长程计划；HackSynth 用 Planner/Summarizer 双模块以滚动摘要替代原始历史；BUUCTF_Agent 设计了 checkpoint 与 ToolSmith 动态造工具机制。

**（3）知识增强：writeup 是最重要的资产**
CRAKEN 把人类选手的解题 writeups 做成向量库（Milvus）+ 知识图谱（Neo4j），配 Self-RAG 式迭代自反思检索，把 NYU CTF 推到 22%。CTFAgent 用两阶段 RAG 提取"精炼洞察"。结论一致：**强模型从知识注入中获益更大**。另一条路线是 BUUCTF_Agent / ctf-skills 的领域 Skills 包（按题目类别注入 SKILL.md 领域知识）。

**（4）推理与提示策略**
Cybench 的子任务分解（难题拆成中间目标，产出梯度化分数）、HackSynth 的创造力参数研究（temperature=1、top-p=0.9 最优，采样带来 +38%；提示链反而 -5%）、EnIGMA/D-CIPHER 的 few-shot 演示与反思提示。但"Plain Agents"论文给出了反直觉结论：裸 ReAct agent 就能在 InterCode-CTF 上拿 95%——**脚手架创新的边际价值在递减，模型能力才是主变量**。

**（5）运行时策略：多模型并行竞速**
verialabs/ctf-agent 把"哪个模型强"变成运行时筛选问题：每题 5 个 solver（不同模型/不同推理力度）并行竞速，Coordinator 读各 solver 轨迹注入技术指导，跨 solver 共享线索，最终在真实比赛 BSidesSF 2026 拿下 52/52 全解冠军。这代表了从"单一最优 agent"到"工程化组合"的转向。

**（6）复用通用编码 Agent**
一条明显的新路线是不自研框架，直接把 Claude Code 等通用编码 agent 当 solver：ctf-skills（3557★）提供 CTF 技能包，SmartData-Polito 做了"Claude Code vs 自建 LangGraph"对照实验，"A Second Look"论文则用 claude-code 作强基线重新审视既有论文的贡献。

**（7）训练：执行验证轨迹**
CTF-Dojo（Amazon）代表数据派：CTF-Forge 把任意公开 CTF 工件自动转成可运行 Docker 环境（658 题），用 EnIGMA+ 采集**经 flag 校验的执行验证轨迹**，仅 486 条轨迹 SFT 就让 32B 开源模型提升 11.6%。姊妹工作 HackSynth-GRPO 探索 RL。这一派解决的是"评测题不够、训练数据更少"的瓶颈。

**（8）评测科学：从"是否拿到 flag"到"怎么拿到的"**
难度标定（Cybench 的 FST 人类首解时间）、梯度化打分（子任务分数）、LLM 判分（CTFJudge）、真实赛事流式评测（CTFusion）、变体生成抗污染（Evolve-CTF、D-CIPHER 的 CSAW 动态变体）、以及 CTF-ABACUS 的 trace 级污点审计——评测方法论本身已成一个子研究方向。

### 2.2 已经较好解决的问题

1. **从"几乎不能解"到"稳定解中等难度题"**：NYU CTF 上从 2024 年 baseline 4% 提升到 22%（CRAKEN）；InterCode-CTF 被刷到 95% 饱和；XBOW 基准被刷穿；真实中等难度赛事可全解夺冠（verialabs）。
2. **交互式环境操作**：GDB 单步调试、nc/pwntools 远程交互这类此前 agent 完全无法使用的工具，已通过 IAT/伪终端/MCP 标准化解决。
3. **上下文管理**：滚动摘要、Executor 摘要回传、任务树、checkpoint 等组合，使 agent 能在数十轮交互的长任务中不丢失状态。
4. **基准缺失**：从零到拥有 NYU CTF Bench（200 题）、Cybench（40 职业题）、InterCode-CTF、CTF-Dojo（658 题）等可复现开源基准，且有 pip/Docker 一键运行。
5. **知识复用**：writeups→RAG/GraphRAG→Skills 的路线已验证有效，知识注入可稳定带来 3 个百分点以上提升。
6. **小模型可用性**：执行验证轨迹训练让 32B 开源模型接近前沿专有系统水平（31.9% Pass@1）；本地 Ollama 方案（hvbhanot、BishopFox）证明低端部署可行。
7. **端到端参赛工程化**：自动拉题、并行竞速、自动提交、跨 solver 信息共享的全流程已打通。

### 2.3 尚未很好解决的问题

1. **高难度 pwn/rev 仍是深水区**：堆利用、内核利用、大型二进制逆向在所有基准上成功率都极低；Cybench 上最强模型 unguided 也只有 17.5%~20%，其按人类首解时间标定的难题几乎全军覆没。专攻 pwn 的 AutoPwn/PwnGPT 距通用可用尚远。
2. **分数≠能力：捷径与"意外成功"**：CTF-ABACUS 发现 62–87% 的"成功"才是真正按预期漏洞利用拿到 flag，其余靠捷径（如题目配置缺陷、目录遍历直接读 flag）；捷径轨迹交互更浅。**仅看提交结果的评分系统性高估了 agent 真实攻防能力。**
3. **基准饱和与数据污染**：InterCode-CTF（95%）、XBOW 基准（~100%，官方宣布停用）已饱和；picoCTF 等老题大量存在于训练语料，ICARuS 随机化重测后部分模型跌破 60%。现有基准的"区分度存量"正在快速耗尽，变体生成（Evolve-CTF）与 live 评测（CTFusion）才刚起步。
4. **幻觉与"自言自语"（soliloquizing）**：EnIGMA 量化发现 Claude 3.5 Sonnet 在 NYU CTF 上 48.4% 的步骤存在模型自造幻觉观察、绕过真实环境交互的现象；命令幻觉、工具误用在 weak 模型上更严重。这是 LLM 固有问题在安全场景的尖锐化。
5. **成本与效率**：SOTA 配置每题 $0.5–0.9 且依赖最强闭源模型；CRAKEN 的知识增强还伴随成本上升（+$0.34/题）。verialabs 式多模型竞速本质是用钱换时间。低成本高能力的开源方案仍落后。
6. **训练数据瓶颈**：执行验证轨迹虽有效，但 486 条的规模天花板明显；自动出题（CTF-Forge、Evolve-CTF、D-CIPHER 变体）生成的题目难度上限低，难以覆盖高阶利用链。RL（HackSynth-GRPO）只在窄域（crypto）初步验证。
7. **长程规划与跨题学习**：单题内 20–50 步的规划基本解决，但跨题目积累经验（"打一题强一题"）除了 writeup RAG 和 Skills 注入外没有根本方案；ToolSmith 式"边打边造工具"多停留在设计稿。真实红队场景需要的数小时级持久任务无人能稳定完成。
8. **可复现性危机（研究侧）**：基准本地搭建不一致、Docker 文件缺失、flag 泄漏（InterCode-CTF 泄漏率 14.1%）、论文间成绩口径不统一（D-CIPHER 19% vs 22% 消融口径），以及"裸 agent 强基线"对既有论文增量的质疑，都是活跃的争议点。
9. **安全与治理**：全自主攻击能力的开源即武器化风险——CTF 技术栈与真实渗透仅一步之遥（XBOW 已登顶 HackerOne 真实漏洞榜；pentagi 等直接面向真实目标）；AIxCC 决赛系统全部开源进一步放大了可得性。CTF 域内尚无对"能力外溢"的约束机制，伦理审查（相关论文统计显示多数论文对滥用风险着墨极少）滞后于能力发展。
10. **攻防 LLM 本身**：反方向上，把 LLM 当靶机的研究（BishopFox、AgentCTF）表明现有"护栏架构"（特权/隔离分进程、RAG 越狱检测）可被另一台本地模型 100% 绕过——AI 系统自身成了新的 CTF 攻击面，防御侧几乎没有成熟能力。

### 2.4 趋势判断

- **2023–2024**：基准奠基期（InterCode、NYU CTF Bench、Cybench），单 agent + 脚手架创新；
- **2025**：多 agent + 知识增强期（D-CIPHER、CRAKEN），训练数据兴起（CTF-Dojo）；
- **2026**：工程化与评测反思期——多模型竞速拿真实冠军（verialabs）、通用 CLI agent 复用（ctf-skills）、MCP 工具标准化，同时"基准是否还在测真能力"成为核心质疑（CTF-ABACUS、基准饱和声明、强基线反思）。

下一步的竞争焦点大概率在：可自动生成的高难题库、trace 级能力审计成为标准评测、开源小模型的执行验证训练、以及真实漏洞（ bounty/AIxCC 式）场景的迁移。

---

## 附：主要参考来源

- EnIGMA: [arXiv:2409.16165](https://arxiv.org/abs/2409.16165) / [项目页](https://enigma-agent.github.io/)
- D-CIPHER: [arXiv:2502.10931](https://arxiv.org/abs/2502.10931) · CRAKEN: [arXiv:2505.17107](https://arxiv.org/abs/2505.17107) · NYU CTF Bench: [arXiv:2406.05590](https://arxiv.org/abs/2406.05590)
- HackSynth: [arXiv:2412.01778](https://arxiv.org/abs/2412.01778) · Cybench: [arXiv:2408.08926](https://arxiv.org/abs/2408.08926)
- InterCode: [arXiv:2306.14898](https://arxiv.org/abs/2306.14898) · CTF-Dojo: [arXiv:2508.18370](https://arxiv.org/abs/2508.18370)
- CTF-ABACUS: [arXiv:2608.26237](https://arxiv.org/abs/2608.26237) · Plain Agents: [arXiv:2412.02776](https://arxiv.org/abs/2412.02776) · A Second Look: [arXiv:2605.21497](https://arxiv.org/abs/2605.21497) · STRIATUM-CTF: [arXiv:2603.22577](https://arxiv.org/html/2603.22577v1)
- CTFAgent: [DOI:10.1016/j.jisa.2025.104305](https://doi.org/10.1016/j.jisa.2025.104305) · PwnGPT: ACL 2025 · KryptoPilot 复测: [arXiv:2601.09129](https://arxiv.org/abs/2601.09129)
- Awesome 列表: [Yeti-791/Awesome-Offensive-AI-Agentic-Landscape](https://github.com/Yeti-791/Awesome-Offensive-AI-Agentic-Landscape) / [raphabot/awesome-cybersecurity-agentic-ai](https://github.com/raphabot/awesome-cybersecurity-agentic-ai)

# CTF-Tiller 架构设计文档（交接版）

> 版本：v1.0（2026-10-29）
> 性质：设计规格 + 交接文档。接收方（人类或 AI）应以本文档为唯一权威来源实施本项目。
> 文档导读：§1 目标 → §2 设计输入 → §3 核心决策（含理由，**不要绕过**）→ §4 总体架构 → §5 组件规格 → §6 数据模型 → §7 主流程 → §8 通信规范 → §9 预算 → §10 路线图 → §11 反模式清单（**不要做**）→ §12 参考。

---

## 1. 项目目标与约束

构建 **CTF-Tiller**：一个可提交到比赛平台的自动化 CTF 解题 Agent 系统。平台侧拉取题目（含附件），系统自动完成解题并提交 flag，覆盖六个类别：

| 类别 | 典型题型 |
|---|---|
| Misc | 隐写、取证、编码、逻辑 |
| Web | SQL 注入、XSS、SSRF、逻辑漏洞、JS 分析 |
| Reverse | 二进制/字节码逆向、算法还原 |
| Crypto | 传统密码、数论、格、RSA |
| Pwn | 栈/堆溢出、格式化字符串、ROP、内核（远期） |
| AI | 攻击目标 LLM/Agent 系统（提示注入、越狱、工具滥用） |

**约束**：
- 平台环境可能封闭：镜像需自带全部工具，不假设外部依赖；
- 有时间/成本预算：单题限时（比赛节奏），token/金钱预算分级；
- 需要可观测：赛后能完整回放与复盘每题的决策过程。

## 2. 设计输入：调研结论与本团队经验

以下七条经验来自对约 35 个开源 CTF-Agent 项目与十余篇论文的调研（EnIGMA、D-CIPHER、CRAKEN、HackSynth、Cybench、CTF-Dojo、InterCode-CTF、verialabs/ctf-agent、ctf-skills、BoxPwnr、BUUCTF_Agent 等，详见 §12），是本架构的直接依据：

1. **交互式工具是基础**：必须在 Docker 镜像中封装全部做题工具，并常驻 tmux 供 agent 进行有状态交互（gdb/nc/REPL）。
2. **多 Agent 角色分工有价值**，但角色数量要克制（scaffold 边际递减，Plain Agents 教训）。
3. **知识增强（writeup RAG）作辅助**：AI 自身能力解不出时接入知识继续解。
4. **上下文工程必要**：长任务需要摘要、状态外置、断点续接。
5. **推理策略的核心是假设并行**：对一道题提出多种 intent 假设，交给不同 agent 探索——**而非把单一思路拆解成步骤分给多个 agent**（理由见 §3-D1）。
6. **多模型竞速是氪金加速项**：作为可选开关，非默认。
7. **复用通用编码 Agent 是常态**：不自研解题执行器，用 claude/codex 等 headless 模式驱动。

## 3. 核心决策（Decisions of Design）

每条决策附理由。**接手方如认为某条不合理，请先重读理由；如仍要修改，需在文档中记录变更依据。**

### D1 并行维度 = 假设（intent），不是步骤（task）
- **决策**：编排层的并行单位是"解题假设"。每道题生成 K 个互异的假设（不同的攻击面世界观），各自独立探索到底；**不做**"把一条既定思路拆成步骤分给多 agent"的分解。
- **理由**：① CTF 失败主因是路线错误而非执行慢，步骤分解在错误路线上加速沉没成本，假设并行在路线层面对冲；② CTF 步骤间依赖天然串行（逆向→提约束→求解），可并行环节少，拼接损耗大；③ 假设间天然独立，通信与汇总成本趋近于零；④ 与人类专家行为一致（快速试几个思路，哪个有戏深入哪个）；⑤ 步骤级并行未删除，**降级为 solver 内部自治**（solver 自己用 tmux 开多实验，编排层不管）。

### D2 编排自研，执行复用
- **决策**：自研的只有编排层（拉题、假设束管理、预算、升级、知识介入、跨题共享）；"解这道题"的执行全部交给通用编码 Agent（headless CLI，可换型号）。
- **理由**：通用编码 Agent 的执行力（写 exploit、调试、迭代脚本）已被调研充分验证（"Plain Agents"与"A Second Look"结论）；自研执行器是重复造轮子。分界线：**与"解这道题"无关的一切归编排层。**

### D3 禁止 agent 间自由对话
- **决策**：solver 之间不直接通信，一切协调经过 Coordinator；共享以文件工件为中心。
- **理由**：两个 LLM 直接对话会退化为幻觉循环与礼貌附和（D-CIPHER 的 executor 只回传摘要给 planner，从不互谈）；文件是无损通信，自然语言是有损通信；中心化拓扑可完整回放调试。

### D4 假设束状态机用纯代码实现，不用 LLM
- **决策**：Beam Manager（假设生命周期流转、调度、预算扣减）是确定性规则代码；智能只花在 Recon / Genesis / Coordinator 三处。
- **理由**：状态流转不需要智能，LLM 化只会引入不可复现与失控；代码状态机可测试、可审计。

### D5 flag 提交权集中独占
- **决策**：只有 Coordinator 可向平台提交 flag；solver（含竞速中的所有 solver）只能上报候选。
- **理由**：候选 flag 须经平台判对才算赢；集中提交避免浪费平台提交限速/扣分（D-CIPHER 的 planner 唯一持有 SubmitFlag 的设计）。

### D6 竞速下保持思路多样性（少注入）
- **决策**：竞速/假设并行期间，只广播负知识（DEAD_END）与平台级事实，**不广播正面发现**。
- **理由**：并行的价值在于多样性；过度共享使多路收敛为一路，N 个模型退化成 1 个。

### D7 tmux 交互必须封装 helper，不许裸用 send-keys/capture-pane
- **决策**：所有 agent 通过 `tt` 脚本与 tmux 会话交互（见 §5.1.3）。
- **理由**：裸用存在四个坑——无完成信号（时序靠猜）、capture-pane 抓的是屏幕快照非数据流（历史丢失/ANSI 污染）、转义错误、每步交互两条命令导致 token 翻倍。封装后收敛为三个原子命令。

### D8 知识库双位介入：先验 + 救兵
- **决策**：writeup 知识库介入两次——① Genesis 阶段作假设生成的先验（调整假设分布）；② Deep Dive 卡住时作救兵（针对当前假设检索技巧）。不做全程默认注入。
- **理由**：全程注入污染上下文且贵；先验位提升假设质量（CRAKEN 证明知识注入有效但强模型获益更大），救兵位保留 fallback 价值。

### D9 Trace 从第一天就冻结格式，且兼容 NYU 轨迹格式
- **决策**：每题落盘完整轨迹（JSONL，NYU CTF 格式兼容）+ 假设树。格式在 MVP 阶段冻结，之后只增不改。
- **理由**：① 赛后复盘（失败归因→补知识/补工具/补 Skills）是长期进化回路的地基；② NYU 兼容使未来可直接跑 CTF-ABACUS 做 trace 审计（区分真漏洞利用与捷径）。

### D10 汇总 = verdict 收集 + workspace 继承，不做委员会
- **决策**：并行结果汇总只收集结构化 Verdict；深入攻坚通过"假设专属 workspace + STATE.md + handoff 字段"文件交接；**禁止**多 agent 投票/讨论出结论。
- **理由**：汇总的本质是交接棒不是开会；证据在文件里，读文件不读对话；矛盾结论由胜负（谁先出真 flag）裁决而非互相说服。

---

## 4. 总体架构

```
┌────────────────────────────────────────────────────────────┐
│                     平台（CTFd / 自建判题）                   │
└─────────▲──────────────────────────────────▲───────────────┘
          │ 拉题/附件                          │ flag 提交（Coordinator 独占，D5）
┌─────────┴──────────────────────────────────┴───────────────┐
│  Platform Adapter（平台适配，可插拔）                         │
├────────────────────────────────────────────────────────────┤
│  ORCHESTRATOR（自研核心）                                    │
│   Recon Agent → Genesis（假设生成）→ Beam Manager（纯代码    │
│   状态机，D4）→ Coordinator（verdict 收集·扩束·注入·提交权）  │
│   Budget 漏斗（分级预算）                                     │
├────────────────────────────┬───────────────────────────────┤
│  Knowledge（writeup RAG，  │  Memory                        │
│  双位介入，D8）             │   Blackboard（跨题共享）· 经验库 │
├────────────────────────────┴───────────────────────────────┤
│  SOLVER 池（统一为通用编码 Agent，按档位分层，D2）            │
│   Scout（便宜模型·≤5min·证伪）  Deep-Diver（强模型·满预算）   │
│   [+ 竞速开关：仅对 ACTIVE 假设 ×N 模型，D6]                 │
├────────────────────────────────────────────────────────────┤
│  RUNTIME（全工具镜像 + tmux 常驻 + tt helper（D7）+          │
│   六类 Skills + 每假设独立 workspace）                        │
└────────────────────────────────────────────────────────────┘
```

## 5. 组件详细设计

### 5.1 Runtime 层（执行环境）

#### 5.1.1 镜像（单一镜像，分层构建）

| 类别 | 预装工具 |
|---|---|
| Pwn | gdb(pwndbg)、pwntools、ROPgadget、ropper、one_gadget、seccomp-tools、patchelf、angr、unicorn、libc-database |
| Reverse | Ghidra（headless，反编译导出伪码供 agent 阅读）、rizin/radare2、z3、UPX、binwalk |
| Crypto | SageMath、pycryptodome、gmpy2、sympy、RsaCtfTool、hashcat、john |
| Web | curl/httpie、ffuf、gobuster、sqlmap、nuclei、nmap、playwright（无头浏览器） |
| Misc | binwalk、foremost、steghide、zsteg、exiftool、tesseract、volatility3、sleuthkit、ffmpeg |
| AI | requests/httpx、目标 LLM 对话封装客户端、payload 变异脚本库 |

要点：
- **`/tools.md` 军火库清单**：列出镜像内全部工具及一句话用法，写入系统提示。agent 不知道有什么等于没有（避免浪费时间 pip install 或放弃）。
- tmux server 由容器入口脚本常驻拉起，会话按用途命名：`gdb-main`、`nc-target`、`py-repl`。
- AI 类 Skills 专项：目标探测（正常对话摸边界）→ 注入模板变异（脚本批量生成变体，**变异生成器是脚本工具而非 agent 角色**）→ 自动迭代（目标反馈→变异→重试）。

#### 5.1.2 Workspace 约定（每假设一个分区）

```
workspace/
  challenge/            # 题目附件与描述（只读）
  h01/                  # 假设 01 专属分区
    STATE.md            # 该假设的活状态（见 5.2.2）
    artifacts/          # 产出物（伪码、脚本、地址清单、exploit）
    findings.md         # append-only 发现日志（原子追加）
  h02/ ... h0K/
  blackboard.json      # 跨题/跨假设共享的平台级事实
```

#### 5.1.3 `tt` tmux helper（D7，agent 与交互式程序通信的唯一入口）

```
tt send <session> <keys>            # 发送按键（处理转义）
tt read <session> [--wait <pattern> --timeout 30]
                                    # 同步等待提示符/关键字符串出现后再抓取，
                                    # 解决"命令未执行完抓到半截输出"的时序问题
tt read <session> -S -2000          # 拉取全量滚动历史
```

### 5.2 Solver 层

#### 5.2.1 两档 solver（均为通用编码 Agent，档位不同）

| 档位 | 模型 | 预算 | 职责 |
|---|---|---|---|
| Scout | 便宜模型（如 mini 档） | ≤5 min / 低 token | 验证单个假设的 cheap_falsifier，返回 Verdict，产出落盘本假设 workspace |
| Deep-Diver | 强模型（如 opus/max 档） | 满预算（题目级分配） | 沿单一假设攻坚到底；可内部自治并行（自开 tmux 实验，编排层不管） |

通过适配器抽象（`solvers/base.py`），底层可换 claude headless / codex exec / 其它。竞速 = 对同一 ACTIVE 假设实例化 N 个 Deep-Diver（不同模型），见 §9。

#### 5.2.2 STATE.md（上下文工程核心）

每个 solver 被要求持续维护本假设分区的 STATE.md，结构固定：

```markdown
# Hypothesis h03: 格式字符串漏洞改写 GOT
## 已确认事实（附证据指针 artifact:line）
## 当前假设与攻击计划
## 已排除路线及原因
## 下一步
```

**作用**：任何重启（升级换模型、知识注入、崩溃恢复、Scout→Deep-Diver 交接）后，新 agent 读 STATE.md 无缝续接——上下文窗口丢失 ≠ 进度丢失。这是 CTFAgent 任务树思想的轻量实现。

#### 5.2.3 Skills 包（六类，按题注入对应一份）

方法论清单（非知识罗列），MVP 阶段每类一份 SKILL.md，例：
- pwn: checksec → 本地复现 → gdb 断点流程 → 远程差异
- misc: file/binwalk → strings → 隐写三板斧 → 编码识别
- web: 目录扫描 → 参数 fuzz → 手工验证 → JS 分析
- AI: 边界探测 → 模板变异 → 迭代注入

### 5.3 Orchestrator 层

#### 5.3.1 Recon Agent（便宜模型，每题一次，1~2 分钟）
不动手解题，只产出**证据包**（evidence pack）：file/strings/checksec/文件头/题目描述/附件结构/平台线索 → 题目画像（类别确认、攻击面清单、异常点标记）。证据包是所有假设的共同地基。

#### 5.3.2 Genesis（假设生成，D8 先验位在此介入）
基于证据包生成 K=3~5 个互异假设：
- 便宜模型高温度多次采样 → 聚类去重 → **强制覆盖不同攻击面**（pwn 题至少含"内存破坏"与"逻辑"两种世界观；misc 题覆盖"隐写/编码/文件结构"）；
- 知识库检索同类题 writeup 洞察作为先验（"这类题 80% 是 X"），调整假设分布；
- 每个假设是结构化对象（schema 见 §6.1），**必须含 cheap_falsifier**（最便宜的证伪实验）。

#### 5.3.3 Beam Manager（纯代码状态机，D4）
管理假设生命周期（状态机见 §6.2）、调度 Scout/Deep-Diver、扣减预算、束全灭时触发再侦察。**不含任何 LLM 调用。**

#### 5.3.4 Coordinator（中等模型，常驻）
- 收集 Verdict，执行剪枝/加码决策；
- **flag 提交权独占**（D5）：收到 FLAG_CANDIDATE → 平台判对 → 判对广播终止；判错通知该 solver 继续；
- 卡住检测（对 Deep-Diver 轨迹）：连续 3 步命令高度相似 / 同一报错重复 / STATE.md 超过 N 步未更新 / 预算过半零进展 → 触发知识救兵介入或假设状态调整；
- 动态扩束：Deep-Diver 上报新证据指向新世界观时，生成新假设走 Scout 流程入束。

### 5.4 Knowledge 层（D8 双位介入）

- 技术栈（MVP 轻量）：本地 embedding（bge-m3）+ sqlite-vec/chroma。**不引入** Milvus/Neo4j（CRAKEN 用的重型栈，量级不需要）。
- 知识源三层：① 分类技巧库（SKILL.md，L0 即注入）→ ② writeup 库（先验位/救兵位检索）→ ③ payload 库（AI 注入模板、pwn ROP/exp 骨架）。
- 检索结果经便宜模型压缩为 3~5 条与本题相关的可执行洞察再注入，防止上下文污染。

### 5.5 Memory 层

- **Blackboard**（redis 或内存 + JSON 落盘）：同一场比赛跨题共享——flag 格式、平台特性、同类题套路、环境坑。一道题学到的平台特征立刻惠及所有 solver。
- **经验库**：赛后复盘产物（见 §5.7），长期进化回路。

### 5.6 Platform Adapter

抽象接口（可插拔适配 CTFd / BUUCTF / 自建）：
```
pull_challenges() -> List[Challenge]
download(challenge) -> artifacts
submit_flag(challenge, flag) -> Correct | Wrong | RateLimited
```
提交结果必须回流 Coordinator（正反馈停止、负反馈换思路）。

### 5.7 Trace 与赛后进化（D9）

每题落盘：
1. **执行轨迹**：JSONL，NYU CTF 格式兼容（未来可跑 CTF-ABACUS 审计，区分真漏洞利用与捷径）；
2. **假设树**：每个假设的 intent、cheap_falsifier、verdict、死因、资源消耗（复盘金矿："总在哪类假设上误判"直接指导补强方向）。

赛后回路：LLM judge 复盘失败题 → 归因三分类 → **知识库缺 → 补 writeup；工具缺 → 补镜像；方法缺 → 补 Skills**。这是所有调研项目都没做好的点，也是 CTF-Tiller 的核心竞争力所在。

## 6. 数据模型

### 6.1 Hypothesis（假设对象）

```json
{
  "id": "h03",
  "intent": "格式字符串漏洞改写 GOT 表",
  "worldview": "memory-corruption",
  "expected_evidence": "%p 输出说明存在格式串漏洞",
  "cheap_falsifier": "本地运行程序输入 %p 观察输出",
  "cost_estimate": "MED",
  "state": "SCOUTING",
  "workspace": "workspace/h03/",
  "budget": {"time_min": 5, "max_tokens": 200000},
  "generation": 1
}
```

### 6.2 假设状态机（Beam Manager 纯代码实现）

```
GENERATED → SCOUTING → ┬─ DEAD        （证伪，死因入 findings.md）
                       ├─ WEAK/PENDING （挂起，束收束后可唤醒）
                       └─ ACTIVE → Deep-Diver 接管 → ┬─ SOLVED（出 flag）
                                                     └─ EXHAUSTED（资源耗尽，回束）
束全灭（无 DEAD 之外的活假设）→ 再侦察（换类别视角 Recon + 知识深度检索）
  → 生成第二波（generation=2，携带第一波全部死因）→ 最多三轮后放弃该题
```

### 6.3 Verdict（Scout 返回的结构化判定）

```json
{
  "hypothesis_id": "h03",
  "verdict": "PROMISING | WEAK | DEAD",
  "evidence": ["artifact:line 的证据指针列表"],
  "artifacts": ["h03/artifacts/01-fmt-check.txt"],
  "handoff": "若深入：交互协议已确认，buf 偏移在 echo 后第 7 个参数，从 GOT 改写开始"
}
```

## 7. 解题主流程（一道题的生命周期）

```
Stage 1  Recon        便宜模型，1~2min，产证据包
Stage 2  Genesis      生成 K=3~5 互异假设（知识先验介入①）
Stage 3  Scout Wave   每假设一个 Scout 并行证伪（≤5min/个，便宜模型）
Stage 4  Refocus      Beam Manager 剪枝：DEAD 剪掉（死因入 findings），
                      PROMISING 留 1~2 个升 ACTIVE，WEAK 挂起
Stage 5  Deep Dive    Deep-Diver 接管 ACTIVE 假设 workspace 攻坚
                      （知识救兵介入②；新证据→动态扩束；EXHAUSTED→回束）
Stage 6  收束/再生    flag→Coordinator 提交→判对终止（其他 workspace 归档）
                      束全灭→再侦察→第二波假设（≤3 波）
```

简单题在漏斗上层结束（多数题 Scout 判明后单 Deep-Diver 解决）；束再生只对值得的题展开。

## 8. 通信与汇总规范

### 8.1 三层通道

| 层 | 载体 | 传什么 | 方向 |
|---|---|---|---|
| 工件层 | workspace 文件 | 产出物本体（伪码/脚本/地址/STATE.md/findings） | 写者→所有读者 |
| 事件层 | 内存队列 | `FOUND_ARTIFACT` / `DEAD_END` / `STUCK` / `FLAG_CANDIDATE` / `DONE` | solver→Coordinator（solver 间只读不回，D3） |
| 注入层 | Coordinator 主动 | 针对性技术提示 | Coordinator→单个 solver |

findings.md 条目固定格式：`[h03] 结论一句话 | 证据: artifact:line | 置信度`。

### 8.2 汇总规则（D10）

- Scout 波结束：收集 Verdict（结构化 JSON），Beam Manager 规则决策，无 LLM 参与；
- Scout→Deep-Diver 交接：workspace 继承（读文件+STATE.md+handoff 字段），不读对话历史；
- 禁止多 agent 投票/协商结论；假设间结论矛盾无需裁决（各自在各自 workspace 持己见，胜负由谁先出真 flag 决定）。

### 8.3 竞速模式的通信限制（D6）

竞速开启期间（同一假设多模型并行）：只广播 `DEAD_END` 与平台级事实（blackboard），**不广播正面发现**。

## 9. 预算模型（漏斗）

```
Recon $0.02 → Scout 波 K×$0.1 → Deep Dive $1~2 → 竞速 ×N（可选，仅 ACTIVE 假设）
 广度·便宜     快速证伪剪枝       深度·集中        冲刺·氪金
```

| 模式 | 配置 | 场景 |
|---|---|---|
| 经济 | 便宜模型单档，无竞速 | 刷题/评测 |
| 标准 | 便宜 Scout + 强 Deep-Diver + 束管理 | 默认 |
| 氪金 | 标准 + ACTIVE 假设 ×2~3 模型竞速 | 比赛冲刺 |

## 10. 落地路线图

**MVP（先跑通，能解大量中低难度题）**
- Adapter + Recon + 简化 Genesis（固定 K=3 单次生成）
- 单档 Deep-Diver（不做 Scout 波，Recon 后直接三假设顺序/简单并行走 Deep-Diver）
- Runtime：镜像 + tools.md + tmux + tt helper + 六份 Skills
- workspace/STATE.md/findings.md 约定 + trace 格式冻结（D9）

**阶段二**
- Scout 波与完整束状态机（纯代码 Beam Manager）
- Coordinator 卡住检测 + 知识双位介入（bge-m3 + sqlite-vec）
- Blackboard

**阶段三**
- 动态扩束、束全灭再侦察
- 竞速模式（ACTIVE ×N 模型）
- 假设树 trace + 赛后复盘回路（LLM judge 归因→补知识/工具/Skills）

**仓库形态**
```
ctf-tiller/
  adapter/        # 平台适配（ctfd, buuctf, ...）
  orchestrator/   # recon.py genesis.py beam.py coordinator.py budget.py
  solvers/        # base.py claude_code.py codex.py race.py
  runtime/        # Dockerfile* tools.md tt/ skills/
  knowledge/      # writeups/ indexer.py retriever.py
  memory/         # blackboard.py
  traces/         # 每题一目录：trace.jsonl + hypothesis_tree.json
```

**最重要的调优旋钮**：Genesis 的多样性质量。假设分布好，后续全程顺水推舟；分布差，后面所有机制都在还债。

## 11. 反模式清单（明确不做）

| # | 不要做 | 依据 |
|---|---|---|
| 1 | 把单一思路拆成步骤分给多 agent（编排层步骤分解） | D1：路线错误时加速沉没成本；CTF 步骤天然串行 |
| 2 | agent 间自由对话 / 委员会投票汇总 | D3/D10：幻觉循环、礼貌附和 |
| 3 | Beam Manager / 调度用 LLM 实现 | D4：确定性逻辑不需要智能 |
| 4 | solver 直接向平台提交 flag | D5：提交权集中 |
| 5 | 竞速/并行期间广播正面发现 | D6：杀死多样性 |
| 6 | 裸用 tmux send-keys/capture-pane | D7：时序/截断/转义三坑 |
| 7 | 知识全程默认注入 RAG 结果 | D8：上下文污染 + 成本 |
| 8 | MVP 就上 Milvus/Neo4j 重型检索栈 | §5.4：量级不需要 |
| 9 | 频繁变更 trace/workspace/findings 的 schema | D9：接口冻结，改动牵一发动全身 |
| 10 | 自研解题执行器（不复用通用编码 Agent） | D2：重复造轮子，已被调研证伪 |
| 11 | 变异生成器/AI 类 payload 生成做成 agent 角色 | §5.1.1：做成脚本工具，保持架构简单 |
| 12 | 一开始就开多模型竞速 | §9：竞速是冲刺选项，钱花在 ACTIVE 假设上 |

## 12. 参考项目与论文（设计依据溯源）

- **EnIGMA**（[arXiv:2409.16165](https://arxiv.org/abs/2409.16165)）：IAT 交互式工具接口（gdb/pwntools 跨轮持久会话）→ D7/tt helper 与 tmux 常驻设计
- **D-CIPHER**（[arXiv:2502.10931](https://arxiv.org/abs/2502.10931)）：Planner-Executor 分工、planner 唯一 SubmitFlag → D5
- **CRAKEN**（[arXiv:2505.17107](https://arxiv.org/abs/2505.17107)）：writeup Graph-RAG 知识注入有效 → D8
- **HackSynth**（[arXiv:2412.01778](https://arxiv.org/abs/2412.01778)）：Planner/Summarizer、多攻击假设、创造力参数 → 假设并行、采样多样性
- **Cybench**（[arXiv:2408.08926](https://arxiv.org/abs/2408.08926)）：scaffold 对比（边际递减）、伪终端脚手架 → D2
- **CTF-Dojo**（[arXiv:2508.18370](https://arxiv.org/abs/2508.18370)）：执行验证轨迹训练 → 远期方向
- **verialabs/ctf-agent**（[GitHub](https://github.com/verialabs/ctf-agent)）：多模型竞速 + Coordinator 注入 + BSidesSF 2026 全解夺冠 → D6、竞速矩阵
- **ctf-skills**（[GitHub](https://github.com/ljagiello/ctf-skills)）：Claude Code Skills 包 → §5.2.3
- **CTF-ABACUS**（[arXiv:2608.26237](https://arxiv.org/abs/2608.26237)）：trace 级审计（62–87% 成功才是真利用）→ D9
- **Plain Agents**（[arXiv:2412.02776](https://arxiv.org/abs/2412.02776)）与 **A Second Look**（arXiv:2605.21497）：裸 agent 强基线，scaffold 边际递减 → D2、角色克制
- **CTFAgent**（DOI:10.1016/j.jisa.2025.104305）：状态化任务树 → STATE.md

---

*本文档由三轮设计讨论收敛而成（环境与交互工具 → 多 agent 通信与汇总 → 假设并行架构）。如需扩展，优先保持 §3 决策与 §11 反模式的一致性。*

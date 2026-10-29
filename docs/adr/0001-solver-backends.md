# ADR 0001：Solver 基座用 Claude CLI 与 Codex CLI

日期：2026-10-29。状态：已接受。对应设计决策 D2。

## 决策

解题执行不自研。并发阶段把 Claude CLI 和 Codex CLI 当作两台可替换的基座，由编排层拉起进程。

- Claude 的调用以 `claude -p` 开头，后面可以追加模型、权限等参数。
- Codex 的可执行文件名固定为 `codex`。完整参数等到对接时再冻结。
- 基座名字只有 `claude` 和 `codex`。
- MVP 一次只跑一个 Deep-Diver，默认 `claude`。竞速开关默认关闭。打开后，只对 ACTIVE 假设同时拉起这两个基座。

命令行参数在真正调用前再写入配置，现在不落配置文件。

## 依据

通用编码 Agent 的执行力已经由调研确认。`claude -p` 是 Claude CLI 的非交互入口，和设计稿里的 headless 模式一致。竞速仍然受 D6 约束：并行期间只共享死路和平台事实。

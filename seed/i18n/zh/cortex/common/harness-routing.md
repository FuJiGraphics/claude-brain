# harness-routing - 这个技能依赖的 Claude Code 行为

每一行: 前提、使用位置、依据,以及失效时的替代。只有行为确实失效时才运行 hippocampus 的 `harness-refresh`。

checked: 2026-09-06
checked_version: claude-code_2-1-263_agent

checked_version 是这张表最后一次核对的版本。实际确认行为的版本见 §5。

## 1. 原则

- 基于文档的行不重新核对,只把基于观察的行与当前版本核对。
- 行号保持不变,其他文件按编号引用(#1、#12)。

## 2. 项目

| # | 前提 | 使用位置 | 依据 | 失效时 |
|---|---|---|---|---|
| 1 | `.claude/` 是受保护的路径,每次 Edit 或 Write 都要求交互式确认。acceptEdits、allow 规则和钩子的 `permissionDecision: allow` 都过不去,只有 bypassPermissions 可以。拒绝规则在 bypassPermissions 下依然有效 | scripts/hippocampus-daemon.sh(权限参数、`--tools`、`--disallowedTools`) | permission-modes 文档,观察 2026-09-03 | done 文件为 `status: denied`。替代办法是把记忆库放到 `~/.claude` 之外 |
| 2 | 钩子的 stdin JSON 含有 `session_id`、`cwd`、`tool_name`、`tool_input` | scripts/thalamus.py | 钩子文档 | brain 不做任何事(fail-open) |
| 3 | PreToolUse 钩子的退出码 2 会阻止工具调用,brain 的钩子命令总是以 `exit 0` 结束 | scripts/install.sh | 钩子文档 | - |
| 11 | `claude -p` 接受 `--tools`、`--disallowedTools`、`--strict-mcp-config`、`--max-turns`、`--effort`、`--name`、`--output-format json` | scripts/hippocampus-daemon.sh、editor/server.py | CLI 参考,`claude -p --help` | 守护进程日志出现参数错误,任务以 `failed` 结束 |
| 12 | 在非交互的 `claude -p` 中启动的子代理没有写权限 | 不使用: 海马不启动子代理 | 观察 2026-09-03 | 不适用 |
| 13 | `claude -p --output-format json` 返回 `result`、`is_error`、`subtype`、`num_turns`、`permission_denials[]`、`total_cost_usd`、`usage` | scripts/hippocampus-daemon.sh、scripts/usage.py | headless 文档,观察 2026-10-05 | 不是 JSON 时把原始文本记入日志 |
| 14 | Windows 上钩子的路径可能是 `C:\...` 或 `C:/...` | scripts/plat.py(两种都会规范化) | 尚未在真机上确认 | 两种都会被规范化 |
| 15 | Windows 上 Bash 运行在 Git Bash 中,基于 Node 的文件工具会误读 `/c/...` 路径 | scripts/_lib.sh 的 `nw_tool_path` | Git for Windows 文档,尚未在真机上确认 | 检查显示的路径是否原样复制 |

## 3. [失效] 记录

(暂无)

## 4. 未验证 (Windows)

- 第 14、15 行基于文档和路径规则,还没有在真实的 Windows 机器上运行过。

## 5. 实测记录(每行写日期和版本)

- 2026-09-29 claude-code 2.1.283: 钩子可以在 SessionStart、UserPromptSubmit、PreToolUse、PostToolUse、PostToolUseFailure 和 Stop 时添加上下文。写成命令口吻的钩子文字被怀疑是提示词注入,没有被遵守。

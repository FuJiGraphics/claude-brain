# harness-routing - Claude Code behaviors this skill relies on

Each row: the assumption, where it is used, the evidence, and the fallback when it breaks. Run hippocampus `harness-refresh` only when a behavior actually broke.

checked: 2026-09-06
checked_version: claude-code_2-1-263_agent

checked_version is the last version this table was compared against. The version where a behavior was actually confirmed is in §5.

## 1. Principles

- Rows based on documentation are not re-checked. Only rows based on observation are compared against the current version.
- Keep the row numbers as they are; other files point at them (#1, #12).

## 2. Items

| # | Assumption | Used in | Evidence | When it breaks |
|---|---|---|---|---|
| 1 | `.claude/` is a protected path: every Edit or Write asks for interactive approval. acceptEdits, allow rules and a hook's `permissionDecision: allow` cannot get past it; only bypassPermissions does. Deny rules still apply in bypassPermissions | scripts/hippocampus-daemon.sh (permission flag, `--tools`, `--disallowedTools`) | permission-modes docs, observation 2026-09-03 | the done file says `status: denied`. The alternative is to keep the memory store outside `~/.claude` |
| 2 | Hook stdin JSON carries `session_id`, `cwd`, `tool_name`, `tool_input` | scripts/thalamus.py | hooks docs | brain stays silent (fail-open) |
| 3 | Exit code 2 from a PreToolUse hook blocks the tool call; brain's hook command always ends with `exit 0` | scripts/install.sh | hooks docs | - |
| 11 | `claude -p` accepts `--tools`, `--disallowedTools`, `--strict-mcp-config`, `--max-turns`, `--effort`, `--name`, `--output-format json` | scripts/hippocampus-daemon.sh, editor/server.py | CLI reference, `claude -p --help` | the daemon log shows a flag error and the job ends `failed` |
| 12 | Sub-agents started inside a headless `claude -p` get no write permission | not used: the hippocampus does not start sub-agents | observation 2026-09-03 | not applicable |
| 13 | `claude -p --output-format json` returns `result`, `is_error`, `subtype`, `num_turns`, `permission_denials[]`, `total_cost_usd`, `usage` | scripts/hippocampus-daemon.sh, scripts/usage.py | headless docs, observation 2026-10-05 | when the output is not JSON, the raw text is logged instead |
| 14 | On Windows, hook paths may arrive as `C:\...` or `C:/...` | scripts/plat.py (normalizes both) | not yet confirmed on a real machine | normalized either way |
| 15 | On Windows, Bash runs in Git Bash, and Node-based file tools misread `/c/...` paths | scripts/_lib.sh `nw_tool_path` | Git for Windows docs, not yet confirmed on a real machine | check that the printed path was copied as is |

## 3. [Broken] log

(none yet)

## 4. Unverified (Windows)

- Rows 14 and 15 come from documentation and path rules; they have not been run on a real Windows machine yet.

## 5. Field log (date and version per line)

- 2026-09-29 claude-code 2.1.283: hooks can add context at SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, PostToolUseFailure and Stop. Hook text written as commands was treated as possible prompt injection and not followed.

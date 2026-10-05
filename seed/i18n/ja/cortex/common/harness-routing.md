# harness-routing - このスキルが頼っている Claude Code の動作

各行: 前提、使う場所、根拠、壊れたときの代わり。実際に動作が壊れたときだけ hippocampus の `harness-refresh` を実行します。

checked: 2026-09-06
checked_version: claude-code_2-1-263_agent

checked_version は、この表を最後に照合したバージョンです。動作を実際に確かめたバージョンは §5 にあります。

## 1. 原則

- ドキュメントに基づく行は照合し直しません。観測に基づく行だけを今のバージョンと照合します。
- 行番号はそのままにします。ほかのファイルが番号で指しています(#1、#12)。

## 2. 項目

| # | 前提 | 使う場所 | 根拠 | 壊れたとき |
|---|---|---|---|---|
| 1 | `.claude/` は保護されたパスで、Edit や Write のたびに対話での承認を求める。acceptEdits、allow ルール、フックの `permissionDecision: allow` では通れず、通れるのは bypassPermissions だけ。拒否ルールは bypassPermissions でも有効 | scripts/hippocampus-daemon.sh(権限フラグ、`--tools`、`--disallowedTools`) | permission-modes のドキュメント、観測 2026-09-03 | done ファイルが `status: denied` になる。代わりに記憶の保存先を `~/.claude` の外に置く |
| 2 | フックの stdin JSON に `session_id`、`cwd`、`tool_name`、`tool_input` がある | scripts/thalamus.py | フックのドキュメント | brain は何もしない(fail-open) |
| 3 | PreToolUse フックの終了コード 2 はツール呼び出しを止める。brain のフックのコマンドは必ず `exit 0` で終わる | scripts/install.sh | フックのドキュメント | - |
| 11 | `claude -p` は `--tools`、`--disallowedTools`、`--strict-mcp-config`、`--max-turns`、`--effort`、`--name`、`--output-format json` を受け付ける | scripts/hippocampus-daemon.sh、editor/server.py | CLI リファレンス、`claude -p --help` | デーモンのログにフラグのエラーが出て、作業は `failed` になる |
| 12 | 非対話の `claude -p` の中で起動したサブエージェントには書き込み権限がない | 使わない: 海馬はサブエージェントを起動しない | 観測 2026-09-03 | 該当なし |
| 13 | `claude -p --output-format json` は `result`、`is_error`、`subtype`、`num_turns`、`permission_denials[]`、`total_cost_usd`、`usage` を返す | scripts/hippocampus-daemon.sh、scripts/usage.py | headless のドキュメント、観測 2026-10-05 | JSON でなければ生のテキストをログに残す |
| 14 | Windows ではフックのパスが `C:\...` または `C:/...` で来ることがある | scripts/plat.py(どちらも正規化する) | 実機ではまだ未確認 | どちらでも正規化される |
| 15 | Windows では Bash が Git Bash で動き、Node ベースのファイルツールは `/c/...` のパスを読み違える | scripts/_lib.sh の `nw_tool_path` | Git for Windows のドキュメント、実機ではまだ未確認 | 表示されたパスをそのまま写したか確かめる |

## 3. [破損] 記録

(まだありません)

## 4. 未検証 (Windows)

- 14 と 15 の行はドキュメントとパスの規則に基づくもので、実際の Windows マシンではまだ動かしていません。

## 5. 実測記録(行ごとに日付とバージョン)

- 2026-09-29 claude-code 2.1.283: フックは SessionStart、UserPromptSubmit、PreToolUse、PostToolUse、PostToolUseFailure、Stop でコンテキストを足せる。命令口調のフックの文はプロンプトインジェクションと疑われ、守られなかった。

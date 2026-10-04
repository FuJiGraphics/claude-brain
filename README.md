<h1 align="center">brain</h1>
<h3 align="center">make Claude Code remember!</h3>

<p align="center">
  <b>English</b> · <a href="README.ko.md">한국어</a> · <a href="README.ja.md">日本語</a> · <a href="README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-CC%20BY--ND%204.0-lightgrey.svg" alt="CC BY-ND 4.0"></a>
  <a href="https://claude.com/claude-code"><img src="https://img.shields.io/badge/Claude%20Code-Skill-d97757?logo=anthropic&logoColor=white" alt="Claude Code skill"></a>
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20(beta)%20%7C%20Linux-lightgrey" alt="platforms">
  <img src="https://img.shields.io/badge/lang-EN%20%7C%20KO%20%7C%20JA%20%7C%20ZH-blue" alt="languages">
  <a href="#benchmark"><img src="https://img.shields.io/badge/blind%20review-2%2F2%20wins-2a78d6" alt="benchmark"></a>
</p>

<p align="center">
  <a href="https://cdn.jsdelivr.net/gh/FuJiGraphics/claude-brain@media/brain-promo-en-720p.mp4">
    <img src="https://raw.githubusercontent.com/FuJiGraphics/claude-brain/media/brain-promo-en-preview.gif" alt="brain app preview" width="720">
  </a>
  <br><sub>▶ <a href="https://cdn.jsdelivr.net/gh/FuJiGraphics/claude-brain@media/brain-promo-en-720p.mp4">Watch the full 60-second video</a> (demo data, no real project)</sub>
</p>

**brain is long-term memory for Claude Code that runs on its own.**
When Claude touches a file, runs a command or hits an error that it has learned something about before, that memory pops into the session by itself. New memories are written from your conversation logs outside the session, and every night the brain tidies up and forgets what is stale. Claude never has to "remember to remember".

```bash
git clone --single-branch https://github.com/FuJiGraphics/claude-brain.git ~/.claude/skills/brain
bash ~/.claude/skills/brain/scripts/install.sh
```

Then open the app with **`/claude-brain-app`** in Claude Code.

**Contents** · [Why](#why-brain) · [How it differs](#how-brain-differs) · [Benchmark](#benchmark) · [Compared with alternatives](#compared-with-alternatives) · [The brain app](#the-brain-app) · [How it works](#how-it-works) · [Install](#install) · [Commands](#commands) · [Cost and privacy](#cost-and-privacy) · [FAQ](#faq) · [Limitations](#limitations) · [Reference](#reference) · [License](#license)

---

## Why brain

If you use Claude Code on the same projects for weeks, you keep paying for the same lessons:

- **Every session starts blank.** The team convention you agreed on two months ago, the pitfall that cost an afternoon, how this feature fits the bigger picture. You explain it again, or it gets skipped and something breaks.
- **"Check your notes first" does not work.** In the author's logs, a hard rule to consult notes before editing was skipped in **20% of 6,300 Edit/Write calls and 32% of 893 Bash writes**.
- **Memory tools that wait to be called don't get called.** If recall depends on the agent deciding to search, it searches least when it doesn't know what it doesn't know.
- **Notes rot.** Without someone to merge, correct and retire them, notes pile up, contradict each other and get loaded whole into every session.

brain moves all of that out of the session. The session does nothing; memories just show up.

```
What enters the session the moment Claude is about to edit src/Payment/PaymentClient.cs (example)

[memory] What I remember about `PaymentClient` (facts verified in the past - the current code may differ).
- Payment retries reuse the idempotency key - creating a new one causes double charges (projects/shop/lessons/payment-retry-reuses-key.md)
```

## How brain differs

| | |
|---|---|
| 🧠 **Recall without asking** | Hooks look at the file being read or edited, the API being called, the files a command touches and the compiler error just thrown, and surface only the memories tied to them. Nothing matches, nothing is added. |
| 🌙 **Learns outside the session** | A separate background agent (the *hippocampus*) replays conversation logs and writes memories with evidence. The session never spends turns on bookkeeping. |
| 🧹 **Sleeps, consolidates and forgets** | Every night it counts how each memory was used, hides memories unused for 45 days (120 for decisions and pitfalls) without deleting them, merges overlaps and checks for broken links. |
| 📜 **Facts, not orders** | Memories arrive as sourced facts. If they disagree with the current code, the current code wins. Commanding hook text was measured to be ignored as suspected prompt injection, so brain never commands. |
| 💸 **On a budget** | About 20 ms per hook and about 2,000 characters per session on average, with hard caps. |
| 📱 **An app you can actually read** | `/claude-brain-app` shows each project's brain, what it cares about, what it learned, and lets you ask it questions, give feedback, tidy it up and set its working style. |
| 🎭 **Persona with real guardrails** | Choose how Claude works per project. "Must" rules are enforced by hooks: ask before hard-to-undo commands, no finishing without verifying edits. |
| 🌐 **Multilingual** | App, session text and personas in English, Korean, Japanese and Chinese. Memories are stored in the language you chat in. |
| 📂 **Local, plain files** | Memories are Markdown files on your machine. No server, no account, no telemetry. |

## Benchmark

**The same feature was built twice on a real project: once with brain, once without.** Same model, same request, same starting commit, each in its own copy. Two reviewers judged the results without knowing which was which.

<p align="center">
<picture><source media="(prefers-color-scheme: dark)" srcset="benchmarks/2026-09-30/score-dark.svg"><img src="benchmarks/2026-09-30/score-light.svg" alt="blind review score" width="720"></picture>
</p>

| | Case 1: roulette mini-game | Case 2: pinball mini-game |
|---|---|---|
| Review score (of 50, two reviewers) | **brain 34** / plain 29 | **brain 30.5** / plain 22 |
| Reviewers' pick | brain 2 / 2 | brain 2 / 2 |
| Time | 9.9 min / 6.9 min | 13.9 min / 4.7 min |
| Cost (list price) | $2.98 / $1.96 | $3.37 / $1.12 |

**The difference came from knowledge that was not in the code or docs.** A verbal team rule (sheet data always arrives as TSV) that brain followed and plain Claude broke; two expensive pitfalls brain avoided and plain Claude stepped on; and the big picture of the feature, which brain wired into the existing event flow while plain Claude built a standalone game.

**The price:** brain took 1.4-2.9x the time and 1.5-3.0x the cost, spent reading and checking memories (and in case 2, doing twice the scope). Two cases, one run each: the trend is clear but not statistically settled. In a separate single-shot planning test (18 tasks, 3 models) there was no quality difference, because one-off plans rarely touch this kind of context. Raw data: [`benchmarks/2026-09-30/results.json`](benchmarks/2026-09-30/results.json).

## Compared with alternatives

As of October 2026, based on each project's own docs. "Recall" is the important column: who decides that a memory enters the context, and when.

| | Who writes | How it is recalled | Curation and forgetting | Where |
|---|---|---|---|---|
| **brain** | A background agent, from conversation logs (plus your feedback) | **Automatically, per file, command and error**, at the moment it matters | Nightly merge, decay to dormant, strength stats, link checks | Local Markdown |
| `CLAUDE.md` / rules | You (or Claude when asked) | Loaded whole at session start (path rules when files are read) | None | Local files |
| Claude Code auto memory | Claude, during the session | First 200 lines or 25 KB of `MEMORY.md` at start; topic files when Claude reads them | A reminder to merge near the limit | Local |
| [claude-mem](https://github.com/thedotmack/claude-mem) | Hooks capture, a worker summarizes | Recent sessions injected at start; search via MCP tools | Not documented | Local SQLite |
| [Mem0 MCP](https://docs.mem0.ai/platform/mem0-mcp) | The agent calls `add_memory` | The agent must call search | Add-only in OSS | Cloud or self-hosted |
| [Basic Memory](https://github.com/basicmachines-co/basic-memory) | The agent writes notes via MCP | The agent must call search | Manual | Local Markdown |
| [MCP memory server](https://github.com/modelcontextprotocol/servers/tree/main/src/memory) | The agent creates entities | The agent must call read/search | None | Local JSONL |
| [Cline Memory Bank](https://docs.cline.bot/customization/memory-bank) | Cline, when you say "update memory bank" | All files read at every task | None | Project Markdown |
| [Cursor rules](https://cursor.com/docs/context/rules) | You (auto memories were removed in 2.1) | Always, by description, or by glob | None | Project, dashboard |
| [Windsurf memories](https://docs.devin.ai/desktop/cascade/memories) | Cascade, automatically | When Cascade judges them relevant | Not documented | Local |
| [Copilot Memory](https://docs.github.com/en/copilot/concepts/agents/copilot-memory) | Copilot, with citations | Validated against the current branch before use | Expires after 28 days unused | GitHub servers |

**When to pick what.** Keep `CLAUDE.md` for the handful of rules every session needs; brain complements it. If you want one memory shared across many tools or a team, an MCP memory (Mem0, Basic Memory) fits better: brain is per-machine and Claude Code only. Pick brain when your projects are long-lived and the costly knowledge is the kind nobody writes down: verbal decisions, hard-won pitfalls, "how this fits together". We recommend turning **off** Claude Code's auto memory alongside brain (see [FAQ](#faq)).

## The brain app

`/claude-brain-app` opens a small, phone-like window (Chrome or Edge app mode, local only).

- **Brains**: one character per project. It grows with its memories (egg, baby, kid, adult, sage) and its mood comes from real signals: head weight, failed jobs, sleep, learning.
- **Bubbles**: words for what this brain cares about most, picked by Claude Haiku from the memory titles. Tap one to gather those memories.
- **Memories in plain words**: AI-written notes are terse. Opening one shows a one-line summary, why it matters, when it comes up and the jargon explained, with the original folded below.
- **Yes/no feedback**: each memory asks a question like "Do you still deploy with the release script?" Tap 👍 still right, ✏️ it changed, ⭐ important, or 🗑 not needed. Feedback collects in a 📮 mailbox and is sent to the hippocampus in one go.
- **Ask the brain**: chat with a project's brain. It answers only from its memories and links the ones it used.
- **Feed**: tell it something it must remember.
- **Tidy up**: when the head gets heavy, the hippocampus merges and trims (archives, never deletes). It shows how many rounds it will take before you start.
- **Persona**: pick a breed (Squirrel, Owl, Cat, Turtle) or wire traits to situations yourself.
- **Journal and settings**: what the hippocampus did, on/off, model, language, theme.

The app never edits memories directly. Feeding, feedback and tidying are handed to the hippocampus through the same queue it always uses.

### Persona

Traits come in opposite pairs (Drive/Careful, Autonomy/Curious, Quick/Thorough, Minimal/Proactive, Concise/Friendly) and are wired to situations (usually, hard-to-undo actions, after editing code, big changes, ambiguous requests, unfamiliar code). Strength decides how hard it pushes:

| Strength | What happens |
|---|---|
| light | A sentence at session start |
| normal | Plus a one-line reminder on every request |
| must! 🔒 | Plus a hook that enforces it: asks you before `rm -rf`, `push --force`, `reset --hard`, DB drops or deploys; asks before editing more than N files; sends Claude back once if it tries to finish without running a build or test |

Personas are compiled from fixed tables, so the preview is exactly what Claude receives.

## How it works

| Part | In the brain | In brain |
|---|---|---|
| **cortex** | Long-term memory | Markdown memory store in three layers: `common/`, `stacks/<stack>/`, `projects/<slug>/`, each with thin indexes and memory files |
| **thalamus** | Filters senses into consciousness | Hooks. Surface memories tied to the current file, command or error; show the project map at session start; start replays at idle moments |
| **hippocampus** | Forms new memories | A background `claude -p` worker and the only writer to cortex. Registers projects, records, replays and tidies |
| **sleep** | Consolidates and forgets | Nightly job: strength stats, forgetting, replay of leftovers, search-miss learning, tidy-up, checks |

```
[recall - inside the session]
tool call ─ hook ─▶ thalamus ─▶ matching memories in cortex ─▶ [memory] message enters the session

[recording - outside the session]
end of turn, before compaction, session end ─▶ thalamus ─▶ replay (awake) ─────────┐
every night 04:30 ─▶ sleep ─▶ replay (scan), search-miss learning, tidy-up ─────────┴─▶ queue ─▶ hippocampus ─▶ cortex
```

The conversation logs Claude Code already writes act as short-term memory. Each segment is processed once.

## Install

```bash
git clone --single-branch https://github.com/FuJiGraphics/claude-brain.git ~/.claude/skills/brain
bash ~/.claude/skills/brain/scripts/install.sh
```

On Windows, run the same two lines in **Git Bash** (the same shell Claude Code uses). The installer is idempotent and backs up every file it changes as `<file>.brain-bak-<time>`. It:

1. registers the thalamus hooks in `~/.claude/settings.json` (other hooks are left alone; every hook exits 0 so brain can never block a tool call),
2. adds one line to `~/.claude/CLAUDE.md` telling Claude what `[memory]` messages are (without it, Claude ignored them),
3. schedules the nightly sleep at 04:30 (launchd on macOS, Task Scheduler on Windows; on Linux, add `scripts/sleep.sh` to cron),
4. creates the `/claude-brain-*` commands,
5. sets the language from your OS (change it in the app or with `scripts/config.sh lang en`).

**Projects register themselves.** At night, a git folder you worked in on 3+ days with 10+ requests in the last week is registered. Run `/claude-brain-sleep` to do it right away.

**Update:** `git -C ~/.claude/skills/brain pull && bash ~/.claude/skills/brain/scripts/install.sh`. Your memories are git-ignored and survive updates.
**Uninstall:** `bash ~/.claude/skills/brain/scripts/install.sh --uninstall` removes hooks, the CLAUDE.md block and the schedule. Memories stay until you delete the folder.

## Commands

Commands run only when you type them. Most are handled by the hook directly, so they cost no tokens.

| Command | What it does |
|---|---|
| `/claude-brain-app` | Open the brain app |
| `/claude-brain-status` | On/off, hippocampus queue and failures, last sleep, recalls in the last 24 h |
| `/claude-brain-on`, `/claude-brain-off` | Turn brain on or off (memories stay) |
| `/claude-brain-config [default\|eco\|quality]` | Hippocampus model: Sonnet medium / Sonnet low / Opus high |
| `/claude-brain-model`, `/claude-brain-effort` | Fine-tune the hippocampus model and effort |
| `/claude-brain-sleep` | Run the nightly cycle now |
| `/claude-brain-results` | Summary of hippocampus results |
| `/claude-brain-stop` | Stop the hippocampus after the current item |
| `/claude-brain-recall <name>...` | Search memories by file, symbol, API, error or symptom |
| `/claude-brain-remember <text>` | Queue something to remember |

## Cost and privacy

- **Recall** costs no API calls: hooks are local Python, about 20 ms each, adding about 2,000 characters per session on average.
- **The hippocampus** runs `claude -p` (Sonnet medium by default) once per queued item, using your Claude subscription or API usage. In the author's measurements a recording item took a median of 48 turns and 9 minutes. Use `/claude-brain-config eco` to spend less.
- **The app** calls Claude Haiku with thinking off for bubbles, plain-word explanations and answers: about $0.001-0.005 and 4-6 seconds each. Explanations are cached.
- **Privacy**: memories, logs and the app stay on your machine. The only network traffic is the Claude API calls Claude Code makes anyway. The app listens on `127.0.0.1` only, with a fresh token each launch.
- **Permissions**: the hippocampus runs without permission prompts (it has no one to ask) but with deny rules for git writes, `rm`, `sudo` and editing settings or other skills. See [hippocampus permissions](#hippocampus-permissions).

## FAQ

**Isn't `CLAUDE.md` enough?** It is perfect for a few rules every session needs. It is loaded whole, written by hand and never cleans itself up. brain holds the long tail (hundreds of pitfalls and decisions) and only surfaces what the current file or error touches.

**Should I keep Claude Code's auto memory on?** We recommend turning it off (`"autoMemoryEnabled": false`). Both store "what we learned last time", but auto memory has nobody correcting it and loads at every start, so stale notes can override fresh ones.

**What if a memory is wrong?** Open it in the app and tap ✏️ "it changed". The hippocampus checks and fixes it. Memories also carry "verified" stamps, and the current code always wins over a memory.

**Will my memories get huge?** The nightly sleep merges overlaps and hides unused memories (they stay searchable). The app's "head weight" shows when a project needs a tidy-up.

**Can my team share it?** Not yet. Memories are per machine. You can sync the `cortex/` folder yourself, but it is not designed for concurrent writers.

**Does it work with Cursor, Codex or others?** No. brain is built on Claude Code hooks.

**Which languages?** The app, session text and personas: English, Korean, Japanese, Chinese. Memories are written in the language you chat in. Japanese and Chinese symptom searches are weaker than file or symbol matches, which work in any language.

**Can I see what it injected?** `/claude-brain-status` shows recent recall counts and characters; `.active/recall.log` has every event.

## Limitations

- **Measured on one person's projects** (macOS, mostly Unity/C# and VS Code extensions). Clue extraction was tuned for C# compiler errors; file and API matching work for any language.
- **Windows support is new (beta).** Paths, hooks, the scheduler and the app were ported and reviewed, but not yet run on a real Windows machine. Please open an issue if something breaks.
- **Costs time and tokens** on tasks where context matters (see the benchmark). It pays off over weeks, not on a one-off script.
- **The hippocampus is an unsupervised agent on your machine** (with deny rules). If that is uncomfortable, set `scripts/hippocampus-perm.mode` to `acceptEdits`; then it only reports what it would write.
- **Not for teams yet**, and Claude Code only.

## Reference

<details><summary><b>Recall details (thalamus)</b></summary>

Hooks are registered for SessionStart, UserPromptSubmit, PreToolUse (Edit, Write, MultiEdit, NotebookEdit, Bash, AskUserQuestion), PostToolUse (Read), PostToolUseFailure (Bash), SubagentStart, Stop, PreCompact and SessionEnd. They act only inside registered projects.

| Hook | Clue |
|---|---|
| SessionStart | Project gist, project `INDEX.md` (2,500 chars max), procedure cards |
| PostToolUse (Read) | Name of the file opened |
| PreToolUse (Edit, Write) | File to edit, APIs newly called in the edit |
| PreToolUse (Bash) | Files the command reads or writes, APIs in inline code |
| PostToolUseFailure (Bash) | C# compiler error file and code, exception name and first project frame |
| Stop, PreCompact, SessionEnd | No recall; starts a replay if enough new conversation piled up |

- 1-2 items at a time (Bash: 1), 240 chars each, at most 40 items or 9,000 chars per session. Each memory appears once per session.
- A clue matching 4+ different memories is treated as too common and only kept when the file name contains it.
- When more memories match than fit, recently used ones win (+2 within 14 days, +1 within 45 days).

Measured by replaying 431 past sessions and having Sonnet judge 371 recalls: interruptions were 0-3% for file reads, 8-20% for edits and about 10% for command files, so those are used. Request text (64%), "doesn't work" conclusions (75%) and CLI names (64%) were too noisy and are not used.
</details>

<details><summary><b>Memory store (cortex)</b></summary>

```
cortex/
├── registry.md            # path prefix, project slug, stack, stack version, note
├── common/                # stack-independent memories (tool pitfalls, general rules)
├── stacks/<stack>/        # engine or framework knowledge
└── projects/<slug>/       # project-specific (structure, entry points, conventions)
```

Layers split by "how far does this fact generalize". Each layer has thin indexes; the first link on an index line is the memory body. Only knowledge that cost real investigation or that only the user can tell is recorded; anything you can confirm in seconds by opening the code is not.
</details>

<details><summary><b>Recording, sleep, forgetting and strength</b></summary>

| | awake | sleep |
|---|---|---|
| Starts | End of turn, before compaction, session end | Daily at 04:30 (or `/claude-brain-sleep`) |
| Takes | New conversation since the last mark | Segments not handled while awake |
| Gate | 4,000+ bytes and salience 6+ (3+ before compaction or at session end); once per 20 min per log | Salience 6+, top 4 |

Salience adds up user corrections (3), decisions (3), "remember this" (5), permission denials (2), tool failures (1, max 5), repeated searching (1, max 3) and long sessions (1).

The nightly cycle: strength stats → forgetting → replay of leftovers → search-miss learning → tidy-up of the 3 least recently tidied slices → checks.

Forgetting: a memory's last use is the latest of recall, open, search hit, edit and install date. After 45 days (120 for memories mentioning user decisions, pitfalls, incidents or losses) its index line moves to `dormant.md`. The body stays and is still searchable; if used again it moves back. Nothing is hard-deleted.

`cortex/.hippocampus/strength.json` keeps `{shown, opened, grepped, last}` per memory, used for forgetting, ranking and tidy-up decisions.
</details>

<details><summary><b>Hippocampus permissions</b></summary>

The hippocampus runs with `bypassPermissions` by default (`scripts/hippocampus-perm.mode`): it is a non-interactive `claude -p` process and Claude Code treats `~/.claude/` as a protected path, so without it every write would wait for an approval nobody can give.

- It applies only to the hippocampus process. Your sessions keep their permissions.
- Tools are limited to Read, Write, Edit, Grep, Glob, Bash, WebFetch and WebSearch; no MCP servers or skills.
- Deny rules block git writes, `rm`, `sudo`, `find -delete`, and editing `settings.json`, `CLAUDE.md`, hooks and any skill's code (including this one). Deny rules hold even in this mode.
- To turn it off: `echo acceptEdits > ~/.claude/skills/brain/scripts/hippocampus-perm.mode`. Items then end as `denied` and their verdicts stay in `hippocampus-ctl.sh results`.
</details>

<details><summary><b>Measurements behind the design</b></summary>

| Fact | Source |
|---|---|
| Hooks can add context at SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, PostToolUseFailure and Stop | Isolated runs, Claude Code 2.1.283, 2026-09-29 |
| Commanding hook text ("you must…") was treated as possible prompt injection and not followed | Same experiment |
| Without the `CLAUDE.md` line, `[memory]` messages were ignored as unknown insertions | Same day |
| A forced "check notes before editing" rule was skipped in 1,264 of 6,300 Edit/Write calls and 290 of 893 Bash writes | Gate logs before brain (shadow mode) |
| Maintenance never ran when the session had to trigger it: 668 queue items, 322 records, 0 tidy-ups | Queue history before brain |
| App Haiku calls: 38 s / $0.024 with thinking on, 6 s / $0.004 with it off | 2026-10-05 |
</details>

<details><summary><b>Folder layout and requirements</b></summary>

```
brain/
├── SKILL.md, commands/        # /brain control panel and /claude-brain-* command templates
├── agents/hippocampus.md      # hippocampus instructions
├── scripts/                   # thalamus.py (hooks), nbsearch.py (search), hippocampus-*.sh, sleep.sh,
│                              # persona.py (persona compiler), lang.py (languages), plat.py (OS differences), install.sh …
├── editor/                    # the brain app (server.py + web/)
├── promo/                     # promo video tooling (demo brain, recorder)
├── cortex/                    # memories (grows on your machine, git-ignored)
└── .active/                   # runtime state (git-ignored)
```

| | |
|---|---|
| Claude Code | 2.1.28x or later (verified on 2.1.283) |
| Python | 3.7+ (`python3`, `python` or `py`) |
| `claude` CLI | On PATH (the hippocampus and the app call it) |
| Shell | bash 3.2+. On Windows, Git Bash (Git for Windows) |
| App window | Chrome (macOS, Linux) or Edge (Windows) app mode; otherwise your default browser |
| OS | macOS (built and measured here), Windows (beta), Linux (works; schedule sleep with cron) |
</details>

<details><summary><b>Relationship with n-worker</b></summary>

brain was split out of [n-worker](https://github.com/FuJiGraphics/n-worker), where its predecessor lived as a notebook with a curator daemon. Each works without the other. With both installed, n-worker sessions also receive `[memory]` messages and use them as input.
</details>

## License

[CC BY-ND 4.0](LICENSE). Copyright (c) 2026 Cheol Jin Choi (FuJiGraphics).

Commercial use and redistribution of the unmodified work are allowed with attribution (author, repository URL, license). Distributing modified versions is not allowed without permission. Memories that grow on your machine are yours and are not covered by this license.

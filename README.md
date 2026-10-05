<h1 align="center">brain</h1>
<p align="center"><b>A long-term memory skill that lets Claude Code remember what it figured out last time</b></p>

<p align="center">
  <b>English</b> · <a href="README.ko.md">한국어</a> · <a href="README.ja.md">日本語</a> · <a href="README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-CC%20BY--ND%204.0-lightgrey.svg" alt="CC BY-ND 4.0"></a>
  <a href="https://claude.com/claude-code"><img src="https://img.shields.io/badge/Claude%20Code-Skill-d97757?logo=anthropic&logoColor=white" alt="Claude Code skill"></a>
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20(beta)%20%7C%20Linux-lightgrey" alt="platforms">
  <img src="https://img.shields.io/badge/lang-EN%20%7C%20KO%20%7C%20JA%20%7C%20ZH-blue" alt="languages">
</p>

<p align="center">
  <a href="https://cdn.jsdelivr.net/gh/FuJiGraphics/claude-brain@media/brain-promo-en-720p.mp4">
    <img src="https://raw.githubusercontent.com/FuJiGraphics/claude-brain/media/brain-promo-en-preview.gif" alt="brain app preview" width="720">
  </a>
  <br><sub>▶ <a href="https://cdn.jsdelivr.net/gh/FuJiGraphics/claude-brain@media/brain-promo-en-720p.mp4">Watch the 1-minute video</a> (the projects and memories on screen are made-up demo data)</sub>
</p>

If you have worked with Claude Code on the same project for a few weeks, you have probably explained the same thing twice: a pitfall you tracked down together last week, or a rule you settled on two months ago. And when you forget to explain it, the same mistake tends to come back.

brain quietly picks those things out of your conversations and keeps them. Later, when Claude opens a file, runs a command or hits an error that a memory is about, brain hands that memory to Claude. You don't have to ask for it, and every memory file stays on your machine as plain Markdown.

```bash
git clone --single-branch https://github.com/FuJiGraphics/claude-brain.git ~/.claude/skills/brain
bash ~/.claude/skills/brain/scripts/install.sh
```

After installing, open Claude Code in the project you are working on and type `/claude-brain-register` once. brain starts collecting memories for that project right away. From then on, just use Claude Code as usual, and type `/claude-brain-app` whenever you are curious what it has learned.

## What changes after you install it

**You stop repeating yourself.** For example, right as Claude is about to edit your payment code, brain hands it something it verified before:

```
[memory] What I remember about `PaymentClient` (facts verified in the past - the current code may differ).
- Payment retries reuse the idempotency key - creating a new one causes double charges (projects/shop/lessons/payment-retry-reuses-key.md)
```

At the start of a session it lays out the project's memory map (its index) once. While you work, it hands over only the one or two memories that match the moment, and adds nothing when nothing matches. That is quite different from loading a long document into every session.

**Memories build up without you asking.** A separate agent that runs outside your sessions (brain calls it the *hippocampus*) reviews your transcripts and writes down only what is worth keeping, with evidence: your corrections, your decisions, causes that took a long time to find.

**Memory tidies itself.** Every night it merges overlapping memories and tucks away the ones nobody has used for 45 days, without deleting them. Important ones, like decisions and pitfalls, stay for 120 days.

**You can see it and fix it.** In the brain app you can watch a brain grow for each project, read the AI's terse notes in plain words, and correct a wrong memory with one tap.

<p align="center">
  <img src="https://raw.githubusercontent.com/FuJiGraphics/claude-brain/media/brain-shots-en.png" alt="brain app - a project's brain, plain-word explanations, asking the brain, persona" width="100%">
</p>

## Does it really make a difference?

We had Claude build the same feature twice in a real project: once with brain and once without it. The model, the request and the starting commit were identical. Two Opus 5.5 reviewers scored the results blind, without knowing which run was which.

<p align="center">
<picture><source media="(prefers-color-scheme: dark)" srcset="benchmarks/2026-09-30/score-dark.svg"><img src="benchmarks/2026-09-30/score-light.svg" alt="Review scores" width="720"></picture>
</p>

| | Case 1: spinning-wheel minigame | Case 2: pinball minigame |
|---|---|---|
| Review score (out of 50, average of 2 reviews) | **brain 34** / plain 29 | **brain 30.5** / plain 22 |
| Reviewers' pick | brain 2 / 2 | brain 2 / 2 |
| Time | 9.9 min / 6.9 min | 13.9 min / 4.7 min |
| Cost (at API prices) | $2.98 / $1.96 | $3.37 / $1.12 |

The difference came from knowledge that was not written down in the code or the docs.

- A rule that only lived in a conversation: in this project, sheet data comes in as TSV. That was decided in a chat two months earlier and is written nowhere in the repository. The brain run followed it; the plain run edited a local JSON file directly.
- Pitfalls that were expensive to find: there were two of them, and the brain run avoided both while the plain run hit both. "Reopening a cached popup skips initialization" was one.
- Where the feature belongs: the brain run wired the manager, popup and rewards into the existing event flow. The plain run built a standalone minigame.

In return, brain took more time and money (1.4 to 3.0 times the time, 1.5 to 3.0 times the cost). Most of that went into reading and checking memories, and in case 2 the brain run also did about twice as much work because it connected the existing event flow. The payoff is in projects that last weeks, not in one-off scripts.

<details><summary>Method and limits</summary>

- Both runs used Sonnet 5.5 at medium effort.
- The plain run used `claude -p --restricted` with CLAUDE.md, auto memory and user settings all off, so it could only read the repository. The brain run had the same setup plus the brain hooks and its one memory line. We checked the transcripts to confirm memories reached only the brain run.
- Two Opus 5.5 reviewers scored conventions, reuse of existing structure, duplication, correctness and completeness.
- Two cases, one run each, so please treat it as an early signal, not a statistically settled result. In a "plan once" test on the same day (18 real tasks, 3 models) there was no quality difference; a one-shot plan rarely needs this kind of context.
- Raw data: [`benchmarks/2026-09-30/results.json`](benchmarks/2026-09-30/results.json)

</details>

## How is it different from other approaches?

The biggest difference is **when, and on whose judgement,** a memory enters the context. Compiled from each project's official documentation as of October 2026.

| | Who writes memories | How they come back | Tidying and forgetting | Where they live |
|---|---|---|---|---|
| **brain** | A background agent, from transcripts (+ your feedback) | **Automatically, per file, command and error**, at the moment they matter | Nightly merging, hiding, usage counts, link checks | Local Markdown |
| `CLAUDE.md` / rules | You (or Claude when asked) | Loaded whole at session start | None | Local files |
| Claude Code auto memory | Claude, during the session | Start of `MEMORY.md` at startup, topic files when Claude reads them | Prompted to tidy near the limit | Local |
| [claude-mem](https://github.com/thedotmack/claude-mem) | Hooks collect, a worker summarizes | Recent sessions injected at start, MCP search | None documented | Local SQLite |
| [Mem0 MCP](https://docs.mem0.ai/platform/mem0-mcp) | The agent calls `add_memory` | The agent has to search | OSS only adds | Cloud or self-hosted |
| [Basic Memory](https://github.com/basicmachines-co/basic-memory) | The agent writes notes over MCP | The agent has to search | Manual | Local Markdown |
| [MCP memory server](https://github.com/modelcontextprotocol/servers/tree/main/src/memory) | The agent creates entities | The agent has to read or search | None | Local JSONL |
| [Cline Memory Bank](https://docs.cline.bot/customization/memory-bank) | Cline, when you say "update memory bank" | Reads all files every task | None | Project Markdown |
| [Cursor rules](https://cursor.com/docs/context/rules) | You (auto memories removed in 2.1) | Always, by description, or by glob | None | Project, dashboard |
| [Windsurf memories](https://docs.devin.ai/desktop/cascade/memories) | Cascade, automatically | When Cascade judges them relevant | None documented | Local |
| [Copilot Memory](https://docs.github.com/en/copilot/concepts/agents/copilot-memory) | Copilot, with cited evidence | Validated against the current branch before use | Expire after 28 days unused | GitHub servers |

Which one should you use? A few rules that every session needs are best kept in `CLAUDE.md`. brain sits next to it and takes care of what is hard to fit there: hundreds of small pitfalls and decisions. If several tools or several people need to share one memory, an MCP memory such as Mem0 or Basic Memory is a better fit; brain works on one machine and only with Claude Code.

## The brain app

Type `/claude-brain-app` and a small phone-shaped window opens. It runs as a Chrome or Edge app window and cannot be reached from outside this computer.

<p align="center">
  <img src="https://raw.githubusercontent.com/FuJiGraphics/claude-brain/media/en-home.png" alt="brain app home" width="300">
  &nbsp;
  <img src="https://raw.githubusercontent.com/FuJiGraphics/claude-brain/media/en-persona.png" alt="Choosing a persona" width="300">
</p>

- A brain for every project: it grows from egg to baby, kid, adult and sage as memories pile up. Its mood follows the real state of things: head weight, hippocampus failures, sleep and learning.
- Bubbles: the topics this brain cares about most, in a few words. Tap one to gather those memories.
- Plain-word explanations: notes written by an AI are short and dense. Open a memory and you first get a one-line summary, why it is remembered, when it comes up, and the jargon explained.
- Feedback: each memory comes with a question like "Do deploys still go through the release script?". Tap "Yes, still right", "It changed", "Important" or "No longer needed". Your answers wait in a mailbox until you tap "Send all to the hippocampus", and the app lets you know once they have been applied.
- Ask: chat with your project's brain. It answers only from its memories and shows which ones it used.
- Feed and tidy up: tell it something it must remember, or ask the hippocampus to tidy up when the head gets heavy.
- Projects brain doesn't know yet: folders you recently worked on with Claude Code that are not registered. Tap "Hatch" and the project's brain appears within a minute or two.
- Dormant memories and the archive: memories tucked away for lack of use show up as "sleeping memories" in the memory list, and memories the hippocampus let go while tidying wait in the archive, where you can bring them back.
- Rest: let brain take a break in one project only.
- Usage and backup: settings show how much Claude usage brain spent this week, and can back up your memories into one zip.

The app never edits memory files itself. Feeding, feedback and tidy-up requests all go into the hippocampus's job queue, so the hippocampus is always the only one that changes memory files.

### Persona: how Claude works in this project

You can choose how Claude works in each project. Pick a breed (squirrel: fast, owl: plans and checks, cat: asks and suggests, turtle: slow but precise), or wire traits to situations yourself.

| Strength | What happens |
|---|---|
| light | One sentence at the start of the session |
| normal | Plus a one-line reminder with every request |
| must! 🔒 | Plus the hooks enforce it: Claude has to ask you before `rm -rf`, `push --force`, `reset --hard` or a deploy, and if it tries to finish without a build or test, it gets sent back once |

What you see in the preview is exactly what Claude receives.

## Commands

Most of them are handled by the hook directly and use no tokens. Output follows the language you set.

| Command | What it does |
|---|---|
| `/claude-brain-app` | Open the brain app |
| `/claude-brain-status` | On or off, hippocampus jobs and failures, last nightly tidy-up, recent recalls, usage this week |
| `/claude-brain-register` | Register this project right now |
| `/claude-brain-on`, `/claude-brain-off` | Turn brain on or off. Add `here` to affect only this project |
| `/claude-brain-config [default\|eco\|quality]` | Hippocampus model: Sonnet medium / Sonnet low / Opus high. Also `lang en` and so on |
| `/claude-brain-model`, `/claude-brain-effort` | Set the hippocampus model and effort separately |
| `/claude-brain-remember <what>` | Tell brain something to remember |
| `/claude-brain-recall <name>...` | Look up memories by file, symbol, API, error or symptom |
| `/claude-brain-sleep` | Run the nightly tidy-up now |
| `/claude-brain-results` | See what the hippocampus did |
| `/claude-brain-stop` | Stop the hippocampus after its current job |
| `/claude-brain-update` | Get the new version (memories stay untouched) |
| `/claude-brain-backup` | Back up memories and personas into one zip |

## Cost and privacy

- Recall makes no extra API calls. It does add context, though: the project's memory map at session start (about 6,000 characters at most), a one-line habit reminder with each request, and the memories recalled while you work (about 2,000 characters per session on average, capped at 9,000). Altogether that came to about 15,000 characters per session (roughly 4,000 to 5,000 tokens) on the author's machine. Each hook call takes about 25 ms.
- The hippocampus uses your Claude usage. It runs `claude -p` once per job (Sonnet 5.5 at medium effort by default). On the demo memory store we measured $0.06 to $0.13 per recording job and $0.05 to $0.11 per tidy-up job, at API prices. Real projects with more memories cost a bit more. To spend less, try `/claude-brain-config eco`.
- The app's AI features (bubbles, plain-word explanations, asking) call Claude Haiku at about $0.002 to $0.004 per call. Explanations are cached.
- You can check what was spent at any time in `/claude-brain-status` or in the app's "Usage" card. On a Pro or Max plan this is a measure of how much was used, not what you are billed.
- Memory files are stored only on this computer. When your Claude sessions, the hippocampus or the app call Claude, the relevant memory text goes into the prompt and is sent to the Anthropic API. The hippocampus may also search or read the web when it needs to check something (WebFetch, WebSearch). Apart from that, brain checks for a new version once a day (`git fetch`); add `update_check=0` to `~/.claude/skills/brain/.active/config` if you don't want that. The app listens on `127.0.0.1` only, with a fresh token every launch.
- Nobody is around to approve prompts for a background job, so the hippocampus runs with approval prompts off. To make up for it, deny rules block git writes, `rm`, `sudo`, and edits to settings files or other skills. See [Hippocampus permissions](#hippocampus-permissions) below.

## Install, update, back up

```bash
git clone --single-branch https://github.com/FuJiGraphics/claude-brain.git ~/.claude/skills/brain
bash ~/.claude/skills/brain/scripts/install.sh
```

On Windows, run the same two lines in Git Bash (the shell Claude Code uses). Running the installer again gives the same result, and every settings file it changes is backed up as `<file>.brain-bak-<time>`. Here is what it does:

1. Registers the brain hooks in `~/.claude/settings.json` and leaves other hooks alone. brain's hooks always exit cleanly, so unless you set a persona trait to "must!", brain never blocks a tool call.
2. Adds a `[BRAIN]` badge to the end of your Claude Code status line, keeping your existing status line as it is.
3. Adds one line to `~/.claude/CLAUDE.md` explaining what `[memory]` messages are. In our tests, without it Claude treated memories as text of unknown origin and ignored them.
4. Schedules the nightly tidy-up for 04:30 (launchd on macOS, Task Scheduler on Windows). On Linux, add `scripts/sleep.sh` to cron yourself.
5. Creates the `/claude-brain-*` commands and picks a language from your OS.

### Registering projects

brain only works inside registered projects. Git folders where you had 3 or more sessions and 10 or more requests in the last 7 days are registered automatically, one per night. To start right away, type `/claude-brain-register` in that folder, or tap "Hatch" under "Projects brain doesn't know yet" in the app.

### Updating

Type `/claude-brain-update` to get the new version and rerun the installer. If you have edited files by hand, it stops and tells you instead of overwriting them. When a new version is out, the app's home screen and `/claude-brain-status` let you know.

<details><summary>Installed before October 5, 2026? (one time only)</summary>

Older versions kept part of the memory folder (`cortex/`) under git, so `git pull` stops with a conflict. Run this once and your memories move to the new layout untouched:

```bash
cd ~/.claude/skills/brain
cp -R cortex .active/cortex-backup          # copy your memories first
git checkout -- cortex && git pull          # get the new version
cp -R .active/cortex-backup/. cortex/       # put your memories back
bash scripts/install.sh
```

From then on, `/claude-brain-update` is all you need.
</details>

### Backing up and moving to another computer

`/claude-brain-backup` (or Backup in the app's settings) packs memories and personas into one zip in `~/Downloads`. On the new computer, install brain and run `bash ~/.claude/skills/brain/scripts/backup.sh restore <zip path>`. Any memories already there are moved to `.active/before-restore-<time>/` first, and if your home folder path is different, project paths are updated for you. Restoring is refused while the hippocampus is working, so stop it first with `/claude-brain-stop` if needed.

### Uninstalling

`bash ~/.claude/skills/brain/scripts/install.sh --uninstall` removes the hooks, the status line badge, the CLAUDE.md line, the command files and the nightly schedule, and stops the hippocampus. Your memories stay until you delete the folder.

## FAQ

**Isn't `CLAUDE.md` enough?** For the handful of rules every session needs, `CLAUDE.md` is the best place. But it is loaded whole every time, written by hand, and never tidies itself. brain takes care of the hundreds of small pitfalls and decisions that are hard to fit into `CLAUDE.md`, and brings out only what matches the file or error at hand.

**Should I keep Claude Code's auto memory on?** We recommend turning it off by adding `"autoMemoryEnabled": false` to `~/.claude/settings.json`. Auto memory has nothing that corrects wrong notes and is loaded in every session, so stale notes can clash with brain's newer memories.

**What if a memory is wrong?** Open it in the app, tap "It changed", write how things are now, and send it from the mailbox. The hippocampus checks and fixes it. Every memory carries the date it was verified, and when it disagrees with the current code, the current code always wins.

**Won't memory grow forever?** Every night overlapping memories are merged and unused ones are tucked away (they can still be found by search). The app's "head weight" tells you when a tidy-up is due.

**Can I turn it off for one project only?** Type `/claude-brain-off here` in that folder, or switch on "Rest in this project" on the project's page in the app. Memories stay as they are.

**Can a team share it?** Not yet. Memories live on each machine. You can move them with a backup zip, but brain was not designed for several people writing at once.

**Does it work in Cursor or Codex?** Unfortunately not. It is built on Claude Code's hooks.

**Which languages are supported?** The app, command output, installer messages, session text and personas come in English, Korean, Japanese and Chinese. Memories are written in the language you talk in, and signals such as corrections and decisions are recognized in all four. Change the language in the app's settings or with `/claude-brain-config lang ja`.

**Can I see what went into a session?** `/claude-brain-status` shows recall counts and characters for the last 24 hours, and `~/.claude/skills/brain/.active/recall.log` keeps every event.

## Good to know

- Measurements come from one person's projects (macOS, mostly Unity/C# and a VS Code extension). The rules for pulling clues out of errors were tuned on C# compile errors. Recall by the names of files you open or edit works in any language. Inside commands, brain recognizes source and config file extensions of common languages, and API names written as capitalized dotted calls such as `PaymentClient.Charge(`.
- Windows support is in beta. Paths, hooks, Task Scheduler and the app were ported and reviewed, but it has not seen much use on real Windows machines yet. If something breaks, an issue would be greatly appreciated.
- It spends more time and tokens on context-heavy work (see the benchmark above).
- The hippocampus is an unsupervised agent on your computer. It has deny rules, but if that makes you uneasy, you can set `scripts/hippocampus-perm.mode` to `acceptEdits`. Be aware that the hippocampus then cannot write memory files, so brain stops learning (recall keeps working).

## How it works

The names are borrowed from the brain.

| Part | In the human brain | In this skill |
|---|---|---|
| **cortex** | Cerebral cortex, consolidated long-term memory | The Markdown memory store, in three layers (`common/`, `stacks/<stack>/`, `projects/<slug>/`), each with thin indexes and memory files |
| **thalamus** | Thalamus, filters senses up to consciousness | The hook. Hands over memories that match the current file, command or error, and lays out the project map at session start |
| **hippocampus** | Hippocampus, forms new memories | A background `claude -p` worker and the only writer to cortex: registering, recording, replaying, tidying |
| **sleep** | Sleep, consolidates and forgets | Every night: usage counts, forgetting, replaying leftover conversation, learning from failed searches, tidying, checks |

```
[recall - inside the session]
tool call ─ hook ─▶ thalamus ─▶ matching memories in cortex ─▶ a [memory] message enters the session

[record - outside the session]
end of turn, before compaction, end of session ─▶ thalamus ─▶ replay (awake) ──────┐
every day at 04:30 ─▶ sleep ─▶ replay, failed-search learning, tidy-up ─────────────┴─▶ queue ─▶ hippocampus ─▶ cortex
```

The transcripts Claude Code already writes serve as short-term memory. Each stretch of conversation is processed once.

<details><summary><b>Recall: the thalamus</b></summary>

The hooks run on SessionStart, UserPromptSubmit, PreToolUse (Edit, Write, MultiEdit, NotebookEdit, Bash, AskUserQuestion), PostToolUse (Read), PostToolUseFailure (Bash), SubagentStart, Stop, PreCompact and SessionEnd, and only inside projects registered in `cortex/registry.md`.

| Hook event | Clues |
|---|---|
| SessionStart | Project gist, the project's `INDEX.md` (capped at 3,000 chars), the stack and shared indexes (2,000 and 1,200 chars), procedure-card lines |
| UserPromptSubmit | A one-line habit reminder to open the index for the area you are about to work on |
| PostToolUse (Read) | Name of the file opened |
| PreToolUse (Edit, Write, MultiEdit, NotebookEdit) | Name of the file being edited, API names new in the edit |
| PreToolUse (Bash) | Files the command reads or writes, API names in code inside the command |
| PostToolUseFailure (Bash) | File and error code of C# compile errors, exception names and the file of the first project frame |
| SubagentStart | The working folder's project and a line on what `[memory]` means |
| Stop, PreCompact, SessionEnd | No recall; starts a replay if the new stretch of conversation stands out |

- When nothing matches, nothing is printed. At most 1 or 2 memories at a time (1 for Bash), 240 characters each, and 40 memories or 9,000 characters per session (the session-start map is counted separately).
- A clue that matches 4 or more different memories is treated as too common; only memories with that clue in their file name are kept.
- We replayed 431 past sessions and had Sonnet judge 371 recalls. brain recalls only where the share judged "distracting" was low: file reads (0 to 3%), right before edits (8 to 20%) and files touched by commands (about 10%). It does not use request text (64%), "it doesn't work" conclusions (75%) or CLI names inside commands (64%) as clues.
</details>

<details><summary><b>Recording, sleep and forgetting</b></summary>

| | Awake | Sleep |
|---|---|---|
| Starts | In the background at end of turn, before compaction, at end of session | Daily at 04:30; once after waking if missed; now with `/claude-brain-sleep` |
| Covers | Conversation added since the last processed position | Stretches not handled while awake |
| Conditions | 4,000 bytes or more and salience 6 or more (3 or more before compaction and at end of session). Once per 20 minutes per transcript (not limited before compaction or at end of session), 4 per hour overall | Salience 6 or more, top 4 |

Salience: user correction 3, decision wording 3, request to remember 5, permission denial 2, tool failure 1 (up to 5), repeated investigation 1 (up to 3), and 1 when there are 5 or more requests. Corrections, decisions and requests to remember are recognized in English, Korean, Japanese and Chinese.

Each night, sleep runs these steps in order: usage and failed-search counts, forgetting, replaying leftover stretches (up to 4) and registering one active unregistered project, failed-search learning, tidying the 3 slices left longest, and a check. To change the defaults, create `scripts/sleep.conf` with lines such as `FORGET_DAYS=60`.

45 days after a memory was last used (120 days for decisions, pitfalls and incidents), its index line moves to `dormant.md`. The body stays and can still be found by search; if it is used again, it returns to its index. Memories the hippocampus lets go while tidying move to `_archive/` and can be brought back from the app's archive. Nothing is ever hard-deleted.
</details>

<a name="hippocampus-permissions"></a>
<details><summary><b>Hippocampus permissions</b></summary>

> [!IMPORTANT]
> By default the hippocampus runs without approval prompts (`bypassPermissions` in `scripts/hippocampus-perm.mode`). When brain lives under `~/.claude/skills/`, its memory folder does too, and Claude Code treats `.claude/` as a protected path that needs approval for every edit. The hippocampus is a non-interactive `claude -p`, so there is nobody to approve.

- This applies only to the hippocampus process. Your own sessions keep their permissions.
- Tools are limited to Read, Write, Edit, Grep, Glob, Bash, WebFetch and WebSearch, with no MCP servers or other skills attached.
- Git writes (`commit`, `push`, `checkout`, `reset` and so on), `rm`, `sudo`, `find -delete`, and edits to other skills, `settings.json`, `CLAUDE.md` and `hooks/` are blocked by deny rules, which still apply in this mode.
- To turn it off, run `echo acceptEdits > ~/.claude/skills/brain/scripts/hippocampus-perm.mode`. Memory writes are then all denied (`denied`), only verdicts are left, and brain stops learning.
</details>

<details><summary><b>Measurements behind the design</b></summary>

| Finding | Source |
|---|---|
| Hook text written as commands was suspected as prompt injection and not followed | Isolated runs on Claude Code 2.1.283, 2026-09-29 |
| Without the `CLAUDE.md` line, `[memory]` was ignored as text of unknown origin | Same day |
| A forced "check your notes before editing" rule was skipped in 20% of 6,300 Edit/Write calls and 32% of 893 Bash writes | Gate logs from the earlier design |
| Maintenance that a session had to ask for never ran (668 queued jobs: 322 records, 0 tidy-ups) | Queue logs from the earlier design |
| The app's Haiku calls took 38 s and $0.024 with thinking on, 6 s and $0.004 with it off | 2026-10-05 |
</details>

<details><summary><b>Folder layout and requirements</b></summary>

```
brain/
├── SKILL.md, commands/        # control panel, /claude-brain-* command templates
├── agents/hippocampus.md      # hippocampus guide
├── scripts/                   # thalamus.py (hook), nbsearch.py (search), hippocampus-*.sh, sleep.sh, install.sh,
│                              # update.py, backup.py, register.py, persona.py, lang.py, cli_i18n.py, plat.py …
├── editor/                    # the brain app (server.py + web/)
├── seed/cortex/               # memory store skeleton used on first install
├── promo/                     # promo video and screenshot tools (a made-up demo brain)
├── cortex/                    # memories (grow on this computer, not tracked by git)
└── .active/                   # runtime state (not tracked by git)
```

| | |
|---|---|
| Claude Code | 2.1.28x or later (verified on 2.1.283) |
| Python | 3.7 or later (`python3`, `python` or `py`) |
| `claude` CLI | On your PATH (the hippocampus and the app call it) |
| Shell | bash 3.2 or later; Git Bash on Windows |
| App window | Chrome (macOS, Linux) or Edge (Windows) app mode, otherwise your default browser |
| OS | macOS (built and measured there), Windows (beta), Linux (works; schedule the nightly tidy-up with cron) |
</details>

## License

[CC BY-ND 4.0](LICENSE) (Attribution-NoDerivatives 4.0 International). Copyright (c) 2026 Cheol Jin Choi (FuJiGraphics).

| | |
|---|---|
| Commercial use | Allowed, including at work and inside paid services |
| Sharing and redistribution | Allowed, as long as it is unmodified |
| Distributing modified versions | Not allowed, including edited or partial versions |
| Attribution | Please credit the author, the repository (https://github.com/FuJiGraphics/claude-brain) and the license |

If you would like to distribute a modified version, please contact the author. The memories that grow on your computer belong to you and are not covered by this license.

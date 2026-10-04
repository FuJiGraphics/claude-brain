<h1 align="center">brain</h1>
<h3 align="center">make Claude Code remember!</h3>

<p align="center">
  <a href="README.md">English</a> · <a href="README.ko.md">한국어</a> · <a href="README.ja.md">日本語</a> · <b>简体中文</b>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-CC%20BY--ND%204.0-lightgrey.svg" alt="CC BY-ND 4.0"></a>
  <a href="https://claude.com/claude-code"><img src="https://img.shields.io/badge/Claude%20Code-Skill-d97757?logo=anthropic&logoColor=white" alt="Claude Code skill"></a>
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20(beta)%20%7C%20Linux-lightgrey" alt="platforms">
  <img src="https://img.shields.io/badge/lang-EN%20%7C%20KO%20%7C%20JA%20%7C%20ZH-blue" alt="languages">
  <a href="#基准测试"><img src="https://img.shields.io/badge/blind%20review-2%2F2%20wins-2a78d6" alt="benchmark"></a>
</p>

<p align="center">
  <a href="https://cdn.jsdelivr.net/gh/FuJiGraphics/claude-brain@media/brain-promo-zh-720p.mp4">
    <img src="https://raw.githubusercontent.com/FuJiGraphics/claude-brain/media/brain-promo-zh-preview.gif" alt="brain 应用预览" width="720">
  </a>
  <br><sub>▶ <a href="https://cdn.jsdelivr.net/gh/FuJiGraphics/claude-brain@media/brain-promo-zh-720p.mp4">观看 60 秒完整视频</a>(虚构的演示数据)</sub>
</p>

**brain 是给 Claude Code 用的、自己会运转的长期记忆。**
当 Claude 打开以前学到过东西的文件、运行命令或遇到错误时,那段记忆会自动浮现到会话中。新的记忆在会话之外从对话记录中生成,每晚整理一次,过时的会被遗忘。Claude 不需要"记得去记"。

```bash
git clone --single-branch https://github.com/FuJiGraphics/claude-brain.git ~/.claude/skills/brain
bash ~/.claude/skills/brain/scripts/install.sh
```

安装后,在 Claude Code 中输入 **`/claude-brain-app`** 打开应用。

**目录** · [为什么需要](#为什么需要) · [有何不同](#有何不同) · [基准测试](#基准测试) · [与其他方案比较](#与其他方案比较) · [brain 应用](#brain-应用) · [工作原理](#工作原理) · [安装](#安装) · [命令](#命令) · [成本与隐私](#成本与隐私) · [常见问题](#常见问题) · [局限](#局限) · [参考资料](#参考资料) · [许可证](#许可证)

---

## 为什么需要

在同一个项目里用 Claude Code 工作几周,你会一次次为同样的教训买单:

- **每个会话都从零开始。** 两个月前定下的团队规则、浪费了一个下午的陷阱、这个功能在整体中的位置。要么再解释一遍,要么被漏掉然后出问题。
- **"先看看笔记"并不管用。** 在作者的记录中,编辑前必须对照笔记的强制规则,在 **6,300 次 Edit/Write 中有 20%、893 次 Bash 写入中有 32%** 没被遵守。
- **等着被调用的记忆工具不会被调用。** 如果要由智能体自己决定是否搜索,它在"不知道自己不知道"的时候搜索得最少。
- **笔记会腐烂。** 没有人去合并、更正、淘汰,笔记就会堆积、互相矛盾,并且每次会话都被整个加载。

brain 把这些全部移到会话之外。会话什么都不用做,记忆自己会浮现。

```
Claude 准备编辑 src/Payment/PaymentClient.cs 的那一刻进入会话的消息(示例)

[记忆] 关于 `PaymentClient` 记得的内容(过去确认过的事实,可能与当前代码不同)。
- 支付重试要复用幂等键 - 新建会导致重复扣款 (projects/shop/lessons/payment-retry-reuses-key.md)
```

## 有何不同

| | |
|---|---|
| 🧠 **不用问也会想起** | 钩子查看正在读取或编辑的文件、新调用的 API、命令涉及的文件、刚出现的编译错误,只把与之相关的记忆交给会话。没有匹配就什么都不加。 |
| 🌙 **在会话之外学习** | 一个独立运行的智能体(*海马*)回顾对话记录,附上依据写入记忆。会话不会为记录花一个回合。 |
| 🧹 **会睡觉、巩固和遗忘** | 每晚统计每条记忆的使用情况,把 45 天(决定和陷阱为 120 天)未用的记忆隐藏而不删除,合并重复,检查失效链接。 |
| 📜 **是事实,不是命令** | 记忆以带出处的事实进入。与当前代码不一致时以当前代码为准。实测发现命令式的钩子文字会被怀疑是提示注入而被忽略,所以 brain 从不下命令。 |
| 💸 **控制在预算内** | 每次钩子约 20 毫秒,每个会话平均约 2,000 字符,并设有上限。 |
| 📱 **看得懂的应用** | `/claude-brain-app` 展示每个项目的大脑在意什么、学到了什么,还能提问、反馈、整理,以及设定工作方式。 |
| 🎭 **真正执行的性格** | 为每个项目选择 Claude 的工作方式。"一定!"的规则由钩子强制执行:难以撤销的命令前先询问,修改后不验证就不让结束。 |
| 🌐 **多语言** | 应用、写入会话的文字、性格都支持英语、韩语、日语、中文。记忆用你对话的语言积累。 |
| 📂 **就是本机的普通文件** | 记忆是 Markdown 文件。没有服务器、没有账号、不收集数据。 |

## 基准测试

**在真实项目中把同一个功能实现了两次:一次带 brain,一次不带。** 模型、需求、起始提交都相同,各自在独立复制的工作副本中真正写代码。两位不知道哪一份是 brain 的评审进行了评估。

<p align="center">
<picture><source media="(prefers-color-scheme: dark)" srcset="benchmarks/2026-09-30/score-dark.svg"><img src="benchmarks/2026-09-30/score-light.svg" alt="盲评分数" width="720"></picture>
</p>

| | 案例 1:转盘小游戏 | 案例 2:弹球小游戏 |
|---|---|---|
| 评审得分(满分 50,两人平均) | **brain 34** / 原版 29 | **brain 30.5** / 原版 22 |
| 评审选择 | brain 2 / 2 | brain 2 / 2 |
| 时间 | 9.9 分钟 / 6.9 分钟 | 13.9 分钟 / 4.7 分钟 |
| 成本(按标价) | $2.98 / $1.96 | $3.37 / $1.12 |

**差距来自代码和文档里都没有的知识。** brain 遵守了口头约定的团队规则(表格数据一律以 TSV 接收),原版 Claude 违反了;两个代价高昂的陷阱,brain 都避开了,原版都踩了;brain 还把握了功能的全局,把它接入现有的活动流程,而原版只做了一个独立的小游戏。

**代价:** brain 多花了 1.4~2.9 倍的时间和 1.5~3.0 倍的成本,用于读取和核对记忆(案例 2 的工作范围也翻了一倍)。只有两个案例、各跑一次:趋势明显,但还不是统计上的定论。在另一个"一次性制定计划"的测试中(18 个真实任务、3 种模型)没有质量差异,因为一次性的计划很少触及这类上下文。原始数据:[`benchmarks/2026-09-30/results.json`](benchmarks/2026-09-30/results.json)

## 与其他方案比较

截至 2026 年 10 月,依据各项目的官方文档整理。关键是"如何想起"这一列 - 由谁、在什么时候决定把记忆放进上下文。

| | 谁来写 | 如何想起 | 整理与遗忘 | 存储位置 |
|---|---|---|---|---|
| **brain** | 后台智能体从对话记录中写(+ 用户反馈) | **按文件、命令、错误自动想起**,就在需要的那一刻 | 每晚合并、休眠化、强度统计、链接检查 | 本地 Markdown |
| `CLAUDE.md` / rules | 用户(或要求时由 Claude 写) | 会话开始时整个加载(路径规则在读取该文件时) | 无 | 本地文件 |
| Claude Code auto memory | 会话中由 Claude 写 | 开始时加载 `MEMORY.md` 前 200 行或 25KB,主题文件在 Claude 读取时 | 接近上限时提示合并 | 本地 |
| [claude-mem](https://github.com/thedotmack/claude-mem) | 钩子收集,工作进程总结 | 开始时注入最近的会话,通过 MCP 工具搜索 | 文档未提及 | 本地 SQLite |
| [Mem0 MCP](https://docs.mem0.ai/platform/mem0-mcp) | 智能体调用 `add_memory` | 必须由智能体调用搜索 | 开源版只增不改 | 云端或自托管 |
| [Basic Memory](https://github.com/basicmachines-co/basic-memory) | 智能体通过 MCP 写笔记 | 必须由智能体调用搜索 | 手动 | 本地 Markdown |
| [MCP memory 服务器](https://github.com/modelcontextprotocol/servers/tree/main/src/memory) | 智能体创建实体 | 必须由智能体调用读取/搜索 | 无 | 本地 JSONL |
| [Cline Memory Bank](https://docs.cline.bot/customization/memory-bank) | 说"update memory bank"时由 Cline 写 | 每个任务都读取全部文件 | 无 | 项目 Markdown |
| [Cursor rules](https://cursor.com/docs/context/rules) | 用户(自动记忆已在 2.1 移除) | 始终、按描述、按 glob | 无 | 项目、控制台 |
| [Windsurf memories](https://docs.devin.ai/desktop/cascade/memories) | Cascade 自动写 | Cascade 判断相关时 | 文档未提及 | 本地 |
| [Copilot Memory](https://docs.github.com/en/copilot/concepts/agents/copilot-memory) | Copilot 写并附引用 | 使用前用当前分支验证 | 28 天未用即过期 | GitHub 服务器 |

**怎么选。** 每个会话都需要的少数规则放在 `CLAUDE.md`,brain 在旁边负责长尾。如果要在多个工具或团队之间共享同一份记忆,MCP 类记忆(Mem0、Basic Memory)更合适 - brain 是单机、仅限 Claude Code。如果项目周期长,而且代价高的知识是那种没人会写下来的(口头决定、辛苦踩出来的陷阱、"各部分怎么配合"),就选 brain。与 brain 一起使用时,建议**关闭** Claude Code 的 auto memory(见[常见问题](#常见问题))。

## brain 应用

`/claude-brain-app` 会打开一个像手机一样的小窗口(Chrome 或 Edge 的应用模式,只在本机打开)。

- **大脑们**:每个项目一个角色。记忆越多长得越大(蛋、宝宝、小朋友、大人、贤者),心情来自真实信号:脑袋重量、海马失败、睡眠、学习。
- **气泡**:用几个词表示这个大脑最在意的东西,由 Claude Haiku 根据记忆标题挑选。点一下就能集中查看那些记忆。
- **用简单的话读记忆**:AI 写的笔记像电报一样难读。打开后先显示一句话总结、为什么要记住、什么时候会想起、难懂词语的解释,原文折叠在下面。
- **是/否反馈**:每条记忆都带一个问题,比如"现在还是用 release 脚本部署吗?"。点 👍 没错、✏️ 变了、⭐ 很重要、🗑 不再需要,反馈会放进 📮 信箱,再一次性交给海马。
- **提问**:和项目的大脑聊天。它只根据记忆回答,并附上用到的记忆。
- **喂食**:告诉它一定要记住的事。
- **大脑整理**:脑袋变重时,海马会合并、精简(归档而不删除)。开始前会显示要分几次完成。
- **性格**:选一个品种(松鼠、猫头鹰、猫、乌龟),或自己把性格连到情况上。
- **日志和设置**:海马做了什么、开关、模型、语言、主题。

应用从不直接修改记忆。喂食、反馈和整理都交给海马一直在用的队列。

### 性格

性格是成对的反义(推进/谨慎、自主/好奇、快速/细致、最小/积极、简洁/亲切),连到情况上(平时、难以撤销的操作、修改代码之后、大改动、请求模糊时、陌生的代码)。强度决定推动的力度:

| 强度 | 会发生什么 |
|---|---|
| 轻 | 会话开始时一句话 |
| 普通 | 再加上每次请求时一行提醒 |
| 一定! 🔒 | 再加上由钩子强制:在 `rm -rf`、`push --force`、`reset --hard`、删库、部署之前询问你;修改超过 N 个文件前询问;不运行构建或测试就想结束时退回一次 |

性格由固定的表格编译而成,所以预览就是 Claude 实际收到的内容。

## 工作原理

| 部件 | 在大脑中 | 在 brain 中 |
|---|---|---|
| **cortex** | 大脑皮层 - 巩固的长期记忆 | Markdown 记忆库,分 `common/`、`stacks/<技术栈>/`、`projects/<项目>/` 三层,每层有轻量索引和记忆正文 |
| **thalamus** | 丘脑 - 过滤感觉送入意识 | 钩子。交出与当前文件、命令、错误相关的记忆,在会话开始时显示项目地图,在空闲时启动回顾 |
| **hippocampus** | 海马 - 形成新记忆 | 后台的 `claude -p` 工作进程,是唯一写入 cortex 的主体,负责登记、记录、回顾、整理 |
| **sleep** | 睡眠 - 巩固与遗忘 | 每晚:强度统计、遗忘、回顾剩余对话、搜索失败学习、整理、检查 |

```
[想起 - 会话之内]
工具调用 ─ 钩子 ─▶ thalamus ─▶ cortex 中匹配的记忆 ─▶ [记忆] 消息进入会话

[记录 - 会话之外]
回合结束、压缩之前、会话结束 ─▶ thalamus ─▶ 回顾(awake) ─────────────┐
每晚 04:30 ─▶ sleep ─▶ 回顾(scan)、搜索失败学习、整理 ─────────────────┴─▶ 队列 ─▶ hippocampus ─▶ cortex
```

Claude Code 本来就会写的对话记录充当短期记忆。每一段只处理一次。

## 安装

```bash
git clone --single-branch https://github.com/FuJiGraphics/claude-brain.git ~/.claude/skills/brain
bash ~/.claude/skills/brain/scripts/install.sh
```

Windows 上在 **Git Bash**(Claude Code 使用的 shell)中运行同样的两行。重复运行结果相同,修改的文件会备份为 `<文件>.brain-bak-<时间>`。安装会:

1. 在 `~/.claude/settings.json` 中注册 thalamus 钩子(不动其他钩子;所有钩子都以退出码 0 结束,brain 永远不会阻止工具调用)
2. 在 `~/.claude/CLAUDE.md` 中加一行,说明 `[记忆]` 消息是什么(没有这一行时 Claude 会忽略它们)
3. 安排每晚 04:30 的睡眠(macOS 用 launchd,Windows 用任务计划程序,Linux 请自行把 `scripts/sleep.sh` 加入 cron)
4. 创建 `/claude-brain-*` 命令
5. 按系统语言设置语言(可在应用中或用 `scripts/config.sh lang zh` 修改)

**项目会自动登记。** 夜间周期会登记最近一周有 3 天以上、10 个以上请求的 git 文件夹。想立即登记请运行 `/claude-brain-sleep`。

**更新:** `git -C ~/.claude/skills/brain pull && bash ~/.claude/skills/brain/scripts/install.sh`。记忆不受 git 跟踪,更新后仍会保留。
**卸载:** `bash ~/.claude/skills/brain/scripts/install.sh --uninstall` 会移除钩子、CLAUDE.md 中的区块和定时任务。记忆会保留,直到你删除文件夹。

## 命令

命令只在你输入时运行。大多数由钩子直接处理,不消耗 token。

| 命令 | 作用 |
|---|---|
| `/claude-brain-app` | 打开 brain 应用 |
| `/claude-brain-status` | 开关状态、海马队列与失败、上次睡眠、最近 24 小时的想起情况 |
| `/claude-brain-on`, `/claude-brain-off` | 开启、关闭(记忆保留) |
| `/claude-brain-config [default\|eco\|quality]` | 海马模型:Sonnet medium / Sonnet low / Opus high |
| `/claude-brain-model`, `/claude-brain-effort` | 细调海马的模型和 effort |
| `/claude-brain-sleep` | 立即运行夜间周期 |
| `/claude-brain-results` | 海马结果摘要 |
| `/claude-brain-stop` | 当前项目完成后停止海马 |
| `/claude-brain-recall <名称>...` | 按文件、符号、API、错误、症状搜索记忆 |
| `/claude-brain-remember <内容>` | 把要记住的内容放进队列 |

## 成本与隐私

- **想起**不调用 API。钩子是本地 Python,每次约 20 毫秒,每个会话平均增加约 2,000 字符。
- **海马**每个队列项运行一次 `claude -p`(默认 Sonnet medium),使用你的 Claude 订阅或 API 用量。作者实测中,记录项的中位数为 48 回合、9 分钟。可用 `/claude-brain-config eco` 节省。
- **应用**在生成气泡、简单解释和回答时调用 Claude Haiku(关闭思考),每次约 0.001~0.005 美元、4~6 秒,解释会缓存。
- **隐私**:记忆、日志和应用都留在本机。唯一的网络流量是 Claude Code 本来就会发出的 Claude API 调用。应用只监听 `127.0.0.1`,每次启动使用新的令牌。
- **权限**:海马在没有授权提示的情况下运行(没有人可以问),但用拒绝规则阻止 git 写入、`rm`、`sudo` 以及修改设置或其他技能。见[海马的权限](#海马的权限)。

## 常见问题

**`CLAUDE.md` 还不够吗?** 对于每个会话都需要的少数规则它很完美。但它会被整个加载、需要手写、也不会自己整理。brain 负责长尾(成百上千的陷阱和决定),只拿出与当前文件或错误相关的部分。

**要不要保留 Claude Code 的 auto memory?** 建议关闭(`"autoMemoryEnabled": false`)。两者都保存"上次弄明白的事",但 auto memory 没有人去更正、每次开始都会加载,旧内容可能覆盖新记忆。

**记忆错了怎么办?** 在应用中打开它,点 ✏️ 变了。海马会核实并修正。记忆带有确认日期,而且当前代码永远优先于记忆。

**记忆会无限变大吗?** 夜间睡眠会合并重复、隐藏不用的记忆(仍可搜索到)。应用里的"脑袋重量"会提示何时需要整理。

**团队可以共享吗?** 暂时不行。记忆是按机器保存的。你可以自己同步 `cortex/`,但它没有为多人同时写入而设计。

**能在 Cursor、Codex 等工具中用吗?** 不能。brain 构建在 Claude Code 的钩子之上。

**支持哪些语言?** 应用、写入会话的文字和性格支持英语、韩语、日语、中文。记忆用你对话的语言写入。用日语、中文症状描述来搜索,效果不如文件和符号匹配(与语言无关)。

**能看到注入了什么吗?** `/claude-brain-status` 会显示最近的想起次数和字符数,`.active/recall.log` 记录了每个事件。

## 局限

- **数据来自一个人的项目**(macOS,主要是 Unity/C# 和 VS Code 扩展)。线索提取针对 C# 编译错误做了调整;文件和 API 匹配与语言无关。
- **Windows 支持是新加入的(beta)。** 路径、钩子、任务计划程序和应用都已移植并审查,但还没有在真实的 Windows 机器上运行过。遇到问题请提 issue。
- **在上下文重要的任务上会多花时间和 token**(见基准测试)。收益以周计,而不是一次性脚本。
- **海马是在本机无人监督运行的智能体**(有拒绝规则)。如果介意,把 `scripts/hippocampus-perm.mode` 改成 `acceptEdits`,它就只记录判断而不写入。
- **暂不面向团队**,且仅限 Claude Code。

## 参考资料

<details><summary><b>想起的细节(thalamus)</b></summary>

钩子注册在 SessionStart、UserPromptSubmit、PreToolUse(Edit、Write、MultiEdit、NotebookEdit、Bash、AskUserQuestion)、PostToolUse(Read)、PostToolUseFailure(Bash)、SubagentStart、Stop、PreCompact、SessionEnd,只在已登记的项目中工作。

| 钩子 | 线索 |
|---|---|
| SessionStart | 项目要点、项目 `INDEX.md`(最多 2,500 字符)、步骤卡 |
| PostToolUse (Read) | 打开的文件名 |
| PreToolUse (Edit, Write) | 要编辑的文件、编辑中新调用的 API |
| PreToolUse (Bash) | 命令读写的文件、内联代码中的 API |
| PostToolUseFailure (Bash) | C# 编译错误的文件和代码、异常名称和第一个项目栈帧 |
| Stop, PreCompact, SessionEnd | 不做想起;新对话积累足够时启动回顾 |

- 每次 1~2 条(Bash 为 1 条),每条最多 240 字符,每个会话最多 40 条或 9,000 字符。同一条记忆在一个会话中只出现一次。
- 一个线索命中 4 条以上不同记忆时视为过于常见,只保留文件名中包含它的记忆。
- 命中太多放不下时,优先最近用过的记忆(14 天内 +2,45 天内 +1)。

通过重放 431 个历史会话并让 Sonnet 评判 371 次想起:打开文件时被判为干扰的比例为 0~3%,编辑前为 8~20%,命令涉及的文件约 10%,因此使用这些线索;请求文本(64%)、"不行"之类的结论(75%)、CLI 名称(64%)噪声太大,不使用。
</details>

<details><summary><b>记忆库(cortex)</b></summary>

```
cortex/
├── registry.md            # 路径前缀、项目标识、技术栈、技术栈版本、备注
├── common/                # 与技术栈无关的记忆(工具陷阱、通用原则)
├── stacks/<技术栈>/       # 引擎或框架通用
└── projects/<项目>/       # 项目特有(结构、入口、规范位置)
```

分层依据是"这个事实能推广到多大范围"。每层都有轻量索引,索引行的第一个链接就是记忆正文。只记录付出调查代价才弄明白的、或者只有用户告诉才知道的东西;打开代码几秒就能确认的不记。
</details>

<details><summary><b>记录、睡眠、遗忘和强度</b></summary>

| | awake | sleep |
|---|---|---|
| 开始 | 回合结束、压缩之前、会话结束 | 每天 04:30(或 `/claude-brain-sleep`) |
| 对象 | 上次位置之后新增的对话 | 清醒时没处理的片段 |
| 条件 | 4,000 字节以上且显著度 6 以上(压缩前和会话结束为 3 以上);同一记录 20 分钟一次 | 显著度 6 以上,前 4 个 |

显著度由以下各项相加:用户纠正(3)、决定(3)、"记住这个"(5)、权限拒绝(2)、工具失败(1,最多 5)、反复搜索(1,最多 3)、长会话(1)。

夜间周期:强度统计 → 遗忘 → 回顾剩余片段 → 搜索失败学习 → 整理最久未整理的 3 个片段 → 检查。

遗忘:记忆的最后使用日是想起、打开、搜索命中、编辑和安装日中最晚的一天。45 天后(涉及用户决定、陷阱、事故、损失的记忆为 120 天),索引行移入 `dormant.md`。正文保留且仍可搜索,再次使用时会移回。没有彻底删除。

`cortex/.hippocampus/strength.json` 为每条记忆保存 `{shown, opened, grepped, last}`,用于遗忘、排序和整理判断。
</details>

<details><summary><b>海马的权限</b></summary>

海马默认以 `bypassPermissions` 运行(`scripts/hippocampus-perm.mode`):它是非交互的 `claude -p` 进程,而 Claude Code 把 `~/.claude/` 视为受保护路径,没有这个设置,每次写入都要等一个没人能给的批准。

- 只对海马进程生效,你的会话权限不变。
- 工具限于 Read、Write、Edit、Grep、Glob、Bash、WebFetch、WebSearch,不挂载 MCP 服务器和技能。
- 拒绝规则阻止 git 写入、`rm`、`sudo`、`find -delete`,以及修改 `settings.json`、`CLAUDE.md`、钩子和任何技能的代码(包括本技能)。拒绝规则在该模式下依然有效。
- 关闭方法:`echo acceptEdits > ~/.claude/skills/brain/scripts/hippocampus-perm.mode`。此后项目会以 `denied` 结束,判断结果保存在 `hippocampus-ctl.sh results`。
</details>

<details><summary><b>设计依据的实测</b></summary>

| 事实 | 依据 |
|---|---|
| 钩子能添加上下文的位置是 SessionStart、UserPromptSubmit、PreToolUse、PostToolUse、PostToolUseFailure、Stop | Claude Code 2.1.283 隔离运行,2026-09-29 |
| 命令式的钩子文字被怀疑为提示注入,没有被遵循 | 同一实验 |
| 没有 `CLAUDE.md` 中那一行时,`[记忆]` 被当作来历不明的插入而忽略 | 同一天 |
| 编辑前必须对照笔记的强制规则,在 6,300 次 Edit/Write 中有 1,264 次、893 次 Bash 写入中有 290 次未被遵守 | brain 之前结构的闸门日志(shadow 模式) |
| 需要会话触发的整理从未运行:队列 668 项,记录 322 项,整理 0 项 | brain 之前结构的队列历史 |
| 应用的 Haiku 调用:开启思考 38 秒/0.024 美元,关闭后 6 秒/0.004 美元 | 2026-10-05 |
</details>

<details><summary><b>目录结构和运行要求</b></summary>

```
brain/
├── SKILL.md, commands/        # /brain 控制面板和 /claude-brain-* 命令模板
├── agents/hippocampus.md      # 给海马的指示
├── scripts/                   # thalamus.py(钩子)、nbsearch.py(搜索)、hippocampus-*.sh、sleep.sh、
│                              # persona.py(性格)、lang.py(语言)、plat.py(系统差异)、install.sh …
├── editor/                    # brain 应用(server.py + web/)
├── promo/                     # 宣传视频工具(演示大脑、录制)
├── cortex/                    # 记忆(在你的机器上成长,不受 git 跟踪)
└── .active/                   # 运行时状态(不受 git 跟踪)
```

| | |
|---|---|
| Claude Code | 2.1.28x 及以上(在 2.1.283 上验证) |
| Python | 3.7 及以上(`python3`、`python` 或 `py`) |
| `claude` CLI | 需在 PATH 中(海马和应用会调用) |
| Shell | bash 3.2 及以上。Windows 使用 Git Bash(Git for Windows) |
| 应用窗口 | Chrome(macOS、Linux)或 Edge(Windows)应用模式,否则用默认浏览器 |
| 系统 | macOS(开发和实测环境)、Windows(beta)、Linux(可用,睡眠用 cron) |
</details>

<details><summary><b>与 n-worker 的关系</b></summary>

brain 是从 [n-worker](https://github.com/FuJiGraphics/n-worker) 中拆分出来的技能,前身是笔记本和 curator 守护进程。两者都能独立运行。同时安装时,n-worker 的会话也会收到 `[记忆]` 消息并把它作为判断依据。
</details>

## 许可证

[CC BY-ND 4.0](LICENSE)。Copyright (c) 2026 Cheol Jin Choi (FuJiGraphics)。

在不修改的前提下可以商用和再分发(需注明作者、仓库地址和许可证)。未经许可不得分发修改版。在你机器上成长的记忆属于你,不受本许可证约束。

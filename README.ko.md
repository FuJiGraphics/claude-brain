<h1 align="center">brain</h1>
<p align="center"><b>Claude Code 가 지난번에 알아낸 것을 기억하게 해 주는 장기 기억 스킬입니다</b></p>

<p align="center">
  <a href="README.md">English</a> · <b>한국어</b> · <a href="README.ja.md">日本語</a> · <a href="README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-CC%20BY--ND%204.0-lightgrey.svg" alt="CC BY-ND 4.0"></a>
  <a href="https://claude.com/claude-code"><img src="https://img.shields.io/badge/Claude%20Code-Skill-d97757?logo=anthropic&logoColor=white" alt="Claude Code skill"></a>
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20(beta)%20%7C%20Linux-lightgrey" alt="platforms">
  <img src="https://img.shields.io/badge/lang-KO%20%7C%20EN%20%7C%20JA%20%7C%20ZH-blue" alt="languages">
</p>

<p align="center">
  <a href="https://cdn.jsdelivr.net/gh/FuJiGraphics/claude-brain@media/brain-promo-ko-720p.mp4">
    <img src="https://raw.githubusercontent.com/FuJiGraphics/claude-brain/media/brain-promo-ko-preview.gif" alt="brain 앱 미리보기" width="720">
  </a>
  <br><sub>▶ <a href="https://cdn.jsdelivr.net/gh/FuJiGraphics/claude-brain@media/brain-promo-ko-720p.mp4">1분 영상으로 보기</a> (화면 속 프로젝트와 기억은 데모용으로 만든 것입니다)</sub>
</p>

같은 프로젝트에서 Claude Code 와 몇 주쯤 일하다 보면, 지난주에 함께 알아낸 함정이나 두 달 전에 정한 규칙을 다시 설명하는 일이 생깁니다. 깜빡하고 설명하지 않으면 같은 실수가 그대로 반복되기도 합니다.

brain 은 그런 내용을 대화에서 알아서 골라 기억해 둡니다. 그리고 나중에 Claude 가 그 기억과 관련된 파일을 열거나, 명령을 실행하거나, 에러를 만나면 그 기억을 Claude 에게 건네줍니다. 따로 불러낼 필요가 없고, 기억 파일은 모두 내 컴퓨터에 평범한 마크다운으로 저장됩니다.

```bash
git clone --single-branch https://github.com/FuJiGraphics/claude-brain.git ~/.claude/skills/brain
bash ~/.claude/skills/brain/scripts/install.sh
```

설치한 뒤 지금 일하고 계신 프로젝트 폴더에서 Claude Code 에 `/claude-brain-register` 를 한 번 입력해 주세요. 그 프로젝트부터 바로 기억이 쌓이기 시작합니다. 그다음에는 평소처럼 쓰시면 되고, 어떤 기억이 쌓였는지 궁금하실 때 `/claude-brain-app` 을 입력해 보세요.

## 설치하면 달라지는 점

**같은 설명을 반복하지 않아도 됩니다.** 예를 들어 Claude 가 결제 코드를 고치려는 순간, brain 은 예전에 확인한 사실을 이렇게 건네줍니다.

```
[기억] `PaymentClient` 에 대해 기억나는 것(과거에 확인한 사실이라 지금 코드와 다를 수 있다).
- 결제 재시도는 멱등 키를 재사용한다 - 새로 만들면 이중 결제가 난다 (projects/shop/lessons/payment-retry-reuses-key.md)
```

세션을 시작할 때 프로젝트의 기억 지도(색인)를 한 번 펼쳐 두고, 작업 중에는 그 순간과 관련 있는 기억만 한두 개씩 건넵니다. 걸리는 기억이 없으면 더 넣지 않습니다. 세션마다 긴 문서를 통째로 읽히는 방식과는 다릅니다.

**기억해 달라고 말하지 않아도 쌓입니다.** 세션 밖에서 따로 도는 에이전트(brain 에서는 *해마*라고 부릅니다)가 대화록을 되짚어 오래 남길 만한 것만 골라 근거와 함께 적습니다. 사용자의 정정, 결정, 오래 걸려 알아낸 원인 같은 것들입니다.

**기억이 스스로 정리됩니다.** 매일 밤 겹친 기억을 합치고, 45일 넘게 쓰이지 않은 기억은 지우지 않고 뒤로 숨겨 둡니다. 결정이나 함정처럼 중요한 기억은 120일 동안 남겨 둡니다.

**눈으로 보고 고칠 수 있습니다.** brain 앱에서 프로젝트마다 자라는 뇌를 보고, AI 가 쓴 메모를 쉬운 말로 읽고, 틀린 기억은 버튼 하나로 바로잡을 수 있습니다.

<p align="center">
  <img src="https://raw.githubusercontent.com/FuJiGraphics/claude-brain/media/brain-shots-ko.png" alt="brain 앱 화면 - 프로젝트의 뇌, 쉬운 말 풀이, 물어보기, 성격" width="100%">
</p>

## 정말 차이가 있을까요

실제 프로젝트에서 같은 기능을 두 번 구현해 보았습니다. 한 번은 brain 을 달고, 한 번은 달지 않고 진행했습니다. 모델, 요청, 시작 커밋은 같게 맞추었고, Opus 5.5 판정 모델 둘이 어느 쪽이 brain 인지 모르는 상태로 채점했습니다.

<p align="center">
<picture><source media="(prefers-color-scheme: dark)" srcset="benchmarks/2026-09-30/score-dark.svg"><img src="benchmarks/2026-09-30/score-light.svg" alt="판정 점수" width="720"></picture>
</p>

| | 사례 1: 회전판 미니게임 | 사례 2: 핀볼 미니게임 |
|---|---|---|
| 판정 점수 (50점 만점, 판정 2회 평균) | **brain 34** / 기본 29 | **brain 30.5** / 기본 22 |
| 판정 모델의 선택 | brain 2 / 2 | brain 2 / 2 |
| 걸린 시간 | 9.9분 / 6.9분 | 13.9분 / 4.7분 |
| 비용 (API 요금 환산) | $2.98 / $1.96 | $3.37 / $1.12 |

차이는 코드나 문서에 적혀 있지 않은 지식에서 났습니다.

- 대화로만 정한 규칙: 이 프로젝트에서는 시트 데이터를 TSV 로 넘겨받기로 두 달 전 대화에서 정했고, 저장소 어디에도 적혀 있지 않았습니다. brain 쪽은 이 규칙을 지켰고, 기본 쪽은 로컬 JSON 을 직접 고쳤습니다.
- 어렵게 알아낸 함정: 이런 함정이 두 개 있었는데 brain 쪽은 둘 다 피했고, 기본 쪽은 둘 다 밟았습니다. "캐시된 팝업을 다시 열면 초기화가 돌지 않는다"가 그중 하나입니다.
- 기능이 놓일 자리: brain 쪽은 기존 이벤트 흐름에 매니저, 팝업, 정산까지 연결했고, 기본 쪽은 따로 떨어진 미니게임만 만들었습니다.

대신 시간과 비용은 더 들었습니다(시간 1.4~3.0배, 비용 1.5~3.0배). 늘어난 몫은 대부분 기억을 읽고 확인하는 데 들었고, 사례 2 에서는 brain 쪽이 기존 이벤트 흐름까지 연결하느라 맡은 일이 두 배쯤 넓었습니다. 한 번 쓰고 버릴 스크립트보다는 몇 주 넘게 이어지는 프로젝트에서 이득이 큽니다.

<details><summary>시험 방법과 한계</summary>

- 모델은 두 쪽 모두 Sonnet 5.5, effort medium 입니다.
- 기본 쪽은 `claude -p --restricted` 로 CLAUDE.md, 자동 메모리, 사용자 설정을 모두 끄고 저장소 파일만 읽게 했습니다. brain 쪽은 같은 조건에 brain 훅과 기억 안내 한 줄만 더했습니다. 대화록을 검사해 brain 쪽에만 기억이 실제로 들어갔는지 확인했습니다.
- 판정은 Opus 5.5 모델 둘이 맡았고, 컨벤션, 기존 구조 활용, 중복, 동작 정확성, 완성도를 보았습니다.
- 사례 2건, 조건별 1회라 통계적으로 확정된 결과는 아니고, 초기 신호로 봐 주시면 좋겠습니다. 같은 날 진행한 "계획 한 번 세우기" 시험(과제 18개, 모델 3종)에서는 품질 차이가 없었습니다. 한 번짜리 계획에는 이런 맥락 지식이 드러날 일이 적었던 것으로 보고 있습니다.
- 원자료: [`benchmarks/2026-09-30/results.json`](benchmarks/2026-09-30/results.json)

</details>

## 다른 방법과 무엇이 다른가요

가장 큰 차이는 기억이 **언제, 누구 판단으로** 컨텍스트에 들어가느냐입니다. 2026년 10월 기준 각 프로젝트의 공식 문서를 보고 정리했습니다.

| | 누가 기억을 쓰나요 | 어떻게 떠오르나요 | 정리와 망각 | 저장 위치 |
|---|---|---|---|---|
| **brain** | 백그라운드 에이전트가 대화록에서 (+ 사용자 피드백) | **파일, 명령, 에러에 맞춰 자동으로**, 필요한 순간에 | 매일 밤 병합, 숨기기, 사용 횟수 집계, 링크 검사 | 로컬 마크다운 |
| `CLAUDE.md` / rules | 사용자 (요청하면 Claude) | 세션 시작에 통째로 | 없음 | 로컬 파일 |
| Claude Code 자동 메모리 | 세션 중 Claude 가 | 시작할 때 `MEMORY.md` 앞부분, 주제 파일은 Claude 가 읽을 때 | 한도 근처에서 정리 안내 | 로컬 |
| [claude-mem](https://github.com/thedotmack/claude-mem) | 훅이 수집, 워커가 요약 | 시작에 최근 세션 주입, MCP 도구로 검색 | 문서상 없음 | 로컬 SQLite |
| [Mem0 MCP](https://docs.mem0.ai/platform/mem0-mcp) | 에이전트가 `add_memory` 호출 | 에이전트가 검색해야 함 | OSS 는 추가만 | 클라우드 또는 직접 호스팅 |
| [Basic Memory](https://github.com/basicmachines-co/basic-memory) | 에이전트가 MCP 로 노트 작성 | 에이전트가 검색해야 함 | 수동 | 로컬 마크다운 |
| [MCP memory 서버](https://github.com/modelcontextprotocol/servers/tree/main/src/memory) | 에이전트가 엔터티 생성 | 에이전트가 읽거나 검색해야 함 | 없음 | 로컬 JSONL |
| [Cline Memory Bank](https://docs.cline.bot/customization/memory-bank) | "update memory bank" 라고 하면 Cline 이 | 작업마다 파일 전부 읽음 | 없음 | 프로젝트 마크다운 |
| [Cursor rules](https://cursor.com/docs/context/rules) | 사용자 (자동 메모리는 2.1 에서 제거) | 항상, 설명 기반, glob | 없음 | 프로젝트, 대시보드 |
| [Windsurf memories](https://docs.devin.ai/desktop/cascade/memories) | Cascade 가 자동으로 | Cascade 가 관련 있다고 판단할 때 | 문서상 없음 | 로컬 |
| [Copilot Memory](https://docs.github.com/en/copilot/concepts/agents/copilot-memory) | Copilot 이 근거 인용과 함께 | 쓰기 전에 현재 브랜치로 검증 | 28일 안 쓰면 만료 | GitHub 서버 |

어떤 것을 고르면 좋을까요? 모든 세션에 꼭 필요한 몇 가지 규칙은 `CLAUDE.md` 에 두시는 것이 가장 좋습니다. brain 은 그 옆에서, `CLAUDE.md` 에 다 적어 두기 어려운 수백 개의 작은 함정과 결정을 맡습니다. 여러 도구나 여러 사람이 기억을 같이 써야 한다면 Mem0, Basic Memory 같은 MCP 기억이 더 잘 맞습니다. brain 은 기기 하나에서, Claude Code 와만 동작합니다.

## brain 앱

`/claude-brain-app` 을 입력하면 폰 모양의 작은 창이 뜹니다. Chrome 이나 Edge 의 앱 모드로 열리고, 이 컴퓨터 밖에서는 접속할 수 없습니다.

<p align="center">
  <img src="https://raw.githubusercontent.com/FuJiGraphics/claude-brain/media/ko-home.png" alt="brain 앱 홈" width="300">
  &nbsp;
  <img src="https://raw.githubusercontent.com/FuJiGraphics/claude-brain/media/ko-persona.png" alt="성격 정하기" width="300">
</p>

- 프로젝트마다 자라는 뇌: 기억이 늘수록 알, 아기, 어린이, 어른, 현자로 자랍니다. 기분은 머리 무게, 해마의 실패, 잠, 학습 같은 실제 상태를 보고 바뀝니다.
- 말풍선: 이 뇌가 가장 아끼는 주제를 낱말로 보여 줍니다. 누르면 그 주제의 기억을 모아 볼 수 있습니다.
- 쉬운 말 풀이: AI 가 쓴 메모는 짧고 딱딱해서 읽기 어렵습니다. 기억을 열면 한 줄 요약, 왜 기억하는지, 언제 떠올리는지, 어려운 낱말 풀이를 먼저 보여 드립니다.
- 피드백: 기억마다 "아직도 배포는 release 스크립트로 하나요?" 같은 질문이 붙습니다. "네, 맞아요", "달라졌어요", "중요해요", "이제 필요 없어요" 가운데 하나를 누르면 우체통에 모이고, 우체통에서 "해마에게 한 번에 보내기"를 누르시면 해마에게 전해집니다. 반영이 끝나면 앱이 알려 드립니다.
- 물어보기: 프로젝트의 뇌와 대화할 수 있습니다. 기억 안에서만 답하고, 근거로 쓴 기억을 함께 보여 줍니다.
- 먹이 주기와 뇌 최적화: 꼭 기억했으면 하는 내용을 직접 알려 주거나, 머리가 무거워졌을 때 해마에게 정리를 맡길 수 있습니다.
- 아직 모르는 프로젝트: 최근에 Claude Code 로 일했지만 아직 등록되지 않은 폴더를 보여 드립니다. "키우기"를 누르면 1~2분 안에 그 프로젝트의 뇌가 생깁니다.
- 잠든 기억과 보관함: 오래 쓰지 않아 숨긴 기억은 기억장의 "잠든 기억"에, 해마가 정리하며 내려놓은 기억은 "보관함"에 있습니다. 보관함의 기억은 다시 필요하면 되살릴 수 있습니다.
- 쉬기: 특정 프로젝트에서만 brain 을 잠시 쉬게 할 수 있습니다.
- 사용량과 백업: 설정에서 이번 주에 brain 이 쓴 Claude 사용량을 확인하고, 기억을 zip 하나로 백업할 수 있습니다.

앱은 기억 파일을 직접 고치지 않습니다. 먹이, 피드백, 정리 요청은 모두 해마의 작업 대기열(큐)로 들어가므로, 기억 파일을 고치는 것은 언제나 해마뿐입니다.

### 일하는 성격

프로젝트마다 Claude 가 일하는 방식을 정할 수 있습니다. 다람쥐(빠르게), 부엉이(계획하고 확인), 고양이(묻고 제안), 거북이(느리지만 정확하게) 가운데 하나를 고르시거나, 성향을 상황에 직접 이어서 만드셔도 됩니다.

| 세기 | 일어나는 일 |
|---|---|
| 살짝 | 세션을 시작할 때 문장 하나로 알려 줍니다 |
| 보통 | 여기에 더해 요청마다 한 줄씩 상기시킵니다 |
| 꼭! 🔒 | 여기에 더해 훅이 직접 지킵니다. `rm -rf`, `push --force`, `reset --hard`, 배포 같은 명령 앞에서 사용자에게 묻고, 빌드나 테스트 없이 끝내려 하면 한 번 되돌려 보냅니다 |

미리보기에 보이는 문장이 Claude 가 실제로 받는 문장입니다.

## 명령어

대부분 훅이 바로 처리하기 때문에 토큰을 쓰지 않습니다. 결과는 설정한 언어로 나옵니다.

| 명령 | 하는 일 |
|---|---|
| `/claude-brain-app` | brain 앱 열기 |
| `/claude-brain-status` | 켜짐 여부, 해마 작업과 실패, 마지막 밤 정리, 최근 떠올림, 이번 주 사용량 |
| `/claude-brain-register` | 지금 이 프로젝트를 바로 등록하기 |
| `/claude-brain-on`, `/claude-brain-off` | brain 켜고 끄기. 뒤에 `here` 를 붙이면 이 프로젝트만 해당합니다 |
| `/claude-brain-config [default\|eco\|quality]` | 해마 모델 고르기: Sonnet medium / Sonnet low / Opus high. `lang ko` 처럼 언어도 바꿀 수 있습니다 |
| `/claude-brain-model`, `/claude-brain-effort` | 해마 모델과 effort 를 따로 정하기 |
| `/claude-brain-remember <내용>` | 기억할 내용 직접 알려 주기 |
| `/claude-brain-recall <이름>...` | 파일, 심볼, API, 에러, 증상으로 기억 찾기 |
| `/claude-brain-sleep` | 밤 정리를 지금 돌리기 |
| `/claude-brain-results` | 해마가 한 일 보기 |
| `/claude-brain-stop` | 지금 하던 일이 끝나면 해마 멈추기 |
| `/claude-brain-update` | 새 버전 받기 (기억은 그대로 둡니다) |
| `/claude-brain-backup` | 기억과 성격을 zip 하나로 백업하기 |

## 비용과 개인정보

- 떠올리기는 따로 API 를 부르지 않습니다. 다만 세션을 시작할 때 프로젝트 기억 지도(최대 약 6,000자), 요청마다 습관 한 줄, 작업 중에 떠올린 기억(세션당 평균 약 2,000자, 상한 9,000자)이 컨텍스트에 더해집니다. 훅 한 번에 걸리는 시간은 약 25ms 입니다.
- 해마는 Claude 사용량을 씁니다. 작업 한 건마다 `claude -p` 를 한 번 실행합니다(기본 Sonnet 5.5, effort medium). 데모 저장소에서 잰 값은 기록 한 건에 0.06~0.13달러, 정리 한 건에 0.05~0.11달러였습니다(API 요금 기준). 실제 프로젝트에서는 기억이 많을수록 조금 더 듭니다. 줄이고 싶으시면 `/claude-brain-config eco` 를 써 보세요.
- 앱의 AI 기능(말풍선, 쉬운 말 풀이, 물어보기)은 Claude Haiku 를 부르고, 한 번에 0.002~0.004달러쯤 듭니다. 풀이는 캐시해 둡니다.
- 쓴 양은 `/claude-brain-status` 와 앱 설정의 "사용량"에서 언제든 확인하실 수 있습니다. Pro, Max 구독이라면 이 금액은 실제 청구액이 아니라 쓴 양을 가늠하는 기준입니다.
- 기억 파일은 이 컴퓨터에만 저장됩니다. 다만 Claude 세션, 해마, 앱이 Claude 를 부를 때는 필요한 기억 내용이 프롬프트에 담겨 Anthropic API 로 전송됩니다. 해마는 확인이 필요하면 웹을 검색하거나 읽을 수 있습니다(WebFetch, WebSearch). 그 밖에 하루 한 번 새 버전을 확인합니다(`git fetch`). 필요 없으시면 `~/.claude/skills/brain/.active/config` 에 `update_check=0` 을 적어 주세요. 앱은 `127.0.0.1` 에서만, 실행할 때마다 새 토큰으로 열립니다.
- 해마는 승인 프롬프트 없이 실행됩니다. 승인해 줄 사람이 없는 백그라운드 작업이기 때문입니다. 대신 git 쓰기, `rm`, `sudo`, 설정 파일과 다른 스킬 편집은 거부 규칙으로 막아 두었습니다. 자세한 내용은 아래 [해마의 권한](#hippocampus-permissions)에 정리해 두었습니다.

## 설치, 업데이트, 백업

```bash
git clone --single-branch https://github.com/FuJiGraphics/claude-brain.git ~/.claude/skills/brain
bash ~/.claude/skills/brain/scripts/install.sh
```

Windows 에서는 같은 두 줄을 Git Bash(Claude Code 가 쓰는 셸)에서 실행해 주세요. 설치는 여러 번 해도 결과가 같고, 고치는 설정 파일은 `<파일>.brain-bak-<시각>` 으로 백업해 둡니다. 설치가 하는 일은 다음과 같습니다.

1. `~/.claude/settings.json` 에 brain 훅을 등록합니다. 다른 훅은 건드리지 않습니다. brain 훅은 어떤 경우에도 정상 종료 코드로 끝나므로, 성격을 "꼭!"으로 정하지 않았다면 brain 이 도구 호출을 막는 일은 없습니다.
2. Claude Code 상태줄 끝에 `[BRAIN]` 표시를 붙입니다. 원래 쓰시던 상태줄은 그대로 둡니다.
3. `~/.claude/CLAUDE.md` 에 `[기억]` 메시지가 무엇인지 알려 주는 한 줄을 넣습니다. 시험해 보니 이 줄이 없을 때는 Claude 가 기억을 출처를 알 수 없는 글로 여기고 무시했습니다.
4. 매일 04:30 에 밤 정리를 예약합니다(macOS 는 launchd, Windows 는 작업 스케줄러). Linux 에서는 cron 에 `scripts/sleep.sh` 를 직접 걸어 주세요.
5. `/claude-brain-*` 명령어를 만들고, 운영체제 언어에 맞춰 언어를 정합니다.

### 프로젝트 등록

brain 은 등록된 프로젝트 안에서만 동작합니다. 최근 7일 안에 세션 3개 이상, 요청 10개 이상을 주고받은 git 폴더는 밤마다 한 곳씩 자동으로 등록됩니다. 바로 시작하고 싶으시면 그 폴더에서 `/claude-brain-register` 를 입력하시거나, 앱 홈의 "아직 모르는 프로젝트"에서 "키우기"를 눌러 주세요.

### 업데이트

`/claude-brain-update` 를 입력하시면 새 버전을 받고 설치를 다시 돌립니다. 직접 고친 파일이 있으면 덮어쓰지 않고 멈춘 뒤 알려 드립니다. 새 버전이 나오면 앱 홈과 `/claude-brain-status` 에 안내가 뜹니다.

<details><summary>2026년 10월 5일 이전에 설치하셨다면 (처음 한 번만)</summary>

예전 버전은 기억 폴더(`cortex/`)의 일부를 git 이 관리해서 `git pull` 이 충돌로 멈춥니다. 아래 명령을 한 번만 실행해 주시면 기억을 그대로 둔 채 새 구조로 옮겨집니다.

```bash
cd ~/.claude/skills/brain
cp -R cortex .active/cortex-backup          # 기억을 먼저 복사해 둡니다
git checkout -- cortex && git pull          # 새 버전을 받습니다
cp -R .active/cortex-backup/. cortex/       # 기억을 제자리로 돌려놓습니다
bash scripts/install.sh
```

이후부터는 `/claude-brain-update` 로 업데이트하시면 됩니다.
</details>

### 백업과 다른 컴퓨터로 옮기기

`/claude-brain-backup`(또는 앱 설정의 백업)으로 기억과 성격을 zip 하나로 만들 수 있습니다. zip 은 `~/Downloads` 에 저장됩니다. 새 컴퓨터에 brain 을 설치한 뒤 `bash ~/.claude/skills/brain/scripts/backup.sh restore <zip 경로>` 를 실행해 주세요. 그 컴퓨터에 있던 기억은 `.active/before-restore-<시각>/` 으로 옮겨 둔 뒤 바꿔 넣고, 사용자 이름이 달라 홈 폴더 경로가 바뀌었다면 프로젝트 경로도 맞춰 드립니다. 해마가 일하는 중에는 되살리지 않으니, 그럴 때는 `/claude-brain-stop` 으로 먼저 멈춰 주세요.

### 제거

`bash ~/.claude/skills/brain/scripts/install.sh --uninstall` 을 실행하시면 훅, 상태줄 표시, CLAUDE.md 의 한 줄, 명령어 파일, 밤 정리 예약을 해제하고 해마를 멈춥니다. 기억은 폴더를 지우기 전까지 남아 있습니다.

## 자주 묻는 질문

**`CLAUDE.md` 만으로는 부족한가요?** 모든 세션에 필요한 몇 가지 규칙에는 `CLAUDE.md` 가 가장 좋습니다. 다만 매번 통째로 읽히고, 사람이 직접 써야 하고, 스스로 정리되지 않습니다. brain 은 `CLAUDE.md` 에 다 적어 두기 어려운 수백 개의 작은 함정과 결정을 맡아, 지금 다루는 파일이나 에러와 관련된 것만 꺼내 줍니다.

**Claude Code 의 자동 메모리는 켜 두어도 될까요?** `~/.claude/settings.json` 에 `"autoMemoryEnabled": false` 를 넣어 끄시기를 권합니다. 자동 메모리는 틀린 내용을 바로잡을 장치가 없고 세션마다 실리기 때문에, 낡은 메모가 brain 의 새 기억과 부딪칠 수 있습니다.

**기억이 틀렸으면 어떻게 하나요?** 앱에서 그 기억을 열고 "달라졌어요"를 눌러 지금 상황을 적은 뒤, 우체통에서 보내 주세요. 해마가 확인한 뒤 고칩니다. 기억에는 확인한 날짜가 붙어 있고, 지금 코드와 다르면 언제나 지금 코드가 우선입니다.

**기억이 끝없이 늘어나지는 않나요?** 매일 밤 겹친 기억을 합치고 오래 쓰지 않은 기억은 숨깁니다. 숨긴 기억도 검색으로는 찾을 수 있습니다. 앱의 "머리 무게"가 정리할 때를 알려 드립니다.

**특정 프로젝트에서만 끄고 싶어요.** 그 폴더에서 `/claude-brain-off here` 를 입력하시거나, 앱의 프로젝트 화면에서 "이 프로젝트에서 쉬기"를 켜 주세요. 기억은 그대로 남습니다.

**팀이 함께 쓸 수 있나요?** 아직은 어렵습니다. 기억은 기기마다 따로 있습니다. 백업 zip 으로 옮길 수는 있지만 여러 사람이 동시에 쓰도록 설계하지는 않았습니다.

**Cursor 나 Codex 에서도 되나요?** 아쉽지만 되지 않습니다. Claude Code 의 훅 위에서 동작합니다.

**어떤 언어를 지원하나요?** 앱, 명령어 결과, 설치 안내, 세션 문구, 성격은 한국어, 영어, 일본어, 중국어를 지원합니다. 기억은 대화한 언어로 쌓이고, 정정이나 결정 같은 신호도 네 언어로 알아봅니다. 언어는 앱 설정이나 `/claude-brain-config lang en` 처럼 바꾸실 수 있습니다.

**무엇이 세션에 들어갔는지 볼 수 있나요?** `/claude-brain-status` 에서 최근 24시간 떠올림 횟수와 글자 수를 보실 수 있고, `~/.claude/skills/brain/.active/recall.log` 에는 모든 기록이 남습니다.

## 알아 두실 점

- 측정은 한 사람의 프로젝트에서 했습니다(macOS, 주로 Unity/C# 와 VS Code 확장). 에러에서 단서를 뽑는 규칙은 C# 컴파일 에러에 맞춰 다듬었습니다. 열거나 고치는 파일의 이름으로 떠올리는 부분은 언어와 상관없이 동작합니다. 명령 속 파일은 흔한 언어의 소스와 설정 파일 확장자를, API 이름은 `PaymentClient.Charge(` 처럼 대문자로 시작하는 점 표기를 알아봅니다.
- Windows 지원은 베타입니다. 경로, 훅, 작업 스케줄러, 앱을 Windows 에 맞게 옮기고 검토했지만 실제 Windows 기기에서는 아직 충분히 써 보지 못했습니다. 문제가 있으면 이슈로 알려 주시면 감사하겠습니다.
- 맥락이 중요한 일에서는 시간과 토큰을 더 씁니다(위의 벤치마크를 참고해 주세요).
- 해마는 이 컴퓨터에서 감독 없이 도는 에이전트입니다. 거부 규칙을 두었지만, 불편하시면 `scripts/hippocampus-perm.mode` 를 `acceptEdits` 로 바꾸실 수 있습니다. 다만 그러면 해마가 기억 파일을 쓰지 못해 brain 이 더는 새로 배우지 않습니다(떠올리기는 그대로 됩니다).

## 동작 원리

뇌의 구조에서 이름을 빌려 왔습니다.

| 부품 | 사람의 뇌에서 | 이 스킬에서 |
|---|---|---|
| **cortex** | 대뇌 피질, 굳어진 장기 기억 | 마크다운 기억 저장소입니다. `common/`, `stacks/<스택>/`, `projects/<슬러그>/` 세 층으로 나뉘고, 층마다 얇은 색인과 기억 본문이 있습니다 |
| **thalamus** | 시상, 감각을 걸러 의식으로 올림 | 훅입니다. 지금 다루는 파일, 명령, 에러에 걸린 기억을 건네고, 세션 시작 때 프로젝트 지도를 펼칩니다 |
| **hippocampus** | 해마, 새 기억을 만듦 | 백그라운드 `claude -p` 작업자입니다. cortex 에 쓰는 유일한 주체로 등록, 기록, 재생, 정리를 맡습니다 |
| **sleep** | 잠, 기억을 굳히고 잊음 | 매일 밤 사용 횟수 집계, 망각, 남은 대화 재생, 검색 실패 학습, 정리, 검사를 합니다 |

```
[떠올리기 - 세션 안]
도구 호출 ─ 훅 ─▶ thalamus ─▶ cortex 에서 걸린 기억 ─▶ [기억] 메시지가 세션에 들어갑니다

[기록하기 - 세션 밖]
턴 끝, 압축 직전, 세션 끝 ─▶ thalamus ─▶ 재생(깨어 있을 때) ──────────┐
매일 04:30 ─▶ sleep ─▶ 재생, 검색 실패 학습, 정리 ─────────────────┴─▶ 큐 ─▶ hippocampus ─▶ cortex
```

Claude Code 가 이미 남기고 있는 대화록이 단기 기억 역할을 합니다. 같은 구간은 한 번만 처리합니다.

<details><summary><b>떠올리기 - thalamus</b></summary>

훅은 SessionStart, UserPromptSubmit, PreToolUse(Edit, Write, MultiEdit, NotebookEdit, Bash, AskUserQuestion), PostToolUse(Read), PostToolUseFailure(Bash), SubagentStart, Stop, PreCompact, SessionEnd 에 걸립니다. `cortex/registry.md` 에 등록된 프로젝트 안에서만 동작합니다.

| 훅 이벤트 | 단서 |
|---|---|
| SessionStart | 프로젝트 요지, 프로젝트 `INDEX.md`(3,000자 상한), 스택과 공용 색인(각각 2,000자, 1,200자), 절차 기억 줄 |
| UserPromptSubmit | 계획 전에 이번 작업 영역의 색인을 열어 보라는 습관 한 줄 |
| PostToolUse (Read) | 연 파일 이름 |
| PreToolUse (Edit, Write, MultiEdit, NotebookEdit) | 고칠 파일 이름, 편집 내용에 새로 나온 API 이름 |
| PreToolUse (Bash) | 명령이 읽거나 쓰는 파일 이름, 명령 속 코드의 API 이름 |
| PostToolUseFailure (Bash) | C# 컴파일 에러의 파일과 에러 코드, 예외 이름과 첫 프로젝트 프레임의 파일 |
| SubagentStart | 작업 폴더의 프로젝트와 `[기억]` 이 무엇인지 알리는 한 줄 |
| Stop, PreCompact, SessionEnd | 떠올림은 없고, 새 대화 구간이 두드러지면 재생을 시작합니다 |

- 걸린 기억이 없으면 아무것도 출력하지 않습니다. 한 번에 1~2개(Bash 는 1개), 항목당 240자 이하, 세션당 40개 또는 9,000자가 상한입니다(세션 시작 지도는 따로 셉니다).
- 단서 하나가 서로 다른 기억 4개 이상에 걸리면 흔한 단서로 보고 파일 이름에 그 단서가 든 기억만 남깁니다.
- 과거 대화록 431세션을 다시 돌려 떠올림 371건을 Sonnet 으로 판정했습니다. "방해가 됐다"는 판정 비율이 낮은 파일 열람(0~3%), 편집 직전(8~20%), 명령이 다루는 파일(약 10%)에서만 떠올리고, 비율이 높았던 요청 글(64%), "안 된다"는 결론(75%), 명령 속 CLI 이름(64%)은 단서로 쓰지 않습니다.
</details>

<details><summary><b>기록, 잠, 망각</b></summary>

| | 깨어 있을 때 | 잠 |
|---|---|---|
| 시작 | 턴 끝, 압축 직전, 세션 끝에 백그라운드로 | 매일 04:30. 놓치면 깨어난 뒤 한 번. `/claude-brain-sleep` 으로 바로 |
| 대상 | 지난번 처리 위치 뒤에 새로 쌓인 대화 구간 | 깨어 있을 때 처리하지 못한 구간 |
| 조건 | 4,000바이트 이상, 두드러짐 6 이상(압축 직전과 세션 끝은 3 이상). 같은 대화록은 20분에 한 번(압축 직전과 세션 끝은 예외), 전체는 시간당 4건 | 두드러짐 6 이상, 높은 순 4건 |

두드러짐 점수는 사용자의 정정 3, 결정 표현 3, 기억 요청 5, 권한 거부 2, 도구 실패 1(최대 5), 반복 조사 1(최대 3), 요청이 5개 이상이면 1로 매깁니다. 정정, 결정, 기억 요청은 한국어, 영어, 일본어, 중국어 표현을 모두 알아봅니다.

잠은 사용 횟수와 검색 실패 집계, 망각, 남은 구간 재생(최대 4건)과 활발한 미등록 프로젝트 1곳 등록, 검색 실패 학습, 가장 오래 정리하지 않은 조각 3개 정리, 검사 순서로 진행됩니다. `scripts/sleep.conf` 를 만들어 `FORGET_DAYS=60` 처럼 적으면 기본값을 바꿀 수 있습니다.

마지막으로 쓰인 날에서 45일(결정, 함정, 사고가 든 기억은 120일)이 지나면 색인 줄을 `dormant.md` 로 옮깁니다. 본문은 남아 검색으로 찾을 수 있고, 다시 쓰이면 원래 색인으로 돌아옵니다. 해마가 정리하며 내려놓은 기억은 `_archive/` 로 옮겨 앱의 보관함에서 되살릴 수 있습니다. 하드 삭제는 하지 않습니다.
</details>

<a name="hippocampus-permissions"></a>
<details><summary><b>해마의 권한</b></summary>

> [!IMPORTANT]
> 해마는 기본적으로 승인 프롬프트 없이 실행됩니다(`scripts/hippocampus-perm.mode` 의 `bypassPermissions`). brain 을 `~/.claude/skills/` 아래에 두면 기억 폴더도 그 아래에 놓이는데, Claude Code 는 `.claude/` 를 보호 경로로 보고 편집마다 승인을 요구합니다. 해마는 비대화형 `claude -p` 라서 승인할 사람이 없습니다.

- 이 설정은 해마 프로세스에만 적용되고, 여러분의 대화 세션 권한은 그대로입니다.
- 도구는 Read, Write, Edit, Grep, Glob, Bash, WebFetch, WebSearch 로 한정하고 MCP 서버와 다른 스킬은 붙이지 않습니다.
- git 쓰기(`commit`, `push`, `checkout`, `reset` 등), `rm`, `sudo`, `find -delete`, 다른 스킬 본문과 `settings.json`, `CLAUDE.md`, `hooks/` 편집은 거부 규칙으로 막습니다. 거부 규칙은 이 모드에서도 유효합니다.
- 끄시려면 `echo acceptEdits > ~/.claude/skills/brain/scripts/hippocampus-perm.mode` 를 실행해 주세요. 그러면 기억 쓰기가 모두 거부되어(`denied`) 판정만 남고, brain 은 더는 새로 배우지 않습니다.
</details>

<details><summary><b>설계의 근거가 된 측정</b></summary>

| 사실 | 근거 |
|---|---|
| 명령형 훅 문구는 프롬프트 주입으로 의심받아 지켜지지 않았습니다 | Claude Code 2.1.283 격리 실행, 2026-09-29 |
| `CLAUDE.md` 의 한 줄이 없으면 `[기억]` 을 출처를 알 수 없는 글로 보고 무시했습니다 | 같은 날 |
| "고치기 전에 노트를 확인하라"는 강제 규칙이 Edit, Write 6,300건 중 20%, Bash 쓰기 893건 중 32%에서 지켜지지 않았습니다 | 분리 전 구조의 게이트 기록 |
| 세션이 시켜야 도는 정리는 돌지 않았습니다 (큐 668건 중 기록 322, 정리 0) | 분리 전 구조의 큐 기록 |
| 앱의 Haiku 호출은 생각을 켜면 38초 0.024달러, 끄면 6초 0.004달러였습니다 | 2026-10-05 |
</details>

<details><summary><b>폴더 구조와 요구 사항</b></summary>

```
brain/
├── SKILL.md, commands/        # 제어판, /claude-brain-* 명령 템플릿
├── agents/hippocampus.md      # 해마 지침
├── scripts/                   # thalamus.py(훅), nbsearch.py(검색), hippocampus-*.sh, sleep.sh, install.sh,
│                              # update.py, backup.py, register.py, persona.py, lang.py, cli_i18n.py, plat.py …
├── editor/                    # brain 앱 (server.py + web/)
├── seed/cortex/               # 처음 설치할 때 쓰는 기억 저장소 골격
├── promo/                     # 홍보 영상, 스크린샷 도구 (가상의 데모 뇌)
├── cortex/                    # 기억 (이 컴퓨터에서 자랍니다, git 이 추적하지 않음)
└── .active/                   # 실행 상태 (git 이 추적하지 않음)
```

| | |
|---|---|
| Claude Code | 2.1.28x 이상 (2.1.283 에서 검증) |
| Python | 3.7 이상 (`python3`, `python`, `py` 중 하나) |
| `claude` CLI | PATH 에 있어야 합니다 (해마와 앱이 부릅니다) |
| 셸 | bash 3.2 이상. Windows 는 Git Bash |
| 앱 창 | Chrome(macOS, Linux) 또는 Edge(Windows) 앱 모드, 없으면 기본 브라우저 |
| OS | macOS (만들고 측정한 곳), Windows (베타), Linux (동작, 밤 정리는 cron) |
</details>

## 라이선스

[CC BY-ND 4.0](LICENSE) (저작자표시-변경금지 4.0 국제). Copyright (c) 2026 Cheol Jin Choi (FuJiGraphics).

| 항목 | 내용 |
|---|---|
| 상업적 이용 | 가능합니다. 회사 업무나 유료 서비스 안에서 쓰셔도 됩니다 |
| 공유, 재배포 | 원본 그대로라면 가능합니다 |
| 수정본 배포 | 고치거나 일부를 떼어 낸 버전은 배포할 수 없습니다 |
| 저작자 표기 | 저작자, 저장소 주소(https://github.com/FuJiGraphics/claude-brain), 라이선스를 밝혀 주세요 |

수정본을 배포하고 싶으시면 저작자에게 따로 연락해 주세요. 설치한 컴퓨터에서 쌓이는 기억은 사용자 본인의 것이며 이 라이선스와 관계가 없습니다.

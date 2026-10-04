<h1 align="center">brain</h1>
<h3 align="center">make Claude Code remember!</h3>

<p align="center">
  <a href="README.md">English</a> · <b>한국어</b> · <a href="README.ja.md">日本語</a> · <a href="README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-CC%20BY--ND%204.0-lightgrey.svg" alt="CC BY-ND 4.0"></a>
  <a href="https://claude.com/claude-code"><img src="https://img.shields.io/badge/Claude%20Code-Skill-d97757?logo=anthropic&logoColor=white" alt="Claude Code skill"></a>
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20(beta)%20%7C%20Linux-lightgrey" alt="platforms">
  <img src="https://img.shields.io/badge/lang-EN%20%7C%20KO%20%7C%20JA%20%7C%20ZH-blue" alt="languages">
  <a href="#벤치마크"><img src="https://img.shields.io/badge/blind%20review-2%2F2%20wins-2a78d6" alt="benchmark"></a>
</p>

<p align="center">
  <a href="https://cdn.jsdelivr.net/gh/FuJiGraphics/claude-brain@media/brain-promo-ko-720p.mp4">
    <img src="https://raw.githubusercontent.com/FuJiGraphics/claude-brain/media/brain-promo-ko-preview.gif" alt="brain 앱 미리보기" width="720">
  </a>
  <br><sub>▶ <a href="https://cdn.jsdelivr.net/gh/FuJiGraphics/claude-brain@media/brain-promo-ko-720p.mp4">60초 전체 영상 보기</a> (가상의 데모 데이터)</sub>
</p>

**brain 은 Claude Code 에 붙이는, 스스로 도는 장기 기억이다.**
Claude 가 예전에 무언가를 배운 파일을 열거나, 명령을 돌리거나, 에러를 만나는 순간 그 기억이 세션에 저절로 떠오른다. 새 기억은 세션 밖에서 대화록을 되짚어 만들어지고, 매일 밤 정리하고 낡은 것은 잊는다. Claude 가 "기억해야 한다는 걸 기억할" 필요가 없다.

```bash
git clone --single-branch https://github.com/FuJiGraphics/claude-brain.git ~/.claude/skills/brain
bash ~/.claude/skills/brain/scripts/install.sh
```

설치하고 Claude Code 에서 **`/claude-brain-app`** 으로 앱을 연다.

**목차** · [왜 필요한가](#왜-필요한가) · [무엇이 다른가](#무엇이-다른가) · [벤치마크](#벤치마크) · [다른 방식과 비교](#다른-방식과-비교) · [brain 앱](#brain-앱) · [어떻게 도는가](#어떻게-도는가) · [설치](#설치) · [명령](#명령) · [비용과 개인정보](#비용과-개인정보) · [자주 묻는 질문](#자주-묻는-질문) · [한계](#한계) · [참고 자료](#참고-자료) · [라이선스](#라이선스)

---

## 왜 필요한가

같은 프로젝트에서 Claude Code 로 몇 주씩 일하면 같은 교훈에 계속 값을 치른다.

- **세션이 매번 백지에서 시작한다.** 두 달 전에 정한 팀 규칙, 오후 하나를 날린 함정, 이 기능이 전체에서 어떤 자리인지를 다시 설명하거나, 빠뜨려서 사고가 난다.
- **"먼저 노트를 확인해" 는 지켜지지 않는다.** 작성자의 기록에서 고치기 전에 노트를 대조하라는 강제 규칙이 **Edit, Write 6,300건 중 20%, Bash 쓰기 893건 중 32%** 에서 지켜지지 않았다.
- **불러야 도는 기억 도구는 불리지 않는다.** 에이전트가 검색할지 스스로 정해야 하면, 모르는 것을 모를 때 가장 덜 검색한다.
- **노트는 썩는다.** 합치고 고치고 은퇴시키는 주체가 없으면 노트는 쌓이고, 서로 어긋나고, 매 세션에 통째로 실린다.

brain 은 이 일을 전부 세션 밖으로 옮긴다. 세션은 아무것도 하지 않고, 기억이 떠오를 뿐이다.

```
세션이 src/Payment/PaymentClient.cs 를 고치려는 순간 세션에 들어가는 메시지 (예시)

[기억] `PaymentClient` 에 대해 기억나는 것(과거에 확인한 사실이라 지금 코드와 다를 수 있다).
- 결제 재시도는 멱등 키를 재사용한다 - 새로 만들면 이중 결제가 난다 (projects/shop/lessons/payment-retry-reuses-key.md)
```

## 무엇이 다른가

| | |
|---|---|
| 🧠 **묻지 않아도 떠오른다** | 훅이 지금 읽거나 고치는 파일, 새로 부르는 API, 명령이 다루는 파일, 방금 난 컴파일 에러를 보고 거기에 걸린 기억만 건넨다. 걸린 게 없으면 아무것도 넣지 않는다. |
| 🌙 **세션 밖에서 배운다** | 따로 도는 에이전트(*해마*)가 대화록을 되짚어 근거를 붙인 기억을 쓴다. 세션은 기록에 한 턴도 쓰지 않는다. |
| 🧹 **자고, 굳히고, 잊는다** | 매일 밤 기억마다 쓰인 횟수를 세고, 45일(결정과 함정은 120일) 안 쓴 기억은 지우지 않고 숨기고, 겹친 것은 합치고, 깨진 링크를 검사한다. |
| 📜 **명령이 아니라 사실** | 기억은 출처가 붙은 사실로 들어온다. 지금 코드와 다르면 지금 코드가 이긴다. 명령형 훅 문구는 프롬프트 주입으로 의심받아 무시된다는 실측이 있어서 brain 은 명령하지 않는다. |
| 💸 **예산 안에서** | 훅 한 번 약 20ms, 세션당 평균 약 2,000자이고 상한이 있다. |
| 📱 **읽을 수 있는 앱** | `/claude-brain-app` 은 프로젝트마다 뇌가 무엇을 아끼고 무엇을 배웠는지 보여 주고, 물어보고, 피드백하고, 정리하고, 일하는 성격을 정하게 해 준다. |
| 🎭 **진짜로 지키는 성격** | 프로젝트마다 Claude 가 일하는 방식을 고른다. "꼭!" 규칙은 훅이 강제한다 - 되돌리기 어려운 명령 앞에서 묻고, 고친 뒤 검증 없이 끝내지 못하게 한다. |
| 🌐 **다국어** | 앱, 세션 문구, 성격을 영어, 한국어, 일본어, 중국어로. 기억은 대화한 언어로 쌓인다. |
| 📂 **내 컴퓨터의 평범한 파일** | 기억은 마크다운 파일이다. 서버도 계정도 수집도 없다. |

## 벤치마크

**실제 프로젝트에서 같은 기능을 두 번 구현시켰다. 한 번은 brain 을 달고, 한 번은 없이.** 모델, 요청, 기준 커밋은 같고 각자 따로 복제한 작업 사본에서 실제로 코드를 썼다. 판정관 2명이 어느 쪽이 brain 인지 모르는 채로 검토했다.

<p align="center">
<picture><source media="(prefers-color-scheme: dark)" srcset="benchmarks/2026-09-30/score-dark.svg"><img src="benchmarks/2026-09-30/score-light.svg" alt="판정 점수" width="720"></picture>
</p>

| | 사례 1: 회전판 미니게임 | 사례 2: 핀볼 미니게임 |
|---|---|---|
| 판정 점수 (50점, 2명 평균) | **brain 34** / 순정 29 | **brain 30.5** / 순정 22 |
| 판정관 선택 | brain 2 / 2 | brain 2 / 2 |
| 프로젝트 소유자 채점 | 속도, 토큰을 뺀 모든 항목 brain | 요청 의도를 정확히 반영한 쪽 brain |
| 시간 | 9.9분 / 6.9분 | 13.9분 / 4.7분 |
| 비용 (정가 환산) | $2.98 / $1.96 | $3.37 / $1.12 |

**차이는 코드와 문서에 없는 지식에서 났다.**

- **구두 지침.** 이 팀은 시트 데이터를 전량 TSV 로 넘겨 받는다. 두 달 전 대화에서 한 번 정한 규칙이고 저장소 어디에도 적혀 있지 않다. brain 은 이 규칙을 지켰고, 순정 모델은 로컬 JSON 을 직접 고쳤다.
- **비싸게 알아낸 함정.** "캐시된 팝업을 다시 열면 초기화가 돌지 않는다", "순환 이벤트에 줄을 추가하면 모든 회차가 다시 계산된다". brain 은 피했고 순정 모델은 둘 다 밟았다.
- **기능의 큰 그림.** brain 은 기존 순환 이벤트 흐름에 매니저, 팝업, 정산까지 연결했고, 순정 모델은 단독 미니게임만 만들었다.

**대가.** brain 쪽이 시간 1.4~2.9배, 비용 1.5~3.0배를 썼다. 기억을 읽고 확인하는 비용이고, 사례 2 는 일의 범위도 두 배였다.

<details><summary>시험 방법과 한계</summary>

- 모델: Sonnet 5.5, effort medium. 두 팀 동일.
- 순정 팀: `claude -p --restricted` 로 CLAUDE.md, 자동 메모리, 사용자 설정을 모두 끄고 저장소 파일만 읽게 했다. brain 팀은 같은 조건에 brain 훅과 기억 출처 한 줄만 더했다. 대화록을 검사해 brain 쪽에는 기억이 실제로 들어갔고 순정 쪽에는 흔적이 0 임을 확인했다.
- 판정관: Opus 5.5 2명, 가림 검토. 항목은 컨벤션, 기존 구조 활용, 헬퍼 중복, 동작 정확성, 완성도.
- 한계: 사례 2건, 조건별 1회. 경향은 분명하지만 통계적으로 확정한 결과는 아니다. 같은 날 한 "계획 한 번 세우기" 시험(실제 과제 18개, 모델 3종)에서는 품질 차이가 없었다. 한 번짜리 계획에는 이런 맥락 지식이 드러날 일이 적었던 것으로 본다.
- 원자료: [`benchmarks/2026-09-30/results.json`](benchmarks/2026-09-30/results.json)

</details>

## 다른 방식과 비교

2026년 10월 기준, 각 프로젝트의 공식 문서로 정리했다. 중요한 것은 "떠올림" 칸이다 - 기억이 컨텍스트에 들어가는 것을 누가, 언제 정하는가.

| | 누가 쓰나 | 어떻게 떠오르나 | 정리와 망각 | 저장 위치 |
|---|---|---|---|---|
| **brain** | 백그라운드 에이전트가 대화록에서 (+ 사용자 피드백) | **파일, 명령, 에러마다 자동으로**, 필요한 그 순간에 | 밤마다 병합, 잠재화, 강도 집계, 링크 검사 | 로컬 마크다운 |
| `CLAUDE.md` / rules | 사용자 (요청하면 Claude) | 세션 시작에 통째로 (경로 규칙은 그 파일을 읽을 때) | 없음 | 로컬 파일 |
| Claude Code 자동 메모리 | 세션 중 Claude 가 | 시작에 `MEMORY.md` 앞 200줄 또는 25KB, 주제 파일은 Claude 가 읽을 때 | 한도 근처에서 병합 안내 | 로컬 |
| [claude-mem](https://github.com/thedotmack/claude-mem) | 훅이 수집, 워커가 요약 | 시작에 최근 세션 주입, MCP 도구로 검색 | 문서상 없음 | 로컬 SQLite |
| [Mem0 MCP](https://docs.mem0.ai/platform/mem0-mcp) | 에이전트가 `add_memory` 호출 | 에이전트가 검색을 불러야 함 | OSS 는 추가만 | 클라우드 또는 직접 호스팅 |
| [Basic Memory](https://github.com/basicmachines-co/basic-memory) | 에이전트가 MCP 로 노트 작성 | 에이전트가 검색을 불러야 함 | 수동 | 로컬 마크다운 |
| [MCP memory 서버](https://github.com/modelcontextprotocol/servers/tree/main/src/memory) | 에이전트가 엔터티 생성 | 에이전트가 읽기,검색을 불러야 함 | 없음 | 로컬 JSONL |
| [Cline Memory Bank](https://docs.cline.bot/customization/memory-bank) | "update memory bank" 라고 하면 Cline 이 | 작업마다 파일 전부 읽음 | 없음 | 프로젝트 마크다운 |
| [Cursor rules](https://cursor.com/docs/context/rules) | 사용자 (자동 메모리는 2.1 에서 제거) | 항상, 설명 기반, glob | 없음 | 프로젝트, 대시보드 |
| [Windsurf memories](https://docs.devin.ai/desktop/cascade/memories) | Cascade 가 자동으로 | Cascade 가 관련 있다고 판단할 때 | 문서상 없음 | 로컬 |
| [Copilot Memory](https://docs.github.com/en/copilot/concepts/agents/copilot-memory) | Copilot 이 근거 인용과 함께 | 쓰기 전에 현재 브랜치로 검증 | 28일 안 쓰면 만료 | GitHub 서버 |

**무엇을 고를까.** 모든 세션에 필요한 몇 가지 규칙은 `CLAUDE.md` 에 두고, brain 은 그 옆에서 긴 꼬리를 맡는다. 여러 도구나 팀이 기억 하나를 같이 써야 한다면 MCP 기억(Mem0, Basic Memory)이 낫다 - brain 은 기기 하나, Claude Code 전용이다. 오래 가는 프로젝트에서 비싼 지식이 아무도 적지 않는 종류(구두 결정, 어렵게 알아낸 함정, "이게 어떻게 맞물리는지")라면 brain 이 맞다. brain 과 함께 쓸 때는 Claude Code 자동 메모리를 **끄는** 것을 권한다([자주 묻는 질문](#자주-묻는-질문)).

## brain 앱

`/claude-brain-app` 은 폰 모양의 작은 창을 연다(Chrome 또는 Edge 앱 모드, 이 컴퓨터에서만).

- **뇌들**: 프로젝트마다 캐릭터 하나. 기억이 늘면 자라고(알, 아기, 어린이, 어른, 현자), 기분은 실제 신호(머리 무게, 해마 실패, 잠, 학습)에서 온다.
- **말풍선**: 이 뇌가 가장 아끼는 것을 단어로. 기억 제목을 보고 Claude Haiku 가 고른다. 누르면 그 기억을 모아 본다.
- **쉬운 말로 보는 기억**: AI 가 쓴 메모는 전보체라 읽기 어렵다. 열면 한 줄 요약, 왜 기억하는지, 언제 떠올리는지, 어려운 낱말 풀이가 먼저 나오고 원문은 접혀 있다.
- **예/아니요 피드백**: 기억마다 "아직도 배포는 release 스크립트로 하나요?" 같은 질문이 붙는다. 👍 맞아요, ✏️ 달라졌어요, ⭐ 중요해요, 🗑 필요 없어요를 누르면 📮 우체통에 모였다가 한 번에 해마에게 간다.
- **물어보기**: 프로젝트의 뇌와 대화한다. 기억 안에서만 답하고 근거로 쓴 기억을 단다.
- **먹이 주기**: 꼭 기억해야 할 것을 알려 준다.
- **뇌 최적화**: 머리가 무거워지면 해마가 합치고 줄인다(지우지 않고 보관). 시작 전에 몇 번 일할지 보여 준다.
- **성격**: 품종(다람쥐, 부엉이, 고양이, 거북이)을 고르거나 성향을 상황에 직접 잇는다.
- **해마 일지와 설정**: 해마가 한 일, 켜기,끄기, 모델, 언어, 테마.

앱은 기억을 직접 고치지 않는다. 먹이, 피드백, 정리는 해마가 늘 쓰는 큐로 넘긴다.

### 성격

성향은 반대 쌍(추진/신중, 자율/호기심, 빠름/꼼꼼, 최소/적극, 간결/친절)이고 상황(평소, 되돌리기 어려운 작업, 코드를 고친 뒤, 큰 변경, 모호한 요청, 처음 보는 영역)에 잇는다. 세기가 얼마나 세게 미는지를 정한다.

| 세기 | 일어나는 일 |
|---|---|
| 살짝 | 세션을 시작할 때 문장 하나 |
| 보통 | 더해서 요청마다 한 줄 상기 |
| 꼭! 🔒 | 더해서 훅이 강제한다: `rm -rf`, `push --force`, `reset --hard`, DB 삭제, 배포 앞에서 사용자에게 묻고, N개 넘는 파일을 고치기 전에 묻고, 빌드나 테스트 없이 끝내려 하면 한 번 되돌려 보낸다 |

성격은 정해진 표로 컴파일되므로 미리보기가 곧 Claude 가 받는 문장이다.

## 어떻게 도는가

| 부품 | 뇌에서 | brain 에서 |
|---|---|---|
| **cortex** | 대뇌 피질 - 굳어진 장기 기억 | 마크다운 기억 저장소. `common/`, `stacks/<스택>/`, `projects/<슬러그>/` 3레이어, 레이어마다 얇은 인덱스와 기억 본문 |
| **thalamus** | 시상 - 감각을 걸러 의식으로 올림 | 훅. 지금 파일, 명령, 에러에 걸린 기억을 건네고, 세션 시작 때 프로젝트 지도를 켜고, 쉬는 순간 재생을 시작한다 |
| **hippocampus** | 해마 - 새 기억 형성 | 백그라운드 `claude -p` 워커. cortex 에 쓰는 유일한 주체로 등록, 기록, 재생, 정비를 한다 |
| **sleep** | 잠 - 굳히고 잊음 | 매일 밤: 강도 집계, 망각, 남은 대화 재생, 검색 실패 학습, 정비, 검사 |

```
[떠올림 - 세션 안]
도구 호출 ─ 훅 ─▶ thalamus ─▶ cortex 에서 걸린 기억 ─▶ [기억] 메시지가 세션에 들어간다

[기록 - 세션 밖]
턴 끝, 압축 직전, 세션 끝 ─▶ thalamus ─▶ 재생(awake) ───────────────┐
매일 04:30 ─▶ sleep ─▶ 재생(scan), 검색 실패 학습, 정비 ───────────────┴─▶ 큐 ─▶ hippocampus ─▶ cortex
```

Claude Code 가 이미 쓰고 있는 대화록이 단기 기억 구실을 한다. 구간마다 한 번만 처리한다.

## 설치

```bash
git clone --single-branch https://github.com/FuJiGraphics/claude-brain.git ~/.claude/skills/brain
bash ~/.claude/skills/brain/scripts/install.sh
```

Windows 에서는 같은 두 줄을 **Git Bash**(Claude Code 가 쓰는 셸)에서 돌린다. 여러 번 돌려도 같은 결과이고, 고치는 파일은 `<파일>.brain-bak-<시각>` 으로 백업한다. 설치가 하는 일:

1. `~/.claude/settings.json` 에 thalamus 훅 등록 (다른 훅은 건드리지 않고, 모든 훅이 종료 코드 0 으로 끝나 brain 이 도구 호출을 막는 일이 없다)
2. `~/.claude/CLAUDE.md` 에 `[기억]` 메시지가 무엇인지 알리는 한 줄 (이 줄이 없으면 Claude 가 무시했다)
3. 매일 04:30 잠 예약 (macOS 는 launchd, Windows 는 작업 스케줄러, Linux 는 cron 에 `scripts/sleep.sh` 를 직접 건다)
4. `/claude-brain-*` 명령 만들기
5. OS 언어로 언어 정하기 (앱이나 `scripts/config.sh lang ko` 로 바꾼다)

**프로젝트는 저절로 등록된다.** 밤 주기가 최근 7일에 3일 이상, 요청 10개 이상 일한 git 폴더를 등록한다. 바로 하려면 `/claude-brain-sleep`.

**업데이트:** `git -C ~/.claude/skills/brain pull && bash ~/.claude/skills/brain/scripts/install.sh`. 기억은 git 추적에서 빠져 있어 그대로 남는다.
**되돌리기:** `bash ~/.claude/skills/brain/scripts/install.sh --uninstall` 이 훅, CLAUDE.md 블록, 예약을 해제한다. 기억은 폴더를 지울 때까지 남는다.

## 명령

명령은 직접 칠 때만 돈다. 대부분 훅이 바로 처리해 토큰을 쓰지 않는다.

| 명령 | 하는 일 |
|---|---|
| `/claude-brain-app` | brain 앱 열기 |
| `/claude-brain-status` | 켜짐, 해마 큐와 실패, 마지막 잠, 최근 24시간 떠올림 |
| `/claude-brain-on`, `/claude-brain-off` | 켜기, 끄기 (기억은 남는다) |
| `/claude-brain-config [default\|eco\|quality]` | 해마 모델: Sonnet medium / Sonnet low / Opus high |
| `/claude-brain-model`, `/claude-brain-effort` | 해마 모델과 effort 세부 설정 |
| `/claude-brain-sleep` | 밤 주기를 지금 |
| `/claude-brain-results` | 해마 결과 요약 |
| `/claude-brain-stop` | 지금 항목이 끝나면 해마를 멈춘다 |
| `/claude-brain-recall <이름>...` | 파일, 심볼, API, 에러, 증상으로 기억 찾기 |
| `/claude-brain-remember <내용>` | 기억할 것을 큐에 넣기 |

## 비용과 개인정보

- **떠올림**은 API 호출이 없다. 훅은 로컬 파이썬이고 한 번에 약 20ms, 세션당 평균 약 2,000자를 더한다.
- **해마**는 큐 항목마다 `claude -p`(기본 Sonnet medium)를 한 번 돌리고 Claude 구독이나 API 사용량을 쓴다. 작성자 실측에서 기록 항목은 중앙값 48턴, 9분이었다. `/claude-brain-config eco` 로 줄일 수 있다.
- **앱**은 말풍선, 쉬운 말 풀이, 물어보기에 Claude Haiku(생각 끔)를 부른다. 한 번에 약 0.001~0.005달러, 4~6초이고 풀이는 캐시한다.
- **개인정보**: 기억, 로그, 앱은 이 컴퓨터에 남는다. 네트워크로 나가는 것은 Claude Code 가 어차피 하는 Claude API 호출뿐이다. 앱은 `127.0.0.1` 에서만, 실행마다 새 토큰으로 열린다.
- **권한**: 해마는 승인 프롬프트 없이 돈다(물을 사람이 없다). 대신 git 쓰기, `rm`, `sudo`, 설정과 다른 스킬 편집을 거부 규칙으로 막는다. [해마의 권한](#해마의-권한) 참고.

## 자주 묻는 질문

**`CLAUDE.md` 로 충분하지 않나?** 모든 세션에 필요한 몇 가지 규칙에는 완벽하다. 하지만 통째로 실리고, 손으로 쓰고, 스스로 정리되지 않는다. brain 은 긴 꼬리(수백 개의 함정과 결정)를 맡고 지금 파일이나 에러에 걸린 것만 꺼낸다.

**Claude Code 자동 메모리는 켜 둘까?** 끄기를 권한다(`"autoMemoryEnabled": false`). 둘 다 "지난번에 알아낸 것" 을 담는데, 자동 메모리는 고쳐 주는 주체가 없고 시작마다 실려서 낡은 내용이 최신 기억을 덮을 수 있다.

**기억이 틀리면?** 앱에서 열고 ✏️ 달라졌어요를 누른다. 해마가 확인하고 고친다. 기억에는 확인한 날짜가 있고, 지금 코드가 늘 기억보다 우선이다.

**기억이 끝없이 커지지 않나?** 밤 잠이 겹친 것을 합치고 안 쓰는 기억을 숨긴다(검색으로는 찾힌다). 앱의 "머리 무게" 가 정리가 필요한 때를 알려 준다.

**팀이 같이 쓸 수 있나?** 아직은 아니다. 기억은 기기마다 있다. `cortex/` 를 직접 동기화할 수는 있지만 여러 명이 동시에 쓰도록 설계하지 않았다.

**Cursor, Codex 같은 데서도 되나?** 안 된다. Claude Code 훅 위에 만들었다.

**어떤 언어를 쓰나?** 앱, 세션 문구, 성격은 영어, 한국어, 일본어, 중국어. 기억은 대화한 언어로 쌓인다. 일본어,중국어 증상 문장 검색은 파일,심볼 일치(언어 무관)보다 약하다.

**무엇을 넣었는지 볼 수 있나?** `/claude-brain-status` 가 최근 떠올림 수와 글자 수를, `.active/recall.log` 가 모든 사건을 보여 준다.

## 한계

- **한 사람의 프로젝트에서 잰 값이다** (macOS, 주로 Unity/C# 와 VS Code 확장). 단서 추출은 C# 컴파일 에러에 맞춰 다듬었다. 파일과 API 일치는 언어와 무관하다.
- **Windows 지원은 새로 붙었다 (beta).** 경로, 훅, 작업 스케줄러, 앱을 옮기고 검토했지만 실제 Windows 기기에서는 아직 돌려 보지 않았다. 문제가 있으면 이슈로 알려 달라.
- **맥락이 중요한 일에서는 시간과 토큰을 더 쓴다** (벤치마크 참고). 일회성 스크립트가 아니라 몇 주 단위로 이득이 난다.
- **해마는 이 컴퓨터에서 감독 없이 도는 에이전트다** (거부 규칙이 있다). 불편하면 `scripts/hippocampus-perm.mode` 를 `acceptEdits` 로 바꾼다. 그러면 쓰지 않고 판정만 남긴다.
- **아직 팀용이 아니고**, Claude Code 전용이다.

## 참고 자료

<details><summary><b>떠올림 - thalamus</b></summary>

훅은 SessionStart, UserPromptSubmit, PreToolUse(Edit, Write, MultiEdit, NotebookEdit, Bash, AskUserQuestion), PostToolUse(Read), PostToolUseFailure(Bash), SubagentStart, Stop, PreCompact, SessionEnd 에 걸린다. `cortex/registry.md` 에 등록된 프로젝트 안에서만 동작한다.

| 훅 이벤트 | 단서 |
|---|---|
| SessionStart | 프로젝트 요지(registry 비고), 프로젝트 `INDEX.md`(2,500자 상한), 절차 기억(단계 카드) 줄. 압축 뒤에는 떠올린 목록을 비운다 |
| PostToolUse (Read) | 연 파일 이름. 기억 저장소 안의 파일이면 열람 횟수만 기록 |
| PreToolUse (Edit, Write, MultiEdit, NotebookEdit) | 고칠 파일 이름, 편집 내용에 새로 나온 API 이름 |
| PreToolUse (Bash) | 명령이 읽거나 쓰는 파일 이름, 명령 속 코드의 API 이름 |
| PostToolUseFailure (Bash) | C# 컴파일 에러의 파일과 에러 코드, 예외 이름과 첫 프로젝트 프레임의 파일 |
| SubagentStart | 작업 폴더의 프로젝트와 `[기억]` 이 무엇인지 알리는 한 줄 |
| Stop, PreCompact, SessionEnd | 떠올림은 없다. 새 대화 구간이 두드러지면 깨어 있는 중 재생을 시작 |

- 걸린 기억이 없으면 출력이 없다. 한 번에 1~2개(Bash 는 1개), 항목당 240자 이하, 세션당 40개 또는 9,000자가 상한이다.
- 단서 하나가 서로 다른 기억 4개 이상에 걸리면 흔한 단서로 보고 파일 이름에 그 단서가 든 기억만 남긴다.
- 보여 줄 수보다 많이 걸리면 최근에 쓰인 기억이 앞선다(14일 안 +2, 45일 안 +1).

**떠올림 판정.** 과거 대화록 431세션을 재생해 371건을 Sonnet 이 판정했다(유용, 관련, 방해). 방해 비율은 파일 열람 0~3%, 편집 직전 8~20%, 명령이 다루는 파일 약 10% 라서 떠올리고, 사용자 요청 글 64%, "안 된다" 결론 75%, 명령문 속 CLI 이름 64% 는 글자 일치로 의도를 알아볼 수 없어 떠올리지 않는다.
</details>

<details><summary><b>기억 저장소 - cortex</b></summary>

```
cortex/
├── registry.md            # 경로 프리픽스, 프로젝트 슬러그, 스택, 스택 버전, 비고
├── common/                # 스택과 무관한 기억 (도구 함정, 일반 원칙)
├── stacks/<스택>/         # 엔진, 프레임워크 일반
└── projects/<슬러그>/     # 프로젝트 고유 (구조, 진입점, 컨벤션 위치)
```

- 레이어는 "이 사실이 어디까지 일반화되는가" 로 가른다.
- 레이어마다 얇은 인덱스(`INDEX.md`, 이름에 `index` 가 든 `.md`)가 있고, 인덱스 줄의 첫 링크가 기억 본문이다.
- 단서가 인덱스 줄의 앞 160자, 첫 링크 글, 기억 파일 이름 중 하나에 있어야 그 기억의 주제로 본다.
- **기록 기준.** 조사 비용을 치르고 알아낸 것, 사용자가 말해 줘야만 알 수 있는 것만 기억한다. 코드를 열면 몇 초 만에 확인되는 것은 기억하지 않는다.
- cortex 에 쓰는 주체는 hippocampus 하나다(예외는 밤 망각이 옮기는 인덱스 줄).
</details>

<details><summary><b>기록, 잠, 망각, 기억 강도</b></summary>

| | awake (깨어 있는 중) | sleep (잠) |
|---|---|---|
| 시작 | 턴 끝, 압축 직전, 세션 끝에 thalamus 가 백그라운드로 | 매일 04:30. 놓치면 깨어난 뒤 한 번. `/claude-brain-sleep` 으로 지금 |
| 대상 | 지난 처리 위치 뒤에 새로 쌓인 대화록 구간 | 깨어 있는 중에 처리되지 못한 구간 |
| 조건 | 4,000바이트 이상, 두드러짐 6 이상(압축 직전과 세션 끝은 3 이상). 같은 대화록은 20분에 한 번, 전체는 시간당 4건 | 두드러짐 6 이상, 높은 순 4건. 처음 보는 대화록은 최근 2일치만 |
| hippocampus | 최대 120턴, 20분 | 최대 200턴, 30분 |

두드러짐 점수: 사용자의 정정 3, 결정 표현 3, 기억 요청 5, 권한 거부 2, 도구 실패 1(최대 5), 반복 조사 1(최대 3), 요청 5개 이상이면 1.

잠 주기: 강도와 검색 실패 집계 → 망각(해마가 일하는 중이면 건너뜀) → 남은 구간 재생(최대 4건)과 활발한 미등록 프로젝트 1곳 등록 → 검색 실패 학습(실패 뒤 다른 이름으로 찾은 짝이 5개 이상이면 별칭 판단) → 가장 오래 정비하지 않은 조각 3개 정비(조각은 약 4만 토큰 이하) → `check.py` 검사. 숫자는 `scripts/sleep.conf` 로 바꾼다.

**망각과 되살림.** 마지막 사용일은 떠올림, 열람, 검색 히트, 본문 수정일, 설치일 중 가장 늦은 날이다. 45일(사용자 결정, 함정, 사고, 손실, 파괴가 든 기억은 120일)이 지나면 인덱스 줄을 `<레이어>/dormant.md` 로 옮긴다. 본문은 남고 검색으로는 찾히며(잠재 기억), 다시 쓰이면 원래 인덱스로 돌아온다. 하드 삭제는 없다.

**기억 강도.** `cortex/.hippocampus/strength.json` 에 기억마다 `{shown, opened, grepped, last}` 를 둔다. 망각, 떠올림 순위(14일 안 +2, 45일 안 +1), 해마 정비의 판단 재료로 쓴다. 강도가 낮다는 것만으로 지우지 않는다.
</details>

<details><summary><b>해마의 권한</b></summary>

> [!IMPORTANT]
> **hippocampus 는 승인 프롬프트 없이 도는 설정이 기본값이다**(`scripts/hippocampus-perm.mode` 의 `bypassPermissions`). 스킬을 `~/.claude/skills/` 아래에 두면 cortex 도 그 아래에 놓이는데, Claude Code 는 `.claude/` 를 보호 경로로 취급해 편집마다 사람의 승인을 요구한다. 해마는 비대화형 `claude -p` 라 승인할 사람이 없다.

- **해마 프로세스에만 적용된다.** 대화 세션 권한은 그대로다.
- 도구는 Read, Write, Edit, Grep, Glob, Bash, WebFetch, WebSearch 로 한정되고 MCP 서버와 스킬은 붙이지 않는다.
- git 쓰기(`commit`, `push`, `checkout`, `reset`, `switch`, `stash`, `rebase`, `merge`, `restore`, `clean`, `add`, `rm`, `mv`), `rm`, `sudo`, `find -delete` 는 거부 규칙으로 막는다. 같은 skills 폴더의 모든 스킬 본문과 설정 폴더의 `settings.json`, `settings.local.json`, `CLAUDE.md`, `hooks/` 편집도 막는다. 거부 규칙은 이 모드에서도 유효하다.
- 끄려면 `echo acceptEdits > ~/.claude/skills/brain/scripts/hippocampus-perm.mode`. 항목이 `denied` 로 끝나고 판정은 `scripts/hippocampus-ctl.sh results` 에 남는다.

항목마다 `claude -p` 를 한 번 띄운다. 모드별 상한은 register,harness-refresh 120턴 15분, record 200턴 30분, replay(awake) 120턴 20분, replay(sleep) 200턴 30분, sweep,targeted 400턴 40분이다. 사용 한도나 로그인 문제로 멈춘 항목은 큐로 되돌린다. 토큰을 아끼려고 지침에서 이번 모드에 필요한 절만 싣고, 스킬 목록과 플러그인을 끈다.
</details>

<details><summary><b>설계 근거 실측</b></summary>

| 사실 | 근거 |
|---|---|
| 훅으로 컨텍스트를 넣을 수 있는 자리는 SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, PostToolUseFailure, Stop 이다 | Claude Code 2.1.283 격리 실행, 2026-09-29 |
| 명령형 훅 문구는 프롬프트 주입으로 의심받아 따르지 않았다 | 같은 실험 |
| `CLAUDE.md` 한 줄이 없으면 `[기억]` 을 출처 불명 삽입으로 보고 무시했다 | 같은 날 |
| 강제 대조 규칙이 Edit, Write 6,300건 중 1,264건, Bash 쓰기 893건 중 290건에서 지켜지지 않았다 | 분리 전 구조의 게이트 로그(shadow 모드) |
| 세션이 시켜야 도는 정비는 돌지 않았다 - 큐 668건 중 기록 322, 정비 0 | 분리 전 구조의 큐 기록 |
| 해마 기록 항목: 58회 중앙값 48턴 9분(90백분위 83턴 15분) | 실측 |
| 앱의 Haiku 호출: 생각을 켜면 38초 0.024달러, 끄면 6초 0.004달러 | 2026-10-05 |
</details>

<details><summary><b>폴더 구조와 요구 사항</b></summary>

```
brain/
├── SKILL.md, commands/        # /brain 제어판, /claude-brain-* 명령 템플릿
├── agents/hippocampus.md      # 해마 지침
├── scripts/                   # thalamus.py(훅), nbsearch.py(검색), hippocampus-*.sh, sleep.sh,
│                              # persona.py(성격), lang.py(언어), plat.py(OS 차이), install.sh …
├── editor/                    # brain 앱 (server.py + web/)
├── promo/                     # 홍보 영상 도구 (데모 뇌, 녹화)
├── cortex/                    # 기억 (이 컴퓨터에서 자란다, git 추적 안 함)
└── .active/                   # 런타임 상태 (git 추적 안 함)
```

| | |
|---|---|
| Claude Code | 2.1.28x 이상 (2.1.283 에서 검증) |
| Python | 3.7 이상 (`python3`, `python`, `py` 중 하나) |
| `claude` CLI | PATH 에 있어야 한다 (해마와 앱이 부른다) |
| 셸 | bash 3.2 이상. Windows 는 Git Bash (Git for Windows) |
| 앱 창 | Chrome(macOS, Linux) 또는 Edge(Windows) 앱 모드, 없으면 기본 브라우저 |
| OS | macOS (만들고 실측한 곳), Windows (beta), Linux (동작, 잠은 cron 으로) |
</details>

<details><summary><b>n-worker 와의 관계</b></summary>

brain 은 [n-worker](https://github.com/FuJiGraphics/n-worker) 안에 있던 장기 기억(노트북, curator 데몬, nb-grep, 노트북 게이트)을 떼어 독립시킨 스킬이다. 두 스킬은 서로를 부르지 않는다. 둘 다 있으면 n-worker 세션에도 `[기억]` 이 떠오르고 판단 재료로 쓴다. `cortex/common/search-aliases.md` 가 옛 이름(노트북, curator, nb-grep)으로 찾아도 새 이름이 걸리게 잇는다.
</details>

## 라이선스

[CC BY-ND 4.0](LICENSE) (저작자표시-변경금지 4.0 국제). Copyright (c) 2026 Cheol Jin Choi (FuJiGraphics).

| 항목 | 내용 |
|---|---|
| 상업적 이용 | 가능 - 회사 업무, 유료 서비스 안에서 써도 된다 |
| 공유, 재배포 | 가능 - 원본 그대로일 때만 |
| 수정본 배포 | 불가 - 고치거나 일부를 떼어 낸 버전은 배포할 수 없다 |
| 저작자 표기 | 필수 - 저작자, 저장소 주소(https://github.com/FuJiGraphics/claude-brain), 라이선스 |

수정본을 배포하려면 저작자에게 따로 허락을 받는다. 설치한 기기에서 쌓이는 cortex 기억은 사용자 본인의 것이며 이 라이선스와 무관하다.

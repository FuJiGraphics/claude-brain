---
name: brain
description: >
  Long-term memory control panel for Claude Code. Use only when the user calls /brain. Memory itself runs without being
  called: the thalamus hook recalls memories that match the file, command or error at hand, the hippocampus reviews
  transcripts and records new memories, and a nightly sleep tidies and forgets. This skill shows status, looks up
  memories, records something directly, and runs sleep now. Each command also has a /claude-brain-<command> shortcut.
disable-model-invocation: true
---

# brain - 장기 기억

사람의 장기 기억을 본뜬 하네스다. 세션(의식)은 이 장치를 모르고, 필요한 기억이 `[기억]` 으로 떠오를 뿐이다.
이 파일은 사용자가 `/brain` 으로 불렀을 때만 읽힌다. 아래 경로의 `<brain>` 은 이 파일이 있는 폴더다.

| 부품 | 하는 일 | 파일 |
|---|---|---|
| cortex (대뇌 피질) | 장기 기억 저장소. registry, common, stacks/<스택>, projects/<슬러그> 3레이어 | `cortex/` |
| thalamus (시상) | 세션 시작 때 그 프로젝트의 기억 지도를 켜고, 작업 중 다루는 파일, 새 API, 명령이 다루는 파일, 컴파일 에러에 걸린 기억을 떠올린다. 쉬는 순간(턴 끝, 압축 직전, 세션 끝)에 두드러진 구간을 해마로 넘긴다 | `scripts/thalamus.py` (훅) |
| hippocampus (해마) | 대화록 구간을 되짚어 새 기억을 만들고, 정비하고, cortex 에 쓰는 단일 주체 | `agents/hippocampus.md`, `scripts/hippocampus-*.sh` |
| sleep (잠) | 매일 밤: 기억 강도 집계, 망각(오래 안 쓴 기억 숨기기), 남은 구간 재생, 검색 실패 학습, 조각 정비, 검사 | `scripts/sleep.sh` |

## 사용자가 부르는 일

명령마다 단축 명령 `/claude-brain-<명령>` 이 있다(설치가 `<설정 폴더>/commands/` 에 만든다). `/brain <명령>` 으로 불러도 같다.
**훅이 바로 처리**하는 명령은 모델을 거치지 않아 토큰을 쓰지 않고, 이 스킬까지 오지 않는다. 여기까지 왔으면 훅이 꺼진 것이니 아래 스크립트를 직접 돌린다.

| 명령 | 할 일 | 처리 |
|---|---|---|
| `status` (인자 없는 `/brain` 포함) | `bash <brain>/scripts/status.sh` - 켜짐, 해마 설정과 큐, 실패, 마지막 잠, 검사, 최근 떠올림 | 훅 |
| `on`, `off` | `bash <brain>/scripts/config.sh on` 또는 `off`. 끄면 떠올림, 조사 한 줄, 재생, 밤 잠이 멈추고 상태줄의 `[BRAIN]` 이 사라진다. 기억은 남는다 | 훅 |
| `on here`, `off here` | 지금 폴더의 프로젝트만 깨우기/쉬기 - `config.sh unmute <슬러그>` / `mute <슬러그>`(`.active/config` 의 `mute=`). 쉬는 프로젝트는 떠올림, 성격, 대화 되짚기가 모두 쉰다 | 훅 |
| `register` | `python3 <brain>/scripts/register.py <현재 폴더>` - 위로 가장 가까운 git 루트를 해마에게 등록해 달라고 맡긴다(밤의 자동 등록 조건을 기다리지 않는다) | 훅 |
| `config [default\|eco\|quality\|lang <언어>]` | 값이 있으면 `config.sh preset <이름>`(또는 `config.sh lang <ko\|en\|ja\|zh>`), 없으면 `config.sh show`. default = Sonnet 5.5 medium, eco = Sonnet 5.5 low, quality = Opus 5.5 high | 훅 |
| `model <sonnet\|opus\|haiku>`, `effort <low\|medium\|high\|xhigh\|max\|auto>` | `config.sh model <이름>`, `config.sh effort <값>` | 훅 |
| `stop` | `bash <brain>/scripts/hippocampus-ctl.sh stop` (지금 항목이 끝나면 멈춘다) | 훅 |
| `sleep` | `bash <brain>/scripts/sleep.sh` - 투입만 하고 곧 끝난다. 처리는 해마가 뒤에서 한다 | 훅 |
| `results` | `bash <brain>/scripts/hippocampus-ctl.sh results --brief` (전체는 `results`, 본 것 표시는 `--ack`) | 훅 |
| `app` | `bash <brain>/scripts/editor.sh` - brain 앱(로컬 웹)을 띄우고 주소를 알린다(옛 이름 editor 도 받는다). 끄기는 `editor.sh stop` | 훅 |
| `update` | `bash <brain>/scripts/update.sh` - 새 버전을 fast-forward 로 받고 install.sh 를 다시 돌린다. 직접 고친 파일이나 따로 만든 커밋이 있으면 멈춘다. 기억(cortex)은 git 이 추적하지 않아 그대로다 | 모델 |
| `backup` | `bash <brain>/scripts/backup.sh make` - 기억과 성격을 zip 하나로(기본 ~/Downloads). 다른 컴퓨터에서 `backup.sh restore <zip>` 으로 되살린다(홈 폴더가 다르면 프로젝트 경로를 바꿔 준다) | 모델 |
| `recall <이름>...` | 현재 폴더에서 `bash <brain>/scripts/recall.sh <이름>...`. 찾은 기억의 요지와 경로를 알려 준다 | 모델 |
| `remember <내용>` | `bash <brain>/scripts/remember.sh "<내용> - 근거: <file:line 또는 사용자 발화>"` - 해마 큐에 넣고 끝난다. 근거는 대화에서 찾아 붙이고 사용자에게 되묻지 않는다 | 모델 |

언어: `bash <brain>/scripts/config.sh lang <ko|en|ja|zh>` (앱 설정의 언어와 같다). 앱 화면, 명령 결과와 설치 글(`scripts/cli_i18n.py`), 해마의 결과 요약, 세션에 들어가는 `[기억]` 문구, 성격 문장, 앱의 Haiku 답이 이 언어를 따르고, 기억은 해마가 대화 언어로 쓴다. 설치가 OS 언어로 처음 값을 정한다.
OS: macOS, Linux, Windows(Git Bash, beta). OS 차이(경로 표기, Git Bash 찾기, 프로세스 분리)는 `scripts/plat.py` 가 맡는다.

## 지키는 것

- cortex 쓰기는 hippocampus 만 한다(여기서도 직접 고치지 않는다). 사용자의 요청은 `remember.sh` 로 넘긴다.
- 돌보기 앱(`editor/`)도 cortex 를 직접 고치지 않는다 - 먹이,정정은 remember.sh, 최적화는 sweep 큐로 넘긴다. 앱이 직접 쓰는 것은 성격(`persona/`)과 캐시,모음(`.active/topics/`, `.active/explain/`, `.active/feedback/`)뿐이다. 피드백 우체통도 보낼 때 remember.sh 로 넘긴다.
- 하드 삭제는 없다. 잊은 기억은 `dormant.md`(잠재) 또는 `_archive/` 로 옮겨진다.
- 해마는 사용자에게 묻지 않는다. 판단이 필요한 것은 해마가 정하고, 코드 문제는 사실로 기억해 그 코드를 만지는 세션에 떠오르게 한다.
- 설치, 훅 등록, 잠 예약, 명령어 파일은 README 의 설치 절을 따른다.

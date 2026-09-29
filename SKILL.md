---
name: brain
description: >
  장기 기억 제어판. 사용자가 /brain 으로 부를 때만 쓴다. 기억 자체는 호출 없이 늘 돈다 - thalamus 훅이 지금 다루는
  파일, 명령, 에러에 걸린 기억을 떠올리고, hippocampus 가 대화록을 되짚어 새기고, 밤마다 잠이 정리와 망각을 한다.
  이 스킬은 상태 보기, 기억 찾기, 직접 새기기, 지금 잠들기, 사용자 판단 대기 처리를 한다.
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

`/brain` 뒤의 말로 고른다. 결과는 사용자에게 짧게 보고한다(표준 용어, 표).

| 명령 | 할 일 |
|---|---|
| (없음), `status` | `bash <brain>/scripts/status.sh` 출력을 요약한다 - 켜짐 여부와 해마 설정, 해마 큐와 실패, 마지막 잠, 오늘 떠올림 수, 검사 결과, 판단 대기 수 |
| `on`, `off` | 보통은 훅이 먼저 처리해 이 스킬까지 오지 않는다(caveman 처럼 즉시, 토큰 없이). 여기까지 왔으면 `bash <brain>/scripts/config.sh on` 또는 `off`. 끄면 떠올림, 조사 한 줄, 재생, 밤 잠이 멈추고 상태줄의 `[BRAIN]` 이 사라진다. 기억은 그대로 남는다 |
| `config` | 뒤에 `default`, `eco`, `quality` 가 있으면 훅이 바로 처리한다. 없으면 `config.sh show` 로 지금 값을 보여 주고 `AskUserQuestion` 한 번으로 고르게 한다 - default(Sonnet 5.5, effort high, 권장), eco(Sonnet 5.5, effort medium, 사용량 절약), quality(Opus 5.5, effort high). 고른 것을 `config.sh preset <이름>` 으로 반영하고 결과 두 줄을 보여 준다 |
| `model <sonnet\|opus\|haiku>`, `effort <low\|medium\|high\|xhigh\|max\|auto>` | 훅이 바로 처리한다. 여기까지 왔으면 `config.sh model <이름>` 또는 `config.sh effort <값>` |
| `recall <이름>...` | `bash <brain>/scripts/recall.sh <이름>...` (현재 폴더의 프로젝트 기준). 결과의 기억 경로를 알려 준다 |
| `remember <내용>` | `bash <brain>/scripts/remember.sh "<내용과 근거>"` - 해마 큐에 넣고 끝난다. 근거(file:line 이나 사용자 발화)를 함께 적어야 해마가 확인할 수 있다 |
| `sleep` (지금 잠들기) | `bash <brain>/scripts/sleep.sh` - 투입만 하고 곧 끝난다. 처리는 해마가 뒤에서 한다 |
| `results` | `bash <brain>/scripts/hippocampus-ctl.sh results` (본 것은 `--ack`) |
| `pending` | `<brain>/cortex/.pending.md` 를 읽고 사용자가 결정할 것만 묶어서 `AskUserQuestion` 으로 묻는다. 답은 `remember.sh` 로 해마에 넘긴다 |
| `stop` | `bash <brain>/scripts/hippocampus-ctl.sh stop` (지금 항목이 끝나면 멈춘다) |

## 지키는 것

- cortex 쓰기는 hippocampus 만 한다(여기서도 직접 고치지 않는다). 사용자의 요청은 `remember.sh` 로 넘긴다.
- 하드 삭제는 없다. 잊은 기억은 `dormant.md`(잠재) 또는 `_archive/` 로 옮겨진다.
- 설치, 훅 등록, 잠 예약은 README 의 설치 절을 따른다.

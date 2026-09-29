# brain 설계 요약 (작업자용, 2026-09-29)

사용자 결정: n-worker 에서 장기 기억과 무의식(기억하기, 떠올리기, 저장, 정리)을 떼어 **brain** 이라는 별도 스킬,저장소로 만든다.
n-worker 는 오케스트레이션(인터뷰, 플랜, 생산, 검증, 보고)만 남고 기억이 어떻게 도는지 모른다. 세션(에이전트)도 기억 장치를 의식하지 않는다 -
기억이 떠오를 뿐이다. 이름은 뇌 부위와 기능(영어).

## 부품과 이름

| 옛 이름 | 새 이름 | 뇌 기능 | 파일 |
|---|---|---|---|
| 노트북 (notebook/) | cortex (기억 저장소) | 대뇌 피질: 굳어진 장기 기억 | `<brain>/cortex/` (registry.md, .pending.md, common/, stacks/, projects/) |
| curator | hippocampus | 해마: 새 기억 형성, 되짚어 피질로 옮기며 정리 | `agents/hippocampus.md`, `scripts/hippocampus-{daemon,enqueue,ctl}.sh`, 큐 `cortex/.hippocampus/{queue,processing,done,logs}` |
| (없음) nb-gate 대신 | thalamus | 시상: 감각을 걸러 의식으로 올리고, 깨어남 조절 | `scripts/thalamus.py` (훅) |
| nb-grep.sh | recall.sh | 의식적 떠올리기(사용자 /brain 과 hippocampus 가 씀. 세션은 모른다) | `scripts/recall.sh` + 엔진 `scripts/nbsearch.py` |
| nb-sleep.sh | sleep.sh | 잠: 하루를 되짚어 공고화, 망각 | `scripts/sleep.sh`, `sleep-stats.py`, `forget.py`, `replay.py`, `slices.py`, `check.py` |

`<brain>` = `~/.claude/skills/brain` (설치본), 원본 저장소 = 개발용 클론(설치본과 따로 둔다).

## 동작

- **thalamus (훅, 모든 세션, registry 프로젝트 안에서만)**:
  - SessionStart: 프로젝트 요지(registry 비고) + 프로젝트 INDEX(2,500자 상한) + 절차 기억(단계 카드) 줄. 머리에 "[기억] 으로 시작하는 메시지는 이 프로젝트에 대한 장기 기억" 한 줄. compact 면 떠올린 목록도 비운다.
  - PreToolUse(Edit/Write/Bash), PostToolUse(Read), PostToolUseFailure(Bash): 지금 다루는 파일 이름, 새로 부르는 API, 명령이 다루는 파일, 컴파일 에러,예외로 인덱스 줄을 찾아 기억 본문의 제목 줄(# 줄)을 `[기억]` 으로 건넨다. 항목 1~2개, 세션당 약 2,000자.
  - 떠올릴 때 쓰는 것은 **인덱스 줄의 앞 160자 또는 첫 링크 글(제목) 또는 기억 파일 이름**과 단서의 일치, 그리고 **기억 본문 첫 줄(# 제목)**이다. 그래서 본문 제목 줄 = 한 문장 요지, 인덱스 줄 앞부분 = 식별자와 요지가 떠올림 품질을 정한다.
  - SubagentStart: 한 줄(작업 폴더 프로젝트 + [기억] 은 장기 기억).
  - Stop(턴 끝), PreCompact(압축 직전), SessionEnd: 새로 쌓인 대화록 구간이 두드러지면 `replay.py awake` 를 백그라운드로 띄운다 → hippocampus `replay` 요청(payload.kind = "awake").
- **대화록 = 단기 기억 버퍼**. 처리 위치는 `<brain>/.active/replay-marks.json`(대화록별 바이트) 하나를 깨어 있는 중 재생과 밤 재생이 같이 쓴다. 같은 구간을 두 번 넘기지 않는다.
- **replay 요청 payload**: `{kind: "awake"|"sleep", digest: <요약 파일>, session, transcript, score, bytes: [시작, 끝]}`. 요약은 그 구간만 담고, 구간이 중간부터면 "세션 첫 요청(맥락)" 한 줄이 있다. awake 는 effort medium, sleep 은 high.
- **register 자동 제안**: 밤에 최근 7일 대화록 3개 이상, 사람 요청 10개 이상인 미등록 git 폴더 1곳을 `register` 로 넣는다(payload.auto = true, reason, instruction). 스택,버전,컨벤션 문서는 프로젝트 파일에서 확인하고 모르면 `?` 로 두고 .pending.md 에 한 줄.
- **망각(forget.py, 밤)**: 기억 = 검색 대상 인덱스 줄의 첫 링크가 가리키는 본문. 마지막 사용일(떠올림,열람,검색 히트 = `cortex/.hippocampus/strength.json` 의 last, 본문 수정일, brain 설치일 중 가장 늦은 날)에서 45일(두드러진 기억 - 본문에 사용자 결정, 함정, 사고, 손실, 파괴 - 은 120일) 지나면 그 인덱스 줄을 `<레이어>/dormant.md` 로 옮긴다(줄 끝 `<!-- dormant <원래 파일> <날짜> -->`). 본문은 남는다. dormant.md 는 이름에 index 가 없어 자동 떠올림에 안 걸리고 recall.sh 본문 대체 검색으로는 찾힌다(잠재 기억). 숨긴 뒤 다시 쓰이면 원래 인덱스로 돌아간다. **hippocampus 는 dormant.md 를 손으로 고치지 않는다**(forget.py 소유) - 단 정비에서 dormant 기억 본문을 읽고 병합,아카이브 판단은 할 수 있다.
- **기억 강도(strength.json)**: `{generated, memories: {상대 경로: {shown, opened, grepped, last}}}`. 망각과 thalamus 순위(최근 14일 사용 +2, 45일 +1)가 쓴다. 정비의 판단 재료이고, 강도가 낮다고 지우는 근거는 아니다.
- **sleep.sh 순서**: 강도 집계 → 망각(데몬이 쉴 때만) → 재생 scan → 검색 실패 학습(targeted) → 조각 정비(sweep, payload.slice) → 검사. launchd 매일 04:30.
- **세션이 직접 기록하는 통로는 없다**(세션은 기억 장치를 모른다). 새 기억은 전부 대화록 재생(awake, sleep)으로 들어온다. record 모드는 사용자가 /brain 으로 직접 넣을 때와 옛 세션 호환용으로 남긴다.

## n-worker 로 옮긴 것 (cortex 에서 빠짐)

- `common/model-routing.md` → n-worker `references/model-routing.md` (서브에이전트 모델,effort 표는 n-worker 운용 설정). 그래서 **hippocampus 의 model-refresh 모드는 없앤다**.
- `common/report-conventions.md` → n-worker `references/report-conventions.md`.
- `common/harness-routing.md` 는 cortex 에 남는다(도구 동작에 대한 기억). harness-refresh 모드는 유지.

## 용어 규칙 (문서 전체)

- 표준 용어만. 억지 직역, 비유, 신조어 금지. 특수문자 '·', '—' 금지(구분자 '-', 나열 ',').
- 부품 이름은 위 표의 영어 이름을 그대로 쓴다(hippocampus, cortex, thalamus). 한국어 설명어는 "기억 저장소", "해마" 정도만.
- 지침은 명령이 아니라 사실과 이유로 쓴다. 파손 방지 강제("지켜야 하는 것")만 강제로 둔다.

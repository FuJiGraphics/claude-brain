# harness-routing - 이 스킬이 기댄 하네스(Claude Code) 동작 목록

> 스킬은 프롬프트, 훅, `claude -p`, Workflow 같은 하네스 표면 위에서 돈다. 그중 문서에 없는 관측 동작에 기댄 곳을 여기 모은다. model-routing.md 가 모델 세대 노후화를 잡는 것과 같은 원리로 이 파일은 하네스 버전 노후화를 잡는다. 층은 common(어느 스택, 프로젝트에서도 같은 사실).

```
checked: 2026-09-06 (전 관측 행 3회 대조. 요청 payload 의 보고 버전은 261, 263, 261 로 세 번 다 어긋났고 검증 프로세스 env `AI_AGENT` 실측은 세 번 다 263 - 아래 checked_version 은 실측값이다. nb-load 가 문자열 그대로 비교하므로 그 줄에 주석 금지. §5 2026-09-06 버전 소스 불일치 항 참조)
checked_version: claude-code_2-1-263_agent
갱신 트리거 (②나 ③일 때 curator harness-refresh 를 큐에 넣는다. ①은 정보다 - 하네스 버전은 자주 바뀌고 대조 실행마다 비용이 들며, 대조는 동작 검증이 아니다):
  ① nb-load 가 읽은 현재 버전(env AI_AGENT, 없으면 `claude --version`)이 checked_version 과 다르다 - nb-load 가 한 줄 알린다
  ② 아래 표의 항목이 실행 중 깨졌다(데몬 done 파일 denied, wf-summarize 0건 파싱, 게이트 미발화)
  ③ 사용자가 갱신을 요청했다
checked_version 은 마지막으로 대조한 버전이다. 동작이 실제로 확인된 버전은 §5 실측 기록의 날짜와 버전으로 본다.
```

## 1. 원칙

- 관측한 하네스 동작을 스킬 규칙으로 승격할 때는 여기에 행을 만든다. 문서화된 동작은 근거 칸에 `문서`, 관측만 된 동작은 `관측 <날짜>` 로 적는다.
- 행마다 "깨졌을 때" 가 있어야 한다. 폴백 없는 의존은 만들지 않는다.
- 확인하지 못한 것은 "미확인" 으로 둔다. 추측을 적으면 이후 전 세션의 동작이 오염된다.

## 2. 항목

| # | 가정 | 사용 위치 | 근거 | 깨졌을 때 |
|---|---|---|---|---|
| 1 | `.claude/` 는 protected path - Edit/Write 마다 대화형 승인 강제. acceptEdits, allow 규칙(`Edit(경로/**)`), 훅 `permissionDecision: allow` 어느 것으로도 못 넘는다. 건너뛰는 유일한 수단은 bypassPermissions. deny 규칙은 bypass 에서도 유효. 운영체제 무관 | scripts/curator-daemon.sh(권한 플래그, `--tools`, `--disallowedTools`) | 문서 permission-modes.md, permissions.md + 관측 2026-09-03(acceptEdits, allow, 훅 전부 `which is a sensitive file` 로 거부) | 데몬 done 파일 `status: denied` → nb-load 가 알린다. 대안은 노트북을 `~/.claude` 밖으로 옮기는 것 |
| 2 | Bash 도구 환경변수에 `CLAUDE_CODE_SESSION_ID`(훅 stdin `session_id` 와 같은 값), `CLAUDE_EFFORT`, `AI_AGENT`(`claude-code_<버전>_agent`) 가 있다 | scripts/nb-load.sh(마커 sid, 버전 비교), scripts/nb-gate.sh(세션 귀속) | 관측 2026-09-03, 미문서 | 게이트가 세션을 못 찾아 전부 통과(fail-open). nb-load 가 "세션 id 환경변수 없음" 을 알린다 |
| 3 | PreToolUse 훅 stdin JSON 에 `session_id`, `tool_input.file_path`. exit 2 = 차단 + stderr 를 모델에 피드백 | scripts/nb-gate.sh | 문서 hooks-guide.md | - |
| 4 | Workflow `return` 값은 완료 알림으로 메인 컨텍스트에 통째 주입되고 약 24KB 에서 잘린다. **스크립트가 미리 슬라이스해도(예: 6000자) 합계가 24KB 를 넘으면 거기서 또 잘린다** - 슬라이스 상한은 절단을 막는 수단이 아니다(관측 2026-09-05) | SKILL.md 위임과 근거 재사용 절, references/review.md §4 | 관측 2026-08(51KB 결과에서 27KB 도착), 미문서 | 건수만 return 하므로 잘림 자체는 무해. journal 판독(#6)이 깨지면 return 전문으로 폴백 |
| 5 | Workflow `args` 는 문자열화되거나 유실될 수 있다 | references/review.md §4 | 관측 2026-07, 미문서 | 이미 프롬프트 리터럴(경로 + 요약)로 우회. 폴백 불필요 |
| 6 | Workflow 가 journal.jsonl 을 남기고 완료 알림 diagnostics 에 경로가 온다. result 한 줄의 키는 `type`,`key`,`agentId`,`result` 이고 **라벨 필드가 없다** - 어느 서브의 결과인지는 `result` 본문의 키워드로 가른다(관측 2026-09-05). 완료 알림이 잘린 보고는 journal 에서 다시 뽑는다 | scripts/wf-summarize.py, references/review.md §4 | 관측 2026-08, 미문서 | wf-summarize 가 0건 파싱이면 exit 1 → 서브 return 전문으로 폴백(24KB 한도 감수) |
| 7 | Workflow 스크립트: `parallel()` 은 throw 항목을 null 로, `meta` 는 순수 리터럴만, `Date.now()` 류는 throw | references/review.md §4 | 관측 2026-07~08 + 도구 설명 | 같은 스크립트 2회 실패 시 raw Agent 폴백(review.md §4) |
| 8 | `Agent` 도구 스키마에 `effort` 파라미터가 없다(`model` 은 있다). effort 차등은 Workflow `agent()` 에서만 가능 | SKILL.md 위임과 근거 재사용 절, references/review.md §4 | 관측 2026-09-03(세션 도구 정의) | Agent 스폰은 세션 effort 상속으로 동작. 규칙은 Workflow 한정 |
| 9 | `AskUserQuestion` 문항 상한 4 | references/interview.md | 문서(도구 스키마) | - |
| 10 | 서브 `model` 별칭 `'opus'`, `'sonnet'` 유효(`'fable'` 은 model-routing.md 에 있으나 스폰 별칭 해석 미확인 - 서브로 쓰지 않는다) | model-routing.md | 관측 2026-09-02 | model-routing 트리거 ③ |
| 11 | `claude -p` 플래그 `--tools "A,B"`, `--disallowedTools`, `--strict-mcp-config`, `--add-dir`, `--max-turns`, `--effort`, `--name` | scripts/curator-daemon.sh | 문서 cli-reference + `claude -p --help` 2026-09-03 | 데몬 로그에 플래그 오류 → done `failed` |
| 12 | 헤드리스 `claude -p` 안에서 `Agent` 로 띄운 하위 서브가 상위의 권한, 도구 제한을 물려받는지 | 사용 안 함 - curator 는 하위 서브를 쓰지 않는다(사용자 결정 2026-09-03) | 미문서. 관측 2026-09-03: acceptEdits 상위에서 서브의 Write/Edit/Bash 전부 거부 | 해당 없음 |
| 13 | `claude -p --output-format json` 의 결과 JSON 에 `result`, `is_error`, `subtype`, `num_turns`, `permission_denials[]`(tool_name, tool_input) | scripts/curator-daemon.sh(사람용 로그 추출, denied 판정) | 문서 headless + 관측 2026-09-03 | JSON 으로 안 읽히면 원문을 로그로 남기고 거부 문구 grep 으로 폴백 |
| 14 | PreToolUse 훅 stdin 의 `tool_input.file_path` 표기 - macOS/Linux 는 절대 POSIX 경로. Windows 는 `C:\...` 또는 `C:/...` 로 추정 | scripts/nb-gate.sh(`nw_key` 로 표기, 대소문자, 끝 슬래시를 지우고 비교) | 관측 2026-08(macOS). Windows 미확인 | 어느 표기든 정규화되므로 무해. 전혀 다른 형태면 절대경로 판정에서 기록 없이 통과(fail-open) |
| 15 | Bash 도구는 Windows 에서 Git Bash(MSYS2)로 실행되고, bash 의 `/c/...`, `/tmp/...` 표기를 Node 기반 파일 도구(Read/Write/Edit)는 드라이브 상대 경로로 오독한다 | scripts/_lib.sh `nw_tool_path`(cygpath -m → `C:/...`), nb-load 출력, 데몬 프롬프트 | 문서(Windows 요구사항 Git for Windows) + MSYS 경로 변환 규칙. 실기 미확인 | 모델이 경로 오류를 내면 nb-load 출력의 표기를 그대로 복사했는지 먼저 본다 |
| 16 | `TaskOutput`(block=true)의 반환 크기가 대상 종류로 갈린다 - `local_workflow` 는 상태,결과 요약만, **`local_agent` 는 `.output` 파일(= 트랜스크립트 JSONL 심볼릭 링크) 내용을 잘라서 통째로** 돌려준다 | **사용 위치 없음** - 스킬 어느 파일에도 `TaskOutput` 언급 0(2026-09-06 대조, `SKILL.md`+`references/`+`scripts/` grep). 옛 좌표 SKILL.md:91 은 현재 Workflow/Agent 선택 규칙 줄 | 관측 2026-09-05(수 KB 의 base64 서명과 tool_use 원문이 메인 컨텍스트로 유입), 도구 설명의 DEPRECATED 경고. 미문서 | **서브 완료는 `TaskOutput` 이 아니라 task-notification 으로 기다린다.** 워크플로(Workflow 도구) 완료 대기에는 `TaskOutput` 이 안전하다 |

## 3. [깨짐] 기록

- 2026-09-03 - §5 실측 기록의 "`Bash` 는 통과" 가 틀렸다. acceptEdits 헤드리스에서 Bash 셸 리다이렉트(`> 파일`)도 `which is a sensitive file` 로 거부(관측: `.curator/logs/20260902T172923Z-eval-session-58298.log:4`). protected path 검사는 파일 편집 도구 한정이 아니다. §5 를 정정했다. 표 #1 의 가정(bypassPermissions 만이 우회 수단)은 그대로 성립 - 이번 bypassPermissions 실행이 실증.

## 4. 미검증 (Windows) - 2026-09-03 07시 개정

Windows 대응은 전부 Git for Windows(MSYS2) 의미론으로 작성했고, macOS 에서 `uname`/`cygpath` 스텁으로 논리만 실측했다. 실기 검증 0회. 어느 항목이든 실기에서 깨지면 `.pending.md` 에 올린다.

- **경로 표기** - 모델과 도구에 보이는 경로는 `scripts/_lib.sh` 의 `nw_tool_path`(`cygpath -m` → `C:/Users/...` 혼합 표기)로 통일했다. 역슬래시 표기(`cygpath -w`)는 bash 인용과 JS/JSON 문자열에서 깨지므로 쓰지 않는다. 비교는 `nw_key`(표기, 대소문자, 끝 슬래시 정규화)로 한다. registry 행은 `C:/...`, `C:\...`, `/c/...` 어느 표기든 매칭된다.
- **데몬 분리** - `nw_detach` 가 python `subprocess.Popen` 으로 띄운다(POSIX 는 `start_new_session`, Windows 는 `DETACHED_PROCESS|CREATE_NEW_PROCESS_GROUP`, stdin 은 /dev/null, cwd 는 스킬 폴더). Windows 에서 이 자식이 Bash 도구 종료 뒤에도 살아남는지, `kill -0`/`ps -p` 가 다른 Git Bash 프로세스의 MSYS pid 를 보는지 미확인. 죽어도 큐는 남고 다음 enqueue 가 다시 띄운다.
- **python 탐색** - `python3`, `python`, `py -3` 순으로 실제 실행해 고른다(Microsoft Store 실행 별칭 스텁은 실행 실패로 걸러진다). `PYTHONUTF8=1` 을 모든 호출에 건다.
- **산출물 열기** - PATH 의 `code`/`cursor`/`windsurf` CLI, 없으면 `cmd //c start`(확장자 기본 앱). `//c` 는 MSYS 경로 변환을 피한 `/c` 스위치다.
- **훅 file_path 표기**(표 #14), `~/.claude` protected path 규칙이 Windows 에서도 같은지, `claude` 가 `.cmd` 셔임으로 PATH 에 잡히는지 - 미확인.
- CRLF: 저장소의 `.gitattributes`(`* text=auto eol=lf`)가 막고, 모드/버전 파일 읽기는 `\r` 과 BOM 을 지운다. 이미 CRLF 로 받은 clone 은 `git ls-files -z | xargs -0 sed -i 's/\r$//'` 로 되돌린다(`reset --hard` 는 로컬 노트북 편집을 지우므로 쓰지 않는다).

## 5. 실측 기록 (macOS - 줄마다 날짜, 버전)

- 헤드리스 `claude -p --permission-mode acceptEdits` 로 `~/.claude` 아래 쓰기: `Edit`/`Write` 거부. **Bash 셸 리다이렉트(`> 파일`)도 같은 문자열 `which is a sensitive file` 로 거부**(관측 2026-09-03, `.curator/logs/20260902T172923Z-eval-session-58298.log:4`). 즉 protected path 검사는 파일 편집 도구 한정이 아니라 쓰기 경로 자체에 걸린다 - 초기 기록의 "`Bash` 는 통과" 는 오류였다(§3).
- 헤드리스 `claude -p --permission-mode bypassPermissions`(`scripts/curator-perm.mode` = `bypassPermissions`) 로 `~/.claude` 아래 쓰기: Bash 리다이렉트, heredoc 쓰기 통과(`Write` 도구는 이번 실행에서 미사용 - 미확인). done 파일과 노트북 본문 기록 정상(스모크 2026-09-03, id `20260902T174528Z-smoke-bypass-63799`). 표 #1 의 "건너뛰는 유일한 수단은 bypassPermissions" 가 양방향으로 실증됐다.
- 데몬 실제 실행(harness-refresh 1건): 큐 투입, 잠금, 항목 이동, opus 실행, 종료까지 정상. 쓰기 단계에서 거부돼 done 파일과 `.pending.md` 를 남기지 못했다. **`scripts/curator-perm.mode` 가 없으면 데몬은 판정만 하고 기록을 못 한다.**
- 그 실행에서 데몬의 거부 판정이 `failed` 로 잘못 찍혔다 - 모델이 "쓰기 권한 문제" 로 요약해 `requested permissions` 문자열이 로그에 없었다. 판정 패턴을 두 갈래(하네스 메시지와 모델 서술)로 넓혔다.

- 2026-09-03 07시 - 데몬 개정 실측(macOS, claude 스텁): `--output-format json` 판독과 denied 판정, 즉시 실패 시 데몬 중단(큐 보존), 벽시계 상한 초과 시 자식 kill 후 timeout, `ctl kill` 시 자식 종료 + 항목 failed 마감, 크래시 뒤 processing 항목 1회 재시도. 헤드리스 bypassPermissions 에서 `Write` 도구로 `~/.claude` 아래 파일 생성 통과(sonnet 프로브).

- 2026-09-04 - 2.1.259 대조(관측 행 #2,4,5,6,7,8,10,12,14). 사용 위치 전부 잔존: `CLAUDE_CODE_SESSION_ID`,`CLAUDE_EFFORT`,`AI_AGENT` 이 실행에서 값 확인(#2), `nb-gate.sh:29,34,41` file_path 판독(#14), `wf-summarize.py:24-25,35` journal 형식 소비(#6), `review.md:89,123-125,130` 함정 1,4,7(#4,5,7), `SKILL.md:34,89` 별칭,effort(#8,10), curator 하위 서브 미사용(#12). 데몬이 `--tools`,`--disallowedTools`,`--strict-mcp-config`,`--add-dir`,`--max-turns`,`--effort`,`--name`,`--output-format json` 으로 이 실행을 띄운 것이 #11,#13 실증, bypassPermissions 쓰기 통과가 #1 실증. 깨진 행 0.

- 2026-09-05 - Workflow journal 의 result 레코드 키 목록이 `type`,`key`,`agentId`,`result` 뿐이었다(#6 근거). 라벨이 없으므로 `wf-summarize.py` 가 서브를 이름으로 못 가른다 - 본문 키워드로 가른다. 같은 실행에서 완료 알림의 `result` 는 스크립트가 6000자로 슬라이스했는데도 합계 24KB 에서 잘렸다(#4 근거) - **보고는 알림이 아니라 journal 에서 다시 뽑는다.**

- 2026-09-05 - `TaskOutput(block=true)` 을 `local_agent` 서브에 걸었더니 결과로 그 서브의 트랜스크립트 JSONL 이 잘린 채 통째로 왔다(표 #16 근거). 같은 호출을 `local_workflow` 에 걸면 요약만 온다. 컨텍스트 경제 관점에서 **서브 완료 대기는 task-notification 이 유일한 안전 경로다.**

- 2026-09-06 - 2.1.263 대조(관측 행 #2,4,5,6,7,8,10,12,14,16). 깨진 행 0. 사용 위치 잔존: `AI_AGENT`=`claude-code_2-1-263_agent`,`CLAUDE_CODE_SESSION_ID`,`CLAUDE_EFFORT`=`medium` 이 실행 env 에서 값 확인(#2), `nb-load.sh:59,82,111-120` sid 마커,버전 비교(#2), `nb-gate.sh:29-35,39-41` file_path,session_id 판독(#14), `wf-summarize.py:24-25,32-35` journal `type`,`key`,`result` 소비 + 0건 exit 1(#6), `review.md:89-93,123-125,130` 함정 1,4,7(#5,4,7), `SKILL.md:73` 컨텍스트 경제(#4), `SKILL.md:89` effort(#8), `model-routing.md:27-29,32-33` 별칭(#10), `curator-daemon.sh:120` `--tools` 에 `Agent` 없음(#12). 이 실행 자체가 #1(bypassPermissions 쓰기 통과, `curator-perm.mode`=`bypassPermissions`), #11(`curator-daemon.sh:118-132` 플래그 전량), #13(`:141-155` `permission_denials`,`is_error`,`subtype`,`num_turns` 판독)의 실증.
- 2026-09-06 - **버전 소스 불일치**: 요청 payload 의 `current` 는 `claude-code_2-1-261_agent`(nb-load 가 세션 Bash env 에서 읽은 값), 같은 날 curator 프로세스 env `AI_AGENT` 실측은 `claude-code_2-1-263_agent`, `claude --version` 도 `2.1.263`. 앞선 같은 날 요청은 263 을 보고했다 → 한 머신에 병행 설치 또는 세션별 버전 고정. 결과: 트리거 ① 이 실제 갱신 없이 발화하고 큐가 빈 harness-refresh 를 돌린다. 대조 판정은 **데몬이 띄운 이 프로세스의 실측 env** 로 한다(payload 값은 참고). 깨진 행 0 - 관측 행 전량(#2,4,5,6,7,8,10,12,14,16) 사용 위치 잔존 재확인: `nb-load.sh:59,82,111-120`, `nb-gate.sh:29-41`, `wf-summarize.py:24-25,32-35`, `review.md:89-93,123-125,130`, `SKILL.md:73,89`, `model-routing.md:27-29,32-33`, `curator-daemon.sh:118-132,141-155`(`--tools` 에 `Agent` 없음), `TaskOutput` grep 0건.

- 2026-09-06 (3회차) - 관측 행 전량(#2,4,5,6,7,8,10,12,14,16) 재대조. 깨진 행 0. 이 프로세스 env 실측 `AI_AGENT`=`claude-code_2-1-263_agent`, `CLAUDE_CODE_SESSION_ID`=`6c1aebd0-...`, `CLAUDE_EFFORT`=`medium`, `claude --version`=`2.1.263`, `curator-perm.mode`=`bypassPermissions`(#2,#1). payload 보고값은 261 - 불일치 3회째, 아래 버전 소스 불일치 항 그대로 성립. 사용 위치 잔존: `nb-load.sh:54,59-60,82,111-113`(#2), `nb-gate.sh:5,29-30,34`(#14), `wf-summarize.py:24-25,31-36` journal `type`,`key`,`result` 소비 + 0건 `sys.exit(1)`(#6), `review.md:89,92,123,130` 함정 1,4,7(#5,4,7), `SKILL.md:66,86,89` 컨텍스트 경제,effort(#4,#8), `SKILL.md:34`,`model-routing.md:27-29,32-34` 별칭(#10), `curator-daemon.sh:118-132` 플래그 전량 + `:120 --tools` 에 `Agent` 없음(#11,#12), `:141,153-155` `permission_denials`,`is_error`,`subtype`,`num_turns`(#13), `interview.md:15` 4문항 상한(#9), `TaskOutput` grep 0건(#16 - 소비처 없음, 아래 항 그대로).

- 2026-09-06 - **#16 은 가정은 살아 있으나 스킬에 소비처가 없다.** `TaskOutput` 문자열이 스킬 어느 파일에도 없어(`SKILL.md`,`references/`,`scripts/` grep 0건) "서브 완료는 task-notification 으로 기다린다" 는 규칙이 문서로 안 적혀 있다. 하네스가 깨진 것이 아니라 스킬 쪽 결손이라 §3 이 아니라 `.pending.md` 로 올렸다. 표의 가정 문구는 그대로 둔다.

verified: 2026-09-06 (Claude Code 2.1.263, 이 환경의 실측 + 공식 문서)

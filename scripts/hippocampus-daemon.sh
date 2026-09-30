#!/bin/bash
# brain hippocampus 데몬 - 세션과 독립된 프로세스. 큐를 순서대로 비운다.
# 단일 실행: lock/ 디렉터리(mkdir 원자성) + pid. 항목마다 새 `claude -p` 1회(컨텍스트 새로, 폭주 방지).
# 중지: hippocampus-ctl.sh stop (항목 경계에서 종료). 모델,effort 는 /claude-brain-config(.active/config, 기본 Sonnet 5.5 medium). 턴, 벽시계 상한은 모드별(루프 안 case).
set -u
SKILL="$(cd "$(dirname "$(printf '%s' "$0" | tr '\\' '/')")/.." && pwd)"
SKILL_DIR="$SKILL"
. "$SKILL/scripts/_lib.sh"
cd "$SKILL" 2>/dev/null || cd /   # 호출 세션의 cwd 가 지워진 폴더면 매 명령마다 getcwd 오류가 난다. 절대경로만 쓰므로 스킬 폴더로 옮긴다.
NB="$SKILL/cortex"; C="$NB/.hippocampus"
nw_need_python
# 호출 세션이 심은 하네스 변수는 물려주지 않는다 - 자식 claude 가 부모 세션의 하위 세션으로 묶이거나 세션 id 와 effort 가 섞인다.
# 인증, 프로바이더 설정(CLAUDE_CODE_USE_*, CLAUDE_CODE_OAUTH_TOKEN, CLAUDE_CONFIG_DIR 등)은 남긴다.
unset CLAUDECODE CLAUDE_CODE_SESSION_ID CLAUDE_CODE_CHILD_SESSION CLAUDE_CODE_MESSAGING_SOCKET CLAUDE_CODE_MESSAGING_TOKEN CLAUDE_PID CLAUDE_EFFORT CLAUDE_CODE_ENTRYPOINT 2>/dev/null
# 권한 모드는 scripts/hippocampus-perm.mode 파일(한 단어)이 정한다. 근거와 배포 기본값은 cortex/common/harness-routing.md #1 과 README.
# 파일이 없거나 값이 깨져 있으면(BOM, UTF-16 등) acceptEdits - 그 경우 `~/.claude` 아래 노트북 쓰기는 하네스가 거부하고 done 파일이 denied 로 남는다.
PERM_MODE="$(cat "$SKILL/scripts/hippocampus-perm.mode" 2>/dev/null | nw_strip)"
case "$PERM_MODE" in ""|*[!A-Za-z]*) PERM_MODE="acceptEdits" ;; esac
IDLE_ROUNDS=2; IDLE_SLEEP="${N_WORKER_IDLE_SLEEP:-30}"
ITEM_MAX_SEC="${N_WORKER_ITEM_MAX_SEC:-}"   # 항목당 벽시계 상한(초) 강제값. 비우면 모드별 기본(루프 안 case). 넘으면 자식 claude 를 죽이고 timeout 으로 기록한다 - 멈춘 자식이 잠금을 영영 쥐지 않게.
FAST_FAIL_SEC="${N_WORKER_FAST_FAIL_SEC:-20}"  # 이보다 빨리 비정상 종료하면 CLI/플래그/로그인 문제다 - 큐 전체를 초 단위로 태우지 않고 데몬을 멈춘다.
POLL_SEC="${N_WORKER_POLL_SEC:-15}"
# 해마 모델,effort - /claude-brain-config 가 .active/config 에 남긴 값(기본 Sonnet 5.5, medium - 2026-09-30 실측 high 대비 턴 절반, 품질 차이 없음). 환경변수 HIPPOCAMPUS_MODEL, HIPPOCAMPUS_EFFORT 가 있으면 그것이 먼저다.
# effort 가 auto 면 모드별 기본(아래 case)을 쓴다.
cfgv() { sed -n "s/^$1=//p" "$SKILL/.active/config" 2>/dev/null | tail -1; }
MODEL="${HIPPOCAMPUS_MODEL:-$(cfgv hippocampus_model)}"; MODEL="${MODEL:-claude-sonnet-5-5}"
EFFORT_FORCE="${HIPPOCAMPUS_EFFORT:-$(cfgv hippocampus_effort)}"; EFFORT_FORCE="${EFFORT_FORCE:-medium}"; [ "$EFFORT_FORCE" = auto ] && EFFORT_FORCE=""
mkdir -p "$C/queue" "$C/processing" "$C/done" "$C/logs"

# 경로는 모델과 도구가 읽는 표기(nw_tool_path)로 넘긴다. macOS/Linux 는 그대로, Windows 는 C:/... 표기.
skill_n="$(nw_tool_path "$SKILL")"; nb_n="$(nw_tool_path "$NB")"; cur_n="$(nw_tool_path "$SKILL/agents/hippocampus.md")"
CFG="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"; CFG="${CFG%/}"; [ -d "$CFG" ] && CFG="$(cd "$CFG" && pwd)"   # 끝 슬래시,상대경로 정리 - 규칙이 문자열로 맞아야 한다
cfg_n="$(nw_tool_path "$CFG")"   # 설정 폴더 - 거부 규칙이 이 경로의 설정,훅을 지킨다
skills_n="$(dirname "$skill_n")"   # brain 이 든 skills 폴더 - 모든 스킬의 본문(SKILL.md, scripts, references, agents)을 지킨다. cortex 는 brain/cortex 라 걸리지 않는다

# 잠금. 죽은 잠금은 rm 이 아니라 mv 로 치운다 - 두 데몬이 동시에 죽은 잠금을 발견해도 mv 는 하나만 성공한다.
acquire() {
  local pid
  if mkdir "$C/lock" 2>/dev/null; then echo $$ > "$C/lock/pid"; return 0; fi
  pid="$(cat "$C/lock/pid" 2>/dev/null)"
  if [ -z "$pid" ]; then
    # pid 파일이 아직 없다 - 방금 잠금을 잡은 데몬이 pid 를 쓰는 중이거나 죽은 잔재다. 30초 안이면 살아 있다고 본다.
    [ $(( $(date +%s) - $(nw_mtime "$C/lock") )) -lt 30 ] && return 1
  elif nw_pid_is "$pid" hippocampus-daemon; then
    return 1
  fi
  mv "$C/lock" "$C/lock.dead.$$" 2>/dev/null || return 1
  rm -rf "$C/lock.dead.$$"
  mkdir "$C/lock" 2>/dev/null || return 1
  echo $$ > "$C/lock/pid"; return 0
}
acquire || { echo "이미 실행 중 (pid $(cat "$C/lock/pid" 2>/dev/null))"; exit 0; }
date -u +%Y-%m-%dT%H:%M:%SZ > "$C/lock/started"; rm -f "$C/stop"
cleanup() { [ -f "$C/lock/child" ] && kill "$(cat "$C/lock/child" 2>/dev/null)" 2>/dev/null; rm -rf "$C/lock"; }
trap cleanup EXIT
trap 'exit 143' TERM INT
# 크래시 회수 - 이전 데몬이 처리 중 죽어 processing/ 에 남은 항목은 큐로 되돌린다(id 앞의 시각으로 순서가 유지된다).
# 재시도는 1회뿐이다(요청 JSON 에 retried 표시) - 같은 항목이 매번 데몬을 죽이면 두 번째는 failed 로 마감한다.
for f in "$C"/processing/*.json; do
  [ -f "$f" ] || continue
  rid="$(basename "$f" .json)"
  if nw_py - "$f" <<'PY'
import json, sys
p = sys.argv[1]; d = json.load(open(p, encoding='utf-8'))
if d.get("retried"): sys.exit(1)
d["retried"] = True; json.dump(d, open(p, "w", encoding='utf-8'), ensure_ascii=False, indent=1)
PY
  then mv "$f" "$C/queue/" && echo "회수: $rid (이전 데몬이 처리 중 종료 - 1회 재시도)"
  else
    nw_py - "$C/done/$rid.json" "$rid" <<'PY'
import json, sys, datetime
json.dump({"id": sys.argv[2], "status": "failed", "summary": "두 번 연속 처리 중 데몬이 종료됐다 - 재시도하지 않고 마감. 요청은 done/<id>.request.json", "finished_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}, open(sys.argv[1], "w", encoding='utf-8'), ensure_ascii=False, indent=1)
PY
    mv "$f" "$C/done/$rid.request.json"; echo "마감: $rid (재시도 후에도 처리 중 종료 - failed)"
  fi
done

write_fallback_done() {   # $1 status  $2 rc  - hippocampus 가 done 파일을 못 남겼을 때 데몬이 대신 쓴다
  nw_py - "$done_file" "$id" "$2" "$log" "$1" <<'PY'
import json, sys, datetime, os
p, id_, rc, log, status = sys.argv[1:6]
tail = open(log, encoding='utf-8', errors='replace').read()[-1500:] if os.path.exists(log) else ''
json.dump({"id": id_, "status": status,
           "summary": f"hippocampus 실행이 결과 파일을 남기지 않았다 (exit {rc}, 판정 {status}). 로그 꼬리:\n{tail}",
           "finished_at": datetime.datetime.now(datetime.timezone.utc).isoformat()},
          open(p, "w", encoding='utf-8'), ensure_ascii=False, indent=1)
PY
}

idle=0
while :; do
  if [ -f "$C/stop" ]; then echo "중지 요청 - 종료"; rm -f "$C/stop"; break; fi
  next="$(ls "$C/queue"/*.json 2>/dev/null | head -1)"
  if [ -z "$next" ]; then
    idle=$((idle+1))
    if [ "$idle" -ge "$IDLE_ROUNDS" ]; then
      # 종료 직전 경합 - enqueue 가 "데몬 살아 있음" 을 보고 큐만 쌓았을 수 있다. 잠금을 놓은 뒤 한 번 더 본다.
      trap - EXIT; rm -rf "$C/lock"
      if [ -n "$(ls "$C/queue"/*.json 2>/dev/null | head -1)" ] && mkdir "$C/lock" 2>/dev/null; then
        echo $$ > "$C/lock/pid"; trap cleanup EXIT; idle=0; continue
      fi
      echo "큐 비어 있음 - 종료"; break
    fi
    sleep "$IDLE_SLEEP"; continue
  fi
  idle=0
  id="$(basename "$next" .json)"; req="$C/processing/$id.json"
  mv "$next" "$req" 2>/dev/null || { sleep 1; continue; }
  echo "$id" > "$C/lock/current"; date -u +%Y-%m-%dT%H:%M:%SZ > "$C/lock/heartbeat"
  done_file="$C/done/$id.json"; log="$C/logs/$id.log"; raw="$C/logs/$id.json"
  meta="$(nw_py -c 'import json,sys
d=json.load(open(sys.argv[1],encoding="utf-8")); print(d.get("project_root","")); print(d["mode"]); print((d.get("payload") or {}).get("kind",""))' "$req" 2>/dev/null)"
  root="$(printf '%s\n' "$meta" | sed -n 1p)"; mode="$(printf '%s\n' "$meta" | sed -n 2p)"; kind="$(printf '%s\n' "$meta" | sed -n 3p)"
  rc=0; status=""; t0=$(date +%s); denials="?"
  if [ -z "$mode" ]; then
    rc=2; status="failed"; echo "요청 JSON 을 읽지 못했다 (mode 없음 또는 JSON 오류): $req" > "$log"
  else
    # 모드별 예산. 실측(record 58회: 중앙값 48턴/9분, p90 83턴/15분, 최대 107턴/20분. 갱신류: 최대 16턴/2분)에서 정상 실행을 덮되 폭주를 자른다.
    # record 는 메인의 제안을 옮겨 적는 일이라 medium(hippocampus.md §2). replay 는 대화록 요약에서 기록할 것을 직접 골라내는 판단이 들어가 effort 는 high 이고, 턴과 시간 상한은 record 와 같다(hippocampus.md §2b). 상한에 닿으면 자식을 죽이고 timeout 으로 기록하므로 hippocampus.md 가 항목 단위로 끝내라고 한다.
    effort="high"; max_turns=400; item_max=2400
    case "$mode" in
      register|harness-refresh) effort="medium"; max_turns=120; item_max=900;;
      record) effort="medium"; max_turns=200; item_max=1800;;
      replay) effort="high"; max_turns=200; item_max=1800
              # 깨어 있는 중 재생은 방금 구간 하나라 가볍게 - 세션과 같은 시간대에 도므로 사용량도 아낀다
              [ "$kind" = "awake" ] && { effort="medium"; max_turns=120; item_max=1200; };;
    esac
    [ -n "$ITEM_MAX_SEC" ] && item_max="$ITEM_MAX_SEC"
    [ -n "$EFFORT_FORCE" ] && effort="$EFFORT_FORCE"
    req_n="$(nw_tool_path "$req")"; done_n="$(nw_tool_path "$done_file")"; root_n="$(nw_tool_path "$root")"
    # 지침은 이번 모드에 필요한 절만 시스템 프롬프트에 붙인다 - 파일로 읽히면 그 도구 결과가 매 턴 다시 읽히고, 안 쓰는 절도 함께 실린다
    brief="$(nw_py "$SKILL/scripts/hippocampus-brief.py" "$SKILL/agents/hippocampus.md" "$mode" 2>/dev/null)"
    [ -n "$brief" ] || brief="$(cat "$SKILL/agents/hippocampus.md")"
    prompt="너는 brain 의 hippocampus(해마)다. 지침은 시스템 프롬프트 끝의 hippocampus 지침이다(원본 $cur_n 에서 이번 모드에 필요한 절만 실었다 - 원본을 다시 읽지 않는다. 빠진 절이 꼭 필요하면 원본에서 그 절만 sed -n 으로 본다). 특히 '큐 실행 형태' 절대로 행동하라. 오늘 날짜: $(date +%F). brain 경로: $skill_n. 기억 저장소(cortex) 경로: $nb_n. 요청 파일: $req_n (mode=$mode, 이 JSON 의 payload 가 네 입력이다). 끝나면 결과 JSON 을 $done_n 에 써라(형식은 hippocampus.md '돌려줄 것' 의 큐 형식). 하위 서브에이전트는 쓰지 않는다 - 전부 직접 한다. 노트북($nb_n) 밖은 수정하지 않는다. 프로젝트 루트($root_n)는 읽기만 한다. git 으로 커밋, 푸시, 체크아웃, 리셋을 하지 않는다. 경로는 받은 표기 그대로 쓴다. 말하지 마라 - 서술,진행 보고,요약 출력 없이 도구 호출만 하고, 마지막 출력은 'done: $done_n' 한 줄이다."
    # 프로젝트 루트가 없으면(옮겨짐, 삭제) --add-dir 을 빼고 띄운다 - 있지 않은 폴더를 주면 claude 가 시작 전에 종료한다.
    ADD_DIR=""; [ -n "$root" ] && [ -d "$root" ] && ADD_DIR="$root_n"
    # 거부 규칙은 bypassPermissions 에서도 유효하다(문서). git 쓰기, 삭제, 하네스 설정과 모든 스킬 본문(n-worker 등 이웃 스킬 포함) 편집을 막는다.
    # `git -C <루트> ...` 형태(hippocampus.md 가 지시)와 `/bin/rm`, `find -delete` 도 막는다.
    (cd "$NB" && exec claude -p "$prompt" \
      --name "hippocampus-$id" --model "$MODEL" --effort "$effort" \
      --permission-mode "$PERM_MODE" \
      --tools "Read,Edit,Write,Grep,Glob,Bash,WebFetch,WebSearch" \
      --disable-slash-commands --append-system-prompt "$brief" \
      --allowedTools "Read" "Edit" "Write" "Grep" "Glob" "Bash(python3 *)" "Bash(python *)" "Bash(py *)" "Bash(ls *)" "Bash(wc *)" "Bash(cat *)" "Bash(sed *)" "Bash(mv *)" "Bash(cp *)" "Bash(mkdir *)" "Bash(date *)" "Bash(git -C * log*)" "Bash(git -C * show*)" "Bash(git -C * rev-parse*)" "Bash(git -C * diff*)" \
      --disallowedTools \
        "Bash(git push*)" "Bash(git commit*)" "Bash(git reset*)" "Bash(git checkout*)" "Bash(git switch*)" "Bash(git stash*)" "Bash(git rebase*)" "Bash(git merge*)" "Bash(git restore*)" "Bash(git clean*)" "Bash(git rm*)" "Bash(git mv*)" "Bash(git add*)" \
        "Bash(git -C * push*)" "Bash(git -C * commit*)" "Bash(git -C * reset*)" "Bash(git -C * checkout*)" "Bash(git -C * switch*)" "Bash(git -C * stash*)" "Bash(git -C * rebase*)" "Bash(git -C * merge*)" "Bash(git -C * restore*)" "Bash(git -C * clean*)" "Bash(git -C * rm*)" "Bash(git -C * mv*)" "Bash(git -C * add*)" \
        "Bash(rm *)" "Bash(/bin/rm *)" "Bash(sudo *)" "Bash(find * -delete*)" "Bash(xargs rm*)" \
        "Edit(//${cfg_n#/}/settings.json)" "Write(//${cfg_n#/}/settings.json)" "Edit(//${cfg_n#/}/settings.local.json)" "Write(//${cfg_n#/}/settings.local.json)" \
        "Edit(//${cfg_n#/}/hooks/**)" "Write(//${cfg_n#/}/hooks/**)" "Edit(//${cfg_n#/}/CLAUDE.md)" "Write(//${cfg_n#/}/CLAUDE.md)" \
        "Edit(//${skills_n#/}/*/SKILL.md)" "Write(//${skills_n#/}/*/SKILL.md)" "Edit(//${skills_n#/}/*/scripts/**)" "Write(//${skills_n#/}/*/scripts/**)" \
        "Edit(//${skills_n#/}/*/references/**)" "Write(//${skills_n#/}/*/references/**)" "Edit(//${skills_n#/}/*/agents/**)" "Write(//${skills_n#/}/*/agents/**)" \
      --strict-mcp-config \
      ${ADD_DIR:+--add-dir "$ADD_DIR"} \
      --output-format json --max-turns "$max_turns" </dev/null >"$raw" 2>"$log.err") &
    cpid=$!; echo "$cpid" > "$C/lock/child"
    while kill -0 "$cpid" 2>/dev/null; do
      sleep "$POLL_SEC"; date -u +%Y-%m-%dT%H:%M:%SZ > "$C/lock/heartbeat"
      if [ -z "$status" ] && [ $(( $(date +%s) - t0 )) -gt "$item_max" ]; then
        status="timeout"; kill "$cpid" 2>/dev/null; sleep 3; kill -9 "$cpid" 2>/dev/null
      fi
    done
    wait "$cpid"; rc=$?; rm -f "$C/lock/child"
    # `--output-format json` 의 결과에서 사람이 읽을 본문($log)과 권한 거부 건수를 뽑는다. JSON 이 아니면(형식 변경) 원문을 그대로 로그로.
    denials="$(nw_py - "$raw" "$log" <<'PY'
import json, os, sys
raw, log = sys.argv[1], sys.argv[2]
txt = open(raw, encoding='utf-8', errors='replace').read() if os.path.exists(raw) else ''
err = open(log + '.err', encoding='utf-8', errors='replace').read() if os.path.exists(log + '.err') else ''
try:
    d = json.loads(txt)
except Exception:
    d = None
if isinstance(d, dict):
    out = str(d.get('result', ''))
    den = d.get('permission_denials') or []
    if d.get('is_error') or d.get('subtype') not in (None, 'success'):
        out += f"\n[하네스: is_error={d.get('is_error')} subtype={d.get('subtype')} turns={d.get('num_turns')}]"
    for x in den:
        out += f"\n[권한 거부] {x.get('tool_name')} {json.dumps(x.get('tool_input', {}), ensure_ascii=False)[:200]}"
    if err.strip():
        out += "\n[stderr]\n" + err[-1500:]
    open(log, 'w', encoding='utf-8').write(out + "\n")
    print(len(den))
else:
    open(log, 'w', encoding='utf-8').write(txt + ("\n[stderr]\n" + err[-1500:] if err.strip() else ''))
    print('?')
PY
)"
    rm -f "$log.err"
  fi
  # 사용 한도, 로그인, 네트워크,일시 장애로 멈춘 항목은 실패가 아니다 - 요청을 큐 제자리로 되돌리고 데몬만 멈춘다(다음 투입이나 밤 잠이 다시 띄운다).
  # 실패로 마감하면 그 대화 구간은 다시 재생되지 않는다(재생 위치는 요청 때 이미 넘어갔다). 30번 넘게 보류되면 실패로 마감한다.
  if [ ! -f "$done_file" ] && [ -n "$mode" ] && [ "$status" != "timeout" ] && \
     grep -qiE "hit your .*limit|usage limit|rate.?limit|overloaded|not logged in|please run /login|invalid api key|API Error: 5[0-9][0-9]|connection error|request timed out|ECONNRESET|ETIMEDOUT|ENOTFOUND|fetch failed|network error|socket hang up" "$log" 2>/dev/null; then
    nd="$(nw_py - "$req" <<'PY'
import json, sys
p = sys.argv[1]; d = json.load(open(p, encoding='utf-8'))
d['deferrals'] = d.get('deferrals', 0) + 1
json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(d['deferrals'])
PY
)"
    if [ "${nd:-99}" -le 30 ] 2>/dev/null; then
      mv "$req" "$C/queue/"; rm -f "$C/lock/current"
      echo "보류: $id - 사용 한도,로그인,일시 장애로 멈췄다(${nd}번째). 큐로 되돌리고 데몬을 멈춘다. 로그: $log"
      break
    fi
  fi
  if [ ! -f "$done_file" ]; then
    [ -n "$status" ] || status="failed"
    if [ "$denials" = "?" ]; then
      # JSON 판독 실패 - 하네스 메시지와 모델 서술 두 갈래로 거부 문구를 찾는다(구형 판정).
      grep -qiE "requested permissions|sensitive file|permission denied|쓰기 권한|권한 거부|권한 문제" "$log" 2>/dev/null && status="denied"
    elif [ "$denials" != "0" ] && [ "$status" = "failed" ]; then
      status="denied"
    fi
    write_fallback_done "$status" "$rc"
    # 재생 항목이 끝내지 못한 구간은 다음 재생이 다시 가져가게 위치를 되돌린다(같은 대화록 3번까지)
    [ "$mode" = "replay" ] && nw_py "$SKILL/scripts/replay.py" rollback "$req" 2>/dev/null
    if [ "$rc" != 0 ] && [ "$status" != "timeout" ] && [ $(( $(date +%s) - t0 )) -lt "$FAST_FAIL_SEC" ]; then
      mv "$req" "$C/done/$id.request.json"; rm -f "$C/lock/current"
      echo "중단: claude 가 ${rc} 로 즉시 종료 - CLI, 플래그, 로그인 문제일 가능성. 항목 $id 는 failed. 남은 큐는 다음 enqueue 가 다시 띄운다. 로그: $log"
      break
    fi
  fi
  mv "$req" "$C/done/$id.request.json"; rm -f "$C/lock/current"
  echo "완료 $id (exit $rc, $(( $(date +%s) - t0 ))초)"
done

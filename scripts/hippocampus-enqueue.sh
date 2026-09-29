#!/bin/bash
# brain hippocampus 큐 투입. 어느 세션이든 이 한 줄로 hippocampus 에 일을 맡긴다.
# 사용법: hippocampus-enqueue.sh <요청 JSON 경로> [--wait <초>]
#   요청 JSON 필수 키(최상위): mode(register|record|targeted|sweep|replay|harness-refresh), project_root, slug, stack,
#                     caller(호출 세션 이름), payload(모드별 입력 - record 면 proposals[], scripts[] 등, replay 면 digest, session, transcript,
#                     sweep 이면 slice{id, files, tok})
#   --wait 를 주면 done 파일이 생길 때까지 폴링해 요약을 출력한다(register 처럼 결과가 즉시 필요한 모드용).
#   주의: Bash 도구의 기본 timeout 은 120초다. --wait 600 을 쓰려면 도구 호출의 timeout 인자를 그보다 크게 준다.
# 동작: queue/ 에 <ISO시각>-<caller>-<pid>.json 으로 넣고, 살아 있는 데몬이 없으면 hippocampus-daemon.sh 를 세션과 무관한 프로세스로 띄운다.
#       살아 있으면 큐만 쌓고 반환한다 - 데몬은 큐를 순서대로 비운다(단일 실행, 단일 쓰기 주체).
set -u
SKILL="$(cd "$(dirname "$(printf '%s' "$0" | tr '\\' '/')")/.." && pwd)"
SKILL_DIR="$SKILL"
. "$SKILL/scripts/_lib.sh"
C="$SKILL/cortex/.hippocampus"
nw_need_python
REQ="${1:-}"; WAIT=0
[ -n "$REQ" ] && [ -f "$REQ" ] || { echo "오류: 요청 JSON 경로가 필요하다"; exit 2; }
if [ "${2:-}" = "--wait" ]; then WAIT="${3:-600}"; fi
mkdir -p "$C/queue" "$C/processing" "$C/done" "$C/logs"
nw_py - "$REQ" <<'PY' || exit 2
import json, sys
d = json.load(open(sys.argv[1], encoding='utf-8'))
for k in ("mode", "project_root", "slug", "caller", "payload"):
    if k not in d: print(f"오류: 요청 JSON 최상위에 '{k}' 가 없다"); sys.exit(1)
if d["mode"] not in ("register", "record", "targeted", "sweep", "replay", "harness-refresh"): print("오류: mode 값이 아니다"); sys.exit(1)
PY
TS="$(date -u +%Y%m%dT%H%M%SZ)"
CALLER="$(nw_py -c "import json,sys,re; print(re.sub(r'[^A-Za-z0-9_-]','_',json.load(open(sys.argv[1],encoding='utf-8'))['caller'])[:40])" "$REQ")"
ID="${TS}-${CALLER}-$(printf '%07d' $$)"   # pid 를 자릿수 고정 - 같은 초에 두 건이 들어와도 ls 정렬이 투입 순서와 같다
nw_py - "$REQ" "$C/queue/$ID.json" "$ID" <<'PY'
import json, sys, datetime, os
d = json.load(open(sys.argv[1], encoding='utf-8')); d["id"] = sys.argv[3]; d["enqueued_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
tmp = sys.argv[2] + ".tmp"; json.dump(d, open(tmp, "w", encoding='utf-8'), ensure_ascii=False, indent=1)
os.replace(tmp, sys.argv[2])
PY
# 출력은 할 일(투입, 데몬 기동)을 다 끝낸 뒤에 한다. 호출자가 `| head -1` 로 첫 줄만 읽으면 둘째 줄의 echo 에서 SIGPIPE 로 끝나는데,
# 그 전에 데몬이 떠 있어야 한다. (SIGPIPE 를 무시하면 실패한 echo 의 버퍼가 뒤 $(...) 결과에 섞여 경로가 오염된다 - 실측)
NOTE=""; MSG=""
# 이 기기에서 hippocampus 가 노트북에 쓸 수 있는 상태인지 한 줄로 알린다.
# 노트북이 `~/.claude/` 아래면 하네스가 그 경로를 protected path 로 취급해 헤드리스 데몬의 파일 편집이 거부된다
# (cortex/common/harness-routing.md #1). 그 경우 데몬은 판정만 하고 기록을 못 하므로, 기기마다 한 번 설정이 필요하다.
PERM_FILE="$SKILL/scripts/hippocampus-perm.mode"
PERM_NOW="$(cat "$PERM_FILE" 2>/dev/null | nw_strip)"
if nw_under "$(nw_key "${CLAUDE_CONFIG_DIR:-$HOME/.claude}")" "$(nw_key "$SKILL")" && [ "$PERM_NOW" != "bypassPermissions" ]; then
  NOTE="알림: 권한 모드가 ${PERM_NOW:-미설정} 이라 노트북 쓰기가 거부된다(결과는 denied, 판정은 hippocampus-ctl.sh results). 되돌리려면 $(nw_tool_path "$PERM_FILE") 에 bypassPermissions."
fi
# 데몬 생존 확인 - lock/pid 의 프로세스가 살아 있으면 큐만 쌓는다
if nw_pid_is "$(cat "$C/lock/pid" 2>/dev/null)" hippocampus-daemon; then
  MSG="데몬 실행 중 (pid $(cat "$C/lock/pid"), 현재: $(cat "$C/lock/current" 2>/dev/null || echo '-')) - 큐에 쌓아 두었다"
else
  # 세션과 무관한 프로세스로 띄운다(새 세션/프로세스 그룹, stdin 없음, cwd 는 스킬 폴더) - nohup+& 는 도구 셸의 프로세스 그룹에 남는다.
  if dpid="$(nw_detach "$C/logs/daemon.out" bash "$(nw_tool_path "$SKILL/scripts/hippocampus-daemon.sh")")"; then
    MSG="데몬 기동 (pid $dpid) - 로그 $(nw_tool_path "$C/logs/daemon.out")"
  else
    MSG="오류: 데몬을 띄우지 못했다 - 큐에는 남아 있다. 직접: bash $(nw_tool_path "$SKILL/scripts/hippocampus-daemon.sh")"
  fi
fi
echo "큐 투입: $ID"
[ -n "$NOTE" ] && echo "$NOTE"
echo "$MSG"
if [ "$WAIT" -gt 0 ]; then
  i=0
  while [ "$i" -lt "$WAIT" ]; do
    if [ -f "$C/done/$ID.json" ]; then
      # hippocampus 의 Write 는 원자적이지 않다 - 파일이 생긴 직후 반쯤 쓰인 상태일 수 있어 파싱될 때까지 몇 초 더 기다린다.
      j=0
      while [ "$j" -lt 5 ]; do
        nw_py -c "import json,sys; d=json.load(open(sys.argv[1],encoding='utf-8')); print(d.get('status','?')); print(d.get('summary',''))" "$C/done/$ID.json" 2>/dev/null && exit 0
        sleep 1; j=$((j+1))
      done
      echo "오류: done 파일이 JSON 으로 읽히지 않는다: $(nw_tool_path "$C/done/$ID.json")"; exit 4
    fi
    sleep 1; i=$((i+1))
  done
  echo "대기 ${WAIT}초 초과 - 나중에 hippocampus-ctl.sh status 로 확인"; exit 3
fi

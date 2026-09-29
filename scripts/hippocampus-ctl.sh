#!/bin/bash
# brain hippocampus 데몬 제어. 어느 세션에서든 쓴다.
# 사용법: hippocampus-ctl.sh status | stop | kill | results [--ack] | log [id] | sweep [N]
set -u
SKILL="$(cd "$(dirname "$(printf '%s' "$0" | tr '\\' '/')")/.." && pwd)"
SKILL_DIR="$SKILL"
. "$SKILL/scripts/_lib.sh"
C="$SKILL/cortex/.hippocampus"
cmd="${1:-status}"
alive() { nw_pid_is "$(cat "$C/lock/pid" 2>/dev/null)" hippocampus-daemon; }
case "$cmd" in
  status)
    if alive; then echo "데몬: 실행 중 pid $(cat "$C/lock/pid") (시작 $(cat "$C/lock/started" 2>/dev/null), 현재 항목: $(cat "$C/lock/current" 2>/dev/null || echo '대기'), 심장박동 $(cat "$C/lock/heartbeat" 2>/dev/null || echo '-'))"; else echo "데몬: 없음$( [ -d "$C/lock" ] && echo ' (죽은 잠금 - 다음 enqueue 가 넘겨받는다)')"; fi
    echo "큐 대기: $(ls "$C/queue"/*.json 2>/dev/null | wc -l | tr -d ' ')건 / 처리 중: $(ls "$C/processing"/*.json 2>/dev/null | wc -l | tr -d ' ')건 / 완료: $(ls "$C/done"/*.json 2>/dev/null | grep -vc request.json | tr -d ' ')건"
    ls "$C/queue"/*.json 2>/dev/null | xargs -n1 basename 2>/dev/null | sed 's/^/  대기: /'
    if ! alive && [ -n "$(ls "$C/processing"/*.json 2>/dev/null)" ]; then echo "  처리 중 항목은 데몬이 죽어 남은 것 - 다음 enqueue 때 데몬이 큐로 되돌린다"; fi
    ;;
  stop) touch "$C/stop"; echo "중지 요청 - 현재 항목이 끝나면 종료된다";;
  kill)
    if alive; then
      # 자식 claude 도 함께 죽인다 - 데몬만 죽이면 고아 hippocampus 가 잠금 없이 노트북에 계속 쓴다.
      [ -f "$C/lock/child" ] && kill "$(cat "$C/lock/child" 2>/dev/null)" 2>/dev/null
      kill "$(cat "$C/lock/pid")" 2>/dev/null; sleep 1
      [ -f "$C/lock/child" ] && kill -9 "$(cat "$C/lock/child" 2>/dev/null)" 2>/dev/null
      rm -rf "$C/lock"
      # 처리 중이던 항목은 failed 로 마감한다 - 사람이 멈춘 것이라 다음 데몬이 다시 돌리지 않는다. 다시 하려면 요청을 새로 enqueue.
      for f in "$C"/processing/*.json; do
        [ -f "$f" ] || continue; rid="$(basename "$f" .json)"
        nw_py -c 'import json,sys,datetime; json.dump({"id":sys.argv[2],"status":"failed","summary":"hippocampus-ctl.sh kill 로 처리 중 강제 종료 - 요청은 done/<id>.request.json","finished_at":datetime.datetime.now(datetime.timezone.utc).isoformat()},open(sys.argv[1],"w",encoding="utf-8"),ensure_ascii=False,indent=1)' "$C/done/$rid.json" "$rid"
        mv "$f" "$C/done/$rid.request.json"; echo "마감(failed): $rid"
      done
      echo "강제 종료"
    else echo "실행 중인 데몬 없음"; fi
    ;;
  results)
    nw_py - "$C/done" "${2:-}" <<'PY'
import json, sys, glob, os
d, ack = sys.argv[1], sys.argv[2] == "--ack"
for p in sorted(glob.glob(os.path.join(d, "*.json"))):
    if p.endswith(".request.json"): continue
    try: r = json.load(open(p, encoding='utf-8'))
    except Exception as e: print(f"--- {os.path.basename(p)} [읽기 실패: {e}]"); continue
    if r.get("seen") and not ack: continue
    print(f"--- {r.get('id')} [{r.get('status')}] {r.get('finished_at','')}\n{r.get('summary','')}\n")
    if ack and not r.get("seen"):
        r["seen"] = True; json.dump(r, open(p, "w", encoding='utf-8'), ensure_ascii=False, indent=1)
PY
    ;;
  sweep)
    # 가장 오래 정비 안 된 조각 N개(기본 3)를 sweep 요청으로 큐에 넣는다. 조각 하나 = hippocampus 한 번 실행(컨텍스트 안에 들어가는 크기).
    n="${2:-3}"
    tmp="$C/sweep-req"; mkdir -p "$tmp"; rm -f "$tmp"/req-*.json
    nw_py "$SKILL/scripts/slices.py" --nb "$SKILL/cortex" --due "$n" > "$tmp/due.json" || { echo "조각 계산 실패"; exit 1; }
    nw_py "$SKILL/scripts/slices.py" --make-requests "$tmp/due.json" --registry "$SKILL/cortex/registry.md" --out "$tmp" || exit 1
    for r in "$tmp"/req-*.json; do [ -f "$r" ] && bash "$SKILL/scripts/hippocampus-enqueue.sh" "$r" | head -1; done
    ;;
  log) id="${2:-}"; if [ -n "$id" ]; then tail -40 "$C/logs/$id.log"; else tail -20 "$C/logs/daemon.out" 2>/dev/null; fi;;
  *) echo "사용법: hippocampus-ctl.sh status | stop | kill | results [--ack] | log [id] | sweep [N]";;
esac

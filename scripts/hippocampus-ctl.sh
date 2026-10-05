#!/bin/bash
# brain hippocampus 데몬 제어. 어느 세션에서든 쓴다.
# 사용법: hippocampus-ctl.sh status | stop | kill | results [--ack|--brief] | log [id] | sweep [N]
#   results --brief: 상태별 건수, 실패 항목, 최근 5건의 첫 줄만(훅이 /claude-brain-results 로 바로 보여 준다)
set -u
SKILL="$(cd "$(dirname "$(printf '%s' "$0" | tr '\\' '/')")/.." && pwd)"
SKILL_DIR="$SKILL"
. "$SKILL/scripts/_lib.sh"
C="$SKILL/cortex/.hippocampus"
cmd="${1:-status}"
nw_i18n hc
alive() { nw_pid_is "$(cat "$C/lock/pid" 2>/dev/null)" hippocampus-daemon; }
case "$cmd" in
  status)
    if alive; then nw_say hc_alive "$(cat "$C/lock/pid")" "$(cat "$C/lock/started" 2>/dev/null)" "$(cat "$C/lock/current" 2>/dev/null || echo "$M_hc_idle")" "$(cat "$C/lock/heartbeat" 2>/dev/null || echo '-')"
    elif [ -d "$C/lock" ]; then nw_say hc_stale; else nw_say hc_none; fi
    nw_say hc_counts "$(ls "$C/queue"/*.json 2>/dev/null | wc -l | tr -d ' ')" "$(ls "$C/processing"/*.json 2>/dev/null | wc -l | tr -d ' ')" "$(ls "$C/done"/*.json 2>/dev/null | grep -vc request.json | tr -d ' ')"
    for q in "$C/queue"/*.json; do [ -f "$q" ] && nw_say hc_wait_item "$(basename "$q")"; done
    if ! alive && [ -n "$(ls "$C/processing"/*.json 2>/dev/null)" ]; then nw_say hc_orphan; fi
    ;;
  # 쉬고 있을 때 stop 파일을 남기면 다음에 뜬 데몬이 큐를 두고 바로 멈춘다 - 살아 있을 때만 남긴다
  stop) if alive; then touch "$C/stop"; nw_say hc_stop; else nw_say hc_no_daemon; fi;;
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
        nw_py -c 'import json,sys,datetime; json.dump({"id":sys.argv[2],"status":"failed","summary":sys.argv[3],"finished_at":datetime.datetime.now(datetime.timezone.utc).isoformat()},open(sys.argv[1],"w",encoding="utf-8"),ensure_ascii=False,indent=1)' "$C/done/$rid.json" "$rid" "$M_hc_kill_sum"
        mv "$f" "$C/done/$rid.request.json"; nw_say hc_closed "$rid"
      done
      nw_say hc_killed
    else nw_say hc_no_daemon; fi
    ;;
  results)
    nw_py - "$C/done" "${2:-}" "$SKILL/scripts" <<'PY'
import json, sys, glob, os
d, ack = sys.argv[1], sys.argv[2] == "--ack"
sys.path.insert(0, sys.argv[3])
from cli_i18n import m, status_counts
if sys.argv[2] == "--brief":
    import collections
    rows = []
    for p in sorted(glob.glob(os.path.join(d, "*.json"))):
        if p.endswith(".request.json"): continue
        try: r = json.load(open(p, encoding='utf-8'))
        except Exception: continue
        if not isinstance(r, dict): continue
        first = next((l for l in (r.get("summary") or "").splitlines() if l.strip()), "")
        rows.append((r.get("id") or os.path.basename(p), r.get("status") or "?", (r.get("finished_at") or "")[:16], first[:120]))
    if not rows:
        print(m("hc.r_none")); sys.exit(0)
    c = collections.Counter(x[1] for x in rows)
    st = lambda k: m("stat." + k) if k in ("done", "failed", "denied", "timeout", "partial") else k
    print(m("hc.r_total", len(rows), status_counts(c.most_common())))
    bad = [x for x in rows if x[1] in ("failed", "denied", "timeout")]
    if bad:
        print(m("hc.r_bad"))
        for x in bad[-10:]: print("- %s %s [%s] %s" % (x[2], x[0][:60], st(x[1]), x[3]))
    print(m("hc.r_recent"))
    for x in rows[-5:]: print("- %s [%s] %s" % (x[2], st(x[1]), x[3]))
    print(m("hc.r_all", os.path.normpath(os.path.join(os.path.abspath(d), "..", "..", "..", "scripts", "hippocampus-ctl.sh")).replace(os.sep, "/")))
    sys.exit(0)
for p in sorted(glob.glob(os.path.join(d, "*.json"))):
    if p.endswith(".request.json"): continue
    try: r = json.load(open(p, encoding='utf-8'))
    except Exception as e: print(f"--- {os.path.basename(p)} [{m('hc.r_readfail')}: {e}]"); continue
    if not isinstance(r, dict): continue
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
    nw_py "$SKILL/scripts/slices.py" --nb "$SKILL/cortex" --due "$n" > "$tmp/due.json" || { nw_say hc_slice_fail; exit 1; }
    nw_py "$SKILL/scripts/slices.py" --make-requests "$tmp/due.json" --registry "$SKILL/cortex/registry.md" --out "$tmp" || exit 1
    for r in "$tmp"/req-*.json; do [ -f "$r" ] && bash "$SKILL/scripts/hippocampus-enqueue.sh" "$r" | head -1; done
    ;;
  log) id="${2:-}"; if [ -n "$id" ]; then tail -40 "$C/logs/$id.log"; else tail -20 "$C/logs/daemon.out" 2>/dev/null; fi;;
  *) nw_say hc_usage;;
esac

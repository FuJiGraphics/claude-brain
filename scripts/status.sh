#!/bin/bash
# brain 상태 한눈에 - /brain 이 부른다.
set -u
BRAIN="$(cd "$(dirname "$(printf '%s' "$0" | tr '\\' '/')")/.." && pwd)"
SKILL_DIR="$BRAIN"
. "$BRAIN/scripts/_lib.sh"
C="$BRAIN/cortex/.hippocampus"
echo "== 설정"; bash "$BRAIN/scripts/config.sh" show
echo "== 해마"; bash "$BRAIN/scripts/hippocampus-ctl.sh" status
fails="$(grep -l '"status": *"\(failed\|denied\|timeout\)"' "$C"/done/*.json 2>/dev/null | grep -vc request.json | tr -d ' ')"
echo "실패,거부,시간 초과로 끝난 항목: ${fails:-0}건 (hippocampus-ctl.sh results)"
last="$(cat "$C/sleep/last" 2>/dev/null)"
echo "== 잠: 마지막 $( [ -n "$last" ] && date -r "$last" '+%F %T' 2>/dev/null || echo '아직 없음')"
[ -f "$C/sleep/check.txt" ] && head -1 "$C/sleep/check.txt"
today="$(date +%s)"
if [ -f "$BRAIN/.active/recall.log" ]; then
  nw_py - "$BRAIN/.active/recall.log" "$today" <<'PY'
import json, sys, collections
since = int(sys.argv[2]) - 86400
c = collections.Counter(); ch = 0; sess = set()
for l in open(sys.argv[1], encoding='utf-8'):
    try: d = json.loads(l)
    except ValueError: continue
    if d.get('t', 0) < since: continue
    c[d.get('ev')] += 1; ch += d.get('chars', 0); sess.add(d.get('sid'))
print('== 최근 24시간 떠올림: %s, 세션 %d, 주입 %d자' % (', '.join('%s %d' % kv for kv in c.most_common()), len(sess), ch))
PY
fi
[ -f "$C/sleep/notice-harness.txt" ] && echo "== $(cat "$C/sleep/notice-harness.txt") - 도구 동작이 실제로 깨졌을 때만 hippocampus harness-refresh 를 넣는다"

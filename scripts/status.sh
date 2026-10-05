#!/bin/bash
# brain 상태 한눈에 - /claude-brain-status 가 부른다. 글은 brain 언어(scripts/cli_i18n.py)로 나온다.
set -u
BRAIN="$(cd "$(dirname "$(printf '%s' "$0" | tr '\\' '/')")/.." && pwd)"
SKILL_DIR="$BRAIN"
. "$BRAIN/scripts/_lib.sh"
nw_i18n st
C="$BRAIN/cortex/.hippocampus"
nw_say st_h_cfg; bash "$BRAIN/scripts/config.sh" show
mu="$(sed -n 's/^mute=//p' "$BRAIN/.active/config" 2>/dev/null | tail -1)"
[ -n "$mu" ] && nw_say st_muted "$(printf '%s' "$mu" | sed 's/,/, /g')"
nw_say st_h_hippo; bash "$BRAIN/scripts/hippocampus-ctl.sh" status
fails="$(grep -l '"status": *"\(failed\|denied\|timeout\)"' "$C"/done/*.json 2>/dev/null | grep -vc request.json | tr -d ' ')"
nw_say st_fails "${fails:-0}"
last="$(cat "$C/sleep/last" 2>/dev/null)"
when=""; [ -n "$last" ] && when="$(date -r "$last" '+%F %T' 2>/dev/null || date -d "@$last" '+%F %T' 2>/dev/null)"
nw_say st_sleep "${when:-$M_st_never}"
# 기억 검사 첫 줄 '== check <범위> - 파손,인출 불가 N건, 참고 M건' 에서 수만 꺼낸다(check.py 는 해마가 읽는 도구라 한국어로 둔다)
if [ -f "$C/sleep/check.txt" ]; then
  nums="$(head -1 "$C/sleep/check.txt" | sed -n 's/.* \([0-9][0-9]*\)건, [^0-9]* \([0-9][0-9]*\)건.*/\1 \2/p')"
  [ -n "$nums" ] && nw_say st_check ${nums}
fi
if [ -f "$BRAIN/.active/recall.log" ]; then
  nw_py - "$BRAIN/.active/recall.log" "$(date +%s)" "$BRAIN/scripts" <<'PY'
import json, sys, collections
sys.path.insert(0, sys.argv[3])
from cli_i18n import m
since = int(sys.argv[2]) - 86400
c = collections.Counter(); ch = 0; sess = set()
for l in open(sys.argv[1], encoding='utf-8', errors='replace'):
    try: d = json.loads(l)
    except ValueError: continue
    if not isinstance(d, dict) or d.get('t', 0) < since: continue
    c[d.get('ev')] += 1; ch += d.get('chars', 0) or 0; sess.add(d.get('sid'))
print(m('st.recall', ', '.join('%s %d' % kv for kv in c.most_common()), len(sess), ch) if c else m('st.recall_none'))
PY
fi
nw_py "$BRAIN/scripts/usage.py" line
# 새 버전 알림 - 밤 정리(update.py check)가 남긴다: <변경 수>\t<최근 제목>\t<시각>
if [ -f "$BRAIN/.active/update-available" ]; then
  IFS="$(printf '\t')" read -r un us _ < "$BRAIN/.active/update-available"
  [ -n "${un:-}" ] && nw_say st_update "$un" "${us:-}"
fi
# 하네스 버전 알림 - sleep.sh 가 '기록 현재' 두 값을 남긴다
if [ -f "$C/sleep/notice-harness.txt" ]; then
  set -- $(cat "$C/sleep/notice-harness.txt")
  [ $# -eq 2 ] && nw_say st_harness "$1" "$2"
fi
exit 0

#!/bin/bash
# brain 상태줄 - 설치 전에 걸려 있던 상태줄(예: caveman)을 그대로 보여 주고, brain 이 켜져 있으면 뒤에 [BRAIN] 을 붙인다.
# install.sh 가 원래 상태줄 명령을 .active/statusline-prev.cmd 에 남기고 이 스크립트를 상태줄로 건다(해제,되돌리기 때 원래대로).
B="$(cd "$(dirname "$0")/.." && pwd)"
IN="$(cat)"
out=""
P="$B/.active/statusline-prev.cmd"
if [ -f "$P" ] && [ ! -L "$P" ]; then
  cmd="$(cat "$P")"
  [ -n "$cmd" ] && out="$(printf '%s' "$IN" | bash -c "$cmd" 2>/dev/null)"
fi
badge=""
grep -qs '^enabled=0' "$B/.active/config" || badge="$(printf '\033[38;5;30m[BRAIN]\033[0m')"
if [ -n "$out" ] && [ -n "$badge" ]; then printf '%s %s' "$out" "$badge"; else printf '%s%s' "$out" "$badge"; fi

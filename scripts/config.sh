#!/bin/bash
# brain 설정 - 켜기,끄기와 해마(hippocampus) 모델,effort. 값은 <brain>/.active/config 에 한 줄씩 남는다(기기 로컬, 저장소에 안 올라간다).
# 사용법: config.sh [show] | on | off | preset <default|eco|quality> | model <sonnet|opus|haiku> | effort <low|medium|high|xhigh|max|auto> | lang <ko|en|ja|zh>
#   default = Sonnet 5.5, effort medium (2026-09-30 실측: high 대비 턴 절반, 격리 시험 3건 품질 차이 없음)
#   eco     = Sonnet 5.5, effort low    (사용량 최소 - 품질은 재지 않았다)
#   quality = Opus 5.5, effort high
#   off 는 떠올림, 조사 습관 한 줄, 재생 투입, 밤 잠을 멈춘다(기억은 그대로 남는다). 돌고 있는 해마는 지금 항목이 끝나면 선다.
set -u
BRAIN="$(cd "$(dirname "$(printf '%s' "$0" | tr '\\' '/')")/.." && pwd)"
SKILL_DIR="$BRAIN"
. "$BRAIN/scripts/_lib.sh"
F="$BRAIN/.active/config"
mkdir -p "$BRAIN/.active"
get() { sed -n "s/^$1=//p" "$F" 2>/dev/null | tail -1; }
put() {
  local tmp="$F.tmp.$$"
  { grep -v "^$1=" "$F" 2>/dev/null; echo "$1=$2"; } > "$tmp" && mv "$tmp" "$F"
}
model_id() {
  case "$1" in
    sonnet|claude-sonnet-5-5) echo claude-sonnet-5-5 ;;
    opus|claude-opus-5-5) echo claude-opus-5-5 ;;
    haiku|claude-haiku-4-5*) echo claude-haiku-4-5-20251001 ;;
    *) return 1 ;;
  esac
}
name_of() {
  case "$1" in
    claude-sonnet-5-5) echo 'Sonnet 5.5' ;;
    claude-opus-5-5) echo 'Opus 5.5' ;;
    claude-haiku-4-5*) echo 'Haiku 4.5' ;;
    *) echo "$1" ;;
  esac
}
USAGE="[show] | on | off | mute <slug> | unmute <slug> | preset <default|eco|quality> | model <sonnet|opus|haiku> | effort <low|medium|high|xhigh|max|auto> | lang <ko|en|ja|zh>"
nw_i18n cfg
show() {
  local on m e
  on="$(get enabled)"; m="$(get hippocampus_model)"; e="$(get hippocampus_effort)"
  if [ "${on:-1}" = 0 ]; then nw_say cfg_off; else nw_say cfg_on; fi
  nw_say cfg_hippo "$(name_of "${m:-claude-sonnet-5-5}")" "${e:-medium}"
  nw_say cfg_lang "$M_native"
}
stop_daemon() {
  local C="$BRAIN/cortex/.hippocampus"
  if nw_pid_is "$(cat "$C/lock/pid" 2>/dev/null)" hippocampus-daemon; then touch "$C/stop"; nw_say cfg_stop; fi
}
case "${1:-show}" in
  show) show ;;
  on) put enabled 1; show ;;
  off) put enabled 0; stop_daemon; show ;;
  preset)
    case "${2:-}" in
      default) put hippocampus_model claude-sonnet-5-5; put hippocampus_effort medium ;;
      eco) put hippocampus_model claude-sonnet-5-5; put hippocampus_effort low ;;
      quality) put hippocampus_model claude-opus-5-5; put hippocampus_effort high ;;
      *) nw_say cfg_usage "preset <default|eco|quality>"; exit 2 ;;
    esac
    show ;;
  model)
    m="$(model_id "${2:-}")" || { nw_say cfg_usage "model <sonnet|opus|haiku>"; exit 2; }
    put hippocampus_model "$m"; show ;;
  effort)
    case "${2:-}" in
      low|medium|high|xhigh|max) put hippocampus_effort "$2" ;;
      auto) put hippocampus_effort auto ;;
      *) nw_say cfg_usage "effort <low|medium|high|xhigh|max|auto>"; exit 2 ;;
    esac
    show ;;
  mute|unmute)
    # 프로젝트 하나만 쉬기/깨우기 - mute= 에 슬러그를 쉼표로 둔다. 떠올림, 성격, 그 프로젝트 대화의 되짚기가 쉰다(기억은 그대로)
    case "${2:-}" in ''|*[!a-z0-9-]*) nw_say cfg_usage "$1 <slug>"; exit 2 ;; esac
    cur="$(get mute | tr ',' '\n' | grep -v "^$2\$" | grep -v '^$' | tr '\n' ',' | sed 's/,$//')"
    if [ "$1" = mute ]; then cur="${cur:+$cur,}$2"; fi
    put mute "$cur" ;;
  lang)
    # 언어 - 앱 화면, 세션 문구, 성격 문장, 앱의 Haiku 답. 해마는 대화 언어로 기억을 쓰고 모를 때만 이 값을 쓴다
    case "${2:-}" in
      ko|en|ja|zh) put lang "$2" ;;
      *) nw_say cfg_usage "lang <ko|en|ja|zh>"; exit 2 ;;
    esac
    # 설치된 명령어 파일의 설명도 새 언어로 다시 쓴다(설치기가 남긴 위치. 없으면 건너뛴다)
    CD="$(cat "$BRAIN/.active/commands-dir" 2>/dev/null)"
    [ -n "$CD" ] && nw_py "$BRAIN/scripts/cli_i18n.py" commands "$(nw_tool_path "$BRAIN/commands")" "$CD" "$(nw_tool_path "$BRAIN")" refresh >/dev/null 2>&1
    nw_i18n cfg   # 새 언어로 다시 읽는다
    show ;;
  *) nw_say cfg_usage "$USAGE"; exit 2 ;;
esac

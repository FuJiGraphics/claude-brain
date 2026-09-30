#!/bin/bash
# brain 설정 - 켜기,끄기와 해마(hippocampus) 모델,effort. 값은 <brain>/.active/config 에 한 줄씩 남는다(기기 로컬, 저장소에 안 올라간다).
# 사용법: config.sh [show] | on | off | preset <default|eco|quality> | model <sonnet|opus|haiku> | effort <low|medium|high|xhigh|max|auto>
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
show() {
  local on m e
  on="$(get enabled)"; m="$(get hippocampus_model)"; e="$(get hippocampus_effort)"
  if [ "${on:-1}" = 0 ]; then echo "brain: 꺼짐"; else echo "brain: 켜짐"; fi
  echo "해마: $(name_of "${m:-claude-sonnet-5-5}"), effort ${e:-high}"
}
stop_daemon() {
  local C="$BRAIN/cortex/.hippocampus"
  if nw_pid_is "$(cat "$C/lock/pid" 2>/dev/null)" hippocampus-daemon; then touch "$C/stop"; echo "해마: 지금 항목이 끝나면 멈춘다(큐는 남는다)"; fi
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
      *) echo "사용법: config.sh preset <default|eco|quality>"; exit 2 ;;
    esac
    show ;;
  model)
    m="$(model_id "${2:-}")" || { echo "사용법: config.sh model <sonnet|opus|haiku>"; exit 2; }
    put hippocampus_model "$m"; show ;;
  effort)
    case "${2:-}" in
      low|medium|high|xhigh|max) put hippocampus_effort "$2" ;;
      auto) put hippocampus_effort auto ;;
      *) echo "사용법: config.sh effort <low|medium|high|xhigh|max|auto>"; exit 2 ;;
    esac
    show ;;
  *) echo "사용법: config.sh [show] | on | off | preset <default|eco|quality> | model <sonnet|opus|haiku> | effort <low|medium|high|xhigh|max|auto>"; exit 2 ;;
esac

#!/bin/bash
# brain 잠 - 세션이 없는 밤에 기억을 정리한다(사람의 해마가 잠자는 동안 하루를 되짚어 피질로 옮기듯). 세션 비용 0.
# 사용법: sleep.sh [--dry-run]   (launchd 가 매일 04:30 에 부른다 - scripts/brain.sleep.plist. 놓치면 깨어난 뒤 한 번)
# 순서(설정은 scripts/sleep.conf, 없으면 아래 기본값):
#   1. 기억 강도, 검색 실패 짝 집계(sleep-stats.py) -> cortex/.hippocampus/strength.json, sleep/misses.md
#   2. 망각(forget.py): 오래 안 쓴 기억은 자동 떠올림에서 숨기고(잠재화), 다시 쓰인 기억은 되살린다. 데몬이 쉴 때만
#   3. 재생(replay.py scan): 깨어 있는 중 재생이 처리하지 못한 대화록 구간 중 두드러진 것 REPLAY_MAX 개 + 활발한 미등록 프로젝트 등록 1건
#   4. 검색 실패 학습: 실패 짝이 MISS_MIN 개 이상이면 hippocampus targeted 1건(별칭, 단서 반영 판단)
#   5. 조각 정비: 가장 오래 정비 안 된 조각 SWEEP_N 개(slices.py) - 한 조각 = hippocampus 한 번(컨텍스트 안에서 끝나는 크기)
#   6. 검사(check.py) 결과를 sleep/check.txt 에 남긴다
# hippocampus 는 큐를 순서대로 비우는 데몬 하나라 이 스크립트는 투입만 하고 곧 끝난다. 겹쳐 돌지 않게 잠금을 잡는다.
set -u
BRAIN="$(cd "$(dirname "$(printf '%s' "$0" | tr '\\' '/')")/.." && pwd)"
SKILL_DIR="$BRAIN"
. "$BRAIN/scripts/_lib.sh"
nw_need_python
nw_i18n sl
if grep -qs '^enabled=0' "$BRAIN/.active/config"; then nw_say sl_off; exit 0; fi
CX="$BRAIN/cortex"
C="$CX/.hippocampus"
S="$C/sleep"
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
REPLAY_MAX=4; REPLAY_MIN_SCORE=6; SWEEP_N=3; MISS_MIN=5; FIRST_WINDOW_DAYS=2; FORGET_DAYS=45; FORGET_SALIENT_DAYS=120
[ -f "$BRAIN/scripts/sleep.conf" ] && . "$BRAIN/scripts/sleep.conf"
mkdir -p "$S/req" "$C/logs"
LOCK="$S/lock"
if ! mkdir "$LOCK" 2>/dev/null; then
  if [ -n "$(find "$LOCK" -maxdepth 0 -mmin +360 2>/dev/null)" ]; then rm -rf "$LOCK"; mkdir "$LOCK" || exit 0; else nw_say sl_running; exit 0; fi
fi
trap 'rm -rf "$LOCK"' EXIT
nw_say sl_start "$(date '+%F %T')"
rm -f "$S/req"/*.json

# 1. 기억 강도, 검색 실패
nw_py "$BRAIN/scripts/sleep-stats.py" --misses-out "$S/misses.md" | tail -1

# 2. 망각 - 인덱스를 고치므로 hippocampus 가 쉬고 있을 때만
if nw_pid_is "$(cat "$C/lock/pid" 2>/dev/null)" hippocampus-daemon; then
  nw_say sl_forget_skip
elif [ "$DRY" = 1 ]; then
  nw_py "$BRAIN/scripts/forget.py" --days "$FORGET_DAYS" --salient-days "$FORGET_SALIENT_DAYS" --dry-run | tail -1
else
  nw_py "$BRAIN/scripts/forget.py" --days "$FORGET_DAYS" --salient-days "$FORGET_SALIENT_DAYS" | tail -1
fi

# 3. 재생 (dry-run 이면 처리 위치를 옮기지 않도록 건너뛴다)
[ "$DRY" = 1 ] || nw_py "$BRAIN/scripts/replay.py" scan --reqs "$S/req" --max "$REPLAY_MAX" --min-score "$REPLAY_MIN_SCORE" --first-days "$FIRST_WINDOW_DAYS" | tail -1

# 4. 검색 실패 학습
nmiss="$(grep -c '^- ' "$S/misses.md" 2>/dev/null || true)"
if [ -n "$nmiss" ] && [ "$nmiss" -ge "$MISS_MIN" ]; then
  nw_py - "$S/req/misses.json" "$S/misses.md" <<'PY'
import json, sys
json.dump({"mode": "targeted", "project_root": "", "slug": "-", "stack": "-", "caller": "brain-sleep",
           "payload": {"task": "검색 실패 학습", "candidates": sys.argv[2],
                       "instruction": "세션이 앞 이름으로 찾다 실패하고 뒤 이름으로 찾은 짝 목록이다. 같은 것을 가리키는 짝이면 common/search-aliases.md 에 별칭을 더하거나 해당 인덱스 줄에 그 말을 단서로 넣는다. 우연한 짝과 이미 반영된 짝은 건너뛴다."}},
          open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
PY
  nw_say sl_miss "$nmiss"
fi

# 5. 조각 정비
nw_py "$BRAIN/scripts/slices.py" --nb "$CX" --due "$SWEEP_N" > "$S/due.json" \
  && nw_py "$BRAIN/scripts/slices.py" --make-requests "$S/due.json" --registry "$CX/registry.md" --out "$S/req" --caller brain-sleep | tail -"$SWEEP_N"

# 투입: 등록 → 재생 → 실패 학습 → 정비 순(새 기억을 먼저 새기고 정리한다)
if [ "$DRY" = 1 ]; then
  nw_say sl_dry "$(ls "$S/req"/*.json 2>/dev/null | wc -l | tr -d ' ')"
else
  for r in "$S/req"/register-*.json "$S/req"/replay-*.json "$S/req"/misses.json "$S/req"/req-*.json; do
    [ -f "$r" ] && bash "$BRAIN/scripts/hippocampus-enqueue.sh" "$r" | head -1
  done
  date +%s > "$S/last"
fi

# 6. 검사
nw_py "$BRAIN/scripts/check.py" --nb "$CX" > "$S/check.txt" 2>&1
head -1 "$S/check.txt"

# 6b. 새 버전 확인(하루 한 번, 네트워크 - 설정 update_check=0 이면 건너뛴다)과 사용량 기록 정리
[ "$DRY" = 0 ] && nw_py "$BRAIN/scripts/update.py" check >/dev/null 2>&1
nw_py "$BRAIN/scripts/usage.py" prune >/dev/null 2>&1

# 7. 요약 - 사람에게 따로 띄우지 않는다(사용자 결정 2026-09-29). 잠 로그와 sleep/last-summary.txt 에만 남기고 /brain status 로 본다
HV="$(claude --version 2>/dev/null | head -1 | sed -n 's/^\([0-9][0-9.]*\).*/\1/p' | tr . -)"
CV="$(sed -n 's/^checked_version:[[:space:]]*claude-code_\([0-9-]*\)_agent.*/\1/p' "$CX/common/harness-routing.md" 2>/dev/null | head -1)"
# 두 값만 남긴다 - status.sh 가 brain 언어로 알린다
if [ -n "$HV" ] && [ -n "$CV" ] && [ "$HV" != "$CV" ]; then echo "$CV $HV" > "$S/notice-harness.txt"; else rm -f "$S/notice-harness.txt"; fi
fails="$(find "$C/done" -name '*.json' ! -name '*.request.json' -mtime -1 -exec grep -l '"status": *"\(failed\|denied\|timeout\)"' {} + 2>/dev/null | wc -l | tr -d ' ')"
msg=""
[ "${fails:-0}" -gt 0 ] && msg="$(nw_say sl_fails "$fails")"
if [ "$DRY" = 0 ]; then echo "$(date '+%F %T') ${msg:-$M_sl_ok}" > "$S/last-summary.txt"; fi
[ -n "$msg" ] && nw_say sl_sum "$msg"
nw_say sl_end "$(date '+%T')"

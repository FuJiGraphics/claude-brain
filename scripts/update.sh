#!/bin/bash
# brain 업데이트 - /claude-brain-update 가 부른다. 본체는 update.py (기억은 건드리지 않고 새 버전을 받은 뒤 install.sh 를 다시 돌린다).
# exec 로 넘긴다 - 받는 도중 이 파일이 바뀌어도 bash 가 바뀐 파일을 이어 읽지 않게.
set -u
BRAIN="$(cd "$(dirname "$(printf '%s' "$0" | tr '\\' '/')")/.." && pwd)"
SKILL_DIR="$BRAIN"
. "$BRAIN/scripts/_lib.sh"
nw_need_python
if [ "$NW_PY" = py ]; then exec py -3 "$BRAIN/scripts/update.py" "$@"; else exec "$NW_PY" "$BRAIN/scripts/update.py" "$@"; fi

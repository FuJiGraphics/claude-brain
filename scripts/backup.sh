#!/bin/bash
# brain 백업과 옮기기 - 본체는 backup.py.  사용법: backup.sh make [폴더] | restore <zip>
set -u
BRAIN="$(cd "$(dirname "$(printf '%s' "$0" | tr '\\' '/')")/.." && pwd)"
SKILL_DIR="$BRAIN"
. "$BRAIN/scripts/_lib.sh"
nw_need_python
nw_py "$BRAIN/scripts/backup.py" "$@"

#!/bin/bash
# brain 직접 새기기 - 사용자가 /brain 으로 남기라고 한 것을 hippocampus 큐에 넣고 바로 끝난다(기다리지 않는다).
# 사용법: remember.sh [--root <프로젝트 루트>] "<무엇을, 왜 - 근거(file:line 또는 사용자 발화)>" [더 있으면 인자를 더]
# 범위는 현재 폴더(또는 --root)가 속한 registry 프로젝트. 등록 안 된 곳이면 common 후보로 넘긴다(레이어는 해마가 정한다).
set -u
BRAIN="$(cd "$(dirname "$(printf '%s' "$0" | tr '\\' '/')")/.." && pwd)"
SKILL_DIR="$BRAIN"
. "$BRAIN/scripts/_lib.sh"
nw_need_python
ROOT="$PWD"
if [ "${1:-}" = "--root" ]; then ROOT="${2:?}"; shift 2; fi
[ $# -ge 1 ] || { echo "사용법: remember.sh \"<내용과 근거>\" ..."; exit 2; }
SC="$(nw_py "$BRAIN/scripts/thalamus.py" scope "$ROOT")"
REQ="$BRAIN/cortex/.hippocampus/remember-$$.json"
mkdir -p "$BRAIN/cortex/.hippocampus"
nw_py - "$REQ" "$SC" "$@" <<'PY'
import json, sys
out, sc, items = sys.argv[1], sys.argv[2], sys.argv[3:]
root, slug, stack = (sc.split('\t') + ['', '-', '-'])[:3] if sc else ('', '-', '-')
json.dump({"mode": "record", "project_root": root, "slug": slug or '-', "stack": stack or '-', "caller": "brain-remember",
           "payload": {"proposals": [{"what": x, "evidence": "사용자가 /brain 으로 직접 남기라고 한 내용"} for x in items]}},
          open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
PY
bash "$BRAIN/scripts/hippocampus-enqueue.sh" "$REQ" | head -1
rm -f "$REQ"

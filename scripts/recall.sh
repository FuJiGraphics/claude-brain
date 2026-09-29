#!/bin/bash
# brain 의식적 떠올리기 - 이름(파일, 심볼, API, 에러 문자열, 한국어 증상)으로 기억 저장소(cortex)를 찾는다.
# 세션은 이 도구를 모른다(기억은 thalamus 가 떠올려 준다). 사용자의 /brain 과 hippocampus 의 확인 단계가 쓴다.
# 사용법: recall.sh [--root <프로젝트 루트>] <이름1> [이름2] ...
#   범위: 현재 폴더(또는 --root)가 속한 registry 프로젝트의 projects, stacks, common 3레이어. 등록 안 된 곳이면 common 만.
#   찾은 기억 본문을 예산 안에서 함께 싣고, 같은 세션에서 이미 실은 본문은 경로만 보인다. 인덱스에서 못 찾으면 본문과
#   잠재 기억(dormant.md)까지 대체 검색한다.
#   기록: .active/<세션>.checks.log - 잠(sleep-stats.py)의 기억 강도와 검색 실패 학습이 읽는다.
set -u
BRAIN="$(cd "$(dirname "$(printf '%s' "$0" | tr '\\' '/')")/.." && pwd)"
SKILL_DIR="$BRAIN"
. "$BRAIN/scripts/_lib.sh"
nw_need_python
ROOT="$PWD"
if [ "${1:-}" = "--root" ]; then ROOT="${2:?사용법: recall.sh [--root <경로>] <이름>...}"; shift 2; fi
[ $# -ge 1 ] || { echo "사용법: recall.sh [--root <경로>] <이름>..."; exit 2; }
SC="$(nw_py "$BRAIN/scripts/thalamus.py" scope "$ROOT")"
SLUG="$(printf '%s' "$SC" | cut -f2)"; STACK="$(printf '%s' "$SC" | cut -f3)"
[ -n "$SLUG" ] || SLUG="?"; [ -n "$STACK" ] || STACK="-"
SID="$(printf '%s' "${CLAUDE_CODE_SESSION_ID:-manual}" | tr -cd 'A-Za-z0-9_-')"
mkdir -p "$BRAIN/.active/cache"
exec "$NW_PY" "$BRAIN/scripts/nbsearch.py" --nb "$BRAIN/cortex" --slug "$SLUG" --stack "$STACK" \
  --log "$BRAIN/.active/$SID.checks.log" --bodies "$BRAIN/.active/$SID.bodies" --cache-dir "$BRAIN/.active/cache" -- "$@"

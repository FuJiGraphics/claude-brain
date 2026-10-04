#!/bin/bash
# brain 에디터 열기 - 로컬 웹 서버(editor/server.py)를 세션과 무관한 프로세스로 띄우고 주소를 알린다. 떠 있으면 주소만 알린다.
# 사용법: editor.sh [--no-open] [stop]
#   /claude-brain-app 가 훅에서 부른다(훅 제한 5초 - 서버를 기다리는 것은 최대 3초).
#   서버는 127.0.0.1 에만 열리고 2시간 동안 요청이 없으면 스스로 끝난다.
set -u
BRAIN="$(cd "$(dirname "$(printf '%s' "$0" | tr '\\' '/')")/.." && pwd)"
SKILL_DIR="$BRAIN"
. "$BRAIN/scripts/_lib.sh"
nw_need_python
ST="$BRAIN/.active/editor.json"
OPEN=1; CMD=start
for a in "$@"; do case "$a" in --no-open) OPEN=0;; stop) CMD=stop;; esac; done
mkdir -p "$BRAIN/.active"
url() { nw_py -c 'import json,sys; d=json.load(open(sys.argv[1])); print("http://127.0.0.1:%d/?t=%s" % (d["port"], d["token"]))' "$ST" 2>/dev/null; }
pid() { nw_py -c 'import json,sys; print(json.load(open(sys.argv[1]))["pid"])' "$ST" 2>/dev/null; }
alive() { [ -f "$ST" ] && nw_pid_is "$(pid)" server.py; }
if [ "$CMD" = stop ]; then
  if alive; then kill "$(pid)" 2>/dev/null; rm -f "$ST"; echo "brain 앱을 껐다"; else echo "실행 중인 앱 없음"; fi
  exit 0
fi
if ! alive; then
  rm -f "$ST"
  nw_detach "$BRAIN/.active/editor.out" "$NW_PY" "$(nw_tool_path "$BRAIN/editor/server.py")" >/dev/null || { echo "오류: 에디터를 띄우지 못했다 - 직접: python3 $BRAIN/editor/server.py"; exit 1; }
  i=0
  while [ ! -f "$ST" ] && [ "$i" -lt 30 ]; do sleep 0.1; i=$((i+1)); done
  [ -f "$ST" ] || { echo "오류: 에디터가 3초 안에 뜨지 않았다 - 로그: $BRAIN/.active/editor.out"; exit 1; }
fi
U="$(url)"
if [ "$OPEN" = 1 ]; then
  # Chrome 이 있으면 주소창 없는 앱 창(폰 크기)으로 연다 - 브라우저 탭보다 앱처럼 보인다
  if [ "$NW_MAC" = 1 ] && [ -d "/Applications/Google Chrome.app" ]; then
    open -na "Google Chrome" --args --app="$U" --window-size=450,920 >/dev/null 2>&1 || open "$U" >/dev/null 2>&1
  elif [ "$NW_MAC" = 1 ]; then open "$U" >/dev/null 2>&1
  elif [ "$NW_WIN" = 1 ]; then cmd.exe /c start "" "$U" >/dev/null 2>&1
  elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$U" >/dev/null 2>&1 &
  fi
fi
echo "brain 앱: $U"
echo "(이 컴퓨터에서만 열린다. 끄기: bash $(nw_tool_path "$BRAIN/scripts/editor.sh") stop)"

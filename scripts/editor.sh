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
nw_i18n ed
ST="$BRAIN/.active/editor.json"
OPEN=1; CMD=start
for a in "$@"; do case "$a" in --no-open) OPEN=0;; stop) CMD=stop;; esac; done
mkdir -p "$BRAIN/.active"
STN="$(nw_tool_path "$ST")"
# i 는 서버 인스턴스 번호(시작 시각, 비밀 아님) - 페이지는 t 만 주소에서 지우므로 i 가 남아, 열린 창이 지금 서버의 것인지 알 수 있다
url() { nw_py -c 'import json,sys; d=json.load(open(sys.argv[1])); print("http://127.0.0.1:%d/?t=%s&i=%d" % (d["port"], d["token"], d.get("started", 0)))' "$STN" 2>/dev/null; }
# 살아 있는지는 HTTP 로 본다 - Windows 는 Git Bash 와 네이티브 프로세스의 번호 체계가 달라 pid 로는 알 수 없다
alive() {
  [ -f "$ST" ] && nw_py -c 'import json,sys,urllib.request; d=json.load(open(sys.argv[1])); urllib.request.urlopen("http://127.0.0.1:%d/index.html" % d["port"], timeout=1)' "$STN" >/dev/null 2>&1
}
quit_server() {
  nw_py -c 'import json,sys,urllib.request; d=json.load(open(sys.argv[1])); urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:%d/api/quit" % d["port"], data=b"{}", headers={"X-Brain-Token": d["token"], "Content-Type": "application/json"}), timeout=2)' "$STN" >/dev/null 2>&1
  local i=0; while alive && [ "$i" -lt 20 ]; do sleep 0.1; i=$((i+1)); done
  rm -f "$ST"
}
# 떠 있는 서버의 코드가 지금 파일과 같은가 - 서버가 남긴 code(가장 늦은 수정 시각)를 같은 방식으로 계산해 비교한다(server.py code_stamp)
same_code() {
  nw_py -c 'import glob,json,os,sys
b=sys.argv[2]; fs=[os.path.join(b,"editor","server.py")]+glob.glob(os.path.join(b,"editor","web","*"))+glob.glob(os.path.join(b,"scripts","*.py"))
cur=int(max((os.path.getmtime(f) for f in fs if os.path.isfile(f)), default=0))
sys.exit(0 if json.load(open(sys.argv[1])).get("code") == cur else 1)' "$STN" "$(nw_tool_path "$BRAIN")" 2>/dev/null
}
if [ "$CMD" = stop ]; then
  if alive; then quit_server; nw_say ed_off
  else nw_say ed_none; fi
  exit 0
fi
# focus_mac: Chrome 에 이 서버 주소의 탭이 있으면 그 창을 앞으로 가져온다(새 창을 또 만들지 않는다). 옛 서버의 탭이면 새 주소(새 토큰)로
#   다시 열되 보던 화면(# 뒤)은 지킨다. 찾았으면 0. Chrome 이 안 떠 있거나, 탭이 없거나, 자동화 권한이 없거나 1.5초를 넘기면 1(새 창을 연다) - 훅이 editor.sh 전체에 4초를 준다
focus_mac() {
  nw_py - "$U" <<'PY' >/dev/null 2>&1
import re, subprocess, sys
url = sys.argv[1]
m = re.match(r'(http://127\.0\.0\.1:\d+/)\?.*[?&]i=(\d+)', url)
if not m:
    sys.exit(1)
S = """on run argv
  set pre to item 1 of argv
  set newUrl to item 2 of argv
  set inst to item 3 of argv
  if application "Google Chrome" is not running then return "none"
  tell application "Google Chrome"
    repeat with w in windows
      set n to 0
      repeat with t in tabs of w
        set n to n + 1
        set u to URL of t
        if u starts with pre then
          if u does not contain ("i=" & inst) then
            set h to ""
            set AppleScript's text item delimiters to "#"
            if (count of text items of u) > 1 then set h to "#" & ((text items 2 thru -1 of u) as text)
            set AppleScript's text item delimiters to ""
            set URL of t to newUrl & h
          end if
          set active tab index of w to n
          set index of w to 1
          activate
          return "focused"
        end if
      end repeat
    end repeat
  end tell
  return "none"
end run"""
try:
    p = subprocess.run(['osascript', '-', m.group(1), url, m.group(2)], input=S, capture_output=True, text=True, timeout=1.5)
except Exception:
    sys.exit(1)
sys.exit(0 if p.stdout.strip() == 'focused' else 1)
PY
}
RESTARTED=0
if alive && ! same_code; then quit_server; RESTARTED=1; fi   # 업데이트 뒤 옛 코드 서버가 남아 있으면 새로 띄운다
if ! alive; then
  rm -f "$ST"
  nw_detach "$BRAIN/.active/editor.out" "$NW_PY" "$(nw_tool_path "$BRAIN/editor/server.py")" >/dev/null || { nw_say ed_fail "$(nw_tool_path "$BRAIN/editor/server.py")"; exit 1; }
  i=0
  while [ ! -f "$ST" ] && [ "$i" -lt 30 ]; do sleep 0.1; i=$((i+1)); done
  [ -f "$ST" ] || { nw_say ed_slow "$(nw_tool_path "$BRAIN/.active/editor.out")"; exit 1; }
fi
U="$(url)"; FRONT=0
if [ "$OPEN" = 1 ]; then
  # 주소창 없는 앱 창(폰 크기)으로 연다 - macOS 는 Chrome, Windows 는 Edge(늘 깔려 있다), Linux 는 Chrome 계열. 없으면 기본 브라우저
  # 이미 열린 앱 창이 있으면 새로 만들지 않고 그 창을 앞으로 가져온다(macOS 의 Chrome - AppleScript)
  if [ "$NW_MAC" = 1 ] && [ -d "/Applications/Google Chrome.app" ] && focus_mac; then
    FRONT=1
  elif [ "$NW_MAC" = 1 ] && [ -d "/Applications/Google Chrome.app" ]; then
    open -na "Google Chrome" --args --app="$U" --window-size=450,920 >/dev/null 2>&1 || open "$U" >/dev/null 2>&1
  elif [ "$NW_MAC" = 1 ]; then open "$U" >/dev/null 2>&1
  elif [ "$NW_WIN" = 1 ]; then
    # Git Bash 는 /c 같은 인자를 경로로 바꾼다 - 변환을 끄고 cmd 의 start 로 연다
    MSYS_NO_PATHCONV=1 cmd.exe /c start "" msedge "--app=$U" "--window-size=450,920" >/dev/null 2>&1 \
      || MSYS_NO_PATHCONV=1 cmd.exe /c start "" "$U" >/dev/null 2>&1
  else
    opened=0
    for b in google-chrome chromium chromium-browser microsoft-edge; do
      if command -v "$b" >/dev/null 2>&1; then ("$b" --app="$U" --window-size=450,920 >/dev/null 2>&1 &); opened=1; break; fi
    done
    [ "$opened" = 0 ] && command -v xdg-open >/dev/null 2>&1 && (xdg-open "$U" >/dev/null 2>&1 &)
  fi
fi
[ "$RESTARTED" = 1 ] && nw_say ed_restart
[ "$FRONT" = 1 ] && nw_say ed_front
nw_say ed_url "$U"
nw_say ed_local "$(nw_tool_path "$BRAIN/scripts/editor.sh")"

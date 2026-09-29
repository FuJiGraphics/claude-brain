#!/bin/bash
# n-worker 스크립트 공용 함수. 각 스크립트가 SKILL_DIR 를 정한 뒤 `. "$SKILL_DIR/scripts/_lib.sh"` 로 읽는다.
# bash 3.2(macOS 기본), Git Bash(MSYS2), Linux bash 에서 같은 동작이 목표다. 배열 확장 같은 bash 4 전용 문법은 쓰지 않는다.

# ---- 플랫폼 ----
NW_OS="$(uname -s 2>/dev/null)"
case "$NW_OS" in MINGW*|MSYS*|CYGWIN*) NW_WIN=1 ;; *) NW_WIN=0 ;; esac
case "$NW_OS" in Darwin) NW_MAC=1 ;; *) NW_MAC=0 ;; esac
NW_CYGPATH=0; [ "$NW_WIN" = 1 ] && command -v cygpath >/dev/null 2>&1 && NW_CYGPATH=1

# ---- python ----
# 후보를 실제로 실행해 본다. `command -v` 만 보면 Windows 의 Microsoft Store 실행 별칭(WindowsApps\python3.exe)처럼
# 존재하지만 실행되지 않는 스텁이 잡힌다. 첫 호출 때만 찾고 결과를 NW_PY 에 둔다.
# 모든 python 호출은 UTF-8 로 고정한다 - Windows 의 기본 로케일(cp949 등)이 한글 JSON 읽기와 파이프 출력을 깨뜨린다.
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
NW_PY="${NW_PY:-}"
nw_find_python() {
  local c
  for c in python3 python py; do
    command -v "$c" >/dev/null 2>&1 || continue
    if [ "$c" = py ]; then
      py -3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 7) else 1)' >/dev/null 2>&1 && { NW_PY="py"; return 0; }
    else
      "$c" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 7) else 1)' >/dev/null 2>&1 && { NW_PY="$c"; return 0; }
    fi
  done
  return 1
}
nw_py() {
  [ -n "$NW_PY" ] || nw_find_python || { echo "오류: python 3.7 이상이 없다 (python3, python, py 중 실행되는 것이 없음)" >&2; return 127; }
  if [ "$NW_PY" = py ]; then py -3 "$@"; else "$NW_PY" "$@"; fi
}
nw_need_python() { [ -n "$NW_PY" ] || nw_find_python || { echo "오류: python 3.7 이상이 필요하다 (python3, python, py 중 실행되는 것이 없음)" >&2; exit 2; }; }

# ---- 경로 ----
# nw_tool_path: 모델의 파일 도구(Node)와 bash 양쪽에서 통하는 표기. Windows 는 C:/Users/... (cygpath -m), 그 외는 그대로.
#   MSYS 의 자동 경로 변환은 독립된 argv 인자에만 적용되고 프롬프트 문장 안의 /c/Users/... 는 바꾸지 않으므로, 모델에게 보여 주는
#   경로는 여기서 미리 바꿔야 한다. 역슬래시 표기(cygpath -w)는 bash 인용과 JS/JSON 문자열에서 깨지므로 쓰지 않는다.
nw_tool_path() {
  if [ "$NW_CYGPATH" = 1 ]; then cygpath -m "$1" 2>/dev/null || printf '%s' "$1"; else printf '%s' "$1"; fi
}
# nw_bash_path: 반대 방향. 셸이 직접 실행하거나 여는 경로는 bash 표기(Windows 는 /c/...)여야 한다.
#   nw_tool_path 가 만든 C:/... 는 모델의 도구와 네이티브 프로세스용이고, Git Bash 의 bash 에는 -u 표기를 준다.
nw_bash_path() {
  if [ "$NW_CYGPATH" = 1 ]; then cygpath -u "$1" 2>/dev/null || printf '%s' "$1"; else printf '%s' "$1"; fi
}
# nw_key: 비교용 정규화. 표기 차이(/c/..., C:/..., C:\...)와 끝 슬래시를 지우고, 대소문자를 무시하는 파일시스템(Windows, macOS 기본)에서는 소문자로.
nw_key() {
  local p="$1"
  [ "$NW_CYGPATH" = 1 ] && p="$(cygpath -m "$p" 2>/dev/null || printf '%s' "$p")"
  p="$(printf '%s' "$p" | tr '\\' '/')"
  p="${p%/}"
  if [ "$NW_WIN" = 1 ] || [ "$NW_MAC" = 1 ]; then p="$(printf '%s' "$p" | tr '[:upper:]' '[:lower:]')"; fi
  printf '%s' "$p"
}
# nw_real_key: 심링크를 푼 실경로의 비교 키(macOS 의 /var → /private/var 같은 경우). 폴더가 없으면 빈 문자열.
nw_real_key() { local r; r="$(cd "$1" 2>/dev/null && pwd -P)" || { printf ''; return; }; nw_key "$r"; }
# nw_is_abs: 절대경로인가 (POSIX `/...` 또는 드라이브 `C:/...`, `C:\...`)
nw_is_abs() { case "$1" in /*|[A-Za-z]:/*|[A-Za-z]:\\*) return 0 ;; *) return 1 ;; esac; }
# nw_under <상위키> <경로키>: 경로가 상위 자체이거나 그 아래인가 (둘 다 nw_key 값)
nw_under() { [ -n "$1" ] || return 1; case "$2" in "$1"|"$1"/*) return 0 ;; *) return 1 ;; esac; }
# nw_dirname_of_script: $0 의 폴더. Windows 훅 등록에서 역슬래시 경로가 오면 dirname 이 구분자를 못 보므로 먼저 바꾼다.
nw_script_dir() { cd "$(dirname "$(printf '%s' "$1" | tr '\\' '/')")" 2>/dev/null && pwd; }

# ---- 파일 ----
nw_mtime() { stat -c %Y "$1" 2>/dev/null || stat -f %m "$1" 2>/dev/null || echo 0; }   # GNU 먼저 - GNU 의 -f 는 파일시스템 모드라 오류 없이 엉뚱한 값을 낸다
nw_strip() { tr -d ' \r\n' | tr -d '\357\273\277'; }   # 한 단어 설정 파일: 공백, CRLF, UTF-8 BOM 제거
nw_sha1() {   # stdin → 40자 hex
  if command -v shasum >/dev/null 2>&1; then shasum | cut -c1-40
  elif command -v sha1sum >/dev/null 2>&1; then sha1sum | cut -c1-40
  else nw_py -c 'import sys,hashlib; print(hashlib.sha1(sys.stdin.buffer.read()).hexdigest())'; fi
}

# ---- 프로세스 ----
# nw_pid_is <pid> <태그>: pid 가 살아 있고 그 명령줄이 태그(예: curator-daemon)를 담거나 bash 프로세스인가.
# kill -0 만 보면 재부팅/크래시 뒤 재사용된 pid 를 데몬으로 오판한다. MSYS 의 ps 는 인자 없이 명령 이름만 보이므로 bash 면 살아 있다고 본다.
nw_pid_is() {
  local pid="$1" tag="$2" cmd
  case "$pid" in ""|*[!0-9]*) return 1 ;; esac
  kill -0 "$pid" 2>/dev/null || return 1
  cmd="$(ps -p "$pid" -o command= 2>/dev/null || ps -p "$pid" -o args= 2>/dev/null || ps -p "$pid" 2>/dev/null)" || return 0
  [ -n "$cmd" ] || return 0
  case "$cmd" in *"$tag"*|*bash*) return 0 ;; *) return 1 ;; esac
}
# nw_detach <로그> <명령...>: 세션과 무관한 프로세스로 띄운다 - 새 세션(setsid) 또는 Windows DETACHED_PROCESS, stdin 은 /dev/null,
# cwd 는 스킬 폴더. `nohup cmd &` 는 같은 프로세스 그룹에 남아 하네스가 도구 셸의 그룹을 죽일 때 같이 죽고, 지워진 cwd 를 물려받는다.
# 명령과 로그 경로는 nw_tool_path 표기로 넘긴다(Windows 의 python 은 네이티브 프로세스라 /c/... 를 모른다). 성공 시 pid 를 출력한다.
nw_detach() {
  local log="$1"; shift
  local pid
  pid="$(nw_py - "$(nw_tool_path "$log")" "$(nw_tool_path "$SKILL_DIR")" "$@" 2>/dev/null <<'PY'
import os, shutil, subprocess, sys
log, cwd, cmd = sys.argv[1], sys.argv[2], list(sys.argv[3:])
cmd[0] = shutil.which(cmd[0]) or cmd[0]
out = open(log, "ab")
kw = dict(stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT, cwd=cwd, close_fds=True)
if os.name == "nt":
    kw["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
else:
    kw["start_new_session"] = True
print(subprocess.Popen(cmd, **kw).pid)
PY
)"
  case "$pid" in ''|*[!0-9]*) ;; *) printf '%s' "$pid"; return 0 ;; esac
  # 폴백: python 분리가 안 되는 환경. setsid 가 있으면 새 세션, 없으면 nohup 으로 띄운다.
  # nohup 은 도구 셸의 프로세스 그룹에 남아 하네스가 그룹을 죽이면 함께 죽는다 - 그래도 큐는 남고 다음 투입이 다시 띄운다.
  # 여기서는 셸이 직접 실행하므로 경로를 bash 표기로 되돌린다.
  # command substitution 안에서 case 를 쓰지 않는다 - ')' 가 '$(' 의 닫는 괄호로 오인돼 런타임 구문 오류가 난다
  # (cortex/common/lessons/deferred-parse-defeats-syntax-check.md).
  local a; local -a conv; conv=()
  for a in "$@"; do
    case "$a" in
      [A-Za-z]:/*) conv[${#conv[@]}]="$(nw_bash_path "$a")" ;;
      *) conv[${#conv[@]}]="$a" ;;
    esac
  done
  set -- "${conv[@]}"
  ( cd "$SKILL_DIR" 2>/dev/null || cd /
    if command -v setsid >/dev/null 2>&1; then setsid "$@" </dev/null >>"$(nw_bash_path "$log")" 2>&1 &
    else nohup "$@" </dev/null >>"$(nw_bash_path "$log")" 2>&1 & fi
    printf '%s' "$!" )
}

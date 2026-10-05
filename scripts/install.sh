#!/bin/bash
# brain 설치 - 이 폴더(설치 위치, 보통 ~/.claude/skills/brain)를 기준으로 네 가지를 건다. 여러 번 돌려도 같은 결과다.
#   1. ~/.claude/settings.json 에 thalamus 훅(SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, PostToolUseFailure, SubagentStart,
#      Stop, PreCompact, SessionEnd). 이 스크립트가 건 항목은 명령에 scripts/thalamus.py 가 든 것으로 알아본다.
#   2. ~/.claude/CLAUDE.md 에 기억 소유 한 줄 - 모델은 이 줄이 있어야 [기억] 을 자기 기억으로 믿고 쓴다(없으면 출처 불명
#      삽입으로 보고 무시했다, 2026-09-29 실측). 작동 원리는 적지 않는다.
#   3. macOS 면 launchd 로 매일 04:30 잠(scripts/sleep.sh). 다른 OS 는 cron 등으로 sleep.sh 를 하루 한 번 부르면 된다.
#   4. <설정 폴더>/commands/ 에 /claude-brain-* 명령어 파일(commands/ 템플릿에 설치 경로를 채운 것).
# 사용법: bash scripts/install.sh [--uninstall] [--no-sleep]
# 고치기 전 설정 파일은 <파일>.brain-bak-<시각> 으로 남긴다(직전 백업과 내용이 같으면 새로 만들지 않는다).
# 훅 등록이 실패하면(settings.json 이 JSON 이 아님 등) 나머지를 걸지 않고 종료 코드 1 로 멈춘다 - 반쪽 설치를 남기지 않는다.
set -u
BRAIN="$(cd "$(dirname "$(printf '%s' "$0" | tr '\\' '/')")/.." && pwd)"
SKILL_DIR="$BRAIN"
. "$BRAIN/scripts/_lib.sh"
nw_need_python
MODE="install"; SLEEP=1
for a in "$@"; do case "$a" in --uninstall) MODE="uninstall";; --no-sleep) SLEEP=0;; esac; done
# 언어 - 처음 설치면 OS 언어로 정한다(ko, en, ja, zh 밖이면 en). 이미 정했으면 그대로 둔다. 설치 글도 이 언어로 나온다
mkdir -p "$BRAIN/.active"
if [ "$MODE" = install ] && ! grep -q '^lang=' "$BRAIN/.active/config" 2>/dev/null; then
  echo "lang=$(nw_py "$BRAIN/scripts/lang.py" detect)" >> "$BRAIN/.active/config"
fi
nw_i18n in
CFG="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"; CFG="${CFG%/}"
[ -d "$CFG" ] && CFG="$(cd "$CFG" && pwd)"   # 끝 슬래시, 상대경로를 정리한다 - 거부 규칙과 경로 비교가 문자열로 맞아야 한다
# brain 이 <설정 폴더>/skills/brain 에 있으면 그 설정 폴더를 고쳐야 한다. 환경이 다른 폴더를 가리키면 엉뚱한 설정을 고치게 되므로 멈춘다.
if [ "$(basename "$(dirname "$BRAIN")")" = "skills" ]; then
  LOC="$(dirname "$(dirname "$BRAIN")")"
  if [ -f "$LOC/settings.json" ] && [ ! "$LOC" -ef "$CFG" ]; then
    nw_say in_loc_stop "$LOC" "$CFG" "$LOC"; exit 1
  fi
fi
TS="$(date +%Y%m%d-%H%M%S)"
# logs 는 launchd 가 잠 출력을 쓰는 곳이다(plist StandardOutPath) - 없는 폴더면 첫 잠이 뜨지 못할 수 있다
mkdir -p "$BRAIN/.active" "$BRAIN/cortex/.hippocampus/logs"
[ -f "$BRAIN/.active/brain-born" ] || date +%F > "$BRAIN/.active/brain-born"
[ "$MODE" = install ] && nw_say in_lang "$M_native"
# 설치 선택을 남긴다 - /claude-brain-update 가 install.sh 를 다시 돌릴 때 같은 선택(--no-sleep)을 쓴다
if [ "$MODE" = install ]; then if [ "$SLEEP" = 0 ]; then echo "--no-sleep" > "$BRAIN/.active/install-opts"; else rm -f "$BRAIN/.active/install-opts"; fi; fi

# 0. 기억 저장소 - 저장소의 seed/cortex 골격 중 없는 파일만 채운다. cortex/ 는 git 이 추적하지 않는다(사용자 기억이 자라는 곳)
if [ "$MODE" = install ]; then
  nw_py - "$BRAIN/seed/cortex" "$BRAIN/cortex" <<'PY' && nw_say in_seed "$(nw_tool_path "$BRAIN/cortex")"
import os, shutil, sys
src, dst = sys.argv[1], sys.argv[2]
if not os.path.isfile(os.path.join(src, 'registry.md')):
    sys.exit(1)   # 저장소가 온전하지 않다 - 빈 기억 저장소로 설치하지 않는다(아래 셸이 알린다)
for root, dirs, files in os.walk(src):
    rel = os.path.relpath(root, src)
    os.makedirs(os.path.join(dst, rel), exist_ok=True)
    for f in files:
        if f == '.gitkeep':
            continue
        t = os.path.join(dst, rel, f)
        if not os.path.exists(t):
            shutil.copyfile(os.path.join(root, f), t)
PY
  [ -f "$BRAIN/cortex/registry.md" ] || { nw_say in_seed_fail "$(nw_tool_path "$BRAIN/seed/cortex")"; exit 1; }
fi
# backup <파일>: 고치기 전 사본. 가장 최근 사본과 같으면 새로 만들지 않는다(여러 번 돌려도 사본이 쌓이지 않게)
backup() {
  [ -f "$1" ] || return 0
  local last; last="$(ls "$1".brain-bak-* 2>/dev/null | sort | tail -1)"   # 이름의 시각 순(cp -p 가 수정 시각을 복사해 ls -t 는 못 쓴다)
  [ -n "$last" ] && cmp -s "$1" "$last" && return 0
  local dest="$1.brain-bak-$TS"; [ -e "$dest" ] && dest="$dest-$$"   # 같은 초에 두 번 돌아도 앞 사본을 덮지 않는다
  cp -p "$1" "$dest"
}

# 1. 훅
backup "$CFG/settings.json"
mkdir -p "$CFG"
# 훅이 부를 파이썬 - Windows 는 python3 이 없고 python 이나 py 런처만 있는 경우가 많다. 경로는 파이썬이 읽는 표기(C:/...)로 넘긴다
case "$NW_PY" in py) PYHOOK="py -3" ;; *) PYHOOK="$NW_PY" ;; esac
nw_py - "$CFG/settings.json" "$(nw_tool_path "$BRAIN")" "$MODE" "$PYHOOK" <<'PY' || { nw_say in_hook_fail "$CFG/settings.json"; exit 1; }
import json, os, shlex, stat, sys
path, brain, mode = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, os.path.join(brain, 'scripts'))
from cli_i18n import m
path = os.path.realpath(path)   # dotfiles 로 관리하는 심링크면 링크를 끊지 않고 대상 파일을 고친다
try:
    d = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}
except ValueError as e:
    print(m('in.not_json', e))
    sys.exit(1)
if not isinstance(d, dict) or not isinstance(d.get('hooks', {}), dict):
    print(m('in.bad_shape'))
    sys.exit(1)
hooks = d.setdefault('hooks', {})
# 끝의 exit 0 이 핵심이다: 파일이 없으면 python3 이 종료 코드 2 를 내는데, PreToolUse 훅의 2 는 '모든 도구 호출 차단'이다.
# 어떤 경우에도 세션을 막지 않도록 명령 전체를 0 으로 끝낸다(출력 JSON 은 그대로 전달된다).
cmd = 'f=%s; [ -f "$f" ] && %s "$f" hook; exit 0' % (shlex.quote(brain + '/scripts/thalamus.py'), sys.argv[4])
mine = lambda h: 'scripts/thalamus.py' in (h.get('command') or '')
for ev in list(hooks):
    groups = []
    for g in hooks[ev]:
        g['hooks'] = [h for h in g.get('hooks', []) if not mine(h)]
        if g['hooks']:
            groups.append(g)
    hooks[ev] = groups
    if not groups:
        del hooks[ev]
if mode == 'install':
    want = [('SessionStart', '*'), ('UserPromptSubmit', None), ('PreToolUse', 'Edit|Write|MultiEdit|NotebookEdit|Bash|AskUserQuestion'), ('PostToolUse', 'Read'),
            ('PostToolUseFailure', 'Bash'), ('SubagentStart', None), ('Stop', None), ('PreCompact', None), ('SessionEnd', None)]
    for ev, matcher in want:
        g = {'hooks': [{'type': 'command', 'command': cmd, 'timeout': 5}]}
        if matcher:
            g['matcher'] = matcher
        hooks.setdefault(ev, []).append(g)
# 상태줄 - 원래 상태줄(예: caveman)을 남기고 brain 상태줄로 감싼다(켜져 있으면 [BRAIN] 을 붙인다). 해제면 원래대로 되돌린다.
# 명령 끝에 원래 명령을 한 번 더 둔다 - brain 폴더가 사라져도 원래 상태줄은 그대로 뜬다.
act = os.path.join(brain, '.active')
prev_json, prev_cmd = os.path.join(act, 'statusline-prev.json'), os.path.join(act, 'statusline-prev.cmd')
sl = d.get('statusLine')
ours = isinstance(sl, dict) and 'scripts/statusline.sh' in (sl.get('command') or '')
if mode == 'install' and not ours:
    os.makedirs(act, exist_ok=True)
    pc = sl.get('command') if isinstance(sl, dict) and sl.get('type') == 'command' else ''
    if sl is not None:
        json.dump(sl, open(prev_json, 'w', encoding='utf-8'), ensure_ascii=False)
    elif os.path.exists(prev_json):
        os.remove(prev_json)
    open(prev_cmd, 'w', encoding='utf-8').write(pc or '')
    new = dict(sl) if isinstance(sl, dict) else {}
    new['type'] = 'command'
    new['command'] = 'f=%s; if [ -f "$f" ]; then exec bash "$f"; fi; %s' % (shlex.quote(brain + '/scripts/statusline.sh'), pc or 'exit 0')
    d['statusLine'] = new
elif mode == 'uninstall' and ours:
    if os.path.exists(prev_json):
        d['statusLine'] = json.load(open(prev_json, encoding='utf-8'))
    else:
        d.pop('statusLine', None)
tmp = path + '.tmp'
json.dump(d, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
if os.path.exists(path):
    os.chmod(tmp, stat.S_IMODE(os.stat(path).st_mode))   # 0600 같은 원래 권한 유지
os.replace(tmp, path)
print(m('in.hooks_on' if mode == 'install' else 'in.hooks_off', path))
PY

# 2. 기억 소유 한 줄
MD="$CFG/CLAUDE.md"
backup "$MD"
LANG_NOW="$(nw_py "$BRAIN/scripts/lang.py" get)"
nw_py - "$MD" "$MODE" "$BRAIN/scripts" "$LANG_NOW" <<'PY' || { nw_say in_md_fail "$MD"; exit 1; }
import os, re, sys
path, mode = sys.argv[1], sys.argv[2]
sys.path.insert(0, sys.argv[3])
import lang
from cli_i18n import m
path = os.path.realpath(path)
s = open(path, encoding='utf-8').read() if os.path.exists(path) else ''
begin, end = '<!-- brain:begin -->', '<!-- brain:end -->'
s = re.sub(r'\n*' + re.escape(begin) + r'.*?' + re.escape(end) + r'\n?', '\n', s, flags=re.S).rstrip() + '\n'
if mode == 'install':
    s += '\n' + begin + '\n' + lang.T[sys.argv[4]]['claude_md'] + '\n' + end + '\n'   # 네 언어의 [기억] 표시를 모두 적는다
open(path, 'w', encoding='utf-8').write(s)
print(m('in.md_on' if mode == 'install' else 'in.md_off', path))
PY

# 2b. 명령어 - <설정 폴더>/commands/claude-brain-*.md. 저장소 commands/ 템플릿의 {{BRAIN}}, {{DESC}}, {{HINT}} 를 이 설치 경로와
# brain 언어로 채운다. 자동완성에 /claude-brain-status 처럼 하나씩 뜬다. 표식 줄(brain:command)이 있는 파일만 이 스크립트 것으로 보고 고치거나 지운다.
# 위치를 .active/commands-dir 에 남긴다 - 언어를 바꾸면(config.sh lang) 설명을 그 언어로 다시 쓴다.
nw_py "$BRAIN/scripts/cli_i18n.py" commands "$(nw_tool_path "$BRAIN/commands")" "$(nw_tool_path "$CFG/commands")" "$(nw_tool_path "$BRAIN")" "$MODE" || nw_say in_cmd_fail
if [ "$MODE" = install ]; then nw_tool_path "$CFG/commands" > "$BRAIN/.active/commands-dir"; else rm -f "$BRAIN/.active/commands-dir"; fi

# 3. 밤 잠 예약
# 예약 이름은 기기 하나에 하나다 - 기본 설정 폴더(~/.claude)가 아니면 폴더별 꼬리표를 붙여 다른 설치의 예약을 덮거나 지우지 않는다
LABEL="com.brain.sleep"; TN="brain-sleep"
if [ "$CFG" != "$(cd "$HOME/.claude" 2>/dev/null && pwd)" ]; then
  SUF="$(printf '%s' "$CFG" | nw_sha1 | cut -c1-8)"; LABEL="$LABEL.$SUF"; TN="$TN-$SUF"
fi
PL="$HOME/Library/LaunchAgents/$LABEL.plist"
if [ "$(uname)" = "Darwin" ]; then
  if [ "$MODE" = "install" ] && [ "$SLEEP" = 1 ]; then
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null
    mkdir -p "$HOME/Library/LaunchAgents"
    P="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
    # plistlib 로 채운다 - 경로에 &, #, 따옴표가 있어도 깨지지 않는다. 설정 폴더를 바꿔 쓰는 기기면 밤 잠도 같은 폴더를 보게 넘긴다.
    nw_py - "$BRAIN/scripts/brain.sleep.plist" "$PL" "$BRAIN" "$P" "$LABEL" "${CLAUDE_CONFIG_DIR:+$CFG}" <<'PY' || { nw_say in_plist_fail; nw_say in_done; exit 0; }
import plistlib, sys
tpl, out, brain, path, label, cfg = sys.argv[1:7]
d = plistlib.loads(open(tpl, 'rb').read())
def fill(v):
    if isinstance(v, str):
        return v.replace('{{BRAIN}}', brain).replace('{{PATH}}', path).replace('{{LABEL}}', label)
    if isinstance(v, list):
        return [fill(x) for x in v]
    if isinstance(v, dict):
        return {k: fill(x) for k, x in v.items()}
    return v
d = fill(d)
env = d.setdefault('EnvironmentVariables', {})
env.pop('CLAUDE_CONFIG_DIR', None)
if cfg:
    env['CLAUDE_CONFIG_DIR'] = cfg
data = plistlib.dumps(d)
plistlib.loads(data)
open(out, 'wb').write(data)
PY
    # bootout 직후 bootstrap 은 EIO(5)로 실패할 때가 있다 - 잠깐 쉬고 몇 번 다시 한다. 끝내 실패해도 훅과 기억은 이미 걸렸으니
    # 설치 실패로 치지 않고 알리기만 한다(잠은 /brain sleep 으로 손으로 돌릴 수 있다).
    ok=0
    for i in 1 2 3; do
      if launchctl bootstrap "gui/$(id -u)" "$PL" 2>/dev/null; then ok=1; break; fi
      sleep 1
    done
    if [ "$ok" = 1 ]; then nw_say in_sleep_on "$PL"; else nw_say in_sleep_fail "$(id -u)" "$PL"; fi
  elif [ "$MODE" = "uninstall" ]; then
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null; rm -f "$PL"; nw_say in_sleep_off
  fi
elif [ "$NW_WIN" = 1 ]; then
  # Windows - 작업 스케줄러에 매일 04:30 으로 건다. Git Bash 의 경로 변환이 /Create 같은 인자를 망가뜨리지 않게 끈다
  if [ "$MODE" = "install" ] && [ "$SLEEP" = 1 ]; then
    BASHW="$(cygpath -w "$(command -v bash)" 2>/dev/null || echo bash)"
    SLEEPW="$(nw_tool_path "$BRAIN/scripts/sleep.sh")"
    if MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*' schtasks /Create /F /SC DAILY /ST 04:30 /TN "$TN" /TR "\"$BASHW\" -l \"$SLEEPW\"" >/dev/null 2>&1; then
      nw_say in_sleep_win "$TN"
    else
      nw_say in_sleep_win_fail
    fi
  elif [ "$MODE" = "uninstall" ]; then
    MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*' schtasks /Delete /F /TN "$TN" >/dev/null 2>&1 && nw_say in_sleep_off
  fi
else
  [ "$MODE" = "install" ] && nw_say in_sleep_other "$BRAIN/scripts/sleep.sh"
fi

# 4. 해제면 해마도 멈춘다 - 지금 항목이 끝나면 선다. 남은 큐는 지우지 않는다(다시 설치하면 이어서 돈다).
if [ "$MODE" = "uninstall" ]; then
  C="$BRAIN/cortex/.hippocampus"
  nq="$(ls "$C/queue"/*.json 2>/dev/null | wc -l | tr -d ' ')"
  if nw_pid_is "$(cat "$C/lock/pid" 2>/dev/null)" hippocampus-daemon; then
    touch "$C/stop"; nw_say in_hippo_stop "$nq"
  elif [ "$nq" != "0" ]; then
    nw_say in_hippo_idle "$nq"
  fi
fi
if [ "$MODE" = install ]; then nw_say in_done; else nw_say in_undone "$(nw_tool_path "$BRAIN/cortex")"; fi
exit 0

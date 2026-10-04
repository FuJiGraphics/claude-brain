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
CFG="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"; CFG="${CFG%/}"
[ -d "$CFG" ] && CFG="$(cd "$CFG" && pwd)"   # 끝 슬래시, 상대경로를 정리한다 - 거부 규칙과 경로 비교가 문자열로 맞아야 한다
# brain 이 <설정 폴더>/skills/brain 에 있으면 그 설정 폴더를 고쳐야 한다. 환경이 다른 폴더를 가리키면 엉뚱한 설정을 고치게 되므로 멈춘다.
if [ "$(basename "$(dirname "$BRAIN")")" = "skills" ]; then
  LOC="$(dirname "$(dirname "$BRAIN")")"
  if [ -f "$LOC/settings.json" ] && [ ! "$LOC" -ef "$CFG" ]; then
    echo "중단: brain 은 $LOC/skills 에 있는데 설정 폴더는 $CFG 다 - CLAUDE_CONFIG_DIR=$LOC 로 다시 돌린다"; exit 1
  fi
fi
TS="$(date +%Y%m%d-%H%M%S)"
# logs 는 launchd 가 잠 출력을 쓰는 곳이다(plist StandardOutPath) - 없는 폴더면 첫 잠이 뜨지 못할 수 있다
mkdir -p "$BRAIN/.active" "$BRAIN/cortex/.hippocampus/logs"
[ -f "$BRAIN/.active/brain-born" ] || date +%F > "$BRAIN/.active/brain-born"
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
nw_py - "$CFG/settings.json" "$(nw_tool_path "$BRAIN")" "$MODE" "$PYHOOK" <<'PY' || { echo "중단: 훅을 등록하지 못했다 - $CFG/settings.json 을 확인한 뒤 다시(CLAUDE.md, 잠 예약은 건드리지 않았다)"; exit 1; }
import json, os, shlex, stat, sys
path, brain, mode = sys.argv[1], sys.argv[2], sys.argv[3]
path = os.path.realpath(path)   # dotfiles 로 관리하는 심링크면 링크를 끊지 않고 대상 파일을 고친다
try:
    d = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}
except ValueError as e:
    print('settings.json 이 JSON 이 아니다: %s' % e)
    sys.exit(1)
if not isinstance(d, dict) or not isinstance(d.get('hooks', {}), dict):
    print('settings.json 의 형식이 예상과 다르다(최상위나 hooks 가 객체가 아님)')
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
print('훅: %s (%s)' % ('등록' if mode == 'install' else '해제', path))
PY

# 2. 기억 소유 한 줄
MD="$CFG/CLAUDE.md"
backup "$MD"
# 언어 - 처음 설치면 OS 언어로 정한다(ko, en, ja, zh 밖이면 en). 이미 정했으면 그대로 둔다. 바꾸기: scripts/config.sh lang <언어>
if [ "$MODE" = install ] && ! grep -q '^lang=' "$BRAIN/.active/config" 2>/dev/null; then
  echo "lang=$(nw_py "$BRAIN/scripts/lang.py" detect)" >> "$BRAIN/.active/config"
fi
LANG_NOW="$(nw_py "$BRAIN/scripts/lang.py" get)"
nw_py - "$MD" "$MODE" "$BRAIN/scripts" "$LANG_NOW" <<'PY' || { echo "중단: CLAUDE.md 를 고치지 못했다 - 훅은 이미 걸렸다. $MD 를 확인한 뒤 install.sh 를 다시 돌린다"; exit 1; }
import os, re, sys
path, mode = sys.argv[1], sys.argv[2]
sys.path.insert(0, sys.argv[3])
import lang
path = os.path.realpath(path)
s = open(path, encoding='utf-8').read() if os.path.exists(path) else ''
begin, end = '<!-- brain:begin -->', '<!-- brain:end -->'
s = re.sub(r'\n*' + re.escape(begin) + r'.*?' + re.escape(end) + r'\n?', '\n', s, flags=re.S).rstrip() + '\n'
if mode == 'install':
    s += '\n' + begin + '\n' + lang.T[sys.argv[4]]['claude_md'] + '\n' + end + '\n'   # 네 언어의 [기억] 표시를 모두 적는다
open(path, 'w', encoding='utf-8').write(s)
print('기억 소유 한 줄: %s (%s)' % ('추가' if mode == 'install' else '제거', path))
PY

# 2b. 명령어 - <설정 폴더>/commands/claude-brain-*.md. 저장소 commands/ 템플릿의 {{BRAIN}} 을 이 설치 경로로 채워 만든다.
# 자동완성에 /claude-brain-status 처럼 하나씩 뜬다. 표식 줄(brain:command)이 있는 파일만 이 스크립트 것으로 보고 고치거나 지운다.
nw_py - "$BRAIN/commands" "$CFG/commands" "$BRAIN" "$MODE" <<'PY' || echo "경고: 명령어 파일을 만들지 못했다 - 훅과 기억은 정상"
import glob, os, sys
src, dst, brain, mode = sys.argv[1:5]
MARK = '<!-- brain:command'
mine = lambda f: MARK in open(f, encoding='utf-8').read()
want = {}
if mode == 'install':
    for t in sorted(glob.glob(os.path.join(src, 'claude-brain-*.md'))):
        want[os.path.basename(t)] = open(t, encoding='utf-8').read().replace('{{BRAIN}}', brain)
    os.makedirs(dst, exist_ok=True)
n_add = n_del = 0
for f in glob.glob(os.path.join(dst, 'claude-brain-*.md')):
    if os.path.basename(f) not in want and mine(f):
        os.remove(f); n_del += 1
for name, text in want.items():
    f = os.path.join(dst, name)
    if os.path.exists(f) and not mine(f):
        print('건너뜀: %s 는 사용자 파일이다' % f); continue
    if not os.path.exists(f) or open(f, encoding='utf-8').read() != text:
        open(f, 'w', encoding='utf-8').write(text); n_add += 1
if mode == 'install':
    print('명령어: /claude-brain-* %d개 (%s, 새로 쓴 것 %d, 지운 것 %d)' % (len(want), dst, n_add, n_del))
else:
    print('명령어: /claude-brain-* %d개 제거' % n_del)
PY

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
    nw_py - "$BRAIN/scripts/brain.sleep.plist" "$PL" "$BRAIN" "$P" "$LABEL" "${CLAUDE_CONFIG_DIR:+$CFG}" <<'PY' || { echo "경고: 잠 예약 파일을 만들지 못했다 - 훅과 기억은 정상"; exit 0; }
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
    if [ "$ok" = 1 ]; then echo "잠 예약: 매일 04:30 ($PL)"; else echo "경고: 잠 예약(launchctl bootstrap)이 실패했다 - 훅과 기억은 정상. 나중에 install.sh 를 다시 돌리거나 launchctl bootstrap gui/$(id -u) $PL"; fi
  elif [ "$MODE" = "uninstall" ]; then
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null; rm -f "$PL"; echo "잠 예약 해제"
  fi
elif [ "$NW_WIN" = 1 ]; then
  # Windows - 작업 스케줄러에 매일 04:30 으로 건다. Git Bash 의 경로 변환이 /Create 같은 인자를 망가뜨리지 않게 끈다
  if [ "$MODE" = "install" ] && [ "$SLEEP" = 1 ]; then
    BASHW="$(cygpath -w "$(command -v bash)" 2>/dev/null || echo bash)"
    SLEEPW="$(nw_tool_path "$BRAIN/scripts/sleep.sh")"
    if MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*' schtasks /Create /F /SC DAILY /ST 04:30 /TN "$TN" /TR "\"$BASHW\" -l \"$SLEEPW\"" >/dev/null 2>&1; then
      echo "잠 예약: 매일 04:30 (작업 스케줄러 $TN)"
    else
      echo "경고: 작업 스케줄러 등록이 실패했다 - 훅과 기억은 정상. 잠은 /claude-brain-sleep 으로 손으로 돌릴 수 있다"
    fi
  elif [ "$MODE" = "uninstall" ]; then
    MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*' schtasks /Delete /F /TN "$TN" >/dev/null 2>&1 && echo "잠 예약 해제"
  fi
else
  [ "$MODE" = "install" ] && echo "잠 예약: 자동 등록은 macOS, Windows 만 한다 - 하루 한 번 bash $BRAIN/scripts/sleep.sh 를 부르도록 cron 등에 건다"
fi

# 4. 해제면 해마도 멈춘다 - 지금 항목이 끝나면 선다. 남은 큐는 지우지 않는다(다시 설치하면 이어서 돈다).
if [ "$MODE" = "uninstall" ]; then
  C="$BRAIN/cortex/.hippocampus"
  nq="$(ls "$C/queue"/*.json 2>/dev/null | wc -l | tr -d ' ')"
  if nw_pid_is "$(cat "$C/lock/pid" 2>/dev/null)" hippocampus-daemon; then
    touch "$C/stop"; echo "해마: 지금 항목이 끝나면 멈춘다(남은 큐 ${nq}건은 두었다)"
  elif [ "$nq" != "0" ]; then
    echo "해마: 실행 중 아님(남은 큐 ${nq}건은 두었다)"
  fi
fi
exit 0

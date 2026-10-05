#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""brain 업데이트 - 설치 폴더(git clone)를 원격의 새 버전으로 올리고 install.sh 를 다시 돌린다. 기억(cortex)은 건드리지 않는다.

사용법: update.py          새 버전이 있으면 받는다 (/claude-brain-update 가 update.sh 로 부른다)
       update.py check    원격만 확인해 .active/update-available 을 남기거나 지운다 (밤 정리가 하루 한 번 부른다)

안전장치:
- fast-forward 만 한다. 직접 고친 파일이나 따로 만든 커밋이 있으면 멈추고 알린다(개발용 clone 을 망가뜨리지 않는다).
- cortex/ 는 git 이 추적하지 않는다(seed/cortex 가 골격). 그래서 받기는 기억을 건드리지 않는다.
  cortex 를 추적하던 옛 버전(2026-10-05 이전)은 이 파일이 없어서 README 의 한 번용 이전 명령으로 올라온다.
- 끝나면 install.sh 를 다시 돌리고(새 훅, 명령어), 떠 있는 앱은 끈다(다음 /claude-brain-app 이 새 코드로 연다).
"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BRAIN = os.path.dirname(HERE)
ACTIVE = os.path.join(BRAIN, '.active')
FLAG = os.path.join(ACTIVE, 'update-available')
sys.path.insert(0, HERE)
import plat  # noqa: E402
from cli_i18n import m  # noqa: E402

ENV = dict(os.environ, GIT_TERMINAL_PROMPT='0', LC_ALL='C', PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
ENV.setdefault('GIT_SSH_COMMAND', 'ssh -o BatchMode=yes')   # 암호를 묻는 ssh 키면 묻지 않고 실패한다(밤에 멈춰 서지 않게)


def say(text):
    sys.stdout.buffer.write((text + '\n').encode('utf-8'))
    sys.stdout.buffer.flush()


def git(*args, timeout=60):
    p = subprocess.run(['git', '-C', BRAIN] + list(args), capture_output=True, timeout=timeout, env=ENV)
    # 앞 공백은 남긴다 - status --porcelain 의 첫 줄 ' M 파일' 에서 칸이 밀린다
    return p.returncode, p.stdout.decode('utf-8', 'replace').rstrip(), p.stderr.decode('utf-8', 'replace').strip()


def upstream():
    """[원격 브랜치] (이름, 오류 키) - git 저장소가 아니거나 추적 브랜치가 없으면 오류 키"""
    if not os.path.isdir(os.path.join(BRAIN, '.git')):
        return None, 'up.nogit'
    rc, up, _ = git('rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}')
    if rc != 0 or not up:
        return None, 'up.noupstream'
    return up, None


def fetch():
    try:
        rc, _, err = git('fetch', '--quiet', timeout=60)
    except subprocess.TimeoutExpired:
        return 'timeout'
    return None if rc == 0 else (err.splitlines() or ['?'])[-1][:200]


def behind(up):
    rc, n, _ = git('rev-list', '--count', 'HEAD..' + up)
    return int(n) if rc == 0 and n.isdigit() else 0


def check():
    """[밤의 확인] 새 커밋 수와 마지막 제목을 FLAG 에 남긴다. 실패하면 조용히 둔다(다음 밤에 다시)"""
    try:
        cfg = open(os.path.join(ACTIVE, 'config'), encoding='utf-8', errors='replace').read()
    except OSError:
        cfg = ''
    if 'update_check=0' in cfg.split('\n'):
        return 0
    up, err = upstream()
    if err or fetch():
        return 0
    n = behind(up)
    if n > 0:
        _, subj, _ = git('log', '-1', '--format=%s', up)
        os.makedirs(ACTIVE, exist_ok=True)
        with open(FLAG, 'w', encoding='utf-8') as f:
            f.write('%d\t%s\t%d\n' % (n, subj[:120], int(time.time())))
    elif os.path.exists(FLAG):
        os.remove(FLAG)
    return 0


def _read_text(p):
    try:
        return open(p, encoding='utf-8', errors='replace').read()
    except OSError:
        return ''


def update():
    up, err = upstream()
    if err:
        say(m(err))
        return 2
    say(m('up.checking'))
    e = fetch()
    if e:
        say(m('up.fetch_fail', e))
        return 1
    n = behind(up)
    _, head, _ = git('rev-parse', '--short', 'HEAD')
    if n == 0:
        if os.path.exists(FLAG):
            os.remove(FLAG)
        say(m('up.latest', head))
        return 0
    rc, ahead, _ = git('rev-list', '--count', up + '..HEAD')
    if rc == 0 and ahead.isdigit() and int(ahead) > 0:
        say(m('up.diverged', ahead))
        return 2
    rc, st, _ = git('status', '--porcelain', '--untracked-files=no')
    dirty = [l[3:] for l in st.splitlines() if l and not l[3:].startswith('cortex/')]
    if dirty:
        say(m('up.dirty', ', '.join(dirty[:8])))
        return 2
    old = head
    rc, _, err = git('merge', '--ff-only', up, timeout=120)
    if rc != 0:
        say(m('up.merge_fail', (err.splitlines() or ['?'])[-1][:200]))
        return 1
    _, new, _ = git('rev-parse', '--short', 'HEAD')
    _, log, _ = git('log', '--format=- %s', '%s..HEAD' % old)
    say(m('up.done', old, new))
    lines = log.splitlines()
    for l in lines[:10]:
        say(l)
    if len(lines) > 10:
        say(m('up.more', len(lines) - 10))
    # 새 훅, 명령어, 시드 반영 - install.sh 는 여러 번 돌려도 같은 결과다. 처음 설치 때의 선택(--no-sleep)을 그대로 쓴다
    opts = [x for x in _read_text(os.path.join(ACTIVE, 'install-opts')).split() if x in ('--no-sleep',)]
    p = subprocess.run(plat.argv(['bash', os.path.join(HERE, 'install.sh')] + opts), capture_output=True, env=ENV, timeout=180)
    say(p.stdout.decode('utf-8', 'replace').strip())
    if p.returncode != 0:
        say(p.stderr.decode('utf-8', 'replace').strip()[-400:])
    # 떠 있는 앱은 옛 코드다 - 끈다
    subprocess.run(plat.argv(['bash', os.path.join(HERE, 'editor.sh'), 'stop']), capture_output=True, env=ENV, timeout=20)
    if os.path.exists(FLAG):
        os.remove(FLAG)
    say(m('up.restart'))
    return 0 if p.returncode == 0 else 1


def main():
    a = sys.argv[1:]
    if a and a[0] == 'check':
        return check()
    return update()


if __name__ == '__main__':
    sys.exit(main())

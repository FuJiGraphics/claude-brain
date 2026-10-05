#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""brain 플랫폼 처리 - 경로 비교, bash 찾기, 프로세스 분리, 생존 확인을 macOS, Linux, Windows 에서 같게 한다.

경로: Windows 의 훅 입력은 C:\\Users\\..., registry 는 C:/Users/..., Git Bash 는 /c/Users/... 로 올 수 있다.
      norm 이 셋을 C:/Users/... 하나로 맞추고, Windows 는 대소문자를 무시해 비교한다. macOS, Linux 는 지금까지와 같다(끝 / 만 뗀다).
bash: Windows 의 PATH 에 있는 bash 는 WSL(C:\\Windows\\System32\\bash.exe)일 수 있다 - Git Bash 를 골라야 스크립트가 같은 환경에서 돈다.
"""
import os
import re
import shutil
import subprocess
import sys

WIN = os.name == 'nt'
_ABS = re.compile(r'^(/|[A-Za-z]:[\\/])')
_MSYS = re.compile(r'^/([A-Za-z])(/.*)?$')


def is_abs(p):
    """[절대경로인가] /..., C:/..., C:\\..."""
    return bool(p) and bool(_ABS.match(p))


def norm(p):
    """[경로 표기 맞추기] 역슬래시 → /, Windows 면 /c/... → C:/..., 끝 / 제거(루트는 남긴다)"""
    p = (p or '').replace('\\', '/')
    if WIN:
        m = _MSYS.match(p)
        if m:
            p = m.group(1).upper() + ':' + (m.group(2) or '/')
        if len(p) >= 2 and p[1] == ':':
            p = p[0].upper() + p[1:]
    if len(p) > 1 and p.endswith('/') and not re.match(r'^[A-Za-z]:/$', p):
        p = p.rstrip('/')
    return p


def key(p):
    """[비교 키] Windows 는 대소문자를 무시한다"""
    q = norm(p)
    return q.lower() if WIN else q


def under(root, p):
    """[p 가 root 자신이거나 그 아래인가]"""
    r, q = key(root), key(p)
    return bool(r) and (q == r or q.startswith(r.rstrip('/') + '/'))


def git_root(p):
    """[가장 가까운 git 루트] p 자신이나 위로 .git 이 있는 폴더(norm 표기), 없으면 None. 드라이브 루트, / 에서 멈춘다"""
    cur = os.path.abspath(p or '.')
    while True:
        if os.path.exists(os.path.join(cur, '.git')):
            return norm(cur)
        up = os.path.dirname(cur)
        if up == cur:
            return None
        cur = up


def is_tmp(p):
    """[임시 폴더인가] /tmp, /private(macOS 의 /tmp, /var 실체), /var/tmp, /var/folders, Windows 의 TEMP 아래"""
    q = key(p)
    roots = ['/tmp', '/private', '/var/tmp', '/var/folders'] + [key(os.environ.get(k) or '') for k in ('TEMP', 'TMP') if os.environ.get(k)]
    return any(r and (q == r or q.startswith(r.rstrip('/') + '/')) for r in roots)


def bash():
    """[bash 실행 파일] Windows 는 Git Bash(Claude Code 가 쓰는 것과 같은 것)를 고른다"""
    if not WIN:
        return 'bash'
    for env in ('CLAUDE_CODE_GIT_BASH_PATH', 'BRAIN_BASH'):
        v = os.environ.get(env)
        if v and os.path.isfile(v):
            return v
    found = shutil.which('bash')
    if found and 'system32' not in found.lower() and 'windowsapps' not in found.lower():
        return found
    for base in (os.environ.get('ProgramFiles', r'C:\Program Files'), os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'),
                 os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs')):
        for rel in (r'Git\bin\bash.exe', r'Git\usr\bin\bash.exe'):
            c = os.path.join(base, rel)
            if os.path.isfile(c):
                return c
    return 'bash'


def argv(args):
    """[bash 로 돌릴 명령] 첫 칸은 Git Bash, 절대경로 인자는 / 표기로(Windows 의 C:\\... 를 bash 가 그대로 받지 않게)"""
    out = [bash()] + list(args[1:]) if args and args[0] == 'bash' else list(args)
    if WIN:
        out = out[:1] + [norm(a) if isinstance(a, str) and is_abs(a) else a for a in out[1:]]
    return out


def detach_kw():
    """[세션과 무관한 프로세스로 띄울 Popen 인자] POSIX 는 새 세션, Windows 는 분리된 새 프로세스 그룹"""
    if WIN:
        return {'creationflags': getattr(subprocess, 'DETACHED_PROCESS', 0x8) | getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0x200),
                'close_fds': True}
    return {'start_new_session': True, 'close_fds': True}


def pid_alive(pid):
    """[프로세스가 살아 있나] Windows 에서 os.kill(pid, 0) 은 그 프로세스를 끝내 버리므로 쓰지 않는다"""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    if WIN:
        try:
            import ctypes
            k = ctypes.windll.kernel32
            h = k.OpenProcess(0x1000, False, pid)   # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                return False
            code = ctypes.c_ulong()
            ok = k.GetExitCodeProcess(h, ctypes.byref(code))
            k.CloseHandle(h)
            return bool(ok) and code.value == 259   # STILL_ACTIVE
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:   # 다른 사용자의 프로세스 - 살아 있다
        return True
    except OSError:
        return False


if __name__ == '__main__':
    a = sys.argv[1:]
    if a and a[0] == 'bash':
        print(bash())
    elif a and a[0] == 'norm' and len(a) > 1:
        print(norm(a[1]))
    else:
        print(__doc__)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""brain 지금 등록 - 그 폴더가 속한 프로젝트(위로 가장 가까운 git 루트, 없으면 그 폴더)를 해마에게 등록해 달라고 맡긴다.
밤 주기의 자동 등록(최근 7일 3세션, 요청 10개)을 기다리지 않는다. /claude-brain-register 와 앱의 '키우기' 버튼이 부른다.

사용법: register.py <폴더>     → 사람이 읽는 한 줄(brain 언어). 종료 코드 0 맡김, 3 이미 등록됨/대기 중, 2 거절, 1 오류
       register.py --json <폴더> → {"code", "message", "slug", "root", "id"}
등록 자체는 해마가 한다(registry 행, projects/<슬러그>/ 골격) - cortex 에 쓰는 것은 해마 하나다.
"""
import glob
import hashlib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BRAIN = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import plat  # noqa: E402
from cli_i18n import m  # noqa: E402

CX = os.environ.get('BRAIN_CORTEX') or os.path.join(BRAIN, 'cortex')
QUEUE = os.path.join(CX, '.hippocampus', 'queue')
PROC = os.path.join(CX, '.hippocampus', 'processing')


def registry():
    """[(루트, 슬러그)] registry.md 의 표 행"""
    rows = []
    try:
        lines = open(os.path.join(CX, 'registry.md'), encoding='utf-8', errors='replace').read().splitlines()
    except OSError:
        return rows
    for l in lines:
        c = [x.strip() for x in l.strip().strip('|').split('|')]
        if len(c) >= 2 and plat.is_abs(c[0]):
            rows.append((plat.norm(c[0]), c[1]))
    return rows


def slug_of(root, taken):
    """[슬러그] 폴더 이름을 영어 소문자와 하이픈으로. 남는 글자가 없으면(예: 한글 이름) project-<해시>. 겹치면 -2, -3"""
    base = re.sub(r'[^a-z0-9-]+', '-', os.path.basename(root.rstrip('/')).lower()).strip('-')[:40]
    if not base:
        base = 'project-' + hashlib.sha1(root.encode('utf-8')).hexdigest()[:6]
    s, i = base, 2
    while s in taken:
        s, i = '%s-%d' % (base, i), i + 1
    return s


def pending(root):
    """[같은 루트의 등록이 큐에 있나]"""
    for d in (QUEUE, PROC):
        for p in glob.glob(os.path.join(d, '*.json')):
            try:
                r = json.load(open(p, encoding='utf-8'))
            except (OSError, ValueError):
                continue
            if isinstance(r, dict) and r.get('mode') == 'register' and plat.key(r.get('project_root') or '') == plat.key(root):
                return True
    return False


def register(path):
    """[등록 맡기기] (code, message, slug, root, id)"""
    p = plat.norm(os.path.abspath(os.path.expanduser(path or '.')))
    if not os.path.isdir(p):
        return 2, m('rg.nodir', p), '', p, ''
    home = plat.key(os.path.expanduser('~'))
    cfg = plat.key(os.environ.get('CLAUDE_CONFIG_DIR') or os.path.join(os.path.expanduser('~'), '.claude'))
    if plat.under(BRAIN, p) or plat.under(os.path.realpath(BRAIN), p) or plat.under(cfg, p):
        return 2, m('rg.self'), '', p, ''
    root = plat.git_root(p) or p
    if plat.key(root) == home or os.path.dirname(root.rstrip('/')) == root.rstrip('/') or re.match(r'^[A-Za-z]:/?$', root) or root == '/':
        return 2, m('rg.home'), '', root, ''
    rows = registry()
    for r, s in rows:
        if plat.under(r, root) or plat.under(root, r):
            return 3, m('rg.already', s, r), s, r, ''
    if pending(root):
        return 3, m('rg.pending'), '', root, ''
    slug = slug_of(root, {s for _, s in rows})
    req = {'mode': 'register', 'project_root': root, 'slug': slug, 'stack': '?', 'caller': 'brain-register',
           'payload': {'auto': True, 'reason': '사용자가 직접 등록을 요청했다(/claude-brain-register 또는 brain 앱)',
                       'instruction': '스택과 버전, 컨벤션 문서 위치는 프로젝트 파일(ProjectSettings/ProjectVersion.txt, package.json, CLAUDE.md 등)에서 확인한다. 확인이 안 되는 칸은 ? 로 둔다.'}}
    os.makedirs(os.path.join(CX, '.hippocampus'), exist_ok=True)
    rp = os.path.join(CX, '.hippocampus', 'register-%d.json' % os.getpid())
    with open(rp, 'w', encoding='utf-8') as f:
        json.dump(req, f, ensure_ascii=False, indent=1)
    try:
        out = subprocess.run(plat.argv(['bash', os.path.join(HERE, 'hippocampus-enqueue.sh'), rp]), capture_output=True, timeout=20,
                             env=dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8'))
        text = out.stdout.decode('utf-8', 'replace')
    except (OSError, subprocess.SubprocessError) as e:
        text = str(e)
        out = None
    finally:
        try:
            os.remove(rp)
        except OSError:
            pass
    qid = re.search(r'\d{8}T\d{6}Z-[A-Za-z0-9_-]+', text)
    if not out or out.returncode != 0 or not qid:
        return 1, m('rg.fail', text.strip()[:200]), slug, root, ''
    return 0, m('rg.queued', slug, root), slug, root, qid.group(0)


def main():
    a = sys.argv[1:]
    as_json = bool(a) and a[0] == '--json'
    if as_json:
        a = a[1:]
    code, msg, slug, root, qid = register(a[0] if a else os.getcwd())
    if as_json:
        out = json.dumps({'code': code, 'message': msg, 'slug': slug, 'root': root, 'id': qid}, ensure_ascii=False)
    else:
        out = msg
    sys.stdout.buffer.write((out + '\n').encode('utf-8'))
    return code


if __name__ == '__main__':
    sys.exit(main())

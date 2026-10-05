#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""brain 백업과 옮기기 - 기억(cortex)과 성격(persona)을 zip 하나로 묶고, 다른 컴퓨터에서 그 zip 으로 되살린다.

사용법:
  backup.py make [폴더]        zip 을 만든다(기본: ~/Downloads, 없으면 홈). 경로를 출력한다. /claude-brain-backup, 앱 설정이 부른다
  backup.py restore <zip>     지금 기억을 .active/before-restore-<시각>/ 로 옮겨 두고 zip 의 기억으로 바꾼다

들어가는 것: cortex/ (해마 런타임 상태 .hippocampus 는 빼고 기억 강도 strength.json 만), persona/, .active/brain-born, manifest.json.
설정(.active/config: 언어, 모델)은 기기마다 다를 수 있어 넣지 않는다.
되살릴 때 홈 폴더가 다르면(사용자 이름이 다른 컴퓨터) registry 의 프로젝트 경로 앞부분을 이 컴퓨터의 홈으로 바꾼다.
해마가 일하는 중이면 되살리지 않는다(기억 저장소에 동시에 쓰게 된다).
"""
import json
import os
import shutil
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
BRAIN = os.path.dirname(HERE)
CX = os.path.join(BRAIN, 'cortex')
ACTIVE = os.path.join(BRAIN, '.active')
PERSONA = os.environ.get('BRAIN_PERSONA_DIR') or os.path.join(BRAIN, 'persona')
sys.path.insert(0, HERE)
import plat  # noqa: E402
from cli_i18n import m  # noqa: E402

MAX_BYTES = 500 * 1024 * 1024   # 되살릴 때 풀린 크기 상한 - 망가진 zip 이 디스크를 채우지 않게


def say(text):
    sys.stdout.buffer.write((text + '\n').encode('utf-8'))
    sys.stdout.buffer.flush()


def out_dir(d=None):
    if d:
        return d
    dl = os.path.join(os.path.expanduser('~'), 'Downloads')
    return dl if os.path.isdir(dl) else os.path.expanduser('~')


def make(d=None):
    """[zip 만들기] 만든 파일 경로와 기억 파일 수"""
    d = out_dir(d)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, 'brain-backup-%s.zip' % time.strftime('%Y%m%d-%H%M%S'))
    n = 0
    tmp = path + '.part'
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(CX):
            rel_root = os.path.relpath(root, BRAIN)
            if '.hippocampus' in rel_root.replace('\\', '/').split('/'):
                continue
            dirs[:] = [x for x in dirs if x != '.hippocampus']
            for f in files:
                p = os.path.join(root, f)
                z.write(p, os.path.relpath(p, BRAIN).replace('\\', '/'))
                n += f.endswith('.md')
        st = os.path.join(CX, '.hippocampus', 'strength.json')
        if os.path.isfile(st):
            z.write(st, 'cortex/.hippocampus/strength.json')
        if os.path.isdir(PERSONA):
            for f in sorted(os.listdir(PERSONA)):
                if f.endswith('.json'):
                    z.write(os.path.join(PERSONA, f), 'persona/' + f)
        born = os.path.join(ACTIVE, 'brain-born')
        if os.path.isfile(born):
            z.write(born, '.active/brain-born')
        z.writestr('manifest.json', json.dumps({'brain_backup': 1, 'created': time.strftime('%Y-%m-%dT%H:%M:%S'),
                                                'home': plat.norm(os.path.expanduser('~')), 'brain': plat.norm(BRAIN),
                                                'memories': n}, ensure_ascii=False, indent=1))
    os.replace(tmp, path)
    return path, n


def daemon_busy():
    try:
        pid = open(os.path.join(CX, '.hippocampus', 'lock', 'pid')).read().strip()
    except OSError:
        return False
    return plat.pid_alive(pid)


def restore(zpath):
    """[되살리기] 종료 코드"""
    if not os.path.isfile(zpath):
        say(m('bk.nofile', zpath))
        return 2
    try:
        z = zipfile.ZipFile(zpath)
        man = json.loads(z.read('manifest.json').decode('utf-8'))
        assert isinstance(man, dict) and man.get('brain_backup') == 1
    except Exception:
        say(m('bk.notbackup', zpath))
        return 2
    names = z.namelist()
    if sum(i.file_size for i in z.infolist()) > MAX_BYTES:
        say(m('bk.notbackup', zpath))
        return 2
    for n in names:   # zip 안의 경로가 기억 저장소 밖으로 나가지 않는지 (../, 절대경로)
        q = n.replace('\\', '/')
        if q.startswith('/') or '..' in q.split('/') or ':' in q.split('/')[0] or not (q.startswith(('cortex/', 'persona/', '.active/brain-born')) or q == 'manifest.json'):
            say(m('bk.notbackup', zpath))
            return 2
    if daemon_busy():
        say(m('bk.busy'))
        return 3
    keep = os.path.join(ACTIVE, 'before-restore-%s' % time.strftime('%Y%m%d-%H%M%S'))
    os.makedirs(keep, exist_ok=True)
    if os.path.isdir(CX):
        hc = os.path.join(CX, '.hippocampus')
        shutil.move(CX, os.path.join(keep, 'cortex'))
        os.makedirs(CX, exist_ok=True)
        if os.path.isdir(os.path.join(keep, 'cortex', '.hippocampus')):   # 큐, 로그 같은 런타임 상태는 이 기기 것을 그대로 쓴다
            shutil.move(os.path.join(keep, 'cortex', '.hippocampus'), hc)
    if os.path.isdir(PERSONA):
        shutil.copytree(PERSONA, os.path.join(keep, 'persona'))
    n = 0
    for info in z.infolist():
        q = info.filename.replace('\\', '/')
        if q.endswith('/') or q == 'manifest.json':
            continue
        if q.startswith('persona/'):
            t = os.path.join(PERSONA, q[len('persona/'):])
        else:
            t = os.path.join(BRAIN, *q.split('/'))
        os.makedirs(os.path.dirname(t), exist_ok=True)
        with z.open(info) as src, open(t, 'wb') as dst:
            shutil.copyfileobj(src, dst)
        n += q.startswith('cortex/') and q.endswith('.md')
    # 홈 폴더가 다르면 registry 의 프로젝트 경로를 이 컴퓨터의 홈으로 옮긴다
    old_home, new_home = plat.norm(man.get('home') or ''), plat.norm(os.path.expanduser('~'))
    reg = os.path.join(CX, 'registry.md')
    moved = 0
    missing = []
    if os.path.isfile(reg):
        lines = open(reg, encoding='utf-8', errors='replace').read().split('\n')
        for i, l in enumerate(lines):
            if not l.startswith('|'):
                continue
            c = l.split('|')
            if len(c) < 3:
                continue
            p = c[1].strip().strip('`')
            if not plat.is_abs(p):
                continue
            if old_home and plat.key(old_home) != plat.key(new_home) and plat.under(old_home, p):
                np = new_home + plat.norm(p)[len(old_home):]
                c[1] = c[1].replace(p, np)
                lines[i] = '|'.join(c)
                p = np
                moved += 1
            if not os.path.isdir(p):
                missing.append(p)
        with open(reg, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(lines))
    shutil.rmtree(os.path.join(ACTIVE, 'cache'), ignore_errors=True)   # 옛 기억의 검색 캐시
    say(m('bk.restored', n, plat.norm(keep)))
    if moved:
        say(m('bk.moved', moved, old_home, new_home))
    if missing:
        say(m('bk.missing', ', '.join(missing[:6])))
    return 0


def main():
    a = sys.argv[1:]
    if a and a[0] == 'make':
        path, n = make(a[1] if len(a) > 1 else None)
        say(m('bk.made', n, plat.norm(path)))
        return 0
    if len(a) >= 2 and a[0] == 'restore':
        return restore(os.path.abspath(os.path.expanduser(a[1])))
    say(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""brain 망각 - 오래 안 쓴 기억을 지우지 않고 숨긴다(잠재화). 다시 쓰이면 되살린다. sleep.sh 가 밤마다 부른다.

사용법: forget.py [--days 45] [--salient-days 120] [--dry-run]
  기억 하나 = 검색 대상 인덱스 줄(레이어 루트 INDEX.md, *index*.md)의 첫 링크가 가리키는 본문.
  마지막 사용일 = max(떠올림,열람,검색 히트 마지막 날(.hippocampus/strength.json), 본문 수정일, brain 설치일).
  오늘 - 마지막 사용일 이 기준을 넘으면 그 본문을 첫 링크로 가리키는 인덱스 줄을 전부 <레이어>/dormant.md 로 옮긴다.
    - 본문 파일은 그대로 남는다. dormant.md 는 이름에 index 가 없어 자동 떠올림(thalamus)에 안 걸리고,
      의식적 검색(recall.sh 의 본문 대체 검색)으로는 여전히 찾힌다 - 사람의 잠재 기억과 같다.
    - 두드러진 기억(본문에 '사용자 결정', '함정', '사고', '손실', '파괴')은 salient-days 를 쓴다(아팠던 기억이 오래 가듯).
  dormant.md 에 있는 기억이 숨은 뒤 다시 쓰였으면(강도 기록의 마지막 날이 숨긴 날보다 뒤) 원래 인덱스 파일 끝으로 줄을 돌려놓는다.
표준 출력 끝 줄: '# 잠재화 n, 되살림 m'. 인덱스를 고치므로 hippocampus 데몬이 쉬고 있을 때만 부른다(sleep.sh 가 확인한다).
"""
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BRAIN = os.path.dirname(HERE)
CX = os.path.join(BRAIN, 'cortex')
ACTIVE = os.path.join(BRAIN, '.active')
FIRST_MD = re.compile(r'\]\(([^() ]+\.md)\)')
TAG_RE = re.compile(r' <!-- dormant (\S+) (\d{4}-\d{2}-\d{2}) -->$')
SALIENT_RE = re.compile(r'(사용자 결정|함정|사고|손실|파괴)')
DORMANT_HEAD = ('# 잠재 기억 - 오래 안 쓰여 자동 떠올림에서 빠진 기억\n\n'
                '> forget.py 가 옮긴 인덱스 줄이다. 본문은 그대로 있고, 다시 쓰이면 원래 인덱스로 돌아간다. 줄 끝 주석 = 원래 파일과 숨긴 날.\n\n')


def arg(a, k, d):
    return a[a.index(k) + 1] if k in a else d


def layers():
    out = ['common'] if os.path.isdir(os.path.join(CX, 'common')) else []
    for top in ('stacks', 'projects'):
        d = os.path.join(CX, top)
        if os.path.isdir(d):
            out += ['%s/%s' % (top, x) for x in sorted(os.listdir(d)) if os.path.isdir(os.path.join(d, x))]
    return out


def index_files(lay):
    d = os.path.join(CX, lay)
    fs = sorted(f for f in os.listdir(d) if f.endswith('.md') and (f == 'INDEX.md' or 'index' in f))
    return fs


def born():
    p = os.path.join(ACTIVE, 'brain-born')
    try:
        return open(p).read().strip()[:10]
    except OSError:
        os.makedirs(ACTIVE, exist_ok=True)
        d = datetime.date.today().isoformat()
        with open(p, 'w') as f:
            f.write(d + '\n')
        return d


def main():
    a = sys.argv[1:]
    days = int(arg(a, '--days', '45'))
    sdays = int(arg(a, '--salient-days', '120'))
    dry = '--dry-run' in a
    today = datetime.date.today()
    base = born()
    strength = {}
    try:
        strength = json.load(open(os.path.join(CX, '.hippocampus', 'strength.json'), encoding='utf-8')).get('memories', {})
    except (OSError, ValueError):
        pass
    hid = back = 0
    for lay in layers():
        root = os.path.join(CX, lay)
        dp = os.path.join(root, 'dormant.md')
        dorm = open(dp, encoding='utf-8').read().splitlines() if os.path.isfile(dp) else []
        # 1. 되살리기
        keep_dorm = []
        restore = {}
        for line in dorm:
            m = TAG_RE.search(line)
            lk = FIRST_MD.search(line)
            if not (m and lk):
                keep_dorm.append(line)
                continue
            rel = os.path.normpath(os.path.join(lay, lk.group(1)))
            bp = os.path.join(CX, rel)
            if not os.path.isfile(bp):
                continue   # 본문이 아카이브로 갔다 - 완전히 잊은 기억이라 잠재 줄도 뺀다
            last = (strength.get(rel) or {}).get('last', '')
            mt = datetime.date.fromtimestamp(os.path.getmtime(bp)).isoformat()
            if (last and last > m.group(2)) or mt > m.group(2):
                restore.setdefault(m.group(1), []).append(TAG_RE.sub('', line))   # 다시 쓰였거나 본문이 고쳐졌다
            else:
                keep_dorm.append(line)
        # 2. 잠재화 대상
        moves = {}
        for f in index_files(lay):
            p = os.path.join(root, f)
            for line in open(p, encoding='utf-8').read().splitlines():
                lk = FIRST_MD.search(line)
                if not lk or not line.lstrip().startswith(('-', '*')):
                    continue
                rel = os.path.normpath(os.path.join(lay, lk.group(1)))
                bp = os.path.join(CX, rel)
                if '/lessons/' not in '/' + rel or not os.path.isfile(bp):
                    continue
                st = strength.get(rel) or {}
                mt = datetime.date.fromtimestamp(os.path.getmtime(bp)).isoformat()
                last = max(st.get('last', ''), mt, base)
                body = open(bp, encoding='utf-8', errors='replace').read(4000)
                limit = sdays if SALIENT_RE.search(body) else days
                if (today - datetime.date.fromisoformat(last)).days > limit:
                    moves.setdefault(f, set()).add(rel)
        if dry:
            for f, rels in moves.items():
                for r in sorted(rels):
                    print('잠재화 후보: %s (%s)' % (r, f))
            for f, ls in restore.items():
                print('되살림 후보: %d줄 -> %s' % (len(ls), f))
            hid += sum(len(v) for v in moves.values())
            back += sum(len(v) for v in restore.values())
            continue
        stamp = today.isoformat()
        for f in set(list(moves) + list(restore)):
            p = os.path.join(root, f)
            lines = open(p, encoding='utf-8').read().splitlines()
            out = []
            for line in lines:
                lk = FIRST_MD.search(line)
                rel = os.path.normpath(os.path.join(lay, lk.group(1))) if lk else None
                if rel and rel in moves.get(f, ()) and line.lstrip().startswith(('-', '*')):
                    keep_dorm.append('%s <!-- dormant %s %s -->' % (line, f, stamp))
                    hid += 1
                else:
                    out.append(line)
            if f in restore:
                out += restore[f]
                back += len(restore[f])
            tmp = p + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as w:
                w.write('\n'.join(out) + '\n')
            os.replace(tmp, p)
        body_lines = [l for l in keep_dorm if TAG_RE.search(l)]
        if body_lines or os.path.isfile(dp):
            with open(dp + '.tmp', 'w', encoding='utf-8') as w:
                w.write(DORMANT_HEAD + '\n'.join(body_lines) + ('\n' if body_lines else ''))
            os.replace(dp + '.tmp', dp)
    print('# 잠재화 %d, 되살림 %d%s' % (hid, back, ' (dry-run)' if dry else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())

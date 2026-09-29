#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""brain 기억 강도와 검색 실패 집계 - sleep.sh 가 밤마다 한 번 돌린다.

사용법: sleep-stats.py [--misses-out <파일>]
  cortex/.hippocampus/strength.json 을 다시 쓴다: {본문 상대 경로: {shown, opened, grepped, last}} (떠올림, 열람, nb-grep 히트 횟수와 마지막 날짜)
  --misses-out: 검색 실패 뒤 곧 찾은 기억 짝(별칭 후보)을 markdown 으로 쓴다. 표준 출력 끝 줄: '# 강도 n개, 실패 짝 m개'
기억 강도는 망각(forget.py)과 hippocampus 정비의 판단 재료다 - 오래 안 떠오른 기억도 사용자 결정과 함정은 남긴다.
"""
import collections
import datetime
import glob
import json
import os
import re
import sys

LINE_RE = re.compile(r'^#(\d+) (\S+) (\S+) name="([^"]*)" hits=(\d+) files="([^"]*)"')


def arg(a, k, d=None):
    return a[a.index(k) + 1] if k in a else d


def main():
    a = sys.argv[1:]
    brain = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    nb = os.path.join(brain, 'cortex')
    active = os.path.join(brain, '.active')
    by_base = collections.defaultdict(list)
    for dp, dn, fn in os.walk(nb):
        dn[:] = [d for d in dn if d not in ('_archive', '.hippocampus', 'scripts')]
        for f in fn:
            if f.endswith('.md'):
                by_base[f].append(os.path.relpath(os.path.join(dp, f), nb))
    st = collections.defaultdict(lambda: {'shown': 0, 'opened': 0, 'grepped': 0, 'last': ''})

    def bump(rel, key, day):
        s = st[rel]
        s[key] += 1
        if day > s['last']:
            s['last'] = day

    try:
        for line in open(os.path.join(active, 'recall.log'), encoding='utf-8'):
            try:
                d = json.loads(line)
            except ValueError:
                continue
            day = datetime.datetime.fromtimestamp(d.get('t', 0)).strftime('%Y-%m-%d')
            if d.get('ev') == 'open' and d.get('body'):
                bump(d['body'], 'opened', day)
            for rel in d.get('shown') or []:
                bump(rel, 'shown', day)
    except OSError:
        pass
    pairs = collections.Counter()
    for lf in glob.glob(os.path.join(active, '*.checks.log')) + glob.glob(os.path.join(active, 'legacy', '*.checks.log')):
        rows = []
        for line in open(lf, encoding='utf-8', errors='replace'):
            m = LINE_RE.match(line.strip())
            if m:
                rows.append((m.group(2), m.group(3), m.group(4), int(m.group(5)), [x for x in m.group(6).split(',') if x]))
        for i, (day, tm, name, hits, files) in enumerate(rows):
            for f in files:
                cands = by_base.get(os.path.basename(f), [])
                if len(cands) == 1:
                    bump(cands[0], 'grepped', day)
            if hits != 0 or len(name) < 3:
                continue
            # 실패 뒤 같은 대조 기록 안 가까운 성공(히트 1~3개)을 짝으로 본다 - 같은 것을 다른 말로 찾았을 가능성
            for day2, tm2, name2, hits2, files2 in rows[i + 1:i + 6]:
                if 1 <= hits2 <= 3 and name2.lower() != name.lower() and day2 == day:
                    pairs[(name, name2, ','.join(os.path.basename(x) for x in files2))] += 1
                    break
    out = {k: v for k, v in sorted(st.items())}
    cur = os.path.join(nb, '.hippocampus')
    os.makedirs(cur, exist_ok=True)
    tmp = os.path.join(cur, 'strength.json.tmp')
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump({'generated': datetime.date.today().isoformat(), 'memories': out}, f, ensure_ascii=False, indent=0)
    os.replace(tmp, os.path.join(cur, 'strength.json'))
    mo = arg(a, '--misses-out')
    if mo:
        with open(mo, 'w', encoding='utf-8') as f:
            f.write('# 검색 실패 뒤 곧 찾은 짝 (별칭,단서 후보) - %s\n\n' % datetime.date.today().isoformat())
            f.write('세션이 앞 이름으로 찾아 히트 0 이었고, 몇 줄 안에 뒤 이름으로 찾아 히트가 났다. 같은 것을 다른 말로 찾았을 수 있다(우연일 수도 있다).\n\n')
            for (a1, a2, fl), n in pairs.most_common(80):
                f.write('- `%s` -> `%s` (%s) x%d\n' % (a1, a2, fl, n))
    print('# 강도 %d개, 실패 짝 %d개' % (len(out), len(pairs)))
    return 0


if __name__ == '__main__':
    sys.exit(main())

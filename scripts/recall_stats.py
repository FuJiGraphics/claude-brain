#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""brain 떠올림 기록 집계 - 밤 잠(sleep-stats.py)과 앱(editor/server.py)이 같은 정의로 센다.

기록은 실시간이다: thalamus 훅이 .active/recall.log 에 떠올림(shown)과 본문 열람(open)을 한 줄씩 쓰고,
nb-grep 은 .active/*.checks.log 에 검색 히트를 쓴다. 여기서는 그 기록을 다시 셀 뿐이다.
collect() -> {'memories': {본문 상대 경로: {shown, opened, grepped, last}},
              'pairs': Counter{(실패 이름, 찾은 이름, 파일들): 횟수},
              'hits': {본문 상대 경로: [떠오른 세션 수, 그 뒤 같은 세션이 연 수]}}
"""
import collections
import datetime
import glob
import json
import os
import re

LINE_RE = re.compile(r'^#(\d+) (\S+) (\S+) name="([^"]*)" hits=(\d+) files="([^"]*)"')
# 명령(cat, sed, grep)으로 연 본문도 열람으로 세기 시작한 때(2026-10-07 02:30) - 그 전 떠올림은 Read 로 연 것만 남아(실측 0건) 적중률에서 뺀다
OPENS_FROM = 1791307832


def collect(nb, active, hit_since=''):
    """[기록 전체 집계]
    - hit_since: 이 날짜(YYYY-MM-DD) 이후 떠오른 것만 적중에 센다. OPENS_FROM 전 떠올림은 늘 뺀다
    - 적중 = 떠오른 기억을 같은 세션이 그 뒤에 열었다. 요지만 보고 충분했으면 안 열므로 낮다고 틀린 떠올림은 아니다
    """
    by_base = collections.defaultdict(list)
    for dp, dn, fn in os.walk(nb):
        dn[:] = [d for d in dn if d not in ('_archive', '.hippocampus', 'scripts')]
        for f in fn:
            if f.endswith('.md'):
                by_base[f].append(os.path.relpath(os.path.join(dp, f), nb))
    st = collections.defaultdict(lambda: {'shown': 0, 'opened': 0, 'grepped': 0, 'last': ''})
    shown_in = {}   # (세션, 본문) -> 그 뒤에 열었나

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
            sid = d.get('sid') or ''
            if d.get('ev') == 'open' and d.get('body'):
                bump(d['body'], 'opened', day)
                if shown_in.get((sid, d['body'])) is False:
                    shown_in[(sid, d['body'])] = True
            for rel in d.get('shown') or []:
                bump(rel, 'shown', day)
                if day >= hit_since and d.get('t', 0) >= OPENS_FROM and (sid, rel) not in shown_in:
                    shown_in[(sid, rel)] = False
    except OSError:
        pass
    hits = collections.defaultdict(lambda: [0, 0])
    for (_, rel), opened in shown_in.items():
        hits[rel][0] += 1
        hits[rel][1] += opened
    pairs = collections.Counter()
    for lf in glob.glob(os.path.join(active, '*.checks.log')) + glob.glob(os.path.join(active, 'legacy', '*.checks.log')):
        rows = []
        for line in open(lf, encoding='utf-8', errors='replace'):
            m = LINE_RE.match(line.strip())
            if m:
                rows.append((m.group(2), m.group(3), m.group(4), int(m.group(5)), [x for x in m.group(6).split(',') if x]))
        for i, (day, tm, name, hits_n, files) in enumerate(rows):
            for f in files:
                cands = by_base.get(os.path.basename(f), [])
                if len(cands) == 1:
                    bump(cands[0], 'grepped', day)
            if hits_n != 0 or len(name) < 3:
                continue
            # 실패 뒤 같은 대조 기록 안 가까운 성공(히트 1~3개)을 짝으로 본다 - 같은 것을 다른 말로 찾았을 가능성
            for day2, tm2, name2, hits2, files2 in rows[i + 1:i + 6]:
                if 1 <= hits2 <= 3 and name2.lower() != name.lower() and day2 == day:
                    pairs[(name, name2, ','.join(os.path.basename(x) for x in files2))] += 1
                    break
    return {'memories': {k: v for k, v in sorted(st.items())}, 'pairs': pairs, 'hits': dict(hits)}

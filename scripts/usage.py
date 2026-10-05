#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""brain 사용량 - brain 이 뒤에서 부른 claude -p 의 횟수, 토큰, 비용을 남기고 모은다.

해마(hippocampus 데몬)와 앱(말풍선, 쉬운 말 풀이, 물어보기)의 claude -p --output-format json 결과에서
total_cost_usd 와 usage 를 한 줄씩 <brain>/.active/usage.jsonl 에 적는다. 비용은 Claude Code 가 API 요금으로 계산한 값이라
구독 요금제(Pro, Max)에서는 실제 청구액이 아니라 쓴 양의 기준이다.

명령행:
  usage.py record <src> <what> <claude 결과 JSON 파일>   한 줄 남기기 (src: hippo | app)
  usage.py line                                          /claude-brain-status 의 한 줄 (이번 주)
  usage.py prune [일]                                     오래된 줄 정리 (기본 120일)
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BRAIN = os.path.dirname(HERE)
ACTIVE = os.environ.get('BRAIN_ACTIVE') or os.path.join(BRAIN, '.active')


def path(active=None):
    return os.path.join(active or ACTIVE, 'usage.jsonl')


def record(src, what, d, active=None):
    """[한 줄 남기기] d 는 claude -p --output-format json 결과(dict). 실패해도 조용히 넘어간다 - 사용량 기록이 일을 막지 않는다"""
    if not isinstance(d, dict):
        return
    u = d.get('usage') if isinstance(d.get('usage'), dict) else {}
    num = lambda v: v if isinstance(v, (int, float)) and v == v else 0   # noqa: E731
    row = {'t': int(time.time()), 'src': str(src)[:12], 'what': str(what)[:24],
           'cost': round(num(d.get('total_cost_usd')), 6),
           'tin': int(num(u.get('input_tokens')) + num(u.get('cache_creation_input_tokens')) + num(u.get('cache_read_input_tokens'))),
           'tout': int(num(u.get('output_tokens'))), 'turns': int(num(d.get('num_turns')))}
    try:
        os.makedirs(active or ACTIVE, exist_ok=True)
        with open(path(active), 'a', encoding='utf-8') as f:
            f.write(json.dumps(row) + '\n')
    except OSError:
        pass


def rows(days, active=None):
    since = time.time() - days * 86400
    out = []
    try:
        with open(path(active), encoding='utf-8', errors='replace') as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if isinstance(r, dict) and isinstance(r.get('t'), (int, float)) and r['t'] >= since:
                    out.append(r)
    except OSError:
        pass
    return out


def summary(days, active=None):
    """[합계] {'runs', 'cost', 'tin', 'tout', 'hippo': 횟수, 'app': 횟수, 'days'}"""
    rs = rows(days, active)
    num = lambda v: v if isinstance(v, (int, float)) else 0   # noqa: E731
    return {'days': days, 'runs': len(rs), 'cost': round(sum(num(r.get('cost')) for r in rs), 4),
            'tin': sum(num(r.get('tin')) for r in rs), 'tout': sum(num(r.get('tout')) for r in rs),
            'hippo': sum(1 for r in rs if r.get('src') == 'hippo'), 'app': sum(1 for r in rs if r.get('src') == 'app')}


def prune(keep_days=120, active=None):
    keep = rows(keep_days, active)
    try:
        tmp = path(active) + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            for r in keep:
                f.write(json.dumps(r) + '\n')
        os.replace(tmp, path(active))
    except OSError:
        pass


def main():
    a = sys.argv[1:]
    cmd = a[0] if a else ''
    if cmd == 'record' and len(a) >= 4:
        try:
            d = json.load(open(a[3], encoding='utf-8', errors='replace'))
        except (OSError, ValueError):
            return 0
        record(a[1], a[2], d)
        return 0
    if cmd == 'line':
        sys.path.insert(0, HERE)
        from cli_i18n import m
        s = summary(7)
        text = m('us.week', s['hippo'], s['app'], '%.2f' % s['cost']) if s['runs'] else m('us.none')
        sys.stdout.buffer.write((text + '\n').encode('utf-8'))
        return 0
    if cmd == 'prune':
        prune(int(a[1]) if len(a) > 1 and a[1].isdigit() else 120)
        return 0
    sys.stdout.write(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main())

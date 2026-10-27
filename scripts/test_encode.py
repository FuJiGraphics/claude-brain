#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""재생 요약(replay.digest) 시험 - 합성 대화록으로 에러 단서, 종료 코드 0 에러, 같은 명령 성공 기록을 본다

사용: python3 scripts/test_encode.py
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import replay  # noqa: E402

ROOT = '/work/ledger'
TS = '2026-10-28T10:%02d:00Z'


def transcript(lines):
    """[합성 대화록] (종류, 값) 목록 → jsonl 경로. 종류: user(글), bash(id, 명령), result(id, 글, is_error, stdout, stderr)"""
    out = []
    for k, (kind, v) in enumerate(lines):
        base = {'timestamp': TS % k, 'cwd': ROOT, 'sessionId': 's1'}
        if kind == 'user':
            out.append(dict(base, type='user', message={'role': 'user', 'content': v}))
        elif kind == 'bash':
            tid, cmd = v
            out.append(dict(base, type='assistant', message={'role': 'assistant', 'content': [
                {'type': 'tool_use', 'id': tid, 'name': 'Bash', 'input': {'command': cmd}}]}))
        elif kind == 'text':
            out.append(dict(base, type='assistant', message={'role': 'assistant', 'content': [{'type': 'text', 'text': v}]}))
        elif kind == 'result':
            tid, text, err, so, se = v
            d = dict(base, type='user', message={'role': 'user', 'content': [
                {'type': 'tool_result', 'tool_use_id': tid, 'content': text, 'is_error': err}]})
            if not err:
                d['toolUseResult'] = {'stdout': so, 'stderr': se, 'interrupted': False}
            out.append(d)
    f = tempfile.NamedTemporaryFile('w', suffix='.jsonl', delete=False, encoding='utf-8')
    for d in out:
        f.write(json.dumps(d, ensure_ascii=False) + '\n')
    f.close()
    return f.name


TB = ("Traceback (most recent call last):\n  File \"/work/ledger/ledger/rates.py\", line 2, in <module>\n"
      "ModuleNotFoundError: No module named 'ledger.gen.rates'")
CASES = []


def case(name):
    def deco(fn):
        CASES.append((name, fn))
        return fn
    return deco


@case('실패한 명령(is_error)에 단서가 붙고, 같은 명령이 뒤에 성공하면 그 사실이 붙는다')
def _1():
    p = transcript([('user', '시험이 깨진다 고쳐 줘'), ('bash', ('t1', 'python3 -m unittest')),
                    ('result', ('t1', 'Exit code 1\n' + TB, True, '', '')),
                    ('bash', ('t2', 'python3 tools/build_rates.py --rounding half-even')), ('result', ('t2', 'ok', False, 'ok', '')),
                    ('bash', ('t3', 'python3 -m unittest')), ('result', ('t3', 'OK', False, '', 'Ran 3 tests\n\nOK'))])
    text, score, n, end = replay.digest(p, 'ledger', 0, ROOT)
    e = [l for l in text.splitlines() if ' E] ' in l]
    assert len(e) == 1, e
    assert '단서: ' in e[0] and 'ledger.gen.rates' in e[0], e[0]
    assert '같은 명령이 10:06 에 에러 없이 끝남' in e[0], e[0]
    assert n['도구 실패'] == 1


@case('종료 코드 0 인데 에러 형식인 출력은 E 로 잡되 점수에는 넣지 않는다')
def _2():
    p = transcript([('user', '확인해 줘'), ('bash', ('t1', 'python3 -m unittest 2>&1 | tail -5')),
                    ('result', ('t1', TB, False, TB, ''))])
    text, score, n, end = replay.digest(p, 'ledger', 0, ROOT)
    e = [l for l in text.splitlines() if ' E] ' in l]
    assert len(e) == 1 and '(종료 코드 0)' in e[0] and 'ledger.gen.rates' in e[0], text
    assert n['도구 실패'] == 0 and score == 0, (n, score)


@case('기억을 여는 명령(recall.sh, cortex)의 출력은 에러 문자열이 있어도 E 가 아니다')
def _3():
    p = transcript([('user', '찾아 줘'), ('bash', ('t1', 'bash ~/.claude/skills/brain/scripts/recall.sh ledger.gen.rates')),
                    ('result', ('t1', TB, False, TB, '')),
                    ('bash', ('t2', 'cat ~/.claude/skills/brain/cortex/projects/ledger/lessons/x.md')), ('result', ('t2', TB, False, TB, ''))])
    text, score, n, end = replay.digest(p, 'ledger', 0, ROOT)
    assert ' E] ' not in text, text


@case('성공 출력(grep 결과, 시험 통과)은 E 가 아니다')
def _4():
    p = transcript([('user', '찾아 줘'), ('bash', ('t1', 'grep -rn error src')),
                    ('result', ('t1', "src/x.ts:12:  throw new Error('bad')", False, "src/x.ts:12:  throw new Error('bad')", '')),
                    ('bash', ('t2', 'python3 -m unittest')), ('result', ('t2', 'OK', False, '', 'Ran 3 tests\n\nOK'))])
    text, score, n, end = replay.digest(p, 'ledger', 0, ROOT)
    assert ' E] ' not in text, text


@case('세션 표시(remember.sh --mark)는 M 줄로 실리고, 사람 요청이 없는 구간도 요약된다')
def _5():
    p = transcript([('bash', ('t1', 'bash ~/.claude/skills/brain/scripts/remember.sh --mark "gen 파일은 half-even 으로 만든다"')),
                    ('result', ('t1', '[brain-mark] gen 파일은 half-even 으로 만든다', False, '[brain-mark] gen 파일은 half-even 으로 만든다', ''))])
    r = replay.digest(p, 'ledger', 0, ROOT)
    assert r is not None, '요청 없는 표시 구간이 None'
    text, score, n, end = r
    assert n['표시'] == 1 and ' M] gen 파일은 half-even 으로 만든다' in text, text
    assert score == 0, score


@case('표시는 한 구간에 10개까지')
def _6():
    lines = [('user', '진행해')]
    for k in range(12):
        lines += [('bash', ('m%d' % k, 'remember.sh --mark x%d' % k)), ('result', ('m%d' % k, '[brain-mark] x%d' % k, False, '[brain-mark] x%d' % k, ''))]
    text, score, n, end = replay.digest(transcript(lines), 'ledger', 0, ROOT)
    assert n['표시'] == 10 and text.count(' M] ') == 10, n


def main():
    bad = 0
    for name, fn in CASES:
        try:
            fn()
            print('ok  ' + name)
        except AssertionError as e:
            bad += 1
            print('BAD ' + name + '\n    ' + str(e)[:400])
    print('실패 %d' % bad)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""thalamus 훅 전체 시험 - 임시 brain 과 기억 저장소를 만들어 실제 사건 순서대로 훅을 불러 본다(예외를 삼키지 않는다)

사용: python3 scripts/test_hook.py
- 훅은 실제로는 예외를 조용히 삼킨다(세션을 막지 않으려고). 그래서 함수가 빠지는 회귀를 단위 시험만으로는 놓친다 - 여기서는 hook() 을 직접 부른다
"""
import io
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    tmp = os.path.realpath(tempfile.mkdtemp(prefix='brain-hook-test-'))
    bad = 0
    try:
        brain = os.path.join(tmp, 'brain')
        shutil.copytree(HERE, os.path.join(brain, 'scripts'), ignore=shutil.ignore_patterns('__pycache__'))
        ws = os.path.join(tmp, 'proj')
        os.makedirs(os.path.join(ws, 'src'))
        cx = os.path.join(brain, 'cortex')
        os.makedirs(os.path.join(cx, 'projects', 'proj', 'lessons'))
        os.makedirs(os.path.join(cx, 'common'))
        open(os.path.join(cx, 'registry.md'), 'w', encoding='utf-8').write(
            '| 경로 | 슬러그 | 스택 | 버전 | 비고 |\n|---|---|---|---|---|\n| %s | proj | - | - | 시험 프로젝트 |\n' % ws)
        open(os.path.join(cx, 'projects', 'proj', 'INDEX.md'), 'w', encoding='utf-8').write(
            '# proj\n\n## lessons - [lessons-index.md](lessons-index.md)\n')
        open(os.path.join(cx, 'common', 'INDEX.md'), 'w', encoding='utf-8').write('# common\n')
        lessons = [('payment-gateway-retry-doubles-charge-2026-10-01', 'PaymentGateway 재시도가 결제를 두 번 한다', 'payment_gateway.py'),
                   ('ts-lib-generated-by-build-wasm', 'TS2307 ../gen/ts-lib.ts 는 build:wasm 이 만든다', 'type-check')]
        idx = ['# lessons', '']
        for slug, title, kw in lessons:
            open(os.path.join(cx, 'projects', 'proj', 'lessons', slug + '.md'), 'w', encoding='utf-8').write('# %s\n\n본문\n' % title)
            idx.append('- [%s](lessons/%s.md) - %s' % (title, slug, kw))
        open(os.path.join(cx, 'projects', 'proj', 'lessons-index.md'), 'w', encoding='utf-8').write('\n'.join(idx) + '\n')
        sys.path.insert(0, os.path.join(brain, 'scripts'))
        import thalamus as T

        def hook(ev):
            ev.setdefault('session_id', 's1')
            ev.setdefault('cwd', ws)
            sys.stdin = io.TextIOWrapper(io.BytesIO(json.dumps(ev).encode('utf-8')), encoding='utf-8')
            buf = io.StringIO()
            old = sys.stdout
            sys.stdout = buf
            try:
                T.hook()   # 예외가 그대로 올라온다
            finally:
                sys.stdout = old
                T._GATE.clear()
            o = buf.getvalue().strip()
            return json.loads(o.splitlines()[-1])['hookSpecificOutput'].get('additionalContext', '') if o else ''

        cases = [
            ('세션 시작: 지도와 recall.sh, remember.sh --mark 안내', {'hook_event_name': 'SessionStart', 'source': 'startup'},
             lambda o: 'recall.sh' in o and '--mark' in o),
            ('요청 글로는 떠올리지 않는다', {'hook_event_name': 'UserPromptSubmit', 'prompt': 'PaymentGateway 재시도 고쳐 줘'}, lambda o: o == ''),
            ('파일 열람: 키워드와 펼치기 명령', {'hook_event_name': 'PostToolUse', 'tool_name': 'Read',
                                        'tool_input': {'file_path': os.path.join(ws, 'src', 'PaymentGateway.py')}},
             lambda o: '`payment-gateway-retry-doubles-charge`' in o and 'recall.sh' in o),
            ('종료 코드 0 에러 출력: 오류 코드로 떠올림', {'hook_event_name': 'PostToolUse', 'tool_name': 'Bash',
                                              'tool_input': {'command': 'pnpm type-check | tail'},
                                              'tool_response': {'stdout': "src/type-check.ts(12,27): error TS2307: Cannot find module '../gen/ts-lib.ts'",
                                                                'stderr': '', 'interrupted': False}},
             lambda o: '`ts-lib-generated-by-build-wasm`' in o),
            ('recall.sh 로 펼침: 떠올림 없이 열람 기록', {'hook_event_name': 'PreToolUse', 'tool_name': 'Bash',
                                               'tool_input': {'command': 'bash %s/scripts/recall.sh payment-gateway-retry-doubles-charge' % brain}},
             lambda o: o == ''),
            ('서브에이전트 시작 줄', {'hook_event_name': 'SubagentStart', 'agent_id': 'a1', 'agent_type': 'general-purpose'},
             lambda o: 'recall.sh' in o and '--mark' not in o),
        ]
        for name, ev, ok in cases:
            try:
                out = hook(dict(ev))
                good = ok(out)
            except Exception as e:
                out, good = '%s: %s' % (e.__class__.__name__, e), False
            bad += not good
            print('%s %s%s' % ('ok ' if good else 'BAD', name, '' if good else '\n    ' + out[:300]))
        log = open(os.path.join(brain, '.active', 'recall.log'), encoding='utf-8').read()
        good = '"ev": "open"' in log and 'payment-gateway-retry-doubles-charge' in log
        bad += not good
        print('%s recall.sh 로 펼친 기억이 열람으로 기록됨' % ('ok ' if good else 'BAD'))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print('실패 %d' % bad)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())

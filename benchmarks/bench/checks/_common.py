"""채점 공통 - 작업 폴더에서 시험을 돌리고 결과를 JSON 한 줄로 낸다. 작업 폴더 밖에 있어 모델이 볼 수 없다"""
import hashlib
import json
import os
import subprocess
import sys

WS = sys.argv[1]
FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'fixture', 'project')
RESULTS = []


def check(name, ok, detail=''):
    RESULTS.append([name, bool(ok), str(detail)[:300]])


def sh(args, cwd=WS, timeout=120):
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout + p.stderr)


def same_as_fixture(rel):
    a = os.path.join(WS, rel)
    b = os.path.join(FIX, rel)
    if not os.path.isfile(a):
        return False
    return hashlib.sha256(open(a, 'rb').read()).digest() == hashlib.sha256(open(b, 'rb').read()).digest()


def unittest_ok():
    rc, out = sh([sys.executable, '-m', 'unittest'])
    check('python3 -m unittest 통과', rc == 0, out.strip().splitlines()[-1] if out.strip() else '')


def call(expr):
    """작업 폴더의 ledger 를 새 프로세스로 불러 식을 평가한다"""
    rc, out = sh([sys.executable, '-c', 'import json, ledger.money as m; print(json.dumps(%s))' % expr])
    if rc != 0:
        return ('ERR', out.strip().splitlines()[-1] if out.strip() else '')
    return (json.loads(out.strip().splitlines()[-1]), '')


def done():
    print(json.dumps({'pass': all(ok for _, ok, _ in RESULTS), 'checks': RESULTS}, ensure_ascii=False))

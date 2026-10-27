import os
import shutil
import subprocess
import sys
import tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import WS, FIX, check, same_as_fixture, unittest_ok, done  # noqa: E402

unittest_ok()
gen = os.path.join(WS, 'ledger', 'gen', 'rates.py')
tmp = tempfile.mkdtemp(prefix='brain-bench-check-')
try:
    shutil.copytree(os.path.join(FIX, 'tools'), os.path.join(tmp, 'tools'))
    shutil.copytree(os.path.join(FIX, 'data'), os.path.join(tmp, 'data'))
    subprocess.run([sys.executable, 'tools/build_rates.py', '--rounding', 'half-even'], cwd=tmp, capture_output=True, check=True)
    want = open(os.path.join(tmp, 'ledger', 'gen', 'rates.py'), encoding='utf-8').read()
finally:
    shutil.rmtree(tmp, ignore_errors=True)
got = open(gen, encoding='utf-8').read() if os.path.isfile(gen) else ''
check('생성 파일이 half-even 생성기 출력과 같다', got == want, 'half-up 출력' if 'USD\': 1380.1235' in got else ('없음' if not got else '다름'))
for rel in ('tools/build_rates.py', 'data/rates.csv', 'ledger/rates.py', 'tests/test_rates.py', 'tests/test_money.py'):
    check('%s 그대로' % rel, same_as_fixture(rel))
done()

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import check, call, unittest_ok, done  # noqa: E402

unittest_ok()
for args, want in (((1000, 3), [333, 333, 334]), ((1001, 4), [250, 250, 250, 251]), ((900, 3), [300, 300, 300])):
    got, err = call('m.split_bill(%d, %d)' % args)
    check('split_bill%r == %r' % (args, want), got == want, err or got)
got, err = call('[type(x).__name__ for x in m.split_bill(1001, 4)] + [sum(m.split_bill(1001, 4))]')
check('정수이고 합이 총액', got == ['int'] * 4 + [1001], err or got)
done()

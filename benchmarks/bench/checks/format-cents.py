import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import check, call, unittest_ok, done  # noqa: E402

unittest_ok()
for c, want in ((123456, '1,234.56'), (-5, '-0.05'), (0, '0.00'), (100000000, '1,000,000.00'), (-123456, '-1,234.56')):
    got, err = call('m.format_cents(%d)' % c)
    check('format_cents(%d) == %r' % (c, want), got == want, err or got)
done()

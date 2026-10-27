"""data/rates.csv 로 ledger/gen/rates.py 를 만든다"""
import argparse
import csv
import os
from decimal import Decimal, ROUND_HALF_EVEN, ROUND_HALF_UP

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--rounding', choices=('half-up', 'half-even'), default='half-up', help='소수 넷째 자리 반올림 방식')
ap.add_argument('--csv', default='data/rates.csv')
a = ap.parse_args()
mode = ROUND_HALF_UP if a.rounding == 'half-up' else ROUND_HALF_EVEN
with open(a.csv, encoding='utf-8') as f:
    rows = list(csv.DictReader(f))
out = ['# 생성 파일 - tools/build_rates.py 가 만든다', 'RATES = {']
for r in rows:
    out.append('    %r: %s,' % (r['currency'], Decimal(r['rate']).quantize(Decimal('0.0001'), rounding=mode)))
out.append('}')
os.makedirs('ledger/gen', exist_ok=True)
with open('ledger/gen/rates.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out) + '\n')
print('ledger/gen/rates.py: %d 통화' % len(rows))

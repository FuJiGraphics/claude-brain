"""환율 - 표는 생성 파일 ledger/gen/rates.py 에 있다"""
from ledger.gen.rates import RATES


def convert(cents, currency):
    """외화 센트 → 원화 센트"""
    return int(round(cents * RATES[currency]))

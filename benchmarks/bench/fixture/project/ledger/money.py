"""금액은 모두 정수 센트로 다룬다."""
from decimal import Decimal, ROUND_HALF_UP


def to_cents(amount):
    """'12.34' 나 12.34 → 1234"""
    return int((Decimal(str(amount)) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def add(*cents):
    """센트 합"""
    return sum(int(c) for c in cents)

import unittest

from ledger import money


class MoneyTest(unittest.TestCase):
    def test_to_cents(self):
        self.assertEqual(money.to_cents('12.34'), 1234)
        self.assertEqual(money.to_cents(0.1), 10)

    def test_add(self):
        self.assertEqual(money.add(1, 2, 3), 6)

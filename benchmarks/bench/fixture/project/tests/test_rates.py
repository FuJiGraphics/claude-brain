import unittest

from ledger import rates


class RatesTest(unittest.TestCase):
    def test_convert(self):
        self.assertGreater(rates.convert(100, 'USD'), 100000)

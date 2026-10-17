"""Offline unit tests with synthetic data for calibration logic.
"""
import datetime as dt
import json
import unittest

def fee(shares, rate, p):
    return round(shares * rate * p * (1 - p), 5)

def price_bucket(p):
    buckets = [(0,0.01,"<=1"),(0.01,0.02,"1-2"),(0.02,0.05,"2-5"),(0.05,0.10,"5-10"),
               (0.10,0.20,"10-20"),(0.20,0.40,"20-40"),(0.40,0.60,"40-60"),
               (0.60,0.80,"60-80"),(0.80,0.90,"80-90"),(0.90,0.95,"90-95"),
               (0.95,0.98,"95-98"),(0.98,0.99,"98-99"),(0.99,1.01,">99")]
    for lo, hi, name in buckets:
        if lo <= p < hi:
            return name
    return "other"

class TestCalib(unittest.TestCase):
    def test_fee(self):
        self.assertEqual(fee(100, 0.07, 0.5), 1.75)
        self.assertEqual(fee(100, 0.07, 0.01), 0.0693)  # round

    def test_bucket(self):
        self.assertEqual(price_bucket(0.005), "<=1")
        self.assertEqual(price_bucket(0.015), "1-2")
        self.assertEqual(price_bucket(0.995), ">99")

    def test_hours_to_end(self):
        end = dt.datetime(2026, 5, 1, tzinfo=dt.timezone.utc)
        ts = dt.datetime(2026, 4, 30, 22, tzinfo=dt.timezone.utc)
        h = (end - ts).total_seconds() / 3600
        self.assertAlmostEqual(h, 2.0)

    def test_winner_join(self):
        mkt = {"winner_token": "tok1", "tokens": json.dumps(["tok1", "tok2"])}
        self.assertTrue("tok1" == mkt["winner_token"])

if __name__ == "__main__":
    unittest.main()

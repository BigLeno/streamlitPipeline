import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from dashboard.market_hours import B3, NYSE, format_duration, market_for, market_status

NY = ZoneInfo("America/New_York")


class MarketHoursTest(unittest.TestCase):
    def test_open_during_session(self):
        status = market_status(datetime(2026, 11, 4, 10, 0, tzinfo=NY))  # quarta
        self.assertTrue(status.is_open)
        self.assertEqual(status.time_to_change, timedelta(hours=6))

    def test_before_open(self):
        status = market_status(datetime(2026, 11, 4, 8, 0, tzinfo=NY))
        self.assertFalse(status.is_open)
        self.assertEqual(status.next_change, datetime(2026, 11, 4, 9, 30, tzinfo=NY))

    def test_close_time_is_closed(self):
        self.assertFalse(market_status(datetime(2026, 11, 4, 16, 0, tzinfo=NY)).is_open)

    def test_friday_after_close_opens_on_monday(self):
        status = market_status(datetime(2026, 11, 6, 17, 0, tzinfo=NY))
        self.assertEqual(status.next_change, datetime(2026, 11, 9, 9, 30, tzinfo=NY))

    def test_weekend(self):
        status = market_status(datetime(2026, 11, 7, 11, 0, tzinfo=NY))  # sábado
        self.assertFalse(status.is_open)
        self.assertEqual(status.next_change.weekday(), 0)

    def test_converts_from_other_timezones(self):
        brasilia = ZoneInfo("America/Sao_Paulo")
        self.assertTrue(market_status(datetime(2026, 11, 4, 12, 0, tzinfo=brasilia)).is_open)

    def test_requires_timezone(self):
        with self.assertRaises(ValueError):
            market_status(datetime(2026, 11, 4, 12, 0))

    def test_market_for_ticker(self):
        self.assertIs(market_for("PETR4.SA"), B3)
        self.assertIs(market_for("^bvsp"), B3)
        self.assertIs(market_for("AAPL"), NYSE)
        self.assertIs(market_for("^GSPC"), NYSE)

    def test_b3_closes_at_18h_without_us_daylight_saving(self):
        sp = ZoneInfo("America/Sao_Paulo")
        self.assertTrue(market_status(datetime(2026, 11, 4, 17, 30, tzinfo=sp), B3).is_open)  # novembro
        self.assertFalse(market_status(datetime(2026, 11, 4, 18, 0, tzinfo=sp), B3).is_open)

    def test_b3_closes_at_17h_with_us_daylight_saving(self):
        sp = ZoneInfo("America/Sao_Paulo")
        status = market_status(datetime(2026, 7, 15, 16, 0, tzinfo=sp), B3)  # julho
        self.assertTrue(status.is_open)
        self.assertEqual(status.next_change, datetime(2026, 7, 15, 17, 0, tzinfo=sp))
        self.assertFalse(market_status(datetime(2026, 7, 15, 17, 30, tzinfo=sp), B3).is_open)

    def test_b3_before_open(self):
        sp = ZoneInfo("America/Sao_Paulo")
        status = market_status(datetime(2026, 11, 4, 9, 0, tzinfo=sp), B3)
        self.assertFalse(status.is_open)
        self.assertEqual(status.next_change, datetime(2026, 11, 4, 10, 0, tzinfo=sp))

    def test_format_duration(self):
        self.assertEqual(format_duration(timedelta(hours=2, minutes=5)), "2h 5min")
        self.assertEqual(format_duration(timedelta(days=2, hours=16, minutes=30)), "2d 16h 30min")


if __name__ == "__main__":
    unittest.main()

import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from dashboard.market_hours import format_duration, market_status

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

    def test_format_duration(self):
        self.assertEqual(format_duration(timedelta(hours=2, minutes=5)), "2h 5min")
        self.assertEqual(format_duration(timedelta(days=2, hours=16, minutes=30)), "2d 16h 30min")


if __name__ == "__main__":
    unittest.main()

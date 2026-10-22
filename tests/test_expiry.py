from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app import config
from app.services import expiry


def test_stored_value_roundtrips_to_the_same_calendar_day():
    day = date(2026, 10, 22)
    stored = expiry.to_stored(day)

    assert stored == datetime(2026, 10, 22, tzinfo=timezone.utc)
    assert expiry.from_stored(stored) == day


def test_none_stays_none():
    assert expiry.to_stored(None) is None
    assert expiry.from_stored(None) is None
    assert expiry.days_left(None, date(2026, 10, 22)) is None
    assert expiry.is_expiring_soon(None) is False


def test_naive_datetime_from_sqlite_is_read_as_utc_day():
    assert expiry.from_stored(datetime(2026, 10, 22, 0, 0)) == date(2026, 10, 22)


def test_aware_datetime_in_another_zone_is_converted_to_utc_day():
    # Postgres oturum saat dilimi UTC değilse: 23 Ekim 00:00 +03:00 = 22 Ekim 21:00 UTC → gün 22
    istanbul = datetime(2026, 10, 23, 0, 0, tzinfo=timezone(timedelta(hours=3)))
    assert expiry.from_stored(istanbul) == date(2026, 10, 22)


def test_days_left_counts_calendar_days():
    today = date(2026, 10, 22)
    assert expiry.days_left(date(2026, 10, 22), today) == 0  # bugün bitiyor
    assert expiry.days_left(date(2026, 10, 25), today) == 3
    assert expiry.days_left(date(2026, 10, 21), today) == -1  # dün bitti


def test_expiring_soon_threshold_includes_today_and_already_expired():
    assert expiry.is_expiring_soon(-5) is True
    assert expiry.is_expiring_soon(0) is True
    assert expiry.is_expiring_soon(expiry.EXPIRY_SOON_DAYS) is True
    assert expiry.is_expiring_soon(expiry.EXPIRY_SOON_DAYS + 1) is False


def test_today_uses_the_configured_timezone_not_utc(monkeypatch):
    # 22 Ekim 22:30 UTC, İstanbul'da (UTC+3) 23 Ekim 01:30: "bugün" 23 Ekim olmalı
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 22, 22, 30, tzinfo=timezone.utc).astimezone(tz)

    monkeypatch.setattr(expiry, "datetime", FixedDatetime)
    monkeypatch.setattr(config, "TIMEZONE", "Europe/Istanbul")
    assert expiry.today() == date(2026, 10, 23)

    monkeypatch.setattr(config, "TIMEZONE", "UTC")
    assert expiry.today() == date(2026, 10, 22)


def test_istanbul_zone_is_available():
    # tzdata paketi requirements.txt'te olmalı (Windows ve minimal imajlarda sistem tz verisi yoktur)
    assert ZoneInfo("Europe/Istanbul").utcoffset(datetime(2026, 10, 22)) == timedelta(hours=3)

"""Son kullanma tarihi yardımcıları.

Tarih bir **takvim günü**dür: `pantry_items.expires_at` sütununda o günün UTC gece yarısı olarak
saklanır, okunurken tekrar güne çevrilir. "Bugün" `config.TIMEZONE` saat dilimine göre hesaplanır;
böylece gece yarısı civarında (Vercel UTC çalışır) gün yanlış kaymaz.
"""
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from app import config

# Bu kadar gün veya daha az kalan (süresi geçmişler dahil) malzemeler "yakında bozulacak" sayılır
EXPIRY_SOON_DAYS = 3


def today() -> date:
    return datetime.now(ZoneInfo(config.TIMEZONE)).date()


def to_stored(day: date | None) -> datetime | None:
    return None if day is None else datetime.combine(day, time.min, tzinfo=timezone.utc)


def from_stored(value: datetime | None) -> date | None:
    if value is None:
        return None
    if value.tzinfo is not None:  # Postgres saat dilimli döner; SQLite saat dilimsiz
        value = value.astimezone(timezone.utc)
    return value.date()


def days_left(expires_on: date | None, now: date) -> int | None:
    """Bugünden itibaren kalan gün (bugün bitiyorsa 0, geçmişse negatif)."""
    return None if expires_on is None else (expires_on - now).days


def is_expiring_soon(days: int | None) -> bool:
    return days is not None and days <= EXPIRY_SOON_DAYS

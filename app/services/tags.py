from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Tag
from app.utils.text import normalize


def clean_tags(names: Iterable[str]) -> list[str]:
    """Etiket adlarını temizler: boşlukları sadeleştirir, boşları atar, normalize edilmiş
    hâlde tekrar edenleri (ilk yazılışı koruyarak) tek bırakır."""
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in names:
        name = " ".join(raw.split())
        key = normalize(name)
        if not key or key in seen:
            continue
        seen.add(key)
        cleaned.append(name)
    return cleaned


def get_or_create_tag(db: Session, name: str) -> Tag:
    """Normalize edilmiş ada göre etiketi bulur, yoksa oluşturur (commit etmez)."""
    name = " ".join(name.split())
    normalized = normalize(name)
    tag = db.scalar(select(Tag).where(Tag.normalized == normalized))
    if tag is None:
        tag = Tag(name=name, normalized=normalized)
        db.add(tag)
        db.flush()
    return tag

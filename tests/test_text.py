import pytest

from app.utils.text import normalize


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("İrmik", "irmik"),  # büyük İ → i (Python'ın "i̇" hatası olmamalı)
        ("IRMIK", "ırmık"),  # büyük I → ı
        ("ISPANAK", "ıspanak"),
        ("İSTANBUL", "istanbul"),
        ("Şeker", "şeker"),
        ("ÇÖĞÜŞ", "çöğüş"),
        ("  Sivri   biber ", "sivri biber"),  # baş/son ve ardışık boşluklar
        ("domates", "domates"),
        ("", ""),
        ("   ", ""),
    ],
)
def test_normalize(raw, expected):
    assert normalize(raw) == expected


def test_normalize_leaves_no_combining_dot():
    assert "̇" not in normalize("İİİ")


def test_normalize_is_idempotent():
    once = normalize("İRMİK  Helvası")
    assert normalize(once) == once

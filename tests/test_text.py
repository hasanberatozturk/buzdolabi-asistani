import pytest

from app.utils.text import normalize


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("İrmik", "irmik"),  # büyük İ → i (Python'ın "i̇" hatası olmamalı)
        ("IRMIK", "irmik"),  # büyük I de i'ye katlanır
        ("ISPANAK", "ispanak"),
        ("Ispanak", "ispanak"),
        ("ıspanak", "ispanak"),  # noktasız ı da katlanır
        ("ispanak", "ispanak"),
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


def test_all_i_variants_normalize_to_the_same_key():
    assert len({normalize(word) for word in ("ISPANAK", "Ispanak", "ıspanak", "ispanak", "İSPANAK")}) == 1


def test_normalize_is_idempotent():
    once = normalize("İRMİK  Helvası")
    assert normalize(once) == once

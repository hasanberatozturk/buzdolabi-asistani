"""Stil dosyasındaki, arayüz davranışını bozabilecek kurallar için regresyon testleri."""
import re
from pathlib import Path

CSS = (Path(__file__).resolve().parent.parent / "public" / "css" / "style.css").read_text(encoding="utf-8")


def test_hidden_attribute_always_wins_over_display_rules():
    # `.switch` / `.actions` gibi `display` veren kurallar [hidden] ile gizlenen öğeyi göstermesin
    assert re.search(r"\[hidden\]\s*\{[^}]*display:\s*none\s*!important", CSS)

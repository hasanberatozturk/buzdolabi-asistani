def normalize(text: str) -> str:
    """Türkçe harflere duyarlı küçük harfe çevirme ve boşluk temizleme."""
    text = text.strip().replace("İ", "i").replace("I", "ı")
    return " ".join(text.lower().split())

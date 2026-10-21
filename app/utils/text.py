def normalize(text: str) -> str:
    """Büyük/küçük harf ve i/ı/İ/I farkından bağımsız karşılaştırma anahtarı.

    İngilizce klavyeyle "ispanak" yazan kullanıcı "Ispanak" kaydını bulabilsin diye
    dört harfin hepsi "i"ye katlanır. Görünen ad ayrıca `name` sütununda tutulur.
    """
    text = text.strip().replace("İ", "i").replace("I", "i").replace("ı", "i")
    return " ".join(text.lower().split())

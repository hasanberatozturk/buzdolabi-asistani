import hmac

from fastapi import Header, HTTPException

from app import config


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Yazma uç noktalarını `ADMIN_KEY` ile korur.

    - ADMIN_KEY tanımlıysa istek `X-API-Key` başlığında aynı değeri taşımalı (401).
    - Tanımlı değilse yerelde serbest; Vercel'de kapalı (503), yani yanlışlıkla
      anahtarsız yayına çıkılamaz.
    """
    expected = config.ADMIN_KEY
    if not expected:
        if config.IS_VERCEL:
            raise HTTPException(status_code=503, detail="Sunucuda ADMIN_KEY ayarlanmamış.")
        return
    if x_api_key is None or not hmac.compare_digest(x_api_key.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Geçersiz veya eksik anahtar.")

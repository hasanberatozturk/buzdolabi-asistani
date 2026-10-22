import logging

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers import ingredients, pantry, recipes, shopping

logger = logging.getLogger(__name__)

app = FastAPI(title="Buzdolabı Asistanı")
app.include_router(ingredients.router)
app.include_router(pantry.router)
app.include_router(recipes.router)
app.include_router(shopping.router)


@app.get("/api/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        # Kullanıcıya genel mesaj döner; asıl hata (şifre, pooler, ağ...) Vercel loglarına düşer.
        logger.exception("Sağlık kontrolü: veritabanı bağlantısı başarısız")
        raise HTTPException(status_code=503, detail="Veritabanına bağlanılamadı.")
    return {"status": "ok", "database": "ok"}

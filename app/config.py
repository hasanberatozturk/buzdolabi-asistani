import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL: str = os.getenv("DATABASE_URL") or "sqlite:///./local.db"

# Yazma uç noktalarını koruyan paylaşılan anahtar (bkz. app/security.py)
ADMIN_KEY: str | None = os.getenv("ADMIN_KEY") or None
IS_VERCEL: bool = bool(os.getenv("VERCEL"))

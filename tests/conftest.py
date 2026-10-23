import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

from app import config
from app.database import get_db
from app.main import app
from app.models import Base

# Varsayılan: her test kendi bellek içi SQLite'ını kullanır.
# TEST_DATABASE_URL (postgresql://...) verilirse tüm testler Postgres'te, geçici bir şemada
# çalışır: `public` şemasına dokunulmaz, oturum sonunda şema silinir. Örnek:
#   TEST_DATABASE_URL=postgresql://... pytest
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
TEST_SCHEMA = "pytest_tmp"
TABLES = (
    "shopping_items",
    "pantry_items",
    "recipe_tags",
    "tags",
    "recipe_ingredients",
    "recipes",
    "ingredients",
)


@pytest.fixture(autouse=True)
def no_admin_key(monkeypatch):
    """Testler geliştiricinin .env dosyasındaki ADMIN_KEY'den etkilenmesin."""
    monkeypatch.setattr(config, "ADMIN_KEY", None)
    monkeypatch.setattr(config, "IS_VERCEL", False)


@pytest.fixture(scope="session")
def postgres_engine():
    if not TEST_DATABASE_URL:
        yield None
        return

    url = TEST_DATABASE_URL
    if url.startswith(("postgres://", "postgresql://")):
        url = "postgresql+psycopg://" + url.split("://", 1)[1]
    # Uygulamadakiyle aynı ayarlar (NullPool, transaction pooler uyumu)
    base = create_engine(url, poolclass=NullPool, connect_args={"prepare_threshold": None})
    with base.begin() as connection:
        connection.execute(text(f"DROP SCHEMA IF EXISTS {TEST_SCHEMA} CASCADE"))
        connection.execute(text(f"CREATE SCHEMA {TEST_SCHEMA}"))
    # Model tabloları public yerine geçici şemaya yazılır/okunur
    engine = base.execution_options(schema_translate_map={None: TEST_SCHEMA})
    Base.metadata.create_all(engine)
    yield engine
    with base.begin() as connection:
        connection.execute(text(f"DROP SCHEMA IF EXISTS {TEST_SCHEMA} CASCADE"))


@pytest.fixture
def client(postgres_engine):
    """(TestClient, db oturumu) döndürür; her test boş bir veritabanıyla başlar."""
    if postgres_engine is None:
        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(engine)
    else:
        engine = postgres_engine
        with engine.begin() as connection:
            tables = ", ".join(f"{TEST_SCHEMA}.{table}" for table in TABLES)
            connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    Session = sessionmaker(bind=engine, autoflush=False)

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with Session() as db:
        yield TestClient(app), db
    app.dependency_overrides.clear()

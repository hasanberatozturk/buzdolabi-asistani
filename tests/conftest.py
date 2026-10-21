import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import config
from app.database import get_db
from app.main import app
from app.models import Base


@pytest.fixture(autouse=True)
def no_admin_key(monkeypatch):
    """Testler geliştiricinin .env dosyasındaki ADMIN_KEY'den etkilenmesin."""
    monkeypatch.setattr(config, "ADMIN_KEY", None)
    monkeypatch.setattr(config, "IS_VERCEL", False)


@pytest.fixture
def client():
    """(TestClient, db oturumu) döndürür; her test kendi bellek içi SQLite'ını kullanır."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
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

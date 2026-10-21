from app.database import get_db
from app.main import app


def test_health_ok(client):
    http, _ = client
    response = http.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_returns_503_when_database_is_down(client):
    http, _ = client

    class BrokenSession:
        def execute(self, *args, **kwargs):
            raise RuntimeError("bağlantı yok")

    app.dependency_overrides[get_db] = lambda: BrokenSession()

    response = http.get("/api/health")

    assert response.status_code == 503
    assert response.json()["detail"] == "Veritabanına bağlanılamadı."

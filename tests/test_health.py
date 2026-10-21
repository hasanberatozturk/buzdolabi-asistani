import logging

from app.database import get_db
from app.main import app


def test_health_ok(client):
    http, _ = client
    response = http.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


class BrokenSession:
    def execute(self, *args, **kwargs):
        raise RuntimeError("bağlantı yok: şifre reddedildi")


def test_health_returns_503_when_database_is_down(client):
    http, _ = client
    app.dependency_overrides[get_db] = lambda: BrokenSession()

    response = http.get("/api/health")

    assert response.status_code == 503
    assert response.json()["detail"] == "Veritabanına bağlanılamadı."


def test_health_logs_the_real_cause_but_does_not_leak_it_to_the_client(client, caplog):
    http, _ = client
    app.dependency_overrides[get_db] = lambda: BrokenSession()

    with caplog.at_level(logging.ERROR, logger="app.main"):
        response = http.get("/api/health")

    assert "şifre reddedildi" not in response.text
    [record] = [r for r in caplog.records if r.name == "app.main"]
    assert record.exc_info is not None
    assert "şifre reddedildi" in str(record.exc_info[1])

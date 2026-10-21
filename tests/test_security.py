import pytest

from app import config

KEY = "test-anahtari-123"
RECIPE = {"title": "Omlet", "instructions": "Pişir.", "ingredients": [{"name": "Yumurta"}]}


@pytest.fixture
def locked(client, monkeypatch):
    """Bir tarif, malzeme ve buzdolabı kaydı oluşturur, sonra anahtarı devreye alır."""
    http, db = client
    recipe_id = http.post("/api/recipes", json=RECIPE).json()["id"]
    ingredient_id = http.get("/api/ingredients").json()[0]["id"]
    item_id = http.post("/api/pantry", json={"ingredient_id": ingredient_id}).json()["id"]
    monkeypatch.setattr(config, "ADMIN_KEY", KEY)
    return http, {"recipe": recipe_id, "ingredient": ingredient_id, "item": item_id}


def write_requests(ids):
    return [
        ("POST", "/api/recipes", RECIPE),
        ("PUT", f"/api/recipes/{ids['recipe']}", RECIPE),
        ("DELETE", f"/api/recipes/{ids['recipe']}", None),
        ("POST", "/api/ingredients", {"name": "Süt"}),
        ("POST", "/api/pantry", {"ingredient_id": ids["ingredient"]}),
        ("DELETE", f"/api/pantry/{ids['item']}", None),
        ("DELETE", "/api/pantry", None),
    ]


def test_every_write_endpoint_rejects_missing_key(locked):
    http, ids = locked
    for method, path, body in write_requests(ids):
        response = http.request(method, path, json=body)
        assert response.status_code == 401, (method, path)
        assert response.json()["detail"] == "Geçersiz veya eksik anahtar."


def test_every_write_endpoint_rejects_wrong_key(locked):
    http, ids = locked
    for method, path, body in write_requests(ids):
        response = http.request(method, path, json=body, headers={"X-API-Key": "yanlis"})
        assert response.status_code == 401, (method, path)


def test_wrong_key_changes_nothing(locked):
    http, ids = locked
    http.delete(f"/api/recipes/{ids['recipe']}", headers={"X-API-Key": "yanlis"})
    http.delete("/api/pantry", headers={"X-API-Key": "yanlis"})

    assert http.get(f"/api/recipes/{ids['recipe']}").status_code == 200
    assert len(http.get("/api/pantry").json()) == 1


def test_correct_key_allows_writes(locked):
    http, ids = locked
    headers = {"X-API-Key": KEY}

    assert http.post("/api/recipes", json=RECIPE, headers=headers).status_code == 201
    assert http.put(f"/api/recipes/{ids['recipe']}", json=RECIPE, headers=headers).status_code == 200
    assert http.post("/api/ingredients", json={"name": "Süt"}, headers=headers).status_code == 201
    assert http.delete(f"/api/pantry/{ids['item']}", headers=headers).status_code == 204
    assert http.delete(f"/api/recipes/{ids['recipe']}", headers=headers).status_code == 204


def test_non_ascii_key_is_rejected_not_crashing(locked):
    http, _ = locked
    response = http.delete("/api/pantry", headers={"X-API-Key": "şifre".encode("utf-8")})
    assert response.status_code == 401


def test_read_endpoints_stay_public(locked):
    http, ids = locked
    assert http.get("/api/health").status_code == 200
    assert http.get("/api/recipes").status_code == 200
    assert http.get(f"/api/recipes/{ids['recipe']}").status_code == 200
    assert http.get("/api/recipes/match").status_code == 200
    assert http.get("/api/ingredients").status_code == 200
    assert http.get("/api/pantry").status_code == 200


def test_without_key_configured_writes_are_open_locally(client):
    http, _ = client
    assert http.post("/api/recipes", json=RECIPE).status_code == 201


def test_without_key_configured_writes_are_closed_on_vercel(client, monkeypatch):
    http, _ = client
    monkeypatch.setattr(config, "IS_VERCEL", True)

    response = http.post("/api/recipes", json=RECIPE)

    assert response.status_code == 503
    assert response.json()["detail"] == "Sunucuda ADMIN_KEY ayarlanmamış."
    assert http.get("/api/recipes").status_code == 200  # okuma etkilenmez

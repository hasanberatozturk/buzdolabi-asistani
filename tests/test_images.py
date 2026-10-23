import pytest

from app.models import Recipe
from sqlalchemy import select

URL = "https://example.com/foto.jpg"


def body(**overrides):
    data = {"title": "Menemen", "instructions": "x", "ingredients": [{"name": "Yumurta"}], "image_url": URL}
    data.update(overrides)
    return data


@pytest.mark.parametrize(
    "bad",
    [
        "http://example.com/a.jpg",  # https değil
        "javascript:alert(1)",
        "data:image/png;base64,AAAA",
        "//example.com/a.jpg",
        "ftp://example.com/a.jpg",
        "https://",
        "https:///a.jpg",
        "https:example.com/a.jpg",
        "example.com/a.jpg",
        "https://user:pass@example.com/a.jpg",  # kimlik bilgisi içeren adres
        "https://kullanici@example.com/a.jpg",
        "https://exa mple.com/a.jpg",  # boşluk
        "https://example.com/a b.jpg",
        "https://example.com/a.jpg\nX",  # satır sonu
        "https://example.com/" + "a" * 500,  # 500 karakteri aşıyor
    ],
)
def test_invalid_image_urls_are_rejected(client, bad):
    http, db = client
    assert http.post("/api/recipes", json=body(image_url=bad)).status_code == 422, bad
    assert db.scalar(select(Recipe.id)) is None


@pytest.mark.parametrize(
    "good",
    [
        URL,
        "HTTPS://Example.com/Foto.JPG",
        "https://cdn.example.com/a/b/c.png?w=600&q=80#x",
        "https://example.com:8443/a.jpg",
        "https://sub.example.co.uk/%C3%A7.jpg",
    ],
)
def test_valid_https_image_urls_are_accepted(client, good):
    http, _ = client
    response = http.post("/api/recipes", json=body(image_url=good))
    assert response.status_code == 201, good
    assert response.json()["image_url"] == good


def test_image_url_is_trimmed_and_blank_becomes_null(client):
    http, _ = client
    assert http.post("/api/recipes", json=body(image_url=f"  {URL}  ")).json()["image_url"] == URL
    assert http.post("/api/recipes", json=body(image_url="   ")).json()["image_url"] is None
    assert http.post("/api/recipes", json=body(image_url=None)).json()["image_url"] is None
    no_field = {k: v for k, v in body().items() if k != "image_url"}
    assert http.post("/api/recipes", json=no_field).json()["image_url"] is None


def test_image_url_appears_in_detail_list_and_match(client):
    http, _ = client
    recipe_id = http.post("/api/recipes", json=body()).json()["id"]
    ingredient = http.get("/api/ingredients").json()[0]
    http.post("/api/pantry", json={"ingredient_id": ingredient["id"]})

    assert http.get(f"/api/recipes/{recipe_id}").json()["image_url"] == URL
    assert http.get("/api/recipes").json()["items"][0]["image_url"] == URL
    [match] = http.get("/api/recipes/match", params={"max_missing": 0}).json()
    assert match["image_url"] == URL


def test_match_result_has_null_image_when_recipe_has_none(client):
    http, _ = client
    http.post("/api/recipes", json=body(image_url=None))
    ingredient = http.get("/api/ingredients").json()[0]
    http.post("/api/pantry", json={"ingredient_id": ingredient["id"]})

    [match] = http.get("/api/recipes/match", params={"max_missing": 0}).json()

    assert match["image_url"] is None


def test_update_can_change_and_clear_the_image(client):
    http, _ = client
    recipe_id = http.post("/api/recipes", json=body()).json()["id"]

    changed = http.put(f"/api/recipes/{recipe_id}", json=body(image_url="https://example.org/yeni.png"))
    assert changed.json()["image_url"] == "https://example.org/yeni.png"

    cleared = http.put(f"/api/recipes/{recipe_id}", json=body(image_url=None))
    assert cleared.json()["image_url"] is None


def test_update_rejects_a_bad_image_url_and_keeps_the_old_one(client):
    http, _ = client
    recipe_id = http.post("/api/recipes", json=body()).json()["id"]

    response = http.put(f"/api/recipes/{recipe_id}", json=body(image_url="http://example.com/a.jpg"))

    assert response.status_code == 422
    assert http.get(f"/api/recipes/{recipe_id}").json()["image_url"] == URL

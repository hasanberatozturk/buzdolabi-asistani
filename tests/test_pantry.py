from datetime import date

import pytest

from app.models import Ingredient
from app.services import expiry


def make_ingredient(db, name):
    ingredient = Ingredient(name=name, normalized=name.lower())
    db.add(ingredient)
    db.commit()
    return ingredient.id


def test_pantry_starts_empty(client):
    http, _ = client
    assert http.get("/api/pantry").json() == []


def test_add_to_pantry_and_list_it(client):
    http, db = client
    egg = make_ingredient(db, "Yumurta")

    response = http.post("/api/pantry", json={"ingredient_id": egg})

    assert response.status_code == 201
    assert response.json()["ingredient"] == {"id": egg, "name": "Yumurta"}
    [item] = http.get("/api/pantry").json()
    assert item["ingredient"]["name"] == "Yumurta"


def test_list_keeps_insertion_order(client):
    http, db = client
    ids = [make_ingredient(db, name) for name in ("Süt", "Un", "Şeker")]
    for ingredient_id in ids:
        http.post("/api/pantry", json={"ingredient_id": ingredient_id})

    listed = [item["ingredient"]["name"] for item in http.get("/api/pantry").json()]

    assert listed == ["Süt", "Un", "Şeker"]


def test_adding_same_ingredient_twice_returns_409(client):
    http, db = client
    egg = make_ingredient(db, "Yumurta")
    http.post("/api/pantry", json={"ingredient_id": egg})

    response = http.post("/api/pantry", json={"ingredient_id": egg})

    assert response.status_code == 409
    assert len(http.get("/api/pantry").json()) == 1


def test_adding_unknown_ingredient_returns_404(client):
    http, _ = client
    response = http.post("/api/pantry", json={"ingredient_id": 999})
    assert response.status_code == 404
    assert response.json()["detail"] == "Malzeme bulunamadı."


def test_adding_without_ingredient_id_returns_422(client):
    http, _ = client
    assert http.post("/api/pantry", json={}).status_code == 422


TODAY = date(2026, 10, 22)


@pytest.fixture
def fixed_today(monkeypatch):
    monkeypatch.setattr(expiry, "today", lambda: TODAY)


def test_item_without_expiry_has_null_date_and_days_left(client):
    http, db = client
    egg = make_ingredient(db, "Yumurta")

    body = http.post("/api/pantry", json={"ingredient_id": egg}).json()

    assert body["expires_on"] is None
    assert body["days_left"] is None


def test_add_with_expiry_date_returns_days_left(client, fixed_today):
    http, db = client
    milk = make_ingredient(db, "Süt")

    response = http.post("/api/pantry", json={"ingredient_id": milk, "expires_on": "2026-10-25"})

    assert response.status_code == 201
    assert response.json()["expires_on"] == "2026-10-25"
    assert response.json()["days_left"] == 3
    [listed] = http.get("/api/pantry").json()
    assert (listed["expires_on"], listed["days_left"]) == ("2026-10-25", 3)


def test_days_left_is_zero_today_and_negative_when_expired(client, fixed_today):
    http, db = client
    today_id = make_ingredient(db, "Süt")
    old_id = make_ingredient(db, "Yoğurt")
    http.post("/api/pantry", json={"ingredient_id": today_id, "expires_on": "2026-10-22"})
    http.post("/api/pantry", json={"ingredient_id": old_id, "expires_on": "2026-10-20"})

    days = {i["ingredient"]["name"]: i["days_left"] for i in http.get("/api/pantry").json()}

    assert days == {"Süt": 0, "Yoğurt": -2}


def test_add_rejects_invalid_or_out_of_range_dates(client):
    http, db = client
    egg = make_ingredient(db, "Yumurta")
    for bad in ("yarın", "2026-13-40", "1999-12-31", "2101-01-01", 20261022, ""):
        response = http.post("/api/pantry", json={"ingredient_id": egg, "expires_on": bad})
        assert response.status_code == 422, bad
    assert http.get("/api/pantry").json() == []


def test_patch_sets_changes_and_clears_expiry(client, fixed_today):
    http, db = client
    egg = make_ingredient(db, "Yumurta")
    item_id = http.post("/api/pantry", json={"ingredient_id": egg}).json()["id"]

    set_date = http.patch(f"/api/pantry/{item_id}", json={"expires_on": "2026-10-30"})
    assert (set_date.status_code, set_date.json()["days_left"]) == (200, 8)

    changed = http.patch(f"/api/pantry/{item_id}", json={"expires_on": "2026-10-23"})
    assert changed.json()["days_left"] == 1

    cleared = http.patch(f"/api/pantry/{item_id}", json={"expires_on": None})
    assert cleared.json()["expires_on"] is None
    assert cleared.json()["days_left"] is None
    assert http.get("/api/pantry").json()[0]["expires_on"] is None


def test_patch_requires_the_expires_on_field(client):
    http, db = client
    egg = make_ingredient(db, "Yumurta")
    item_id = http.post("/api/pantry", json={"ingredient_id": egg}).json()["id"]

    assert http.patch(f"/api/pantry/{item_id}", json={}).status_code == 422
    assert http.patch(f"/api/pantry/{item_id}", json={"expires_on": "bozuk"}).status_code == 422


def test_patch_unknown_item_returns_404_and_bad_id_422(client):
    http, _ = client
    assert http.patch("/api/pantry/999", json={"expires_on": None}).status_code == 404
    assert http.patch("/api/pantry/99999999999999999999", json={"expires_on": None}).status_code == 422
    assert http.patch("/api/pantry/0", json={"expires_on": None}).status_code == 422


def test_patch_keeps_the_item_in_place_in_the_list(client):
    http, db = client
    ids = [make_ingredient(db, name) for name in ("Süt", "Un", "Şeker")]
    items = [http.post("/api/pantry", json={"ingredient_id": i}).json()["id"] for i in ids]

    http.patch(f"/api/pantry/{items[0]}", json={"expires_on": "2026-11-01"})

    assert [i["ingredient"]["name"] for i in http.get("/api/pantry").json()] == ["Süt", "Un", "Şeker"]


def test_out_of_range_ids_are_rejected_not_500(client):
    http, _ = client
    huge = 99999999999999999999

    assert http.post("/api/pantry", json={"ingredient_id": huge}).status_code == 422
    assert http.post("/api/pantry", json={"ingredient_id": 0}).status_code == 422
    assert http.delete(f"/api/pantry/{huge}").status_code == 422


def test_remove_item_from_pantry(client):
    http, db = client
    egg = make_ingredient(db, "Yumurta")
    item_id = http.post("/api/pantry", json={"ingredient_id": egg}).json()["id"]

    assert http.delete(f"/api/pantry/{item_id}").status_code == 204

    assert http.get("/api/pantry").json() == []
    assert http.delete(f"/api/pantry/{item_id}").status_code == 404


def test_clear_pantry_removes_everything_but_keeps_ingredients(client):
    http, db = client
    for name in ("Süt", "Un"):
        http.post("/api/pantry", json={"ingredient_id": make_ingredient(db, name)})

    assert http.delete("/api/pantry").status_code == 204

    assert http.get("/api/pantry").json() == []
    assert len(http.get("/api/ingredients").json()) == 2


def test_clearing_empty_pantry_is_fine(client):
    http, _ = client
    assert http.delete("/api/pantry").status_code == 204

from app.models import Ingredient


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

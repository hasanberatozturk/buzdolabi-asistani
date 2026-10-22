import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models import Ingredient, PantryItem, ShoppingItem
from app.routers.shopping import _commit_retrying_on_conflict


def make_recipe(http, title="Tarif", servings=2, rows=None):
    rows = rows or [{"name": "Un", "quantity": 200, "unit": "gram"}, {"name": "Süt", "quantity": 1, "unit": "su bardağı"}]
    response = http.post(
        "/api/recipes",
        json={"title": title, "instructions": "x", "servings": servings, "ingredients": rows},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def ingredient_id(db, name):
    return db.scalar(select(Ingredient.id).where(Ingredient.name == name))


def add_to_pantry(http, db, name):
    assert http.post("/api/pantry", json={"ingredient_id": ingredient_id(db, name)}).status_code == 201


def names(http):
    return [i["ingredient"]["name"] for i in http.get("/api/shopping").json()]


def count(db, model):
    return db.scalar(select(func.count()).select_from(model))


def test_shopping_list_starts_empty(client):
    http, _ = client
    assert http.get("/api/shopping").json() == []


def test_from_recipe_adds_missing_required_ingredients_with_amounts(client):
    http, db = client
    recipe_id = make_recipe(
        http,
        rows=[
            {"name": "Yumurta", "quantity": 3, "unit": "adet"},
            {"name": "Süt", "quantity": 1, "unit": "su bardağı"},
            {"name": "Un", "quantity": 200, "unit": "gram"},
            {"name": "Soğan", "is_optional": True},
            {"name": "Tuz"},
        ],
    )
    add_to_pantry(http, db, "Yumurta")

    response = http.post("/api/shopping/from-recipe", json={"recipe_id": recipe_id})

    assert response.status_code == 200
    assert response.json() == {"added": 2, "already_listed": 0, "nothing_missing": False}
    items = http.get("/api/shopping").json()
    assert [(i["ingredient"]["name"], i["quantity"], i["unit"], i["checked"]) for i in items] == [
        ("Süt", 1, "su bardağı", False),
        ("Un", 200, "gram", False),
    ]


def test_adding_the_same_recipe_twice_does_not_duplicate_items(client):
    http, db = client
    recipe_id = make_recipe(http)
    http.post("/api/shopping/from-recipe", json={"recipe_id": recipe_id})

    second = http.post("/api/shopping/from-recipe", json={"recipe_id": recipe_id})

    assert second.json() == {"added": 0, "already_listed": 2, "nothing_missing": False}
    assert count(db, ShoppingItem) == 2


def test_second_recipe_only_adds_ingredients_not_already_listed(client):
    http, db = client
    first = make_recipe(http, "Birinci", rows=[{"name": "Un"}, {"name": "Süt"}])
    second = make_recipe(http, "İkinci", rows=[{"name": "Süt"}, {"name": "Şeker"}])
    http.post("/api/shopping/from-recipe", json={"recipe_id": first})

    result = http.post("/api/shopping/from-recipe", json={"recipe_id": second}).json()

    assert result == {"added": 1, "already_listed": 1, "nothing_missing": False}
    assert names(http) == ["Un", "Süt", "Şeker"]


def test_nothing_missing_when_everything_is_in_the_pantry(client):
    http, db = client
    recipe_id = make_recipe(http, rows=[{"name": "Un"}, {"name": "Tuz"}])
    add_to_pantry(http, db, "Un")

    result = http.post("/api/shopping/from-recipe", json={"recipe_id": recipe_id})

    assert result.json() == {"added": 0, "already_listed": 0, "nothing_missing": True}
    assert http.get("/api/shopping").json() == []


def test_amounts_scale_with_selected_servings(client):
    http, _ = client
    recipe_id = make_recipe(http, servings=2)

    http.post("/api/shopping/from-recipe", json={"recipe_id": recipe_id, "servings": 6})

    amounts = {i["ingredient"]["name"]: i["quantity"] for i in http.get("/api/shopping").json()}
    assert amounts == {"Un": 600, "Süt": 3}


def test_amounts_are_not_scaled_when_recipe_has_no_servings(client):
    http, _ = client
    recipe_id = make_recipe(http, servings=None)

    http.post("/api/shopping/from-recipe", json={"recipe_id": recipe_id, "servings": 6})

    assert {i["quantity"] for i in http.get("/api/shopping").json()} == {200, 1}


def test_from_recipe_validation_and_not_found(client):
    http, _ = client
    recipe_id = make_recipe(http)
    huge = 99999999999999999999

    assert http.post("/api/shopping/from-recipe", json={"recipe_id": 999}).status_code == 404
    assert http.post("/api/shopping/from-recipe", json={}).status_code == 422
    assert http.post("/api/shopping/from-recipe", json={"recipe_id": huge}).status_code == 422
    assert http.post("/api/shopping/from-recipe", json={"recipe_id": 0}).status_code == 422
    for bad in (0, -1, 1001, "x", 2.5):
        response = http.post("/api/shopping/from-recipe", json={"recipe_id": recipe_id, "servings": bad})
        assert response.status_code == 422, bad
    assert http.get("/api/shopping").json() == []


def test_unchecked_items_come_before_checked_ones(client):
    http, _ = client
    recipe_id = make_recipe(http, rows=[{"name": "A"}, {"name": "B"}, {"name": "C"}])
    http.post("/api/shopping/from-recipe", json={"recipe_id": recipe_id})
    first = http.get("/api/shopping").json()[0]["id"]

    http.patch(f"/api/shopping/{first}", json={"checked": True})

    assert names(http) == ["B", "C", "A"]


def test_patch_checks_and_unchecks_an_item(client):
    http, _ = client
    http.post("/api/shopping/from-recipe", json={"recipe_id": make_recipe(http)})
    item_id = http.get("/api/shopping").json()[0]["id"]

    checked = http.patch(f"/api/shopping/{item_id}", json={"checked": True})
    assert (checked.status_code, checked.json()["checked"]) == (200, True)
    unchecked = http.patch(f"/api/shopping/{item_id}", json={"checked": False})
    assert unchecked.json()["checked"] is False


def test_patch_validation(client):
    http, _ = client
    http.post("/api/shopping/from-recipe", json={"recipe_id": make_recipe(http)})
    item_id = http.get("/api/shopping").json()[0]["id"]

    assert http.patch(f"/api/shopping/{item_id}", json={}).status_code == 422
    assert http.patch(f"/api/shopping/{item_id}", json={"checked": "belki"}).status_code == 422
    assert http.patch("/api/shopping/999", json={"checked": True}).status_code == 404
    assert http.patch("/api/shopping/99999999999999999999", json={"checked": True}).status_code == 422
    assert http.patch("/api/shopping/0", json={"checked": True}).status_code == 422


def test_delete_one_item(client):
    http, _ = client
    http.post("/api/shopping/from-recipe", json={"recipe_id": make_recipe(http)})
    item_id = http.get("/api/shopping").json()[0]["id"]

    assert http.delete(f"/api/shopping/{item_id}").status_code == 204

    assert len(http.get("/api/shopping").json()) == 1
    assert http.delete(f"/api/shopping/{item_id}").status_code == 404
    assert http.delete("/api/shopping/99999999999999999999").status_code == 422


def test_clear_all_and_clear_only_checked(client):
    http, _ = client
    http.post("/api/shopping/from-recipe", json={"recipe_id": make_recipe(http)})
    first = http.get("/api/shopping").json()[0]["id"]
    http.patch(f"/api/shopping/{first}", json={"checked": True})

    assert http.delete("/api/shopping", params={"only_checked": "true"}).status_code == 204
    assert len(http.get("/api/shopping").json()) == 1  # işaretsiz kalan

    assert http.delete("/api/shopping").status_code == 204
    assert http.get("/api/shopping").json() == []
    assert http.delete("/api/shopping").status_code == 204  # boş listeyi temizlemek sorun değil


def test_move_to_pantry_moves_only_checked_items(client):
    http, db = client
    http.post("/api/shopping/from-recipe", json={"recipe_id": make_recipe(http)})
    first = http.get("/api/shopping").json()[0]["id"]
    http.patch(f"/api/shopping/{first}", json={"checked": True})

    result = http.post("/api/shopping/move-to-pantry")

    assert (result.status_code, result.json()) == (200, {"moved": 1})
    assert names(http) == ["Süt"]  # işaretsiz kaldı
    pantry = http.get("/api/pantry").json()
    assert [p["ingredient"]["name"] for p in pantry] == ["Un"]
    assert (pantry[0]["quantity"], pantry[0]["unit"]) == (200, "gram")  # miktar taşındı
    assert count(db, PantryItem) == 1


def test_move_to_pantry_does_not_duplicate_an_item_already_in_the_pantry(client):
    http, db = client
    http.post("/api/shopping/from-recipe", json={"recipe_id": make_recipe(http)})
    add_to_pantry(http, db, "Un")  # sonradan buzdolabına eklendi
    for item in http.get("/api/shopping").json():
        http.patch(f"/api/shopping/{item['id']}", json={"checked": True})

    result = http.post("/api/shopping/move-to-pantry").json()

    assert result == {"moved": 2}
    assert http.get("/api/shopping").json() == []
    assert sorted(p["ingredient"]["name"] for p in http.get("/api/pantry").json()) == ["Süt", "Un"]


def test_move_to_pantry_with_nothing_checked_changes_nothing(client):
    http, _ = client
    http.post("/api/shopping/from-recipe", json={"recipe_id": make_recipe(http)})

    assert http.post("/api/shopping/move-to-pantry").json() == {"moved": 0}
    assert len(http.get("/api/shopping").json()) == 2
    assert http.get("/api/pantry").json() == []


class FakeSession:
    def __init__(self, commit_failures):
        self.commit_failures = commit_failures
        self.commits = 0
        self.rollbacks = 0

    def commit(self):
        self.commits += 1
        if self.commits <= self.commit_failures:
            raise IntegrityError("INSERT", {}, Exception("unique"))

    def rollback(self):
        self.rollbacks += 1


def test_unique_conflict_is_retried_once_and_then_succeeds():
    db, calls = FakeSession(commit_failures=1), []

    result = _commit_retrying_on_conflict(db, lambda: calls.append(1) or "tamam")

    assert result == "tamam"
    assert (len(calls), db.rollbacks, db.commits) == (2, 1, 2)


def test_persistent_unique_conflict_is_raised():
    db = FakeSession(commit_failures=5)

    with pytest.raises(IntegrityError):
        _commit_retrying_on_conflict(db, lambda: None)

    assert (db.commits, db.rollbacks) == (2, 2)

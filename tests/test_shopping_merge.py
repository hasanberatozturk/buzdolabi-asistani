"""Aynı malzemeyi isteyen tariflerin alışveriş listesinde toplanması (aynı birim) ve tekrar eklemenin
miktarı katlamaması."""
from sqlalchemy import func, select

from app.models import ShoppingItemSource
from app.services.shopping import ListedItem, MissingIngredient, plan_additions


def make_recipe(http, title, rows, servings=2):
    response = http.post(
        "/api/recipes",
        json={"title": title, "instructions": "x", "servings": servings, "ingredients": rows},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def add(http, recipe_id, servings=None):
    response = http.post("/api/shopping/from-recipe", json={"recipe_id": recipe_id, "servings": servings})
    assert response.status_code == 200, response.text
    return response.json()


def amounts(http):
    return {i["ingredient"]["name"]: (i["quantity"], i["unit"]) for i in http.get("/api/shopping").json()}


def source_count(db):
    return db.scalar(select(func.count()).select_from(ShoppingItemSource))


EGG = lambda quantity, unit="adet": {"name": "Yumurta", "quantity": quantity, "unit": unit}  # noqa: E731


# --- saf planlama ---------------------------------------------------------------------------


def listed(quantity, unit="adet", sources=None):
    return {1: ListedItem(1, quantity, unit, sources or {})}


def missing(quantity, unit="adet"):
    return [MissingIngredient(1, quantity, unit)]


def test_plan_new_ingredient_becomes_a_new_item():
    plan = plan_additions(7, missing(3), {})
    assert [m.ingredient_id for m in plan.new] == [1]
    assert (plan.merges, plan.unchanged) == ([], 0)


def test_plan_sums_same_unit_from_another_recipe():
    plan = plan_additions(8, missing(2), listed(3, sources={7: 3}))
    assert [(m.quantity, m.source_quantity) for m in plan.merges] == [(5, 2)]
    assert (plan.new, plan.unchanged) == ([], 0)


def test_plan_same_recipe_again_with_same_amount_changes_nothing():
    plan = plan_additions(7, missing(3), listed(3, sources={7: 3}))
    assert (plan.new, plan.merges, plan.unchanged) == ([], [], 1)


def test_plan_same_recipe_with_new_amount_replaces_only_its_own_contribution():
    plan = plan_additions(7, missing(6), listed(5, sources={7: 3, 8: 2}))
    assert [m.quantity for m in plan.merges] == [8]  # 5 - 3 + 6


def test_plan_units_are_compared_ignoring_case_and_spaces():
    plan = plan_additions(8, missing(1, "Su Bardağı"), listed(2, "su bardağı", {7: 2}))
    assert [m.quantity for m in plan.merges] == [3]


def test_plan_different_units_keep_the_existing_item():
    plan = plan_additions(8, missing(200, "gram"), listed(3, "adet", {7: 3}))
    assert (plan.merges, plan.unchanged) == ([], 1)


def test_plan_missing_quantities_are_never_merged():
    assert plan_additions(8, missing(None, None), listed(None, None, {7: None})).unchanged == 1
    assert plan_additions(8, missing(2), listed(None, "adet", {7: None})).unchanged == 1
    assert plan_additions(8, missing(None, "adet"), listed(3, "adet", {7: 3})).unchanged == 1


def test_plan_rounds_floating_point_noise():
    plan = plan_additions(8, missing(0.2), listed(0.1, sources={7: 0.1}))
    assert [m.quantity for m in plan.merges] == [0.3]


def test_plan_handles_a_mix_of_new_merged_and_unchanged_items():
    items = {
        1: ListedItem(1, 3, "adet", {7: 3}),
        2: ListedItem(2, 100, "gram", {7: 100}),
        3: ListedItem(3, None, None, {7: None}),
    }
    todo = [MissingIngredient(1, 2, "adet"), MissingIngredient(2, 1, "adet"), MissingIngredient(3, None, None), MissingIngredient(4, 5, "adet")]

    plan = plan_additions(8, todo, items)

    assert [m.ingredient_id for m in plan.new] == [4]
    assert [(m.ingredient_id, m.quantity) for m in plan.merges] == [(1, 5)]
    assert plan.unchanged == 2


# --- API ------------------------------------------------------------------------------------


def test_two_recipes_with_the_same_unit_are_summed(client):
    http, db = client
    a = make_recipe(http, "A", [EGG(3)])
    b = make_recipe(http, "B", [EGG(2)])

    first = add(http, a)
    second = add(http, b)

    assert first == {"added": 1, "merged": 0, "already_listed": 0, "nothing_missing": False}
    assert second == {"added": 0, "merged": 1, "already_listed": 0, "nothing_missing": False}
    assert amounts(http) == {"Yumurta": (5, "adet")}
    assert len(http.get("/api/shopping").json()) == 1
    assert source_count(db) == 2


def test_adding_the_same_recipe_again_does_not_double_the_amount(client):
    http, _ = client
    a = make_recipe(http, "A", [EGG(3)])
    b = make_recipe(http, "B", [EGG(2)])
    add(http, a)
    add(http, b)

    again = [add(http, a), add(http, b), add(http, a)]

    assert all(r["merged"] == 0 and r["already_listed"] == 1 for r in again)
    assert amounts(http) == {"Yumurta": (5, "adet")}


def test_changing_servings_replaces_that_recipes_contribution(client):
    http, _ = client
    a = make_recipe(http, "A", [EGG(3)], servings=2)
    b = make_recipe(http, "B", [EGG(2)])
    add(http, a)
    add(http, b)

    result = add(http, a, servings=4)  # A'nın katkısı 3 → 6

    assert result["merged"] == 1
    assert amounts(http) == {"Yumurta": (8, "adet")}  # 6 + 2
    add(http, a, servings=1)  # 3 → 1.5
    assert amounts(http) == {"Yumurta": (3.5, "adet")}


def test_different_units_keep_the_first_item_unchanged(client):
    http, db = client
    a = make_recipe(http, "A", [EGG(3)])
    b = make_recipe(http, "B", [EGG(200, "gram")])
    add(http, a)

    result = add(http, b)

    assert result == {"added": 0, "merged": 0, "already_listed": 1, "nothing_missing": False}
    assert amounts(http) == {"Yumurta": (3, "adet")}
    assert source_count(db) == 1  # B katkı vermedi


def test_amounts_without_quantity_are_not_summed(client):
    http, _ = client
    a = make_recipe(http, "A", [{"name": "Pul biber"}])
    b = make_recipe(http, "B", [{"name": "Pul biber", "quantity": 1, "unit": "çay kaşığı"}])
    add(http, a)

    assert add(http, b)["already_listed"] == 1
    assert amounts(http) == {"Pul biber": (None, None)}


def test_deleting_a_recipe_removes_its_sources_but_keeps_the_listed_total(client):
    http, db = client
    a = make_recipe(http, "A", [EGG(3)])
    b = make_recipe(http, "B", [EGG(2)])
    c = make_recipe(http, "C", [EGG(4)])
    add(http, a)
    add(http, b)

    assert http.delete(f"/api/recipes/{a}").status_code == 204

    assert source_count(db) == 1
    assert amounts(http) == {"Yumurta": (5, "adet")}  # listedeki miktar değişmez
    add(http, c)
    assert amounts(http) == {"Yumurta": (9, "adet")}  # silinen tarifin katkısı hesaba yeniden girmez


def test_removing_an_item_clears_its_sources_and_a_new_add_starts_fresh(client):
    http, db = client
    a = make_recipe(http, "A", [EGG(3)])
    b = make_recipe(http, "B", [EGG(2)])
    add(http, a)
    add(http, b)
    item_id = http.get("/api/shopping").json()[0]["id"]

    assert http.delete(f"/api/shopping/{item_id}").status_code == 204

    assert source_count(db) == 0
    add(http, b)
    assert amounts(http) == {"Yumurta": (2, "adet")}


def test_clearing_the_list_clears_all_sources(client):
    http, db = client
    a = make_recipe(http, "A", [EGG(3)])
    b = make_recipe(http, "B", [EGG(2)])
    add(http, a)
    add(http, b)

    assert http.delete("/api/shopping").status_code == 204

    assert source_count(db) == 0
    add(http, b)  # SQLite'ta kalem id'si yeniden kullanılsa bile eski katkılar karışmamalı
    assert amounts(http) == {"Yumurta": (2, "adet")}


def test_clearing_only_checked_items_keeps_other_sources(client):
    http, db = client
    a = make_recipe(http, "A", [EGG(3), {"name": "Süt", "quantity": 1, "unit": "su bardağı"}])
    add(http, a)
    items = {i["ingredient"]["name"]: i["id"] for i in http.get("/api/shopping").json()}
    http.patch(f"/api/shopping/{items['Süt']}", json={"checked": True})

    assert http.delete("/api/shopping", params={"only_checked": "true"}).status_code == 204

    assert amounts(http) == {"Yumurta": (3, "adet")}
    assert source_count(db) == 1


def test_moving_checked_items_to_the_pantry_clears_their_sources(client):
    http, db = client
    a = make_recipe(http, "A", [EGG(3)])
    add(http, a)
    item_id = http.get("/api/shopping").json()[0]["id"]
    http.patch(f"/api/shopping/{item_id}", json={"checked": True})

    assert http.post("/api/shopping/move-to-pantry").json() == {"moved": 1}

    assert source_count(db) == 0

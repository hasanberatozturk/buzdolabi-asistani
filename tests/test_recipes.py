from app.models import Ingredient, PantryItem, Recipe, RecipeIngredient


def add_recipe(db, title, rows=(), **fields):
    recipe = Recipe(title=title, instructions="Adım 1\nAdım 2", **fields)
    for ingredient, extra in rows:
        recipe.ingredients.append(RecipeIngredient(ingredient=ingredient, **extra))
    db.add(recipe)
    db.commit()
    return recipe


def test_list_recipes_is_paginated(client):
    http, db = client
    for i in range(5):
        add_recipe(db, f"Tarif {i}")

    page = http.get("/api/recipes", params={"limit": 2, "offset": 2}).json()

    assert page["total"] == 5
    assert (page["limit"], page["offset"]) == (2, 2)
    assert [item["title"] for item in page["items"]] == ["Tarif 2", "Tarif 3"]


def test_list_recipes_rejects_bad_paging(client):
    http, _ = client
    assert http.get("/api/recipes", params={"limit": 0}).status_code == 422
    assert http.get("/api/recipes", params={"limit": 101}).status_code == 422
    assert http.get("/api/recipes", params={"offset": -1}).status_code == 422


def test_recipe_detail_marks_pantry_and_staple_ingredients(client):
    http, db = client
    egg = Ingredient(name="Yumurta", normalized="yumurta")
    milk = Ingredient(name="Süt", normalized="süt")
    salt = Ingredient(name="Tuz", normalized="tuz")
    recipe = add_recipe(
        db,
        "Omlet",
        [(egg, {"quantity": 2, "unit": "adet"}), (milk, {"is_optional": True}), (salt, {})],
        prep_minutes=5,
        servings=1,
    )
    db.add(PantryItem(ingredient=egg))
    db.commit()

    body = http.get(f"/api/recipes/{recipe.id}").json()

    assert body["title"] == "Omlet"
    assert body["instructions"] == "Adım 1\nAdım 2"
    by_name = {row["name"]: row for row in body["ingredients"]}
    assert by_name["Yumurta"]["in_pantry"] is True
    assert by_name["Yumurta"]["quantity"] == 2
    assert by_name["Süt"]["in_pantry"] is False
    assert by_name["Süt"]["is_optional"] is True
    assert by_name["Tuz"]["in_pantry"] is True  # temel malzeme


def test_recipe_detail_returns_404_for_unknown_id(client):
    http, _ = client
    response = http.get("/api/recipes/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Tarif bulunamadı."


def test_recipe_detail_rejects_non_numeric_id(client):
    http, _ = client
    assert http.get("/api/recipes/abc").status_code == 422


def test_match_route_is_not_shadowed_by_recipe_id(client):
    http, _ = client
    response = http.get("/api/recipes/match")
    assert response.status_code == 200
    assert response.json() == []

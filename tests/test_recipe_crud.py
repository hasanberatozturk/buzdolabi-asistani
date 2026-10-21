from sqlalchemy import func, select

from app.models import Ingredient, Recipe, RecipeIngredient


def payload(**overrides):
    data = {
        "title": "Menemen",
        "description": "Klasik.",
        "instructions": "Pişir.\nServis et.",
        "prep_minutes": 15,
        "servings": 2,
        "ingredients": [
            {"name": "Yumurta", "quantity": 3, "unit": "adet"},
            {"name": "Soğan", "is_optional": True},
        ],
    }
    data.update(overrides)
    return data


def count(db, model):
    return db.scalar(select(func.count()).select_from(model))


def test_create_recipe_returns_detail_and_creates_ingredients(client):
    http, db = client

    response = http.post("/api/recipes", json=payload())

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Menemen"
    assert [row["name"] for row in body["ingredients"]] == ["Yumurta", "Soğan"]
    assert body["ingredients"][1]["is_optional"] is True
    assert count(db, Ingredient) == 2
    assert http.get(f"/api/recipes/{body['id']}").status_code == 200


def test_create_recipe_reuses_existing_ingredient_by_normalized_name(client):
    http, db = client
    db.add(Ingredient(name="İrmik", normalized="irmik"))
    db.commit()

    http.post("/api/recipes", json=payload(ingredients=[{"name": "  İRMİK "}]))

    assert count(db, Ingredient) == 1


def test_create_recipe_trims_and_nulls_blank_optional_fields(client):
    http, _ = client

    body = http.post(
        "/api/recipes",
        json=payload(
            title="  Omlet  ",
            description="   ",
            ingredients=[{"name": "Yumurta", "unit": "  "}],
        ),
    ).json()

    assert body["title"] == "Omlet"
    assert body["description"] is None
    assert body["ingredients"][0]["unit"] is None


def test_create_recipe_validation_errors(client):
    http, db = client
    bad_payloads = [
        payload(title="   "),
        payload(instructions=""),
        payload(ingredients=[]),
        payload(ingredients=[{"name": "  "}]),
        payload(ingredients=[{"name": "Yumurta", "quantity": -1}]),
        payload(prep_minutes=-5),
        payload(servings=0),
        payload(image_url="javascript:alert(1)"),
    ]
    for bad in bad_payloads:
        assert http.post("/api/recipes", json=bad).status_code == 422, bad
    assert count(db, Recipe) == 0


def test_create_recipe_rejects_duplicate_ingredient(client):
    http, db = client

    response = http.post(
        "/api/recipes", json=payload(ingredients=[{"name": "Süt"}, {"name": " süt "}])
    )

    assert response.status_code == 400
    assert count(db, Recipe) == 0


def test_update_recipe_replaces_fields_and_ingredients(client):
    http, db = client
    recipe_id = http.post("/api/recipes", json=payload()).json()["id"]

    response = http.put(
        f"/api/recipes/{recipe_id}",
        json=payload(title="Sade Menemen", ingredients=[{"name": "Yumurta"}, {"name": "Domates"}]),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Sade Menemen"
    assert [row["name"] for row in body["ingredients"]] == ["Yumurta", "Domates"]
    assert count(db, RecipeIngredient) == 2  # eski satırlar yetim kalmadı
    assert count(db, Recipe) == 1


def test_update_unknown_recipe_returns_404(client):
    http, _ = client
    assert http.put("/api/recipes/999", json=payload()).status_code == 404


def test_delete_recipe_removes_its_ingredient_rows(client):
    http, db = client
    recipe_id = http.post("/api/recipes", json=payload()).json()["id"]

    assert http.delete(f"/api/recipes/{recipe_id}").status_code == 204

    assert http.get(f"/api/recipes/{recipe_id}").status_code == 404
    assert count(db, Recipe) == 0
    assert count(db, RecipeIngredient) == 0
    assert count(db, Ingredient) == 2  # malzeme kataloğu korunur


def test_delete_unknown_recipe_returns_404(client):
    http, _ = client
    assert http.delete("/api/recipes/999").status_code == 404

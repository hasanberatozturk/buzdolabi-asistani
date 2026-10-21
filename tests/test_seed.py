import json

from sqlalchemy import func, select

from app.models import Ingredient, Recipe, RecipeIngredient
from app.utils.text import normalize
from scripts.seed import SEED_FILE, seed


def count(db, model):
    return db.scalar(select(func.count()).select_from(model))


def test_seed_loads_every_recipe_in_the_json_file(client):
    _, db = client
    expected = json.loads(SEED_FILE.read_text(encoding="utf-8"))

    added, skipped = seed(db)

    assert (added, skipped) == (len(expected), 0)
    assert count(db, Recipe) == len(expected)
    assert all(recipe.ingredients for recipe in db.scalars(select(Recipe)))


def test_seed_is_idempotent(client):
    _, db = client
    seed(db)
    totals = (count(db, Recipe), count(db, Ingredient), count(db, RecipeIngredient))

    added, skipped = seed(db)

    assert added == 0
    assert skipped == totals[0]
    assert (count(db, Recipe), count(db, Ingredient), count(db, RecipeIngredient)) == totals


def test_seed_shares_ingredients_between_recipes(client):
    _, db = client
    seed(db)
    names = [
        row["name"]
        for recipe in json.loads(SEED_FILE.read_text(encoding="utf-8"))
        for row in recipe["ingredients"]
    ]

    assert count(db, Ingredient) == len({normalize(name) for name in names})
    assert len(names) > count(db, Ingredient)  # örn. "Tereyağı" birden çok tarifte geçiyor


def test_seed_keeps_optional_flag_and_quantities(client):
    _, db = client
    seed(db)

    menemen = db.scalar(select(Recipe).where(Recipe.title == "Menemen"))
    rows = {row.ingredient.name: row for row in menemen.ingredients}

    assert rows["Soğan"].is_optional is True
    assert rows["Yumurta"].is_optional is False
    assert rows["Yumurta"].quantity == 3
    assert rows["Yumurta"].unit == "adet"


def test_seed_file_has_no_duplicate_ingredients_within_a_recipe():
    for recipe in json.loads(SEED_FILE.read_text(encoding="utf-8")):
        names = [normalize(row["name"]) for row in recipe["ingredients"]]
        assert len(names) == len(set(names)), recipe["title"]

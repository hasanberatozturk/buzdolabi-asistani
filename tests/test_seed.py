import json

from sqlalchemy import func, select

from app.models import Ingredient, Recipe, RecipeIngredient, Tag
from app.services.tags import get_or_create_tag
from app.utils.text import normalize
from scripts.seed import SEED_FILE, seed


def count(db, model):
    return db.scalar(select(func.count()).select_from(model))


def test_seed_loads_every_recipe_in_the_json_file(client):
    _, db = client
    expected = json.loads(SEED_FILE.read_text(encoding="utf-8"))

    added, skipped, _ = seed(db)

    assert (added, skipped) == (len(expected), 0)
    assert count(db, Recipe) == len(expected)
    assert all(recipe.ingredients for recipe in db.scalars(select(Recipe)))


def test_seed_is_idempotent(client):
    _, db = client
    seed(db)
    totals = (count(db, Recipe), count(db, Ingredient), count(db, RecipeIngredient))

    added, skipped, tagged = seed(db)

    assert added == 0
    assert skipped == totals[0]
    assert tagged == 0  # ilk çalıştırmada etiketler zaten yazıldı
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


def tag_names(db, title):
    recipe = db.scalar(select(Recipe).where(Recipe.title == title))
    return [tag.name for tag in recipe.tags]


def test_seed_attaches_tags_from_the_json_file(client):
    _, db = client
    seed(db)

    assert tag_names(db, "Menemen") == ["kahvaltı", "vejetaryen"]
    assert tag_names(db, "Makarna") == ["ana yemek", "vegan", "vejetaryen"]
    expected = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    assert all(item.get("tags") for item in expected)  # her seed tarifinin etiketi var
    assert count(db, Tag) == len({normalize(t) for item in expected for t in item["tags"]})


def test_seed_adds_tags_to_existing_recipes_that_have_none(client):
    """Canlıdaki gibi: tarifler etiketsiz yüklenmiş; seed'i yeniden çalıştırmak etiketleri ekler."""
    _, db = client
    seed(db)
    for recipe in db.scalars(select(Recipe)):
        recipe.tags = []
    db.commit()

    added, skipped, tagged = seed(db)

    assert (added, skipped, tagged) == (0, 8, 8)
    assert tag_names(db, "Cacık") == ["meze", "vejetaryen"]


def test_seed_never_overwrites_tags_given_by_the_user(client):
    _, db = client
    seed(db)
    omlet = db.scalar(select(Recipe).where(Recipe.title == "Omlet"))
    omlet.tags = [get_or_create_tag(db, "benim etiketim")]
    db.commit()

    _, _, tagged = seed(db)

    assert tagged == 0
    assert tag_names(db, "Omlet") == ["benim etiketim"]

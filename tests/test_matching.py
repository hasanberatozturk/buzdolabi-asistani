import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.models import Base, Ingredient, PantryItem, Recipe, RecipeIngredient
from app.services.matching import RecipeCandidate, match_recipes


def candidate(recipe_id, title, required, prep_minutes=10):
    return RecipeCandidate(recipe_id, title, prep_minutes, tuple(required))


MENEMEN = candidate(1, "Menemen", [(1, "Yumurta"), (2, "Domates"), (3, "Biber"), (4, "Tereyağı")], 15)
OMLET = candidate(2, "Omlet", [(1, "Yumurta"), (5, "Süt")], 5)


def test_full_match_has_ratio_one_and_nothing_missing():
    [result] = match_recipes([OMLET], {1, 5}, max_missing=0)
    assert result.match_ratio == 1.0
    assert result.missing == []
    assert result.have == ["Yumurta", "Süt"]


def test_partial_match_lists_have_and_missing():
    [result] = match_recipes([MENEMEN], {1, 2, 3}, max_missing=2)
    assert result.match_ratio == 0.75
    assert result.have == ["Yumurta", "Domates", "Biber"]
    assert result.missing == ["Tereyağı"]


def test_recipes_over_max_missing_are_filtered_out():
    assert match_recipes([MENEMEN], {1, 2}, max_missing=1) == []


def test_recipe_with_no_matching_ingredient_is_skipped():
    assert match_recipes([OMLET], {99}, max_missing=5) == []


def test_recipe_without_required_ingredients_is_skipped():
    assert match_recipes([candidate(3, "Boş", [])], {1}, max_missing=5) == []


def test_empty_pantry_matches_nothing():
    assert match_recipes([MENEMEN, OMLET], set(), max_missing=5) == []


def test_sorted_by_missing_then_ratio_then_prep_time():
    fewer_missing = candidate(10, "A", [(1, "x"), (2, "y")], 30)  # 1 eksik, %50
    higher_ratio = candidate(11, "B", [(1, "x"), (3, "z"), (4, "w")], 30)  # 2 eksik, %33
    slower = candidate(12, "C", [(1, "x"), (2, "y")], 20)  # 1 eksik, %50, daha hızlı
    no_time = candidate(13, "D", [(1, "x"), (2, "y")], None)  # 1 eksik, %50, süresiz
    results = match_recipes([higher_ratio, fewer_missing, no_time, slower], {1}, max_missing=2)
    assert [r.title for r in results] == ["C", "A", "D", "B"]


def test_higher_ratio_wins_when_missing_count_is_equal():
    big = candidate(20, "Büyük", [(1, "a"), (2, "b"), (3, "c"), (4, "d")], 10)  # 1 eksik, %75
    small = candidate(21, "Küçük", [(1, "a"), (5, "e")], 10)  # 1 eksik, %50
    results = match_recipes([small, big], {1, 2, 3}, max_missing=1)
    assert [r.title for r in results] == ["Büyük", "Küçük"]


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False)

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with Session() as db:
        yield TestClient(app), db
    app.dependency_overrides.clear()


def test_match_endpoint_ignores_optional_ingredients(client):
    http, db = client
    egg = Ingredient(name="Yumurta", normalized="yumurta")
    onion = Ingredient(name="Soğan", normalized="soğan")
    recipe = Recipe(title="Sade", instructions="Pişir.", prep_minutes=5)
    recipe.ingredients = [
        RecipeIngredient(ingredient=egg),
        RecipeIngredient(ingredient=onion, is_optional=True),
    ]
    db.add_all([recipe, PantryItem(ingredient=egg)])
    db.commit()

    response = http.get("/api/recipes/match", params={"max_missing": 0})

    assert response.status_code == 200
    [item] = response.json()
    assert item["title"] == "Sade"
    assert item["match_ratio"] == 1.0
    assert item["have"] == ["Yumurta"]
    assert item["missing"] == []


def test_match_endpoint_returns_empty_list_for_empty_pantry(client):
    http, _ = client
    assert http.get("/api/recipes/match").json() == []


def test_match_endpoint_rejects_negative_max_missing(client):
    http, _ = client
    assert http.get("/api/recipes/match", params={"max_missing": -1}).status_code == 422

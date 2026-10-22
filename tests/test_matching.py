from datetime import date

from app.models import Ingredient, PantryItem, Recipe, RecipeIngredient
from app.services import expiry
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


def test_match_endpoint_treats_staples_as_always_available(client):
    http, db = client
    rice = Ingredient(name="Pirinç", normalized="pirinç")
    water = Ingredient(name="Su", normalized="su")
    recipe = Recipe(title="Pilav", instructions="Pişir.", prep_minutes=25)
    recipe.ingredients = [RecipeIngredient(ingredient=rice), RecipeIngredient(ingredient=water)]
    db.add_all([recipe, PantryItem(ingredient=rice)])
    db.commit()

    [item] = http.get("/api/recipes/match", params={"max_missing": 0}).json()

    assert item["match_ratio"] == 1.0
    assert item["have"] == ["Pirinç"]
    assert item["missing"] == []


def test_match_endpoint_returns_empty_list_for_empty_pantry(client):
    http, _ = client
    assert http.get("/api/recipes/match").json() == []


def test_match_endpoint_rejects_negative_max_missing(client):
    http, _ = client
    assert http.get("/api/recipes/match", params={"max_missing": -1}).status_code == 422


def test_expiring_ingredients_used_by_a_recipe_are_listed():
    [result] = match_recipes([OMLET], {1, 5}, max_missing=0, expiring_ids={5})
    assert result.expiring == ["Süt"]


def test_expiring_ingredient_that_is_not_in_the_pantry_is_ignored():
    [result] = match_recipes([OMLET], {1}, max_missing=1, expiring_ids={5})
    assert result.expiring == []  # 5 buzdolabında yok (eksik), "yakında bozulacak" olamaz


def test_no_expiring_ids_means_empty_expiring_and_unchanged_order():
    results = match_recipes([MENEMEN, OMLET], {1, 2, 3, 4, 5}, max_missing=2)
    assert [r.title for r in results] == ["Omlet", "Menemen"]  # ikisi de %100, Omlet daha hızlı
    assert all(r.expiring == [] for r in results)


def test_recipe_using_expiring_ingredient_ranks_first_when_missing_count_is_equal():
    slow = candidate(30, "Yavaş ama süt kullanır", [(5, "Süt"), (6, "Un")], 60)
    fast = candidate(31, "Hızlı", [(7, "Elma"), (8, "Bal")], 5)
    results = match_recipes([fast, slow], {5, 6, 7, 8}, max_missing=0, expiring_ids={5})
    assert [r.title for r in results] == ["Yavaş ama süt kullanır", "Hızlı"]


def test_more_expiring_ingredients_rank_higher():
    one = candidate(40, "Bir", [(1, "a"), (2, "b")], 10)
    two = candidate(41, "İki", [(3, "c"), (4, "d")], 10)
    results = match_recipes([one, two], {1, 2, 3, 4}, max_missing=0, expiring_ids={1, 3, 4})
    assert [r.title for r in results] == ["İki", "Bir"]


def test_expiring_does_not_beat_fewer_missing_ingredients():
    complete = candidate(50, "Tam", [(1, "a"), (2, "b")], 10)
    expiring_but_missing = candidate(51, "Eksikli", [(3, "c"), (9, "z")], 10)
    results = match_recipes([expiring_but_missing, complete], {1, 2, 3}, max_missing=1, expiring_ids={3})
    assert [r.title for r in results] == ["Tam", "Eksikli"]


def test_match_endpoint_reports_and_prioritizes_expiring_ingredients(client, monkeypatch):
    monkeypatch.setattr(expiry, "today", lambda: date(2026, 10, 22))
    http, db = client
    milk = Ingredient(name="Süt", normalized="süt")
    egg = Ingredient(name="Yumurta", normalized="yumurta")
    flour = Ingredient(name="Un", normalized="un")
    fast = Recipe(title="Omlet", instructions="x", prep_minutes=5)
    fast.ingredients = [RecipeIngredient(ingredient=egg)]
    slow = Recipe(title="Sütlü tatlı", instructions="x", prep_minutes=40)
    slow.ingredients = [RecipeIngredient(ingredient=milk), RecipeIngredient(ingredient=flour)]
    db.add_all(
        [
            fast,
            slow,
            PantryItem(ingredient=egg),
            PantryItem(ingredient=milk, expires_at=expiry.to_stored(date(2026, 10, 24))),  # 2 gün kaldı
            PantryItem(ingredient=flour, expires_at=expiry.to_stored(date(2026, 12, 1))),  # uzak
        ]
    )
    db.commit()

    results = http.get("/api/recipes/match", params={"max_missing": 0}).json()

    assert [r["title"] for r in results] == ["Sütlü tatlı", "Omlet"]
    assert results[0]["expiring"] == ["Süt"]
    assert results[1]["expiring"] == []


def test_match_endpoint_treats_expired_items_as_expiring_and_far_dates_as_not(client, monkeypatch):
    monkeypatch.setattr(expiry, "today", lambda: date(2026, 10, 22))
    http, db = client
    boundary = Ingredient(name="Sınır", normalized="sınır")  # tam 3 gün: yakında sayılır
    beyond = Ingredient(name="Uzak", normalized="uzak")  # 4 gün: sayılmaz
    expired = Ingredient(name="Geçmiş", normalized="geçmiş")  # süresi dolmuş: sayılır
    recipe = Recipe(title="Karışık", instructions="x")
    recipe.ingredients = [RecipeIngredient(ingredient=i) for i in (boundary, beyond, expired)]
    db.add_all(
        [
            recipe,
            PantryItem(ingredient=boundary, expires_at=expiry.to_stored(date(2026, 10, 25))),
            PantryItem(ingredient=beyond, expires_at=expiry.to_stored(date(2026, 10, 26))),
            PantryItem(ingredient=expired, expires_at=expiry.to_stored(date(2026, 10, 20))),
        ]
    )
    db.commit()

    [result] = http.get("/api/recipes/match", params={"max_missing": 0}).json()

    assert sorted(result["expiring"]) == ["Geçmiş", "Sınır"]

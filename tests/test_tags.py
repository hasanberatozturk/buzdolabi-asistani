import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models import Tag, recipe_tags
from app.services.tags import clean_tags


def post_recipe(http, title, tags=None, minutes=None, ingredients=("Un",)):
    body = {
        "title": title,
        "instructions": "x",
        "prep_minutes": minutes,
        "ingredients": [{"name": name} for name in ingredients],
    }
    if tags is not None:
        body["tags"] = tags
    response = http.post("/api/recipes", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def titles(response):
    assert response.status_code == 200, response.text
    body = response.json()
    items = body["items"] if isinstance(body, dict) else body
    return [item["title"] for item in items]


def count(db, table):
    return db.scalar(select(func.count()).select_from(table))


# --- saf yardımcı ---------------------------------------------------------------------------


def test_clean_tags_collapses_spaces_drops_blanks_and_keeps_first_spelling():
    assert clean_tags(["  ana   yemek ", "", "   ", "Kahvaltı"]) == ["ana yemek", "Kahvaltı"]


def test_clean_tags_dedupes_by_normalized_form():
    assert clean_tags(["Çorba", "çorba", "ÇORBA"]) == ["Çorba"]
    assert clean_tags(["Irmak", "ırmak", "İrmak"]) == ["Irmak"]  # i/ı katlaması
    assert clean_tags(["kahvaltı", "KAHVALTI"]) == ["kahvaltı"]


def test_clean_tags_empty_input():
    assert clean_tags([]) == []
    assert clean_tags([" ", ""]) == []


# --- tarife etiket ekleme -------------------------------------------------------------------


def test_recipe_can_be_created_with_tags(client):
    http, _ = client

    recipe = post_recipe(http, "Menemen", tags=["vejetaryen", "kahvaltı"])

    assert recipe["tags"] == ["kahvaltı", "vejetaryen"]  # normalize edilmiş ada göre sıralı
    assert http.get(f"/api/recipes/{recipe['id']}").json()["tags"] == ["kahvaltı", "vejetaryen"]


def test_tags_are_optional_and_default_to_empty(client):
    http, _ = client
    assert post_recipe(http, "Etiketsiz")["tags"] == []
    assert post_recipe(http, "Boş", tags=[])["tags"] == []


def test_duplicate_blank_and_differently_spelled_tags_are_cleaned(client):
    http, db = client

    recipe = post_recipe(http, "A", tags=["Kahvaltı", "kahvalti", " KAHVALTI ", "", "  ", "ana   yemek"])

    assert recipe["tags"] == ["ana yemek", "Kahvaltı"]
    assert count(db, Tag) == 2


def test_tags_are_shared_between_recipes(client):
    http, db = client
    post_recipe(http, "Bir", tags=["kahvaltı"])
    post_recipe(http, "İki", tags=["Kahvaltı"])  # aynı etiket, farklı yazım

    assert count(db, Tag) == 1
    assert count(db, recipe_tags) == 2


def test_update_replaces_tags(client):
    http, db = client
    recipe = post_recipe(http, "Menemen", tags=["kahvaltı", "vejetaryen"])
    body = {"title": "Menemen", "instructions": "x", "ingredients": [{"name": "Un"}], "tags": ["tatlı"]}

    response = http.put(f"/api/recipes/{recipe['id']}", json=body)

    assert response.json()["tags"] == ["tatlı"]
    assert count(db, recipe_tags) == 1


def test_update_without_tags_clears_them(client):
    http, _ = client
    recipe = post_recipe(http, "Menemen", tags=["kahvaltı"])
    body = {"title": "Menemen", "instructions": "x", "ingredients": [{"name": "Un"}]}

    assert http.put(f"/api/recipes/{recipe['id']}", json=body).json()["tags"] == []


def test_deleting_a_recipe_removes_its_tag_links_but_keeps_the_tag_catalog(client):
    http, db = client
    recipe = post_recipe(http, "Menemen", tags=["kahvaltı"])

    assert http.delete(f"/api/recipes/{recipe['id']}").status_code == 204

    assert count(db, recipe_tags) == 0
    assert count(db, Tag) == 1
    assert http.get("/api/tags").json() == []  # kullanılmayan etiket filtre listesinde görünmez


def test_tag_validation(client):
    http, _ = client
    base = {"title": "T", "instructions": "x", "ingredients": [{"name": "Un"}]}

    assert http.post("/api/recipes", json={**base, "tags": [f"e{i}" for i in range(11)]}).status_code == 422
    assert http.post("/api/recipes", json={**base, "tags": ["x" * 51]}).status_code == 422
    assert http.post("/api/recipes", json={**base, "tags": [5]}).status_code == 422
    assert http.post("/api/recipes", json={**base, "tags": "kahvaltı"}).status_code == 422
    assert http.post("/api/recipes", json={**base, "tags": [f"e{i}" for i in range(10)]}).status_code == 201
    assert http.post("/api/recipes", json={**base, "title": "U", "tags": ["x" * 50]}).status_code == 201


class _FlakyTag:
    def __init__(self, monkeypatch, failures):
        from app.routers import recipes
        from app.services.tags import get_or_create_tag

        self.calls = 0

        def flaky(db, name):
            self.calls += 1
            if self.calls <= failures:
                raise IntegrityError("INSERT INTO tags", {}, Exception("tags_name_key"))
            return get_or_create_tag(db, name)

        monkeypatch.setattr(recipes, "get_or_create_tag", flaky)


def test_tag_unique_conflict_is_retried_once(client, monkeypatch):
    http, db = client
    flaky = _FlakyTag(monkeypatch, failures=1)

    recipe = post_recipe(http, "A", tags=["kahvaltı"])

    assert recipe["tags"] == ["kahvaltı"]
    assert flaky.calls == 2
    assert count(db, Tag) == 1


def test_persistent_tag_conflict_is_not_swallowed(client, monkeypatch):
    http, db = client
    _FlakyTag(monkeypatch, failures=99)
    body = {"title": "A", "instructions": "x", "ingredients": [{"name": "Un"}], "tags": ["kahvaltı"]}

    with pytest.raises(IntegrityError):
        http.post("/api/recipes", json=body)

    assert count(db, Tag) == 0


# --- GET /api/tags --------------------------------------------------------------------------


def test_tags_endpoint_lists_used_tags_with_counts(client):
    http, _ = client
    post_recipe(http, "Bir", tags=["kahvaltı", "vejetaryen"])
    post_recipe(http, "İki", tags=["kahvaltı"])
    post_recipe(http, "Üç", tags=["tatlı"])

    assert http.get("/api/tags").json() == [
        {"name": "kahvaltı", "count": 2},
        {"name": "tatlı", "count": 1},
        {"name": "vejetaryen", "count": 1},
    ]


def test_tags_endpoint_is_empty_without_tags(client):
    http, _ = client
    post_recipe(http, "Etiketsiz")
    assert http.get("/api/tags").json() == []


# --- liste filtreleri -----------------------------------------------------------------------


@pytest.fixture
def library(client):
    http, db = client
    post_recipe(http, "Menemen", ["kahvaltı", "vejetaryen"], minutes=15)
    post_recipe(http, "Omlet", ["kahvaltı", "vejetaryen"], minutes=5)
    post_recipe(http, "Makarna", ["ana yemek", "vegan", "vejetaryen"], minutes=20)
    post_recipe(http, "Mercimek", ["çorba", "vejetaryen"], minutes=35)
    post_recipe(http, "Süresiz", ["kahvaltı"], minutes=None)
    post_recipe(http, "Etiketsiz", None, minutes=10)
    return http, db


def test_list_filters_by_one_tag(library):
    http, _ = library
    result = titles(http.get("/api/recipes", params={"tag": "kahvaltı"}))
    assert result == ["Menemen", "Omlet", "Süresiz"]


def test_list_with_several_tags_requires_all_of_them(library):
    http, _ = library
    assert titles(http.get("/api/recipes", params=[("tag", "kahvaltı"), ("tag", "vejetaryen")])) == ["Menemen", "Omlet"]
    assert titles(http.get("/api/recipes", params=[("tag", "vegan"), ("tag", "kahvaltı")])) == []


def test_tag_filter_ignores_case_spelling_and_i_dotting(library):
    http, _ = library
    for spelling in ("KAHVALTI", "Kahvaltı", "kahvalti", "  kahvaltı  "):
        result = titles(http.get("/api/recipes", params={"tag": spelling}))
        assert result == ["Menemen", "Omlet", "Süresiz"], spelling


def test_unknown_tag_returns_nothing(library):
    http, _ = library
    page = http.get("/api/recipes", params={"tag": "yok böyle etiket"}).json()
    assert (page["items"], page["total"]) == ([], 0)
    assert titles(http.get("/api/recipes", params=[("tag", "kahvaltı"), ("tag", "yok")])) == []


def test_blank_tag_parameter_is_ignored(library):
    http, _ = library
    assert len(titles(http.get("/api/recipes", params={"tag": "  "}))) == 6


def test_filtered_list_total_and_paging_follow_the_filter(library):
    http, _ = library
    page = http.get("/api/recipes", params={"tag": "vejetaryen", "limit": 2, "offset": 1}).json()
    assert page["total"] == 4  # Menemen, Omlet, Makarna, Mercimek
    assert [i["title"] for i in page["items"]] == ["Omlet", "Makarna"]


def test_list_items_carry_their_tags(library):
    http, _ = library
    items = {i["title"]: i["tags"] for i in http.get("/api/recipes").json()["items"]}
    assert items["Makarna"] == ["ana yemek", "vegan", "vejetaryen"]
    assert items["Etiketsiz"] == []


def test_max_minutes_filters_by_prep_time_inclusive(library):
    http, _ = library
    assert titles(http.get("/api/recipes", params={"max_minutes": 15})) == ["Menemen", "Omlet", "Etiketsiz"]
    assert titles(http.get("/api/recipes", params={"max_minutes": 14})) == ["Omlet", "Etiketsiz"]


def test_max_minutes_excludes_recipes_without_prep_time(library):
    http, _ = library
    assert "Süresiz" not in titles(http.get("/api/recipes", params={"max_minutes": 10000}))
    assert "Süresiz" in titles(http.get("/api/recipes"))  # filtre yoksa görünür


def test_tag_and_max_minutes_combine(library):
    http, _ = library
    result = titles(http.get("/api/recipes", params={"tag": "vejetaryen", "max_minutes": 15}))
    assert result == ["Menemen", "Omlet"]


def test_filter_parameter_validation(library):
    http, _ = library
    for params in (
        {"max_minutes": -1},
        {"max_minutes": 10001},
        {"max_minutes": "abc"},
        {"tag": "x" * 51},
    ):
        assert http.get("/api/recipes", params=params).status_code == 422, params
    too_many = [("tag", f"e{i}") for i in range(11)]
    assert http.get("/api/recipes", params=too_many).status_code == 422
    assert http.get("/api/recipes", params={"max_minutes": 0}).status_code == 200


# --- eşleştirme filtreleri ------------------------------------------------------------------


@pytest.fixture
def pantry_with_everything(client):
    http, db = client
    post_recipe(http, "Menemen", ["kahvaltı", "vejetaryen"], minutes=15, ingredients=("Yumurta", "Domates"))
    post_recipe(http, "Çorba", ["çorba"], minutes=40, ingredients=("Yumurta", "Un"))
    for ingredient in http.get("/api/ingredients").json():
        assert http.post("/api/pantry", json={"ingredient_id": ingredient["id"]}).status_code == 201
    return http, db


def test_match_without_filters_returns_everything_makeable(pantry_with_everything):
    http, _ = pantry_with_everything
    assert sorted(titles(http.get("/api/recipes/match", params={"max_missing": 0}))) == ["Menemen", "Çorba"]


def test_match_filters_by_tag_and_reports_tags_in_results(pantry_with_everything):
    http, _ = pantry_with_everything

    results = http.get("/api/recipes/match", params={"max_missing": 0, "tag": "kahvaltı"}).json()

    assert [r["title"] for r in results] == ["Menemen"]
    assert results[0]["tags"] == ["kahvaltı", "vejetaryen"]


def test_match_filters_by_max_minutes(pantry_with_everything):
    http, _ = pantry_with_everything
    results = http.get("/api/recipes/match", params={"max_missing": 0, "max_minutes": 30}).json()
    assert [r["title"] for r in results] == ["Menemen"]


def test_match_with_unmatched_filter_is_empty_and_validates_parameters(pantry_with_everything):
    http, _ = pantry_with_everything
    assert http.get("/api/recipes/match", params={"tag": "tatlı"}).json() == []
    assert http.get("/api/recipes/match", params={"max_minutes": -5}).status_code == 422
    assert http.get("/api/recipes/match", params=[("tag", f"e{i}") for i in range(11)]).status_code == 422


def test_filters_do_not_change_ranking_rules(pantry_with_everything):
    http, _ = pantry_with_everything
    plain = http.get("/api/recipes/match", params={"max_missing": 2}).json()
    filtered = http.get("/api/recipes/match", params={"max_missing": 2, "tag": "vejetaryen"}).json()
    assert [r["title"] for r in filtered] == [r["title"] for r in plain if r["title"] == "Menemen"]

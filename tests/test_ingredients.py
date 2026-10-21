from app.models import Ingredient


def add_ingredients(db, *names):
    from app.utils.text import normalize

    db.add_all(Ingredient(name=name, normalized=normalize(name)) for name in names)
    db.commit()


def names(response):
    return [item["name"] for item in response.json()]


def test_search_matches_substring_of_normalized_name(client):
    http, db = client
    add_ingredients(db, "Domates", "Salça domates", "Biber")

    assert names(http.get("/api/ingredients", params={"q": "dom"})) == ["Domates", "Salça domates"]


def test_search_handles_turkish_capitals(client):
    http, db = client
    add_ingredients(db, "İrmik", "Ispanak")

    assert names(http.get("/api/ingredients", params={"q": "İRM"})) == ["İrmik"]
    assert names(http.get("/api/ingredients", params={"q": "ISP"})) == ["Ispanak"]


def test_search_treats_percent_and_underscore_literally(client):
    http, db = client
    add_ingredients(db, "Domates", "Biber")

    assert http.get("/api/ingredients", params={"q": "%"}).json() == []
    assert http.get("/api/ingredients", params={"q": "_"}).json() == []


def test_search_returns_at_most_ten_sorted_results(client):
    http, db = client
    add_ingredients(db, *[f"Malzeme {i:02d}" for i in range(15)])

    result = names(http.get("/api/ingredients"))

    assert len(result) == 10
    assert result == sorted(result)


def test_search_with_no_match_returns_empty_list(client):
    http, db = client
    add_ingredients(db, "Domates")
    assert http.get("/api/ingredients", params={"q": "xyz"}).json() == []


def test_create_ingredient_trims_and_collapses_spaces(client):
    http, _ = client

    response = http.post("/api/ingredients", json={"name": "  Sivri   biber "})

    assert response.status_code == 201
    assert response.json()["name"] == "Sivri biber"


def test_create_duplicate_ingredient_returns_409(client):
    http, db = client
    add_ingredients(db, "İrmik")

    response = http.post("/api/ingredients", json={"name": "İRMİK"})

    assert response.status_code == 409
    assert response.json()["detail"] == "Bu malzeme zaten kayıtlı."


def test_create_ingredient_validation(client):
    http, _ = client
    assert http.post("/api/ingredients", json={}).status_code == 422
    assert http.post("/api/ingredients", json={"name": ""}).status_code == 422
    assert http.post("/api/ingredients", json={"name": "x" * 101}).status_code == 422
    assert http.post("/api/ingredients", json={"name": "   "}).status_code == 400

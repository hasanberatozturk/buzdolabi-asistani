from app.services.shopping import MissingIngredient, RecipeRow, missing_ingredients


def row(ingredient_id, normalized, quantity=None, unit=None, optional=False):
    return RecipeRow(ingredient_id, normalized, quantity, unit, optional)


def test_only_ingredients_missing_from_pantry_are_listed():
    rows = [row(1, "yumurta"), row(2, "süt"), row(3, "un")]

    result = missing_ingredients(rows, pantry_ids={1})

    assert [m.ingredient_id for m in result] == [2, 3]


def test_optional_and_staple_ingredients_are_never_listed():
    rows = [row(1, "soğan", optional=True), row(2, "tuz"), row(3, "su"), row(4, "karabiber"), row(5, "un")]

    assert [m.ingredient_id for m in missing_ingredients(rows, pantry_ids=set())] == [5]


def test_quantity_and_unit_are_kept_without_servings():
    [item] = missing_ingredients([row(1, "un", 2.5, "su bardağı")], pantry_ids=set())

    assert item == MissingIngredient(1, 2.5, "su bardağı")


def test_quantities_scale_with_servings():
    rows = [row(1, "un", 200, "gram"), row(2, "süt", 1.5, "su bardağı")]

    result = missing_ingredients(rows, pantry_ids=set(), base_servings=2, target_servings=6)

    assert [(m.quantity, m.unit) for m in result] == [(600, "gram"), (4.5, "su bardağı")]


def test_scaled_quantity_is_rounded_to_four_decimals():
    [item] = missing_ingredients([row(1, "un", 1, "adet")], pantry_ids=set(), base_servings=3, target_servings=4)

    assert item.quantity == 1.3333


def test_scaling_down_works():
    [item] = missing_ingredients([row(1, "un", 4, "adet")], pantry_ids=set(), base_servings=4, target_servings=1)

    assert item.quantity == 1


def test_no_scaling_when_base_or_target_servings_is_missing():
    rows = [row(1, "un", 200, "gram")]

    assert missing_ingredients(rows, set(), base_servings=None, target_servings=4)[0].quantity == 200
    assert missing_ingredients(rows, set(), base_servings=2, target_servings=None)[0].quantity == 200


def test_ingredient_without_quantity_stays_without_quantity_when_scaled():
    [item] = missing_ingredients([row(1, "pul biber")], pantry_ids=set(), base_servings=2, target_servings=8)

    assert (item.quantity, item.unit) == (None, None)


def test_nothing_missing_returns_empty_list():
    assert missing_ingredients([row(1, "un")], pantry_ids={1}) == []
    assert missing_ingredients([], pantry_ids=set()) == []

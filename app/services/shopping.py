from collections.abc import Iterable
from dataclasses import dataclass

from app.services.matching import STAPLE_INGREDIENTS


@dataclass(frozen=True)
class RecipeRow:
    """Bir tarifin malzeme satırı; veritabanından bağımsızdır."""

    ingredient_id: int
    normalized: str
    quantity: float | None
    unit: str | None
    is_optional: bool


@dataclass(frozen=True)
class MissingIngredient:
    ingredient_id: int
    quantity: float | None
    unit: str | None


def missing_ingredients(
    rows: Iterable[RecipeRow],
    pantry_ids: set[int],
    base_servings: int | None = None,
    target_servings: int | None = None,
) -> list[MissingIngredient]:
    """Tarifte olup buzdolabında bulunmayan zorunlu malzemeler.

    - İsteğe bağlı malzemeler ve temel malzemeler (su, tuz, karabiber) listeye girmez;
      eşleştirmedeki "eksik" tanımıyla aynıdır.
    - `base_servings` (tarifin porsiyonu) ve `target_servings` ikisi de verilirse miktarlar
      orantılı ölçeklenir; aksi hâlde olduğu gibi kalır. Kayan nokta gürültüsü 4 basamağa yuvarlanır.
    """
    scale = target_servings / base_servings if base_servings and target_servings else None
    missing: list[MissingIngredient] = []
    for row in rows:
        if row.is_optional or row.normalized in STAPLE_INGREDIENTS or row.ingredient_id in pantry_ids:
            continue
        quantity = row.quantity
        if quantity is not None and scale is not None:
            quantity = round(quantity * scale, 4)
        missing.append(MissingIngredient(row.ingredient_id, quantity, row.unit))
    return missing

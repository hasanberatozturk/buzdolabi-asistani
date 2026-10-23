from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from app.services.matching import STAPLE_INGREDIENTS
from app.utils.text import normalize


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


@dataclass(frozen=True)
class ListedItem:
    """Listede zaten bulunan bir kalem ve hangi tarifin ne kadar kattığı."""

    ingredient_id: int
    quantity: float | None
    unit: str | None
    sources: Mapping[int, float | None] = field(default_factory=dict)  # tarif id → katkı


@dataclass(frozen=True)
class Merge:
    """Var olan kalemin yeni toplamı ve bu tarifin katkısı."""

    ingredient_id: int
    quantity: float
    source_quantity: float


@dataclass(frozen=True)
class AdditionPlan:
    new: list[MissingIngredient]  # listede olmayanlar: yeni kalem açılır
    merges: list[Merge]  # miktarı değişenler (toplandı ya da bu tarifin katkısı güncellendi)
    unchanged: int  # listede olup değişmeyenler


def _same_unit(a: str | None, b: str | None) -> bool:
    return normalize(a or "") == normalize(b or "")


def plan_additions(
    recipe_id: int,
    missing: Iterable[MissingIngredient],
    listed: Mapping[int, ListedItem],
) -> AdditionPlan:
    """Bir tarifin eksik malzemelerini listeye nasıl ekleyeceğini hesaplar (veritabanına dokunmaz).

    - Listede olmayan malzeme yeni kalem olur.
    - Listede olan malzemede **aynı birim** ve iki miktar da varsa miktarlar toplanır.
    - Aynı tarif tekrar eklenirse miktar katlanmaz: tarifin önceki katkısı yenisiyle **değiştirilir**
      (aynıysa hiçbir şey değişmez; porsiyon değiştiyse toplam buna göre güncellenir).
    - Birim farklıysa ya da miktar yoksa mevcut kalem olduğu gibi korunur.
    """
    new: list[MissingIngredient] = []
    merges: list[Merge] = []
    unchanged = 0
    for item in missing:
        existing = listed.get(item.ingredient_id)
        if existing is None:
            new.append(item)
            continue

        mergeable = (
            existing.quantity is not None
            and item.quantity is not None
            and _same_unit(existing.unit, item.unit)
        )
        if recipe_id in existing.sources:
            previous = existing.sources[recipe_id]
            if previous == item.quantity or not mergeable or previous is None:
                unchanged += 1
            else:
                merges.append(Merge(item.ingredient_id, round(existing.quantity - previous + item.quantity, 4), item.quantity))
        elif mergeable:
            merges.append(Merge(item.ingredient_id, round(existing.quantity + item.quantity, 4), item.quantity))
        else:
            unchanged += 1
    return AdditionPlan(new=new, merges=merges, unchanged=unchanged)

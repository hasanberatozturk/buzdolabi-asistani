from collections.abc import Iterable
from dataclasses import dataclass


# Neredeyse herkeste bulunan malzemeler (normalize edilmiş adlar). Eşleştirmede
# yok sayılır: ne "var" ne "eksik" listesine girer, orana da katılmaz.
STAPLE_INGREDIENTS: frozenset[str] = frozenset({"su", "tuz", "karabiber"})


@dataclass(frozen=True)
class RecipeCandidate:
    """Eşleştirme için gereken en az bilgi; veritabanından bağımsızdır."""

    recipe_id: int
    title: str
    prep_minutes: int | None
    # Sadece zorunlu malzemeler: (ingredient_id, ad)
    required: tuple[tuple[int, str], ...]
    tags: tuple[str, ...] = ()  # eşleştirmeyi etkilemez; sonuçta kartta gösterilir


@dataclass(frozen=True)
class MatchResult:
    recipe_id: int
    title: str
    match_ratio: float
    have: list[str]
    missing: list[str]
    expiring: list[str]
    prep_minutes: int | None
    tags: list[str]


def match_recipes(
    recipes: Iterable[RecipeCandidate],
    pantry_ids: set[int],
    max_missing: int,
    expiring_ids: frozenset[int] | set[int] = frozenset(),
) -> list[MatchResult]:
    """Buzdolabına göre yapılabilen tarifleri, en uygun olandan başlayarak döndürür.

    - Zorunlu malzemesi olmayan tarifler atlanır (oran hesaplanamaz).
    - Buzdolabındaki hiçbir malzemeyi içermeyen tarifler atlanır.
    - `expiring_ids`: yakında bozulacak malzemeler; tarifte kullanılanlar `expiring` listesine girer.
    - Sıralama: eksik sayısı (az → çok), kullanılan yakında-bozulacak malzeme sayısı (çok → az),
      eşleşme oranı (yüksek → düşük), hazırlık süresi (kısa → uzun, süresizler sona), başlık.
    """
    results: list[MatchResult] = []
    for recipe in recipes:
        if not recipe.required:
            continue
        have = [name for ingredient_id, name in recipe.required if ingredient_id in pantry_ids]
        missing = [name for ingredient_id, name in recipe.required if ingredient_id not in pantry_ids]
        if not have or len(missing) > max_missing:
            continue
        expiring = [
            name
            for ingredient_id, name in recipe.required
            if ingredient_id in pantry_ids and ingredient_id in expiring_ids
        ]
        results.append(
            MatchResult(
                recipe_id=recipe.recipe_id,
                title=recipe.title,
                match_ratio=round(len(have) / len(recipe.required), 2),
                have=have,
                missing=missing,
                expiring=expiring,
                prep_minutes=recipe.prep_minutes,
                tags=list(recipe.tags),
            )
        )

    results.sort(
        key=lambda r: (
            len(r.missing),
            -len(r.expiring),
            -r.match_ratio,
            r.prep_minutes is None,
            r.prep_minutes or 0,
            r.title,
        )
    )
    return results

"""Örnek tarifleri data/seed_recipes.json dosyasından yükler.

Çalıştırma (proje kökünden): python scripts/seed.py
Tekrar çalıştırmak güvenlidir: var olan malzeme ve tarifler tekrar eklenmez. Var olan bir tarifin
hiç etiketi yoksa JSON'daki etiketler eklenir; kullanıcının verdiği etiketlere dokunulmaz.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session, selectinload  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models import Recipe, RecipeIngredient  # noqa: E402
from app.services.ingredients import get_or_create_ingredient  # noqa: E402
from app.services.tags import clean_tags, get_or_create_tag  # noqa: E402

SEED_FILE = ROOT / "data" / "seed_recipes.json"


def seed(db: Session) -> tuple[int, int, int]:
    """(eklenen tarif, zaten var olan tarif, var olan tariflerden yeni etiket alan) döndürür."""
    data = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    existing = {
        recipe.title: recipe
        for recipe in db.scalars(select(Recipe).options(selectinload(Recipe.tags)))
    }
    added = skipped = tagged = 0

    for item in data:
        tags = clean_tags(item.get("tags", []))
        recipe = existing.get(item["title"])
        if recipe is not None:
            skipped += 1
            if tags and not recipe.tags:
                recipe.tags = [get_or_create_tag(db, name) for name in tags]
                tagged += 1
            continue
        recipe = Recipe(
            title=item["title"],
            description=item.get("description"),
            instructions=item["instructions"],
            prep_minutes=item.get("prep_minutes"),
            servings=item.get("servings"),
        )
        for row in item["ingredients"]:
            ingredient = get_or_create_ingredient(db, row["name"])
            recipe.ingredients.append(
                RecipeIngredient(
                    ingredient=ingredient,
                    quantity=row.get("quantity"),
                    unit=row.get("unit"),
                    is_optional=row.get("is_optional", False),
                )
            )
        recipe.tags = [get_or_create_tag(db, name) for name in tags]
        db.add(recipe)
        added += 1

    db.commit()
    return added, skipped, tagged


if __name__ == "__main__":
    with SessionLocal() as session:
        added, skipped, tagged = seed(session)
    print(f"{added} tarif eklendi, {skipped} tarif zaten vardı ({tagged} tanesine etiket eklendi).")

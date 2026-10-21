"""Örnek tarifleri data/seed_recipes.json dosyasından yükler.

Çalıştırma (proje kökünden): python scripts/seed.py
Tekrar çalıştırmak güvenlidir; var olan malzeme ve tarifler tekrar eklenmez.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models import Ingredient, Recipe, RecipeIngredient  # noqa: E402
from app.utils.text import normalize  # noqa: E402

SEED_FILE = ROOT / "data" / "seed_recipes.json"


def get_or_create_ingredient(db: Session, name: str) -> Ingredient:
    normalized = normalize(name)
    ingredient = db.scalar(select(Ingredient).where(Ingredient.normalized == normalized))
    if ingredient is None:
        ingredient = Ingredient(name=name.strip(), normalized=normalized)
        db.add(ingredient)
        db.flush()
    return ingredient


def seed(db: Session) -> tuple[int, int]:
    data = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    existing_titles = set(db.scalars(select(Recipe.title)))
    added = skipped = 0

    for item in data:
        if item["title"] in existing_titles:
            skipped += 1
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
        db.add(recipe)
        added += 1

    db.commit()
    return added, skipped


if __name__ == "__main__":
    with SessionLocal() as session:
        added, skipped = seed(session)
    print(f"{added} tarif eklendi, {skipped} tarif zaten vardı.")

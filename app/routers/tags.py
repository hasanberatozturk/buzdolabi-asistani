from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Tag, recipe_tags
from app.schemas import TagCount

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("", response_model=list[TagCount])
def list_tags(db: Session = Depends(get_db)) -> list[TagCount]:
    """Filtre çubuğu için: yalnızca en az bir tarifte kullanılan etiketler ve tarif sayıları."""
    rows = db.execute(
        select(Tag.name, func.count(recipe_tags.c.recipe_id))
        .join(recipe_tags, recipe_tags.c.tag_id == Tag.id)
        .group_by(Tag.id, Tag.name, Tag.normalized)
        .order_by(Tag.normalized)
    ).all()
    return [TagCount(name=name, count=count) for name, count in rows]

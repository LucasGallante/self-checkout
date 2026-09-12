from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models import Category, Item, Option, OptionGroup
from app.schemas import (
    CategoryCreate,
    CategoryOut,
    CategoryUpdate,
    ItemCreate,
    ItemOut,
    ItemUpdate,
    OptionCreate,
    OptionGroupCreate,
    OptionGroupOut,
    OptionGroupUpdate,
    OptionOut,
    OptionUpdate,
)

router = APIRouter(prefix="/menu", tags=["menu"])


# ---- reads (customer + admin share this shape) ----

def _menu_query():
    return select(Category).options(
        selectinload(Category.items).selectinload(Item.option_groups).selectinload(OptionGroup.options)
    )


@router.get("", response_model=list[CategoryOut])
def get_menu(db: Session = Depends(get_db)):
    return db.scalars(_menu_query().order_by(Category.sort_order, Category.id)).all()


# ---- categories ----

@router.post("/categories", response_model=CategoryOut, status_code=201)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)):
    category = Category(**payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.patch("/categories/{category_id}", response_model=CategoryOut)
def update_category(category_id: int, payload: CategoryUpdate, db: Session = Depends(get_db)):
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(category, key, value)
    db.commit()
    db.refresh(category)
    return category


@router.delete("/categories/{category_id}", status_code=204)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    if category.items:
        raise HTTPException(status_code=409, detail="Category still has items")
    db.delete(category)
    db.commit()


# ---- items ----

@router.post("/items", response_model=ItemOut, status_code=201)
def create_item(payload: ItemCreate, db: Session = Depends(get_db)):
    if db.get(Category, payload.category_id) is None:
        raise HTTPException(status_code=404, detail="Category not found")
    item = Item(
        category_id=payload.category_id,
        name=payload.name,
        description=payload.description,
        image_url=payload.image_url,
        price=payload.price,
        stock=payload.stock,
        option_groups=_get_option_groups(db, payload.option_group_ids),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _load_item(db, item.id)


@router.patch("/items/{item_id}", response_model=ItemOut)
def update_item(item_id: int, payload: ItemUpdate, db: Session = Depends(get_db)):
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    data = payload.model_dump(exclude_unset=True)
    if "category_id" in data and db.get(Category, data["category_id"]) is None:
        raise HTTPException(status_code=404, detail="Category not found")
    if "option_group_ids" in data:
        item.option_groups = _get_option_groups(db, data.pop("option_group_ids"))

    for key, value in data.items():
        setattr(item, key, value)

    db.commit()
    db.refresh(item)
    return _load_item(db, item.id)


@router.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    if item.order_items:
        raise HTTPException(status_code=409, detail="Item is referenced by past orders")
    db.delete(item)
    db.commit()


# ---- option groups ----

@router.post("/option-groups", response_model=OptionGroupOut, status_code=201)
def create_option_group(payload: OptionGroupCreate, db: Session = Depends(get_db)):
    group = OptionGroup(**payload.model_dump())
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@router.patch("/option-groups/{group_id}", response_model=OptionGroupOut)
def update_option_group(group_id: int, payload: OptionGroupUpdate, db: Session = Depends(get_db)):
    group = db.get(OptionGroup, group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Option group not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(group, key, value)
    db.commit()
    db.refresh(group)
    return group


@router.delete("/option-groups/{group_id}", status_code=204)
def delete_option_group(group_id: int, db: Session = Depends(get_db)):
    group = db.get(OptionGroup, group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Option group not found")
    if group.options:
        raise HTTPException(status_code=409, detail="Option group still has options")
    db.delete(group)
    db.commit()


# ---- options ----

@router.post("/option-groups/{group_id}/options", response_model=OptionOut, status_code=201)
def create_option(group_id: int, payload: OptionCreate, db: Session = Depends(get_db)):
    if db.get(OptionGroup, group_id) is None:
        raise HTTPException(status_code=404, detail="Option group not found")
    option = Option(option_group_id=group_id, **payload.model_dump())
    db.add(option)
    db.commit()
    db.refresh(option)
    return option


@router.patch("/options/{option_id}", response_model=OptionOut)
def update_option(option_id: int, payload: OptionUpdate, db: Session = Depends(get_db)):
    option = db.get(Option, option_id)
    if option is None:
        raise HTTPException(status_code=404, detail="Option not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(option, key, value)
    db.commit()
    db.refresh(option)
    return option


@router.delete("/options/{option_id}", status_code=204)
def delete_option(option_id: int, db: Session = Depends(get_db)):
    option = db.get(Option, option_id)
    if option is None:
        raise HTTPException(status_code=404, detail="Option not found")
    if option.order_item_options:
        raise HTTPException(status_code=409, detail="Option is referenced by past orders")
    db.delete(option)
    db.commit()


# ---- helpers ----

def _get_option_groups(db: Session, group_ids: list[int]) -> list[OptionGroup]:
    if not group_ids:
        return []
    groups = db.scalars(select(OptionGroup).where(OptionGroup.id.in_(group_ids))).all()
    if len(groups) != len(set(group_ids)):
        raise HTTPException(status_code=404, detail="Option group not found")
    return groups


def _load_item(db: Session, item_id: int) -> Item:
    item = db.scalars(
        select(Item)
        .where(Item.id == item_id)
        .options(selectinload(Item.option_groups).selectinload(OptionGroup.options))
    ).one()
    return item

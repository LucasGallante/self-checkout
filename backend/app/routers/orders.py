from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models import Order, OrderItem
from app.schemas import OrderDetailOut, OrderOut

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("", response_model=list[OrderOut])
def list_orders(db: Session = Depends(get_db)):
    return db.scalars(select(Order).order_by(Order.id.desc())).all()


@router.get("/{order_id}", response_model=OrderDetailOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.scalars(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.items).selectinload(OrderItem.options))
    ).first()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

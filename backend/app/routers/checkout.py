from datetime import datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Item, Option, Order, OrderItem, OrderItemOption, OrderStatus
from app.schemas import CheckoutRequest, CheckoutResponse

router = APIRouter(tags=["checkout"])


@router.post("/checkout", response_model=CheckoutResponse, status_code=201)
def checkout(payload: CheckoutRequest, db: Session = Depends(get_db)):
    # Idempotency: a repeat of the same key returns the existing order.
    existing = db.scalars(
        select(Order).where(Order.idempotency_key == payload.idempotency_key)
    ).first()
    if existing is not None:
        return CheckoutResponse(order_number=existing.number, total=existing.total)

    if not payload.items:
        raise HTTPException(status_code=400, detail="Order has no items")

    # Re-validate every line against the current menu; never trust the client.
    order_items: list[tuple[Item, int, list[Option]]] = []
    total = 0
    for line in payload.items:
        item = db.get(Item, line.item_id)
        if item is None:
            raise HTTPException(status_code=404, detail=f"Item {line.item_id} not found")
        if item.stock < line.quantity:
            raise HTTPException(
                status_code=409,
                detail=f"Not enough stock for '{item.name}' (only {item.stock} left)",
            )

        options: list[Option] = []
        if line.options:
            options = db.scalars(select(Option).where(Option.id.in_(line.options))).all()
            if len(options) != len(set(line.options)):
                raise HTTPException(status_code=404, detail="Option not found")
            allowed = {g.id for g in item.option_groups}
            if any(o.option_group_id not in allowed for o in options):
                raise HTTPException(status_code=400, detail="Option does not belong to this item")

        unit_price = item.price + sum(o.price_delta for o in options)
        total += unit_price * line.quantity
        order_items.append((item, line.quantity, options))

    # Per-day order number: count of today's orders + 1.
    today_start = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)
    count_today = db.scalar(
        select(func.count()).select_from(Order).where(Order.created_at >= today_start)
    )
    number = (count_today or 0) + 1

    order = Order(
        number=number,
        idempotency_key=payload.idempotency_key,
        status=OrderStatus.PLACED,
        total=total,
    )
    db.add(order)

    # Decrement stock and build snapshot lines, all in the same transaction.
    for item, quantity, options in order_items:
        item.stock -= quantity
        order_item = OrderItem(
            item_id=item.id,
            item_name=item.name,
            quantity=quantity,
            unit_price=item.price + sum(o.price_delta for o in options),
        )
        order.items.append(order_item)
        for option in options:
            order_item.options.append(
                OrderItemOption(
                    option_id=option.id,
                    option_name=option.name,
                    price_delta=option.price_delta,
                )
            )

    db.commit()
    db.refresh(order)
    return CheckoutResponse(order_number=order.number, total=order.total)

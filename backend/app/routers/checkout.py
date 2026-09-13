from collections import Counter
from datetime import datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
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

    # Aggregate demand per item so a single order can't oversell an item
    # across multiple lines.
    demand = Counter()
    for line in payload.items:
        demand[line.item_id] += line.quantity

    # Load and lock each item (SELECT ... FOR UPDATE) so concurrent checkouts
    # serialize on the same rows and can't oversell the last unit.
    items: dict[int, Item] = {}
    for item_id in demand:
        item = db.get(Item, item_id, with_for_update=True)
        if item is None:
            raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
        if item.stock < demand[item_id]:
            raise HTTPException(
                status_code=409,
                detail=f"Not enough stock for '{item.name}' (only {item.stock} left)",
            )
        items[item_id] = item

    # Validate options and compute unit prices once (never trust the client).
    lines: list[tuple[Item, int, list[Option], int]] = []
    total = 0
    for line in payload.items:
        item = items[line.item_id]

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
        lines.append((item, line.quantity, options, unit_price))

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
    for item, quantity, options, unit_price in lines:
        item.stock -= quantity
        order_item = OrderItem(
            item_id=item.id,
            item_name=item.name,
            quantity=quantity,
            unit_price=unit_price,
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

    try:
        db.commit()
    except IntegrityError:
        # A concurrent request with the same idempotency_key committed first;
        # roll back our duplicate and return the existing order.
        db.rollback()
        existing = db.scalars(
            select(Order).where(Order.idempotency_key == payload.idempotency_key)
        ).first()
        if existing is None:
            raise
        return CheckoutResponse(order_number=existing.number, total=existing.total)

    db.refresh(order)
    return CheckoutResponse(order_number=order.number, total=order.total)

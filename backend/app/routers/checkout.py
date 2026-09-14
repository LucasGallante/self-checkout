from collections import Counter
from datetime import datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models import Item, Option, Order, OrderItem, OrderItemOption, OrderStatus
from app.schemas import CheckoutRequest, CheckoutResponse

router = APIRouter(tags=["checkout"])

# Advisory lock key: serializes per-day order-number assignment so concurrent
# checkouts can't compute the same `number`.
_ORDER_NUMBER_LOCK = 7919


def compute_unit_price(item_price: int, options: list[Option]) -> int:
    """Item price + the sum of selected option deltas (integer cents)."""
    return item_price + sum(o.price_delta for o in options)


def _get_existing_order(db: Session, key: str) -> Order | None:
    return db.scalars(select(Order).where(Order.idempotency_key == key)).first()


def _load_and_lock_items(db: Session, demand: Counter) -> dict[int, Item]:
    """Fetch all ordered items in one query with FOR UPDATE, then validate
    availability in memory. Ids are sorted so concurrent checkouts lock rows
    in a consistent order, avoiding deadlocks."""
    item_ids = sorted(demand)
    items = db.scalars(
        select(Item)
        .where(Item.id.in_(item_ids))
        .options(selectinload(Item.option_groups))
        .with_for_update()
    ).all()
    by_id = {item.id: item for item in items}

    missing = [item_id for item_id in item_ids if item_id not in by_id]
    if missing:
        db.rollback()
        raise HTTPException(status_code=404, detail=f"Item {missing[0]} not found")

    for item_id, quantity in demand.items():
        item = by_id[item_id]
        if item.stock < quantity:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail=f"Not enough stock for '{item.name}' (only {item.stock} left)",
            )

    return by_id


def _resolve_options(db: Session, item: Item, option_ids: list[int], options_by_id: dict[int, Option]) -> list[Option]:
    """Validate that each requested option exists and belongs to the item.
    Options are looked up from the pre-fetched map (no per-line query)."""
    if not option_ids:
        return []

    options: list[Option] = []
    for option_id in option_ids:
        option = options_by_id.get(option_id)
        if option is None:
            db.rollback()
            raise HTTPException(status_code=404, detail="Option not found")
        options.append(option)

    allowed = {g.id for g in item.option_groups}
    if any(o.option_group_id not in allowed for o in options):
        db.rollback()
        raise HTTPException(status_code=400, detail="Option does not belong to this item")
    return options


def _next_order_number(db: Session) -> int:
    """Next per-day order number, serialized by an advisory lock. The "day"
    boundary is UTC (deliberate for this demo)."""
    db.execute(select(func.pg_advisory_xact_lock(_ORDER_NUMBER_LOCK)))
    today_start = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)
    count_today = db.scalar(
        select(func.count()).select_from(Order).where(Order.created_at >= today_start)
    )
    return (count_today or 0) + 1


def _to_response(order: Order) -> CheckoutResponse:
    return CheckoutResponse(order_number=order.number, total=order.total)


@router.post("/checkout", response_model=CheckoutResponse, status_code=201)
def checkout(payload: CheckoutRequest, db: Session = Depends(get_db)):
    # Validate input shape before touching the DB.
    if not payload.items:
        raise HTTPException(status_code=400, detail="Order has no items")

    # Fast path: a sequential retry of an already-placed order returns it
    # before we re-validate stock/options against the (now changed) menu.
    existing = _get_existing_order(db, payload.idempotency_key)
    if existing is not None:
        return _to_response(existing)

    # Aggregate demand per item so a single order can't oversell an item
    # across multiple lines.
    demand = Counter()
    for line in payload.items:
        demand[line.item_id] += line.quantity

    items = _load_and_lock_items(db, demand)

    # Fetch every requested option in one query, then validate per line.
    # Skip the query entirely when no line has options (the common case).
    all_option_ids = sorted({oid for line in payload.items for oid in line.options})
    options_by_id = {}
    if all_option_ids:
        options_by_id = {
            o.id: o
            for o in db.scalars(select(Option).where(Option.id.in_(all_option_ids))).all()
        }

    # Validate options and compute unit prices once (never trust the client).
    lines: list[tuple[Item, int, list[Option], int]] = []
    total = 0
    for line in payload.items:
        item = items[line.item_id]
        options = _resolve_options(db, item, line.options, options_by_id)
        unit_price = compute_unit_price(item.price, options)
        total += unit_price * line.quantity
        lines.append((item, line.quantity, options, unit_price))

    order = Order(
        number=_next_order_number(db),
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
        # Backstop for the concurrent duplicate-key race: two requests passed
        # the fast path before either committed. Return the winner's order.
        db.rollback()
        existing = _get_existing_order(db, payload.idempotency_key)
        if existing is None:
            raise
        return _to_response(existing)

    db.refresh(order)
    return _to_response(order)

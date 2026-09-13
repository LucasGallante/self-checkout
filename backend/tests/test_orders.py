from datetime import datetime, timedelta, timezone

from app.models import Order, OrderItem, OrderStatus
from tests.helpers import make_category, make_item, make_option, make_option_group

_key_counter = iter(range(1000))


def _place_order(db, item, quantity=1, options=None):
    key = f"place-{next(_key_counter)}"
    order = Order(number=1, idempotency_key=key, status=OrderStatus.PLACED, total=300)
    line = OrderItem(item_id=item.id, item_name=item.name, quantity=quantity, unit_price=300)
    order.items.append(line)
    db.add(order)
    db.flush()
    return order


def test_list_orders_newest_first(client, db):
    category = make_category(db)
    item = make_item(db, category)
    o1 = _place_order(db, item)
    o2 = _place_order(db, item)
    db.commit()

    res = client.get("/orders")
    assert res.status_code == 200
    ids = [o["id"] for o in res.json()]
    assert ids == [o2.id, o1.id]  # newest first


def test_order_detail_snapshot(client, db):
    category = make_category(db)
    group = make_option_group(db)
    opt = make_option(db, group, name="Almond", price_delta=50)
    item = make_item(db, category, name="Coffee", price=300, groups=[group])
    order = Order(number=1, idempotency_key="x", status=OrderStatus.PLACED, total=350)
    line = OrderItem(item_id=item.id, item_name="Coffee", quantity=1, unit_price=350)
    order.items.append(line)
    db.add(order)
    db.flush()
    db.commit()

    res = client.get(f"/orders/{order.id}")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 350
    assert body["items"][0]["item_name"] == "Coffee"
    assert body["items"][0]["unit_price"] == 350


def test_unknown_order(client):
    assert client.get("/orders/9999").status_code == 404


def test_price_snapshot_survives_edit(client, db):
    """Raising an item's price must not rewrite an already-placed order."""
    category = make_category(db)
    item = make_item(db, category, price=300)
    order = _place_order(db, item)
    db.commit()

    # change the item price via the API
    res = client.patch(f"/menu/items/{item.id}", json={"price": 400})
    assert res.status_code == 200

    # the order's total/unit_price are unchanged
    detail = client.get(f"/orders/{order.id}").json()
    assert detail["total"] == 300
    assert detail["items"][0]["unit_price"] == 300


def test_per_day_numbering(client, db):
    category = make_category(db)
    item = make_item(db, category)

    # First order: number 1
    r1 = client.post("/checkout", json={"idempotency_key": "k1", "items": [{"item_id": item.id, "quantity": 1}]})
    assert r1.json()["order_number"] == 1

    # Second: number 2
    r2 = client.post("/checkout", json={"idempotency_key": "k2", "items": [{"item_id": item.id, "quantity": 1}]})
    assert r2.json()["order_number"] == 2


def test_per_day_numbering_resets(client, db):
    category = make_category(db)
    item = make_item(db, category)

    # Seed an order from "yesterday" so today's count starts at 0.
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    db.add(
        Order(
            number=1,
            idempotency_key="yesterday",
            status=OrderStatus.PLACED,
            total=300,
            created_at=yesterday,
        )
    )
    db.commit()

    r = client.post("/checkout", json={"idempotency_key": "k1", "items": [{"item_id": item.id, "quantity": 1}]})
    assert r.json()["order_number"] == 1

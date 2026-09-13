import threading

from pydantic import ValidationError

from app.models import Order
from app.routers.checkout import checkout, compute_unit_price
from app.schemas import CheckoutRequest
from tests.conftest import TestingSessionLocal
from tests.helpers import make_category, make_item, make_option, make_option_group


def _checkout(client, key, items):
    return client.post("/checkout", json={"idempotency_key": key, "items": items})


def _checkout_direct(key, items):
    """Call the checkout endpoint function directly on a fresh session.

    Used by the concurrency tests: calling the function (not HTTP) lets two
    threads hit the same rows with genuinely independent connections, which is
    what exercises SELECT ... FOR UPDATE and the idempotency unique constraint.
    """
    session = TestingSessionLocal()
    try:
        return checkout(CheckoutRequest(idempotency_key=key, items=items), session)
    finally:
        session.rollback()
        session.close()


def test_happy_path(client, db):
    category = make_category(db)
    item = make_item(db, category, name="Coffee", price=300, stock=5)

    res = _checkout(client, "key-1", [{"item_id": item.id, "quantity": 2, "options": []}])

    assert res.status_code == 201
    body = res.json()
    assert body["order_number"] == 1
    assert body["total"] == 600

    db.expire_all()
    assert db.get(type(item), item.id).stock == 3


def test_options_in_total(client, db):
    category = make_category(db)
    group = make_option_group(db)
    opt = make_option(db, group, name="Almond", price_delta=50)
    item = make_item(db, category, name="Coffee", price=300, stock=5, groups=[group])

    res = _checkout(client, "key-1", [{"item_id": item.id, "quantity": 2, "options": [opt.id]}])

    assert res.status_code == 201
    assert res.json()["total"] == 700  # 2 * (300 + 50)


def test_idempotency_same_key(client, db):
    category = make_category(db)
    item = make_item(db, category, stock=5)

    first = _checkout(client, "key-1", [{"item_id": item.id, "quantity": 1}])
    second = _checkout(client, "key-1", [{"item_id": item.id, "quantity": 1}])

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json() == second.json()

    # only one order, and stock decremented once
    assert db.query(Order).count() == 1
    db.expire_all()
    assert db.get(type(item), item.id).stock == 4


def test_empty_items(client):
    res = _checkout(client, "key-1", [])
    assert res.status_code == 400


def test_unknown_item(client):
    res = _checkout(client, "key-1", [{"item_id": 9999, "quantity": 1}])
    assert res.status_code == 404


def test_unknown_option(client, db):
    category = make_category(db)
    group = make_option_group(db)
    item = make_item(db, category, groups=[group])

    res = _checkout(client, "key-1", [{"item_id": item.id, "quantity": 1, "options": [9999]}])
    assert res.status_code == 404


def test_wrong_group_option(client, db):
    category = make_category(db)
    group_a = make_option_group(db, name="Milk")
    group_b = make_option_group(db, name="Size")
    opt_b = make_option(db, group_b, name="Large", price_delta=100)
    item = make_item(db, category, groups=[group_a])  # only offers Milk

    res = _checkout(client, "key-1", [{"item_id": item.id, "quantity": 1, "options": [opt_b.id]}])
    assert res.status_code == 400


def test_insufficient_stock(client, db):
    category = make_category(db)
    item = make_item(db, category, stock=1)

    res = _checkout(client, "key-1", [{"item_id": item.id, "quantity": 2}])
    assert res.status_code == 409


def test_aggregate_demand_within_order(client, db):
    """Two lines for the same item must be validated against combined demand."""
    category = make_category(db)
    item = make_item(db, category, stock=3)

    res = _checkout(
        client,
        "key-1",
        [{"item_id": item.id, "quantity": 2}, {"item_id": item.id, "quantity": 2}],
    )
    assert res.status_code == 409  # 4 > 3 stock


def test_oversell_concurrency(db):
    """Last unit, two simultaneous checkouts: exactly one succeeds.

    One thread wins the FOR UPDATE lock and commits; the other blocks, then
    sees the decremented stock and returns a 409. Stock must never go negative.
    """
    category = make_category(db)
    item = make_item(db, category, stock=1)
    db.commit()
    item_id = item.id

    outcomes = {}

    def submit(i):
        try:
            res = _checkout_direct(f"key-{i}", [{"item_id": item_id, "quantity": 1}])
            outcomes[i] = (201, res.total)
        except Exception as e:
            # 409s surface as HTTPException
            from fastapi import HTTPException

            outcomes[i] = (getattr(e, "status_code", 500), None)

    threads = [threading.Thread(target=submit, args=(i,)) for i in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    codes = sorted(code for code, _ in outcomes.values())
    assert codes == [201, 409]

    # stock never negative
    db.expire_all()
    assert db.get(type(item), item_id).stock == 0


def test_duplicate_key_concurrency(db):
    """Two simultaneous submits with the same key: one order, no 500."""
    category = make_category(db)
    item = make_item(db, category, stock=10)
    db.commit()
    item_id = item.id

    results = {}

    def submit(i):
        try:
            res = _checkout_direct("same-key", [{"item_id": item_id, "quantity": 1}])
            results[i] = (201, res.order_number, res.total)
        except Exception as e:
            from fastapi import HTTPException

            results[i] = (getattr(e, "status_code", 500), None, None)

    threads = [threading.Thread(target=submit, args=(i,)) for i in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Both should succeed with the SAME order (one inserts, the other returns it)
    assert all(code == 201 for code, _, _ in results.values())
    bodies = [(num, total) for _, num, total in results.values()]
    assert bodies[0] == bodies[1]


# ---- Unit tests (no DB) ----


def _option(price_delta):
    class O:
        pass

    o = O()
    o.price_delta = price_delta
    return o


def test_compute_unit_price():
    assert compute_unit_price(300, []) == 300
    assert compute_unit_price(300, [_option(50)]) == 350
    assert compute_unit_price(300, [_option(50), _option(100)]) == 450
    assert compute_unit_price(300, [_option(0)]) == 300


def test_checkout_schema_validation():
    # valid
    CheckoutRequest(idempotency_key="k", items=[{"item_id": 1, "quantity": 1}])

    # quantity must be > 0
    try:
        CheckoutRequest(idempotency_key="k", items=[{"item_id": 1, "quantity": 0}])
        assert False, "expected ValidationError for quantity <= 0"
    except ValidationError:
        pass

    # empty idempotency_key
    try:
        CheckoutRequest(idempotency_key="", items=[{"item_id": 1, "quantity": 1}])
        assert False, "expected ValidationError for empty key"
    except ValidationError:
        pass

    # >36-char key (after #6)
    try:
        CheckoutRequest(idempotency_key="x" * 37, items=[{"item_id": 1, "quantity": 1}])
        assert False, "expected ValidationError for >36-char key"
    except ValidationError:
        pass


def test_price_schemas_reject_negatives():
    from app.schemas import ItemCreate, OptionCreate

    try:
        ItemCreate(category_id=1, name="x", price=-1)
        assert False, "expected ValidationError for negative price"
    except ValidationError:
        pass

    try:
        OptionCreate(name="x", price_delta=-1)
        assert False, "expected ValidationError for negative price_delta"
    except ValidationError:
        pass

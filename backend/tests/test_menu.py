from app.models import Order, OrderItem, OrderItemOption, OrderStatus
from tests.helpers import make_category, make_item, make_option, make_option_group


def test_category_roundtrip(client):
    # create
    res = client.post("/menu/categories", json={"name": "Food", "sort_order": 1})
    assert res.status_code == 201
    cat_id = res.json()["id"]

    # read
    assert client.get("/menu").json()[0]["name"] == "Food"

    # update
    res = client.patch(f"/menu/categories/{cat_id}", json={"name": "Snacks"})
    assert res.status_code == 200
    assert res.json()["name"] == "Snacks"

    # delete
    assert client.delete(f"/menu/categories/{cat_id}").status_code == 204
    assert client.get("/menu").json() == []


def test_delete_category_with_items_conflicts(client, db):
    category = make_category(db)
    make_item(db, category)
    db.commit()

    res = client.delete(f"/menu/categories/{category.id}")
    assert res.status_code == 409


def test_delete_item_with_option_groups_conflicts(client, db):
    category = make_category(db)
    group = make_option_group(db)
    item = make_item(db, category, groups=[group])
    db.commit()

    res = client.delete(f"/menu/items/{item.id}")
    assert res.status_code == 409


def test_delete_item_attached_group_after_detach(client, db):
    """An item with no option groups and no orders can be deleted."""
    category = make_category(db)
    item = make_item(db, category)
    db.commit()

    assert client.delete(f"/menu/items/{item.id}").status_code == 204


def test_delete_option_group_with_items_conflicts(client, db):
    category = make_category(db)
    group = make_option_group(db)
    make_item(db, category, groups=[group])
    db.commit()

    res = client.delete(f"/menu/option-groups/{group.id}")
    assert res.status_code == 409


def test_delete_option_group_with_options_conflicts(client, db):
    group = make_option_group(db)
    make_option(db, group)
    db.commit()

    res = client.delete(f"/menu/option-groups/{group.id}")
    assert res.status_code == 409


def test_delete_option_group_empty_succeeds(client, db):
    group = make_option_group(db)
    db.commit()

    assert client.delete(f"/menu/option-groups/{group.id}").status_code == 204


def test_create_item_with_option_groups(client, db):
    category = make_category(db)
    group = make_option_group(db)
    db.commit()

    res = client.post(
        "/menu/items",
        json={
            "category_id": category.id,
            "name": "Coffee",
            "price": 300,
            "stock": 5,
            "option_group_ids": [group.id],
        },
    )
    assert res.status_code == 201
    assert [g["name"] for g in res.json()["option_groups"]] == ["Milk"]


def test_delete_item_referenced_by_order_succeeds(client, db):
    """Deleting an item is allowed even if a past order references it —
    the order's snapshots preserve history."""
    category = make_category(db)
    item = make_item(db, category)

    order = Order(number=1, idempotency_key="ref-item", status=OrderStatus.PLACED, total=300)
    line = OrderItem(item_id=item.id, item_name="Coffee", quantity=1, unit_price=300)
    order.items.append(line)
    db.add(order)
    db.commit()

    # The item had no option groups, so it deletes cleanly.
    assert client.delete(f"/menu/items/{item.id}").status_code == 204


def test_delete_option_referenced_by_order_succeeds(client, db):
    """An option on a past order can be deleted; history is snapshotted."""
    category = make_category(db)
    group = make_option_group(db)
    opt = make_option(db, group, name="Almond", price_delta=50)
    item = make_item(db, category, groups=[group])

    order = Order(number=1, idempotency_key="ref-opt", status=OrderStatus.PLACED, total=350)
    line = OrderItem(item_id=item.id, item_name="Coffee", quantity=1, unit_price=350)
    line.options.append(OrderItemOption(option_id=opt.id, option_name="Almond", price_delta=50))
    order.items.append(line)
    db.add(order)
    db.commit()

    assert client.delete(f"/menu/options/{opt.id}").status_code == 204


# ---- Step 1: 404 on update/delete of missing entities ----

def test_update_missing_category(client):
    assert client.patch("/menu/categories/9999", json={"name": "x"}).status_code == 404


def test_delete_missing_category(client):
    assert client.delete("/menu/categories/9999").status_code == 404


def test_update_missing_item(client):
    assert client.patch("/menu/items/9999", json={"name": "x"}).status_code == 404


def test_delete_missing_item(client):
    assert client.delete("/menu/items/9999").status_code == 404


def test_update_missing_option_group(client):
    assert client.patch("/menu/option-groups/9999", json={"name": "x"}).status_code == 404


def test_delete_missing_option_group(client):
    assert client.delete("/menu/option-groups/9999").status_code == 404


def test_update_missing_option(client):
    assert client.patch("/menu/options/9999", json={"name": "x"}).status_code == 404


def test_delete_missing_option(client):
    assert client.delete("/menu/options/9999").status_code == 404


# ---- Step 2: option group + option round-trips ----

def test_option_group_roundtrip(client):
    res = client.post("/menu/option-groups", json={"name": "Milk", "sort_order": 1})
    assert res.status_code == 201
    group_id = res.json()["id"]

    res = client.patch(f"/menu/option-groups/{group_id}", json={"name": "Dairy"})
    assert res.status_code == 200
    assert res.json()["name"] == "Dairy"

    assert client.delete(f"/menu/option-groups/{group_id}").status_code == 204


def test_option_roundtrip(client, db):
    group = make_option_group(db)
    db.commit()

    res = client.post(
        f"/menu/option-groups/{group.id}/options",
        json={"name": "Almond", "price_delta": 50},
    )
    assert res.status_code == 201
    option_id = res.json()["id"]

    res = client.patch(f"/menu/options/{option_id}", json={"price_delta": 100})
    assert res.status_code == 200
    assert res.json()["price_delta"] == 100

    assert client.delete(f"/menu/options/{option_id}").status_code == 204


def test_create_option_unknown_group(client):
    res = client.post("/menu/option-groups/9999/options", json={"name": "Almond"})
    assert res.status_code == 404


# ---- Step 3: item update reassigns groups + unknown group ----

def test_update_item_reassigns_groups(client, db):
    category = make_category(db)
    group_a = make_option_group(db, name="Milk")
    group_b = make_option_group(db, name="Size")
    item = make_item(db, category, groups=[group_a])
    db.commit()

    res = client.patch(
        f"/menu/items/{item.id}",
        json={"option_group_ids": [group_b.id]},
    )
    assert res.status_code == 200
    assert [g["name"] for g in res.json()["option_groups"]] == ["Size"]


def test_update_item_unknown_group(client, db):
    category = make_category(db)
    item = make_item(db, category)
    db.commit()

    res = client.patch(f"/menu/items/{item.id}", json={"option_group_ids": [9999]})
    assert res.status_code == 404


# ---- Step 4: item create/update with unknown category ----

def test_create_item_unknown_category(client):
    res = client.post(
        "/menu/items", json={"category_id": 9999, "name": "x", "price": 100, "stock": 5}
    )
    assert res.status_code == 404


def test_update_item_unknown_category(client, db):
    category = make_category(db)
    item = make_item(db, category)
    db.commit()

    res = client.patch(f"/menu/items/{item.id}", json={"category_id": 9999})
    assert res.status_code == 404

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


def test_delete_option_referenced_by_order_conflicts(client, db):
    """An option that appears on a past order can't be deleted."""
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

    res = client.delete(f"/menu/options/{opt.id}")
    assert res.status_code == 409

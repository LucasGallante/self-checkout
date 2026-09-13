"""Shared factories for building menu/order fixtures via the ORM."""

from app.models import Category, Item, Option, OptionGroup


def make_category(db, name="Food", sort_order=1, description=""):
    category = Category(name=name, sort_order=sort_order, description=description)
    db.add(category)
    db.flush()
    return category


def make_option_group(db, name="Milk", sort_order=1):
    group = OptionGroup(name=name, sort_order=sort_order)
    db.add(group)
    db.flush()
    return group


def make_option(db, group, name="Whole", price_delta=0):
    option = Option(option_group_id=group.id, name=name, price_delta=price_delta)
    db.add(option)
    db.flush()
    return option


def make_item(db, category, name="Coffee", price=300, stock=10, groups=None):
    item = Item(
        category_id=category.id,
        name=name,
        description="",
        price=price,
        stock=stock,
    )
    if groups:
        item.option_groups = groups
    db.add(item)
    db.flush()
    return item

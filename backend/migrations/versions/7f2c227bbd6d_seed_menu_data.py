"""seed menu data

Revision ID: 7f2c227bbd6d
Revises: e3362ba5df3d
Create Date: 2026-09-12 15:16:34.434709

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '7f2c227bbd6d'
down_revision: Union[str, Sequence[str], None] = 'e3362ba5df3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed two categories with items and option groups."""
    bind = op.get_bind()

    def insert(table: str, columns: list[str], returning: str | None = "id", **values):
        cols = ", ".join(columns)
        placeholders = ", ".join(f":{c}" for c in columns)
        returning_clause = f" RETURNING {returning}" if returning else ""
        result = bind.execute(
            sa.text(f"INSERT INTO {table} ({cols}) VALUES ({placeholders}){returning_clause}"),
            values,
        )
        return result.scalar_one() if returning else None

    # ---- categories ----
    food_id = insert(
        "categories", ["name", "description", "sort_order"],
        name="Food", description="Snacks and mains", sort_order=1,
    )
    drinks_id = insert(
        "categories", ["name", "description", "sort_order"],
        name="Drinks", description="Cold and hot beverages", sort_order=2,
    )

    # ---- option groups ----
    bread_group = insert(
        "option_groups", ["name", "sort_order"], name="Bread", sort_order=1,
    )
    extras_group = insert(
        "option_groups", ["name", "sort_order"], name="Extras", sort_order=1,
    )
    dip_group = insert(
        "option_groups", ["name", "sort_order"], name="Dip", sort_order=1,
    )

    # ---- options ----
    # Bread: 3 options
    insert("options", ["option_group_id", "name", "price_delta"],
           option_group_id=bread_group, name="White", price_delta=0)
    insert("options", ["option_group_id", "name", "price_delta"],
           option_group_id=bread_group, name="Whole wheat", price_delta=0)
    insert("options", ["option_group_id", "name", "price_delta"],
           option_group_id=bread_group, name="Sourdough", price_delta=100)

    # Extras: 2 options
    insert("options", ["option_group_id", "name", "price_delta"],
           option_group_id=extras_group, name="Cheese", price_delta=100)
    insert("options", ["option_group_id", "name", "price_delta"],
           option_group_id=extras_group, name="Bacon", price_delta=150)

    # Dip: 1 option
    insert("options", ["option_group_id", "name", "price_delta"],
           option_group_id=dip_group, name="Cheese sauce", price_delta=100)

    # ---- items (Food) ----
    sandwich_id = insert(
        "items", ["category_id", "name", "description", "price", "stock"],
        category_id=food_id, name="Sandwich", description="Ham and cheese on fresh bread",
        price=650, stock=20,
    )
    insert("item_option_group", ["item_id", "option_group_id"], returning=None,
           item_id=sandwich_id, option_group_id=bread_group)

    burger_id = insert(
        "items", ["category_id", "name", "description", "price", "stock"],
        category_id=food_id, name="Burger", description="Beef patty with lettuce and tomato",
        price=800, stock=15,
    )
    insert("item_option_group", ["item_id", "option_group_id"], returning=None,
           item_id=burger_id, option_group_id=extras_group)

    fries_id = insert(
        "items", ["category_id", "name", "description", "price", "stock"],
        category_id=food_id, name="Fries", description="Crispy golden fries",
        price=350, stock=30,
    )
    insert("item_option_group", ["item_id", "option_group_id"], returning=None,
           item_id=fries_id, option_group_id=dip_group)

    insert(
        "items", ["category_id", "name", "description", "price", "stock"],
        category_id=food_id, name="Salad", description="Garden salad with vinaigrette",
        price=500, stock=10,
    )

    # ---- items (Drinks) ----
    insert(
        "items", ["category_id", "name", "description", "price", "stock"],
        category_id=drinks_id, name="Coffee", description="Hot brewed coffee",
        price=300, stock=50,
    )
    insert(
        "items", ["category_id", "name", "description", "price", "stock"],
        category_id=drinks_id, name="Iced Tea", description="Freshly brewed iced tea",
        price=250, stock=40,
    )
    insert(
        "items", ["category_id", "name", "description", "price", "stock"],
        category_id=drinks_id, name="Soda", description="Chilled soda",
        price=200, stock=60,
    )
    insert(
        "items", ["category_id", "name", "description", "price", "stock"],
        category_id=drinks_id, name="Water", description="Bottled water",
        price=150, stock=100,
    )


def downgrade() -> None:
    """Remove the seeded menu (everything belongs to categories Food/Drinks)."""
    bind = op.get_bind()

    # Delete in FK-dependency order: joins, options, groups, items, categories.
    bind.execute(
        sa.text(
            "DELETE FROM item_option_group WHERE option_group_id IN "
            "(SELECT id FROM option_groups WHERE name IN ('Bread', 'Extras', 'Dip'))"
        )
    )
    bind.execute(
        sa.text(
            "DELETE FROM options WHERE option_group_id IN "
            "(SELECT id FROM option_groups WHERE name IN ('Bread', 'Extras', 'Dip'))"
        )
    )
    bind.execute(
        sa.text("DELETE FROM option_groups WHERE name IN ('Bread', 'Extras', 'Dip')")
    )
    bind.execute(
        sa.text(
            "DELETE FROM items WHERE category_id IN "
            "(SELECT id FROM categories WHERE name IN ('Food', 'Drinks'))"
        )
    )
    bind.execute(sa.text("DELETE FROM categories WHERE name IN ('Food', 'Drinks')"))

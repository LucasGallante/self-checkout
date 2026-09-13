"""order tables reference items/options by id, not FK

Revision ID: 8bd0dac054e0
Revises: a07f0b21cd48
Create Date: 2026-09-13 18:27:15.676084

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8bd0dac054e0'
down_revision: Union[str, Sequence[str], None] = 'a07f0b21cd48'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop FKs so order history survives menu item/option deletion."""
    op.drop_constraint("order_items_item_id_fkey", "order_items", type_="foreignkey")
    op.drop_constraint("order_item_options_option_id_fkey", "order_item_options", type_="foreignkey")


def downgrade() -> None:
    """Re-add the FKs (restores referential integrity)."""
    op.create_foreign_key(
        "order_items_item_id_fkey", "order_items", "items", ["item_id"], ["id"]
    )
    op.create_foreign_key(
        "order_item_options_option_id_fkey",
        "order_item_options",
        "options",
        ["option_id"],
        ["id"],
    )

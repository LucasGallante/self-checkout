"""add item image urls

Revision ID: a07f0b21cd48
Revises: 7f2c227bbd6d
Create Date: 2026-09-12 15:26:05.393493

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a07f0b21cd48'
down_revision: Union[str, Sequence[str], None] = '7f2c227bbd6d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


IMAGE_URLS = {
    "Sandwich": "https://images.unsplash.com/photo-1528735602780-2552fd46c7af?w=800&q=80",
    "Burger": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=800&q=80",
    "Fries": "https://images.unsplash.com/photo-1573080496219-bb080dd4f877?w=800&q=80",
    "Salad": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=800&q=80",
    "Coffee": "https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=800&q=80",
    "Iced Tea": "https://images.unsplash.com/photo-1499636136210-6f4ee915583e?w=800&q=80",
    "Soda": "https://images.unsplash.com/photo-1554866585-cd94860890b7?w=800&q=80",
    "Water": "https://images.unsplash.com/photo-1548839140-29a749e1cf4d?w=800&q=80",
}


def upgrade() -> None:
    bind = op.get_bind()
    for name, url in IMAGE_URLS.items():
        bind.execute(
            sa.text("UPDATE items SET image_url = :url WHERE name = :name"),
            {"url": url, "name": name},
        )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("UPDATE items SET image_url = NULL"))

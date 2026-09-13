from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class OrderStatus(str, enum.Enum):
    PLACED = "PLACED"
    COMPLETED = "COMPLETED"


# many-to-many join: which option groups an item offers
item_option_group = Table(
    "item_option_group",
    Base.metadata,
    Column("item_id", ForeignKey("items.id"), primary_key=True),
    Column("option_group_id", ForeignKey("option_groups.id"), primary_key=True),
)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(default=0)  # lower first

    items: Mapped[list["Item"]] = relationship(back_populates="category")


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")
    image_url: Mapped[str | None] = mapped_column(String(500))
    price: Mapped[int] = mapped_column()  # integer cents
    stock: Mapped[int] = mapped_column(default=0)  # 0 = sold out

    category: Mapped["Category"] = relationship(back_populates="items")
    option_groups: Mapped[list["OptionGroup"]] = relationship(
        secondary=item_option_group, back_populates="items"
    )
    order_items: Mapped[list["OrderItem"]] = relationship(back_populates="item")


class OptionGroup(Base):
    __tablename__ = "option_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    sort_order: Mapped[int] = mapped_column(default=0)  # global priority

    items: Mapped[list["Item"]] = relationship(
        secondary=item_option_group, back_populates="option_groups"
    )
    options: Mapped[list["Option"]] = relationship(back_populates="option_group")


class Option(Base):
    __tablename__ = "options"

    id: Mapped[int] = mapped_column(primary_key=True)
    option_group_id: Mapped[int] = mapped_column(ForeignKey("option_groups.id"))
    name: Mapped[str] = mapped_column(String(100))
    image_url: Mapped[str | None] = mapped_column(String(500))
    price_delta: Mapped[int] = mapped_column(default=0)  # non-negative upcharge

    option_group: Mapped["OptionGroup"] = relationship(back_populates="options")
    order_item_options: Mapped[list["OrderItemOption"]] = relationship(back_populates="option")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[int] = mapped_column()  # count of orders placed today
    idempotency_key: Mapped[str] = mapped_column(String(36), unique=True)
    status: Mapped[OrderStatus] = mapped_column(default=OrderStatus.PLACED)
    total: Mapped[int] = mapped_column(default=0)  # integer cents
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    items: Mapped[list["OrderItem"]] = relationship(back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"))
    item_name: Mapped[str] = mapped_column(String(100))  # snapshot at order time
    quantity: Mapped[int] = mapped_column()
    unit_price: Mapped[int] = mapped_column()  # snapshot: item price + option deltas

    order: Mapped["Order"] = relationship(back_populates="items")
    item: Mapped["Item"] = relationship(back_populates="order_items")
    options: Mapped[list["OrderItemOption"]] = relationship(back_populates="order_item")


class OrderItemOption(Base):
    __tablename__ = "order_item_options"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_item_id: Mapped[int] = mapped_column(ForeignKey("order_items.id"))
    option_id: Mapped[int] = mapped_column(ForeignKey("options.id"))
    option_name: Mapped[str] = mapped_column(String(100))  # snapshot
    price_delta: Mapped[int] = mapped_column(default=0)  # snapshot

    order_item: Mapped["OrderItem"] = relationship(back_populates="options")
    option: Mapped["Option"] = relationship(back_populates="order_item_options")

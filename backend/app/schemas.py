from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import OrderStatus


# ---- Menu (responses) ----

class OptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    image_url: str | None
    price_delta: int


class OptionGroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    sort_order: int
    options: list[OptionOut]


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    image_url: str | None
    price: int
    stock: int
    option_groups: list[OptionGroupOut]


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    sort_order: int
    items: list[ItemOut]


# ---- Menu (requests) ----

class CategoryCreate(BaseModel):
    name: str
    description: str = ""
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    sort_order: int | None = None


class ItemCreate(BaseModel):
    category_id: int
    name: str
    description: str = ""
    image_url: str | None = None
    price: int = Field(ge=0)
    stock: int = Field(ge=0)
    option_group_ids: list[int] = []


class ItemUpdate(BaseModel):
    category_id: int | None = None
    name: str | None = None
    description: str | None = None
    image_url: str | None = None
    price: int | None = Field(default=None, ge=0)
    stock: int | None = Field(default=None, ge=0)
    option_group_ids: list[int] | None = None


class OptionGroupCreate(BaseModel):
    name: str
    sort_order: int = 0


class OptionGroupUpdate(BaseModel):
    name: str | None = None
    sort_order: int | None = None


class OptionCreate(BaseModel):
    name: str
    image_url: str | None = None
    price_delta: int = Field(default=0, ge=0)


class OptionUpdate(BaseModel):
    name: str | None = None
    image_url: str | None = None
    price_delta: int | None = Field(default=None, ge=0)


# ---- Checkout ----

class CheckoutItem(BaseModel):
    item_id: int
    quantity: int = Field(gt=0)
    options: list[int] = []


class CheckoutRequest(BaseModel):
    idempotency_key: str = Field(min_length=1, max_length=36)
    items: list[CheckoutItem]


class CheckoutResponse(BaseModel):
    order_number: int
    total: int


# ---- Orders ----

class OrderItemOptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    option_name: str
    price_delta: int


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    item_name: str
    quantity: int
    unit_price: int
    options: list[OrderItemOptionOut]


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: int
    status: OrderStatus
    total: int
    created_at: datetime


class OrderDetailOut(OrderOut):
    items: list[OrderItemOut]

from fastapi import FastAPI

from app.routers import checkout, menu, orders

app = FastAPI(title="Self-Checkout API")

app.include_router(menu.router)
app.include_router(checkout.router)
app.include_router(orders.router)


@app.get("/")
def hello():
    return {"message": "Self-checkout API is running"}

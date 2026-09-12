from fastapi import FastAPI

app = FastAPI(title="Self-Checkout API")


@app.get("/")
def hello():
    return {"message": "Self-checkout API is running"}

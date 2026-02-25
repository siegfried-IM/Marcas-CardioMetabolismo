from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import (
    agreements,
    brands,
    budget,
    channels,
    ddd,
    kpis,
    market,
    prescriptions,
    prices,
    stock,
)

app = FastAPI(title="Siegfried BI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(brands.router, prefix="/api/v1")
app.include_router(budget.router, prefix="/api/v1")
app.include_router(market.router, prefix="/api/v1")
app.include_router(prescriptions.router, prefix="/api/v1")
app.include_router(channels.router, prefix="/api/v1")
app.include_router(agreements.router, prefix="/api/v1")
app.include_router(prices.router, prefix="/api/v1")
app.include_router(stock.router, prefix="/api/v1")
app.include_router(kpis.router, prefix="/api/v1")
app.include_router(ddd.router, prefix="/api/v1")

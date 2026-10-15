import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.auth import database_models
from app.api.dashboard import router as dashboard_router
from app.auth.routes import router as auth_router
from app.api.analytics import router as analytics_router
from app.api.sales import router as sales_router
from app.api.dashboard_insights import router as dashboard_insights_router

from app.auth import database_models

Base.metadata.create_all(bind=engine)

app = FastAPI()

frontend_url = os.getenv("FRONTEND_URL", "").strip().rstrip("/")

allowed_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
]

if frontend_url:
    allowed_origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "MarketMind AI API is running"}


app.include_router(dashboard_router)
app.include_router(auth_router)
app.include_router(analytics_router)
app.include_router(sales_router)
app.include_router(dashboard_insights_router)


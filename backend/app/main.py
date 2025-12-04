from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.api import routes, auth_routes

# Створюємо всі таблиці
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Routing Parallel Web System",
    version="1.0.0",
)

# CORS (для фронтенду на localhost:5173/3000 тощо)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # для диплому можна так
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Маршрути
app.include_router(auth_routes.router, prefix="/api")
app.include_router(routes.router, prefix="/api")

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.ext.asyncio import AsyncEngine
from sqladmin import Admin

from packages.common_settings import settings
from packages.db.database import Database
from packages.app_state import AppState
from backend.app.api.routers import api_router
from backend.app.admin.views import AdminAuth, setup_admin
from packages.db.migrate_and_seed import run_migrations, ensure_admin
from bot.app.utils.logging_config import setup_logging

setup_logging()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1) DB
    state = AppState(
        db=Database(
            db_url=settings.db.sqlalchemy_url(),
            echo=settings.debug,
            pool_recycle=settings.db.pool_recycle,
            pool_pre_ping=settings.db.pool_pre_ping,
        ),
        cleanup_task=None,
    )
    app.state.app_state = state
    engine: AsyncEngine = state.db.engine
    logger.info('БД загружена')
    # 2) Миграции и сид админа ДО инициализации админки
    if settings.db.run_migrations_on_startup:
        await run_migrations(
            db_url=settings.db.sqlalchemy_url().render_as_string(
                hide_password=False
            )
        )
        logger.info('Миграция выполнена')
    await ensure_admin(state.db)

    # 3) SQLAdmin c auth
    authentication_backend = AdminAuth(
        state.db,
        secret_key=settings.security.password_pepper.get_secret_value()
    )
    admin = Admin(app, engine, authentication_backend=authentication_backend)
    setup_admin(admin)
    logger.info('Админка загружена')

    try:
        yield
    finally:
        engine.dispose()


app = FastAPI(
    title="Recipes Backend",
    debug=settings.debug,
    lifespan=lifespan,
)

# Session cookie для SQLAdmin auth
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.security.password_pepper.get_secret_value()
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API
app.include_router(api_router, prefix="/api")


@app.get("/ping", tags=["health"])
async def ping():
    return {"ok": True}

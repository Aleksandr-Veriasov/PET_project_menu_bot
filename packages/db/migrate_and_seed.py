# packages/db/migrate_and_seed.py
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from alembic import command
from alembic.config import Config
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.common_settings.settings import settings
from packages.db.database import Database
from packages.db.models import Admin  # <-- ваша модель Admin (см. ранее)
from packages.security.passwords import hash_password

ALEMBIC_INI_PATH = Path('alembic.ini')  # скорректируйте путь при необходимости
MIGRATIONS_PATH = Path('packages/db/migrations')


def _make_alembic_config(db_url: str) -> Config:
    cfg = Config(str(ALEMBIC_INI_PATH))
    cfg.set_main_option('script_location', str(MIGRATIONS_PATH))
    cfg.set_main_option('sqlalchemy.url', db_url)
    return cfg


async def run_migrations(db_url: str) -> None:
    """
    Программно выполняет alembic upgrade head.
    Alembic API синхронный — запускаем в отдельном потоке.
    """
    cfg = _make_alembic_config(db_url)
    await asyncio.to_thread(command.upgrade, cfg, 'head')


async def ensure_admin(db: Database) -> None:
    """
    Создаёт администратора из settings, если его ещё нет.
    Не делает ничего, если логин/пароль не заданы или флаг отключён.
    """
    adm = settings.admin
    if not adm.create_on_startup or not adm.login or not adm.password:
        return

    async with db.session() as session:  # AsyncSession
        await _ensure_admin_in_session(
            session, adm.login, adm.password.get_secret_value()
        )


async def _ensure_admin_in_session(
        session: AsyncSession, login: str, raw_password: str
) -> None:
    # Ищем по логину
    res = await session.execute(select(Admin).where(Admin.login == login))
    existing: Optional[Admin] = res.scalar_one_or_none()
    if existing:
        return

    # Создаём
    admin = Admin(login=login, password_hash=hash_password(raw_password))
    session.add(admin)
    await session.commit()

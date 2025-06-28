from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Optional, Generator
from contextlib import contextmanager
import logging

from app.core.settings import settings

logger = logging.getLogger(__name__)


class Database:
    """
    Класс для управления подключением к базе данных и сессиями SQLAlchemy.

    Позволяет создать движок по URL или использовать переданный engine.
    Предоставляет методы для получения сессии и работы с контекстным
    менеджером.

    Используется как в продакшене, так и в тестах (с подменой engine).
    """

    def __init__(
            self, db_url: Optional[str] = None, engine: Optional[Engine] = None
    ):
        if engine is not None:
            self.engine = engine
        elif db_url is not None:
            self.engine = create_engine(
                db_url, pool_pre_ping=True, pool_recycle=1800
            )
        else:
            raise ValueError('Укажите db_url или engine')

        self.SessionLocal = sessionmaker(
            bind=self.engine, expire_on_commit=False
        )
        logger.info('🚀 Движок базы данных создан')

    def get_session(self) -> Session:
        logger.info('💾 Создана сессия базы данных')
        return self.SessionLocal()

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        db_session = self.get_session()
        try:
            yield db_session
            db_session.commit()
        except Exception as e:
            logger.error(f'❌ Ошибка в сессии БД: {e}')
            db_session.rollback()
            raise
        finally:
            db_session.close()
            logger.info('🔒 Сессия базы данных закрыта')


# Использование для основного кода:
db = Database(db_url=settings.database_url)

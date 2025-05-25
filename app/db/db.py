import logging
import os
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()
print('DATABASE_URL now =', os.getenv('DATABASE_URL'))

logger = logging.getLogger(__name__)


def get_engine(database_url=None):
    # Создаём движок базы данных
    if database_url is None:
        database_url = os.getenv('DATABASE_URL')  # Основная база данных
        logger.info('База данных загружена')
    return create_engine(database_url, pool_pre_ping=True, pool_recycle=1800)


def get_session(engine) -> Session:
    # Создаём сессию для работы с базой данных
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    logger.info('Создана сессия базы данных')
    return session_factory()


@contextmanager
def get_session_context():
    ''' Контекстный менеджер для работы с сессией базы данных. '''
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        logger.error(f'Ошибка в контексте сессии: {e}')
        session.rollback()
        raise
    finally:
        session.close()
        logger.info('Сессия базы данных закрыта')

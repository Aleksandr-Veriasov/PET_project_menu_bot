import logging
import os

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
    return create_engine(database_url, pool_pre_ping=True)


def get_session(engine) -> Session:
    # Создаём сессию для работы с базой данных
    session_factory = sessionmaker(bind=engine)
    logger.info('Создана сессия базы данных')
    return session_factory()

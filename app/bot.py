import logging
import os
import sys

from dotenv import load_dotenv
from telegram.ext import Application

from app.db import get_engine
from app.handlers import setup_handlers
from app.models import Base

logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('project.log', encoding='utf-8'),
        ]
    )
logger = logging.getLogger(__name__)


def initialize_database(engine=None) -> None:
    # Создаём движок базы данных
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(bind=engine)


def create_app(engine=None) -> Application:
    # Загружаем токен из .env
    load_dotenv()
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    if not TOKEN:
        raise ValueError('TELEGRAM_BOT_TOKEN не найден в .env файле')
    # Создаём бота
    app = Application.builder().token(TOKEN or '').build()

    # Регистрация хандлеров
    setup_handlers(app)

    # Инициализация базы данных
    initialize_database(engine)

    return app


if __name__ == '__main__':
    # Создаём и запускаем бота
    try:
        app = create_app()
        logger.info('Бот запущен...')
        app.run_polling()
    except Exception as e:
        logger.error(f'Ошибка при запуске бота: {e}')

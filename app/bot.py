import logging
import os
import sys
import asyncio

from dotenv import load_dotenv
from telegram.ext import Application

from app.db.db import get_engine
from app.db.models import Base
from app.handlers.setup import setup_handlers
from app.media.video_downloader import cleanup_old_videos

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)


def initialize_database(engine=None) -> None:
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(bind=engine)


def create_app(engine=None) -> Application:
    load_dotenv()
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    if not TOKEN:
        raise ValueError('TELEGRAM_BOT_TOKEN не найден в .env файле')

    app = Application.builder().token(TOKEN).build()
    setup_handlers(app)
    initialize_database(engine)

    return app


async def main():
    try:
        app = create_app()
        asyncio.create_task(cleanup_old_videos())  # запускаем фоновую очистку
        logger.info('Бот запущен...')
        await app.run_polling()
    except Exception as e:
        logger.error(f'Ошибка при запуске бота: {e}')


if __name__ == '__main__':
    asyncio.run(main())

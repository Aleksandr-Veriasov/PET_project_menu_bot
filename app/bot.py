import asyncio
import logging
import os
import sys
from logtail import LogtailHandler

from dotenv import load_dotenv
from sqlalchemy.orm import close_all_sessions
from telegram.ext import Application

from app.db.db import get_engine
from app.db.models import Base
from app.handlers.setup import setup_handlers
from app.media.video_downloader import cleanup_old_videos

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Logtail handler (отправка в Better Stack)
logtail_token = os.getenv("LOGTAIL_TOKEN")
if logtail_token:
    logtail_handler = LogtailHandler(source_token=logtail_token)
    logger.addHandler(logtail_handler)
else:
    logger.warning("⚠️ Переменная окружения LOGTAIL_TOKEN не найдена")

# Стандартный вывод в консоль
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
logger.addHandler(stream_handler)
cleanup_task: asyncio.Task | None = None


def initialize_database(engine=None) -> None:
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(bind=engine)


def create_app(engine=None) -> Application:
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    if not TOKEN:
        raise ValueError('TELEGRAM_BOT_TOKEN не найден в .env файле')

    async def on_startup(app: Application):
        global cleanup_task
        logger.info('Запускаем фоновую задачу очистки видео...')
        cleanup_task = asyncio.create_task(cleanup_old_videos())

    async def on_shutdown(app: Application):
        global cleanup_task
        if cleanup_task and not cleanup_task.done():
            logger.info('Останавливаем фоновую задачу...')
            cleanup_task.cancel()
            try:
                await cleanup_task
            except asyncio.CancelledError:
                logger.info('Фоновая задача остановлена.')

        # Закрываем SQLAlchemy-сессии
        logger.info('Закрываем все SQLAlchemy-сессии...')
        close_all_sessions()

    app = (
        Application.builder().
        token(TOKEN).
        post_init(on_startup).
        post_shutdown(on_shutdown).
        build()
    )

    setup_handlers(app)
    initialize_database(engine)

    return app


if __name__ == '__main__':
    try:
        app = create_app()
        logger.info('Бот запущен...')
        app.run_polling()
    except Exception as e:
        logger.exception(f'Ошибка при запуске бота {e}')

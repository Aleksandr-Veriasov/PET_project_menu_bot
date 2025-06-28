import asyncio
import logging

from sqlalchemy.orm import close_all_sessions
from telegram.ext import Application

from app.utils.logging_config import setup_logging
from app.core.settings import settings
from app.db.db import db
from app.db.models import Base
from app.handlers.setup import setup_handlers
from app.media.video_downloader import cleanup_old_videos

setup_logging()
logger = logging.getLogger(__name__)
cleanup_task: asyncio.Task | None = None


def initialize_database() -> None:
    '''Создание таблиц, если они ещё не существуют.'''
    engine = db.engine
    Base.metadata.create_all(bind=engine)
    logger.info('📦 Таблицы базы данных инициализированы')


def create_app() -> Application:
    if not settings.telegram_token:
        raise ValueError('❌ TELEGRAM_BOT_TOKEN отсутствует в конфигурации.')

    async def on_startup(app: Application):
        global cleanup_task
        logger.info('🚀 Запускаем фоновую задачу очистки видео...')
        cleanup_task = asyncio.create_task(cleanup_old_videos())

    async def on_shutdown(app: Application):
        global cleanup_task
        if cleanup_task and not cleanup_task.done():
            logger.info('⛔ Останавливаем фоновую задачу...')
            cleanup_task.cancel()
            try:
                await cleanup_task
            except asyncio.CancelledError:
                logger.info('✅ Фоновая задача остановлена.')

        logger.info('🧹 Закрываем все SQLAlchemy-сессии...')
        close_all_sessions()

    app = (
        Application.builder()
        .token(settings.telegram_token)
        .post_init(on_startup)
        .post_shutdown(on_shutdown)
        .build()
    )

    setup_handlers(app)
    initialize_database()

    return app


if __name__ == '__main__':
    try:
        app = create_app()
        logger.info('🤖 Бот запущен и работает...')
        app.run_polling()
    except Exception as e:
        logger.exception(f'🔥 Ошибка при запуске бота: {e}')

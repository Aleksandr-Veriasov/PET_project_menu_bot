import asyncio
import logging
import os
import sys

from dotenv import load_dotenv
from sqlalchemy.orm import close_all_sessions
from telegram.ext import Application, ContextTypes, CommandHandler
import sentry_sdk
from sentry_sdk import capture_exception
from sentry_sdk.integrations.httpx import HttpxIntegration
from telegram import Update

from app.db.db import get_engine
from app.db.models import Base
from app.handlers.setup import setup_handlers
from app.media.video_downloader import cleanup_old_videos

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(asctime)s - %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)

sentry_sdk.init(
    dsn="https://a497c568b2d4ef6931a422f27f48d879@o4509428615872512.ingest.de.sentry.io/4509428632387664",
    # Add data like request headers and IP for users,
    # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
    send_default_pii=True,
    environment="production",
    traces_sample_rate=1.0,
    integrations=[HttpxIntegration()],
)


async def test_error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Тестовая команда для проверки Sentry."""
    try:
        # Намеренно вызываем ошибку
        division_by_zero = 1 / 0
        await update.message.reply_text("Это сообщение не отправится")
    except Exception as e:
        capture_exception(e)
        await update.message.reply_text("⚠ Произошла ошибка. Разработчик уже уведомлен.")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Глобальный обработчик ошибок."""
    logger.error("Ошибка в обработчике: %s", context.error, exc_info=True)
    capture_exception(context.error)

    # Отправляем сообщение пользователю, если это возможно
    if isinstance(update, Update) and update.message:
        await update.message.reply_text("⚠ Произошла ошибка. Разработчик уже уведомлен.")

cleanup_task: asyncio.Task | None = None


def initialize_database(engine=None) -> None:
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(bind=engine)


def create_app(engine=None) -> Application:
    load_dotenv()
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    if not TOKEN:
        raise ValueError('TELEGRAM_BOT_TOKEN не найден в .env файле')

    async def on_startup(app: Application):
        global cleanup_task
        logger.info('Запускаем фоновую задачу очистки видео...')
        cleanup_task = asyncio.create_task(cleanup_old_videos())

        # Добавляем тестовую команду
        app.add_handler(CommandHandler("test_error", test_error))

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
    app.add_error_handler(error_handler)
    initialize_database(engine)

    return app


if __name__ == '__main__':
    try:
        app = create_app()
        logger.info('Бот запущен...')
        app.run_polling()
    except Exception as e:
        logger.exception(f'Ошибка при запуске бота {e}')

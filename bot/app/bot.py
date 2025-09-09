import asyncio
import logging
from contextlib import suppress
from typing import Optional, cast

from telegram.ext import Application

from bot.app.core.types import AppState, PTBApp
from bot.app.handlers.setup import setup_handlers
from packages.common_settings.settings import settings
from packages.db.database import Database
from packages.db.models import Base
from packages.media.video_downloader import cleanup_old_videos
from packages.redis.redis_conn import close_redis, get_redis

logger = logging.getLogger(__name__)


def create_app() -> PTBApp:
    # 1) Конфигурация и секреты
    token = settings.telegram.bot_token.get_secret_value().strip()
    if not token:
        raise ValueError('❌ TELEGRAM_BOT_TOKEN пуст.')

    # 2) Сборка зависимостей (composition root)
    state = AppState(
        db=Database(
            db_url=settings.db.sqlalchemy_url(),
            echo=settings.debug,
            pool_recycle=settings.db.pool_recycle,
            pool_pre_ping=settings.db.pool_pre_ping,
        ),
        cleanup_task=None,  # поле в контейнере, держим тут
    )

    # 3) Callbacks старта/остановки
    async def on_startup(app: PTBApp) -> None:
        # кладём контейнер в bot_data
        # (делаем это в post_init, когда app уже есть)
        app.bot_data['state'] = state
        state.redis = await get_redis()
        pong = await state.redis.ping()
        logger.info('🧠 Redis подключён, PING=%s', pong)

        logger.info('🚀 Запускаем фоновую задачу очистки видео…')
        state.cleanup_task = asyncio.create_task(cleanup_old_videos())

        # первичный bootstrap схемы: включаем только осознанно
        if settings.db.bootstrap_schema:
            await state.db.create_all(Base.metadata)

        ok = await state.db.healthcheck()
        if not ok:
            raise RuntimeError('DB healthcheck failed at startup')

        if settings.telegram.use_webhook:
            url = settings.webhooks.url()
            secret = settings.webhooks.secret_token.get_secret_value()
            await app.bot.set_webhook(
                url=url,
                secret_token=secret,
                drop_pending_updates=True,
                allowed_updates=['message', 'callback_query', 'inline_query'],
            )
            logger.info('🔗 Webhook установлен: %s', url)

    async def on_shutdown(app: PTBApp) -> None:
        # Остановить фоновые задачи
        # достаём контейнер и корректно гасим ресурсы
        cur_state: AppState = app.bot_data['state']

        task: Optional[asyncio.Task[None]] = cur_state.cleanup_task
        if task and not task.done():
            logger.info('⛔ Останавливаем фоновую задачу…')
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
            logger.info('✅ Фоновая задача остановлена.')

        # Закрыть Redis
        if cur_state.redis is not None:
            await close_redis()
            cur_state.redis = None
            logger.info('🔒 Redis соединения закрыты.')

        cur_state.db.dispose()
        logger.info('🔒 Соединения БД закрыты.')

    # 4) Сборка Application
    def build_app(token: str) -> PTBApp:
        return cast(
            PTBApp,
            Application.builder()
                       .token(token)
                       .post_init(on_startup)
                       .post_shutdown(on_shutdown)
                       .build()
        )

    app = build_app(token)

    # 5) Маршруты/хендлеры
    setup_handlers(app)

    return app

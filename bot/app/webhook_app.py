import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from telegram import Update

from bot.app.bot import create_app
from bot.app.core.types import PTBApp
from packages.common_settings import settings
from packages.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)
_PTBA: Optional[PTBApp] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan: инициализация PTB внутри FastAPI
    """
    ptba = create_app()
    await ptba.initialize()
    await ptba.start()
    app.state.ptba = ptba
    try:
        yield
    finally:
        await ptba.stop()
        await ptba.shutdown()
        app.state.ptba = None


fastapi_app = FastAPI(title='Telegram Bot Webhook', lifespan=lifespan)


@fastapi_app.post(settings.webhooks.path())
async def telegram_webhook(request: Request):
    """
    Единственный публичный эндпойнт для Telegram:
    - проверяем заголовок X-Telegram-Bot-Api-Secret-Token
    - парсим апдейт и кладём в PTB очередь
    """
    global _PTBA
    if _PTBA is None:
        raise HTTPException(status_code=503, detail='PTB not ready')

    secret_hdr = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
    if secret_hdr != settings.webhooks.secret_token.get_secret_value():
        raise HTTPException(status_code=403, detail='Invalid secret token')

    data = await request.json()
    update = Update.de_json(data, _PTBA.bot)
    await _PTBA.update_queue.put(update)
    return {'ok': True}


if __name__ == '__main__':
    if not settings.telegram.use_webhook:
        # Классический режим: polling
        try:
            application = create_app()
            logger.info('🤖 Бот запускается (polling)…')
            application.run_polling(
                poll_interval=1.0,
                drop_pending_updates=True,
            )
        except Exception:
            logger.exception('🔥 Ошибка при запуске бота (polling)')
            raise
    else:
        # Режим вебхука: поднимаем FastAPI-сервер внутри этого процесса
        import uvicorn
        port = settings.webhooks.port
        logger.info('🌐 Запуск webhook-сервера FastAPI на порту %s', port)
        uvicorn.run(
            'bot.webhook_app:fastapi_app',
            host='0.0.0.0',
            port=port,
            # reload не нужен в контейнере
            workers=settings.fast_api.uvicorn_workers,
            log_level='info',
        )

import logging
from pydantic_settings import BaseSettings
from pydantic import Field, ValidationError

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    telegram_token: str = Field(..., alias='TELEGRAM_BOT_TOKEN')
    database_url: str = Field(..., alias='DATABASE_URL')
    deepseek_api_key: str = Field(..., alias='DEEPSEEK_API_KEY')
    sentry_dsn: str = Field(..., alias='SENTRY_DSN')
    chat_id: str = Field(..., alias='CHAT_ID')

    model_config = {
        'env_file': '.env',
        'extra': 'ignore',
        'case_sensitive': False,
    }


try:
    settings = Settings()  # type: ignore
    logger.info('✅ Конфигурация успешно загружена из .env')
except ValidationError as e:
    logger.error('❌ Ошибка загрузки конфигурации: %s', e)
    raise SystemExit(
        'Остановка: отсутствуют обязательные переменные окружения.'
    )

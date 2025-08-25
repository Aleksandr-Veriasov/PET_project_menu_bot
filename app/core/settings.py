from __future__ import annotations

import logging
import os
from enum import Enum
from pathlib import Path
from typing import Any, Literal, Optional, Tuple

from pydantic import AnyUrl, Field, SecretStr, ValidationError, model_validator
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import (
    EnvSettingsSource, PydanticBaseSettingsSource
)
from sqlalchemy.engine import URL

logger = logging.getLogger(__name__)


class FileAwareEnvSource(EnvSettingsSource):
    """
    Источник ENV с поддержкой fallback на <ENV>_FILE.
    Приоритет: ENV > ENV_FILE.
    """

    def get_field_value(
            self, field: FieldInfo, field_name: str
    ) -> Tuple[Any, str, bool]:
        # 1) Берём стандартное значение из окружения
        value, key, is_complex = super().get_field_value(field, field_name)

        # 2) Если пусто — пробуем <KEY>_FILE
        if value in (None, ''):
            file_env = f'{key}_FILE'  # key уже учитывает env_prefix и alias
            file_path = os.getenv(file_env)
            if file_path:
                p = Path(file_path).expanduser().resolve()
                if not p.is_file():
                    raise ValueError(f'{file_env} points to missing file: {p}')
                value = p.read_text().strip()
                # Содержимое файла — обычная строка (не JSON и т.п.)
                is_complex = False

        return value, key, is_complex


class BaseAppSettings(BaseSettings):
    """ Базовый класс настроек приложения с кастомным источником ENV.
    Используется для переопределения источников конфигурации и
    настройки их порядка.
    """
    model_config = SettingsConfigDict(
        env_file='.env',
        case_sensitive=False,
        extra='ignore',
        frozen=True,
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[
        PydanticBaseSettingsSource,
        PydanticBaseSettingsSource,
        PydanticBaseSettingsSource,
        PydanticBaseSettingsSource,
    ]:
        # порядок источников:
        # kwargs -> наш ENV/ENV_FILE -> .env -> secrets_dir
        return (
            init_settings,
            FileAwareEnvSource(settings_cls),
            dotenv_settings,
            file_secret_settings
        )


class DbDriver(str, Enum):
    """
    Драйверы для подключения к PostgreSQL.
    Используется в SQLAlchemy URL.
    """
    asyncpg = 'asyncpg'
    psycopg2 = 'psycopg2'


class SslMode(str, Enum):
    """
    Режимы SSL для подключения к PostgreSQL.
    Используется в SQLAlchemy URL.
    """
    disable = 'disable'
    allow = 'allow'
    prefer = 'prefer'
    require = 'require'
    verify_ca = 'verify-ca'
    verify_full = 'verify-full'


class DatabaseSettings(BaseAppSettings):
    """
    Конфигурация БД: собираем DSN из составных полей.
    """

    host: str = Field(..., alias='DB_HOST')
    port: int = Field(default=5432, alias='DB_PORT')
    username: str = Field(..., alias='DB_USER')
    password: SecretStr = Field(..., alias='DB_PASSWORD')
    database_name: str = Field(..., alias='DB_NAME')

    driver: DbDriver = Field(DbDriver.psycopg2, alias='DB_DRIVER')
    ssl_mode: Optional[SslMode] = Field(default=None, alias='DB_SSLMODE')
    ssl_root_cert_file: Optional[str] = Field(
        default=None, alias='DB_SSLROOTCERT'
    )  # путь к CA

    # Рантайм-флаги
    # dev-bootstrap: Base.metadata.create_all()
    bootstrap_schema: bool = Field(default=False, alias='DB_BOOTSTRAP_SCHEMA')
    # ping перед выдачей коннекта из пула
    pool_pre_ping: bool = Field(default=True, alias='DB_POOL_PRE_PING')
    # время жизни коннекта в пуле
    pool_recycle: int = Field(default=1800, alias='DB_POOL_RECYCLE')

    @model_validator(mode='after')
    def _validate_required(self) -> DatabaseSettings:
        problems = []
        if not self.host.strip():
            problems.append('host')
        if not self.username.strip():
            problems.append('username')
        if not self.password.get_secret_value().strip():
            problems.append('password')
        if not self.database_name.strip():
            problems.append('database_name')
        if problems:
            raise ValueError(
                f'DB config incomplete: set {", ".join(problems)}'
            )
        return self

    def sqlalchemy_url(self) -> URL:
        query: dict[str, str] = {}
        if self.ssl_mode:
            query["sslmode"] = self.ssl_mode.value
        if self.ssl_root_cert_file:
            query["sslrootcert"] = self.ssl_root_cert_file
    # для asyncpg ничего SSL-ного в URL не добавляем: обработаем в connect_args

        return URL.create(
            drivername=f'postgresql+{self.driver.value}',
            username=self.username,
            password=self.password.get_secret_value(),
            host=self.host,
            port=self.port,
            database=self.database_name,
            query=query,
        )

    def safe_dict(self) -> dict[str, Any]:
        return {
            'host': self.host,
            'port': self.port,
            'username': self.username,
            'password': '***',
            'database_name': self.database_name,
            'driver': self.driver,
            'ssl_mode': self.ssl_mode,
            'ssl_root_cert_file': self.ssl_root_cert_file,
        }


class TelegramSettings(BaseAppSettings):
    """
    Конфигурация Telegram бота: токен и ID чата.
    Используется для отправки уведомлений и логов.
    """
    bot_token: SecretStr = Field(alias='TELEGRAM_BOT_TOKEN')
    chat_id: str = Field(alias='TELEGRAM_CHAT_ID')


class DeepSeekSettings(BaseAppSettings):
    """
    Конфигурация DeepSeek API: ключ API.
    Используется для доступа к DeepSeek сервисам.
    """

    api_key: SecretStr = Field(alias='DEEPSEEK_API_KEY')


class SentrySettings(BaseAppSettings):
    """
    Конфигурация Sentry: DSN для отправки ошибок.
    Используется для мониторинга и отслеживания ошибок.
    """

    dsn: Optional[AnyUrl] = Field(default=None, alias='SENTRY_DSN')


class AppSettings(BaseAppSettings):
    """
    Основные настройки приложения: окружение, отладка,
    конфигурация БД, Telegram, DeepSeek и Sentry.
    """
    env: Literal['local', 'dev', 'staging', 'prod'] = Field(
        default='prod', alias='APP_ENV'
    )
    debug: bool = Field(default=False, alias='DEBUG')

    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    deepseek: DeepSeekSettings = Field(default_factory=DeepSeekSettings)
    sentry: SentrySettings = Field(default_factory=SentrySettings)

    @model_validator(mode='after')
    def _prod_debug_guard(self) -> AppSettings:
        if self.env == 'prod' and self.debug:
            raise ValueError('DEBUG must be False in prod')
        return self

    def safe_dict(self) -> dict[str, Any]:
        return {
            'env': self.env,
            'debug': self.debug,
            'db': self.db.safe_dict(),
            'telegram': {'chat_id': self.telegram.chat_id, 'bot_token': '***'},
            'deepseek': {'api_key': '***'},
            'sentry': {'dsn': '***' if self.sentry.dsn else None},
        }


# Инициализация с fail-fast и безопасным логированием
try:
    settings = AppSettings()
    logger.info('✅ Конфигурация загружена')
    logger.debug('Config dump: %s', settings.safe_dict())
except ValidationError as e:
    logger.critical('❌ Ошибка конфигурации: %s', e.errors())
    raise SystemExit(
        'Остановка: отсутствуют обязательные '
        'переменные окружения или заданы неверно.'
    )

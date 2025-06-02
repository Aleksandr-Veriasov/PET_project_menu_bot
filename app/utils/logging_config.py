import logging
import sys
import os

from dotenv import load_dotenv
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration


load_dotenv()

# Настройка стандартного логгера
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(asctime)s - %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

sentry_dsn = os.getenv("SENTRY_DSN")
# Инициализация Sentry
sentry_sdk.init(
    dsn=sentry_dsn,
    send_default_pii=True,
    _experiments={
        "enable_logs": True,
    },
    integrations=[
        LoggingIntegration(sentry_logs_level=logging.WARNING),
    ],
    environment="production",
    traces_sample_rate=1.0,
)

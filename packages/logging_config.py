import logging
import sys
import requests

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

from packages.common_settings.settings import settings


class CustomFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__(fmt="%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(name)s - %(message)s")


class APINotificationHandler(logging.Handler):
    def __init__(self, token: str, admin: int) -> None:
        logging.Handler.__init__(self)
        self.url = f'https://api.telegram.org/bot{token}/sendMessage'
        self.admin = admin
        self.formatter = CustomFormatter()

    def emit(self, record: logging.LogRecord) -> None:
        log_entry = self.format(record)
        log_entry = log_entry.replace('[', '\n[')
        log_entry = log_entry.replace(']', ']\n')
        log_entry = log_entry.replace('__ -', '__ -\n')
        payload = {'chat_id': self.admin,
                   'text': f'<code>{log_entry}</code>',
                   'parse_mode': 'HTML'}
        requests.post(self.url, json=payload)


logging.getLogger("httpcore.connection").setLevel(logging.INFO)
logging.getLogger("httpcore.http11").setLevel(logging.INFO)
logging.getLogger("httpcore.proxy").setLevel(logging.INFO)
logging.getLogger("httpx").setLevel(
    logging.WARNING if not settings.debug else logging.INFO
)
logging.getLogger("websockets.client").setLevel(logging.INFO)
logging.getLogger('sqlalchemy.engine.Engine').setLevel(logging.ERROR)
logging.getLogger('python_multipart.multipart').setLevel(logging.INFO)


def setup_logging() -> None:
    """Настраивает логирование и интеграцию с Sentry."""
    level = logging.DEBUG if settings.debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(levelname)s - %(asctime)s - %(name)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )

    if settings.telegram.admin_id:
        logger_init = logging.getLogger(__name__)
        api_handler = APINotificationHandler(
            str(settings.telegram.bot_token), int(settings.telegram.admin_id)
        )
        api_handler.setLevel(logging.ERROR)
        logger_init.addHandler(api_handler)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("root").setLevel(logging.INFO)

    if settings.sentry.dsn and settings.debug is False:
        sentry_sdk.init(
            dsn=str(settings.sentry.dsn),
            send_default_pii=False,
            _experiments={"enable_logs": True},
            integrations=[
                LoggingIntegration(sentry_logs_level=logging.WARNING)
            ],
            environment=settings.env,
            traces_sample_rate=1.0,
        )
        logging.getLogger(__name__).info("✅ Sentry инициализирован.")
    else:
        logging.getLogger(__name__).warning(
            "⚠️ SENTRY_DSN не задан. Sentry не активен."
        )

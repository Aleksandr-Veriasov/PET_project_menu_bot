import logging
import sys

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

from app.core.settings import settings


def setup_logging():
    """Настраивает логирование и интеграцию с Sentry."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s - %(asctime)s - %(name)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )

    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            send_default_pii=True,
            _experiments={"enable_logs": True},
            integrations=[
                LoggingIntegration(sentry_logs_level=logging.WARNING)
            ],
            environment="production",
            traces_sample_rate=1.0,
        )
        logging.getLogger(__name__).info("✅ Sentry инициализирован.")
    else:
        logging.getLogger(__name__).warning(
            "⚠️ SENTRY_DSN не задан. Sentry не активен."
        )

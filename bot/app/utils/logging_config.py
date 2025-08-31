import logging
import sys

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

from packages.common_settings.settings import settings


def setup_logging() -> None:
    """Настраивает логирование и интеграцию с Sentry."""
    level = logging.DEBUG if settings.debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(levelname)s - %(asctime)s - %(name)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )

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

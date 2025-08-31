from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def safe_remove(path: Optional[str]) -> None:
    """Безопасно удаляет файл, если он существует."""
    if not path:
        return
    p = Path(path)
    try:
        if p.exists():
            p.unlink()  # Python 3.10 ок
            logger.info("🧹 Удалён временный файл: %s", p)
    except FileNotFoundError:
        pass
    except Exception as e:
        logger.warning("Не удалось удалить %s: %s", p, e)

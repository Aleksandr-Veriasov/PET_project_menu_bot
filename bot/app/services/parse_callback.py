import logging
import re
from typing import Optional, Tuple

from bot.app.core.recipes_mode import RecipeMode

logger = logging.getLogger(__name__)

# slug может содержать a-z, 0-9, _ и -
CB_RE = re.compile(
    r'^(?P<category>[a-z0-9][a-z0-9_-]*?)(?:_(?P<mode>show|random|edit))?$'
)

CB_RE_C = re.compile(
    r'^(?P<category>[a-z0-9][a-z0-9_-]*)_save?$'
)

CB_RE_M = re.compile(
    r'^recipes(?:_(?P<mode>show|random|edit))?$'
)
CB_CAT_MODE_ID = re.compile(
    r'^([a-z0-9][a-z0-9_-]*)_(show|random|edit)_(\d+)$'
)


def parse_category_mode(cb: str) -> Optional[Tuple[str, RecipeMode]]:
    """
    Возвращает (category_slug, mode) или None, если формат не подошёл.
    """
    logger.info(f'⏩⏩⏩ m = {cb}')
    m = CB_RE.fullmatch((cb or '').lower())
    logger.info(f'⏩⏩⏩ m = {m}')
    if not m:
        return None
    category = m.group('category')
    mode_str = m.group('mode')
    logger.info(f'⏩⏩⏩ mode_str = {mode_str}')
    mode = RecipeMode(mode_str)
    return category, mode


def parse_category(cb: str) -> Optional[Tuple[str, RecipeMode]]:
    """
    Возвращает (category_slug) или None, если формат не подошёл.
    """
    logger.info(f'⏩⏩⏩ m = {cb}')
    m = CB_RE_C.fullmatch((cb or '').lower())
    logger.info(f'⏩⏩⏩ m = {m}')
    if not m:
        return None
    category = m.group('category')
    return category


def parse_mode(cb: str) -> Optional[Tuple[str, RecipeMode]]:
    """
    Возвращает (mode) или None, если формат не подошёл.
    """
    m = CB_RE_M.fullmatch((cb or '').lower())
    logger.info(f'⏩⏩⏩ m = {m}')
    if not m:
        return None
    mode_str = m.group('mode')
    logger.info(f'⏩⏩⏩ mode_str = {mode_str}')
    mode = RecipeMode(mode_str)
    return mode


def parse_category_mode_id(cb: str) -> Optional[Tuple[str, str, int]]:
    """
    Возвращает (category, mode, obj_id) или None, если формат не подошёл.
    mode: 'show' | 'random' | 'edit'
    """
    m = CB_CAT_MODE_ID.fullmatch((cb or '').lower().strip())
    if not m:
        return None
    category, mode, obj_id = m.groups()
    return category, mode, int(obj_id)

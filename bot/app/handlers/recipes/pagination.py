import logging
import re
from contextlib import suppress

from telegram import Update
from telegram.error import BadRequest

from bot.app.core.types import PTBContext
from bot.app.keyboards.inlines import (
    build_recipes_list_keyboard, home_keyboard
)
from packages.redis.repository import RecipeCacheRepository

# Включаем логирование
logger = logging.getLogger(__name__)

# допустимые callback_data: 'next_3' / 'prev_0'
_PAGE_RE = re.compile(r'^(next|prev)_(\d+)$')


async def handler_pagination(update: Update, context: PTBContext) -> None:
    """
    Обрабатывает нажатия кнопок пагинации.
    Entry-point: next_ / prev_
    """
    cq = update.callback_query
    if not cq:
        return
    await cq.answer()

    # Берём user_data; если у вас есть свой хелпер — можно использовать его
    state = context.user_data
    state_r = context.bot_data['state']
    category_id = state.get('category_id', 0)
    items = await RecipeCacheRepository.get_all_recipes_ids_and_titles(
        state_r.redis, cq.from_user.id, category_id
    )
    if not items:
        if cq.message:
            with suppress(BadRequest):
                await cq.edit_message_text(
                    'Список рецептов пуст.', reply_markup=home_keyboard()
                )
        return

    m = _PAGE_RE.match(cq.data or '')
    if not m:
        # незнакомый callback — просто игнор
        return

    _, page_str = m.groups()
    try:
        page = int(page_str)
    except ValueError:
        page = 0

    per_page = int(state.get('recipes_per_page', 5)) if state else 5
    total_pages = int(state.get('recipes_total_pages', 1)) if state else 1
    page = max(0, min(page, max(0, total_pages - 1)))
    mode = state.get('mode', 'show')
    if state:
        state['recipes_page'] = page
        category_slug = state.get('category_slug', 'recipes')
        logger.info(f'🗑 {state["recipes_page"]} - category_slug')
        markup = build_recipes_list_keyboard(
            items, page=page, per_page=per_page,
            edit=bool(state.get('is_editing', False)),
            category_slug=category_slug, mode=mode
        )
        title = state.get('category_name', 'категория')

    if cq.message:
        try:
            await cq.edit_message_text(
                f'Выберите рецепт из категории «{title}»:',
                parse_mode='HTML',
                disable_web_page_preview=True,
                reply_markup=markup
            )
        except BadRequest as e:
            if 'message is not modified' in str(e).lower():
                with suppress(BadRequest):
                    await cq.edit_message_reply_markup(reply_markup=markup)
            else:
                raise

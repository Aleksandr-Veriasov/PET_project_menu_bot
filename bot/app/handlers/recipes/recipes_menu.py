import logging
from contextlib import suppress
from typing import List

from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest

from packages.db.repository import (
    RecipeRepository, VideoRepository
)
from bot.app.utils.context_helpers import get_db
from bot.app.keyboards.inlines import (
    build_recipes_list_keyboard,
    category_keyboard,
    choice_recipe_keyboard,
    home_keyboard,
    recipe_edit_keyboard,
)
from bot.app.utils.message_utils import random_recipe
from bot.app.core.types import PTBContext
from bot.app.services.parse_callback import parse_category_mode, parse_mode
from bot.app.core.recipes_mode import RecipeMode
from bot.app.services.category_service import CategoryService
from bot.app.services.recipe_service import RecipeService
from packages.common_settings import settings

# Включаем логирование
logger = logging.getLogger(__name__)


async def upload_recipe(update: Update, context: PTBContext) -> None:
    """Обработчик команды /upload_recipe."""
    cq = update.callback_query
    if cq:
        await cq.answer()
        if cq.message:
            await cq.edit_message_text(
                'Пожалуйста, отправьте ссылку на видео с рецептом.',
                reply_markup=home_keyboard(),
                parse_mode=ParseMode.HTML
            )


async def recipes_menu(update: Update, context: PTBContext) -> None:
    """
    Обработчик нажатия кнопки 'Рецепты'.
    Entry-point: recipe, recipe_random, recipe_edit.
    """
    cq = update.callback_query
    if not cq:
        return
    logger.debug(f'⏩⏩ Получен колбэк: {cq}')
    await cq.answer()

    user_id = cq.from_user.id
    db = get_db(context)
    state = context.bot_data['state']
    service = CategoryService(db, state.redis)
    categories = await service.get_user_categories_cached(user_id)

    mode = parse_mode(cq.data or "")
    logger.debug(f'⏩ Получен колбэк: {mode}')
    if mode == RecipeMode.RANDOM:
        text = "🔖 Выберите раздел со случайным блюдом:"
    elif mode == RecipeMode.EDIT:
        text = "🔖 Выберите раздел с блюдом для редактирования:"
    else:
        text = "🔖 Выберите раздел:"

    markup = category_keyboard(categories, mode)

    if cq.message:
        try:
            await cq.edit_message_text(
                text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                reply_markup=markup
            )
        except BadRequest as e:
            if "message is not modified" in str(e).lower():
                with suppress(BadRequest):
                    await cq.edit_message_reply_markup(reply_markup=markup)
            else:
                raise


async def recipes_from_category(update: Update, context: PTBContext) -> None:
    """
    Обработчик выбора категории рецептов.
    Entry-point: r'^(?[a-z0-9][a-z0-9_-]*_recipes(?:_(?:show|random|edit))?$'
    """
    cq = update.callback_query
    if not cq:
        return
    await cq.answer()

    category_slug, mode = parse_category_mode(cq.data or "")
    logger.debug(f'⏩⏩ category_slug = {category_slug}, mode = {mode}')

    user_id = cq.from_user.id
    db = get_db(context)
    state = context.bot_data['state']
    text = ''

    # RANDOM — отдельный сценарий (без user_data)
    if mode.value == 'random':
        video_url, text = await random_recipe(
            db, state.redis, user_id, category_slug
        )

        if cq.message:
            if not text:
                await cq.edit_message_text(
                    '👉 🍽 Здесь появится ваш рецепт, '
                    'когда вы что-нибудь сохраните.',
                    reply_markup=home_keyboard()
                )
                return
            # показываем видео и текст отдельными сообщениями
            if update.effective_message:
                if video_url:
                    await update.effective_message.reply_video(video_url)
                await update.effective_message.reply_text(
                    text, parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True,
                    reply_markup=home_keyboard(),
                )
            return

    # DEFAULT/EDIT — вытягиваем список и кладём в user_data
    pairs: List[dict[str, str]] = []
    service = CategoryService(db, state.redis)
    category_id, category_name = (
        await service.get_id_and_name_by_slug_cached(
            category_slug
        )
    )
    logger.info(f'📼 category_id = {category_id}')
    service = RecipeService(db, state.redis)
    if category_id:
        pairs = await service.get_all_recipes_ids_and_titles(
            user_id, category_id
        )
        logger.info(f'📼 pairs = {pairs}')

    if not pairs:
        if cq.message:
            await cq.edit_message_text(
                f'У вас нет рецептов в категории «{category_name}».',
                reply_markup=home_keyboard()
            )
        return

    # сохраняем состояние в user_data
    state = context.user_data
    # state['recipes_items'] = pairs  # [(id, title)]
    state['recipes_page'] = 0
    state['recipes_per_page'] = settings.telegram.recipes_per_page
    state['recipes_total_pages'] = (
        len(pairs) + state['recipes_per_page'] - 1
    ) // state['recipes_per_page']
    state['is_editing'] = (mode == 'edit')
    state['category_name'] = category_name
    state['category_slug'] = category_slug
    state['category_id'] = category_id
    state['mode'] = mode

    # рисуем первую страницу
    markup = build_recipes_list_keyboard(
        pairs, page=0, per_page=state['recipes_per_page'],
        edit=state['is_editing'], category_slug=category_slug,
        mode=mode
    )
    try:
        await cq.edit_message_text(
            f'Выберите рецепт из категории «{category_name}»:',
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=markup
        )
    except BadRequest as e:
        if 'message is not modified' in str(e).lower():
            with suppress(BadRequest):
                await cq.edit_message_reply_markup(reply_markup=markup)
        else:
            raise


async def recipe_choice(
    update: Update, context: PTBContext
) -> None:
    """
    Обработчик выбора рецепта.
    Entry-point: r'^(?[a-z0-9][a-z0-9_-]*_(?:recipe|edit_recipe)+$'
    """
    cq = update.callback_query
    if not cq:
        return

    await cq.answer()

    data = cq.data or ''
    category_slug = data.split('_', 1)[0]  # breakfast|main|salad
    logger.info(f'🗑 {category_slug} - category_slug')
    state = context.user_data
    if state:
        page = state.get('recipes_page', 0)
    if data.startswith(f'{category_slug}_edit_'):
        # Редактирование рецепта
        recipe_id = int(data.split('_')[2])
        keyboard = recipe_edit_keyboard(recipe_id, page)
    else:
        recipe_id = int(data.split('_')[2])
        keyboard = choice_recipe_keyboard(page)

    db = get_db(context)
    async with db.session() as session:
        recipe = await RecipeRepository.get_by_id(session, recipe_id)
        if not recipe:
            await cq.edit_message_text('❌ Рецепт не найден.')
            return
        video_url = await VideoRepository.get_video_url(
            session, int(recipe.id)
        )
        if not video_url:
            video_url = None
        ingredients_text = '\n'.join(
            f'- {ingredient.name}' for ingredient in recipe.ingredients
        )
        text = (
            f'🍽 <b>Название рецепта:</b> {recipe.title}\n\n'
            f'📝 <b>Рецепт:</b>\n{recipe.description}\n\n'
            f'🥦 <b>Ингредиенты:</b>\n{ingredients_text}'
        )
        if video_url and update.effective_message:
            await update.effective_message.reply_video(video_url)

        if update.effective_message:
            await update.effective_message.reply_text(
                text, parse_mode=ParseMode.HTML, disable_web_page_preview=True,
                reply_markup=keyboard
            )

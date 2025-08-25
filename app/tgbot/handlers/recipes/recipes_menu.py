import asyncio
import logging
from contextlib import suppress
from typing import List, Tuple

from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest

from app.db.repository import (
    CategoryRepository, RecipeRepository, VideoRepository
)
from app.tgbot.context_helpers import get_db
from app.tgbot.keyboards.inlines import (
    _CB_RE,
    build_recipes_list_keyboard,
    category_keyboard,
    choice_recipe_keyboard,
    home_keyboard,
    recipe_edit_keyboard,
)
from app.tgbot.message_utils import random_recipe
from app.tgbot.recipes_modes import RecipeMode
from app.types import PTBContext

# Включаем логирование
logger = logging.getLogger(__name__)

CATEGORY_DICT = {
    'breakfast': 'Завтрак',
    'main': 'Основное блюдо',
    'salad': 'Салат',
}


async def upload_recipe(update: Update, context: PTBContext):
    """Обработчик команды /upload_recipe."""
    cq = update.callback_query
    await cq.answer()
    if cq.message:
        await cq.message.edit_text(
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

    await cq.answer()

    data = cq.data or ""
    logger.info(f'⏩ Получен колбэк: {data}')
    if data == RecipeMode.RANDOM:
        mode = RecipeMode.RANDOM
        text = "🔖 Выберите раздел со случайным блюдом:"
    elif data == RecipeMode.EDIT:
        mode = RecipeMode.EDIT
        text = "🔖 Выберите раздел с блюдом для редактирования:"
    else:
        mode = RecipeMode.DEFAULT
        text = "🔖 Выберите раздел:"

    markup = category_keyboard(mode)

    if cq.message:
        try:
            await cq.message.edit_text(
                text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                reply_markup=category_keyboard(mode),
            )
        except BadRequest as e:
            if "message is not modified" in str(e).lower():
                with suppress(BadRequest):
                    await cq.message.edit_reply_markup(reply_markup=markup)
            else:
                raise


async def recipes_from_category(update: Update, context: PTBContext) -> None:
    """
    Обработчик выбора категории рецептов.
    Entry-point: r'^(?:breakfast|main|salad)_recipes(?:_(?:random|edit))?$'
    """
    cq = update.callback_query
    if not cq:
        return
    await cq.answer()

    data = cq.data or ''
    m = _CB_RE.match(data)
    if not m:
        # неизвестный колбэк
        return

    category_slug = m.group('category')  # breakfast|main|salad
    mode = (m.group('mode') or 'default')  # default|random|edit
    category_name = CATEGORY_DICT.get(
        category_slug, category_slug.capitalize()
    )

    user_id = cq.from_user.id
    db = get_db(context)

    # RANDOM — отдельный сценарий (без user_data)
    if mode == 'random':
        with db.session() as session:
            video_url, text = await asyncio.to_thread(
                random_recipe, session, user_id, category_name
            )

        if cq.message:
            if not text:
                await cq.message.edit_text(
                    '👉 🍽 Здесь появится ваш рецепт, '
                    'когда вы что-нибудь сохраните.',
                    reply_markup=home_keyboard()
                )
                return
            # показываем видео и текст отдельными сообщениями (как у тебя)
            # await cq.message.reply_video(video_url)
            await cq.message.reply_text(
                text, parse_mode=ParseMode.HTML, disable_web_page_preview=True,
                reply_markup=home_keyboard(),
            )
        return

    # DEFAULT/EDIT — вытягиваем список и кладём в user_data
    with db.session() as session:
        category_id = CategoryRepository.get_id_by_name(session, category_name)
        # ожидаем ЛЁГКИЙ список [(id, title)]
        pairs: List[Tuple[int, str]] = (
            RecipeRepository.get_all_recipes_ids_and_titles(
                session, user_id, category_id
                )
            )

    if not pairs:
        if cq.message:
            await cq.message.edit_text(
                f'У вас нет рецептов в категории «{category_name}».',
                reply_markup=home_keyboard()
            )
        return

    # сохраняем состояние в user_data
    state = context.user_data
    state['recipes_items'] = pairs  # [(id, title)]
    state['recipes_page'] = 0
    state['recipes_per_page'] = 5
    state['recipes_total_pages'] = (
        len(pairs) + state['recipes_per_page'] - 1
    ) // state['recipes_per_page']
    state['is_editing'] = (mode == 'edit')
    state['category_name'] = category_name
    state['category_slug'] = category_slug

    # рисуем первую страницу
    markup = build_recipes_list_keyboard(
        pairs, page=0, per_page=state['recipes_per_page'],
        edit=state['is_editing'], category_slug=category_slug
    )

    if cq.inline_message_id:
        await context.bot.edit_message_text(
            text=f'Выберите рецепт из категории «{category_name}»:',
            inline_message_id=cq.inline_message_id,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=markup
        )
    elif cq.message:
        try:
            await cq.message.edit_text(
                f'Выберите рецепт из категории «{category_name}»:',
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                reply_markup=markup
            )
        except BadRequest as e:
            if 'message is not modified' in str(e).lower():
                with suppress(BadRequest):
                    await cq.message.edit_reply_markup(reply_markup=markup)
            else:
                raise


async def recipe_choice(
    update: Update, context: PTBContext
) -> None:
    """
    Обработчик выбора рецепта.
    Entry-point: r'^(?:breakfast|main|salad)_(?:recipe|edit_recipe)+$'
    """
    cq = update.callback_query
    if not cq:
        return

    await cq.answer()

    data = cq.data or ''
    category_slug = data.split('_', 1)[0]  # breakfast|main|salad
    logger.info(f'🗑 {category_slug} - category_slug')
    state = context.user_data
    page = state.get('recipes_page', 0)
    if data.startswith(f'{category_slug}_edit_recipe_'):
        # Редактирование рецепта
        recipe_id = int(data.split('_')[3])
        keyboard = recipe_edit_keyboard(recipe_id, page)
    else:
        recipe_id = int(data.split('_')[2])
        keyboard = choice_recipe_keyboard(page)

    db = get_db(context)
    with db.session() as session:
        recipe = RecipeRepository.get_by_id(session, recipe_id)
        if not recipe:
            await cq.message.edit_text('❌ Рецепт не найден.')
            return
        video_url = VideoRepository.get_video_url(session, recipe.id)
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
        # if video_url:
        #     await cq.message.reply_video(video_url)

        await cq.message.reply_text(
            text, parse_mode=ParseMode.HTML, disable_web_page_preview=True,
            reply_markup=keyboard
        )

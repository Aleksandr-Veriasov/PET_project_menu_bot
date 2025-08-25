import asyncio
import logging
from typing import Optional

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CallbackQueryHandler, ConversationHandler

from app.db.repository import (
    CategoryRepository,
    IngredientRepository,
    RecipeIngredientRepository,
    RecipeRepository,
    VideoRepository,
)
from app.db.schemas import RecipeCreate
from app.services.ingredients_parser import parse_ingredients
from app.tgbot.context_helpers import get_db
from app.tgbot.keyboards.inlines import category_keyboard, home_keyboard
from app.tgbot.recipes_modes import RecipeMode
from app.tgbot.recipes_state import SaveRecipeState
from app.types import PTBContext

logger = logging.getLogger(__name__)


async def start_save_recipe(update: Update, context: PTBContext) -> int:
    """
    Обработчик команды 'save_recipe' при нажатия кнопки 'Сохранить рецепт'.
    Отправляет пользователю сообщение с подтверждением рецепта.
    """
    cq = update.callback_query
    if not cq:
        return ConversationHandler.END

    await cq.answer()
    if context.user_data:
        draft = context.user_data.get("recipe_draft", {})
    title = draft.get('title', '')
    await cq.edit_message_text(
        f'🔖 <b>Выберете категорию для этого рецепта:</b>\n\n'
        f'🍽 <b>Название рецепта:</b>\n{title}\n\n',
        reply_markup=category_keyboard(RecipeMode.SAVE),
        parse_mode=ParseMode.HTML
    )
    return SaveRecipeState.CHOOSE_CATEGORY


async def save_recipe(update: Update, context: PTBContext) -> int:
    cq = update.callback_query
    if not cq:
        return ConversationHandler.END
    await cq.answer()
    if context.user_data:
        draft = context.user_data.get("recipe_draft", {})
    category = cq.data
    if category not in ['breakfast_recipes', 'main_recipes', 'salad_recipes']:
        await cq.edit_message_text(
            '❗️ Выберите корректную категорию рецепта.'
        )
        return SaveRecipeState.CHOOSE_CATEGORY

        # Добавляем категорию в базу, если её нет
    category_name = ''
    if category == 'breakfast_recipes':
        category_name = 'Завтрак'
    elif category == 'main_recipes':
        category_name = 'Основное блюдо'
    elif category == 'salad_recipes':
        category_name = 'Салат'

    title = draft.get('title', 'Не указано')
    description = draft.get('description', 'Не указано')
    ingredients = draft.get('ingredients', 'Не указано')
    video_url = draft.get('video_url', '')
    ingredients_raw = parse_ingredients(ingredients)
    user_id = cq.from_user.id if cq.from_user else None

    db = get_db(context)

    def _save_sync() -> Optional[int]:
        with db.session() as session:
            category_id = CategoryRepository.get_id_by_name(
                session, category_name
            )
            if user_id and category_id:
                payload = RecipeCreate(
                    user_id=user_id,
                    title=title,
                    description=description,
                    category_id=category_id
                )
            recipe = RecipeRepository.create(session, payload)
            try:
                for ingredient in ingredients_raw:
                    ingredient = IngredientRepository.create(
                        session, ingredient
                    )
                    RecipeIngredientRepository.create(
                        session, int(recipe.id), ingredient.id
                    )
            except Exception:
                session.rollback()
                raise

            if video_url:
                VideoRepository.create(session, video_url, int(recipe.id))
            session.commit()
            return int(recipe.id)
    try:
        await asyncio.to_thread(_save_sync)
    except Exception as e:
        logger.exception("Ошибка при сохранении рецепта: %s", e)
        await cq.edit_message_text(
            "❗️ Произошла ошибка при сохранении рецепта. Попробуйте позже.",
            reply_markup=home_keyboard(),
        )
        return ConversationHandler.END
    await cq.edit_message_text(
        f'✅ Ваш рецепт успешно сохранен!\n\n'
        f'🍽 <b>Название рецепта:</b>\n{title}\n\n'
        f'🔖 <b>Категория:</b> {category_name}',
        parse_mode=ParseMode.HTML,
        reply_markup=home_keyboard()
    )
    return ConversationHandler.END


async def cancel_recipe_save(update: Update, context: PTBContext) -> int:
    """Обработка нажатия «Не сохранять рецепт» — просто чистим черновик."""
    cq = update.callback_query
    if not cq:
        return ConversationHandler.END
    await cq.answer()
    user_id = cq.from_user.id
    if context.user_data:
        context.user_data.pop(user_id, None)

    await cq.edit_message_text(
        'Рецепт не сохранен.',
        parse_mode=ParseMode.HTML,
        reply_markup=home_keyboard()
    )
    return ConversationHandler.END


def save_recipe_handlers() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                start_save_recipe,
                pattern='^save_recipe$'
            ),
            CallbackQueryHandler(
                cancel_recipe_save,
                pattern='^cancel_save_recipe$'
            )
        ],
        states={
            SaveRecipeState.CHOOSE_CATEGORY: [
                CallbackQueryHandler(
                    save_recipe,
                    pattern='^(breakfast|main_course|salad)_recipes$'
                )
            ]
        },
        fallbacks=[
            CallbackQueryHandler(
                cancel_recipe_save,
                pattern='^cancel_save_recipe$'
            )
        ],
        per_chat=True,
        per_user=True,
        per_message=True,
        conversation_timeout=600,
        # name='save_recipe_conversation',
        # persistent=True
    )

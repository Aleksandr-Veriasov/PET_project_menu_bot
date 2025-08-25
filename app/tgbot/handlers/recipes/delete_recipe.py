import asyncio

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CallbackQueryHandler, ConversationHandler

from app.db.repository import RecipeRepository
from app.tgbot.context_helpers import get_db
from app.tgbot.handlers.recipes.edit_recipe import cancel
from app.tgbot.keyboards.inlines import (
    home_keyboard, keyboard_save_cancel_delete
)
from app.tgbot.recipes_state import DeleteRecipeState
from app.types import PTBContext


async def delete_recipe(update: Update, context: PTBContext) -> int:
    """Entry-point: колбэк вида delete_recipe_{id}."""
    cq = update.callback_query
    if not cq:
        return ConversationHandler.END
    await cq.answer()
    data = cq.data or ''
    # парсим id рецепта
    try:
        recipe_id = int(data.rsplit('_', 1)[1])
    except Exception:
        await cq.message.edit_text('Не смог понять ID рецепта.')
        return ConversationHandler.END
    db = get_db(context)
    with db.session() as session:
        # проверяем, есть ли рецепт с таким ID
        recipe_name = RecipeRepository.get_name_by_id(session, recipe_id)

    # кладём ID в user_data для шага 2+
    context.user_data['delete'] = {'recipe_id': recipe_id}
    await cq.message.edit_text(
        f'Вы точно хотите удалить рецепт <b>{recipe_name}</b>?',
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard_save_cancel_delete(func='delete_recipe'),
    )
    return DeleteRecipeState.CONFIRM


async def confirm_delete(update: Update, context: PTBContext) -> int:
    cq = update.callback_query
    if not cq:
        return ConversationHandler.END
    await cq.answer()
    recipe_id = context.user_data.get('delete', {}).get('recipe_id')
    if not recipe_id:
        await cq.message.edit_text('Не смог понять ID рецепта.')
        return ConversationHandler.END
    db = get_db(context)

    def _do():
        with db.session() as session:
            # удаляем рецепт
            RecipeRepository.delete(session, recipe_id)
            session.commit()
    await asyncio.to_thread(_do)
    await cq.message.edit_text(
        '✅ Рецепт успешно удалён.',
        reply_markup=home_keyboard(),
        parse_mode=ParseMode.HTML
    )
    return ConversationHandler.END


def conversation_delete_recipe() -> ConversationHandler:
    """Создаёт ConversationHandler для удаления рецепта."""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(delete_recipe, pattern=r'^delete_recipe_\d+$')
        ],
        states={
            DeleteRecipeState.CONFIRM: [
                CallbackQueryHandler(confirm_delete, pattern='^delete$'),
                CallbackQueryHandler(cancel, pattern=r'^cancel$'),
            ]
        },
        fallbacks=[CallbackQueryHandler(cancel, pattern=r'^cancel$')],
        per_chat=True,
        per_user=True,
        per_message=True,
        conversation_timeout=600,  # 10 минут
        # name='delete_recipe_conversation',
        # persistent=True
    )

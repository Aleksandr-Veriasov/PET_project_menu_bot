import asyncio

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.db.repository import RecipeRepository
from app.db.schemas import RecipeUpdate
from app.tgbot.context_helpers import get_db
from app.tgbot.keyboards.inlines import (
    home_keyboard, keyboard_save_cancel_delete
)
from app.tgbot.recipes_state import EditRecipeState
from app.types import PTBContext


async def start_edit(update: Update, context: PTBContext) -> int:
    """Entry-point: колбэк вида edit_recipe_{id}."""
    cq = update.callback_query
    if not cq:
        return ConversationHandler.END
    await cq.answer()
    data = cq.data or ''
    # парсим id рецепта
    try:
        recipe_id = int(data.rsplit('_', 1)[1])
    except Exception:
        await cq.edit_message_text('Не смог понять ID рецепта.')
        return ConversationHandler.END
    db = get_db(context)
    with db.session() as session:
        # проверяем, есть ли рецепт с таким ID
        recipe_name = RecipeRepository.get_name_by_id(session, recipe_id)

    # кладём ID в user_data для шага 2+
    if context.user_data:
        context.user_data['edit'] = {'recipe_id': recipe_id}
    await cq.edit_message_text(
        f'Вы хотите отредактировать название рецепта <b>{recipe_name}</b>?',
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard_save_cancel_delete(func='start_edit'),
    )
    return EditRecipeState.CHOOSE_FIELD


async def choose_field(update: Update, context: PTBContext) -> int:
    cq = update.callback_query
    if not cq:
        return ConversationHandler.END
    await cq.answer()
    if cq.data == 'f:title':
        await cq.edit_message_text(
            'Введите новое <b>название</b> рецепта:',
            reply_markup=keyboard_save_cancel_delete(),
            parse_mode=ParseMode.HTML
        )
        return EditRecipeState.WAIT_TITLE
    # отмена
    return await cancel(update, context)


async def handle_title(update: Update, context: PTBContext) -> int:
    """Поймаем текст — это новое название."""
    msg = update.effective_message
    if msg and context.user_data:
        title = (msg.text or '').strip()
        if not title:
            await msg.reply_text('Пусто. Введите название ещё раз.')
            return EditRecipeState.WAIT_TITLE
        context.user_data.setdefault('edit', {})['title'] = title
        await msg.reply_text(
            f'Сохранить название:\n<b>{title}</b>',
            reply_markup=keyboard_save_cancel_delete(func='handle_title'),
            parse_mode=ParseMode.HTML)
        return EditRecipeState.CONFIRM
    return ConversationHandler.END


async def save_changes(update: Update, context: PTBContext) -> int:
    """Сохраняем в БД и завершаем диалог."""
    msg = update.effective_message
    if context.user_data:
        edit = context.user_data.get('edit') or {}
    recipe_id: int = int(edit.get('recipe_id', 0))
    changes = {k: v for k, v in edit.items() if k in ('title', 'description')}

    if not recipe_id or not changes:
        if msg:
            await msg.reply_text('Нет изменений для сохранения.')
        return ConversationHandler.END

    db = get_db(context)

    def _do() -> None:
        with db.session() as session:
            payload = RecipeUpdate(**changes)
            RecipeRepository.update(session, recipe_id, payload)
    await asyncio.to_thread(_do)
    if msg and context.user_data:
        await msg.edit_text(
            '✅ Изменения сохранены.', reply_markup=home_keyboard()
        )
        context.user_data.pop('edit', None)
    return ConversationHandler.END


async def cancel(update: Update, context: PTBContext) -> int:
    # поддержим и колбэк, и команду
    msg = update.effective_message
    if update.callback_query:
        await update.callback_query.answer()
    if msg and context.user_data:
        await msg.edit_text('Отменено.', reply_markup=home_keyboard())
        context.user_data.pop('edit', None)
    return ConversationHandler.END


def conversation_edit_recipe() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_edit, pattern=r'^edit_recipe_(\d+)$')
        ],
        states={
            EditRecipeState.CHOOSE_FIELD: [
                CallbackQueryHandler(
                    choose_field, pattern=r'^(f:title|f:desc|cancel)$'
                )
            ],
            EditRecipeState.WAIT_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_title),
                CallbackQueryHandler(cancel, pattern=r'^cancel$'),
            ],
            EditRecipeState.CONFIRM: [
                CallbackQueryHandler(save_changes, pattern=r'^save_changes$'),
                CallbackQueryHandler(cancel, pattern=r'^cancel$'),
            ],
        },
        fallbacks=[CallbackQueryHandler(cancel, pattern=r'^cancel$')],
        per_chat=True,
        per_user=True,
        per_message=True,
        conversation_timeout=600,  # 10 минут
        # name='edit_recipe_conv',   # если используешь persistence
        # persistent=True,
    )

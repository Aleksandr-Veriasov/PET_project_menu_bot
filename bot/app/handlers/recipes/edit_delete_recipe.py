import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.app.core.recipes_mode import RecipeMode
from bot.app.core.recipes_state import EDRState
from bot.app.core.types import PTBContext
from bot.app.keyboards.inlines import (
    category_keyboard,
    home_keyboard,
    keyboard_save_cancel_delete,
)
from bot.app.services.category_service import CategoryService
from bot.app.services.parse_callback import parse_category
from bot.app.utils.context_helpers import get_db
from packages.db.repository import RecipeRepository
from packages.redis.repository import CategoryCacheRepository, RecipeCacheRepository

logger = logging.getLogger(__name__)


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
    async with db.session() as session:
        # проверяем, есть ли рецепт с таким ID
        recipe_name = await RecipeRepository.get_name_by_id(session, recipe_id)

    # кладём ID в user_data для шага 2+
    if context.user_data:
        context.user_data['edit'] = {'recipe_id': recipe_id}
    await cq.edit_message_text(
        f'Вы хотите отредактировать название рецепта <b>{recipe_name}</b>?',
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard_save_cancel_delete(func='start_edit'),
    )
    return EDRState.CHOOSE_FIELD


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
        return EDRState.WAIT_TITLE
    # отмена
    return await cancel(update, context)


async def handle_title(update: Update, context: PTBContext) -> int:
    """Поймаем текст — это новое название."""
    msg = update.effective_message
    logger.info(f'🥩 msg = {msg}, context.user_data = {context.user_data}')
    if msg:
        title = (msg.text or '').strip()
        if not title:
            await msg.reply_text('Пусто. Введите название ещё раз.')
            return EDRState.WAIT_TITLE
        context.user_data.setdefault('edit', {})['title'] = title
        await msg.reply_text(
            f'Сохранить название:\n<b>{title}</b>',
            reply_markup=keyboard_save_cancel_delete(func='handle_title'),
            parse_mode=ParseMode.HTML)
        return EDRState.CONFIRM_TITLE
    return ConversationHandler.END


async def save_changes(update: Update, context: PTBContext) -> int:
    """Сохраняем в БД и завершаем диалог."""
    msg = update.effective_message
    if context.user_data:
        edit = context.user_data.get('edit') or {}
    recipe_id: int = int(edit.get('recipe_id', 0))
    title = edit.get('title')

    if not recipe_id or not title:
        if msg:
            await msg.reply_text('Нет изменений для сохранения.')
        return ConversationHandler.END

    db = get_db(context)

    async with db.session() as session:
        await RecipeRepository.update_title(session, recipe_id, title)
    if msg and context.user_data:
        await msg.edit_text(
            '✅ Изменения сохранены.', reply_markup=home_keyboard()
        )
        context.user_data.pop('edit', None)
    return ConversationHandler.END


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
        await cq.edit_message_text('Не смог понять ID рецепта.')
        return ConversationHandler.END
    db = get_db(context)
    async with db.session() as session:
        # проверяем, есть ли рецепт с таким ID
        recipe_name = await RecipeRepository.get_name_by_id(session, recipe_id)

    # кладём ID в user_data для шага 2+
    if context.user_data:
        context.user_data['delete'] = {'recipe_id': recipe_id}
    await cq.edit_message_text(
        f'Вы точно хотите удалить рецепт <b>{recipe_name}</b>?',
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard_save_cancel_delete(func='delete_recipe'),
    )
    return EDRState.CONFIRM_DELETE


async def confirm_delete(update: Update, context: PTBContext) -> int:
    cq = update.callback_query
    if not cq:
        return ConversationHandler.END
    await cq.answer()
    recipe_id = None

    if context.user_data:
        delete_data = context.user_data.get('delete')
        if delete_data and 'recipe_id' in delete_data:
            recipe_id = delete_data['recipe_id']

    if not recipe_id:
        await cq.edit_message_text('Не смог понять ID рецепта.')
        return ConversationHandler.END
    db = get_db(context)

    async with db.session() as session:
        await RecipeRepository.delete(session, recipe_id)

    await cq.edit_message_text(
        '✅ Рецепт успешно удалён.',
        reply_markup=home_keyboard(),
        parse_mode=ParseMode.HTML
    )
    context.user_data.pop('delete', None)
    return ConversationHandler.END


async def change_category(update: Update, context: PTBContext) -> int:
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
    state = context.bot_data['state']
    service = CategoryService(db, state.redis)
    category = await service.get_all_category()
    if context.user_data:
        context.user_data['change_category'] = {'recipe_id': recipe_id}
    await cq.edit_message_text(
        '🏷️ Выберете новую категорию:',
        parse_mode=ParseMode.HTML,
        reply_markup=category_keyboard(category, RecipeMode.SAVE),
    )
    return EDRState.CONFIRM_CHANGE_CATEGORY


async def confirm_change_category(update: Update, context: PTBContext) -> int:
    cq = update.callback_query
    if not cq:
        return ConversationHandler.END
    await cq.answer()
    recipe_id = None

    if context.user_data:
        change_category = context.user_data.get('change_category')
        if change_category and 'recipe_id' in change_category:
            recipe_id = change_category['recipe_id']

    if not recipe_id:
        await cq.edit_message_text('Не смог понять ID рецепта.')
        return ConversationHandler.END
    category_slug = parse_category(cq.data or '')
    db = get_db(context)
    state = context.bot_data['state']
    service = CategoryService(db, state.redis)
    category_id, _ = await service.get_id_and_name_by_slug_cached(
        category_slug
    )
    async with db.session() as session:
        recipe_title = await RecipeRepository.update_category(
            session, recipe_id, category_id
        )
    await CategoryCacheRepository.invalidate_user_categories(
        state.redis, cq.from_user.id
    )
    await RecipeCacheRepository.invalidate_all_recipes_ids_and_titles(
        state.redis, cq.from_user.id, category_id
    )
    logger.info(f'🗑️ Инвалидирован кэш категорий юзера {cq.from_user.id}')
    await cq.edit_message_text(
            f'✅ Категория рецепта <b>{recipe_title}</b> изменена',
            parse_mode=ParseMode.HTML,
            reply_markup=home_keyboard()
        )
    context.user_data.pop('change_category', None)
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
            CallbackQueryHandler(start_edit, pattern=r'^edit_recipe_(\d+)$'),
            CallbackQueryHandler(
                    delete_recipe, pattern=r'^delete_recipe_\d+$'
                ),
            CallbackQueryHandler(
                    change_category, pattern=r'^change_category_\d+$'
                ),
        ],
        states={
            EDRState.CHOOSE_FIELD: [
                CallbackQueryHandler(
                    choose_field, pattern=r'^(f:title|f:desc|cancel)$'
                ),
                CallbackQueryHandler(cancel, pattern=r'^cancel$'),
            ],
            EDRState.WAIT_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_title),
                CallbackQueryHandler(cancel, pattern=r'^cancel$'),
            ],
            EDRState.CONFIRM_TITLE: [
                CallbackQueryHandler(save_changes, pattern=r'^save_changes$'),
                CallbackQueryHandler(cancel, pattern=r'^cancel$'),
            ],
            EDRState.CONFIRM_DELETE: [
                CallbackQueryHandler(confirm_delete, pattern=r'^delete$'),
                CallbackQueryHandler(cancel, pattern=r'^cancel$'),
            ],
            EDRState.CONFIRM_CHANGE_CATEGORY: [
                CallbackQueryHandler(
                    confirm_change_category,
                    pattern='^[a-z0-9][a-z0-9_-]*_save$'
                ),
                CallbackQueryHandler(cancel, pattern=r'^cancel$'),
            ]
        },
        fallbacks=[CallbackQueryHandler(cancel, pattern=r'^cancel$')],
        per_chat=True,
        per_user=True,
        # per_message=True,
        # conversation_timeout=600,  # 10 минут
        # name='edit_recipe_conv',   # если используешь persistence
        # persistent=True,
    )

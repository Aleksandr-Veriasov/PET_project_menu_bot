import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.db.db import get_session_context
from app.db.models import Recipe
from app.utils.helpers import (
    edit_reply_markup_safe,
    get_safe_callback_query,
    get_safe_message_from_update,
    get_safe_query_message,
    get_safe_text_from_update,
    get_safe_user_data,
)

logger = logging.getLogger(__name__)

# Состояния FSM
CHOOSE_EDIT_ACTION, EDIT_NAME = range(2)


async def start_edit(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    '''Запрашивает новое действие с рецептом: изменить или удалить.'''
    query = get_safe_callback_query(update)
    await query.answer()

    callback_data = query.data
    if callback_data is None:
        logger.warning('CallbackQuery.data отсутствует')
        return ConversationHandler.END
    recipe_id = int(callback_data.split('_')[-1])

    user_data = get_safe_user_data(context)
    user_data['recipe_id'] = recipe_id
    user_data['is_editing'] = True

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            '✏️ Изменить название', callback_data='edit_name'
        )],
        [InlineKeyboardButton('❌ Отмена', callback_data='cancel_edit')]
    ])

    message = get_safe_query_message(query)
    await message.reply_text(
        'Вы хотите отредактировать название рецепта?',
        reply_markup=keyboard
    )
    return CHOOSE_EDIT_ACTION


async def choose_edit_action(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    '''Обрабатывает выбор действия: изменить или удалить.'''
    query = get_safe_callback_query(update)
    await query.answer()

    action = query.data
    if action is None:
        logger.warning(
            "❌ CallbackQuery.data is None — невозможно определить действие"
        )
        return ConversationHandler.END
    user_data = get_safe_user_data(context)
    recipe_id = user_data.get('recipe_id')
    if not isinstance(recipe_id, int):
        logger.error(f"❌ Неверный recipe_id в user_data: {recipe_id}")
        return ConversationHandler.END
    message = get_safe_query_message(query)
    if action == 'edit_name':
        # Переходим к вводу нового названия
        await message.reply_text('Введите новое название рецепта:')
        return EDIT_NAME

    elif action == 'delete_recipe':
        # Запрашиваем подтверждение удаления рецепта
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    '✅ Да, удалить',
                    callback_data=f'confirm_delete_{recipe_id}'
                ),
                InlineKeyboardButton(
                    '❌ Нет, не удалять',
                    callback_data=f'cancel_delete_{recipe_id}'
                )
            ]
        ])
        await message.reply_text(
            'Вы уверены, что хотите удалить этот рецепт?',
            reply_markup=keyboard
        )
        # После отправки подтверждения завершаем FSM
        user_data.pop('is_editing', None)
        user_data.pop('recipe_id', None)
        return ConversationHandler.END

    elif action == 'cancel_edit':
        await cancel_edit(update, context)
        return ConversationHandler.END
    logger.warning(f"Неизвестное действие: {action}")
    return ConversationHandler.END


async def edit_name(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    '''Сохраняет новое название рецепта.'''
    text = get_safe_text_from_update(update)
    new_name = text.strip()
    user_data = get_safe_user_data(context)
    recipe_id = user_data.get('recipe_id')
    message = get_safe_message_from_update(update)

    with get_session_context() as session:
        recipe = session.query(Recipe).get(recipe_id)
        if not recipe:
            await message.reply_text('❌ Рецепт не найден.')
            user_data.pop('is_editing', None)
            user_data.pop('recipe_id', None)
            return ConversationHandler.END

        recipe.title = new_name
        session.commit()
        session.refresh(recipe)

    await message.reply_text('✅ Название рецепта обновлено!')

    # Очищаем временные данные
    user_data.pop('is_editing', None)
    user_data.pop('recipe_id', None)

    return ConversationHandler.END


async def cancel_edit(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    '''Обработка отмены редактирования.'''
    user_data = get_safe_user_data(context)
    user_data.pop('is_editing', None)
    user_data.pop('recipe_id', None)
    callback_query = get_safe_callback_query(update)

    if callback_query:
        await callback_query.answer()
        await edit_reply_markup_safe(callback_query)
        message = get_safe_query_message(callback_query)
        await message.reply_text("Редактирование отменено.")
    else:
        await get_safe_message_from_update(update).reply_text(
            'Редактирование отменено.'
        )

    return ConversationHandler.END


# ConversationHandler для FSM редактирования
edit_recipe_conv = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(start_edit, pattern='^redact_recipe_')
    ],
    states={
        CHOOSE_EDIT_ACTION: [
            CallbackQueryHandler(
                choose_edit_action,
                pattern='^(edit_name|delete_recipe|cancel_edit)$'
            )
        ],
        EDIT_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_name)
        ],
    },
    fallbacks=[
        CallbackQueryHandler(cancel_edit, pattern='^cancel_edit$')
    ],
    allow_reentry=True,
    per_message=False
)

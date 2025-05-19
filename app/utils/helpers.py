import logging
from typing import Any, Optional, cast

from telegram import CallbackQuery, InlineKeyboardMarkup, Message, Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


def get_safe_query_message(query: CallbackQuery) -> Message:
    ''' Возвращает сообщение из CallbackQuery, если оно существует. '''
    if query.message is None:
        logger.error("❌ query.message is None — невозможно продолжить")
        raise ValueError("query.message is None")
    return cast(Message, query.message)  # теперь тип — строго Message


def get_safe_callback_query(update: Update) -> CallbackQuery:
    '''Возвращает CallbackQuery, если он есть, иначе выбрасывает ошибку.'''
    if update.callback_query is None:
        logger.error("❌ update.callback_query is None — невозможно продолжить")
        raise ValueError("update.callback_query is None")
    return update.callback_query


def get_safe_user_data(context: ContextTypes.DEFAULT_TYPE) -> dict[str, Any]:
    '''Возвращает user_data, гарантированно как словарь.'''
    if context.user_data is None:
        logger.error("❌ context.user_data is None — невозможно продолжить")
        raise ValueError("context.user_data is None")
    return context.user_data


def get_safe_message_from_update(update: Update) -> Message:
    '''Возвращает update.message с гарантией типа Message.'''
    if update.message is None:
        logger.error("❌ update.message is None — невозможно продолжить")
        raise ValueError("update.message is None")
    return update.message


def get_safe_text_from_update(update: Update) -> str:
    '''
    Возвращает текст сообщения, если он существует, иначе выбрасывает ошибку.
    '''
    if update.message is None:
        logger.error("❌ update.message is None — сообщение отсутствует")
        raise ValueError("update.message is None")
    if update.message.text is None:
        logger.error(
            "❌ update.message.text is None — это не текстовое сообщение"
        )
        raise ValueError("update.message.text is None")
    return update.message.text


def get_safe_callback_data(query: CallbackQuery) -> str:
    if query.data is None:
        logger.error("❌ query.data is None — невозможно продолжить")
        raise ValueError("query.data is None")
    return query.data


async def edit_reply_markup_safe(
    query: CallbackQuery,
    reply_markup: Optional[InlineKeyboardMarkup] = None
) -> None:
    '''Безопасно вызывает edit_reply_markup, если message существует.'''
    if query.message is None:
        logger.warning(
            "❌ query.message is None — не могу отредактировать клавиатуру"
        )
        return

    message = cast(Message, query.message)
    try:
        await message.edit_reply_markup(reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Ошибка при вызове edit_reply_markup: {e}")

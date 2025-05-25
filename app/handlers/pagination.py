import logging

from telegram import Update
from telegram.ext import ContextTypes

from app.utils.helpers import (
    get_safe_callback_query,
    get_safe_query_message,
    get_safe_user_data,
)
from app.utils.message_utils import send_recipe_list

# Включаем логирование
logger = logging.getLogger(__name__)


async def handle_recipe_pagination(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    '''Обрабатывает нажатие кнопок пагинации.'''
    query = get_safe_callback_query(update)
    await query.answer()

    user_data = get_safe_user_data(context)
    # Получаем список рецептов из context.user_data
    recipes = user_data.get('recipes', [])
    # При извлечении списка рецептов
    if not recipes:
        message = get_safe_query_message(query)
        await message.reply_text('Список рецептов пуст.')
        return

    # Определяем текущую страницу из callback_data
    data = query.data
    if data is None:
        logger.warning('CallbackQuery.data отсутствует')
        return
    if data.startswith(('next_', 'prev_')):
        try:
            page = int(data.split('_')[1])
        except ValueError:
            logger.error(f'Невозможно разобрать номер страницы из "{data}"')
            return
    else:
        page = 0

    edit_mode = user_data.get('is_editing', False)
    # Отправляем обновлённый список рецептов
    await send_recipe_list(update, context, recipes, page=page, edit=edit_mode)

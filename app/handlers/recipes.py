import logging
from datetime import datetime
from typing import cast

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    Update
)
from telegram.ext import CallbackContext, ContextTypes

from app.db.db import get_session_context
from app.db.db_utils import (
    add_category_if_not_exists,
    add_recipe,
    add_user_if_not_exists,
    add_video_to_recipe,
    delete_recipe,
    get_recipe,
)
from app.utils.helpers import (
    get_safe_callback_data,
    get_safe_callback_query,
    get_safe_user_data,
)
from app.utils.recipe_edit import start_edit
from app.utils.state import user_data_tempotary

logger = logging.getLogger(__name__)


async def handle_category_choice(
    update: Update, context: CallbackContext
) -> None:
    '''
    Обработчик для кнопок выбора категории рецепта.
    Добавление рецепта в БД.
    '''
    query = get_safe_callback_query(update)
    await query.answer()

    user_id = query.from_user.id
    user_info = user_data_tempotary.get(user_id, {})

    # Получаем информацию о пользователе
    username: str = query.from_user.username or ''
    first_name: str = query.from_user.first_name or ''
    last_name: str = query.from_user.last_name or ''
    created_at = datetime.now()

    # Выводим для отладки
    logger.info(
        f'Пользователь {user_id} выбрал категорию: {query.data}'
    )

    # Логика для получения ID категории
    category = query.data  # Выбираем категорию

    # Добавляем категорию в базу, если её нет
    category_name = ''
    if category == 'breakfast':
        category_name = 'Завтрак'
    elif category == 'main_course':
        category_name = 'Основное блюдо'
    elif category == 'salad':
        category_name = 'Салат'

    # Добавляем категорию в таблицу, если её нет
    logger.info(f'Пользователь {user_id} выбрал категорию: {category_name}')
    with get_session_context() as session:
        category_obj = add_category_if_not_exists(category_name, session)
        logger.info(f'Категория {category_name} добавлена в базу данных.')

        # Получаем ID категории
        category_id: int = int(category_obj.id)

        # Проверяем, существует ли пользователь в базе данных.
        # Если нет, добавляем его
        add_user_if_not_exists(
            user_id,
            username,
            first_name,
            last_name,
            created_at,
            session
        )

        # Получаем временно сохраненные данные рецепта
        title = user_info.get('title', 'Не указано')
        recipe = user_info.get('recipe', 'Не указан')
        ingredients = user_info.get('ingredients', 'Не указаны')

        logger.info('Добавляем рецепт в базу данных.')
        # Сохраняем рецепт в базе данных
        new_recipe = add_recipe(
            user_id,
            title,
            recipe,
            ingredients,
            category_id,
            session
        )
        logger.info(f'Рецепт успешно добавлен с ID: {new_recipe.id}')
        # Получаем путь к видео из user_data
        user_data = get_safe_user_data(context)
        video_file_id = user_data.get('video_file_id')
        logger.info(f'Получаем video_file_id: {video_file_id}')

        # Проверяем, если видео URL существует
        if video_file_id:
            # Сохраняем видео в базу данных
            new_recipe_id: int = int(new_recipe.id)
            add_video_to_recipe(new_recipe_id, video_file_id, session)

        await query.edit_message_text(
            f'✅ Ваш рецепт успешно сохранен!\n\n'
            f'🍽 <b>Название рецепта:</b>\n{title}\n\n'
            f'🔖 <b>Категория:</b> {category_name}',
            parse_mode='HTML'  # Включаем HTML для форматирования
        )


async def handle_recipe_choice(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    ''' Обработчик вызова рецепта. '''
    edit = False
    query = get_safe_callback_query(update)
    await query.answer()
    # Получаем callback_data
    callback_data = get_safe_callback_data(query)
    if callback_data.startswith('edit_recipe_'):
        recipe_id = int(callback_data.split('_')[2])
        edit = True
        keyboard = [
            [InlineKeyboardButton(
                'Редактировать рецепт',
                callback_data=f'redact_recipe_{recipe_id}'
            )],
            [InlineKeyboardButton(
                'Удалить рецепт',
                callback_data=f'delete_recipe_{recipe_id}'
            )]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
    else:
        # Получаем ID рецепта из callback_data
        recipe_id = int(callback_data.split('_')[1])
    # Получаем рецепт по ID из базы
    with get_session_context() as session:
        recipe = get_recipe(recipe_id, session)

        if not recipe:
            await query.edit_message_text('❌ Рецепт не найден.')
            return

        # Ищем видео, привязанное к этому рецепту
        video = recipe.video
        message = cast(Message, query.message)
        if video:
            # Отправляем видео пользователю
            await message.reply_video(video.video_url)

        # Отправляем подробности о рецепте
        ingredients_text = '\n'.join(
            f'- {ingredient.name}' for ingredient in recipe.ingredients
        )
        text = (
            f'🍽 <b>Название рецепта:</b> {recipe.title}\n\n'
            f'📝 <b>Рецепт:</b>\n{recipe.description}\n\n'
            f'🥦 <b>Ингредиенты:</b>\n{ingredients_text}'
        )
        await message.reply_text(
            text,
            parse_mode='HTML',
            reply_markup=reply_markup if edit else None
        )


async def handle_edit_delete_recipe(
    update: Update, context: CallbackContext
) -> None:
    ''' Обработчик для редактирования или удаления рецепта. '''
    query = get_safe_callback_query(update)
    await query.answer()

    # Получаем ID рецепта из callback_data
    callback_data = get_safe_callback_data(query)
    recipe_id = int(callback_data.split('_')[2])

    if callback_data.startswith('redact_recipe_'):
        # Логика редактирования рецепта
        await start_edit(update, context)

    elif callback_data.startswith('delete_recipe_'):
        # Логика удаления рецепта
        keyboard = [
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
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            'Вы уверены, что хотите удалить этот рецепт?',
            reply_markup=reply_markup
        )


async def handle_confirm_delete(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    ''' Обработчик подтверждения или отмены удаления рецепта. '''
    query = get_safe_callback_query(update)
    await query.answer()

    callback_data = get_safe_callback_data(query)
    recipe_id = int(callback_data.split('_')[2])

    if callback_data.startswith('confirm_delete_'):
        # Удаляем рецепт
        with get_session_context() as session:
            delete_recipe(recipe_id, session)
            await query.edit_message_text('✅ Рецепт успешно удалён.')
    elif callback_data.startswith('cancel_delete_'):
        # Отмена удаления
        await query.edit_message_text('❎ Удаление рецепта отменено.')

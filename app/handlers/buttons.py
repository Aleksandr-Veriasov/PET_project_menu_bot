import logging

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import CallbackContext, ContextTypes

from app.db.db import get_engine, get_session
from app.db.db_utils import get_recipes_by_category_name
from app.utils.helpers import (
    get_safe_callback_query,
    get_safe_message_from_update,
    get_safe_user_data,
)
from app.utils.message_utils import send_random_recipe, send_recipe_list
from app.utils.state import user_data_tempotary

# Включаем логирование
logger = logging.getLogger(__name__)

engine = get_engine()
session = get_session(engine)


async def handle_button_click(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    ''' Обработчик для кнопок 'Рецепты', 'Случайное блюдо', 'Загрузить' и '''
    ''' 'Редактировать рецепты'. '''
    user_data = get_safe_user_data(context)
    user_data['is_editing'] = False
    message = get_safe_message_from_update(update)
    user_text = message.text or ''

    if user_text == 'Рецепты':
        new_keyboard = [
            [KeyboardButton('Завтрак')],
            [KeyboardButton('Основное блюдо')],
            [KeyboardButton('Салат')]
        ]
        reply_markup = ReplyKeyboardMarkup(new_keyboard, resize_keyboard=True)
        await message.reply_text(
            '🔖 Выберите раздел:',
            reply_markup=reply_markup
        )

    elif user_text == 'Случайное блюдо':
        new_keyboard = [
            [KeyboardButton('Случайный завтрак')],
            [KeyboardButton('Случайное горячее')],
            [KeyboardButton('Случайный салат')]
        ]
        reply_markup = ReplyKeyboardMarkup(new_keyboard, resize_keyboard=True)
        await message.reply_text(
            '🔖 Выберите раздел:',
            reply_markup=reply_markup
        )

    elif user_text == 'Загрузить':
        await message.reply_text(
            'Пожалуйста, отправьте ссылку на видео для загрузки.'
        )

    elif user_text == 'Редактировать рецепты':
        new_keyboard = [
            [KeyboardButton('Изменить завтрак')],
            [KeyboardButton('Изменить основное блюдо')],
            [KeyboardButton('Изменить салат')]
        ]
        reply_markup = ReplyKeyboardMarkup(new_keyboard, resize_keyboard=True)
        await message.reply_text(
            '🔖 Выберите раздел для редактирования рецепта:',
            reply_markup=reply_markup
        )


async def handle_button_click_recipe(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    '''Обработчик для кнопок выбора категории и случайных блюд.'''
    user_data = get_safe_user_data(context)
    user_data['is_editing'] = False
    logger.info(
        f'handle_button_click сработал. '
        f'is_editing={user_data.get("is_editing")}'
    )
    if user_data.get('is_editing'):
        logger.info('Пользователь редактирует рецепт — не обрабатываем кнопку')
        # Пользователь редактирует рецепт — не обрабатываем кнопку
        return
    message = get_safe_message_from_update(update)
    user_text = message.text or ''

    if message.from_user is None:
        logger.warning('Пользователь неизвестен (from_user is None)')
        return
    user_id = message.from_user.id

    logger.info(
        f'Пользователь {user_id} выбрал категорию: {user_text}'
    )

    # Карта категорий для рецептов
    category_map = {
        'Завтрак': 'Завтрак',
        'Основное блюдо': 'Основное блюдо',
        'Салат': 'Салат',
        'Случайный завтрак': 'Завтрак',
        'Случайное горячее': 'Основное блюдо',
        'Случайный салат': 'Салат',
        'Изменить завтрак': 'Завтрак',
        'Изменить основное блюдо': 'Основное блюдо',
        'Изменить салат': 'Салат',
    }

    # Определяем категорию
    category = category_map.get(user_text)

    if not category:
        await message.reply_text(
            'Что-то пошло не так, пожалуйста, попробуйте снова.'
        )
        return
    session.expire_all()
    # Получаем рецепты для категории
    recipes = get_recipes_by_category_name(user_id, category, session)

    if not recipes:
        await message.reply_text(
            f'У вас нет рецептов в категории "{category}".'
        )
        return

    # Если запрос на случайный рецепт
    if user_text.startswith(('Случайный', 'Случайное')):
        await send_random_recipe(update, category, recipes)
    elif user_text.startswith('Изменить'):
        await send_recipe_list(update, context, recipes, edit=True)
    else:
        await send_recipe_list(update, context, recipes)


async def handle_confirm_changes(
    update: Update, context: CallbackContext
) -> None:
    ''' Обработчик для кнопок 'Сохранить Рецепт' и 'Не сохранять'. '''
    query = get_safe_callback_query(update)
    await query.answer()

    user_id = query.from_user.id
    user_info = user_data_tempotary.get(user_id, {})

    # Если пользователь выбрал 'Сохранить рецепт'
    if query.data == 'save_recipe':
        logger.info(f'Пользователь {user_id} выбрал сохранить рецепт.')

        # Получаем временно сохраненные данные рецепта
        title = user_info.get('title', 'Не указано')

        new_keyboard = [
            [InlineKeyboardButton('🥞 Завтрак', callback_data='breakfast')],
            [InlineKeyboardButton(
                '🍝 Основное блюдо',
                callback_data='main_course'
            )],
            [InlineKeyboardButton('🥗 Салат', callback_data='salad')]
        ]

        reply_markup = InlineKeyboardMarkup(new_keyboard)

        # Отправляем подтверждение пользователю
        await query.edit_message_text(
            f'🔖 <b>Выберете категорию для этого рецепта:</b>\n\n'
            f'🍽 <b>Название рецепта:</b>\n{title}\n\n',
            parse_mode='HTML',  # Включаем HTML для форматирования
            reply_markup=reply_markup
        )
        logger.debug(f'Временные данные рецепта: {user_info}')
    elif query.data == 'discard_recipe':
        await query.edit_message_text(
            '❌ Рецепт не был сохранен. Завершаем работу.'
        )
        logger.info(f'Пользователь {user_id} выбрал не сохранять рецепт.')

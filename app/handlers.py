import asyncio
import logging
import os
from datetime import datetime
from typing import cast

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.audio_extractor import extract_audio
from app.db import get_engine, get_session
from app.db_utils import (
    add_category_if_not_exists,
    add_recipe,
    add_user_if_not_exists,
    add_video_to_recipe,
    delete_recipe,
    get_recipe,
    get_recipes_by_category_name,
)
from app.deepseek_api import extract_recipe_data_async
from app.helpers import (
    get_safe_callback_data,
    get_safe_callback_query,
    get_safe_message_from_update,
    get_safe_query_message,
    get_safe_text_from_update,
    get_safe_user_data,
)
from app.message_utils import (
    send_random_recipe,
    send_recipe_confirmation,
    send_recipe_list,
)
from app.recipe_edit import edit_recipe_conv, start_edit
from app.speech_recognition import async_transcribe_audio
from app.state import user_data_tempotary
from app.video_downloader import (
    async_convert_to_mp4,
    async_download_video_and_description,
    send_video_to_channel,
)

# Включаем логирование
logger = logging.getLogger(__name__)

engine = get_engine()
session = get_session(engine)

AUDIO_FOLDER = 'audio/'


# Создание шаблона ссылки для видео
video_link_pattern = (
    r'(https?://)?(www\.)?'
    r'(youtube\.com|youtu\.be|tiktok\.com|instagram\.com|vimeo\.com)/\S+'
)


async def start(update: Update, context: CallbackContext) -> None:
    ''' Приветственное сообщение. '''
    # Создаем кнопки для меню
    keyboard = [
        [KeyboardButton('Рецепты'), KeyboardButton('Случайное блюдо')],
        [KeyboardButton('Загрузить'), KeyboardButton('Редактировать рецепты')]
    ]

    # Разметка для кнопок
    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        one_time_keyboard=True,
        resize_keyboard=True
    )

    # Приветственное сообщение
    if update.message:
        await update.message.reply_text(
            'Привет! 👋 Я — бот, который помогает вам удобно сохранять '
            '<b>рецепты</b>, которые вам понравились в <b>ТикТоке</b> или '
            '<b>Инстаграме</b>. Вот что я могу сделать для вас:\n\n'
            '✨ <b>Сохранить рецепты</b> и ингредиенты из видео\n'
            '🔍 <b>Искать рецепты</b> по категориям\n'
            '🎲 <b>Предложить случайное блюдо</b> на ваш выбор\n\n'
            '<b>Выберите действие</b> 👇',
            parse_mode='HTML',  # Включаем HTML для форматирования
            reply_markup=reply_markup
        )
    else:
        logger.error('update.message отсутствует в функции start')


async def handle_button_click(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    ''' Обработчик для кнопок 'Рецепты', 'Случайное блюдо', 'Загрузить' и '''
    ''' 'Редактировать рецепты'. '''
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
    if data.startswith('next_'):
        page = int(data.split('_')[1])
    elif data.startswith('prev_'):
        page = int(data.split('_')[1])
    else:
        page = 0

    # Отправляем обновлённый список рецептов
    await send_recipe_list(update, context, recipes, page=page)


async def handle_video_link(update: Update, context: CallbackContext) -> None:
    try:
        url = get_safe_text_from_update(update)
        message = get_safe_message_from_update(update)
    except ValueError as e:
        logger.error(f'Ошибка: {e}')
        if update.message:
            await update.message.reply_text(
                '❌ Ошибка: Сообщение не содержит текста.'
            )
        return

    logger.info(f'Пользователь отправил ссылку: {url}')
    await message.reply_text(
        '✅ Ссылка получена. Обработка запущена...'
    )

    # Запускаем обработку в фоне (без ожидания)
    asyncio.create_task(process_video_pipeline(url, message, context))


async def process_video_pipeline(
    url: str, message: Message, context: CallbackContext
) -> None:
    try:
        await message.reply_text(
            '🔄 Скачиваю видео и описание...\n'
            'Это может занять некоторое время, пожалуста, подождите.'
        )
        video_path, description = await async_download_video_and_description(
            url
        )

        if not video_path:
            await message.reply_text(
                '❌ Не удалось скачать видео.\n'
                'Пожалуйста, попробуйте снова.'
            )
            return

        converted_path = await async_convert_to_mp4(video_path)
        video_file_id = await send_video_to_channel(
            context, converted_path
        )
        user_data = get_safe_user_data(context)
        user_data['video_file_id'] = video_file_id
        user_data['video_path'] = converted_path

        await message.reply_text(
            '✅ Видео загружено. Распознаём текст...\n'
            'Осталось еще немного подождать.'
        )
        audio_path = extract_audio(converted_path, AUDIO_FOLDER)
        transcript = await async_transcribe_audio(audio_path)

        await message.reply_text(
            '🧠 Подготавливаем рецепт через AI...\n'
            'Это займет еще 20 секунд, рецепт практически готов!'
        )
        title, recipe, ingredients = await extract_recipe_data_async(
            description, transcript
        )

        if title and recipe:
            await send_recipe_confirmation(
                message, title, recipe, ingredients, video_file_id
            )
        else:
            await message.reply_text('❌ Не удалось извлечь данные из видео.')

        for path in [video_path, converted_path, audio_path]:
            if path and os.path.exists(path):
                os.remove(path)

    except Exception as e:
        logger.exception(f'Ошибка при обработке видео: {e}')
        await message.reply_text(
            '❌ Произошла ошибка при обработке видео.\n'
            'Пожалуйста, попробуйте еще раз.'
        )


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
    category_obj = add_category_if_not_exists(category_name, session)
    logger.info(f'Категория {category_name} добавлена в базу данных.')

    # Получаем ID категории
    category_id: int = int(category_obj.id)

    # Проверяем, существует ли пользователь в базе данныхю.
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
    session.expire_all()
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
        delete_recipe(recipe_id, session)
        await query.edit_message_text('✅ Рецепт успешно удалён.')
    elif callback_data.startswith('cancel_delete_'):
        # Отмена удаления
        await query.edit_message_text('❎ Удаление рецепта отменено.')


# Регистрация хандлеров
def setup_handlers(app):
    # Обработчик для редактирования рецепта
    logger.info('Регистрация обработчика редактирования рецепта')
    app.add_handler(edit_recipe_conv)

    # Обработчик для команды /start
    logger.info('Регистрация обработчика команды /start')
    app.add_handler(CommandHandler('start', start))

    # Обработчик для ссылок на видео
    logger.info('Регистрация обработчика ссылок на видео')
    app.add_handler(MessageHandler(
        filters.Regex(video_link_pattern) & filters.TEXT, handle_video_link
    ))

    # Обработчик для кнопок 'Рецепты', 'Случайное блюдо' и 'Загрузить'
    logger.info('Регистрация обработчика кнопок')
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(
            '^(Рецепты|Загрузить|Случайное блюдо|Редактировать рецепты)$'
        ),
        handle_button_click
    ))

    # Обработчик для кнопок выбора категории и случайных блюд
    logger.info('Регистрация обработчика кнопок выбора категории')
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(
            r'^(Завтрак|Основное блюдо|Салат|Случайный завтрак|'
            r'Случайное горячее|Случайный салат|Изменить завтрак|'
            r'Изменить основное блюдо|Изменить салат)$|'
        ),
        handle_button_click_recipe
    ))

    # Обработчик для подтверждения изменений
    logger.info('Регистрация обработчика подтверждения изменений')
    app.add_handler(CallbackQueryHandler(
        handle_confirm_changes,
        pattern='^(save_recipe|discard_recipe)$'
    ))

    # Обработчик для подтверждения изменений
    logger.info('Регистрация обработчика выбора категории')
    app.add_handler(CallbackQueryHandler(
        handle_category_choice,
        pattern='^(breakfast|main_course|salad)$'
    ))

    # Обработчик для выбора рецепта
    logger.info('Регистрация обработчика выбора рецепта')
    app.add_handler(CallbackQueryHandler(
        handle_recipe_choice, pattern='^recipe_|edit_recipe_'
    ))

    # Обработчик для пагинации рецептов
    logger.info('Регистрация обработчика пагинации рецептов')
    app.add_handler(CallbackQueryHandler(
        handle_recipe_pagination, pattern='^(next|prev)_'
    ))

    # Обработчик для редактирования и удаления рецепта
    logger.info('Регистрация обработчика редактирования и удаления рецепта')
    app.add_handler(CallbackQueryHandler(
        handle_edit_delete_recipe,
        pattern='^(redact_recipe_|delete_recipe_)'
    ))

    # Обработчик для подтверждения удаления рецепта
    logger.info('Регистрация обработчика подтверждения удаления рецепта')
    app.add_handler(CallbackQueryHandler(
        handle_confirm_delete,
        pattern='^(confirm_delete_|cancel_delete_)'
    ))

import logging
import os
from datetime import datetime
import random

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters
)

from audio_extractor import extract_audio
from db_utils import (
    add_category_if_not_exists,
    add_recipe,
    add_user_if_not_exists,
    add_video_to_recipe,
    get_recipe,
    get_recipes_by_category_name,
)
from deepseek_api import extract_recipe_data_with_deepseek
from speech_recognition import transcribe_audio
from video_downloader import (
    convert_to_mp4,
    download_video_and_description,
    send_video_to_channel,
)

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Используем глобальный словарь для хранения данных до подтверждения
user_data = {}

# Создание шаблона ссылки для видео
video_link_pattern = (
    r'(https?://)?(www\.)?'
    r'(youtube\.com|youtu\.be|tiktok\.com|instagram\.com|vimeo\.com)/\S+'
)


async def start(update: Update, context: CallbackContext):
    ''' Приветственное сообщение. '''
    # Создаем кнопки для меню
    keyboard = [
        [KeyboardButton('Рецепты')],
        [KeyboardButton('Случайное блюдо')],
        [KeyboardButton('Загрузить')]
    ]

    # Разметка для кнопок
    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        one_time_keyboard=True,
        resize_keyboard=True
    )

    # Приветственное сообщение
    await update.message.reply_text(
        'Привет! 👋 Я — бот, который помогает вам удобно сохранять '
        '<b>рецепты</b>, которые вам понравились в <b>ТикТоке</b> или '
        '<b>Инстаграме</b>. Вот что я могу сделать для вас:\n\n'
        '✨ <b>Сохранить рецепты</b> и ингредиенты из видео\n'
        '🔍 <b>Искать рецепты</b> по ингредиентам\n'
        '🎲 <b>Предложить случайное блюдо</b> на ваш выбор\n\n'
        '<b>Выберите действие</b> 👇',
        parse_mode='HTML',  # Включаем HTML для форматирования
        reply_markup=reply_markup
    )


async def handle_button_click(update, context):
    ''' Обработчик для кнопок 'Рецепты', 'Случайное блюдо' и 'Загрузить'. '''
    user_text = update.message.text

    if user_text == 'Рецепты':
        new_keyboard = [
            [KeyboardButton('Завтрак')],
            [KeyboardButton('Основное блюдо')],
            [KeyboardButton('Салат')]
        ]
        reply_markup = ReplyKeyboardMarkup(new_keyboard, resize_keyboard=True)
        await update.message.reply_text(
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
        await update.message.reply_text(
            '🔖 Выберите раздел:',
            reply_markup=reply_markup
        )

    elif user_text == 'Загрузить':
        await update.message.reply_text(
            'Пожалуйста, отправьте ссылку на видео для загрузки.'
        )


async def handle_button_click_recipe(update, context):
    ''' Обработчик для кнопок выбора категории и случайных блюд. '''
    user_text = update.message.text
    user_id = update.message.from_user.id

    logging.info(f"Получено сообщение: {user_text}")

    if user_text in ['Завтрак', 'Основное блюдо', 'Салат']:
        logging.info(f"Обрабатываем категорию: {user_text}")
        recipes = get_recipes_by_category_name(user_id, user_text)

        if not recipes:
            await update.message.reply_text(
                'У вас пока нет сохраненных рецептов.'
            )
            return

        keyboard = []
        for recipe in recipes:
            # Добавляем кнопки с названиями рецептов
            keyboard.append([InlineKeyboardButton(
                recipe.title,
                callback_data=f'recipe_{recipe.id}'
            )])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            'Выберите рецепт:',
            reply_markup=reply_markup
        )

    elif user_text in [
        'Случайный завтрак',
        'Случайное горячее',
        'Случайный салат'
    ]:
        category_map = {
            'Случайный завтрак': 'Завтрак',
            'Случайное горячее': 'Основное блюдо',
            'Случайный салат': 'Салат'
        }

        category = category_map.get(user_text)

        if category:
            recipes = get_recipes_by_category_name(user_id, category)

            if not recipes:
                await update.message.reply_text(
                    f'У вас нет рецептов в категории "{category}".'
                )
                return

            # Выбираем случайный рецепт из категории
            random_recipe = random.choice(recipes)

            await update.message.reply_text(
                f"Вот случайный рецепт из категории '{category}':\n\n"
                f"🍽 **{random_recipe.title}**\n\n"
                f"📝 {random_recipe.description}\n\n"
                f"🥦 **Ингредиенты:** {', '.join([ingredient.name for ingredient in random_recipe.ingredients])}"
            )
        else:
            await update.message.reply_text("Что-то пошло не так, пожалуйста, попробуйте снова.")



async def handle_video_link(update: Update, context: CallbackContext):
    ''' Функция скачивания по ссылке и обработке видео. '''
    logging.info('Получена ссылка: %s', update.message.text)
    try:
        url = update.message.text
        await update.message.reply_text(
            '🔄 Скачиваю видео и описание. Это займет немного времени...'
        )

        video_path, description = download_video_and_description(url)
        if not video_path:
            await update.message.reply_text(
                '❌ Ошибка: Не удалось скачать видео.'
            )
            return

        # Конвертируем видео
        converted_video_path = convert_to_mp4(video_path)

        # Сохраняем путь к видео в user_data
        context.user_data['video_path'] = converted_video_path

        # Отправляем видео в канал, но не сохраняем его сразу
        video_file_id = await send_video_to_channel(
            update,
            context,
            converted_video_path
        )

        # Сохраняем ссылку на видео в user_data
        context.user_data['video_file_id'] = video_file_id

        await update.message.reply_text(
            '✅ Видео успешно скачано!\n'
            'Распознаем текст из видео...'
        )

        # Извлекаем аудио и распознаем текст после отправки видео**
        audio_path = extract_audio(converted_video_path)
        recognized_text = transcribe_audio(audio_path)

        # Теперь передаем описание (если оно есть) и распознанный текст
        # в DeepSeek API
        await update.message.reply_text(
            '🤖 Распознание рецепта и ингредиентов AI...'
        )
        title, recipe, ingredients = extract_recipe_data_with_deepseek(
            description,
            recognized_text
        )

        if title and recipe and ingredients:
            await send_recipe_confirmation(
                update,
                title,
                recipe,
                ingredients,
                video_file_id
            )
        else:
            await update.message.reply_text(
                '❌ Не удалось извлечь данные из описания и текста.'
            )

        # Удаляем файлы после отправки
        for file in [video_path, converted_video_path, audio_path]:
            if os.path.exists(file):
                os.remove(file)

    except Exception as e:
        logging.error(f'Ошибка обработки видео или аудио: {e}')
        await update.message.reply_text(f'❌ Произошла ошибка: {str(e)}')


async def send_recipe_confirmation(
        update,
        title,
        recipe,
        ingredients,
        video_file_id
):
    '''
    Функция отправляет пользователю сообщение с рецептом и кнопками для
    подтверждения или редактирования.
    '''
    logging.info('Кнопки появились')
    user_id = update.message.from_user.id
    user_data[user_id] = {
        'title': title,
        'recipe': recipe,
        'ingredients': ingredients
    }

    keyboard = [
        [InlineKeyboardButton(
            '✅ Сохранить рецепт',
            callback_data='save_recipe'
        )],
        [InlineKeyboardButton(
            '❌ Не сохранять рецепт',
            callback_data='discard_recipe'
        )]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Отправляем видео с file_id
    await update.message.reply_video(video_file_id)

    await update.message.reply_text(
        f'🍽 <b>Название рецепта:</b>\n{title}\n\n'
        f'📝 <b>Рецепт:</b>\n{recipe}\n\n'
        f'🥦 <b>Ингредиенты:</b>\n{ingredients}\n\n',
        parse_mode='HTML',  # Включаем HTML для форматирования
        reply_markup=reply_markup
    )


async def handle_confirm_changes(update, context):
    ''' Обработчик для кнопок 'Сохранить Рецепт' и 'Не сохранять'. '''
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user_info = user_data.get(user_id, {})

    # Если пользователь выбрал 'Сохранить рецепт'
    if query.data == 'save_recipe':
        logging.info('Сохранение рецепта')

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

    elif query.data == 'discard_recipe':
        await query.edit_message_text(
            '❌ Рецепт не был сохранен. Завершаем работу.'
        )


async def handle_category_choice(update, context):
    '''
    Обработчик для кнопок выбора категории рецепта.
    Добавление рецепта в БД.
    '''
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user_info = user_data.get(user_id, {})

    # Получаем информацию о пользователе
    username = query.from_user.username
    first_name = query.from_user.first_name
    last_name = query.from_user.last_name
    created_at = datetime.now()

    # Выводим для отладки
    logging.info(
        f'User {first_name} {last_name} (username: {username}) '
        'confirmed changes.'
    )

    # Получаем ID рецепта из callback_data
    recipe_id = context.user_data.get('recipe_id')
    category = query.data  # Выбираем категорию

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
    category_obj = add_category_if_not_exists(category_name)

    # Получаем ID категории
    category_id = category_obj.id

    # Проверяем, существует ли пользователь в базе данныхю.
    # Если нет, добавляем его
    add_user_if_not_exists(
        user_id,
        username,
        first_name,
        last_name,
        created_at
    )

    # Получаем временно сохраненные данные рецепта
    title = user_info.get('title', 'Не указано')
    recipe = user_info.get('recipe', 'Не указан')
    ingredients = user_info.get('ingredients', 'Не указаны')

    logging.info('Добавление рецепта в БД')
    # Сохраняем рецепт в базе данных
    new_recipe = add_recipe(user_id, title, recipe, ingredients, category_id)

    # Получаем путь к видео из user_data
    video_file_id = context.user_data.get('video_file_id')
    logging.info(f'video_file_id= {video_file_id}')

    # Проверяем, если видео URL существует
    if video_file_id:
        # Сохраняем видео в базу данных
        add_video_to_recipe(new_recipe.id, video_file_id)

    await query.edit_message_text(
        f'✅ Ваш рецепт успешно сохранен!\n\n'
        f'🍽 <b>Название рецепта:</b>\n{title}\n\n'
        f'🔖 <b>Категория:</b> {category_name}',
        parse_mode='HTML'  # Включаем HTML для форматирования
    )


async def send_recipe_suggestions(update, context):
    ''' Обработчик кнопки 'Рецепты'. '''
    user_id = update.message.from_user.id
    recipes = get_user_recipes_by_category(user_id)

    if not recipes:
        await update.message.reply_text('У вас пока нет сохраненных рецептов.')
        return

    keyboard = []
    for recipe in recipes:
        # Добавляем кнопки с названиями рецептов
        keyboard.append([InlineKeyboardButton(
            recipe.title,
            callback_data=f'recipe_{recipe.id}'
        )])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        'Выберите рецепт:',
        reply_markup=reply_markup
    )


async def handle_recipe_choice(update, context):
    ''' Обработчик вызова рецепта. '''
    query = update.callback_query
    await query.answer()

    recipe_id = int(query.data.split('_')[1])  # Получаем ID рецепта из callback_data
    recipe = get_recipe(recipe_id)  # Получаем рецепт по ID из базы

    if not recipe:
        await query.edit_message_text('❌ Рецепт не найден.')
        return

    # Ищем видео, привязанное к этому рецепту
    video = recipe.video  # Связь `relationship('Video', backref='recipe', uselist=False)`

    if video:
        # Отправляем видео пользователю
        await query.message.reply_video(video.video_url)

    # Отправляем подробности о рецепте
    await query.message.reply_text(
        f'🍽 <b>Название рецепта:</b> {recipe.title}\n\n'
        f'📝 <b>Рецепт:</b>\n{recipe.description}\n\n'
        f'🥦 <b>Ингредиенты:</b>\n{", ".join([ingredient.name for ingredient in recipe.ingredients])}',
        parse_mode='HTML'
    )

# Функция для предложения первого рецепта
async def suggest_recipe(update, context):
    user_id = update.message.from_user.id
    recipes = get_user_recipes(user_id)

    if not recipes:
        await update.message.reply_text('У вас пока нет сохраненных рецептов.')
        return

    # Получаем первый рецепт из списка
    first_recipe = recipes[0]

    # Кнопка для подтверждения рецепта
    keyboard = [
        [InlineKeyboardButton(f'Предложить: {first_recipe.title}', callback_data=f'suggest_{first_recipe.id}')]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Нажмите на кнопку, чтобы предложить первый рецепт из списка:', reply_markup=reply_markup)

# Обработчик выбора рецепта из предложенных
async def handle_suggested_recipe(update, context):
    query = update.callback_query
    await query.answer()

    recipe_id = int(query.data.split('_')[1])  # Получаем ID рецепта из callback_data
    recipe = get_recipe(recipe_id)  # Получаем рецепт из базы по ID

    if not recipe:
        await query.edit_message_text('❌ Рецепт не найден.')
        return

    # Отправляем подробности о рецепте
    await query.edit_message_text(
        f'🍽 **Название рецепта**: {recipe.title}\n\n'
        f'📝 **Рецепт**:\n{recipe.description}\n\n'
        f'🥦 **Ингредиенты**:\n{", ".join([ingredient.name for ingredient in recipe.ingredients])}'
    )


# Регистрация хандлеров
def setup_handlers(app):
    # Обработчик для команды /start
    app.add_handler(CommandHandler('start', start))

    # Обработчик для ссылок на видео
    app.add_handler(MessageHandler(
        filters.Regex(video_link_pattern) & filters.TEXT, handle_video_link
    ))

    # Обработчик для кнопок 'Рецепты', 'Случайное блюдо' и 'Загрузить'
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(
            '^(Рецепты|Загрузить|Случайное блюдо)$'
        ),
        handle_button_click
    ))

    # Обработчик для кнопок выбора категории и случайных блюд
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(
            '^(Завтрак|Основное блюдо|Салат|Случайный завтрак|Случайное горячее|Случайный салат)$'
        ),
        handle_button_click_recipe
    ))

    # Обработчик для подтверждения изменений
    app.add_handler(CallbackQueryHandler(
        handle_confirm_changes,
        pattern='^(save_recipe|discard_recipe)$'
    ))

    # Обработчик для подтверждения изменений
    app.add_handler(CallbackQueryHandler(
        handle_category_choice,
        pattern='^(breakfast|main_course|salad)$'
    ))

    # Обработчик для предложений рецептов
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, send_recipe_suggestions
    ))

    # Обработчик для выбора рецепта
    app.add_handler(CallbackQueryHandler(
        handle_recipe_choice, pattern='^recipe_'
    ))

    # Обработчик для предложений рецептов
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, suggest_recipe
    ))

    # Обработчик для выбранного рецепта
    app.add_handler(CallbackQueryHandler(
        handle_suggested_recipe, pattern='^suggest_'
    ))

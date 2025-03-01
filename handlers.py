import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, CallbackQueryHandler, MessageHandler, filters

# Храним данные о рецептах для каждого пользователя в словаре
user_data = {}

# Настроим логирование
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot_logs.log")  # Логирование в файл
    ]
)

async def send_recipe_confirmation(update: Update, title: str, recipe: str, ingredients: str):
    """
    Функция отправляет пользователю сообщение с рецептом и кнопками для подтверждения или редактирования.
    """
    logging.info(f"Отправка сообщения с рецептом пользователю {update.message.from_user.id}")
    
    # Кнопки для подтверждения или редактирования
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm")],
        [InlineKeyboardButton("✏️ Редактировать", callback_data="edit")]
    ]
    
    # Разметка для кнопок
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправка сообщения
    await update.message.reply_text(
        f"🍽 **Название рецепта**: {title}\n\n"
        f"📝 **Рецепт**:\n{recipe}\n\n"
        f"🥦 **Ингредиенты**:\n{ingredients}",
        reply_markup=reply_markup
    )
    logging.info("Сообщение отправлено с кнопками")


# Хандлер редактирования данных
async def handle_edit(update: Update, context: CallbackContext):
    query = update.callback_query
    logging.info(f"Нажата кнопка: {query.data} от пользователя {query.from_user.id}")
    await query.answer()

    user_id = query.from_user.id
    
    # Извлекаем текущие данные для пользователя
    user_info = user_data.get(user_id, {})
    title = user_info.get("title", "Не указано")
    recipe = user_info.get("recipe", "Не указан")
    ingredients = user_info.get("ingredients", "Не указаны")

    logging.info(f"Обработка редактирования данных для пользователя {user_id}, текущие данные: {title}, {recipe}, {ingredients}")

    if query.data == "edit_name":
        user_data[user_id] = {"edit_stage": "edit_name"}  # Сохраняем стадию редактирования
        await query.edit_message_text(f"Введите новое название рецепта (текущее название: {title}):")
    
    elif query.data == "edit_recipe":
        user_data[user_id] = {"edit_stage": "edit_recipe"}  # Сохраняем стадию редактирования
        await query.edit_message_text(f"Введите новый рецепт (текущий рецепт:\n{recipe}):")
    
    elif query.data == "edit_ingredients":
        user_data[user_id] = {"edit_stage": "edit_ingredients"}  # Сохраняем стадию редактирования
        await query.edit_message_text(f"Введите новые ингредиенты (текущие ингредиенты:\n{ingredients}):")

    logging.info(f"Стадия редактирования установлена для пользователя {user_id}: {user_data[user_id]['edit_stage']}")


# Хандлер для сохранения изменений и отправки кнопки "Подтвердить"
async def handle_edit_input(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_info = user_data.get(user_id, {})

    if "edit_stage" not in user_info:
        return  # Если пользователь не в процессе редактирования, ничего не делаем

    stage = user_info["edit_stage"]
    logging.info(f"Получены данные для редактирования от пользователя {user_id}: {stage}")

    if stage == "edit_name":
        new_title = update.message.text
        if user_id not in user_data:
            user_data[user_id] = {}  # Инициализируем пользователя, если его еще нет
        user_data[user_id]["title"] = new_title  # Сохраняем новое название рецепта
        await update.message.reply_text(f"Название рецепта изменено на: {new_title}")
        logging.info(f"Название рецепта обновлено для пользователя {user_id}: {new_title}")
    
    elif stage == "edit_recipe":
        new_recipe = update.message.text
        if user_id not in user_data:
            user_data[user_id] = {}  # Инициализируем пользователя, если его еще нет
        user_data[user_id]["recipe"] = new_recipe  # Сохраняем новый рецепт
        await update.message.reply_text(f"Рецепт изменен на:\n{new_recipe}")
        logging.info(f"Рецепт обновлен для пользователя {user_id}: {new_recipe}")
    
    elif stage == "edit_ingredients":
        new_ingredients = update.message.text
        if user_id not in user_data:
            user_data[user_id] = {}  # Инициализируем пользователя, если его еще нет
        user_data[user_id]["ingredients"] = new_ingredients  # Сохраняем новые ингредиенты
        await update.message.reply_text(f"Ингредиенты изменены на:\n{new_ingredients}")
        logging.info(f"Ингредиенты обновлены для пользователя {user_id}: {new_ingredients}")

    # Завершаем процесс редактирования
    del user_data[user_id]["edit_stage"]  # Удаляем стадию редактирования, чтобы завершить процесс
    logging.info(f"Завершен процесс редактирования для пользователя {user_id}")

    # Добавляем кнопку "Подтвердить"
    confirm_button = InlineKeyboardButton("Подтвердить", callback_data="confirm_changes")
    keyboard = InlineKeyboardMarkup([[confirm_button]])

    await update.message.reply_text("Подтвердите изменения:", reply_markup=keyboard)


# Хандлер для подтверждения изменений
async def handle_confirm_changes(update: Update, context: CallbackContext):
    query = update.callback_query
    logging.info(f"Нажата кнопка: Подтвердить")
    await query.answer()

    user_id = query.from_user.id
    user_info = user_data.get(user_id, {})

    title = user_info.get("title", "Не указано")
    recipe = user_info.get("recipe", "Не указан")
    ingredients = user_info.get("ingredients", "Не указаны")

    logging.info(f"Подтверждение изменений для пользователя {user_id}, данные: {title}, {recipe}, {ingredients}")

    # Проверяем, если данные присутствуют
    if title and recipe and ingredients:
        await query.edit_message_text(
            f"✅ Ваш рецепт успешно обновлен!\n\n"
            f"🍽 **Название рецепта**: {title}\n\n"
            f"📝 **Рецепт**:\n{recipe}\n\n"
            f"🥦 **Ингредиенты**:\n{ingredients}"
        )
        logging.info(f"Изменения подтверждены для пользователя {user_id}")
    else:
        await query.edit_message_text("❌ Ошибка: данные не были заполнены корректно. Пожалуйста, попробуйте снова.")
        logging.error(f"Ошибка при подтверждении изменений для пользователя {user_id}: неполные данные")


# Регистрация хандлеров
def setup_handlers(app):
    logging.info("Регистрация хандлеров...")
    app.add_handler(CallbackQueryHandler(handle_edit, pattern="^edit_.*$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_input))
    app.add_handler(CallbackQueryHandler(handle_confirm_changes, pattern="^confirm_changes$"))
    logging.info("Хандлеры успешно зарегистрированы.")

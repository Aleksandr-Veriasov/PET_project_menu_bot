from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

# Словарь для хранения рецептов
user_data = {}

async def send_recipe_confirmation(update, title, recipe, ingredients):
    """
    Функция отправляет пользователю сообщение с рецептом и кнопками для подтверждения или редактирования.
    """
    keyboard = [
        [InlineKeyboardButton("✅ Сохранить рецепт", callback_data="save_recipe")],
        [InlineKeyboardButton("❌ Не сохранять рецепт", callback_data="discard_recipe")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🍽 **Название рецепта**: {title}\n\n"
        f"📝 **Рецепт**:\n{recipe}\n\n"
        f"🥦 **Ингредиенты**:\n{ingredients}",
        reply_markup=reply_markup
    )


async def handle_confirm_changes(update, context):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user_info = user_data.get(user_id, {})

    if query.data == "save_recipe":
        # Сохраняем рецепт в словаре
        title = user_info.get("title", "Не указано")
        recipe = user_info.get("recipe", "Не указан")
        ingredients = user_info.get("ingredients", "Не указаны")

        user_data[user_id] = {
            "title": title,
            "recipe": recipe,
            "ingredients": ingredients
        }

        await query.edit_message_text(
            f"✅ Ваш рецепт успешно сохранен!\n\n"
            f"🍽 **Название рецепта**: {title}\n\n"
            f"📝 **Рецепт**:\n{recipe}\n\n"
            f"🥦 **Ингредиенты**:\n{ingredients}"
        )
    elif query.data == "discard_recipe":
        # Завершаем процесс без сохранения
        await query.edit_message_text("❌ Рецепт не был сохранен. Завершение работы.")

# Регистрация хандлеров
def setup_handlers(app):
    app.add_handler(CallbackQueryHandler(handle_confirm_changes, pattern="^(save_recipe|discard_recipe)$"))

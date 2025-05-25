import logging

from telegram import KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import CallbackContext, ContextTypes

from app.utils.helpers import get_safe_message_from_update

logger = logging.getLogger(__name__)

START_TEXT = (
    'Привет! 👋 Я — бот, который помогает вам удобно сохранять '
    '<b>рецепты</b>, которые вам понравились в <b>ТикТоке</b> или '
    '<b>Инстаграме</b>. Вот что я могу сделать для вас:\n\n'
    '✨ <b>Сохранить рецепты</b> и ингредиенты из видео\n'
    '🔍 <b>Искать рецепты</b> по категориям\n'
    '🎲 <b>Предложить случайное блюдо</b> из ваших сохранёнок\n'
    '📩 <b>Чтобы загрузить рецепт</b> — просто пришлите мне ссылку '
    'на Reels или TikTok.\n\n'
    '<b>Выберите действие</b> 👇'
)

HELP_TEXT = (
    '🤖 <b>SmartMenuBot</b> — ваш помощник для сохранения рецептов из '
    'TikTok и Reels!\n\n'
    '<b>📌 Что я умею:</b>\n'
    '• Сохранять рецепты и ингредиенты из видео\n'
    '• Сортировать рецепты по категориям (завтрак, обед и салат)\n'
    '• Предлагать случайный рецепт из сохранённых\n'
    '• Позволять редактировать название и удалять рецепты\n\n'
    '<b>🛠 Как пользоваться:</b>\n'
    '1️⃣ Отправьте ссылку на видео из TikTok или Instagram Reels\n'
    '   — я обработаю его, распознаю речь и сохраню рецепт\n'
    '2️⃣ Нажмите на одну из кнопок категорий:\n'
    '   • Завтрак\n'
    '   • Основное блюдо\n'
    '   • Салат\n'
    '3️⃣ Вы можете:\n'
    '   • 📂 Просмотреть рецепты по категориям\n'
    '   • ✏️ Редактировать название рецептов\n'
    '   • ❌ Удалить рецепт\n'
    '   • 🎲 Получить случайный рецепт\n\n'
    '<b>💬 Команды:</b>\n'
    '/start — Перезапустить бота\n'
    '/help — Показать это сообщение\n\n'
    '<i>Приятного приготовления! 🍽</i>'
)


async def start(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [KeyboardButton('Рецепты'), KeyboardButton('Случайное блюдо')],
        [KeyboardButton('Загрузить'), KeyboardButton('Редактировать рецепты')]
    ]
    reply_markup = ReplyKeyboardMarkup(
        keyboard, one_time_keyboard=True, resize_keyboard=True
    )

    if update.message:
        await update.message.reply_text(
            START_TEXT,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    else:
        logger.error('update.message отсутствует в функции start')


async def handle_help(
        update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    message = get_safe_message_from_update(update)
    await message.reply_text(
        HELP_TEXT,
        parse_mode='HTML',
        disable_web_page_preview=True
    )

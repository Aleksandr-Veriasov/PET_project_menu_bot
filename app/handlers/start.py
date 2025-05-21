import logging

from telegram import KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)


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
            'Привет! 👋 Я — бот, который помогает вам удобно сохранять '
            '<b>рецепты</b>, которые вам понравились в <b>ТикТоке</b> или '
            '<b>Инстаграме</b>. Вот что я могу сделать для вас:\n\n'
            '✨ <b>Сохранить рецепты</b> и ингредиенты из видео\n'
            '🔍 <b>Искать рецепты</b> по категориям\n'
            '🎲 <b>Предложить случайное блюдо</b> из Ваших сохраненок\n\n'
            '<b>Выберите действие</b> 👇',
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    else:
        logger.error('update.message отсутствует в функции start')

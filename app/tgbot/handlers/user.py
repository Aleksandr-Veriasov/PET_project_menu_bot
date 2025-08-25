from __future__ import annotations

import asyncio
import logging
from typing import Tuple

from telegram import Update

from app.db.models import User
from app.db.repository import RecipeRepository, UserRepository
from app.db.schemas import UserCreate
from app.tgbot.context_helpers import get_db
from app.tgbot.keyboards.inlines import help_keyboard, start_keyboard
from app.types import PTBContext

logger = logging.getLogger(__name__)


START_TEXT_NEW_USER = (
    'Привет {user.first_name}! 👋 Я — бот, который помогает вам удобно '
    'сохранять '
    '<b>рецепты</b>, которые вам понравились в <b>ТикТоке</b> или '
    '<b>Инстаграме</b>. Вот что я могу сделать для вас:\n\n'
    '✨ <b>Сохранить рецепты</b> и ингредиенты из видео\n'
    '🔍 <b>Искать рецепты</b> по категориям\n'
    '🎲 <b>Предложить случайное блюдо</b> из ваших сохранёнок\n'
    '📩 <b>Чтобы загрузить рецепт</b> — просто пришлите мне ссылку '
    'на Reels или TikTok.\n\n'
    '<b>Выберите действие</b> 👇'
)

START_TEXT_USER = (
    'Выберете то, что хотите сделать:\n\n'
    '• <b>Рецепты</b> — просмотреть сохранённые рецепты\n'
    '• <b>Случайное блюдо</b> — получить случайный рецепт\n'
    '• <b>Редактировать рецепты</b> — изменить название или удалить рецепт\n'
    '• <b>Загрузить рецепт</b> — отправить ссылку на видео с рецептом\n'
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


async def user_start(update: Update, context: PTBContext) -> None:
    """Обработчик команды /start для новых пользователей."""
    tg_user = update.effective_user
    if not tg_user:
        logger.error('update.effective_user отсутствует в функции start')
        return

    db = get_db(context)

    def _ensure_user_and_count() -> Tuple[User, int]:
        """Проверка пользователя в БД и получение количества рецептов."""
        with db.session() as session:
            # Проверяем, существует ли пользователь в БД
            user = session.get(User, tg_user.id)
            if user is None:
                # Если нет, создаём нового пользователя
                payload = UserCreate(
                    id=tg_user.id,
                    username=tg_user.username,
                    first_name=tg_user.first_name,
                    last_name=tg_user.last_name,
                )
                user = UserRepository.create(session, payload)
            recipe_count = RecipeRepository.get_count_by_user(session, user.id)
            return user, recipe_count

    user, count = await asyncio.to_thread(_ensure_user_and_count)

    new_user = True if count == 0 else False
    text_new_user = START_TEXT_NEW_USER.format(user=user)
    text = text_new_user if new_user else START_TEXT_USER
    keyboard = start_keyboard(new_user)

    cq = update.callback_query
    if cq:
        await cq.answer()  # убираем «часики»
        # если есть исходное сообщение — отвечаем рядом
        if cq.message:
            await cq.message.edit_text(
                text, reply_markup=keyboard, parse_mode='HTML',
            )
        return
    # Если это не callback_query, то обычное сообщение
    msg = update.effective_message
    if msg:
        await msg.reply_text(
            text, reply_markup=keyboard, parse_mode='HTML',
        )


async def user_help(update: Update, context: PTBContext) -> None:
    """Обработчик команды /help и нажатия инлайн-кнопки «Помощь»."""
    # 1) Нажатие инлайн-кнопки «Помощь»
    if update.callback_query:
        cq = update.callback_query
        await cq.answer()  # убираем «часики»
        # если есть исходное сообщение — отвечаем рядом
        if cq.message:
            await cq.message.edit_text(
                HELP_TEXT, parse_mode='HTML', disable_web_page_preview=True,
                reply_markup=help_keyboard()
            )
        return

    # 2) Обычная команда /help как сообщение
    msg = update.effective_message
    if msg:
        await msg.reply_text(
            HELP_TEXT, parse_mode='HTML', disable_web_page_preview=True,
            reply_markup=help_keyboard()
        )

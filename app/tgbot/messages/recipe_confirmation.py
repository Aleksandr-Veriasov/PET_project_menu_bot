import logging
from html import escape
from typing import Iterable

from telegram import Message
from telegram.constants import ParseMode

from app.tgbot.keyboards.inlines import keyboard_save_recipe
from app.types import PTBContext

# Включаем логирование
logger = logging.getLogger(__name__)


def _fmt_ingredients(ingredients: str | Iterable[str]) -> str:
    if isinstance(ingredients, str):
        return ingredients.strip()
    return '\n'.join(f'• {escape(str(x))}' for x in ingredients)


async def send_recipe_confirmation(
    message: Message,
    context: PTBContext,
    title: str,
    recipe: str,
    ingredients: str | Iterable[str],
    video_file_id: str,
) -> None:
    """
    Отправляет пользователю видео (по file_id) и сообщение с рецептом
    + инлайн-кнопки подтверждения/отмены. Данные для последующего сохранения
    кладём в context.user_data.
    """
    if message.from_user is None:
        logger.warning('Пользователь не найден (from_user is None)')
        return

    context.user_data["recipe_draft"] = {
        'title': title,
        'recipe': recipe,
        'video_file_id': video_file_id,
        'ingredients': list(ingredients) if not isinstance(
            ingredients, str
        ) else ingredients,
    }

    # 1) Видео (если есть file_id)
    if video_file_id:
        try:
            logger.info('Отправляем видео с file_id: %s', video_file_id)
            await message.reply_video(
                video_file_id, allow_sending_without_reply=True
            )
            logger.info('Видео успешно отправлено')
        except Exception as e:
            logger.error('Ошибка при отправке видео: %s', e, exc_info=True)
            # не прерываемся — всё равно отправим текст

    # 2) Текст (экранируем только пользовательские поля)
    title_html = escape(title).strip() or 'Без названия'
    recipe_html = escape(recipe).strip() or '—'
    ingr_html = _fmt_ingredients(ingredients)

    text = (
        f'🍽 <b>Название рецепта:</b>\n{title_html}\n\n'
        f'📝 <b>Рецепт:</b>\n{recipe_html}\n\n'
        f'🥦 <b>Ингредиенты:</b>\n{ingr_html}\n\n'
    )

    try:
        # Первый кусок — с кнопками
        await message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard_save_recipe(),
            disable_web_page_preview=True,
        )
        logger.info('Сообщение с рецептом успешно отправлено.')
    except Exception as e:
        logger.error(
            'Ошибка при отправке текста рецепта: %s', e, exc_info=True
        )

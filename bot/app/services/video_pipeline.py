import logging
import asyncio
from typing import Optional

from telegram import Message

from bot.app.utils.deepseek_answers import extract_recipes
from bot.app.messages.telegram_media import send_video_to_channel
from packages.media.audio_extractor import extract_audio
from packages.media.speech_recognition import async_transcribe_audio
from packages.media.video_converter import async_convert_to_mp4
from packages.media.video_downloader import (
    async_download_video_and_description
)
from bot.app.notifications.telegram_notifier import TelegramNotifier
from bot.app.messages.recipe_confirmation import send_recipe_confirmation
from bot.app.core.types import PTBContext
from packages.media.safe_remove import safe_remove

AUDIO_FOLDER = 'audio/'

logger = logging.getLogger(__name__)


async def process_video_pipeline(
        url: str, message: Message, context: PTBContext
) -> None:
    chat_id = message.chat_id if hasattr(
        message, 'chat_id'
    ) else message.chat.id

    notifier = TelegramNotifier(context.bot, chat_id, context=context)

    # стартовое сообщение (создастся и запомнится message_id)
    await notifier.info(
        '🔄 Скачиваю видео и описание... Пожалуйста, подождите.'
    )

    # дальше обычный ход
    video_path, description = await async_download_video_and_description(url)
    await notifier.progress(20, '📼 Видео скачано')
    if not video_path:
        await notifier.error(
            'Не удалось скачать видео. Отправьте ссылку ещё раз.'
        )
        return

    convert_task = asyncio.create_task(async_convert_to_mp4(video_path))
    await notifier.progress(40, 'Видео конвертировано')

    def _cleanup_src_video_after_convert(t: asyncio.Task) -> None:
        safe_remove(video_path)

    convert_task.add_done_callback(_cleanup_src_video_after_convert)
    converted_path = await convert_task

    upload_task: asyncio.Task[Optional[str]] = asyncio.create_task(
        send_video_to_channel(context, converted_path)
    )

    if context.user_data is not None:
        context.user_data['video_path'] = converted_path
        context.user_data['video_upload_task'] = upload_task
    await notifier.progress(60, '✅ Видео загружено. Распознаём текст...')

    audio_path = extract_audio(converted_path, AUDIO_FOLDER)
    transcribe_task = asyncio.create_task(async_transcribe_audio(audio_path))

    def _cleanup_audio_after_done(_task: asyncio.Task) -> None:
        safe_remove(audio_path)

    transcribe_task.add_done_callback(_cleanup_audio_after_done)
    transcript = await transcribe_task

    await notifier.progress(
        80, '🧠 Подготавливаем рецепт через AI... '
        'Рецепт практически готов!'
    )

    title, recipe, ingredients = await extract_recipes(
        description, transcript
    )

    video_file_id: Optional[str] = None
    try:
        # если аплоад уже успел — получим результат мгновенно
        # таймаут можно убрать, если не нужен контроль зависания
        video_file_id = await upload_task
    except Exception:
        # не валим весь процесс: просто не будет превью из канала
        # (при желании можно notifier.info(...) или notifier.error(...))
        video_file_id = None

    if context.user_data is not None and video_file_id:
        context.user_data['video_file_id'] = video_file_id
        safe_remove(converted_path)

    if title and recipe:
        await notifier.progress(100, 'Готово ✅')
        await send_recipe_confirmation(
            message, context, title, recipe, ingredients, video_file_id
        )
    else:
        await notifier.error('Не удалось извлечь данные из видео.')

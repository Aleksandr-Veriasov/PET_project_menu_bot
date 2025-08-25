import logging
import asyncio

from telegram import Message

from app.integrations.deepseek_api import extract_recipe_data_async
from app.integrations.telegram_media import send_video_to_channel
from app.media.audio_extractor import extract_audio
from app.media.speech_recognition import async_transcribe_audio
from app.media.video_converter import async_convert_to_mp4
from app.media.video_downloader import async_download_video_and_description
from app.notifications.telegram_notifier import TelegramNotifier
from app.tgbot.messages.recipe_confirmation import send_recipe_confirmation
from app.types import PTBContext
from app.media.safe_remove import safe_remove

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

    video_file_id = await send_video_to_channel(context, converted_path)

    if context.user_data is not None:
        context.user_data['video_file_id'] = video_file_id
        context.user_data['video_path'] = converted_path
    await notifier.progress(60, '✅ Видео загружено. Распознаём текст...')

    audio_path = extract_audio(converted_path, AUDIO_FOLDER)
    transcribe_task = asyncio.create_task(async_transcribe_audio(audio_path))
    await notifier.progress(
        80, '🧠 Подготавливаем рецепт через AI... '
        'Рецепт практически готов!'
    )

    def _cleanup_audio_after_done(_task: asyncio.Task) -> None:
        safe_remove(audio_path)

    transcribe_task.add_done_callback(_cleanup_audio_after_done)
    transcript = await transcribe_task

    title, recipe, ingredients = await extract_recipe_data_async(
        description, transcript
    )

    if title and recipe:
        await notifier.progress(100, 'Готово ✅')
        await send_recipe_confirmation(
            message, context, title, recipe, ingredients, video_file_id
        )
    else:
        await notifier.error('Не удалось извлечь данные из видео.')

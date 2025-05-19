import asyncio
import logging
import os

from telegram import Message, Update
from telegram.ext import CallbackContext

from app.api.deepseek_api import extract_recipe_data_async
from app.media.audio_extractor import extract_audio
from app.media.speech_recognition import async_transcribe_audio
from app.media.video_downloader import (
    async_convert_to_mp4,
    async_download_video_and_description,
    send_video_to_channel,
)
from app.utils.helpers import (
    get_safe_message_from_update,
    get_safe_text_from_update,
    get_safe_user_data,
)
from app.utils.message_utils import send_recipe_confirmation

AUDIO_FOLDER = 'audio/'
logger = logging.getLogger(__name__)


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
    await message.reply_text('✅ Ссылка получена. Обработка запущена...')
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
        video_file_id = await send_video_to_channel(context, converted_path)

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

    except Exception as e:
        logger.exception(f'Ошибка при обработке видео: {e}')
        await message.reply_text(
            '❌ Произошла ошибка при обработке видео.\n'
            'Пожалуйста, попробуйте ещё раз.'
        )

    finally:
        for path in [video_path, converted_path, audio_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as e:
                    logger.warning(f'Не удалось удалить {path}: {e}')

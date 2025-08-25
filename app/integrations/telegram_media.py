from __future__ import annotations

import logging
from pathlib import Path

from telegram import InputFile

from app.core.settings import settings
from app.types import PTBContext

logger = logging.getLogger(__name__)


async def send_video_to_channel(
    context: PTBContext,
    converted_video_path: str
) -> str:
    """
    Функция отправляет видео в канал и возвращает ссылку на видео.
    """
    p = Path(converted_video_path)
    if not p.is_file():
        logger.error('Видео не найдено: %s', p)
        return ''

    try:
        with p.open('rb') as f:
            message = await context.bot.send_video(
                chat_id=settings.telegram.chat_id,
                video=InputFile(f, filename=p.name),
                caption='📹 Новое видео!',
                supports_streaming=True,
                allow_sending_without_reply=True,
            )
        file_id = message.video.file_id if message.video else ''
        logger.info(
            'Видео отправлено: file_id=%s, message_id=%s',
            file_id, message.message_id
        )
        return file_id
    except Exception as e:
        logger.error('Ошибка при отправке видео: %s', e, exc_info=True)
        return ''

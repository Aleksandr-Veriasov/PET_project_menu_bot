from __future__ import annotations

import asyncio
import logging
import re
from typing import Optional

from telegram import Message, MessageEntity, Update

from app.services.video_pipeline import process_video_pipeline
from app.types import PTBContext

logger = logging.getLogger(__name__)

_URL_RE = re.compile(
    r'(?P<url>https?://(?:www\.)?[^\s<>()\[\]]+)', re.IGNORECASE
)


def extract_first_url(msg: Message) -> Optional[str]:
    """Вернёт первую ссылку из текста/подписи сообщения, если она есть."""
    # 1) Сначала — entities (Telegram сам корректно выделяет URL и TEXT_LINK)
    ent_map = msg.parse_entities(
        [MessageEntity.URL, MessageEntity.TEXT_LINK]
    ) or {}
    for ent, value in ent_map.items():
        if ent.type == MessageEntity.TEXT_LINK and ent.url:
            return ent.url
        if ent.type == MessageEntity.URL:
            return value

    # 2) Затем — caption_entities (если ссылка в подписи к медиа)
    cap_map = msg.parse_caption_entities(
        [MessageEntity.URL, MessageEntity.TEXT_LINK]
    ) or {}
    for ent, value in cap_map.items():
        if ent.type == MessageEntity.TEXT_LINK and ent.url:
            return ent.url
        if ent.type == MessageEntity.URL:
            return value

    # 3) Fallback — простая регулярка по тексту/подписи
    s = (msg.text or msg.caption or '')
    m = _URL_RE.search(s)
    return m.group('url').rstrip('.,);:!?]»”') if m else None


async def video_link(update: Update, context: PTBContext) -> None:
    """
    Принимает сообщение с ссылкой и запускает обработку.
    Entry-point: /video_link
    """
    message = update.effective_message
    if not message:
        return
    url = extract_first_url(message)
    if not url:
        await message.reply_text(
            '❌ Не нашёл ссылку в сообщении. Пришлите корректный URL.'
        )
        return
    logger.info(f'Пользователь отправил ссылку: {url}')
    msg = await message.reply_text('✅ Ссылка получена. Обработка запущена...')
    if context.user_data:
        context.user_data["progress_msg_id"] = msg.message_id
    asyncio.create_task(process_video_pipeline(url, message, context))

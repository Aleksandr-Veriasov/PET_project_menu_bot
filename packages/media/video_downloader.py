import asyncio
import logging
import os
import time

import yt_dlp

VIDEO_FOLDER = 'videos/'
if os.path.exists('/data'):
    COOKIE_PATH = '/data/cookies/instagram_cookies.txt'  # сервер
else:
    COOKIE_PATH = 'data/cookies/instagram_cookies.txt'   # локально

WIDTH_VIDEO = 720  # Примерный размер, можно изменить
HEIGHT_VIDEO = 1280  # Примерный размер, можно изменить
INACTIVITY_LIMIT_SECONDS = 15 * 60  # 15 минут

logger = logging.getLogger(__name__)


def _ensure_dir(path: str) -> None:
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
        logger.info(f'📁 Папка для видео создана: {path}')


def _finalize_path(raw_path: str, prefer_ext: str | None = 'mp4') -> str:
    """yt_dlp.prepare_filename(info) даёт путь до постобработки.
    Если мы мерджим в mp4, удобнее вернуть финальный путь .mp4.
    """
    if not prefer_ext:
        return raw_path
    base, _ = os.path.splitext(raw_path)
    return f'{base}.{prefer_ext}'


def _ydl_opts(output_path: str, *, use_cookie: bool = False) -> dict:
    opts = {
        'outtmpl': output_path,
        'format': 'bv+ba/best',
        'merge_output_format': 'mp4',
        'postprocessors': [
            {'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'}
        ],
        'noprogress': True,
        'nocheckcertificate': True,
        # 'quiet': True,  # если нужно тише в stdout
    }
    if use_cookie:
        opts['cookiefile'] = COOKIE_PATH
    return opts


def _try_download(url: str, *, use_cookie: bool) -> tuple[str, str]:
    """Один заход на скачивание. Бросает исключение наверх при ошибке."""
    output_path = os.path.join(VIDEO_FOLDER, '%(id)s.%(ext)s')
    ydl_opts = _ydl_opts(output_path, use_cookie=use_cookie)

    if use_cookie:
        if not os.path.isfile(COOKIE_PATH):
            raise FileNotFoundError(f'Cookie-файл не найден: {COOKIE_PATH}')
        logger.info('🍪 Скачиваем с cookie-файлом')

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)  # может бросить
        raw_path = ydl.prepare_filename(info)
        file_path = _finalize_path(raw_path, prefer_ext='mp4')
        description = info.get('description', '') or ''
        logger.info(f'✅ Скачивание завершено: {file_path}')
        return file_path, description


def download_video_and_description(url: str) -> tuple[str, str]:
    """
    Скачивает видео: сперва без cookie, при неудаче — с cookie через 2 сек.
    """
    _ensure_dir(VIDEO_FOLDER)

    logger.info(f'🔍 Пытаемся скачать без cookie: {url}')
    try:
        return _try_download(url, use_cookie=False)
    except Exception as e1:
        logger.warning(f'Первый заход без cookie не удался: {e1}')

    # Повтор через 2 секунды с cookie (если файл есть)
    if os.path.isfile(COOKIE_PATH):
        logger.info('⏳ Ждём 2 сек и пробуем со сookie…')
        time.sleep(2)
        try:
            return _try_download(url, use_cookie=True)
        except Exception as e2:
            logger.error(f'Повтор с cookie не удался: {e2}', exc_info=True)
            return '', ''
    else:
        logger.error(
            f'❌ Cookie-файл отсутствует: {COOKIE_PATH}. Повтор не выполняем.'
        )
        return '', ''


async def async_download_video_and_description(url: str) -> tuple[str, str]:
    """Асинхронная обёртка поверх блокирующей загрузки."""
    return await asyncio.to_thread(download_video_and_description, url)


async def cleanup_old_videos() -> None:
    """Фоновая задача, удаляющая старые видеофайлы без активности."""
    while True:
        logger.info('Фоновая задача начала работать')
        now = time.time()
        if os.path.exists(VIDEO_FOLDER):
            for filename in os.listdir(VIDEO_FOLDER):
                file_path = os.path.join(VIDEO_FOLDER, filename)
                try:
                    if os.path.isfile(file_path):
                        last_access = os.path.getatime(file_path)
                        if now - last_access > INACTIVITY_LIMIT_SECONDS:
                            os.remove(file_path)
                            logger.info(
                                f'Удалён неиспользуемый файл: {file_path}'
                            )
                except Exception as e:
                    logger.error(
                        f'Ошибка при удалении файла: {file_path} — {e}'
                    )
        await asyncio.sleep(INACTIVITY_LIMIT_SECONDS)

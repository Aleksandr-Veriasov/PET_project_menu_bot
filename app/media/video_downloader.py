import asyncio
import logging
import os
import time

import ffmpeg  # type: ignore
import yt_dlp  # type: ignore
from dotenv import load_dotenv
from telegram.ext import CallbackContext

VIDEO_FOLDER = 'videos/'
COOKIE_PATH = "/app/instagram_cookies.txt"

WIDTH_VIDEO = 720  # Примерный размер, можно изменить
HEIGHT_VIDEO = 1280  # Примерный размер, можно изменить
CORRECTION_FACTOR = 0.6  # Уменьшение разрешения на 40%
INACTIVITY_LIMIT_SECONDS = 15 * 60  # 15 минут

logger = logging.getLogger(__name__)

load_dotenv()


def download_video_and_description(url: str) -> tuple[str, str]:
    '''Скачивает видео по ссылке и возвращает путь к файлу.'''
    if not os.path.exists(VIDEO_FOLDER):
        os.makedirs(VIDEO_FOLDER)
        logger.info(f'Папка для видео создана: {VIDEO_FOLDER}')

    # Загружаем куки из переменных окружения
    sessionid = os.getenv("INSTAGRAM_SESSIONID")
    user_id = os.getenv("INSTAGRAM_USERID")
    csrftoken = os.getenv("INSTAGRAM_CSRFTOKEN")
    rur = os.getenv("INSTAGRAM_RUR")

    # Проверка наличия переменных
    if not all([sessionid, user_id, csrftoken, rur]):
        logger.error("❌ Отсутствуют переменные окружения с cookie-данными")
        return '', ''

    # Формируем заголовок
    cookie_header = {
        'Cookie': (
            f'sessionid={sessionid}; '
            f'ds_user_id={user_id}; '
            f'csrftoken={csrftoken}; '
            f'rur={rur}'
        )
    }
    logger.info('✅ Используем Cookie-заголовок из переменных окружения')

    output_path = os.path.join(VIDEO_FOLDER, '%(title)s.%(ext)s')

    ydl_opts = {
        'outtmpl': output_path,
        'format': 'bv+ba/best',  # Скачиваем видео + аудио вместе
        'merge_output_format': 'mp4',  # Telegram требует MP4
        'postprocessors': [
            {
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4'
            }
        ],
        'noprogress': True,
        'nocheckcertificate': True,
        'http_headers': cookie_header,
        'verbose': True
    }
    logger.info("🔍 Начинаем чтение cookie-файла для проверки формата")
    with open(COOKIE_PATH, "rb") as f:
        raw = f.read()
        logger.info(f"📦 Размер файла: {len(raw)} байт")
        logger.info(f"🔍 Первые байты: {raw[:60]!r}")

        # Проверка строково
        f.seek(0)
        for i, line in enumerate(f):
            logger.info(f"🔍 Строка {i+1}: {line!r}")
    logger.info(f'Начинаем скачивание видео по ссылке: {url}')
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            description = info.get('description', '')
            logger.info(f'Скачивание завершено: {file_path}')
            return file_path, description
    except Exception as e:
        logger.error(f'Ошибка при скачивании видео: {e}', exc_info=True)
        return '', ''


async def async_download_video_and_description(url: str) -> tuple[str, str]:
    '''Асинхронная версия функции скачивания видео.'''
    return await asyncio.to_thread(download_video_and_description, url)


def get_video_resolution(video_path: str) -> tuple[int, int]:
    '''Получаем разрешение видео'''
    logger.info(f'Получаем разрешение видео: {video_path}')
    try:
        probe = ffmpeg.probe(
            video_path, v='error',
            select_streams='v:0',
            show_entries='stream=width,height'
        )
        width = probe['streams'][0]['width']
        height = probe['streams'][0]['height']
        logger.info(f'Разрешение видео: {width}x{height}')
        return width, height
    except ffmpeg.Error as e:
        logger.error(f'Ошибка при анализе видео: {e}', exc_info=True)
        return 0, 0


def correct_resolution(width: int, height: int) -> tuple[int, int]:
    '''Корректируем разрешение видео, чтобы оно делилось на 2'''
    if width % 2 != 0:
        width -= 1
    if height % 2 != 0:
        height -= 1
    return width, height


def convert_to_mp4(input_path: str) -> str:
    '''Конвертирует видео в MP4 (H.264) с уменьшением качества на 40%.'''
    output_path = input_path.rsplit('.', 1)[0] + '_converted.mp4'

    # Получаем исходное разрешение видео
    width, height = get_video_resolution(input_path)

    logger.info(f'Начинаем конвертацию видео: {input_path}')
    if width is None or height is None:
        logging.error('Не удалось получить разрешение видео')
        return None

    # Корректируем разрешение, если необходимо
    corrected_width, corrected_height = correct_resolution(width, height)

    # Логирование размеров для проверки
    logger.info(
        f'Исходное разрешение видео: {width}x{height}'
    )
    logger.info(
        f'Исправленное разрешение видео: {corrected_width}x{corrected_height}'
    )

    # Уменьшаем разрешение на 40%
    new_width = int(corrected_width * CORRECTION_FACTOR)
    new_height = int(corrected_height * CORRECTION_FACTOR)

    # Корректируем новый размер на 2 (чтобы избежать ошибок при обработке)
    new_width, new_height = correct_resolution(new_width, new_height)

    logger.info(
        f'Новое разрешение видео после сжатия: {new_width}x{new_height}'
    )

    try:
        # Выполняем конвертацию с исправленным разрешением
        ffmpeg.input(input_path).output(
            output_path,
            vf=f'scale={new_width}:{new_height}',
            vcodec='libx264',
            acodec='aac',
            crf=32
        ).run()
        logger.info(f'Конвертация завершена: {output_path}')
    except ffmpeg.Error as e:
        logger.error(f'Ошибка при конвертации видео: {e}', exc_info=True)
        return ''

    return output_path


async def async_convert_to_mp4(input_path: str) -> str:
    '''Асинхронная версия функции конвертации видео.'''
    return await asyncio.to_thread(convert_to_mp4, input_path)


async def send_video_to_channel(
        context: CallbackContext,
        converted_video_path: str
) -> str:
    '''
    Функция отправляет видео в канал и возвращает ссылку на видео.
    '''
    CHAT_ID = os.getenv('CHAT_ID')
    if not CHAT_ID:
        logger.error('CHAT_ID не найден в .env файле')
        return ''
    logger.info(f'Отправляем видео в канал: {CHAT_ID}')
    logger.info(f'Путь к видео: {converted_video_path}')
    try:
        with open(converted_video_path, 'rb') as video:
            message = await context.bot.send_video(
                chat_id=CHAT_ID,  # Указание канала
                video=video,
                caption='📹 Новое видео!',
                width=WIDTH_VIDEO,  # Примерный размер, можно изменить
                height=HEIGHT_VIDEO  # Примерный размер, можно изменить
            )

        # Получаем ID видео
        video_file_id = message.video.file_id
        logger.info(f'Видео успешно отправлено: {video_file_id}')
        return video_file_id  # Ссылка на видео
    except Exception as e:
        logger.error(f'Ошибка при отправке видео: {e}', exc_info=True)
        return ''


async def cleanup_old_videos():
    '''Фоновая задача, удаляющая старые видеофайлы без активности.'''
    while True:
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

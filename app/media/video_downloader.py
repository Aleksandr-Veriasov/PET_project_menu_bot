import asyncio
import logging
import os

import ffmpeg  # type: ignore
import yt_dlp  # type: ignore
from dotenv import load_dotenv
from telegram.ext import CallbackContext

VIDEO_FOLDER = 'videos/'
WIDTH_VIDEO = 720  # Примерный размер, можно изменить
HEIGHT_VIDEO = 1280  # Примерный размер, можно изменить
CORRECTION_FACTOR = 0.6  # Уменьшение разрешения на 40%

logger = logging.getLogger(__name__)


def download_video_and_description(url: str) -> tuple[str, str]:
    '''Скачивает видео по ссылке и возвращает путь к файлу.'''
    if not os.path.exists(VIDEO_FOLDER):
        os.makedirs(VIDEO_FOLDER)
        logger.info(f'Папка для видео создана: {VIDEO_FOLDER}')

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
        'nocheckcertificate': True
    }
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
    load_dotenv()
    CHAT_ID = os.getenv('CHAT_ID')
    if not CHAT_ID:
        logger.error('CHAT_ID не найден в .env файле')
        return ''
    logger.info(f'Отправляем видео в канал: {CHAT_ID}')
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

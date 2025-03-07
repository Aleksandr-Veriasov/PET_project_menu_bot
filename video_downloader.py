import ffmpeg
import logging
import os

import yt_dlp
from telegram import Update
from telegram.ext import CallbackContext

VIDEO_FOLDER = 'videos/'


def download_video_and_description(url):
    '''Скачивает видео по ссылке и возвращает путь к файлу.'''
    if not os.path.exists(VIDEO_FOLDER):
        os.makedirs(VIDEO_FOLDER)

    output_path = os.path.join(VIDEO_FOLDER, '%(title)s.%(ext)s')

    ydl_opts = {
        'outtmpl': 'videos/%(title)s.%(ext)s',
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

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            description = info.get('description', '')
            return file_path, description
    except Exception as e:
        print(f'Ошибка при скачивании видео: {e}')
        return None


def get_video_resolution(video_path):
    '''Получаем разрешение видео'''
    try:
        probe = ffmpeg.probe(
            video_path, v='error',
            select_streams='v:0',
            show_entries='stream=width,height'
        )
        width = probe['streams'][0]['width']
        height = probe['streams'][0]['height']
        return width, height
    except ffmpeg.Error as e:
        logging.error(f'Ошибка при получении разрешения видео: {e}')
        return None, None


def correct_resolution(width, height):
    '''Корректируем разрешение видео, чтобы оно делилось на 2'''
    if width % 2 != 0:
        width -= 1
    if height % 2 != 0:
        height -= 1
    return width, height


def convert_to_mp4(input_path):
    '''Конвертирует видео в MP4 (H.264) с уменьшением качества на 40%.'''
    output_path = input_path.rsplit('.', 1)[0] + '_converted.mp4'

    # Получаем исходное разрешение видео
    width, height = get_video_resolution(input_path)

    if width is None or height is None:
        logging.error('Не удалось получить разрешение видео')
        return None

    # Корректируем разрешение, если необходимо
    corrected_width, corrected_height = correct_resolution(width, height)

    # Логирование размеров для проверки
    logging.info(f'Исходное разрешение видео: {width}x{height}')
    logging.info(
        f'Исправленное разрешение видео: {corrected_width}x{corrected_height}'
    )

    # Уменьшаем разрешение на 40%
    new_width = int(corrected_width * 0.6)
    new_height = int(corrected_height * 0.6)

    # Корректируем новый размер на 2 (чтобы избежать ошибок при обработке)
    new_width, new_height = correct_resolution(new_width, new_height)

    logging.info(
        f'Новый размер после уменьшения на 40%: {new_width}x{new_height}'
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
        logging.info(f'Конвертация завершена: {output_path}')
    except ffmpeg.Error as e:
        logging.error(f'Ошибка при конвертации видео: {e}')
        return None

    return output_path


async def send_video_to_channel(
        update: Update,
        context: CallbackContext,
        converted_video_path: str
):
    '''
    Функция отправляет видео в канал и возвращает ссылку на видео.
    '''
    try:
        with open(converted_video_path, 'rb') as video:
            message = await context.bot.send_video(
                chat_id='@gmzcvi',  # Указание канала
                video=video,
                caption='📹 Новое видео!',
                width=720,  # Примерный размер, можно изменить
                height=1280  # Примерный размер, можно изменить
            )

        # Получаем ID видео
        video_file_id = message.video.file_id

        return video_file_id  # Ссылка на видео
    except Exception as e:
        logging.error(f'Ошибка при отправке видео в канал: {e}')
        return None

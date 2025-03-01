import yt_dlp
import os
import subprocess
import json
import logging


VIDEO_FOLDER = "videos/"

def download_video_and_description(url):
    """Скачивает видео по ссылке и возвращает путь к файлу."""
    if not os.path.exists(VIDEO_FOLDER):
        os.makedirs(VIDEO_FOLDER)

    output_path = os.path.join(VIDEO_FOLDER, "%(title)s.%(ext)s")

    ydl_opts = {
        "outtmpl": "videos/%(title)s.%(ext)s",
        "format": "bv+ba/best",  # Скачиваем видео + аудио вместе
        "merge_output_format": "mp4",  # Telegram требует MP4
        "postprocessors": [
            {
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4"
            }
        ],
        "noprogress": True,
        "nocheckcertificate": True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            description = info.get("description", "")
            return file_path, description
    except Exception as e:
        print(f"Ошибка при скачивании видео: {e}")
        return None

def get_video_resolution(video_path):
    """Возвращает (width, height) видео, используя ffprobe"""
    try:
        command = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0", "-show_entries", "stream=width,height",
            "-of", "json", video_path
        ]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        metadata = json.loads(result.stdout)
        width = metadata["streams"][0]["width"]
        height = metadata["streams"][0]["height"]
        return width, height
    except Exception as e:
        print(f"Ошибка при получении разрешения видео: {e}")
        return None, None

def convert_to_mp4(input_path):
    """Конвертирует видео в MP4 (H.264) с уменьшением качества на 40%."""
    output_path = input_path.rsplit(".", 1)[0] + "_converted.mp4"

    command = [
        "ffmpeg", "-i", input_path,
        "-vcodec", "libx264", "-preset", "medium",
        "-crf", "32",  # Увеличили CRF (качество хуже, файл меньше)
        "-acodec", "aac", "-b:a", "96k",  # Уменьшаем битрейт аудио
        "-vf", "scale=iw*0.6:ih*0.6",  # Уменьшаем разрешение на 40%
        "-movflags", "+faststart",
        "-max_muxing_queue_size", "1024",
        output_path
    ]

    try:
        # Увеличиваем тайм-аут до 600 секунд (10 минут)
        subprocess.run(command, check=True, timeout=600)  # Тайм-аут 600 секунд
        logging.info(f"Конвертация завершена: {output_path}")
    except subprocess.TimeoutExpired:
        logging.error(f"Конвертация видео превысила время ожидания: {input_path}")
    except Exception as e:
        logging.error(f"Ошибка конвертации видео: {e}")

    return output_path

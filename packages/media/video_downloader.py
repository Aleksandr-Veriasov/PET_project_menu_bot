from __future__ import annotations

import asyncio
import logging
import os
import random
import re
import socket
import time
from pathlib import Path
from typing import Tuple
from urllib.error import HTTPError, URLError

import yt_dlp
from instaloader import Instaloader, Post
from yt_dlp.utils import DownloadError, ExtractorError

VIDEO_FOLDER = 'videos/'
WIDTH_VIDEO = 720  # Примерный размер, можно изменить
HEIGHT_VIDEO = 1280  # Примерный размер, можно изменить
INACTIVITY_LIMIT_SECONDS = 15 * 60  # 15 минут

logger = logging.getLogger(__name__)


def _ensure_dir(path: str) -> None:
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
        logger.debug(f'📁 Папка для видео создана: {path}')


def _finalize_path(raw_path: str, prefer_ext: str | None = 'mp4') -> str:
    """yt_dlp.prepare_filename(info) даёт путь до постобработки.
    Если мы мерджим в mp4, удобнее вернуть финальный путь .mp4.
    """
    if not prefer_ext:
        return raw_path
    base, _ = os.path.splitext(raw_path)
    return f'{base}.{prefer_ext}'


def _platform_from_url(url: str) -> str:
    u = url.lower()
    if "instagram.com" in u:
        return "instagram"
    if "tiktok.com" in u:
        return "tiktok"
    if "youtube.com" in u or "youtu.be" in u:
        return "youtube"
    return "unknown"


def _random_human_sleep(min_s: float, max_s: float) -> None:
    time.sleep(random.uniform(min_s, max_s))


def _yt_dlp_opts(output_path: str) -> dict:
    """
    Настройки с «человечным» поведением:
    - sleep_interval: паузы между запросами/фрагментами
    - retries/fragment_retries: ограниченные ретраи
    - ratelimit: мягкое ограничение скорости (имитируем пользователя)
    - noprogress/quiet: тише в stdout
    """
    return {
        "outtmpl": output_path,
        "format": "bv+ba/best/best",
        "merge_output_format": "mp4",
        "postprocessors": [
            {"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}
        ],
        "noprogress": True,
        "quiet": True,
        "nocheckcertificate": True,
        "retries": 3,
        "fragment_retries": 3,
        "sleep_interval": 1.0,
        "max_sleep_interval": 3.0,
        "ratelimit": 2_000_000,  # ~2 MB/s
        # Ограничиваем параллелизм фрагментов (по умолчанию = 1 в yt-dlp)
        # "concurrent_fragment_downloads": 1,
        # Чуть более «обычный» User-Agent (yt-dlp сам ставит современный UA)
        # "http_headers": {"User-Agent": "..."},
    }


def _is_instagram_login_or_rate_error(err: Exception) -> bool:
    """
    Эвристики: когда у Instagram требуется логин / словили 403/429, либо
    блокируется доступ из-за частоты запросов.
    """
    s = str(err).lower()
    patterns = [
        "http error 403",
        "http error 429",
        "forbidden",
        "too many requests",
        "login required",
        "private video",
        "this video is only available for registered users",
        "please log in",
        "not logged in",
    ]
    return any(p in s for p in patterns)


def _should_retry(err: Exception) -> bool:
    """
    Решаем, стоит ли делать повторную попытку yt-dlp.
    Сетевые/временные ошибки — да. Тяжёлые ошибки (геолокация, удалено) — нет.
    """
    s = str(err).lower()

    # Сетевые/временные
    transient_hints = [
        "timed out",
        "timeout",
        "temporary failure",
        "server error",
        "503 service unavailable",
        "connection reset",
        "network is unreachable",
        "incomplete fragment",
        "http error 5",  # 5xx
    ]
    if any(h in s for h in transient_hints):
        return True

    # OAuth/DRM/гео/удалено — повтор обычно не поможет
    terminal_hints = [
        "copyright",
        "dmca",
        "drm",
        "geo restricted",
        "geo-restricted",
        "unavailable",
        "video has been removed",
        "video unavailable",
        "private video",
        "sign in to confirm your age",
        "age-restricted",
    ]
    if any(h in s for h in terminal_hints):
        return False

    # По умолчанию: 1 повтор попробовать можно
    return True


def _extract_description_from_info(info: dict) -> str:
    """
    Унифицированное извлечение текста: description, title, caption.
    """
    cand = (
        info.get("description")
        or info.get("fulltitle")
        or info.get("title")
        or info.get("caption")
        or ""
    )
    if not cand and "entries" in info and isinstance(info["entries"], list):
        # Плейлисты/мульти-видео
        for it in info["entries"]:
            cand = (
                (it or {}).get("description")
                or (it or {}).get("title")
                or (it or {}).get("caption")
                or ""
            )
            if cand:
                break
    return cand or ""


def _try_download_with_yt_dlp(url: str) -> Tuple[str, str]:
    """
    Одна попытка скачать через yt-dlp. Бросает исключение при неудаче.
    """
    output_path = os.path.join(VIDEO_FOLDER, "%(id)s.%(ext)s")
    ydl_opts = _yt_dlp_opts(output_path)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)  # может бросить
        raw_path = ydl.prepare_filename(info)
        file_path = _finalize_path(raw_path, prefer_ext="mp4")
        desc = _extract_description_from_info(info)
        logger.debug("✅ yt-dlp скачал файл: %s", file_path)
        return file_path, desc


def _instagram_shortcode_from_url(url: str) -> str | None:
    """
    Извлекаем shortcode из ссылок Instagram:
    - .../reel/<shortcode>/
    - .../p/<shortcode>/
    - .../share/<shortcode>/
    """
    m = re.search(r"/(?:reel|p|share)/([A-Za-z0-9_-]{5,})", url)
    return m.group(1) if m else None


def _download_with_instaloader(url: str) -> Tuple[str, str]:
    """
    Фолбэк для Instagram через instaloader==4.14.2.
    Скачиваем видео поста/рила по shortcode, возвращаем путь и подпись.
    """
    if Instaloader is None or Post is None:
        raise RuntimeError(
            "instaloader не установлен. Установите instaloader для фолбэка."
        )

    shortcode = _instagram_shortcode_from_url(url)
    if not shortcode:
        raise ValueError("Не удалось извлечь Instagram shortcode из URL.")

    _ensure_dir(VIDEO_FOLDER)

    # Настройки: сохраняем только медиа, без доп. файлов и альбомов
    L = Instaloader(
        dirname_pattern=VIDEO_FOLDER.rstrip("/"),
        filename_pattern="{shortcode}",
        download_pictures=False,
        download_videos=True,
        download_video_thumbnails=False,
        save_metadata=False,
        compress_json=False,
        post_metadata_txt_pattern="",
        max_connection_attempts=3,
        quiet=True,
    )

    # «Человечные» паузы
    _random_human_sleep(0.8, 2.2)

    post = Post.from_shortcode(L.context, shortcode)
    caption = post.caption or ""

    # Скачаем только этот пост (если карусель — instaloader может качать
    # все элементы, но в большинстве случаев Reels — одиночное видео)
    L.download_post(post, target=".")

    # Instaloader сохраняет как {shortcode}.mp4 в VIDEO_FOLDER
    candidate = Path(VIDEO_FOLDER) / f"{shortcode}.mp4"
    if not candidate.exists():
        # возможны варианты именования; попробуем найти любой .mp4 с shortcode
        for p in Path(VIDEO_FOLDER).glob(f"{shortcode}*.mp4"):
            candidate = p
            break

    if not candidate.exists():
        raise FileNotFoundError(
            "Instaloader не создал видеофайл ожидемого имени."
        )

    logger.debug("✅ instaloader скачал файл: %s", candidate)
    return str(candidate), caption


def download_video_and_description(url: str) -> Tuple[str, str]:
    """
    Скачивает видео и возвращает (path, description).
    1) yt-dlp с несколькими повторами и «человечными» паузами
    2) При Instagram-ошибках типа 403/429/login — фолбэк на instaloader
    (одна попытка)
    """
    _ensure_dir(VIDEO_FOLDER)
    platform = _platform_from_url(url)

    max_attempts = 3
    base_sleep = 1.0  # сек; будет нарастать экспоненциально
    last_exc: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            # Небольшая человеческая задержка перед каждой попыткой
            _random_human_sleep(0.6, 1.8)
            return _try_download_with_yt_dlp(url)
        except (DownloadError, ExtractorError) as e:
            last_exc = e
            logger.warning(
                "yt-dlp ошибка (%d/%d): %s", attempt, max_attempts, e
            )

            # Если это Instagram-ошибка логина/рейта — переходим к instaloader
            if platform == "instagram" and _is_instagram_login_or_rate_error(
                e
            ):
                logger.info(
                    "Переходим на instaloader из-за ограничений Instagram…"
                )
                try:
                    return _download_with_instaloader(url)
                except Exception as ie:
                    logger.error(
                        "instaloader тоже не смог: %s", ie, exc_info=True
                    )
                    # если instaloader не помог — прекращаем
                    return "", ""

            # Решаем, стоит ли ретраить yt-dlp
            if attempt < max_attempts and _should_retry(e):
                # экспоненциальная пауза + джиттер
                delay = base_sleep * (2 ** (attempt - 1)) + random.uniform(
                    0.2, 0.8
                )
                delay = min(delay, 6.0)
                logger.debug("Повтор через %.1f сек…", delay)
                time.sleep(delay)
                continue
            else:
                break
        except (
            socket.timeout, URLError, HTTPError, OSError, ConnectionError
        ) as ne:
            last_exc = ne
            logger.warning(
                "Сетевая ошибка (%d/%d): %s", attempt, max_attempts, ne
            )
            if attempt < max_attempts:
                delay = base_sleep * (2 ** (attempt - 1)) + random.uniform(
                    0.1, 0.6
                )
                delay = min(delay, 5.0)
                time.sleep(delay)
                continue
            break
        except Exception as e:
            # Прочие ошибки — завершаем без агрессивных ретраев
            last_exc = e
            logger.error("Неожиданная ошибка: %s", e, exc_info=True)
            break

    logger.error("❌ Не удалось скачать видео: %s", last_exc)
    return "", ""


async def async_download_video_and_description(url: str) -> Tuple[str, str]:
    """
    Асинхронная обёртка поверх блокирующей загрузки.
    """
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
                            logger.debug(
                                f'Удалён неиспользуемый файл: {file_path}'
                            )
                except Exception as e:
                    logger.error(
                        f'Ошибка при удалении файла: {file_path} — {e}'
                    )
        await asyncio.sleep(INACTIVITY_LIMIT_SECONDS)

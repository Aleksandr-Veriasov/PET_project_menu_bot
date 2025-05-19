from unittest.mock import AsyncMock, Mock, mock_open, patch

import ffmpeg  # type: ignore
import pytest

from app.media.video_downloader import (
    convert_to_mp4,
    correct_resolution,
    download_video_and_description,
    get_video_resolution,
    send_video_to_channel,
)


def test_download_video_and_description_success(mocker):
    '''Проверяем успешное скачивание видео и описание.'''
    mock_yt_dlp = mocker.patch('app.media.video_downloader.yt_dlp.YoutubeDL')
    mock_instance = mock_yt_dlp.return_value.__enter__.return_value
    mock_instance.extract_info.return_value = {
        'title': 'Test Video',
        'ext': 'mp4',
        'description': 'Test Description'
    }
    mock_instance.prepare_filename.return_value = 'videos/Test Video.mp4'

    url = 'https://example.com/video'
    file_path, description = download_video_and_description(url)

    assert file_path == 'videos/Test Video.mp4'
    assert description == 'Test Description'
    mock_instance.extract_info.assert_called_once_with(url, download=True)


def test_download_video_and_description_error(mocker):
    '''Проверяем обработку ошибки при скачивании.'''
    mock_yt_dlp = mocker.patch('app.media.video_downloader.yt_dlp.YoutubeDL')
    mock_instance = mock_yt_dlp.return_value.__enter__.return_value
    mock_instance.extract_info.side_effect = Exception('Download error')

    url = 'https://example.com/video'
    result = download_video_and_description(url)

    assert result == ('', '')


def test_get_video_resolution_success(mocker):
    '''Проверяем успешное получение разрешения видео.'''
    mock_probe = mocker.patch('app.media.video_downloader.ffmpeg.probe')
    mock_probe.return_value = {
        'streams': [{'width': 1920, 'height': 1080}]
    }

    width, height = get_video_resolution('test_video.mp4')

    assert width == 1920
    assert height == 1080
    mock_probe.assert_called_once_with(
        'test_video.mp4',
        v='error',
        select_streams='v:0',
        show_entries='stream=width,height'
    )


def test_get_video_resolution_error(mocker):
    '''Проверяем обработку ошибки при анализе видео.'''
    mock_probe = mocker.patch('app.media.video_downloader.ffmpeg.probe')
    mock_probe.side_effect = ffmpeg.Error('Probe error', b'stdout', b'stderr')

    width, height = get_video_resolution('test_video.mp4')

    assert width == 0
    assert height == 0


def test_correct_resolution():
    '''Проверяем корректировку разрешения.'''
    assert correct_resolution(1921, 1081) == (1920, 1080)
    assert correct_resolution(1920, 1080) == (1920, 1080)


def test_convert_to_mp4_success(mocker):
    '''Проверяем успешную конвертацию видео.'''
    mock_ffmpeg = mocker.patch('app.media.video_downloader.ffmpeg.input')
    mock_ffmpeg.return_value.output.return_value.run.return_value = None

    mock_get_resolution = mocker.patch(
        'app.media.video_downloader.get_video_resolution'
    )
    mock_get_resolution.return_value = (1920, 1080)

    input_path = 'test_video.mp4'
    output_path = convert_to_mp4(input_path)

    assert output_path == 'test_video_converted.mp4'
    mock_ffmpeg.return_value.output.assert_called_once()


def test_convert_to_mp4_error(mocker):
    '''Проверяем обработку ошибки при конвертации.'''
    mock_ffmpeg = mocker.patch('app.media.video_downloader.ffmpeg.input')
    mock_ffmpeg.return_value.output.return_value.run.side_effect = (
        ffmpeg.Error('Conversion error', b'stdout', b'stderr')
    )

    mock_get_resolution = mocker.patch(
        'app.media.video_downloader.get_video_resolution'
    )
    mock_get_resolution.return_value = (1920, 1080)

    input_path = 'test_video.mp4'
    output_path = convert_to_mp4(input_path)

    assert output_path == ''


@pytest.mark.asyncio
async def test_send_video_to_channel_success(mocker):
    '''Проверяем успешную отправку видео в канал.'''
    # Мокируем bot.send_video с использованием AsyncMock
    mock_bot = mocker.patch(
        'app.media.video_downloader.CallbackContext.bot',
        new_callable=AsyncMock
    )
    mock_message = Mock()
    mock_message.video.file_id = 'test_file_id'
    mock_bot.send_video.return_value = mock_message

    # Мокируем os.getenv для получения CHAT_ID
    mocker.patch(
        'app.media.video_downloader.os.getenv', return_value='test_chat_id'
    )

    # Мокируем open для двух разных случаев: .env и видеофайл
    mock_file_open = mock_open()
    with patch('builtins.open', mock_file_open):
        # Настраиваем side_effect для разных путей
        mock_file_open.side_effect = [
            # Для .env файла
            mock_open(read_data='CHAT_ID=test_chat_id').return_value,
            mock_open().return_value  # Для видеофайла
        ]

        context = Mock()
        context.bot = mock_bot  # Привязываем мокированный bot к context
        converted_video_path = 'test_video_converted.mp4'

        # Вызываем функцию
        result = await send_video_to_channel(
            context,
            converted_video_path
        )

        # Проверяем результат
        assert result == 'test_file_id'
        mock_bot.send_video.assert_called_once()
        mock_file_open.assert_any_call(converted_video_path, 'rb')


@pytest.mark.asyncio
async def test_send_video_to_channel_error(mocker):
    '''Проверяем обработку ошибки при отправке видео.'''
    mock_bot = mocker.patch('app.media.video_downloader.CallbackContext.bot')
    mock_bot.send_video.side_effect = Exception('Send error')

    mocker.patch(
        'app.media.video_downloader.os.getenv', return_value='test_chat_id'
    )

    context = Mock()
    converted_video_path = 'test_video_converted.mp4'

    result = await send_video_to_channel(context, converted_video_path)

    assert result == ''

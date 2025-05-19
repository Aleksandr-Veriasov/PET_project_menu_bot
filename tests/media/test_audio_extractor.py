from unittest.mock import patch

import pytest

from app.media.audio_extractor import extract_audio


def test_extract_audio_success(sample_video_file, tmp_path):
    '''
    Проверяем успешное извлечение аудио из видеофайла.
    '''
    # Указываем путь для выходного аудиофайла
    audio_folder = tmp_path / 'audio'
    audio_folder.mkdir()
    # Имя файла совпадает с входным
    output_audio = audio_folder / f'{sample_video_file.stem}.wav'

    # Мокируем вызов subprocess.run
    with patch('app.media.audio_extractor.subprocess.run') as mock_run:
        mock_run.return_value = None  # subprocess.run ничего не возвращает

        # Вызываем функцию
        result = extract_audio(str(sample_video_file), str(audio_folder))

        # Проверяем, что результат совпадает с ожидаемым
        assert result == str(output_audio)
        mock_run.assert_called_once_with(
            [
                'ffmpeg', '-i', str(sample_video_file),
                '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
                str(output_audio)
            ],
            check=True
        )


def test_extract_audio_invalid_file(tmp_path):
    '''
    Проверяем обработку некорректного видеофайла.
    '''
    # Создаём некорректный видеофайл
    invalid_video_file = tmp_path / 'invalid_video.mp4'
    # Записываем текст вместо видео
    invalid_video_file.write_text('This is not a valid video file')

    # Указываем путь для выходного аудиофайла
    output_audio = tmp_path / 'output_audio.wav'

    # Проверяем, что вызывается исключение
    with pytest.raises(Exception):
        # Ожидаем, что subprocess.run выбросит исключение
        extract_audio(str(invalid_video_file), str(output_audio))

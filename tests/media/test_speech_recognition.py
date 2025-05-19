from app.media.speech_recognition import transcribe_audio


def test_transcribe_audio_success(mocker):
    """
    Проверяем успешную транскрибацию.
    """
    mock_model = mocker.patch('app.media.speech_recognition.model')
    mock_model.transcribe.return_value = {'text': 'Пример текста'}

    audio_path = '/path/to/audio/file.wav'
    result = transcribe_audio(audio_path)

    assert result == 'Пример текста'
    mock_model.transcribe.assert_called_once_with(audio_path)


def test_transcribe_audio_error(mocker):
    """
    Проверяем обработку ошибки при транскрибации.
    """
    mock_model = mocker.patch('app.media.speech_recognition.model')
    mock_model.transcribe.side_effect = Exception('Ошибка транскрибации')

    audio_path = '/path/to/audio/file.wav'
    result = transcribe_audio(audio_path)

    assert result == ''
    mock_model.transcribe.assert_called_once_with(audio_path)

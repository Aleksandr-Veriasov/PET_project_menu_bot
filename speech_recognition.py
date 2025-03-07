import logging

import whisper

# Загружаем модель Whisper (можно выбрать другую, например, 'medium', 'large')
model = whisper.load_model('small')


def transcribe_audio(audio_path):
    '''Распознаёт речь из аудиофайла.'''
    logging.info(f'Запуск транскрибации для файла: {audio_path}')

    try:
        result = model.transcribe(audio_path)
        # Логируем первые 100 символов текста
        logging.info(f'Транскрибация завершена: {result["text"][:100]}...')
        return result['text']
    except Exception as e:
        logging.error(f'Ошибка при транскрибации: {e}')
        return ''

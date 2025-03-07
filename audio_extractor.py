import os
import subprocess

AUDIO_FOLDER = 'audio/'


def extract_audio(video_path):
    '''Извлекает аудио из видео и сохраняет как WAV.'''
    if not os.path.exists(AUDIO_FOLDER):
        os.makedirs(AUDIO_FOLDER)

    audio_path = os.path.join(
        AUDIO_FOLDER,
        os.path.basename(video_path).rsplit('.', 1)[0] + '.wav'
    )

    command = [
        'ffmpeg', '-i', video_path,
        '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
        audio_path
    ]

    subprocess.run(command, check=True)
    return audio_path

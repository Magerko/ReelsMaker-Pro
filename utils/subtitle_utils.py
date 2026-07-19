import logging
import os
import platform
import subprocess
import sys
import threading
from typing import Callable, Optional

from .ffmpeg_utils import run_ffmpeg
from .transcribe_cli import WORKER_FLAG

logger = logging.getLogger(__name__)

# faster-whisper принимает коды ISO 639-1, а в интерфейсе языки названы словами.
LANGUAGE_CODES = {
    "russian": "ru",
    "english": "en",
    "ukrainian": "uk",
    "german": "de",
    "french": "fr",
    "spanish": "es",
    "italian": "it",
}


def extract_audio(video_path: str, audio_path: str):
    cmd = [
        "-y",
        "-i", video_path,
        "-vn",
        "-ar", "16000",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        audio_path
    ]
    run_ffmpeg(cmd, video_path)


def _format_time(seconds):
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    ms = int((s - int(s)) * 1000)
    return f"{int(h):02}:{int(m):02}:{int(s):02},{ms:03}"


def _worker_command(audio_path, srt_path, model_name, language, words_per_line):
    """Как запустить дочерний процесс — из сборки или из исходников."""
    arguments = [
        WORKER_FLAG,
        '--audio', audio_path,
        '--srt', srt_path,
        '--model', model_name,
        '--language', language or '',
        '--words-per-line', str(words_per_line),
    ]
    if getattr(sys, 'frozen', False):
        # Отдельный исполняемый файл со своим набором библиотек. Перезапускать
        # само приложение нельзя: рядом с ним лежит Qt, Windows подтянет его в
        # оба процесса, и распознавание снова упадёт.
        worker = os.path.join(os.path.dirname(os.path.abspath(sys.executable)),
                              'transcriber', 'rm-transcribe.exe')
        return [worker] + arguments
    entry = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'transcribe_cli.py')
    return [sys.executable, entry] + arguments


def generate_srt_from_whisper(
        audio_path: str,
        srt_path: str,
        model_name: str,
        language: str,
        words_per_line: int,
        progress_callback: Optional[Callable[[int], None]] = None,
):
    """Распознаёт речь и пишет SRT.

    Работа идёт в отдельном процессе: Qt и ctranslate2 конфликтуют при загрузке
    нативных библиотек, и в одном процессе с интерфейсом обращение к модели
    роняет программу без единого сообщения.
    """
    command = _worker_command(audio_path, srt_path, model_name, language, words_per_line)

    creationflags = 0
    if platform.system() == 'Windows':
        creationflags = subprocess.CREATE_NO_WINDOW

    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL, text=True, encoding='utf-8',
        errors='replace', bufsize=1, creationflags=creationflags)

    # stdout вычитываем отдельным потоком: иначе дочерний процесс упрётся в
    # переполненный буфер канала, пока родитель читает stderr, и оба замрут.
    drained = []

    def drain_stdout():
        drained.append(process.stdout.read())

    reader = threading.Thread(target=drain_stdout, daemon=True)
    reader.start()

    failure = None
    for line in process.stderr:
        line = line.strip()
        if line.startswith('PROGRESS ') and progress_callback:
            try:
                progress_callback(int(line.split(' ', 1)[1]))
            except ValueError:
                pass
        elif line.startswith('ERROR '):
            failure = line.split(' ', 1)[1]
        elif line:
            logger.info('transcriber: %s', line)

    code = process.wait()
    reader.join(timeout=5)
    process.stdout.close()
    process.stderr.close()

    if code != 0 or failure:
        raise RuntimeError(
            'Не удалось распознать речь. При первом запуске модель скачивается '
            'из интернета. Ошибка: %s' % (failure or 'код возврата %d' % code))

    logger.info(f"SRT file saved to {srt_path}")
    return srt_path

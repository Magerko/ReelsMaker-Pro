import logging
from typing import Callable, Optional

from .ffmpeg_utils import run_ffmpeg

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


def generate_srt_from_whisper(
        audio_path: str,
        srt_path: str,
        model_name: str,
        language: str,
        words_per_line: int,
        progress_callback: Optional[Callable[[int], None]] = None,
):
    # Импорт отложен: подтягивание модели заметно дороже старта приложения.
    from faster_whisper import WhisperModel

    logger.info(f"Loading Whisper model '{model_name}'...")
    try:
        # int8 на CPU: та же модель, но без тяжёлой зависимости от torch и
        # заметно быстрее на обычных машинах без видеокарты.
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
    except Exception as e:
        raise RuntimeError(
            f"Не удалось загрузить модель Whisper '{model_name}'. "
            f"При первом запуске она скачивается из интернета. Ошибка: {e}")

    lang_code = None
    if language and language != "Auto-detect":
        lang_code = LANGUAGE_CODES.get(language.lower(), language.lower())

    logger.info("Model loaded. Starting transcription...")
    segments, info = model.transcribe(
        audio_path, language=lang_code, word_timestamps=True)

    total_duration = getattr(info, "duration", 0) or 0
    srt_content = ""
    sub_index = 1

    # segments - генератор: распознавание идёт по мере обхода, поэтому прогресс
    # можно отдавать прямо здесь.
    for segment in segments:
        words = getattr(segment, "words", None)
        if not words:
            continue

        for i in range(0, len(words), words_per_line):
            chunk = words[i:i + words_per_line]
            if not chunk:
                continue

            start_time = _format_time(chunk[0].start)
            end_time = _format_time(chunk[-1].end)
            text = " ".join(word.word for word in chunk).strip()

            srt_content += f"{sub_index}\n"
            srt_content += f"{start_time} --> {end_time}\n"
            srt_content += f"{text}\n\n"
            sub_index += 1

        if progress_callback and total_duration > 0:
            progress_callback(min(99, int(segment.end / total_duration * 100)))

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt_content)

    if progress_callback:
        progress_callback(100)

    logger.info(f"SRT file saved to {srt_path}")
    return srt_path

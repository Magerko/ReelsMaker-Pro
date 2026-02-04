import os
import datetime
from .ffmpeg_utils import run_ffmpeg


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


def generate_srt_from_whisper(audio_path: str, srt_path: str, model_name: str, language: str, words_per_line: int):
    import whisper
    print(f"Loading Whisper model '{model_name}'...")
    try:
        model = whisper.load_model(model_name)
    except Exception as e:
        raise RuntimeError(
            f"Не удалось загрузить модель Whisper '{model_name}'. Убедитесь, что она доступна. Ошибка: {e}")

    print("Model loaded. Starting transcription...")
    lang_code = language.lower() if language != "Auto-detect" else None

    result = model.transcribe(audio_path, language=lang_code, verbose=True, fp16=False, word_timestamps=True)

    print("Transcription finished. Generating SRT file...")

    srt_content = ""
    sub_index = 1

    for segment in result['segments']:
        if 'words' not in segment:
            continue

        words = segment['words']

        num_words = len(words)
        for i in range(0, num_words, words_per_line):
            chunk = words[i:i + words_per_line]
            if not chunk:
                continue

            start_time = _format_time(chunk[0]['start'])
            end_time = _format_time(chunk[-1]['end'])
            text = " ".join([word['word'] for word in chunk]).strip()

            srt_content += f"{sub_index}\n"
            srt_content += f"{start_time} --> {end_time}\n"
            srt_content += f"{text}\n\n"
            sub_index += 1

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt_content)

    print(f"SRT file saved to {srt_path}")
    return srt_path
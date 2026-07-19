"""Дочерний процесс распознавания речи.

Запускается отдельно от интерфейса намеренно: Qt и ctranslate2 конфликтуют при
загрузке нативных библиотек, и если Qt загрузился первым, обращение к модели
роняет процесс без единого сообщения. Отдельный процесс загруженных Qt
библиотек не наследует.

Здесь нельзя импортировать PyQt5 — ни прямо, ни через utils. Прогресс идёт в
stderr строками «PROGRESS n», готовый SRT пишется в файл.
"""
import argparse
import os
import sys

WORKER_FLAG = '--transcribe-worker'

LANGUAGE_CODES = {
    'русский': 'ru', 'russian': 'ru',
    'английский': 'en', 'english': 'en',
    'украинский': 'uk', 'ukrainian': 'uk',
}


def _emit(kind, value):
    print('%s %s' % (kind, value), file=sys.stderr, flush=True)


def _format_time(seconds):
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    ms = int((s - int(s)) * 1000)
    return '%02d:%02d:%02d,%03d' % (int(h), int(m), int(s), ms)


def run(args):
    from faster_whisper import WhisperModel

    _emit('STAGE', 'loading')
    # int8 на CPU: та же модель, но без тяжёлой зависимости от torch и заметно
    # быстрее на машинах без видеокарты.
    model = WhisperModel(args.model, device='cpu', compute_type='int8')

    language = None
    if args.language and args.language != 'Auto-detect':
        language = LANGUAGE_CODES.get(args.language.lower(), args.language.lower())

    _emit('STAGE', 'transcribing')
    segments, info = model.transcribe(args.audio, language=language,
                                      word_timestamps=True)

    total = getattr(info, 'duration', 0) or 0
    lines = []
    index = 1
    # segments — генератор: распознавание идёт по мере обхода, поэтому прогресс
    # отдаём прямо здесь.
    for segment in segments:
        words = getattr(segment, 'words', None)
        if not words:
            continue
        for start in range(0, len(words), args.words_per_line):
            chunk = words[start:start + args.words_per_line]
            if not chunk:
                continue
            text = ' '.join(word.word for word in chunk).strip()
            lines.append('%d\n%s --> %s\n%s\n\n' % (
                index, _format_time(chunk[0].start), _format_time(chunk[-1].end), text))
            index += 1
        if total > 0:
            _emit('PROGRESS', min(99, int(segment.end / total * 100)))

    with open(args.srt, 'w', encoding='utf-8') as handle:
        handle.write(''.join(lines))
    _emit('PROGRESS', 100)
    return 0


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(WORKER_FLAG, action='store_true', dest='worker')
    parser.add_argument('--audio', required=True)
    parser.add_argument('--srt', required=True)
    parser.add_argument('--model', default='base')
    parser.add_argument('--language', default='')
    parser.add_argument('--words-per-line', type=int, default=5, dest='words_per_line')
    args = parser.parse_args(argv)
    try:
        return run(args)
    except Exception as error:
        _emit('ERROR', error)
        return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

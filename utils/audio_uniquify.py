import random
from typing import Optional

def get_pitch_shift_filter(shift_factor: float = None) -> str:
    if shift_factor is None:
        shift_factor = random.uniform(0.95, 1.05)
    semitones = (shift_factor - 1.0) * 12
    return f"asetrate=44100*{shift_factor},aresample=44100"

def get_reverb_filter(room_size: float = None) -> str:
    if room_size is None:
        room_size = random.uniform(0.3, 0.6)
    return f"aecho=0.8:0.88:{int(room_size*1000)}:0.3"

def get_bass_boost_filter(strength: int = None) -> str:
    if strength is None:
        strength = random.randint(2, 6)
    return f"bass=g={strength}"

def get_treble_adjust_filter(db: int = None) -> str:
    if db is None:
        db = random.randint(-3, 3)
    return f"treble=g={db}"

def get_compression_filter() -> str:
    return "acompressor=threshold=-20dB:ratio=4:attack=5:release=50"

def get_normalization_filter() -> str:
    return "loudnorm=I=-16:TP=-1.5:LRA=11"

def build_audio_uniquify_filters(
    pitch_shift: bool = False,
    reverb: bool = False,
    bass_boost: bool = False,
    treble_adjust: bool = False,
    compression: bool = False,
    normalize: bool = False
) -> str:
    filters = []

    if pitch_shift:
        filters.append(get_pitch_shift_filter())
    if reverb:
        filters.append(get_reverb_filter())
    if bass_boost:
        filters.append(get_bass_boost_filter())
    if treble_adjust:
        filters.append(get_treble_adjust_filter())
    if compression:
        filters.append(get_compression_filter())
    if normalize:
        filters.append(get_normalization_filter())

    return ",".join(filters) if filters else None

def get_random_audio_filter() -> str:
    options = [
        get_pitch_shift_filter(),
        get_reverb_filter(),
        get_bass_boost_filter(),
        get_treble_adjust_filter(),
        get_compression_filter(),
    ]
    return random.choice(options)

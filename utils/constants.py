APP_NAME = "ReelsMaker Pro"
APP_VERSION = "1.0.0"
LOG_FILE = "app.log"
FFMPEG_EXE_PATH = "ffmpeg/bin/ffmpeg.exe"

VIDEO_EXTENSIONS = ['.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv']
GIF_EXTENSIONS = ['.gif']
VALID_INPUT_EXTENSIONS = VIDEO_EXTENSIONS + GIF_EXTENSIONS

FILTERS = {
    "Нет фильтра": "",
    "Случ. цвет (яркость/контраст/...)": "eq=brightness={br}:contrast={ct}:saturation={sat},hue=h={hue}",
    "Черно-белое": "hue=s=0",
    "Сепия": "colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131:0",
    "Инверсия": "negate",
    "Размытие (легкое)": "gblur=sigma=2",
    "Размытие (сильное)": "gblur=sigma=10",
    "Отразить по горизонтали": "hflip",
    "Отразить по вертикали": "vflip",
    "Пикселизация": "scale=iw/10:ih/10,scale=iw*10:ih*10:flags=neighbor",
    "VHS (шум, сдвиг)": "chromashift=1:1,noise=alls=20:allf=t+u",
    "Повыш. контрастность": "eq=contrast=1.5",
    "Пониж. контрастность": "eq=contrast=0.7",
    "Повыш. насыщенность": "eq=saturation=1.5",
    "Пониж. насыщенность": "eq=saturation=0.5",
    "Повыш. яркость": "eq=brightness=0.15",
    "Пониж. яркость": "eq=brightness=-0.15",
    "Холодный фильтр": "curves=b='0/0 0.4/0.5 1/1':g='0/0 0.4/0.4 1/1'",
    "Теплый фильтр": "curves=r='0/0 0.4/0.5 1/1':g='0/0 0.6/0.6 1/1'",
    "Виньетка": "vignette=PI/4",
    "Виньетка (сильная)": "vignette=PI/3",
    "Искажение линз": "lenscorrection=k1=-0.227:k2=-0.022",
    "RGB сдвиг": "chromashift=cbh=-2:crh=2",
    "Шум/зерно": "noise=alls=12:allf=t",
    "Шум (сильный)": "noise=alls=25:allf=t+u",
    "Резкость": "unsharp=5:5:1.0:5:5:0.0",
    "Мягкий фокус": "smartblur=1.5:-0.35",
    "Cyan-Magenta": "colorbalance=rs=.3:gs=-.1:bs=-.2",
    "Orange-Teal": "colorbalance=rs=.15:bs=-.15",
    "Случайный фильтр": "RANDOM_PLACEHOLDER"
}

# Порядок групп задаёт порядок в списке: тридцать фильтров подряд глазом не
# охватить, разбитые по смыслу — охватываются.
FILTER_GROUPS = (
    ("Цвет", [
        "Случ. цвет (яркость/контраст/...)",
        "Черно-белое",
        "Сепия",
        "Инверсия",
        "Холодный фильтр",
        "Теплый фильтр",
        "Cyan-Magenta",
        "Orange-Teal",
    ]),
    ("Яркость и контраст", [
        "Повыш. контрастность",
        "Пониж. контрастность",
        "Повыш. насыщенность",
        "Пониж. насыщенность",
        "Повыш. яркость",
        "Пониж. яркость",
    ]),
    ("Резкость и размытие", [
        "Резкость",
        "Мягкий фокус",
        "Размытие (легкое)",
        "Размытие (сильное)",
    ]),
    ("Плёнка и шум", [
        "VHS (шум, сдвиг)",
        "Шум/зерно",
        "Шум (сильный)",
        "RGB сдвиг",
        "Виньетка",
        "Виньетка (сильная)",
    ]),
    ("Геометрия", [
        "Отразить по горизонтали",
        "Отразить по вертикали",
        "Искажение линз",
        "Пикселизация",
    ]),
    ("Особые", [
        "Случайный фильтр",
    ]),
)

SUBTITLE_PRESETS = {
    "Классический": {
        "font": "Arial",
        "size": 36,
        "color": "#FFFFFF",
        "outline_color": "#000000",
        "outline_width": 2,
        "shadow": 1,
        "bold": False,
        "position": 2
    },
    "Жирный TikTok": {
        "font": "Arial Black",
        "size": 42,
        "color": "#FFFFFF",
        "outline_color": "#000000",
        "outline_width": 3,
        "shadow": 2,
        "bold": True,
        "position": 5
    },
    "Неон": {
        "font": "Impact",
        "size": 40,
        "color": "#00FF00",
        "outline_color": "#0000FF",
        "outline_width": 3,
        "shadow": 3,
        "bold": False,
        "position": 2
    },
    "Минимализм": {
        "font": "Calibri",
        "size": 32,
        "color": "#F0F0F0",
        "outline_color": "#1A1A1A",
        "outline_width": 1,
        "shadow": 0,
        "bold": False,
        "position": 2
    },
    "YouTube стиль": {
        "font": "Roboto",
        "size": 38,
        "color": "#FFFFFF",
        "outline_color": "#CC0000",
        "outline_width": 2,
        "shadow": 2,
        "bold": True,
        "position": 8
    }
}

ROTATION_RANGE = (-3, 3)
AUDIO_PITCH_RANGE = (0.95, 1.05)
CROP_RANDOM_OFFSET = 20

OVERLAY_POSITIONS = {
    "Верх-Лево": "x=20:y=70",
    "Верх-Центр": "x=(W-w)/2:y=10",
    "Верх-Право": "x=W-w-10:y=10",
    "Середина-Лево": "x=10:y=(H-h)/2",
    "Середина-Центр": "x=(W-w)/2:y=(H-h)/2",
    "Середина-Право": "x=W-w-10:y=(H-h)/2",
    "Низ-Лево": "x=10:y=H-h-10",
    "Низ-Центр": "x=(W-w)/2:y=H-h-10",
    "Низ-Право": "x=W-w-10:y=H-h-10"
}

REELS_WIDTH = 1080
REELS_HEIGHT = 1920
REELS_FORMAT_NAME = f"Reels/TikTok ({REELS_WIDTH}x{REELS_HEIGHT})"
OUTPUT_FORMATS = ["Оригинальный", REELS_FORMAT_NAME]

# Разделение экрана ("залипалка"): в одной половине кадра — исходное видео,
# в другой — зацикленный фоновый ролик. Значение словаря — высота панели с
# контентом; залипалке достаётся остаток от 1920 px.
SPLIT_LAYOUTS = {
    "Квадрат 1:1 — контент 1080, залипалка 840": 1080,
    "Поровну — 960 и 960": 960,
    "Больше контента — 1280 и 640": 1280,
    "Больше залипалки — 840 и 1080": 840,
}
SPLIT_CONTENT_TOP = "Контент сверху, залипалка снизу"
SPLIT_CONTENT_BOTTOM = "Залипалка сверху, контент снизу"
SPLIT_POSITIONS = [SPLIT_CONTENT_TOP, SPLIT_CONTENT_BOTTOM]

# Готовые фоновые ролики, лежащие в поставке.
PRESETS_DIR = "resources/presets"

# Сценарии: один выбор вместо обхода одиннадцати групп настроек.
# Ключи соответствуют элементам интерфейса, значения — разумные умолчания.
SCENARIOS = {
    "Вертикальное видео 9:16": {
        "output_format": REELS_FORMAT_NAME,
        "blur_background": True,
        "auto_crop": True,
        "split": False,
        "subtitles": False,
    },
    "Вертикальное с субтитрами": {
        "output_format": REELS_FORMAT_NAME,
        "blur_background": True,
        "auto_crop": True,
        "split": False,
        "subtitles": True,
    },
    "Залипалка — разделение экрана": {
        "output_format": REELS_FORMAT_NAME,
        "blur_background": False,
        "auto_crop": False,
        "split": True,
        "subtitles": False,
    },
    "Только перекодировать": {
        "output_format": "Оригинальный",
        "blur_background": False,
        "auto_crop": False,
        "split": False,
        "subtitles": False,
    },
    "С нуля": {},
}

CODECS = {
    "CPU (H.264 | libx264)": "libx264",
    "NVIDIA (H.264 | h264_nvenc)": "h264_nvenc",
    "NVIDIA (H.265 | hevc_nvenc)": "hevc_nvenc",
    "Intel (H.264 | h264_qsv)": "h264_qsv",
    "Intel (H.265 | hevc_qsv)": "hevc_qsv",
    "AMD (H.264 | h264_amf)": "h264_amf",
    "AMD (H.265 | hevc_amf)": "hevc_amf",
}

WHISPER_MODELS = ["tiny", "base", "small", "medium", "large"]
WHISPER_LANGUAGES = ["Auto-detect", "Russian", "English", "Ukrainian", "German", "French", "Spanish", "Italian"]

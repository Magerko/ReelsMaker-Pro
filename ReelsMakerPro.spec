# -*- mode: python ; coding: utf-8 -*-
#
# Собирать только из пути без кириллицы. Хук PyQt5 узнаёт расположение
# плагинов через вспомогательный процесс и декодирует его вывод системной
# кодировкой: на пути вроде «Рабочий стол» буквы превращаются в вопросительные
# знаки, и сборка падает с «Qt plugin directory does not exist». У PyQt6
# (SilenceCutter, загрузчик) этого шага нет, потому там путь и не мешает.
import os

# ffmpeg в репозитории не хранится: положите его в vendor/ перед сборкой.
# Без него приложение соберётся и будет искать ffmpeg в PATH.
binaries = []
for name in ('ffmpeg.exe', 'ffprobe.exe'):
    candidate = os.path.join('vendor', name)
    if os.path.exists(candidate):
        binaries.append((candidate, 'ffmpeg/bin'))

datas = [
    ('resources/icon.png', 'resources'),
    ('resources/icon.ico', 'resources'),
    ('resources/styles_dark.qss', 'resources'),
    ('resources/styles_light.qss', 'resources'),
]
for folder in ('resources/icons', 'resources/presets'):
    if os.path.isdir(folder):
        datas.append((folder, folder))
for extra in ('vendor/FFMPEG-LICENSE.txt',):
    if os.path.exists(extra):
        datas.append((extra, '.'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=['qtawesome'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'unittest',
        'pydoc_data',
        'PyQt5.QtWebEngineCore',
        'PyQt5.QtWebEngineWidgets',
        'PyQt5.QtQml',
        'PyQt5.QtQuick',
        'PyQt5.QtMultimedia',
        'PyQt5.QtBluetooth',
        'PyQt5.QtPositioning',
        'PyQt5.QtSensors',
        'PyQt5.QtSerialPort',
        'PyQt5.QtSql',
        'PyQt5.QtTest',
        # Живут в отдельном исполняемом файле распознавания: рядом с Qt они
        # роняют процесс при обращении к модели.
        'faster_whisper',
        'ctranslate2',
        'onnxruntime',
        'av',
        'torch',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ReelsMakerPro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX портит библиотеки Qt и почти гарантированно приводит к срабатыванию
    # антивирусов.
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='ReelsMakerPro',
)

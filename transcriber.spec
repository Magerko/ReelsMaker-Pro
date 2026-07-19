# -*- mode: python ; coding: utf-8 -*-
"""Отдельный исполняемый файл распознавания речи.

Собирается отдельно от приложения намеренно: Qt и ctranslate2 конфликтуют при
загрузке нативных библиотек. Одного лишь запуска в другом процессе мало —
Windows подтягивает библиотеки из папки родителя, поэтому у распознавания
должна быть своя папка без Qt.
"""
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = [], [], []
for package in ('faster_whisper', 'ctranslate2', 'tokenizers', 'onnxruntime', 'av'):
    try:
        d, b, h = collect_all(package)
    except Exception:
        continue
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    ['utils/transcribe_cli.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Ради этого списка всё и затевалось.
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
        'tkinter',
        'torch',
        'matplotlib',
        'unittest',
        'pydoc_data',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='rm-transcribe',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='transcriber',
)

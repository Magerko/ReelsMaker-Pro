# -*- mode: python ; coding: utf-8 -*-
import os

from PyInstaller.utils.hooks import collect_all

# ffmpeg is fetched into vendor/ at build time and never committed. ffprobe is
# needed too: durations and dimensions are read with it.
binaries = []
for tool in ('ffmpeg.exe', 'ffprobe.exe'):
    candidate = os.path.join('vendor', tool)
    if os.path.exists(candidate):
        binaries.append((candidate, '.'))

datas = [('resources', 'resources')]
if os.path.exists('vendor/FFMPEG-LICENSE.txt'):
    datas.append(('vendor/FFMPEG-LICENSE.txt', '.'))

hiddenimports = []

# faster-whisper reaches ctranslate2, onnxruntime, tokenizers and av, all of
# which carry native libraries or data files the import graph does not reveal.
# qtawesome loads its icon fonts from package data at runtime.
for package in ('faster_whisper', 'ctranslate2', 'onnxruntime', 'tokenizers',
                'av', 'qtawesome'):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'unittest',
        'pydoc_data',
        # torch is what faster-whisper was chosen to avoid; make sure no
        # transitive dependency drags it back in.
        'torch',
        'torchvision',
        'torchaudio',
        'matplotlib',
        'PyQt5.QtWebEngineCore',
        'PyQt5.QtWebEngineWidgets',
        'PyQt5.QtQml',
        'PyQt5.QtQuick',
        'PyQt5.QtMultimedia',
        'PyQt5.QtBluetooth',
        'PyQt5.QtNfc',
        'PyQt5.QtPositioning',
        'PyQt5.QtSensors',
        'PyQt5.QtSerialPort',
        'PyQt5.QtTest',
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
    # UPX mangles Qt DLLs and is a reliable way to get flagged by antivirus.
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

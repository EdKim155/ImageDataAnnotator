# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec файл для Image Data Annotator (Windows).
"""

import sys
from pathlib import Path

block_cipher = None

# Определяем пути
project_dir = Path(SPECPATH)

# Собираем все модули из src
analysis_result = Analysis(
    ['main.py'],
    pathex=[str(project_dir)],
    binaries=[],
    datas=[
        # Добавляем папку stamps если существует
        ('stamps', 'stamps') if (project_dir / 'stamps').exists() else None,
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PIL._tkinter_finder',
        'openpyxl',
        'img2pdf',
        'reportlab',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy.random._examples',
        'tkinter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Фильтруем None из datas
analysis_result.datas = [d for d in analysis_result.datas if d is not None]

pyz = PYZ(
    analysis_result.pure,
    analysis_result.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    analysis_result.scripts,
    [],
    exclude_binaries=True,
    name='ImageDataAnnotator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Без консоли для GUI приложения
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icon.ico',  # Иконка для Windows
    version='version_info.txt',  # Информация о версии
)

coll = COLLECT(
    exe,
    analysis_result.binaries,
    analysis_result.zipfiles,
    analysis_result.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ImageDataAnnotator',
)

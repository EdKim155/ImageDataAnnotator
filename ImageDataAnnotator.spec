# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec файл для Image Data Annotator.
"""

import sys
from pathlib import Path

block_cipher = None

# Определяем пути
project_dir = Path(SPECPATH)
src_dir = project_dir / 'src'

# Собираем все модули из src
analysis_result = Analysis(
    ['main.py'],
    pathex=[str(project_dir)],
    binaries=[],
    datas=[
        # Добавляем папку stamps если существует
        ('stamps', 'stamps') if (project_dir / 'stamps').exists() else None,
    ],
    # Фильтруем None значения
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
    icon='resources/icon.icns',  # Иконка приложения
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

# Создаем .app bundle для macOS
app = BUNDLE(
    coll,
    name='Image Data Annotator.app',
    icon='resources/icon.icns',
    bundle_identifier='com.imagedata.annotator',
    version='1.0.0',
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSAppleScriptEnabled': False,
        'CFBundleName': 'Image Data Annotator',
        'CFBundleDisplayName': 'Image Data Annotator',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'NSHumanReadableCopyright': 'Copyright © 2024',
        'NSHighResolutionCapable': True,
    },
)

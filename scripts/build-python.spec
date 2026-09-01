# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Editor Agent backend

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['backend/app/main.py'],
    pathex=['backend'],
    binaries=[],
    datas=[
        ('config', 'config'),
        ('frontend/dist', 'frontend/dist'),
    ],
    hiddenimports=[
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'uvicorn.lifespan.off',
        'engineio.async_drivers.threading',
        'librosa',
        'librosa.util',
        'soundfile',
        'numpy',
        'numpy.core',
        'numpy.core._methods',
        'numpy.lib',
        'numpy.lib.format',
        'chromadb',
        'chromadb.config',
        'sentence_transformers',
        'torch',
        'transformers',
        'open_clip',
        'faster_whisper',
        'cv2',
        'av',
        'pydantic',
        'pydantic.deprecated',
        'fastapi',
        'starlette',
        'yaml',
        'multipart',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'pandas',
        'PIL',
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
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
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='main',
)

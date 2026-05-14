# PyInstaller spec for the Claire FastAPI backend.
# Produces a single binary: installer/dist/declutter-api-bin
# Run from the repo root with the venv activated:
#   pyinstaller installer/build_api.spec --distpath installer/dist --noconfirm

import sys
from pathlib import Path

root = Path(SPECPATH).parent  # repo root

a = Analysis(
    [str(root / 'declutter_bot' / 'api' / 'app.py')],
    pathex=[str(root)],
    binaries=[],
    datas=[],
    hiddenimports=[
        # ASGI server
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
        # FastAPI / Starlette
        'fastapi',
        'starlette',
        'starlette.middleware',
        'starlette.middleware.cors',
        # Document parsers
        'pypdf',
        'docx',
        'pptx',
        # Google APIs
        'googleapiclient',
        'google.auth',
        'google.oauth2',
        'google.genai',
        # Ollama client
        'ollama',
        # Declutter routes (dynamic imports via FastAPI router)
        'declutter_bot.api.routes.report',
        'declutter_bot.api.routes.scan',
        'declutter_bot.api.routes.search',
        'declutter_bot.api.routes.staging',
        'declutter_bot.api.routes.blacklist',
        'declutter_bot.api.routes.drive',
        'declutter_bot.api.routes.untrack',
        'declutter_bot.api.routes.classify',
        'declutter_bot.api.routes.files',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='declutter-api-bin',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    onefile=True,
)

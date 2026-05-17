from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from declutter_bot.api.routes import report, scan, search, staging, blacklist, drive, untrack, classify, files

app = FastAPI(title="Declutter API", version="0.1.0")

import os
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(report.router)
app.include_router(scan.router)
app.include_router(search.router)
app.include_router(staging.router)
app.include_router(blacklist.router)
app.include_router(drive.router)
app.include_router(untrack.router)
app.include_router(classify.router)
app.include_router(files.router)


@app.get("/")
def root():
    return {"status": "ok", "docs": "/docs"}


def main():
    import sys
    import uvicorn
    frozen = getattr(sys, 'frozen', False)  # True when running as PyInstaller bundle
    uvicorn.run(
        app if frozen else "declutter_bot.api.app:app",
        host="127.0.0.1",
        port=8000,
        reload=not frozen,
    )


if __name__ == "__main__":
    main()

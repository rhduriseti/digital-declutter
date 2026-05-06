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
    import uvicorn
    uvicorn.run("declutter_bot.api.app:app", host="127.0.0.1", port=8000, reload=True)

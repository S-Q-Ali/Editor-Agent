import sys
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

from app.utils.config import load_config, BASE_DIR
from app.api.projects import router as projects_router
from app.api.health import router as health_router
from app.api.upload import router as upload_router
from app.api.jobs import router as jobs_router
from app.api.analysis import router as analysis_router
from app.api.lyrics import router as lyrics_router
from app.api.clips import router as clips_router
from app.api.search import router as search_router
from app.api.timeline import router as timeline_router
from app.api.render import router as render_router
from app.api.qc import router as qc_router
from app.api.revision import router as revision_router
from app.api.files import router as files_router

config = load_config()

app = FastAPI(
    title="Local AI Video Editor",
    description="Local-first AI-assisted video editing agent",
    version="0.1.0",
)

is_frozen = getattr(sys, 'frozen', False)

if is_frozen:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000", "file://"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(projects_router)
app.include_router(health_router)
app.include_router(upload_router)
app.include_router(jobs_router)
app.include_router(analysis_router)
app.include_router(lyrics_router)
app.include_router(clips_router)
app.include_router(search_router)
app.include_router(timeline_router)
app.include_router(render_router)
app.include_router(qc_router)
app.include_router(revision_router)
app.include_router(files_router)


@app.get("/")
async def root():
    return {"message": "Local AI Video Editor API", "version": "0.1.0"}


@app.get("/api/config")
async def get_config():
    return config


frontend_dist = BASE_DIR / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="static")


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.getenv("BACKEND_HOST", "127.0.0.1"),
        port=int(os.getenv("BACKEND_PORT", "8000")),
        reload=False if is_frozen else os.getenv("DEBUG", "true").lower() == "true",
    )

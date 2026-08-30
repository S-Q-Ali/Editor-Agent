from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from pathlib import Path

from app.utils.config import load_config

config = load_config()

app = FastAPI(
    title="Local AI Video Editor",
    description="Local-first AI-assisted video editing agent",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Local AI Video Editor API", "version": "0.1.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/api/config")
async def get_config():
    return config


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.getenv("BACKEND_HOST", "127.0.0.1"),
        port=int(os.getenv("BACKEND_PORT", "8000")),
        reload=os.getenv("DEBUG", "true").lower() == "true",
    )

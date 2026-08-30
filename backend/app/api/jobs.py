from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

jobs: Dict[str, Dict[str, Any]] = {}


@router.post("/{project_path:path}/analyze-music")
async def start_music_analysis(project_path: str):
    job_id = f"music_analysis_{project_path}"
    jobs[job_id] = {
        "id": job_id,
        "type": "music_analysis",
        "project": project_path,
        "status": "queued",
        "progress": 0,
        "result": None,
        "error": None,
    }
    return jobs[job_id]


@router.post("/{project_path:path}/align-lyrics")
async def start_lyrics_alignment(project_path: str):
    job_id = f"lyrics_alignment_{project_path}"
    jobs[job_id] = {
        "id": job_id,
        "type": "lyrics_alignment",
        "project": project_path,
        "status": "queued",
        "progress": 0,
        "result": None,
        "error": None,
    }
    return jobs[job_id]


@router.post("/{project_path:path}/analyze-clips")
async def start_clip_analysis(project_path: str):
    job_id = f"clip_analysis_{project_path}"
    jobs[job_id] = {
        "id": job_id,
        "type": "clip_analysis",
        "project": project_path,
        "status": "queued",
        "progress": 0,
        "result": None,
        "error": None,
    }
    return jobs[job_id]


@router.post("/{project_path:path}/generate-timeline")
async def start_timeline_generation(project_path: str):
    job_id = f"timeline_gen_{project_path}"
    jobs[job_id] = {
        "id": job_id,
        "type": "timeline_generation",
        "project": project_path,
        "status": "queued",
        "progress": 0,
        "result": None,
        "error": None,
    }
    return jobs[job_id]


@router.post("/{project_path:path}/render-preview")
async def start_preview_render(project_path: str):
    job_id = f"preview_render_{project_path}"
    jobs[job_id] = {
        "id": job_id,
        "type": "preview_render",
        "project": project_path,
        "status": "queued",
        "progress": 0,
        "result": None,
        "error": None,
    }
    return jobs[job_id]


@router.get("/{job_id}")
async def get_job_status(job_id: str):
    if job_id not in jobs:
        return {"error": "Job not found"}
    return jobs[job_id]


@router.get("/")
async def list_jobs():
    return list(jobs.values())

"""
Server-Sent Events endpoint for pipeline progress.
"""
import json
import asyncio
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from app.utils.progress import get_progress_dict, subscribe, unsubscribe, init_pipeline

router = APIRouter(prefix="/api/progress", tags=["progress"])


@router.post("/{project_id:path}/init")
async def init_progress(project_id: str):
    """Initialize pipeline progress tracking."""
    init_pipeline(project_id)
    return {"status": "ok", "project_id": project_id}


@router.get("/{project_id:path}")
async def stream_progress(project_id: str, request: Request):
    """Stream pipeline progress via SSE."""
    queue = []
    subscribe(project_id, queue)

    async def event_generator():
        try:
            # Send current state immediately
            current = get_progress_dict(project_id)
            if current:
                yield f"data: {json.dumps(current)}\n\n"

            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break

                # Wait for updates with timeout
                try:
                    data = await asyncio.wait_for(
                        asyncio.to_thread(queue.pop, 0) if queue else asyncio.sleep(0.1),
                        timeout=1.0,
                    )
                    if isinstance(data, dict):
                        yield f"data: {json.dumps(data)}\n\n"
                        if data.get("done"):
                            break
                except (asyncio.TimeoutError, IndexError):
                    # Send heartbeat to keep connection alive
                    current = get_progress_dict(project_id)
                    if current:
                        yield f"data: {json.dumps(current)}\n\n"
                        if current.get("done"):
                            break
                    yield ": heartbeat\n\n"
        finally:
            unsubscribe(project_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{project_id:path}/snapshot")
async def get_progress_snapshot(project_id: str):
    """Get current progress without SSE (for polling fallback)."""
    progress = get_progress_dict(project_id)
    if not progress:
        return {"error": "No pipeline running for this project"}
    return progress

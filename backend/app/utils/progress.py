"""
In-memory progress tracking for pipeline steps.
Thread-safe via simple locking.
"""
import threading
import time
from typing import Dict, Optional, List
from dataclasses import dataclass, field, asdict


@dataclass
class StepProgress:
    name: str
    status: str = "pending"  # pending, running, completed, error
    percent: int = 0
    message: str = ""
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


@dataclass
class PipelineProgress:
    project_id: str
    steps: Dict[str, StepProgress] = field(default_factory=dict)
    current_step: str = ""
    overall_percent: int = 0
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    done: bool = False
    error: Optional[str] = None


_lock = threading.Lock()
_store: Dict[str, PipelineProgress] = {}
_subscribers: Dict[str, List] = {}


PIPELINE_STEPS = [
    "analyzing_music",
    "extracting_lyrics",
    "analyzing_clips",
    "building_index",
    "generating_timeline",
    "rendering_preview",
]

STEP_LABELS = {
    "analyzing_music": "Analyzing music",
    "extracting_lyrics": "Extracting lyrics",
    "analyzing_clips": "Analyzing clips",
    "building_index": "Building search index",
    "generating_timeline": "Generating timeline",
    "rendering_preview": "Rendering preview",
}


def _notify(project_id: str):
    """Notify all SSE subscribers for a project."""
    if project_id in _subscribers:
        dead = []
        for q in _subscribers[project_id]:
            try:
                q.append(get_progress_dict(project_id))
            except Exception:
                dead.append(q)
        for d in dead:
            _subscribers[project_id].remove(d)


def _recalculate_overall(progress: PipelineProgress):
    """Recalculate overall percent from individual step percents."""
    total = len(progress.steps)
    if total == 0:
        progress.overall_percent = 0
        return
    step_sum = sum(s.percent for s in progress.steps.values())
    progress.overall_percent = step_sum // total


def init_pipeline(project_id: str):
    """Initialize a new pipeline progress tracker."""
    with _lock:
        progress = PipelineProgress(
            project_id=project_id,
            started_at=time.time(),
            steps={
                step: StepProgress(name=STEP_LABELS[step])
                for step in PIPELINE_STEPS
            },
        )
        _store[project_id] = progress
        _notify(project_id)


def update_progress(project_id: str, step: str, percent: int, message: str = ""):
    """Update progress for a specific step."""
    with _lock:
        progress = _store.get(project_id)
        if not progress:
            return
        if step in progress.steps:
            s = progress.steps[step]
            if s.status == "pending":
                s.status = "running"
                s.started_at = time.time()
            s.percent = min(100, max(0, percent))
            s.message = message
            if percent >= 100:
                s.status = "completed"
                s.percent = 100
                s.completed_at = time.time()
            progress.current_step = step
            _recalculate_overall(progress)
            _notify(project_id)


def complete_step(project_id: str, step: str):
    """Mark a step as completed."""
    with _lock:
        progress = _store.get(project_id)
        if not progress:
            return
        if step in progress.steps:
            s = progress.steps[step]
            s.status = "completed"
            s.percent = 100
            s.completed_at = time.time()
            _recalculate_overall(progress)
            _notify(project_id)


def fail_step(project_id: str, step: str, error: str = ""):
    """Mark a step as failed."""
    with _lock:
        progress = _store.get(project_id)
        if not progress:
            return
        if step in progress.steps:
            s = progress.steps[step]
            s.status = "error"
            s.message = error
            s.completed_at = time.time()
            progress.error = error
            _notify(project_id)


def complete_pipeline(project_id: str):
    """Mark entire pipeline as completed."""
    with _lock:
        progress = _store.get(project_id)
        if not progress:
            return
        progress.done = True
        progress.overall_percent = 100
        progress.completed_at = time.time()
        for s in progress.steps.values():
            if s.status != "error":
                s.status = "completed"
                s.percent = 100
        _notify(project_id)


def skip_step(project_id: str, step: str, reason: str = ""):
    """Skip a step (e.g., no lyrics found)."""
    with _lock:
        progress = _store.get(project_id)
        if not progress:
            return
        if step in progress.steps:
            s = progress.steps[step]
            s.status = "completed"
            s.percent = 100
            s.message = reason or "Skipped"
            s.completed_at = time.time()
            _recalculate_overall(progress)
            _notify(project_id)


def get_progress_dict(project_id: str) -> Optional[dict]:
    """Get progress as a dict for serialization."""
    progress = _store.get(project_id)
    if not progress:
        return None
    return {
        "project_id": progress.project_id,
        "overall_percent": progress.overall_percent,
        "current_step": progress.current_step,
        "done": progress.done,
        "error": progress.error,
        "steps": {
            name: {
                "name": s.name,
                "status": s.status,
                "percent": s.percent,
                "message": s.message,
            }
            for name, s in progress.steps.items()
        },
    }


def subscribe(project_id: str, queue: list):
    """Subscribe to progress updates. Queue receives progress dicts."""
    with _lock:
        if project_id not in _subscribers:
            _subscribers[project_id] = []
        _subscribers[project_id].append(queue)


def unsubscribe(project_id: str, queue: list):
    """Unsubscribe from progress updates."""
    with _lock:
        if project_id in _subscribers:
            if queue in _subscribers[project_id]:
                _subscribers[project_id].remove(queue)


def cleanup(project_id: str):
    """Remove progress data for a project."""
    with _lock:
        _store.pop(project_id, None)
        _subscribers.pop(project_id, None)

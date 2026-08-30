from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
import json
from app.agents.editor_brain import EditingBrain

router = APIRouter(prefix="/api/revision", tags=["revision"])
brain = EditingBrain()


class RevisionRequest(BaseModel):
    instruction: str


@router.post("/{project_path:path}")
async def apply_revision(project_path: str, data: RevisionRequest):
    project_dir = Path(project_path)
    timeline_file = project_dir / "timeline" / "timeline.json"

    if not timeline_file.exists():
        raise HTTPException(status_code=404, detail="Timeline not found")

    with open(timeline_file, "r") as f:
        timeline = json.load(f)

    events = timeline.get("tracks", {}).get("video", [])
    modified = False

    instruction_lower = data.instruction.lower()

    if "repeat" in instruction_lower or "repetition" in instruction_lower:
        clip_counts = {}
        for event in events:
            clip_id = event["clip_id"]
            clip_counts[clip_id] = clip_counts.get(clip_id, 0) + 1

        for clip_id, count in clip_counts.items():
            if count > 2:
                for i, event in enumerate(events):
                    if event["clip_id"] == clip_id and i > 0:
                        event["confidence"] = max(0.1, event["confidence"] - 0.2)
                        event["reason"] = f"Reduced confidence due to repetition ({data.instruction})"
                        modified = True

    if "low confidence" in instruction_lower:
        for event in events:
            if event.get("confidence", 0) < 0.4:
                event["confidence"] = 0.5
                event["reason"] = f"Adjusted per revision: {data.instruction}"
                modified = True

    if "transition" in instruction_lower:
        for event in events:
            if "smooth" in instruction_lower:
                event["transition"] = "crossfade"
            elif "cut" in instruction_lower:
                event["transition"] = "cut"
            modified = True

    if modified:
        timeline["tracks"]["video"] = events
        timeline["revision_applied"] = data.instruction

        with open(timeline_file, "w") as f:
            json.dump(timeline, f, indent=2)

    return {
        "modified": modified,
        "instruction": data.instruction,
        "events_modified": sum(1 for e in events if "revision" in e.get("reason", "").lower()),
    }

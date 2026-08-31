import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from app.utils.config import get_project_dir


class ProjectManager:
    def __init__(self):
        self.projects_dir = get_project_dir()

    def create_project(self, name: str) -> Dict[str, Any]:
        project_id = str(uuid.uuid4())[:8]
        project_dir = self.projects_dir / f"{name}_{project_id}"

        dirs = ["music", "lyrics", "clips", "analysis", "timeline", "previews", "renders", "logs"]
        for d in dirs:
            (project_dir / d).mkdir(parents=True, exist_ok=True)

        project_data = {
            "id": project_id,
            "name": name,
            "path": str(project_dir.resolve()),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": "created",
            "music_file": None,
            "lyrics_file": None,
            "clips": [],
            "clip_order_file": None,
            "timeline_mode": "auto",
            "analysis_complete": False,
            "timeline_ready": False,
            "preview_ready": False,
            "approved": False,
        }

        self._save_project(project_dir, project_data)
        return project_data

    def get_project(self, project_path: str) -> Optional[Dict[str, Any]]:
        project_dir = Path(project_path)
        project_file = project_dir / "project.json"
        if project_file.exists():
            with open(project_file, "r") as f:
                data = json.load(f)
                data["path"] = str(project_dir.resolve())
                return data
        return None

    def list_projects(self) -> list:
        projects = []
        if self.projects_dir.exists():
            for d in self.projects_dir.iterdir():
                if d.is_dir():
                    project = self.get_project(str(d))
                    if project:
                        project["path"] = str(d.resolve())
                        projects.append(project)
        return projects

    def update_project(self, project_path: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        project = self.get_project(project_path)
        if project:
            project.update(updates)
            project["updated_at"] = datetime.now().isoformat()
            self._save_project(Path(project_path), project)
        return project

    def delete_project(self, project_path: str) -> bool:
        project_dir = Path(project_path)
        if project_dir.exists() and project_dir.is_dir():
            shutil.rmtree(project_dir)
            return True
        return False

    def _save_project(self, project_dir: Path, data: Dict[str, Any]):
        project_file = project_dir / "project.json"
        with open(project_file, "w") as f:
            json.dump(data, f, indent=2)

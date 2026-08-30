from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from app.storage.project_manager import ProjectManager

router = APIRouter(prefix="/api/projects", tags=["projects"])
pm = ProjectManager()


class ProjectCreate(BaseModel):
    name: str


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None


@router.post("/")
async def create_project(data: ProjectCreate):
    project = pm.create_project(data.name)
    return project


@router.get("/")
async def list_projects():
    return pm.list_projects()


@router.get("/{project_path:path}")
async def get_project(project_path: str):
    project = pm.get_project(project_path)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_path:path}")
async def update_project(project_path: str, data: ProjectUpdate):
    updates = data.dict(exclude_none=True)
    project = pm.update_project(project_path, updates)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

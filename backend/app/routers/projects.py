from fastapi import APIRouter, HTTPException
from app.models.project import Project, ProjectCreate
from datetime import datetime
import uuid

router = APIRouter(prefix="/projects", tags=["Projects"])

# In-memory store for MVP (replace with DB in production)
_projects: dict[str, Project] = {}


@router.post("/", response_model=Project, status_code=201)
def create_project(payload: ProjectCreate) -> Project:
    project = Project(**payload.model_dump(), id=str(uuid.uuid4()), created_at=datetime.utcnow(), updated_at=datetime.utcnow())
    _projects[project.id] = project
    return project


@router.get("/", response_model=list[Project])
def list_projects() -> list[Project]:
    return list(_projects.values())


@router.get("/{project_id}", response_model=Project)
def get_project(project_id: str) -> Project:
    project = _projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: str) -> None:
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")
    del _projects[project_id]

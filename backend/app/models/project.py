from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from enum import Enum
import uuid


class LandscapeType(str, Enum):
    watershed = "watershed"
    woreda = "woreda"
    kebele = "kebele"
    rangeland = "rangeland"
    reservoir_catchment = "reservoir_catchment"
    custom = "custom"


class TargetObjective(str, Enum):
    erosion_control = "erosion_control"
    water_security = "water_security"
    food_security = "food_security"
    biodiversity = "biodiversity"
    carbon_sequestration = "carbon_sequestration"
    rangeland_restoration = "rangeland_restoration"
    integrated = "integrated"


class ProjectCreate(BaseModel):
    name: str
    country: str = "Ethiopia"
    region: str
    admin_level: str
    landscape_type: LandscapeType
    target_objective: TargetObjective
    notes: Optional[str] = None
    boundary_geojson: Optional[dict[str, Any]] = None


class Project(ProjectCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "active"

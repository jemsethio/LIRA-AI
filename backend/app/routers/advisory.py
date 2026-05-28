"""Advisory Communication router."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.agents.advisory_agent import AdvisoryCommunicationAgent, AdvisoryPackage
from app.models.syndromes import SyndromeDiagnosis

router = APIRouter(prefix="/advisory", tags=["Advisory & Communication"])
_agent = AdvisoryCommunicationAgent()
_packages: dict[str, AdvisoryPackage] = {}


class AdvisoryRequest(BaseModel):
    syndrome: dict
    degradation_severity: str = "moderate"
    pathway_set: Optional[dict] = None
    climate: Optional[dict] = None
    community: Optional[dict] = None


@router.post("/{project_id}", response_model=AdvisoryPackage)
def generate_advisory(project_id: str, req: AdvisoryRequest) -> AdvisoryPackage:
    try:
        syndrome = SyndromeDiagnosis(**req.syndrome)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid syndrome: {e}")

    output = _agent.run(
        project_id=project_id,
        syndrome=syndrome,
        degradation_severity=req.degradation_severity,
    )
    if not output.success:
        raise HTTPException(status_code=500, detail=str(output.result))
    pkg: AdvisoryPackage = output.result
    _packages[project_id] = pkg
    return pkg


@router.get("/{project_id}", response_model=AdvisoryPackage)
def get_advisory(project_id: str) -> AdvisoryPackage:
    pkg = _packages.get(project_id)
    if not pkg:
        raise HTTPException(status_code=404, detail="No advisory generated yet")
    return pkg

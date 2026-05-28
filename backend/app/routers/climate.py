"""
Climate router — serves from pre-computed CMIP6 data when available,
falls back to fast eco-profile placeholder for interactive API calls.
Background CMIP6 fetch triggered separately via /climate-data endpoints.
"""

import concurrent.futures
from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.models.indicators import LandscapeIndicators
from app.models.climate import ClimateFuturesReport, ClimateScenario
from app.agents.climate_futures_agent import ClimateFuturesAgent

router = APIRouter(prefix="/climate", tags=["Climate Futures"])
_agent   = ClimateFuturesAgent()
_reports: dict[str, ClimateFuturesReport] = {}

# Maximum seconds we allow for CMIP6 download in an interactive request
_INTERACTIVE_TIMEOUT_SEC = 20


@router.post("/{project_id}", response_model=ClimateFuturesReport)
def run_climate_futures(
    project_id: str,
    indicators: LandscapeIndicators,
    scenario: ClimateScenario = ClimateScenario.ssp245,
    horizon: str = "2050",
) -> ClimateFuturesReport:
    """
    Run Climate Futures Agent.
    - Tries real CMIP6 first (20-second budget for interactive use)
    - Falls back immediately to eco-profile placeholder if timeout exceeded
    - Use /climate-data/cmip6/fetch-live for a full background CMIP6 run
    """
    def _run_agent():
        return _agent.run(
            project_id=project_id,
            indicators=indicators,
            scenario=scenario,
            horizon=horizon,
            models=["MIROC6"],          # only 1 model for interactive speed
        )

    # Run with timeout so the API stays responsive
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(_run_agent)
            output = future.result(timeout=_INTERACTIVE_TIMEOUT_SEC)
    except concurrent.futures.TimeoutError:
        # CMIP6 download took too long → run instant eco-profile fallback
        output = _agent.run(
            project_id=project_id,
            indicators=indicators,
            scenario=scenario,
            horizon=horizon,
            models=[],          # empty → skips CMIP6, goes straight to fallback
        )

    if not output.success:
        raise HTTPException(status_code=500, detail=str(output.result))

    report: ClimateFuturesReport = output.result
    _reports[project_id] = report
    return report


@router.get("/{project_id}", response_model=ClimateFuturesReport)
def get_climate_report(project_id: str) -> ClimateFuturesReport:
    report = _reports.get(project_id)
    if not report:
        raise HTTPException(status_code=404, detail="No climate report found — run POST first")
    return report

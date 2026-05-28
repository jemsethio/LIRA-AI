from pydantic import BaseModel
from typing import Optional
from enum import Enum


class ClimateScenario(str, Enum):
    rcp45 = "RCP4.5"
    rcp85 = "RCP8.5"
    ssp245 = "SSP2-4.5"
    ssp585 = "SSP5-8.5"
    mock = "mock_placeholder"


class ClimateRiskIndicator(BaseModel):
    name: str
    current_level: str
    projected_level: str
    change_direction: str          # increasing / decreasing / stable
    risk_score: float              # 0–1
    scenario: ClimateScenario
    horizon: str                   # "2030", "2050", "2070"
    confidence: str
    data_source: str
    is_mock: bool = True


class ClimateFuturesReport(BaseModel):
    project_id: str
    scenario: ClimateScenario
    horizon: str
    rainfall_intensity_risk: ClimateRiskIndicator
    drought_dry_spell_risk: ClimateRiskIndicator
    heat_stress_risk: ClimateRiskIndicator
    soil_moisture_stress: ClimateRiskIndicator
    erosion_runoff_risk: ClimateRiskIndicator
    vegetation_stress: ClimateRiskIndicator
    restoration_suitability_stress: ClimateRiskIndicator
    overall_climate_risk_score: float
    restoration_window_narrowing: bool
    maladaptation_climate_alerts: list[str]
    summary_narrative: str
    is_mock: bool

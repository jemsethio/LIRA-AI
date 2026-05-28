from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class SeverityLevel(str, Enum):
    very_low = "very_low"
    low = "low"
    moderate = "moderate"
    moderate_low = "moderate_low"
    moderately_high = "moderately_high"
    severe = "severe"
    very_severe = "very_severe"
    high = "high"
    very_high = "very_high"
    unknown = "unknown"


class ConditionCategory(str, Enum):
    deficit = "deficit"
    limiting = "limiting"
    adequate = "adequate"
    surplus = "surplus"
    degraded = "degraded"
    sparse = "sparse"
    moderate = "moderate"
    healthy = "healthy"
    unknown = "unknown"


class IndicatorResult(BaseModel):
    value: Optional[float] = None
    category: str
    severity_score: float = Field(ge=0.0, le=1.0, description="0=best, 1=worst")
    threshold_used: str
    is_mock: bool = False
    data_gap: bool = False
    note: Optional[str] = None


class LandscapeIndicators(BaseModel):
    """Raw input indicators for a landscape. All optional — missing = data gap."""
    project_id: str

    # Soil
    soil_loss_rate_t_ha_yr: Optional[float] = None          # t/ha/year
    soil_moisture_pct: Optional[float] = None               # 0–100+
    soil_organic_carbon_g_per_kg: Optional[float] = None    # g/kg
    soil_texture: Optional[str] = None                      # clay/silt/sand

    # Land productivity / vegetation
    land_productivity_index: Optional[float] = None         # 0–1
    ndvi_mean: Optional[float] = None                       # -1 to 1
    evi_mean: Optional[float] = None
    ndvi_trend_5yr: Optional[float] = None                  # positive=improving

    # Topography
    slope_mean_degrees: Optional[float] = None
    flow_accumulation: Optional[float] = None

    # Land cover
    land_cover_change_pct_10yr: Optional[float] = None      # % change
    forest_cover_pct: Optional[float] = None
    bare_soil_pct: Optional[float] = None

    # Climate
    rainfall_mm_annual: Optional[float] = None
    temperature_mean_c: Optional[float] = None
    dry_spell_days_per_year: Optional[float] = None
    drought_frequency_per_decade: Optional[float] = None

    # Proxies (scored 0–1 externally or estimated)
    overgrazing_proxy: Optional[float] = None               # 0=none, 1=severe
    reservoir_sedimentation_proxy: Optional[float] = None

    is_mock: bool = False


class DiagnosticResult(BaseModel):
    project_id: str
    indicators: dict[str, IndicatorResult]
    composite_health_score: float = Field(ge=0.0, le=1.0, description="0=worst, 1=best")
    degradation_severity: str
    data_completeness_pct: float
    data_gaps: list[str]
    is_mock: bool

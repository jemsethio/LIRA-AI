"""
Adaptive Monitoring Agent.
Tracks landscape recovery using remote sensing trend analysis,
before-after/treated-control evidence, and community validation.
Triggers re-prescription alerts when recovery deviates from predictions.
"""

from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel
from typing import Optional
from app.agents.base_agent import BaseAgent
from app.data_adapters.planetary_computer import fetch_sentinel2_ndvi, fetch_ndvi_trend


class RecoveryObservation(BaseModel):
    date: str
    ndvi_observed: Optional[float] = None
    ndvi_predicted: Optional[float] = None
    deviation_pct: Optional[float] = None
    soil_loss_observed: Optional[float] = None
    vegetation_cover_pct: Optional[float] = None
    community_validation_score: Optional[float] = None  # 0–1 from participatory assessment
    field_notes: Optional[str] = None
    data_source: str = "remote_sensing"


class MonitoringAlert(BaseModel):
    alert_type: str   # recovery_below_target / maladaptation_signal / data_gap / re_prescription_needed
    severity: str     # low / medium / high / critical
    message: str
    recommended_action: str
    triggered_at: str


class AdaptiveMonitoringReport(BaseModel):
    project_id: str
    monitoring_period: str
    baseline_ndvi: Optional[float]
    current_ndvi: Optional[float]
    ndvi_change_absolute: Optional[float]
    ndvi_change_pct: Optional[float]
    recovery_trajectory: str    # improving / stable / declining / insufficient_data
    predicted_vs_actual_gap: Optional[float]
    alerts: list[MonitoringAlert]
    observations: list[RecoveryObservation]
    before_after_summary: str
    treated_control_status: str
    melia_indicators: dict[str, float | str]   # MELIA framework indicators
    re_prescription_needed: bool
    next_monitoring_date: str
    confidence: str
    is_mock: bool


class AdaptiveMonitoringAgent(BaseAgent):
    name = "AdaptiveMonitoringAgent"

    def _execute(
        self,
        project_id: str,
        bbox: list[float],
        baseline_date_range: str = "2020-01-01/2021-01-01",
        current_date_range: str = "2023-01-01/2024-01-01",
        predicted_recovery_ndvi: Optional[float] = None,
        community_score: Optional[float] = None,
        **kwargs,
    ) -> AdaptiveMonitoringReport:
        is_mock = kwargs.get("is_mock", False)

        # Fetch baseline and current NDVI from Planetary Computer
        baseline = fetch_sentinel2_ndvi(bbox, date_range=baseline_date_range)
        current  = fetch_sentinel2_ndvi(bbox, date_range=current_date_range)
        trend    = fetch_ndvi_trend(bbox)

        baseline_ndvi = baseline.get("ndvi_mean")
        current_ndvi  = current.get("ndvi_mean")

        ndvi_change_abs = None
        ndvi_change_pct = None
        if baseline_ndvi is not None and current_ndvi is not None:
            ndvi_change_abs = round(current_ndvi - baseline_ndvi, 4)
            ndvi_change_pct = round((current_ndvi - baseline_ndvi) / max(abs(baseline_ndvi), 0.01) * 100, 2)

        # Recovery trajectory
        trend_slope = trend.get("ndvi_trend_slope", 0)
        if trend_slope is None:
            trajectory = "insufficient_data"
        elif trend_slope > 0.005:
            trajectory = "improving"
        elif trend_slope < -0.005:
            trajectory = "declining"
        else:
            trajectory = "stable"

        # Predicted vs actual gap
        pred_actual_gap = None
        if predicted_recovery_ndvi and current_ndvi:
            pred_actual_gap = round(current_ndvi - predicted_recovery_ndvi, 4)

        # MELIA indicators
        melia = {
            "ndvi_baseline": baseline_ndvi or "not_available",
            "ndvi_current":  current_ndvi  or "not_available",
            "ndvi_trend_slope_per_yr": trend_slope,
            "community_acceptance_score": community_score or "not_assessed",
            "re_prescription_triggered": False,
            "data_source": current.get("source", "unknown"),
        }

        # Alerts
        alerts: list[MonitoringAlert] = []
        now = datetime.utcnow().isoformat()

        if trajectory == "declining":
            alerts.append(MonitoringAlert(
                alert_type="re_prescription_needed",
                severity="high",
                message=f"NDVI trend is declining ({trend_slope:.4f}/yr) — restoration trajectory not meeting target.",
                recommended_action="Review intervention implementation; consider adaptive management — possible overgrazing or drought impact.",
                triggered_at=now,
            ))

        if pred_actual_gap is not None and pred_actual_gap < -0.05:
            alerts.append(MonitoringAlert(
                alert_type="recovery_below_target",
                severity="medium",
                message=f"Current NDVI ({current_ndvi:.3f}) is {abs(pred_actual_gap):.3f} below prediction ({predicted_recovery_ndvi:.3f}).",
                recommended_action="Investigate cause: drought, incomplete implementation, pest/livestock pressure, or model error.",
                triggered_at=now,
            ))

        if not baseline.get("is_real") or not current.get("is_real"):
            alerts.append(MonitoringAlert(
                alert_type="data_gap",
                severity="medium",
                message="Real-time satellite data not available — monitoring using mock fallback data.",
                recommended_action="Ensure Planetary Computer connectivity and valid boundary GeoJSON.",
                triggered_at=now,
            ))

        if community_score is not None and community_score < 0.4:
            alerts.append(MonitoringAlert(
                alert_type="maladaptation_signal",
                severity="high",
                message=f"Community acceptance score low ({community_score:.2f}) — risk of non-adoption or maladaptation.",
                recommended_action="Conduct community dialogue; revisit pathway design with participatory process.",
                triggered_at=now,
            ))

        re_prescription = any(a.alert_type in ("re_prescription_needed", "maladaptation_signal") for a in alerts)
        melia["re_prescription_triggered"] = re_prescription

        # Build observation record
        obs = RecoveryObservation(
            date=datetime.utcnow().date().isoformat(),
            ndvi_observed=current_ndvi,
            ndvi_predicted=predicted_recovery_ndvi,
            deviation_pct=ndvi_change_pct,
            community_validation_score=community_score,
            data_source=current.get("source", "unknown"),
        )

        def _f(v, fmt): return format(v, fmt) if v is not None else "N/A"
        sign = "+" if (ndvi_change_abs or 0) >= 0 else ""
        ba_summary = (
            f"Baseline NDVI ({baseline_date_range.split('/')[0][:4]}): {_f(baseline_ndvi, '.3f')}. "
            f"Current NDVI ({current_date_range.split('/')[0][:4]}): {_f(current_ndvi, '.3f')}. "
            f"Change: {sign}{_f(ndvi_change_abs, '.4f')} ({_f(ndvi_change_pct, '.1f')}%)."
        )

        return AdaptiveMonitoringReport(
            project_id=project_id,
            monitoring_period=f"{baseline_date_range.split('/')[0]} → {current_date_range.split('/')[-1]}",
            baseline_ndvi=baseline_ndvi,
            current_ndvi=current_ndvi,
            ndvi_change_absolute=ndvi_change_abs,
            ndvi_change_pct=ndvi_change_pct,
            recovery_trajectory=trajectory,
            predicted_vs_actual_gap=pred_actual_gap,
            alerts=alerts,
            observations=[obs],
            before_after_summary=ba_summary,
            treated_control_status="NEEDS VALIDATION: Control area not yet defined — field team to establish treatment/control pairs",
            melia_indicators=melia,
            re_prescription_needed=re_prescription,
            next_monitoring_date=f"{datetime.utcnow().year + 1}-06-01",
            confidence="low" if not current.get("is_real") else "medium",
            is_mock=not current.get("is_real", False),
        )

    def _evidence_trail(self) -> list[str]:
        return [
            "Sentinel-2 L2A NDVI time series — Microsoft Planetary Computer",
            "Before-after monitoring framework (BACI design)",
            "Community participatory validation scoring",
        ]

    def _assumptions(self) -> list[str]:
        return [
            "ASSUMPTION: NDVI trend computed from growing-season composites — inter-annual rainfall variation affects comparability.",
            "NEEDS VALIDATION: Control (untreated) areas required for rigorous BACI analysis.",
            "ASSUMPTION: Community acceptance score is self-reported — independent validation needed.",
        ]

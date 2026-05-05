"""
account_selector.py - Top account selection for v1 demo.

Selects the daily top 10 after Tool 4 has finalized gap_score and before
Tool 5 generates emails. This keeps OpenRouter usage bounded and matches
the PRD's "Today's Critical 10" workflow.
"""

from typing import Any


LEAD_ANGLE_PRIORITY = {
    "hcahps_care_transition_gap": 0,
    "hcahps_discharge_gap": 1,
    "state_strength_vs_hospital_lag": 2,
}


def _star_sort_value(value: Any) -> int:
    if value is None:
        return 99
    try:
        return int(value)
    except (TypeError, ValueError):
        return 99


def select_top_accounts(
    hospitals: list[dict[str, Any]],
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Return the top high-confidence high/medium urgency accounts."""
    eligible = [
        hospital
        for hospital in hospitals
        if hospital.get("data_confidence") == "high"
        and hospital.get("urgency_tier") in ("high", "medium")
    ]
    ranked = sorted(
        eligible,
        key=lambda hospital: (
            -float(hospital.get("gap_score") or 0),
            LEAD_ANGLE_PRIORITY.get(hospital.get("lead_angle"), 99),
            _star_sort_value(hospital.get("overall_star")),
            _star_sort_value(hospital.get("discharge_info_star")),
            str(hospital.get("facility_name") or ""),
        ),
    )
    return ranked[:limit]

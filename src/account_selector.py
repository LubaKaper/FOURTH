"""
account_selector.py - Top account selection.

Selects the daily top 10 after Tool 4 has finalized gap_score and before
Tool 5 generates outbound. In the tuning phase, low-confidence accounts
can remain visible for review; production auto-send gates are enforced
downstream.
"""

from typing import Any


LEAD_ANGLE_PRIORITY = {
    "baby_vs_mother_contrast": 0,
    "smm_rate_gap": 1,
    "hcahps_care_transition_gap": 2,
    "financial_unrealized": 3,
    "state_strength_vs_hospital_lag": 4,
}


def select_top_accounts(
    hospitals: list[dict[str, Any]],
    limit: int = 10,
    require_high_confidence: bool = False,
) -> list[dict[str, Any]]:
    """Return top accounts by final Gap Score after add_urgency().

    require_high_confidence: set True for production auto-send to hard-block
    low-confidence hospitals at selection time. Default False preserves
    tuning-phase visibility.
    """
    eligible = [
        hospital
        for hospital in hospitals
        if hospital.get("urgency_tier") in ("high", "medium")
        and float(hospital.get("gap_score") or 0) >= 40.0
        and (not require_high_confidence or hospital.get("data_confidence") == "high")
    ]
    ranked = sorted(
        eligible,
        key=lambda hospital: (
            -float(hospital.get("gap_score") or 0),
            LEAD_ANGLE_PRIORITY.get(hospital.get("lead_angle"), 99),
            str(hospital.get("facility_name") or ""),
        ),
    )
    return ranked[:limit]

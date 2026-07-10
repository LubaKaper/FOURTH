"""
gap_calculator.py - Tool 3

Calculates the intermediate ADR Gap Score for one hospital dict.
Tool 3 fills Layer 1 commitment strength and Layer 2 outcome gap
(0-75 total). Tool 4 adds urgency context to produce the final 0-100
score and urgency tier.
"""

from typing import Any


VALID_LEAD_ANGLES = {
    "baby_vs_mother_contrast",
    "hcahps_care_transition_gap",
    "state_strength_vs_hospital_lag",
    "financial_unrealized",
    "smm_rate_gap",
}

BABY_MOTHER_GAP_THRESHOLD = 15.0
STATE_LAG_THRESHOLD = 3.0
SMM_RATE_THRESHOLD = 150.0


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _bool_points(value: Any, points: int) -> int:
    return points if value is True else 0


def _commitment_strength(hospital: dict[str, Any]) -> int:
    points = 0
    points += _bool_points(hospital.get("birthing_friendly"), 15)
    points += _bool_points(hospital.get("mmsm_participant"), 10)
    return min(points, 25)


# Internal ranking proxy: compares the hospital's discharge-info measure
# against the state postpartum visit benchmark. Fine for relative scoring;
# outbound copy must present the two numbers as different measures.
def _discharge_info_lag_points(hospital: dict[str, Any]) -> int:
    discharge_info = _number(hospital.get("discharge_info_pct"))
    state_avg = _number(hospital.get("state_postpartum_avg"))
    if discharge_info is None or state_avg is None:
        return 0

    lag = max(state_avg - discharge_info, 0.0)
    if lag >= 20:
        return 15
    if lag >= 10:
        return 12
    if lag >= STATE_LAG_THRESHOLD:
        return 6
    return 0


def _smm_points(hospital: dict[str, Any]) -> int:
    smm_rate = _number(hospital.get("smm_rate"))
    if smm_rate is None:
        return 0
    if smm_rate >= 175:
        return 20
    if smm_rate >= SMM_RATE_THRESHOLD:
        return 15
    return 0


def _hcahps_points(hospital: dict[str, Any]) -> int:
    star = _number(hospital.get("hcahps_care_transition_star"))
    if star is None:
        return 0
    if star <= 1:
        return 10
    if star == 2:
        return 8
    return 0


def _outcome_gap(hospital: dict[str, Any]) -> int:
    points = (
        _smm_points(hospital)
        + _discharge_info_lag_points(hospital)
        + _hcahps_points(hospital)
        + _bool_points(hospital.get("readmission_penalty"), 5)
    )
    return min(points, 50)


def _has_baby_vs_mother_contrast(hospital: dict[str, Any]) -> bool:
    baby = _number(hospital.get("well_baby_visit_pct"))
    discharge_info = _number(hospital.get("discharge_info_pct"))
    return baby is not None and discharge_info is not None and baby - discharge_info >= BABY_MOTHER_GAP_THRESHOLD


def _has_smm_gap(hospital: dict[str, Any]) -> bool:
    smm_rate = _number(hospital.get("smm_rate"))
    return smm_rate is not None and smm_rate >= SMM_RATE_THRESHOLD


def _has_hcahps_gap(hospital: dict[str, Any]) -> bool:
    star = _number(hospital.get("hcahps_care_transition_star"))
    return star is not None and star < 3


def _has_state_lag(hospital: dict[str, Any]) -> bool:
    discharge_info = _number(hospital.get("discharge_info_pct"))
    state_avg = _number(hospital.get("state_postpartum_avg"))
    return discharge_info is not None and state_avg is not None and state_avg - discharge_info >= STATE_LAG_THRESHOLD


def _lead_angle(hospital: dict[str, Any]) -> str:
    if _has_baby_vs_mother_contrast(hospital):
        return "baby_vs_mother_contrast"
    if _has_smm_gap(hospital):
        return "smm_rate_gap"
    if _has_hcahps_gap(hospital):
        return "hcahps_care_transition_gap"
    if hospital.get("medicaid_extended") is True:
        return "financial_unrealized"
    if _has_state_lag(hospital):
        return "state_strength_vs_hospital_lag"
    return "state_strength_vs_hospital_lag"


def _data_confidence(hospital: dict[str, Any]) -> str:
    has_baby_mother = (
        hospital.get("discharge_info_pct") is not None
        and hospital.get("well_baby_visit_pct") is not None
    )
    has_state_lag = (
        hospital.get("discharge_info_pct") is not None
        and hospital.get("state_postpartum_avg") is not None
    )
    has_hcahps = hospital.get("hcahps_care_transition_star") is not None
    has_smm = hospital.get("smm_rate") is not None
    return "high" if any((has_baby_mother, has_state_lag, has_hcahps, has_smm)) else "low"


def calculate_gap_score(hospital: dict[str, Any]) -> dict[str, Any]:
    commitment_points = _commitment_strength(hospital)
    outcome_points = _outcome_gap(hospital)
    lead_angle = _lead_angle(hospital)

    if lead_angle not in VALID_LEAD_ANGLES:
        raise ValueError(f"Invalid lead_angle: {lead_angle}")

    hospital["gap_score"] = float(commitment_points + outcome_points)
    hospital["lead_angle"] = lead_angle
    hospital["gap_breakdown"] = {
        "commitment_strength": commitment_points,
        "outcome_gap": outcome_points,
        "urgency_context": 0,
    }
    hospital["data_confidence"] = _data_confidence(hospital)
    return hospital

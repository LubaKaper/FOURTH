"""
gap_calculator.py - Tool 3 | Owner: Luba

Calculates the intermediate gap score and lead angle for one hospital dict.
Implements SCHEMA.md v0.2:
- HCAHPS discharge information star: discharge_info_star
- HCAHPS overall star: overall_star
- State benchmark: state_postpartum_visit_rate
"""

from typing import Any


VALID_LEAD_ANGLES = {
    "hcahps_discharge_gap",
    "hcahps_care_transition_gap",
    "state_strength_vs_hospital_lag",
}


def _star_gap_points(star: Any, points_by_star: dict[int, int]) -> int:
    if star is None:
        return 0
    try:
        star_int = int(star)
    except (TypeError, ValueError):
        return 0
    return points_by_star.get(star_int, 0)


def _commitment_strength(hospital: dict[str, Any]) -> int:
    if not hospital.get("birthing_friendly"):
        raise ValueError("birthing_friendly must be True for v1 scoring.")
    if not hospital.get("commitment_tag"):
        raise ValueError("commitment_tag is required for v1 scoring.")
    return 25


def _outcome_gap(hospital: dict[str, Any]) -> int:
    # Max 50. Overall experience is weighted slightly higher because the
    # lead-angle cascade treats it as the broadest patient-experience signal.
    overall_points = _star_gap_points(
        hospital.get("overall_star"),
        {1: 30, 2: 25, 3: 15, 4: 5, 5: 0},
    )
    discharge_points = _star_gap_points(
        hospital.get("discharge_info_star"),
        {1: 20, 2: 15, 3: 8, 4: 3, 5: 0},
    )
    return min(overall_points + discharge_points, 50)


def _lead_angle(hospital: dict[str, Any]) -> str:
    overall = hospital.get("overall_star")
    discharge = hospital.get("discharge_info_star")

    if overall is not None and int(overall) in (1, 2):
        return "hcahps_care_transition_gap"
    if discharge is not None and int(discharge) in (1, 2):
        return "hcahps_discharge_gap"
    return "state_strength_vs_hospital_lag"


def _data_confidence(hospital: dict[str, Any]) -> str:
    if hospital.get("discharge_info_star") is None and hospital.get("overall_star") is None:
        return "low"
    return "high"


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

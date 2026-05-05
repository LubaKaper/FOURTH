import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from account_selector import select_top_accounts


def _hospital(
    facility_id: str,
    gap_score: float,
    lead_angle: str = "state_strength_vs_hospital_lag",
    urgency_tier: str = "high",
    data_confidence: str = "high",
    overall_star: int | None = 3,
    discharge_info_star: int | None = 3,
) -> dict:
    return {
        "facility_id": facility_id,
        "facility_name": f"Hospital {facility_id}",
        "gap_score": gap_score,
        "lead_angle": lead_angle,
        "urgency_tier": urgency_tier,
        "data_confidence": data_confidence,
        "overall_star": overall_star,
        "discharge_info_star": discharge_info_star,
    }


def test_select_top_accounts_limits_to_10():
    hospitals = [_hospital(str(i), float(i)) for i in range(20)]

    selected = select_top_accounts(hospitals)

    assert len(selected) == 10


def test_select_top_accounts_sorts_by_gap_score_descending():
    hospitals = [
        _hospital("low", 50.0),
        _hospital("high", 90.0),
        _hospital("medium", 70.0),
    ]

    selected = select_top_accounts(hospitals, limit=3)

    assert [h["facility_id"] for h in selected] == ["high", "medium", "low"]


def test_select_top_accounts_excludes_low_confidence_and_low_urgency():
    hospitals = [
        _hospital("eligible", 90.0),
        _hospital("low-confidence", 100.0, data_confidence="low"),
        _hospital("low-urgency", 100.0, urgency_tier="low"),
    ]

    selected = select_top_accounts(hospitals, limit=10)

    assert [h["facility_id"] for h in selected] == ["eligible"]


def test_select_top_accounts_uses_lead_angle_tiebreaker():
    hospitals = [
        _hospital("default", 90.0, lead_angle="state_strength_vs_hospital_lag"),
        _hospital("discharge", 90.0, lead_angle="hcahps_discharge_gap"),
        _hospital("care", 90.0, lead_angle="hcahps_care_transition_gap"),
    ]

    selected = select_top_accounts(hospitals, limit=3)

    assert [h["facility_id"] for h in selected] == ["care", "discharge", "default"]


def test_select_top_accounts_uses_star_tiebreakers_then_name():
    hospitals = [
        _hospital("b", 90.0, overall_star=3, discharge_info_star=3),
        _hospital("a", 90.0, overall_star=3, discharge_info_star=3),
        _hospital("worse-overall", 90.0, overall_star=2, discharge_info_star=5),
        _hospital("worse-discharge", 90.0, overall_star=3, discharge_info_star=1),
    ]
    hospitals[0]["facility_name"] = "Beta"
    hospitals[1]["facility_name"] = "Alpha"

    selected = select_top_accounts(hospitals, limit=4)

    assert [h["facility_id"] for h in selected] == [
        "worse-overall",
        "worse-discharge",
        "a",
        "b",
    ]

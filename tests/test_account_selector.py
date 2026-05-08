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
) -> dict:
    return {
        "facility_id": facility_id,
        "facility_name": f"Hospital {facility_id}",
        "gap_score": gap_score,
        "lead_angle": lead_angle,
        "urgency_tier": urgency_tier,
        "data_confidence": data_confidence,
        "postpartum_visit_pct": 61.0,
        "well_baby_visit_pct": 94.0,
    }


def test_select_top_accounts_limits_to_10():
    hospitals = [_hospital(str(i), float(i + 40)) for i in range(20)]

    selected = select_top_accounts(hospitals)

    assert len(selected) == 10


def test_select_top_accounts_sorts_by_final_gap_score_descending():
    hospitals = [
        _hospital("low", 50.0),
        _hospital("high", 90.0),
        _hospital("medium", 70.0),
    ]

    selected = select_top_accounts(hospitals, limit=3)

    assert [h["facility_id"] for h in selected] == ["high", "medium", "low"]


def test_select_top_accounts_excludes_below_threshold_and_low_urgency():
    hospitals = [
        _hospital("eligible", 90.0),
        _hospital("below-threshold", 39.0, urgency_tier="low"),
        _hospital("low-urgency", 100.0, urgency_tier="low"),
    ]

    selected = select_top_accounts(hospitals, limit=10)

    assert [h["facility_id"] for h in selected] == ["eligible"]


def test_select_top_accounts_keeps_low_confidence_visible_during_tuning():
    hospitals = [
        _hospital("high-confidence", 80.0, data_confidence="high"),
        _hospital("low-confidence", 90.0, data_confidence="low"),
    ]

    selected = select_top_accounts(hospitals, limit=10)

    assert [h["facility_id"] for h in selected] == ["low-confidence", "high-confidence"]


def test_select_top_accounts_uses_adr_lead_angle_tiebreaker():
    hospitals = [
        _hospital("state", 90.0, lead_angle="state_strength_vs_hospital_lag"),
        _hospital("financial", 90.0, lead_angle="financial_unrealized"),
        _hospital("hcahps", 90.0, lead_angle="hcahps_care_transition_gap"),
        _hospital("smm", 90.0, lead_angle="smm_rate_gap"),
        _hospital("baby", 90.0, lead_angle="baby_vs_mother_contrast"),
    ]

    selected = select_top_accounts(hospitals, limit=5)

    assert [h["facility_id"] for h in selected] == [
        "baby",
        "smm",
        "hcahps",
        "financial",
        "state",
    ]

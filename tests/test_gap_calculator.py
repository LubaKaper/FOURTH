import copy
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tests.fixtures import HIGH_GAP, LOW_GAP, MEDIUM_GAP, NO_COMMITMENT, NULL_DATA
from gap_calculator import calculate_gap_score


VALID_LEAD_ANGLES = {
    "hcahps_discharge_gap",
    "hcahps_care_transition_gap",
    "state_strength_vs_hospital_lag",
}


def _score(fixture: dict) -> dict:
    return calculate_gap_score(copy.deepcopy(fixture))


def test_returns_required_gap_fields():
    hospital = _score(HIGH_GAP)

    assert "gap_score" in hospital
    assert "lead_angle" in hospital
    assert "gap_breakdown" in hospital
    assert "data_confidence" in hospital


def test_intermediate_score_is_float_within_range():
    for fixture in (HIGH_GAP, MEDIUM_GAP, LOW_GAP, NULL_DATA):
        hospital = _score(fixture)

        assert isinstance(hospital["gap_score"], float)
        assert 0.0 <= hospital["gap_score"] <= 75.0


def test_lead_angle_uses_v02_allowed_values():
    for fixture in (HIGH_GAP, MEDIUM_GAP, LOW_GAP, NULL_DATA):
        hospital = _score(fixture)

        assert hospital["lead_angle"] in VALID_LEAD_ANGLES


def test_lead_angle_priority_overall_star_before_discharge_info():
    hospital = _score(HIGH_GAP)

    assert hospital["lead_angle"] == "hcahps_care_transition_gap"


def test_lead_angle_uses_discharge_gap_when_overall_not_low():
    hospital = _score(MEDIUM_GAP)

    assert hospital["lead_angle"] == "hcahps_discharge_gap"


def test_lead_angle_defaults_to_state_strength():
    hospital = _score(LOW_GAP)

    assert hospital["lead_angle"] == "state_strength_vs_hospital_lag"


def test_gap_breakdown_structure():
    hospital = _score(HIGH_GAP)
    breakdown = hospital["gap_breakdown"]

    assert set(breakdown) == {"commitment_strength", "outcome_gap", "urgency_context"}
    assert 0 <= breakdown["commitment_strength"] <= 25
    assert 0 <= breakdown["outcome_gap"] <= 50
    assert breakdown["urgency_context"] == 0


def test_high_gap_scores_above_low_gap():
    assert _score(HIGH_GAP)["gap_score"] > _score(LOW_GAP)["gap_score"]


def test_data_confidence_low_only_when_both_hcahps_stars_missing():
    assert _score(NULL_DATA)["data_confidence"] == "low"
    assert _score(HIGH_GAP)["data_confidence"] == "high"


def test_null_hcahps_data_does_not_crash():
    hospital = _score(NULL_DATA)

    assert isinstance(hospital["gap_score"], float)


def test_no_commitment_raises_value_error():
    with pytest.raises(ValueError, match="birthing_friendly"):
        _score(NO_COMMITMENT)

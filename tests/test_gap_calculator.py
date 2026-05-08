import copy
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tests.fixtures import FINANCIAL_ONLY, HIGH_GAP, LOW_GAP, MEDIUM_GAP, NO_COMMITMENT, NULL_DATA, SMM_ONLY
from gap_calculator import calculate_gap_score


VALID_LEAD_ANGLES = {
    "baby_vs_mother_contrast",
    "hcahps_care_transition_gap",
    "state_strength_vs_hospital_lag",
    "financial_unrealized",
    "smm_rate_gap",
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
    for fixture in (HIGH_GAP, MEDIUM_GAP, LOW_GAP, NULL_DATA, NO_COMMITMENT):
        hospital = _score(fixture)

        assert isinstance(hospital["gap_score"], float)
        assert 0.0 <= hospital["gap_score"] <= 75.0


def test_lead_angle_uses_adr_allowed_values():
    for fixture in (HIGH_GAP, MEDIUM_GAP, LOW_GAP, NULL_DATA, NO_COMMITMENT):
        hospital = _score(fixture)

        assert hospital["lead_angle"] in VALID_LEAD_ANGLES


def test_lead_angle_prioritizes_baby_vs_mother_contrast():
    hospital = _score(HIGH_GAP)

    assert hospital["lead_angle"] == "baby_vs_mother_contrast"


def test_lead_angle_uses_hcahps_when_no_baby_vs_mother_contrast():
    hospital = _score(MEDIUM_GAP)

    assert hospital["lead_angle"] == "hcahps_care_transition_gap"


def test_lead_angle_can_use_state_strength_gap():
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


def test_null_outcome_data_scores_zero_for_missing_layer_and_continues():
    hospital = _score(NULL_DATA)

    assert isinstance(hospital["gap_score"], float)
    assert hospital["data_confidence"] == "low"
    assert hospital["gap_breakdown"]["outcome_gap"] == 0


def test_no_commitment_does_not_crash_and_scores_zero_commitment_strength():
    hospital = _score(NO_COMMITMENT)

    assert isinstance(hospital["gap_score"], float)
    assert hospital["gap_breakdown"]["commitment_strength"] == 0


# ── Task 1: Lead angle diversity — all five angles exercised ─────────────────

def test_lead_angle_selects_smm_rate_gap_when_smm_elevated_and_no_baby_mother_data():
    """smm_rate_gap is selected when SMM is elevated and well_baby_visit_pct is None."""
    hospital = _score(SMM_ONLY)

    assert hospital["lead_angle"] == "smm_rate_gap"


def test_lead_angle_selects_financial_unrealized_when_medicaid_and_no_stronger_signal():
    """financial_unrealized is selected when Medicaid is extended and no higher-priority signal exists."""
    hospital = _score(FINANCIAL_ONLY)

    assert hospital["lead_angle"] == "financial_unrealized"


def test_baby_vs_mother_contrast_takes_priority_over_smm_when_both_qualify():
    """baby_vs_mother_contrast wins over smm_rate_gap when both signals are present."""
    hospital = _score(HIGH_GAP)
    # HIGH_GAP has well_baby=94, postpartum=61 (gap=33) AND smm_rate=180 (elevated)
    # baby_vs_mother_contrast must be chosen

    assert hospital["lead_angle"] == "baby_vs_mother_contrast"


def test_smm_rate_gap_takes_priority_over_hcahps_when_both_qualify():
    """smm_rate_gap wins over hcahps_care_transition_gap when both signals are present."""
    import copy
    hospital_data = copy.deepcopy(SMM_ONLY)
    hospital_data["hcahps_care_transition_star"] = 2  # now both SMM and HCAHPS qualify
    hospital = _score(hospital_data)

    assert hospital["lead_angle"] == "smm_rate_gap"


def test_hcahps_gap_takes_priority_over_financial_when_both_qualify():
    """hcahps_care_transition_gap wins over financial_unrealized when both signals are present."""
    import copy
    hospital_data = copy.deepcopy(FINANCIAL_ONLY)
    hospital_data["hcahps_care_transition_star"] = 2  # add HCAHPS gap
    hospital_data["smm_rate"] = None
    hospital = _score(hospital_data)

    assert hospital["lead_angle"] == "hcahps_care_transition_gap"

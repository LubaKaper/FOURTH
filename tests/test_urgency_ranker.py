import copy
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tests.fixtures import HIGH_GAP, LOW_GAP, MEDIUM_GAP
from gap_calculator import calculate_gap_score
from urgency_ranker import add_urgency


VALID_TIERS = {"high", "medium", "low"}
VALID_FLAGS = {"🔴 Act this week", "🟡 Monitor", "🟢 Not ready"}


def _scored(fixture: dict) -> dict:
    return calculate_gap_score(copy.deepcopy(fixture))


def test_final_score_is_float_within_range():
    for fixture in (HIGH_GAP, MEDIUM_GAP, LOW_GAP):
        hospital = add_urgency(_scored(fixture))

        assert isinstance(hospital["gap_score"], float)
        assert 0.0 <= hospital["gap_score"] <= 100.0


def test_urgency_tier_allowed_values():
    for fixture in (HIGH_GAP, MEDIUM_GAP, LOW_GAP):
        hospital = add_urgency(_scored(fixture))

        assert hospital["urgency_tier"] in VALID_TIERS


def test_urgency_flag_exact_values():
    for fixture in (HIGH_GAP, MEDIUM_GAP, LOW_GAP):
        hospital = add_urgency(_scored(fixture))

        assert hospital["urgency_flag"] in VALID_FLAGS


def test_expected_tiers_for_shared_fixtures():
    assert add_urgency(_scored(HIGH_GAP))["urgency_tier"] == "high"
    assert add_urgency(_scored(MEDIUM_GAP))["urgency_tier"] == "medium"
    assert add_urgency(_scored(LOW_GAP))["urgency_tier"] == "low"


def test_urgency_context_filled_within_range():
    hospital = add_urgency(_scored(HIGH_GAP))

    assert 0 <= hospital["gap_breakdown"]["urgency_context"] <= 25


def test_final_score_adds_urgency_context_to_intermediate_score():
    intermediate = _scored(HIGH_GAP)
    final = add_urgency(copy.deepcopy(intermediate))

    assert final["gap_score"] == intermediate["gap_score"] + final["gap_breakdown"]["urgency_context"]


def test_adds_schema_v02_urgency_fields():
    hospital = add_urgency(_scored(HIGH_GAP))

    assert "medicaid_extended" in hospital
    assert "racial_disparity_flag" in hospital


def test_adds_urgency_context_fields_when_missing_from_upstream():
    hospital = _scored(HIGH_GAP)
    hospital.pop("medicaid_extended")
    hospital.pop("racial_disparity_flag")

    ranked = add_urgency(hospital)

    assert ranked["medicaid_extended"] is True
    assert ranked["racial_disparity_flag"] is True
    assert ranked["gap_breakdown"]["urgency_context"] == 25


def test_missing_gap_score_raises_key_error():
    with pytest.raises(KeyError):
        add_urgency({"facility_id": "330000", "gap_breakdown": {}})


def test_missing_gap_breakdown_raises_key_error():
    with pytest.raises(KeyError):
        add_urgency({"facility_id": "330000", "gap_score": 10.0})

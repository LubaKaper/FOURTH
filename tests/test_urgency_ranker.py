import copy
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tests.fixtures import HIGH_GAP, LOW_GAP, MEDIUM_GAP, NULL_DATA
from gap_calculator import calculate_gap_score
from urgency_ranker import add_urgency


VALID_TIERS = {"high", "medium", "low"}
VALID_FLAGS = {"🔴 Act this week", "🟡 Monitor", "🟢 Not ready"}


def _scored(fixture: dict) -> dict:
    return calculate_gap_score(copy.deepcopy(fixture))


def _final(fixture: dict) -> dict:
    return add_urgency(_scored(fixture))


def test_final_score_is_float_within_range():
    for fixture in (HIGH_GAP, MEDIUM_GAP, LOW_GAP, NULL_DATA):
        hospital = _final(fixture)

        assert isinstance(hospital["gap_score"], float)
        assert 0.0 <= hospital["gap_score"] <= 100.0


def test_urgency_tier_allowed_values():
    for fixture in (HIGH_GAP, MEDIUM_GAP, LOW_GAP, NULL_DATA):
        hospital = _final(fixture)

        assert hospital["urgency_tier"] in VALID_TIERS


def test_urgency_flag_exact_values():
    for fixture in (HIGH_GAP, MEDIUM_GAP, LOW_GAP, NULL_DATA):
        hospital = _final(fixture)

        assert hospital["urgency_flag"] in VALID_FLAGS


def test_expected_tiers_use_final_gap_score_after_add_urgency():
    high = _final(HIGH_GAP)
    medium = _final(MEDIUM_GAP)
    low = _final(LOW_GAP)

    assert high["gap_score"] >= 70
    assert high["urgency_tier"] == "high"

    assert 40 <= medium["gap_score"] < 70
    assert medium["urgency_tier"] == "medium"

    assert low["gap_score"] < 40
    assert low["urgency_tier"] == "low"


def test_urgency_context_filled_within_range():
    hospital = _final(HIGH_GAP)

    assert 0 <= hospital["gap_breakdown"]["urgency_context"] <= 25


def test_final_score_adds_urgency_context_to_intermediate_score():
    intermediate = _scored(HIGH_GAP)
    final = add_urgency(copy.deepcopy(intermediate))

    assert final["gap_score"] == intermediate["gap_score"] + final["gap_breakdown"]["urgency_context"]


def test_null_urgency_context_scores_zero_and_continues():
    hospital = _final(NULL_DATA)

    assert hospital["data_confidence"] == "low"
    assert hospital["gap_breakdown"]["urgency_context"] == 0
    assert isinstance(hospital["gap_score"], float)


def test_missing_gap_score_raises_key_error():
    with pytest.raises(KeyError):
        add_urgency({"facility_id": "330000", "gap_breakdown": {}})


def test_missing_gap_breakdown_raises_key_error():
    with pytest.raises(KeyError):
        add_urgency({"facility_id": "330000", "gap_score": 10.0})

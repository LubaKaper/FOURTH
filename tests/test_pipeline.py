"""Schema-facing pipeline handoff tests for Fourth.

These tests verify the ADR contracts across Tools 3-5 using deterministic
fixtures. Real-data validation remains the manual agent run.
"""

import copy
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tests.fixtures import HIGH_GAP, LOW_GAP, MEDIUM_GAP, NO_COMMITMENT, NULL_DATA

from account_selector import select_top_accounts
from gap_calculator import calculate_gap_score
from outbound_generator import generate_outbound_email
from urgency_ranker import add_urgency


@pytest.fixture
def fresh_hospitals() -> list[dict]:
    return [
        copy.deepcopy(HIGH_GAP),
        copy.deepcopy(MEDIUM_GAP),
        copy.deepcopy(LOW_GAP),
        copy.deepcopy(NULL_DATA),
        copy.deepcopy(NO_COMMITMENT),
    ]


def _run_through_tool_4(hospitals: list[dict]) -> list[dict]:
    after_3 = [calculate_gap_score(h) for h in hospitals]
    return [add_urgency(h) for h in after_3]


def test_dict_fields_only_grow_through_pipeline(fresh_hospitals):
    initial_keys = [set(h.keys()) for h in fresh_hospitals]

    after_3 = [calculate_gap_score(copy.deepcopy(h)) for h in fresh_hospitals]
    for original, scored in zip(initial_keys, after_3):
        assert original.issubset(scored.keys()), "Tool 3 dropped or renamed a field"

    pre_tool_4_keys = [set(h.keys()) for h in after_3]
    after_4 = [add_urgency(h) for h in after_3]
    for pre, post in zip(pre_tool_4_keys, after_4):
        assert pre.issubset(post.keys()), "Tool 4 dropped or renamed a field"


def test_tool_3_gap_score_within_intermediate_range(fresh_hospitals):
    after_3 = [calculate_gap_score(h) for h in fresh_hospitals]
    for h in after_3:
        assert isinstance(h["gap_score"], float)
        assert 0.0 <= h["gap_score"] <= 75.0


def test_tool_4_thresholds_use_final_gap_score_after_add_urgency(fresh_hospitals):
    after_4 = _run_through_tool_4(fresh_hospitals)
    by_id = {h["facility_id"]: h for h in after_4}

    assert by_id[HIGH_GAP["facility_id"]]["gap_score"] >= 70
    assert by_id[HIGH_GAP["facility_id"]]["urgency_tier"] == "high"

    assert 40 <= by_id[MEDIUM_GAP["facility_id"]]["gap_score"] < 70
    assert by_id[MEDIUM_GAP["facility_id"]]["urgency_tier"] == "medium"

    assert by_id[LOW_GAP["facility_id"]]["gap_score"] < 40
    assert by_id[LOW_GAP["facility_id"]]["urgency_tier"] == "low"


def test_low_tier_hospitals_stop_before_outbound(fresh_hospitals):
    after_4 = _run_through_tool_4(fresh_hospitals)
    selected = select_top_accounts(after_4)

    assert all(h["urgency_tier"] != "low" for h in selected)
    assert all(h["gap_score"] >= 40 for h in selected)


def test_outbound_objects_include_audit_trail_fields(fresh_hospitals):
    after_4 = _run_through_tool_4(fresh_hospitals)
    selected = select_top_accounts(after_4)
    emails = generate_outbound_email(selected)

    for email in emails:
        assert email["product"] == "Babyscripts"
        assert email["lead_angle"]
        assert isinstance(email["gap_score"], float)
        assert email["status"] == "pending_review"
        assert email["sent_at"] is None


def test_null_data_continues_through_tool_4_with_low_confidence(fresh_hospitals):
    null_id = NULL_DATA["facility_id"]
    after_4 = _run_through_tool_4(fresh_hospitals)

    null_after_4 = [h for h in after_4 if h["facility_id"] == null_id]
    assert len(null_after_4) == 1
    assert null_after_4[0]["data_confidence"] == "low"
    assert isinstance(null_after_4[0]["gap_score"], float)


def test_no_commitment_continues_with_zero_commitment_strength():
    hospital = add_urgency(calculate_gap_score(copy.deepcopy(NO_COMMITMENT)))

    assert hospital["gap_breakdown"]["commitment_strength"] == 0
    assert isinstance(hospital["gap_score"], float)

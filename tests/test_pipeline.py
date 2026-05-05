"""End-to-end pipeline integration tests.

Runs all seven tools against deterministic fixtures and verifies dict
shape contracts at each stage. Real-data validation lives in the
manual agent run, not here. See issue #12 for tool mutation asymmetry
that requires deepcopy at fixture entry.
"""
import copy
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tests.fixtures import HIGH_GAP, LOW_GAP, MEDIUM_GAP, NO_COMMITMENT, NULL_DATA

from account_selector import select_top_accounts
from dashboard_generator import generate_dashboard
from gap_calculator import calculate_gap_score
from human_checkpoint import display_checkpoint
from outbound_generator import generate_outbound_email
from urgency_ranker import add_urgency


@pytest.fixture
def fresh_hospitals() -> list[dict]:
    """Deep-copied hospital fixtures.

    Required because Tools 3 and 4 mutate input dicts in place. See
    https://github.com/PMAIGURU2026/ECHO/issues/12 for the contract
    inconsistency this works around.
    """
    return [
        copy.deepcopy(HIGH_GAP),
        copy.deepcopy(MEDIUM_GAP),
        copy.deepcopy(LOW_GAP),
        copy.deepcopy(NULL_DATA),
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


def test_tool_4_gap_score_within_final_range(fresh_hospitals):
    after_4 = _run_through_tool_4(fresh_hospitals)
    for h in after_4:
        assert isinstance(h["gap_score"], float)
        assert 0.0 <= h["gap_score"] <= 100.0


def test_emails_only_for_high_or_medium_high_confidence(fresh_hospitals):
    after_4 = _run_through_tool_4(fresh_hospitals)
    selected = select_top_accounts(after_4)
    emails = generate_outbound_email(selected)

    email_ids = {e["facility_id"] for e in emails}

    for h in after_4:
        eligible = (
            h["urgency_tier"] in ("high", "medium")
            and h["data_confidence"] == "high"
            and h in selected
        )
        if eligible:
            assert h["facility_id"] in email_ids, (
                f"{h['facility_name']} eligible but no email generated"
            )
        else:
            assert h["facility_id"] not in email_ids, (
                f"{h['facility_name']} ineligible but received an email"
            )


def test_null_data_retained_through_tool_4_then_skipped_by_tool_5(fresh_hospitals):
    null_id = NULL_DATA["facility_id"]
    after_4 = _run_through_tool_4(fresh_hospitals)

    null_after_4 = [h for h in after_4 if h["facility_id"] == null_id]
    assert len(null_after_4) == 1, "NULL_DATA hospital was dropped before Tool 5"
    assert null_after_4[0]["data_confidence"] == "low"

    selected = select_top_accounts(after_4)
    emails = generate_outbound_email(selected)
    assert all(e["facility_id"] != null_id for e in emails), (
        "NULL_DATA hospital received an email despite low data_confidence"
    )


def test_top_account_selection_caps_tool_5_input_to_10():
    hospitals = []
    for index in range(15):
        hospital = copy.deepcopy(HIGH_GAP)
        hospital["facility_id"] = f"top-{index:02d}"
        hospital["facility_name"] = f"Top Hospital {index:02d}"
        hospital["overall_star"] = 1
        hospital["discharge_info_star"] = 1
        hospital["gap_score"] = 100.0 - index
        hospital["urgency_tier"] = "high"
        hospital["data_confidence"] = "high"
        hospital["lead_angle"] = "hcahps_care_transition_gap"
        hospitals.append(hospital)

    selected = select_top_accounts(hospitals)
    emails = generate_outbound_email(selected)

    assert len(selected) == 10
    assert len(emails) == 10
    assert [email["facility_id"] for email in emails] == [
        hospital["facility_id"] for hospital in selected
    ]


def test_human_checkpoint_returns_summary_string(fresh_hospitals):
    after_4 = _run_through_tool_4(fresh_hospitals)
    selected = select_top_accounts(after_4)
    emails = generate_outbound_email(selected)

    summary = display_checkpoint(selected, emails)

    assert isinstance(summary, str)
    assert len(summary) > 0


def test_full_pipeline_generates_dashboard_html(fresh_hospitals, tmp_path):
    after_4 = _run_through_tool_4(fresh_hospitals)
    selected = select_top_accounts(after_4)
    emails = generate_outbound_email(selected)

    output_path = tmp_path / "test_dashboard.html"
    generate_dashboard(selected, emails, str(output_path))

    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_no_commitment_fixture_raises_in_tool_3_per_v2_guard():
    """NO_COMMITMENT (birthing_friendly=False, commitment_tag=None) is the
    v2 silent-gap guard fixture. v1 Tool 3 must reject it with ValueError."""
    fixture = copy.deepcopy(NO_COMMITMENT)
    with pytest.raises(ValueError):
        calculate_gap_score(fixture)

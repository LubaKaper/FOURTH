"""
Schema-facing tests for Tool 5 — outbound_generator.

These tests encode the ADR Handoff 4 production contract. They are
expected to fail until outbound_generator.py is migrated from the legacy
three-variant tuning object.
"""

import copy
import logging
import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.gap_calculator import calculate_gap_score
from src.outbound_generator import _email_body, _openrouter_prompt, _validate_llm_body, generate_outbound_email
from src.urgency_ranker import add_urgency
from tests.fixtures import FINANCIAL_ONLY, HIGH_GAP, LOW_GAP, MEDIUM_GAP, NULL_DATA, SMM_ONLY


REQUIRED_EMAIL_KEYS = {
    "facility_id",
    "facility_name",
    "recipient_role",
    "subject",
    "email_body",
    "product",
    "lead_angle",
    "gap_score",
    "urgency_tier",
    "sent_at",
    "status",
}

VALID_RECIPIENT_ROLES = {"CMO", "VP Patient Experience"}
VALID_STATUSES = {"pending_review", "ready_to_send"}


def _ready(fixture: dict) -> dict:
    return add_urgency(calculate_gap_score(copy.deepcopy(fixture)))


def test_low_urgency_or_below_threshold_skipped():
    email = generate_outbound_email([_ready(LOW_GAP)])

    assert email == []


def test_high_and_medium_accounts_get_send_contract_objects():
    emails = generate_outbound_email([_ready(HIGH_GAP), _ready(MEDIUM_GAP)])

    assert len(emails) == 2
    for email in emails:
        missing = REQUIRED_EMAIL_KEYS - set(email)
        assert not missing, f"email missing keys: {missing}"


def test_email_contract_copies_audit_fields_from_hospital():
    hospital = _ready(HIGH_GAP)
    email = generate_outbound_email([hospital])[0]

    assert email["facility_id"] == hospital["facility_id"]
    assert email["facility_name"] == hospital["facility_name"]
    assert email["lead_angle"] == hospital["lead_angle"]
    assert email["gap_score"] == hospital["gap_score"]
    assert email["urgency_tier"] == hospital["urgency_tier"]


def test_email_contract_uses_babyscripts_product():
    email = generate_outbound_email([_ready(HIGH_GAP)])[0]

    assert email["product"] == "Babyscripts"
    assert "Babyscripts" in email["email_body"]


def test_recipient_role_is_cmo_or_vp_patient_experience():
    emails = generate_outbound_email([_ready(HIGH_GAP), _ready(MEDIUM_GAP)])

    for email in emails:
        assert email["recipient_role"] in VALID_RECIPIENT_ROLES


def test_tuning_phase_status_is_pending_review():
    email = generate_outbound_email([_ready(HIGH_GAP)])[0]

    assert email["status"] in VALID_STATUSES
    assert email["status"] == "pending_review"
    assert email["sent_at"] is None


def test_low_confidence_accounts_do_not_auto_send():
    hospital = _ready(NULL_DATA)
    emails = generate_outbound_email([hospital])

    assert hospital["data_confidence"] == "low"
    assert emails == []


def test_legacy_three_variant_fields_are_not_part_of_send_contract():
    email = generate_outbound_email([_ready(HIGH_GAP)])[0]

    legacy_keys = {
        "to_role",
        "body_moral",
        "body_clinical",
        "body_financial",
        "lead_angle_used",
        "generation_method",
    }
    assert not legacy_keys & set(email)


def test_missing_tool_4_state_raises_value_error():
    incomplete = copy.deepcopy(HIGH_GAP)
    with pytest.raises(ValueError, match="urgency_tier"):
        generate_outbound_email([incomplete])


def test_llm_validation_rejects_gap_score_labeled_as_hcahps_score():
    hospital = _ready(HIGH_GAP)
    body = (
        f"Hi,\n\n{hospital['facility_name']} earned the CMS Birthing-Friendly designation. "
        f"Your HCAHPS care transition score is {hospital['gap_score']}, which suggests a gap. "
        "Babyscripts can help with remote postpartum monitoring. Hospitals using Babyscripts "
        "saw patients become 2x more likely to complete their 30-day postpartum visit.\n\n"
        "Open to a short conversation?"
    )

    with pytest.raises(ValueError, match="mislabeled gap_score"):
        _validate_llm_body(hospital, body)


# ── Task 3: Claim validation ──────────────────────────────────────────────────

def _valid_body(hospital: dict, data_line: str) -> str:
    """Build a minimal valid email body with a swappable data claim line."""
    return (
        f"Hi,\n\n{hospital['facility_name']} earned the CMS Birthing-Friendly designation. "
        f"{data_line} "
        "Babyscripts supports remote postpartum monitoring. Hospitals using Babyscripts saw "
        "patients become 2x more likely to complete their 30-day postpartum visit.\n\n"
        "Open to a short conversation?"
    )


def test_fabricated_percentage_not_in_hospital_dict_fails_validation():
    """A percentage with no match within 1 point of any hospital outcome field is rejected."""
    hospital = _ready(HIGH_GAP)
    # HIGH_GAP: postpartum=61.0, well_baby=94.0, state_avg=82.4
    # 55% is > 1 point from all three
    body = _valid_body(hospital, "Your postpartum visit completion rate is 55%.")

    with pytest.raises(ValueError, match="ungrounded percentage"):
        _validate_llm_body(hospital, body)


def test_percentage_off_by_more_than_one_point_fails_validation():
    """A percentage more than 1 point from the nearest hospital outcome field is rejected."""
    hospital = _ready(HIGH_GAP)
    # postpartum=61.0 — 65% is 4 points off; not within 1 of any field
    body = _valid_body(hospital, "Your postpartum visit completion rate is 65%.")

    with pytest.raises(ValueError, match="ungrounded percentage"):
        _validate_llm_body(hospital, body)


def test_percentage_within_one_point_of_hospital_field_passes_validation():
    """A percentage within 1 point of a hospital outcome field passes validation."""
    hospital = _ready(HIGH_GAP)
    # 61% matches postpartum_visit_pct=61.0 exactly; 82% matches state_postpartum_avg=82.4 within 1 point
    body = _valid_body(
        hospital,
        "Your postpartum visit completion rate is 61%, below the state average of 82%.",
    )

    result = _validate_llm_body(hospital, body)
    assert result


def test_fabricated_star_rating_not_in_hospital_dict_fails_validation():
    """A star rating not matching any HCAHPS field exactly is rejected."""
    hospital = _ready(HIGH_GAP)
    # HIGH_GAP: hcahps_care_transition_star=2, hcahps_overall_star=2 — citing 3/5 should fail
    body = _valid_body(hospital, "With a care transition rating of 3/5 stars, there is room to improve.")

    with pytest.raises(ValueError, match="ungrounded star rating"):
        _validate_llm_body(hospital, body)


def test_star_rating_matching_hcahps_field_exactly_passes_validation():
    """A star rating matching an HCAHPS field exactly passes validation."""
    hospital = _ready(HIGH_GAP)
    # hcahps_care_transition_star=2 — citing 2/5 stars should pass
    body = _valid_body(hospital, "With a care transition rating of 2/5 stars, there is room to improve.")

    result = _validate_llm_body(hospital, body)
    assert result


def test_star_rating_when_hcahps_fields_are_none_fails_validation():
    """Any star rating cited when both HCAHPS fields are None in the hospital dict is rejected."""
    hospital = _ready(NULL_DATA)
    # NULL_DATA: hcahps_care_transition_star=None, hcahps_overall_star=None
    # No valid star value exists — any citation is fabricated
    body = _valid_body(hospital, "With a care transition rating of 2/5 stars, there is room to improve.")

    with pytest.raises(ValueError, match="ungrounded star rating"):
        _validate_llm_body(hospital, body)


# ── Task 2: OpenRouter failure handling ──────────────────────────────────────

def test_openrouter_prompt_states_exact_proof_point_as_required():
    """The proof point sentence must appear as an explicit rule, not only in the facts dict."""
    hospital = _ready(HIGH_GAP)
    prompt = _openrouter_prompt(hospital)
    rules_section = prompt.split("Facts:")[0]

    assert "2x more likely to complete their 30-day postpartum visit" in rules_section, (
        "Proof point sentence must be explicitly required in the rules section, "
        "not only present as a value in the facts dict."
    )


# ── angle_reason field ───────────────────────────────────────────────────────

def test_email_object_includes_angle_reason_field():
    """Email object must include a deterministic angle_reason string."""
    email = generate_outbound_email([_ready(HIGH_GAP)])[0]

    assert "angle_reason" in email
    assert isinstance(email["angle_reason"], str)
    assert len(email["angle_reason"]) > 0


def test_angle_reason_for_hcahps_gap_includes_star_rating():
    """angle_reason for hcahps_care_transition_gap must cite the actual star rating."""
    hospital = _ready(MEDIUM_GAP)
    assert hospital["lead_angle"] == "hcahps_care_transition_gap"
    email = generate_outbound_email([hospital])[0]

    assert str(MEDIUM_GAP["hcahps_care_transition_star"]) in email["angle_reason"]
    assert "star" in email["angle_reason"].lower()


def test_angle_reason_for_baby_vs_mother_includes_both_visit_pcts():
    """angle_reason for baby_vs_mother_contrast must cite both visit percentages."""
    hospital = _ready(HIGH_GAP)
    assert hospital["lead_angle"] == "baby_vs_mother_contrast"
    email = generate_outbound_email([hospital])[0]

    assert str(int(HIGH_GAP["well_baby_visit_pct"])) in email["angle_reason"]
    assert str(int(HIGH_GAP["postpartum_visit_pct"])) in email["angle_reason"]


# ── Task 4: Source grounding audit ───────────────────────────────────────────

def test_financial_unrealized_template_uses_hospital_state_not_hardcoded_ny():
    """financial_unrealized email body must reference the hospital's state, not hardcoded 'NY'."""
    hospital = copy.deepcopy(FINANCIAL_ONLY)
    hospital["lead_angle"] = "financial_unrealized"
    hospital["state"] = "TX"

    body = _email_body(hospital)

    assert "NY" not in body, "Template must not hardcode 'NY' — use the hospital's state field"
    assert "TX" in body, "Template must reference the hospital's actual state"


def test_openrouter_prompt_includes_well_baby_pct_for_baby_vs_mother_lead_angle():
    """When lead angle is baby_vs_mother_contrast, the prompt facts must include well_baby_visit_pct."""
    hospital = _ready(HIGH_GAP)
    assert hospital["lead_angle"] == "baby_vs_mother_contrast"

    prompt = _openrouter_prompt(hospital)

    assert "well_baby_visit_pct" in prompt, (
        "LLM cannot write the baby-vs-mother hook without well_baby_visit_pct in the facts"
    )
    assert str(int(hospital["well_baby_visit_pct"])) in prompt


def test_openrouter_prompt_includes_smm_rate_for_smm_rate_gap_lead_angle():
    """When lead angle is smm_rate_gap, the prompt facts must include the actual smm_rate value."""
    hospital = _ready(SMM_ONLY)
    assert hospital["lead_angle"] == "smm_rate_gap"

    prompt = _openrouter_prompt(hospital)

    assert "smm_rate" in prompt, (
        "LLM cannot ground an SMM claim without smm_rate in the facts"
    )
    assert str(int(hospital["smm_rate"])) in prompt


def test_generate_outbound_email_logs_fallback_summary_by_hospital_name(caplog):
    """After batch generation, a dedicated summary log names each hospital that fell back and why."""
    hospital = _ready(HIGH_GAP)
    failure_reason = "OpenRouter body did not include Babyscripts proof point"

    with patch("src.outbound_generator._call_openrouter", side_effect=ValueError(failure_reason)):
        with caplog.at_level(logging.WARNING, logger="fourth.outbound_generator"):
            generate_outbound_email([hospital])

    # Must be a dedicated batch-level summary entry, not just the per-hospital warning
    summary_records = [r for r in caplog.records if "fallback summary" in r.message.lower()]
    assert summary_records, "No batch fallback summary log entry found after generation"
    combined = " ".join(r.message for r in summary_records)
    assert hospital["facility_name"] in combined, "Fallback summary must name the specific hospital"
    assert failure_reason in combined, "Fallback summary must include the failure reason"

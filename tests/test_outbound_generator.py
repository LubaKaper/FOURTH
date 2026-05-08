"""
Schema-facing tests for Tool 5 — outbound_generator.

These tests encode the ADR Handoff 4 production contract. They are
expected to fail until outbound_generator.py is migrated from the legacy
three-variant tuning object.
"""

import copy
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.gap_calculator import calculate_gap_score
from src.outbound_generator import _validate_llm_body, generate_outbound_email
from src.urgency_ranker import add_urgency
from tests.fixtures import HIGH_GAP, LOW_GAP, MEDIUM_GAP, NULL_DATA


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

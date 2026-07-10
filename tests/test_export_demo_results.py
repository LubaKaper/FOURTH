"""build_demo_payload packages pipeline output for the Streamlit app."""

import copy

from src.gap_calculator import calculate_gap_score
from src.outbound_generator import generate_outbound_email
from src.urgency_ranker import add_urgency
from tests.fixtures import HIGH_GAP, MEDIUM_GAP

from scripts.export_demo_results import HOSPITAL_EXPORT_FIELDS, build_demo_payload

REQUIRED_EMAIL_KEYS = {
    "facility_id", "facility_name", "recipient_role", "subject", "email_body",
    "product", "lead_angle", "angle_reason", "gap_score", "urgency_tier",
    "sent_at", "status", "claim_validation", "data_confidence",
}


def _ready(fixture: dict) -> dict:
    return add_urgency(calculate_gap_score(copy.deepcopy(fixture)))


def test_payload_shape_and_email_contract():
    hospitals = [_ready(HIGH_GAP), _ready(MEDIUM_GAP)]
    emails = generate_outbound_email(hospitals)  # network blocked -> template bodies

    payload = build_demo_payload(hospitals, emails, "2026-07-10T00:00:00+00:00")

    assert payload["state"] == "NY"
    assert payload["generated_at"] == "2026-07-10T00:00:00+00:00"
    assert len(payload["accounts"]) == 2
    for account in payload["accounts"]:
        assert set(account) == set(HOSPITAL_EXPORT_FIELDS) | {"email"}
        assert account["email"] is not None
        assert REQUIRED_EMAIL_KEYS <= set(account["email"])


def test_account_without_email_gets_null_email():
    hospitals = [_ready(HIGH_GAP)]
    payload = build_demo_payload(hospitals, [], "2026-07-10T00:00:00+00:00")
    assert payload["accounts"][0]["email"] is None

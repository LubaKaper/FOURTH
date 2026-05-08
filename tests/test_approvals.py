"""
Schema-facing tests for Task 3.1 — approvals module.

These tests encode the auto-approve contract:
  gap_score >= 70  AND  data_confidence == "high"  AND  claim_validation == "passed"
  → status promoted to "ready_to_send"

All other emails remain "pending_review".
The layer is bypassable: run_approvals() is a pure function the orchestrator
calls. Skipping it leaves all emails at "pending_review".
"""

import copy
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.approvals import run_approvals


def _email(
    gap_score: float = 75.0,
    data_confidence: str = "high",
    claim_validation: str = "passed",
    status: str = "pending_review",
    facility_id: str = "330001",
) -> dict:
    return {
        "facility_id": facility_id,
        "facility_name": f"Hospital {facility_id}",
        "recipient_role": "CMO",
        "subject": "subject",
        "email_body": "body",
        "product": "Babyscripts",
        "lead_angle": "baby_vs_mother_contrast",
        "angle_reason": "Well-baby 91.5% vs postpartum 61%",
        "gap_score": gap_score,
        "urgency_tier": "high",
        "sent_at": None,
        "status": status,
        "claim_validation": claim_validation,
        "data_confidence": data_confidence,
    }


# ── auto-approve criteria ─────────────────────────────────────────────────────

def test_auto_approve_promotes_to_ready_to_send_when_all_criteria_met():
    email = _email(gap_score=75.0, data_confidence="high", claim_validation="passed")
    result = run_approvals([email])
    assert result[0]["status"] == "ready_to_send"


def test_auto_approve_leaves_pending_when_gap_score_below_70():
    email = _email(gap_score=69.9, data_confidence="high", claim_validation="passed")
    result = run_approvals([email])
    assert result[0]["status"] == "pending_review"


def test_auto_approve_leaves_pending_at_exactly_70():
    """Boundary: 70.0 is the inclusive threshold."""
    email = _email(gap_score=70.0, data_confidence="high", claim_validation="passed")
    result = run_approvals([email])
    assert result[0]["status"] == "ready_to_send"


def test_auto_approve_leaves_pending_when_low_confidence():
    email = _email(gap_score=80.0, data_confidence="low", claim_validation="passed")
    result = run_approvals([email])
    assert result[0]["status"] == "pending_review"


def test_auto_approve_leaves_pending_when_claim_validation_failed():
    email = _email(gap_score=80.0, data_confidence="high", claim_validation="failed")
    result = run_approvals([email])
    assert result[0]["status"] == "pending_review"


def test_auto_approve_all_three_conditions_required():
    """All three must be true — any single failure blocks promotion."""
    base = dict(gap_score=75.0, data_confidence="high", claim_validation="passed")
    failures = [
        {**base, "gap_score": 65.0},
        {**base, "data_confidence": "low"},
        {**base, "claim_validation": "failed"},
    ]
    for overrides in failures:
        email = _email(**overrides)
        result = run_approvals([email])
        assert result[0]["status"] == "pending_review", (
            f"Expected pending_review with overrides {overrides}"
        )


# ── batch behaviour ───────────────────────────────────────────────────────────

def test_run_approvals_processes_mixed_batch():
    """Auto-approve eligible emails, leave others pending, in one call."""
    emails = [
        _email(gap_score=75.0, facility_id="A"),   # eligible
        _email(gap_score=65.0, facility_id="B"),   # below threshold
        _email(gap_score=72.0, facility_id="C"),   # eligible
    ]
    result = run_approvals(emails)
    by_id = {e["facility_id"]: e for e in result}
    assert by_id["A"]["status"] == "ready_to_send"
    assert by_id["B"]["status"] == "pending_review"
    assert by_id["C"]["status"] == "ready_to_send"


def test_run_approvals_returns_same_count_as_input():
    emails = [_email(facility_id=str(i)) for i in range(5)]
    result = run_approvals(emails)
    assert len(result) == 5


def test_run_approvals_does_not_mutate_input():
    email = _email(gap_score=75.0)
    original_status = email["status"]
    run_approvals([email])
    assert email["status"] == original_status


def test_run_approvals_empty_list_returns_empty_list():
    assert run_approvals([]) == []


# ── claim_validation field on outbound emails ─────────────────────────────────

def test_outbound_generator_emails_include_claim_validation_field():
    """Every email object from generate_outbound_email must carry claim_validation."""
    import copy
    from src.gap_calculator import calculate_gap_score
    from src.urgency_ranker import add_urgency
    from src.outbound_generator import generate_outbound_email
    from tests.fixtures import HIGH_GAP

    hospital = add_urgency(calculate_gap_score(copy.deepcopy(HIGH_GAP)))
    emails = generate_outbound_email([hospital])

    assert len(emails) == 1
    assert "claim_validation" in emails[0], "claim_validation missing from email object"
    assert emails[0]["claim_validation"] == "passed"

"""
Schema-facing tests for Task 3.2 — send_gate module.

The send gate is the final enforcement point before an email reaches the
mailer. It is belt-and-suspenders over approvals.py: an email must have
status == "ready_to_send" AND pass all three auto-approve criteria.

A violation raises ValueError — nothing sends silently.
"""

import copy
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.send_gate import filter_sendable


def _email(
    status: str = "ready_to_send",
    gap_score: float = 75.0,
    data_confidence: str = "high",
    claim_validation: str = "passed",
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


# ── filtering ─────────────────────────────────────────────────────────────────

def test_filter_sendable_passes_ready_to_send_emails():
    email = _email(status="ready_to_send")
    result = filter_sendable([email])
    assert len(result) == 1


def test_filter_sendable_blocks_pending_review_emails():
    email = _email(status="pending_review")
    result = filter_sendable([email])
    assert result == []


def test_filter_sendable_returns_only_ready_emails_from_mixed_batch():
    emails = [
        _email(status="ready_to_send", facility_id="A"),
        _email(status="pending_review", facility_id="B"),
        _email(status="ready_to_send", facility_id="C"),
    ]
    result = filter_sendable(emails)
    ids = [e["facility_id"] for e in result]
    assert ids == ["A", "C"]


def test_filter_sendable_empty_list_returns_empty_list():
    assert filter_sendable([]) == []


# ── belt-and-suspenders validation ───────────────────────────────────────────

def test_filter_sendable_raises_if_ready_to_send_but_gap_score_below_70():
    """An email marked ready_to_send but with gap_score < 70 is a bug — raise."""
    email = _email(status="ready_to_send", gap_score=65.0)
    with pytest.raises(ValueError, match="gap_score"):
        filter_sendable([email])


def test_filter_sendable_raises_if_ready_to_send_but_low_confidence():
    """An email marked ready_to_send but with low data_confidence is a bug — raise."""
    email = _email(status="ready_to_send", data_confidence="low")
    with pytest.raises(ValueError, match="data_confidence"):
        filter_sendable([email])


def test_filter_sendable_raises_if_ready_to_send_but_claim_validation_failed():
    """An email marked ready_to_send but with failed validation is a bug — raise."""
    email = _email(status="ready_to_send", claim_validation="failed")
    with pytest.raises(ValueError, match="claim_validation"):
        filter_sendable([email])


def test_filter_sendable_does_not_raise_for_pending_review_with_low_gap():
    """pending_review emails are not validated — they are simply filtered out."""
    email = _email(status="pending_review", gap_score=40.0, data_confidence="low")
    result = filter_sendable([email])
    assert result == []


# ── immutability ──────────────────────────────────────────────────────────────

def test_filter_sendable_does_not_mutate_input():
    email = _email(status="ready_to_send")
    original = copy.deepcopy(email)
    filter_sendable([email])
    assert email == original

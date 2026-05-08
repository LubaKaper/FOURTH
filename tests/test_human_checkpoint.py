# tests/test_human_checkpoint.py
import copy
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.fixtures import HIGH_GAP, MEDIUM_GAP, LOW_GAP
from src.gap_calculator import calculate_gap_score
from src.urgency_ranker import add_urgency
from src.outbound_generator import generate_outbound_email
from src.human_checkpoint import display_checkpoint


def _run(fixture):
    return add_urgency(calculate_gap_score(copy.deepcopy(fixture)))


def _pipeline():
    hospitals = [_run(HIGH_GAP), _run(MEDIUM_GAP), _run(LOW_GAP)]
    emails = generate_outbound_email(hospitals)
    return hospitals, emails


# ── return type ────────────────────────────────────────────────────────────────

def test_returns_string():
    hospitals, emails = _pipeline()
    result = display_checkpoint(hospitals, emails)
    assert isinstance(result, str)


def test_non_empty():
    hospitals, emails = _pipeline()
    result = display_checkpoint(hospitals, emails)
    assert len(result.strip()) > 0


# ── counts ─────────────────────────────────────────────────────────────────────

def test_includes_high_count():
    hospitals, emails = _pipeline()
    result = display_checkpoint(hospitals, emails)
    assert "1 high" in result.lower() or "high: 1" in result.lower()


def test_includes_medium_count():
    hospitals, emails = _pipeline()
    result = display_checkpoint(hospitals, emails)
    assert "1 medium" in result.lower() or "medium: 1" in result.lower()


# ── nothing sent statement ─────────────────────────────────────────────────────

def test_clearly_says_nothing_sent():
    hospitals, emails = _pipeline()
    result = display_checkpoint(hospitals, emails)
    lower = result.lower()
    assert "nothing" in lower or "not sent" in lower or "no email" in lower or "draft" in lower


# ── per-hospital fields ────────────────────────────────────────────────────────

def test_includes_hospital_name():
    hospitals, emails = _pipeline()
    result = display_checkpoint(hospitals, emails)
    assert HIGH_GAP["facility_name"] in result
    assert MEDIUM_GAP["facility_name"] in result


def test_includes_state():
    hospitals, emails = _pipeline()
    result = display_checkpoint(hospitals, emails)
    assert "NY" in result


def test_includes_urgency_flag():
    hospitals, emails = _pipeline()
    result = display_checkpoint(hospitals, emails)
    assert "🔴" in result
    assert "🟡" in result


def test_includes_gap_score():
    h_high = _run(HIGH_GAP)
    h_med = _run(MEDIUM_GAP)
    emails = generate_outbound_email([h_high, h_med])
    result = display_checkpoint([h_high, h_med], emails)
    assert str(int(h_high["gap_score"])) in result
    assert str(int(h_med["gap_score"])) in result


def test_includes_commitment_tag():
    hospitals, emails = _pipeline()
    result = display_checkpoint(hospitals, emails)
    assert HIGH_GAP["commitment_tag"] in result


def test_includes_lead_angle():
    hospitals, emails = _pipeline()
    result = display_checkpoint(hospitals, emails)
    h_high = hospitals[0]
    assert h_high["lead_angle"] in result


# ── email body ─────────────────────────────────────────────────────────────────

def test_email_body_status_present():
    hospitals, emails = _pipeline()
    result = display_checkpoint(hospitals, emails)
    lower = result.lower()
    assert "email body" in lower
    assert "pending_review" in lower


def test_email_body_content_present():
    hospitals, emails = _pipeline()
    result = display_checkpoint(hospitals, emails)
    assert "Babyscripts" in result
    assert "30-day postpartum visit" in result


# ── edge cases ─────────────────────────────────────────────────────────────────

def test_empty_emails_still_returns_string():
    hospitals = [_run(LOW_GAP)]
    emails = generate_outbound_email(hospitals)
    result = display_checkpoint(hospitals, emails)
    assert isinstance(result, str)


# ── decision brief ────────────────────────────────────────────────────────────

def test_checkpoint_includes_decision_brief_compact_format():
    """Checkpoint output must include a compact one-line decision brief per hospital."""
    hospitals, emails = _pipeline()
    result = display_checkpoint(hospitals, emails)

    # Brief format contains: · Gap {score} · {lead_angle} · ... · {recipient_role}
    assert "· Gap " in result, "Decision brief must include '· Gap {score} ·'"


def test_checkpoint_decision_brief_includes_recipient_role():
    """Decision brief must include the recipient role from the email object."""
    hospitals, emails = _pipeline()
    result = display_checkpoint(hospitals, emails)
    roles = {"CMO", "VP Patient Experience"}

    assert any(role in result for role in roles), "Decision brief must include recipient role"


def test_low_urgency_not_shown():
    h_low = _run(LOW_GAP)
    emails = generate_outbound_email([h_low])
    result = display_checkpoint([h_low], emails)
    assert LOW_GAP["facility_name"] not in result

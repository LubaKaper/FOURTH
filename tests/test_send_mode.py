"""
Schema-facing tests for Task 3.6 — production send mode (--send flag).

Tests verify that run_pipeline() routes emails through the full Phase 3
stack only when send_mode=True, and that review-only mode (default) never
touches the mailer, dedup gate, or audit log.

All Phase 3 side-effecting modules are mocked so no real SMTP or file I/O
occurs during the test suite.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agent import run_pipeline

# Synthetic gate-cleared email for send-mode plumbing tests. These tests
# verify dedup/mailer/audit wiring, not whether live NY data crosses the
# auto-approve threshold — with the data-driven state_mortality_rank, real
# NY accounts legitimately score below the >=70 gate, so plumbing tests
# inject their own sendable email at the send-gate boundary. The gate's
# own behavior is covered by tests/test_send_gate.py.
READY_EMAIL = {
    "facility_id": "330199",
    "facility_name": "Synthetic Ready Hospital",
    "recipient_role": "CMO",
    "subject": "subject",
    "email_body": "body",
    "product": "Babyscripts",
    "lead_angle": "hcahps_care_transition_gap",
    "angle_reason": "reason",
    "gap_score": 75.0,
    "urgency_tier": "high",
    "sent_at": None,
    "status": "ready_to_send",
    "claim_validation": "passed",
    "data_confidence": "high",
}


# ── review-only mode (default) ────────────────────────────────────────────────

def test_review_mode_does_not_call_mailer():
    """Default pipeline must never invoke the mailer."""
    with patch("mailer.send_batch") as mock_send:
        run_pipeline("NY", send_mode=False)
    mock_send.assert_not_called()


def test_review_mode_does_not_call_audit_logger():
    """Default pipeline must never write to the audit log."""
    with patch("audit_logger.log_send") as mock_log:
        run_pipeline("NY", send_mode=False)
    mock_log.assert_not_called()


def test_review_mode_does_not_call_dedup():
    """Default pipeline must not run dedup — no log file interaction."""
    with patch("dedup.filter_duplicates") as mock_dedup:
        run_pipeline("NY", send_mode=False)
    mock_dedup.assert_not_called()


# ── send mode ─────────────────────────────────────────────────────────────────

def test_send_mode_calls_mailer_for_cleared_emails(tmp_path):
    """With --send, mailer.send_batch is called with the dedup-cleared emails."""
    log_path = tmp_path / "send_log.csv"

    with patch("agent.filter_sendable", return_value=[dict(READY_EMAIL)]), \
         patch("dedup.filter_duplicates", return_value=[]) as mock_dedup, \
         patch("mailer.send_batch", return_value=[]) as mock_send, \
         patch("audit_logger.log_send") as mock_log:
        run_pipeline("NY", send_mode=True, log_path=log_path)

    mock_send.assert_called_once()


def test_send_mode_runs_dedup_before_mailer(tmp_path):
    """Dedup must be called before mailer — order enforced via call sequence."""
    log_path = tmp_path / "send_log.csv"
    call_order = []

    def fake_dedup(emails, path):
        call_order.append("dedup")
        return emails

    def fake_send(emails, dry_run):
        call_order.append("mailer")
        return emails

    with patch("agent.filter_sendable", return_value=[dict(READY_EMAIL)]), \
         patch("dedup.filter_duplicates", side_effect=fake_dedup), \
         patch("mailer.send_batch", side_effect=fake_send), \
         patch("audit_logger.log_send"):
        run_pipeline("NY", send_mode=True, log_path=log_path)

    assert call_order.index("dedup") < call_order.index("mailer"), (
        "dedup must run before mailer"
    )


def test_send_mode_logs_each_sent_email_to_audit(tmp_path):
    """audit_logger.log_send called once per email returned by mailer."""
    log_path = tmp_path / "send_log.csv"
    sent_emails = [
        {"facility_id": "A", "sent_at": "2026-05-08T14:00:00Z"},
        {"facility_id": "B", "sent_at": "2026-05-08T14:00:01Z"},
    ]

    with patch("agent.filter_sendable", return_value=[dict(READY_EMAIL)]), \
         patch("dedup.filter_duplicates", side_effect=lambda emails, p: emails), \
         patch("mailer.send_batch", return_value=sent_emails) as mock_send, \
         patch("audit_logger.log_send") as mock_log:
        run_pipeline("NY", send_mode=True, log_path=log_path)

    # log_send called once per sent email
    assert mock_log.call_count == len(sent_emails)


def test_send_mode_passes_dry_run_false_to_mailer(tmp_path):
    """In send mode, mailer must be called with dry_run=False."""
    log_path = tmp_path / "send_log.csv"

    with patch("agent.filter_sendable", return_value=[dict(READY_EMAIL)]), \
         patch("dedup.filter_duplicates", side_effect=lambda emails, p: emails), \
         patch("mailer.send_batch", return_value=[]) as mock_send, \
         patch("audit_logger.log_send"):
        run_pipeline("NY", send_mode=True, log_path=log_path)

    _, kwargs = mock_send.call_args
    assert kwargs.get("dry_run") is False or mock_send.call_args[0][1] is False, (
        "send_batch must be called with dry_run=False in send mode"
    )


def test_send_mode_enforces_require_high_confidence(tmp_path):
    """With --send, account_selector must receive require_high_confidence=True."""
    log_path = tmp_path / "send_log.csv"

    # Patch agent's already-imported reference, not the source module
    with patch("agent.select_top_accounts", wraps=__import__("account_selector").select_top_accounts) as mock_select, \
         patch("dedup.filter_duplicates", side_effect=lambda emails, p: emails), \
         patch("mailer.send_batch", return_value=[]), \
         patch("audit_logger.log_send"):
        run_pipeline("NY", send_mode=True, log_path=log_path)

    _, kwargs = mock_select.call_args
    assert kwargs.get("require_high_confidence") is True, (
        "send mode must enforce require_high_confidence=True"
    )


def test_send_mode_does_not_send_pending_review_emails(tmp_path):
    """Emails that stayed pending_review (below auto-approve threshold) never reach mailer."""
    log_path = tmp_path / "send_log.csv"
    # dedup returns only the emails it receives — if send_gate blocked them, none arrive
    with patch("dedup.filter_duplicates", side_effect=lambda emails, p: emails) as mock_dedup, \
         patch("mailer.send_batch", return_value=[]) as mock_send, \
         patch("audit_logger.log_send"):
        run_pipeline("NY", send_mode=True, log_path=log_path)

    if mock_send.called:
        sent = mock_send.call_args[0][0]
        for email in sent:
            assert email.get("status") == "ready_to_send", (
                f"pending_review email reached mailer: {email.get('facility_id')}"
            )

"""
Schema-facing tests for Task 3.3 — mailer module.

Tests use dry_run=True for most cases (no SMTP server available in CI).
One test mocks smtplib to verify the live send path calls the right methods.
Credentials are checked at send time; missing env vars raise ValueError.
"""

import copy
import os
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.mailer import send_email, send_batch


def _email(facility_id: str = "330001") -> dict:
    return {
        "facility_id": facility_id,
        "facility_name": f"Hospital {facility_id}",
        "recipient_role": "CMO",
        "subject": "Hospital postpartum follow-up gap",
        "email_body": "Hi,\n\nBabyscripts can help. Hospitals using Babyscripts saw patients become 2x more likely to complete their 30-day postpartum visit.\n\nOpen to a short conversation?",
        "product": "Babyscripts",
        "lead_angle": "baby_vs_mother_contrast",
        "angle_reason": "Well-baby 91.5% vs postpartum 61%",
        "gap_score": 75.0,
        "urgency_tier": "high",
        "sent_at": None,
        "status": "ready_to_send",
        "claim_validation": "passed",
        "data_confidence": "high",
    }


SMTP_ENV = {
    "SMTP_HOST": "smtp.example.com",
    "SMTP_PORT": "465",
    "SMTP_USER": "gtm@example.com",
    "SMTP_PASSWORD": "secret",
    "SMTP_FROM_EMAIL": "gtm@example.com",
    "SMTP_TO_EMAIL": "recipient@hospital.com",
}


# ── dry_run mode ──────────────────────────────────────────────────────────────

def test_dry_run_populates_sent_at():
    result = send_email(_email(), dry_run=True)
    assert result["sent_at"] is not None


def test_dry_run_sent_at_is_iso_8601_utc():
    result = send_email(_email(), dry_run=True)
    sent_at = result["sent_at"]
    # Must parse as ISO 8601 UTC (ends with Z or +00:00)
    assert sent_at.endswith("Z") or sent_at.endswith("+00:00"), (
        f"sent_at not UTC: {sent_at!r}"
    )
    parsed = datetime.fromisoformat(sent_at.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None


def test_dry_run_does_not_open_smtp_connection():
    with patch("smtplib.SMTP_SSL") as mock_smtp:
        send_email(_email(), dry_run=True)
    mock_smtp.assert_not_called()


def test_dry_run_does_not_mutate_input():
    email = _email()
    original = copy.deepcopy(email)
    send_email(email, dry_run=True)
    assert email == original


def test_dry_run_returns_new_dict_not_same_object():
    email = _email()
    result = send_email(email, dry_run=True)
    assert result is not email


# ── credential validation ─────────────────────────────────────────────────────

def test_send_raises_value_error_when_smtp_host_missing():
    env = {k: v for k, v in SMTP_ENV.items() if k != "SMTP_HOST"}
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(ValueError, match="SMTP_HOST"):
            send_email(_email(), dry_run=False)


def test_send_raises_value_error_when_smtp_password_missing():
    env = {k: v for k, v in SMTP_ENV.items() if k != "SMTP_PASSWORD"}
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(ValueError, match="SMTP_PASSWORD"):
            send_email(_email(), dry_run=False)


def test_send_raises_value_error_when_smtp_to_email_missing():
    env = {k: v for k, v in SMTP_ENV.items() if k != "SMTP_TO_EMAIL"}
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(ValueError, match="SMTP_TO_EMAIL"):
            send_email(_email(), dry_run=False)


# ── live send path (mocked SMTP) ──────────────────────────────────────────────

def test_live_send_calls_smtp_ssl_and_populates_sent_at():
    mock_server = MagicMock()
    mock_server.__enter__ = MagicMock(return_value=mock_server)
    mock_server.__exit__ = MagicMock(return_value=False)

    with patch.dict(os.environ, SMTP_ENV, clear=True):
        with patch("smtplib.SMTP_SSL", return_value=mock_server):
            result = send_email(_email(), dry_run=False)

    mock_server.login.assert_called_once()
    mock_server.sendmail.assert_called_once()
    assert result["sent_at"] is not None


def test_live_send_does_not_mutate_input():
    mock_server = MagicMock()
    mock_server.__enter__ = MagicMock(return_value=mock_server)
    mock_server.__exit__ = MagicMock(return_value=False)

    email = _email()
    original = copy.deepcopy(email)

    with patch.dict(os.environ, SMTP_ENV, clear=True):
        with patch("smtplib.SMTP_SSL", return_value=mock_server):
            send_email(email, dry_run=False)

    assert email == original


# ── required field validation (tests 6 & 7) ──────────────────────────────────

def test_missing_email_body_raises():
    """send_email raises ValueError before any send attempt when email_body is absent."""
    email = _email()
    del email["email_body"]
    with pytest.raises(ValueError, match="email_body"):
        send_email(email, dry_run=True)


def test_missing_recipient_role_raises():
    """send_email raises ValueError before any send attempt when recipient_role is absent."""
    email = _email()
    del email["recipient_role"]
    with pytest.raises(ValueError, match="recipient_role"):
        send_email(email, dry_run=True)


# ── send_batch ────────────────────────────────────────────────────────────────

def test_send_batch_returns_same_count():
    emails = [_email(str(i)) for i in range(3)]
    results = send_batch(emails, dry_run=True)
    assert len(results) == 3


def test_send_batch_all_have_sent_at():
    emails = [_email(str(i)) for i in range(3)]
    results = send_batch(emails, dry_run=True)
    for r in results:
        assert r["sent_at"] is not None


def test_send_batch_empty_list_returns_empty_list():
    assert send_batch([], dry_run=True) == []

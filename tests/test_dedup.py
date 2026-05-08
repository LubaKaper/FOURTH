"""
Schema-facing tests for Task 3.5 — dedup module.

A hospital must not be emailed twice within the 30-day cooldown window.
is_duplicate(email, log_path) checks the audit log and returns True when
a send for the same facility_id exists within the last 30 days.

filter_duplicates(emails, log_path) removes duplicates from a batch,
logs a warning for each blocked hospital, and returns the clean list.
"""

import csv
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.dedup import is_duplicate, filter_duplicates


COOLDOWN_DAYS = 30


def _email(facility_id: str = "330001") -> dict:
    return {
        "facility_id": facility_id,
        "facility_name": f"Hospital {facility_id}",
        "recipient_role": "CMO",
        "email_body": "body",
        "gap_score": 75.0,
        "sent_at": None,
        "status": "ready_to_send",
    }


def _write_log(log_path: Path, facility_id: str, sent_at: str) -> None:
    """Helper: write a single row directly to the log CSV."""
    write_header = not log_path.exists()
    with log_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["facility_id", "facility_name",
                                                "recipient_role", "gap_score",
                                                "sent_at", "status", "body_hash"])
        if write_header:
            writer.writeheader()
        writer.writerow({
            "facility_id": facility_id,
            "facility_name": f"Hospital {facility_id}",
            "recipient_role": "CMO",
            "gap_score": "75.0",
            "sent_at": sent_at,
            "status": "ready_to_send",
            "body_hash": "abc123",
        })


def _utc(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


NOW = datetime.now(timezone.utc)


# ── is_duplicate ──────────────────────────────────────────────────────────────

def test_not_duplicate_when_log_is_empty(tmp_path):
    log_path = tmp_path / "send_log.csv"
    assert is_duplicate(_email(), log_path) is False


def test_not_duplicate_when_log_file_absent(tmp_path):
    log_path = tmp_path / "send_log.csv"
    assert is_duplicate(_email(), log_path) is False


def test_is_duplicate_when_sent_within_cooldown(tmp_path):
    log_path = tmp_path / "send_log.csv"
    recent = _utc(NOW - timedelta(days=10))
    _write_log(log_path, "330001", recent)
    assert is_duplicate(_email("330001"), log_path) is True


def test_not_duplicate_when_sent_outside_cooldown(tmp_path):
    log_path = tmp_path / "send_log.csv"
    old = _utc(NOW - timedelta(days=31))
    _write_log(log_path, "330001", old)
    assert is_duplicate(_email("330001"), log_path) is False


def test_not_duplicate_for_different_facility(tmp_path):
    log_path = tmp_path / "send_log.csv"
    recent = _utc(NOW - timedelta(days=5))
    _write_log(log_path, "330001", recent)
    assert is_duplicate(_email("330002"), log_path) is False


def test_duplicate_uses_most_recent_send_for_same_facility(tmp_path):
    """If sent 35 days ago and again 5 days ago, still a duplicate."""
    log_path = tmp_path / "send_log.csv"
    _write_log(log_path, "330001", _utc(NOW - timedelta(days=35)))
    _write_log(log_path, "330001", _utc(NOW - timedelta(days=5)))
    assert is_duplicate(_email("330001"), log_path) is True


def test_boundary_exactly_30_days_is_duplicate(tmp_path):
    """sent_at exactly 30 days ago is still within the cooldown window."""
    log_path = tmp_path / "send_log.csv"
    _write_log(log_path, "330001", _utc(NOW - timedelta(days=30)))
    assert is_duplicate(_email("330001"), log_path, _now=NOW) is True


def test_boundary_31_days_is_not_duplicate(tmp_path):
    log_path = tmp_path / "send_log.csv"
    _write_log(log_path, "330001", _utc(NOW - timedelta(days=31)))
    assert is_duplicate(_email("330001"), log_path, _now=NOW) is False


# ── filter_duplicates ─────────────────────────────────────────────────────────

def test_filter_duplicates_removes_duplicate_from_batch(tmp_path):
    log_path = tmp_path / "send_log.csv"
    _write_log(log_path, "330001", _utc(NOW - timedelta(days=5)))
    emails = [_email("330001"), _email("330002")]
    result = filter_duplicates(emails, log_path)
    assert [e["facility_id"] for e in result] == ["330002"]


def test_filter_duplicates_passes_clean_batch_unchanged(tmp_path):
    log_path = tmp_path / "send_log.csv"
    emails = [_email("A"), _email("B"), _email("C")]
    result = filter_duplicates(emails, log_path)
    assert [e["facility_id"] for e in result] == ["A", "B", "C"]


def test_filter_duplicates_empty_batch_returns_empty(tmp_path):
    log_path = tmp_path / "send_log.csv"
    assert filter_duplicates([], log_path) == []


def test_filter_duplicates_does_not_mutate_input(tmp_path):
    import copy
    log_path = tmp_path / "send_log.csv"
    emails = [_email("330001")]
    original = copy.deepcopy(emails)
    filter_duplicates(emails, log_path)
    assert emails == original

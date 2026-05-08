"""
Schema-facing tests for Task 3.4 — audit_logger module.

Every send attempt is logged to an append-only CSV. Tests use a tmp_path
fixture so no real send_log.csv is touched during the suite.

Contract:
  log_send(email, log_path)  — appends one row; creates file+header if absent
  read_log(log_path)         — returns list of row dicts for inspection/dedup
"""

import csv
import hashlib
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.audit_logger import log_send, read_log


REQUIRED_COLUMNS = {
    "facility_id",
    "facility_name",
    "recipient_role",
    "gap_score",
    "sent_at",
    "status",
    "body_hash",
}


def _email(facility_id: str = "330001") -> dict:
    return {
        "facility_id": facility_id,
        "facility_name": f"Hospital {facility_id}",
        "recipient_role": "CMO",
        "subject": "Subject line",
        "email_body": "Hi,\n\nBabyscripts. 2x more likely. Open to a chat?",
        "product": "Babyscripts",
        "lead_angle": "baby_vs_mother_contrast",
        "angle_reason": "Well-baby 91.5% vs postpartum 61%",
        "gap_score": 75.0,
        "urgency_tier": "high",
        "sent_at": "2026-05-08T14:00:00Z",
        "status": "ready_to_send",
        "claim_validation": "passed",
        "data_confidence": "high",
    }


# ── appending ─────────────────────────────────────────────────────────────────

def test_log_send_creates_file_if_absent(tmp_path):
    log_path = tmp_path / "send_log.csv"
    log_send(_email(), log_path)
    assert log_path.exists()


def test_log_send_writes_header_on_first_write(tmp_path):
    log_path = tmp_path / "send_log.csv"
    log_send(_email(), log_path)
    with log_path.open() as f:
        header = f.readline().strip().split(",")
    assert set(header) >= REQUIRED_COLUMNS


def test_log_send_appends_one_row_per_call(tmp_path):
    log_path = tmp_path / "send_log.csv"
    log_send(_email("A"), log_path)
    log_send(_email("B"), log_path)
    rows = read_log(log_path)
    assert len(rows) == 2


def test_log_send_does_not_overwrite_existing_rows(tmp_path):
    log_path = tmp_path / "send_log.csv"
    log_send(_email("A"), log_path)
    log_send(_email("B"), log_path)
    log_send(_email("C"), log_path)
    rows = read_log(log_path)
    ids = [r["facility_id"] for r in rows]
    assert ids == ["A", "B", "C"]


# ── row content ───────────────────────────────────────────────────────────────

def test_log_send_row_contains_all_required_columns(tmp_path):
    log_path = tmp_path / "send_log.csv"
    log_send(_email(), log_path)
    rows = read_log(log_path)
    assert len(rows) == 1
    missing = REQUIRED_COLUMNS - set(rows[0])
    assert not missing, f"Row missing columns: {missing}"


def test_log_send_body_hash_is_sha256_of_email_body(tmp_path):
    log_path = tmp_path / "send_log.csv"
    email = _email()
    log_send(email, log_path)
    rows = read_log(log_path)
    expected = hashlib.sha256(email["email_body"].encode()).hexdigest()
    assert rows[0]["body_hash"] == expected


def test_log_send_copies_audit_fields_correctly(tmp_path):
    log_path = tmp_path / "send_log.csv"
    email = _email("330099")
    log_send(email, log_path)
    rows = read_log(log_path)
    row = rows[0]
    assert row["facility_id"] == "330099"
    assert row["recipient_role"] == "CMO"
    assert row["gap_score"] == "75.0"
    assert row["sent_at"] == "2026-05-08T14:00:00Z"
    assert row["status"] == "ready_to_send"


# ── immutability ──────────────────────────────────────────────────────────────

def test_log_send_does_not_mutate_input(tmp_path):
    import copy
    log_path = tmp_path / "send_log.csv"
    email = _email()
    original = copy.deepcopy(email)
    log_send(email, log_path)
    assert email == original


# ── read_log ──────────────────────────────────────────────────────────────────

def test_read_log_returns_empty_list_when_file_absent(tmp_path):
    log_path = tmp_path / "nonexistent.csv"
    assert read_log(log_path) == []


def test_read_log_returns_list_of_dicts(tmp_path):
    log_path = tmp_path / "send_log.csv"
    log_send(_email(), log_path)
    rows = read_log(log_path)
    assert isinstance(rows, list)
    assert isinstance(rows[0], dict)

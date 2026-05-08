"""Schema-facing pipeline handoff tests for Fourth.

These tests verify the ADR contracts across Tools 3-5 using deterministic
fixtures. Real-data validation remains the manual agent run.

Task 3.7 integration tests are at the bottom: they exercise the full Phase 3
chain (approvals → send_gate → dedup → mailer → audit_logger) using fixtures,
without loading real CMS data.
"""

import copy
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tests.fixtures import HIGH_GAP, LOW_GAP, MEDIUM_GAP, NO_COMMITMENT, NULL_DATA

from account_selector import select_top_accounts
from approvals import run_approvals
from audit_logger import log_send, read_log
from dedup import filter_duplicates
from gap_calculator import calculate_gap_score
from mailer import send_email, send_batch
from outbound_generator import generate_outbound_email
from send_gate import filter_sendable
from urgency_ranker import add_urgency


@pytest.fixture
def fresh_hospitals() -> list[dict]:
    return [
        copy.deepcopy(HIGH_GAP),
        copy.deepcopy(MEDIUM_GAP),
        copy.deepcopy(LOW_GAP),
        copy.deepcopy(NULL_DATA),
        copy.deepcopy(NO_COMMITMENT),
    ]


def _run_through_tool_4(hospitals: list[dict]) -> list[dict]:
    after_3 = [calculate_gap_score(h) for h in hospitals]
    return [add_urgency(h) for h in after_3]


def test_dict_fields_only_grow_through_pipeline(fresh_hospitals):
    initial_keys = [set(h.keys()) for h in fresh_hospitals]

    after_3 = [calculate_gap_score(copy.deepcopy(h)) for h in fresh_hospitals]
    for original, scored in zip(initial_keys, after_3):
        assert original.issubset(scored.keys()), "Tool 3 dropped or renamed a field"

    pre_tool_4_keys = [set(h.keys()) for h in after_3]
    after_4 = [add_urgency(h) for h in after_3]
    for pre, post in zip(pre_tool_4_keys, after_4):
        assert pre.issubset(post.keys()), "Tool 4 dropped or renamed a field"


def test_tool_3_gap_score_within_intermediate_range(fresh_hospitals):
    after_3 = [calculate_gap_score(h) for h in fresh_hospitals]
    for h in after_3:
        assert isinstance(h["gap_score"], float)
        assert 0.0 <= h["gap_score"] <= 75.0


def test_tool_4_thresholds_use_final_gap_score_after_add_urgency(fresh_hospitals):
    after_4 = _run_through_tool_4(fresh_hospitals)
    by_id = {h["facility_id"]: h for h in after_4}

    assert by_id[HIGH_GAP["facility_id"]]["gap_score"] >= 70
    assert by_id[HIGH_GAP["facility_id"]]["urgency_tier"] == "high"

    assert 40 <= by_id[MEDIUM_GAP["facility_id"]]["gap_score"] < 70
    assert by_id[MEDIUM_GAP["facility_id"]]["urgency_tier"] == "medium"

    assert by_id[LOW_GAP["facility_id"]]["gap_score"] < 40
    assert by_id[LOW_GAP["facility_id"]]["urgency_tier"] == "low"


def test_low_tier_hospitals_stop_before_outbound(fresh_hospitals):
    after_4 = _run_through_tool_4(fresh_hospitals)
    selected = select_top_accounts(after_4)

    assert all(h["urgency_tier"] != "low" for h in selected)
    assert all(h["gap_score"] >= 40 for h in selected)


def test_outbound_objects_include_audit_trail_fields(fresh_hospitals):
    after_4 = _run_through_tool_4(fresh_hospitals)
    selected = select_top_accounts(after_4)
    emails = generate_outbound_email(selected)

    for email in emails:
        assert email["product"] == "Babyscripts"
        assert email["lead_angle"]
        assert isinstance(email["gap_score"], float)
        assert email["status"] == "pending_review"
        assert email["sent_at"] is None


def test_null_data_continues_through_tool_4_with_low_confidence(fresh_hospitals):
    null_id = NULL_DATA["facility_id"]
    after_4 = _run_through_tool_4(fresh_hospitals)

    null_after_4 = [h for h in after_4 if h["facility_id"] == null_id]
    assert len(null_after_4) == 1
    assert null_after_4[0]["data_confidence"] == "low"
    assert isinstance(null_after_4[0]["gap_score"], float)


def test_no_commitment_continues_with_zero_commitment_strength():
    hospital = add_urgency(calculate_gap_score(copy.deepcopy(NO_COMMITMENT)))

    assert hospital["gap_breakdown"]["commitment_strength"] == 0
    assert isinstance(hospital["gap_score"], float)


# ── Task 3.7: Phase 3 integration tests ──────────────────────────────────────

def _phase3_ready(fixture: dict) -> dict:
    """Run fixture through Tools 3-4 to produce a pipeline-ready hospital."""
    return add_urgency(calculate_gap_score(copy.deepcopy(fixture)))


def test_full_phase3_chain_populates_sent_at(tmp_path):
    """Dry-run: full Phase 3 chain produces emails with sent_at populated."""
    log_path = tmp_path / "send_log.csv"

    hospital = _phase3_ready(HIGH_GAP)
    emails = generate_outbound_email([hospital])
    emails = run_approvals(emails)
    sendable = filter_sendable(emails)
    clean = filter_duplicates(sendable, log_path)
    sent = send_batch(clean, dry_run=True)

    assert len(sent) == 1
    assert sent[0]["sent_at"] is not None
    assert sent[0]["status"] == "ready_to_send"


def test_full_phase3_chain_writes_audit_log_entry(tmp_path):
    """Dry-run: after send, audit log has one row per sent email."""
    log_path = tmp_path / "send_log.csv"

    hospital = _phase3_ready(HIGH_GAP)
    emails = generate_outbound_email([hospital])
    emails = run_approvals(emails)
    sendable = filter_sendable(emails)
    clean = filter_duplicates(sendable, log_path)
    sent = send_batch(clean, dry_run=True)
    for email in sent:
        log_send(email, log_path)

    rows = read_log(log_path)
    assert len(rows) == 1
    assert rows[0]["facility_id"] == HIGH_GAP["facility_id"]
    assert rows[0]["sent_at"] is not None
    assert len(rows[0]["body_hash"]) == 64  # SHA-256 hex digest


def test_dedup_blocks_second_send_within_30_days(tmp_path):
    """Send-mode: dedup gate blocks a second send to the same facility."""
    log_path = tmp_path / "send_log.csv"

    hospital = _phase3_ready(HIGH_GAP)

    # First run — no history, goes through
    emails = generate_outbound_email([hospital])
    emails = run_approvals(emails)
    sendable = filter_sendable(emails)
    first_clean = filter_duplicates(sendable, log_path)
    assert len(first_clean) == 1, "First send should not be blocked"
    sent = send_batch(first_clean, dry_run=True)
    for email in sent:
        log_send(email, log_path)

    # Second run — same facility, within cooldown
    emails2 = generate_outbound_email([hospital])
    emails2 = run_approvals(emails2)
    sendable2 = filter_sendable(emails2)
    second_clean = filter_duplicates(sendable2, log_path)

    assert len(second_clean) == 0, "Second send within 30 days must be blocked by dedup"


def test_pending_review_email_never_reaches_audit_log(tmp_path):
    """pending_review emails stop at send_gate — nothing written to audit log."""
    log_path = tmp_path / "send_log.csv"

    # MEDIUM_GAP scores below 70 after urgency — stays pending_review
    hospital = _phase3_ready(MEDIUM_GAP)
    emails = generate_outbound_email([hospital])
    emails = run_approvals(emails)

    # Verify this email is pending_review (gap_score < 70)
    assert emails[0]["status"] == "pending_review"

    sendable = filter_sendable(emails)  # gate blocks it
    assert len(sendable) == 0

    # Nothing to dedup, send, or log
    clean = filter_duplicates(sendable, log_path)
    sent = send_batch(clean, dry_run=True)
    for email in sent:
        log_send(email, log_path)

    assert read_log(log_path) == [], "No audit log entry for pending_review email"


def test_low_confidence_email_excluded_by_send_gate(tmp_path):
    """low data_confidence emails never reach the send gate."""
    log_path = tmp_path / "send_log.csv"

    hospital = _phase3_ready(NULL_DATA)
    emails = generate_outbound_email([hospital])

    # NULL_DATA has low data_confidence — outbound generator excludes it
    assert len(emails) == 0, "low confidence hospital must produce no emails"
    assert read_log(log_path) == []

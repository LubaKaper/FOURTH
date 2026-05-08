"""
Tool 5.6 — send_gate.

Final enforcement point before an email reaches the mailer.

Responsibility split:
  approvals.py  — decides which emails are ready_to_send
  send_gate.py  — enforces that only ready emails proceed AND validates
                  all three criteria a second time (belt-and-suspenders)

A ready_to_send email that fails any criterion is a pipeline bug.
Raise ValueError loudly rather than sending a bad email silently.

pending_review emails are filtered out without error — they are expected
to be reviewed by a human or await the next scoring cycle.

Pure function: does not mutate input.
"""

import logging
from typing import Any

log = logging.getLogger("fourth.send_gate")

AUTO_APPROVE_GAP_THRESHOLD: float = 70.0


def filter_sendable(emails: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return emails that are ready_to_send, validated. Raise on any gate violation."""
    sendable = []
    for email in emails:
        if email.get("status") != "ready_to_send":
            log.debug("send_gate: skipping %s (status=%s)", email.get("facility_id"), email.get("status"))
            continue
        _assert_gate_conditions(email)
        sendable.append(dict(email))
    return sendable


def _assert_gate_conditions(email: dict[str, Any]) -> None:
    """Raise ValueError if a ready_to_send email violates any send criterion."""
    fid = email.get("facility_id", "unknown")
    gap = float(email.get("gap_score", 0))
    if gap < AUTO_APPROVE_GAP_THRESHOLD:
        raise ValueError(
            f"send_gate: {fid} has status=ready_to_send but gap_score={gap} "
            f"< {AUTO_APPROVE_GAP_THRESHOLD} — approvals bug"
        )
    if email.get("data_confidence") != "high":
        raise ValueError(
            f"send_gate: {fid} has status=ready_to_send but data_confidence="
            f"{email.get('data_confidence')!r} — approvals bug"
        )
    if email.get("claim_validation") != "passed":
        raise ValueError(
            f"send_gate: {fid} has status=ready_to_send but claim_validation="
            f"{email.get('claim_validation')!r} — approvals bug"
        )

"""
Tool 5.5 — approvals.

Bypassable approval layer between Outbound Generator and the mailer.

Auto-approve criteria (ADR Section 1):
  gap_score >= 70  AND  data_confidence == "high"  AND  claim_validation == "passed"

Emails meeting all three are promoted to "ready_to_send".
All others remain "pending_review" for Human Checkpoint review.

During tuning, the orchestrator calls run_approvals() after generate_outbound_email().
For full automation, the orchestrator routes ready_to_send emails directly to the
mailer — no human step required.

Pure function: returns new dicts, does not mutate input.
"""

from typing import Any

AUTO_APPROVE_GAP_THRESHOLD: float = 70.0


def run_approvals(emails: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a new list of email dicts with status updated per auto-approve criteria."""
    return [_evaluate(email) for email in emails]


def _evaluate(email: dict[str, Any]) -> dict[str, Any]:
    if _qualifies(email):
        return {**email, "status": "ready_to_send"}
    return dict(email)


def _qualifies(email: dict[str, Any]) -> bool:
    return (
        float(email.get("gap_score", 0)) >= AUTO_APPROVE_GAP_THRESHOLD
        and email.get("data_confidence") == "high"
        and email.get("claim_validation") == "passed"
    )

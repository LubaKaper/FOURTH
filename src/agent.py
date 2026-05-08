"""
agent.py — Fourth Pipeline Orchestrator

Runs the seven-tool Fourth pipeline end-to-end for a given state.
Thin orchestration only; all business logic lives in the per-tool
modules in src/. v1 is NY-only.

Run: python src/agent.py NY
"""
import argparse
import io
import logging
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from commitment_ingester import get_hospital_commitments
from outcome_scorer import score_outcomes
from gap_calculator import calculate_gap_score
from urgency_ranker import add_urgency
from account_selector import select_top_accounts
from outbound_generator import generate_outbound_email
from approvals import run_approvals
from send_gate import filter_sendable
import audit_logger
import dedup
import mailer
from human_checkpoint import display_checkpoint
from dashboard_generator import generate_dashboard


DASHBOARD_PATH = "dashboard/fourth_dashboard.html"
DEFAULT_LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "send_log.csv"

log = logging.getLogger("fourth.agent")


def run_pipeline(
    state: str,
    send_mode: bool = False,
    log_path: Path | None = None,
) -> int:
    """Execute the Fourth pipeline for `state`. Return process exit code.

    send_mode=False (default): review-only. No mailer, dedup, or audit log.
    send_mode=True (--send):   full production path. Enforces high-confidence
                               gate, dedup, SMTP delivery, and audit logging.
    """
    if log_path is None:
        log_path = DEFAULT_LOG_PATH

    log.info(
        "Starting Fourth pipeline for state=%s mode=%s",
        state,
        "send" if send_mode else "review",
    )

    hospitals = get_hospital_commitments(state)
    log.info("Tool 1 — Loaded %d %s hospitals", len(hospitals), state)

    if not hospitals:
        log.info("v1 is NY-only; nothing to do for %s", state)
        return 0

    hospitals = score_outcomes(hospitals)
    log.info("Tool 2 — Scored outcomes for %d hospitals", len(hospitals))

    hospitals = [calculate_gap_score(h) for h in hospitals]
    confidence = Counter(h["data_confidence"] for h in hospitals)
    log.info(
        "Tool 3 — Gap calculator complete (%d high confidence, %d low)",
        confidence["high"],
        confidence["low"],
    )

    hospitals = [add_urgency(h) for h in hospitals]
    tier = Counter(h["urgency_tier"] for h in hospitals)
    log.info(
        "Tool 4 — Urgency ranker complete (%d high, %d medium, %d low)",
        tier["high"],
        tier["medium"],
        tier["low"],
    )

    selected_hospitals = select_top_accounts(
        hospitals,
        limit=10,
        require_high_confidence=send_mode,
    )
    log.info("Account selector — Selected top %d accounts", len(selected_hospitals))

    emails = generate_outbound_email(selected_hospitals)
    emails = run_approvals(emails)
    statuses = Counter(e["status"] for e in emails)
    status_summary = ", ".join(f"{k}={v}" for k, v in statuses.items()) or "none"
    log.info("Tool 5 — Generated %d emails (%s)", len(emails), status_summary)
    ready = statuses.get("ready_to_send", 0)
    if ready:
        log.info("Approvals — %d email(s) auto-approved (ready_to_send)", ready)

    sendable = filter_sendable(emails)
    log.info("Send gate — %d email(s) cleared for delivery", len(sendable))

    if send_mode and sendable:
        clean = dedup.filter_duplicates(sendable, log_path)
        log.info("Dedup — %d email(s) passed cooldown gate (%d blocked)", len(clean), len(sendable) - len(clean))
        sent = mailer.send_batch(clean, dry_run=False)
        for email in sent:
            audit_logger.log_send(email, log_path)
        log.info("Send — %d email(s) delivered and logged", len(sent))

    display_checkpoint(selected_hospitals, emails)
    log.info("Tool 6 — Checkpoint displayed")

    output_path = generate_dashboard(selected_hospitals, emails, DASHBOARD_PATH)
    log.info("Tool 7 — Dashboard written to %s", output_path)

    return 0


def main() -> int:
    # Windows cp1252 console can't encode urgency_flag emoji from Tool 6.
    # Reconfigure stdout to UTF-8 so the human checkpoint renders correctly.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, io.UnsupportedOperation):
        pass

    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(message)s",
    )

    parser = argparse.ArgumentParser(description="Fourth pipeline orchestrator")
    parser.add_argument(
        "state",
        nargs="?",
        default="NY",
        help="Two-letter state code (default: NY).",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Production send mode: enforce high-confidence gate, run dedup, deliver via SMTP, write audit log.",
    )
    args = parser.parse_args()

    try:
        return run_pipeline(args.state.upper(), send_mode=args.send)
    except Exception as exc:
        log.error("Pipeline failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())

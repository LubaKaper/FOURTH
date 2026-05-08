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

sys.path.insert(0, os.path.dirname(__file__))

from commitment_ingester import get_hospital_commitments
from outcome_scorer import score_outcomes
from gap_calculator import calculate_gap_score
from urgency_ranker import add_urgency
from account_selector import select_top_accounts
from outbound_generator import generate_outbound_email
from human_checkpoint import display_checkpoint
from dashboard_generator import generate_dashboard


DASHBOARD_PATH = "dashboard/fourth_dashboard.html"

log = logging.getLogger("fourth.agent")


def run_pipeline(state: str) -> int:
    """Execute the Fourth pipeline for `state`. Return process exit code."""
    log.info("Starting Fourth pipeline for state=%s", state)

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

    selected_hospitals = select_top_accounts(hospitals, limit=10)
    log.info("Account selector — Selected top %d accounts", len(selected_hospitals))

    emails = generate_outbound_email(selected_hospitals)
    statuses = Counter(e["status"] for e in emails)
    status_summary = ", ".join(f"{k}={v}" for k, v in statuses.items()) or "none"
    log.info("Tool 5 — Generated %d emails (%s)", len(emails), status_summary)

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
    args = parser.parse_args()

    try:
        return run_pipeline(args.state.upper())
    except Exception as exc:
        log.error("Pipeline failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())

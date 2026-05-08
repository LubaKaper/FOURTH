"""
Tool 6.6 — dedup.

30-day cooldown gate. Prevents resending to the same facility within
the cooldown window by checking the audit log before delivery.

is_duplicate(email, log_path)      — True when facility_id appears in log
                                     with a sent_at within the last 30 days
filter_duplicates(emails, log_path) — removes duplicates from a batch;
                                     logs a warning for each blocked hospital

Uses audit_logger.read_log() as the authority — no separate state.
Pure output: filter_duplicates does not mutate the input list or dicts.
"""

import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(__file__))
from audit_logger import read_log

log = logging.getLogger("fourth.dedup")

COOLDOWN_DAYS: int = 30


def is_duplicate(
    email: dict[str, Any],
    log_path: Path,
    _now: datetime | None = None,
) -> bool:
    """Return True when this facility was sent an email within the cooldown window.

    _now is injected in tests to eliminate clock drift on exact-boundary checks.
    """
    facility_id = email["facility_id"]
    rows = read_log(log_path)
    now = _now if _now is not None else datetime.now(timezone.utc)
    cutoff = now - timedelta(days=COOLDOWN_DAYS)

    sent_dates = []
    for row in rows:
        if row.get("facility_id") != facility_id:
            continue
        sent_at_str = row.get("sent_at", "")
        try:
            sent_at = datetime.fromisoformat(sent_at_str.replace("Z", "+00:00"))
            sent_dates.append(sent_at)
        except (ValueError, AttributeError):
            continue

    if not sent_dates:
        return False

    return max(sent_dates) >= cutoff


def filter_duplicates(
    emails: list[dict[str, Any]], log_path: Path
) -> list[dict[str, Any]]:
    """Return emails with duplicates removed. Logs a warning for each blocked send."""
    clean = []
    for email in emails:
        if is_duplicate(email, log_path):
            log.warning(
                "dedup: skipping %s (%s) — sent within %d-day cooldown window",
                email.get("facility_id"),
                email.get("facility_name"),
                COOLDOWN_DAYS,
            )
        else:
            clean.append(email)
    return clean

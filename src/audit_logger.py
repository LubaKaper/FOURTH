"""
Tool 6.5 — audit_logger.

Append-only send log. Every call to log_send() adds one row to a CSV.
Rows are never deleted or modified — the log is an immutable audit trail.

body_hash is SHA-256 of email_body. It lets you verify body integrity
without storing PII in the log file.

log_send(email, log_path)  — append one row; create file+header if absent
read_log(log_path)         — return list of row dicts; [] if file absent

Pure output: log_send does not mutate the input email dict.
"""

import csv
import hashlib
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger("fourth.audit_logger")

LOG_COLUMNS = [
    "facility_id",
    "facility_name",
    "recipient_role",
    "gap_score",
    "sent_at",
    "status",
    "body_hash",
]


def log_send(email: dict[str, Any], log_path: Path) -> None:
    """Append one row to the send log CSV. Creates the file if absent."""
    log_path = Path(log_path)
    write_header = not log_path.exists()

    body_hash = hashlib.sha256(email["email_body"].encode()).hexdigest()
    row = {
        "facility_id": email["facility_id"],
        "facility_name": email["facility_name"],
        "recipient_role": email["recipient_role"],
        "gap_score": email["gap_score"],
        "sent_at": email["sent_at"],
        "status": email["status"],
        "body_hash": body_hash,
    }

    with log_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerow(row)

    log.info("audit_logger: logged send for %s", email.get("facility_id"))


def read_log(log_path: Path) -> list[dict[str, str]]:
    """Return all rows from the send log as a list of dicts. [] if file absent."""
    log_path = Path(log_path)
    if not log_path.exists():
        return []
    with log_path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

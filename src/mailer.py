"""
Tool 6 — mailer.

Delivers a single Babyscripts outbound email via SMTP SSL.

Credentials are read from environment variables at send time:
  SMTP_HOST        — e.g. smtp.gmail.com
  SMTP_PORT        — e.g. 465 (SSL) or 587 (STARTTLS); defaults to 465
  SMTP_USER        — authenticated sender login
  SMTP_PASSWORD    — app password or API key
  SMTP_FROM_EMAIL  — From address in the envelope
  SMTP_TO_EMAIL    — Recipient address (single address for tuning phase)

Fourth does NOT send in review-only mode. Call send_email() only after
filter_sendable() confirms the email is ready_to_send.

dry_run=True skips the SMTP call and populates sent_at — used for tests
and for tuning-phase pipeline runs before --send is enabled (Task 3.6).

Pure output: returns a new dict with sent_at populated. Never mutates input.
"""

import logging
import os
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Any

log = logging.getLogger("fourth.mailer")

_REQUIRED_ENV = ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM_EMAIL", "SMTP_TO_EMAIL")


def send_email(email: dict[str, Any], dry_run: bool = True) -> dict[str, Any]:
    """Send one email. Return a new dict with sent_at populated.

    Args:
        email:    A send-contract email dict from the outbound generator.
        dry_run:  When True, skip the SMTP call (default). Pass False only
                  from the production send path (Task 3.6 --send flag).
    """
    _check_required_fields(email)

    if not dry_run:
        _check_credentials()

    sent_at = _utc_now_iso()

    if dry_run:
        log.debug("mailer dry_run: skipping SMTP for %s", email.get("facility_id"))
    else:
        _smtp_send(email)
        log.info(
            "mailer: sent to %s for %s",
            os.environ["SMTP_TO_EMAIL"],
            email.get("facility_id"),
        )

    return {**email, "sent_at": sent_at}


def send_batch(emails: list[dict[str, Any]], dry_run: bool = True) -> list[dict[str, Any]]:
    """Send a batch of emails. Returns a new list with sent_at populated on each."""
    return [send_email(e, dry_run=dry_run) for e in emails]


def _check_required_fields(email: dict[str, Any]) -> None:
    for field in ("email_body", "recipient_role"):
        if field not in email:
            raise ValueError(f"mailer: email dict missing required field '{field}'")


def _check_credentials() -> None:
    missing = [k for k in _REQUIRED_ENV if not os.environ.get(k)]
    if missing:
        raise ValueError(
            f"mailer: missing required env vars: {', '.join(missing)}"
        )


def _smtp_send(email: dict[str, Any]) -> None:
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "465"))
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASSWORD"]
    from_addr = os.environ["SMTP_FROM_EMAIL"]
    to_addr = os.environ["SMTP_TO_EMAIL"]

    msg = EmailMessage()
    msg["Subject"] = email["subject"]
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.set_content(email["email_body"])

    with smtplib.SMTP_SSL(host, port) as server:
        server.login(user, password)
        server.sendmail(from_addr, [to_addr], msg.as_string())


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

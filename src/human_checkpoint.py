"""
human_checkpoint.py — Tool 6 | Owner: Paula

Presents a readable terminal review surface for the GTM engineer.
Shows all high/medium email drafts. Fourth drafts only — the human sends.
"""
from typing import Any

DIVIDER = "─" * 72


def _email_block(email: dict[str, Any]) -> str:
    lines = [
        f"  EMAIL BODY ({email.get('status', 'pending_review')})",
        email["email_body"],
    ]
    return "\n".join(lines)


def _hospital_block(h: dict[str, Any], email: dict[str, Any]) -> str:
    score = int(h["gap_score"])
    return "\n".join([
        DIVIDER,
        f"  {h['urgency_flag']}  {h['facility_name']} · {h['state']}",
        f"  Gap score: {score}  |  Lead angle: {h['lead_angle']}",
        f"  Commitment: \"{h['commitment_tag']}\"",
        f"  To role: {email['recipient_role']}",
        f"  Subject: {email['subject']}",
        f"  Product: {email['product']}",
        "",
        _email_block(email),
    ])


def display_checkpoint(
    hospitals: list[dict[str, Any]],
    emails: list[dict[str, Any]],
) -> str:
    email_by_id = {e["facility_id"]: e for e in emails}

    included = [
        h for h in hospitals
        if h.get("urgency_tier") in ("high", "medium") and h["facility_id"] in email_by_id
    ]

    high_count = sum(1 for h in included if h["urgency_tier"] == "high")
    medium_count = sum(1 for h in included if h["urgency_tier"] == "medium")

    header = "\n".join([
        "=" * 72,
        "  Fourth — HUMAN CHECKPOINT",
        f"  {high_count} high  ·  {medium_count} medium  ·  Nothing sent — review, copy, send yourself.",
        "=" * 72,
    ])

    if not included:
        summary = header + "\n\n  No high or medium urgency accounts today.\n"
    else:
        blocks = [_hospital_block(h, email_by_id[h["facility_id"]]) for h in included]
        footer = DIVIDER + "\n  Review complete. Copy the variant that fits. Fourth does not send.\n"
        summary = "\n".join([header] + blocks + [footer])

    print(summary)
    return summary

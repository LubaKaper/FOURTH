"""
human_checkpoint.py — Tool 6

Presents a readable terminal review surface for the GTM engineer.
Shows all high/medium email drafts. Fourth drafts only — the human sends.
"""
from typing import Any

DIVIDER = "─" * 72


def _key_metric(hospital: dict[str, Any]) -> str:
    lead = hospital.get("lead_angle", "")
    discharge_info = hospital.get("discharge_info_pct")
    well_baby = hospital.get("well_baby_visit_pct")
    state_avg = hospital.get("state_postpartum_avg")
    star = hospital.get("hcahps_care_transition_star")
    smm = hospital.get("smm_rate")

    if lead == "baby_vs_mother_contrast" and well_baby is not None and discharge_info is not None:
        return f"Well-baby {float(well_baby):g}% (state proxy) vs discharge-info {float(discharge_info):g}%"
    if lead == "hcahps_care_transition_gap" and star is not None:
        return f"Care transition {star}/5 stars"
    if lead == "smm_rate_gap" and smm is not None:
        return f"SMM {float(smm):.0f}/10K"
    if lead == "financial_unrealized":
        return "Medicaid extended"
    if lead == "state_strength_vs_hospital_lag" and discharge_info is not None and state_avg is not None:
        return f"Discharge-info {float(discharge_info):g}% vs state postpartum {float(state_avg):g}%"
    return "—"


def _decision_brief(hospital: dict[str, Any], email: dict[str, Any]) -> str:
    flag = hospital.get("urgency_flag", "")
    name = hospital.get("facility_name", "")
    score = int(hospital.get("gap_score", 0))
    lead = hospital.get("lead_angle", "")
    metric = _key_metric(hospital)
    role = email.get("recipient_role", "")
    return f"  {flag}  {name} · Gap {score} · {lead} · {metric} · {role}"


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
        _decision_brief(h, email),
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

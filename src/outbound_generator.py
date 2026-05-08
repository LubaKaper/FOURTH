"""
outbound_generator.py — Tool 5

Builds ADR send-contract email objects for Babyscripts outbound. During
tuning, generated emails are marked pending_review and are displayed by
the Human Checkpoint/dashboard before any production send path exists.
"""

import logging
import os
import re
from typing import Any

from dotenv import load_dotenv

try:
    import requests as _requests
    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False


load_dotenv()

log = logging.getLogger("fourth.outbound_generator")

_OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
_OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
_OPENROUTER_TIMEOUT_SECONDS = int(os.getenv("OPENROUTER_TIMEOUT_SECONDS", "10"))
_OPENROUTER_MAX_TOKENS = int(os.getenv("OPENROUTER_MAX_TOKENS", "450"))

VALID_LEAD_ANGLES = {
    "baby_vs_mother_contrast",
    "hcahps_care_transition_gap",
    "state_strength_vs_hospital_lag",
    "financial_unrealized",
    "smm_rate_gap",
}

RECIPIENT_ROLE_BY_LEAD = {
    "baby_vs_mother_contrast": "VP Patient Experience",
    "hcahps_care_transition_gap": "VP Patient Experience",
    "state_strength_vs_hospital_lag": "CMO",
    "financial_unrealized": "CMO",
    "smm_rate_gap": "CMO",
}

REQUIRED_TOOL_5_INPUT_FIELDS = [
    "facility_id",
    "facility_name",
    "gap_score",
    "urgency_tier",
    "data_confidence",
    "lead_angle",
]


def _validate_hospital_state(hospital: dict[str, Any]) -> None:
    facility_name = hospital.get("facility_name") or hospital.get("facility_id") or "unknown hospital"
    missing = [field for field in REQUIRED_TOOL_5_INPUT_FIELDS if field not in hospital]
    if missing:
        raise ValueError(f"Tool 5 received incomplete hospital state for {facility_name}: missing {', '.join(missing)}")

    gap_score = hospital.get("gap_score")
    if not isinstance(gap_score, int | float) or not 0 <= float(gap_score) <= 100:
        raise ValueError(f"Tool 5 received invalid gap_score for {facility_name}: {gap_score}")

    urgency_tier = hospital.get("urgency_tier")
    if urgency_tier not in ("high", "medium", "low"):
        raise ValueError(f"Tool 5 received invalid urgency_tier for {facility_name}: {urgency_tier}")

    data_confidence = hospital.get("data_confidence")
    if data_confidence not in ("high", "low"):
        raise ValueError(f"Tool 5 received invalid data_confidence for {facility_name}: {data_confidence}")

    lead_angle = hospital.get("lead_angle")
    if lead_angle not in VALID_LEAD_ANGLES:
        raise ValueError(f"Tool 5 received invalid lead_angle for {facility_name}: {lead_angle}")


def _subject(hospital: dict[str, Any]) -> str:
    return f"{hospital['facility_name']} postpartum follow-up gap"


def _format_pct(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return f"{float(value):g}%"
    except (TypeError, ValueError):
        return None


def _email_body(hospital: dict[str, Any]) -> str:
    name = hospital["facility_name"]
    lead = hospital["lead_angle"]
    commitment = hospital.get("commitment_tag") or "a CMS Birthing-Friendly commitment"
    postpartum = _format_pct(hospital.get("postpartum_visit_pct"))
    well_baby = _format_pct(hospital.get("well_baby_visit_pct"))
    state_avg = _format_pct(hospital.get("state_postpartum_avg"))

    if lead == "baby_vs_mother_contrast" and postpartum and well_baby:
        hook = (
            f"Your well-baby visit completion rate is {well_baby}. "
            f"Your postpartum maternal visit completion rate is {postpartum}. "
            "The system you built works — for babies."
        )
    elif lead == "hcahps_care_transition_gap":
        star = hospital.get("hcahps_care_transition_star")
        hook = f"{name}'s care transition signal is {star}/5 stars, creating a postpartum handoff risk."
    elif lead == "smm_rate_gap":
        hook = f"{name}'s maternal morbidity signal gives your team a reason to inspect postpartum follow-up."
    elif lead == "financial_unrealized":
        hook = "NY's 12-month postpartum Medicaid coverage creates a longer RPM follow-up window."
    elif state_avg and postpartum:
        hook = f"{name}'s postpartum visit rate is {postpartum} against a state benchmark of {state_avg}."
    else:
        hook = f"{name} has a reviewable postpartum follow-up gap."

    return (
        "Hi,\n\n"
        f"{name} made a public commitment: \"{commitment}.\"\n\n"
        f"{hook}\n\n"
        "Babyscripts supports remote postpartum monitoring with BP kits, a mobile app, "
        "OB-specialized care managers, and RPM CPT billing support. Hospitals using "
        "Babyscripts saw patients become 2x more likely to complete their 30-day "
        "postpartum visit.\n\n"
        "Worth a 15-minute look?\n\n"
        "Best,\n"
        "[YOUR NAME]"
    )


def _openrouter_prompt(hospital: dict[str, Any]) -> str:
    facts = {
        "hospital_name": hospital["facility_name"],
        "commitment_quote": hospital.get("commitment_tag"),
        "lead_angle": hospital.get("lead_angle"),
        "fourth_internal_gap_score_context_only_do_not_quote": hospital.get("gap_score"),
        "hcahps_care_transition_star": hospital.get("hcahps_care_transition_star"),
        "postpartum_visit_pct": hospital.get("postpartum_visit_pct"),
        "state_postpartum_avg": hospital.get("state_postpartum_avg"),
        "babyscripts_service": "remote postpartum monitoring: BP monitoring kit, mobile app, OB-specialized care managers, RPM CPT billing support",
        "babyscripts_proof": "Hospitals using Babyscripts saw patients become 2x more likely to complete their 30-day postpartum visit. Source: LCMC Health case study.",
    }
    return (
        "Write one concise cold outbound email body for a Babyscripts GTM Engineer to send to a hospital buyer.\n"
        "Audience: CMO or VP Patient Experience at the hospital.\n"
        "Rules:\n"
        "- Return only the email body, no JSON, markdown, subject line, or explanation.\n"
        "- Start with 'Hi,'.\n"
        "- Use the hospital name exactly.\n"
        "- Use only the provided facts; do not invent outcomes, customers, reimbursement amounts, or clinical claims.\n"
        "- The gap_score is Fourth's internal account score, not an HCAHPS score or HCAHPS rating.\n"
        "- Do not mention the gap_score or any internal Fourth score in the email body.\n"
        "- If mentioning HCAHPS, use only the HCAHPS care transition star rating as a 1-to-5 star value.\n"
        "- Mention Babyscripts and the proof point.\n"
        "- Keep it under 140 words.\n"
        "- End with a short CTA question.\n"
        f"Facts: {facts}"
    )


def _validate_llm_body(hospital: dict[str, Any], body: str) -> str:
    cleaned = body.strip()
    if not cleaned:
        raise ValueError("OpenRouter returned empty email body")
    if hospital["facility_name"] not in cleaned:
        raise ValueError("OpenRouter body did not include facility_name")
    if "Babyscripts" not in cleaned:
        raise ValueError("OpenRouter body did not include Babyscripts")
    if "2x" not in cleaned and "two times" not in cleaned.lower():
        raise ValueError("OpenRouter body did not include Babyscripts proof point")
    if len(cleaned.split()) > 170:
        raise ValueError("OpenRouter body exceeded length limit")
    unsupported = (
        "guarantee",
        "guaranteed",
        "cms reimbursement at risk",
        "penalty",
        "penalties",
        "mortality rate",
        "gap score",
    )
    lower = cleaned.lower()
    for phrase in unsupported:
        if phrase in lower:
            raise ValueError(f"OpenRouter body used unsupported claim: {phrase}")
    gap_score = hospital.get("gap_score")
    if gap_score is not None:
        gap_text = rf"{float(gap_score):g}(?:\.0)?"
        bad_gap_labels = (
            rf"hcahps[^.\n]{{0,60}}(?:score|rating)[^.\n]{{0,20}}{gap_text}",
            rf"(?:score|rating)[^.\n]{{0,20}}{gap_text}[^.\n]{{0,60}}hcahps",
            rf"care transition score[^.\n]{{0,20}}{gap_text}",
        )
        for pattern in bad_gap_labels:
            if re.search(pattern, lower):
                raise ValueError("OpenRouter body mislabeled gap_score as an HCAHPS score")
    return cleaned


def _call_openrouter(hospital: dict[str, Any]) -> str:
    if not _OPENROUTER_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    if not _REQUESTS_AVAILABLE:
        raise RuntimeError("requests is not installed")

    response = _requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {_OPENROUTER_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": _OPENROUTER_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "You write accurate, source-grounded B2B healthcare GTM email copy.",
                },
                {"role": "user", "content": _openrouter_prompt(hospital)},
            ],
            "temperature": 0.35,
            "max_tokens": _OPENROUTER_MAX_TOKENS,
        },
        timeout=(_OPENROUTER_TIMEOUT_SECONDS, _OPENROUTER_TIMEOUT_SECONDS),
    )
    response.raise_for_status()
    payload = response.json()
    body = payload["choices"][0]["message"].get("content", "")
    return _validate_llm_body(hospital, body)


def _generate_email_body(hospital: dict[str, Any]) -> tuple[str, str]:
    try:
        return _call_openrouter(hospital), "openrouter_api"
    except Exception as exc:
        log.warning(
            "Tool 5 — OpenRouter failed for %s; using template fallback: %s",
            hospital.get("facility_name", "unknown hospital"),
            exc,
        )
        return _email_body(hospital), "cached_fallback"


def _email_object(hospital: dict[str, Any], email_body: str) -> dict[str, Any]:
    return {
        "facility_id": hospital["facility_id"],
        "facility_name": hospital["facility_name"],
        "recipient_role": RECIPIENT_ROLE_BY_LEAD[hospital["lead_angle"]],
        "subject": _subject(hospital),
        "email_body": email_body,
        "product": "Babyscripts",
        "lead_angle": hospital["lead_angle"],
        "gap_score": float(hospital["gap_score"]),
        "urgency_tier": hospital["urgency_tier"],
        "sent_at": None,
        "status": "pending_review",
    }


def generate_outbound_email(hospitals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return one pending-review email object per eligible hospital."""
    for hospital in hospitals:
        _validate_hospital_state(hospital)

    eligible = [
        hospital
        for hospital in hospitals
        if hospital.get("data_confidence") == "high"
        and hospital.get("urgency_tier") in ("high", "medium")
        and float(hospital.get("gap_score") or 0) >= 40.0
    ]

    method_counts = {"openrouter_api": 0, "cached_fallback": 0}
    emails = []
    for hospital in eligible:
        email_body, generation_method = _generate_email_body(hospital)
        method_counts[generation_method] += 1
        emails.append(_email_object(hospital, email_body))

    log.info("Tool 5 — Generated %d Babyscripts emails", len(emails))
    log.info(
        "Tool 5 — generation_method openrouter_api=%d cached_fallback=%d",
        method_counts["openrouter_api"],
        method_counts["cached_fallback"],
    )
    return emails

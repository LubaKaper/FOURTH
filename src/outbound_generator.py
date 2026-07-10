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

try:
    import anthropic as _anthropic_sdk
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False


load_dotenv()

log = logging.getLogger("fourth.outbound_generator")

_OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
_OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
_OPENROUTER_TIMEOUT_SECONDS = int(os.getenv("OPENROUTER_TIMEOUT_SECONDS", "10"))
_OPENROUTER_MAX_TOKENS = int(os.getenv("OPENROUTER_MAX_TOKENS", "450"))

_ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")
_ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

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
    name = hospital["facility_name"]
    lead = hospital.get("lead_angle")
    postpartum = hospital.get("discharge_info_pct")
    well_baby = hospital.get("well_baby_visit_pct")
    state_avg = hospital.get("state_postpartum_avg")
    star = hospital.get("hcahps_care_transition_star")

    if lead == "baby_vs_mother_contrast" and well_baby is not None and postpartum is not None:
        gap = round(float(well_baby) - float(postpartum))
        return f"{name} — {gap}pt gap between well-baby and postpartum follow-up"
    if lead == "hcahps_care_transition_gap" and star is not None:
        return f"{name} — {star}/5 care transition score"
    if lead == "financial_unrealized":
        return f"{name} — RPM billing opportunity in your Medicaid mix"
    if lead == "smm_rate_gap":
        return f"{name} — maternal morbidity signal worth addressing"
    if lead == "state_strength_vs_hospital_lag" and postpartum is not None and state_avg is not None:
        lag = round(float(state_avg) - float(postpartum))
        return f"{name} — postpartum follow-up {lag}pt below NY average"
    return f"{name} — postpartum follow-up gap"


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
    postpartum = _format_pct(hospital.get("discharge_info_pct"))
    well_baby = _format_pct(hospital.get("well_baby_visit_pct"))
    state_avg = _format_pct(hospital.get("state_postpartum_avg"))

    proof = (
        "Hospitals using Babyscripts saw patients become 2x more likely to complete "
        "their 30-day postpartum visit."
    )
    sign_off = "Worth a 15-minute conversation?\n\nBest,\n[YOUR NAME]"

    if lead == "baby_vs_mother_contrast" and postpartum and well_baby:
        gap = round(float(hospital["well_baby_visit_pct"]) - float(hospital["discharge_info_pct"]))
        return (
            "Hi,\n\n"
            f"Across NY, well-baby visit completion averages {well_baby} — but postpartum "
            f"maternal completion at {name} sits at {postpartum}. That {gap}-point gap is "
            "where mothers fall through.\n\n"
            f"Babyscripts is built for exactly this: remote postpartum monitoring with BP kits, "
            f"a mobile app, OB-specialized care managers, and RPM CPT billing support. {proof}\n\n"
            f"{sign_off}"
        )

    if lead == "hcahps_care_transition_gap":
        star = hospital.get("hcahps_care_transition_star")
        return (
            "Hi,\n\n"
            f"{name}'s HCAHPS care transition score is {star}/5 stars. That's the discharge "
            "moment — the handoff where postpartum patients either stay connected to care or "
            "fall through.\n\n"
            f"Babyscripts closes that gap with remote postpartum monitoring: BP kits, mobile app, "
            f"OB-specialized care managers, and RPM CPT billing support. {proof}\n\n"
            f"{sign_off}"
        )

    if lead == "smm_rate_gap":
        return (
            "Hi,\n\n"
            f"{name}'s severe maternal morbidity signal is elevated. That's a clinical flag "
            "that often tracks with gaps in postpartum follow-up — the window where remote "
            "monitoring has the clearest impact.\n\n"
            f"Babyscripts provides that infrastructure: BP kits, mobile app, OB-specialized "
            f"care managers, and RPM CPT billing support. {proof}\n\n"
            f"{sign_off}"
        )

    if lead == "financial_unrealized":
        state = hospital.get("state", "NY")
        return (
            "Hi,\n\n"
            f"{state}'s 12-month postpartum Medicaid coverage creates a billing window most "
            "hospitals aren't fully capturing. Remote postpartum monitoring with RPM CPT codes "
            f"fits directly into that window — and {name} already has the patient population.\n\n"
            f"Babyscripts provides the infrastructure: BP kits, mobile app, OB-specialized "
            f"care managers, and billing support. {proof}\n\n"
            f"{sign_off}"
        )

    if state_avg and postpartum:
        return (
            "Hi,\n\n"
            f"{name}'s postpartum visit completion is at {postpartum} against a NY benchmark "
            f"of {state_avg}. Closing that gap is exactly what Babyscripts is built for — "
            "remote postpartum monitoring with BP kits, a mobile app, OB-specialized care "
            f"managers, and RPM CPT billing support. {proof}\n\n"
            f"{sign_off}"
        )

    return (
        "Hi,\n\n"
        f"{name} made a public commitment: \"{commitment}.\"\n\n"
        f"Babyscripts supports remote postpartum monitoring with BP kits, a mobile app, "
        f"OB-specialized care managers, and RPM CPT billing support. {proof}\n\n"
        f"{sign_off}"
    )


def _openrouter_prompt(hospital: dict[str, Any]) -> str:
    lead = hospital.get("lead_angle")
    facts: dict[str, Any] = {
        "hospital_name": hospital["facility_name"],
        "commitment_quote": hospital.get("commitment_tag"),
        "lead_angle": lead,
        "fourth_internal_gap_score_context_only_do_not_quote": hospital.get("gap_score"),
        "hcahps_care_transition_star": hospital.get("hcahps_care_transition_star"),
        "discharge_info_pct": hospital.get("discharge_info_pct"),
        "state_postpartum_avg": hospital.get("state_postpartum_avg"),
        "babyscripts_service": "remote postpartum monitoring: BP monitoring kit, mobile app, OB-specialized care managers, RPM CPT billing support",
        "babyscripts_proof": "Hospitals using Babyscripts saw patients become 2x more likely to complete their 30-day postpartum visit. Source: LCMC Health case study.",
    }
    if lead == "baby_vs_mother_contrast":
        facts["well_baby_visit_pct"] = hospital.get("well_baby_visit_pct")
    if lead == "smm_rate_gap":
        facts["smm_rate"] = hospital.get("smm_rate")
    return (
        "Write one concise cold outbound email body for a Babyscripts GTM Engineer to send to a hospital buyer.\n"
        "Audience: CMO or VP Patient Experience at the hospital.\n"
        "\n"
        "Tone and framing:\n"
        "- Write as a peer reaching out to a healthcare professional, not as a vendor pitching a product.\n"
        "- Lead with the insight or implication first — not the raw numbers. Make the reader feel the gap before they see the data.\n"
        "- Do not open with the hospital name as the first word. Vary your opening.\n"
        "- Avoid buzzwords: 'opportunity', 'solutions', 'leverage', 'synergy', 'innovative'.\n"
        "- Be specific and concrete. One clear idea per paragraph.\n"
        "\n"
        "Rules:\n"
        "- Return only the email body, no JSON, markdown, subject line, or explanation.\n"
        "- Start with 'Hi,'.\n"
        f"- Use the hospital name exactly as provided: \"{hospital['facility_name']}\". Do not shorten, abbreviate, or paraphrase it.\n"
        "- Use only the provided facts; do not invent outcomes, customers, reimbursement amounts, or clinical claims.\n"
        "- The gap_score is Fourth's internal account score — do not mention it in the email.\n"
        "- If mentioning HCAHPS, use only the care transition star rating as a 1-to-5 star value.\n"
        '- You MUST include this exact sentence: "Hospitals using Babyscripts saw patients become 2x more likely to complete their 30-day postpartum visit."\n'
        "- Keep it under 140 words.\n"
        "- End with a specific, low-friction CTA question (not 'Worth a chat?').\n"
        "\n"
        f"Facts: {facts}"
    )


def _validate_llm_body(hospital: dict[str, Any], body: str) -> str:
    cleaned = body.strip()
    if not cleaned:
        raise ValueError("LLM returned empty email body")
    if hospital["facility_name"] not in cleaned:
        raise ValueError("LLM body did not include facility_name")
    if "Babyscripts" not in cleaned:
        raise ValueError("LLM body did not include Babyscripts")
    if "2x" not in cleaned and "two times" not in cleaned.lower():
        raise ValueError("LLM body did not include Babyscripts proof point")
    if len(cleaned.split()) > 170:
        raise ValueError("LLM body exceeded length limit")
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
            raise ValueError(f"LLM body used unsupported claim: {phrase}")
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
                raise ValueError("LLM body mislabeled gap_score as an HCAHPS score")

    # Percentage grounding — every XX% in the body must match a hospital outcome field within 1 point
    pct_fields = [
        v for v in (
            hospital.get("discharge_info_pct"),
            hospital.get("well_baby_visit_pct"),
            hospital.get("state_postpartum_avg"),
        )
        if v is not None
    ]
    for raw in re.findall(r"(\d+\.?\d*)%", cleaned):
        cited = float(raw)
        if not any(abs(cited - f) <= 1.0 for f in pct_fields):
            raise ValueError(
                f"ungrounded percentage: {raw}% not within 1 point of any hospital outcome field"
            )

    # Star rating grounding — every X/5 in the body must match an HCAHPS field exactly
    star_fields = {
        v for v in (
            hospital.get("hcahps_care_transition_star"),
            hospital.get("hcahps_overall_star"),
        )
        if v is not None
    }
    for raw in re.findall(r"(\d+)/5", cleaned):
        cited = int(raw)
        if cited not in star_fields:
            raise ValueError(
                f"ungrounded star rating: {raw}/5 not in hospital HCAHPS fields"
            )

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
    body = payload["choices"][0]["message"].get("content") or ""
    return _validate_llm_body(hospital, body)


def _call_anthropic(hospital: dict[str, Any]) -> str:
    if not _ANTHROPIC_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    if not _ANTHROPIC_AVAILABLE:
        raise RuntimeError("anthropic package is not installed")

    client = _anthropic_sdk.Anthropic(api_key=_ANTHROPIC_KEY)
    message = client.messages.create(
        model=_ANTHROPIC_MODEL,
        max_tokens=_OPENROUTER_MAX_TOKENS,
        system="You write accurate, source-grounded B2B healthcare GTM email copy.",
        messages=[{"role": "user", "content": _openrouter_prompt(hospital)}],
    )
    body = (message.content[0].text if message.content else "") or ""
    return _validate_llm_body(hospital, body)


def _generate_email_body(hospital: dict[str, Any]) -> tuple[str, str, str]:
    name = hospital.get("facility_name", "unknown hospital")

    try:
        return _call_openrouter(hospital), "openrouter_api", ""
    except Exception as exc:
        openrouter_reason = str(exc)
        log.warning("Tool 5 — OpenRouter failed for %s; trying Anthropic: %s", name, openrouter_reason)

    try:
        return _call_anthropic(hospital), "anthropic_api", ""
    except Exception as exc:
        anthropic_reason = str(exc)
        log.warning("Tool 5 — Anthropic failed for %s; using template fallback: %s", name, anthropic_reason)
        combined_reason = f"OpenRouter: {openrouter_reason}; Anthropic: {anthropic_reason}"
        return _email_body(hospital), "cached_fallback", combined_reason


def _angle_reason(hospital: dict[str, Any]) -> str:
    lead = hospital.get("lead_angle", "")
    postpartum = hospital.get("discharge_info_pct")
    well_baby = hospital.get("well_baby_visit_pct")
    state_avg = hospital.get("state_postpartum_avg")
    star = hospital.get("hcahps_care_transition_star")
    smm = hospital.get("smm_rate")

    if lead == "baby_vs_mother_contrast" and well_baby is not None and postpartum is not None:
        gap = float(well_baby) - float(postpartum)
        return f"Well-baby {float(well_baby):g}% vs postpartum {float(postpartum):g}% — {gap:.0f}pt gap"
    if lead == "hcahps_care_transition_gap" and star is not None:
        return f"Care transition {star}/5 stars — below 3-star threshold"
    if lead == "smm_rate_gap" and smm is not None:
        return f"SMM rate {float(smm):.0f}/10K deliveries — above 150 benchmark"
    if lead == "financial_unrealized":
        return "Medicaid extended — RPM coverage window available"
    if lead == "state_strength_vs_hospital_lag" and postpartum is not None and state_avg is not None:
        lag = float(state_avg) - float(postpartum)
        return f"Postpartum {float(postpartum):g}% vs state avg {float(state_avg):g}% — {lag:.0f}pt lag"
    return f"Lead angle: {lead}"


def _email_object(hospital: dict[str, Any], email_body: str) -> dict[str, Any]:
    return {
        "facility_id": hospital["facility_id"],
        "facility_name": hospital["facility_name"],
        "recipient_role": RECIPIENT_ROLE_BY_LEAD[hospital["lead_angle"]],
        "subject": _subject(hospital),
        "email_body": email_body,
        "product": "Babyscripts",
        "lead_angle": hospital["lead_angle"],
        "angle_reason": _angle_reason(hospital),
        "gap_score": float(hospital["gap_score"]),
        "urgency_tier": hospital["urgency_tier"],
        "sent_at": None,
        "status": "pending_review",
        "claim_validation": "passed",
        "data_confidence": hospital["data_confidence"],
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

    method_counts = {"openrouter_api": 0, "anthropic_api": 0, "cached_fallback": 0}
    fallback_details: list[tuple[str, str]] = []
    emails = []
    for hospital in eligible:
        email_body, generation_method, fallback_reason = _generate_email_body(hospital)
        method_counts[generation_method] += 1
        if generation_method == "cached_fallback":
            fallback_details.append((hospital["facility_name"], fallback_reason))
        emails.append(_email_object(hospital, email_body))

    log.info("Tool 5 — Generated %d Babyscripts emails", len(emails))
    log.info(
        "Tool 5 — generation_method openrouter_api=%d anthropic_api=%d cached_fallback=%d",
        method_counts["openrouter_api"],
        method_counts["anthropic_api"],
        method_counts["cached_fallback"],
    )
    if fallback_details:
        for name, reason in fallback_details:
            log.warning("Tool 5 — Fallback summary: %s — %s", name, reason)
    return emails

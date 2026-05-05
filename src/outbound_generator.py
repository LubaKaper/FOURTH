"""
outbound_generator.py — Tool 5 | Owner: Paula

Generates 3 email variants (moral, clinical, financial) per high/medium
urgency hospital. Low urgency and low data_confidence hospitals are skipped.

generation_method is "openrouter_api" when OpenRouter succeeds;
"cached_fallback" when commitment_tag is None or the API call fails.

[COMPANY_NAME] and [SOCIAL_PROOF] are placeholders — the GTM engineer
fills these in before sending. Nothing is sent by this tool.
"""
import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from dotenv import load_dotenv

load_dotenv()

try:
    import requests as _requests
    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False

_OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
_OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "poolside/laguna-m.1:free")
_OPENROUTER_FALLBACK_MODELS = [
    model.strip()
    for model in os.getenv("OPENROUTER_FALLBACK_MODELS", "tencent/hy3-preview:free").split(",")
    if model.strip()
]


def _int_env(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return max(value, 0)


_OPENROUTER_TIMEOUT_SECONDS = _int_env("OPENROUTER_TIMEOUT_SECONDS", 5)
_OPENROUTER_MAX_LIVE_EMAILS = _int_env("OPENROUTER_MAX_LIVE_EMAILS", 1)
_OPENROUTER_CONCURRENCY = _int_env("OPENROUTER_CONCURRENCY", 1)
_OPENROUTER_MAX_TOKENS = _int_env("OPENROUTER_MAX_TOKENS", 1200)
_OPENROUTER_RETRIES = _int_env("OPENROUTER_RETRIES", 1)
_OPENROUTER_USE_FALLBACK_MODELS = os.getenv("OPENROUTER_USE_FALLBACK_MODELS", "false").lower() == "true"
_OPENROUTER_JSON_MODE = os.getenv("OPENROUTER_JSON_MODE", "false").lower() == "true"

log = logging.getLogger("echo.outbound_generator")

TO_ROLE_BY_LEAD = {
    "hcahps_care_transition_gap": "CMO",
    "hcahps_discharge_gap": "VP of Women's Services",
    "state_strength_vs_hospital_lag": "VP of Quality",
}

BODY_KEYS = ["body_moral", "body_clinical", "body_financial"]

UNSUPPORTED_CLAIMS = [
    "cms reimbursement at risk",
    "payment",
    "payment adjustment",
    "payment adjustments",
    "revenue loss",
    "readmission",
    "readmissions",
    "penalty",
    "penalties",
    "mortality rate",
    "severe maternal morbidity",
]

MISREAD_DISCHARGE_HELP_PATTERNS = [
    "need help",
    "needs help",
    "needed help",
    "need support",
    "needs support",
    "needed support",
]

REQUIRED_TOOL_5_INPUT_FIELDS = [
    "facility_id",
    "facility_name",
    "gap_score",
    "urgency_tier",
    "data_confidence",
    "lead_angle",
]


def _subject(h: dict[str, Any]) -> str:
    return f"{h['facility_name']} — postpartum discharge gap vs. Birthing-Friendly commitment"


def _body_moral(h: dict[str, Any]) -> str:
    tag = h.get("commitment_tag") or "a CMS Birthing-Friendly commitment"
    name = h["facility_name"]
    pct = h.get("discharge_help_pct")
    discharge_star = h.get("discharge_info_star")
    overall_star = h.get("overall_star")
    star_line = ""
    if discharge_star is not None and overall_star is not None:
        star_line = f"That sits beside {discharge_star}/5 discharge information and {overall_star}/5 overall HCAHPS stars."
    pct_line = f"{pct}% of patients said they got enough help after discharge." if pct else "Discharge help data is limited."
    return f"""Hi,

{name} made a public commitment: "{tag}".

{pct_line} {star_line}

That is the gap ECHO flags: public commitment on one side, patient-reported handoff friction on the other.

[COMPANY_NAME] helps maternal health teams make the discharge-to-postpartum handoff visible. [SOCIAL_PROOF]

Worth a 15-minute look?

Best,
[YOUR NAME]"""


def _body_clinical(h: dict[str, Any]) -> str:
    tag = h.get("commitment_tag") or "a CMS Birthing-Friendly commitment"
    name = h["facility_name"]
    state = h.get("state", "")
    discharge_pct = h.get("discharge_help_pct")
    state_rate = h.get("state_postpartum_visit_rate")
    discharge_star = h.get("discharge_info_star")
    overall_star = h.get("overall_star")

    discharge_line = f"{discharge_pct}% of patients said they got enough discharge help." if discharge_pct else "Discharge help data is unavailable."
    star_line = ""
    if discharge_star is not None:
        star_line = f"Discharge information is {discharge_star}/5 stars; overall experience is {overall_star}/5."
    state_line = (
        f"{state}'s postpartum visit rate is {state_rate}%, so the state has a follow-up baseline to work from."
        if state_rate else ""
    )

    return f"""Hi,

{name} has a discharge handoff problem hiding in plain sight.

{star_line}
{discharge_line}
{state_line}

If patients do not leave with clear next steps, postpartum follow-up gets harder before the first visit is even scheduled.

[COMPANY_NAME] helps teams catch and route postpartum follow-up work after discharge. [SOCIAL_PROOF]

Should I send the one-page workflow?

Best,
[YOUR NAME]"""


def _body_financial(h: dict[str, Any]) -> str:
    tag = h.get("commitment_tag") or "a CMS Birthing-Friendly commitment"
    name = h["facility_name"]
    state = h.get("state", "")
    medicaid_extended = h.get("medicaid_extended", False)
    medicaid_line = (
        f"{state} has 12-month postpartum Medicaid coverage, which keeps the follow-up window open longer."
        if medicaid_extended
        else "Federal postpartum Medicaid policy is expanding reimbursement windows across states."
    )

    return f"""Hi,

{name} is operating in a state where postpartum coverage lasts beyond the delivery episode.

{medicaid_line}

The operational question is whether discharge teams can reliably hand patients into that longer follow-up window.

[COMPANY_NAME] helps maternal health teams track that handoff from discharge into postpartum care. [SOCIAL_PROOF]

Worth a 15-minute look?

Best,
[YOUR NAME]"""


def _openrouter_models() -> list[str]:
    models = [_OPENROUTER_MODEL]
    if _OPENROUTER_USE_FALLBACK_MODELS:
        models.extend(_OPENROUTER_FALLBACK_MODELS)
    deduped = []
    for model in models:
        if model and model not in deduped:
            deduped.append(model)
    return deduped


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
    if lead_angle not in TO_ROLE_BY_LEAD:
        raise ValueError(f"Tool 5 received invalid lead_angle for {facility_name}: {lead_angle}")


def _validate_generated_bodies(data: dict[str, Any]) -> tuple[str, str, str]:
    bodies = []
    for key in BODY_KEYS:
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"OpenRouter response missing {key}")

        lower_value = value.lower()
        if "[company_name]" not in lower_value or "[social_proof]" not in lower_value:
            raise ValueError(f"OpenRouter response missing placeholders in {key}")
        if len(value.split()) > 115:
            raise ValueError(f"OpenRouter response too long in {key}")

        for claim in UNSUPPORTED_CLAIMS:
            if claim in lower_value:
                raise ValueError(f"OpenRouter response used unsupported claim in {key}: {claim}")

        bodies.append(value.strip())
    return bodies[0], bodies[1], bodies[2]


def _extract_json_object(content: str) -> str:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("OpenRouter response did not contain a JSON object")
    return cleaned[start:end + 1]


def _parse_quoted_body_fields(content: str) -> dict[str, Any] | None:
    parsed = {}
    for key in BODY_KEYS:
        match = re.search(rf'"{key}"\s*:\s*"((?:\\.|[^"\\])*)"', content, flags=re.DOTALL)
        if not match:
            return None
        raw_value = match.group(1)
        try:
            parsed[key] = json.loads(f'"{raw_value}"')
        except json.JSONDecodeError:
            parsed[key] = json.loads(f'"{raw_value.replace(chr(10), r"\n")}"')
    return parsed


def _parse_labeled_body_fields(content: str) -> dict[str, Any] | None:
    labels = {
        "body_moral": r"(?:body_moral|moral(?: angle| variant)?)",
        "body_clinical": r"(?:body_clinical|clinical(?: angle| variant)?)",
        "body_financial": r"(?:body_financial|financial(?: angle| variant)?)",
    }
    combined = "|".join(f"(?P<{key}>{pattern})" for key, pattern in labels.items())
    label_prefix = r"^\s*(?:[-*]\s*)?(?:#{1,4}\s*)?(?:\*\*)?(?:`)?"
    label_suffix = r"(?:`)?(?:\*\*)?\s*(?:[:\-–—]|\n)\s*"
    matches = list(
        re.finditer(
            rf"{label_prefix}(?:{combined}){label_suffix}",
            content,
            flags=re.IGNORECASE | re.MULTILINE,
        )
    )
    if len(matches) < 3:
        return None

    parsed = {}
    for index, match in enumerate(matches):
        key = match.lastgroup
        if key is None:
            return None
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        parsed[key] = content[start:end].strip().strip('"')

    return parsed if all(parsed.get(key) for key in BODY_KEYS) else None


def _parse_openrouter_json(content: str) -> dict[str, Any]:
    loose_labeled = _parse_labeled_body_fields(content)
    if loose_labeled is not None:
        return loose_labeled

    json_text = _extract_json_object(content)
    try:
        return json.loads(json_text)
    except json.JSONDecodeError as original_error:
        loose_json = _parse_quoted_body_fields(json_text)
        if loose_json is not None:
            return loose_json
        # Some free models emit literal newlines inside strings. Preserve strict
        # JSON behavior for everything else, but repair that common formatting bug.
        repaired = []
        in_string = False
        escaped = False
        for char in json_text:
            if char == '"' and not escaped:
                in_string = not in_string
            if char == "\n" and in_string:
                repaired.append("\\n")
            else:
                repaired.append(char)
            escaped = char == "\\" and not escaped
        try:
            return json.loads("".join(repaired))
        except json.JSONDecodeError:
            raise original_error


def _normalize_social_proof_placeholder(text: str) -> str:
    replacements = [
        (r"\bhelped\s+\[SOCIAL_PROOF\]", "[SOCIAL_PROOF]"),
        (r"\bsupports\s+\[SOCIAL_PROOF\]", "[SOCIAL_PROOF]"),
        (r"\bsupported\s+\[SOCIAL_PROOF\]", "[SOCIAL_PROOF]"),
        (r"\bwith\s+\[SOCIAL_PROOF\]", "[SOCIAL_PROOF]"),
    ]
    normalized = text
    for pattern, replacement in replacements:
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
    return normalized


def _ensure_required_placeholders(text: str) -> str:
    normalized = text.strip()
    missing = []
    lower_text = normalized.lower()
    if "[company_name]" not in lower_text:
        missing.append("[COMPANY_NAME]")
    if "[social_proof]" not in lower_text:
        missing.append("[SOCIAL_PROOF]")
    if missing:
        normalized = f"{normalized} {' '.join(missing)}"
    return normalized


def _normalize_generated_data(data: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(data)
    for key in BODY_KEYS:
        value = normalized.get(key)
        if isinstance(value, str):
            normalized[key] = _ensure_required_placeholders(_normalize_social_proof_placeholder(value))
    return normalized


def _validate_generated_email(hospital: dict[str, Any], data: dict[str, Any]) -> tuple[str, str, str]:
    bodies = _validate_generated_bodies(_normalize_generated_data(data))
    facility_name = hospital["facility_name"]
    discharge_help_pct = hospital.get("discharge_help_pct")

    for body in bodies:
        lower_body = body.lower()
        if facility_name not in body:
            raise ValueError("OpenRouter response did not use full facility_name")
        if "helped [SOCIAL_PROOF]" in body or "supports [SOCIAL_PROOF]" in body:
            raise ValueError("OpenRouter response used awkward social proof placeholder")
        if discharge_help_pct is not None:
            pct_prefix = f"{discharge_help_pct:g}%"
            if pct_prefix in body and any(pattern in lower_body for pattern in MISREAD_DISCHARGE_HELP_PATTERNS):
                raise ValueError("OpenRouter response misread discharge_help_pct as unmet need")

    return bodies


def _is_rate_limit_error(exc: Exception) -> bool:
    response = getattr(exc, "response", None)
    return getattr(response, "status_code", None) == 429


def _call_openrouter(h: dict[str, Any], model: str) -> tuple[str, str, str]:
    """Call OpenRouter to generate personalized email bodies. Raises on failure."""
    tag = h.get("commitment_tag")
    name = h["facility_name"]
    state = h.get("state", "")
    discharge_pct = h.get("discharge_help_pct")
    state_rate = h.get("state_postpartum_visit_rate")
    discharge_star = h.get("discharge_info_star")
    overall_star = h.get("overall_star")
    medicaid_extended = h.get("medicaid_extended", False)
    lead = h.get("lead_angle", "state_strength_vs_hospital_lag")

    system_prompt = (
        "Return only valid compact JSON. No markdown. No explanation. Total response under 700 tokens. "
        "Write direct GTM cold email copy. "
        "Use only provided facts. Use full facility name exactly. Include [COMPANY_NAME] and [SOCIAL_PROOF]. "
        "If using discharge_help_pct, phrase it as 'X% said they got enough help after discharge'; never say X% need help. "
        "Do not mention reimbursement risk, penalties, payment, readmissions, mortality, severe morbidity, or national average. "
        "Do not use generic phrases: optimizes workflows, streamlines care, boost outcomes, tailored clinical pathways. "
        "Do not write helped [SOCIAL_PROOF] or supports [SOCIAL_PROOF]."
    )

    facts = {
        "facility_name": name,
        "state": state,
        "commitment": tag,
        "lead_angle": lead,
        "discharge_help_pct": discharge_pct,
        "discharge_info_star": discharge_star,
        "overall_star": overall_star,
        "state_postpartum_visit_rate": state_rate,
        "medicaid_extended": medicaid_extended,
    }
    prompt = (
        "Create 3 email bodies as JSON keys body_moral, body_clinical, body_financial. "
        "Each body: 45-70 words, starts 'Hi,', uses facility_name exactly, cites 1-2 facts, "
        "includes [COMPANY_NAME] and [SOCIAL_PROOF], ends with a CTA question. "
        "Angles: moral=commitment vs patient experience; clinical=discharge support to postpartum handoff; "
        "financial=12-month Medicaid coverage means longer follow-up window, not revenue. "
        f"Facts: {json.dumps(facts, separators=(',', ':'))}"
    )

    request_payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.35,
        "max_tokens": _OPENROUTER_MAX_TOKENS,
    }
    if _OPENROUTER_JSON_MODE:
        request_payload["response_format"] = {"type": "json_object"}

    resp = _requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {_OPENROUTER_KEY}",
            "Content-Type": "application/json",
        },
        json=request_payload,
        timeout=(_OPENROUTER_TIMEOUT_SECONDS, _OPENROUTER_TIMEOUT_SECONDS),
    )
    resp.raise_for_status()
    payload = resp.json()
    choice = payload["choices"][0]
    content = choice["message"].get("content")
    if not content:
        finish_reason = choice.get("finish_reason", "unknown")
        raise ValueError(f"OpenRouter returned empty content (finish_reason={finish_reason})")
    data = _parse_openrouter_json(content)
    return _validate_generated_email(h, data)


def _try_openrouter(
    h: dict[str, Any],
    attempt_number: int,
    total_attempts: int,
) -> tuple[str, str, str] | None:
    log.info(
        "Tool 5 — OpenRouter attempt %d/%d for %s",
        attempt_number,
        total_attempts,
        h.get("facility_name", "unknown hospital"),
    )
    for model in _openrouter_models():
        for retry_index in range(_OPENROUTER_RETRIES + 1):
            retry_label = f" retry {retry_index}/{_OPENROUTER_RETRIES}" if retry_index else ""
            log.info("Tool 5 — Trying OpenRouter model %s%s", model, retry_label)
            try:
                bodies = _call_openrouter(h, model)
                log.info("Tool 5 — OpenRouter model %s succeeded", model)
                return bodies
            except Exception as exc:
                log.warning("Tool 5 — OpenRouter model %s failed%s: %s", model, retry_label, exc)
                if _is_rate_limit_error(exc):
                    log.warning("Tool 5 — OpenRouter rate limit hit; using cached fallback for this hospital")
                    return None
    return None


def _cached_bodies(h: dict[str, Any]) -> tuple[str, str, str]:
    return _body_moral(h), _body_clinical(h), _body_financial(h)


def _email_object(
    h: dict[str, Any],
    tier: str,
    bodies: tuple[str, str, str],
    generation_method: str,
) -> dict[str, Any]:
    lead = h.get("lead_angle", "state_strength_vs_hospital_lag")
    body_moral, body_clinical, body_financial = bodies
    return {
        "facility_id": h["facility_id"],
        "subject": _subject(h),
        "to_role": TO_ROLE_BY_LEAD.get(lead, "VP of Women's Services"),
        "body_moral": body_moral,
        "body_clinical": body_clinical,
        "body_financial": body_financial,
        "lead_angle_used": lead,
        "urgency_tier": tier,
        "generation_method": generation_method,
    }


def generate_outbound_email(hospitals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return one email dict per high/medium urgency, high data_confidence hospital."""
    for h in hospitals:
        _validate_hospital_state(h)

    eligible = []
    for h in hospitals:
        if h.get("data_confidence") == "low":
            continue
        tier = h.get("urgency_tier")
        if tier not in ("high", "medium"):
            continue
        eligible.append((h, tier))

    live_candidates = [
        (index, h)
        for index, (h, _tier) in enumerate(eligible)
        if h.get("commitment_tag") and _OPENROUTER_KEY and _REQUESTS_AVAILABLE
    ][:_OPENROUTER_MAX_LIVE_EMAILS]

    live_results: dict[int, tuple[str, str, str]] = {}
    if live_candidates:
        worker_count = max(1, min(_OPENROUTER_CONCURRENCY, len(live_candidates)))
        log.info("Tool 5 — OpenRouter concurrency=%d", worker_count)
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = {
                executor.submit(_try_openrouter, h, attempt_number, len(live_candidates)): index
                for attempt_number, (index, h) in enumerate(live_candidates, start=1)
            }
            for future in as_completed(futures):
                index = futures[future]
                bodies = future.result()
                if bodies is not None:
                    live_results[index] = bodies

    results = []
    for index, (h, tier) in enumerate(eligible):
        if index in live_results:
            results.append(_email_object(h, tier, live_results[index], "openrouter_api"))
        else:
            results.append(_email_object(h, tier, _cached_bodies(h), "cached_fallback"))
    return results

# tests/test_outbound_generator.py
import copy
import sys
import os
import pytest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.fixtures import HIGH_GAP, MEDIUM_GAP, LOW_GAP, NULL_DATA
from src.gap_calculator import calculate_gap_score
from src.urgency_ranker import add_urgency
import src.outbound_generator as outbound_generator
from src.outbound_generator import generate_outbound_email

BANNED_COMPANIES = ["Babyscripts", "Maven", "Wildflower", "Mahmee", "Bloomlife", "Cocoon"]
VALID_ROLES = {"CMO", "VP of Women's Services", "Chief Nursing Officer", "VP of Quality"}
BODY_KEYS = ["body_moral", "body_clinical", "body_financial"]
REQUIRED_FIELDS = [
    "facility_id", "subject", "to_role",
    "body_moral", "body_clinical", "body_financial",
    "lead_angle_used", "urgency_tier", "generation_method",
]


def _run(fixture):
    return add_urgency(calculate_gap_score(copy.deepcopy(fixture)))


# ── filtering ──────────────────────────────────────────────────────────────────

def test_low_urgency_skipped():
    emails = generate_outbound_email([_run(LOW_GAP)])
    assert len(emails) == 0


def test_missing_tool_4_state_raises_value_error():
    h = copy.deepcopy(HIGH_GAP)
    with pytest.raises(ValueError, match="missing gap_score"):
        generate_outbound_email([h])


def test_invalid_gap_score_raises_value_error():
    h = _run(HIGH_GAP)
    h["gap_score"] = 125
    with pytest.raises(ValueError, match="invalid gap_score"):
        generate_outbound_email([h])


def test_invalid_urgency_tier_raises_value_error():
    h = _run(HIGH_GAP)
    h["urgency_tier"] = "urgent"
    with pytest.raises(ValueError, match="invalid urgency_tier"):
        generate_outbound_email([h])


def test_invalid_data_confidence_raises_value_error():
    h = _run(HIGH_GAP)
    h["data_confidence"] = "medium"
    with pytest.raises(ValueError, match="invalid data_confidence"):
        generate_outbound_email([h])


def test_invalid_lead_angle_raises_value_error():
    h = _run(HIGH_GAP)
    h["lead_angle"] = "unknown_gap"
    with pytest.raises(ValueError, match="invalid lead_angle"):
        generate_outbound_email([h])


def test_high_and_medium_included():
    emails = generate_outbound_email([_run(HIGH_GAP), _run(MEDIUM_GAP), _run(LOW_GAP)])
    assert len(emails) == 2


def test_empty_list_returns_empty():
    assert generate_outbound_email([]) == []


def test_low_data_confidence_skipped():
    h = _run(NULL_DATA)
    assert h.get("data_confidence") == "low"
    emails = generate_outbound_email([h])
    assert len(emails) == 0


# ── output shape ───────────────────────────────────────────────────────────────

def test_output_has_all_fields():
    email = generate_outbound_email([_run(HIGH_GAP)])[0]
    for field in REQUIRED_FIELDS:
        assert field in email, f"Missing field: {field}"


def test_facility_id_copied():
    email = generate_outbound_email([_run(HIGH_GAP)])[0]
    assert email["facility_id"] == HIGH_GAP["facility_id"]


def test_urgency_tier_copied():
    email = generate_outbound_email([_run(HIGH_GAP)])[0]
    assert email["urgency_tier"] == "high"


def test_lead_angle_used_matches_pipeline():
    h = _run(HIGH_GAP)
    email = generate_outbound_email([h])[0]
    assert email["lead_angle_used"] == h["lead_angle"]


# ── generation_method ──────────────────────────────────────────────────────────

def test_generation_method_is_valid():
    email = generate_outbound_email([_run(HIGH_GAP)])[0]
    assert email["generation_method"] in ("openrouter_api", "cached_fallback")


def test_generation_method_openrouter_on_success():
    h = _run(HIGH_GAP)
    mock_bodies = ("moral body [COMPANY_NAME]", "clinical body [COMPANY_NAME]", "financial body [COMPANY_NAME]")
    with patch("src.outbound_generator._OPENROUTER_KEY", "fake-key"), \
         patch("src.outbound_generator._REQUESTS_AVAILABLE", True), \
         patch("src.outbound_generator._call_openrouter", return_value=mock_bodies):
        email = generate_outbound_email([h])[0]
    assert email["generation_method"] == "openrouter_api"


def test_openrouter_tries_preferred_model_first_then_fallback_models():
    h = _run(HIGH_GAP)
    mock_bodies = ("moral body [COMPANY_NAME]", "clinical body [COMPANY_NAME]", "financial body [COMPANY_NAME]")
    calls = []

    def fake_call(hospital, model):
        calls.append(model)
        if model == "poolside/laguna-m.1:free":
            raise Exception("preferred unavailable")
        return mock_bodies

    with patch("src.outbound_generator._OPENROUTER_KEY", "fake-key"), \
         patch("src.outbound_generator._REQUESTS_AVAILABLE", True), \
         patch("src.outbound_generator._OPENROUTER_MODEL", "poolside/laguna-m.1:free"), \
         patch("src.outbound_generator._OPENROUTER_FALLBACK_MODELS", ["tencent/hy3-preview:free"]), \
         patch("src.outbound_generator._OPENROUTER_USE_FALLBACK_MODELS", True), \
         patch("src.outbound_generator._OPENROUTER_RETRIES", 0), \
         patch("src.outbound_generator._call_openrouter", side_effect=fake_call):
        email = generate_outbound_email([h])[0]

    assert calls == ["poolside/laguna-m.1:free", "tencent/hy3-preview:free"]
    assert email["generation_method"] == "openrouter_api"


def test_openrouter_live_generation_respects_max_live_email_cap():
    high = _run(HIGH_GAP)
    medium = _run(MEDIUM_GAP)
    mock_bodies = ("moral body [COMPANY_NAME]", "clinical body [COMPANY_NAME]", "financial body [COMPANY_NAME]")

    with patch("src.outbound_generator._OPENROUTER_KEY", "fake-key"), \
         patch("src.outbound_generator._REQUESTS_AVAILABLE", True), \
         patch("src.outbound_generator._OPENROUTER_MAX_LIVE_EMAILS", 1), \
         patch("src.outbound_generator._call_openrouter", return_value=mock_bodies) as call:
        emails = generate_outbound_email([high, medium])

    assert call.call_count == 1
    assert [email["generation_method"] for email in emails] == [
        "openrouter_api",
        "cached_fallback",
    ]


def test_openrouter_parallel_generation_preserves_input_order():
    high = _run(HIGH_GAP)
    medium = _run(MEDIUM_GAP)

    def fake_call(hospital, model):
        return (
            f"moral body for {hospital['facility_name']} [COMPANY_NAME]",
            f"clinical body for {hospital['facility_name']} [COMPANY_NAME]",
            f"financial body for {hospital['facility_name']} [COMPANY_NAME]",
        )

    with patch("src.outbound_generator._OPENROUTER_KEY", "fake-key"), \
         patch("src.outbound_generator._REQUESTS_AVAILABLE", True), \
         patch("src.outbound_generator._OPENROUTER_MAX_LIVE_EMAILS", 2), \
         patch("src.outbound_generator._OPENROUTER_CONCURRENCY", 2), \
         patch("src.outbound_generator._call_openrouter", side_effect=fake_call):
        emails = generate_outbound_email([high, medium])

    assert [email["facility_id"] for email in emails] == [
        high["facility_id"],
        medium["facility_id"],
    ]
    assert [email["generation_method"] for email in emails] == [
        "openrouter_api",
        "openrouter_api",
    ]


def test_openrouter_call_uses_configured_timeout():
    h = _run(HIGH_GAP)
    response = type("Response", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: {
            "choices": [{
                "message": {
                    "content": (
                        '{"body_moral":"Hi, Test High Gap Hospital moral [COMPANY_NAME]. [SOCIAL_PROOF]",'
                        '"body_clinical":"Hi, Test High Gap Hospital clinical [COMPANY_NAME]. [SOCIAL_PROOF]",'
                        '"body_financial":"Hi, Test High Gap Hospital financial [COMPANY_NAME]. [SOCIAL_PROOF]"}'
                    )
                }
            }]
        },
    })()

    with patch("src.outbound_generator._OPENROUTER_KEY", "fake-key"), \
         patch("src.outbound_generator._OPENROUTER_TIMEOUT_SECONDS", 5), \
         patch("src.outbound_generator._requests.post", return_value=response) as post:
        outbound_generator._call_openrouter(h, "tencent/hy3-preview:free")

    assert post.call_args.kwargs["timeout"] == (5, 5)


def test_openrouter_call_sets_temperature_and_max_tokens():
    h = _run(HIGH_GAP)
    response = type("Response", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: {
            "choices": [{
                "message": {
                    "content": (
                        '{"body_moral":"Hi, Test High Gap Hospital moral [COMPANY_NAME]. [SOCIAL_PROOF]",'
                        '"body_clinical":"Hi, Test High Gap Hospital clinical [COMPANY_NAME]. [SOCIAL_PROOF]",'
                        '"body_financial":"Hi, Test High Gap Hospital financial [COMPANY_NAME]. [SOCIAL_PROOF]"}'
                    )
                }
            }]
        },
    })()

    with patch("src.outbound_generator._OPENROUTER_KEY", "fake-key"), \
         patch("src.outbound_generator._OPENROUTER_MAX_TOKENS", 1200), \
         patch("src.outbound_generator._requests.post", return_value=response) as post:
        outbound_generator._call_openrouter(h, "tencent/hy3-preview:free")

    payload = post.call_args.kwargs["json"]
    assert payload["temperature"] == 0.35
    assert payload["max_tokens"] == 1200
    assert "response_format" not in payload


def test_openrouter_json_mode_is_optional():
    h = _run(HIGH_GAP)
    response = type("Response", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: {
            "choices": [{
                "message": {
                    "content": (
                        '{"body_moral":"Hi, Test High Gap Hospital moral [COMPANY_NAME]. [SOCIAL_PROOF]",'
                        '"body_clinical":"Hi, Test High Gap Hospital clinical [COMPANY_NAME]. [SOCIAL_PROOF]",'
                        '"body_financial":"Hi, Test High Gap Hospital financial [COMPANY_NAME]. [SOCIAL_PROOF]"}'
                    )
                }
            }]
        },
    })()

    with patch("src.outbound_generator._OPENROUTER_KEY", "fake-key"), \
         patch("src.outbound_generator._OPENROUTER_JSON_MODE", True), \
         patch("src.outbound_generator._requests.post", return_value=response) as post:
        outbound_generator._call_openrouter(h, "tencent/hy3-preview:free")

    payload = post.call_args.kwargs["json"]
    assert payload["response_format"] == {"type": "json_object"}


def test_openrouter_prompt_forbids_unsupported_financial_claims():
    h = _run(HIGH_GAP)
    response = type("Response", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: {
            "choices": [{
                "message": {
                    "content": (
                        '{"body_moral":"Hi, Test High Gap Hospital moral [COMPANY_NAME]. [SOCIAL_PROOF]",'
                        '"body_clinical":"Hi, Test High Gap Hospital clinical [COMPANY_NAME]. [SOCIAL_PROOF]",'
                        '"body_financial":"Hi, Test High Gap Hospital financial [COMPANY_NAME]. [SOCIAL_PROOF]"}'
                    )
                }
            }]
        },
    })()

    with patch("src.outbound_generator._OPENROUTER_KEY", "fake-key"), \
         patch("src.outbound_generator._requests.post", return_value=response) as post:
        outbound_generator._call_openrouter(h, "tencent/hy3-preview:free")

    payload = post.call_args.kwargs["json"]
    messages = payload["messages"]
    prompt_text = "\n".join(message["content"] for message in messages)

    assert messages[0]["role"] == "system"
    assert "Use full facility name exactly" in prompt_text
    assert "Do not mention reimbursement risk" in prompt_text
    assert "national average" in prompt_text
    assert "Do not write helped [SOCIAL_PROOF]" in prompt_text
    assert "never say X% need help" in prompt_text
    assert "45-70 words" in prompt_text
    assert "ends with a CTA question" in prompt_text


def test_openrouter_unsupported_claims_fall_back_to_cached_templates():
    h = _run(HIGH_GAP)
    response = type("Response", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: {
            "choices": [{
                "message": {
                    "content": (
                        '{"body_moral":"Hi, Test High Gap Hospital moral [COMPANY_NAME]. [SOCIAL_PROOF]",'
                        '"body_clinical":"Hi, Test High Gap Hospital clinical [COMPANY_NAME]. [SOCIAL_PROOF]",'
                        '"body_financial":"Hi, Test High Gap Hospital CMS reimbursement at risk [COMPANY_NAME]. [SOCIAL_PROOF]"}'
                    )
                }
            }]
        },
    })()

    with patch("src.outbound_generator._OPENROUTER_KEY", "fake-key"), \
         patch("src.outbound_generator._REQUESTS_AVAILABLE", True), \
         patch("src.outbound_generator._OPENROUTER_MAX_LIVE_EMAILS", 1), \
         patch("src.outbound_generator._requests.post", return_value=response):
        email = generate_outbound_email([h])[0]

    assert email["generation_method"] == "cached_fallback"
    assert "CMS reimbursement at risk" not in email["body_financial"]


def test_openrouter_requires_full_facility_name():
    h = _run(HIGH_GAP)
    response = type("Response", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: {
            "choices": [{
                "message": {
                    "content": (
                        '{"body_moral":"Hi, Test High moral [COMPANY_NAME]. [SOCIAL_PROOF]",'
                        '"body_clinical":"Hi, Test High clinical [COMPANY_NAME]. [SOCIAL_PROOF]",'
                        '"body_financial":"Hi, Test High financial [COMPANY_NAME]. [SOCIAL_PROOF]"}'
                    )
                }
            }]
        },
    })()

    with patch("src.outbound_generator._OPENROUTER_KEY", "fake-key"), \
         patch("src.outbound_generator._REQUESTS_AVAILABLE", True), \
         patch("src.outbound_generator._OPENROUTER_MAX_LIVE_EMAILS", 1), \
         patch("src.outbound_generator._requests.post", return_value=response):
        email = generate_outbound_email([h])[0]

    assert email["generation_method"] == "cached_fallback"


def test_openrouter_rejects_overlong_generated_bodies():
    h = _run(HIGH_GAP)
    long_body = "Hi, Test High Gap Hospital " + "word " * 120 + "[COMPANY_NAME]. [SOCIAL_PROOF]"
    response = type("Response", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: {
            "choices": [{
                "message": {
                    "content": (
                        '{"body_moral":' + repr(long_body).replace("'", '"') + ','
                        '"body_clinical":"Hi, Test High Gap Hospital clinical [COMPANY_NAME]. [SOCIAL_PROOF]",'
                        '"body_financial":"Hi, Test High Gap Hospital financial [COMPANY_NAME]. [SOCIAL_PROOF]"}'
                    )
                }
            }]
        },
    })()

    with patch("src.outbound_generator._OPENROUTER_KEY", "fake-key"), \
         patch("src.outbound_generator._REQUESTS_AVAILABLE", True), \
         patch("src.outbound_generator._OPENROUTER_MAX_LIVE_EMAILS", 1), \
         patch("src.outbound_generator._requests.post", return_value=response):
        email = generate_outbound_email([h])[0]

    assert email["generation_method"] == "cached_fallback"


def test_openrouter_repairs_awkward_social_proof_placeholder():
    h = _run(HIGH_GAP)
    response = type("Response", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: {
            "choices": [{
                "message": {
                    "content": (
                        '{"body_moral":"Hi, Test High Gap Hospital helped [SOCIAL_PROOF] [COMPANY_NAME]",'
                        '"body_clinical":"Hi, Test High Gap Hospital clinical [COMPANY_NAME]. [SOCIAL_PROOF]",'
                        '"body_financial":"Hi, Test High Gap Hospital financial [COMPANY_NAME]. [SOCIAL_PROOF]"}'
                    )
                }
            }]
        },
    })()

    with patch("src.outbound_generator._OPENROUTER_KEY", "fake-key"), \
         patch("src.outbound_generator._REQUESTS_AVAILABLE", True), \
         patch("src.outbound_generator._OPENROUTER_MAX_LIVE_EMAILS", 1), \
         patch("src.outbound_generator._requests.post", return_value=response):
        email = generate_outbound_email([h])[0]

    assert email["generation_method"] == "openrouter_api"
    assert "helped [SOCIAL_PROOF]" not in email["body_moral"]
    assert "[SOCIAL_PROOF]" in email["body_moral"]


def test_openrouter_repairs_missing_placeholders():
    h = _run(HIGH_GAP)
    response = type("Response", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: {
            "choices": [{
                "message": {
                    "content": (
                        '{"body_moral":"Hi, Test High Gap Hospital moral angle.",'
                        '"body_clinical":"Hi, Test High Gap Hospital clinical [COMPANY_NAME].",'
                        '"body_financial":"Hi, Test High Gap Hospital financial [SOCIAL_PROOF]."}'
                    )
                }
            }]
        },
    })()

    with patch("src.outbound_generator._OPENROUTER_KEY", "fake-key"), \
         patch("src.outbound_generator._REQUESTS_AVAILABLE", True), \
         patch("src.outbound_generator._OPENROUTER_MAX_LIVE_EMAILS", 1), \
         patch("src.outbound_generator._requests.post", return_value=response):
        email = generate_outbound_email([h])[0]

    assert email["generation_method"] == "openrouter_api"
    for key in BODY_KEYS:
        assert "[COMPANY_NAME]" in email[key]
        assert "[SOCIAL_PROOF]" in email[key]


def test_openrouter_parses_json_wrapped_in_markdown():
    h = _run(HIGH_GAP)
    response = type("Response", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: {
            "choices": [{
                "message": {
                    "content": (
                        '```json\n'
                        '{"body_moral":"Hi, Test High Gap Hospital moral [COMPANY_NAME]. [SOCIAL_PROOF]",'
                        '"body_clinical":"Hi, Test High Gap Hospital clinical [COMPANY_NAME]. [SOCIAL_PROOF]",'
                        '"body_financial":"Hi, Test High Gap Hospital financial [COMPANY_NAME]. [SOCIAL_PROOF]"}'
                        '\n```'
                    )
                }
            }]
        },
    })()

    with patch("src.outbound_generator._OPENROUTER_KEY", "fake-key"), \
         patch("src.outbound_generator._REQUESTS_AVAILABLE", True), \
         patch("src.outbound_generator._OPENROUTER_MAX_LIVE_EMAILS", 1), \
         patch("src.outbound_generator._requests.post", return_value=response):
        email = generate_outbound_email([h])[0]

    assert email["generation_method"] == "openrouter_api"


def test_openrouter_repairs_literal_newlines_inside_json_strings():
    h = _run(HIGH_GAP)
    response = type("Response", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: {
            "choices": [{
                "message": {
                    "content": (
                        '{"body_moral":"Hi, Test High Gap Hospital moral\n[COMPANY_NAME]. [SOCIAL_PROOF]",'
                        '"body_clinical":"Hi, Test High Gap Hospital clinical [COMPANY_NAME]. [SOCIAL_PROOF]",'
                        '"body_financial":"Hi, Test High Gap Hospital financial [COMPANY_NAME]. [SOCIAL_PROOF]"}'
                    )
                }
            }]
        },
    })()

    with patch("src.outbound_generator._OPENROUTER_KEY", "fake-key"), \
         patch("src.outbound_generator._REQUESTS_AVAILABLE", True), \
         patch("src.outbound_generator._OPENROUTER_MAX_LIVE_EMAILS", 1), \
         patch("src.outbound_generator._requests.post", return_value=response):
        email = generate_outbound_email([h])[0]

    assert email["generation_method"] == "openrouter_api"


def test_openrouter_parses_labeled_non_json_body_sections():
    h = _run(HIGH_GAP)
    response = type("Response", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: {
            "choices": [{
                "message": {
                    "content": (
                        "body_moral: Hi, Test High Gap Hospital moral [COMPANY_NAME]. [SOCIAL_PROOF]\n"
                        "body_clinical: Hi, Test High Gap Hospital clinical [COMPANY_NAME]. [SOCIAL_PROOF]\n"
                        "body_financial: Hi, Test High Gap Hospital financial [COMPANY_NAME]. [SOCIAL_PROOF]"
                    )
                }
            }]
        },
    })()

    with patch("src.outbound_generator._OPENROUTER_KEY", "fake-key"), \
         patch("src.outbound_generator._REQUESTS_AVAILABLE", True), \
         patch("src.outbound_generator._OPENROUTER_MAX_LIVE_EMAILS", 1), \
         patch("src.outbound_generator._requests.post", return_value=response):
        email = generate_outbound_email([h])[0]

    assert email["generation_method"] == "openrouter_api"


def test_openrouter_parses_markdown_heading_body_sections():
    h = _run(HIGH_GAP)
    response = type("Response", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: {
            "choices": [{
                "message": {
                    "content": (
                        "**MORAL ANGLE**\n"
                        "Hi, Test High Gap Hospital moral [COMPANY_NAME]. [SOCIAL_PROOF]\n"
                        "**CLINICAL ANGLE**\n"
                        "Hi, Test High Gap Hospital clinical [COMPANY_NAME]. [SOCIAL_PROOF]\n"
                        "**FINANCIAL ANGLE**\n"
                        "Hi, Test High Gap Hospital financial [COMPANY_NAME]. [SOCIAL_PROOF]"
                    )
                }
            }]
        },
    })()

    with patch("src.outbound_generator._OPENROUTER_KEY", "fake-key"), \
         patch("src.outbound_generator._REQUESTS_AVAILABLE", True), \
         patch("src.outbound_generator._OPENROUTER_MAX_LIVE_EMAILS", 1), \
         patch("src.outbound_generator._requests.post", return_value=response):
        email = generate_outbound_email([h])[0]

    assert email["generation_method"] == "openrouter_api"


def test_openrouter_recovers_quoted_body_fields_from_malformed_json():
    h = _run(HIGH_GAP)
    response = type("Response", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: {
            "choices": [{
                "message": {
                    "content": (
                        '{"body_moral":"Hi, Test High Gap Hospital moral [COMPANY_NAME]. [SOCIAL_PROOF]"'
                        '"body_clinical":"Hi, Test High Gap Hospital clinical [COMPANY_NAME]. [SOCIAL_PROOF]",'
                        '"body_financial":"Hi, Test High Gap Hospital financial [COMPANY_NAME]. [SOCIAL_PROOF]"}'
                    )
                }
            }]
        },
    })()

    with patch("src.outbound_generator._OPENROUTER_KEY", "fake-key"), \
         patch("src.outbound_generator._REQUESTS_AVAILABLE", True), \
         patch("src.outbound_generator._OPENROUTER_MAX_LIVE_EMAILS", 1), \
         patch("src.outbound_generator._requests.post", return_value=response):
        email = generate_outbound_email([h])[0]

    assert email["generation_method"] == "openrouter_api"


def test_openrouter_retries_after_empty_content():
    h = _run(HIGH_GAP)
    empty_response = type("Response", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: {
            "choices": [{
                "finish_reason": "length",
                "message": {"content": None},
            }]
        },
    })()
    valid_response = type("Response", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: {
            "choices": [{
                "message": {
                    "content": (
                        '{"body_moral":"Hi, Test High Gap Hospital moral [COMPANY_NAME]. [SOCIAL_PROOF]",'
                        '"body_clinical":"Hi, Test High Gap Hospital clinical [COMPANY_NAME]. [SOCIAL_PROOF]",'
                        '"body_financial":"Hi, Test High Gap Hospital financial [COMPANY_NAME]. [SOCIAL_PROOF]"}'
                    )
                }
            }]
        },
    })()

    with patch("src.outbound_generator._OPENROUTER_KEY", "fake-key"), \
         patch("src.outbound_generator._REQUESTS_AVAILABLE", True), \
         patch("src.outbound_generator._OPENROUTER_MAX_LIVE_EMAILS", 1), \
         patch("src.outbound_generator._OPENROUTER_RETRIES", 1), \
         patch("src.outbound_generator._requests.post", side_effect=[empty_response, valid_response]) as post:
        email = generate_outbound_email([h])[0]

    assert post.call_count == 2
    assert email["generation_method"] == "openrouter_api"


def test_openrouter_does_not_retry_rate_limit_errors():
    h = _run(HIGH_GAP)
    response = type("Response", (), {"status_code": 429})()
    rate_limit_error = Exception("429 Client Error: Too Many Requests")
    rate_limit_error.response = response

    with patch("src.outbound_generator._OPENROUTER_KEY", "fake-key"), \
         patch("src.outbound_generator._REQUESTS_AVAILABLE", True), \
         patch("src.outbound_generator._OPENROUTER_MAX_LIVE_EMAILS", 1), \
         patch("src.outbound_generator._OPENROUTER_RETRIES", 1), \
         patch("src.outbound_generator._call_openrouter", side_effect=rate_limit_error) as call:
        email = generate_outbound_email([h])[0]

    assert call.call_count == 1
    assert email["generation_method"] == "cached_fallback"


def test_openrouter_rejects_discharge_help_pct_as_unmet_need():
    h = _run(HIGH_GAP)
    response = type("Response", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: {
            "choices": [{
                "message": {
                    "content": (
                        '{"body_moral":"Hi, Test High Gap Hospital 62% need help after discharge [COMPANY_NAME]. [SOCIAL_PROOF]",'
                        '"body_clinical":"Hi, Test High Gap Hospital clinical [COMPANY_NAME]. [SOCIAL_PROOF]",'
                        '"body_financial":"Hi, Test High Gap Hospital financial [COMPANY_NAME]. [SOCIAL_PROOF]"}'
                    )
                }
            }]
        },
    })()

    with patch("src.outbound_generator._OPENROUTER_KEY", "fake-key"), \
         patch("src.outbound_generator._REQUESTS_AVAILABLE", True), \
         patch("src.outbound_generator._OPENROUTER_MAX_LIVE_EMAILS", 1), \
         patch("src.outbound_generator._requests.post", return_value=response):
        email = generate_outbound_email([h])[0]

    assert email["generation_method"] == "cached_fallback"


def test_openrouter_empty_content_falls_back_to_cached_templates():
    h = _run(HIGH_GAP)
    response = type("Response", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: {
            "choices": [{
                "finish_reason": "length",
                "message": {"content": None},
            }]
        },
    })()

    with patch("src.outbound_generator._OPENROUTER_KEY", "fake-key"), \
         patch("src.outbound_generator._REQUESTS_AVAILABLE", True), \
         patch("src.outbound_generator._OPENROUTER_MAX_LIVE_EMAILS", 1), \
         patch("src.outbound_generator._requests.post", return_value=response):
        email = generate_outbound_email([h])[0]

    assert email["generation_method"] == "cached_fallback"
    assert "handoff friction" in email["body_moral"]


def test_generation_method_cached_fallback_on_api_failure():
    h = _run(HIGH_GAP)
    with patch("src.outbound_generator._OPENROUTER_KEY", "fake-key"), \
         patch("src.outbound_generator._REQUESTS_AVAILABLE", True), \
         patch("src.outbound_generator._call_openrouter", side_effect=Exception("API error")):
        email = generate_outbound_email([h])[0]
    assert email["generation_method"] == "cached_fallback"


def test_generation_method_cached_fallback_no_commitment_tag():
    h = _run(HIGH_GAP)
    h["commitment_tag"] = None
    email = generate_outbound_email([h])[0]
    assert email["generation_method"] == "cached_fallback"


# ── body_moral ─────────────────────────────────────────────────────────────────

def test_body_moral_quotes_commitment_tag():
    h = _run(HIGH_GAP)
    email = generate_outbound_email([h])[0]
    assert HIGH_GAP["commitment_tag"] in email["body_moral"], \
        "body_moral must quote commitment_tag verbatim"


def test_body_moral_medium_quotes_commitment_tag():
    h = _run(MEDIUM_GAP)
    email = generate_outbound_email([h])[0]
    assert MEDIUM_GAP["commitment_tag"] in email["body_moral"]


# ── body_clinical ──────────────────────────────────────────────────────────────

def test_body_clinical_has_discharge_help_pct():
    # HIGH_GAP discharge_help_pct = 62.0
    email = generate_outbound_email([_run(HIGH_GAP)])[0]
    assert "62" in email["body_clinical"], \
        "body_clinical must include discharge_help_pct (62.0)"


def test_body_clinical_has_state_postpartum_rate():
    # state_postpartum_visit_rate = 82.4 for all fixtures
    email = generate_outbound_email([_run(HIGH_GAP)])[0]
    assert "82" in email["body_clinical"], \
        "body_clinical must reference state_postpartum_visit_rate (82.4)"


# ── body_financial ─────────────────────────────────────────────────────────────

def test_body_financial_references_medicaid():
    email = generate_outbound_email([_run(HIGH_GAP)])[0]
    body = email["body_financial"].lower()
    assert "medicaid" in body, "body_financial must reference Medicaid coverage"


def test_body_financial_extended_coverage_line():
    # HIGH_GAP has medicaid_extended = True
    email = generate_outbound_email([_run(HIGH_GAP)])[0]
    assert "12-month" in email["body_financial"] or "12 month" in email["body_financial"], \
        "body_financial should mention 12-month Medicaid coverage when medicaid_extended is True"


def test_cached_fallback_has_specific_cta_and_less_generic_copy():
    email = generate_outbound_email([_run(HIGH_GAP)])[0]

    assert "Worth a 15-minute look?" in email["body_moral"]
    assert "Should I send the one-page workflow?" in email["body_clinical"]
    assert "Worth a 15-minute look?" in email["body_financial"]
    for key in BODY_KEYS:
        assert "serious about closing that gap" not in email[key]
        assert "structured postpartum monitoring" not in email[key]


# ── to_role ────────────────────────────────────────────────────────────────────

def test_to_role_is_valid():
    email = generate_outbound_email([_run(HIGH_GAP)])[0]
    assert email["to_role"] in VALID_ROLES


def test_to_role_valid_for_medium():
    email = generate_outbound_email([_run(MEDIUM_GAP)])[0]
    assert email["to_role"] in VALID_ROLES


# ── placeholder hygiene ────────────────────────────────────────────────────────

def test_no_company_name_hardcoded():
    emails = generate_outbound_email([_run(HIGH_GAP), _run(MEDIUM_GAP)])
    for email in emails:
        for key in BODY_KEYS:
            for company in BANNED_COMPANIES:
                assert company not in email[key], \
                    f"Hardcoded company '{company}' found in {key}"


def test_company_name_placeholder_present():
    email = generate_outbound_email([_run(HIGH_GAP)])[0]
    has_placeholder = any("[COMPANY_NAME]" in email[k] for k in BODY_KEYS)
    assert has_placeholder, "At least one body variant must contain [COMPANY_NAME]"


# ── null data ──────────────────────────────────────────────────────────────────

def test_null_data_does_not_crash():
    # NULL_DATA has data_confidence="low" — skipped entirely
    h = _run(NULL_DATA)
    emails = generate_outbound_email([h])
    assert isinstance(emails, list)

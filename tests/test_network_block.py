"""The test suite must never reach a live LLM API, even with real .env keys."""

import copy

import src.outbound_generator as og
from src.gap_calculator import calculate_gap_score
from src.urgency_ranker import add_urgency
from tests.fixtures import HIGH_GAP


def _ready() -> dict:
    return add_urgency(calculate_gap_score(copy.deepcopy(HIGH_GAP)))


def test_llm_calls_fall_back_without_touching_network(monkeypatch):
    # Simulate a configured machine: key present, requests importable.
    monkeypatch.setattr(og, "_OPENROUTER_KEY", "fake-key-must-never-be-sent")
    monkeypatch.setattr(og, "_ANTHROPIC_KEY", "fake-key-must-never-be-sent")
    if og._REQUESTS_AVAILABLE:
        def _explode(*args, **kwargs):
            raise AssertionError("requests.post reached from a test")
        monkeypatch.setattr(og._requests, "post", _explode)

    body, method, reason = og._generate_email_body(_ready())

    assert method == "cached_fallback"
    assert "network disabled in tests" in reason
    assert body.startswith("Hi,")

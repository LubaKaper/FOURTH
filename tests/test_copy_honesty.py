"""
Outbound copy may only claim what the underlying measure shows.

discharge_info_pct is HCAHPS H_DISCH_HELP_Y_P — % of patients who
reported receiving recovery information at discharge. No hospital-level
copy may present it as a postpartum visit completion rate, and no copy
may compute a point-gap between it and a different measure.
"""

import copy

from src.gap_calculator import calculate_gap_score
from src.human_checkpoint import _key_metric
from src.outbound_generator import _angle_reason, _email_body, _openrouter_prompt, _subject
from src.urgency_ranker import add_urgency
from tests.fixtures import FINANCIAL_ONLY, HIGH_GAP, MEDIUM_GAP

FORBIDDEN_PHRASES = [
    "postpartum maternal completion",
    "postpartum completion",
    "visit completion at",       # "...completion at {hospital}" claims a hospital-level rate
    "-point gap",
    "point gap is",
    "pt gap",
    "pt below",
    "pt lag",
]


def _ready(fixture: dict) -> dict:
    return add_urgency(calculate_gap_score(copy.deepcopy(fixture)))


def test_no_surface_claims_visit_completion_from_discharge_measure():
    for fixture in (HIGH_GAP, MEDIUM_GAP, FINANCIAL_ONLY):
        h = _ready(fixture)
        text = " ".join(
            [_subject(h), _email_body(h), _angle_reason(h), _key_metric(h)]
        ).lower()
        for phrase in FORBIDDEN_PHRASES:
            assert phrase not in text, f"{phrase!r} found in copy for {h['lead_angle']}"


def test_baby_vs_mother_copy_labels_both_measures():
    h = _ready(HIGH_GAP)  # HIGH_GAP resolves to baby_vs_mother_contrast
    assert h["lead_angle"] == "baby_vs_mother_contrast"
    body = _email_body(h)
    assert "well-baby" in body.lower()
    assert "discharge" in body.lower()          # the hospital number is a discharge measure
    assert "94%" in body and "61%" in body      # both real numbers present, no fake subtraction


def test_prompt_defines_discharge_measure_and_forbids_mislabeling():
    h = _ready(HIGH_GAP)
    prompt = _openrouter_prompt(h)
    assert "discharge_info_pct" in prompt
    assert "postpartum_visit_pct" not in prompt
    assert "not a postpartum visit completion rate" in prompt.lower()

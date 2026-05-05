"""
Tests for Tool 2 — outcome_scorer.

Runs against the real CSVs in data/. A module-scoped fixture pipes
real Tool 1 output through score_outcomes() once; tests assert shape,
types, allowed values, no-hospital-dropped, no-mutation, no removed
v0.1 fields, and identity preservation per SCHEMA.md.

v1 covers NY only; the state benchmark is a hardcoded constant
(NY 2023 = 82.4) sourced from data/core-set-ppc-ad-ny.csv for citation
but not parsed at runtime — it is the same value on every NY hospital
dict.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from commitment_ingester import get_hospital_commitments
from constants import NY_POSTPARTUM_VISIT_RATE_2023, NY_POSTPARTUM_VISIT_YEAR
from outcome_scorer import score_outcomes


TOOL_1_KEYS = {
    "facility_id",
    "facility_name",
    "state",
    "city",
    "county",
    "address",
    "zip",
    "lat",
    "lon",
    "birthing_friendly",
    "commitment_tag",
    "commitment_source",
    "commitment_year",
}

TOOL_2_KEYS_ADDED = {
    "discharge_info_star",
    "discharge_help_pct",
    "overall_star",
    "state_postpartum_visit_rate",
    "state_postpartum_visit_year",
    "hcahps_start_date",
    "hcahps_end_date",
}

REMOVED_V01_FIELDS = {
    "hcahps_discharge_score",
    "hcahps_discharge_national_avg",
    "hcahps_care_transition_score",
    "state_postpartum_care_pct",
    "state_avg_postpartum_pct",
    "compared_to_national",
    "severe_morbidity_rate",
    "postpartum_visit_pct",
    "well_baby_visit_pct",
    "maternal_quality_score",
    "readmission_penalty",
    "excess_readmission_ratio",
    "medicaid_pct",
    "care_transition_score",
    "has_commitment",
    "hospital_type",
    "hospital_ownership",
    "state_mortality_rate",
    "state_mortality_rank",
}


@pytest.fixture(scope="module")
def tool_1_hospitals():
    return get_hospital_commitments()


@pytest.fixture(scope="module")
def hospitals(tool_1_hospitals):
    return score_outcomes(tool_1_hospitals)


def test_does_not_drop_hospitals(tool_1_hospitals, hospitals):
    """Tool 2 must score every Tool 1 hospital, even when all HCAHPS
    measures resolve to None. Hospitals are filtered (if at all) by
    Tool 5, never here."""
    assert len(hospitals) == len(tool_1_hospitals)


def test_every_hospital_has_all_tool_2_fields(hospitals):
    for h in hospitals:
        missing = TOOL_2_KEYS_ADDED - set(h.keys())
        assert not missing, f"{h.get('facility_id')!r} missing keys: {missing}"


def test_upstream_tool_1_fields_preserved(tool_1_hospitals, hospitals):
    """Every Tool 1 field must arrive on the Tool 2 output dict
    unchanged. Tools only add fields; renaming or rewriting an
    upstream field is a pipeline-contract bug."""
    by_id = {h["facility_id"]: h for h in hospitals}
    for original in tool_1_hospitals:
        h = by_id[original["facility_id"]]
        for key in TOOL_1_KEYS:
            assert h[key] == original[key], (
                f"{original['facility_id']} key {key!r} changed: "
                f"{original[key]!r} -> {h[key]!r}"
            )


def test_facility_name_is_preserved_from_tool_1_to_tool_2(tool_1_hospitals, hospitals):
    by_id = {h["facility_id"]: h for h in hospitals}

    for original in tool_1_hospitals:
        scored = by_id[original["facility_id"]]
        assert scored["facility_name"] == original["facility_name"]
        assert "name" not in scored


def test_score_outcomes_requires_list_input(tool_1_hospitals):
    with pytest.raises(TypeError, match="expects a list"):
        score_outcomes(tool_1_hospitals[0])


def test_hcahps_stars_are_int_1_to_5_or_none(hospitals):
    for h in hospitals:
        for key in ("discharge_info_star", "overall_star"):
            v = h[key]
            if v is None:
                continue
            assert isinstance(v, int) and not isinstance(v, bool), (
                f"{h['facility_id']} {key} not int: {v!r}"
            )
            assert 1 <= v <= 5, f"{h['facility_id']} {key} out of 1-5: {v}"


def test_discharge_help_pct_is_float_or_none(hospitals):
    for h in hospitals:
        v = h["discharge_help_pct"]
        if v is None:
            continue
        assert isinstance(v, float), (
            f"{h['facility_id']} discharge_help_pct not float: {v!r}"
        )
        assert 0.0 <= v <= 100.0, (
            f"{h['facility_id']} discharge_help_pct out of 0-100: {v}"
        )


def test_state_postpartum_visit_rate_is_float(hospitals):
    for h in hospitals:
        v = h["state_postpartum_visit_rate"]
        assert isinstance(v, float), (
            f"{h['facility_id']} state_postpartum_visit_rate not float: {v!r}"
        )


def test_state_postpartum_visit_year_is_int(hospitals):
    for h in hospitals:
        v = h["state_postpartum_visit_year"]
        assert isinstance(v, int) and not isinstance(v, bool), (
            f"{h['facility_id']} state_postpartum_visit_year not int: {v!r}"
        )


def test_hcahps_dates_are_strings_or_none(hospitals):
    """Schema allows None (forward-looking for v2 hospitals from
    non-HCAHPS sources). In v1 every CCN was sourced from HCAHPS so
    dates should always be present, but we don't enforce that — that
    would overfit to current data."""
    for h in hospitals:
        for key in ("hcahps_start_date", "hcahps_end_date"):
            v = h[key]
            if v is None:
                continue
            assert isinstance(v, str), f"{h['facility_id']} {key} not str: {v!r}"
            assert v.strip(), f"{h['facility_id']} {key} blank string"


def test_state_benchmark_consistency(hospitals):
    """All NY hospitals must carry the same state benchmark — one
    number per state, broadcast onto every hospital dict. Catches
    bugs where the constant gets accidentally recomputed per-row."""
    rates = {h["state_postpartum_visit_rate"] for h in hospitals}
    years = {h["state_postpartum_visit_year"] for h in hospitals}
    assert rates == {NY_POSTPARTUM_VISIT_RATE_2023}, f"varying rates: {rates}"
    assert years == {NY_POSTPARTUM_VISIT_YEAR}, f"varying years: {years}"


def test_no_v01_removed_fields(hospitals):
    for h in hospitals:
        leaked = REMOVED_V01_FIELDS & set(h.keys())
        assert not leaked, f"{h['facility_id']} has removed v0.1 fields: {leaked}"


def test_score_outcomes_does_not_mutate_input():
    """Tool 2 must build new dicts, not mutate input.

    Pipeline composability requires this: if score_outcomes mutated
    its input, a debug path that re-uses the Tool 1 list would see
    the mutation. Re-reads Tool 1 fresh so this test is independent
    of the module-scoped fixture (which has already been augmented
    by the time other tests run)."""
    fresh = get_hospital_commitments()
    snapshot = [dict(h) for h in fresh]
    score_outcomes(fresh)
    for original, current in zip(snapshot, fresh):
        assert original == current, (
            f"{original['facility_id']} mutated by score_outcomes"
        )

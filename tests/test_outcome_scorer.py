"""
Schema-facing tests for Tool 2 — outcome_scorer.

These tests encode the ADR-backed Handoff 1B contract. They are expected
to fail until outcome_scorer.py is migrated from the legacy v0.2 fields.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from commitment_ingester import get_hospital_commitments
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
    "postpartum_visit_pct",
    "well_baby_visit_pct",
    "well_baby_visit_estimated",
    "state_postpartum_avg",
    "smm_rate",
    "hcahps_care_transition_star",
    "hcahps_overall_star",
    "readmission_penalty",
    "state_mortality_rank",
    "racial_disparity_flag",
    "medicaid_extended",
    "mmsm_participant",
}

LEGACY_V02_FIELDS = {
    "discharge_info_star",
    "discharge_help_pct",
    "overall_star",
    "state_postpartum_visit_rate",
    "state_postpartum_visit_year",
    "hcahps_start_date",
    "hcahps_end_date",
}

VALID_STATE_MORTALITY_RANKS = {"top_quartile", "bottom_quartile", "middle", None}


@pytest.fixture(scope="module")
def tool_1_hospitals():
    return get_hospital_commitments()


@pytest.fixture(scope="module")
def hospitals(tool_1_hospitals):
    return score_outcomes(tool_1_hospitals)


def test_does_not_drop_hospitals(tool_1_hospitals, hospitals):
    assert len(hospitals) == len(tool_1_hospitals)


def test_every_hospital_has_all_adr_tool_2_fields(hospitals):
    for h in hospitals:
        missing = TOOL_2_KEYS_ADDED - set(h.keys())
        assert not missing, f"{h.get('facility_id')!r} missing keys: {missing}"


def test_upstream_tool_1_fields_preserved(tool_1_hospitals, hospitals):
    by_id = {h["facility_id"]: h for h in hospitals}
    for original in tool_1_hospitals:
        h = by_id[original["facility_id"]]
        for key in TOOL_1_KEYS:
            assert h[key] == original[key], (
                f"{original['facility_id']} key {key!r} changed: "
                f"{original[key]!r} -> {h[key]!r}"
            )


def test_facility_name_is_preserved_and_name_alias_is_not_added(tool_1_hospitals, hospitals):
    by_id = {h["facility_id"]: h for h in hospitals}

    for original in tool_1_hospitals:
        scored = by_id[original["facility_id"]]
        assert scored["facility_name"] == original["facility_name"]
        assert "name" not in scored
        assert "hospital_name" not in scored


def test_score_outcomes_requires_list_input(tool_1_hospitals):
    with pytest.raises(TypeError, match="expects a list"):
        score_outcomes(tool_1_hospitals[0])


def test_percentage_fields_are_float_0_to_100_or_none(hospitals):
    for h in hospitals:
        for key in ("postpartum_visit_pct", "well_baby_visit_pct", "state_postpartum_avg"):
            value = h[key]
            if value is None:
                continue
            assert isinstance(value, float), f"{h['facility_id']} {key} not float: {value!r}"
            assert 0.0 <= value <= 100.0, f"{h['facility_id']} {key} out of range: {value}"


def test_smm_rate_is_float_or_none(hospitals):
    for h in hospitals:
        value = h["smm_rate"]
        if value is None:
            continue
        assert isinstance(value, float), f"{h['facility_id']} smm_rate not float: {value!r}"
        assert value >= 0.0, f"{h['facility_id']} smm_rate negative: {value}"


def test_hcahps_stars_are_int_1_to_5_or_none(hospitals):
    for h in hospitals:
        for key in ("hcahps_care_transition_star", "hcahps_overall_star"):
            value = h[key]
            if value is None:
                continue
            assert isinstance(value, int) and not isinstance(value, bool), (
                f"{h['facility_id']} {key} not int: {value!r}"
            )
            assert 1 <= value <= 5, f"{h['facility_id']} {key} out of 1-5: {value}"


def test_boolean_context_fields_are_bool_or_none(hospitals):
    for h in hospitals:
        for key in ("readmission_penalty", "racial_disparity_flag", "medicaid_extended", "mmsm_participant"):
            value = h[key]
            assert value is None or isinstance(value, bool), (
                f"{h['facility_id']} {key} not bool|None: {value!r}"
            )


def test_state_mortality_rank_allowed_values(hospitals):
    for h in hospitals:
        assert h["state_mortality_rank"] in VALID_STATE_MORTALITY_RANKS


def test_mmsm_participant_maps_from_maternal_health_csv(hospitals):
    nassau = next(h for h in hospitals if h["facility_id"] == "330027")
    assert nassau["mmsm_participant"] is True


def test_readmission_penalty_maps_from_hrrp_excess_ratio(hospitals):
    nassau = next(h for h in hospitals if h["facility_id"] == "330027")
    assert nassau["readmission_penalty"] is True


def test_unavailable_smm_rate_remains_none(hospitals):
    nassau = next(h for h in hospitals if h["facility_id"] == "330027")
    assert nassau["smm_rate"] is None


def test_well_baby_visit_pct_uses_ny_state_benchmark_proxy(hospitals):
    """outcome_scorer sets well_baby_visit_pct = 91.5 (NY state proxy) for all NY hospitals."""
    nassau = next(h for h in hospitals if h["facility_id"] == "330027")
    assert nassau["well_baby_visit_pct"] == 91.5
    assert isinstance(nassau["well_baby_visit_pct"], float)


def test_well_baby_visit_estimated_is_true_for_all_ny_hospitals(hospitals):
    """well_baby_visit_estimated must be True whenever the proxy value is used."""
    for h in hospitals:
        assert h["well_baby_visit_estimated"] is True, (
            f"{h['facility_id']} well_baby_visit_estimated not True"
        )


def test_legacy_v02_fields_not_added_by_outcome_scorer(hospitals):
    for h in hospitals:
        leaked = LEGACY_V02_FIELDS & set(h.keys())
        assert not leaked, f"{h['facility_id']} has legacy v0.2 fields: {leaked}"


def test_score_outcomes_does_not_mutate_input():
    fresh = get_hospital_commitments()
    snapshot = [dict(h) for h in fresh]
    score_outcomes(fresh)
    for original, current in zip(snapshot, fresh):
        assert original == current, (
            f"{original['facility_id']} mutated by score_outcomes"
        )

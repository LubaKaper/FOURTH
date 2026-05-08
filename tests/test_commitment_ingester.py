"""
Tests for Tool 1 — commitment_ingester.

Runs against the real CSVs in data/. A module-scoped fixture invokes
get_hospital_commitments() once; individual tests assert shape, types,
and ADR-backed identity/commitment values per SCHEMA.md.
"""

import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from commitment_ingester import get_hospital_commitments


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

OUTCOME_FIELDS_NOT_IN_TOOL_1 = {
    "postpartum_visit_pct",
    "well_baby_visit_pct",
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

V1_COMMITMENT_TAG = "Earned the CMS Birthing-Friendly designation"
V1_COMMITMENT_SOURCE = "CMS Birthing-Friendly Registry"


@pytest.fixture(scope="module")
def hospitals():
    return get_hospital_commitments()


def test_returns_non_empty_list(hospitals):
    assert isinstance(hospitals, list)
    assert len(hospitals) > 0


def test_every_hospital_has_all_tool_1_fields(hospitals):
    for h in hospitals:
        missing = TOOL_1_KEYS - set(h.keys())
        assert not missing, f"{h.get('facility_id')!r} missing keys: {missing}"


def test_facility_id_is_string_ccn(hospitals):
    for h in hospitals:
        ccn = h["facility_id"]
        assert isinstance(ccn, str), f"facility_id not str: {ccn!r}"
        assert ccn.isdigit(), f"facility_id not all digits: {ccn!r}"
        assert len(ccn) == 6, f"facility_id not length 6: {ccn!r}"


def test_state_is_two_letter_uppercase(hospitals):
    pattern = re.compile(r"^[A-Z]{2}$")
    for h in hospitals:
        assert pattern.match(h["state"]), f"bad state: {h['state']!r}"
        assert h["state"] == "NY", f"non-NY hospital in default call: {h['state']!r}"


def test_birthing_friendly_true_in_v1(hospitals):
    for h in hospitals:
        assert h["birthing_friendly"] is True, f"{h['facility_id']} not BF=True"


def test_commitment_tag_v1_default(hospitals):
    for h in hospitals:
        assert h["commitment_tag"] == V1_COMMITMENT_TAG


def test_commitment_source_v1_default(hospitals):
    for h in hospitals:
        assert h["commitment_source"] == V1_COMMITMENT_SOURCE


def test_commitment_year_is_none_in_v1(hospitals):
    for h in hospitals:
        assert h["commitment_year"] is None, (
            f"{h['facility_id']} commitment_year not None: {h['commitment_year']!r}"
        )


def test_lat_lon_are_floats(hospitals):
    for h in hospitals:
        assert isinstance(h["lat"], float), f"{h['facility_id']} lat not float"
        assert isinstance(h["lon"], float), f"{h['facility_id']} lon not float"


def test_zip_is_string_and_populated(hospitals):
    for h in hospitals:
        z = h["zip"]
        assert isinstance(z, str), f"zip not str: {z!r}"
        assert len(z) >= 5, f"zip too short: {z!r}"


def test_county_is_populated(hospitals):
    for h in hospitals:
        c = h["county"]
        assert isinstance(c, str)
        assert c.strip(), f"{h['facility_id']} has empty county"


def test_tool_1_does_not_add_outcome_fields(hospitals):
    for h in hospitals:
        leaked = OUTCOME_FIELDS_NOT_IN_TOOL_1 & set(h.keys())
        assert not leaked, f"{h['facility_id']} has outcome fields too early: {leaked}"


def test_non_ny_state_returns_empty_list():
    """v1 has HCAHPS data for NY only. Non-NY states must return [] via
    an early-return guard so the function does not iterate the BF
    registry and emit a warning per unmatched out-of-state hospital."""
    assert get_hospital_commitments("CA") == []


def test_no_duplicate_facility_ids(hospitals):
    ids = [h["facility_id"] for h in hospitals]
    duplicates = {i for i in ids if ids.count(i) > 1}
    assert not duplicates, f"duplicate CCNs in result: {duplicates}"

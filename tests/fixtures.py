# tests/fixtures.py
"""
Shared test fixtures for Fourth tests.

Import these instead of defining ad hoc hospitals in test files. Fixtures
match the ADR-backed SCHEMA.md handoff contracts.
"""

BASE_IDENTITY = {
    "facility_id": "330001",
    "facility_name": "Test Birthing Friendly Hospital",
    "state": "NY",
    "city": "New York",
    "county": "New York",
    "address": "123 Test Ave",
    "zip": "10001",
    "lat": 40.7128,
    "lon": -74.0060,
    "birthing_friendly": True,
    "commitment_tag": "Earned the CMS Birthing-Friendly designation",
    "commitment_source": "CMS Birthing-Friendly Registry",
    "commitment_year": 2023,
}

HIGH_GAP = {
    **BASE_IDENTITY,
    "facility_id": "330101",
    "facility_name": "Test High Gap Hospital",
    "discharge_info_pct": 61.0,
    "well_baby_visit_pct": 94.0,
    "state_postpartum_avg": 82.4,
    "smm_rate": 180.0,
    "hcahps_care_transition_star": 2,
    "hcahps_overall_star": 2,
    "readmission_penalty": True,
    "state_mortality_rank": "bottom_quartile",
    "racial_disparity_flag": True,
    "medicaid_extended": True,
    "mmsm_participant": True,
}

MEDIUM_GAP = {
    **BASE_IDENTITY,
    "facility_id": "330102",
    "facility_name": "Test Medium Gap Hospital",
    "discharge_info_pct": 70.0,
    "well_baby_visit_pct": 74.0,
    "state_postpartum_avg": 82.4,
    "smm_rate": None,
    "hcahps_care_transition_star": 2,
    "hcahps_overall_star": 3,
    "readmission_penalty": False,
    "state_mortality_rank": "middle",
    "racial_disparity_flag": False,
    "medicaid_extended": True,
    "mmsm_participant": False,
}

LOW_GAP = {
    **BASE_IDENTITY,
    "facility_id": "330103",
    "facility_name": "Test Low Gap Hospital",
    "discharge_info_pct": 79.0,
    "well_baby_visit_pct": 81.0,
    "state_postpartum_avg": 82.4,
    "smm_rate": None,
    "hcahps_care_transition_star": 5,
    "hcahps_overall_star": 5,
    "readmission_penalty": False,
    "state_mortality_rank": "middle",
    "racial_disparity_flag": False,
    "medicaid_extended": False,
    "mmsm_participant": False,
}

NULL_DATA = {
    **BASE_IDENTITY,
    "facility_id": "330104",
    "facility_name": "Test Null Data Hospital",
    "discharge_info_pct": None,
    "well_baby_visit_pct": None,
    "state_postpartum_avg": 82.4,
    "smm_rate": None,
    "hcahps_care_transition_star": None,
    "hcahps_overall_star": None,
    "readmission_penalty": None,
    "state_mortality_rank": None,
    "racial_disparity_flag": None,
    "medicaid_extended": None,
    "mmsm_participant": None,
}

NO_COMMITMENT = {
    **BASE_IDENTITY,
    "facility_id": "330105",
    "facility_name": "Test No Commitment Hospital",
    "birthing_friendly": False,
    "commitment_tag": None,
    "commitment_source": None,
    "commitment_year": None,
    "discharge_info_pct": 58.0,
    "well_baby_visit_pct": 92.0,
    "state_postpartum_avg": 82.4,
    "smm_rate": 175.0,
    "hcahps_care_transition_star": 2,
    "hcahps_overall_star": 2,
    "readmission_penalty": True,
    "state_mortality_rank": "bottom_quartile",
    "racial_disparity_flag": True,
    "medicaid_extended": True,
    "mmsm_participant": False,
}

# Isolates smm_rate_gap angle: elevated SMM, no well_baby data, no HCAHPS gap
SMM_ONLY = {
    **BASE_IDENTITY,
    "facility_id": "330106",
    "facility_name": "Test SMM Only Hospital",
    "discharge_info_pct": 78.0,
    "well_baby_visit_pct": None,       # no hospital-level well-baby source
    "state_postpartum_avg": 82.4,
    "smm_rate": 180.0,                 # elevated above 150 threshold
    "hcahps_care_transition_star": 4,  # no HCAHPS gap (>= 3)
    "hcahps_overall_star": 4,
    "readmission_penalty": False,
    "state_mortality_rank": "middle",
    "racial_disparity_flag": False,
    "medicaid_extended": False,
    "mmsm_participant": False,
}

# Isolates financial_unrealized angle: Medicaid extended, no SMM, no HCAHPS gap, no baby-mother data
FINANCIAL_ONLY = {
    **BASE_IDENTITY,
    "facility_id": "330107",
    "facility_name": "Test Financial Only Hospital",
    "discharge_info_pct": 81.0,
    "well_baby_visit_pct": None,       # no hospital-level well-baby source
    "state_postpartum_avg": 82.4,
    "smm_rate": None,                  # no SMM data
    "hcahps_care_transition_star": 4,  # no HCAHPS gap
    "hcahps_overall_star": 4,
    "readmission_penalty": False,
    "state_mortality_rank": "middle",
    "racial_disparity_flag": False,
    "medicaid_extended": True,         # triggers financial_unrealized
    "mmsm_participant": False,
}

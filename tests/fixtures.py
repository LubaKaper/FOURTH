# tests/fixtures.py
"""
Shared test fixtures for all ECHO tests.
Import these instead of defining your own test hospitals.
Every fixture uses SCHEMA.md v0.2 fields.
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
    "discharge_info_star": 1,
    "discharge_help_pct": 62.0,
    "overall_star": 1,
    "state_postpartum_visit_rate": 82.4,
    "state_postpartum_visit_year": 2023,
    "hcahps_start_date": "04/01/2024",
    "hcahps_end_date": "03/31/2025",
    "medicaid_extended": True,
    "racial_disparity_flag": True,
}

MEDIUM_GAP = {
    **BASE_IDENTITY,
    "facility_id": "330102",
    "facility_name": "Test Medium Gap Hospital",
    "discharge_info_star": 2,
    "discharge_help_pct": 70.0,
    "overall_star": 3,
    "state_postpartum_visit_rate": 82.4,
    "state_postpartum_visit_year": 2023,
    "hcahps_start_date": "04/01/2024",
    "hcahps_end_date": "03/31/2025",
    "medicaid_extended": True,
    "racial_disparity_flag": False,
}

LOW_GAP = {
    **BASE_IDENTITY,
    "facility_id": "330103",
    "facility_name": "Test Low Gap Hospital",
    "discharge_info_star": 5,
    "discharge_help_pct": 91.0,
    "overall_star": 5,
    "state_postpartum_visit_rate": 82.4,
    "state_postpartum_visit_year": 2023,
    "hcahps_start_date": "04/01/2024",
    "hcahps_end_date": "03/31/2025",
    "medicaid_extended": True,
    "racial_disparity_flag": False,
}

NULL_DATA = {
    **BASE_IDENTITY,
    "facility_id": "330104",
    "facility_name": "Test Null Data Hospital",
    "discharge_info_star": None,
    "discharge_help_pct": None,
    "overall_star": None,
    "state_postpartum_visit_rate": 82.4,
    "state_postpartum_visit_year": 2023,
    "hcahps_start_date": None,
    "hcahps_end_date": None,
    "medicaid_extended": True,
    "racial_disparity_flag": True,
}

NO_COMMITMENT = {
    **BASE_IDENTITY,
    "facility_id": "330105",
    "facility_name": "Test No Commitment Hospital",
    "birthing_friendly": False,
    "commitment_tag": None,
    "commitment_source": None,
    "commitment_year": None,
    "discharge_info_star": 4,
    "discharge_help_pct": 88.0,
    "overall_star": 4,
    "state_postpartum_visit_rate": 82.4,
    "state_postpartum_visit_year": 2023,
    "hcahps_start_date": "04/01/2024",
    "hcahps_end_date": "03/31/2025",
    "medicaid_extended": True,
    "racial_disparity_flag": False,
}

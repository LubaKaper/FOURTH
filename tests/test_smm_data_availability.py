# tests/test_smm_data_availability.py
"""
PC_07a (SMM rate) is 'Not Available' in the current CMS release, so the
smm_rate_gap angle cannot fire from real data. If this test FAILS, CMS
has shipped SMM data — activate the angle: remove this test, verify
smm-dependent copy, and update README/methodology roadmap notes.
"""

from src.commitment_ingester import get_hospital_commitments
from src.outcome_scorer import score_outcomes


def test_smm_rate_is_none_for_all_hospitals_in_current_release():
    hospitals = score_outcomes(get_hospital_commitments("NY"))
    assert hospitals, "pipeline returned no hospitals — data files missing?"
    assert all(h["smm_rate"] is None for h in hospitals)

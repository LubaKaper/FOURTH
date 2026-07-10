"""
Project-wide constants. State benchmarks, file paths, and lookup tables.

Adding a constant here? Source it. Every value should have a comment
pointing to the file, URL, or rationale it came from.
"""

# Source: CMS Medicaid Adult Core Set, PPC-AD measure, NY filter, 2023.
# Documented at data/core-set-ppc-ad-ny.csv (citation only; not parsed).
# https://www.medicaid.gov/medicaid/quality-of-care/core-set-data-dashboard/welcome
NY_POSTPARTUM_VISIT_RATE_2023: float = 82.4
NY_POSTPARTUM_VISIT_YEAR: int = 2023

# Source: NY State Child Core Set / DOH well-baby visit benchmark, 2023 (GTM research).
# Used as state-level proxy for well_baby_visit_pct when no hospital-specific source exists.
# Verify against CMS Child Core Set or NY DOH before production auto-send.
NY_WELL_BABY_VISIT_RATE_2023: float = 91.5

# NY state-level urgency context. These apply IDENTICALLY to every NY
# hospital — they are facts about the state, not per-hospital signals,
# and add flat urgency-context points in Tool 4 (see SCHEMA.md).
# Sources:
# - medicaid_extended: KFF postpartum Medicaid coverage tracker
#   (data/kff_postpartum_coverage.csv) — NY adopted the 12-month extension.
# - racial_disparity_flag: NCHS Health E-Stat 113 (data/hestat113.pdf) and
#   Cureus racial disparity study (data/cureus-racial-disparity.pdf).
# - state_mortality_rank: NCHS Health E-Stat 113 state maternal mortality tables.
NY_STATE_URGENCY_CONTEXT: dict[str, bool | str] = {
    "medicaid_extended": True,
    "racial_disparity_flag": True,
    "state_mortality_rank": "bottom_quartile",
}

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
# - racial_disparity_flag: documented racial disparity in maternal mortality,
#   national and NY-specific.
#   National: NCHS Health E-Stat 113, "Maternal Mortality Rates in the United
#   States, 2024" (data/hestat113.pdf) — Black non-Hispanic maternal mortality
#   44.8/100k live births vs 14.2 White non-Hispanic (2024, statistically
#   significant). National-only document; it has no state breakdown.
#   NY-specific: NY State Comptroller audit, July 2024
#   (https://www.osc.ny.gov/state-agencies/audits/2024/07/30/maternal-health)
#   — Black women in NY died at over 4x the rate of White women (2018-2020).
#   See also data/cureus-racial-disparity.pdf for peer-reviewed context.
#
# state_mortality_rank is NOT hardcoded here: it is computed per state by
# outcome_scorer from data/state_maternal_mortality.csv (CDC NCHS/NVSS,
# "Maternal Deaths and Mortality Rates by State, 2018-2022"). An earlier
# version hardcoded "bottom_quartile" for NY, which the data contradicts —
# NY (22.4/100k) sits in the second-best quartile of reportable states.
NY_STATE_URGENCY_CONTEXT: dict[str, bool | str] = {
    "medicaid_extended": True,
    "racial_disparity_flag": True,
}

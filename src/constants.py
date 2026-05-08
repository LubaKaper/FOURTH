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

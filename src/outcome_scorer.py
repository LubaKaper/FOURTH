"""
Tool 2 — outcome_scorer.

Takes Tool 1 output and adds ADR outcome fields per SCHEMA.md.

Current repo data has HCAHPS, CMS Maternal Health, CMS HRRP, and the NY
state postpartum benchmark on hand. ADR fields whose source files are
not present yet are emitted as None, per the schema null rule:
downstream scoring gives the missing subcomponent zero points and
continues.

Pure function: builds new dicts via {**h, ...}. Never mutates input.
v1 covers NY only; non-NY hospitals never reach Tool 2 because Tool 1
returns [] for them.
"""

import csv
import logging
import statistics
from pathlib import Path
from typing import Any

from constants import (
    NY_POSTPARTUM_VISIT_RATE_2023,
    NY_STATE_URGENCY_CONTEXT,
    NY_WELL_BABY_VISIT_RATE_2023,
)


logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
HCAHPS_PATH = DATA_DIR / "HCAHPS-Hospital-NY.csv"
MATERNAL_HEALTH_PATH = DATA_DIR / "Maternal_Health-Hospital.csv"
READMISSIONS_PATH = DATA_DIR / "FY_2026_Hospital_Readmissions_Reduction_Program_Hospital.csv"
# CDC NCHS/NVSS, "Maternal Deaths and Mortality Rates by State, 2018-2022".
# Rates for states with <20 deaths are suppressed by CDC (reliability_flag).
STATE_MORTALITY_PATH = DATA_DIR / "state_maternal_mortality.csv"

MEASURE_CARE_TRANSITION_STAR = "H_COMP_6_STAR_RATING"
MEASURE_DISCHARGE_INFO_PCT = "H_DISCH_HELP_Y_P"
MEASURE_OVERALL_STAR = "H_STAR_RATING"
MEASURE_SMM_RATE = "PC_07a"
MEASURE_MMSM = "SM_7"

RELEVANT_MEASURES = frozenset({
    MEASURE_CARE_TRANSITION_STAR,
    MEASURE_DISCHARGE_INFO_PCT,
    MEASURE_OVERALL_STAR,
})

# HCAHPS uses "Not Applicable" and "Not Available" interchangeably for
# unreported values. Both map to None per SCHEMA.md ("missing data is
# None, never imputed").
NULL_SENTINELS = frozenset({"not applicable", "not available", "n/a", ""})

STAR_VALUE_COLUMN = "Patient Survey Star Rating"
PERCENT_VALUE_COLUMN = "HCAHPS Answer Percent"
START_DATE_COLUMN = "Start Date"
END_DATE_COLUMN = "End Date"
MEASURE_ID_COLUMN = "Measure ID"
SCORE_COLUMN = "Score"
EXCESS_READMISSION_RATIO_COLUMN = "Excess Readmission Ratio"


def score_outcomes(
    hospitals: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return a new list of new dicts: each input hospital plus Tool 2
    outcome fields.

    Joins on facility_id (CCN) to HCAHPS-Hospital-NY.csv. Missing rows
    or sentinel values become None — scoring is Tool 3's job, not ours.
    Does not drop hospitals; does not mutate input.
    """
    if isinstance(hospitals, dict):
        raise TypeError(
            "score_outcomes() expects a list of hospital dicts, not a single dict"
        )

    hcahps_index = _build_hcahps_measure_index()
    maternal_index = _build_maternal_health_index()
    readmission_index = _build_readmission_penalty_index()
    mortality_rank_index = _build_state_mortality_rank_index()
    scored = [
        _build_outcome_dict(
            h, hcahps_index, maternal_index, readmission_index, mortality_rank_index
        )
        for h in hospitals
    ]
    logger.info("Tool 2: scored %d hospitals", len(scored))
    return scored


def _build_hcahps_measure_index() -> dict[str, dict[str, dict[str, str]]]:
    """Read HCAHPS-Hospital-NY.csv once; return {ccn: {measure_id: row}}.

    Only retains the three currently relevant measure rows; the ~64 other
    measure rows per facility are dropped to keep the index small.
    """
    index: dict[str, dict[str, dict[str, str]]] = {}
    try:
        with HCAHPS_PATH.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                measure_id = row["HCAHPS Measure ID"]
                if measure_id not in RELEVANT_MEASURES:
                    continue
                ccn = row["Facility ID"]
                index.setdefault(ccn, {})[measure_id] = row
    except OSError as e:
        raise RuntimeError(
            f"Could not read HCAHPS file at {HCAHPS_PATH}: {e}"
        ) from e
    return index


def _build_maternal_health_index() -> dict[str, dict[str, str | None]]:
    """Read Maternal_Health-Hospital.csv; return ADR maternal fields by CCN."""
    index: dict[str, dict[str, str | None]] = {}
    try:
        with MATERNAL_HEALTH_PATH.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                measure_id = row[MEASURE_ID_COLUMN]
                if measure_id not in {MEASURE_SMM_RATE, MEASURE_MMSM}:
                    continue

                ccn = row["Facility ID"]
                entry = index.setdefault(
                    ccn,
                    {
                        "smm_rate_raw": None,
                        "mmsm_participant_raw": None,
                    },
                )
                if measure_id == MEASURE_SMM_RATE:
                    entry["smm_rate_raw"] = row[SCORE_COLUMN]
                elif measure_id == MEASURE_MMSM:
                    entry["mmsm_participant_raw"] = row[SCORE_COLUMN]
    except OSError as e:
        raise RuntimeError(
            f"Could not read CMS Maternal Health file at {MATERNAL_HEALTH_PATH}: {e}"
        ) from e
    return index


def _build_readmission_penalty_index() -> dict[str, bool | None]:
    """Read HRRP rows; return True when any excess readmission ratio is above 1.0."""
    ratios_by_ccn: dict[str, list[float]] = {}
    seen_ccns: set[str] = set()
    try:
        with READMISSIONS_PATH.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                ccn = row["Facility ID"]
                seen_ccns.add(ccn)
                ratio = _to_float_or_none(row[EXCESS_READMISSION_RATIO_COLUMN])
                if ratio is not None:
                    ratios_by_ccn.setdefault(ccn, []).append(ratio)
    except OSError as e:
        raise RuntimeError(
            f"Could not read CMS HRRP file at {READMISSIONS_PATH}: {e}"
        ) from e

    return {
        ccn: (any(ratio > 1.0 for ratio in ratios) if ratios else None)
        for ccn, ratios in ((ccn, ratios_by_ccn.get(ccn, [])) for ccn in seen_ccns)
    }


def _build_state_mortality_rank_index() -> dict[str, str | None]:
    """Read state_maternal_mortality.csv; return {state: quartile rank}.

    Quartile cutoffs are computed over states with reliable (non-suppressed)
    CDC rates only. Mapping per SCHEMA.md's allowed values:
    best quartile -> "top_quartile", worst quartile -> "bottom_quartile",
    middle two -> "middle". Suppressed states map to None — missing data is
    None, never imputed.
    """
    rates: dict[str, float | None] = {}
    try:
        with STATE_MORTALITY_PATH.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rates[row["state"]] = _to_float_or_none(
                    row["maternal_mortality_rate_per_100k"]
                )
    except OSError as e:
        raise RuntimeError(
            f"Could not read state maternal mortality file at {STATE_MORTALITY_PATH}: {e}"
        ) from e

    reliable = sorted(rate for rate in rates.values() if rate is not None)
    if len(reliable) < 4:
        raise RuntimeError(
            f"State maternal mortality file at {STATE_MORTALITY_PATH} has too few "
            f"reliable rates ({len(reliable)}) to compute quartiles"
        )
    q1, _, q3 = statistics.quantiles(reliable, n=4)

    def rank(rate: float | None) -> str | None:
        if rate is None:
            return None
        if rate <= q1:
            return "top_quartile"
        if rate > q3:
            return "bottom_quartile"
        return "middle"

    return {state: rank(rate) for state, rate in rates.items()}


def _lookup_measures(
    index: dict[str, dict[str, dict[str, str]]],
    ccn: str,
) -> dict[str, str | None] | None:
    """Pull raw values for the three relevant measures + dates for one CCN.

    Returns a dict with keys: care_transition_star_raw,
    discharge_info_pct_raw, overall_star_raw.
    Values are raw CSV strings or None when the measure row is absent.

    Returns None if the CCN itself is missing from the index — a
    "shouldn't happen in v1" case (Tool 1 sourced CCNs from this same
    file). The caller is responsible for logging that case loudly.
    """
    rows = index.get(ccn)
    if rows is None:
        return None
    care_transition_row = rows.get(MEASURE_CARE_TRANSITION_STAR)
    discharge_info_row = rows.get(MEASURE_DISCHARGE_INFO_PCT)
    overall_row = rows.get(MEASURE_OVERALL_STAR)
    return {
        "care_transition_star_raw": (
            care_transition_row[STAR_VALUE_COLUMN]
            if care_transition_row is not None
            else None
        ),
        "discharge_info_pct_raw": (
            discharge_info_row[PERCENT_VALUE_COLUMN]
            if discharge_info_row is not None
            else None
        ),
        "overall_star_raw": (
            overall_row[STAR_VALUE_COLUMN]
            if overall_row is not None
            else None
        ),
    }


def _parse_or_none(raw: str | None) -> str | None:
    """Filter HCAHPS null sentinels.

    Returns None for None, empty/whitespace, or any case-insensitive
    match in NULL_SENTINELS. Otherwise returns the stripped string.
    Casts are done by callers; this only decides "is it a real value".
    """
    if raw is None:
        return None
    cleaned = raw.strip()
    if cleaned.lower() in NULL_SENTINELS:
        return None
    return cleaned


def _to_int_or_none(raw: str | None) -> int | None:
    parsed = _parse_or_none(raw)
    return None if parsed is None else int(parsed)


def _to_float_or_none(raw: str | None) -> float | None:
    parsed = _parse_or_none(raw)
    return None if parsed is None else float(parsed)


def _to_mmsm_bool_or_none(raw: str | None) -> bool | None:
    parsed = _parse_or_none(raw)
    if parsed is None:
        return None
    return parsed.casefold() == "yes"


def _build_outcome_dict(
    hospital: dict[str, Any],
    hcahps_index: dict[str, dict[str, dict[str, str]]],
    maternal_index: dict[str, dict[str, str | None]],
    readmission_index: dict[str, bool | None],
    mortality_rank_index: dict[str, str | None],
) -> dict[str, Any]:
    """Return a new dict: input hospital + ADR Tool 2 fields."""
    facility_id = hospital["facility_id"]
    measures = _lookup_measures(hcahps_index, facility_id)
    if measures is None:
        # Should be impossible in v1: Tool 1's CCNs come from this
        # same HCAHPS file. If this fires, the data pipeline is
        # inconsistent (stale file, dedup bug, mismatched CCNs).
        # Degrade gracefully to all-None HCAHPS fields so the rest of
        # the pipeline keeps moving, but log loudly.
        logger.error(
            "facility_id %r in Tool 1 output but missing from HCAHPS "
            "measure index — should be impossible in v1; check for "
            "stale HCAHPS file or pipeline inconsistency",
            hospital["facility_id"],
        )
        measures = {
            "care_transition_star_raw": None,
            "discharge_info_pct_raw": None,
            "overall_star_raw": None,
        }

    maternal = maternal_index.get(
        facility_id,
        {
            "smm_rate_raw": None,
            "mmsm_participant_raw": None,
        },
    )
    discharge_info_pct = _to_float_or_none(measures["discharge_info_pct_raw"])

    return {
        **hospital,
        # H_DISCH_HELP_Y_P — % of patients who reported receiving the
        # information they needed for recovery at discharge. Fourth uses it
        # as its hospital-level discharge-readiness signal. It is NOT a
        # postpartum visit completion rate; outbound copy must never
        # present it as one (enforced by tests/test_copy_honesty.py).
        "discharge_info_pct": discharge_info_pct,
        # No hospital-level well-baby visit source exists in the current CMS files.
        # NY state benchmark used as proxy; well_baby_visit_estimated flags this.
        "well_baby_visit_pct": NY_WELL_BABY_VISIT_RATE_2023,
        "well_baby_visit_estimated": True,
        "state_postpartum_avg": NY_POSTPARTUM_VISIT_RATE_2023,
        "smm_rate": _to_float_or_none(maternal["smm_rate_raw"]),
        "hcahps_care_transition_star": _to_int_or_none(measures["care_transition_star_raw"]),
        "hcahps_overall_star": _to_int_or_none(measures["overall_star_raw"]),
        "readmission_penalty": readmission_index.get(facility_id),
        # State-level context, identical for all NY hospitals (see constants.py)
        **NY_STATE_URGENCY_CONTEXT,
        # Computed from CDC NCHS state data (data/state_maternal_mortality.csv);
        # None when CDC suppressed the state's rate (<20 deaths).
        "state_mortality_rank": mortality_rank_index.get(
            str(hospital.get("state") or "").upper()
        ),
        "mmsm_participant": _to_mmsm_bool_or_none(maternal["mmsm_participant_raw"]),
    }

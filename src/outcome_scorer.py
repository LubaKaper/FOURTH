"""
Tool 2 — outcome_scorer.

Takes Tool 1 output and adds Tool 2 outcome fields per SCHEMA.md by
joining each hospital's CCN to HCAHPS-Hospital-NY.csv on three measure
rows:

    H_COMP_6_STAR_RATING -> discharge_info_star (int 1-5 or None)
    H_DISCH_HELP_Y_P     -> discharge_help_pct  (float or None)
    H_STAR_RATING        -> overall_star        (int 1-5 or None)

Plus the HCAHPS reporting window (Start Date, End Date) and the
hardcoded NY 2023 postpartum-visit benchmark from constants.py.

Pure function: builds new dicts via {**h, ...}. Never mutates input.
v1 covers NY only; non-NY hospitals never reach Tool 2 because Tool 1
returns [] for them.
"""

import csv
import logging
from pathlib import Path
from typing import Any

from constants import NY_POSTPARTUM_VISIT_RATE_2023, NY_POSTPARTUM_VISIT_YEAR


logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
HCAHPS_PATH = DATA_DIR / "HCAHPS-Hospital-NY.csv"

MEASURE_DISCHARGE_INFO_STAR = "H_COMP_6_STAR_RATING"
MEASURE_DISCHARGE_HELP_PCT = "H_DISCH_HELP_Y_P"
MEASURE_OVERALL_STAR = "H_STAR_RATING"

RELEVANT_MEASURES = frozenset({
    MEASURE_DISCHARGE_INFO_STAR,
    MEASURE_DISCHARGE_HELP_PCT,
    MEASURE_OVERALL_STAR,
})

# HCAHPS uses "Not Applicable" and "Not Available" interchangeably for
# unreported values. Both map to None per SCHEMA.md ("missing data is
# None, never imputed").
NULL_SENTINELS = frozenset({"not applicable", "not available", ""})

STAR_VALUE_COLUMN = "Patient Survey Star Rating"
PERCENT_VALUE_COLUMN = "HCAHPS Answer Percent"
START_DATE_COLUMN = "Start Date"
END_DATE_COLUMN = "End Date"


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

    index = _build_hcahps_measure_index()
    scored = [_build_outcome_dict(h, index) for h in hospitals]
    logger.info("Tool 2: scored %d hospitals", len(scored))
    return scored


def _build_hcahps_measure_index() -> dict[str, dict[str, dict[str, str]]]:
    """Read HCAHPS-Hospital-NY.csv once; return {ccn: {measure_id: row}}.

    Only retains the three relevant measure rows; the ~64 other
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


def _lookup_measures(
    index: dict[str, dict[str, dict[str, str]]],
    ccn: str,
) -> dict[str, str | None] | None:
    """Pull raw values for the three relevant measures + dates for one CCN.

    Returns a dict with keys: discharge_info_star_raw,
    discharge_help_pct_raw, overall_star_raw, start_date, end_date.
    Values are raw CSV strings or None when the measure row is absent.

    Returns None if the CCN itself is missing from the index — a
    "shouldn't happen in v1" case (Tool 1 sourced CCNs from this same
    file). The caller is responsible for logging that case loudly.
    """
    rows = index.get(ccn)
    if rows is None:
        return None
    discharge_info_row = rows.get(MEASURE_DISCHARGE_INFO_STAR)
    discharge_help_row = rows.get(MEASURE_DISCHARGE_HELP_PCT)
    overall_row = rows.get(MEASURE_OVERALL_STAR)
    # All three measure rows share the same reporting window for a
    # given CCN, so any present row will do for the dates.
    date_row = discharge_info_row or overall_row or discharge_help_row
    return {
        "discharge_info_star_raw": (
            discharge_info_row[STAR_VALUE_COLUMN]
            if discharge_info_row is not None
            else None
        ),
        "discharge_help_pct_raw": (
            discharge_help_row[PERCENT_VALUE_COLUMN]
            if discharge_help_row is not None
            else None
        ),
        "overall_star_raw": (
            overall_row[STAR_VALUE_COLUMN]
            if overall_row is not None
            else None
        ),
        "start_date": (
            date_row[START_DATE_COLUMN] if date_row is not None else None
        ),
        "end_date": (
            date_row[END_DATE_COLUMN] if date_row is not None else None
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


def _build_outcome_dict(
    hospital: dict[str, Any],
    index: dict[str, dict[str, dict[str, str]]],
) -> dict[str, Any]:
    """Return a new dict: input hospital + the seven Tool 2 fields."""
    measures = _lookup_measures(index, hospital["facility_id"])
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
            "discharge_info_star_raw": None,
            "discharge_help_pct_raw": None,
            "overall_star_raw": None,
            "start_date": None,
            "end_date": None,
        }

    return {
        **hospital,
        "discharge_info_star": _to_int_or_none(measures["discharge_info_star_raw"]),
        "discharge_help_pct": _to_float_or_none(measures["discharge_help_pct_raw"]),
        "overall_star": _to_int_or_none(measures["overall_star_raw"]),
        "state_postpartum_visit_rate": NY_POSTPARTUM_VISIT_RATE_2023,
        "state_postpartum_visit_year": NY_POSTPARTUM_VISIT_YEAR,
        "hcahps_start_date": _parse_or_none(measures["start_date"]),
        "hcahps_end_date": _parse_or_none(measures["end_date"]),
    }

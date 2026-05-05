"""
Tool 1 — commitment_ingester.

Reads the CMS Birthing-Friendly registry and joins to HCAHPS-Hospital-NY
by facility name (with light normalization) to recover the CCN that
becomes `facility_id`. Returns one Tool 1 hospital dict per matched
BF hospital, per SCHEMA.md.

v1 has HCAHPS data for NY only; non-NY states return an empty list.
"""

import csv
import logging
import re
from pathlib import Path
from typing import Any

from name_matching import normalize


logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
BF_PATH = DATA_DIR / "Birthing_Friendly_Hospitals_Geocoded.csv"
HCAHPS_PATH = DATA_DIR / "HCAHPS-Hospital-NY.csv"

V1_COMMITMENT_TAG = "Earned the CMS Birthing-Friendly designation"
V1_COMMITMENT_SOURCE = "CMS Birthing-Friendly Registry"


def get_hospital_commitments(state: str = "NY") -> list[dict[str, Any]]:
    """Return one Tool 1 hospital dict per BF hospital in `state`.

    Joins the BF registry to HCAHPS-Hospital-NY by normalized facility
    name to recover the CCN. Unmatched hospitals are dropped with a
    logged warning. HCAHPS-side normalized-name collisions are dropped
    from the index entirely (assigning either CCN risks silent
    misrouting downstream).

    v1 has HCAHPS data for NY only. Non-NY states return [] without
    iterating the BF registry, to avoid spamming per-row warnings.
    """
    if state != "NY":
        logger.info(
            "v1 has HCAHPS data for NY only; returning [] for state=%s", state
        )
        return []

    ccn_index = _build_hcahps_ccn_index()
    bf_rows = _load_bf_rows_for_state(state)

    hospitals: list[dict[str, Any]] = []
    for row in bf_rows:
        key = normalize(row["name"])
        match = ccn_index.get(key)
        if match is None:
            logger.warning(
                "BF hospital %r could not be matched to HCAHPS — dropping",
                row["name"],
            )
            continue
        hospitals.append(_build_hospital_dict(row, match))

    logger.info(
        "Tool 1: matched %d / %d BF hospitals in %s",
        len(hospitals),
        len(bf_rows),
        state,
    )
    return hospitals


def _load_bf_rows_for_state(state: str) -> list[dict[str, str]]:
    """Read the BF registry; return rows where state matches (uppercased)."""
    try:
        with BF_PATH.open(newline="", encoding="utf-8") as f:
            return [
                row for row in csv.DictReader(f) if row["state"].upper() == state
            ]
    except OSError as e:
        raise RuntimeError(
            f"Could not read BF registry at {BF_PATH}: {e}"
        ) from e


def _build_hcahps_ccn_index() -> dict[str, dict[str, str]]:
    """Build {normalized_name: {ccn, county, name}} from HCAHPS.

    HCAHPS has ~67 measure rows per facility — we keep one per CCN.
    If two distinct facilities share a normalized name, both are
    dropped from the index; the warning logs which names collided.
    """
    buckets: dict[str, list[dict[str, str]]] = {}
    seen_ccns: set[str] = set()
    try:
        with HCAHPS_PATH.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                ccn = row["Facility ID"]
                if ccn in seen_ccns:
                    continue
                seen_ccns.add(ccn)
                key = normalize(row["Facility Name"])
                buckets.setdefault(key, []).append(
                    {
                        "ccn": ccn,
                        "county": row["County/Parish"],
                        "name": row["Facility Name"],
                    }
                )
    except OSError as e:
        raise RuntimeError(
            f"Could not read HCAHPS file at {HCAHPS_PATH}: {e}"
        ) from e

    # HCAHPS occasionally lists the same physical hospital under multiple
    # CCNs (e.g., Carthage Area Hospital appears under 330060 and 331318
    # at the same address). Collision-and-drop is correct here: we'd
    # rather lose both than silently pick the wrong CCN. BF rarely
    # overlaps these cases because BF is keyed off facility name +
    # address, not CCN.
    index: dict[str, dict[str, str]] = {}
    for key, rows in buckets.items():
        if len(rows) > 1:
            collided = [r["name"] for r in rows]
            logger.warning(
                "HCAHPS name collision on %r matches %s — dropping all",
                key,
                collided,
            )
            continue
        index[key] = rows[0]
    return index


def _build_hospital_dict(
    bf_row: dict[str, str],
    hcahps_match: dict[str, str],
) -> dict[str, Any]:
    """Assemble the Tool 1 hospital dict per SCHEMA.md."""
    return {
        "facility_id": hcahps_match["ccn"],
        "facility_name": re.sub(r"\s+", " ", bf_row["name"].replace("\\", "")).strip(),
        "state": bf_row["state"].upper(),
        "city": bf_row["city"],
        "county": hcahps_match["county"],
        "address": bf_row["addr"],
        "zip": bf_row["zip"],
        "lat": float(bf_row["lat"]),
        "lon": float(bf_row["lon"]),
        "birthing_friendly": True,
        "commitment_tag": V1_COMMITMENT_TAG,
        "commitment_source": V1_COMMITMENT_SOURCE,
        "commitment_year": None,
    }

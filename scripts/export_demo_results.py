#!/usr/bin/env python3
"""
export_demo_results.py — run the full Fourth pipeline (review mode) and
write data/demo_results.json for the Streamlit demo app (app.py).

Run locally with live LLM keys in .env to get real generated emails
(one LLM call per selected account):
    .venv/bin/python scripts/export_demo_results.py

Real CMS data, real pipeline output. No mock data. Fails loudly (exit 1)
if the pipeline yields zero accounts or zero emails.
"""

import datetime
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from account_selector import select_top_accounts          # noqa: E402
from approvals import run_approvals                       # noqa: E402
from commitment_ingester import get_hospital_commitments  # noqa: E402
from gap_calculator import calculate_gap_score            # noqa: E402
from outbound_generator import generate_outbound_email    # noqa: E402
from outcome_scorer import score_outcomes                 # noqa: E402
from urgency_ranker import add_urgency                    # noqa: E402

OUTPUT_PATH = ROOT / "data" / "demo_results.json"

HOSPITAL_EXPORT_FIELDS = [
    "facility_id", "facility_name", "city", "county", "state",
    "birthing_friendly", "commitment_tag",
    "discharge_info_pct", "well_baby_visit_pct", "well_baby_visit_estimated",
    "state_postpartum_avg", "smm_rate", "hcahps_care_transition_star",
    "hcahps_overall_star", "readmission_penalty",
    "gap_score", "gap_breakdown", "urgency_tier", "urgency_flag",
    "urgency_breakdown", "lead_angle", "data_confidence",
]


def build_demo_payload(
    hospitals: list[dict[str, Any]],
    emails: list[dict[str, Any]],
    generated_at: str,
) -> dict[str, Any]:
    """Package selected hospitals + their email objects for app.py."""
    email_by_id = {e["facility_id"]: e for e in emails}
    accounts = []
    for hospital in hospitals:
        account = {key: hospital.get(key) for key in HOSPITAL_EXPORT_FIELDS}
        account["email"] = email_by_id.get(hospital["facility_id"])
        accounts.append(account)
    return {"generated_at": generated_at, "state": "NY", "accounts": accounts}


def main() -> int:
    hospitals = get_hospital_commitments("NY")
    hospitals = score_outcomes(hospitals)
    hospitals = [calculate_gap_score(h) for h in hospitals]
    hospitals = [add_urgency(h) for h in hospitals]
    selected = select_top_accounts(hospitals, limit=10, require_high_confidence=False)
    emails = run_approvals(generate_outbound_email(selected))

    if not selected or not emails:
        print(
            f"ERROR: pipeline produced {len(selected)} accounts and "
            f"{len(emails)} emails — refusing to write demo data.",
            file=sys.stderr,
        )
        return 1

    generated_at = datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")
    payload = build_demo_payload(selected, emails, generated_at)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(payload['accounts'])} accounts to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

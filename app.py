"""
Fourth — Account Intelligence for Maternal Health GTM (demo app).

Read-only Streamlit viewer over data/demo_results.json — precomputed
output of the real pipeline over real CMS data. No API keys, no email
sending, no pipeline imports.

Run: streamlit run app.py
"""

import json
from pathlib import Path
from typing import Any

import streamlit as st

RESULTS_PATH = Path(__file__).parent / "data" / "demo_results.json"

REQUIRED_TOP_KEYS = {"generated_at", "state", "accounts"}

TIER_BADGE = {"high": "🔴 High", "medium": "🟡 Medium", "low": "🟢 Low"}

ANGLE_LABELS = {
    "baby_vs_mother_contrast": "Baby vs. mother contrast",
    "hcahps_care_transition_gap": "HCAHPS care transition gap",
    "state_strength_vs_hospital_lag": "State strength vs. hospital lag",
    "financial_unrealized": "Unrealized RPM billing window",
    "smm_rate_gap": "SMM rate gap",
}

# (measure, provenance, meaning) — data honesty shown to every visitor.
SIGNAL_PROVENANCE = [
    ("HCAHPS care transition star", "Hospital-level",
     "CMS HCAHPS H_COMP_6 star rating for the discharge/transition experience."),
    ("Discharge info received %", "Hospital-level",
     "CMS patient-experience survey measure H_DISCH_HELP_Y_P — % of patients who "
     "reported receiving the information they needed for recovery at discharge. "
     "A discharge-readiness signal, NOT a postpartum visit completion rate."),
    ("Well-baby visit %", "State-level proxy",
     "NY Child Core Set 2023 benchmark (91.5%) applied to every hospital; "
     "flagged well_baby_visit_estimated. No hospital-level source exists yet."),
    ("State postpartum visit average", "State benchmark",
     "CMS Medicaid Adult Core Set PPC-AD, NY 2023: 82.4% postpartum visit completion."),
    ("SMM rate", "Not yet available",
     "PC_07a is 'Not Available' in the current CMS release. The smm_rate_gap "
     "lead angle stays dormant until CMS ships it (roadmap: CDC WONDER)."),
    ("Medicaid extension / disparity / mortality rank", "State-level context",
     "State facts applied identically to all NY hospitals; add flat urgency "
     "context points and cannot differentiate hospitals within NY."),
]


def load_results(path: Path = RESULTS_PATH) -> dict[str, Any]:
    """Load and validate the demo payload. Raises ValueError on bad shape."""
    data = json.loads(path.read_text(encoding="utf-8"))
    missing = REQUIRED_TOP_KEYS - set(data)
    if missing:
        raise ValueError(f"demo_results.json missing keys: {', '.join(sorted(missing))}")
    return data


def _fmt(value: Any, suffix: str = "") -> str:
    return "—" if value is None else f"{value}{suffix}"


def _markdown_table(rows: list[dict[str, Any]]) -> str:
    """Render a GitHub-style markdown table from a list of dicts.

    Column order follows the first row's key order; pipe characters in
    values are escaped. Used instead of st.dataframe(): the small tables
    here don't need interactivity, and st.dataframe()'s DataFrame/Arrow
    native conversion segfaulted the interpreter in this environment on
    any script-rerun thread after the first (see commit message).
    """
    if not rows:
        return ""
    headers = list(rows[0].keys())

    def esc(value: Any) -> str:
        return str(value).replace("|", "\\|")

    lines = [
        "| " + " | ".join(esc(h) for h in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(esc(row.get(h, "")) for h in headers) + " |")
    return "\n".join(lines)


def render_accounts(data: dict[str, Any]) -> None:
    st.subheader(f"Top accounts — {data['state']}")
    st.caption(f"Generated {data['generated_at']} from CMS public data.")
    rows = [
        {
            "Hospital": a["facility_name"],
            "Gap score": a["gap_score"],
            "Urgency": TIER_BADGE.get(a["urgency_tier"], a["urgency_tier"]),
            "Lead angle": ANGLE_LABELS.get(a["lead_angle"], a["lead_angle"]),
            "Confidence": a["data_confidence"],
            "Email drafted": "✉️" if a.get("email") else "—",
        }
        for a in data["accounts"]
    ]
    st.markdown(_markdown_table(rows))


def render_account_detail(data: dict[str, Any]) -> None:
    names = [a["facility_name"] for a in data["accounts"]]
    chosen = st.selectbox("Account", names)
    account = next(a for a in data["accounts"] if a["facility_name"] == chosen)

    left, right = st.columns(2)
    with left:
        st.metric("Gap score", account["gap_score"])
        st.write(f"**Urgency:** {TIER_BADGE.get(account['urgency_tier'])}")
        st.write(f"**Lead angle:** {ANGLE_LABELS.get(account['lead_angle'])}")
        if account.get("email"):
            st.write(f"**Angle reason:** {account['email']['angle_reason']}")
    with right:
        st.write("**Gap breakdown**")
        st.json(account.get("gap_breakdown") or {})
        st.write("**Urgency breakdown**")
        st.json(account.get("urgency_breakdown") or {})

    st.divider()
    st.write("**Signals** (provenance in Methodology)")
    st.markdown(_markdown_table(
        [
            {"Signal": "Discharge info received (hospital)", "Value": _fmt(account.get("discharge_info_pct"), "%")},
            {"Signal": "Care transition star (hospital)", "Value": _fmt(account.get("hcahps_care_transition_star"), "/5")},
            {"Signal": "Well-baby visits (state proxy)", "Value": _fmt(account.get("well_baby_visit_pct"), "%")},
            {"Signal": "State postpartum visit avg", "Value": _fmt(account.get("state_postpartum_avg"), "%")},
            {"Signal": "SMM rate", "Value": _fmt(account.get("smm_rate"))},
            {"Signal": "Readmission penalty", "Value": _fmt(account.get("readmission_penalty"))},
        ]
    ))

    st.divider()
    email = account.get("email")
    if not email:
        st.info("No email drafted for this account (below threshold or low confidence).")
        return
    st.write(f"**To:** {email['recipient_role']}  ·  **Status:** `{email['status']}`  ·  "
             f"**Claim validation:** `{email['claim_validation']}`")
    st.write(f"**Subject:** {email['subject']}")
    st.code(email["email_body"], language=None)


def render_methodology() -> None:
    st.subheader("How Fourth works")
    st.markdown(
        """
```text
commitment_ingester → outcome_scorer → gap_calculator → urgency_ranker
      → account_selector → outbound_generator → approvals → send controls
```

**Gap score (0–100), three layers:** commitment strength (0–25, CMS
Birthing-Friendly designation + MMSM participation) · outcome gap (0–50,
discharge-info lag vs. state benchmark, HCAHPS care transition, readmission
penalty, SMM when available) · urgency context (0–25, state-level factors).

**Claim validation.** The LLM drafts only the email body. Deterministic code
then rejects any draft containing a percentage not within 1 point of a real
source field, any star rating that doesn't match the hospital's HCAHPS data,
unsupported claim language, or the internal gap score. Rejected drafts fall
back to deterministic templates. The LLM cannot introduce a number this app
displays.

**Send safety.** Emails hold at `pending_review` for human review. The send
path (not exposed here) enforces an approval gate, a final send gate, a
30-day dedup cooldown, and an append-only audit log with body hashes.
        """
    )
    st.subheader("Signal provenance — what's real, what's proxy")
    st.markdown(_markdown_table(
        [{"Signal": s, "Provenance": p, "Meaning": m} for s, p, m in SIGNAL_PROVENANCE]
    ))


def main() -> None:
    st.set_page_config(page_title="Fourth — Account Intelligence", page_icon="🏥", layout="wide")
    st.title("Fourth")
    st.caption(
        "Account intelligence for maternal health GTM — finds CMS Birthing-Friendly "
        "hospitals whose postpartum follow-through signals lag their commitments. "
        "Demo shows precomputed output of the real pipeline over real CMS data."
    )

    if not RESULTS_PATH.exists():
        st.warning("Demo data not generated yet. Run:")
        st.code(".venv/bin/python scripts/export_demo_results.py")
        st.stop()
    try:
        data = load_results()
    except (ValueError, json.JSONDecodeError) as exc:
        st.error(f"demo_results.json is invalid: {exc}")
        st.stop()

    view = st.sidebar.radio("View", ["Ranked accounts", "Account detail", "Methodology"])
    if view == "Ranked accounts":
        render_accounts(data)
    elif view == "Account detail":
        render_account_detail(data)
    else:
        render_methodology()


if __name__ == "__main__":
    main()

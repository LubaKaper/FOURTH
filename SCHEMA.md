# Fourth — Shared Data Schema

Source of truth: `ADR.md`.

This document defines the legal handoff contracts between Fourth modules. If a field name, type, enum value, or null rule is not in this document, do not implement it. Schema changes require an ADR update first.

Fourth is account intelligence for maternal health GTM. It is built for Babyscripts GTM, owned by Luba Kaper, and targets hospitals where CMS Birthing-Friendly commitments do not match postpartum outcome performance.

---

## Pipeline Order

```text
commitment_ingester
-> outcome_scorer
-> gap_calculator
-> urgency_ranker
-> account_selector
-> outbound_generator
-> human_checkpoint/dashboard_generator
```

One hospital dict travels through the pipeline. Fields are only added. Removing or renaming a field mid-pipeline is a contract violation.

The Human Checkpoint and dashboard are tuning-phase review surfaces. The end-state architecture in `ADR.md` is automatic send once scoring, validation, and prompt reliability are trusted.

---

## GTM Context

**Customer/end user:** Babyscripts GTM Engineer.

**Sales targets:** Hospitals, specifically CMOs and VP Patient Experience roles at hospitals with CMS Birthing-Friendly designation and lagging postpartum outcome scores.

**Service being sold:** Babyscripts remote postpartum monitoring:

- BP monitoring kit
- Mobile app
- OB-specialized care managers
- RPM CPT billing support

**Social proof:** "Hospitals using Babyscripts saw patients become 2x more likely to complete their 30-day postpartum visit." (LCMC Health case study)

**Core outbound hook:** Baby vs mother contrast. "The system you built works — for babies."

---

## Null Handling — Non-Negotiable

Fourth does **not** crash on null outcome fields.

For nullable scoring inputs:

- Missing numeric fields are represented as `None`, never fabricated.
- A missing field contributes `0` points to the scoring layer that uses it.
- A missing field cannot trigger a lead angle that depends on that field.
- The hospital continues through the pipeline.
- `data_confidence` records whether the hospital has enough outcome data to trust the score.

`data_confidence` values:

- `"high"` — the hospital has enough core outcome data to support a specific lead angle.
- `"low"` — one or more core outcome fields needed for the strongest scoring/lead-angle story are missing.

Low-confidence hospitals may still be ranked and reviewed during tuning. Before production auto-send, the orchestrator must enforce the approved confidence threshold.

This rule intentionally differs from the strict no-null language in `ADR.md` Handoff 1. Luba's decision for this repo is: **score zero for the missing layer, flag `data_confidence`, and continue.**

---

## Handoff 0 — CMS CSVs To Commitment Ingester

`commitment_ingester.py` consumes raw CMS/public data directly.

Expected source files from `ADR.md`:

- `Hospital_General_Information.csv`
- `Maternal_Health-Hospital.csv`
- `FY2025_Hospital_Readmissions_Reduction_Program.csv`
- `HCAHPS-Hospital.csv`

Current repo data may still be NY-filtered while migration is underway. The HRRP file currently committed from CMS is `FY_2026_Hospital_Readmissions_Reduction_Program_Hospital.csv`; it provides the same `Excess Readmission Ratio` column used for `readmission_penalty`. Do not invent column names. Open the CSV before mapping any field.

---

## Handoff 1 — Commitment Ingester Output

Function contract:

```python
get_hospital_commitments(state: str) -> list[dict]
```

Each returned hospital dict must include:

```python
{
  # Identity
  "facility_id":       str,          # CMS provider number / CCN
  "facility_name":     str,          # Hospital name; NOT "name" or "hospital_name"
  "state":             str,          # 2-letter uppercase code
  "city":              str,
  "county":            str,
  "address":           str,
  "zip":               str,
  "lat":               float,
  "lon":               float,

  # Commitment signal
  "birthing_friendly": bool,
  "commitment_tag":    str,          # Required for commitment-based outreach
  "commitment_source": str,
  "commitment_year":   int | None,
}
```

Field rules:

- `facility_name` is the only hospital-name field.
- `state` is always two-letter uppercase.
- `commitment_tag` must be present for scored commitment-led accounts. If absent, commitment strength scores `0` and `data_confidence` must reflect the missing support.

---

## Handoff 1B — Outcome Scorer Output

Function contract:

```python
score_outcomes(hospitals: list[dict]) -> list[dict]
```

`score_outcomes()` takes and returns the full hospital list. Passing a single hospital dict is a contract error.

Each hospital dict is enriched with:

```python
{
  # Maternal / infant follow-up outcomes
  "postpartum_visit_pct":          float | None,  # 0.0-100.0
  "well_baby_visit_pct":           float | None,  # 0.0-100.0
  "state_postpartum_avg":          float | None,  # State benchmark, 0.0-100.0

  # Maternal safety / quality outcomes
  "smm_rate":                      float | None,  # Severe maternal morbidity per 10,000 deliveries
  "hcahps_care_transition_star":   int | None,    # 1-5, lower is worse
  "hcahps_overall_star":           int | None,    # 1-5, lower is worse
  "readmission_penalty":           bool | None,

  # Urgency / context signals
  "state_mortality_rank":          str | None,    # "top_quartile" | "bottom_quartile" | "middle"
  "racial_disparity_flag":         bool | None,
  "medicaid_extended":             bool | None,
  "mmsm_participant":              bool | None,
}
```

Allowed `state_mortality_rank` values:

- `"top_quartile"`
- `"bottom_quartile"`
- `"middle"`
- `None`

Null scoring rules:

| Field | If `None` |
|---|---|
| `postpartum_visit_pct` | Scores `0` for postpartum-vs-state outcome subcomponent; cannot drive `baby_vs_mother_contrast` without `well_baby_visit_pct`. |
| `well_baby_visit_pct` | Scores `0` for baby-vs-mother contrast; cannot drive `baby_vs_mother_contrast`. |
| `state_postpartum_avg` | Scores `0` for state-strength comparison; cannot drive `state_strength_vs_hospital_lag`. |
| `smm_rate` | Scores `0` for SMM subcomponent; cannot drive `smm_rate_gap`. |
| `hcahps_care_transition_star` | Scores `0` for HCAHPS subcomponent; cannot drive `hcahps_care_transition_gap`. |
| `hcahps_overall_star` | Display/context only unless a downstream test explicitly uses it. |
| `readmission_penalty` | `None` is treated as no points, not as `False` in source display. |
| `state_mortality_rank` | Scores `0` for mortality-rank urgency context. |
| `racial_disparity_flag` | Scores `0` for disparity urgency context. |
| `medicaid_extended` | Scores `0` for Medicaid-extension urgency context. |
| `mmsm_participant` | Scores `0` for MMSM commitment-strength subcomponent. |

---

## Handoff 2 — Gap Calculator Output

Function contract:

```python
calculate_gap_score(hospital: dict) -> dict
```

Adds:

```python
{
  "gap_score":          float,       # 0-75 after Tool 3; urgency layer not added yet
  "lead_angle":         str,
  "gap_breakdown": {
      "commitment_strength": int,    # 0-25
      "outcome_gap":         int,    # 0-50
      "urgency_context":     int,    # 0 after Tool 3; filled by Tool 4
  },
  "data_confidence":    str,         # "high" | "low"
}
```

`gap_score` after Tool 3 is intermediate. Downstream modules must not treat it as final until `urgency_tier` exists.

---

## Handoff 2B — Urgency Ranker Output

Function contract:

```python
add_urgency(hospital: dict) -> dict
```

Updates `gap_score` to final 0-100 value and adds:

```python
{
  "gap_score":              float,   # 0-100 final
  "urgency_tier":           str,     # "high" | "medium" | "low"
  "urgency_flag":           str,     # exact values below
  "medicaid_extended":      bool | None,
  "racial_disparity_flag":  bool | None,
}
```

Exact `urgency_tier` values:

- `"high"`
- `"medium"`
- `"low"`

Exact `urgency_flag` values:

- `"🔴 Act this week"`
- `"🟡 Monitor"`
- `"🟢 Not ready"`

Urgency thresholds:

| Final `gap_score` | Tier | Flag | Pipeline behavior |
|---:|---|---|---|
| `70+` | `"high"` | `"🔴 Act this week"` | Eligible for top 10 and outbound. |
| `40-69` | `"medium"` | `"🟡 Monitor"` | Eligible for top 10 and outbound during tuning. |
| `<40` | `"low"` | `"🟢 Not ready"` | Orchestrator/account selector stops; no outbound generated. |

---

## Gap Score Formula

Three layers, 0-100 total.

### Layer 1 — Commitment Strength, 0-25

| Signal | Points |
|---|---:|
| `birthing_friendly is True` | 15 |
| `mmsm_participant is True` | 10 |
| Future manual curated commitment tag bonus | 5 bonus, capped at layer max |

Missing/null commitment inputs score `0` for their subcomponent.

### Layer 2 — Outcome Gap, 0-50

| Signal | Points |
|---|---:|
| `smm_rate` above accepted benchmark | up to 20 |
| `postpartum_visit_pct` below `state_postpartum_avg` | up to 15 |
| `hcahps_care_transition_star < 3` | up to 10 |
| `readmission_penalty is True` | 5 |

Missing/null outcome inputs score `0` for their subcomponent.

### Layer 3 — Urgency Context, 0-25

| Signal | Points |
|---|---:|
| `state_mortality_rank == "bottom_quartile"` | 10 |
| `racial_disparity_flag is True` | 8 |
| `medicaid_extended is True` | 7 |

Missing/null urgency inputs score `0` for their subcomponent.

---

## Lead Angle Selection

Exact valid `lead_angle` values:

- `"baby_vs_mother_contrast"` — well-baby visit completion materially outperforms postpartum maternal visit completion.
- `"hcahps_care_transition_gap"` — patient experience / care transition signal is weak.
- `"state_strength_vs_hospital_lag"` — hospital postpartum performance lags the state benchmark.
- `"financial_unrealized"` — Medicaid coverage/RPM billing context supports financial framing.
- `"smm_rate_gap"` — severe maternal morbidity signal is elevated.

Priority order:

1. `baby_vs_mother_contrast`
   - Use when both `well_baby_visit_pct` and `postpartum_visit_pct` are present and the baby-vs-mother gap is large enough to support the hook.
2. `smm_rate_gap`
   - Use when `smm_rate` is present and elevated against the accepted benchmark.
3. `hcahps_care_transition_gap`
   - Use when `hcahps_care_transition_star` is present and below 3.
4. `financial_unrealized`
   - Use when Medicaid/RPM context is present and the financial angle can be grounded without inventing payer mix or revenue.
5. `state_strength_vs_hospital_lag`
   - Use when `postpartum_visit_pct` and `state_postpartum_avg` are present and hospital performance lags the benchmark.

If no specific lead angle can be grounded because required fields are `None`, default to `state_strength_vs_hospital_lag` only if its required fields are present. Otherwise set the best available review-safe angle and mark `data_confidence = "low"`.

---

## Handoff 3 — Account Selector To Outbound Generator

Function contract:

```python
select_top_accounts(hospitals: list[dict], limit: int = 10) -> list[dict]
```

Selection rules:

- Exclude `urgency_tier == "low"` / `gap_score < 40`.
- Rank by final `gap_score` descending.
- Return at most 10 hospitals.
- Preserve all upstream fields.
- During tuning, low-confidence hospitals may remain visible for review but should not auto-send in production.

Outbound Generator assumes:

- `gap_score >= 40`
- `urgency_tier` is present
- `lead_angle` is one of the five exact valid strings
- `facility_name` is present
- `commitment_tag` is present for commitment-led copy; otherwise copy must avoid quoting a missing commitment

---

## Handoff 4 — Outbound Generator Output

Function contract:

```python
generate_outbound_email(hospitals: list[dict]) -> list[dict]
```

During tuning, Fourth may generate three angle variants for dashboard review. The ADR production send contract is one send-ready email object per hospital:

```python
{
  "facility_id":      str,
  "facility_name":    str,
  "recipient_role":   str,       # "CMO" | "VP Patient Experience"
  "subject":          str,
  "email_body":       str,
  "product":          str,       # exactly "Babyscripts"
  "lead_angle":       str,
  "gap_score":        float,
  "urgency_tier":     str,
  "sent_at":          None,      # populated on send
  "status":           str,       # "pending_review" | "ready_to_send"
}
```

Allowed `recipient_role` values:

- `"CMO"`
- `"VP Patient Experience"`

Allowed `product` value:

- `"Babyscripts"`

Allowed `status` values:

- `"pending_review"` — tuning phase; Human Checkpoint/dashboard displays for review.
- `"ready_to_send"` — production target; orchestrator may send automatically once safety gates are approved.

Current transition note:

- Existing tests/code may still use `body_moral`, `body_clinical`, `body_financial`, `to_role`, and `generation_method`.
- Those fields are legacy tuning fields and must be migrated through tests before production send behavior is implemented.

---

## Field Rules — Non-Negotiable

1. `facility_name`, not `name` or `hospital_name`.
2. `state` is always two-letter uppercase.
3. `score_outcomes()` takes `list[dict]`, not one dict.
4. `gap_score` is intermediate until `urgency_tier` exists.
5. `lead_angle` is exactly one of the five schema values.
6. `urgency_tier` is exactly `"high"`, `"medium"`, or `"low"`.
7. `urgency_flag` is exactly one of the three emoji-prefixed schema values.
8. Missing data does not crash the pipeline; it scores `0` for the affected subcomponent and lowers `data_confidence`.
9. Production auto-send cannot happen for a hospital until threshold, confidence, and validation gates are explicitly satisfied.

---

## Removed / Legacy v0.2 Fields

These fields are from the prior ECHO/Fourth v0.2 contract and should be migrated away as tests and logic move to the ADR schema:

- `discharge_info_star`
- `discharge_help_pct`
- `overall_star`
- `state_postpartum_visit_rate`
- `state_postpartum_visit_year`
- `hcahps_start_date`
- `hcahps_end_date`
- `to_role`
- `body_moral`
- `body_clinical`
- `body_financial`
- `lead_angle_used`
- `generation_method`

Do not add new behavior against these legacy fields unless it is explicitly part of the migration bridge.

---

## Data Sources

ADR target files:

| Source file | Provides |
|---|---|
| `Hospital_General_Information.csv` | identity, location, CMS provider number |
| `Maternal_Health-Hospital.csv` | maternal quality/outcome fields including SMM and follow-up where available |
| `FY2025_Hospital_Readmissions_Reduction_Program.csv` | `readmission_penalty`; current repo refresh uses `FY_2026_Hospital_Readmissions_Reduction_Program_Hospital.csv` |
| `HCAHPS-Hospital.csv` | HCAHPS care transition / patient experience signals |

Current repo files may remain in use until the migration is implemented. When source files conflict with this schema, update the ADR/schema before code.

---

*Last updated: May 5, 2026 — Fourth ADR-aligned schema. Luba Kaper, solo owner.*

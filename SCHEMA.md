# ECHO — Shared Data Schema (v0.2)
Team Female | Pursuit AI-Native Cycle 3 | April 2026

This is the team's source of truth. If a field name, type, or value is not in this document, it does not exist. Every function in every file must match this schema exactly.

---

## Changes from v0.1 → v0.2

This version reflects the actual data we have on hand. v0.1 was written before we ingested the source CSVs and assumed CMS files we never pulled. v0.2 maps every field to a real source.

**Renamed**
- `care_transition_score` → `discharge_info_star`. Source: HCAHPS `H_COMP_6_STAR_RATING`. Type unchanged (int 1-5). Old name implied a "care transition" measure that doesn't exist in HCAHPS. New name matches what the field actually is: the discharge information composite star rating.

**Added**
- `discharge_help_pct` (float | None). Source: HCAHPS `H_DISCH_HELP_Y_P`. Percentage of patients who said YES, they discussed help after discharge. Display field for the briefing card; not used in scoring math.
- `state_postpartum_visit_rate` (float). The state-level Medicaid postpartum care rate from CMS Core Set PPC-AD. Used in mismatch calculation as the "state achieves X" benchmark.
- `state_postpartum_visit_year` (int). Reporting year for the state rate. Used for citation in emails and briefing cards.

**Removed (moved to v2 roadmap)**
- `severe_morbidity_rate`, `maternal_quality_score`, `well_baby_visit_pct`, `excess_readmission_ratio`, `readmission_penalty`, `medicaid_pct`, `compared_to_national`, `state_avg_postpartum_pct`. None of these had a v1 data source. v1 doesn't need them for the within-state mismatch story (Option 3).

**Lead angle enum (replaces v0.1 set entirely)**
- `hcahps_discharge_gap` — hospital scores low on the discharge information composite (H_COMP_6_STAR_RATING)
- `hcahps_care_transition_gap` — hospital scores low on overall patient experience (H_STAR_RATING). Named for narrative purposes; HCAHPS has no literal "care transition" measure, but the overall star is the closest aggregate signal.
- `state_strength_vs_hospital_lag` — the default headline mismatch: state achieves X, hospital lags. Used when no specific HCAHPS measure is severely failing.

**Promoted to scoring**
- `overall_star` (H_STAR_RATING) — was "context only" in earlier draft, now used in scoring. Drives `hcahps_care_transition_gap` when low.

**Removed from urgency Layer 3**
- `state_mortality_rate`, `state_mortality_rank`, `racial_disparity_flag` — kept (CDC and Cureus PDFs available as citations).
- `medicaid_extended` — kept (KFF file ingested).

**Impact on email variants**
- The `body_financial` variant in v0.1 quoted `medicaid_pct` (hospital-level Medicaid mix). That field is gone. Paula's financial variant should now lead with state-level Medicaid context: NY has 12-month postpartum Medicaid coverage implemented since June 2023 (KFF tracker). This preserves three-variant structure without quoting a number we can't verify.

**Data file scope**
- HCAHPS-Hospital file is NY-filtered for v1 (`HCAHPS-Hospital-NY.csv`, 161 facilities, 3.3 MB) to keep the repo committable. Full national file (~102 MB) is regenerated via `scripts/filter_hcahps_to_ny.py` when refreshing data.

---

## Pipeline Order
Jonel (Tools 1+2) → Luba (Tools 3+4) → Paula (Tools 5+6) → Human

Jonel must finish first. Luba cannot score without Jonel's output. Paula cannot generate emails without Luba's scores.

---

## The Hospital Dict — Full Schema

One dict per hospital travels through the entire pipeline. Each tool adds fields. Nothing is renamed or removed mid-pipeline.

### After Tool 1 — Commitment Ingester (Jonel)

```python
{
  # ── IDENTITY ──────────────────────────────────────────────────────
  "facility_id":        str,    # CMS CCN e.g. "330024"
                                # PRIMARY KEY — joins to HCAHPS-Hospital-NY.csv
                                # Sourced from HCAHPS-Hospital join, not from
                                # Birthing-Friendly registry (which has no CCN)
  "facility_name":      str,    # Full name e.g. "Mount Sinai Hospital"
  "state":              str,    # 2-letter code e.g. "NY" — ALWAYS uppercase
  "city":               str,    # City e.g. "New York"
  "county":             str,    # County name from HCAHPS-Hospital "County/Parish"
  "address":            str,    # Street address from Birthing-Friendly registry
  "zip":                str,    # ZIP code from Birthing-Friendly registry
  "lat":                float,  # Latitude from Birthing-Friendly registry
  "lon":                float,  # Longitude from Birthing-Friendly registry

  # ── COMMITMENT SIGNAL ─────────────────────────────────────────────
  "birthing_friendly":  bool,   # Always True in v1 (universe is BF registry)
  "commitment_tag":     str,    # The quotable commitment sentence.
                                # v1 default for all hospitals:
                                # "Earned the CMS Birthing-Friendly designation"
                                # v2 will replace per-hospital with curated tags
                                # (PQC membership, press releases, AIM bundle).
  "commitment_source":  str,    # "CMS Birthing-Friendly Registry" in v1.
  "commitment_year":    int | None,  # Year designation was earned. None if not on file.
}
```

### After Tool 2 — Outcome Scorer (Jonel)

Adds outcome fields to the dict above:

Function contract:

```python
score_outcomes(hospitals: list[dict]) -> list[dict]
```

Tool 2 always receives and returns a list of hospital dicts. Passing a single hospital dict is a contract error.

```python
{
  # ── HOSPITAL-LEVEL OUTCOMES (HCAHPS) ──────────────────────────────
  "discharge_info_star":   int | None,    # H_COMP_6_STAR_RATING — 1-5
                                          # LOWER = WORSE
                                          # None if hospital not in HCAHPS or
                                          #   measure not reported
  "discharge_help_pct":    float | None,  # H_DISCH_HELP_Y_P percent
                                          # Display field for briefing card
  "overall_star":          int | None,    # H_STAR_RATING — 1-5 summary
                                          # LOWER = WORSE
                                          # Used in scoring: drives
                                          # hcahps_care_transition_gap lead angle
                                          # when low.

  # ── STATE-LEVEL OUTCOME BENCHMARK (Core Set PPC-AD) ───────────────
  "state_postpartum_visit_rate":  float,  # NY 2023 = 82.4
                                          # Source: CMS Medicaid Core Set
                                          # Dashboard, PPC-AD, all-ages.
                                          # Hardcoded constant in v1; one number
                                          # per state. Travels with every
                                          # hospital dict in that state.
  "state_postpartum_visit_year":  int,    # Reporting year e.g. 2023

  # ── DATA PROVENANCE ───────────────────────────────────────────────
  "hcahps_start_date":  str | None,  # Survey period start, e.g. "04/01/2024"
  "hcahps_end_date":    str | None,  # Survey period end, e.g. "03/31/2025"
}
```

### After Tool 3 — Gap Calculator (Luba)

Adds gap score fields:

```python
{
  # ── GAP SCORE ─────────────────────────────────────────────────────
  "gap_score":          float,  # 0-75 AFTER this tool (intermediate)
                                # ⚠️ NOT FINAL — urgency_ranker adds up to 25 more
                                # Paula must NOT read gap_score until after
                                # add_urgency() runs.
  "lead_angle":         str,    # Which mismatch to lead with in outbound email.
                                # EXACTLY one of these three strings:
                                # "hcahps_discharge_gap"
                                # "hcahps_care_transition_gap"
                                # "state_strength_vs_hospital_lag"
                                # See "Lead Angle Selection Logic" below for
                                # how Luba's scorer picks between them.
  "gap_breakdown":      dict,   # Point breakdown for transparency:
                                # {
                                #   "commitment_strength": int,  # 0-25
                                #   "outcome_gap": int,          # 0-50
                                #   "urgency_context": int       # 0-25 (Tool 4)
                                # }
  "data_confidence":    str,    # "high" or "low"
                                # "low" = both discharge_info_star AND
                                #   overall_star are None (no hospital-level
                                #   HCAHPS data at all)
                                # "high" = discharge_info_star is present
                                # Paula: show "data unavailable" on briefing card
                                #   when data_confidence = "low"
}
```

### After Tool 4 — Urgency Ranker (Luba)

Updates `gap_score` to FINAL value and adds urgency fields:

```python
{
  # ── URGENCY ───────────────────────────────────────────────────────
  "gap_score":              float,  # ✅ FINAL — Layer 1 + 2 + 3 complete
                                    # Max 100 for v1 hospitals.
                                    # Paula reads this value, not the
                                    # intermediate one.
  "urgency_flag":           str,    # EXACTLY one of:
                                    # "🔴 Act this week"
                                    # "🟡 Monitor"
                                    # "🟢 Not ready"
  "urgency_tier":           str,    # EXACTLY one of: "high" / "medium" / "low"
                                    # Paula's email template branches on this.
                                    # Lowercase, no variations.
  "medicaid_extended":      bool,   # True if state has 12-month postpartum
                                    # Medicaid coverage. Source: KFF tracker.
                                    # NY = True (implemented June 2023).
  "racial_disparity_flag":  bool,   # True if Black MMR > 2x White MMR in state.
                                    # Source: NCHS Health E-Stat 113.
                                    # National 2024: Black 44.8 vs White 14.2 →
                                    # ratio 3.15. NY-specific values from
                                    # Health E-Stat detail tables.
}
```

### After Tool 5 — Outbound Generator (Paula)

One email object per hospital, separate from the hospital dict. Each has **three body variants** generated via OpenRouter. The GTM engineer picks one from the dashboard. Nothing is sent automatically.

```python
{
  "facility_id":        str,   # Matches hospital dict. Links email to account.
  "subject":            str,   # Email subject line (same for all 3 variants)
  "to_role":            str,   # Recommended contact role.
                               # EXACTLY one of:
                               # "CMO"
                               # "VP of Women's Services"
                               # "Chief Nursing Officer"
                               # "VP of Quality"

  # ── Three email body variants ─────────────────────────────────────────
  # Generated via OpenRouter.
  # GTM engineer reads all three on dashboard and picks the one that fits.
  # All three quote commitment_tag and name a specific lagging metric with
  # a number ECHO actually has.

  "body_moral":         str,   # Variant A — leads with commitment vs. outcome gap
                               # Hook: quotes commitment_tag, then names the
                               # within-state mismatch (this hospital below
                               # state benchmark)

  "body_clinical":      str,   # Variant B — leads with patient care failure
                               # Hook: discharge_info_star or postpartum visit
                               # gap with state benchmark numbers

  "body_financial":     str,   # Variant C — leads with state coverage context
                               # Hook: NY's 12-month postpartum Medicaid
                               # coverage (KFF) creates a longer follow-up
                               # window. Does NOT quote hospital-level Medicaid
                               # mix or imply reimbursement risk/revenue.

  # ── Metadata ──────────────────────────────────────────────────────────
  "lead_angle_used":    str,   # Which lead_angle from hospital dict drove
                               # subject line; pre-selects variant on dashboard.
  "urgency_tier":       str,   # Copied from hospital dict.
  "generation_method":  str,   # "openrouter_api" or "cached_fallback"
                               # cached_fallback ONLY when:
                               #   1. OpenRouter API call fails, OR
                               #   2. commitment_tag is None
                               # Hospitals with data_confidence="low" are
                               # skipped entirely; no email object is created.
}
```

**Lead angle → default variant mapping** (pre-selects on dashboard load):

| lead_angle | Default variant |
|------------|----------------|
| `hcahps_discharge_gap` | `body_clinical` |
| `hcahps_care_transition_gap` | `body_clinical` |
| `state_strength_vs_hospital_lag` | `body_moral` |

The GTM engineer can switch variants manually before copying.

---

## Lead Angle Selection Logic

The lead angle drives how the email opens and which variant pre-selects on the dashboard. Luba's `gap_calculator.py` picks the angle using a priority cascade — specific failures lead when severe, otherwise the default headline mismatch.

**Priority order (first match wins):**

1. `overall_star` is 1 or 2 → `hcahps_care_transition_gap`
   - The hospital is failing on overall patient experience. Lead with that.

2. `discharge_info_star` is 1 or 2 → `hcahps_discharge_gap`
   - The hospital is failing specifically on discharge information. Lead with that.

3. Otherwise → `state_strength_vs_hospital_lag`
   - The default. Tells the headline Option 3 mismatch story:
     "NY achieves X% on postpartum care; this Birthing-Friendly hospital
     scores Y on patient experience; the commitment and outcomes don't match."

**Null handling in the cascade:**

- If `overall_star` is `None`, skip rule 1.
- If `discharge_info_star` is `None`, skip rule 2.
- If both are `None`, the default rule still applies — `state_strength_vs_hospital_lag` only requires the state benchmark, which is always present.
- The default angle is what makes `data_confidence` still useful even with limited hospital data.

---

## ⚠️ Critical Handoff Note — gap_score

`gap_score` appears in the hospital dict after Tool 3 AND after Tool 4.

- After Tool 3 (`calculate_gap_score`): value is 0-75. **Intermediate**. Do not use.
- After Tool 4 (`add_urgency`): value is 0-100. **Final**. Paula reads this.

Paula's Outbound Generator must only consume hospital dicts that have passed through `add_urgency()`. If `urgency_tier` is not present in the dict, `add_urgency()` has not run yet. Do not proceed.

---

## Field Rules — Non-Negotiable

1. **Field names are exact.** `facility_name` not `hospital_name`. `discharge_info_star` not `discharge_star`. Copy from this doc, do not type from memory.

2. **State is always 2-letter uppercase.** `"NY"` not `"New York"` not `"ny"`.

3. **`urgency_tier` is always one of exactly three strings.** `"high"` / `"medium"` / `"low"`. Lowercase. Paula's email template branches on this. Any variation breaks her code.

4. **`commitment_tag` is a specific quotable sentence.** v1 default is `"Earned the CMS Birthing-Friendly designation"` for all hospitals (the BF designation IS the commitment in v1). v2 will replace with curated per-hospital tags.

5. **`gap_score` after Tool 3 is intermediate.** Only read `gap_score` after `urgency_tier` is present in the dict.

6. **`facility_id` is the CCN string from HCAHPS-Hospital.** Not the BF registry index, not a row number. The 6 NY BF hospitals whose names don't exact-match HCAHPS get matched via name normalization (uppercase, strip apostrophes/punctuation/escape chars). Hospitals that still can't be matched after normalization are dropped from v1 with a logged warning.

7. **`generation_method` is exactly one of two strings.** `"openrouter_api"` when live generation succeeds, or `"cached_fallback"` when the API fails or grounding data is missing.

---

## Missing Data Handling

CMS data has gaps. Tools must never crash on `None`. Hospitals are scored on what is available and flagged with `data_confidence`. **No imputation, ever.**

### Per-field rules

| Field | If missing | Effect on scoring |
|-------|-----------|-------------------|
| `discharge_info_star` | `None` | Skip `hcahps_discharge_gap` lead angle in Layer 2 |
| `discharge_help_pct` | `None` | No scoring impact (display only) |
| `overall_star` | `None` | Skip `hcahps_care_transition_gap` lead angle in Layer 2 |
| `state_postpartum_visit_rate` | Always present (hardcoded NY constant in v1) | n/a |
| `commitment_year` | `None` | No scoring impact |

### data_confidence field

Output of `gap_calculator.py`:

- `"low"` — both `discharge_info_star` AND `overall_star` are `None`. We have no hospital-level HCAHPS data at all, so neither specific lead angle can fire. The hospital still gets scored under `state_strength_vs_hospital_lag` but with low confidence.
- `"high"` — at least one of `discharge_info_star` or `overall_star` is present.

**Paula:** when `data_confidence = "low"`, display `"data unavailable"` on the briefing card instead of the gap score number. Skip email generation for that hospital.

### Implementation rules for Luba

- Use `hospital.get("field_name") is not None` before every calculation that could receive `None`.
- Never substitute `0` for a missing value — that would falsely penalize the hospital.
- Never skip a hospital in Tool 3 — score what's there, set `data_confidence` accordingly.
- Tool 5 (Paula) is where low-confidence hospitals get filtered out of email generation.

---

## v1 Scope Boundaries

These are **NOT** in v1:

- Live web scraping of press releases
- CRM integration
- Sending emails
- Clinical recommendations
- Patient-facing features
- Hospital-level severe maternal morbidity, readmissions, or maternal quality scores
- Hospital-level Medicaid payer mix
- Per-hospital curated commitment tags (all v1 hospitals share one default tag)
- Silent Gap mode

---

## v2 Roadmap

These get reintroduced when their data sources are wired up:

- **CMS Maternal Health Hospital file** → restores `severe_morbidity_rate`, `maternal_quality_score`, `compared_to_national`, `well_baby_visit_pct`. Restores `baby_vs_mother_contrast` and `severe_morbidity_rate` lead angles.
- **CMS Hospital Readmissions Reduction Program file** → restores `excess_readmission_ratio`, `readmission_penalty`. Restores `readmission_penalty` lead angle.
- **CMS Hospital Provider Cost Report** → restores `medicaid_pct`. Restores hospital-level financial variant.
- **Curated commitment database** (PQC membership, AIM bundles, press release mining) → replaces default `commitment_tag` with per-hospital specifics. Restores `commitment_source` variation.
- **Silent Gap mode** → adds `has_commitment: bool` and `silent_gap` lead angle. Caps score at 75 for non-committed hospitals.
- **Disparity widening trend** → adds `disparity_worsening_trend: bool` to urgency context (Layer 3) using Cureus 2025 post-pandemic data. A widening trend is a stronger urgency signal than a static gap.

---

## File Ownership

| File | Owner | Depends on |
|------|-------|-----------|
| `commitment_ingester.py` | Jonel | `Birthing_Friendly_Hospitals_Geocoded.csv` + `HCAHPS-Hospital-NY.csv` (for CCN crosswalk) |
| `outcome_scorer.py` | Jonel | `HCAHPS-Hospital-NY.csv` + state constants module |
| `gap_calculator.py` | Luba | Output of `outcome_scorer.py` |
| `urgency_ranker.py` | Luba | Output of `gap_calculator.py` + KFF + NCHS constants |
| `outbound_generator.py` | Paula | Output of `urgency_ranker.py` + OpenRouter |
| `human_checkpoint.py` | Paula | Output of `outbound_generator.py` |

---

## Data Sources On Hand

Every field above traces to a real file:

| File | Provides |
|------|----------|
| `Birthing_Friendly_Hospitals_Geocoded.csv` | facility_name, state, city, address, zip, lat, lon, birthing_friendly |
| `HCAHPS-Hospital-NY.csv` | facility_id (CCN), county, discharge_info_star, discharge_help_pct, overall_star, hcahps_start_date, hcahps_end_date |
| `core-set-data-dashboard...postpartum-care...csv` | state_postpartum_visit_rate (82.4 for NY 2023), state_postpartum_visit_year |
| `raw_data.csv` (KFF) | medicaid_extended (True for NY) |
| `hestat113.pdf` | racial_disparity_flag (computed from Black vs White MMR ratio) |

---

*Last updated: April 28, 2026 — Team Female, Pursuit AI-Native Cycle 3*
*v0.2 changes: schema rewritten by Jonel after data ingestion, pending Luba and Paula review.*

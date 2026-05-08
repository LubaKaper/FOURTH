# ECHO v1 Build Plan

This plan follows `prd.md` and `SCHEMA.md`. If there is a conflict, `SCHEMA.md` wins for field names, allowed values, null handling, and pipeline contracts.

## Goal

Build the v1 ECHO pipeline:

```text
commitment_ingester -> outcome_scorer -> gap_calculator -> urgency_ranker -> outbound_generator -> human_checkpoint
```

One hospital dict moves through the full pipeline. Each tool only adds fields. No tool removes or renames fields.

v1 detects a within-state mismatch:

```text
CMS Birthing-Friendly commitment
+ hospital HCAHPS patient experience lag
+ state postpartum visit strength
```

v1 uses local data files in `data/` for demo reliability. Do not build live scraping or rely on live API calls in the core pipeline. v1 uses OpenRouter for email generation with cached fallback. Anthropic is v2 only.

The concrete seller context is **NurtureBridge Health**, which sells **Postpartum Handoff Navigation** to hospitals. Outbound should use that service context while keeping hospital-specific claims limited to ECHO's schema fields and source files.

## Source Of Truth

Read in this order before implementation:

1. `prd.md` - product direction and scope.
2. `SCHEMA.md` - exact field names, allowed values, null rules, and file dependencies.
3. `tests/fixtures.py` - shared test hospitals.
4. This file - build order and ownership.

Do not implement any field or feature that is not in `SCHEMA.md`.

## v1 Scope

Use these v1 outcome fields:

- `discharge_info_star`
- `discharge_help_pct`
- `overall_star`
- `state_postpartum_visit_rate`
- `state_postpartum_visit_year`
- `hcahps_start_date`
- `hcahps_end_date`

Do not use these old/v2 fields in v1:

- `hcahps_discharge_score`
- `hcahps_discharge_national_avg`
- `hcahps_care_transition_score`
- `state_postpartum_care_pct`
- `compared_to_national`
- `severe_morbidity_rate`
- `postpartum_visit_pct`
- `well_baby_visit_pct`
- `maternal_quality_score`
- `readmission_penalty`
- `excess_readmission_ratio`
- `medicaid_pct`

Valid v1 `lead_angle` values:

- `hcahps_discharge_gap`
- `hcahps_care_transition_gap`
- `state_strength_vs_hospital_lag`

Valid v1 `generation_method` values:

- `openrouter_api`
- `cached_fallback`

## Ownership

This is now Luba's standalone repo. Historical owner names in older task headings are origin/history only.

| Files | Responsibility |
|---|---|
| `src/commitment_ingester.py`, `src/outcome_scorer.py`, `tests/test_commitment_ingester.py`, `tests/test_outcome_scorer.py` | Data layer |
| `tests/fixtures.py`, `src/gap_calculator.py`, `src/urgency_ranker.py`, `tests/test_gap_calculator.py`, `tests/test_urgency_ranker.py` | Fixtures, scoring, ranking |
| `src/outbound_generator.py`, `src/human_checkpoint.py`, `tests/test_outbound_generator.py`, `tests/test_human_checkpoint.py`, `data/email_cache.json` | Email generation and human review |
| `src/dashboard_generator.py`, `tests/test_dashboard_generator.py`, `dashboard/echo_dashboard.html` | Static HTML dashboard |
| `src/agent.py`, `tests/test_pipeline.py` | End-to-end integration |

## Build Order

### Task 0 - Shared Fixtures

Owner: Luba

Status: update first to match `SCHEMA.md` v0.2.

Acceptance criteria:

- `tests/fixtures.py` uses only fields from `SCHEMA.md`.
- Fixtures cover high, medium, low, null-data, and no-commitment/silent-gap v2 guard cases.
- Fixtures do not include removed v0.1 fields.
- No test file defines its own hospital fixtures.

### Task 1 - Commitment Ingester Tests

Owner: Jonel

Create `tests/test_commitment_ingester.py`.

Test requirements:

- `get_hospital_commitments()` returns a non-empty list.
- Every hospital has all Tool 1 schema fields.
- `facility_id` is a string CCN sourced through HCAHPS matching.
- `state` is two-letter uppercase.
- `birthing_friendly` is boolean and true for v1 hospitals.
- `commitment_tag` equals the v1 default: `Earned the CMS Birthing-Friendly designation`.
- `commitment_source` equals `CMS Birthing-Friendly Registry`.

Run:

```bash
.venv/bin/python -m pytest tests/test_commitment_ingester.py -v
```

Expected before implementation: import failure or failing tests.

### Task 2 - Commitment Ingester Implementation

Owner: Jonel

Create `src/commitment_ingester.py`.

Data inputs:

- `data/Birthing_Friendly_Hospitals_Geocoded.csv`
- `data/HCAHPS-Hospital-NY.csv`

Acceptance criteria:

- Returns Tool 1 fields exactly as defined in `SCHEMA.md`.
- Filters to CMS Birthing-Friendly hospitals for v1.
- Uses name normalization to match BF registry hospitals to HCAHPS rows and recover `facility_id` (CCN).
- Drops hospitals that still cannot be matched after normalization, with a logged warning.
- Sets v1 default commitment tag/source.
- Missing optional values are `None`, not `0`.

Run:

```bash
.venv/bin/python -m pytest tests/test_commitment_ingester.py -v
```

### Task 3 - Outcome Scorer Tests

Owner: Jonel

Create `tests/test_outcome_scorer.py`.

Test requirements:

- `score_outcomes(hospitals)` does not drop hospitals.
- Adds only Tool 2 v0.2 fields.
- `discharge_info_star` is `None` or int 1-5.
- `overall_star` is `None` or int 1-5.
- `discharge_help_pct` is `None` or float.
- `state_postpartum_visit_rate` and `state_postpartum_visit_year` are present.
- Missing HCAHPS fields are `None`, not `0`.
- Removed v0.1 fields are not added.

Run:

```bash
.venv/bin/python -m pytest tests/test_outcome_scorer.py -v
```

Expected before implementation: import failure or failing tests.

### Task 4 - Outcome Scorer Implementation

Owner: Jonel

Create `src/outcome_scorer.py`.

Data inputs:

- `data/HCAHPS-Hospital-NY.csv`
- `data/core-set-data-dashboard...postpartum-care...csv` or a renamed local equivalent documented in the module

Acceptance criteria:

- Adds `discharge_info_star` from `H_COMP_6_STAR_RATING`.
- Adds `discharge_help_pct` from `H_DISCH_HELP_Y_P`.
- Adds `overall_star` from `H_STAR_RATING`.
- Adds `state_postpartum_visit_rate`.
- Adds `state_postpartum_visit_year`.
- Adds `hcahps_start_date` and `hcahps_end_date`.
- Does not add removed v0.1 fields.

Run:

```bash
.venv/bin/python -m pytest tests/test_outcome_scorer.py -v
```

Signal Luba when Tasks 1-4 pass.

### Task 5 - Gap Calculator Tests

Owner: Luba

Create `tests/test_gap_calculator.py`.

Test requirements:

- `calculate_gap_score(hospital)` returns the same dict with added Tool 3 fields.
- Intermediate `gap_score` is a float from 0 to 75.
- `lead_angle` is one of the three v1 values.
- Lead angle cascade is exact:
- `overall_star` 1 or 2 -> `hcahps_care_transition_gap`.
- `discharge_info_star` 1 or 2 -> `hcahps_discharge_gap`.
- Otherwise -> `state_strength_vs_hospital_lag`.
- `gap_breakdown` contains `commitment_strength`, `outcome_gap`, and `urgency_context`.
- `urgency_context` is `0` after Tool 3.
- High-gap fixture scores above low-gap fixture.
- `data_confidence` is `low` only when both `discharge_info_star` and `overall_star` are `None`.
- Null HCAHPS data does not crash.

Run:

```bash
.venv/bin/python -m pytest tests/test_gap_calculator.py -v
```

Expected before implementation: import failure or failing tests.

### Task 6 - Gap Calculator Implementation

Owner: Luba

Create `src/gap_calculator.py`.

Acceptance criteria:

- Uses only v0.2 fields.
- Does not reference dropped v0.1 fields.
- Uses `hospital.get("field") is not None` before calculations that may receive nulls.
- Sets `data_confidence` exactly as defined in `SCHEMA.md`.
- Produces one of the three valid v1 `lead_angle` values.

Run:

```bash
.venv/bin/python -m pytest tests/test_gap_calculator.py -v
```

### Task 7 - Urgency Ranker Tests

Owner: Luba

Create `tests/test_urgency_ranker.py`.

Test requirements:

- `add_urgency(hospital)` requires Tool 3 fields.
- Final `gap_score` is a float from 0 to 100.
- `urgency_tier` is exactly `high`, `medium`, or `low`.
- `urgency_flag` is exactly one of the three schema strings.
- Adds `medicaid_extended` and `racial_disparity_flag`.
- `gap_breakdown["urgency_context"]` is filled in and is between 0 and 25.
- Missing `gap_score` or `gap_breakdown` raises `KeyError`.

Run:

```bash
.venv/bin/python -m pytest tests/test_urgency_ranker.py -v
```

Expected before implementation: import failure or failing tests.

### Task 8 - Urgency Ranker Implementation

Owner: Luba

Create `src/urgency_ranker.py`.

Data inputs:

- `data/raw_data.csv` (KFF)
- `data/hestat113.pdf` or manually extracted constants from the PDF

Acceptance criteria:

- Adds Medicaid extension and racial disparity context.
- Updates intermediate Tool 3 `gap_score` to final Tool 4 `gap_score`.
- Sets `urgency_tier` and `urgency_flag` exactly per schema.
- Does not add `state_mortality_rate` or `state_mortality_rank` unless schema changes again.
- Does not rank hospitals against each other inside this function.

Run:

```bash
.venv/bin/python -m pytest tests/test_urgency_ranker.py -v
```

Signal Paula when Tasks 5-8 pass.

### Task 9 - Outbound Generator Tests

Owner: Paula

Create `tests/test_outbound_generator.py`.

Test requirements:

- Low urgency hospitals do not get emails.
- Hospitals with `data_confidence="low"` do not get emails and are skipped entirely; no email object is created.
- With a successful mocked OpenRouter call, high urgency/high confidence hospitals get emails with `generation_method="openrouter_api"`.
- With a successful mocked OpenRouter call, medium urgency/high confidence hospitals get emails with `generation_method="openrouter_api"`.
- Email object has all Tool 5 schema fields.
- Each email has `body_moral`, `body_clinical`, and `body_financial`.
- `generation_method` is exactly `openrouter_api` or `cached_fallback`.
- `generation_method="cached_fallback"` triggers only when:
- The OpenRouter API call fails, OR
- `commitment_tag` is `None`.
- A hospital with one null HCAHPS star but the other present is still high-confidence and eligible for OpenRouter email generation. The lead angle cascade uses the available star; if no severe star rule matches, it falls through to `state_strength_vs_hospital_lag`.
- Financial variant uses state-level Medicaid context, not `medicaid_pct`.
- Bodies use the NurtureBridge Health / Postpartum Handoff Navigation seller context.
- Bodies do not invent social proof, customer names, financial impact, clinical recommendations, or outcomes beyond ECHO-provided facts.
- `urgency_tier` is copied from the hospital dict.

Run:

```bash
.venv/bin/python -m pytest tests/test_outbound_generator.py -v
```

Expected before implementation: import failure or failing tests.

### Task 10 - Outbound Generator Implementation

Owner: Paula

Create:

- `src/outbound_generator.py`
- `data/email_cache.json`

Acceptance criteria:

- Requires input hospitals to have `urgency_tier`.
- Uses OpenRouter in v1.
- Sets `generation_method` truthfully.
- Skips low-confidence hospitals entirely.
- Falls back to cached templates only on API failure or missing `commitment_tag`.
- Generates three grounded variants per included hospital using NurtureBridge Health and Postpartum Handoff Navigation context.
- Does not send email.

Run:

```bash
.venv/bin/python -m pytest tests/test_outbound_generator.py -v
```

### Task 11 - Human Checkpoint Tests

Owner: Paula

Create `tests/test_human_checkpoint.py`.

Test requirements:

- `display_checkpoint(hospitals, emails)` returns a summary string.
- Summary includes high and medium counts.
- Summary clearly says nothing was sent.
- Display includes all three email variants.
- Display includes hospital name, state, urgency flag, final gap score, commitment tag, and lead angle.

Run:

```bash
.venv/bin/python -m pytest tests/test_human_checkpoint.py -v
```

Expected before implementation: import failure or failing tests.

### Task 12 - Human Checkpoint Implementation

Owner: Paula

Create `src/human_checkpoint.py`.

Acceptance criteria:

- Presents a readable terminal checkpoint.
- Shows all high/medium email drafts.
- Clearly communicates that ECHO drafts only; a human sends.

Run:

```bash
.venv/bin/python -m pytest tests/test_human_checkpoint.py -v
```

### Task 13 - Dashboard Generator Tests

Owner: Luba

Create `tests/test_dashboard_generator.py`.

v1 dashboard scope:

- Static HTML output generated by Python.
- No web server, frontend framework, auth, CRM integration, or email sending.
- Sits alongside `human_checkpoint.py`; it does not replace the terminal checkpoint.
- Uses the existing dashboard mockup as visual reference, but renders real pipeline/email data.

Test requirements:

- `generate_dashboard(hospitals, emails, output_path)` writes an HTML file.
- Dashboard includes summary counts for high and medium urgency accounts.
- Dashboard includes ranked high/medium hospitals only.
- Low-confidence hospitals are shown with `data unavailable` or excluded from email sections according to Tool 5 output.
- Dashboard displays hospital name, state, urgency tier, urgency flag, final `gap_score`, `lead_angle`, `data_confidence`, and `commitment_tag`.
- Dashboard displays all three email variants when an email object exists: `body_moral`, `body_clinical`, and `body_financial`.
- Dashboard displays `generation_method`.
- Dashboard clearly states that no email has been sent and a human must review/copy/send.
- Output HTML contains no live network calls required for core rendering.

Run:

```bash
.venv/bin/python -m pytest tests/test_dashboard_generator.py -v
```

Expected before implementation: import failure or failing tests.

### Task 14 - Dashboard Generator Implementation

Owner: Luba

Create:

- `src/dashboard_generator.py`
- `dashboard/echo_dashboard.html` generated output

Acceptance criteria:

- Generates a self-contained static HTML dashboard from hospital dicts and email objects.
- Preserves the human-in-the-loop rule: review only, no sending.
- Groups high urgency before medium urgency.
- Uses schema v0.2 fields only.
- Escapes dynamic text before rendering into HTML.
- Can be run from integration after Tool 5/6 data exists.

Run:

```bash
.venv/bin/python -m pytest tests/test_dashboard_generator.py -v
```

### Task 15 - Pipeline Integration Tests

Owner: Team

Create `tests/test_pipeline.py`.

Test requirements:

- Full pipeline runs on `tests/fixtures.py`.
- Dict fields only grow after each tool.
- Tool 3 `gap_score` is <= 75.
- Tool 4 `gap_score` is <= 100.
- Account selector returns the top 10 high/medium, high-confidence hospitals by final score.
- Emails are created only for selected top 10 accounts.
- Null-data hospital is retained through Tool 4 and skipped by Tool 5.

Run:

```bash
.venv/bin/python -m pytest tests/test_pipeline.py -v
```

### Task 16 - Agent Integration

Owner: Team

Refactor `src/agent.py` so it orchestrates the separate modules instead of embedding tool implementations.

Acceptance criteria:

- Runs the tools in the required order.
- Accepts a state argument, with NY as the demo target.
- Produces a ranked top 10 account list.
- Displays the human checkpoint.
- Generates the static dashboard when dashboard dependencies are available.
- Does not send email.
- Automated sending remains out of scope until prompt reliability, claim validation, source grounding, safety checks, approvals, suppressions, throttling, audit logs, and send controls exist.

Run:

```bash
.venv/bin/python src/agent.py NY
```

## Final Done Criteria

```bash
.venv/bin/python -m pytest tests/ -v
.venv/bin/python src/agent.py NY
```

Expected final behavior:

- All tests pass.
- The NY run uses real NY hospitals.
- Top 10 high/medium, high-confidence accounts get three email variants.
- Email generation uses OpenRouter or cached fallback.
- Human checkpoint is displayed.
- Static dashboard is generated.
- Nothing is sent automatically.

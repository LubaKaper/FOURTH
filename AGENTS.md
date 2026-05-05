# AGENTS.md — ECHO Standalone

Instructions for AI coding assistants working in this repo.

## Standalone Context

This is Luba's standalone continuation of ECHO after the original team moved to a different project. Treat this repo as a solo product/codebase. Historical docs may mention Jonel/Paula/team ownership, but current work does not require cross-person approval.

Default owner for all files: Luba.

## Seller/Service Context

ECHO's GTM Engineer works for **NurtureBridge Health**, a fictional postpartum health company used as the concrete v1 seller context.

NurtureBridge sells **Postpartum Handoff Navigation** to hospitals: a discharge-to-postpartum service that gives maternity teams a shared work queue for postpartum follow-up, patient check-ins, escalation routing, and visit-readiness tracking after discharge.

Outbound should become specific to that seller and service. Avoid generic vendor placeholders when the implementation is updated; ground claims in the hospital dict and describe the service only in terms ECHO can support.

Long-term direction is automated sending, but only after prompt reliability, claim validation, source grounding, safety checks, suppressions, approvals, throttling, audit logs, and send controls exist. v1 remains human-reviewed drafts only.

## Read These First

Before touching any file:

1. `prd.md` — what we are building and why.
2. `SCHEMA.md` — exact field names, types, allowed values, source files, and null rules.
3. `PLAN.md` — original build order, test requirements, done criteria.
4. `STANDALONE_CONTEXT.md` — current status and next steps for this standalone repo.
5. `tests/fixtures.py` — shared test hospitals. Import from here; do not define your own.

## Pipeline Order — Hard Constraint

```text
commitment_ingester -> outcome_scorer -> gap_calculator -> urgency_ranker -> account_selector -> outbound_generator -> human_checkpoint -> dashboard_generator
```

One hospital dict travels the full pipeline. Fields are only added. If a function removes or renames a field, it is wrong.

## v0.2 Core Logic

The v1 mismatch compares hospital HCAHPS patient experience against state postpartum visit strength.

Example:

```text
NY achieves 82.4% postpartum visit completion. This Birthing-Friendly hospital scores 1 star on HCAHPS discharge information.
```

## Field Rules — Non-Negotiable

- Field names are exact. `discharge_info_star` not `care_transition_score`. `state_postpartum_visit_rate` not `state_postpartum_care_pct`.
- `state` is always 2-letter uppercase.
- `urgency_tier` is exactly one of: `"high"` / `"medium"` / `"low"`.
- `urgency_flag` is exactly one of: `"🔴 Act this week"` / `"🟡 Monitor"` / `"🟢 Not ready"`.
- `lead_angle` is exactly one of: `"hcahps_discharge_gap"` / `"hcahps_care_transition_gap"` / `"state_strength_vs_hospital_lag"`.
- `generation_method` is exactly one of: `"openrouter_api"` / `"cached_fallback"`.
- `commitment_tag` v1 default is exactly `"Earned the CMS Birthing-Friendly designation"`.
- `gap_score` after `gap_calculator.py` is intermediate (0-75). Only read it after `urgency_tier` is present in the dict.

## Removed v0.1 Fields

Do not use these in v1:

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

## Null Handling

- Missing fields are `None`, never `0`, never imputed.
- Never skip a hospital in Tools 1-4 for missing HCAHPS data. Score what is available and set `data_confidence`.
- `data_confidence = "low"` only when both `discharge_info_star` and `overall_star` are `None`.
- Tool 5 skips low-confidence hospitals for email generation.

## Cached Fallback Trigger

Low-confidence hospitals (both `discharge_info_star` and `overall_star` null) are skipped entirely by Tool 5. No email object is created.

For all other hospitals, `outbound_generator.py` calls OpenRouter and falls back to cached templates only when:

1. OpenRouter API call fails, OR
2. `commitment_tag` is null and no variant can be grounded.

A hospital with only one HCAHPS star null still gets a real OpenRouter email. The lead angle cascade uses the available star; if no severe star rule matches, it falls through to `state_strength_vs_hospital_lag`.

`generation_method = "openrouter_api"` on success, or `"cached_fallback"` on either failure mode.

## File Ownership

This standalone repo is owned by Luba. Historical team ownership from the original class project is no longer a blocker. Still keep changes scoped and note cross-file contract changes in commits.

## v1 Scope — Do Not Build

- No live web scraping.
- No CRM integration.
- No sending email.
- No patient-facing features.
- No silent gap mode.
- No hospital-level severe morbidity, readmissions, maternal quality scores, or Medicaid payer mix.
- No per-hospital curated commitment tags.
- No Anthropic API in v1.

If a feature is not in `PLAN.md`, do not build it.

## TDD Workflow

Tests are written before implementation. For every task:

1. Write the failing test.
2. Run it and confirm it fails.
3. Write minimal implementation.
4. Run again and confirm it passes.
5. Commit.

Never commit an implementation without a passing test. Never skip the failing-test step.

## Running Tests

```bash
.venv/bin/python -m pytest tests/test_gap_calculator.py -v
.venv/bin/python -m pytest tests/ -v
.venv/bin/python src/agent.py NY
.venv/bin/python -m pytest tests/test_dashboard_generator.py -v
```

## Done Criteria

```text
.venv/bin/python -m pytest tests/ -v       -> all green, 0 failures
.venv/bin/python src/agent.py NY           -> real NY hospitals, 3 OpenRouter/cached email variants per top 10 high-confidence accounts, human checkpoint displayed, static dashboard generated
```

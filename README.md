# ECHO - Early Care Handoff Observer

ECHO is a GTM intelligence agent for **NurtureBridge Health**, a fictional postpartum health company selling **Postpartum Handoff Navigation** to hospitals. It finds CMS Birthing-Friendly hospitals whose HCAHPS patient experience lags behind their state's postpartum visit strength, then drafts grounded outreach for a human to review and send.

NurtureBridge's service helps maternity teams manage the discharge-to-postpartum transition with a shared follow-up work queue, patient check-ins, escalation routing, and visit-readiness tracking.

```text
NY achieves 82.4% postpartum visit completion.
This Birthing-Friendly hospital scores 1 star on HCAHPS discharge information.
```

## What It Does

ECHO gives a NurtureBridge GTM Engineer today's top 10 high-confidence accounts and three outreach variants per account.

The human stays in control:

- ECHO ranks accounts.
- ECHO explains the mismatch.
- ECHO drafts outreach.
- The GTM Engineer reviews, edits, copies, and sends.
- ECHO never sends email automatically.

## v1 Scope

v1 is intentionally narrow:

- NY demo territory.
- CMS Birthing-Friendly hospitals.
- Hospital-level HCAHPS patient experience.
- State-level postpartum visit benchmark.
- OpenRouter email generation with cached fallback.
- Terminal human checkpoint.
- Static HTML dashboard for human review.

Hospital-level severe morbidity, readmissions, maternal quality scores, Medicaid payer mix, silent-gap mode, CRM integration, per-hospital curated commitment tags, and Anthropic are v2.

Automated email sending is a long-term direction, not v1. It should wait until prompt reliability, claim validation, source grounding, safety checks, approvals, suppressions, throttling, audit logs, and send controls are designed and tested.

## Pipeline

```text
commitment_ingester
  -> outcome_scorer
  -> gap_calculator
  -> urgency_ranker
  -> account_selector
  -> outbound_generator
  -> human_checkpoint
  -> dashboard_generator
```

One hospital dict travels through the full pipeline. Each tool only adds fields.

## v0.2 Data Fields

Primary v1 fields:

- `discharge_info_star`
- `discharge_help_pct`
- `overall_star`
- `state_postpartum_visit_rate`
- `state_postpartum_visit_year`
- `medicaid_extended`
- `racial_disparity_flag`

Removed v0.1 fields such as `compared_to_national`, `postpartum_visit_pct`, `severe_morbidity_rate`, `readmission_penalty`, and `medicaid_pct` are v2.

## Data Sources

| Source file | v1 use |
|---|---|
| `Birthing_Friendly_Hospitals_Geocoded.csv` | Birthing-Friendly universe, address, ZIP, lat/lon |
| `HCAHPS-Hospital-NY.csv` | CCN, county, discharge information star, discharge help percent, overall star, survey dates |
| `core-set-data-dashboard...postpartum-care...csv` | State postpartum visit rate and reporting year |
| `raw_data.csv` | KFF Medicaid extension context |
| `hestat113.pdf` | Racial disparity context |
| OpenRouter API | Three grounded outreach variants |

## Dashboard

v1 includes a static HTML dashboard generated from hospital dicts and email objects. It is a visual review surface, not a web app:

- No server, auth, CRM integration, or email sending.
- Generated output: `dashboard/echo_dashboard.html`.
- Mockup reference: `docs/mockups/echo-dashboard-mockup.html`.
- The GTM Engineer reviews email variants, then copies/sends from their own tool.

## Standalone Ownership

This is Luba's standalone continuation of ECHO. Historical docs and comments may mention the original class team, but current ownership for all files is Luba.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add `OPENROUTER_API_KEY` to `.env` for live generation. Without it, the outbound generator should use cached fallback templates.

Optional model settings:

```bash
OPENROUTER_MODEL=poolside/laguna-m.1:free
OPENROUTER_FALLBACK_MODELS=
OPENROUTER_USE_FALLBACK_MODELS=false
OPENROUTER_TIMEOUT_SECONDS=5
OPENROUTER_MAX_LIVE_EMAILS=1
OPENROUTER_CONCURRENCY=1
OPENROUTER_MAX_TOKENS=1200
OPENROUTER_RETRIES=1
OPENROUTER_JSON_MODE=false
```

For a full live email generation run, set `OPENROUTER_MAX_LIVE_EMAILS=10`.
Set `OPENROUTER_USE_FALLBACK_MODELS=true` only when you have verified a backup model works for Tool 5.
Increase `OPENROUTER_CONCURRENCY` only if OpenRouter is responding reliably; `1` is the safer free-tier demo default.

## Run

```bash
.venv/bin/python -m pytest tests/ -v
.venv/bin/python src/agent.py NY
```

## Docs

- `prd.md` - product source of truth.
- `SCHEMA.md` - engineering contract.
- `PLAN.md` - owner split, implementation order, and test contract.

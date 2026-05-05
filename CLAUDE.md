# CLAUDE.md — ECHO Standalone

## Project Context

ECHO is now Luba's standalone continuation project. The original class team moved on to a different build, but this repo preserves the working ECHO pipeline and should be treated as a solo product/codebase.

Historical docs may mention Jonel, Paula, or team ownership. Those notes explain origin/history only. Current owner for all code and docs is Luba.

## Product Summary

ECHO is a GTM intelligence agent for a specific postpartum health seller: **NurtureBridge Health**.

The GTM Engineer works for NurtureBridge and sells **Postpartum Handoff Navigation** to hospitals. The service helps maternity teams manage the discharge-to-postpartum transition with a shared follow-up work queue, patient check-ins, escalation routing, and visit-readiness tracking.

ECHO finds CMS Birthing-Friendly hospitals where hospital-level HCAHPS patient experience lags against state postpartum visit strength, ranks the top accounts for that GTM Engineer, drafts outreach variants, and pauses for human review.

The core v1 story:

```text
NY achieves 82.4% postpartum visit completion.
This Birthing-Friendly hospital scores 1 star on HCAHPS discharge information.
ECHO surfaces the account, explains the gap, drafts outreach, and waits for human review.
```

## Read First

1. `AGENTS.md` — current assistant rules for this standalone repo.
2. `STANDALONE_CONTEXT.md` — current state, setup, and next work.
3. `SCHEMA.md` — exact field names and pipeline contracts.
4. `prd.md` — product direction and scope.
5. `tests/fixtures.py` — shared test hospitals.

If docs conflict, `SCHEMA.md` wins for data contracts and `AGENTS.md` wins for current repo workflow.

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

One hospital dict moves through the pipeline. Fields are only added. Removing or renaming a field is a bug.

## Current Working Commands

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env

.venv/bin/python -m pytest tests/ -v
.venv/bin/python src/agent.py NY
```

The generated dashboard is `dashboard/echo_dashboard.html`, but that file is intentionally gitignored because it is generated output.

## Important Contracts

- Hospital name field is `facility_name`, not `name`.
- `score_outcomes()` takes `list[dict]`, not a single hospital dict.
- Missing fields are `None`, never `0`.
- `generation_method` is exactly `openrouter_api` or `cached_fallback`.
- Low-confidence hospitals are skipped by Tool 5.
- ECHO never sends email automatically.
- v1 outbound may use NurtureBridge/service context, but every hospital-specific claim must come from ECHO data.

## Development Rules

- Prefer TDD for behavior changes.
- Run the focused test first, then full tests.
- Keep v1 scoped: no CRM integration, no sending email, no live scraping, no patient-facing features.
- Use real local data files in `data/`; do not invent CMS column names.
- Keep generated artifacts, `.env`, `.venv`, `node_modules`, and `dashboard/echo_dashboard.html` out of git.

## Suggested Next Product Work

1. Update Tool 5 prompts and cached fallback copy to use NurtureBridge Health and Postpartum Handoff Navigation.
2. Add source links beneath claims.
3. Improve dashboard review workflow.
4. Add account actions: approve, suppress, watchlist, copy selected variant.
5. Add persistence for notes and suppressions.
6. Improve prompt reliability and claim validation before any automated sending work.

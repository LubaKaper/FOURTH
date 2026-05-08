# AGENTS.md — Fourth (ECHO-standalone)

Instructions for AI coding assistants working in this repo.

## Ownership

Solo project. Owner: Luba Kaper. No cross-person approval required.

## What This Is

**Fourth** — Account intelligence for maternal health GTM.
Finds CMS Birthing-Friendly hospitals with postpartum outcome gaps, ranks priority accounts, and drafts Babyscripts outbound for GTM review.

**Seller:** Babyscripts GTM Engineer.
**Targets:** CMOs and VP Patient Experience at Birthing-Friendly hospitals with lagging postpartum outcomes.
**Service:** Babyscripts remote postpartum monitoring — BP kit, mobile app, OB-specialized care managers, RPM CPT billing support.

## Read These First

Before touching any file:

1. `ADR.md` — architecture decisions and end-goal. Source of truth for product direction.
2. `SCHEMA.md` — exact field names, types, allowed values, null rules, handoff contracts.
3. `CLAUDE.md` — coding conventions, phase protocol, change protocol, quality checklist.
4. `tests/fixtures.py` — shared test hospitals. Import from here; never define ad hoc hospitals in test files.

If `SCHEMA.md` conflicts with anything else, `SCHEMA.md` wins on field names and contracts.

## Pipeline Order — Hard Constraint

```text
commitment_ingester
→ outcome_scorer
→ gap_calculator
→ urgency_ranker
→ account_selector
→ outbound_generator
→ human_checkpoint
→ dashboard_generator
```

One hospital dict travels the full pipeline. Fields are only added. Removing or renaming a field mid-pipeline is a contract violation.

## Field Rules

- `facility_name` — the only hospital name field. Not `name`, not `hospital_name`.
- `state` — always 2-letter uppercase.
- `gap_score` — intermediate (0–75) after `gap_calculator`; final (0–100) after `urgency_ranker`. Do not read as final until `urgency_tier` is present.
- `urgency_tier` — exactly `"high"` / `"medium"` / `"low"`.
- `urgency_flag` — exactly `"🔴 Act this week"` / `"🟡 Monitor"` / `"🟢 Not ready"`.
- `lead_angle` — exactly one of the five valid values below.
- `data_confidence` — exactly `"high"` / `"low"`.

## Valid `lead_angle` Values (5 total)

```
baby_vs_mother_contrast
smm_rate_gap
hcahps_care_transition_gap
financial_unrealized
state_strength_vs_hospital_lag
```

Priority order is defined in `SCHEMA.md`. Do not change priority without an ADR update.

## Email Contract (Handoff 4)

One email object per hospital. No three-variant structure.

```python
{
  "facility_id":      str,
  "facility_name":    str,
  "recipient_role":   str,       # "CMO" | "VP Patient Experience"
  "subject":          str,
  "email_body":       str,
  "product":          str,       # exactly "Babyscripts"
  "lead_angle":       str,
  "angle_reason":     str,       # deterministic one-liner — no LLM
  "gap_score":        float,
  "urgency_tier":     str,
  "sent_at":          None,
  "status":           str,       # "pending_review" | "ready_to_send"
}
```

## Null Handling

- Missing fields are `None`, never `0`, never imputed.
- Null inputs score `0` for the affected scoring layer and continue the pipeline.
- `data_confidence = "low"` when core outcome fields are missing.
- Low-confidence hospitals are visible during tuning review but skipped by `outbound_generator`.

## Do Not Build

- Live web scraping
- CRM integration
- Sending email from this repo
- Patient-facing features
- Anything not in `SCHEMA.md`

## TDD Workflow

1. Write the failing test.
2. Run it — confirm it fails for the right reason.
3. Write minimal implementation.
4. Run again — confirm it passes.
5. Run full suite: `.venv/bin/python -m pytest tests/ -v`

Never commit implementation without a passing test.

## Running the Pipeline

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest tests/ -v
.venv/bin/python src/agent.py NY
open dashboard/fourth_dashboard.html
```

## Done Criteria

```bash
.venv/bin/python -m pytest tests/ -v    # all green
.venv/bin/python src/agent.py NY        # 101 hospitals scored, 10 emails generated, dashboard written
```

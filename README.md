# Fourth - Account Intelligence for Maternal Health GTM

Fourth is a GTM intelligence agent built for maternal health software companies like Babyscripts. It finds CMS Birthing-Friendly hospitals whose postpartum outcome scores lag behind their public commitments, then drafts personalized outbound for a GTM Engineer to review and send. Babyscripts' GTM Engineer is the end user. Hospitals are the sales targets.

Babyscripts' remote postpartum monitoring service includes BP monitoring kits, a mobile app, OB-specialized care managers, and RPM CPT billing support.

```text
NY achieves 82.4% postpartum visit completion.
This Birthing-Friendly hospital scores 1 star on HCAHPS discharge information.
```

## What It Does

Fourth gives a Babyscripts GTM Engineer today's top 10 high-confidence accounts with one grounded outreach email per account.

The pipeline:

- Ranks accounts by a 3-layer gap score (commitment strength, outcome gap, urgency context).
- Selects the strongest lead angle per hospital from 5 evidence-based options.
- Drafts a Babyscripts outbound email grounded in CMS data with validated claims.
- Auto-approves emails meeting all safety criteria (`gap_score ≥ 70`, `data_confidence = high`, `claim_validation = passed`).
- Delivers via SMTP when `--send` is active; otherwise holds everything at `pending_review` for human review.

## Scope

Current build targets NY. CMS Birthing-Friendly hospitals only.

**Implemented (Phases 1–3):**
- Gap scoring across 3 layers (commitment strength, outcome gap, urgency context)
- 5 lead angles with priority ordering and `angle_reason` explanation
- Claim validation — LLM body checked for fabricated percentages and star ratings
- Auto-approve gate — `gap_score ≥ 70` + `data_confidence = high` + `claim_validation = passed`
- SMTP delivery with `--send` flag, 30-day dedup cooldown, append-only audit log
- Terminal human checkpoint + static HTML dashboard

**Not yet implemented (v2):**
- Hospital-level well-baby visit source (currently using NY state benchmark proxy 91.5%)
- SMM rate data (PC_07a Not Available in current CMS release; roadmap: CDC WONDER v2)
- Silent-gap mode (non-BF hospitals with poor outcomes)
- CRM integration, multi-state, per-hospital curated commitment tags

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

## Data Sources

| Source | Provides |
|---|---|
| `Birthing_Friendly_Hospitals_Geocoded.csv` | Birthing-Friendly universe, address, lat/lon |
| `HCAHPS-Hospital-NY.csv` | Care transition star, discharge info pct (H_DISCH_HELP_Y_P), overall star |
| `Maternal_Health-Hospital.csv` | SMM rate (PC_07a — Not Available in current CMS release), MMSM participation |
| `FY_2026_Hospital_Readmissions_Reduction_Program_Hospital.csv` | Readmission penalty via Excess Readmission Ratio |
| NY state benchmark | Postpartum visit avg 82.4% (CMS Medicaid Adult Core Set 2023); well-baby proxy 91.5% (NY DOH Child Core Set 2023) |
| OpenRouter API | Email body generation with deterministic fallback |

## Dashboard

Static HTML dashboard generated from hospital dicts and email objects — a visual review surface, not a web app.

- Generated output: `dashboard/fourth_dashboard.html`.
- Shows urgency tier, gap score, lead angle, angle reason, and email body per account.
- In review mode, all emails show `pending_review`. In `--send` mode, auto-approved emails are delivered before the dashboard is written.

## Standalone Ownership

This is Luba's standalone continuation of Fourth. Historical docs and comments may mention the original class team, but current ownership for all files is Luba.

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
# Run test suite
.venv/bin/python -m pytest tests/ -v

# Review mode (default) — no email sent
.venv/bin/python src/agent.py NY

# Send mode — requires SMTP credentials in .env
.venv/bin/python src/agent.py NY --send
```

For send mode, add SMTP credentials to `.env`:

```bash
SMTP_HOST=smtp.example.com
SMTP_USER=you@example.com
SMTP_PASSWORD=secret
SMTP_FROM_EMAIL=you@example.com
SMTP_TO_EMAIL=recipient@hospital.com
```

## Docs

- `ADR.md` - architecture decisions and pipeline contracts.
- `SCHEMA.md` - engineering contract (field names, handoffs, null rules).

# CLAUDE.md — Fourth

## 1. Project Overview
- **Name:** Fourth — Account Intelligence for Maternal Health GTM
- **One-liner:** Finds CMS Birthing-Friendly hospitals with postpartum outcome gaps, ranks priority accounts, and drafts Babyscripts outbound for GTM review.
- **Stack:** Python 3, pytest, static HTML dashboard, OpenRouter API, CMS/public CSV data.
- **Deployment:** Local CLI/static dashboard. Production send path built — requires SMTP env vars. Use `--send` flag to activate.
- **Repo:** ECHO-standalone.
- **Branch strategy:** Feature branches only. Never merge to main until complete.
- **Branch naming:** `phase-N/short-description` when working in phases.

## 2. Confidence Rule
**Do not write or change any code until you reach 95% confidence in what needs to be built.**
- Ask follow-up questions until you hit that threshold.
- State your confidence level and what is unclear before proceeding.
- If a requirement is ambiguous, stop and ask. Never guess.
- Never mock data, fabricate CMS columns, or fabricate endpoints. If you don't know, ask or inspect the source file first.

## 3. File Index

Claude reads ONLY the files it needs. Update this index as files are added.
```text
src/
├── agent.py                 — Pipeline orchestrator (--send flag for production mode)
├── commitment_ingester.py   — Loads Birthing-Friendly hospitals and matches CCNs
├── outcome_scorer.py        — Adds outcome/context fields from CMS/public CSVs
├── gap_calculator.py        — Calculates ADR Gap Score layers 1-2
├── urgency_ranker.py        — Adds urgency context and final tier
├── account_selector.py      — Selects ranked accounts for outbound
├── outbound_generator.py    — Builds Babyscripts email objects with claim validation
├── approvals.py             — Auto-approve gate (gap>=70, high confidence, passed validation)
├── send_gate.py             — Final enforcement before mailer; raises on contract violations
├── mailer.py                — SMTP delivery via smtplib; dry_run=True safe for review mode
├── audit_logger.py          — Append-only send_log.csv; body_hash for integrity
├── dedup.py                 — 30-day cooldown gate using audit log
├── human_checkpoint.py      — Prints review checkpoint
├── dashboard_generator.py   — Writes static review dashboard
├── constants.py             — Shared constants and benchmarks
└── name_matching.py         — Hospital name normalization/matching helpers
```

**Tests:**
```text
tests/
├── fixtures.py
├── test_commitment_ingester.py
├── test_outcome_scorer.py
├── test_gap_calculator.py
├── test_urgency_ranker.py
├── test_account_selector.py
├── test_outbound_generator.py
├── test_approvals.py
├── test_send_gate.py
├── test_mailer.py
├── test_audit_logger.py
├── test_dedup.py
├── test_send_mode.py
├── test_human_checkpoint.py
├── test_dashboard_generator.py
└── test_pipeline.py         — Handoff contracts + Phase 3 integration tests
```

**Docs/data:**
```text
ADR.md                       — Current source of truth for product/pipeline direction
SCHEMA.md                    — Exact field names, handoffs, null rules
AGENTS.md                    — Assistant workflow rules for this repo
README.md                    — Public project overview
PRODUCT_VISION.md            — Product thesis and GTM direction
data/                        — Committed CMS/public source files
dashboard/fourth_dashboard.html — Generated local dashboard output
```

> Update this map when you add a new file or directory.

## 4. Build & Dev Commands
```bash
python3 -m venv .venv                         # Create local virtualenv
.venv/bin/pip install -r requirements.txt     # Install dependencies
.venv/bin/python -m pytest tests/ -v          # Full test suite
.venv/bin/python -m pytest tests/test_name.py -v # Focused test file
.venv/bin/python src/agent.py NY              # Run full NY pipeline (review mode)
.venv/bin/python src/agent.py NY --send       # Production send mode (requires SMTP env vars)
open dashboard/fourth_dashboard.html          # Open generated dashboard locally
```

**SMTP env vars required for `--send`:**
```bash
SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM_EMAIL, SMTP_TO_EMAIL
```

## 5. Coding Conventions

### Architecture
- Pipeline order is fixed: `commitment_ingester -> outcome_scorer -> gap_calculator -> urgency_ranker -> account_selector -> outbound_generator -> human_checkpoint -> dashboard_generator`.
- One hospital dict travels the full pipeline. Fields are only added. Do not remove or rename existing fields in downstream tools.
- Keep business rules in the relevant pipeline tool, not in the dashboard or checkpoint presentation layer.
- Centralize shared constants in `src/constants.py`.

### Error Handling
- Missing source data is `None`, never `0`, never imputed.
- Null fields score zero for the affected layer/subcomponent, set/retain `data_confidence`, and continue the pipeline.
- Do not crash on null Handoff 1 fields.
- Low-confidence hospitals are not eligible for email generation.
- Every OpenRouter call must have deterministic fallback copy.

### Python
- Prefer clear typed helper functions where they reduce ambiguity.
- Keep functions pure when the surrounding module already follows that pattern.
- Do not mutate input lists or upstream hospital dicts unless the local tool contract explicitly does so.
- Use `csv.DictReader` or structured parsers for CSVs. Do not parse CSVs with ad hoc string splitting.

### Data & Claims
- Do not invent CMS column names. Open the CSV and inspect headers before mapping.
- Do not invent hospital-specific claims.
- OpenRouter may generate `email_body` only; deterministic code owns all other ADR contract fields.
- `generation_method` is log/internal trace only, not part of the ADR email object and not part of `SCHEMA.md`.
- Fourth sends email only via `--send` flag with valid SMTP credentials. Review mode never calls the mailer.

### Git
- Commit messages: `type(scope): description` (e.g., `fix(outbound): restore openrouter generation`).
- Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`.
- One logical change per commit.
- No commit happens without Luba approving the summary first.

## 6. Phase Protocol

### Structure
Each project is built in numbered phases. A phase is not complete until:
1. All acceptance criteria for that phase are met
2. Focused tests pass
3. `.venv/bin/python -m pytest tests/ -v` passes
4. Luba confirms the phase is done

**Never start Phase N+1 until Phase N is confirmed complete.**

### Phases for This Project
| Phase | Goal | Status |
|-------|------|--------|
| 1 | ADR/schema migration for Fourth and Babyscripts GTM context | ✅ Complete |
| 2 | Prompt reliability, claim validation, source grounding, safety checks | ✅ Complete |
| 3 | Send controls and automation readiness | ✅ Complete |

> Add/remove phases as the project evolves.

## 7. Read Before Write

Before editing any file:
1. Read its current contents first.
2. After any successful edit, the previous view is stale. Re-read before making another edit to the same file.
3. Never assume file state from memory or earlier context.

## 8. Change Protocol

When a direction change or update is needed:
1. Luba describes the change.
2. You confirm your understanding and list affected files.
3. Luba approves the direction.
4. You update all affected files.
5. You provide a summary of every change made.
6. You provide a detailed commit message at the end of the summary.

**No commit happens without a summary first.**

## 9. Summary & Commit Format

After every meaningful update, provide:

```text
### Summary
- What changed and why
- Files added/modified/deleted
- Any open questions or follow-ups

### Commit
git add [files]
git commit -m "type(scope): concise description

- Detail 1
- Detail 2
- Detail 3"
```

## 10. Compaction Protocol (Token Optimization)

Context windows are finite. Optimize aggressively:

- **After 4 compactions:** Write a session summary capturing: current phase, what was completed, what is in progress, any blockers or decisions made, and the next step. Then alert Luba to `/clear`.
- **Where to store it:** Luba will paste the session summary into the Session Log section of `claude.local.md`. On the next session, read that log first to pick up context.
- **Session summary format:**
  ```text
  ## Session Summary — [Date]
  **Phase:** N
  **Completed:** [list]
  **In progress:** [list]
  **Decisions:** [list]
  **Blockers:** [list]
  **Next step:** [specific next action]
  ```
- **Between tasks:** Use `/clear` to drop stale context.
- **Keep responses tight:** No preamble, no restating the question, no filler paragraphs.
- **File index exists so you don't read everything.** Only read files relevant to the current task.

## 11. Quality Checklist (Pre-Merge)

Before any branch merges to main:
- [ ] Focused tests pass for changed behavior
- [ ] `.venv/bin/python -m pytest tests/ -v` passes
- [ ] `.venv/bin/python src/agent.py NY` runs when pipeline behavior changed
- [ ] Dashboard writes to `dashboard/fourth_dashboard.html` when dashboard behavior changed
- [ ] No invented CMS columns, source names, or hospital-specific claims
- [ ] Email output remains `pending_review`; no automatic sending path
- [ ] README/SCHEMA/ADR updated if public behavior or contracts changed

## 12. Rules (Enforcement Layer)

These are non-negotiable. If any rule conflicts with a request, flag it.

1. Never mock data, guess CMS columns, or fabricate endpoints.
2. Never merge to main until a branch is complete and confirmed.
3. Never skip null handling for Handoff 1 fields.
4. Never send email from this repo.
5. Always preserve pipeline order and add-only hospital dict handoffs.
6. Always keep deterministic control of ADR contract fields outside the LLM.
7. Always ask before making changes you are not 95% confident about.
8. Always provide a summary and commit message after updates.
9. Always read a file before editing it.
10. Prefer targeted fixes over full rebuilds.
11. No commit happens without Luba approving it first.

# CLAUDE.md — ECHO

## 1. Project Overview

- **Name:** ECHO
- **One-liner:** Sales intelligence agent that surfaces CMS Birthing-Friendly hospitals whose HCAHPS patient experience lags their state's Medicaid postpartum strength, with three drafted outreach variants per account.
- **Stack:** Python 3.12, pandas, pytest, requests, python-dotenv, OpenRouter API
- **Team:** Jonel (Tools 1+2 — data layer), Luba (Tools 3+4 — scoring), Paula (Tools 5+6 — emails + checkpoint)
- **My ownership:** `src/commitment_ingester.py`, `src/outcome_scorer.py`, and matching tests
- **Branch strategy:** Feature branches only. Never merge to main until a tool is complete and tests pass.
- **Branch naming:** `jonel/tool1`, `jonel/tool2`. One branch per tool, not per task.

## 2. Source of Truth

Read in this order before any edit. If any of these conflict, SCHEMA.md wins.

1. `SCHEMA.md` — exact field names, types, allowed values, null rules, file dependencies
2. `prd.md` — product direction and scope
3. `PLAN.md` — build order, ownership, test requirements, done criteria
4. `tests/fixtures.py` — shared test hospitals (Luba owns; do not redefine)

Do not implement any field or feature not in SCHEMA.md.

## 3. Confidence Rule

Do not write or change any code until you reach 95% confidence in what needs to be built.

- Ask follow-up questions until you hit that threshold.
- State confidence level and what is unclear before proceeding.
- If a requirement is ambiguous, stop and ask. Never guess.
- Never mock data, never fabricate column names, never invent CMS field names. If you don't know what a CSV column is named, open the CSV and look.

## 4. Pipeline Order — Hard Constraint

```
commitment_ingester → outcome_scorer → gap_calculator → urgency_ranker → outbound_generator → human_checkpoint
```

One hospital dict travels the full pipeline. Each tool only adds fields. Removing or renaming a field is a bug.

I am responsible for the first two tools. Luba cannot start scoring until my output ships and her fixtures match what I produce.

## 5. File Index

```
echo/
├── data/                                 — CSVs and PDFs (not all gitignored, see .gitignore)
│   ├── Birthing_Friendly_Hospitals_Geocoded.csv
│   ├── HCAHPS-Hospital-NY.csv
│   ├── core-set-ppc-ad-ny.csv            — renamed from the ugly CMS filename
│   ├── kff_postpartum_coverage.csv       — renamed from raw_data.csv
│   ├── nnpqc_funding.csv                 — renamed from data-table.csv
│   └── hestat113.pdf                     — citation-only, not ingested
├── src/
│   ├── commitment_ingester.py            — Tool 1 (mine)
│   ├── outcome_scorer.py                 — Tool 2 (mine)
│   ├── gap_calculator.py                 — Tool 3 (Luba)
│   ├── urgency_ranker.py                 — Tool 4 (Luba)
│   ├── outbound_generator.py             — Tool 5 (Paula)
│   ├── human_checkpoint.py               — Tool 6 (Paula)
│   ├── agent.py                          — orchestration (team)
│   ├── name_matching.py                  — name normalization for BF→HCAHPS join
│   └── constants.py                      — state benchmarks, role mappings, file paths
├── tests/
│   ├── fixtures.py                       — Luba owns, everyone imports
│   ├── test_commitment_ingester.py       — mine
│   ├── test_outcome_scorer.py            — mine
│   ├── test_gap_calculator.py            — Luba
│   ├── test_urgency_ranker.py            — Luba
│   ├── test_outbound_generator.py        — Paula
│   ├── test_human_checkpoint.py          — Paula
│   └── test_pipeline.py                  — team
├── .env                                  — OpenRouter API key (gitignored)
├── .env.example                          — template, committed
├── .gitignore
├── CLAUDE.md
├── claude.local.md                       — gitignored
├── SCHEMA.md
├── prd.md
├── PLAN.md
├── requirements.txt
└── README.md
```

Update this map when a file is added.

## 6. Build & Dev Commands

```bash
# Setup (first time only)
python -m venv .venv
.venv\Scripts\activate                      # Windows PowerShell
pip install -r requirements.txt

# Run tests for one tool
.venv\Scripts\python -m pytest tests/test_commitment_ingester.py -v

# Run full test suite
.venv\Scripts\python -m pytest tests/ -v

# Run the full agent against NY
.venv\Scripts\python src/agent.py NY
```

PowerShell paths use backslashes. If switching to WSL or Mac, adjust.

## 7. Coding Conventions

### Architecture
- **Separation of concerns.** No business logic in tool entry functions if it can live in a helper. Each tool's public function is thin; private helpers do the work.
- **No magic strings or numbers.** State benchmarks, role labels, file paths, threshold values all live in `src/constants.py`.
- **No dict mutation across tool boundaries.** Each tool returns the same dict with added fields. Never delete or rename a field that came from upstream.
- **Pure functions where possible.** A tool function takes a dict, returns a dict. No global state, no side effects beyond logging.

### Error Handling
- Every CSV load gets a try/except with a clear message about which file failed and why.
- Missing fields are `None`, never `0`, never imputed. Never substitute a default value to avoid a None check.
- Use `hospital.get("field") is not None` before any calculation that could receive None.
- No silent failures. Every except block logs a meaningful message.

### Python Style
- Type hints on every function signature. `list[dict[str, Any]]` over `list`.
- Docstrings on every public function. State what it does, what it reads, what it returns.
- No `from x import *`. Explicit imports only.
- f-strings over `.format()` or `%`.

### Git
- Commit message format: `type(tool): description` e.g. `feat(commitment_ingester): add name normalization for BF→HCAHPS join`
- Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`
- One logical change per commit.
- No "WIP" commits on `main`.

## 8. Tool Build Protocol

I build one tool at a time on its own branch. A tool is not complete until:

1. All test requirements in PLAN.md for that tool are met
2. All tests for that tool pass
3. The full test suite still passes (no regressions in shared code)
4. I confirm the tool is done before opening the next branch

| Tool | Branch | Status |
|------|--------|--------|
| Tool 1 — commitment_ingester | `jonel/tool1` | [x] |
| Tool 2 — outcome_scorer | `jonel/tool2` | [ ] |

When Tool 2 is done I signal Luba so she can start Tool 3.

## 9. Read Before Write

Before editing any file:
1. Read its current contents first.
2. After any successful edit, the previous view is stale. Re-read before making another edit to the same file.
3. Never assume file state from memory or earlier context.

This applies to CSVs too. Before writing a column name in code, open the CSV and confirm the exact spelling. CMS column names tend to be longer and uglier than what feels natural.

## 10. Change Protocol

When a direction change or update is needed:
1. I describe the change.
2. You confirm understanding and list affected files.
3. I approve the direction.
4. You update all affected files (code, this file's tool table, any docs).
5. You provide a summary of every change.
6. You provide a commit message at the end.

No commit happens without a summary first.

If a change affects SCHEMA.md, stop. Schema changes go through the team, not solo.

## 11. Summary & Commit Format

After every meaningful update:

```
### Summary
- What changed and why
- Files added/modified/deleted
- Any open questions or follow-ups

### Commit
git add [files]
git commit -m "type(tool): concise description

- Detail 1
- Detail 2"
```

## 12. Compaction Protocol

Context windows are finite.

- After about 4 compactions, write a session summary into `claude.local.md` and alert me to `/clear`.
- Session summary format lives in claude.local.md.
- Use `/clear` between tasks or when switching tools.
- Keep responses tight. No preamble, no restating the question.
- The file index exists so you don't read everything. Only read files relevant to the current task.

## 13. Quality Checklist (Pre-Branch-Merge)

Before any tool branch merges to `main`:

- [ ] All tests for the tool pass
- [ ] Full test suite passes (no regressions)
- [ ] No `print()` left for debugging (use logging if you need it)
- [ ] No hardcoded values (everything routes through `constants.py`)
- [ ] No silent except blocks
- [ ] Type hints on every function signature
- [ ] Docstrings on every public function
- [ ] Field names match SCHEMA.md exactly (`discharge_info_star` not `discharge_star`, etc.)
- [ ] No removed v0.1 fields appear anywhere

## 14. Rules — Non-Negotiable

1. Never mock data or guess at CMS column names. Open the CSV.
2. Never merge to `main` until a tool branch is complete and confirmed.
3. Never skip error handling, even on "simple" functions.
4. Never use a removed v0.1 field. The list lives in PLAN.md.
5. Never edit Luba's or Paula's files without flagging the reason.
6. Always separate concerns: thin tool entry, helpers do the work.
7. Always centralize constants in `src/constants.py`.
8. Always ask before making changes you are not 95% confident about.
9. Always read a file before editing it.
10. Prefer targeted fixes over full rebuilds.
11. Schema changes require team agreement. Do not edit SCHEMA.md solo.

## 15. Removed v0.1 Fields — Do Not Use

These fields appeared in v0.1 of the schema and are gone in v0.2. Do not reference them anywhere in code or tests:

- `hcahps_discharge_score`
- `hcahps_discharge_national_avg`
- `hcahps_care_transition_score`
- `state_postpartum_care_pct`
- `state_avg_postpartum_pct`
- `compared_to_national`
- `severe_morbidity_rate`
- `postpartum_visit_pct`
- `well_baby_visit_pct`
- `maternal_quality_score`
- `readmission_penalty`
- `excess_readmission_ratio`
- `medicaid_pct`
- `care_transition_score`
- `has_commitment`
- `hospital_type`
- `hospital_ownership`
- `state_mortality_rate`
- `state_mortality_rank`

## 16. Lead Angles — Exact Strings Only

Three valid `lead_angle` values. Anything else is a bug:

- `hcahps_discharge_gap`
- `hcahps_care_transition_gap`
- `state_strength_vs_hospital_lag`

## 17. Cached Fallback Trigger (Tool 5 — Paula)

Not my tool, but the rule affects schema contracts I produce, so it's documented here.

Low-confidence hospitals (both `discharge_info_star` and `overall_star` null) are skipped entirely by Tool 5. No email object is created.

For all other hospitals, `outbound_generator.py` calls OpenRouter and falls back to cached templates only when:

1. OpenRouter API call fails, OR
2. `commitment_tag` is null

A hospital with only one HCAHPS star null still gets a real OpenRouter email; the `lead_angle` cascade falls through to `state_strength_vs_hospital_lag`.

`generation_method = "openrouter_api"` on success, `"cached_fallback"` on either failure mode.

In v1 every hospital has a non-null `commitment_tag` (the BF default), so trigger #2 is essentially dead code in v1. It exists for v2 when curated tags are introduced and some hospitals may not have one.

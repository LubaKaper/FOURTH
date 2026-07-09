# Fourth — Portfolio & Product Readiness Design

**Date:** 2026-07-09
**Owner:** Luba Kaper
**Status:** Approved direction; pending spec review

## Goal

Make Fourth (a) a portfolio piece that survives technical scrutiny and (b) a deployed, interactive demo of the product — with every data claim honest and defensible. Deliverables: a hardened public repo with green CI, a Streamlit app on Streamlit Community Cloud serving precomputed real-data results, and a README that sells the work with visuals and a live demo link.

## Current State (verified 2026-07-09)

- Repo: `github.com/LubaKaper/FOURTH`. Local `main` is 11 commits ahead of origin — all of Phase 3 (mailer, send gate, dedup, audit log, ~1,800 lines) is unpushed.
- Test suite: 196 tests, all pass. Two problems: (1) tests exercising `generate_outbound_email` call live OpenRouter/Anthropic when `.env` keys are present — slow, flaky, costs money; (2) even offline the suite takes ~2:19, dominated by re-parsing multi-MB CMS CSVs.
- No CI, no README visuals, generated dashboard is gitignored so the repo shows no output.
- `requirements.txt` unpinned; `strands-agents` and `openai` are never imported (dead). `pandas` is used only by `scripts/filter_hcahps_to_ny.py` (keep).
- Data integrity issues (see Workstream 1): a mislabeled HCAHPS proxy drives false claims in email copy; three urgency signals are hardcoded constants; `smm_rate` is always None in the current CMS release.

## Workstream 1 — Data Integrity Pass (blocks everything public)

The product's credibility rests on "grounded claims." Today the grounding has three cracks. This workstream ships first.

### 1.1 Rename the mislabeled discharge measure

`postpartum_visit_pct` actually holds HCAHPS `H_DISCH_HELP_Y_P` — the % of patients who reported receiving information about recovery at discharge. It is not a postpartum visit completion rate, but email copy claims it is ("postpartum maternal completion at {name} sits at X%").

- Rename `postpartum_visit_pct` → `discharge_info_pct` across `src/`, `tests/`, `SCHEMA.md`, `ADR.md`, `README.md` (~12 files, ~28 occurrences). This is a schema change; Luba is sole owner and approves it via this spec.
- `state_postpartum_avg` (82.4%, a true Medicaid Core Set postpartum visit benchmark) keeps its name — it is what it says.
- Rewrite all copy that cites the measure — template emails in `outbound_generator._email_body`, `_subject`, `_angle_reason`, the OpenRouter prompt facts, dashboard, human checkpoint — to claim what the data shows. Honest framing: "only X% of patients at {name} reported understanding their recovery care at discharge."

### 1.2 Make cross-measure comparisons honest

Two lead angles currently compare unlike measures as if they were the same thing:

- `baby_vs_mother_contrast`: compares state well-baby benchmark (91.5%) against the hospital discharge-info proxy. Keep the angle (it is the product's hook) but reword copy to a true statement: "NY's well-baby follow-up averages 91.5% statewide, yet only Y% of postpartum patients at {name} reported understanding their recovery care at discharge."
- `state_strength_vs_hospital_lag`: currently says "postpartum follow-up Xpt below NY average," subtracting a discharge-info % from a visit-completion benchmark. Reword to present the two facts side by side without computing a fake point-gap: NY achieves 82.4% postpartum visit completion (state strength) while the hospital's discharge-readiness signal lags (hospital measure). Numeric subtraction across the two measures is removed from subjects, bodies, and `angle_reason`.

Gap scoring may still use the proxy internally (scores are relative rankings, not outbound claims), but SCHEMA.md documents the proxy explicitly.

### 1.3 Label state-level context as state-level

`state_mortality_rank="bottom_quartile"`, `racial_disparity_flag=True`, `medicaid_extended=True` are hardcoded identically for every hospital in `outcome_scorer` / `urgency_ranker`. They are legitimate NY-state facts, not per-hospital signals — every hospital gets the same urgency points from them.

- Move the values to `src/constants.py` as named NY state context with source citations.
- SCHEMA.md documents them as state-level context fields (same pattern as `well_baby_visit_estimated`).
- The app's methodology page (Workstream 3) shows a provenance table: hospital-level measure / state-level context / not yet available.

### 1.4 Acknowledge the dead SMM angle

`smm_rate` (PC_07a) is "Not Available" in the current CMS release, so `smm_rate_gap` can never fire. Verify with a test that the angle is unreachable with current data; document it as roadmap (CDC WONDER v2) in README and methodology page. No code removal — the angle activates when data ships.

### 1.5 Claim-validation extension

- Update `_validate_llm_body` grounding lists for renamed fields.
- Add a copy-honesty test: no template or prompt may pair the discharge measure with the phrases "postpartum visit," "visit completion," or "postpartum follow-up rate."

## Workstream 2 — Repo Hardening

### 2.1 Push `main`

Push the 11 local commits to origin so Phase 3 is publicly visible. Data-integrity fixes land as new commits on top. (Per repo rules: Luba approves the push.)

### 2.2 Offline, deterministic tests

- New `tests/conftest.py` with an autouse fixture that monkeypatches `outbound_generator._call_openrouter` and `_call_anthropic` to raise `RuntimeError("network disabled in tests")`, forcing the deterministic template path regardless of `.env` contents. Tests that specifically exercise LLM-path logic override the fixture with explicit mocks.
- A guard test patches `requests.post` to assert it is never reached from the suite.

### 2.3 Test speed

Cache the three CSV index builders in `outcome_scorer` (e.g., `functools.lru_cache` on `_build_hcahps_measure_index` etc. keyed on no args; file contents are static per run) and reuse fixture-level pipeline objects where tests rebuild them repeatedly. Target: full suite < 30 s offline. Cache must be resettable for tests that simulate missing files.

### 2.4 Dependencies

- Remove `strands-agents`, `openai` from `requirements.txt`; keep `pandas` (used by `scripts/`).
- Pin all versions (`==`).
- `streamlit` added (app dependency; see 3.3).

### 2.5 CI

`.github/workflows/ci.yml`: on push + PR → checkout, Python 3.12, `pip install -r requirements.txt`, `pytest tests/ -q`. CI badge in README. The conftest network block makes this safe (no secrets in CI).

### 2.6 Identity cleanup

Product name is **Fourth** everywhere. One README line notes it evolved from a team class project (ECHO). No other historical rewrites.

## Workstream 3 — Streamlit App

### 3.1 Demo data export

- New `scripts/export_demo_results.py` (or `--export <path>` flag on `agent.py`): after a full local pipeline run (live LLM keys available locally), write `data/demo_results.json`:

```json
{
  "generated_at": "<ISO timestamp>",
  "state": "NY",
  "accounts": [ { ...selected hospital fields..., "email": { ...email object... } } ]
}
```

- Real CMS data, real pipeline output, real LLM-drafted emails — generated once, committed. **No mock data.** Exporter fails loudly (nonzero exit) if the pipeline yields zero accounts or zero emails.

### 3.2 The app

`app.py` at repo root (Streamlit Cloud convention). Reads `data/demo_results.json` only — the deployed app imports no pipeline code, needs no API keys, and cannot send anything. Views:

1. **Ranked accounts** — table of top accounts: gap score, urgency tier, lead angle, data confidence; sort/filter.
2. **Account detail** — gap breakdown, urgency breakdown, angle reason, signal values with provenance labels.
3. **Drafted email** — subject, body, recipient role, claim-validation status, generation method.
4. **Methodology** — pipeline diagram (8 tools), the 3-layer gap score, how claim validation rejects LLM fabrication (with a real rejected example), and the signal-provenance table (hospital-level vs state-level vs not-yet-available). Data honesty presented as a feature.

Missing/invalid `demo_results.json` → friendly message with the command to generate it, not a stack trace.

### 3.3 Deploy

Streamlit Community Cloud (free), connected to the GitHub repo, `app.py` entrypoint. Demo URL added to README and repo About field.

## Workstream 4 — Portfolio Polish

- README rewrite: one-line pitch → live demo link → hero screenshot → architecture diagram → "how claim validation works" with a real fabrication-rejection example → data provenance section (honest about proxies) → roadmap (SMM data, multi-state, curated commitment tags) → setup/run instructions.
- Screenshots committed under `docs/images/` so they render on GitHub.
- Repo About: description + topics (`healthcare`, `sales-intelligence`, `llm`, `python`, `streamlit`).

## Testing Strategy

- All 196 existing tests keep passing (updated for renames/copy changes).
- New: conftest network-block guard test; CSV-cache behavior test; exporter contract test (exported email objects match the send-contract keys); copy-honesty test (1.5); SMM-angle-unreachable test (1.4).
- App gets a light smoke test (JSON loads, required keys present); full Streamlit UI testing is out of scope.

## Sequencing

1. WS2.1 push current `main` (immediate visibility)
2. WS1 data integrity (blocks public demo)
3. WS2.2–2.6 hardening + CI
4. WS3 exporter + app + deploy
5. WS4 README + screenshots

Each chunk lands as a reviewed commit with summary + commit message per repo rules (no commit without Luba's approval).

## Acceptance Criteria

- [ ] `origin/main` matches local `main`; CI green on GitHub
- [ ] `pytest tests/` completes offline in < 30 s with zero network calls, keys present or not
- [ ] No email, subject, prompt, dashboard, or doc claims "postpartum visit completion" from the discharge-info measure
- [ ] No fabricated point-gaps between unlike measures in any outbound copy
- [ ] Deployed Streamlit URL serves precomputed real-data results with all four views
- [ ] README: demo link, screenshots, CI badge, architecture diagram, provenance section

## Out of Scope (v-next)

Multi-state expansion, CRM integration, auth/user accounts, live LLM generation in the public demo, real send campaigns, hospital-level well-baby or postpartum visit data sourcing, curated commitment-tag database (the "moat" work).

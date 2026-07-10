# Fourth — Portfolio & Product Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Fourth as a hardened public repo (green CI, honest data claims, offline tests) with a deployed Streamlit demo app serving precomputed real-pipeline results.

**Architecture:** The existing 8-tool pipeline is untouched structurally. Work lands in four waves: (1) test infrastructure so every later suite run is fast, free, and offline; (2) data-integrity rename + honest copy; (3) a JSON exporter + read-only Streamlit app; (4) CI, README, deploy. One repo, one branch of commits on `main` (solo owner; Luba approved this plan, which constitutes approval for the commits listed in each task).

**Tech Stack:** Python 3.12, pytest, csv/stdlib, Streamlit (new), GitHub Actions (new). Repo: `/Users/lubakaper/Desktop/L3Projects/ECHO-standalone` (GitHub: `LubaKaper/FOURTH`).

**Spec:** `docs/superpowers/specs/2026-07-09-portfolio-product-readiness-design.md`

**Conventions for every task:** run commands from the repo root `/Users/lubakaper/Desktop/L3Projects/ECHO-standalone` (shell cwd may reset between sessions — always `cd` first). Test command: `.venv/bin/python -m pytest`. Read any file before editing it.

---

### Task 1: Push current `main` to origin

Local `main` is 11 commits ahead; Phase 3 is invisible on GitHub until this lands.

**Files:** none (git only)

- [ ] **Step 1: Verify clean tree and push**

```bash
cd /Users/lubakaper/Desktop/L3Projects/ECHO-standalone
git status --short        # expect: empty
git push origin main
```

- [ ] **Step 2: Verify**

```bash
git fetch origin && git status
```
Expected: "Your branch is up to date with 'origin/main'."

---

### Task 2: Offline test guard (network block)

Tests currently reach live OpenRouter/Anthropic when `.env` has keys. An autouse fixture kills that path for every test; tests that exercise LLM logic re-patch explicitly (they already do, e.g. `tests/test_outbound_generator.py:308`).

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/test_network_block.py`

- [ ] **Step 1: Write the guard test (failing)**

```python
# tests/test_network_block.py
"""The test suite must never reach a live LLM API, even with real .env keys."""

import copy

import src.outbound_generator as og
from src.gap_calculator import calculate_gap_score
from src.urgency_ranker import add_urgency
from tests.fixtures import HIGH_GAP


def _ready() -> dict:
    return add_urgency(calculate_gap_score(copy.deepcopy(HIGH_GAP)))


def test_llm_calls_fall_back_without_touching_network(monkeypatch):
    # Simulate a configured machine: key present, requests importable.
    monkeypatch.setattr(og, "_OPENROUTER_KEY", "fake-key-must-never-be-sent")
    monkeypatch.setattr(og, "_ANTHROPIC_KEY", "fake-key-must-never-be-sent")
    if og._REQUESTS_AVAILABLE:
        def _explode(*args, **kwargs):
            raise AssertionError("requests.post reached from a test")
        monkeypatch.setattr(og._requests, "post", _explode)

    body, method, reason = og._generate_email_body(_ready())

    assert method == "cached_fallback"
    assert "network disabled in tests" in reason
    assert body.startswith("Hi,")
```

- [ ] **Step 2: Run it — verify it fails**

```bash
.venv/bin/python -m pytest tests/test_network_block.py -v
```
Expected: FAIL — without the conftest fixture, `_call_openrouter` runs and hits the exploding `requests.post` (AssertionError) or returns a non-fallback method.

- [ ] **Step 3: Write `tests/conftest.py`**

```python
# tests/conftest.py
"""
Global fixtures for the Fourth test suite.

block_llm_network (autouse): stubs both LLM entry points so no test can
reach OpenRouter or Anthropic, regardless of what is in .env. Tests that
exercise LLM-path logic override by patching the same names inside the
test (an inner unittest.mock.patch wins over this fixture).

The pipeline modules are importable under two names — "src.X" (tests)
and bare "X" (agent.py's sys.path hack). Both module objects are patched
when present so no path is left live.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import outbound_generator as _outbound_flat  # noqa: E402
import src.outbound_generator as _outbound_pkg  # noqa: E402


@pytest.fixture(autouse=True)
def block_llm_network(monkeypatch):
    def _blocked(*_args, **_kwargs):
        raise RuntimeError("network disabled in tests")

    for module in (_outbound_pkg, _outbound_flat):
        monkeypatch.setattr(module, "_call_openrouter", _blocked)
        monkeypatch.setattr(module, "_call_anthropic", _blocked)
```

- [ ] **Step 4: Run the guard test — verify it passes**

```bash
.venv/bin/python -m pytest tests/test_network_block.py -v
```
Expected: PASS

- [ ] **Step 5: Run the full suite — verify no regressions and no live calls**

```bash
time .venv/bin/python -m pytest tests/ -q
```
Expected: 197 passed. Runtime should already drop versus the ~2:19 baseline (LLM timeout waits are gone); CSV time remains until Task 3.

- [ ] **Step 6: Commit**

```bash
git add tests/conftest.py tests/test_network_block.py
git commit -m "test(conftest): block all LLM network paths in tests

- autouse fixture stubs _call_openrouter/_call_anthropic on both module names
- guard test proves fallback engages without touching requests.post"
```

---

### Task 3: Cache CSV index builders (test speed)

`score_outcomes` re-parses three multi-MB CSVs on every call; `get_hospital_commitments` re-parses two. Dozens of pipeline-building tests multiply that. Wrap the pure loader functions in `functools.lru_cache`. No test currently patches the `*_PATH` globals to simulate missing files (verified 2026-07-09), so caching by no-arg identity is safe; exceptions are not cached by `lru_cache`, so the OSError paths still work.

**Files:**
- Modify: `src/outcome_scorer.py` (decorate `_build_hcahps_measure_index`, `_build_maternal_health_index`, `_build_readmission_penalty_index`)
- Modify: `src/commitment_ingester.py` (decorate `_build_hcahps_ccn_index`, `_load_bf_rows_for_state`)
- Create: `tests/test_csv_cache.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_csv_cache.py
"""CSV index builders are cached — repeated pipeline calls must not re-parse."""

from src.commitment_ingester import _build_hcahps_ccn_index, _load_bf_rows_for_state
from src.outcome_scorer import (
    _build_hcahps_measure_index,
    _build_maternal_health_index,
    _build_readmission_penalty_index,
)


def test_outcome_scorer_builders_are_cached():
    for builder in (
        _build_hcahps_measure_index,
        _build_maternal_health_index,
        _build_readmission_penalty_index,
    ):
        builder.cache_clear()
        first = builder()
        assert builder() is first, f"{builder.__name__} not cached"


def test_commitment_ingester_builders_are_cached():
    _build_hcahps_ccn_index.cache_clear()
    first = _build_hcahps_ccn_index()
    assert _build_hcahps_ccn_index() is first

    _load_bf_rows_for_state.cache_clear()
    first_rows = _load_bf_rows_for_state("NY")
    assert _load_bf_rows_for_state("NY") is first_rows
```

- [ ] **Step 2: Run it — verify it fails**

```bash
.venv/bin/python -m pytest tests/test_csv_cache.py -v
```
Expected: FAIL with `AttributeError: 'function' object has no attribute 'cache_clear'`

- [ ] **Step 3: Add the decorators**

In `src/outcome_scorer.py` — add to imports:

```python
from functools import lru_cache
```

Decorate the three builders (the returned indexes are shared across calls; callers only read them — do not add mutation):

```python
@lru_cache(maxsize=1)
def _build_hcahps_measure_index() -> dict[str, dict[str, dict[str, str]]]:
```
```python
@lru_cache(maxsize=1)
def _build_maternal_health_index() -> dict[str, dict[str, str | None]]:
```
```python
@lru_cache(maxsize=1)
def _build_readmission_penalty_index() -> dict[str, bool | None]:
```

In `src/commitment_ingester.py` — add `from functools import lru_cache` and decorate:

```python
@lru_cache(maxsize=1)
def _build_hcahps_ccn_index() -> dict[str, dict[str, str]]:
```
```python
@lru_cache(maxsize=4)
def _load_bf_rows_for_state(state: str) -> list[dict[str, str]]:
```

- [ ] **Step 4: Run new test, then the full suite with timing**

```bash
.venv/bin/python -m pytest tests/test_csv_cache.py -v
time .venv/bin/python -m pytest tests/ -q
```
Expected: all pass; total wall time **< 30 s**. If any test fails because it mutated a cached index, fix that test to copy before mutating (`copy.deepcopy`) — the pipeline contract already forbids mutating loader output.

- [ ] **Step 5: Commit**

```bash
git add src/outcome_scorer.py src/commitment_ingester.py tests/test_csv_cache.py
git commit -m "perf(data): lru_cache CSV index builders

- outcome_scorer and commitment_ingester parse each CMS file once per process
- full suite drops from ~2:19 to well under 30s"
```

---

### Task 4: Rename `postpartum_visit_pct` → `discharge_info_pct`

The field holds HCAHPS `H_DISCH_HELP_Y_P` (% of patients who reported receiving recovery information at discharge), not a visit completion rate. Mechanical rename first; copy rewrites are Task 5. This is the approved SCHEMA change.

**Files:**
- Modify: `src/outcome_scorer.py`, `src/gap_calculator.py`, `src/outbound_generator.py`, `src/human_checkpoint.py`, `src/dashboard_generator.py`, `src/agent.py`
- Modify: `tests/fixtures.py` and every test file referencing the field
- Modify: `SCHEMA.md`, `ADR.md`, `README.md`

- [ ] **Step 1: Global rename of the field and related identifiers**

```bash
cd /Users/lubakaper/Desktop/L3Projects/ECHO-standalone
grep -rl "postpartum_visit_pct" src tests SCHEMA.md ADR.md README.md \
  | xargs sed -i '' 's/postpartum_visit_pct/discharge_info_pct/g'
grep -rl "postpartum_proxy_pct_raw\|postpartum_proxy_row\|MEASURE_POSTPARTUM_PROXY_PCT\|_postpartum_lag_points" src tests \
  | xargs sed -i '' \
    -e 's/postpartum_proxy_pct_raw/discharge_info_pct_raw/g' \
    -e 's/postpartum_proxy_row/discharge_info_row/g' \
    -e 's/MEASURE_POSTPARTUM_PROXY_PCT/MEASURE_DISCHARGE_INFO_PCT/g' \
    -e 's/_postpartum_lag_points/_discharge_info_lag_points/g'
```

Note: `state_postpartum_avg` keeps its name (it truly is a postpartum visit benchmark). `NY_POSTPARTUM_VISIT_RATE_2023` keeps its name.

- [ ] **Step 2: Fix the semantic comment in `src/outcome_scorer.py`**

Replace the comment block above the renamed field in `_build_outcome_dict` with:

```python
        # H_DISCH_HELP_Y_P — % of patients who reported receiving the
        # information they needed for recovery at discharge. Fourth uses it
        # as its hospital-level discharge-readiness signal. It is NOT a
        # postpartum visit completion rate; outbound copy must never
        # present it as one (enforced by tests/test_copy_honesty.py).
        "discharge_info_pct": discharge_info_pct,
```

Also rename the local variable `postpartum_proxy_pct` → `discharge_info_pct` in `_build_outcome_dict`:

```python
    discharge_info_pct = _to_float_or_none(measures["discharge_info_pct_raw"])
```

- [ ] **Step 3: Update the gap_calculator docstring comment**

In `src/gap_calculator.py`, above `_discharge_info_lag_points`, add:

```python
# Internal ranking proxy: compares the hospital's discharge-info measure
# against the state postpartum visit benchmark. Fine for relative scoring;
# outbound copy must present the two numbers as different measures.
```

- [ ] **Step 4: Update SCHEMA.md prose for the renamed field**

After the sed pass, read `SCHEMA.md` and update the wording around the renamed lines (previously lines ~140, ~170, ~277, ~299):

- Field table row: `"discharge_info_pct": float | None,  # 0.0-100.0 — HCAHPS H_DISCH_HELP_Y_P, % reporting recovery info received at discharge (proxy; not a visit completion rate)`
- Null-rule row for `discharge_info_pct`: keep scoring semantics, wording: "Scores 0 for the discharge-lag subcomponent; cannot drive `baby_vs_mother_contrast` without `well_baby_visit_pct`."
- Scoring row: `discharge_info_pct below state_postpartum_avg | up to 15` plus a footnote: "cross-measure proxy comparison, used for ranking only — never quoted as a like-for-like gap in outbound copy."
- Lead-angle definition: `"baby_vs_mother_contrast"` — "state well-baby completion (state-level proxy) materially outperforms the hospital's discharge-information measure."

- [ ] **Step 5: Run the full suite**

```bash
.venv/bin/python -m pytest tests/ -q
```
Expected: all pass (rename is mechanical; template copy still references the renamed variable via `hospital.get("discharge_info_pct")` after sed).

- [ ] **Step 6: Verify no stragglers, then run the pipeline end-to-end**

```bash
grep -rn "postpartum_visit_pct" src tests SCHEMA.md ADR.md README.md; echo "exit=$?"   # expect exit=1 (no matches)
.venv/bin/python src/agent.py NY
```
Expected: pipeline completes, dashboard written.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "refactor(schema): rename postpartum_visit_pct to discharge_info_pct

- field holds HCAHPS H_DISCH_HELP_Y_P (discharge info received), not visit completion
- rename across src, tests, SCHEMA, ADR, README; scoring unchanged
- SCHEMA documents the proxy explicitly"
```

---

### Task 5: Honest outbound copy + copy-honesty tests

Rewrite every surface that presented the discharge measure as "postpartum visit completion" or computed fake point-gaps across unlike measures.

**Files:**
- Modify: `src/outbound_generator.py` (`_subject`, `_email_body`, `_angle_reason`, `_openrouter_prompt`)
- Modify: `src/human_checkpoint.py` (`_key_metric`)
- Modify: `src/dashboard_generator.py` (metric label, ~line 163)
- Modify: `src/agent.py` (debug label, ~line 102)
- Create: `tests/test_copy_honesty.py`

- [ ] **Step 1: Write the failing copy-honesty tests**

```python
# tests/test_copy_honesty.py
"""
Outbound copy may only claim what the underlying measure shows.

discharge_info_pct is HCAHPS H_DISCH_HELP_Y_P — % of patients who
reported receiving recovery information at discharge. No hospital-level
copy may present it as a postpartum visit completion rate, and no copy
may compute a point-gap between it and a different measure.
"""

import copy

from src.gap_calculator import calculate_gap_score
from src.human_checkpoint import _key_metric
from src.outbound_generator import _angle_reason, _email_body, _openrouter_prompt, _subject
from src.urgency_ranker import add_urgency
from tests.fixtures import FINANCIAL_ONLY, HIGH_GAP, MEDIUM_GAP

FORBIDDEN_PHRASES = [
    "postpartum maternal completion",
    "postpartum completion",
    "visit completion at",       # "...completion at {hospital}" claims a hospital-level rate
    "-point gap",
    "point gap is",
    "pt gap",
    "pt below",
    "pt lag",
]


def _ready(fixture: dict) -> dict:
    return add_urgency(calculate_gap_score(copy.deepcopy(fixture)))


def test_no_surface_claims_visit_completion_from_discharge_measure():
    for fixture in (HIGH_GAP, MEDIUM_GAP, FINANCIAL_ONLY):
        h = _ready(fixture)
        text = " ".join(
            [_subject(h), _email_body(h), _angle_reason(h), _key_metric(h)]
        ).lower()
        for phrase in FORBIDDEN_PHRASES:
            assert phrase not in text, f"{phrase!r} found in copy for {h['lead_angle']}"


def test_baby_vs_mother_copy_labels_both_measures():
    h = _ready(HIGH_GAP)  # HIGH_GAP resolves to baby_vs_mother_contrast
    assert h["lead_angle"] == "baby_vs_mother_contrast"
    body = _email_body(h)
    assert "well-baby" in body.lower()
    assert "discharge" in body.lower()          # the hospital number is a discharge measure
    assert "94%" in body and "61%" in body      # both real numbers present, no fake subtraction


def test_prompt_defines_discharge_measure_and_forbids_mislabeling():
    h = _ready(HIGH_GAP)
    prompt = _openrouter_prompt(h)
    assert "discharge_info_pct" in prompt
    assert "postpartum_visit_pct" not in prompt
    assert "not a postpartum visit completion rate" in prompt.lower()
```

- [ ] **Step 2: Run — verify failures**

```bash
.venv/bin/python -m pytest tests/test_copy_honesty.py -v
```
Expected: FAIL (current copy says "postpartum maternal completion", computes point-gaps, prompt lacks the definition).

- [ ] **Step 3: Replace `_subject` in `src/outbound_generator.py`**

```python
def _subject(hospital: dict[str, Any]) -> str:
    name = hospital["facility_name"]
    lead = hospital.get("lead_angle")
    discharge_info = hospital.get("discharge_info_pct")
    well_baby = hospital.get("well_baby_visit_pct")
    state_avg = hospital.get("state_postpartum_avg")
    star = hospital.get("hcahps_care_transition_star")

    if lead == "baby_vs_mother_contrast" and well_baby is not None and discharge_info is not None:
        return f"{name} — infant follow-up is working; maternal discharge prep lags"
    if lead == "hcahps_care_transition_gap" and star is not None:
        return f"{name} — {star}/5 care transition score"
    if lead == "financial_unrealized":
        return f"{name} — RPM billing opportunity in your Medicaid mix"
    if lead == "smm_rate_gap":
        return f"{name} — maternal morbidity signal worth addressing"
    if lead == "state_strength_vs_hospital_lag" and discharge_info is not None and state_avg is not None:
        return f"{name} — discharge readiness vs NY's postpartum strength"
    return f"{name} — postpartum care continuity"
```

- [ ] **Step 4: Replace the two dishonest branches of `_email_body`**

Replace the `baby_vs_mother_contrast` branch:

```python
    if lead == "baby_vs_mother_contrast" and discharge_info and well_baby:
        return (
            "Hi,\n\n"
            f"Across NY, well-baby visit completion averages {well_baby} — infant "
            f"follow-up systems work. Yet only {discharge_info} of patients at {name} "
            "reported getting the information they needed for their own recovery at "
            "discharge. The baby gets a system; the mother gets a pamphlet.\n\n"
            f"Babyscripts is built for exactly this: remote postpartum monitoring with BP kits, "
            f"a mobile app, OB-specialized care managers, and RPM CPT billing support. {proof}\n\n"
            f"{sign_off}"
        )
```

Replace the `state_avg and postpartum` branch (now `state_avg and discharge_info`):

```python
    if state_avg and discharge_info:
        return (
            "Hi,\n\n"
            f"NY is one of the stronger postpartum states — {state_avg} of Medicaid "
            f"postpartum visits are completed statewide. But at {name}, only "
            f"{discharge_info} of patients reported getting the information they needed "
            "for their recovery at discharge — and that handoff is where follow-through "
            "starts.\n\n"
            f"Babyscripts closes that gap with remote postpartum monitoring: BP kits, mobile app, "
            f"OB-specialized care managers, and RPM CPT billing support. {proof}\n\n"
            f"{sign_off}"
        )
```

Update the local variable block at the top of `_email_body`:

```python
    discharge_info = _format_pct(hospital.get("discharge_info_pct"))
    well_baby = _format_pct(hospital.get("well_baby_visit_pct"))
    state_avg = _format_pct(hospital.get("state_postpartum_avg"))
```

(`hcahps_care_transition_gap`, `smm_rate_gap`, `financial_unrealized`, and the commitment fallback branches are already honest — leave them.)

- [ ] **Step 5: Replace `_angle_reason`**

```python
def _angle_reason(hospital: dict[str, Any]) -> str:
    lead = hospital.get("lead_angle", "")
    discharge_info = hospital.get("discharge_info_pct")
    well_baby = hospital.get("well_baby_visit_pct")
    state_avg = hospital.get("state_postpartum_avg")
    star = hospital.get("hcahps_care_transition_star")
    smm = hospital.get("smm_rate")

    if lead == "baby_vs_mother_contrast" and well_baby is not None and discharge_info is not None:
        return (
            f"NY well-baby {float(well_baby):g}% (state proxy) vs "
            f"{float(discharge_info):g}% discharge-info at hospital"
        )
    if lead == "hcahps_care_transition_gap" and star is not None:
        return f"Care transition {star}/5 stars — below 3-star threshold"
    if lead == "smm_rate_gap" and smm is not None:
        return f"SMM rate {float(smm):.0f}/10K deliveries — above 150 benchmark"
    if lead == "financial_unrealized":
        return "Medicaid extended — RPM coverage window available"
    if lead == "state_strength_vs_hospital_lag" and discharge_info is not None and state_avg is not None:
        return (
            f"NY postpartum visits {float(state_avg):g}% (state benchmark) vs "
            f"{float(discharge_info):g}% discharge-info at hospital"
        )
    return f"Lead angle: {lead}"
```

- [ ] **Step 6: Update `_openrouter_prompt`**

In the `facts` dict, replace the old key with:

```python
        "discharge_info_pct": hospital.get("discharge_info_pct"),
        "discharge_info_definition": (
            "percent of patients who reported receiving the information they "
            "needed for their recovery at discharge (HCAHPS H_DISCH_HELP_Y_P). "
            "This is not a postpartum visit completion rate."
        ),
```

And add one rule line to the Rules block:

```python
        "- discharge_info_pct measures discharge information received; never describe it as a visit completion, follow-up, or postpartum visit rate.\n"
```

In `_validate_llm_body`, the `pct_fields` list already picks up the renamed field from Task 4's sed — verify it reads:

```python
    pct_fields = [
        v for v in (
            hospital.get("discharge_info_pct"),
            hospital.get("well_baby_visit_pct"),
            hospital.get("state_postpartum_avg"),
        )
        if v is not None
    ]
```

- [ ] **Step 7: Replace `_key_metric` in `src/human_checkpoint.py`**

```python
def _key_metric(hospital: dict[str, Any]) -> str:
    lead = hospital.get("lead_angle", "")
    discharge_info = hospital.get("discharge_info_pct")
    well_baby = hospital.get("well_baby_visit_pct")
    state_avg = hospital.get("state_postpartum_avg")
    star = hospital.get("hcahps_care_transition_star")
    smm = hospital.get("smm_rate")

    if lead == "baby_vs_mother_contrast" and well_baby is not None and discharge_info is not None:
        return f"Well-baby {float(well_baby):g}% (state) vs discharge-info {float(discharge_info):g}%"
    if lead == "hcahps_care_transition_gap" and star is not None:
        return f"Care transition {star}/5 stars"
    if lead == "smm_rate_gap" and smm is not None:
        return f"SMM {float(smm):.0f}/10K"
    if lead == "financial_unrealized":
        return "Medicaid extended"
    if lead == "state_strength_vs_hospital_lag" and discharge_info is not None and state_avg is not None:
        return f"Discharge-info {float(discharge_info):g}% vs state postpartum {float(state_avg):g}%"
    return "—"
```

- [ ] **Step 8: Update dashboard + agent labels**

`src/dashboard_generator.py` (~line 163): change `{_metric("Postpartum visit", hospital.get("discharge_info_pct"))}` to:

```python
        {_metric("Discharge info received", hospital.get("discharge_info_pct"))}
```

`src/agent.py` (~line 102): change the debug format string `"Tool 2 — First hospital outcome fields: postpartum=%s well_baby=%s "` to `"Tool 2 — First hospital outcome fields: discharge_info=%s well_baby=%s "`.

- [ ] **Step 9: Run copy-honesty tests, then the full suite**

```bash
.venv/bin/python -m pytest tests/test_copy_honesty.py -v
.venv/bin/python -m pytest tests/ -q
```
Expected: all pass. Some existing outbound/checkpoint/dashboard tests assert old copy strings — update those assertions to the new honest strings (they are testing presentation text, not contracts).

- [ ] **Step 10: Run the pipeline and eyeball one email**

```bash
.venv/bin/python src/agent.py NY --debug 2>&1 | head -60
```
Expected: emails render with the new copy; no "maternal completion" phrasing anywhere.

- [ ] **Step 11: Commit**

```bash
git add -A
git commit -m "fix(copy): outbound claims match what the data measures

- discharge-info measure never presented as visit completion
- no computed point-gaps across unlike measures
- LLM prompt defines the measure and forbids mislabeling
- copy-honesty tests enforce all of it"
```

---

### Task 6: Centralize state-level urgency context in constants

`outcome_scorer` hardcodes `state_mortality_rank`, `racial_disparity_flag`, `medicaid_extended` per hospital; `urgency_ranker` duplicates two of them. Single sourced constant, documented as state-level context.

**Files:**
- Modify: `src/constants.py`
- Modify: `src/outcome_scorer.py` (`_build_outcome_dict`)
- Modify: `src/urgency_ranker.py` (`STATE_URGENCY_CONTEXT`)
- Modify: `SCHEMA.md` (state-level context note)

- [ ] **Step 1: Add to `src/constants.py`**

```python
# NY state-level urgency context. These apply IDENTICALLY to every NY
# hospital — they are facts about the state, not per-hospital signals,
# and add flat urgency-context points in Tool 4 (see SCHEMA.md).
# Sources:
# - medicaid_extended: KFF postpartum Medicaid coverage tracker
#   (data/kff_postpartum_coverage.csv) — NY adopted the 12-month extension.
# - racial_disparity_flag: NCHS Health E-Stat 113 (data/hestat113.pdf) and
#   Cureus racial disparity study (data/cureus-racial-disparity.pdf).
# - state_mortality_rank: NCHS Health E-Stat 113 state maternal mortality tables.
NY_STATE_URGENCY_CONTEXT: dict[str, bool | str] = {
    "medicaid_extended": True,
    "racial_disparity_flag": True,
    "state_mortality_rank": "bottom_quartile",
}
```

- [ ] **Step 2: Use it in `src/outcome_scorer.py`**

Import: `from constants import NY_POSTPARTUM_VISIT_RATE_2023, NY_WELL_BABY_VISIT_RATE_2023, NY_STATE_URGENCY_CONTEXT`

In `_build_outcome_dict`, replace the three hardcoded lines:

```python
        "state_mortality_rank": "bottom_quartile",
        "racial_disparity_flag": True,
        "medicaid_extended": True,
```

with:

```python
        # State-level context, identical for all NY hospitals (see constants.py)
        **NY_STATE_URGENCY_CONTEXT,
```

- [ ] **Step 3: Use it in `src/urgency_ranker.py`**

Replace the `STATE_URGENCY_CONTEXT` literal with:

```python
from constants import NY_STATE_URGENCY_CONTEXT

STATE_URGENCY_CONTEXT = {
    # State facts, not per-hospital signals — sources cited in constants.py.
    "NY": {
        "medicaid_extended": NY_STATE_URGENCY_CONTEXT["medicaid_extended"],
        "racial_disparity_flag": NY_STATE_URGENCY_CONTEXT["racial_disparity_flag"],
    }
}
```

Note: `urgency_ranker` imports `constants` bare (matching the module's existing flat-import style used across `src/`).

- [ ] **Step 4: Add SCHEMA.md note**

In the field-documentation section, add under the three fields:

> `state_mortality_rank`, `racial_disparity_flag`, and `medicaid_extended` are **state-level context** — identical for every hospital in a state (same pattern as `well_baby_visit_estimated`). They add flat urgency-context points and cannot differentiate hospitals within a state. Sources are cited in `src/constants.py`.

- [ ] **Step 5: Run the full suite**

```bash
.venv/bin/python -m pytest tests/ -q
```
Expected: all pass (values unchanged; only their source moved).

- [ ] **Step 6: Commit**

```bash
git add src/constants.py src/outcome_scorer.py src/urgency_ranker.py SCHEMA.md
git commit -m "refactor(constants): single-source NY state urgency context with citations"
```

---### Task 7: Guard test — SMM angle is dead until CMS ships PC_07a

**Files:**
- Create: `tests/test_smm_data_availability.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_smm_data_availability.py
"""
PC_07a (SMM rate) is 'Not Available' in the current CMS release, so the
smm_rate_gap angle cannot fire from real data. If this test FAILS, CMS
has shipped SMM data — activate the angle: remove this test, verify
smm-dependent copy, and update README/methodology roadmap notes.
"""

from src.commitment_ingester import get_hospital_commitments
from src.outcome_scorer import score_outcomes


def test_smm_rate_is_none_for_all_hospitals_in_current_release():
    hospitals = score_outcomes(get_hospital_commitments("NY"))
    assert hospitals, "pipeline returned no hospitals — data files missing?"
    assert all(h["smm_rate"] is None for h in hospitals)
```

- [ ] **Step 2: Run it — expect immediate pass (documents current reality)**

```bash
.venv/bin/python -m pytest tests/test_smm_data_availability.py -v
```
Expected: PASS (fast — CSV indexes are cached from Task 3).

- [ ] **Step 3: Commit**

```bash
git add tests/test_smm_data_availability.py
git commit -m "test(data): pin SMM unavailability — failing test signals CMS shipped PC_07a"
```

---

### Task 8: Clean and pin dependencies

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Capture installed versions and install streamlit**

```bash
.venv/bin/pip install streamlit
.venv/bin/pip freeze | grep -iE "^(anthropic|pandas|requests|python-dotenv|pytest|streamlit)=="
```

- [ ] **Step 2: Rewrite `requirements.txt`**

Using the exact versions printed above (do not guess versions), in this shape:

```text
# Pipeline
pandas==<printed>          # scripts/filter_hcahps_to_ny.py only
requests==<printed>
python-dotenv==<printed>
anthropic==<printed>       # LLM fallback for outbound generation

# Demo app
streamlit==<printed>

# Dev
pytest==<printed>
```

Removed: `strands-agents`, `openai` (never imported anywhere in the repo — verified 2026-07-09).

- [ ] **Step 3: Verify from a clean install**

```bash
python3 -m venv /tmp/fourth-req-check
/tmp/fourth-req-check/bin/pip install -q -r requirements.txt
/tmp/fourth-req-check/bin/python -m pytest tests/ -q
rm -rf /tmp/fourth-req-check
```
Expected: suite passes on a fresh environment.

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "chore(deps): pin versions, drop unused strands-agents/openai, add streamlit"
```

---

### Task 9: GitHub Actions CI

Safe to run in CI because Task 2 guarantees no network and no secrets are needed.

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Write the workflow**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install -r requirements.txt
      - run: python -m pytest tests/ -q
```

- [ ] **Step 2: Commit, push, verify**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: run test suite on push and PR"
git push origin main
gh run watch --repo LubaKaper/FOURTH --exit-status || gh run list --repo LubaKaper/FOURTH --limit 1
```
Expected: run completes green. If it fails, read the log (`gh run view --log-failed`), fix, and re-push before proceeding.

---

### Task 10: Demo results exporter

**Files:**
- Create: `scripts/export_demo_results.py`
- Create: `tests/test_export_demo_results.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_export_demo_results.py
"""build_demo_payload packages pipeline output for the Streamlit app."""

import copy

from src.gap_calculator import calculate_gap_score
from src.outbound_generator import generate_outbound_email
from src.urgency_ranker import add_urgency
from tests.fixtures import HIGH_GAP, MEDIUM_GAP

from scripts.export_demo_results import HOSPITAL_EXPORT_FIELDS, build_demo_payload

REQUIRED_EMAIL_KEYS = {
    "facility_id", "facility_name", "recipient_role", "subject", "email_body",
    "product", "lead_angle", "angle_reason", "gap_score", "urgency_tier",
    "sent_at", "status", "claim_validation", "data_confidence",
}


def _ready(fixture: dict) -> dict:
    return add_urgency(calculate_gap_score(copy.deepcopy(fixture)))


def test_payload_shape_and_email_contract():
    hospitals = [_ready(HIGH_GAP), _ready(MEDIUM_GAP)]
    emails = generate_outbound_email(hospitals)  # network blocked -> template bodies

    payload = build_demo_payload(hospitals, emails, "2026-07-09T00:00:00+00:00")

    assert payload["state"] == "NY"
    assert payload["generated_at"] == "2026-07-09T00:00:00+00:00"
    assert len(payload["accounts"]) == 2
    for account in payload["accounts"]:
        assert set(account) == set(HOSPITAL_EXPORT_FIELDS) | {"email"}
        assert account["email"] is not None
        assert REQUIRED_EMAIL_KEYS <= set(account["email"])


def test_account_without_email_gets_null_email():
    hospitals = [_ready(HIGH_GAP)]
    payload = build_demo_payload(hospitals, [], "2026-07-09T00:00:00+00:00")
    assert payload["accounts"][0]["email"] is None
```

- [ ] **Step 2: Run — verify failure**

```bash
.venv/bin/python -m pytest tests/test_export_demo_results.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.export_demo_results'`. Create an empty `scripts/__init__.py` if the import path needs it.

- [ ] **Step 3: Write `scripts/export_demo_results.py`**

```python
#!/usr/bin/env python3
"""
export_demo_results.py — run the full Fourth pipeline (review mode) and
write data/demo_results.json for the Streamlit demo app (app.py).

Run locally with live LLM keys in .env to get real generated emails:
    OPENROUTER_MAX_LIVE_EMAILS=10 .venv/bin/python scripts/export_demo_results.py

Real CMS data, real pipeline output. No mock data. Fails loudly (exit 1)
if the pipeline yields zero accounts or zero emails.
"""

import datetime
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from account_selector import select_top_accounts          # noqa: E402
from approvals import run_approvals                       # noqa: E402
from commitment_ingester import get_hospital_commitments  # noqa: E402
from gap_calculator import calculate_gap_score            # noqa: E402
from outbound_generator import generate_outbound_email    # noqa: E402
from outcome_scorer import score_outcomes                 # noqa: E402
from urgency_ranker import add_urgency                    # noqa: E402

OUTPUT_PATH = ROOT / "data" / "demo_results.json"

HOSPITAL_EXPORT_FIELDS = [
    "facility_id", "facility_name", "city", "county", "state",
    "birthing_friendly", "commitment_tag",
    "discharge_info_pct", "well_baby_visit_pct", "well_baby_visit_estimated",
    "state_postpartum_avg", "smm_rate", "hcahps_care_transition_star",
    "hcahps_overall_star", "readmission_penalty",
    "gap_score", "gap_breakdown", "urgency_tier", "urgency_flag",
    "urgency_breakdown", "lead_angle", "data_confidence",
]


def build_demo_payload(
    hospitals: list[dict[str, Any]],
    emails: list[dict[str, Any]],
    generated_at: str,
) -> dict[str, Any]:
    """Package selected hospitals + their email objects for app.py."""
    email_by_id = {e["facility_id"]: e for e in emails}
    accounts = []
    for hospital in hospitals:
        account = {key: hospital.get(key) for key in HOSPITAL_EXPORT_FIELDS}
        account["email"] = email_by_id.get(hospital["facility_id"])
        accounts.append(account)
    return {"generated_at": generated_at, "state": "NY", "accounts": accounts}


def main() -> int:
    hospitals = get_hospital_commitments("NY")
    hospitals = score_outcomes(hospitals)
    hospitals = [calculate_gap_score(h) for h in hospitals]
    hospitals = [add_urgency(h) for h in hospitals]
    selected = select_top_accounts(hospitals, limit=10, require_high_confidence=False)
    emails = run_approvals(generate_outbound_email(selected))

    if not selected or not emails:
        print(
            f"ERROR: pipeline produced {len(selected)} accounts and "
            f"{len(emails)} emails — refusing to write demo data.",
            file=sys.stderr,
        )
        return 1

    generated_at = datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")
    payload = build_demo_payload(selected, emails, generated_at)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(payload['accounts'])} accounts to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests — verify pass**

```bash
touch scripts/__init__.py
.venv/bin/python -m pytest tests/test_export_demo_results.py -v
.venv/bin/python -m pytest tests/ -q
```
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/__init__.py scripts/export_demo_results.py tests/test_export_demo_results.py
git commit -m "feat(demo): exporter packages real pipeline output as demo_results.json"
```

---

### Task 11: Streamlit app

Read-only viewer over `data/demo_results.json`. Imports no pipeline code; needs no keys; cannot send.

**Files:**
- Create: `app.py` (repo root — Streamlit Cloud convention)
- Create: `tests/test_app_data.py`

- [ ] **Step 1: Write the failing data-loader test**

```python
# tests/test_app_data.py
"""app.py's loader validates demo_results.json before rendering."""

import json

import pytest

from app import load_results


def test_load_results_rejects_missing_keys(tmp_path):
    bad = tmp_path / "demo_results.json"
    bad.write_text(json.dumps({"accounts": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="generated_at"):
        load_results(bad)


def test_load_results_accepts_valid_payload(tmp_path):
    good = tmp_path / "demo_results.json"
    good.write_text(
        json.dumps(
            {
                "generated_at": "2026-07-09T00:00:00+00:00",
                "state": "NY",
                "accounts": [
                    {"facility_id": "330101", "facility_name": "Test", "gap_score": 70.0,
                     "urgency_tier": "high", "lead_angle": "baby_vs_mother_contrast",
                     "data_confidence": "high", "email": None}
                ],
            }
        ),
        encoding="utf-8",
    )
    data = load_results(good)
    assert data["state"] == "NY"
    assert len(data["accounts"]) == 1
```

- [ ] **Step 2: Run — verify failure**

```bash
.venv/bin/python -m pytest tests/test_app_data.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'app'` (conftest already puts repo root on sys.path).

- [ ] **Step 3: Write `app.py`**

```python
"""
Fourth — Account Intelligence for Maternal Health GTM (demo app).

Read-only Streamlit viewer over data/demo_results.json — precomputed
output of the real pipeline over real CMS data. No API keys, no email
sending, no pipeline imports.

Run: streamlit run app.py
"""

import json
from pathlib import Path
from typing import Any

import streamlit as st

RESULTS_PATH = Path(__file__).parent / "data" / "demo_results.json"

REQUIRED_TOP_KEYS = {"generated_at", "state", "accounts"}

TIER_BADGE = {"high": "🔴 High", "medium": "🟡 Medium", "low": "🟢 Low"}

ANGLE_LABELS = {
    "baby_vs_mother_contrast": "Baby vs. mother contrast",
    "hcahps_care_transition_gap": "HCAHPS care transition gap",
    "state_strength_vs_hospital_lag": "State strength vs. hospital lag",
    "financial_unrealized": "Unrealized RPM billing window",
    "smm_rate_gap": "SMM rate gap",
}

# (measure, provenance, meaning) — data honesty shown to every visitor.
SIGNAL_PROVENANCE = [
    ("HCAHPS care transition star", "Hospital-level",
     "CMS HCAHPS H_COMP_6 star rating for the discharge/transition experience."),
    ("Discharge info received %", "Hospital-level",
     "CMS HCAHPS H_DISCH_HELP_Y_P — % of patients who reported receiving the "
     "information they needed for recovery at discharge. A discharge-readiness "
     "signal, NOT a postpartum visit completion rate."),
    ("Well-baby visit %", "State-level proxy",
     "NY Child Core Set 2023 benchmark (91.5%) applied to every hospital; "
     "flagged well_baby_visit_estimated. No hospital-level source exists yet."),
    ("State postpartum visit average", "State benchmark",
     "CMS Medicaid Adult Core Set PPC-AD, NY 2023: 82.4% postpartum visit completion."),
    ("SMM rate", "Not yet available",
     "PC_07a is 'Not Available' in the current CMS release. The smm_rate_gap "
     "lead angle stays dormant until CMS ships it (roadmap: CDC WONDER)."),
    ("Medicaid extension / disparity / mortality rank", "State-level context",
     "State facts applied identically to all NY hospitals; add flat urgency "
     "context points and cannot differentiate hospitals within NY."),
]


def load_results(path: Path = RESULTS_PATH) -> dict[str, Any]:
    """Load and validate the demo payload. Raises ValueError on bad shape."""
    data = json.loads(path.read_text(encoding="utf-8"))
    missing = REQUIRED_TOP_KEYS - set(data)
    if missing:
        raise ValueError(f"demo_results.json missing keys: {', '.join(sorted(missing))}")
    return data


def _fmt(value: Any, suffix: str = "") -> str:
    return "—" if value is None else f"{value}{suffix}"


def render_accounts(data: dict[str, Any]) -> None:
    st.subheader(f"Top accounts — {data['state']}")
    st.caption(f"Generated {data['generated_at']} from CMS public data.")
    rows = [
        {
            "Hospital": a["facility_name"],
            "Gap score": a["gap_score"],
            "Urgency": TIER_BADGE.get(a["urgency_tier"], a["urgency_tier"]),
            "Lead angle": ANGLE_LABELS.get(a["lead_angle"], a["lead_angle"]),
            "Confidence": a["data_confidence"],
            "Email drafted": "✉️" if a.get("email") else "—",
        }
        for a in data["accounts"]
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)


def render_account_detail(data: dict[str, Any]) -> None:
    names = [a["facility_name"] for a in data["accounts"]]
    chosen = st.selectbox("Account", names)
    account = next(a for a in data["accounts"] if a["facility_name"] == chosen)

    left, right = st.columns(2)
    with left:
        st.metric("Gap score", account["gap_score"])
        st.write(f"**Urgency:** {TIER_BADGE.get(account['urgency_tier'])}")
        st.write(f"**Lead angle:** {ANGLE_LABELS.get(account['lead_angle'])}")
        if account.get("email"):
            st.write(f"**Angle reason:** {account['email']['angle_reason']}")
    with right:
        st.write("**Gap breakdown**")
        st.json(account.get("gap_breakdown") or {})
        st.write("**Urgency breakdown**")
        st.json(account.get("urgency_breakdown") or {})

    st.divider()
    st.write("**Signals** (provenance in Methodology)")
    st.dataframe(
        [
            {"Signal": "Discharge info received (hospital)", "Value": _fmt(account.get("discharge_info_pct"), "%")},
            {"Signal": "Care transition star (hospital)", "Value": _fmt(account.get("hcahps_care_transition_star"), "/5")},
            {"Signal": "Well-baby visits (state proxy)", "Value": _fmt(account.get("well_baby_visit_pct"), "%")},
            {"Signal": "State postpartum visit avg", "Value": _fmt(account.get("state_postpartum_avg"), "%")},
            {"Signal": "SMM rate", "Value": _fmt(account.get("smm_rate"))},
            {"Signal": "Readmission penalty", "Value": _fmt(account.get("readmission_penalty"))},
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.divider()
    email = account.get("email")
    if not email:
        st.info("No email drafted for this account (below threshold or low confidence).")
        return
    st.write(f"**To:** {email['recipient_role']}  ·  **Status:** `{email['status']}`  ·  "
             f"**Claim validation:** `{email['claim_validation']}`")
    st.write(f"**Subject:** {email['subject']}")
    st.code(email["email_body"], language=None)


def render_methodology() -> None:
    st.subheader("How Fourth works")
    st.markdown(
        """
```text
commitment_ingester → outcome_scorer → gap_calculator → urgency_ranker
      → account_selector → outbound_generator → approvals → send controls
```

**Gap score (0–100), three layers:** commitment strength (0–25, CMS
Birthing-Friendly designation + MMSM participation) · outcome gap (0–50,
discharge-info lag vs. state benchmark, HCAHPS care transition, readmission
penalty, SMM when available) · urgency context (0–25, state-level factors).

**Claim validation.** The LLM drafts only the email body. Deterministic code
then rejects any draft containing a percentage not within 1 point of a real
source field, any star rating that doesn't match the hospital's HCAHPS data,
unsupported claim language, or the internal gap score. Rejected drafts fall
back to deterministic templates. The LLM cannot introduce a number this app
displays.

**Send safety.** Emails hold at `pending_review` for human review. The send
path (not exposed here) enforces an approval gate, a final send gate, a
30-day dedup cooldown, and an append-only audit log with body hashes.
        """
    )
    st.subheader("Signal provenance — what's real, what's proxy")
    st.dataframe(
        [{"Signal": s, "Provenance": p, "Meaning": m} for s, p, m in SIGNAL_PROVENANCE],
        use_container_width=True,
        hide_index=True,
    )


def main() -> None:
    st.set_page_config(page_title="Fourth — Account Intelligence", page_icon="🏥", layout="wide")
    st.title("Fourth")
    st.caption(
        "Account intelligence for maternal health GTM — finds CMS Birthing-Friendly "
        "hospitals whose postpartum follow-through signals lag their commitments. "
        "Demo shows precomputed output of the real pipeline over real CMS data."
    )

    if not RESULTS_PATH.exists():
        st.warning("Demo data not generated yet. Run:")
        st.code(".venv/bin/python scripts/export_demo_results.py")
        st.stop()
    try:
        data = load_results()
    except (ValueError, json.JSONDecodeError) as exc:
        st.error(f"demo_results.json is invalid: {exc}")
        st.stop()

    view = st.sidebar.radio("View", ["Ranked accounts", "Account detail", "Methodology"])
    if view == "Ranked accounts":
        render_accounts(data)
    elif view == "Account detail":
        render_account_detail(data)
    else:
        render_methodology()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests, then eyeball the app with placeholder-free data**

```bash
.venv/bin/python -m pytest tests/test_app_data.py -v
.venv/bin/python -m pytest tests/ -q
.venv/bin/python scripts/export_demo_results.py   # template emails (no keys needed) — enough to view layout
.venv/bin/streamlit run app.py                    # check all three views render, then Ctrl-C
```
Expected: tests pass; all three views render without errors against real pipeline data with template email bodies.

- [ ] **Step 5: Commit (app code only — real demo data comes in Task 12)**

```bash
git add app.py tests/test_app_data.py
git commit -m "feat(app): Streamlit demo viewer over precomputed pipeline results

- ranked accounts, account detail, methodology + signal provenance views
- reads data/demo_results.json only; no keys, no pipeline imports, no send path"
```

---

### Task 12: Generate and commit real demo data (needs Luba's `.env` keys)

**Files:**
- Create: `data/demo_results.json` (committed)

- [ ] **Step 1: Full live run** (requires `OPENROUTER_API_KEY` and/or `ANTHROPIC_API_KEY` in `.env`)

```bash
OPENROUTER_MAX_LIVE_EMAILS=10 .venv/bin/python scripts/export_demo_results.py
```
Expected: "Wrote N accounts to .../data/demo_results.json" with N ≥ 1.

- [ ] **Step 2: Review the output with Luba before committing**

```bash
.venv/bin/python -m json.tool data/demo_results.json | head -80
.venv/bin/streamlit run app.py
```
Check: email bodies read well, no mislabeled claims, no PII beyond public hospital info. **Luba reviews and approves the JSON content** (it ships publicly).

- [ ] **Step 3: Smoke-check the committed payload passes the app loader test against the real file**

```bash
.venv/bin/python -c "from app import load_results; d = load_results(); print(len(d['accounts']), 'accounts OK')"
```

- [ ] **Step 4: Commit**

```bash
git add data/demo_results.json
git commit -m "feat(demo): commit precomputed real-pipeline demo results for the app"
```

---

### Task 13: README rewrite, screenshots, identity cleanup

**Files:**
- Modify: `README.md` (full rewrite)
- Create: `docs/images/app-accounts.png`, `docs/images/app-detail.png`, `docs/images/app-methodology.png`
- Modify: `CLAUDE.md` (repo name field), `STANDALONE_CONTEXT.md`/`AGENTS.md` only if they misname the product

- [ ] **Step 1: Capture screenshots**

Run `.venv/bin/streamlit run app.py`, open `http://localhost:8501`, capture each of the three views at ~1280px wide, save as the three PNG paths above. (Use the browser tooling or macOS `Cmd-Shift-4`.)

- [ ] **Step 2: Rewrite `README.md`**

```markdown
# Fourth — Account Intelligence for Maternal Health GTM

Fourth finds CMS Birthing-Friendly hospitals whose discharge-readiness and
patient-experience signals lag their public maternal health commitments,
ranks them with a 3-layer gap score, and drafts claim-validated outbound
email for a GTM engineer to review. Built for maternal health companies
like Babyscripts; hospitals are the sales targets.

**Live demo:** _link added on deploy (Task 14)_ · ![CI](https://github.com/LubaKaper/FOURTH/actions/workflows/ci.yml/badge.svg)

![Ranked accounts view](docs/images/app-accounts.png)

## Why this exists

NY completes 82.4% of Medicaid postpartum visits statewide, and well-baby
follow-up runs even higher — yet at many Birthing-Friendly hospitals, far
fewer patients report getting the information they needed for their own
recovery at discharge. The baby gets a system; the mother gets a pamphlet.
Fourth finds those hospitals and turns ~90 minutes of manual account
research into a 10-minute review.

## What makes it interesting technically

**LLM claim validation.** The LLM drafts only the email body. Deterministic
code rejects any draft with a percentage not within 1 point of a real source
field, a star rating that doesn't match the hospital's HCAHPS data,
unsupported claim language, or the internal account score — and falls back
to deterministic templates. A fabricated number cannot reach an email.

**Send safety.** Approval gate (score ≥ 70 + high confidence + validation
passed) → final send gate → 30-day dedup cooldown → SMTP → append-only
audit log with body hashes. Review mode never touches the mailer.

**Data honesty.** Every signal is labeled hospital-level, state-level proxy,
or not-yet-available — in the app's methodology view and in SCHEMA.md. The
discharge-information measure is never presented as visit completion.

## Pipeline

```text
commitment_ingester → outcome_scorer → gap_calculator → urgency_ranker
      → account_selector → outbound_generator → approvals → send controls
```

One hospital dict travels the pipeline; each tool only adds fields.
Contracts live in [SCHEMA.md](SCHEMA.md); decisions in [ADR.md](ADR.md).

## Data sources

| Source | Provides | Level |
|---|---|---|
| CMS Birthing-Friendly registry | Hospital universe + commitment | Hospital |
| CMS HCAHPS (NY) | Care transition star, discharge-info %, overall star | Hospital |
| CMS Maternal Health file | MMSM participation; SMM pending CMS release | Hospital |
| CMS HRRP FY2026 | Readmission penalty signal | Hospital |
| CMS Medicaid Core Sets (NY 2023) | Postpartum visit benchmark 82.4%, well-baby proxy 91.5% | State |

## Run it

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest tests/ -q      # offline, no API keys needed
.venv/bin/python src/agent.py NY          # full pipeline, review mode
.venv/bin/streamlit run app.py            # demo app over precomputed results
```

Optional: add `OPENROUTER_API_KEY` (and/or `ANTHROPIC_API_KEY`) to `.env`
for live email generation — see `.env.example`. Send mode (`--send`)
additionally requires SMTP credentials and is never exposed by the app.

## Status & roadmap

Prototype targeting NY. Next: hospital-level SMM when CMS ships PC_07a
(CDC WONDER as interim), hospital-level well-baby sourcing, multi-state,
curated commitment tags, CRM integration.

Fourth grew out of a team class project (ECHO); this repo is the standalone
continuation, built and owned by Luba Kaper.
```

Keep the existing OpenRouter env-var reference table by moving it into `.env.example` comments if it's removed from README.

- [ ] **Step 3: Identity cleanup**

```bash
grep -rn "ECHO" README.md CLAUDE.md AGENTS.md STANDALONE_CONTEXT.md PRODUCT_VISION.md | grep -vi "grew out\|class project\|standalone continuation"
```
Update `CLAUDE.md`'s "**Repo:** ECHO-standalone" line to "**Repo:** FOURTH (local dir: ECHO-standalone)". Leave historical docs (`STANDALONE_CONTEXT.md`, `prd.md`) intact — they are history, and README now tells the current story.

- [ ] **Step 4: Verify README renders (images resolve) and commit**

```bash
git add README.md CLAUDE.md docs/images/
git commit -m "docs(readme): portfolio rewrite — demo, claim validation, data honesty, screenshots"
```

---

### Task 14: Deploy to Streamlit Community Cloud + final push

Manual steps with Luba (requires her GitHub/Streamlit login).

- [ ] **Step 1: Push everything**

```bash
git push origin main
gh run watch --repo LubaKaper/FOURTH --exit-status
```
Expected: CI green on the final tree.

- [ ] **Step 2: Deploy (Luba, in browser)**

1. Go to https://share.streamlit.io → sign in with GitHub.
2. "Create app" → repo `LubaKaper/FOURTH`, branch `main`, entrypoint `app.py`.
3. No secrets needed (the app is read-only by design).
4. Confirm the app builds and all three views render at the public URL.

- [ ] **Step 3: Wire the URL back into the repo**

- Replace the README line `**Live demo:** _link added on deploy (Task 14)_` with `**Live demo:** https://<app-url>`.
- On GitHub → repo → About: add the URL, description "Account intelligence for maternal health GTM — CMS data, gap scoring, claim-validated LLM outbound", topics: `healthcare`, `sales-intelligence`, `llm`, `python`, `streamlit`.

```bash
git add README.md
git commit -m "docs(readme): add live demo URL"
git push origin main
```

- [ ] **Step 4: Final acceptance sweep (from the spec)**

```bash
git fetch origin && git status                          # up to date with origin/main
time .venv/bin/python -m pytest tests/ -q               # < 30s, all pass, offline
grep -rn "postpartum_visit_pct" src tests SCHEMA.md     # no matches
```
Then verify by hand: CI badge green on GitHub, live demo URL loads all views, README shows screenshots + provenance section.

---

## Self-Review Notes

- **Spec coverage:** WS1.1→Task 4, WS1.2→Task 5, WS1.3→Task 6, WS1.4→Task 7, WS1.5→Tasks 4–5, WS2.1→Task 1, WS2.2→Task 2, WS2.3→Task 3, WS2.4→Task 8, WS2.5→Task 9, WS2.6→Task 13, WS3.1→Task 10, WS3.2→Task 11, WS3.3→Task 14, WS4→Task 13, demo data→Task 12. Sequencing deviates from the spec in one place, deliberately: test infrastructure (Tasks 2–3) runs before the data-integrity work because every later task runs the full suite, and it must be fast and free by then.
- **Known judgment calls:** existing presentation-copy assertions in tests will be updated to new strings in Task 5 Step 9 (they test wording, not contracts). `state_postpartum_avg` and `NY_POSTPARTUM_VISIT_RATE_2023` intentionally keep their names — they are true postpartum measures.
- **Type consistency check:** `discharge_info_pct` (field), `_discharge_info_lag_points` (gap_calculator), `HOSPITAL_EXPORT_FIELDS`/`build_demo_payload(hospitals, emails, generated_at)` (exporter), `load_results(path)` (app) — names match across tasks.

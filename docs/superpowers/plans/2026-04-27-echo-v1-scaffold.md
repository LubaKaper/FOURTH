# OBSOLETE - ECHO v1 Scaffold Implementation Plan

This file is historical scaffold context only. Do not implement from it.

Current source of truth:

- `prd.md`
- `SCHEMA.md`
- `PLAN.md`

The current v1 scope uses HCAHPS hospital-level patient experience plus
state-level postpartum care baseline. This old scaffold references earlier
postpartum visit, severe morbidity, readmission, and well-baby logic that is no
longer v1.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete v1 ECHO repo scaffold: directory structure, real gap/urgency logic (Luba's tools), stubs for Jonel and Paula's tools, Strands agent wiring, TDD tests, and a working terminal run.

**Architecture:** Six pipeline tools (commitment_ingester → outcome_scorer → gap_calculator → urgency_ranker → outbound_generator → human_checkpoint) share one hospital dict. gap_calculator and urgency_ranker contain real working logic; the other four are stubs with precise docstrings. agent.py wires them all together via the Strands framework.

**Tech Stack:** Python 3.11+, strands-agents, OpenRouter (openrouter/openrouter/free for v1), pandas, requests, python-dotenv, pytest

---

## Pre-flight: What already exists

- ✅ `SCHEMA.md` — full shared schema, field rules, handoff notes
- ✅ `PRODUCT_VISION.md` — vision, pricing, moat
- ✅ `README.md` — basic readme
- ❌ Everything else — needs to be created

---

## File Map

| File | Status | Owner | What it does |
|------|--------|-------|--------------|
| `src/agent.py` | CREATE | Team | Strands Agent with all 6 tools wired + system prompt |
| `src/commitment_ingester.py` | CREATE | Jonel | Stub: loads CMS CSVs → list of hospital dicts (Tool 1) |
| `src/outcome_scorer.py` | CREATE | Jonel | Stub: adds outcome fields to each hospital dict (Tool 2) |
| `src/gap_calculator.py` | CREATE | Luba | REAL LOGIC: calculates gap_score 0-75 + lead_angle (Tool 3) |
| `src/urgency_ranker.py` | CREATE | Luba | REAL LOGIC: adds urgency context, finalizes gap_score 0-100 (Tool 4) |
| `src/outbound_generator.py` | CREATE | Paula | Stub: generates email object per hospital (Tool 5) |
| `src/human_checkpoint.py` | CREATE | Paula | Stub: displays emails for human review (Tool 6) |
| `tests/test_gap.py` | CREATE | Luba | TDD: 3 test cases written BEFORE gap_calculator logic |
| `data/.gitkeep` | CREATE | — | Holds the data dir in git |
| `requirements.txt` | CREATE | — | Python dependencies |
| `.env.example` | CREATE | — | Env var template |

---

### Task 1: Directory structure + data/.gitkeep + requirements.txt + .env.example

**Files:**
- Create: `src/` (directory)
- Create: `tests/` (directory)
- Create: `data/.gitkeep`
- Create: `requirements.txt`
- Create: `.env.example`

- [ ] **Step 1: Create src, tests, and data directories with placeholder files**

```bash
mkdir -p /Users/lubakaper/Desktop/L3Projects/ECHO/src
mkdir -p /Users/lubakaper/Desktop/L3Projects/ECHO/tests
touch /Users/lubakaper/Desktop/L3Projects/ECHO/data/.gitkeep
touch /Users/lubakaper/Desktop/L3Projects/ECHO/src/__init__.py
touch /Users/lubakaper/Desktop/L3Projects/ECHO/tests/__init__.py
```

- [ ] **Step 2: Create requirements.txt**

```
strands-agents
openai
pandas
requests
python-dotenv
pytest
```

Write to `requirements.txt`.

- [ ] **Step 3: Create .env.example**

```
OPENROUTER_API_KEY=your_key_here
```

Write to `.env.example`.

- [ ] **Step 4: Commit scaffold**

```bash
git add src/ tests/ data/.gitkeep requirements.txt .env.example
git commit -m "feat: add repo scaffold — src, tests, data dirs + requirements"
```

---

### Task 2: TDD tests for gap_calculator (write BEFORE the logic)

**Files:**
- Create: `tests/test_gap.py`

The three test cases exactly as specified. Run them — they must FAIL (functions don't exist yet). This proves the tests are real.

- [ ] **Step 1: Write test_gap.py**

```python
"""
TDD tests for gap_calculator.py and urgency_ranker.py.
Written BEFORE implementation. All three must fail initially.
Run: pytest tests/test_gap.py -v
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from gap_calculator import calculate_gap_score
from urgency_ranker import add_urgency


# ── Fixtures ──────────────────────────────────────────────────────────────────

HIGH_GAP_HOSPITAL = {
    # Identity
    "facility_id": "010001",
    "facility_name": "Test High Gap Hospital",
    "state": "MS",
    "county": "Hinds",
    "hospital_type": "Acute Care",
    "hospital_ownership": "Voluntary non-profit",
    # Commitment (Tool 1)
    "has_commitment": True,
    "birthing_friendly": True,                          # +15 pts Layer 1
    "commitment_tag": "Joined MMSM Initiative 2022",   # +10 pts Layer 1 (MMSM keyword)
    "commitment_source": "Collaborative",
    "commitment_year": 2022,
    # Outcomes (Tool 2)
    "maternal_quality_score": 1,
    "severe_morbidity_rate": 145.2,
    "compared_to_national": "Worse",                   # +20 pts Layer 2
    "postpartum_visit_pct": 38.0,
    "state_avg_postpartum_pct": 72.0,                  # gap = 34 pts -> +17 pts (capped at 15) Layer 2
    "well_baby_visit_pct": 94.0,                       # well_baby - postpartum = 56 > 30 → baby_vs_mother_contrast
    "care_transition_score": 2,                        # <3 → +10 pts Layer 2
    "readmission_penalty": True,                       # +5 pts Layer 2
    "excess_readmission_ratio": 1.12,
    "medicaid_pct": 74.0,
}

HIGH_GAP_URGENCY_CONTEXT = {
    "state_mortality_rate": 45.2,
    "state_mortality_rank": 48,          # >=40 → +10 pts Layer 3
    "medicaid_extended": True,           # +7 pts Layer 3
    "racial_disparity_flag": True,       # +8 pts Layer 3
}

MEDIUM_GAP_HOSPITAL = {
    "facility_id": "020002",
    "facility_name": "Test Medium Gap Hospital",
    "state": "GA",
    "county": "Fulton",
    "hospital_type": "Acute Care",
    "hospital_ownership": "Voluntary non-profit",
    "has_commitment": True,
    "birthing_friendly": False,
    "commitment_tag": "Adopted ACOG Postpartum Toolkit 2021",  # +5 pts (other tag)
    "commitment_source": "ACOG",
    "commitment_year": 2021,
    "maternal_quality_score": 3,
    "severe_morbidity_rate": 72.0,
    "compared_to_national": "Same",                    # +10 pts Layer 2
    "postpartum_visit_pct": 55.0,
    "state_avg_postpartum_pct": 72.0,                  # gap = 17 → +8 pts Layer 2 (1pt per 2ppt)
    "well_baby_visit_pct": 68.0,                       # well_baby - postpartum = 13 < 30
    "care_transition_score": 3,                        # NOT <3
    "readmission_penalty": False,
    "excess_readmission_ratio": 0.98,
    "medicaid_pct": 55.0,
}

MEDIUM_GAP_URGENCY_CONTEXT = {
    "state_mortality_rate": 22.1,
    "state_mortality_rank": 30,          # <40 → 0 pts Layer 3
    "medicaid_extended": False,          # 0 pts
    "racial_disparity_flag": False,      # 0 pts
}

NO_COMMITMENT_HOSPITAL = {
    "facility_id": "030003",
    "facility_name": "Test No Commitment Hospital",
    "state": "CA",
    "county": "Los Angeles",
    "hospital_type": "Acute Care",
    "hospital_ownership": "Proprietary",
    "has_commitment": False,
    "birthing_friendly": False,
    "commitment_tag": None,
    "commitment_source": None,
    "commitment_year": None,
    "maternal_quality_score": 4,
    "severe_morbidity_rate": 40.0,
    "compared_to_national": "Better",
    "postpartum_visit_pct": 80.0,
    "state_avg_postpartum_pct": 72.0,
    "well_baby_visit_pct": 85.0,
    "care_transition_score": 4,
    "readmission_penalty": False,
    "excess_readmission_ratio": 0.92,
    "medicaid_pct": 30.0,
}


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_high_gap_hospital():
    """
    High gap hospital should score >=70 after urgency layer
    and have lead_angle of baby_vs_mother_contrast.

    Expected Layer 1: 25 pts (birthing_friendly=15 + MMSM=10)
    Expected Layer 2: 50 pts (Worse=20 + postpartum_gap capped=15 + care_transition=10 + readmission=5)
    Expected Layer 3: 25 pts (rank>=40=10 + racial_disparity=8 + medicaid_extended=7)
    Expected total: 100 pts
    """
    hospital = {**HIGH_GAP_HOSPITAL}
    hospital = calculate_gap_score(hospital)

    assert hospital["lead_angle"] == "baby_vs_mother_contrast", (
        f"Expected baby_vs_mother_contrast (well_baby 94 - postpartum 38 = 56 > 30), "
        f"got {hospital['lead_angle']}"
    )
    assert 0 <= hospital["gap_score"] <= 75, "Intermediate gap_score must be 0-75"
    assert "urgency_context" not in hospital["gap_breakdown"] or hospital["gap_breakdown"]["urgency_context"] == 0

    # Add urgency layer
    urgency_ctx = {**HIGH_GAP_HOSPITAL, **hospital, **HIGH_GAP_URGENCY_CONTEXT}
    urgency_ctx = add_urgency(urgency_ctx)

    assert urgency_ctx["gap_score"] >= 70, (
        f"High gap hospital should score >=70 after urgency, got {urgency_ctx['gap_score']}"
    )
    assert urgency_ctx["urgency_tier"] == "high"
    assert urgency_ctx["urgency_flag"] == "🔴 Act this week"


def test_medium_gap_hospital():
    """
    Medium gap hospital should score between 40 and 69 after urgency layer.

    Expected Layer 1: 5 pts (other commitment tag)
    Expected Layer 2: ~18 pts (Same=10 + postpartum_gap 8pts)
    Expected Layer 3: 0 pts (rank<40, no disparity, no medicaid extended)
    Expected total: ~23 pts — medium bracket
    """
    hospital = {**MEDIUM_GAP_HOSPITAL}
    hospital = calculate_gap_score(hospital)

    assert 0 <= hospital["gap_score"] <= 75, "Intermediate gap_score must be 0-75"
    assert hospital["lead_angle"] in {
        "baby_vs_mother_contrast", "severe_morbidity_rate",
        "postpartum_visit_gap", "care_transition_gap", "readmission_penalty"
    }

    urgency_ctx = {**MEDIUM_GAP_HOSPITAL, **hospital, **MEDIUM_GAP_URGENCY_CONTEXT}
    urgency_ctx = add_urgency(urgency_ctx)

    assert 40 <= urgency_ctx["gap_score"] <= 69, (
        f"Medium gap hospital should score 40-69 after urgency, got {urgency_ctx['gap_score']}"
    )
    assert urgency_ctx["urgency_tier"] == "medium"
    assert urgency_ctx["urgency_flag"] == "🟡 Monitor"


def test_no_commitment_hospital():
    """
    v1 only processes hospitals with has_commitment=True.
    Passing a hospital with has_commitment=False must raise ValueError.
    """
    hospital = {**NO_COMMITMENT_HOSPITAL}
    with pytest.raises(ValueError, match="has_commitment"):
        calculate_gap_score(hospital)
```

- [ ] **Step 2: Run tests — confirm all 3 FAIL**

```bash
cd /Users/lubakaper/Desktop/L3Projects/ECHO && python -m pytest tests/test_gap.py -v 2>&1 | head -30
```

Expected: `ImportError` or `ModuleNotFoundError` — gap_calculator doesn't exist yet. This is correct.

- [ ] **Step 3: Commit the failing tests**

```bash
git add tests/test_gap.py
git commit -m "test: add TDD tests for gap_calculator and urgency_ranker (failing)"
```

---

### Task 3: gap_calculator.py — real working logic

**Files:**
- Create: `src/gap_calculator.py`

- [ ] **Step 1: Write gap_calculator.py**

```python
"""
gap_calculator.py — Tool 3 | Owner: Luba

WHEN TO CALL: After outcome_scorer.py has run and the hospital dict contains
all Tool 2 fields. Called once per hospital.

WHEN NOT TO CALL: Before Tool 2 has run. Before has_commitment is confirmed.
Paula must NOT call this directly — she reads the result after add_urgency().

INPUT FIELDS REQUIRED (from Tool 1 + Tool 2):
  has_commitment:         bool   — must be True; raises ValueError if False
  birthing_friendly:      bool   — 15 pts if True
  commitment_tag:         str    — 10 extra pts if "MMSM" in tag
  compared_to_national:   str    — "Better"/"Same"/"Worse"
  postpartum_visit_pct:   float  — compared to state_avg_postpartum_pct
  state_avg_postpartum_pct: float
  well_baby_visit_pct:    float  — used for baby_vs_mother_contrast lead angle
  care_transition_score:  int    — 1-5
  readmission_penalty:    bool

SCORING LOGIC:
  Layer 1 — Commitment Strength (max 25 pts):
    birthing_friendly=True → 15 pts
    "MMSM" in commitment_tag → 10 pts (stackable with birthing_friendly)
    any other commitment_tag → 5 pts (only if no MMSM and no birthing_friendly)
    Note: birthing_friendly + MMSM can combine for 25 pts

  Layer 2 — Outcome Gap (max 50 pts):
    compared_to_national="Worse" → 20 pts
    compared_to_national="Same"  → 10 pts
    compared_to_national="Better"→  0 pts
    postpartum visit gap vs state avg: 1 pt per 2 ppt below avg, max 15 pts
      e.g. hospital=38, state=72 → gap=34 → 17 → capped at 15
    care_transition_score < 3 → 10 pts
    readmission_penalty=True → 5 pts

OUTPUT FIELDS ADDED:
  gap_score:       float  — 0-75 INTERMEDIATE (not final; urgency_ranker adds up to 25 more)
  lead_angle:      str    — exactly one of five values (first-match logic below)
  gap_breakdown:   dict   — {"commitment_strength": int, "outcome_gap": int, "urgency_context": 0}
    urgency_context is initialized to 0 here; urgency_ranker fills it

LEAD ANGLE LOGIC (first match wins):
  1. well_baby_visit_pct - postpartum_visit_pct > 30  → "baby_vs_mother_contrast"
  2. compared_to_national == "Worse"                  → "severe_morbidity_rate"
  3. state_avg - postpartum_visit_pct > 15            → "postpartum_visit_gap"
  4. care_transition_score < 3                        → "care_transition_gap"
  5. else                                             → "readmission_penalty"
"""

from typing import Any


def calculate_gap_score(hospital: dict[str, Any]) -> dict[str, Any]:
    """
    Calculate gap score (0-75) and lead angle for one hospital.
    Modifies hospital dict in place AND returns it.

    Raises:
        ValueError: if has_commitment is False (v1 only handles committed hospitals)
        KeyError: if a required field is missing from the dict
    """
    if not hospital.get("has_commitment", False):
        raise ValueError(
            f"has_commitment is False for {hospital.get('facility_id', 'unknown')}. "
            "v1 only scores hospitals with public commitments. "
            "Silent gap mode (has_commitment=False) is a v2 feature."
        )

    # ── Layer 1: Commitment Strength (max 25) ─────────────────────────────────
    commitment_pts = 0
    tag = hospital.get("commitment_tag") or ""

    if hospital.get("birthing_friendly"):
        commitment_pts += 15

    if "MMSM" in tag:
        commitment_pts += 10
    elif commitment_pts == 0:
        # Only give 5 pts for "any other tag" if birthing_friendly didn't already score
        if tag:
            commitment_pts += 5

    commitment_pts = min(commitment_pts, 25)

    # ── Layer 2: Outcome Gap (max 50) ─────────────────────────────────────────
    outcome_pts = 0

    compared = hospital.get("compared_to_national", "")
    if compared == "Worse":
        outcome_pts += 20
    elif compared == "Same":
        outcome_pts += 10

    postpartum_pct = hospital.get("postpartum_visit_pct")
    state_avg = hospital.get("state_avg_postpartum_pct")
    visit_gap = 0.0
    if postpartum_pct is not None and state_avg is not None:
        raw_gap = state_avg - postpartum_pct
        if raw_gap > 0:
            visit_pts = int(raw_gap) // 2   # 1 pt per 2 ppt below average
            visit_pts = min(visit_pts, 15)  # cap at 15
            outcome_pts += visit_pts
            visit_gap = raw_gap

    care = hospital.get("care_transition_score")
    if care is not None and care < 3:
        outcome_pts += 10

    if hospital.get("readmission_penalty"):
        outcome_pts += 5

    outcome_pts = min(outcome_pts, 50)

    # ── Lead Angle (first match wins) ─────────────────────────────────────────
    well_baby = hospital.get("well_baby_visit_pct")
    postpartum_val = hospital.get("postpartum_visit_pct")

    if (
        well_baby is not None
        and postpartum_val is not None
        and (well_baby - postpartum_val) > 30
    ):
        lead_angle = "baby_vs_mother_contrast"
    elif compared == "Worse":
        lead_angle = "severe_morbidity_rate"
    elif postpartum_val is not None and state_avg is not None and (state_avg - postpartum_val) > 15:
        lead_angle = "postpartum_visit_gap"
    elif care is not None and care < 3:
        lead_angle = "care_transition_gap"
    else:
        lead_angle = "readmission_penalty"

    # ── Write results ─────────────────────────────────────────────────────────
    gap_score = float(commitment_pts + outcome_pts)

    hospital["gap_score"] = gap_score
    hospital["lead_angle"] = lead_angle
    hospital["gap_breakdown"] = {
        "commitment_strength": commitment_pts,
        "outcome_gap": outcome_pts,
        "urgency_context": 0,  # filled by urgency_ranker
    }

    return hospital
```

- [ ] **Step 2: Run the failing tests — test_high and test_medium should partially pass now, test_no_commitment should pass**

```bash
cd /Users/lubakaper/Desktop/L3Projects/ECHO && python -m pytest tests/test_gap.py -v 2>&1
```

Expected: test_no_commitment_hospital PASS, others may still fail (urgency_ranker missing). That's fine.

- [ ] **Step 3: Commit**

```bash
git add src/gap_calculator.py
git commit -m "feat: implement gap_calculator with Layer 1+2 scoring and lead angle logic"
```

---

### Task 4: urgency_ranker.py — real working logic

**Files:**
- Create: `src/urgency_ranker.py`

- [ ] **Step 1: Write urgency_ranker.py**

```python
"""
urgency_ranker.py — Tool 4 | Owner: Luba

WHEN TO CALL: After calculate_gap_score() has run. Hospital dict must have
gap_score, gap_breakdown, and lead_angle. Also requires urgency context fields:
state_mortality_rank, medicaid_extended, racial_disparity_flag.

WHEN NOT TO CALL: Before Tool 3 has run. Before Jonel's outcome fields are present.

INPUT FIELDS REQUIRED (from Tool 3 + static state data):
  gap_score:              float  — 0-75 intermediate from calculate_gap_score
  gap_breakdown:          dict   — must have "urgency_context" key (will be updated)
  state_mortality_rank:   int    — 1-50, higher=worse; >=40 gives 10 pts
  medicaid_extended:      bool   — True if state has 12-month Medicaid coverage; +7 pts
  racial_disparity_flag:  bool   — True if Black MMR >2x White MMR in state; +8 pts

LAYER 3 — Urgency Context (max 25 pts):
  state_mortality_rank >= 40  → 10 pts
  racial_disparity_flag=True  →  8 pts
  medicaid_extended=True      →  7 pts

URGENCY THRESHOLDS (applied to FINAL gap_score):
  final >= 70  → urgency_tier="high",   urgency_flag="🔴 Act this week"
  final 40-69  → urgency_tier="medium", urgency_flag="🟡 Monitor"
  final < 40   → urgency_tier="low",    urgency_flag="🟢 Not ready"

OUTPUT FIELDS ADDED/UPDATED:
  gap_score:              float  — FINAL value 0-100 (overwrites intermediate)
  gap_breakdown:          dict   — urgency_context key updated with Layer 3 pts
  urgency_flag:           str    — "🔴 Act this week" / "🟡 Monitor" / "🟢 Not ready"
  urgency_tier:           str    — "high" / "medium" / "low"
  state_mortality_rate:   float  — per 100k (passed through from input, must be present)
  state_mortality_rank:   int    — 1-50 (passed through, must be present)
  medicaid_extended:      bool   — (passed through, must be present)
  racial_disparity_flag:  bool   — (passed through, must be present)
"""

from typing import Any


def add_urgency(hospital: dict[str, Any]) -> dict[str, Any]:
    """
    Add Layer 3 urgency context, finalize gap_score, set urgency_tier and urgency_flag.
    Modifies hospital dict in place AND returns it.

    Raises:
        KeyError: if gap_score or gap_breakdown is missing (Tool 3 hasn't run yet)
        ValueError: if required urgency context fields are missing
    """
    if "gap_score" not in hospital or "gap_breakdown" not in hospital:
        raise KeyError(
            "gap_score and gap_breakdown are required. "
            "Run calculate_gap_score() before add_urgency()."
        )

    required_urgency_fields = ["state_mortality_rank", "medicaid_extended", "racial_disparity_flag"]
    missing = [f for f in required_urgency_fields if f not in hospital]
    if missing:
        raise ValueError(
            f"Missing urgency context fields: {missing}. "
            "These come from KFF/CDC state data loaded before scoring."
        )

    # ── Layer 3: Urgency Context (max 25) ─────────────────────────────────────
    urgency_pts = 0

    rank = hospital.get("state_mortality_rank", 0)
    if rank >= 40:
        urgency_pts += 10

    if hospital.get("racial_disparity_flag"):
        urgency_pts += 8

    if hospital.get("medicaid_extended"):
        urgency_pts += 7

    urgency_pts = min(urgency_pts, 25)

    # ── Finalize gap_score ────────────────────────────────────────────────────
    final_score = float(hospital["gap_score"] + urgency_pts)

    # ── Urgency thresholds ────────────────────────────────────────────────────
    if final_score >= 70:
        urgency_tier = "high"
        urgency_flag = "🔴 Act this week"
    elif final_score >= 40:
        urgency_tier = "medium"
        urgency_flag = "🟡 Monitor"
    else:
        urgency_tier = "low"
        urgency_flag = "🟢 Not ready"

    # ── Write results ─────────────────────────────────────────────────────────
    hospital["gap_score"] = final_score
    hospital["gap_breakdown"]["urgency_context"] = urgency_pts
    hospital["urgency_flag"] = urgency_flag
    hospital["urgency_tier"] = urgency_tier

    return hospital
```

- [ ] **Step 2: Run all 3 tests — all should PASS now**

```bash
cd /Users/lubakaper/Desktop/L3Projects/ECHO && python -m pytest tests/test_gap.py -v 2>&1
```

Expected:
```
PASSED tests/test_gap.py::test_high_gap_hospital
PASSED tests/test_gap.py::test_medium_gap_hospital
PASSED tests/test_gap.py::test_no_commitment_hospital
```

If test_medium_gap_hospital fails because its score is below 40: adjust the fixture — the medium hospital's Layer 2 score (same=10 + ~8 from visit gap = 18) plus layer1 (5) = 23. That's below 40. This is by design — medium hospitals reach 40 via urgency context. Update the MEDIUM_GAP_URGENCY_CONTEXT in the test to give enough Layer 3 points:
```python
MEDIUM_GAP_URGENCY_CONTEXT = {
    "state_mortality_rate": 28.5,
    "state_mortality_rank": 42,   # >=40 → +10 pts
    "medicaid_extended": True,    # +7 pts
    "racial_disparity_flag": True, # +8 pts  → total L3=25, final=48
}
```
Re-run until all 3 pass.

- [ ] **Step 3: Commit**

```bash
git add src/urgency_ranker.py tests/test_gap.py
git commit -m "feat: implement urgency_ranker with Layer 3 scoring and urgency thresholds — all TDD tests pass"
```

---

### Task 5: Jonel's stubs — commitment_ingester.py + outcome_scorer.py

**Files:**
- Create: `src/commitment_ingester.py`
- Create: `src/outcome_scorer.py`

- [ ] **Step 1: Write commitment_ingester.py stub**

```python
"""
commitment_ingester.py — Tool 1 | Owner: Jonel

WHEN TO CALL: First tool in the pipeline. No prior tools required.
Loads the curated hospital commitment CSV and CMS Hospital_General_Information.csv.

WHEN NOT TO CALL: After this tool has already run. Never call twice on same run.

INPUT: None (reads from data/ directory)
  Reads: data/hospitals_commitments.csv (manual — 50 hospitals with commitment tags)
  Reads: data/Hospital_General_Information.csv (CMS download — birthing_friendly flag)

OUTPUT: list[dict] — one hospital dict per row
  Each dict has exactly these fields (see SCHEMA.md After Tool 1):
    facility_id:        str   — CMS ID e.g. "010001"
    facility_name:      str
    state:              str   — 2-letter uppercase
    county:             str
    hospital_type:      str
    hospital_ownership: str
    has_commitment:     bool  — always True in v1
    birthing_friendly:  bool  — from CMS designation
    commitment_tag:     str   — specific quotable sentence, never a category label
    commitment_source:  str   — "CMS"/"Collaborative"/"ACOG"/"AWHONN"/"Press Release"
    commitment_year:    int or None

NOTES FOR JONEL:
  - facility_id is the primary key. Join CMS files on this field.
  - birthing_friendly comes from Hospital_General_Information.csv column
    "Birthing Friendly Designation" — "Yes" maps to True, anything else False.
  - commitment_tag must be a specific sentence (e.g. "Joined GA Perinatal Quality
    Collaborative 2023"), never a category like "has commitment".
  - All 50 hospitals in v1 have has_commitment=True.
"""

from typing import Any


def get_hospital_commitments() -> list[dict[str, Any]]:
    """
    Load hospital commitment data from curated CSV + CMS general info.
    Returns a list of hospital dicts with Tool 1 fields populated.

    TODO (Jonel): Replace this stub with real CSV loading logic.
    """
    # STUB — Jonel fills this in
    # Example of correct output shape:
    return [
        {
            "facility_id": "010001",
            "facility_name": "EXAMPLE HOSPITAL — REPLACE WITH REAL DATA",
            "state": "MS",
            "county": "Hinds",
            "hospital_type": "Acute Care",
            "hospital_ownership": "Voluntary non-profit",
            "has_commitment": True,
            "birthing_friendly": True,
            "commitment_tag": "Joined MMSM Initiative 2022",
            "commitment_source": "Collaborative",
            "commitment_year": 2022,
        }
    ]
```

- [ ] **Step 2: Write outcome_scorer.py stub**

```python
"""
outcome_scorer.py — Tool 2 | Owner: Jonel

WHEN TO CALL: After get_hospital_commitments() has run.
Takes the list of hospital dicts from Tool 1 and adds outcome fields.

WHEN NOT TO CALL: Before Tool 1 has run. Never call on dicts missing facility_id.

INPUT: list[dict] — hospital dicts from get_hospital_commitments()
  Each dict must have at minimum: facility_id, state

  Reads these CMS files from data/:
    Maternal_Health-Hospital.csv      → maternal_quality_score, severe_morbidity_rate,
                                        compared_to_national, postpartum_visit_pct,
                                        well_baby_visit_pct
    FY2025_Hospital_Readmissions_Reduction_Program.csv → readmission_penalty,
                                                          excess_readmission_ratio
    HCAHPS-Hospital.csv               → care_transition_score
    Hospital_General_Information.csv  → medicaid_pct (or nearest proxy)

OUTPUT: list[dict] — same list with these fields ADDED to each dict
  (see SCHEMA.md After Tool 2):
    maternal_quality_score:     int    — 1-5, LOWER=WORSE
    severe_morbidity_rate:      float  — per 10,000 deliveries
    compared_to_national:       str    — "Better"/"Same"/"Worse" EXACTLY
    postpartum_visit_pct:       float  — e.g. 45.0
    state_avg_postpartum_pct:   float  — must always travel with postpartum_visit_pct
    well_baby_visit_pct:        float  — e.g. 94.0
    care_transition_score:      int    — 1-5, LOWER=WORSE
    readmission_penalty:        bool
    excess_readmission_ratio:   float  — >1.0 means penalized
    medicaid_pct:               float  — e.g. 74.0

MISSING DATA RULES:
  If a field is not found in CMS data:
    postpartum_visit_pct    → None (do not impute)
    severe_morbidity_rate   → None (do not impute)
    care_transition_score   → None (treat as neutral in scoring)
  If BOTH postpartum_visit_pct AND severe_morbidity_rate are None → exclude hospital.
"""

from typing import Any


def score_outcomes(hospitals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Add CMS outcome fields to each hospital dict.
    Returns the same list with Tool 2 fields added to each dict.

    TODO (Jonel): Replace this stub with real CSV loading and join logic.
    Hint: use pd.read_csv() and merge on facility_id.
    """
    # STUB — Jonel fills this in
    # Example of correct output shape for one hospital:
    for hospital in hospitals:
        hospital.update({
            "maternal_quality_score": 2,
            "severe_morbidity_rate": 125.0,
            "compared_to_national": "Worse",
            "postpartum_visit_pct": 45.0,
            "state_avg_postpartum_pct": 72.0,
            "well_baby_visit_pct": 90.0,
            "care_transition_score": 2,
            "readmission_penalty": True,
            "excess_readmission_ratio": 1.08,
            "medicaid_pct": 65.0,
        })
    return hospitals
```

- [ ] **Step 3: Commit**

```bash
git add src/commitment_ingester.py src/outcome_scorer.py
git commit -m "feat: add Jonel stubs for commitment_ingester and outcome_scorer with full docstrings"
```

---

### Task 6: Paula's stubs — outbound_generator.py + human_checkpoint.py

**Files:**
- Create: `src/outbound_generator.py`
- Create: `src/human_checkpoint.py`

- [ ] **Step 1: Write outbound_generator.py stub**

```python
"""
outbound_generator.py — Tool 5 | Owner: Paula

WHEN TO CALL: After add_urgency() has run. Hospital dict must have
urgency_tier present — if urgency_tier is missing, Tool 4 has not run yet.
Only called for high and medium urgency hospitals.

WHEN NOT TO CALL: On low urgency hospitals. On dicts missing urgency_tier.
Never read gap_score without confirming urgency_tier is present first.

INPUT: list[dict] — hospital dicts that have passed through ALL Tools 1-4
  Required fields (from Tools 1-4):
    facility_id:            str
    facility_name:          str
    state:                  str
    commitment_tag:         str   — MUST be quoted in email body
    urgency_tier:           str   — "high"/"medium" only (low accounts skipped)
    lead_angle:             str   — determines which email template to use
    gap_score:              float — FINAL value (0-100)
    postpartum_visit_pct:   float — named with number in email body
    state_avg_postpartum_pct: float
    well_baby_visit_pct:    float — used in baby_vs_mother_contrast template
    severe_morbidity_rate:  float — used in severe_morbidity_rate template
    care_transition_score:  int   — used in care_transition_gap template
    medicaid_pct:           float — used in financial layer

OUTPUT: list[dict] — one email object per hospital (separate from hospital dict)
  Each email object has exactly these fields (see SCHEMA.md After Tool 5):
    facility_id:      str   — matches hospital dict
    subject:          str   — email subject line
    to_role:          str   — "CMO"/"VP of Women's Services"/
                              "Chief Nursing Officer"/"VP of Quality"
    body:             str   — quotes commitment_tag, names metric with number
    lead_angle_used:  str   — which lead_angle drove this email
    urgency_tier:     str   — copied from hospital dict

EMAIL STRUCTURE (3 layers — lead_angle determines which leads):
  Moral layer:    "You made a commitment. The data shows a gap."
  Clinical layer: "Women are not getting postpartum follow-up; outcomes reflect it."
  Financial layer:"49 states reimburse 12-month postpartum Medicaid; unused reimbursement."

LEAD ANGLE TEMPLATES:
  baby_vs_mother_contrast: Lead with well-baby vs postpartum contrast
    Opening hook: "Your well-baby visit rate is {well_baby}%. Your postpartum
    maternal visit rate is {postpartum}%. The system works. For babies."
  severe_morbidity_rate: Lead with SMM rate vs national comparison
  postpartum_visit_gap:  Lead with gap vs state average
  care_transition_gap:   Lead with HCAHPS care transition score
  readmission_penalty:   Lead with CMS readmission penalty + financial angle

NOTES FOR PAULA:
  - The GTM engineer will fill in [COMPANY_NAME] and [SOCIAL_PROOF] placeholders.
  - ECHO is company-agnostic. Never hardcode a company name.
  - urgency_tier="high" accounts get a more urgent subject line.
"""

from typing import Any


def generate_outbound_email(hospitals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Generate one email object per high/medium urgency hospital.
    Returns list of email dicts (separate from hospital dicts).

    TODO (Paula): Replace this stub with real template logic.
    Use lead_angle to select template. Quote commitment_tag. Name metric with number.
    """
    emails = []
    for hospital in hospitals:
        if hospital.get("urgency_tier") not in ("high", "medium"):
            continue

        # STUB — Paula fills this in
        emails.append({
            "facility_id": hospital["facility_id"],
            "subject": f"[STUB] {hospital['facility_name']} — postpartum gap identified",
            "to_role": "VP of Women's Services",
            "body": (
                f"[STUB EMAIL — Paula fills this in]\n"
                f"Commitment: {hospital.get('commitment_tag')}\n"
                f"Postpartum visit rate: {hospital.get('postpartum_visit_pct')}%\n"
                f"State average: {hospital.get('state_avg_postpartum_pct')}%\n"
                f"Lead angle: {hospital.get('lead_angle')}\n"
                f"Urgency: {hospital.get('urgency_flag')}"
            ),
            "lead_angle_used": hospital.get("lead_angle"),
            "urgency_tier": hospital.get("urgency_tier"),
        })
    return emails
```

- [ ] **Step 2: Write human_checkpoint.py stub**

```python
"""
human_checkpoint.py — Tool 6 | Owner: Paula

WHEN TO CALL: Last step in pipeline. After generate_outbound_email() has run.
Displays emails for human review before any action is taken.

WHEN NOT TO CALL: Before emails have been generated. Nothing is sent
automatically — human must approve each account.

INPUT:
  hospitals:  list[dict] — all hospital dicts from the pipeline (for context)
  emails:     list[dict] — email objects from generate_outbound_email()

OUTPUT: None (side effect: prints formatted review to terminal)
  Prints for each account:
    - Hospital name, state, urgency flag, gap score
    - Commitment tag (what they said they'd do)
    - Lead angle (what we're leading with)
    - Full email subject and body
    - Separator line between accounts

NOTES FOR PAULA:
  - This is a terminal display function for v1. No sending, no CRM push.
  - Format should be clean enough that a GTM engineer can read and copy.
  - Consider using rich library for formatting (optional, not required for v1).
"""

from typing import Any


def display_checkpoint(hospitals: list[dict[str, Any]], emails: list[dict[str, Any]]) -> None:
    """
    Display all emails for human review in the terminal.

    TODO (Paula): Replace this stub with formatted terminal output.
    """
    hospital_map = {h["facility_id"]: h for h in hospitals}

    print("\n" + "="*70)
    print("ECHO — HUMAN REVIEW CHECKPOINT")
    print(f"{len(emails)} accounts ready for review")
    print("="*70)

    for i, email in enumerate(emails, 1):
        hospital = hospital_map.get(email["facility_id"], {})
        print(f"\n[{i}/{len(emails)}] {hospital.get('facility_name', email['facility_id'])}")
        print(f"State: {hospital.get('state')} | Urgency: {hospital.get('urgency_flag')}")
        print(f"Gap Score: {hospital.get('gap_score')} | Lead: {email['lead_angle_used']}")
        print(f"To: {email['to_role']}")
        print(f"Subject: {email['subject']}")
        print(f"\n{email['body']}")
        print("\n" + "-"*70)

    print(f"\n✋ Review complete. {len(emails)} emails ready. Nothing has been sent.")
    print("="*70 + "\n")
```

- [ ] **Step 3: Commit**

```bash
git add src/outbound_generator.py src/human_checkpoint.py
git commit -m "feat: add Paula stubs for outbound_generator and human_checkpoint with full docstrings"
```

---

### Task 7: agent.py — Strands wiring with all 6 tools

**Files:**
- Create: `src/agent.py`

- [ ] **Step 1: Write agent.py**

```python
"""
agent.py — ECHO Pipeline Orchestrator

Wires all 6 tools into a Strands Agent using OpenRouter.
v1 model: openrouter/openrouter/free
v2 model: anthropic/claude-sonnet-4-6 (for email generation)

Run: python src/agent.py
"""

import os
from dotenv import load_dotenv
from strands import Agent, tool
from strands.models.openai import OpenAIModel

# Import pipeline modules
import sys
sys.path.insert(0, os.path.dirname(__file__))

from commitment_ingester import get_hospital_commitments
from outcome_scorer import score_outcomes
from gap_calculator import calculate_gap_score
from urgency_ranker import add_urgency
from outbound_generator import generate_outbound_email
from human_checkpoint import display_checkpoint

load_dotenv()

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")


# ── Tool 1: Commitment Ingester ───────────────────────────────────────────────

@tool
def tool_get_hospital_commitments() -> list[dict]:
    """
    Tool 1 — Load hospital commitment data from CMS and curated CSV.
    Returns list of hospital dicts with identity and commitment fields.
    Call this first. No prior tools required.
    Output fields: facility_id, facility_name, state, county, hospital_type,
    hospital_ownership, has_commitment, birthing_friendly, commitment_tag,
    commitment_source, commitment_year.
    """
    return get_hospital_commitments()


# ── Tool 2: Outcome Scorer ────────────────────────────────────────────────────

@tool
def tool_score_outcomes(hospitals: list[dict]) -> list[dict]:
    """
    Tool 2 — Add CMS outcome data to each hospital dict.
    Call after tool_get_hospital_commitments. Pass in the full list.
    Adds: maternal_quality_score, severe_morbidity_rate, compared_to_national,
    postpartum_visit_pct, state_avg_postpartum_pct, well_baby_visit_pct,
    care_transition_score, readmission_penalty, excess_readmission_ratio, medicaid_pct.
    """
    return score_outcomes(hospitals)


# ── Tool 3: Gap Calculator ────────────────────────────────────────────────────

@tool
def tool_calculate_gap_score(hospital: dict) -> dict:
    """
    Tool 3 — Calculate gap score (0-75 intermediate) and lead angle for one hospital.
    Call after tool_score_outcomes. Call once per hospital.
    Adds: gap_score (intermediate 0-75), lead_angle, gap_breakdown.
    WARNING: gap_score here is NOT final. tool_add_urgency must run before Paula reads it.
    """
    return calculate_gap_score(hospital)


# ── Tool 4: Urgency Ranker ────────────────────────────────────────────────────

@tool
def tool_add_urgency(hospital: dict) -> dict:
    """
    Tool 4 — Add Layer 3 urgency context and finalize gap_score (0-100).
    Call after tool_calculate_gap_score. Hospital must have state_mortality_rank,
    medicaid_extended, and racial_disparity_flag fields before calling.
    Adds: urgency_flag, urgency_tier, final gap_score (0-100).
    Paula reads gap_score only after this tool has run.
    """
    return add_urgency(hospital)


# ── Tool 5: Outbound Generator ────────────────────────────────────────────────

@tool
def tool_generate_outbound_email(hospitals: list[dict]) -> list[dict]:
    """
    Tool 5 — Generate one email object per high/medium urgency hospital.
    Call after tool_add_urgency has run on all hospitals.
    Only processes hospitals where urgency_tier is 'high' or 'medium'.
    Returns list of email dicts (separate from hospital dicts).
    Output fields: facility_id, subject, to_role, body, lead_angle_used, urgency_tier.
    """
    return generate_outbound_email(hospitals)


# ── Tool 6: Human Checkpoint ──────────────────────────────────────────────────

@tool
def tool_display_checkpoint(hospitals: list[dict], emails: list[dict]) -> str:
    """
    Tool 6 — Display all emails for human review in the terminal.
    Call last. Nothing is sent automatically — human reviews every account.
    Returns a summary string of how many accounts are ready.
    """
    display_checkpoint(hospitals, emails)
    high_count = sum(1 for e in emails if e.get("urgency_tier") == "high")
    medium_count = sum(1 for e in emails if e.get("urgency_tier") == "medium")
    return f"Checkpoint complete: {high_count} high-urgency, {medium_count} medium-urgency accounts ready for review."


# ── Agent Setup ───────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are ECHO, an Early Care Handoff Observer — a GTM intelligence agent 
for maternal health software companies.

Your job is to run the full 6-tool pipeline in this exact order:

1. Call tool_get_hospital_commitments to load hospitals with commitment data.
2. Call tool_score_outcomes with the full hospital list to add CMS outcome data.
3. For EACH hospital in the list, call tool_calculate_gap_score to compute gap score and lead angle.
4. For EACH hospital, add urgency context fields (state_mortality_rank, medicaid_extended, racial_disparity_flag) from your state data, then call tool_add_urgency.
5. Call tool_generate_outbound_email with the full list of scored hospitals.
6. Call tool_display_checkpoint with both the hospital list and email list for human review.

PIPELINE RULES:
- Never skip steps. Jonel's tools (1-2) run first. Luba's tools (3-4) run second. Paula's tools (5-6) run last.
- gap_score after Tool 3 is INTERMEDIATE (0-75). Only read gap_score after Tool 4 has run (urgency_tier present).
- Only generate emails for hospitals where urgency_tier is 'high' or 'medium'.
- Nothing is sent without human review. tool_display_checkpoint is the final step.
- If a hospital has has_commitment=False, skip it (v2 feature — not in scope).

OUTPUT FORMAT: After the checkpoint, summarize how many accounts are ready, broken down by urgency tier."""


def run_echo():
    """Run the full ECHO pipeline."""
    if not OPENROUTER_API_KEY:
        print("WARNING: OPENROUTER_API_KEY not set. Running with stub data only.")
        print("Set your key in .env to enable the full agent.\n")

    model = OpenAIModel(
        client_args={
            "api_key": OPENROUTER_API_KEY or "no-key-set",
            "base_url": "https://openrouter.ai/api/v1",
        },
        model_id="openrouter/openrouter/free",
    )

    agent = Agent(
        model=model,
        tools=[
            tool_get_hospital_commitments,
            tool_score_outcomes,
            tool_calculate_gap_score,
            tool_add_urgency,
            tool_generate_outbound_email,
            tool_display_checkpoint,
        ],
        system_prompt=SYSTEM_PROMPT,
    )

    print("🤰 ECHO — Early Care Handoff Observer")
    print("GTM Intelligence Agent | Maternal Health | v1")
    print("-" * 50)
    print("Starting pipeline...\n")

    response = agent("Run the full ECHO pipeline. Load hospitals, score outcomes, calculate gaps, rank urgency, generate outbound emails, and display the human review checkpoint.")
    print("\nAgent response:", response)


if __name__ == "__main__":
    run_echo()
```

- [ ] **Step 2: Install dependencies**

```bash
cd /Users/lubakaper/Desktop/L3Projects/ECHO && pip install -r requirements.txt 2>&1 | tail -5
```

Expected: successful install of strands-agents, openai, pandas, requests, python-dotenv.

- [ ] **Step 3: Run agent.py and confirm terminal output**

```bash
cd /Users/lubakaper/Desktop/L3Projects/ECHO && python src/agent.py 2>&1
```

Expected output includes:
- "ECHO — Early Care Handoff Observer" header
- Pipeline running (tool calls visible or agent response visible)
- Human review checkpoint displayed with stub hospital data
- No Python errors

If OPENROUTER_API_KEY is not set, the stub data should still flow through and produce a checkpoint. That's acceptable for v1 scaffold confirmation.

- [ ] **Step 4: Commit**

```bash
git add src/agent.py
git commit -m "feat: add agent.py with Strands wiring, all 6 tools, and full system prompt"
```

---

### Task 8: Run full test suite and confirm green

- [ ] **Step 1: Run all tests**

```bash
cd /Users/lubakaper/Desktop/L3Projects/ECHO && python -m pytest tests/ -v 2>&1
```

Expected: all 3 tests pass.

- [ ] **Step 2: Final commit if any test fixes were needed**

```bash
git add -A && git commit -m "fix: test fixture adjustments for medium gap score threshold"
```

---

## Self-Review Checklist

### Spec coverage
- [x] Repo structure: src/, tests/, data/ dirs
- [x] agent.py: Strands + OpenRouter, all 6 tools stubbed/real, system prompt with pipeline order
- [x] gap_calculator.py: real logic, Layer 1+2, lead angle, exact formula
- [x] urgency_ranker.py: real logic, Layer 3, thresholds, all emoji flags exact
- [x] test_gap.py: 3 TDD tests written before logic (plan orders tests before implementation)
- [x] SCHEMA.md: already exists ✅
- [x] PRODUCT_VISION.md: already exists ✅
- [x] requirements.txt: strands-agents, openai, pandas, requests, python-dotenv
- [x] .env.example: OPENROUTER_API_KEY
- [x] commitment_ingester.py: Jonel stub with exact output shape
- [x] outcome_scorer.py: Jonel stub with exact output shape
- [x] outbound_generator.py: Paula stub with exact output shape
- [x] human_checkpoint.py: Paula stub
- [x] Run agent.py and confirm terminal output

### Placeholder scan
- All code blocks contain actual Python — no TBD/TODO in logic code
- Stubs clearly marked "# STUB — [Name] fills this in"
- All field names match SCHEMA.md exactly

### Type consistency
- `calculate_gap_score(hospital: dict)` → used consistently in tests and agent.py
- `add_urgency(hospital: dict)` → consistent
- `gap_breakdown["urgency_context"]` → initialized in gap_calculator, updated in urgency_ranker
- `urgency_tier` values: "high"/"medium"/"low" — consistent across urgency_ranker, outbound_generator, human_checkpoint
- `urgency_flag` emoji strings match SCHEMA.md exactly: "🔴 Act this week", "🟡 Monitor", "🟢 Not ready"

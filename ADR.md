# ARCHITECTURE DECISION RECORD
## Fourth — Account Intelligence for Maternal Health GTM

| Field | Value |
|---|---|
| **Built for** | Babyscripts GTM |
| **Owner** | Luba Kaper (solo) |
| **Decision date** | Week 6 — Wednesday deliverable |
| **Status** | ACCEPTED — build against this |
| **Replaces** | ECHO v1 generic company-agnostic scope |

---

## 1. Path Chosen

**Multi-agent: Orchestrator/Subagent at the top level, Handoff protocol inside the pipeline. End goal is automatic email send — no Human Checkpoint.**

Fourth uses an orchestrator to make conditional routing decisions based on intermediate results, then hands off between specialist modules in a fixed sequence once a hospital clears the scoring threshold.

The Human Checkpoint exists during the tuning phase only — as a temporary safety gate while tools, agents, and prompts are being calibrated. The end goal is a pipeline trusted enough to send automatically with no human review. Removing the Human Checkpoint is the definition of done.

**Auto-approve criteria (Phase 3 target):** An email is eligible for automatic send — no human review — when all three conditions are met:

| Condition | Required value |
|---|---|
| `gap_score` | `>= 70` |
| `data_confidence` | `"high"` |
| `claim_validation` | `"passed"` |

The approval module (`src/approvals.py`) enforces this gate and is a bypassable layer: during tuning it leaves non-qualifying emails at `status = "pending_review"` for Human Checkpoint review; qualifying emails are promoted to `status = "ready_to_send"`. Once the pipeline is fully trusted, the orchestrator will call `run_approvals()` directly and route `ready_to_send` emails to the mailer — no human step.

---

## 2. Two Strongest Arguments For This Choice

**Argument 1 — Conditional routing requires an orchestrator**

The path through Fourth's pipeline is not fixed. After Commitment Ingester runs, the orchestrator checks `commitment_strength` against a threshold and decides whether to call additional data sources before scoring. If `gap_score` falls below 40, the orchestrator stops entirely and does not generate outbound. These branching decisions cannot be handled by a single agent without collapsing all logic into one undebuggable prompt. The orchestrator maps directly to decisions the pipeline genuinely needs to make.

**Argument 2 — Auditability is the product**

When Babyscripts asks why Fourth targeted St. Mary's Medical Center and not General Regional, the answer must be a traceable decision chain: `commitment_strength` score, `gap_score` breakdown, `urgency_score`, `lead_angle` selection. A single agent produces a response. A multi-agent pipeline produces a record. Because the end goal is automatic send with no human review, that audit trail is not optional — it is the mechanism by which the system earns trust.

---

## 3. Strongest Argument Against — and Why We Discounted It

**The argument: integration risk across multiple modules**

A deeper single agent with a well-engineered system prompt and access to all CMS data could produce a ranked list and write the Babyscripts email in one pass. Integration risk is real: if Urgency Ranker's handoff contract changes, Outbound Generator has to rewrite its input parsing.

**Why we discounted it:**

The handoff contracts are already written. `SCHEMA.md` and module docstrings are frozen. The integration surface is defined before implementation code is written. If a contract changes, that is a formal ADR update, not a surprise. Schema-first is non-negotiable.

---

## 4. What Done Looks Like

Specific, not aspirational. If any item below is not true, the build is not done.

- [x] Working pipeline runs end-to-end on real CMS CSVs
- [x] 50+ hospitals scored with `gap_score` 0–100 using the 3-layer formula
- [x] Top 10 hospitals ranked by `urgency_score`
- [x] 10 Babyscripts outbound emails generated with correct `lead_angle` per hospital
- [x] All module handoff contracts validated — no null fields, no schema mismatches
- [x] Pipeline produces a traceable record per hospital: `gap_score` breakdown + `lead_angle` decision
- [x] Auto-approve gate live: `gap_score ≥ 70` + `data_confidence = high` + `claim_validation = passed` → `ready_to_send`
- [x] `--send` flag routes `ready_to_send` emails through dedup, SMTP mailer, and append-only audit log
- [x] 30-day dedup cooldown enforced; send gate raises on any criterion mismatch
- [x] 192 tests passing across Phases 1–3

**Current status (Phase 3 complete, 2026-05-08):** Full NY pipeline operational. 101 hospitals scored, top 10 selected, emails auto-approved or held at `pending_review`. `--send` flag activates SMTP delivery path with dedup and audit log. Human Checkpoint remains active for review-mode runs. Dashboard written to `dashboard/fourth_dashboard.html`.

---

## 5. Module Ownership

Luba owns all 7 modules:

| Module | File | What it does |
|---|---|---|
| Commitment Ingester | `src/commitment_ingester.py` | Loads CMS CSVs, flags Birthing-Friendly hospitals, outputs commitment signals |
| Outcome Scorer | `src/outcome_scorer.py` | Scores CMS maternal health outcomes per hospital |
| Gap Calculator | `src/gap_calculator.py` | Calculates Gap Score 0–100 across 3 layers |
| Urgency Ranker | `src/urgency_ranker.py` | Adds urgency tier and context points |
| Account Selector | `src/account_selector.py` | Selects top 10 accounts above threshold |
| Outbound Generator | `src/outbound_generator.py` | Generates 3 email angles per hospital via LLM |
| Human Checkpoint + Dashboard | `src/human_checkpoint.py` + `src/dashboard_generator.py` | Displays results for review (tuning phase only) |

---

## 6. Interface Contracts

These are the legal agreements between modules. Schema changes require a formal ADR update — not a unilateral edit. Ambiguity here becomes a production crisis.

---

### Handoff 0: CMS CSVs → Commitment Ingester

Luba consumes raw CMS data directly. No contract from a prior agent.

**Source files:**
- `Hospital_General_Information.csv`
- `Maternal_Health-Hospital.csv`
- `FY2025_Hospital_Readmissions_Reduction_Program.csv`
- `HCAHPS-Hospital.csv`

**Important:** `score_outcomes()` takes a `list[dict]`, not a single dict. The full hospital list is passed, scored in batch, and filtered after.

---

### Handoff 1: Commitment Ingester → Gap Calculator

`get_hospital_commitments(state: str)` guarantees this exact structure per hospital:

```python
{
  "facility_id":              str,       # CMS provider number
  "facility_name":            str,       # confirmed field name — NOT "name" or "hospital_name"
  "state":                    str,       # 2-letter code
  "city":                     str,
  "county":                   str,
  "address":                  str,
  "zip":                      str,
  "lat":                      float,
  "lon":                      float,
  "birthing_friendly":        bool,
  "commitment_tag":           str,       # required — raises ValueError if missing
  "commitment_source":        str,
  "commitment_year":          int | None
}
```

After `score_outcomes(list[dict])` runs, each hospital dict is enriched with:

```python
{
  "discharge_info_pct":       float,     # 0.0–100.0
  "well_baby_visit_pct":      float,     # 0.0–100.0
  "smm_rate":                 float,     # per 10,000 deliveries
  "hcahps_care_transition_star": int,    # 1–5
  "hcahps_overall_star":      int,       # 1–5
  "state_postpartum_avg":     float,     # state benchmark
  "readmission_penalty":      bool,
  "state_mortality_rank":     str,       # "top_quartile" | "bottom_quartile" | "middle"
  "racial_disparity_flag":    bool,
  "medicaid_extended":        bool,
  "mmsm_participant":         bool
}
```

**Gap Calculator assumes:**
- No null fields — validated before passing
- `commitment_tag` is present — raises `ValueError` if missing
- `facility_name` is the hospital name field — not `name` or `hospital_name`

---

### Handoff 2: Gap Calculator + Urgency Ranker → Account Selector → Outbound Generator

`calculate_gap_score()` → `add_urgency()` guarantees this exact structure:

```python
{
  "facility_id":              str,
  "facility_name":            str,
  "state":                    str,
  "gap_score":                float,     # 0–100
  "lead_angle":               str,       # see valid values below
  "gap_breakdown": {
      "commitment_strength":  int,       # 0–25
      "outcome_gap":          int,       # 0–50
      "urgency_context":      int        # 0–25
  },
  "data_confidence":          str,       # "high" | "low"
  "urgency_tier":             str,       # "high" | "medium" | "low"
  "urgency_flag":             str,       # "🔴 Act this week" | "🟡 Monitor" | "🟢 Not ready"
  "medicaid_extended":        bool,
  "racial_disparity_flag":    bool
}
```

**Valid `lead_angle` values:**
- `"baby_vs_mother_contrast"` — well-baby visit (state proxy) vs hospital discharge-information disparity
- `"hcahps_care_transition_gap"` — discharge information star rating gap
- `"state_strength_vs_hospital_lag"` — hospital lags state postpartum average
- `"financial_unrealized"` — Medicaid payer mix + RPM CPT codes = uncaptured revenue
- `"smm_rate_gap"` — severe maternal morbidity above national average

**Outbound Generator assumes:**
- `gap_score >= 40` — Orchestrator filters below-threshold hospitals before this handoff
- `lead_angle` is always one of the five exact strings above
- `urgency_tier` is present before reading `gap_score` — confirms `add_urgency()` has run

---

### Handoff 3: Outbound Generator → Send

```python
{
  "facility_id":    str,
  "facility_name":  str,
  "recipient_role": str,             # "CMO" | "VP Patient Experience"
  "subject":        str,
  "email_body":     str,
  "product":        "Babyscripts",   # hardcoded
  "lead_angle":     str,             # passed through for audit log
  "gap_score":      float,           # passed through for audit log
  "urgency_tier":   str,             # passed through for audit log
  "sent_at":        None,            # populated on send
  "status":         str              # "pending_review" (tuning) | "ready_to_send" (production)
}
```

**Tuning phase:** status = `"pending_review"` — Human Checkpoint displays for review.
**Production (end goal):** status = `"ready_to_send"` — Orchestrator sends automatically. No review step. Paula's input validation and Luba's threshold enforcement are the only safety gates.

---

## 7. Gap Score Formula

Three layers, 0–100 total:

| Layer | Max Points | Signals |
|---|---|---|
| Layer 1 — Commitment Strength | 25 | Birthing-Friendly flag (15), MMSM participation (10), manual tag (5 bonus) |
| Layer 2 — Outcome Gap | 50 | SMM rate vs national (20), discharge-info % vs state postpartum avg (15, cross-measure proxy), HCAHPS care transition below 3 (10), readmission penalty (5) |
| Layer 3 — Urgency Context | 25 | State mortality rank bottom quartile (10), racial disparity flag (8), Medicaid extended (7) |

**Urgency tiers:**
- 70+ → 🔴 Act this week
- 40–69 → 🟡 Monitor
- Under 40 → 🟢 Not ready (pipeline stops, no outbound generated)

**Silent Gap mode (v2):** Hospitals with no public commitment but poor outcomes included as secondary tier. `has_commitment: False` skips Layer 1, caps score at 75.

---

## 8. GTM Direction

**Customer:** Babyscripts — their GTM Engineer is the end user of Fourth.

**Sales targets:** Hospitals — specifically CMOs and VP Patient Experience roles at hospitals with CMS Birthing-Friendly designation and lagging postpartum outcome scores.

**Service being sold:** Babyscripts remote postpartum monitoring — BP monitoring kit, mobile app, OB-specialized care managers (RNs), RPM CPT billing support.

**Social proof:** "Hospitals using Babyscripts saw patients become 2x more likely to complete their 30-day postpartum visit." (LCMC Health case study)

**Core outbound hook:** Baby vs mother contrast — "Your well-baby visit completion rate is 94%. Your postpartum maternal visit completion rate is 61%. The system you built works — for babies."

**Three email angles per hospital:**
1. **Moral** — "You made a commitment. The data shows a gap."
2. **Clinical** — "Women aren't completing postpartum follow-up and outcomes reflect it."
3. **Financial** — "NY has 12-month postpartum Medicaid coverage. There is unrealized reimbursement in your payer mix."

---

## 9. Architecture Decision Rule

For future decisions during the build:

| Question | Answer |
|---|---|
| Can steps run simultaneously? | Parallel |
| Must they run in order, same path always? | Handoff |
| Must they run in order but path changes based on results? | Orchestrator/Subagent |
| Task can't be decomposed? | Deeper Single Agent |

---

*Fourth ADR v1.0 — Luba Kaper, Pursuit AI-Native Cycle 3 — Built for Babyscripts*
# PRD — ECHO (Maternal Accountability Intelligence Agent)

> Product Requirements Document. Written before code.
> The "what and why." CLAUDE.md will be the "how."

## Problem Statement

**Who is affected:** GTM Engineers and Solutions Engineers at postpartum software companies (remote monitoring, care navigation, fourth trimester platforms) who sell into hospital and health system buyers.

**What's broken:** Hospitals publicly commit to maternal quality improvement through federal programs like the CMS Birthing-Friendly designation, then send women home with a paper pamphlet and a six-week appointment. The fourth trimester is where the system goes silent. GTM Engineers selling postpartum software are walking into hospitals that have made the commitment but don't know the outcomes have not followed. There is no tool that surfaces this gap at the hospital territory level.

**How we know it's real:**
- 2,265 hospitals have earned the CMS Birthing-Friendly designation (CMS Provider Data Catalog, 2025)
- Maternal mortality rate in the US was 17.9 per 100,000 live births in 2024; Black women die at 3x the rate of White women, with the gap widening post-pandemic (NCHS Health E-Stat 113, March 2026; Kamijo et al., Cureus 2025)
- Brooklyn validation sample: NY Birthing-Friendly hospitals show measurable HCAHPS patient experience scores well below what the state's strong Medicaid postpartum performance would predict. NY achieves 82.4% postpartum care completion (top quartile nationally) yet hospital-level patient experience varies widely. Hospital-level performance lags state-level strength.
- Maternal health data lives in at least 9 federal and non-federal sources that don't cross-reference each other

## Target User

**Primary user:** GTM Engineer or Solutions Engineer at a postpartum software company (Maven, Pomelo Care, Mahmee, Babyscripts, Midi, Elektra, similar). They work a territory of 30 to 200 hospital accounts. Their day is finite. Their first decision every morning is which accounts deserve outreach today.

**Secondary user:** Sales leadership at the same company who needs visibility into territory health and how the GTM team is prioritizing.

**How they solve this today:** Manually. They use territory lists from CRMs, public news searches, and gut instinct. No one is cross-referencing CMS Birthing-Friendly designations against state-aggregate and hospital-level outcome data daily. The synthesis work doesn't exist as a tool.

**User needs:**
- As a GTM Engineer, I need a daily list of the 10 hospitals in my territory most worth contacting today, because I cannot manually monitor 200 accounts every morning.
- As a GTM Engineer, I need to see *why* a hospital is on the list so I can decide whether the data justifies the outreach, because pulling the trigger on the wrong account costs a meeting.
- As a GTM Engineer, I need to see source links beneath every claim so I can pressure-test the data before I write the email, because I am the one who has to defend it on the call.
- As a GTM Engineer, I need three drafted outreach variants per account so I can pick the angle that fits the persona I'm writing to, because a CMO and a CFO need different framing.
- As a GTM Engineer, I need to override the agent's calls when I have context the data doesn't show, because not every flagged account is the right call today.

## Solution

**One-liner:** ECHO is an agent that finds Birthing-Friendly hospitals where commitments aren't translating to patient experience, and arms GTM Engineers with the daily 10 most critical accounts plus three drafted outreach variants per account.

**Core mismatch logic (within-state comparison):**

> *"NY state achieves [X%] postpartum care completion across Medicaid managed care. This Birthing-Friendly hospital scores [Y] stars on HCAHPS patient experience, suggesting their patients aren't benefiting from the state's overall strength."*

The state aggregate becomes the *expectation* hospitals should be meeting. Hospital-level HCAHPS scores well below state strength reveal which Birthing-Friendly hospitals are dragging behind.

**Core user flow:**
1. GTM Engineer opens dashboard → sees Today's Critical 10 ranked by mismatch severity
2. GTM Engineer clicks an account → sees the briefing card with mismatches, supporting commitments, context signals, confidence, and three drafted email variants
3. GTM Engineer reviews the 10, suppresses any that don't fit, picks call order, picks the email variant that fits the persona, copies and sends from their own tool

## Feature Scope

### User Journey: GTM Engineer reviews today's critical accounts

**Context:** This is the morning ritual. The GTM Engineer opens ECHO, decides who to call today, and gets out.

**Step 1: Reviewing the daily 10**
- [P0] User can see a ranked list of 10 hospitals scored CRITICAL, HIGH, ELEVATED, or WATCH
- [P0] User can see hospital name, location, CCN identifier, and a one-sentence top mismatch summary per row
- [P0] User can see severity badge, hospital-level HCAHPS scores, the state benchmark they're being compared against, and confidence percentage per row
- [P0] User can see the territory toolbar showing the count and source ("New York · 101 hospitals · monitored against CMS Birthing-Friendly registry")
- [P1] User can filter by severity tier
- [P1] User can see a stats strip showing critical mismatches today, high severity count, and average confidence
- [P2] User can export the list to CSV

**Step 2: Drilling into a briefing card**
- [P0] User can click any of the 10 accounts to see a full briefing card
- [P0] User can see hospital metadata: name, location, parent system, CCN, beds and deliveries per year if available
- [P0] User can see each commitment-outcome mismatch with the commitment, the state aggregate, the hospital-level HCAHPS score, the recency, and the gap visualization
- [P0] User can see source links beneath every commitment, state-level outcome, and hospital-level outcome claim
- [P0] User can see the Birthing-Friendly designation as the commitment (v1 default for all hospitals; v2 adds curated per-hospital tags)
- [P0] User can see context signals (state postpartum Medicaid coverage, racial disparity flag, recent leadership changes if known)
- [P0] User can see a confidence breakdown per mismatch with a brief explanation of why confidence is reduced when applicable
- [P0] User can see "data unavailable" displayed neutrally with a confidence flag when an outcome metric is missing
- [P1] User can see a judgment call callout flagging context the agent thinks the human should weigh
- [P2] User can see all tracked commitments for the hospital (only Birthing-Friendly designation in v1)

**Step 3: Acting on the daily 10**
- [P0] User can suppress an account from today's list with optional reason
- [P0] User can move accounts up or down in priority
- [P0] User can view 3 AI-generated email variants per account (moral / clinical / financial), each grounded in the same underlying mismatch data, and copy the one that fits the persona
- [P1] User can add an account to a watchlist for tomorrow
- [P2] User can hand off to an external CRM via "Open in [CRM]" button

> **Briefing card field list:** specified by the existing mockup HTML. Mockup needs an update pass to match v1 scope (NY-only, Birthing-Friendly only, within-state mismatch framing using HCAHPS star ratings, three angles preserved). Paula owns the update.

### Out of Scope (for v1)
- **Sending email.** ECHO never sends email. The GTM Engineer copies a draft and sends from their own tool.
- **Reliable API uptime.** v1 depends on the OpenRouter API for email generation. If API is down or slow during demo, fallback is cached static templates pre-generated the night before.
- **Hospital-level outcome data beyond HCAHPS.** v1 uses three HCAHPS signals per hospital: discharge information composite star (H_COMP_6), summary star rating (H_STAR_RATING), and discharge help YES percent (H_DISCH_HELP_Y_P). Other hospital-level metrics (severe maternal morbidity per hospital, AIM Data Center metrics, hospital-level readmissions) are v2.
- **Multiple commitment sources.** v1 uses CMS Birthing-Friendly designation only, and every v1 hospital shares one default commitment tag. v2 adds curated per-hospital tags from AIM bundle participation, NNPQC PQC membership, Joint Commission Perinatal Care certification, and hospital newsroom press releases.
- **Hospital-level Medicaid mix.** v1's financial email variant uses state-level Medicaid context (NY's 12-month postpartum coverage from KFF) instead of hospital-level Medicaid payer mix. Hospital-level Medicaid mix is v2.
- **Outreach angle expansion beyond the three v1 variants.** v1 ships moral, clinical, and financial leads. v2 may add cost-of-poor-outcomes, peer benchmarking, and regulatory pressure variants.
- **National territory display.** v1 demos NY-only (101 Birthing-Friendly hospitals). Backend ingests national data and could display all states; the NY filter is a demo choice, not a data limitation.
- **Patient-facing surface.** ECHO never communicates with patients. The agent's only audience is the GTM Engineer.
- **Leapfrog Hospital Survey data.** Licensed data not included in v1.
- **Real-time alerts or sub-daily cadence.** v1 refreshes daily.
- **Customer discovery validation.** No external user interviews in v1 scope. Acknowledged as next-phase work.
- **Visual design mockup as separate deliverable.** Existing mockup HTML serves as spec, pending Paula's v1-scope update.

## Data Sources

| Data | Source | Format | Notes |
|------|--------|--------|-------|
| Birthing-Friendly hospital registry | CMS Provider Data Catalog | CSV (free) | 2,265 hospitals, geocoded; filter to NY for v1 demo (101 hospitals) |
| State-level postpartum care visit completion | CMS Medicaid Adult Core Set (PPC-AD) | CSV (free, all 50 states) | Primary state benchmark in `state_postpartum_visit_rate`. NY 82.4% (2023), top quartile. |
| State-level prenatal care timeliness | CMS Medicaid Child Core Set (PPC-CH) | CSV (free, all 50 states) | NY 86.8% (2023), top quartile. Supporting context in briefing card sidebar; not used in scoring math. |
| State-level postpartum care by age | CMS Medicaid Core Set (PPC2-AD, PPC2-CH) | CSV (free, all 50 states) | NY top quartile. Supporting context only. |
| State-level postpartum contraceptive care | CMS Medicaid Child Core Set (CCP-CH) | CSV (free, all 50 states) | NY 47.2% (2024). Supporting context only. |
| Hospital-level HCAHPS patient experience | CMS Provider Data Catalog | CSV (free, ~4,000 hospitals) | Required for within-state mismatch. v1 uses three measures: H_COMP_6_STAR_RATING (discharge information composite), H_STAR_RATING (summary star), H_DISCH_HELP_Y_P (discharge help YES percent). |
| State-level maternal mortality | NCHS Health E-Stat 113 (March 2026) | PDF (free) | 2024 data; cite undercount caveat. Used to compute `racial_disparity_flag`. |
| Postpartum Medicaid coverage status | KFF Medicaid Postpartum Coverage Extension Tracker | CSV (free) | All 50 states + DC. NY = 12-month coverage implemented June 2023. Drives `medicaid_extended` field and the financial email variant. |
| State perinatal quality collaborative status | NNPQC | CSV (free) | State-level membership and funding status. NY = funded. |
| Racial disparity context | Kamijo et al., Cureus 2025 | PDF (free, peer-reviewed) | Post-pandemic Black-White MMR gap widening. Cited in dashboard, not ingested per-hospital. |
| OpenRouter API | OpenRouter | REST API (free tier in v1) | Email generation; key in `.env`, gitignored; fallback to static cache for demo reliability. |

> **Adult Core Set source URL:** https://www.medicaid.gov/medicaid/quality-of-care/core-set-data-dashboard/welcome
> **Hospital HCAHPS source URL:** https://data.cms.gov/provider-data/dataset/dgck-syfz
> **OpenRouter API docs:** https://openrouter.ai/docs

**v2 expansion sources (not in v1):**
- State-level all-cause readmissions (CMS Medicaid Adult Core Set, PCR-AD)
- State-level postpartum depression screening (CMS Medicaid Adult Core Set, PDS-AD)
- State-level low-risk cesarean delivery (CMS Medicaid Maternity Core Set, LRCD-AD)
- Hospital-level severe maternal morbidity (CMS Maternal Health Hospital file)
- Hospital-level readmissions penalties (CMS FY2025 Hospital Readmissions Reduction Program)
- Hospital-level Medicaid payer mix (CMS Hospital Provider Cost Report)
- Curated per-hospital commitment tags (PQC membership, AIM bundles, press releases)

## Success Metrics

| Goal | Signal | Metric | Target |
|------|--------|--------|--------|
| Demo Day usability | Judges understand ECHO's value in under 60 seconds | Time from demo start to "I get it" reaction | Under 60 seconds |
| Architecture defensibility | Interviewer asks "where does the data come from" and gets a clean answer | Number of source links visible per briefing card | At least 1 source link per claim, no exceptions |
| Mismatch logic validity | NY Birthing-Friendly hospitals show measurable hospital-level HCAHPS lag against state strength | Percent of NY-101 hospitals with at least one defensible within-state mismatch surfaced by ECHO | At least 50% |
| Email quality | Generated emails reference only ECHO's underlying data with no hallucinated claims | Percent of test emails that pass manual review | 100% |
| Build completion | All 6 tools shipped and integrated | Tools complete and producing output by Demo Day | 6 of 6 |
| Honest framing | Confidence flags appear when data is missing | Percent of briefing cards with at least one confidence indicator | 100% of cards show confidence breakdown |

## ROI Snapshot

| Category | Without ECHO | With ECHO | Delta |
|----------|------------------|----------------|-------|
| **Time** | GTM Engineer spends estimated 2–4 hours per week manually researching territory accounts across CMS, CDC, KFF, March of Dimes, plus drafting outreach for each | Daily 10 surfaced in seconds; review takes 5–10 minutes; three email drafts per account ready to copy | Estimated 3–6 hours per week per GTM Engineer |
| **Coverage** | Manual review covers maybe 10–20% of territory accounts in detail | Agent monitors 100% of Birthing-Friendly hospitals daily | Full territory coverage vs. partial |
| **Build cost** | — | ~3 weeks build time across 3-person team; free OpenRouter tier in v1 | Demo Day deliverable |

**One-line pitch:** ECHO replaces manual cross-referencing of fragmented federal maternal health data with a daily ranked list of the 10 Birthing-Friendly hospitals in a GTM Engineer's territory whose patient experience is dragging behind their state's strength, plus three drafted outreach variants per account ready to copy and send.

## Stakeholder Concerns

**Sales (the imagined buyer):**
- The buyer at a postpartum software company (VP Sales, Head of GTM) is the same person whose team would use ECHO
- Sales cycle for a B2B internal tool is typically a pilot followed by team rollout — multi-week, not one-call
- Top objections likely: "we already have a CRM for this" (answer: ECHO produces signal CRMs don't, the CRM still owns pipeline), "the data is too narrow" (answer: v1 is intentionally scoped, v2 expands sources), "you haven't talked to a real GTM Engineer" (answer: scope discipline; customer discovery is the next phase), "AI-generated emails feel impersonal" (answer: three variants per account let the GTM Engineer pick the angle and edit before sending; ECHO drafts, the human ships)

**Customer Success / Support:**
- Onboarding for a real GTM Engineer would require importing their territory and tuning the urgency formula and prompt templates to their preferences. Out of scope for v1.
- Most common confusion will be "why is this hospital ranked above that one" — the briefing card's confidence breakdown and judgment call callout are designed to answer that
- Email quality issues (tone off, claim wrong, source missing) will be the top support burden once real users adopt

**Operations / Engineering:**
- All v1 outcome and commitment data sources are free public CSVs and APIs. No HIPAA-sensitive data. No PII.
- v1 uses OpenRouter free tier.
- Daily refresh runs against static or slowly-changing federal data. No real-time pipeline required for v1.
- API outage = email generation breaks. Cached static fallback required for Demo Day reliability.
- If CMS or CDC sources change URLs or formats (real risk given proposed FY27 HHS reorganization), the data layer is the only piece that needs updating.

**Legal / Compliance:**
- All data sources are public and free to use
- No PII, no patient data, no HIPAA exposure
- Hospital names are public; CCN identifiers are public; outcome data is published by CMS/CDC for public use
- AI-generated emails: ECHO cites only ECHO-verified data. Prompt design constraints prevent the model from inventing claims about hospitals.
- The human reviews and sends, so accountability for what's actually communicated stays with the GTM Engineer

**Marketing / Communications:**
- One-sentence description: "ECHO finds Birthing-Friendly hospitals whose patient experience lags their state's strength, surfaces the daily 10 a GTM Engineer should contact today, and drafts three outreach variants per account ready to send."
- Visual hook: the briefing card showing a hospital's commitment date next to the within-state outcome gap, with source links beneath every claim, and three email tabs at the bottom
- Sensitivity concern: maternal mortality and racial disparity data carry real weight; the language across the dashboard and generated emails should be precise and non-sensationalized
- Story arc: hospitals committed publicly → state achieves the standard → this hospital lags behind → ECHO surfaces the gap → ECHO drafts the outreach → the human walks into the room

**End Users:**
- Biggest reason a GTM Engineer would distrust ECHO: opaque scoring or hallucinated email claims. Mitigated by per-mismatch confidence breakdowns, visible source links, and prompt design that constrains generation to ECHO data.
- Ethical risk: ECHO surfacing accounts in a way that feels accusatory toward hospitals. Mitigated by within-state framing (hospital lags state strength, not "your state is bad") and by the judgment call callout.
- Accessibility: dashboard should meet basic web accessibility standards (semantic HTML, keyboard navigation, sufficient color contrast)

## Open Questions

- [ ] **Honesty stance for v1 limitations.** Do we lean fully into honest framing in the dashboard copy and demo script, or smooth over what's curated vs. automated? Suggestion: lean honest. (Question 9 in team_questions.md)
- [ ] **One-page v2 roadmap doc.** Multiple PRD sections reference v2 (commitment scope expansion, additional hospital-level metrics, additional outreach angles, customizable cadence, AIM Data Center integration). A short v2 roadmap as a v1 deliverable would make the demo more defensible.
- [ ] **Mockup update.** Paula updates the existing mockup HTML to match v1 scope. Team reviews together so Jonel can confirm the data layer schema matches what the briefing card expects.
- [ ] **Model choice.** v1 uses OpenRouter free tier (current model: `tencent/hy3-preview:free`, configurable via `OPENROUTER_MODEL` env var). Model selection lives in Paula's code, not the schema.
- [ ] **Email generation cache strategy.** Generate live during dashboard open, or pre-generate nightly and serve from cache? Cache is safer for demo reliability; live is more impressive. Paula and Luba decide together.

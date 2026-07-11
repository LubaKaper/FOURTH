# Fourth — Standalone Context

## Current Direction

Fourth (formerly ECHO) is Luba's standalone continuation of the original
class project. Current ownership for all files is Luba.

Seller context:

- Seller: **Babyscripts** (and companies like it — Delfina, Wildflower Health, Mahmee, Bloomlife)
- Service: **remote postpartum monitoring** — BP monitoring kit, mobile app, OB-specialized care managers, RPM CPT billing support
- Buyer: CMOs and VPs of Patient Experience at CMS Birthing-Friendly hospitals
- User: a GTM Engineer reviewing priority hospital accounts

## What Fourth Does

Fourth finds CMS Birthing-Friendly hospitals whose discharge-readiness and
patient-experience signals lag their public maternal health commitments,
ranks them with a 3-layer gap score, drafts one claim-validated outbound
email per account, and presents everything for human review — in the
terminal checkpoint, a static dashboard, and a read-only Streamlit demo app.

The core story:

```text
NY completes 82.4% of its Medicaid postpartum visits statewide.
At this Birthing-Friendly hospital, far fewer patients report receiving
the information they needed for their own recovery at discharge.
```

## Guardrails (built, enforced by tests)

- The LLM writes only the email body; deterministic code owns every other field.
- Claim validation rejects ungrounded percentages, star ratings, and unsupported claim language.
- Copy-honesty tests forbid presenting the discharge-info measure as visit completion.
- Review mode never sends. `--send` requires SMTP credentials and passes the
  approval gate → send gate → 30-day dedup cooldown → append-only audit log chain.
- Low-confidence hospitals are skipped by the outbound generator.
- The demo app is read-only: no keys, no pipeline imports, no send path.

## Next Product Work

1. Hospital-level SMM when CMS ships PC_07a (tests/test_smm_data_availability.py fails loudly when it lands).
2. Hospital-level well-baby visit sourcing to replace the state proxy.
3. Multi-state expansion beyond NY.
4. Curated per-hospital commitment tags (the dataset moat).
5. Review workflow: approve, suppress, watchlist; persistence for review decisions.
6. CRM integration.

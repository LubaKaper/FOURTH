# ECHO Standalone Context

## Current Direction

Fourth (formerly ECHO) is Luba's standalone continuation of the original class project. Current ownership for all files is Luba.

The product now has a concrete seller context:

- Seller: **NurtureBridge Health**
- Service: **Postpartum Handoff Navigation**
- Buyer: hospitals and health systems with maternity/postpartum quality responsibility
- User: a NurtureBridge GTM Engineer reviewing priority hospital accounts

Postpartum Handoff Navigation helps maternity teams manage the discharge-to-postpartum transition with a shared follow-up work queue, patient check-ins, escalation routing, and visit-readiness tracking.

## What ECHO Does

ECHO finds CMS Birthing-Friendly hospitals where hospital-level HCAHPS patient experience lags against state postpartum visit strength. It ranks the best accounts for a NurtureBridge GTM Engineer, generates grounded outreach variants for Postpartum Handoff Navigation, displays a human checkpoint, and generates a static dashboard.

The core v1 story remains:

```text
NY achieves 82.4% postpartum visit completion.
This Birthing-Friendly hospital scores 1 star on HCAHPS discharge information.
NurtureBridge can speak to the discharge-to-postpartum handoff gap.
```

## v1 Guardrails

- No automated email sending.
- No CRM integration.
- No live web scraping.
- No patient-facing features.
- No unsupported hospital-level financial, readmission, morbidity, or Medicaid payer-mix claims.
- Hospital-specific claims must come from ECHO's schema fields and source files.
- Low-confidence hospitals are skipped by Tool 5.
- Generated outreach is reviewed by a human before use.

## Long-Term Direction

The long-term product can move toward automated sending, but only after the system has stronger controls:

- Prompt reliability tests
- Claim validation against source-grounded facts
- Source links beneath generated claims
- Safety checks for unsupported clinical, financial, or accusatory language
- Account suppressions and watchlists
- Explicit human approvals
- Send throttles and daily caps
- Audit logs for prompts, facts, outputs, and sends
- Kill switch and rollback controls

Until those controls exist, ECHO drafts only.

## Next Product Work

1. Update `src/outbound_generator.py` prompts and cached fallback copy to use NurtureBridge Health and Postpartum Handoff Navigation instead of generic company placeholders.
2. Update tests for Tool 5 so specificity is required while unsupported claims remain blocked.
3. Add source grounding to dashboard/email claims.
4. Improve review workflow: approve, suppress, watchlist, copy selected variant.
5. Add persistence for notes, suppressions, and review decisions.

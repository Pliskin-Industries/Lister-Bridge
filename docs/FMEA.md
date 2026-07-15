# FMEA.md — Risk Register: Lister-Bridge Hybrid Agent

**Status:** Active — Ground Rules 5, 8, and 9 in full enforcement.
**Amendment Protocol:** Any proposed change requires a FMEA Amendment Proposal (Ground Rule 9) approved by the human owner before taking effect.

---

## Active Risk Register

### Pipeline and Pricing Risks

| ID | Failure mode and effect | S/O/D (RPN) | Mitigation | Status | Owner |
|---|---|---|---|---|---|
| PI-001 | Google Drive API sync failure or delay halts the listing pipeline when images or source files are unavailable. | 6/5/3 (90) | Implement local cache fallback and exponential backoff retries. | Open — mitigation planned | DevOps/Data Eng |
| PI-002 | Accidental `.env` exposure lets malicious actors drain API credits or hijack the eBay account. | 10/2/4 (80) | Ignore `.env` and add automated pre-commit secret scanning. | Mitigated | Security/DevOps |
| PI-003 | Context-window token bloat crashes the orchestrator midway through a session. | 8/6/5 (240) | Use stateless per-item AI calls, persist frozen review candidates, and release image/JSON references after a terminal batch state. | Open — mitigation planned | AI/Core Eng |
| PI-004 | Vision misses physical defects, causing an inaccurate listing and INAD returns. | 8/4/7 (224) | Force structured negative confirmation through `defects_found: []`. | Open — mitigation planned | Prompt Engineer |
| PI-005 | Vision hallucinates item specifics, causing data-quality flags and poor search visibility. | 7/6/4 (168) | Enforce a strict JSON schema mapped to eBay category enums and drop invalid values. | Open — mitigation planned | AI Engineer |
| PI-006 | Margin Guard calculates an unviable price, undermining margin or the sell-through objective. | 8/3/6 (144) | Enforce a deterministic `(cost + fees) × 1.15` floor that overrides AI. | Open — mitigation planned | Product Owner |
| PI-011 | Sparse, stale, or biased outcomes distort the pricing prior and degrade sell-through or margin. | 7/5/6 (210) | Use same-account/category evidence with N ≥ 30; cap adjustment at ±15%; exclude unknown and sold-elsewhere; count reversals as failures; preserve floor and human gate. | Open — mitigation planned | Pricing/Product |

### Review and Publication Risks

| ID | Failure mode and effect | S/O/D (RPN) | Mitigation | Status | Owner |
|---|---|---|---|---|---|
| PI-007 | User approval of a flawed payload sends a bad listing live. | 7/5/8 (280) | Show photos, critical fields, defects, blockers, and pricing evidence in Streamlit; require explicit confirmation before publishing. | Open — mitigation planned | UI/Product |
| PI-008 | Raw JSON overwhelms the operator and causes blind approvals. | 5/8/4 (160) | Use a progressive-disclosure Streamlit summary; keep raw JSON as optional diagnostic evidence. | Open — mitigation planned | UI/Product |
| PI-009 | An invalid Sell Inventory or Media payload is rejected by eBay. | 7/5/2 (70) | Enforce strict pre-submit validation before `createInventoryItem`, `createOffer`, or `publishOffer`. | Open — mitigation planned | Integration Dev |
| PI-010 | A crash or concurrent approval duplicates a remote publication, fees, or sale. | 9/4/8 (288) | Use an atomic composite claim, persisted remote checkpoints, deterministic SKU/offer reconciliation, and concurrency/fault-injection tests. | Open — mitigation planned | State/Integration Eng |
| PI-012 | Outcome polling exceeds limits or misses transitions, leaving pricing and review guidance stale. | 7/5/5 (175) | Poll only due records; persist `last_checked`; honor `Retry-After` with jitter; maintain a rate budget; use `UNKNOWN` on ambiguity. | Open — mitigation planned | API/State Eng |
| PI-013 | Incomplete environment, account, marketplace, or SKU identity mutates or attributes the wrong listing. | 9/3/8 (216) | Key by environment, seller account, marketplace, SKU, offer ID, and listing ID; forbid SKU-only joins; isolate accounts in tests; verify remote state after writes. | Open — mitigation planned | Integration/Data Eng |

---

## FMEA Amendment 5

**Date:** July 14, 2026
**Triggering task:** T-002 and roadmap epic #7
**Status:** Approved and active
**Approval record:** The human owner replied `execute` on July 14, 2026, immediately after the branch handoff identified FMEA approval as the next gate. Before modifying the register, the Tier-3 primary agent recorded that response as approval of the four scores and controls exactly as previously presented.

The active register now replaces the obsolete CLI mitigations for PI-003, PI-007, and PI-008 and adds PI-010 through PI-013. The active rows are the authoritative scores, controls, owners, and status.

---

## High-Risk Mitigation Map (RPN ≥ 100)

### Publication and State Risks

| ID | RPN | Primary Mitigation Task |
|---|---|---|
| PI-010 | 288 | T-004 and T-005 — atomic state and checkpointed publication |
| PI-007 | 280 | T-006 and T-009 — durable review and truthful UI |
| PI-003 | 240 | T-006 — frozen review candidates |
| PI-013 | 216 | T-005 and T-014 — composite identity and reconciliation |
| PI-012 | 175 | T-014 — rate-aware outcome polling |

### AI and Pricing Risks

| ID | RPN | Primary Mitigation Task |
|---|---|---|
| PI-004 | 224 | T-006 and T-019 — defect contract and photo QA |
| PI-011 | 210 | T-014 and T-015 — outcome evidence and pricing prior |
| PI-005 | 168 | T-006 and T-007 — schema and aspect validation |
| PI-008 | 160 | T-009 — progressive-disclosure review UI |
| PI-006 | 144 | T-006 and T-015 — deterministic floor and prior cap |

---

## Revision History

| Date | Change | Author | Amendment # |
|---|---|---|---|
| March 29, 2026 | Initial FMEA generated from Master Plan | AI Systems Reliability Engineer | — |
| March 29, 2026 | Assigned role-based owners to open risks | AI Systems Reliability Engineer | 1 |
| March 29, 2026 | Added architectural mitigation plans for all High-Risk (RPN ≥ 100) items | AI Systems Reliability Engineer | 2 |
| March 29, 2026 | Finalized statuses for sub-100 RPN items based on SRE recommendations | AI Systems Reliability Engineer | 3 |
| March 29, 2026 | Corrected statuses: items with unbuilt mitigations moved from Mitigated to Open — mitigation planned | Calibration Review | 4 |
| July 14, 2026 | Activated Streamlit mitigation corrections and PI-010–PI-013 after exact-score approval | Human owner and Tier-3 primary agent | 5 |

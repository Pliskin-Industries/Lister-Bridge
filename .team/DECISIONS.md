# DECISIONS

## D-TEAM-001 — Governance coexistence

The existing master plan, FMEA, and decision logs remain requirements records. The Tier-3 `.team` workspace is an execution overlay: `.team/PLAN.md` controls current execution scope, dependencies, and status when legacy tasks, prompts, or issues conflict; `.team/STATE.md` owns resumability; GitHub issues remain the external binding record. Existing FMEA amendment and human approval gates remain binding. Roadmap epic: https://github.com/GhengisPliskin/Lister-Bridge/issues/7.

## D-TEAM-002 — Release boundary

This roadmap ends at a sandbox-verified, unsigned Windows release candidate. Production credentials, publishing, code signing, and rollout require a separate human-approved release.

## D-TEAM-003 — Scheduling default

Headless scans use Windows Task Scheduler, are disabled until explicitly registered, and may prepare review work but never publish listings.

## D-TEAM-004 — Issue Binding

T-001 is the bootstrap exception because it created the binding mechanism. T-002 is bound to roadmap epic #7. Beginning with T-003, every task requires its own assigned GitHub issue linked in `.team/PLAN.md` and `.team/STATE.md` before `IN-FLIGHT`. Issue text may narrow but never expand PLAN scope.

## D-TEAM-005 — OAuth Token Separation

Seller authorization uses base, Inventory, Account read-only, Media, and Fulfillment scopes. Browse and Taxonomy use a separate client-credentials application token. The nonsecret eBay user ID scopes publication and outcome identity.

## D-TEAM-006 — Isolate the Roadmap from Legacy Main

Execute Tier-3 and v2 roadmap work on `tier3-v2-roadmap`, based on legacy commit `678ff26`. Keep `main` unchanged as the protected legacy baseline. Integration into `main` requires explicit user authorization after evidence-gated review; ordinary task completion does not imply merge or publication authority.

## D-TEAM-007 — Activate FMEA Amendment 5

The human owner replied `execute` immediately after the branch handoff identified FMEA approval as the next gate. Before modifying the register, the primary agent recorded that response as approval of Amendment 5 exactly as previously presented. PI-010 9/4/8 (288), PI-011 7/5/6 (210), PI-012 7/5/5 (175), and PI-013 9/3/8 (216), together with their listed controls and the PI-003/PI-007/PI-008 mitigation corrections, are active as of July 14, 2026.

## D-TEAM-008 — Activate FMEA Amendment 6 and Bind the Manual Paste Provider

On September 10, 2026 the human owner approved three sitrep items in one reply: T-004 remediation cycle 4, creation of the T-026/T-027 issues with FMEA Amendment 6, and a durable Python 3.12 install under `%LOCALAPPDATA%`. The primary agent recorded PI-014 7/4/3 (84) with its packet-ID control exactly as presented in `docs/proposals/v2.1_manual_paste_ai_provider.md`. T-026 is bound to https://github.com/Pliskin-Industries/Lister-Bridge/issues/10 and T-027 to https://github.com/Pliskin-Industries/Lister-Bridge/issues/11. Gemini remains the default AI route; the manual route must reuse the frozen extraction prompt and parser.

## D-TEAM-009 — Operator Testing Waits for a Working UI

The owner defers all hands-on testing until a working UI exists. T-027 is the first operator test point. Agent-side QA, adversarial review, and evidence continue unchanged; no smoke transcript, credential entry, or sandbox action is requested from the owner before T-027 reaches `READY-FOR-QA`.

## D-TEAM-010 — Standing Commit, Merge, and Push Authorization Until the UI Is Complete

On September 10, 2026 the owner approved commits and merges for all future roadmap work until the UI is complete, authorized pushing to `origin`, and authorized closing issues #9 and #10. This supersedes the per-commit gate in D-TEAM-006 for the duration of the UI track: `tier3-v2-roadmap` stays the working branch, `main` fast-forwards to it after each task closes with QA evidence, and both branches push to `origin`. Production publishing, credentials, and code signing remain excluded. The gate returns to per-task owner authorization when the owner declares the UI complete or withdraws this decision.

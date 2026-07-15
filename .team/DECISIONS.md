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

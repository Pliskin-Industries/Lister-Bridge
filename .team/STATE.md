# STATE

## Current Status

- Completed: T-001 — Deploy Tier-3 execution workspace (QA PASS; adversarial CLEAR; 166 tests passed).
- Escalated task: T-002 — Establish governance precedence and issue binding.
- Active issue: https://github.com/GhengisPliskin/Lister-Bridge/issues/7.
- Next task issue: https://github.com/GhengisPliskin/Lister-Bridge/issues/8 (T-003).
- Repository: `C:\\Claude\\Lister-Bridge`, working branch `tier3-v2-roadmap`.
- Protected legacy baseline: `main` at `678ff26`; no roadmap commits belong on `main` without explicit user authorization.
- Baseline: clean at start; 166 tests previously passed in a disposable environment; PyInstaller spec built an unsigned executable.
- Production publishing: disabled and out of scope.

## Next Actions

1. Obtain human approval or revised scores for FMEA Amendment Proposal 5 in `docs/FMEA.md`.
2. Activate the approved rows and mitigation corrections without changing their approved values.
3. Run T-002 QA; dispatch T-003 only after T-002 is DONE.

## Blockers

- T-002 is at the required FMEA human gate. Proposed scores: PI-010 9/4/8, PI-011 7/5/6, PI-012 7/5/5, and PI-013 9/3/8.
- Live sandbox tasks T-013, T-017, and T-024 require external credentials and operator-controlled eBay buyer/seller actions.
- The current Codex writable workspace differs from the authoritative repository; approved filesystem escalation was used for deployment.

## Decisions

- Legacy governance remains requirements context; `.team/PLAN.md` owns executable status.
- Python 3.12 is the verification target.
- Windows Task Scheduler is the scheduling mechanism.
- Direct upload, code signing, and production enablement are excluded.

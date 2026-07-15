# STATE

## Current Status

- Completed: T-001 — Tier-3 execution workspace; T-002 — governance precedence and FMEA Amendment 5 activation. Both have QA PASS; adversarial review is CLEAR; 166 tests passed.
- Next task: T-003 — reproducible Windows verification.
- Roadmap issue: https://github.com/GhengisPliskin/Lister-Bridge/issues/7, assigned to `GhengisPliskin`.
- Next task issue: https://github.com/GhengisPliskin/Lister-Bridge/issues/8, assigned to `GhengisPliskin`.
- Repository: `C:\\Claude\\Lister-Bridge`, working branch `tier3-v2-roadmap`.
- Protected legacy baseline: `main` at `678ff26`; no roadmap commits belong on `main` without explicit user authorization.
- Baseline: clean at start; 166 tests previously passed in a disposable environment; PyInstaller spec built an unsigned executable.
- Production publishing: disabled and out of scope.

## Next Actions

1. Commit the completed T-002 governance and evidence packet on `tier3-v2-roadmap`.
2. Move T-003 to `IN-FLIGHT` under assigned issue #8.
3. Dispatch the bounded T-003 Windows verification change set.

## Blockers

- Live sandbox tasks T-013, T-017, and T-024 require external credentials and operator-controlled eBay buyer/seller actions.
- The current Codex writable workspace differs from the authoritative repository; approved filesystem escalation was used for deployment.

## Decisions

- Legacy governance remains requirements context; `.team/PLAN.md` owns executable status.
- Python 3.12 is the verification target.
- Windows Task Scheduler is the scheduling mechanism.
- Direct upload, code signing, and production enablement are excluded.

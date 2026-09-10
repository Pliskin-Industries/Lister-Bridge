# STATE

## Current Status

- Sitrep date: 2026-09-10. No roadmap activity between 2026-07-15 and this date; this session closed T-004 and opened the manual AI mode tasks.
- Completed: T-001 through T-004. T-004 closed on cycle 4 with independent QA PASS and adversarial critic CONCERNS (no blocker); evidence under `.team/evidence/T-004/`.
- Proposed and bound: T-026 (core) and T-027 (UI) for the manual paste AI provider, issues [#10](https://github.com/Pliskin-Industries/Lister-Bridge/issues/10) and [#11](https://github.com/Pliskin-Industries/Lister-Bridge/issues/11). FMEA Amendment 6 (PI-014) approved and active. Design: `docs/proposals/v2.1_manual_paste_ai_provider.md`.
- Issues: roadmap [#7](https://github.com/GhengisPliskin/Lister-Bridge/issues/7); T-003 [#8](https://github.com/GhengisPliskin/Lister-Bridge/issues/8); T-004 [#9](https://github.com/GhengisPliskin/Lister-Bridge/issues/9); all assigned to `GhengisPliskin`. GitHub now resolves the repository as `Pliskin-Industries/Lister-Bridge`; older links redirect.
- Repository: `C:\\Claude\\Lister-Bridge`, working branch `tier3-v2-roadmap`, not pushed to `origin`.
- Protected legacy baseline: `main` at `678ff26`; no roadmap commits belong on `main` without explicit user authorization (D-TEAM-006).
- Verification: Python 3.12.10 at `%LOCALAPPDATA%\Programs\Python\Python312`; `.venv-py312` rebuilt from it on 2026-09-10; `scripts/verify.ps1` exits 0 with 209 collected tests.
- Production publishing: disabled and out of scope.

## Next Actions

1. Start T-005 (checkpoint eBay publication) or T-026 (manual paste provider core). T-026 has a disjoint file surface and unblocks the owner's first UI test (T-027); T-005 is next on the safety-kernel critical path. Recommend T-026 first, then T-005.
2. Before the next `IN-FLIGHT` transition, move the chosen task's status in PLAN and STATE and confirm its issue is assigned.
3. Apply the queued T-004 follow-ups when T-005 touches `src/core/state_store.py`.
4. Close issue #9 on GitHub when the owner confirms the commit (the primary does not close issues without that confirmation).

## Blockers

- Live sandbox tasks T-013, T-017, and T-024 require external credentials and operator-controlled eBay buyer/seller actions.
- The hosted GitHub Actions run is not local evidence and remains deferred to T-013.
- Owner testing is deferred until T-027 reaches `READY-FOR-QA`.

## Decisions

- Legacy governance remains requirements context; `.team/PLAN.md` owns executable status.
- Python 3.12 is the verification target, installed under `%LOCALAPPDATA%`, never under `%TEMP%`.
- The Python 3.12 Windows dependency graph is locked; byte-identical executables are not claimed.
- Windows Task Scheduler is the scheduling mechanism.
- Publication claims and `PUBLISHING` state remain T-005 scope.
- Direct upload, code signing, and production enablement are excluded.
- 2026-09-10: the owner defers all operator testing until a working UI exists (D-TEAM-009). T-027 is the first operator test point.
- 2026-09-10: Gemini stays the default AI route; the manual paste provider is an optional route that must reuse the frozen extraction prompt and parser (D-TEAM-008).
- 2026-09-10: T-004 cycle-4 critic concerns are accepted as operational follow-ups, not blockers; no code changed after the QA PASS so the PASS remains valid.
- 2026-09-10: README received a development-status Gantt at direct owner request; bound retroactively to T-025 AC3.

# STATE

## Current Status

- Sitrep date: 2026-09-10. This session closed T-004 (cycle 4) and T-026, and opened the manual AI mode track.
- Completed: T-001 through T-004 and T-026. T-004 closed with QA PASS and critic CONCERNS (evidence `.team/evidence/T-004/`). T-026 closed with QA PASS and critic CONCERNS, no blocker (evidence `.team/evidence/T-026/qa.md` and `critic.md`; handoff `.team/handoffs/T-026.md`).
- Uncommitted: the T-026 change set (`src/ai/manual_provider.py`, `tests/test_manual_provider.py`, `src/core/orchestrator.py`, `src/core/settings.py`, `.env.example`) plus its evidence, handoff, PLAN, STATE, `working/ISSUE_QUEUE.md`, and `working/CODE_DECISIONS_PATCH.md`. Awaiting owner commit authorization.
- Manual mode exposure: `AI_PROVIDER=manual` is wired in settings and the orchestrator but the Scan button and headless entry still construct `GeminiProvider`; manual mode is not operator-exposed until T-027 (accepted critic F1, no operator test precedes T-027).
- Issues: roadmap [#7](https://github.com/GhengisPliskin/Lister-Bridge/issues/7); T-003 [#8](https://github.com/GhengisPliskin/Lister-Bridge/issues/8); T-004 [#9](https://github.com/GhengisPliskin/Lister-Bridge/issues/9); T-026 [#10](https://github.com/Pliskin-Industries/Lister-Bridge/issues/10); T-027 [#11](https://github.com/Pliskin-Industries/Lister-Bridge/issues/11); all assigned to `GhengisPliskin`. GitHub resolves the repository as `Pliskin-Industries/Lister-Bridge`; older links redirect.
- Repository: `C:\\Claude\\Lister-Bridge`, working branch `tier3-v2-roadmap` at `955dabb` plus the uncommitted T-026 tree; not pushed to `origin`.
- Protected legacy baseline: `main` at `678ff26`; no roadmap commits belong on `main` without explicit user authorization (D-TEAM-006).
- Verification: Python 3.12.10 at `%LOCALAPPDATA%\Programs\Python\Python312`; `.venv-py312` rebuilt from it on 2026-09-10; `scripts/verify.ps1` exits 0 with 233 collected tests on the T-026 tree.
- Production publishing: disabled and out of scope.

## Next Actions

1. Owner: authorize the T-026 commit (local, on `tier3-v2-roadmap`), and say whether to push the branch and close issues #9 and #10.
2. Start T-027 (manual paste review UI, #11): it is the owner's first operator test point and inherits the review items listed in its PLAN notes.
3. Then T-005 (checkpoint eBay publication), applying the queued T-004 follow-ups when it touches `src/core/state_store.py`.
4. At the next Housekeeping pass, create the two queued hardening issues (T-004 state-store follow-ups; T-026 manual provider follow-ups) and reset processed queue entries.

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
- 2026-09-10: T-026 critic concerns F1 and F2 are accepted; their mitigations are T-027 acceptance notes and a queued hardening issue. The packet ID stays file-name based because Drive cache names are globally unique file IDs (C26-2).
- 2026-09-10: README received a development-status Gantt at direct owner request; bound retroactively to T-025 AC3.

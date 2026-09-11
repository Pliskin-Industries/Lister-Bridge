# STATE

## Current Status

- Sitrep date: 2026-09-11. Sessions on 2026-09-10/11 closed T-004 and T-026 and brought T-027 to `READY-FOR-QA`.
- Completed: T-001 through T-004 and T-026, each with QA PASS and critic clearance; evidence under `.team/evidence/`.
- Ready for owner QA: T-027 (manual paste review UI). Agent review: cycle 1 QA PASS / critic BLOCK (mid-run rerun dropped widget state); cycle 2 fixed it, QA PASS, critic CONCERNS with no blocker; C1/C2 folded in and re-verified. AC1–AC4 verified; AC5 is the owner's smoke test per `.team/evidence/T-027/smoke-guide.md`. Evidence: `qa.md`, `qa-cycle-2.md`, `critic-cycle-2.md`; handoff `.team/handoffs/T-027.md`.
- Manual mode is now operator-exposed: the Scan button follows `AI_PROVIDER`, pending cards render, and rejected pastes give plain guidance. The headless entry `orchestrator.main()` still constructs `GeminiProvider` (queued follow-up).
- Issues: roadmap [#7](https://github.com/GhengisPliskin/Lister-Bridge/issues/7); T-003 [#8](https://github.com/GhengisPliskin/Lister-Bridge/issues/8) closed; T-004 [#9](https://github.com/GhengisPliskin/Lister-Bridge/issues/9) closed; T-026 [#10](https://github.com/Pliskin-Industries/Lister-Bridge/issues/10) closed; T-027 [#11](https://github.com/Pliskin-Industries/Lister-Bridge/issues/11) open until the owner smoke passes. All assigned to `GhengisPliskin`. GitHub resolves the repository as `Pliskin-Industries/Lister-Bridge`.
- Repository: `C:\\Claude\\Lister-Bridge`, working branch `tier3-v2-roadmap`; `main` fast-forwards to it after each closed task and both push to `origin` (D-TEAM-010).
- Untracked `Test.pdf` (about 272 KB, 2026-09-10) sits at the repository root; not part of any task, never opened by agents, excluded from commits by explicit staging. Owner to confirm its disposition.
- Verification: Python 3.12.10 at `%LOCALAPPDATA%\Programs\Python\Python312`; `.venv-py312` rebuilt 2026-09-10; `scripts/verify.ps1` exits 0 with 263 collected tests on the T-027 tree.
- Production publishing: disabled and out of scope.

## Next Actions

1. Owner: run the T-027 smoke test (`.team/evidence/T-027/smoke-guide.md`) and record `owner-smoke.md`; the primary then marks T-027 `DONE` and closes #11. Also confirm what to do with `Test.pdf`.
2. Primary: T-005 (checkpoint eBay publication) is next on the safety-kernel path; apply the queued T-004 follow-ups when it touches `src/core/state_store.py`.
3. Housekeeping pass: create the queued hardening issues (T-004 state-store follow-ups; T-026/T-027 manual-provider follow-ups including the headless `GeminiProvider` construction, Markdown in echoed IDs, off-schema replies, digit-prefixed MISMATCH), reset processed queue entries, and patch the `Pliskin-Industries` links per `working/DOCUMENT_DRIFT_LOG.md`.
4. Refresh the README Gantt at the next phase gate (T-026/T-027 done or near-done; T-004 closed 2026-09-10).

## Blockers

- T-027 `DONE` waits on the owner smoke test (AC5).
- Live sandbox tasks T-013, T-017, and T-024 require external credentials and operator-controlled eBay buyer/seller actions.
- The hosted GitHub Actions run is not local evidence and remains deferred to T-013.

## Decisions

- Legacy governance remains requirements context; `.team/PLAN.md` owns executable status.
- Python 3.12 is the verification target, installed under `%LOCALAPPDATA%`, never under `%TEMP%`.
- The Python 3.12 Windows dependency graph is locked; byte-identical executables are not claimed.
- Windows Task Scheduler is the scheduling mechanism.
- Publication claims and `PUBLISHING` state remain T-005 scope.
- Direct upload, code signing, and production enablement are excluded.
- 2026-09-10: operator testing deferred until a working UI exists (D-TEAM-009); T-027 is that test point and is now ready.
- 2026-09-10: Gemini stays the default AI route; the manual paste provider reuses the frozen extraction prompt and parser (D-TEAM-008).
- 2026-09-10: standing authorization to commit, fast-forward `main`, push, and close issues until the UI is complete (D-TEAM-010).
- 2026-09-11: manual replies are released only after an eBay publish or an explicit "Redo AI reply"; drafts keep them so no item asks for a second paste. Widgets are keyed by SKU. The deferred rescan and rerun run at the end of `main()` so operator edits survive.
- 2026-09-11: T-027 cycle-2 critic concerns C1 and C2 were fixed after the QA PASS and re-verified by the builder driver, unit suites, and the canonical verifier; the owner smoke test is the final gate.

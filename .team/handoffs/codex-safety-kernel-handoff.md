# Safety-kernel Codex handoff (T-005 to T-009)

Copy-paste prompts for running the safety kernel and review queue in the Codex desktop app (GPT-6 Astra, ultracode) against the local repository, with Fable reviewing each task afterward. The task definitions and acceptance criteria live in `.team/PLAN.md`; every prompt below points Codex at its section there. Fable prepared this on 2026-09-14.

## Owner setup (once)

No second clone. Codex works in `C:\Claude\Lister-Bridge` on a branch off the roadmap branch. Rollback is the branch itself: if things go badly, `git checkout tier3-v2-roadmap` and delete the Codex branch.

```powershell
git -C "C:\Claude\Lister-Bridge" checkout tier3-v2-roadmap
git -C "C:\Claude\Lister-Bridge" pull --ff-only
git -C "C:\Claude\Lister-Bridge" checkout -b codex/safety-kernel
```

Confirm the baseline before the first prompt (expect exit 0, 263 tests collected):

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Claude\Lister-Bridge\scripts\verify.ps1"
```

Open `C:\Claude\Lister-Bridge` in the Codex app. Use GPT-6 Astra with reasoning `max` for the task prompts and `ultra` for the review prompt at the end. Paste one prompt per Codex thread. Keep each thread open until Fable has reviewed that task; fix-up instructions go back into the same thread.

## Order and parallelism

| Step | Task | Issue | Runs | Why |
| --- | --- | --- | --- | --- |
| 1 | T-005 Checkpoint eBay publication | [#12](https://github.com/GhengisPliskin/Lister-Bridge/issues/12) | alone | Owns `state_store.py` and `orchestrator.py`; everything else builds on its claim and checkpoint tables |
| 2 | T-006 Persist review candidates | [#13](https://github.com/GhengisPliskin/Lister-Bridge/issues/13) | first of the pair | Defines `ReviewCandidate`, blockers, overrides |
| 2 | T-007 Aspects and preflight | [#14](https://github.com/GhengisPliskin/Lister-Bridge/issues/14) | may start in parallel with T-006 in a `git worktree`; rebase onto T-006 and commit after it | File surfaces are disjoint; its editable blockers must use T-006's blocker shape |
| 3 | T-008 Drafts and ingestion | [#15](https://github.com/GhengisPliskin/Lister-Bridge/issues/15) | after T-006 and T-007 | Touches `orchestrator.py` and `ui/review.py` after both |
| 4 | T-009 Review queue UI | [#16](https://github.com/GhengisPliskin/Lister-Bridge/issues/16) | last | Consumes all four |
| 5 | R1 self-review | none | after T-009 | Findings for Fable, not fixes |

Inside each task, Astra may fan out (builder, independent QA, adversarial critic) as it sees fit. Constraints on the fan-out: parallel writers need disjoint files or a worktree; one agent integrates and commits; QA writes only under `.team/evidence/T-xxx/`; the critic writes nothing.

## After each task

1. Codex reports "committed on codex/safety-kernel" and "READY-FOR-QA". Confirm with `git -C "C:\Claude\Lister-Bridge" log --oneline -3`.
2. Tell Fable: "T-00x is READY-FOR-QA on codex/safety-kernel." Fable reviews the diff and the evidence, runs the verifier, and either marks the task `DONE`, merges to `tier3-v2-roadmap`, and pushes, or gives you a delta prompt to paste into the same Codex thread.
3. Do not push from Codex. Do not merge yourself. Codex never commits to `main` or `tier3-v2-roadmap`.

If Codex stops with a question, answer it from `.team/PLAN.md` if the answer is there; otherwise bring the question to Fable. Two failed build-to-QA cycles on one task is a mandatory stop.

## Shared rules block

Every prompt below ends with this block. This copy is for reference.

```xml
<repo_rules>
You are working in C:\Claude\Lister-Bridge on branch codex/safety-kernel. Confirm with `git branch --show-current` before editing; if it is not codex/safety-kernel, stop and report.
If `git status --porcelain` shows uncommitted changes you did not make (other than the untracked Test.pdf, which you never open, stage, or delete), stop and report; never discard or overwrite them.
Read AGENTS.md, .team/TEAM_PROTOCOL.md, .team/PLAN.md, and .team/STATE.md first. The PLAN section for your task is the acceptance contract; the linked GitHub issue cannot expand it. docs/FMEA.md constraints (PI-xxx) are immutable; a conflict means stop and report an amendment proposal, never a workaround.
Python 3.12 via .venv-py312. Canonical verifier: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/verify.ps1` (must exit 0 before every commit). Targeted runs: `.venv-py312\Scripts\python.exe -m pytest -q -p no:cacheprovider -o addopts= --basetemp=.test-tmp\<name> tests\<file>.py`. Never run pytest without a fresh --basetemp under .test-tmp.
Never read or write .env, any credential file, or %APPDATA%\ListerBridge. Tests inject temporary settings paths, temporary SQLite files, and fake credentials only. Never construct a production eBay client; sandbox is the only environment. Never make a live network call.
Never edit main, docs/FMEA.md, docs/Ebay lister bridge master plan.md, KEY_DECISION_LOG.md, CODE_DECISION_LOG.md, ARCHITECTURE.md (Fable updates it at merge), or files outside your task's Files list. Code decisions go to working/CODE_DECISIONS_PATCH.md, new issues you discover go to working/ISSUE_QUEUE.md, stale facts you notice go to working/DOCUMENT_DRIFT_LOG.md.
Every .py file keeps the CLAUDE.md comment standard: module docstring with Purpose, Primary Responsibilities, Key Interfaces, FMEA Constraints Enforced; function docstrings with Args, Returns, Side Effects, FMEA Constraints; plain-English block comments. Never remove, truncate, or rewrite existing comments.
Status: set your task to IN-FLIGHT in .team/PLAN.md when you start and READY-FOR-QA when your independent QA passes; never DONE. Write .team/handoffs/T-xxx.md (changed files, verification table with exact commands and results, risk boundaries, remaining work) and .team/evidence/T-xxx/qa.md (per-AC verdict table, reproduction commands, observed output) before committing. Update .team/STATE.md so a fresh agent reading only .team/ knows what happened.
Commit on codex/safety-kernel with a message starting "T-00x: ". One commit per task is preferred; stage files by name. Never push. Never commit to main or tier3-v2-roadmap. Never rewrite history.
Finish with: 1) summary of the change, 2) files touched, 3) the exact tail of the verifier output and each targeted test command with its result, 4) residual risks or questions for the reviewer, ending with "This changes if [specific condition]."
</repo_rules>
```

---

## Prompt T-005 — Checkpoint eBay publication (issue #12)

```xml
<task>
Implement task T-005 (Checkpoint eBay publication) from .team/PLAN.md, bound to GitHub issue #12. FMEA constraints PI-010 (no duplicate publication) and PI-013 (composite identity) govern every design choice. Expected end state:
- src/contracts/state.py gains the composite publication identity (environment, seller account, marketplace, target, SKU) plus checkpoint fields for image URLs, offer ID, listing ID, and claim status. SKU-only joins are forbidden anywhere.
- src/core/state_store.py adds a schema version 2 migration with its own complete manifest in _SCHEMA_MANIFESTS (T-004 rejects any version without one), an atomic claim primitive under BEGIN IMMEDIATE that only one concurrent caller wins for the same composite key while a different account claims the same SKU freely, checkpoint writes after each remote milestone, and claim release on terminal outcomes. Read .team/handoffs/T-004.md and .team/evidence/T-004/critic-cycle-4.md before touching this file; the manifest and canonical-SQL validators are fail-closed on purpose.
- While in state_store.py, close the queued T-004 follow-ups listed in working/ISSUE_QUEUE.md under "State-store hardening follow-ups from the T-004 cycle-4 adversarial review": C-1 (no backup per failed launch of an unchanged malformed legacy DB), C-2 (lock timeout reported as a lock timeout), N-3 (_is_lock_contention respects a present sqlite_errorcode), N-8 (_PATH_LOCKS does not retain :memory: URIs). Record which rule you chose for C-1 in working/CODE_DECISIONS_PATCH.md.
- src/api/ebay_client.py: publication is at-least-once with reconciliation. Before createInventoryItem, createOffer, or publishOffer on retry, look the deterministic SKU up (getInventoryItem / getOffers by SKU) and resume from the recorded milestone instead of creating again. Retry never produces a second offer or listing.
- src/core/orchestrator.py: _auto_publish and any approve path claim first, publish through checkpoints, and release; the check-then-act path is gone.
- tests/test_publication_recovery.py: concurrency test (two threads, one adapter invocation, same SKU under another account allowed); injected failure after each milestone with checkpoint assertions; retry reconciliation ending in exactly one listing ID; restart fixture (new StateStore over the same file) calling the publisher twice and recording one listing. Use a fake eBay client that records calls; no network.
Files in scope: exactly the five in the PLAN Files list, plus .team/PLAN.md status, .team/STATE.md, .team/handoffs/T-005.md, .team/evidence/T-005/, working/CODE_DECISIONS_PATCH.md, working/ISSUE_QUEUE.md.
Do not touch: src/ui/, src/ai/, src/marketplace/, docs/, main.
</task>

<completeness_contract>
Resolve all four acceptance criteria and the four T-004 follow-ups. Do not stop after the claim primitive; the checkpoint, reconciliation, and restart paths are the point of the task.
</completeness_contract>

<verification_loop>
Run tests/test_state_store.py, tests/test_state_store_concurrency.py (three fresh basetemps), tests/test_publication_recovery.py, tests/test_orchestrator.py, tests/test_ebay_client.py, then the canonical verifier. Have an independent QA agent reproduce each AC from a fresh basetemp and write .team/evidence/T-005/qa.md; have a critic try to produce a second listing (crash between offer create and publish, two approvals, process restart mid-publish). Do not commit failing work.
</verification_loop>

<action_safety>
No live eBay calls. No production client. The T-004 validators must not be weakened to make version 2 fit; add a manifest and canonical definitions for version 2 instead.
</action_safety>

<missing_context_gating>
Read src/core/state_store.py, src/api/ebay_client.py, src/core/orchestrator.py, src/contracts/state.py, and tests/test_state_store.py in full before designing. Do not guess the existing claim, token-cache, or migration APIs.
</missing_context_gating>

<repo_rules>
You are working in C:\Claude\Lister-Bridge on branch codex/safety-kernel. Confirm with `git branch --show-current` before editing; if it is not codex/safety-kernel, stop and report.
If `git status --porcelain` shows uncommitted changes you did not make (other than the untracked Test.pdf, which you never open, stage, or delete), stop and report; never discard or overwrite them.
Read AGENTS.md, .team/TEAM_PROTOCOL.md, .team/PLAN.md, and .team/STATE.md first. The PLAN section for your task is the acceptance contract; the linked GitHub issue cannot expand it. docs/FMEA.md constraints (PI-xxx) are immutable; a conflict means stop and report an amendment proposal, never a workaround.
Python 3.12 via .venv-py312. Canonical verifier: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/verify.ps1` (must exit 0 before every commit). Targeted runs: `.venv-py312\Scripts\python.exe -m pytest -q -p no:cacheprovider -o addopts= --basetemp=.test-tmp\<name> tests\<file>.py`. Never run pytest without a fresh --basetemp under .test-tmp.
Never read or write .env, any credential file, or %APPDATA%\ListerBridge. Tests inject temporary settings paths, temporary SQLite files, and fake credentials only. Never construct a production eBay client; sandbox is the only environment. Never make a live network call.
Never edit main, docs/FMEA.md, docs/Ebay lister bridge master plan.md, KEY_DECISION_LOG.md, CODE_DECISION_LOG.md, ARCHITECTURE.md (Fable updates it at merge), or files outside your task's Files list. Code decisions go to working/CODE_DECISIONS_PATCH.md, new issues you discover go to working/ISSUE_QUEUE.md, stale facts you notice go to working/DOCUMENT_DRIFT_LOG.md.
Every .py file keeps the CLAUDE.md comment standard: module docstring with Purpose, Primary Responsibilities, Key Interfaces, FMEA Constraints Enforced; function docstrings with Args, Returns, Side Effects, FMEA Constraints; plain-English block comments. Never remove, truncate, or rewrite existing comments.
Status: set your task to IN-FLIGHT in .team/PLAN.md when you start and READY-FOR-QA when your independent QA passes; never DONE. Write .team/handoffs/T-xxx.md (changed files, verification table with exact commands and results, risk boundaries, remaining work) and .team/evidence/T-xxx/qa.md (per-AC verdict table, reproduction commands, observed output) before committing. Update .team/STATE.md so a fresh agent reading only .team/ knows what happened.
Commit on codex/safety-kernel with a message starting "T-00x: ". One commit per task is preferred; stage files by name. Never push. Never commit to main or tier3-v2-roadmap. Never rewrite history.
Finish with: 1) summary of the change, 2) files touched, 3) the exact tail of the verifier output and each targeted test command with its result, 4) residual risks or questions for the reviewer, ending with "This changes if [specific condition]."
</repo_rules>
```

---

## Prompt T-006 — Persist fail-closed review candidates (issue #13)

```xml
<task>
Implement task T-006 (Persist fail-closed review candidates) from .team/PLAN.md, bound to GitHub issue #13, on top of the committed T-005. FMEA constraints PI-003 (frozen candidates), PI-004 (defects_found negative confirmation), PI-005 (strict schema), PI-006 (deterministic floor), PI-007 (explicit confirmation) govern the design. Expected end state:
- src/contracts/review.py defines ReviewCandidate holding the original vision output, pricing evidence, marketplace payload, target, validation result, required confirmations, and overrides, with hard blockers and soft blockers as distinct typed lists. A soft override carries operator, reason, and timestamp, all required; an override can never remove a hard blocker.
- src/contracts/vision.py: defects_found missing or malformed (null, string, non-list) is a hard blocker; an explicit empty list is valid and distinguishable from absent. Three named contract tests prove it.
- src/ai/margin_guard.py: unknown condition, incomplete cost, fee, or profit inputs, and a final price below the (cost + fees) × 1.15 floor each produce a hard blocker rather than a silent default.
- src/core/state_store.py: a schema version 3 migration with its own manifest persists ReviewCandidate rows keyed by the T-005 composite identity; candidates reload after a new StateStore over the same file with every field equal.
- tests/test_review_candidate.py: round-trip test, the three defects_found tests, a parameterized blocker test, and override validation tests.
- Manual-paste replies (src/ai/manual_provider.py) are out of scope; do not touch them. Note in your handoff if candidate persistence would change when they are persisted later.
Files in scope: exactly the five in the PLAN Files list, plus .team/PLAN.md status, .team/STATE.md, .team/handoffs/T-006.md, .team/evidence/T-006/, working/CODE_DECISIONS_PATCH.md, working/ISSUE_QUEUE.md.
Do not touch: src/ui/, src/api/, src/marketplace/, src/ai/manual_provider.py, docs/, main.
</task>

<completeness_contract>
Resolve all four acceptance criteria including persistence across restart. Blockers that exist only in memory do not satisfy AC1.
</completeness_contract>

<verification_loop>
Run tests/test_review_candidate.py, tests/test_contracts.py, tests/test_margin_guard.py, tests/test_vision_agent.py, tests/test_state_store.py, then the canonical verifier. Independent QA reproduces each AC from a fresh basetemp into .team/evidence/T-006/qa.md; a critic tries to clear a hard blocker through an override, a malformed defects_found, or a candidate edited after freezing. Do not commit failing work.
</verification_loop>

<action_safety>
The floor multiplier stays 1.15 and stays deterministic. No new AI calls. Version 3 gets its own manifest; T-004 and T-005 validators are not weakened.
</action_safety>

<missing_context_gating>
Read src/contracts/vision.py, src/contracts/pricing.py, src/ai/margin_guard.py, src/ai/vision_agent.py, and the T-005 additions to src/core/state_store.py in full before designing.
</missing_context_gating>

<repo_rules>
You are working in C:\Claude\Lister-Bridge on branch codex/safety-kernel. Confirm with `git branch --show-current` before editing; if it is not codex/safety-kernel, stop and report.
If `git status --porcelain` shows uncommitted changes you did not make (other than the untracked Test.pdf, which you never open, stage, or delete), stop and report; never discard or overwrite them.
Read AGENTS.md, .team/TEAM_PROTOCOL.md, .team/PLAN.md, and .team/STATE.md first. The PLAN section for your task is the acceptance contract; the linked GitHub issue cannot expand it. docs/FMEA.md constraints (PI-xxx) are immutable; a conflict means stop and report an amendment proposal, never a workaround.
Python 3.12 via .venv-py312. Canonical verifier: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/verify.ps1` (must exit 0 before every commit). Targeted runs: `.venv-py312\Scripts\python.exe -m pytest -q -p no:cacheprovider -o addopts= --basetemp=.test-tmp\<name> tests\<file>.py`. Never run pytest without a fresh --basetemp under .test-tmp.
Never read or write .env, any credential file, or %APPDATA%\ListerBridge. Tests inject temporary settings paths, temporary SQLite files, and fake credentials only. Never construct a production eBay client; sandbox is the only environment. Never make a live network call.
Never edit main, docs/FMEA.md, docs/Ebay lister bridge master plan.md, KEY_DECISION_LOG.md, CODE_DECISION_LOG.md, ARCHITECTURE.md (Fable updates it at merge), or files outside your task's Files list. Code decisions go to working/CODE_DECISIONS_PATCH.md, new issues you discover go to working/ISSUE_QUEUE.md, stale facts you notice go to working/DOCUMENT_DRIFT_LOG.md.
Every .py file keeps the CLAUDE.md comment standard: module docstring with Purpose, Primary Responsibilities, Key Interfaces, FMEA Constraints Enforced; function docstrings with Args, Returns, Side Effects, FMEA Constraints; plain-English block comments. Never remove, truncate, or rewrite existing comments.
Status: set your task to IN-FLIGHT in .team/PLAN.md when you start and READY-FOR-QA when your independent QA passes; never DONE. Write .team/handoffs/T-xxx.md (changed files, verification table with exact commands and results, risk boundaries, remaining work) and .team/evidence/T-xxx/qa.md (per-AC verdict table, reproduction commands, observed output) before committing. Update .team/STATE.md so a fresh agent reading only .team/ knows what happened.
Commit on codex/safety-kernel with a message starting "T-00x: ". One commit per task is preferred; stage files by name. Never push. Never commit to main or tier3-v2-roadmap. Never rewrite history.
Finish with: 1) summary of the change, 2) files touched, 3) the exact tail of the verifier output and each targeted test command with its result, 4) residual risks or questions for the reviewer, ending with "This changes if [specific condition]."
</repo_rules>
```

---

## Prompt T-007 — Validate category aspects and publication input (issue #14)

```xml
<task>
Implement task T-007 (Validate category aspects and publication input) from .team/PLAN.md, bound to GitHub issue #14. FMEA constraints PI-005 (aspect enums) and PI-009 (pre-submit validation) govern the design. You may start in a git worktree in parallel with T-006 because the file surfaces are disjoint, but your editable blockers must use the hard/soft blocker types T-006 defines in src/contracts/review.py; rebase onto the T-006 commit and integrate before committing. Expected end state:
- src/api/ebay_client.py: Taxonomy getItemAspectsForCategory results are cached by (environment, marketplace, category) for seven days through the StateStore or a file cache under the injected settings path, with an injectable clock. A clock test observes one request before expiry and two after.
- src/contracts/ebay.py: a preflight validator for title, description, condition, quantity, media manifest, category, business policies, and location that runs before the first remote write; each invalid fixture leaves the fake client with zero writes. Missing required aspects come back as editable blockers naming each aspect.
- src/marketplace/ebay_adapter.py runs the preflight; draft adapters (via the shared base) reject a missing title, description, price, or image manifest.
- src/ui/review.py: the minimum change to surface aspect blockers as editable fields; the full queue rendering is T-009.
- tests/test_ebay_preflight.py covers the cache clock, the two-missing-aspects fixture, every invalid-input fixture with zero writes, and adapter validation.
Files in scope: exactly the five in the PLAN Files list, plus .team/PLAN.md status, .team/STATE.md, .team/handoffs/T-007.md, .team/evidence/T-007/, working/CODE_DECISIONS_PATCH.md, working/ISSUE_QUEUE.md.
Do not touch: src/core/state_store.py schema (request a migration through the T-006 owner or use the existing key-value surface), src/core/orchestrator.py, src/ai/, docs/, main.
</task>

<completeness_contract>
Resolve all four acceptance criteria. "Zero writes" means the fake client records no createInventoryItem, createOffer, publishOffer, or media upload for every invalid fixture, not just one.
</completeness_contract>

<verification_loop>
Run tests/test_ebay_preflight.py, tests/test_ebay_client.py, tests/test_marketplace.py, tests/test_review.py, then the canonical verifier. Independent QA reproduces each AC into .team/evidence/T-007/qa.md; a critic tries to reach a remote write with an invalid payload or a stale aspect cache. Do not commit failing work.
</verification_loop>

<action_safety>
No live Taxonomy calls; fixtures only. Sandbox base URLs only. Do not change T-005 publication or claim behavior.
</action_safety>

<missing_context_gating>
Read src/api/ebay_client.py, src/contracts/ebay.py, src/marketplace/base.py, src/marketplace/ebay_adapter.py, src/marketplace/other_adapter.py, and src/contracts/review.py (from T-006) in full before designing.
</missing_context_gating>

<repo_rules>
You are working in C:\Claude\Lister-Bridge on branch codex/safety-kernel. Confirm with `git branch --show-current` before editing; if it is not codex/safety-kernel, stop and report.
If `git status --porcelain` shows uncommitted changes you did not make (other than the untracked Test.pdf, which you never open, stage, or delete), stop and report; never discard or overwrite them.
Read AGENTS.md, .team/TEAM_PROTOCOL.md, .team/PLAN.md, and .team/STATE.md first. The PLAN section for your task is the acceptance contract; the linked GitHub issue cannot expand it. docs/FMEA.md constraints (PI-xxx) are immutable; a conflict means stop and report an amendment proposal, never a workaround.
Python 3.12 via .venv-py312. Canonical verifier: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/verify.ps1` (must exit 0 before every commit). Targeted runs: `.venv-py312\Scripts\python.exe -m pytest -q -p no:cacheprovider -o addopts= --basetemp=.test-tmp\<name> tests\<file>.py`. Never run pytest without a fresh --basetemp under .test-tmp.
Never read or write .env, any credential file, or %APPDATA%\ListerBridge. Tests inject temporary settings paths, temporary SQLite files, and fake credentials only. Never construct a production eBay client; sandbox is the only environment. Never make a live network call.
Never edit main, docs/FMEA.md, docs/Ebay lister bridge master plan.md, KEY_DECISION_LOG.md, CODE_DECISION_LOG.md, ARCHITECTURE.md (Fable updates it at merge), or files outside your task's Files list. Code decisions go to working/CODE_DECISIONS_PATCH.md, new issues you discover go to working/ISSUE_QUEUE.md, stale facts you notice go to working/DOCUMENT_DRIFT_LOG.md.
Every .py file keeps the CLAUDE.md comment standard: module docstring with Purpose, Primary Responsibilities, Key Interfaces, FMEA Constraints Enforced; function docstrings with Args, Returns, Side Effects, FMEA Constraints; plain-English block comments. Never remove, truncate, or rewrite existing comments.
Status: set your task to IN-FLIGHT in .team/PLAN.md when you start and READY-FOR-QA when your independent QA passes; never DONE. Write .team/handoffs/T-xxx.md (changed files, verification table with exact commands and results, risk boundaries, remaining work) and .team/evidence/T-xxx/qa.md (per-AC verdict table, reproduction commands, observed output) before committing. Update .team/STATE.md so a fresh agent reading only .team/ knows what happened.
Commit on codex/safety-kernel with a message starting "T-00x: ". One commit per task is preferred; stage files by name. Never push. Never commit to main or tier3-v2-roadmap. Never rewrite history.
Finish with: 1) summary of the change, 2) files touched, 3) the exact tail of the verifier output and each targeted test command with its result, 4) residual risks or questions for the reviewer, ending with "This changes if [specific condition]."
</repo_rules>
```

---

## Prompt T-008 — Decouple drafts and harden ingestion (issue #15)

```xml
<task>
Implement task T-008 (Decouple drafts and harden ingestion) from .team/PLAN.md, bound to GitHub issue #15, on top of the committed T-006 and T-007. FMEA constraints PI-001 (Drive resilience) and PI-006 (floor) govern the design. Expected end state:
- src/core/orchestrator.py: Facebook and Mercari draft flows run with every eBay setting absent (no EbayClient construction, no eBay adapter import side effects). A credential-free integration test exits 0. The headless entry orchestrator.main() constructs the provider from AI_PROVIDER instead of always GeminiProvider (queued T-027 follow-up; record the decision).
- Pricing: when no active comps exist, the item requires either a manual comp or an audited no-comp override (operator, reason, timestamp, persisted on the T-006 candidate), and the final price never drops below the floor.
- Retry policy for Drive and eBay calls: network errors, 429, and 5xx retry at most three times, honoring Retry-After when present and jittered exponential backoff otherwise; other 4xx errors do not retry. Fake-clock tests assert exact call counts and sleeps.
- src/core/drive_fetcher.py: a failed batch is recorded as an error and does not discard sibling batches' payloads; archive_batch is called only after every item in the batch is terminal. A mixed-batch test asserts payloads, errors, and archive calls.
- src/marketplace/other_adapter.py and src/ui/review.py: minimum changes so drafts and the no-comp override are reachable.
- tests/test_ingestion_resilience.py covers all four ACs.
Files in scope: exactly the five in the PLAN Files list, plus .team/PLAN.md status, .team/STATE.md, .team/handoffs/T-008.md, .team/evidence/T-008/, working/CODE_DECISIONS_PATCH.md, working/ISSUE_QUEUE.md.
Do not touch: src/core/state_store.py schema, src/api/ebay_auth.py, src/ai/manual_provider.py internals, docs/, main.
</task>

<completeness_contract>
Resolve all four acceptance criteria. The no-retry-on-4xx and archive-only-after-terminal rules are the ones most easily left half-done; prove both with call-count assertions.
</completeness_contract>

<verification_loop>
Run tests/test_ingestion_resilience.py, tests/test_orchestrator.py, tests/test_drive_fetcher.py, tests/test_marketplace.py, tests/test_integration.py, tests/test_manual_provider.py, then the canonical verifier. Independent QA reproduces each AC into .team/evidence/T-008/qa.md; a critic tries to archive a batch with a non-terminal item, retry a 401, or price below floor through the override. Do not commit failing work.
</verification_loop>

<action_safety>
No live Drive or eBay calls. Do not change the T-005 claim or checkpoint semantics; wrap them.
</action_safety>

<missing_context_gating>
Read src/core/orchestrator.py, src/core/drive_fetcher.py, src/marketplace/other_adapter.py, src/ai/margin_guard.py, and working/ISSUE_QUEUE.md (the archive_batch and orchestrator error-handling entries) in full before designing.
</missing_context_gating>

<repo_rules>
You are working in C:\Claude\Lister-Bridge on branch codex/safety-kernel. Confirm with `git branch --show-current` before editing; if it is not codex/safety-kernel, stop and report.
If `git status --porcelain` shows uncommitted changes you did not make (other than the untracked Test.pdf, which you never open, stage, or delete), stop and report; never discard or overwrite them.
Read AGENTS.md, .team/TEAM_PROTOCOL.md, .team/PLAN.md, and .team/STATE.md first. The PLAN section for your task is the acceptance contract; the linked GitHub issue cannot expand it. docs/FMEA.md constraints (PI-xxx) are immutable; a conflict means stop and report an amendment proposal, never a workaround.
Python 3.12 via .venv-py312. Canonical verifier: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/verify.ps1` (must exit 0 before every commit). Targeted runs: `.venv-py312\Scripts\python.exe -m pytest -q -p no:cacheprovider -o addopts= --basetemp=.test-tmp\<name> tests\<file>.py`. Never run pytest without a fresh --basetemp under .test-tmp.
Never read or write .env, any credential file, or %APPDATA%\ListerBridge. Tests inject temporary settings paths, temporary SQLite files, and fake credentials only. Never construct a production eBay client; sandbox is the only environment. Never make a live network call.
Never edit main, docs/FMEA.md, docs/Ebay lister bridge master plan.md, KEY_DECISION_LOG.md, CODE_DECISION_LOG.md, ARCHITECTURE.md (Fable updates it at merge), or files outside your task's Files list. Code decisions go to working/CODE_DECISIONS_PATCH.md, new issues you discover go to working/ISSUE_QUEUE.md, stale facts you notice go to working/DOCUMENT_DRIFT_LOG.md.
Every .py file keeps the CLAUDE.md comment standard: module docstring with Purpose, Primary Responsibilities, Key Interfaces, FMEA Constraints Enforced; function docstrings with Args, Returns, Side Effects, FMEA Constraints; plain-English block comments. Never remove, truncate, or rewrite existing comments.
Status: set your task to IN-FLIGHT in .team/PLAN.md when you start and READY-FOR-QA when your independent QA passes; never DONE. Write .team/handoffs/T-xxx.md (changed files, verification table with exact commands and results, risk boundaries, remaining work) and .team/evidence/T-xxx/qa.md (per-AC verdict table, reproduction commands, observed output) before committing. Update .team/STATE.md so a fresh agent reading only .team/ knows what happened.
Commit on codex/safety-kernel with a message starting "T-00x: ". One commit per task is preferred; stage files by name. Never push. Never commit to main or tier3-v2-roadmap. Never rewrite history.
Finish with: 1) summary of the change, 2) files touched, 3) the exact tail of the verifier output and each targeted test command with its result, 4) residual risks or questions for the reviewer, ending with "This changes if [specific condition]."
</repo_rules>
```

---

## Prompt T-009 — Render a truthful persistent review queue (issue #16)

```xml
<task>
Implement task T-009 (Render a truthful persistent review queue) from .team/PLAN.md, bound to GitHub issue #16, on top of the committed T-005 through T-008. FMEA constraints PI-007 (explicit confirmation) and PI-008 (progressive disclosure) govern the design. Expected end state:
- src/ui/review.py exposes a pure view-model (no Streamlit calls) built from the persisted ReviewCandidate: defects, dropped fields, hard and soft blockers, comp provenance, floor, required confirmations, and overrides. A view-model test asserts every field.
- src/ui/app.py renders the queue from the view-model with progressive disclosure (summary first, raw JSON behind an expander), keeps the T-027 manual paste cards working, and reloads pending candidates from SQLite in a new session. A restart integration test proves it without Streamlit's runtime.
- src/core/settings.py: sandbox state is always visible; every production selection is rejected during this roadmap even when ALLOW_EBAY_PRODUCTION=true; settings tests cover absent, false, and true with zero production client construction. Document the flag in .env.example.
- Approval stays disabled until every hard blocker and required confirmation is resolved; a truth-table test covers the gate.
- tests/test_review_ui_logic.py holds the view-model, restart, and gate tests; existing tests/test_review.py and tests/test_settings.py keep passing.
Files in scope: exactly the five in the PLAN Files list, plus .team/PLAN.md status, .team/STATE.md, .team/handoffs/T-009.md, .team/evidence/T-009/, working/CODE_DECISIONS_PATCH.md, working/ISSUE_QUEUE.md.
Do not touch: src/core/state_store.py schema, src/api/, src/ai/, src/marketplace/, docs/, main.
</task>

<completeness_contract>
Resolve all four acceptance criteria. Reload-after-restart and the production rejection are the two that ship half-done most often; both need tests that construct a second session.
</completeness_contract>

<verification_loop>
Run tests/test_review_ui_logic.py, tests/test_review.py, tests/test_settings.py, tests/test_help_content.py, then the canonical verifier. Launch the Streamlit app once with an injected temporary settings path and a fake StateStore seeded with two candidates (one blocked, one approvable) and record what renders in .team/evidence/T-009/qa.md. Independent QA reproduces each AC; a critic tries to approve a blocked candidate, to select production, and to lose a pending candidate across restart. Do not commit failing work.
</verification_loop>

<action_safety>
No real .env, no real StateStore file, no eBay client with real credentials. The UI computes nothing about publication state; it reads the StateStore and the T-006 candidate.
</action_safety>

<missing_context_gating>
Read src/ui/app.py, src/ui/review.py, src/ui/help_content.py, src/core/settings.py, .team/handoffs/T-027.md, and .team/evidence/T-027/smoke-guide.md in full before designing; the manual paste workflow must survive.
</missing_context_gating>

<repo_rules>
You are working in C:\Claude\Lister-Bridge on branch codex/safety-kernel. Confirm with `git branch --show-current` before editing; if it is not codex/safety-kernel, stop and report.
If `git status --porcelain` shows uncommitted changes you did not make (other than the untracked Test.pdf, which you never open, stage, or delete), stop and report; never discard or overwrite them.
Read AGENTS.md, .team/TEAM_PROTOCOL.md, .team/PLAN.md, and .team/STATE.md first. The PLAN section for your task is the acceptance contract; the linked GitHub issue cannot expand it. docs/FMEA.md constraints (PI-xxx) are immutable; a conflict means stop and report an amendment proposal, never a workaround.
Python 3.12 via .venv-py312. Canonical verifier: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/verify.ps1` (must exit 0 before every commit). Targeted runs: `.venv-py312\Scripts\python.exe -m pytest -q -p no:cacheprovider -o addopts= --basetemp=.test-tmp\<name> tests\<file>.py`. Never run pytest without a fresh --basetemp under .test-tmp.
Never read or write .env, any credential file, or %APPDATA%\ListerBridge. Tests inject temporary settings paths, temporary SQLite files, and fake credentials only. Never construct a production eBay client; sandbox is the only environment. Never make a live network call.
Never edit main, docs/FMEA.md, docs/Ebay lister bridge master plan.md, KEY_DECISION_LOG.md, CODE_DECISION_LOG.md, ARCHITECTURE.md (Fable updates it at merge), or files outside your task's Files list. Code decisions go to working/CODE_DECISIONS_PATCH.md, new issues you discover go to working/ISSUE_QUEUE.md, stale facts you notice go to working/DOCUMENT_DRIFT_LOG.md.
Every .py file keeps the CLAUDE.md comment standard: module docstring with Purpose, Primary Responsibilities, Key Interfaces, FMEA Constraints Enforced; function docstrings with Args, Returns, Side Effects, FMEA Constraints; plain-English block comments. Never remove, truncate, or rewrite existing comments.
Status: set your task to IN-FLIGHT in .team/PLAN.md when you start and READY-FOR-QA when your independent QA passes; never DONE. Write .team/handoffs/T-xxx.md (changed files, verification table with exact commands and results, risk boundaries, remaining work) and .team/evidence/T-xxx/qa.md (per-AC verdict table, reproduction commands, observed output) before committing. Update .team/STATE.md so a fresh agent reading only .team/ knows what happened.
Commit on codex/safety-kernel with a message starting "T-00x: ". One commit per task is preferred; stage files by name. Never push. Never commit to main or tier3-v2-roadmap. Never rewrite history.
Finish with: 1) summary of the change, 2) files touched, 3) the exact tail of the verifier output and each targeted test command with its result, 4) residual risks or questions for the reviewer, ending with "This changes if [specific condition]."
</repo_rules>
```

---

## Prompt R1 — Self-review before handing back (`ultra`)

Run this in a fresh Codex thread after T-009 and before telling Fable the chunk is ready. It is a read-only review; it produces findings for Fable to triage, not fixes.

```xml
<task>
You are a skeptical staff engineer reviewing `git diff tier3-v2-roadmap...codex/safety-kernel` in C:\Claude\Lister-Bridge against .team/PLAN.md tasks T-005 through T-009 and docs/FMEA.md constraints PI-003 through PI-010 and PI-013. Find the strongest reasons this should not merge. Cover, in order:
1. Duplicate publication: any path (crash, restart, concurrent approve, retry, different account) that produces a second offer or listing, or a SKU-only join.
2. Fail-closed review: any way a hard blocker, missing defects_found, unknown condition, or below-floor price reaches an approvable state, including through an override.
3. Remote writes before validation: any createInventoryItem, createOffer, publishOffer, or media upload reachable with an invalid payload or stale aspect cache.
4. Persistence: what is lost on restart mid-publish, mid-review, or after a schema-version change; whether every new version has a complete manifest.
5. Production leakage: any construction of a production client or base URL, any read of .env or %APPDATA%.
6. Test honesty: any test whose assertion passes without exercising the AC it names; any comment removed or truncated (Ground Rule 11).
Do not edit any file.
</task>
<grounding_rules>
Cite the file and line for every finding. Label hypotheses.
</grounding_rules>
<dig_deeper_nudge>
After the first issue in each area, check second-order cases: two StateStore instances over one file, the manual paste provider path, drafts with eBay settings absent, and the override path.
</dig_deeper_nudge>
<structured_output_contract>
Numbered findings, highest severity first: ID, severity (blocker / major / minor), file and line, the failure in two sentences, the smallest change that closes it. Nothing else.
</structured_output_contract>
```

Save the output to `.team/evidence/codex-safety-kernel-review.md` (or hand it to Fable) so the findings are triaged before merge.

## What Fable does at review

Per task: fetch nothing (same directory), read the task's handoff and evidence, run the verifier, spot-check the critic's attack list, then mark `DONE` in PLAN, update `ARCHITECTURE.md` and `CODE_DECISION_LOG.md` from the patch file, fast-forward `tier3-v2-roadmap` and `main`, push, and close the issue (D-TEAM-010). A rejected task gets a delta prompt for the same Codex thread.

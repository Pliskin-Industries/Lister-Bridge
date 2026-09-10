# T-004 Adversarial Critic Evidence — Cycle 4

## Outcome

**Verdict: CONCERNS.** No unbacked migration, no lock escape at the retry point, no manifest bypass, and no comment removal were found. Two operational concerns and several notes are recorded for the primary agent's ruling. The critic wrote no repository file; the primary agent transcribed this record from the critic's report on 2026-09-10.

## Confirmed Solid

| Claim | Independent observation |
| --- | --- |
| Builder numbers | 43 state tests passed; 6 concurrency tests passed in five consecutive fresh-basetemp runs. |
| AC3 backup under lock | 8 processes × 5 repetitions on a rollback-mode legacy file: all exit 0, ledger `[1]`, WAL, rows preserved, exactly one backup, zero partials. |
| AC4 WAL activation | Same stress on a nonexistent file: 40 constructors, zero failures. An external reader pinning the legacy file produced a bounded "could not enable WAL mode" error after 5.48 s with no mutation, then a clean retry. The post-assignment mode check is load-bearing: `PRAGMA journal_mode = WAL` can silently return `delete` inside a transaction. |
| Manifest validation | `sqlite_autoindex_*`, `sqlite_sequence`, and `sqlite_stat1` are tolerated; user indexes, views, and triggers are rejected; legacy tables plus an empty ledger are rejected; a version-0 ledger row smuggled under `ignore_check_constraints` is rejected. |
| Regressions | `:memory:` keeper, keeper-only `check_same_thread`, idempotent `close()`, rollback with preserved backup, and the unchanged `_validate_constraint_behavior` signature all hold. |

## Findings

| ID | Severity | Mechanism | Primary ruling |
| --- | --- | --- | --- |
| C-1 | CONCERN | Backup precedes legacy validation, so each failed launch against a persistently malformed legacy database adds another token-bearing snapshot (3 attempts → 3 backups). | Accepted for this task: fail-closed and data-safe; the malformed-legacy test asserts backup-first by design. Queued as a T-005 follow-up (bounded retention or validate-before-backup). |
| C-2 | CONCERN | A constructor waiting at `BEGIN IMMEDIATE` past 5000 ms receives "migration failed and was rolled back" although it migrated nothing. Requires backup plus migration to exceed 5 s. | Accepted: message accuracy only; queued follow-up to distinguish lock timeout from migration failure. |
| N-3 | NOTE | `_is_lock_contention` falls back to message matching even when a definitive non-BUSY/LOCKED code is present; bounded to ≤5 s extra latency; no real SQLite message found. | Queued follow-up: return False when a known code is outside the set. |
| N-4 | NOTE | An operator-added index is rejected as an unexpected object; manifests have no slot for indexes or views. | Intentional design ceiling, documented in the handoff. |
| N-8 | NOTE | `_PATH_LOCKS` retains one lock per `:memory:` store URI. | Negligible in production; queued as a test-hygiene note. |
| N-10 | NOTE | Two cycle-1 docstring sentences were rewritten: the module FMEA line and the class idempotency line. | Ruled acceptable: both sentences claimed a duplicate-publication guarantee the code never provided (T-005 scope); the correction removes a false safety claim and is logged in `working/CODE_DECISIONS_PATCH.md`. |

Notes N-5 (table-less file backed up then rejected), N-6 (external reader blocks first WAL switch, bounded), N-7 (schema-only validation), N-9 (annotation drift on `_validate_constraint_behavior`), and N-11 (working tree contains this session's planning documents, committed separately) were confirmed and carry no action beyond this record. One plausible, unreproduced item: a UNC-hosted database path may yield a URI SQLite rejects in `_create_backup`; `%APPDATA%` is local.

## Boundaries

- Diagnostics ran under `.test-tmp\crit4-*` and the session scratchpad with fake data only.
- No `.env`, credential file, real database, or `%APPDATA%/ListerBridge` access.

## HFE Review

- [x] Chunking: no table exceeds seven rows; notes without action are grouped in one paragraph.
- [x] Signal-to-noise: each row supports a verdict, a mechanism, or a ruling.
- [x] Signaling: bold marks only the verdict.
- [x] Contiguity: each finding's ruling sits in the same row as its mechanism.
- [x] Redundancy: the QA record holds the reproduction commands; this record holds the critic's independent observations and rulings.
- [x] Dual-channel: the handoff's cycle-four flowchart covers the mechanism; no second diagram is needed here.
- [x] Progressive disclosure: verdict precedes evidence, findings, and boundaries.

This changes if a real SQLite error text with a non-BUSY/LOCKED code containing "locked" or "busy" is identified, or if the owner deems unbounded retention of token-bearing backups on a malformed legacy database unacceptable; either promotes its finding to BLOCK.

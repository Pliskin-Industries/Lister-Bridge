# LESSONS

## 2026-07-14 - Poll Yielded Packaging Processes

### Signal

An executable changed after QA captured its size and hash, invalidating two evidence packets before T-003 could close.

### Cause

A yielded orchestration cell was treated as a completed PyInstaller process. QA started a second waited build while the first process could still finish later.

### Guard

- Treat a returned cell or session identifier as active work, not completion.
- Resume only that exact cell or session; never launch a replacement command to obtain missing output.
- Before artifact evidence, confirm zero matching processes, run one waited build, capture its exit guard, and confirm zero matching processes afterward.
- Generate the sidecar from the completed artifact, then reread size, timestamp, digest, and process state after a short stability interval.
- Supersede stale evidence explicitly; never preserve a PASS whose artifact changed after inspection.

This changes if the orchestration layer provides an atomic process-completion result that cannot yield before descendant processes exit.

## 2026-07-15 - SQLite Initialization Must Own Its Observations

### Signal

One spawned constructor failed while activating WAL, and a deterministic interleaving migrated a newly appeared legacy database without a backup.

### Cause

WAL activation and the file-size backup predicate run before the cross-process `BEGIN IMMEDIATE` boundary. The intended serialization therefore does not govern either decision.

### Guard

- Retry only SQLite `BUSY` or `LOCKED` results while establishing WAL, then verify the final journal mode.
- Derive backup eligibility from schema state observed after cross-process serialization.
- Test both races deterministically in addition to repeated spawned-process runs.
- Never treat three passing repetitions as proof when one independent repetition fails.

This changes if SQLite provides one atomic operation that establishes WAL, acquires the migration lock, and exposes the locked pre-migration schema.

## 2026-07-15 - Every Migration Version Needs a Target Manifest

### Signal

A synthetic version-2 migration stamped a preexisting malformed table because post-migration validation still inspected only version-1 objects.

### Cause

Migration statements and schema expectations are separate, and the plan does not require one complete target manifest for every declared version.

### Guard

- Require a version-specific column and canonical-SQL manifest for every migration version.
- Validate the current manifest before migration and the target manifest before stamping each new version.
- Reject a migration plan whose version sequence and manifest sequence differ.
- Test preexisting malformed target objects and transactional rollback for each new version.

This changes if future migration DDL becomes intrinsically self-verifying and cannot silently preserve incompatible preexisting objects.

## 2026-09-10 - Verification Interpreters Must Not Live in Temp

### Signal

Eight weeks after T-003 closed, `.venv-py312\Scripts\python.exe` exited with `0xC0000135` and no test could run. The base interpreter directory still existed but held only `python.exe` and one runtime DLL.

### Cause

The Python 3.12 baseline was bootstrapped into `%TEMP%\ListerBridge-Python312`. Windows Temp cleanup removed the DLLs and standard library while leaving the directory, so the venv looked intact but could not start.

### Guard

- Install verification interpreters under a durable path such as `%LOCALAPPDATA%\Programs\Python` or the repo's ignored `.tools\` directory, never under `%TEMP%`.
- Have `scripts/verify.ps1` execute the chosen interpreter with `--version` before trusting it, and print a rebuild instruction when the launch fails.
- Record the interpreter path and its durability in the QA evidence that establishes a baseline.

This changes if the verification interpreter is provisioned fresh by CI on every run and local runs are no longer evidence.

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

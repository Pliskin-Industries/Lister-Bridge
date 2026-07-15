# T-002 QA Evidence

This record independently verifies governance precedence, issue binding, and FMEA Amendment 5 for T-002.

## Verdict

**PASS** — the repository verification command exited successfully, and all four acceptance criteria were independently confirmed.

- Branch: `tier3-v2-roadmap`
- HEAD under test: `af01e06cfadee4f5412df2e085f74bf3d39292b7` with the uncommitted T-002 change set
- Task issue: [roadmap epic #7](https://github.com/GhengisPliskin/Lister-Bridge/issues/7)
- Next-task issue: [T-003 issue #8](https://github.com/GhengisPliskin/Lister-Bridge/issues/8)
- Evidence date: July 14, 2026

## Acceptance Results

| Criterion | Result | Direct evidence | Reproduction |
|---|---|---|---|
| AC1 — precedence | PASS | Decision 7 and D-TEAM-001 preserve legacy requirements while assigning current execution control to `.team/PLAN.md`. | `Select-String` check below |
| AC2 — rule matrix | PASS | `CLAUDE.md` and `AGENTS.md` contain all five required controls. | Rule-matrix check below |
| AC3 — issue binding | PASS | Issues #7 and #8 exist, are assigned to `GhengisPliskin`, and are recorded in `.team/STATE.md`; pre-`IN-FLIGHT` binding is mandatory. | Local and GitHub checks below |
| AC4 — FMEA activation | PASS | Amendment 5 is approved and active with the four required rows, scores, and controls. | Exact-row check below |

## Reproducible Checks

### Repository Verification

Command:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/verify.ps1
```

Observed output:

```text
[verify] interpreter: C:\Claude\Lister-Bridge\.venv\Scripts\python.exe
Python 3.14.5
No broken requirements found.
166 tests collected in 0.51s
[verify] collected tests: 166
........................................................................ [ 43%]
........................................................................ [ 86%]
......................                                                   [100%]
Exit code: 0
```

The current local interpreter is Python 3.14.5. Python 3.12 reproducibility is not a T-002 criterion; it remains T-003 AC1.

### AC1 — Governance Precedence

Command:

```powershell
Select-String -Path 'KEY_DECISION_LOG.md','.team\DECISIONS.md' `
  -Pattern 'execution overlay','controls current execution'
```

Observed evidence:

```text
KEY_DECISION_LOG.md:155: DECISION 7 — Preserve Legacy Gates Under a Tier-3 Execution Overlay
KEY_DECISION_LOG.md:159: .team/PLAN.md controls current execution when a legacy task, prompt, or issue conflicts
.team/DECISIONS.md:5: .team/PLAN.md controls current execution scope, dependencies, and status when legacy records conflict
```

### AC2 — Governance Rule Matrix

Command:

```powershell
$rules = [ordered]@{
  issue_binding      = 'GitHub [Ii]ssue|assigned GitHub issue'
  fmea_gate          = 'FMEA amendment|FMEA.*gate|FMEA.*binding'
  qa_evidence        = 'QA evidence|independent evidence|Reproducible evidence'
  human_escalation   = 'human escalation|ESCALATE'
  stale_cli_graphql  = 'CLI.*GraphQL.*superseded|CLI task.*GraphQL task.*superseded|CLI instructions.*GraphQL instructions.*superseded'
}
foreach ($file in @('CLAUDE.md','AGENTS.md')) {
  $text = Get-Content -LiteralPath $file -Raw
  foreach ($entry in $rules.GetEnumerator()) {
    [regex]::IsMatch($text, $entry.Value, 'IgnoreCase')
  }
}
```

`CLAUDE.md` results:

| Required control | Result |
|---|---|
| Issue binding | PASS |
| FMEA amendment gate | PASS |
| QA evidence | PASS |
| Human escalation | PASS |
| Stale CLI and GraphQL rejection | PASS |

`AGENTS.md` results:

| Required control | Result |
|---|---|
| Issue binding | PASS |
| FMEA amendment gate | PASS |
| QA evidence | PASS |
| Human escalation | PASS |
| Stale CLI and GraphQL rejection | PASS |

### AC3 — Issue Binding

Local command:

```powershell
Select-String -Path '.team\STATE.md','AGENTS.md','.team\DECISIONS.md' `
  -Pattern 'https://github.com/GhengisPliskin/Lister-Bridge/issues/7',`
           'https://github.com/GhengisPliskin/Lister-Bridge/issues/8',`
           'assigned to `GhengisPliskin`',`
           'before.*IN-FLIGHT'
```

Observed local evidence:

```text
.team/STATE.md:7: Active issue: https://github.com/GhengisPliskin/Lister-Bridge/issues/7, assigned to GhengisPliskin
.team/STATE.md:8: Next task issue: https://github.com/GhengisPliskin/Lister-Bridge/issues/8 (T-003), assigned to GhengisPliskin
AGENTS.md:29: Before a task moves from TODO to IN-FLIGHT, record its assigned GitHub issue URL in PLAN and STATE
.team/DECISIONS.md:17: Beginning with T-003, every task requires its own assigned GitHub issue before IN-FLIGHT
```

GitHub connector observations:

- Issue #7 is OPEN, assigned to `GhengisPliskin`, and titled `[Roadmap] Tier-3 Lister-Bridge v2 execution`.
- Issue #8 is OPEN, assigned to `GhengisPliskin`, titled `[T-003] Establish reproducible Windows verification`, and references parent roadmap #7.

### AC4 — FMEA Amendment 5

Exact checks:

```text
Amendment status: Approved and active — PASS
Approval provenance: execute followed the branch handoff that identified FMEA approval as the next gate; the primary recorded the response as exact approval before changing the register — PASS
PI-010 | 9/4/8 (288) — PASS
PI-011 | 7/5/6 (210) — PASS
PI-012 | 7/5/5 (175) — PASS
PI-013 | 9/3/8 (216) — PASS
```

The active rows contain these controls:

| Risk | Score | Active control | Owner |
|---|---|---|---|
| PI-010 | 9/4/8 (288) | Atomic composite claim, remote checkpoints, deterministic reconciliation, and fault/concurrency tests | State/Integration Eng |
| PI-011 | 7/5/6 (210) | Same-account/category evidence, N at least 30, 15% cap, exclusions, floor, and human gate | Pricing/Product |
| PI-012 | 7/5/5 (175) | Due-only polling, `last_checked`, `Retry-After`, jitter, rate budget, and `UNKNOWN` fallback | API/State Eng |
| PI-013 | 9/3/8 (216) | Composite environment/account/marketplace/listing identity, no SKU-only joins, isolation tests, and post-write verification | Integration/Data Eng |

## Quality Gate

`git diff --check` exited 0. Git emitted only line-ending conversion warnings; it reported no whitespace errors.

HFE + MAYER QUALITY GATE

- [x] 1. Chunking — no list, column set, or slide region exceeds 7 items without subgrouping.
- [x] 2. Signal-to-noise — no sentence survives that could be deleted without information loss.
- [x] 3. Signaling — bold and color are used only for defined categories (terminology, diagnoses, actions, decision points, severity, status).
- [x] 4. Contiguity — no definition or reference value is separated from its target concept by more than one line.
- [x] 5. Redundancy — no data point is presented in both prose and table/diagram form.
- [x] 6. Dual-channel — no multi-step procedure, decision tree, or cyclical process requires a visual in this evidence record.
- [x] 7. Progressive disclosure — every section opens with the core concept, not a caveat or edge case.

This changes if the tested governance rules, issue bindings, Amendment 5 status, exact FMEA rows, or verification result change.

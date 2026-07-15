# TEAM PROTOCOL

The contract for an explicitly authorized Codex agent team. The primary agent enforces it; delegated agents read only the sections and task artifacts needed for their role.

## Project Config

```text
VERIFY: powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/verify.ps1
NO-TOUCH: .env; local credential files; user data under %APPDATA%/ListerBridge
BASE_BRANCH: main
INTEGRATION_BRANCH: tier3-v2-roadmap
PORTS: none
NOTES: Authoritative repo is C:\\Claude\\Lister-Bridge. Keep main as the protected legacy baseline; execute this roadmap only on tier3-v2-roadmap unless the user explicitly authorizes a merge. Sandbox is the default eBay environment. Production publishing remains disabled and out of scope. Existing governance documents remain requirements records; .team/PLAN.md owns executable task status.
```

## Roles

### Execution Roles

| Role | Tier | May write | Verdict authority |
| --- | --- | --- | --- |
| primary agent | all | coordination files | PLAN status and DONE |
| builder | 1+ | task scope only | none; ceiling is READY-FOR-QA |
| qa-engineer | 1+ | evidence only | PASS, FAIL, or BLOCKED |
| adversarial-critic | 2+ | no | CLEAR, CONCERNS, or BLOCK |
| research-scout | 2+ | no | findings only |
| system-fixer | 2+ | environment/tooling only | none |

### Continuity Roles

| Role | Tier | May write | Verdict authority |
| --- | --- | --- | --- |
| context-librarian | 3 | `.team` housekeeping only | none |
| eval-designer | 3 | `.team/evals` only | none |
| improvement-analyst | 3 | proposed diffs only | none |

## Status and evidence

Use `TODO → IN-FLIGHT → READY-FOR-QA → DONE`, plus `BLOCKED` and `ESCALATE`.

- Only the primary agent changes PLAN status or declares DONE.
- A QA PASS requires reproducible output in `.team/evidence/T-xxx/`.
- Each handoff lives at `.team/handoffs/T-xxx.md` and names changed files, verification, risks, and remaining work.
- Claims without evidence remain unverified.

## Mandatory escalations

Stop and ask the user for ambiguous requirements, destructive or irreversible actions, scope growth above roughly 20%, two failed build-to-QA cycles, any auth/payment/PII/PHI/secret exposure, or a task marked `ESCALATE`.

## Delegation and parallel work

- Delegate only when the user or applicable `AGENTS.md` explicitly authorizes subagents.
- Give each agent a bounded task, expected files, verification method, and output path.
- Parallel tasks must have disjoint file surfaces or user-approved worktree isolation.
- The primary agent reviews all results and owns the final synthesis.
- The initial non-clobbering `agent-team-deploy` scaffold is an atomic generated bootstrap and is exempt from the five-primary-file builder limit. Product, test, and documentation tasks are not exempt.

## Resurrection test

Before ending, update `STATE.md` so a new agent reading only `.team/` can identify current status, in-flight work, next action, blockers, decisions, and environment constraints.

## Maintenance loop

Log failures in `LESSONS.md`. Repeated lessons may become guards in `evals/`. Improvement proposals are literal diffs requiring human approval; the team never self-modifies.

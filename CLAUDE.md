# CLAUDE.md — Lister-Bridge Hybrid Agent Session Briefing

This file is read automatically by Claude Code at every session start.
Read it completely before taking any action.

---

## Project Identity

**Repo:** `GhengisPliskin/Lister-Bridge`
**Stack:** Python 3, Google GenAI SDK, Google Drive API, eBay REST API (Sell Inventory + Media)
**Master Plan:** `docs/Ebay lister bridge master plan.md`

## Current Execution Overlay

The Tier-3 workspace adds evidence-gated execution without replacing the product and risk records.

1. Read `AGENTS.md`, `.team/TEAM_PROTOCOL.md`, `.team/OPERATOR.md`, `.team/PLAN.md`, and `.team/STATE.md` before starting an execution task.
2. Bind the active T-xxx task to a GitHub issue under roadmap epic #7 before changing code or documentation.
3. Follow the current `.team/PLAN.md` task when an old issue, task registry, or prompt header conflicts with it.
4. Preserve FMEA amendment, QA evidence, and human escalation gates. Builders stop at `READY-FOR-QA`; only the primary agent marks `DONE`.
5. Treat the CLI and eBay GraphQL tasks in issues #5–#6 and their prompt headers as superseded; neither is an executable task in the current PLAN.

---

## Session Types

There are two distinct session types. Determine which one applies before starting.

### Execution Session

Purpose: Code generation and task execution against an open GitHub Issue.

**Startup sequence:**
1. Confirm the active `.team/PLAN.md` task and its assigned GitHub Issue. Load a prompt header only when the current PLAN task explicitly references it.
2. If outside an AI-native IDE, request a current Repomix output (Ground Rule 10).
3. State the Kanban column move: `[Current Column] → In Progress`.
4. Proceed only within the shared scope of the PLAN task and linked Issue.

**File write locations during execution:**
- Code decisions → `working/CODE_DECISIONS_PATCH.md` (never directly to `CODE_DECISION_LOG.md`)
- New Issues discovered → `working/ISSUE_QUEUE.md`
- Stale facts detected → `working/DOCUMENT_DRIFT_LOG.md`

### Housekeeping Session

Purpose: Process queued work from `working/` files. No code generation. No task execution.

**Startup sequence:**
1. Read `working/ISSUE_QUEUE.md`; create only entries explicitly mapped by the current `.team/PLAN.md`. Mark unmatched legacy entries superseded rather than creating them.
2. Read `working/DOCUMENT_DRIFT_LOG.md` — patch stale facts in listed documents.
3. Prepare a descriptive commit summary; commit only when the active task or user explicitly authorizes it.
4. Reset processed entries from both queue files.

Trigger a Housekeeping session after any planning session or phase gate where queues have accumulated.

---

## Ground Rules

### Task and Risk Controls

| # | Rule |
|---|---|
| 1 | No code or docs without a current PLAN task and an active, assigned Issue. |
| 2 | Code decisions → `working/CODE_DECISIONS_PATCH.md`. Merged at HUMAN gate. |
| 3 | State Kanban column change at start and end of every action. |
| 4 | `ARCHITECTURE.md` updated concurrently with any structural change. |
| 5 | FMEA constraint references (e.g., PI-001) in every affected decision. |
| 6 | Read template files before generating structured documents. |

### Spike, Synchronization, and Code Controls

| # | Rule |
|---|---|
| 7 | `spike` issues cannot reach Done without a linked formalization issue. |
| 8 | FMEA constraints are immutable during execution. |
| 9 | Constraint conflicts → HALT, propose FMEA Amendment. |
| 10 | Ingest a fresh repo map (Repomix) at the start of every execution session. |
| 11 | All `.py` files: module docstring, function docstrings, block comments. Never remove or truncate existing comments. |

---

## Code Comment Standard (Ground Rule 11)

Every `.py` file must include:

```python
"""
Module: filename.py
Purpose: One sentence describing what this module does.
Primary Responsibilities:
  - Responsibility 1
  - Responsibility 2
Key Interfaces:
  - Input: describe inputs
  - Output: describe outputs
FMEA Constraints Enforced: PI-XXX (if applicable)
"""

def my_function(param):
    """
    Brief description of what this function does.

    Args:
        param: Description of the parameter.

    Returns:
        Description of the return value.

    Side Effects:
        Any side effects (file writes, API calls, state changes).

    FMEA Constraints:
        PI-XXX — Description of the constraint this function enforces.
    """
    # Plain-English explanation of what this block does and why
    result = do_something(param)
    return result
```

AI sessions must not remove, truncate, or rewrite existing comments.
Comment presence and preservation are standing acceptance criteria on all tasks.

---

## Human and QA Gates

### PLAN-Bound Tasks

1. A builder implements the linked Issue and stops at `READY-FOR-QA`.
2. A separate QA pass writes reproducible evidence under `.team/evidence/T-xxx/`.
3. A task marked `ESCALATE` halts for its named human approval before the protected action.
4. The primary agent marks `DONE` only after QA PASS and required human clearance.

### Legacy Tier 1 and Tier 2 Issues

When a legacy issue explicitly requires two-phase approval and is not superseded by PLAN, retain its exact `[AWAITING_HUMAN_APPROVAL: ...]` halt before documentation or protected actions.

---

## Drift Detection Responsibility

If any session changes a project-level fact (constraint text, task count, phase status,
framework name, file path, directory structure), log all other documents containing the
stale version of that fact to `working/DOCUMENT_DRIFT_LOG.md` before ending the session.

Format:
```
## Drift Entry — [Date]
**Changed fact:** [Old value] → [New value]
**Stale documents:** [List of files that still reference the old value]
```

# Codex Team Operator

Read `TEAM_PROTOCOL.md`, `PLAN.md`, and `STATE.md` before dispatching work.

## Preconditions

- Confirm explicit user or `AGENTS.md` authorization for subagents.
- Confirm `VERIFY` is non-empty.
- Stop on unresolved questions that block the next task.

## Execution loop

1. Select a TODO task whose dependencies are DONE.
2. Set it IN-FLIGHT and dispatch a bounded builder task.
3. Review the handoff, then dispatch or perform QA using the same acceptance criteria and VERIFY command.
4. For tier 2 or 3, run an adversarial review when authorized.
5. Set DONE only after evidence-backed PASS and required review clearance.
6. After two failed build-to-QA cycles, stop and escalate to the user.

The primary agent owns status transitions, integration, and final synthesis.

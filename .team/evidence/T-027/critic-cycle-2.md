# T-027 Adversarial Critic Evidence — Cycles 1 and 2

## Outcome

**Cycle 2 verdict: CONCERNS, no blocker.** Cycle 1 returned BLOCK on F1: `st.rerun()` inside the "Use response" handler ended the run before later cards registered their widgets, so Streamlit dropped their state and reverted operator edits, including PI-004 description text. Cycle 2 fixed F1 and the critic confirmed the fix beyond the builder's checks. Two cycle-2 concerns (C1, C2) were folded in by the primary agent after review and re-verified with the builder driver, unit suites, and the canonical verifier. The critic wrote no repository file; the primary agent transcribed this record on 2026-09-11.

## Cycle 1 → Cycle 2 Closure

| Cycle-1 finding | Cycle-2 critic observation |
| --- | --- |
| F1 BLOCK: mid-run rerun dropped widget state | Edits on Setup-tab inputs, a second pending card's draft paste, and a review card's cost, price, condition, and category widgets all survived a "Use response" on another card. `rescan_requested` and `flash` are absent after every run; no rerun loop is possible. |
| F2: rescan failure invisible | Failure text appears once, in the sidebar, persists across idle interactions and repeated failures without duplicating, and clears on the next successful scan. |
| F3: no way to discard a reply | Redo on priced, drafted, already-released, and just-published cards ran without exception; the item returns to pending. |
| F4: drafted items re-pended | A draft keeps the reply and a rescan leaves the item a review card. A publish that raises keeps the reply; a successful publish releases it. |
| F6/F7: raw exception, unbounded echo | The word-boundary regex rejects `Mismatched`, `MISMATCHED`, `MISMATCH2`, and look-alikes and accepts emphasised or quoted `MISMATCH`; messages are capped. |
| F8: shared packet ID crash | Two same-named batches render two cards with SKU keys; one stored reply satisfies both (known boundary, unreachable with Drive-ID names). |
| Ground Rule 11 | All removed lines are the moved Scan handler (comments reappear verbatim), the provider import, one guard line, and rewritten Help and test prose. |

## Cycle-2 Findings and Rulings

| ID | Severity | Mechanism | Primary ruling |
| --- | --- | --- | --- |
| C1 | CONCERN | A Setup save of AI route = gemini flips the provider immediately while manual cards remain on screen; a paste then failed inside the generic guard with a misleading sentence. | Fixed after review: `apply_manual_reply` names the route switch; the review tab hides stale pending cards behind one notice when the route is not manual. |
| C2 | CONCERN | A failed deferred rescan showed "Reply accepted" in green beside the sidebar failure. | Fixed after review: `main()` drops the flash when the deferred scan fails. Driver check added. |
| C3 | CONCERN | Records were cycle-one stale (handoff line, smoke guide staging, STATE). | Fixed: handoff Risk Boundaries updated, smoke guide stages two items and adds edit-survival and Redo steps, STATE rewritten; `Test.pdf` excluded from the commit by explicit staging. |
| N1 | NOTE | Head truncation dropped the item's own packet ID for echoed IDs over ~320 characters. | Fixed after review: middle truncation keeps both ends; unit test asserts the item's ID survives. |
| N3 | NOTE | An ID-echoing but off-schema reply is accepted and yields a hollow card; pre-existing `extract_item` coercion, more exposed without JSON mode. | Queued to the manual-provider hardening issue; Redo prevents a dead end; T-006 AC2 blocks review on missing defects. |
| N2, N4–N10 | NOTE | Markdown in the echoed ID renders in the red box; Redo on a just-published card flashes without effect; digit-prefixed `MISMATCH` and MISMATCH-plus-JSON are not normalised; per-card settings reads; short helper docstrings; a theoretical flag survival if a tab render raises. | Recorded; N2 and N5 join the queued hardening issue. |

## Post-Review Verification by the Primary Agent

| Gate | Result |
| --- | --- |
| Unit suites (review, help content, manual provider) | 77 passed |
| Builder AppTest driver (28 cycle-2 checks plus the C2 flash check) | 29 of 29 |
| Canonical `scripts/verify.ps1` | Exit 0; 263 collected and passed |
| `git diff --check` | Clean apart from line-ending warnings |

## Boundaries

- Probes ran under `.test-tmp\crit27\` and `.test-tmp\crit27c2\` with fake data, temp SQLite, and a stub eBay client; no `.env`, credential, AppData, or network access; `Test.pdf` not opened.
- AppTest models widget-state retention but is not a browser; the owner smoke test (AC5) is the final check of F1 in a real session.

## HFE Review

- [x] Chunking: no table exceeds seven rows; low-severity notes are grouped in one row.
- [x] Signal-to-noise: each row supports a verdict, a mechanism, or a ruling.
- [x] Signaling: bold marks only the verdict.
- [x] Contiguity: each finding's ruling sits beside its mechanism.
- [x] Redundancy: reproduction commands live in the QA records; this record holds observations and rulings.
- [x] Dual-channel: the handoff's flowchart covers the mechanism.
- [x] Progressive disclosure: verdict precedes closure, findings, verification, and boundaries.

This changes if the owner's browser smoke shows any operator edit lost across the deferred rerun that AppTest preserved, or if Drive cache naming stops being file-ID based, which would promote the shared-packet-ID note to a PI-014 block.

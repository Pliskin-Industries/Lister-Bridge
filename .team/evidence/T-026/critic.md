# T-026 Adversarial Critic Evidence

## Outcome

**Verdict: CONCERNS.** No path lets a reply without the exact packet ID reach the vision contract short of deliberate operator forgery, no pending item is ever written `ERROR`, and the file-name-only packet ID is safe given the Drive cache's `{file_id}.{ext}` naming. Two concerns are operational and are accepted by the primary agent with the rulings below. The critic wrote no repository file; the primary agent transcribed this record on 2026-09-10.

## Confirmed Solid

| Claim | Independent observation |
| --- | --- |
| PI-014 ID check | Rejected: wrong item's ID, missing key, hyphenless or truncated ID, ID as list, nested ID, key-case variant, Cyrillic look-alike, prose mentioning another ID, two concatenated objects. Accepted only when the top-level `packet_id` equals the packet ID. Hex IDs make case folding safe. |
| Store never keeps a bad paste | Wrong-item reply, `MISMATCH`, and garbage all raise; store stays empty; item stays `NEW`. |
| Pending path | Three scans with no replies leave both items `NEW` with no errors or payloads. `ManualResponsePending` is caught before the generic handler; archive and publish run only from an approved payload. |
| Packet-ID collision | Cache names are `{drive_file_id}.{ext}` (`drive_fetcher._get_local_filename`); shortcuts are excluded by the image MIME query; Drive v3 forbids multi-parent files. Two distinct items share an ID only if they share the identical Drive file set, which is one item. |
| PI-004 / PI-005 reuse | The stripped JSON flows through unchanged `vision_agent.extract_item`; `_EXTRACTION_PROMPT` appears verbatim in the packet. |
| Settings, comments, scope | Unknown `AI_PROVIDER` values route to Gemini; no other code reads the key; the Setup tab renders the field; one docstring line was re-emitted, none removed; no change under `src/contracts/`, `src/ui/`, state, API, or marketplace. |

## Findings and Rulings

| ID | Severity | Mechanism | Primary ruling |
| --- | --- | --- | --- |
| F1 | CONCERN | With `AI_PROVIDER=manual` and no key, the startup banner reads complete, but the Scan button and headless `main()` still build `GeminiProvider`, so every batch downloads, fails at the lazy client, and is written `ERROR` (self-healing on later scans). | Accepted: provider selection is T-027 AC1 and no operator test precedes T-027 (D-TEAM-009). Recorded in STATE as "manual mode not operator-exposed until T-027". |
| F2 | CONCERN | A same-`file_id` photo replacement in Drive keeps the packet ID, so a stored reply is reused against new photo bytes within one session. | Accepted with mitigation routed to T-027: call `forget_response` when a payload is rendered or approved. Content or modified-time in the ID is queued as a follow-up; replies are session-only until T-006. |
| F3 | NOTE | Duplicate top-level `packet_id` keys: `json.loads` keeps the last, so a hand-edited reply can pass. | Queued hardening (`object_pairs_hook` rejecting duplicates); requires operator forgery, outside PI-014 as written. |
| F4 | NOTE | `**MISMATCH**` or `MISMATCH.` falls to the JSON error path instead of the photo-mismatch guidance. | Routed to T-027 AC3 (human-readable guidance). |
| F5 | NOTE | The "strip so `extra="forbid"` parses" rationale overstates the protection; `extract_item` reads known keys with `.get`. | Docstring accuracy only; corrected in the next touch of `manual_provider.py` (T-027 or housekeeping). |
| F7 | NOTE | PI-014 verifies the pasted packet, not the attached photos; attach misattribution rests on the human review gate (PI-007/PI-008) and the `MISMATCH` instruction. | Accepted; one sentence added to T-027 Help text scope. |

Notes F6 (an omitted `defects_found` is coerced to an empty list, pre-existing and already the target of T-006 AC2), F8 (pending rescans repeat cache-hit downloads and `NEW` upserts, wasteful not unsafe), and F9 (pass a nested dict rather than the whole session state; `validate_gemini` ignores the mode; `extract_item` docstring omits `ManualResponsePending`; several one-line helper docstrings) are recorded without further action beyond the T-027 notes in `.team/PLAN.md`.

QA's independent finding that three batches with identically named photos in different folders collide on one ID is the same mechanism as the collision row above; it is unreachable through `drive_fetcher` and is covered by the queued content-hash follow-up.

## Boundaries

- Probes ran from the session scratchpad with fake data and `StateStore(":memory:")`; no network, `.env`, credential, or AppData access.
- Baseline reproduced by the critic: 92 passed across the manual-provider, orchestrator, settings, vision, and integration targets; `git diff --check` exit 0.

## HFE Review

- [x] Chunking: no table exceeds seven rows; notes without action are grouped in one paragraph.
- [x] Signal-to-noise: each row supports a verdict, a mechanism, or a ruling.
- [x] Signaling: bold marks only the verdict.
- [x] Contiguity: each finding's ruling sits beside its mechanism.
- [x] Redundancy: reproduction commands live in `qa.md`; this record holds independent observations and rulings.
- [x] Dual-channel: the handoff's flowchart covers the mechanism.
- [x] Progressive disclosure: verdict precedes evidence, findings, and boundaries.

This changes if an operator-facing release or owner test is scheduled before T-027, if replies are persisted across sessions before the ID includes content or modified time, or if any consumer passes the parsed manual reply to `VisionAgentOutput(**parsed)` directly.

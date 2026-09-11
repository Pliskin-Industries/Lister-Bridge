# T-026 Independent QA Evidence

## Outcome

**Overall verdict: PASS.** The canonical verifier exits 0 with 233 collected and passed tests, the 24 builder tests and the 79-test regression set pass, and all five acceptance criteria were confirmed independently with standard-input diagnostics against the product modules. Forty-one attempts to get a reply accepted without the packet's own ID were all rejected, none was stored, and the six existing `extract_item` tests pass unchanged with `ManualProvider` substituted for the stub. The orchestrator leaves pending items at `NEW`, completes them on rescan, and turns a smuggled wrong-ID reply into a `BatchError` with no payload.

One design fragility is recorded for the adversarial critic: the packet ID is derived from photo file names alone, so two items whose photos share file names receive the same packet ID and one pasted reply completes both. This is unreachable through the shipped `drive_fetcher` path, whose local names are Drive file IDs, so no acceptance criterion fails. It should be weighed before any caller other than `scan_and_prepare` builds packets.

QA's PASS is one gate. The task still requires adversarial-critic clearance before the primary agent marks T-026 `DONE`.

## Acceptance Verdicts

| Criterion | Verdict | Evidence |
| --- | --- | --- |
| AC1: deterministic packet | PASS | All 24 permutations of a four-photo list gave one `prompt_text` (SHA-256 `4d00542c…69f8`) and one ID; four directories with the same names gave the same ID and text; a one-character prompt change, one removed photo, one renamed photo, and a case-only rename each changed the ID. |
| AC2: `AIProvider` contract and PI-004/PI-005 reuse | PASS | `ManualProvider` is an `AIProvider` subclass; the six `test_extract_item_*` tests pass with `ManualProvider` substituted (harness below); without a stored reply `ManualResponsePending.packet` equals `build_packet` output. |
| AC3: missing or mismatched ID rejected before parsing | PASS | 41-case matrix: every reply lacking the exact normalized ID raised `ManualPacketMismatch` or the shared parser's `ValueError`; `store_response` left the store at length 0 in every rejected case. |
| AC4: pending items, `NEW` status, rescan completion | PASS | Three-batch scan: `pending` lists all three at `NEW`; one stored reply yields one `PRICED` payload and two pending; injected wrong-ID reply gives one `BatchError` at `ERROR` with no payload; repaired store completes all three; three no-reply scans leave all at `NEW`; stub provider yields zero pending. |
| AC5: settings switch and import purity | PASS | `manual`, `MANUAL `, ` Manual\t` drop `GEMINI_API_KEY`; `gemini`, empty, `None`, absent, `openai`, `manual2` keep it; field optional and non-secret; fresh interpreter import loads no `streamlit`, `google`, or `genai` module; nine import lines, none lazy. |

## Verification Record

### Core Gates

All pytest runs used distinct `--basetemp` paths under `.test-tmp\` with `-p no:cacheprovider -o addopts=`. Interpreter: `.venv-py312\Scripts\python.exe`, Python 3.12.10. Branch `tier3-v2-roadmap` at HEAD `955dabb63d0f6c3008d4605c1544700392c4b115` plus the uncommitted T-026 diff.

| Gate | Exact command | Result |
| --- | --- | --- |
| Task target | `./.venv-py312/Scripts/python.exe -m pytest -q -p no:cacheprovider -o addopts= --basetemp=.test-tmp/qa26-manual-3a1f tests/test_manual_provider.py` | Exit `0`; 24 passed in 0.45 s |
| Regression set | Same options with `--basetemp=.test-tmp/qa26-regress-7c2e tests/test_orchestrator.py tests/test_settings.py tests/test_vision_agent.py tests/test_integration.py tests/test_help_content.py` | Exit `0`; 79 passed in 2.03 s |
| Canonical verification | `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\verify.ps1` | Exit `0`; Python 3.12.10; `pip check` clean; 233 collected and passed |
| Schema parity | `test_schema_covers_every_env_example_var` inside the regression set, plus a `diff` of the 19 `KEY=` names in `.env.example` against `settings._all_fields()` | Passed; `diff` reported no differing names |
| Import purity | `python -c` snapshot of `sys.modules` before and after `import src.ai.manual_provider`; `grep -nE '^\s*(import \|from )'` on the module | 196 new modules, none matching `streamlit`, `google`, or `genai`; imports are stdlib plus `src.ai.provider` and `src.ai.vision_agent` |
| Comment standard | `git diff -U0 -- src/core/orchestrator.py src/core/settings.py \| grep -E '^-'`; `ast` walk of both new `.py` files for missing docstrings | One removed line, `or absent value.`, re-emitted in the extended `missing_required` docstring; no comment removed; every module, class, and function in the two new files has a docstring |
| Patch and status hygiene | `git diff --check`; `git status --short`; `git ls-files --others --exclude-standard` | Exit `0`, no warnings; modified `.env.example`, `.team/PLAN.md`, `.team/STATE.md`, `src/core/orchestrator.py`, `src/core/settings.py`; untracked `.team/handoffs/T-026.md`, `src/ai/manual_provider.py`, `tests/test_manual_provider.py` |

### AC2 Substitution Harness

A standard-input script imported `tests.test_vision_agent`, replaced its `_StubProvider` with a `ManualProvider` subclass that pre-stores the test's canned text as the operator paste (adding the echoed `packet_id` when the text parses, storing raw garbage directly when it does not), and called each `test_extract_item_*` function.

| Test | Result with `ManualProvider` |
| --- | --- |
| `test_extract_item_happy_path` | PASS |
| `test_extract_item_forces_defects_list_pi004` | PASS |
| `test_extract_item_drops_invalid_aspects_pi005` | PASS |
| `test_extract_item_tolerates_code_fences` | PASS |
| `test_extract_item_empty_paths_raises` | PASS |
| `test_extract_item_unparsable_raises` | PASS |

### Determinism Diagnostic

Photos `/cache/b.jpg`, `/cache/a.jpg`, `/cache/c.heic`, `/cache/IMG_0001.HEIC` with `vision_agent._EXTRACTION_PROMPT`.

| Probe | Result |
| --- | --- |
| 24 input orderings | 1 distinct `prompt_text`, 1 distinct ID; `image_paths` sorted `IMG_0001.HEIC, a.jpg, b.jpg, c.heic` |
| Same names under `C:\Users\…`, `/tmp/z`, `D:/y`, `/q` | Same ID, byte-identical `prompt_text`, different `image_paths` |
| Prompt plus `.`; prompt plus trailing `\n` | Different ID each; the trailing newline also changes `prompt_text` because only the rendered copy is `rstrip`ped |
| One photo removed; one renamed; case-only rename `img_0001.heic` | Different ID each |
| `ManualPacket` mutation | `FrozenInstanceError` |
| ID format | Parses with `uuid.UUID`; SHA-256 prefix, not RFC 4122 version bits |

### Orchestrator Diagnostic

Standard-input script; `drive_fetcher.list_pending_batches` and `download_batch_images` replaced by lambdas returning three batches with per-batch file names; `StateStore(":memory:")`; originals restored in `finally`.

| Step | Observation |
| --- | --- |
| Scan 1, no replies | 0 payloads, 0 errors, 3 pending (`LB-F1`, `LB-F2`, `LB-F3`); `len(summary)` is 0; all statuses `NEW`; packet paths sorted; 3 distinct IDs |
| Scan 2, reply stored for F1 only | Payloads `[LB-F1]`; pending `[LB-F2, LB-F3]`; statuses `PRICED, NEW, NEW` |
| Scan 3, F3's reply written to `provider.responses` under F2's ID | Payloads still `[LB-F1]`; pending `[LB-F3]`; one `BatchError(batch_folder_id='F2', folder_name='Camera', reason='ManualPacketMismatch: …')`; `LB-F2` is `ERROR`; no F2 payload |
| Scan 4, correct replies stored for F2 and F3 | Payloads `[LB-F1, LB-F2, LB-F3]`; pending and errors empty; all `PRICED` (the `ERROR` item was retried) |
| Gemini-style stub provider | `pending == []`, 3 payloads, 0 errors |
| Three consecutive scans, no replies | All statuses `NEW`; reply store empty |

## Adversarial Matrix

Each case ran through `parse_manual_response(raw, packet)` and, separately, `ManualProvider().store_response(packet, raw)`, then read `len(provider.responses)`. Packet ID for the run: `b802b16a-2262-ea6b-dbd2-90a9c8407721`.

### Missing or Wrong Identifier

| Input | Result | Stored |
| --- | --- | --- |
| No `packet_id` key | `ManualPacketMismatch` "has no 'packet_id' key" | 0 |
| Other valid UUID | `ManualPacketMismatch` names both IDs | 0 |
| ID under `meta.packet_id` | `ManualPacketMismatch` (missing) | 0 |
| Key spelled `Packet_ID` | `ManualPacketMismatch` (missing) | 0 |
| ID only in the fence header line | `ManualPacketMismatch` (missing) | 0 |
| Reply built for the same photos and a different prompt | `ManualPacketMismatch` | 0 |
| `null` value | `ManualPacketMismatch` (missing) | 0 |

### Altered Identifier Values

| Input | Result | Stored |
| --- | --- | --- |
| `[id]` (list) | `ManualPacketMismatch` | 0 |
| `12345` (int); `true` (bool) | `ManualPacketMismatch` each | 0 |
| Empty string | `ManualPacketMismatch` | 0 |
| Hyphens removed; last character dropped | `ManualPacketMismatch` each | 0 |
| Wrapped in `{…}` | `ManualPacketMismatch` | 0 |
| Leading U+200B zero-width space | `ManualPacketMismatch` (not stripped) | 0 |

### Structure and Non-Object Replies

| Input | Result | Stored |
| --- | --- | --- |
| JSON array wrapping the object | `ValueError` "JSON was not an object" | 0 |
| Two JSON objects, either order | `ValueError` "Extra data" | 0 |
| Duplicate `packet_id`, wrong value last | `ManualPacketMismatch` | 0 |
| Duplicate `packet_id`, correct value last | Accepted (`json.loads` keeps the last key) | 1 |
| Empty string; `None`; whitespace only | `ValueError` "not valid JSON" each | 0 |
| `MISMATCH`, `mismatch`, ` MisMatch \n` | `ManualPacketMismatch` "did not match" each | 0 |
| `MISMATCH.`; fenced `MISMATCH` | `ValueError` "not valid JSON" (not the mismatch message) | 0 |

### Tolerated Normalizations

These accepted replies all carried the packet's own ID after `strip().lower()`, matching the handoff's stated case-insensitive rule and the shared parser's fence and brace fallback.

| Input | Result | Stored |
| --- | --- | --- |
| ID with surrounding whitespace | Accepted | 1 |
| ID upper case; mixed case | Accepted | 1 |
| ` ```json ` fence; bare ``` fence | Accepted | 1 |
| Prose before; prose before and after | Accepted via outermost `{…}` fallback | 1 |
| Extra unknown keys beside a correct ID | Accepted at the parse layer; see below | 1 |

Extra keys: `VisionAgentOutput(**cleaned)` raises `ValidationError` (`extra="forbid"`), but the shipped `extract_item` never spreads the dict into the contract; it reads the four known keys and ignores the rest, so the pipeline accepted the reply and produced a normal `VisionAgentOutput`. The rejecting layer is the direct contract constructor only. This is pre-existing `vision_agent` behaviour, unchanged by T-026, and it means the proposal's Section 3.3 sentence about contract failures surfacing a `ValueError` does not apply to unknown keys.

## Findings for the Critic

None blocks an acceptance criterion.

- Packet ID collision on shared file names. `_packet_id_for` seeds only adapter code, version, prompt, and sorted file names. The collision probe gave three batches photos named `01.jpg` and `02.jpg` in three folders: all three pending items carried ID `179551ed-047a-68f8-d978-c3ade4ba02b8`, and one stored reply completed all three with the same title. `drive_fetcher._get_local_filename` returns `{file_id}.{ext}`, and Drive file IDs are unique, so the shipped `scan_and_prepare` path cannot reach this state. Any future caller passing operator-named files (a local-folder route, a UI that builds packets from original names) would reintroduce the PI-014 misattribution the control exists to prevent. Folding `batch_folder_id` into the seed would close it without changing the directory-independence the builder tested.
- Operator-facing file names. Because local names are Drive IDs, the packet's photo list reads like `1aBcDe.jpg`, not the operator's own names. T-027 must show the cache folder and these names side by side; the handoff notes the folder but not the naming.
- Punctuated or fenced `MISMATCH` falls to the generic "not valid JSON" message rather than the photo-mismatch guidance; a T-027 message-formatting concern.
- Prose-wrapped replies are accepted although the packet forbids prose; the acceptance depends on the shared parser's brace fallback, which also governs Gemini replies today.

## Boundaries and Limitations

- No real Drive, Gemini, eBay, `%APPDATA%/ListerBridge`, `.env`, credential file, network service, or GUI was touched. All fixtures used fake paths and fake JSON; the state store was `":memory:"`; pytest temp roots were under `.test-tmp\`, which is git-ignored.
- Two QA harness defects were corrected and rerun: a cp1252 console encoding error while printing the zero-width-space case, and a first orchestrator fixture that gave every batch identical file names. The second defect is what surfaced the collision finding; the corrected fixture is what the AC4 table reports.
- The headless `orchestrator.main` still constructs `GeminiProvider`; manual mode there was not exercised, matching the handoff's stated boundary.
- `.team/PLAN.md` and `.team/STATE.md` are modified in the working tree and were not reviewed beyond confirming the T-026 acceptance text.
- Two `.test-tmp\qa26-*` pytest basetemp directories remain; they are ignored by git and hold no product data.

## HFE Review

- [x] Chunking: no list or table exceeds seven ungrouped items; the adversarial matrix is split into four groups.
- [x] Signal-to-noise: each section supports a verdict, reproduction, finding, or boundary.
- [x] Signaling: bold is reserved for the overall verdict.
- [x] Contiguity: each command sits beside its result; each finding beside its reproduction.
- [x] Redundancy: no diagram because nothing failed; tables carry the mechanism.
- [x] Dual-channel: not applied; the evidence brief limits diagrams to failing paths.
- [x] Progressive disclosure: verdicts precede gates, harnesses, attacks, findings, and limitations.

This changes if a reply is found that passes `parse_manual_response` without the packet's own ID after whitespace and case normalization, if any caller of `build_packet` supplies non-unique file names across items, if a pending item is ever recorded `ERROR` without a stored reply, or if the adversarial critic rejects the file-name-only ID seed.

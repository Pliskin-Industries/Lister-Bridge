# T-027 Independent QA Evidence

## Outcome

**Overall verdict: PASS.** The canonical verifier exits 0 with 259 tests collected and 259 passing marks, the 73 targeted tests and the 68-test regression set pass, and AC1 through AC4 were each confirmed independently by source review and by a headless `streamlit.testing.v1.AppTest` reproduction that drove the real `app.main()` through launch, Scan, nine rejected pastes, two accepted pastes, a stubbed draft fulfilment, and a rescan. Every rejected paste produced one plain sentence, no traceback, an empty reply store, and statuses `new`/`new`; the accepted pastes turned LB-F1 and then LB-F2 into review cards at `priced`; no item was ever `error`. The reply store is the nested dict `st.session_state["manual_replies"]`, keyed by packet ID only, and fulfilment released exactly the fulfilled item's reply.

AC5 is the owner's smoke test and is recorded as awaiting owner, not as a QA verdict. Three findings go to the adversarial critic; none fails an acceptance criterion: a shared packet ID crashes the page with a duplicate widget key (unreachable through `drive_fetcher`), a drafted item reverts to pending on the next rescan because its reply is released while a draft leaves the item unpublished, and the "Reply accepted" success message is emitted immediately before `st.rerun()`.

A prior `qa.md` (2026-09-10 22:41, verdict PASS, same HEAD) already occupied this path when this QA session started; this file replaces it after an independent reproduction with a freshly written harness. Its conclusions were reproduced, not reused. QA's PASS is one gate; the task still requires adversarial-critic clearance and the owner's smoke transcript before the primary agent marks T-027 `DONE`.

## Acceptance Verdicts

| Criterion | Verdict | Evidence |
| --- | --- | --- |
| AC1: provider follows `AI_PROVIDER`; sidebar names the mode | PASS | `test_build_provider_*` (5 tests) pass; `import src.ui.review` in a fresh interpreter loads no `streamlit`, `google`, or `genai` module; AppTest sidebar caption reads `AI route: **Manual paste (your own chat subscription)**` plus the manual-mode note under `manual`, and `AI route: **Gemini API**` with no note and a `GEMINI_API_KEY` warning under `gemini`; `GeminiProvider` appears in `app.py` only in a docstring and a comment. |
| AC2: photos with paths, copyable packet, paste area; Use response stores by packet ID and rescans | PASS | After Scan: two `Awaiting your AI reply` subheaders, photo-name captions `1aBcF1photo.png` and `1aBcF2photo.png`, two folder lines naming `…\cache\F1` and `…\cache\F2`, two `st.image`, two `st.code` blocks each starting `# Lister-Bridge manual extraction packet` and carrying only its own ID, two text areas keyed `reply_<id>`, two buttons keyed `use_reply_<id>`. The accepted paste stored `{<F1 id>}` in `st.session_state["manual_replies"]` (a `dict`, no widget keys) and the F1 review card `Sony WH-1000XM4 · LB-F1` appeared in the same click with LB-F1 at `priced`. |
| AC3: mismatch and parse failures give readable guidance, no traceback, item stays pending | PASS | Nine rejected pastes (tables below) each produced exactly one `st.error` sentence, zero `st.exception`, no `Traceback` text, two pending cards, statuses `{LB-F1: new, LB-F2: new}`, and an empty reply store. `**MISMATCH**`, `MISMATCH.`, `_mismatch!_`, and fenced `MISMATCH` all yielded the photo-mismatch guidance, not the JSON message. |
| AC4: Help "Manual AI mode" section; every new `TIPS` key referenced in `app.py` | PASS | Section renders as a subheader between "The workflow" and "Understanding warnings & errors"; its body contains "not the attached photos" and "leave this computer under your chat provider's terms". Nine `TIPS[...]` references in `app.py` match the nine keys in `help_content.TIPS`; 13 help-content tests pass. |
| AC5: owner's first operator UI test | Awaiting owner | Out of scope for this verdict. Guide at `.team/evidence/T-027/smoke-guide.md`; transcript expected as `owner-smoke.md`. |

Inherited PLAN notes were also checked: the Scan handler no longer constructs `GeminiProvider()` (the import is removed; `_run_scan` calls `_get_provider()`); `release_manual_reply` runs on the line after `fulfill_approved` and, in the AppTest run, removed only the drafted item's reply; the reply store is the nested dict, never the whole session state; decorated `MISMATCH` is recognised by `normalize_manual_reply`; the Help body states the check covers the pasted reply and that photos leave the machine under the chat provider's terms.

## Verification Record

### Core Gates

All pytest runs used distinct `--basetemp` paths under `.test-tmp\` with `-p no:cacheprovider -o addopts=`. Interpreter: `.venv-py312\Scripts\python.exe`, Python 3.12.10, streamlit 1.59.2. Branch `tier3-v2-roadmap` at HEAD `60d05b17c71507f1f9f2973e585f6f136457bba5` plus the uncommitted T-027 diff. Run on 2026-09-11 between 06:24 and 06:29 EDT from Git Bash at the repo root.

| Gate | Exact command | Result |
| --- | --- | --- |
| Task target | `./.venv-py312/Scripts/python.exe -m pytest -q -p no:cacheprovider -o addopts= --basetemp=.test-tmp/qa27-target-a1 tests/test_review.py tests/test_help_content.py tests/test_manual_provider.py` | Exit `0`; 73 passed in 0.67 s |
| Regression set | Same options with `--basetemp=.test-tmp/qa27-regress-b2 tests/test_orchestrator.py tests/test_settings.py tests/test_vision_agent.py tests/test_integration.py` | Exit `0`; 68 passed in 1.29 s |
| Canonical verification | `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/verify.ps1 > .test-tmp/qa27-verify.log 2>&1` | Exit `0`; Python 3.12.10; `259 tests collected`; 259 progress marks, all `.`; log at `.test-tmp\qa27-verify.log` |
| Import purity | `python -c "import sys, src.ui.review; print([m for m in sys.modules if m.split('.')[0] in ('streamlit','google','genai')])"` | `[]` |
| Comment standard | `git diff -U0 -- src/ui/app.py \| grep '^-'`; `awk '/^def _run_scan/,/^def _render_pending_item/' src/ui/app.py \| grep -c <five moved comment lines>`; `ast` walk of the three changed source files | 17 removed lines: the `GeminiProvider` import, `if not payloads:`, and the inline Scan handler including its five-line comment; all five comment lines reappear in `_run_scan` (count 5); no removed lines in `review.py` or `help_content.py`; every module, class, and function in the three files has a docstring |
| TIPS cross-check | `grep -on 'TIPS\["[a-z_]*"\]' src/ui/app.py \| sort -u`; `grep -nE '^    "[a-z_]+": \($' src/ui/help_content.py` | Nine references (`manual_packet`, `manual_reply`, `condition_select`, `description_editor`, `approve_button`, `provider_mode`, `scan_button`, `error_banner`, `stale_cache`), nine keys, identical sets |
| Patch hygiene | `git diff --check`; `git status --short`; `git ls-files --others --exclude-standard` | Exit `0` with two CRLF warnings only (`.team/DECISIONS.md`, `tests/test_review.py`); see Hygiene Observations |

The verifier log carries the collection count and the progress dots but not pytest's closing `N passed` line; the exit code and the absence of any `F` or `E` mark are the recorded result.

### AppTest Harness

`.test-tmp\qa27\qa_app.py` is a Streamlit script that inserts the repo root on `sys.path`, sets `STATE_STORE_DB_PATH` and `DRIVE_CACHE_DIR` to a per-run directory under `.test-tmp\qa27\qa-run-*` before importing `src`, replaces `settings.read_settings` with a lambda returning `AI_PROVIDER` from `QA27_MODE`, an empty `GEMINI_API_KEY`, and fake values for every other `.env.example` key, replaces `drive_fetcher.list_pending_batches` with two batches (`F1` Headphones, `F2` Camera) and `download_batch_images` with one generated 4x4 PNG per batch (`1aBcF1photo.png`, `1aBcF2photo.png`, or both `01.png` under `QA27_SAME_NAMES=1`), replaces `app._get_ebay_client` with a stub whose `search_active_comps` returns `[]`, optionally replaces `orchestrator.fulfill_approved` with a stub that logs its call and returns a `DraftOutput`, and calls `app.main()`. `.test-tmp\qa27\qa_driver.py` drives it with `AppTest.from_file(harness, default_timeout=30)`, reads statuses through a fresh `StateStore(<run db path>)` after every step, and parses packet IDs from the `Packet ID:` captions.

| Driver | Command | Result |
| --- | --- | --- |
| Main flow | `PYTHONIOENCODING=utf-8 ./.venv-py312/Scripts/python.exe .test-tmp/qa27/qa_driver.py main` | Exit `0`; `CHECKS: 69 total, 0 failed`; transcript `.test-tmp\qa27\qa-main-2.txt` |
| Gemini label | `… qa_driver.py gemini` | Exit `0`; 5 checks passed; transcript `qa-gemini.txt` |
| Collision | `… qa_driver.py collide` | Page exception recorded below; transcript `qa-collide.txt` |

### Main Flow Observations

| Step | Observed |
| --- | --- |
| Launch | Sidebar caption `AI route: **Manual paste (your own chat subscription)**`; info `Manual mode: Scan prepares a packet per item…`; no page warning (so `GEMINI_API_KEY` is not required in manual mode); body info `No items prepared yet…`; zero exceptions |
| Scan | Subheaders `Awaiting your AI reply · Headphones · LB-F1` then `… Camera · LB-F2`; packet IDs `a1741c6c-…3797` and `d2ed921e-…ee52`; two images, two code blocks, two text areas; `st.error` empty; statuses `new`, `new`; store `{}` |
| (a) prose into card 1 | `The reply is not a JSON object. Copy the model's entire reply, starting with { and ending with }, and paste it again.`; both pending; `new`, `new`; store `{}` |
| (b) card 2's JSON into card 1 | `The reply belongs to packet d2ed921e-…, not to this item's packet a1741c6c-…; it was not applied.`; both pending; `new`, `new`; store `{}` |
| (c) correct reply into card 1 | Subheaders `Awaiting … Camera · LB-F2` and `Sony WH-1000XM4 · LB-F1`; success `Reply accepted; re-scanning to extract and price this item.`; item-specifics table present; statuses `{LB-F1: priced, LB-F2: new}`; store keys `{a1741c6c-…}`; no `reply_`/`use_reply_` keys in the store |
| (e) fenced, upper-case-ID reply into card 2 | Subheaders `Sony WH-1000XM4 · LB-F1` and `Canon EOS R6 · LB-F2`; no pending card; statuses `priced`, `priced`; store holds both IDs |
| (d) LB-F1 target `other:mercari`, `Generate Mercari (draft)` (stub) | Stub log `LB-F1\tother:mercari`; success `Draft for Mercari (stub) written to …`; store shrank to `{d2ed921e-…}`; F1 review card still shown |
| (f) Scan again | LB-F1 pending again (`Awaiting … Headphones · LB-F1`), LB-F2 still a review card; statuses `{LB-F1: new, LB-F2: priced}`; no `error` status at any step |

The only `st.error` present after (c), (e), (d), and (f) was the review card's `Cannot publish yet: category_id is required; price must be > 0; fulfillment_policy_id is required; …` banner, which comes from `orchestrator._assemble_payload` reading policy IDs from `os.environ` (unset in the harness). It is pre-existing behaviour and was excluded from the "no error" checks.

### Further Rejected Pastes

All into card 2 after step (b); each left two pending cards, statuses `new`/`new`, an empty store, and zero exceptions.

| Paste | Error text |
| --- | --- |
| `**MISMATCH**` | `The model reported that the attached photos did not match the packet; re-check the photos and send the packet again.` |
| `MISMATCH.` | Same photo-mismatch sentence |
| `_mismatch!_` | Same photo-mismatch sentence |
| fenced ` ```\nMISMATCH\n``` ` | Same photo-mismatch sentence |
| JSON without `packet_id` | `The reply has no 'packet_id' key; paste the reply for packet d2ed921e-… exactly as the model returned it.` |
| Empty string | `Paste the model's reply first, then click Use response.` |
| JSON array wrapping a valid reply | `The reply is not a JSON object. …` |

### Gemini Mode and Collision Runs

Under `AI_PROVIDER=gemini` the sidebar caption read `AI route: **Gemini API**`, no sidebar info was drawn, the page warned `Setup is incomplete — missing required settings: GEMINI_API_KEY…`, and there were zero exceptions. Scan was not clicked in this mode because the real `GeminiProvider` would attempt a network call.

With both batches' photos named `01.png`, Scan produced two pending cards carrying the same `Packet ID: 1dbb8c35-bca9-383f-0556-69e1a1b0fc2b` and the page raised `StreamlitDuplicateElementKey: There are multiple elements with the same key='reply_1dbb8c35-…'`; only one text area rendered; both items stayed `new`.

## Findings for the Critic

None blocks an acceptance criterion.

- Duplicate widget keys on a shared packet ID. `_render_pending_item` keys the paste box and button by `packet_id` alone, and the packet ID is derived from photo file names, so two items with identically named photos crash the page instead of rendering two cards. `drive_fetcher._get_local_filename` yields `{file_id}.{ext}` with globally unique Drive IDs, so the shipped path cannot reach this state; it is the UI face of the T-026 collision finding (C26-2). Keying the widgets by `item_sku` would remove the crash without touching the packet ID.
- Drafted item reverts to pending. `release_manual_reply` runs after every successful `fulfill_approved`, including draft targets, but a draft leaves the item unpublished, so the next scan (the Scan button, or any other card's "Use response") re-runs the item, upserts it to `new`, and asks the operator to paste a reply they already supplied. Step (f) reproduced this: LB-F1 went `priced` → `new` and returned as a pending card after its Mercari draft. The Gemini route has the same rescan (pre-existing, at API cost); in manual mode the cost is a second chat round-trip. Releasing only on `AUTO_PUBLISH` success, or documenting the behaviour in Help, would resolve it.
- Transient success message. `_render_pending_item` calls `st.success(...)`, `_run_scan(store)`, then `st.rerun()`. AppTest retained the message because it coalesces deltas across the rerun; a browser replaces the page, so smoke-guide step 4's "Expect a success message" may not be observable. Not verified in a browser here.
- Deprecated parameter copied into new code. `st.image(path, use_container_width=True)` in `_render_pending_item` logs `Please replace use_container_width with width … will be removed after 2025-12-31` on every render under streamlit 1.59.2, as does the pre-existing call in `_render_item`. Cosmetic today; a future streamlit upgrade would break both.
- Setup tab naming. The `AI route` field the smoke guide names sits under the group titled "Gemini (Vision Agent)" and that group's Test button ignores manual mode; `settings.py` is outside this task and the builder queued it for housekeeping.

## Hygiene Observations

`git status --short` shows the five task files modified, `.team/handoffs/T-027.md` and `.team/evidence/T-027/` untracked, `.team/PLAN.md` modified (T-027 `TODO` → `IN-FLIGHT` only), and three deviations from the dispatch's expected list: `.team/DECISIONS.md` is modified (new D-TEAM-010 standing commit authorization, a primary-agent record, not a T-027 file); `.team/STATE.md` is unmodified and still describes the T-026 tree at `955dabb` with T-027 as the next action, so it fails the protocol's resurrection test until the primary agent updates it; and an untracked `Test.pdf` (272,121 bytes, modified 2026-09-10 22:37 local) sits at the repo root. Nothing in `src`, `tests`, `scripts`, or either QA harness references `.pdf`, the file was not opened, and the primary agent should confirm its origin with the owner before any commit.

## Boundaries and Limitations

- No real Drive, Gemini, eBay, `%APPDATA%/ListerBridge`, `.env` (none exists at the repo root), credential file, network service, or browser was touched. All fixtures were fake settings, generated PNGs, and fake JSON; the SQLite store lived under `.test-tmp\qa27\qa-run-*`; pytest temp roots were under `.test-tmp\`, which is git-ignored.
- Step (d) exercised the reply-release hook with `orchestrator.fulfill_approved` replaced by a stub, so publishing, draft writing, and post-fulfilment status transitions were not exercised; step (f)'s revert follows from the real `release_manual_reply` plus the item being unpublished, which is also what a real draft leaves behind.
- `st.rerun()` inside the "Use response" handler raised nothing in the harness; AppTest completed the rerun within one `at.run()`. AppTest does not paint a browser, so the transient-message finding is reasoned, not observed.
- One harness defect was corrected and rerun: the first main-flow driver failed four of its own checks because it treated the pre-existing `Cannot publish yet` banner as an error and expected both items to stay priced after the draft step; the recorded run filters that banner and orders (e) before (d). The product behaved identically in both runs; the transcript of the first run is `.test-tmp\qa27\qa-main.txt`.
- The Help tab and the code block were verified through the element tree; visual layout, the copy control, and clipboard behaviour are browser concerns left to the owner's smoke test.
- Harness files from this run and the prior QA run remain under `.test-tmp\qa27\`, alongside `.test-tmp\qa27-*` pytest roots; all are git-ignored and hold no product data.

## HFE Review

- [x] Chunking: no list or table exceeds seven ungrouped items; observations are split into main flow, further pastes, and mode runs.
- [x] Signal-to-noise: each section supports a verdict, reproduction, finding, or boundary.
- [x] Signaling: bold is reserved for the overall verdict.
- [x] Contiguity: each command sits beside its result; each paste beside its error text; each finding beside its reproduction step.
- [x] Redundancy: no diagram because no acceptance criterion failed; tables carry the mechanism.
- [x] Dual-channel: not applied; the evidence brief limits diagrams to failing paths.
- [x] Progressive disclosure: verdicts precede gates, harness, observations, findings, hygiene, and limitations.

This changes if the owner's smoke test finds a paste path that yields a traceback or marks an item `ERROR`, if any caller of `scan_and_prepare` can present two pending items with one packet ID, if the adversarial critic treats the duplicate-key crash, the draft-then-revert behaviour, or the transient success message as blocking, or if `Test.pdf` proves to be an artefact of the T-027 change set.

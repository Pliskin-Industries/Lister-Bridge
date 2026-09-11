# T-027 Independent QA Evidence — Cycle 2

## Outcome

**Overall verdict: PASS.** The canonical verifier exits 0 with 262 tests collected and 262 passing marks, the 76 targeted tests and the 68-test regression set pass, and AC1 through AC4 were each re-confirmed by source review and by two headless `streamlit.testing.v1.AppTest` reproductions: the builder's harness and driver copied under `.test-tmp\qa27c2\` (28 of 28 checks), and a QA-written harness and driver with their own assertion set (70 of 72 checks in the main flow, 8 of 8 in the collision run, 4 of 4 under Gemini mode; the two misses are QA expectation artifacts explained below, not product defects). The cycle-one blocker no longer reproduces: sentinel edits to the LB-F1 title and PI-004 description survived a "Use response" on the later card, a "Redo AI reply" on the later card, and a "Redo AI reply" on the earlier card, in every case because the only `st.rerun()` now runs at the end of `main()` after every tab has registered its widgets. No rejected paste, scan failure, or collision run ever wrote an `error` status to the harness SQLite.

AC5 remains the owner's smoke test and is recorded as awaiting owner. `qa.md` and `smoke-guide.md` are unchanged; this file records only the second cycle. QA's PASS is one gate; the task still requires adversarial-critic clearance and the owner's smoke transcript before the primary agent marks T-027 `DONE`.

## Acceptance Verdicts

| Criterion | Verdict | Evidence |
| --- | --- | --- |
| AC1: provider follows `AI_PROVIDER`; sidebar names the mode | PASS | 76 targeted tests pass; QA harness under `manual` shows `AI route: **Manual paste (your own chat subscription)**`, the manual-mode note, and no `GEMINI_API_KEY` warning; under `gemini` it shows `AI route: **Gemini API**`, no note, and the `GEMINI_API_KEY` setup warning; `GeminiProvider` is not imported by `app.py`. |
| AC2: photos with paths, copyable packet, paste area; Use response stores by packet ID and rescans | PASS | After Scan: two `Awaiting your AI reply` cards, two `image` elements (element census), full-path captions `…\run-main\cache\qaF1driveid.png` and `…qaF2driveid.png`, two `st.code` blocks starting `# Lister-Bridge manual extraction packet`, text areas keyed `reply_LB-F1`/`reply_LB-F2`; the accepted paste stored exactly the F1 packet ID in `st.session_state["manual_replies"]`, the deferred rescan ran, and LB-F1 became a review card at `priced` with the flash `Reply accepted; re-scanning…` visible after the rerun. |
| AC3: mismatch and parse failures give readable guidance, no traceback, item stays pending | PASS | Ten rejected pastes (matrix below) each produced exactly one body `st.error` sentence, zero `st.exception`, two pending cards, statuses `new`/`new`, and an empty reply store; direct calls confirm the catch-all sentence for a 100,000-deep JSON object, a `RecursionError`, and a `TypeError`. |
| AC4: Help "Manual AI mode" section; every new `TIPS` key referenced in `app.py` | PASS | Ten `TIPS[...]` references in `app.py` equal the ten keys in `help_content.TIPS` (including new `redo_reply`); the Help subheader `Manual AI mode` renders; its body names `Redo AI reply`; "Before you start" reads `plus a Gemini API key unless you choose manual AI mode`. |
| AC5: owner's first operator UI test | Awaiting owner | Out of scope for this verdict. Guide at `.team/evidence/T-027/smoke-guide.md`; transcript expected as `owner-smoke.md`. |

## Cycle-1 Findings Closed

| Finding | Independent observation (QA driver, `qa-main.txt`) |
| --- | --- |
| F1 BLOCK: mid-run rerun dropped later widgets' state | (a) `desc_LB-F1` = `QA-SENTINEL-DESC…` and `title_LB-F1` = `QA-SENTINEL-TITLE` both held after accepting card 2 with a pre-typed then replaced reply; (b) `desc_LB-F1` held after Redo on LB-F2; (b') `desc_LB-F2` (later card) held after Redo on the earlier card LB-F1; AST: the sole `st.rerun()` is `main` line 732, none in `_render_pending_item` or `_render_item`. |
| F2: rescan failure invisible after rerun | With `FAIL_SCAN` present, "Use response" left one sidebar error `Scan failed: RuntimeError: qa simulated Drive outage`, zero exceptions, the reply stored, prior cards intact; the error persisted through an unrelated rerun (a description edit); removing the file and clicking Scan cleared it and completed LB-F2 from the stored reply. |
| F3: no way to discard an accepted reply | `redo_reply_LB-F2` returned LB-F2 to pending, popped only the F2 ID from the store, showed `Reply for LB-F2 discarded; paste a new one.`, and set LB-F2 back to `new` while LB-F1 stayed `priced`. |
| F4 / QA-2: drafted items re-pended | After `target_LB-F1` = `other:mercari` and Generate, `posting.md` and `photos_manifest.txt` were written under the work dir, the F1 ID stayed in the store, and the next Scan left LB-F1 a review card at `priced` with nothing pending; AST: `release_manual_reply` in `_render_item` is guarded by `not isinstance(result, DraftOutput)`. |
| F6 / F7: raw exception and unbounded echo | A 2000-character echoed packet ID produced a 400-character message ending in `…`; `{"a":`×100000 produced `The reply could not be read…`; `{` + `[`×100000 produced the JSON-object sentence; injected `RecursionError` and `TypeError` both produced the generic sentence. |
| F8 / QA-1: shared packet ID crashed widgets | Collision run (`cache\F1\01.png`, `cache\F2\01.png`): zero exceptions, both pending cards rendered with keys `reply_LB-F1`/`reply_LB-F2`, both showing packet `1dbb8c35-bca9-383f-0556-69e1a1b0fc2b`; one accepted reply completed both items to `priced` (known accepted boundary, see below). |
| F11 / F12: paths, MISMATCH prose, Help accuracy | Full paths are captions above each thumbnail and distinguished the two `01.png` files; `**MISMATCH**: the second photo shows a different item.` and `MISMATCH - photo 1 is a cat` both gave the photo-mismatch sentence while `MISMATCHED photos` correctly fell to the JSON sentence; Help text as recorded under AC4. |

## Verification Record

### Core Gates

All pytest runs used distinct `--basetemp` paths under `.test-tmp\qa27c2\` with `-p no:cacheprovider -o addopts=`. Interpreter: `.venv-py312\Scripts\python.exe`, Python 3.12.10, streamlit 1.59.2. Branch `tier3-v2-roadmap` at HEAD `60d05b17c71507f1f9f2973e585f6f136457bba5` plus the uncommitted T-027 diff. Run 2026-09-11 between 06:42 and 06:47 EDT from Git Bash at the repo root.

| Gate | Exact command | Result |
| --- | --- | --- |
| Task target | `./.venv-py312/Scripts/python.exe -m pytest -q -p no:cacheprovider -o addopts= --basetemp=.test-tmp/qa27c2/pt-target tests/test_review.py tests/test_help_content.py tests/test_manual_provider.py` | Exit `0`; 76 passed in 0.41 s |
| Regression set | Same options with `--basetemp=.test-tmp/qa27c2/pt-regress tests/test_orchestrator.py tests/test_settings.py tests/test_vision_agent.py tests/test_integration.py` | Exit `0`; 68 passed in 1.29 s |
| Canonical verification | `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/verify.ps1 > .test-tmp/qa27c2/verify.log 2>&1` | Exit `0`; Python 3.12.10; `262 tests collected`; 262 progress marks, all `.`, zero `F`/`E`; log at `.test-tmp\qa27c2\verify.log` |
| Source review (AST) | `python .test-tmp/qa27c2/ast_docstrings.py` | `MISSING_DOCSTRINGS: []` across `app.py`, `review.py`, `help_content.py`; `ST_RERUN_CALLS: [('main', 732)]`; `RELEASE_CALLS: [('_render_item', 426), ('_render_item', 443)]`; five new functions in `app.py`, eleven new functions/classes in `review.py`, all documented |
| Ground Rule 11 | `git diff -U0 src/ui/app.py src/ui/review.py src/ui/help_content.py \| grep '^-'` | `app.py`: 17 removed lines (the `GeminiProvider` import, `if not payloads:`, the inline Scan handler with its five comment lines, all five present again in `_run_scan`); `help_content.py`: two removed prose lines of the "Before you start" string (F12 rewording), no comment or docstring; `review.py`: no removed lines |
| TIPS cross-check | `grep -o 'TIPS\["[a-z_]*"\]' src/ui/app.py \| sort -u`; `grep -nE '^    "[a-z_]+": \($' src/ui/help_content.py` | Ten references, ten keys, identical sets |
| Patch hygiene | `git diff --check`; `git status --short`; `git ls-files --others --exclude-standard` | Exit `0` with one CRLF warning (`.team/DECISIONS.md`); see Hygiene Observations |

On the `_REPLY_DECORATION` note in the dispatch: `git show HEAD:src/ui/review.py | grep -c _REPLY_DECORATION` returns 0 and the worktree returns 0, so that cycle-one constant and its comment existed only between commits; relative to HEAD nothing was deleted from `review.py`, and the regex comment at lines 274–276 and 425–429 is an addition.

### Harnesses and Drivers

| Artifact | Origin | Command and result |
| --- | --- | --- |
| `.test-tmp\qa27c2\ui_harness.py`, `t27_driver.py` | Copied from the builder's scratchpad, unmodified; `TMP`/`TEMP` pointed at `.test-tmp\qa27c2\tmp` so its work dir stayed under `.test-tmp` | `PYTHONIOENCODING=utf-8 ./.venv-py312/Scripts/python.exe .test-tmp/qa27c2/t27_driver.py` — exit `0`; `SUMMARY: 28/28`; transcript `builder-driver.txt` |
| `.test-tmp\qa27c2\qa_harness.py`, `qa_driver.py` | Written by QA: fake settings (`AI_PROVIDER` from `QA27C2_MODE`), batches `Turntable`/`Lens`, generated 6x4 PNGs, `STATE_STORE_DB_PATH`/`DRIVE_CACHE_DIR`/`DRAFT_OUTPUT_DIR` under `run-<scenario>`, `FAIL_SCAN` switch, no-network eBay stub, real `fulfill_approved` | `… qa_driver.py main` — exit `1`, `70/72` (two QA expectation artifacts); `… qa_driver.py collide` — exit `0`, `8/8`; `… qa_driver.py gemini` — exit `0`, `4/4`; transcripts `qa-main.txt`, `qa-collide.txt`, `qa-gemini.txt` |
| `.test-tmp\qa27c2\f6_probe.py` | Written by QA: direct `apply_manual_reply` calls plus an element-type census of the rendered tree | Exit `0`; `ELEMENT_CENSUS` shows `image: 2`, `code: 2`, `text_area: 2`; transcript `f6-probe.txt` |

The two QA-driver misses: the F7 check demanded the phrase `not to this item's packet` inside a message that the product had already, correctly, truncated to 400 characters (the truncation check itself passed); the F6 check assumed `{` + `[`×100000 would reach the catch-all, but the shared parser rejects it earlier with the JSON-object sentence, which is equally plain. The product behaved acceptably in both; the expectations were wrong.

### Accepted Paths and Edit Survival

| Step | Observed |
| --- | --- |
| Accept card 1 (fenced JSON) | Cards `[LB-F1]`, pending `[LB-F2]`; flash present; statuses `priced`/`new`; store `[F1 id]`; `redo_reply_LB-F1` present; no sidebar error; zero exceptions |
| (a) sentinels on LB-F1, pre-typed then correct reply on LB-F2 | Pre-typed text survived the LB-F1 edits; after accept both cards, none pending; both sentinels intact; statuses `priced`/`priced` |
| (b) edit LB-F1, Redo on LB-F2 | LB-F2 pending, LB-F1 card; `desc_LB-F1` = `QA-SENTINEL-DESC-2 after both accepted`; store `[F1 id]`; statuses `priced`/`new` |
| (b') re-accept LB-F2, edit LB-F2, Redo on LB-F1 | LB-F1 pending, LB-F2 card; `desc_LB-F2` = `QA-SENTINEL-DESC-F2 later card`; after re-accepting LB-F1 both cards and the LB-F2 edit still held |
| (d) `other:mercari` draft for LB-F1, then Scan | `Draft for Mercari written to …\run-main\drafts\LB-F1\mercari\posting.md`; store kept both IDs; after Scan cards `[LB-F1, LB-F2]`, pending `[]`, LB-F1 `priced` |
| (c) Redo LB-F2, `FAIL_SCAN`, accept LB-F2 | One sidebar error `Scan failed: RuntimeError: qa simulated Drive outage`; zero exceptions; store holds F2 id; cards `[LB-F1]`, pending `[LB-F2]`; no `error` status; error still shown after an unrelated rerun |
| Recovery: remove `FAIL_SCAN`, Scan | Sidebar errors `[]`; cards `[LB-F1, LB-F2]`; pending `[]`; the LB-F1 edit typed during the outage survived; final statuses `priced`/`priced` |

## Adversarial Matrix

Every paste went into `reply_LB-F2` before any acceptance; after each, both cards were pending, SQLite read `{LB-F1: new, LB-F2: new}`, the store was empty, and `at.exception` was empty.

### Packet and JSON Rejections

| Paste | Error text (leading part) |
| --- | --- |
| Prose `Here you go! The item looks great.` | `The reply is not a JSON object. Copy the model's entire reply, starting with { and ending with }, and paste it again.` |
| LB-F1's JSON into LB-F2 | `The reply belongs to packet 027d22d8-…, not to this item's packet 2bc4e2df-…; it was not applied.` |
| JSON without `packet_id` | `The reply has no 'packet_id' key; paste the reply for packet 2bc4e2df-… exactly as the model returned it.` |
| `packet_id` of 2000 `z` characters | `The reply belongs to packet zzzz…` cut at exactly 400 characters with a trailing `…` |
| `{` followed by 100,000 `[` | JSON-object sentence (parser `ValueError` path) |

### MISMATCH and Empty Rejections

| Paste | Error text |
| --- | --- |
| `**MISMATCH**: the second photo shows a different item.` | `The model reported that the attached photos did not match the packet; re-check the photos and send the packet again.` |
| `MISMATCH - photo 1 is a cat` | Same photo-mismatch sentence |
| `MISMATCHED photos` | JSON-object sentence (word boundary holds) |
| Empty string | `Paste the model's reply first, then click Use response.` |
| Whitespace only | Same empty-reply sentence |

### Direct Function Probes

`f6_probe.py` called `review.apply_manual_reply` with a real `ManualProvider` and packet: a 100,000-deep `{"a":…}` object returned `ok=False` with `The reply could not be read. Copy the model's JSON reply again and paste only that.`; a provider raising `RecursionError` and one raising `TypeError` returned the same sentence; `raw=None` returned the empty-reply sentence. No probe raised.

## Observations Not Blocking

- Truncation hides the item's own ID. When the echoed packet ID exceeds roughly 370 characters, the 400-character cut removes the `not to this item's packet <id>; it was not applied` clause, so the operator sees which packet the reply claimed but not which it should have carried. The item stays pending and nothing is stored, so AC3 holds; a shorter echo cap before the sentence is composed would keep both IDs visible.
- Shared packet ID remains a shared reply. In the collision run one accepted reply completed both LB-F1 and LB-F2 to `priced` because `ManualProvider` keys replies by packet ID and the ID derives from photo names only. `drive_fetcher` names cache files by globally unique Drive IDs, so the shipped path cannot reach this state; recorded as the accepted T-026 boundary (content-hash ID queued).
- Docstring drift in `_render_pending_item`: the `store` argument is documented as "needed to re-run the scan" and the Side Effects text says the handler "re-runs the scan", but the function no longer uses `store` and only requests the deferred rescan. Comment text was preserved, so Ground Rule 11 is met; accuracy is a housekeeping note.
- `_render_item` still calls `st.image(path, use_container_width=True)`; the QA transcript logged 123 `Please replace use_container_width with width` warnings. Pre-existing, cosmetic under streamlit 1.59.2, noted in cycle one.
- `AppTest.error` includes sidebar elements, so the builder driver's F2 detail showing the scan-failure text twice is a collection artifact (`at.error=2`, body `1`, sidebar `1` in the QA run); the page renders it once.

## Hygiene Observations

`git status --short` shows the five task files and `.team/PLAN.md` modified, `.team/DECISIONS.md` modified (primary-agent record, not a T-027 file), `.team/handoffs/T-027.md` and `.team/evidence/T-027/` untracked, and an untracked `Test.pdf` (272,121 bytes, 2026-09-10 22:37) at the repo root. `Test.pdf` is not part of T-027, was not opened, and must not be committed with this task; the primary agent should confirm its origin with the owner. `.team/STATE.md` was not reviewed by this pass.

## Boundaries and Limitations

- No real Drive, Gemini, eBay, `%APPDATA%/ListerBridge`, `.env`, credential file, network service, browser, or commit was touched. Fixtures were fake settings, generated PNGs, fake JSON, and SQLite files under `.test-tmp\qa27c2\run-*`; the builder's copied driver wrote under `.test-tmp\qa27c2\tmp\lb-t27-driver`.
- Publishing was not exercised: the eBay stub raises on `publish_listing`, so the post-publish `release_manual_reply` branch is confirmed by AST guard and source reading only, not by execution.
- Gemini mode was verified for the sidebar label and warning only; Scan was not clicked because the real `GeminiProvider` would attempt a network call.
- AppTest does not paint a browser: thumbnail layout, the copy control, tooltip text, and flash timing as a human sees them are left to the owner's smoke test.
- Two QA-driver expectations were wrong (F7 phrase inside a truncated message; F6 route for a bracket flood) and are reported as such rather than rerun to green; the product output for both is recorded above.
- QA artifacts remain under `.test-tmp\qa27c2\` (git-ignored, no product data).

## HFE Review

- [x] Chunking: no list or table exceeds seven ungrouped items; rejected pastes are split into two groups.
- [x] Signal-to-noise: each section supports a verdict, reproduction, closed finding, observation, or boundary.
- [x] Signaling: bold is reserved for the overall verdict.
- [x] Contiguity: each command sits beside its result; each finding beside the observation that closes it; each paste beside its error text.
- [x] Redundancy: no diagram because no acceptance criterion failed; tables carry the mechanism.
- [x] Dual-channel: not applied; the evidence brief limits diagrams to failing paths.
- [x] Progressive disclosure: verdicts precede closed findings, gates, harnesses, observations, hygiene, and limitations.

This changes if the owner's smoke test finds an operator edit reverted by "Use response" or "Redo AI reply" in a browser, a paste path that yields a traceback or marks an item `error`, a scan failure that disappears after the rerun, or a drafted item returning to pending; if any caller can present two pending items with one packet ID in the shipped path; or if the adversarial critic treats the truncated-ID message or the shared-reply boundary as blocking.

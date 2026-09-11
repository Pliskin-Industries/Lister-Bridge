# T-027 Owner Smoke Guide

## Purpose

This is the first operator test of Lister-Bridge under the 2026-09-10 decision to defer testing until a working UI exists. It exercises the manual paste route end to end with your own chat subscription. Nothing publishes: stop before Approve, or select a draft target.

## Before you start

1. Confirm the branch and environment: `git -C C:\Claude\Lister-Bridge log --oneline -1` shows the T-027 commit, and `.venv-py312\Scripts\python.exe --version` prints Python 3.12.10.
2. On the Setup tab, set **AI route** to `manual` and leave the Gemini API key blank. Drive and eBay sandbox credentials are still required for Scan.
3. Put two items' photos in two new subfolders of your Drive staging folder; step 5 needs a second card.

## Steps

```powershell
cd C:\Claude\Lister-Bridge
.\.venv-py312\Scripts\python.exe -m streamlit run src\ui\app.py
```

1. Check the sidebar reads "AI route: Manual paste" and shows the manual-mode note.
2. Click **Scan Drive for new items**. Expect one "Awaiting your AI reply" card per item with its photos, the photo folder path, numbered steps, and a packet block.
3. Open a fresh chat in your subscription model, attach the listed photos from the folder shown, copy the packet with the code block's copy button, paste it, and send.
4. Paste the model's JSON reply into the card's reply box and click **Use response**. Expect a success message, then the card turns into a normal review card with title, specifics, condition, and price.
5. Negative check: paste the same reply into a second item's card. Expect a refusal that names both packet IDs and leaves that item waiting.
6. Negative check: paste a sentence of prose. Expect "The reply is not a JSON object" guidance, no traceback.
7. Edit-survival check: change the first card's description text, then accept the second card with its own reply. Expect your edit to still be there afterwards.
8. Click **Redo AI reply** on one card. Expect it to return to "Awaiting your AI reply".
9. Open the Help tab and confirm the "Manual AI mode" section is present.

## What to record

Save a short transcript or screenshots under `.team/evidence/T-027/` as `owner-smoke.md`, noting the date, which chat model you used, and PASS or FAIL per step. Steps 5 and 6 are the PI-014 checks and step 7 is the PI-004 edit-survival check; any of the three failing is a FAIL for the task.

## Boundaries

- Do not click **Approve & Publish to eBay** during this test.
- Photos you attach leave the machine under your chat provider's terms, as they would with the Gemini API.
- The agent-side rehearsal of this flow (fake Drive batches, generated photos, no credentials) is recorded in `.team/evidence/T-027/qa.md`.

This changes if the owner prefers to test through the packaged executable instead of `streamlit run`; the steps are identical after launch.

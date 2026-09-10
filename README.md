# Lister-Bridge Hybrid Agent

An automated market research and eBay listing tool. Monitors Google Drive for incoming
item photos, uses Gemini Multimodal Vision to extract details and establish a
GMV-optimized "Margin-Guard" price, and uses a Streamlit review/approve interface to
resolve ambiguities before publishing directly to eBay via the REST Sell Inventory API.

---

## Development Status

Roadmap work runs on the `tier3-v2-roadmap` branch; `main` is the protected v1.2 legacy
baseline. Task status of record is `.team/PLAN.md`; resumable context is `.team/STATE.md`.
Bars to the right of the today marker are working-day projections that assume the
pending owner decisions land this week. They are estimates, not commitments.

```mermaid
gantt
    title Lister-Bridge delivery timeline (status as of 2026-09-10)
    dateFormat YYYY-MM-DD
    axisFormat %b %Y
    excludes weekends

    section Legacy v1.x on main
    Phases 1 to 5 and v1.2 hardening               :done, legacy, 2026-03-30, 2026-07-09

    section Phase 0 Governance
    T-001 Tier-3 workspace                          :done, t001, 2026-07-14, 1d
    T-002 Governance precedence and issue binding   :done, t002, 2026-07-14, 1d
    T-003 Reproducible Windows verification         :done, t003, 2026-07-14, 2d

    section Phase 1 Safety kernel
    T-004 Thread-safe state migrations (ESCALATE)   :crit, active, t004, 2026-07-15, 2026-09-19
    T-005 Checkpoint eBay publication               :t005, after t004, 5d
    T-006 Fail-closed review candidates             :t006, after t005, 4d
    T-007 Category aspects and publication input    :t007, after t006, 4d
    T-008 Decouple drafts and harden ingestion      :t008, after t007, 4d
    T-009 Truthful persistent review queue          :t009, after t008, 5d

    section Phase 1b Manual AI mode (proposed)
    T-026 Manual paste provider core                :t026, 2026-09-11, 4d
    T-027 Manual paste review UI                    :t027, after t026, 3d
    First operator UI test                          :milestone, m1, after t027, 0d

    section Phase 2 Guided setup
    T-010 Setup Tier 1                              :t010, after t009, 4d
    T-012 Setup Tier 3 OAuth (ESCALATE)             :t012, after t010, 5d
    T-011 Setup Tier 2 policies and locations       :t011, after t012, 3d
    T-013 Sandbox v1.3 gate (needs credentials)     :crit, t013, after t011, 5d

    section Phase 3 Closed pricing loop
    T-014 Record and poll listing outcomes          :t014, after t013, 5d
    T-015 Category pricing prior                    :t015, after t014, 3d
    T-016 Stale-listing repricing                   :t016, after t015, 4d
    T-017 Closed-loop sandbox gate (needs buyer)    :crit, t017, after t016, 5d

    section Phase 4 Features
    T-018 Double-sale guard                         :t018, after t017, 3d
    T-019 Photo quality coach                       :t019, after t017, 5d
    T-020 Comp evidence transparency                :t020, after t018, 3d
    T-021 Returns into vision review                :t021, after t019, 4d
    T-022 Headless scheduled scans                  :t022, after t021, 5d

    section Phase 4 Docs and release
    T-023 Reconcile core documentation              :t023, after t022, 3d
    T-025 Reconcile operational documentation       :t025, after t022, 3d
    T-024 Sandbox v2 release gate                   :crit, t024, after t025, 5d
    Sandbox-verified v2 release candidate           :milestone, m2, after t024, 0d
```

Legend: grey bars are done; the highlighted bar is in progress; red bars are escalation or
live-sandbox gates that need an owner decision or external credentials.

---

## Success Criteria

| Metric | Target |
|---|---|
| Margin & Velocity | `marginGuardPrice` achieves >80% 30-day sell-through rate |
| Data Accuracy | Zero listings flagged by eBay for inaccurate Item Specifics |
| Vision Reliability | Vision Agent identifies ≥95% of visible physical defects |

---

## Architecture Overview

The system is a Python-based application with a Streamlit review/approve front end. The
**Orchestrator** polls a designated Google Drive folder for new item batches. For each
item, the **Vision Agent** (Gemini `media_resolution: HIGH`) extracts visual data, and
the **Logic Agent** (Gemini `thinking_level: HIGH`) calculates the Margin-Guard price.

If data is missing, the operator resolves it in the Streamlit review UI alongside the
photos, extracted specifics, and suggested price. Once the operator clicks **Approve**,
the payload is pushed to eBay via the REST Sell Inventory publish sequence
(`createInventoryItem` → `createOffer` → `publishOffer`), with images uploaded first via
the Media API.

---

## Directory Structure

```text
lister-bridge/
├── src/
│   ├── contracts/                # FROZEN pydantic data contracts
│   │   ├── vision.py             # VisionAgentOutput (Vision -> Margin-Guard)
│   │   ├── pricing.py            # MarginGuardOutput + ActiveCompRange
│   │   ├── ebay.py               # ListingPayload + REST bodies + result shapes
│   │   ├── adapter.py            # AdapterCapability + DraftOutput
│   │   └── state.py              # ItemRecord / ItemStatus / TokenCacheRecord
│   ├── core/
│   │   ├── orchestrator.py       # Sequencing, per-item state, Drive API integration
│   │   ├── drive_fetcher.py      # Handles Google Drive IO
│   │   ├── state_store.py        # SQLite dedup/resume + token cache
│   │   └── paths.py              # Frozen-aware .env / data-dir resolution
│   ├── ai/
│   │   ├── provider.py           # Swappable AI provider interface (Gemini default)
│   │   ├── vision_agent.py       # High-res image ingestion & Gemini extraction
│   │   └── margin_guard.py       # Pricing logic and market analysis
│   ├── api/
│   │   ├── ebay_auth.py          # OAuth refresh -> cached access token
│   │   └── ebay_client.py        # Media upload + REST Sell Inventory publish + Browse comps
│   ├── marketplace/               # MarketplaceAdapter layer (v1.2)
│   │   ├── base.py               # MarketplaceAdapter / AutoPublishAdapter / DraftAdapter
│   │   ├── ebay_adapter.py       # Auto-publish adapter wrapping ebay_client
│   │   └── other_adapter.py      # Draft-only adapter (Facebook Marketplace, Mercari, ...)
│   └── ui/
│       ├── app.py                 # Streamlit review/approve front end (the human gate)
│       └── review.py              # Pure, Streamlit-free review/validation helpers
├── desktop_app.py                 # Desktop entry point — launches the Streamlit GUI
├── packaging/
│   └── lister_bridge.spec         # PyInstaller spec for the standalone .exe
├── scripts/
│   ├── build_desktop.py           # Builds dist/lister-bridge.exe
│   └── ebay_sandbox_spike.py      # Live/mocked end-to-end eBay de-risk runner
├── tests/
├── docs/
│   ├── FMEA.md
│   ├── KANBAN_SETUP.md
│   ├── templates/
│   └── proposals/
├── working/                     # Ephemeral per-session scratch space
│   ├── CODE_DECISIONS_PATCH.md
│   ├── ISSUE_QUEUE.md
│   └── DOCUMENT_DRIFT_LOG.md
├── .github/
│   └── workflows/
│       └── spike-check.yml
├── CLAUDE.md
├── CONTRIBUTING.md
├── ARCHITECTURE.md
├── CONSTRAINTS.md
├── KEY_DECISION_LOG.md
├── CODE_DECISION_LOG.md
├── .env                         # SECURE — Never commit
├── .repomixignore
├── repomix.config.json
├── requirements.txt
└── README.md
```

---

## Operational Ground Rules

| # | Rule | Mechanism |
|---|---|---|
| 1 | **Issue Binding** — No code or documentation generated without an active, assigned Issue. | PR template requires Issue reference. |
| 2 | **Decision Logging** — Architectural decisions → `KEY_DECISION_LOG.md`. Code decisions → `working/CODE_DECISIONS_PATCH.md`. Merged into `CODE_DECISION_LOG.md` at HUMAN gate. | PR review checklist. |
| 3 | **State Synchronization** — AI explicitly states Kanban column changes at start and end of each action. | Prompt headers include State Sync section. |
| 4 | **Source Truth** — `ARCHITECTURE.md` updated concurrently with any structural change. | PR review checklist. |
| 5 | **Constraint Traceability** — Decisions impacting FMEA reference the FMEA ID. | FMEA labels on Issues. |
| 6 | **Template Adherence** — AI must read templates before generating files. No memory reconstruction. | Embedded in workflow. |
| 7 | **[SPIKE] Exemption** — Spike issues bypass structural requirements. Formalization required before Done. | `spike` label + Kanban Done-lock enforced by `spike-check.yml`. |
| 8 | **Execution-Locked FMEA** — FMEA constraints are immutable during task execution. | Prompt headers cite constraints with immutability notice. |
| 9 | **FMEA Amendment Protocol** — Constraint conflicts halt execution for human review. | FMEA Amendment Proposal template. |
| 10 | **Codebase State Sync** — Fresh repository map required at start of execution sessions. | Prompt header preamble check. |
| 11 | **Code Comment Standard** — All `.py` files must include module-level docstrings, function docstrings, and plain-English block comments. AI sessions must not remove or truncate existing comments. | Enforced via `CONSTRAINTS.md` C-004–C-007. Standing acceptance criterion. |

---

## Setup

1. Copy `.env.example` to `.env` and populate credentials (Gemini API key, Google Service Account JSON path, eBay OAuth tokens).
2. Install dependencies: `pip install -r requirements.txt`
3. Run the GUI: `streamlit run src/ui/app.py` — or headless: `python -m src.core.orchestrator`

## Marketplaces (v1.2)

The approve step routes a listing to a selectable target via the `MarketplaceAdapter` layer (`src/marketplace/`):

- **eBay** — auto-publish (Media upload → REST `createInventoryItem`/`createOffer`/`publishOffer`).
- **Other (draft)** — generic draft-only adapter that writes a platform-tailored posting + photo manifest to disk for manual posting. Templates ship for **Facebook Marketplace** and **Mercari**; add a platform by adding one entry to `_PLATFORM_TEMPLATES` in `src/marketplace/other_adapter.py`. **Etsy** is a future auto-publish candidate.

Drafts are written under `DRAFT_OUTPUT_DIR` (default `data/drafts/<item_sku>/<platform>/`).

## Desktop build (single .exe, v1.2)

Produce a standalone Windows executable that launches the Streamlit GUI in a native window (pywebview + PyInstaller, via `streamlit-desktop-app`):

```bash
pip install -r requirements.txt -r requirements-build.txt
python scripts/build_desktop.py            # -> dist/lister-bridge.exe
```

Reproducible alternative (hand-authored spec):

```bash
pyinstaller packaging/lister_bridge.spec   # -> dist/lister-bridge.exe
```

Dev run without packaging: `python desktop_app.py`. Build dependencies live in `requirements-build.txt` and are **not** required to run the app or the tests.

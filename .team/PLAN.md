# PLAN

## Mission

Deliver a sandbox-verified Lister-Bridge v2 with fail-closed review, reconciliation-backed publishing, guided setup, measured pricing outcomes, and an evidence-gated Windows release process.

## Assumptions

- The authoritative repository is `C:\\Claude\\Lister-Bridge` on `main`.
- Python 3.12 is the supported verification and packaging target.
- Google Drive remains the only ingestion route; direct upload is excluded.
- Existing `.env` files remain compatible, but production credentials and publishing remain disabled.
- Windows Task Scheduler is the headless scheduling mechanism.
- Live sandbox tasks remain `BLOCKED` until the operator supplies credentials and performs required buyer/seller actions.

## Delivery Sequence

The safety kernel precedes live onboarding because current code can duplicate remote listings and accept incomplete review evidence.

```mermaid
flowchart LR
    A["Team governance"] --> B["Windows baseline"]
    B --> C["Safety kernel"]
    C --> D["Guided setup"]
    D --> E["Sandbox release gate"]
    E --> F["Pricing feedback loop"]
    F --> G["Roadmap features"]
    G --> H["Scheduled review queue"]
    H --> I["Version 2 release gate"]
```

## Tasks

### Phase 0 — Governance and baseline

#### T-001 — Deploy Tier-3 execution workspace [DONE]

Depends: —
Parallel-group: serial
Files: `AGENTS.md`, `.team/`, `scripts/verify.ps1`

Acceptance criteria:

- [x] AC1: All eight Tier-3 role briefs and required evidence directories contain non-ignored files eligible for the next user-approved commit. Verify: `git ls-files --cached --others --exclude-standard .team/roles .team/evidence .team/evals .team/retro .team/archive` returns files under every path.
- [x] AC2: `TEAM_PROTOCOL.md` contains a non-empty `VERIFY` command and protects credentials and AppData. Verify: `Select-String -Path .team/TEAM_PROTOCOL.md -Pattern 'VERIFY: powershell','NO-TOUCH: .env'` returns both matches.
- [x] AC3: `AGENTS.md` authorizes only PLAN-bound delegation and names the HFE requirement. Verify: `Select-String -Path AGENTS.md -Pattern 'Multi-agent delegation is authorized','HFE-Mayer'` returns both matches.
- [x] AC4: A fresh agent can identify the current task and next action from `.team/STATE.md`. Verify: direct review records PASS in `.team/evidence/T-001/qa.md`.

Notes: Approved roadmap, Execution Model. The generated deployment scaffold is the protocol's sole atomic-bootstrap exception to the five-file builder limit.

#### T-002 — Establish governance precedence and issue binding [ESCALATE]

Depends: T-001
Issue: [#7](https://github.com/GhengisPliskin/Lister-Bridge/issues/7)
Parallel-group: A
Files: `AGENTS.md`, `CLAUDE.md`, `KEY_DECISION_LOG.md`, `docs/FMEA.md`, `.team/DECISIONS.md`
⚠ ESCALATE: governance and FMEA amendment; the user approved this task in the implementation request.

Acceptance criteria:

- [ ] AC1: A decision entry states that legacy records remain active while `.team/PLAN.md` controls current execution when task instructions conflict. Verify: `Select-String KEY_DECISION_LOG.md,.team/DECISIONS.md -Pattern 'execution overlay','controls current execution'` returns matches.
- [ ] AC2: `CLAUDE.md` and `AGENTS.md` retain issue binding, FMEA amendment gates, QA evidence, and human escalation while rejecting stale CLI/GraphQL tasks not present in PLAN. Verify: direct rule matrix in `.team/evidence/T-002/qa.md` records PASS.
- [ ] AC3: A GitHub roadmap epic exists, and every task must gain a linked issue before `IN-FLIGHT`. Verify: epic URL and T-003 issue URL are recorded in `.team/STATE.md`.
- [ ] AC4: The FMEA contains approved rows for duplicate publication, feedback pricing, polling limits, and cross-account/SKU misattribution. Verify: named FMEA rows are cited in `.team/evidence/T-002/qa.md`.

Notes: Approved roadmap T-002; PDR D-10 conflict and stale issue audit.

#### T-003 — Establish reproducible Windows verification [TODO]

Depends: T-002
Issue: [#8](https://github.com/GhengisPliskin/Lister-Bridge/issues/8)
Parallel-group: B
Files: `constraints-py312.txt`, `scripts/verify.ps1`, `.github/workflows/windows-ci.yml`, `.gitignore`, `requirements-build.txt`

Acceptance criteria:

- [ ] AC1: Python 3.12 installs both requirement sets under the constraint file and `pip check` exits 0. Verify: CI transcript.
- [ ] AC2: `scripts/verify.ps1` exits 0 and the suite contains at least 166 collected tests. Verify: saved console output.
- [ ] AC3: The Windows workflow runs verification, builds `dist/lister-bridge.exe`, rejects a zero-byte artifact, writes SHA-256, and uploads the executable. Verify: workflow YAML review and local execution of the same commands; the remote run is gated by T-013.
- [ ] AC4: `.pytest_cache` and supported build caches remain untracked. Verify: run VERIFY, then `git status --short` contains none of those paths.

Notes: Approved roadmap T-003; baseline audit recorded 166 PASS and one deprecation warning.

### Phase 1 — Safety kernel

#### T-004 — Add thread-safe state migrations [TODO]

Depends: T-002, T-003
Parallel-group: serial
Files: `src/core/state_store.py`, `tests/test_state_store.py`, `tests/test_state_store_concurrency.py`
⚠ ESCALATE: persistent-state migration; implementation must preserve existing rows.

Acceptance criteria:

- [ ] AC1: Each StateStore operation uses a connection owned by the calling operation; WAL, foreign keys, and a 5000 ms busy timeout are active. Verify: named pragma test passes.
- [ ] AC2: A version table applies forward-only migrations inside transactions. Verify: migration tests from an unversioned fixture and the latest fixture pass.
- [ ] AC3: A timestamped SQLite backup exists before the first migration of an existing database. Verify: backup test compares pre-migration row counts.
- [ ] AC4: Concurrent read/write and duplicate-claim tests complete without thread-affinity or locked-database errors. Verify: `pytest tests/test_state_store_concurrency.py` exits 0.

Notes: Approved roadmap T-004.

#### T-005 — Checkpoint eBay publication [TODO]

Depends: T-004
Parallel-group: serial
Files: `src/contracts/state.py`, `src/core/state_store.py`, `src/api/ebay_client.py`, `src/core/orchestrator.py`, `tests/test_publication_recovery.py`

Acceptance criteria:

- [ ] AC1: An environment/account/marketplace/target/SKU can be atomically claimed by only one concurrent caller. Verify: the concurrency test observes one adapter invocation and permits the same SKU under a different account.
- [ ] AC2: Image URLs, offer ID, and listing ID persist after their remote milestones. Verify: checkpoint assertions pass after injected failure at each milestone.
- [ ] AC3: Retry reconciles the deterministic SKU through offer lookup before creating or publishing. Verify: every injected-failure retry ends with one listing ID.
- [ ] AC4: A terminal publication releases its claim and remains idempotent across process restart. Verify: restart fixture calls the publisher twice and records one listing.

Notes: Approved roadmap T-005; external calls are at-least-once with reconciliation.

#### T-006 — Persist fail-closed review candidates [TODO]

Depends: T-005
Parallel-group: C
Files: `src/contracts/review.py`, `src/contracts/vision.py`, `src/core/state_store.py`, `src/ai/margin_guard.py`, `tests/test_review_candidate.py`

Acceptance criteria:

- [ ] AC1: `ReviewCandidate` persists original vision, pricing, payload, target, validation, confirmation, and override data and reloads after restart. Verify: round-trip test passes.
- [ ] AC2: Missing or malformed `defects_found` blocks review while an explicit empty list remains distinguishable. Verify: three named contract tests pass.
- [ ] AC3: Unknown condition, incomplete cost/fee/profit inputs, and final price below floor produce hard blockers. Verify: parameterized blocker test passes.
- [ ] AC4: Soft overrides require operator, reason, and timestamp and cannot remove a hard blocker. Verify: override validation tests pass.

Notes: Approved roadmap T-006.

#### T-007 — Validate category aspects and publication input [TODO]

Depends: T-006
Parallel-group: serial
Files: `src/contracts/ebay.py`, `src/api/ebay_client.py`, `src/marketplace/ebay_adapter.py`, `src/ui/review.py`, `tests/test_ebay_preflight.py`

Acceptance criteria:

- [ ] AC1: Taxonomy aspects are cached by environment, marketplace, and category for seven days. Verify: cache clock test observes one request before expiry and two after expiry.
- [ ] AC2: Missing required aspects appear as editable blockers. Verify: fixture with two missing aspects returns their names.
- [ ] AC3: Invalid title, description, condition, quantity, media, category, policies, or location fails before the first remote write. Verify: fake client records zero writes for each invalid fixture.
- [ ] AC4: Draft adapters reject missing title, description, price, or image manifest. Verify: adapter validation tests pass.

Notes: Approved roadmap T-007.

#### T-008 — Decouple drafts and harden ingestion [TODO]

Depends: T-006, T-007
Parallel-group: serial
Files: `src/core/orchestrator.py`, `src/core/drive_fetcher.py`, `src/marketplace/other_adapter.py`, `src/ui/review.py`, `tests/test_ingestion_resilience.py`

Acceptance criteria:

- [ ] AC1: Facebook and Mercari draft flows complete with all eBay settings absent. Verify: credential-free integration test exits 0.
- [ ] AC2: Missing active comps require a manual comp or audited no-comp override, and the final price remains at or above floor. Verify: parameterized pricing test passes.
- [ ] AC3: Network, 429, and 5xx failures retry at most three times with `Retry-After` or jittered backoff; other 4xx failures do not retry. Verify: fake-clock tests assert call counts.
- [ ] AC4: One failed Drive batch does not discard successful batches, and archive occurs only after every item is terminal. Verify: mixed-batch test asserts payloads, errors, and archive calls.

Notes: Approved roadmap T-008.

#### T-009 — Render a truthful persistent review queue [TODO]

Depends: T-005, T-006, T-007, T-008
Parallel-group: serial
Files: `src/ui/app.py`, `src/ui/review.py`, `src/core/settings.py`, `tests/test_review_ui_logic.py`, `.env.example`

Acceptance criteria:

- [ ] AC1: Review logic exposes defects, dropped fields, blockers, comp provenance, floor, confirmations, and overrides. Verify: view-model test asserts every field.
- [ ] AC2: Pending review candidates reload from SQLite after a new application session. Verify: restart integration test passes.
- [ ] AC3: Sandbox state is always visible, and every production selection is rejected during this roadmap even when `ALLOW_EBAY_PRODUCTION=true`. Verify: settings tests cover absent, false, and true values with zero production client construction.
- [ ] AC4: Approval remains disabled until all hard blockers and required confirmations are resolved. Verify: review gate truth-table test passes.

Notes: Approved roadmap T-009.

### Phase 2 — Guided setup and first release gate

#### T-010 — Add Setup Tier 1 [TODO]

Depends: T-009
Parallel-group: serial
Files: `src/core/settings.py`, `src/ui/app.py`, `src/ui/help_content.py`, `tests/test_settings.py`, `tests/test_setup_guidance.py`

Acceptance criteria:

- [ ] AC1: Drive folder URLs and raw IDs normalize to the same folder ID. Verify: parser fixtures pass.
- [ ] AC2: Selecting a service-account JSON displays its `client_email` and folder-sharing instructions without displaying private-key material. Verify: redaction test and captured UI text.
- [ ] AC3: Per-service completion persists without secret values. Verify: persisted progress fixture contains statuses and no configured secret.
- [ ] AC4: Each required field has adjacent walkthrough and test guidance. Verify: schema audit test reports no missing guidance.

Notes: Approved roadmap T-010.

#### T-011 — Add Setup Tier 2 [TODO]

Depends: T-012
Parallel-group: serial
Files: `src/api/ebay_client.py`, `src/core/settings.py`, `src/ui/app.py`, `tests/test_ebay_setup.py`

Acceptance criteria:

- [ ] AC1: Fulfillment, payment, return policies, and inventory locations map API IDs to selectable labels. Verify: response-fixture tests pass.
- [ ] AC2: Cached selections are keyed by eBay environment and account. Verify: switching either key produces a cache miss.
- [ ] AC3: Empty API results produce instructions naming the missing policy/location and a portal link. Verify: empty-result view-model test passes.
- [ ] AC4: Explicit refresh bypasses the cache and replaces stale choices. Verify: fake-client call-count test passes.

Notes: Approved roadmap T-011.

#### T-012 — Add Setup Tier 3 OAuth [TODO]

Depends: T-010
Parallel-group: serial
Files: `src/api/ebay_auth.py`, `src/core/settings.py`, `src/ui/app.py`, `tests/test_ebay_oauth_flow.py`, `.env.example`
⚠ ESCALATE: auth and refresh-token handling; tests use fake tokens only.

Acceptance criteria:

- [ ] AC1: Seller authorization URLs include RuName, one-use state, and only base `api_scope`, `sell.inventory`, `sell.account.readonly`, `commerce.media`, and `sell.fulfillment`; Browse and Taxonomy use a separate client-credentials base-scope token. Verify: user-token and application-token URL fixture tests pass.
- [ ] AC2: Redirect parsing rejects wrong state, wrong environment, expired code, and missing code. Verify: four named tests pass.
- [ ] AC3: Successful exchange writes the fake refresh token through masked settings without emitting it to logs or errors. Verify: capture test finds zero token occurrences.
- [ ] AC4: No localhost callback server or production endpoint is reachable from the sandbox flow. Verify: static test inspects configured endpoints.
- [ ] AC5: Successful base-scope identity validation stores the nonsecret eBay user ID used by publication and outcome keys. Verify: fake identity response round-trips through settings without token content.

Notes: Approved roadmap T-012; live credential use remains blocked.

#### T-013 — Pass the sandbox version 1.3 gate [TODO]

Depends: T-003, T-009, T-011
Parallel-group: serial
Files: `scripts/ebay_sandbox_spike.py`, `.team/evidence/T-013/`
⚠ ESCALATE: live sandbox credentials and external listing mutation.

Acceptance criteria:

- [ ] AC1: `python scripts/ebay_sandbox_spike.py --require-live` exits nonzero when credentials are missing or any result is pending. Verify: no-credential transcript.
- [ ] AC2: Isolated executable smoke evidence covers first run, Setup, Help, settings, database, queue, and restart. Verify: screenshot/transcript set.
- [ ] AC3: A live sandbox item publishes once, survives restart without duplication, and its Drive batch archives. Verify: redacted IDs and Drive observations.
- [ ] AC4: No production endpoint or credential appears in the evidence. Verify: redaction scan exits 0.
- [ ] AC5: The Windows GitHub workflow completes and uploads the executable and hash at the tested commit. Verify: captured run URL and artifact listing.

Notes: Approved roadmap T-013; unsigned executable is accepted only for this internal gate.

### Phase 3 — Closed pricing loop

#### T-014 — Record and poll listing outcomes [TODO]

Depends: T-013
Parallel-group: serial
Files: `src/contracts/outcomes.py`, `src/core/outcomes.py`, `src/core/state_store.py`, `src/api/ebay_client.py`, `tests/test_outcomes.py`
⚠ ESCALATE: schema migration and new OAuth scope; tests use fixtures.

Acceptance criteria:

- [ ] AC1: Outcome records support ACTIVE, SOLD, ENDED_UNSOLD, ENDED_ELSEWHERE, REVERSED, and UNKNOWN and round-trip with environment, seller account, marketplace, SKU, offer ID, and listing ID. Verify: contract/migration tests pass.
- [ ] AC2: Polling matches orders inside the same environment/account/marketplace identity, reconciles offer state, and applies the 24-hour ended grace period. Verify: transition and cross-account isolation fixtures pass.
- [ ] AC3: Polling is idempotent, rate-aware, and limited to records whose last check exceeds `OUTCOME_POLL_DAYS`. Verify: fake-clock and call-count tests pass.
- [ ] AC4: Existing publication rows backfill as UNKNOWN without changing their identifiers. Verify: migration row comparison passes.

Notes: Approved roadmap T-014.

#### T-015 — Calculate the category pricing prior [TODO]

Depends: T-014
Parallel-group: serial
Files: `src/ai/pricing_prior.py`, `src/ai/margin_guard.py`, `src/contracts/pricing.py`, `tests/test_pricing_prior.py`

Acceptance criteria:

- [ ] AC1: The environment/account/marketplace/category sample counts sold-within-30-days as success, 30-day-unsold and reversed as failure, and excludes unknown/sold-elsewhere. Verify: classification and cross-account isolation tests pass.
- [ ] AC2: Samples below 30 emit evidence and adjustment factor 1.0. Verify: boundary tests at N=29 and N=30 pass.
- [ ] AC3: Adjustment equals `1 + clamp(rate - 0.80, -cap, cap)` and never exceeds the configured cap. Verify: property tests pass.
- [ ] AC4: Margin Guard applies the factor to its base suggestion, never crosses the floor, and remains human-gated. Verify: floor/cap property tests pass.

Notes: Approved roadmap T-015.

#### T-016 — Add stale-listing repricing [TODO]

Depends: T-015
Parallel-group: serial
Files: `src/api/ebay_client.py`, `src/core/outcomes.py`, `src/ui/review.py`, `src/ui/app.py`, `tests/test_repricing.py`
⚠ ESCALATE: eBay offer mutation; tests use a fake client.

Acceptance criteria:

- [ ] AC1: Active listings older than the configured threshold expose N, sell-through, median days, realized ratio, current price, suggestion, and floor. Verify: stale view-model test passes.
- [ ] AC2: Repricing requires an explicit operator action and a value at or above floor. Verify: gate tests pass.
- [ ] AC3: The client reads the complete offer, patches price, sends the complete payload, and re-reads the offer. Verify: fake-client request assertions pass.
- [ ] AC4: Retry of the same approved price produces the same final remote and local state. Verify: idempotency test passes.

Notes: Approved roadmap T-016.

#### T-017 — Pass the closed-loop sandbox gate [TODO]

Depends: T-016
Parallel-group: serial
Files: `.team/evidence/T-017/`
⚠ ESCALATE: live sandbox buyer/seller actions.

Acceptance criteria:

- [ ] AC1: A sandbox buyer purchase transitions a tracked listing to SOLD. Verify: redacted poll transcript and database row.
- [ ] AC2: A cancellation or refund fixture transitions SOLD to REVERSED. Verify: named automated test plus live evidence when the sandbox supports it.
- [ ] AC3: A human-approved sandbox reprice is confirmed by a post-write offer read. Verify: redacted before/after payload evidence.
- [ ] AC4: N-gating, cap, and floor test evidence is attached to the gate. Verify: VERIFY transcript.

Notes: Approved roadmap T-017; do not substitute mocks for AC1 or AC3.

### Phase 4 — Remaining roadmap

#### T-018 — Add the double-sale guard [TODO]

Depends: T-017
Parallel-group: D
Files: `src/api/ebay_client.py`, `src/core/outcomes.py`, `src/ui/review.py`, `tests/test_double_sale.py`
⚠ ESCALATE: live offer withdrawal; implementation tests use fakes.

Acceptance criteria:

- [ ] AC1: Sold-elsewhere requires explicit confirmation naming SKU and marketplace. Verify: confirmation view-model test passes.
- [ ] AC2: Local state changes to ENDED_ELSEWHERE only after successful withdrawal or verified already-ended state. Verify: success/failure fixture tests pass.
- [ ] AC3: Repeating the action makes no second destructive call. Verify: call-count test passes.
- [ ] AC4: UI and documentation make no Facebook or Mercari synchronization claim. Verify: repository text scan returns no such claim.

Notes: Approved roadmap T-018.

#### T-019 — Add the photo quality coach [TODO]

Depends: T-017
Parallel-group: E
Files: `src/contracts/photo_qa.py`, `src/ai/photo_qa.py`, `src/core/orchestrator.py`, `tests/test_photo_qa.py`, `.team/evals/photo-qa.md`

Acceptance criteria:

- [ ] AC1: Photo QA runs before extraction and records blur, duplicate views, primary/alternate angles, labels/serials, and defect close-ups. Verify: ordered pipeline test passes.
- [ ] AC2: No readable primary image is a hard block; missing recommended views require an audited override. Verify: blocker table tests pass.
- [ ] AC3: Photo QA results persist in ReviewCandidate. Verify: round-trip test passes.
- [ ] AC4: The README metric is claimed only after a frozen evaluation set contains at least 100 defect annotations across 30 batches and measured recall is at least 95%. Verify: evaluation report or explicit unverified label.

Notes: Approved roadmap T-019.

#### T-020 — Add comp evidence transparency [TODO]

Depends: T-018
Parallel-group: F
Files: `src/contracts/comp_evidence.py`, `src/ai/margin_guard.py`, `src/ui/review.py`, `tests/test_comp_evidence.py`

Acceptance criteria:

- [ ] AC1: Each comp stores query, source type, URL, title, condition, item price, shipping, timestamp, and operator note. Verify: contract round-trip test passes.
- [ ] AC2: Browse records display as active comps and cannot display as sold comps. Verify: label tests pass.
- [ ] AC3: Manual Terapeak/sold-comp evidence persists and lists whether it influenced the price. Verify: review-candidate fixture test passes.
- [ ] AC4: Pricing evidence shown in review exactly matches the evidence persisted for publication. Verify: equality assertion passes.

Notes: Approved roadmap T-020; Sell Analytics is not a sold-comp source.

#### T-021 — Feed returns into vision review [TODO]

Depends: T-014, T-019
Parallel-group: serial
Files: `src/contracts/returns.py`, `src/core/returns.py`, `src/ai/vision_agent.py`, `tests/test_return_feedback.py`, `.team/evals/return-feedback.md`
⚠ ESCALATE: returns API scope and prompt-version approval; offline fallback is permitted.

Acceptance criteria:

- [ ] AC1: API and manual CSV/form adapters normalize into the same ReturnOutcome contract. Verify: equivalent fixture test passes.
- [ ] AC2: Qualifying cancellation/refund records transition the associated outcome to REVERSED. Verify: transition test passes.
- [ ] AC3: Fewer than five matching misses generate no prompt proposal; five or more generate an evidence-cited proposal. Verify: N=4/N=5 tests pass.
- [ ] AC4: Production prompt text changes only after a recorded human decision and version increment. Verify: guard test rejects an unapproved change.

Notes: Approved roadmap T-021.

#### T-022 — Register headless scheduled scans [TODO]

Depends: T-018, T-019, T-020, T-021
Parallel-group: serial
Files: `desktop_app.py`, `src/core/scheduler.py`, `src/core/orchestrator.py`, `tests/test_scheduler.py`, `packaging/lister_bridge.spec`

Acceptance criteria:

- [ ] AC1: `--headless-scan`, `--register-schedule --daily HH:mm`, and `--unregister-schedule` parse without launching the GUI. Verify: CLI tests pass.
- [ ] AC2: Registration creates a current-user Windows task with no secret command arguments and remains disabled until explicitly requested. Verify: task-definition snapshot test passes.
- [ ] AC3: A two-hour SQLite lease causes a concurrent scan to exit without duplicate work. Verify: concurrent process test passes.
- [ ] AC4: Headless scans create review candidates and poll outcomes but invoke no publish operation. Verify: fake-adapter test records zero publishes.
- [ ] AC5: New review work or errors trigger a desktop notification. Verify: notification adapter test passes.

Notes: Approved roadmap T-022.

#### T-023 — Reconcile core product documentation [TODO]

Depends: T-022
Parallel-group: serial
Files: `PDR_Product_Deployment_Blueprint.md`, `ARCHITECTURE.md`, `docs/FMEA.md`, `docs/Ebay lister bridge master plan.md`, `KEY_DECISION_LOG.md`

Acceptance criteria:

- [ ] AC1: PDR, architecture, FMEA, master plan, and decision records describe the verified implementation and use consistent terms. Verify: context-librarian audit records zero named conflicts.
- [ ] AC2: Safeguards are labeled verified only when a corresponding `.team/evidence` record exists. Verify: evidence-link audit passes.
- [ ] AC3: Product terms for review candidates, outcomes, pricing priors, and release boundaries match code contracts. Verify: context-librarian term audit records zero conflicts.
- [ ] AC4: Every modified document passes the checked HFE-Mayer Markdown gate. Verify: packet checklist under `.team/evidence/T-023/`.

Notes: Approved roadmap T-023; every packet uses HFE-Mayer.

#### T-025 — Reconcile operational documentation [TODO]

Depends: T-022
Parallel-group: serial
Files: `docs/lister-bridge-prompt-headers.md`, `working/ISSUE_QUEUE.md`, `CONTRIBUTING.md`, `working/PROMPT_commit_build_smoketest.md`, `README.md`

Acceptance criteria:

- [ ] AC1: Prompt headers and issue queue contain no active CLI or GraphQL execution task. Verify: repository text scan returns only explicitly superseded historical references.
- [ ] AC2: Contributor links and build instructions use the current repository and `C:\\Claude\\Lister-Bridge` path. Verify: obsolete-repository/path scan exits with no active matches.
- [ ] AC3: README distinguishes active comps, sandbox scope, unsigned packaging, and unverified production KPIs. Verify: direct review checklist passes.
- [ ] AC4: Issues #2–#6 are closed or superseded with commit/test evidence. Verify: `gh issue view 2 --json state` through issue 6 returns `CLOSED`.
- [ ] AC5: Every modified document passes the checked HFE-Mayer Markdown gate. Verify: packet checklist under `.team/evidence/T-025/`.

Notes: Approved roadmap T-002 and T-023 operational cleanup.

#### T-024 — Pass the sandbox version 2 release gate [TODO]

Depends: T-023, T-025
Parallel-group: serial
Files: `.team/evidence/T-024/`, release notes
⚠ ESCALATE: live sandbox mutation and release designation.

Acceptance criteria:

- [ ] AC1: VERIFY and Windows packaging CI pass at the release commit. Verify: captured run URL and transcript.
- [ ] AC2: Isolated GUI/restart, OAuth/policy/location setup, publish/reconcile/reprice/withdraw, and scheduler evidence all pass. Verify: evidence index contains one PASS entry per scenario.
- [ ] AC3: Release artifacts include executable SHA-256 and contain no credentials. Verify: hash command and redaction scan.
- [ ] AC4: Production remains disabled and a separate production-enablement issue records signing and rollout prerequisites. Verify: settings assertion and issue link.
- [ ] AC5: Release notes claim measurement of 30-day sell-through, not achievement of the 80% production target. Verify: text review.

Notes: Approved roadmap T-024.

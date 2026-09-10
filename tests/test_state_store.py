"""
Module: test_state_store.py
Purpose: Tests for the Phase 4 SQLite StateStore against the frozen contracts.
         Uses an in-memory database (no disk, no network).
FMEA Constraints Enforced (asserted): R-STATE, R-AUTH.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.contracts import ItemRecord, ItemStatus, TokenCacheRecord
from src.core import state_store as state_store_module
from src.core.state_store import StateStore, StateStoreMigrationError


_LEGACY_TABLE_STATEMENTS = (
    """
    CREATE TABLE items (
        item_sku        TEXT PRIMARY KEY,
        batch_folder_id TEXT NOT NULL,
        status          TEXT NOT NULL,
        offer_id        TEXT,
        listing_id      TEXT,
        eps_urls        TEXT NOT NULL DEFAULT '[]',
        updated_at      TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE token_cache (
        id               INTEGER PRIMARY KEY CHECK (id = 1),
        access_token     TEXT NOT NULL,
        expires_at_epoch REAL NOT NULL,
        scopes           TEXT NOT NULL DEFAULT ''
    )
    """,
)


def _create_legacy_database(path: Path) -> None:
    """Create an unversioned copy of the original schema with fake rows."""
    connection = sqlite3.connect(path)
    try:
        for statement in _LEGACY_TABLE_STATEMENTS:
            connection.execute(statement)
        connection.execute(
            """
            INSERT INTO items
                (item_sku, batch_folder_id, status, offer_id, listing_id,
                 eps_urls, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "LB-legacy",
                "legacy-folder",
                ItemStatus.PUBLISHED.value,
                "OFFER-legacy",
                "LIST-legacy",
                '["https://example.invalid/legacy.jpg"]',
                "2026-01-01T00:00:00+00:00",
            ),
        )
        connection.execute(
            """
            INSERT INTO token_cache (id, access_token, expires_at_epoch, scopes)
            VALUES (1, 'fake-test-token', 1234.0, 'fake-scope')
            """
        )
        connection.commit()
    finally:
        connection.close()


def _create_version_ledger(path: Path, versions: list[object]) -> None:
    """Create a schema ledger fixture that can also hold malformed versions."""
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "CREATE TABLE schema_migrations (version, applied_at TEXT NOT NULL)"
        )
        connection.executemany(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, 'test')",
            [(version,) for version in versions],
        )
        connection.commit()
    finally:
        connection.close()


def _backup_paths(path: Path) -> list[Path]:
    """Return sibling migration backups created for one database path."""
    return sorted(path.parent.glob(f"{path.name}.backup-*.sqlite3"))


def _replace_token_cache_id_definition(path: Path, id_definition: str) -> None:
    """Recreate token_cache with exact columns and one adversarial id clause."""
    connection = sqlite3.connect(path)
    try:
        existing_rows = connection.execute(
            "SELECT id, access_token, expires_at_epoch, scopes FROM token_cache"
        ).fetchall()
        connection.execute("DROP TABLE token_cache")
        connection.execute(
            f"""
            CREATE TABLE token_cache (
                id               {id_definition},
                access_token     TEXT NOT NULL,
                expires_at_epoch REAL NOT NULL,
                scopes           TEXT NOT NULL DEFAULT ''
            )
            """
        )
        connection.executemany(
            """
            INSERT INTO token_cache (id, access_token, expires_at_epoch, scopes)
            VALUES (?, ?, ?, ?)
            """,
            existing_rows,
        )
        connection.commit()
    finally:
        connection.close()


def _replace_migration_version_definition(
    path: Path, version_definition: str
) -> None:
    """Recreate the v1 ledger with one adversarial version-column clause."""
    connection = sqlite3.connect(path)
    try:
        existing_rows = connection.execute(
            "SELECT version, applied_at FROM schema_migrations"
        ).fetchall()
        connection.execute("DROP TABLE schema_migrations")
        connection.execute(
            f"""
            CREATE TABLE schema_migrations (
                version    {version_definition},
                applied_at TEXT NOT NULL
            )
            """
        )
        connection.executemany(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            existing_rows,
        )
        connection.commit()
    finally:
        connection.close()


def _v2_probe_manifest() -> dict:
    """Return a complete version-2 manifest that adds one exact probe table."""
    probe_columns = (("id", "INTEGER", 0, None, 1),)
    probe_sql = ("CREATE TABLE migration_probe (id INTEGER PRIMARY KEY)",)
    return {
        **state_store_module._SCHEMA_MANIFESTS[1],
        "migration_probe": (probe_columns, probe_sql),
    }


@pytest.fixture
def store():
    """An ephemeral in-memory StateStore."""
    s = StateStore(":memory:")
    yield s
    s.close()


def test_upsert_and_get_roundtrip(store):
    """An item round-trips, including eps_urls JSON and status enum."""
    rec = ItemRecord(
        item_sku="LB-f1",
        batch_folder_id="f1",
        status=ItemStatus.PRICED,
        eps_urls=["https://i.ebayimg.com/a.jpg", "https://i.ebayimg.com/b.jpg"],
    )
    store.upsert_item(rec)
    got = store.get_item("LB-f1")
    assert got is not None
    assert got.status is ItemStatus.PRICED
    assert got.eps_urls == ["https://i.ebayimg.com/a.jpg", "https://i.ebayimg.com/b.jpg"]
    assert got.updated_at  # stamped on write


def test_get_missing_returns_none(store):
    """Unknown SKU returns None."""
    assert store.get_item("nope") is None


def test_upsert_updates_existing(store):
    """A second upsert on the same SKU updates in place (idempotency, R-STATE)."""
    store.upsert_item(ItemRecord(item_sku="LB-f1", batch_folder_id="f1"))
    store.upsert_item(
        ItemRecord(
            item_sku="LB-f1",
            batch_folder_id="f1",
            status=ItemStatus.PUBLISHED,
            offer_id="OFFER-1",
            listing_id="LIST-1",
        )
    )
    got = store.get_item("LB-f1")
    assert got.status is ItemStatus.PUBLISHED
    assert got.offer_id == "OFFER-1"
    assert got.listing_id == "LIST-1"
    # Still a single row.
    assert len(store.list_items()) == 1


def test_is_published_dedup_guard(store):
    """is_published reflects PUBLISHED status only (R-STATE dedup)."""
    store.upsert_item(
        ItemRecord(item_sku="LB-a", batch_folder_id="a", status=ItemStatus.NEW)
    )
    assert store.is_published("LB-a") is False
    store.set_status("LB-a", ItemStatus.PUBLISHED)
    assert store.is_published("LB-a") is True


def test_set_status_updates_timestamp(store):
    """set_status updates status and refreshes updated_at."""
    store.upsert_item(ItemRecord(item_sku="LB-a", batch_folder_id="a", updated_at="old"))
    store.set_status("LB-a", ItemStatus.EXTRACTED)
    got = store.get_item("LB-a")
    assert got.status is ItemStatus.EXTRACTED
    assert got.updated_at != "old"


def test_token_cache_roundtrip(store):
    """Token cache saves and reads back (R-AUTH)."""
    assert store.get_cached_token() is None
    store.save_cached_token(
        TokenCacheRecord(access_token="AT-1", expires_at_epoch=1234567.0, scopes="x y")
    )
    got = store.get_cached_token()
    assert got.access_token == "AT-1"
    assert got.expires_at_epoch == 1234567.0
    assert got.scopes == "x y"
    # Overwrite stays single-row.
    store.save_cached_token(
        TokenCacheRecord(access_token="AT-2", expires_at_epoch=2.0, scopes="")
    )
    assert store.get_cached_token().access_token == "AT-2"


def test_operations_use_fresh_configured_connections(tmp_path, monkeypatch):
    """Every public operation gets a distinct closed connection with safe pragmas."""
    real_connect = sqlite3.connect
    opened_connections = []
    connection_modes = []

    class TrackingConnection(sqlite3.Connection):
        """Capture per-connection configuration immediately before close."""

        closed_by_store = False
        observed_pragmas = None
        executed_sql = None

        def execute(self, sql, *args, **kwargs):
            """Record pragma assignments separately from read-only verification."""
            self.executed_sql.append(" ".join(str(sql).split()).upper())
            return super().execute(sql, *args, **kwargs)

        def close(self):
            """Record configured pragmas before delegating to SQLite close."""
            if not self.closed_by_store:
                self.observed_pragmas = (
                    self.execute("PRAGMA foreign_keys").fetchone()[0],
                    self.execute("PRAGMA busy_timeout").fetchone()[0],
                    self.execute("PRAGMA journal_mode").fetchone()[0],
                )
                self.closed_by_store = True
            super().close()

    def tracking_connect(*args, **kwargs):
        """Open a tracking subclass while preserving sqlite3.connect behavior."""
        connection_modes.append(kwargs.get("check_same_thread", True))
        kwargs["factory"] = TrackingConnection
        connection = real_connect(*args, **kwargs)
        connection.executed_sql = []
        opened_connections.append(connection)
        return connection

    monkeypatch.setattr(state_store_module.sqlite3, "connect", tracking_connect)
    store = StateStore(str(tmp_path / "configured.db"))
    try:
        store.upsert_item(ItemRecord(item_sku="LB-config", batch_folder_id="f"))
        assert store.get_item("LB-config") is not None
        assert store.is_published("LB-config") is False
        assert len(store.list_items()) == 1
        store.save_cached_token(
            TokenCacheRecord(access_token="fake", expires_at_epoch=1.0)
        )
        assert store.get_cached_token() is not None
    finally:
        store.close()

    # One initialization connection plus one fresh connection per operation.
    assert len(opened_connections) == 7
    assert len({id(connection) for connection in opened_connections}) == 7
    assert all(connection.closed_by_store for connection in opened_connections)
    assert all(connection.row_factory is sqlite3.Row for connection in opened_connections)
    assert all(
        connection.observed_pragmas == (1, 5000, "wal")
        for connection in opened_connections
    )
    assert connection_modes == [True] * 7
    wal_assignments = sum(
        sql == "PRAGMA JOURNAL_MODE = WAL"
        for connection in opened_connections
        for sql in connection.executed_sql
    )
    wal_verifications = sum(
        sql == "PRAGMA JOURNAL_MODE"
        for connection in opened_connections
        for sql in connection.executed_sql
    )
    assert wal_assignments == 1
    assert wal_verifications >= 6


def test_memory_store_shares_rows_across_operations_and_closes_idempotently():
    """The memory URI keeper preserves rows while close remains a safe no-op twice."""
    store = StateStore(":memory:")
    store.upsert_item(ItemRecord(item_sku="LB-memory", batch_folder_id="f"))
    assert store.get_item("LB-memory") is not None
    store.save_cached_token(
        TokenCacheRecord(access_token="fake-memory", expires_at_epoch=2.0)
    )
    assert store.get_cached_token() is not None

    store.close()
    store.close()
    with pytest.raises(RuntimeError, match="closed"):
        store.list_items()


def test_only_memory_keeper_disables_thread_affinity(monkeypatch):
    """Only the lifetime keeper opts out of SQLite's normal thread affinity."""
    real_connect = sqlite3.connect
    connection_modes = []

    def tracking_connect(*args, **kwargs):
        """Capture requested thread affinity without changing connection behavior."""
        connection_modes.append(kwargs.get("check_same_thread", True))
        return real_connect(*args, **kwargs)

    monkeypatch.setattr(state_store_module.sqlite3, "connect", tracking_connect)
    store = StateStore(":memory:")
    try:
        store.upsert_item(ItemRecord(item_sku="LB-affinity", batch_folder_id="f"))
        assert store.get_item("LB-affinity") is not None
    finally:
        store.close()

    assert connection_modes[0] is False
    assert connection_modes[1:] == [True, True, True]


def test_unversioned_database_is_backed_up_and_rows_are_preserved(tmp_path):
    """Version 1 preserves legacy item/token rows and leaves a readable backup."""
    database_path = tmp_path / "legacy.db"
    _create_legacy_database(database_path)

    store = StateStore(str(database_path))
    try:
        item = store.get_item("LB-legacy")
        token = store.get_cached_token()
        assert item is not None
        assert item.status is ItemStatus.PUBLISHED
        assert token is not None
        assert token.access_token == "fake-test-token"
    finally:
        store.close()

    backups = _backup_paths(database_path)
    assert len(backups) == 1
    backup = sqlite3.connect(backups[0])
    try:
        assert backup.execute("SELECT COUNT(*) FROM items").fetchone()[0] == 1
        assert backup.execute("SELECT COUNT(*) FROM token_cache").fetchone()[0] == 1
    finally:
        backup.close()

    live = sqlite3.connect(database_path)
    try:
        assert live.execute(
            "SELECT version FROM schema_migrations"
        ).fetchall() == [(1,)]
        assert live.execute("SELECT COUNT(*) FROM items").fetchone()[0] == 1
        assert live.execute("SELECT COUNT(*) FROM token_cache").fetchone()[0] == 1
    finally:
        live.close()


def test_latest_database_reopens_without_creating_backup(tmp_path):
    """New and already-current databases do not create migration backups."""
    database_path = tmp_path / "current.db"
    first = StateStore(str(database_path))
    first.close()
    assert _backup_paths(database_path) == []

    second = StateStore(str(database_path))
    second.close()
    assert _backup_paths(database_path) == []


def test_valid_current_schema_probes_leave_all_rows_unchanged(tmp_path):
    """Current-schema enforcement probes always roll back their harmless writes."""
    database_path = tmp_path / "current-probe.db"
    first = StateStore(str(database_path))
    try:
        first.upsert_item(
            ItemRecord(
                item_sku="LB-probe",
                batch_folder_id="fake-folder",
                status=ItemStatus.PRICED,
            )
        )
        first.save_cached_token(
            TokenCacheRecord(
                access_token="fake-probe-token",
                expires_at_epoch=1.0,
                scopes="fake-scope",
            )
        )
    finally:
        first.close()

    connection = sqlite3.connect(database_path)
    try:
        before = {
            "versions": connection.execute(
                "SELECT version, applied_at FROM schema_migrations ORDER BY version"
            ).fetchall(),
            "items": connection.execute(
                "SELECT * FROM items ORDER BY item_sku"
            ).fetchall(),
            "tokens": connection.execute(
                "SELECT * FROM token_cache ORDER BY id"
            ).fetchall(),
        }
    finally:
        connection.close()

    second = StateStore(str(database_path))
    second.close()

    connection = sqlite3.connect(database_path)
    try:
        after = {
            "versions": connection.execute(
                "SELECT version, applied_at FROM schema_migrations ORDER BY version"
            ).fetchall(),
            "items": connection.execute(
                "SELECT * FROM items ORDER BY item_sku"
            ).fetchall(),
            "tokens": connection.execute(
                "SELECT * FROM token_cache ORDER BY id"
            ).fetchall(),
        }
    finally:
        connection.close()

    assert after == before
    assert [row[0] for row in after["versions"]] == [1]
    assert [row[0] for row in after["tokens"]] == [1]
    assert _backup_paths(database_path) == []


def test_newer_schema_version_is_rejected(tmp_path):
    """A database newer than the application fails closed before migration."""
    database_path = tmp_path / "newer.db"
    _create_version_ledger(database_path, [2])
    with pytest.raises(StateStoreMigrationError, match="newer"):
        StateStore(str(database_path))


def test_gapped_schema_versions_are_rejected(tmp_path, monkeypatch):
    """An otherwise supported ledger cannot skip a migration version."""
    database_path = tmp_path / "gapped.db"
    _create_version_ledger(database_path, [1, 3])
    migration_one = state_store_module._MIGRATIONS[0]
    monkeypatch.setattr(
        state_store_module,
        "_MIGRATIONS",
        (migration_one, (2, ("SELECT 1",)), (3, ("SELECT 1",))),
    )
    # Every declared version needs a manifest before the ledger is even read;
    # the no-op versions here reuse the v1 manifest so the gap is what fails.
    v1_manifest = state_store_module._SCHEMA_MANIFESTS[1]
    monkeypatch.setattr(
        state_store_module,
        "_SCHEMA_MANIFESTS",
        {**state_store_module._SCHEMA_MANIFESTS, 2: v1_manifest, 3: v1_manifest},
    )
    with pytest.raises(StateStoreMigrationError, match="gapped"):
        StateStore(str(database_path))


def test_invalid_schema_version_is_rejected(tmp_path):
    """A non-integer ledger value fails closed as invalid state."""
    database_path = tmp_path / "invalid.db"
    _create_version_ledger(database_path, ["invalid"])
    with pytest.raises(StateStoreMigrationError, match="invalid"):
        StateStore(str(database_path))


def test_empty_migration_plan_is_rejected_before_database_creation(
    tmp_path, monkeypatch
):
    """An empty code-side migration plan fails before opening a database."""
    database_path = tmp_path / "empty-plan.db"
    monkeypatch.setattr(state_store_module, "_MIGRATIONS", ())
    with pytest.raises(StateStoreMigrationError, match="must contain"):
        StateStore(str(database_path))
    assert not database_path.exists()


@pytest.mark.parametrize("mutation", ["extra-column", "missing-token-table"])
def test_malformed_or_missing_legacy_schema_fails_without_version_stamp(
    tmp_path, mutation
):
    """A nonconforming legacy schema is backed up but never stamped version 1."""
    database_path = tmp_path / f"malformed-{mutation}.db"
    _create_legacy_database(database_path)
    connection = sqlite3.connect(database_path)
    try:
        if mutation == "extra-column":
            connection.execute("ALTER TABLE items ADD COLUMN unexpected TEXT")
        else:
            connection.execute("DROP TABLE token_cache")
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(StateStoreMigrationError, match="exact v1 schema"):
        StateStore(str(database_path))

    live = sqlite3.connect(database_path)
    try:
        tables = {
            row[0]
            for row in live.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        assert "schema_migrations" not in tables
        assert live.execute("SELECT COUNT(*) FROM items").fetchone()[0] == 1
    finally:
        live.close()

    backups = _backup_paths(database_path)
    assert len(backups) == 1
    backup = sqlite3.connect(backups[0])
    try:
        assert backup.execute("SELECT COUNT(*) FROM items").fetchone()[0] == 1
    finally:
        backup.close()
    assert list(tmp_path.glob("*.partial")) == []


def test_version_one_ledger_rejects_schema_without_token_id_check(tmp_path):
    """A v1 ledger cannot legitimize a table missing its frozen CHECK constraint."""
    database_path = tmp_path / "ledger-schema-mismatch.db"
    store = StateStore(str(database_path))
    store.close()

    connection = sqlite3.connect(database_path)
    try:
        connection.execute("DROP TABLE token_cache")
        connection.execute(
            """
            CREATE TABLE token_cache (
                id               INTEGER PRIMARY KEY,
                access_token     TEXT NOT NULL,
                expires_at_epoch REAL NOT NULL,
                scopes           TEXT NOT NULL DEFAULT ''
            )
            """
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(StateStoreMigrationError, match="CHECK constraint"):
        StateStore(str(database_path))
    assert _backup_paths(database_path) == []


@pytest.mark.parametrize(
    "id_definition",
    [
        pytest.param(
            "INTEGER PRIMARY KEY /* CHECK (id = 1) */",
            id="block-comment-only",
        ),
        pytest.param(
            "INTEGER PRIMARY KEY -- CHECK (id = 1)\n",
            id="line-comment-only",
        ),
        pytest.param(
            "INTEGER PRIMARY KEY CHECK ('CHECK (id = 1)' <> '')",
            id="string-literal-always-true",
        ),
        pytest.param("INTEGER PRIMARY KEY", id="missing-check"),
        pytest.param(
            "INTEGER PRIMARY KEY CHECK (id = 1) CHECK (id < 100)",
            id="extra-check",
        ),
    ],
)
def test_v1_ledger_rejects_noncanonical_token_constraint_sql(
    tmp_path, id_definition
):
    """Comments, literals, missing checks, and extra clauses cannot spoof v1."""
    database_path = tmp_path / "constraint-spoof.db"
    store = StateStore(str(database_path))
    try:
        store.save_cached_token(
            TokenCacheRecord(
                access_token="fake-preserved-token",
                expires_at_epoch=2.0,
                scopes="fake-scope",
            )
        )
    finally:
        store.close()
    _replace_token_cache_id_definition(database_path, id_definition)

    with pytest.raises(
        StateStoreMigrationError, match="canonical v1 CREATE TABLE SQL"
    ):
        StateStore(str(database_path))

    connection = sqlite3.connect(database_path)
    try:
        assert connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall() == [(1,)]
        assert connection.execute(
            """
            SELECT id, access_token, expires_at_epoch, scopes
            FROM token_cache
            ORDER BY id
            """
        ).fetchall() == [(1, "fake-preserved-token", 2.0, "fake-scope")]
    finally:
        connection.close()
    assert _backup_paths(database_path) == []


@pytest.mark.parametrize(
    "version_definition",
    [
        pytest.param(
            "INTEGER PRIMARY KEY /* CHECK (version >= 1) */",
            id="block-comment-only",
        ),
        pytest.param(
            "INTEGER PRIMARY KEY -- CHECK (version >= 1)\n",
            id="line-comment-only",
        ),
        pytest.param(
            "INTEGER PRIMARY KEY CHECK ('CHECK (version >= 1)' <> '')",
            id="string-literal-always-true",
        ),
        pytest.param("INTEGER PRIMARY KEY", id="missing-check"),
        pytest.param(
            "INTEGER PRIMARY KEY CHECK (version >= 1) CHECK (version < 100)",
            id="extra-check",
        ),
    ],
)
def test_v1_ledger_rejects_noncanonical_version_constraint_sql(
    tmp_path, version_definition
):
    """The ledger constraint cannot be supplied by comments or extra SQL."""
    database_path = tmp_path / "ledger-constraint-spoof.db"
    store = StateStore(str(database_path))
    store.close()
    _replace_migration_version_definition(database_path, version_definition)

    with pytest.raises(
        StateStoreMigrationError, match="canonical v1 CREATE TABLE SQL"
    ):
        StateStore(str(database_path))

    connection = sqlite3.connect(database_path)
    try:
        assert connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall() == [(1,)]
        assert connection.execute("SELECT COUNT(*) FROM token_cache").fetchone()[0] == 0
    finally:
        connection.close()
    assert _backup_paths(database_path) == []


@pytest.mark.parametrize("unenforced_table", ["schema_migrations", "token_cache"])
def test_constraint_behavior_probe_rejects_and_rolls_back_unenforced_checks(
    unenforced_table,
):
    """Behavior probes reject real writes and never retain version 0 or token id 2."""
    connection = sqlite3.connect(":memory:")
    connection.execute(
        f"""
        CREATE TABLE schema_migrations (
            version INTEGER PRIMARY KEY
                {'' if unenforced_table == 'schema_migrations' else 'CHECK (version >= 1)'},
            applied_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        f"""
        CREATE TABLE token_cache (
            id INTEGER PRIMARY KEY
                {'' if unenforced_table == 'token_cache' else 'CHECK (id = 1)'},
            access_token TEXT NOT NULL,
            expires_at_epoch REAL NOT NULL,
            scopes TEXT NOT NULL DEFAULT ''
        )
        """
    )
    connection.execute(
        "INSERT INTO schema_migrations VALUES (1, 'fake-applied-at')"
    )
    connection.execute(
        "INSERT INTO token_cache VALUES (1, 'fake-token', 3.0, 'fake-scope')"
    )
    connection.commit()

    with pytest.raises(StateStoreMigrationError, match="does not enforce"):
        state_store_module._validate_constraint_behavior(
            connection, state_store_module._V1_SCHEMA_COLUMNS
        )

    assert connection.in_transaction is False
    assert connection.execute(
        "SELECT version FROM schema_migrations ORDER BY version"
    ).fetchall() == [(1,)]
    assert connection.execute(
        "SELECT id FROM token_cache ORDER BY id"
    ).fetchall() == [(1,)]
    connection.close()


def test_failed_migration_rolls_back_and_preserves_readable_backup(
    tmp_path, monkeypatch
):
    """Injected DDL failure restores the live schema and retains original rows."""
    database_path = tmp_path / "rollback.db"
    _create_legacy_database(database_path)
    monkeypatch.setattr(
        state_store_module,
        "_MIGRATIONS",
        state_store_module._MIGRATIONS
        + (
            (
                2,
                (
                    "CREATE TABLE migration_probe (id INTEGER PRIMARY KEY)",
                    "INSERT INTO missing_migration_table (id) VALUES (1)",
                ),
            ),
        ),
    )
    monkeypatch.setattr(
        state_store_module,
        "_SCHEMA_MANIFESTS",
        {**state_store_module._SCHEMA_MANIFESTS, 2: _v2_probe_manifest()},
    )

    with pytest.raises(StateStoreMigrationError, match="rolled back"):
        StateStore(str(database_path))

    live = sqlite3.connect(database_path)
    try:
        table_names = {
            row[0]
            for row in live.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        assert "schema_migrations" not in table_names
        assert "migration_probe" not in table_names
        assert live.execute("SELECT COUNT(*) FROM items").fetchone()[0] == 1
        assert live.execute("SELECT COUNT(*) FROM token_cache").fetchone()[0] == 1
    finally:
        live.close()

    backups = _backup_paths(database_path)
    assert len(backups) == 1
    backup = sqlite3.connect(backups[0])
    try:
        assert backup.execute("SELECT COUNT(*) FROM items").fetchone()[0] == 1
        assert backup.execute("SELECT COUNT(*) FROM token_cache").fetchone()[0] == 1
    finally:
        backup.close()


# ── Cycle 4: lock-held backup eligibility ────────────────────────────────────


def test_legacy_database_appearing_before_lock_still_gets_backup(
    tmp_path, monkeypatch
):
    """A legacy database created just before the connection opens is backed up.

    Cycle-3 QA reproduced a zero-backup migration by injecting the database
    after the pre-lock file-size precheck. Backup eligibility now derives from
    schema objects observed under BEGIN IMMEDIATE, so the interleaving cannot
    skip the snapshot.
    """
    database_path = tmp_path / "gap-legacy.db"
    original_open = StateStore._open_connection
    injected = {"done": False}

    def open_with_injected_legacy(self, *args, **kwargs):
        """Create the exact legacy database in the former precheck gap."""
        if not injected["done"] and kwargs.get("enable_wal"):
            _create_legacy_database(database_path)
            injected["done"] = True
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(StateStore, "_open_connection", open_with_injected_legacy)

    store = StateStore(str(database_path))
    try:
        item = store.get_item("LB-legacy")
        assert item is not None and item.status is ItemStatus.PUBLISHED
        assert store.get_cached_token() is not None
    finally:
        store.close()

    assert injected["done"] is True
    backups = _backup_paths(database_path)
    assert len(backups) == 1
    backup = sqlite3.connect(backups[0])
    try:
        assert backup.execute("SELECT COUNT(*) FROM items").fetchone()[0] == 1
        assert backup.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE name = 'schema_migrations'"
        ).fetchone()[0] == 0
    finally:
        backup.close()


def test_file_without_schema_objects_creates_no_backup(tmp_path):
    """A zero-object database has nothing to preserve, so no backup is written."""
    database_path = tmp_path / "header-only.db"
    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA user_version = 0")
    connection.close()

    store = StateStore(str(database_path))
    store.close()
    assert _backup_paths(database_path) == []


# ── Cycle 4: retry-safe WAL activation ───────────────────────────────────────


def _locked_error() -> sqlite3.OperationalError:
    """Build an OperationalError shaped like SQLite lock contention."""
    error = sqlite3.OperationalError("database is locked")
    try:
        error.sqlite_errorcode = sqlite3.SQLITE_BUSY
    except AttributeError:
        pass
    return error


def _is_wal_assignment(sql) -> bool:
    """Return True when a statement is the WAL journal-mode assignment."""
    return " ".join(str(sql).split()).upper() == "PRAGMA JOURNAL_MODE = WAL"


def test_wal_activation_retries_through_transient_lock_contention(
    tmp_path, monkeypatch
):
    """The first constructor survives BUSY on the journal-mode pragma."""
    real_connect = sqlite3.connect
    attempts = {"wal": 0}
    sleeps: list[float] = []

    class ContendedConnection(sqlite3.Connection):
        """Fail the WAL assignment twice before letting SQLite apply it."""

        def execute(self, sql, *args, **kwargs):
            """Raise contention on the first two WAL assignments only."""
            if _is_wal_assignment(sql):
                attempts["wal"] += 1
                if attempts["wal"] <= 2:
                    raise _locked_error()
            return super().execute(sql, *args, **kwargs)

    def contended_connect(*args, **kwargs):
        """Open the contended subclass while preserving sqlite3.connect behavior."""
        kwargs["factory"] = ContendedConnection
        return real_connect(*args, **kwargs)

    monkeypatch.setattr(state_store_module.sqlite3, "connect", contended_connect)
    monkeypatch.setattr(state_store_module.time, "sleep", sleeps.append)

    store = StateStore(str(tmp_path / "contended.db"))
    try:
        store.upsert_item(ItemRecord(item_sku="LB-wal", batch_folder_id="f"))
        assert store.get_item("LB-wal") is not None
    finally:
        store.close()

    assert attempts["wal"] == 3
    assert len(sleeps) == 2
    assert sleeps == sorted(sleeps)
    live = sqlite3.connect(tmp_path / "contended.db")
    try:
        assert live.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    finally:
        live.close()


def test_wal_activation_gives_up_at_deadline_and_fails_closed(tmp_path, monkeypatch):
    """Permanent contention ends in a migration error, not a stuck constructor."""
    real_connect = sqlite3.connect

    class AlwaysLockedConnection(sqlite3.Connection):
        """Never allow the WAL assignment to succeed."""

        def execute(self, sql, *args, **kwargs):
            """Raise contention on every WAL assignment."""
            if _is_wal_assignment(sql):
                raise _locked_error()
            return super().execute(sql, *args, **kwargs)

    def locked_connect(*args, **kwargs):
        """Open the always-locked subclass."""
        kwargs["factory"] = AlwaysLockedConnection
        return real_connect(*args, **kwargs)

    clock = {"now": 1000.0}

    def fake_monotonic() -> float:
        """Advance one second per read so the deadline arrives quickly."""
        clock["now"] += 1.0
        return clock["now"]

    monkeypatch.setattr(state_store_module.sqlite3, "connect", locked_connect)
    monkeypatch.setattr(state_store_module.time, "monotonic", fake_monotonic)
    monkeypatch.setattr(state_store_module.time, "sleep", lambda _seconds: None)

    with pytest.raises(StateStoreMigrationError, match="WAL"):
        StateStore(str(tmp_path / "always-locked.db"))


def test_non_contention_wal_failure_is_not_retried(tmp_path, monkeypatch):
    """A non-lock OperationalError fails immediately without any sleep."""
    real_connect = sqlite3.connect
    sleeps: list[float] = []

    class BrokenConnection(sqlite3.Connection):
        """Fail the WAL assignment with an unrelated error."""

        def execute(self, sql, *args, **kwargs):
            """Raise a non-contention error on the WAL assignment."""
            if _is_wal_assignment(sql):
                raise sqlite3.OperationalError("disk I/O error")
            return super().execute(sql, *args, **kwargs)

    def broken_connect(*args, **kwargs):
        """Open the broken subclass."""
        kwargs["factory"] = BrokenConnection
        return real_connect(*args, **kwargs)

    monkeypatch.setattr(state_store_module.sqlite3, "connect", broken_connect)
    monkeypatch.setattr(state_store_module.time, "sleep", sleeps.append)

    with pytest.raises(StateStoreMigrationError, match="WAL"):
        StateStore(str(tmp_path / "broken.db"))
    assert sleeps == []


def test_existing_wal_database_skips_journal_mode_assignment(tmp_path, monkeypatch):
    """Reopening a WAL database reads the mode and never requests the exclusive lock."""
    database_path = tmp_path / "reopen.db"
    StateStore(str(database_path)).close()

    real_connect = sqlite3.connect
    executed: list[str] = []

    class RecordingConnection(sqlite3.Connection):
        """Record every statement text."""

        def execute(self, sql, *args, **kwargs):
            """Capture normalized SQL then delegate."""
            executed.append(" ".join(str(sql).split()).upper())
            return super().execute(sql, *args, **kwargs)

    def recording_connect(*args, **kwargs):
        """Open the recording subclass."""
        kwargs["factory"] = RecordingConnection
        return real_connect(*args, **kwargs)

    monkeypatch.setattr(state_store_module.sqlite3, "connect", recording_connect)
    StateStore(str(database_path)).close()

    assert "PRAGMA JOURNAL_MODE = WAL" not in executed
    assert "PRAGMA JOURNAL_MODE" in executed


# ── Cycle 4: version-specific schema manifests ───────────────────────────────


def test_migration_plan_without_matching_manifest_is_rejected(tmp_path, monkeypatch):
    """A declared migration version with no target manifest cannot run."""
    monkeypatch.setattr(
        state_store_module,
        "_MIGRATIONS",
        state_store_module._MIGRATIONS + ((2, ("SELECT 1",)),),
    )
    database_path = tmp_path / "no-manifest.db"
    with pytest.raises(StateStoreMigrationError, match="same version sequence"):
        StateStore(str(database_path))
    assert not database_path.exists()


def test_manifest_without_matching_migration_is_rejected(tmp_path, monkeypatch):
    """An orphan manifest version is a plan defect, not a silent extra."""
    monkeypatch.setattr(
        state_store_module,
        "_SCHEMA_MANIFESTS",
        {**state_store_module._SCHEMA_MANIFESTS, 2: _v2_probe_manifest()},
    )
    with pytest.raises(StateStoreMigrationError, match="same version sequence"):
        StateStore(str(tmp_path / "orphan-manifest.db"))


def test_future_migration_cannot_stamp_preexisting_malformed_table(
    tmp_path, monkeypatch
):
    """CREATE TABLE IF NOT EXISTS cannot hide a malformed table from v2 validation.

    Reproduces the cycle-3 adversarial-critic finding: a valid v1 database that
    already contains a malformed ``migration_probe`` table must not be stamped
    version 2 when the v2 migration uses IF NOT EXISTS.
    """
    database_path = tmp_path / "malformed-future.db"
    StateStore(str(database_path)).close()

    connection = sqlite3.connect(database_path)
    try:
        connection.execute(
            "CREATE TABLE migration_probe "
            "(id TEXT, unexpected INTEGER NOT NULL DEFAULT 0)"
        )
        connection.execute("INSERT INTO migration_probe VALUES ('bad-row', 1)")
        connection.commit()
    finally:
        connection.close()

    monkeypatch.setattr(
        state_store_module,
        "_MIGRATIONS",
        state_store_module._MIGRATIONS
        + (
            (
                2,
                (
                    "CREATE TABLE IF NOT EXISTS migration_probe "
                    "(id INTEGER PRIMARY KEY)",
                ),
            ),
        ),
    )
    monkeypatch.setattr(
        state_store_module,
        "_SCHEMA_MANIFESTS",
        {**state_store_module._SCHEMA_MANIFESTS, 2: _v2_probe_manifest()},
    )

    with pytest.raises(StateStoreMigrationError, match="schema"):
        StateStore(str(database_path))

    live = sqlite3.connect(database_path)
    try:
        assert live.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall() == [(1,)]
        assert live.execute("SELECT COUNT(*) FROM migration_probe").fetchone()[0] == 1
    finally:
        live.close()


def test_future_migration_with_exact_target_table_is_stamped(tmp_path, monkeypatch):
    """A v2 migration whose result matches the v2 manifest completes and stamps."""
    database_path = tmp_path / "v2-ok.db"
    StateStore(str(database_path)).close()

    monkeypatch.setattr(
        state_store_module,
        "_MIGRATIONS",
        state_store_module._MIGRATIONS
        + ((2, ("CREATE TABLE migration_probe (id INTEGER PRIMARY KEY)",)),),
    )
    monkeypatch.setattr(
        state_store_module,
        "_SCHEMA_MANIFESTS",
        {**state_store_module._SCHEMA_MANIFESTS, 2: _v2_probe_manifest()},
    )

    StateStore(str(database_path)).close()

    live = sqlite3.connect(database_path)
    try:
        assert live.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall() == [(1,), (2,)]
    finally:
        live.close()
    # Migrating an existing current database still leaves exactly one backup.
    assert len(_backup_paths(database_path)) == 1


def test_unexpected_extra_table_in_current_database_is_rejected(tmp_path):
    """Any user object outside the version manifest is schema drift."""
    database_path = tmp_path / "extra-table.db"
    StateStore(str(database_path)).close()

    connection = sqlite3.connect(database_path)
    try:
        connection.execute("CREATE TABLE stray (id INTEGER PRIMARY KEY)")
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(StateStoreMigrationError, match="Unexpected schema object"):
        StateStore(str(database_path))

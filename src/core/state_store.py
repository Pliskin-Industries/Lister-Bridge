"""
Module: state_store.py
Purpose: SQLite-backed state for dedup/resume — processed items, SKUs, eBay
         offer/listing IDs, EPS URLs, and the eBay access-token cache.
Primary Responsibilities:
  - Create/migrate the SQLite schema (items table + token cache).
  - Upsert/read ItemRecord rows keyed by the deterministic item_sku.
  - Provide dedup queries (is this SKU already published?) for the orchestrator.
  - Cache the eBay OAuth access token (TokenCacheRecord) for ebay_auth.
  - Open a normally thread-affine SQLite connection for each public operation.
  - Apply ordered schema migrations transactionally and back up legacy files.
  - Validate every schema version against its own complete frozen manifest,
    decide backup eligibility only after cross-process serialization, and
    retry WAL activation through transient SQLite lock contention (cycle 4).
Key Interfaces:
  - Input: ItemRecord / TokenCacheRecord writes from orchestrator.py & ebay_auth.py.
  - Output: ItemRecord / TokenCacheRecord reads; STATE_STORE_DB_PATH from .env.
FMEA Constraints Enforced:
  - R-STATE — item_sku is the local deduplication key; rows preserve the latest
    status and remote IDs that callers explicitly persist.
  - R-AUTH / R-COST — token cache avoids re-minting a valid (~2h) access token.
  - PI-010 / R-STATE - isolated connections and transactional migrations protect
    local durable state. Remote checkpoints, reconciliation, and duplicate-
    publication prevention remain T-005 scope.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from src.contracts import ItemRecord, ItemStatus, TokenCacheRecord
from src.core.paths import load_app_dotenv, resolve_app_path

# Frozen-aware .env discovery (tries the exe dir / %APPDATA%/ListerBridge
# first when running as a PyInstaller onefile build; unchanged plain
# load_dotenv() otherwise). See src/core/paths.py (R-STATE).
load_app_dotenv()

# Default DB location if STATE_STORE_DB_PATH is unset.
_DEFAULT_DB_PATH = "data/state/lister_bridge.db"

# The token cache holds a single row, addressed by this fixed id.
_TOKEN_ROW_ID = 1

# SQLite configuration is repeated for every operation-owned connection.
_BUSY_TIMEOUT_MS = 5000

# ``PRAGMA journal_mode = WAL`` needs a brief exclusive lock. SQLite does not
# always invoke the busy handler for that escalation, so concurrent
# constructors can observe SQLITE_BUSY / SQLITE_LOCKED even with busy_timeout
# set (cycle-3 QA AC4 failure). Activation therefore retries with a short
# backoff until the same deadline the busy timeout would have allowed.
_WAL_RETRY_INITIAL_DELAY_S = 0.005
_WAL_RETRY_MAX_DELAY_S = 0.1
_LOCK_CONTENTION_CODES = frozenset(
    code
    for code in (
        getattr(sqlite3, "SQLITE_BUSY", None),
        getattr(sqlite3, "SQLITE_LOCKED", None),
    )
    if code is not None
)

# Process-local locks prevent two StateStore constructors in this process from
# racing before SQLite's BEGIN IMMEDIATE lock serializes schema inspection.
_PATH_LOCKS_GUARD = threading.Lock()
_PATH_LOCKS: dict[str, threading.RLock] = {}

# Version 1 preserves the original items/token_cache columns and row contracts.
# Statements remain discrete so migration execution never uses executescript(),
# whose implicit transaction behavior makes reliable rollback harder to prove.
_MIGRATIONS: tuple[tuple[int, tuple[str, ...]], ...] = (
    (
        1,
        (
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version    INTEGER PRIMARY KEY CHECK (version >= 1),
                applied_at TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS items (
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
            CREATE TABLE IF NOT EXISTS token_cache (
                id               INTEGER PRIMARY KEY CHECK (id = 1),
                access_token     TEXT NOT NULL,
                expires_at_epoch REAL NOT NULL,
                scopes           TEXT NOT NULL DEFAULT ''
            )
            """,
        ),
    ),
)

# PRAGMA table_info returns name, declared type, NOT NULL, default, and primary
# key position. These tuples freeze the exact v1 row contracts and column order.
_ITEM_COLUMNS = (
    ("item_sku", "TEXT", 0, None, 1),
    ("batch_folder_id", "TEXT", 1, None, 0),
    ("status", "TEXT", 1, None, 0),
    ("offer_id", "TEXT", 0, None, 0),
    ("listing_id", "TEXT", 0, None, 0),
    ("eps_urls", "TEXT", 1, "'[]'", 0),
    ("updated_at", "TEXT", 1, None, 0),
)
_TOKEN_COLUMNS = (
    ("id", "INTEGER", 0, None, 1),
    ("access_token", "TEXT", 1, None, 0),
    ("expires_at_epoch", "REAL", 1, None, 0),
    ("scopes", "TEXT", 1, "''", 0),
)
_VERSION_COLUMNS = (
    ("version", "INTEGER", 0, None, 1),
    ("applied_at", "TEXT", 1, None, 0),
)
_V1_SCHEMA_COLUMNS = {
    "schema_migrations": _VERSION_COLUMNS,
    "items": _ITEM_COLUMNS,
    "token_cache": _TOKEN_COLUMNS,
}
_LEGACY_SCHEMA_COLUMNS = {
    "items": _ITEM_COLUMNS,
    "token_cache": _TOKEN_COLUMNS,
}

# SQLite removes ``IF NOT EXISTS`` and a trailing statement semicolon before it
# stores CREATE TABLE text in sqlite_master. Both the original legacy schema and
# migration 1 therefore converge on exactly these demonstrated forms. Validation
# may fold case and whitespace, but it must not discard comments, quoted tokens,
# string literals, or additional clauses: any such text is schema drift.
_CANONICAL_TABLE_SQL: dict[str, tuple[str, ...]] = {
    "schema_migrations": (
        """
        CREATE TABLE schema_migrations (
            version    INTEGER PRIMARY KEY CHECK (version >= 1),
            applied_at TEXT NOT NULL
        )
        """,
    ),
    "items": (
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
    ),
    "token_cache": (
        """
        CREATE TABLE token_cache (
            id               INTEGER PRIMARY KEY CHECK (id = 1),
            access_token     TEXT NOT NULL,
            expires_at_epoch REAL NOT NULL,
            scopes           TEXT NOT NULL DEFAULT ''
        )
        """,
    ),
}

# Harmless writes that SQLite must reject with SQLITE_CONSTRAINT_CHECK when the
# frozen safety constraints are really enforced. They run inside a rollback-only
# savepoint, so neither a rejected nor an accidentally accepted probe persists.
_CHECK_PROBES: dict[str, tuple[tuple[str, tuple[object, ...]], ...]] = {
    "schema_migrations": (
        (
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (0, "constraint-probe"),
        ),
    ),
    "token_cache": (
        (
            "INSERT OR REPLACE INTO token_cache "
            "(id, access_token, expires_at_epoch, scopes) "
            "VALUES (?, ?, ?, ?)",
            (2, "constraint-probe", 1.0, ""),
        ),
    ),
}

# One complete target manifest per schema version: table name -> (exact PRAGMA
# column tuples, allowed canonical CREATE TABLE forms). Version 0 is the
# unversioned legacy layout. Every declared migration version must own an entry
# so validation checks the objects that version introduces rather than
# re-checking version 1 forever (cycle-3 adversarial-critic finding). A
# database may hold no user object outside its version's manifest.
_SCHEMA_MANIFESTS: dict[
    int,
    dict[str, tuple[tuple[tuple[str, str, int, str | None, int], ...], tuple[str, ...]]],
] = {
    0: {
        name: (_LEGACY_SCHEMA_COLUMNS[name], _CANONICAL_TABLE_SQL[name])
        for name in _LEGACY_SCHEMA_COLUMNS
    },
    1: {
        name: (_V1_SCHEMA_COLUMNS[name], _CANONICAL_TABLE_SQL[name])
        for name in _V1_SCHEMA_COLUMNS
    },
}


def _manifest_label(version: int) -> str:
    """Return the human-readable schema label; legacy tables are v1 tables."""
    return "v1" if version <= 1 else f"v{version}"


class StateStoreMigrationError(RuntimeError):
    """Raised when a schema ledger or migration cannot be applied safely."""


def _utc_now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string (for updated_at)."""
    return datetime.now(timezone.utc).isoformat()


def _resolve_db_path(db_path: str | None) -> str:
    """
    Resolve the SQLite DB path, anchoring a relative path to a run-safe root.

    Args:
        db_path: Explicit path, or None to read STATE_STORE_DB_PATH / default.

    Returns:
        An absolute path string; the parent directory is created if missing.

    Side Effects:
        Creates the parent directory tree.

    FMEA Constraints:
        R-STATE — relative paths are anchored via resolve_app_path(), which
        anchors to %APPDATA%/ListerBridge when frozen (PyInstaller onefile)
        instead of the ephemeral sys._MEIPASS extraction dir, so the dedup DB
        survives across runs of the packaged .exe.
    """
    raw = db_path or os.environ.get("STATE_STORE_DB_PATH") or _DEFAULT_DB_PATH
    # resolve_app_path anchors relative paths appropriately for the current
    # runtime mode (frozen vs. source) and passes absolute paths through as-is.
    resolved = resolve_app_path(raw)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return str(resolved)


def _path_lock(key: str) -> threading.RLock:
    """Return the stable process-local initialization lock for one database."""
    with _PATH_LOCKS_GUARD:
        return _PATH_LOCKS.setdefault(key, threading.RLock())


def _validate_migration_plan() -> None:
    """Reject an unordered, gapped, empty, or malformed migration plan."""
    if not _MIGRATIONS:
        raise StateStoreMigrationError(
            "The migration plan must contain schema version 1."
        )
    versions = [migration[0] for migration in _MIGRATIONS]
    if versions != list(range(1, len(_MIGRATIONS) + 1)):
        raise StateStoreMigrationError(
            "Migration definitions must be ordered and contiguous from version 1."
        )
    for version, statements in _MIGRATIONS:
        if not statements or any(
            not isinstance(sql, str) or not sql.strip() for sql in statements
        ):
            raise StateStoreMigrationError(
                f"Migration version {version} contains an invalid SQL statement."
            )

    # Every migration version needs its own complete target manifest, and the
    # legacy layout needs version 0. A plan whose version sequence and manifest
    # sequence differ cannot prove what it stamps (cycle-4 exit condition).
    expected_manifest_versions = [0, *versions]
    if sorted(_SCHEMA_MANIFESTS) != expected_manifest_versions:
        raise StateStoreMigrationError(
            "Migration versions and schema manifests must describe the same "
            "version sequence."
        )
    for version, manifest in _SCHEMA_MANIFESTS.items():
        if not manifest or any(
            not columns or not create_sql for columns, create_sql in manifest.values()
        ):
            raise StateStoreMigrationError(
                f"Schema manifest for version {version} is incomplete."
            )


def _is_lock_contention(exc: sqlite3.OperationalError) -> bool:
    """Return True when an OperationalError is transient BUSY/LOCKED contention."""
    code = getattr(exc, "sqlite_errorcode", None)
    if code is not None and code in _LOCK_CONTENTION_CODES:
        return True
    message = str(exc).lower()
    return "locked" in message or "busy" in message


def _user_schema_objects(connection: sqlite3.Connection) -> set[tuple[str, str]]:
    """Return every (type, name) schema object except SQLite's own internals."""
    rows = connection.execute(
        r"""
        SELECT type, name
        FROM sqlite_master
        WHERE name NOT LIKE 'sqlite\_%' ESCAPE '\'
        """
    ).fetchall()
    return {(str(row["type"]), str(row["name"])) for row in rows}


def _table_columns(
    connection: sqlite3.Connection, table_name: str
) -> tuple[tuple[str, str, int, str | None, int], ...]:
    """Return normalized PRAGMA metadata for one expected table."""
    rows = connection.execute(f'PRAGMA table_info("{table_name}")').fetchall()
    return tuple(
        (
            str(row["name"]),
            str(row["type"]).strip().upper(),
            int(row["notnull"]),
            row["dflt_value"],
            int(row["pk"]),
        )
        for row in rows
    )


def _table_create_sql(connection: sqlite3.Connection, table_name: str) -> str:
    """Return the CREATE TABLE SQL retained by SQLite for one state table."""
    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    if row is None or row["sql"] is None:
        raise StateStoreMigrationError(
            f"Required state table {table_name!r} is missing."
        )
    return str(row["sql"])


def _canonicalize_create_sql(sql: str) -> str:
    """
    Fold only superficial CREATE TABLE case and whitespace differences.

    Comment markers, literal/identifier delimiters, punctuation, and every SQL
    clause remain in the result. Full-string equality therefore cannot be
    satisfied by placing required constraint text in a comment or literal.
    """
    return re.sub(r"\s+", " ", sql.strip()).casefold()


def _require_check_rejection(
    connection: sqlite3.Connection,
    *,
    table_name: str,
    statement: str,
    parameters: tuple[object, ...],
) -> None:
    """Require one harmless probe write to fail specifically as a CHECK."""
    try:
        connection.execute(statement, parameters)
    except sqlite3.IntegrityError as exc:
        if getattr(exc, "sqlite_errorcode", None) == sqlite3.SQLITE_CONSTRAINT_CHECK:
            return
        raise StateStoreMigrationError(
            f"State table {table_name!r} rejected its constraint probe for an "
            "unexpected reason."
        ) from exc
    raise StateStoreMigrationError(
        f"State table {table_name!r} does not enforce its required CHECK constraint."
    )


def _validate_constraint_behavior(
    connection: sqlite3.Connection,
    expected_tables: dict[
        str, tuple[tuple[str, str, int, str | None, int], ...]
    ],
) -> None:
    """Probe required CHECK constraints inside a rollback-only savepoint."""
    savepoint = "state_schema_constraint_validation"
    connection.execute(f"SAVEPOINT {savepoint}")
    try:
        # Probes are keyed by table so a future manifest version can declare
        # its own constraint probes without editing this function.
        for table_name in expected_tables:
            for statement, parameters in _CHECK_PROBES.get(table_name, ()):
                _require_check_rejection(
                    connection,
                    table_name=table_name,
                    statement=statement,
                    parameters=parameters,
                )
    finally:
        # Roll back both successful malicious writes and expected failed probes.
        # RELEASE restores the caller's transaction nesting without committing.
        connection.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
        connection.execute(f"RELEASE SAVEPOINT {savepoint}")


def _validate_exact_schema(connection: sqlite3.Connection, version: int) -> None:
    """
    Validate the live schema against one version's complete frozen manifest.

    Args:
        connection: The migration connection, already inside BEGIN IMMEDIATE.
        version: The manifest version the database must match exactly (0 for
            the unversioned legacy layout).

    Raises:
        StateStoreMigrationError: On any missing, extra, or drifted object,
            noncanonical CREATE TABLE text, or unenforced CHECK constraint.
    """
    manifest = _SCHEMA_MANIFESTS[version]
    label = _manifest_label(version)

    # The manifest is the whole schema: an object outside it is drift, and a
    # preexisting malformed table cannot hide behind CREATE TABLE IF NOT EXISTS
    # in a later migration because that version's manifest names it exactly.
    actual_objects = _user_schema_objects(connection)
    if version == 0 and ("table", "schema_migrations") in actual_objects:
        raise StateStoreMigrationError(
            "An unversioned legacy database has an unexpected version ledger."
        )
    expected_objects = {("table", table_name) for table_name in manifest}
    missing = sorted(name for kind, name in expected_objects - actual_objects)
    if missing:
        raise StateStoreMigrationError(
            f"State table(s) {missing!r} are missing; the database does not "
            f"match the exact {label} schema."
        )
    unexpected = sorted(f"{kind} {name}" for kind, name in actual_objects - expected_objects)
    if unexpected:
        raise StateStoreMigrationError(
            f"Unexpected schema object(s) {unexpected!r} prevent an exact "
            f"{label} schema match."
        )

    for table_name, (expected_columns, canonical_forms) in manifest.items():
        actual_columns = _table_columns(connection, table_name)
        if actual_columns != expected_columns:
            raise StateStoreMigrationError(
                f"State table {table_name!r} does not match the exact {label} schema."
            )

        actual_sql = _canonicalize_create_sql(
            _table_create_sql(connection, table_name)
        )
        allowed_sql = {
            _canonicalize_create_sql(statement) for statement in canonical_forms
        }
        if actual_sql not in allowed_sql:
            raise StateStoreMigrationError(
                f"State table {table_name!r} does not match the canonical {label} "
                "CREATE TABLE SQL, including its required CHECK constraints."
            )

    # Full canonical SQL equality is the primary guard. The rollback-only writes
    # independently confirm that SQLite enforces the two safety constraints.
    _validate_constraint_behavior(connection, manifest)


class StateStore:
    """
    SQLite state store. One instance owns one database file.

    The items table has ≤7 columns (item_sku PK, batch_folder_id, status,
    offer_id, listing_id, eps_urls, updated_at). A small token_cache table holds
    the eBay access token. Item writes replace one local row keyed by item_sku;
    they do not provide remote publication claims, checkpoints, or reconciliation.

    File-backed databases use WAL. In-memory stores use a unique shared-memory
    URI plus a private keeper connection so operation-owned connections observe
    the same ephemeral schema and rows.
    """

    def __init__(self, db_path: str | None = None) -> None:
        """
        Open (and lazily create/migrate) the SQLite database.

        Args:
            db_path: Override for STATE_STORE_DB_PATH (else env / default). Pass
                ":memory:" for an ephemeral in-process DB (used by tests).

        Returns:
            None

        Side Effects:
            Opens a SQLite connection; creates the schema on first use.
            Operation connections are short-lived. A pre-migration backup is
            created only for a nonempty existing file with pending migrations.
        """
        # Historical behavior replaced by T-004 used these implementation rules:
        # ":memory:" is passed straight through; everything else is resolved/created.
        # check_same_thread=False keeps a single Streamlit/orchestrator process
        # flexible across threads; access is serialized by SQLite's own locking.
        # T-004 instead uses a shared-memory URI keeper and thread-affine
        # operation-owned connections.
        self._lifecycle_lock = threading.RLock()
        self._closed = False
        self._keeper: sqlite3.Connection | None = None
        self._is_memory = db_path == ":memory:"

        if self._is_memory:
            self.db_path = ":memory:"
            self._connect_target = (
                f"file:lister_bridge_{uuid.uuid4().hex}?mode=memory&cache=shared"
            )
            self._connect_uri = True
            self._lock_key = self._connect_target
            self._keeper = self._open_connection(keeper=True)
        else:
            self.db_path = _resolve_db_path(db_path)
            self._connect_target = self.db_path
            self._connect_uri = False
            self._lock_key = os.path.normcase(os.path.abspath(self.db_path))

        try:
            self._initialize_schema()
        except BaseException:
            # A failed constructor must not leak the shared-memory keeper.
            with self._lifecycle_lock:
                if self._keeper is not None:
                    self._keeper.close()
                    self._keeper = None
                self._closed = True
            raise

    def _open_connection(
        self, *, enable_wal: bool = False, keeper: bool = False
    ) -> sqlite3.Connection:
        """
        Open and configure a normally thread-affine SQLite connection.

        Args:
            enable_wal: Set persistent WAL mode for a file-backed database.
            keeper: Permit only the lifetime memory keeper to cross threads.

        Returns:
            A configured connection owned by the calling operation.

        Side Effects:
            File initialization can persist WAL journal mode.
        """
        if keeper:
            connection = sqlite3.connect(
                self._connect_target,
                timeout=_BUSY_TIMEOUT_MS / 1000,
                uri=self._connect_uri,
                check_same_thread=False,
            )
        else:
            connection = sqlite3.connect(
                self._connect_target,
                timeout=_BUSY_TIMEOUT_MS / 1000,
                uri=self._connect_uri,
            )
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(f"PRAGMA busy_timeout = {_BUSY_TIMEOUT_MS}")
            if enable_wal and not self._is_memory:
                self._activate_wal(connection)
            elif not self._is_memory:
                journal_mode = connection.execute("PRAGMA journal_mode").fetchone()
                if journal_mode is None or str(journal_mode[0]).lower() != "wal":
                    raise StateStoreMigrationError(
                        "The file-backed state database is not in WAL mode."
                    )
            return connection
        except BaseException:
            connection.close()
            raise

    @staticmethod
    def _activate_wal(connection: sqlite3.Connection) -> None:
        """
        Put a file-backed database into WAL mode, tolerating lock contention.

        Args:
            connection: The freshly opened initialization connection.

        Returns:
            None

        Side Effects:
            May persist WAL journal mode in the database header. Sleeps with
            bounded backoff while another process holds the lock the pragma
            needs; gives up at the busy-timeout deadline.

        Raises:
            StateStoreMigrationError: If the mode is still not WAL after the
                deadline, or the pragma fails for a non-contention reason.

        FMEA Constraints:
            PI-010 / R-STATE — every concurrent constructor must reach the
            BEGIN IMMEDIATE migration lock instead of dying on a transient
            BUSY/LOCKED result while switching journal modes (cycle-3 AC4).
        """
        # An already-WAL database (every run after the first) never needs the
        # exclusive lock, so read first and skip the assignment when possible.
        current = connection.execute("PRAGMA journal_mode").fetchone()
        if current is not None and str(current[0]).lower() == "wal":
            return

        deadline = time.monotonic() + _BUSY_TIMEOUT_MS / 1000
        delay = _WAL_RETRY_INITIAL_DELAY_S
        while True:
            try:
                journal_mode = connection.execute("PRAGMA journal_mode = WAL").fetchone()
            except sqlite3.OperationalError as exc:
                # Only BUSY/LOCKED is retried; anything else is a real failure.
                if not _is_lock_contention(exc) or time.monotonic() >= deadline:
                    raise StateStoreMigrationError(
                        "The file-backed state database could not enable WAL mode."
                    ) from exc
                time.sleep(delay)
                delay = min(delay * 2, _WAL_RETRY_MAX_DELAY_S)
                continue
            # SQLite reports the mode actually in effect; verify it, do not
            # assume the assignment succeeded.
            if journal_mode is None or str(journal_mode[0]).lower() != "wal":
                raise StateStoreMigrationError(
                    "The file-backed state database could not enable WAL mode."
                )
            return

    @contextmanager
    def _operation_connection(self) -> Iterator[sqlite3.Connection]:
        """Yield one fresh connection and close it after the public operation."""
        # Opening and closing share one lifecycle lock. Close may proceed after
        # this connection exists because the operation owns it independently.
        with self._lifecycle_lock:
            if self._closed:
                raise RuntimeError("StateStore is closed.")
            connection = self._open_connection()
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def _write_connection(self) -> Iterator[sqlite3.Connection]:
        """Yield a connection inside an explicit write transaction."""
        with self._operation_connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
            except BaseException:
                connection.rollback()
                raise
            else:
                connection.commit()

    def _read_schema_versions(self, connection: sqlite3.Connection) -> list[int]:
        """Read and validate the applied forward-only schema ledger."""
        try:
            exists = connection.execute(
                """
                SELECT 1
                FROM sqlite_master
                WHERE type = 'table' AND name = 'schema_migrations'
                """
            ).fetchone()
            if not exists:
                return []
            rows = connection.execute(
                "SELECT version FROM schema_migrations ORDER BY version"
            ).fetchall()
        except sqlite3.DatabaseError as exc:
            raise StateStoreMigrationError(
                "The schema migration ledger is unreadable or malformed."
            ) from exc

        versions = [row[0] for row in rows]
        if any(type(version) is not int or version < 1 for version in versions):
            raise StateStoreMigrationError(
                "The schema migration ledger contains an invalid version."
            )

        latest_supported = _MIGRATIONS[-1][0] if _MIGRATIONS else 0
        if versions and versions[-1] > latest_supported:
            raise StateStoreMigrationError(
                "The database schema is newer than this application supports."
            )

        expected = list(range(1, versions[-1] + 1)) if versions else []
        if versions != expected:
            raise StateStoreMigrationError(
                "The schema migration ledger is gapped or duplicated."
            )
        return versions

    def _create_backup(self) -> Path:
        """
        Create a consistent timestamped backup from a separate read connection.

        Returns:
            The path to the completed backup.

        Side Effects:
            Creates a sibling database file. The backup can contain a cached
            token and its contents must never be logged.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup_path = Path(
            f"{self.db_path}.backup-{timestamp}-{uuid.uuid4().hex[:8]}.sqlite3"
        )
        partial_path = backup_path.with_suffix(f"{backup_path.suffix}.partial")
        source_uri = f"{Path(self.db_path).resolve().as_uri()}?mode=ro"
        source: sqlite3.Connection | None = None
        destination: sqlite3.Connection | None = None
        try:
            try:
                # The migration connection already holds BEGIN IMMEDIATE. A
                # second read-only source can snapshot without asking the
                # write-lock holder to back itself up.
                source = sqlite3.connect(
                    source_uri,
                    uri=True,
                    timeout=_BUSY_TIMEOUT_MS / 1000,
                )
                destination = sqlite3.connect(str(partial_path))
                source.backup(destination)
                destination.commit()
            finally:
                try:
                    if destination is not None:
                        destination.close()
                finally:
                    if source is not None:
                        source.close()

            # The final filename appears only after a complete SQLite snapshot.
            os.replace(partial_path, backup_path)
        except BaseException:
            partial_path.unlink(missing_ok=True)
            raise
        return backup_path

    def _initialize_schema(self) -> None:
        """
        Create the items + token_cache tables if they do not already exist.

        The version ledger serializes initialization, backs up legacy state,
        and applies each pending migration atomically.

        Returns:
            None

        Side Effects:
            Executes DDL and commits.
        """
        _validate_migration_plan()
        with _path_lock(self._lock_key):
            # Cycle 3 sampled the file size here, before any lock, so a legacy
            # database that appeared between this point and BEGIN IMMEDIATE was
            # migrated without a backup (cycle-3 AC3 failure). Cycle 4 makes
            # every decision from schema state observed after the lock.
            connection = self._open_connection(enable_wal=not self._is_memory)
            try:
                # BEGIN IMMEDIATE supplies SQLite-level serialization for other
                # processes after the process-local lock handles local threads.
                # The lock is acquired before backup selection so only the
                # process that observes pending work retains a snapshot.
                connection.execute("BEGIN IMMEDIATE")
                versions = self._read_schema_versions(connection)
                current_version = versions[-1] if versions else 0
                pending = [m for m in _MIGRATIONS if m[0] > current_version]

                # Backup eligibility: any user schema object observed under the
                # write lock means existing state that a migration could alter.
                has_existing_schema = (
                    not self._is_memory and bool(_user_schema_objects(connection))
                )
                if pending and has_existing_schema:
                    self._create_backup()

                # Validate the current layout against its own manifest before
                # touching it: legacy (version 0) when tables exist without a
                # ledger, otherwise the stamped version. An empty database
                # (no objects, no ledger) has nothing to validate yet.
                if current_version == 0 and has_existing_schema:
                    _validate_exact_schema(connection, 0)
                elif current_version >= 1:
                    _validate_exact_schema(connection, current_version)

                if not pending:
                    connection.commit()
                    return

                for version, statements in pending:
                    for statement in statements:
                        connection.execute(statement)
                    # Never stamp a version whose complete target manifest is
                    # not satisfied, including objects this version introduces.
                    _validate_exact_schema(connection, version)
                    connection.execute(
                        "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                        (version, _utc_now_iso()),
                    )
                connection.commit()
            except StateStoreMigrationError:
                if connection.in_transaction:
                    connection.rollback()
                raise
            except sqlite3.DatabaseError as exc:
                if connection.in_transaction:
                    connection.rollback()
                raise StateStoreMigrationError(
                    "The state database migration failed and was rolled back."
                ) from exc
            except BaseException:
                if connection.in_transaction:
                    connection.rollback()
                raise
            finally:
                connection.close()

    # ── items ────────────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> ItemRecord:
        """
        Convert a sqlite Row into an ItemRecord (parsing eps_urls JSON).

        Args:
            row: A sqlite3.Row from the items table.

        Returns:
            The corresponding ItemRecord.
        """
        return ItemRecord(
            item_sku=row["item_sku"],
            batch_folder_id=row["batch_folder_id"],
            status=ItemStatus(row["status"]),
            offer_id=row["offer_id"],
            listing_id=row["listing_id"],
            eps_urls=json.loads(row["eps_urls"]) if row["eps_urls"] else [],
            updated_at=row["updated_at"],
        )

    def upsert_item(self, record: ItemRecord) -> None:
        """
        Insert or update an item row, keyed on item_sku.

        Args:
            record: The ItemRecord to persist. updated_at is stamped here if the
                record does not already carry one.

        Returns:
            None

        Side Effects:
            Writes one row to the items table; commits.

        FMEA Constraints:
            R-STATE — written immediately after each pipeline/eBay step so a
            crash-and-resume sees committed offer_id/listing_id.
        """
        updated_at = record.updated_at or _utc_now_iso()
        with self._write_connection() as connection:
            connection.execute(
                """
                INSERT INTO items
                    (item_sku, batch_folder_id, status, offer_id, listing_id,
                     eps_urls, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(item_sku) DO UPDATE SET
                    batch_folder_id = excluded.batch_folder_id,
                    status          = excluded.status,
                    offer_id        = excluded.offer_id,
                    listing_id      = excluded.listing_id,
                    eps_urls        = excluded.eps_urls,
                    updated_at      = excluded.updated_at
                """,
                (
                    record.item_sku,
                    record.batch_folder_id,
                    record.status.value,
                    record.offer_id,
                    record.listing_id,
                    json.dumps(record.eps_urls),
                    updated_at,
                ),
            )

    def get_item(self, item_sku: str) -> ItemRecord | None:
        """
        Fetch one item by SKU.

        Args:
            item_sku: The deterministic SKU / idempotency key.

        Returns:
            The ItemRecord, or None if the SKU is unknown.
        """
        with self._operation_connection() as connection:
            row = connection.execute(
                "SELECT * FROM items WHERE item_sku = ?", (item_sku,)
            ).fetchone()
            return self._row_to_record(row) if row else None

    def is_published(self, item_sku: str) -> bool:
        """
        Return True if the SKU is already PUBLISHED (dedup guard).

        Args:
            item_sku: The deterministic SKU / idempotency key.

        Returns:
            True if a row exists with status == PUBLISHED.

        FMEA Constraints:
            R-STATE — the orchestrator calls this before any eBay publish to
            skip already-live items.
        """
        with self._operation_connection() as connection:
            row = connection.execute(
                "SELECT 1 FROM items WHERE item_sku = ? AND status = ?",
                (item_sku, ItemStatus.PUBLISHED.value),
            ).fetchone()
            return row is not None

    def set_status(self, item_sku: str, status: ItemStatus) -> None:
        """
        Update only the status (and updated_at) of an existing item.

        Args:
            item_sku: The SKU to update.
            status: The new ItemStatus.

        Returns:
            None

        Side Effects:
            Writes status + updated_at for the row; commits. No-op if the SKU is
            unknown (the orchestrator upserts before setting status).
        """
        with self._write_connection() as connection:
            connection.execute(
                "UPDATE items SET status = ?, updated_at = ? WHERE item_sku = ?",
                (status.value, _utc_now_iso(), item_sku),
            )

    def list_items(self) -> list[ItemRecord]:
        """
        Return all item records, newest update first.

        Returns:
            A list of ItemRecord ordered by updated_at descending. Useful for the
            UI to render the current pipeline state.
        """
        with self._operation_connection() as connection:
            rows = connection.execute(
                "SELECT * FROM items ORDER BY updated_at DESC"
            ).fetchall()
            return [self._row_to_record(row) for row in rows]

    # ── token cache ──────────────────────────────────────────────────────────

    def get_cached_token(self) -> TokenCacheRecord | None:
        """
        Return the cached eBay access token, or None if none is stored.

        Returns:
            The TokenCacheRecord, or None. Expiry checking is the caller's
            responsibility (ebay_auth compares expires_at_epoch to now).

        FMEA Constraints:
            R-AUTH / R-COST — lets ebay_auth reuse a valid token.
        """
        with self._operation_connection() as connection:
            row = connection.execute(
                """
                SELECT access_token, expires_at_epoch, scopes
                FROM token_cache
                WHERE id = ?
                """,
                (_TOKEN_ROW_ID,),
            ).fetchone()
            if not row:
                return None
            return TokenCacheRecord(
                access_token=row["access_token"],
                expires_at_epoch=row["expires_at_epoch"],
                scopes=row["scopes"],
            )

    def save_cached_token(self, token: TokenCacheRecord) -> None:
        """
        Persist the eBay access token to the cache (single-row upsert).

        Args:
            token: The TokenCacheRecord to store.

        Returns:
            None

        Side Effects:
            Overwrites the single cached token row; commits.
        """
        with self._write_connection() as connection:
            connection.execute(
                """
                INSERT INTO token_cache (id, access_token, expires_at_epoch, scopes)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    access_token     = excluded.access_token,
                    expires_at_epoch = excluded.expires_at_epoch,
                    scopes           = excluded.scopes
                """,
                (
                    _TOKEN_ROW_ID,
                    token.access_token,
                    token.expires_at_epoch,
                    token.scopes,
                ),
            )

    def close(self) -> None:
        """
        Close the underlying SQLite connection.

        Repeated calls are safe no-ops.
        """
        with self._lifecycle_lock:
            if self._closed:
                return
            if self._keeper is not None:
                self._keeper.close()
                self._keeper = None
            # Closed is published only after the keeper has been released.
            self._closed = True

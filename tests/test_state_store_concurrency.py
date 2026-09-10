"""
Module: test_state_store_concurrency.py
Purpose: Prove StateStore connection isolation and initialization serialization.
Primary Responsibilities:
  - Exercise concurrent readers and writers through one StateStore instance.
  - Prove same-SKU upserts remain one durable row.
  - Prove concurrent constructors apply one complete schema ledger.
Key Interfaces:
  - Input: Temporary SQLite paths and deterministic fake item records.
  - Output: Assertions over rows, migration versions, backups, and WAL state.
FMEA Constraints Enforced:
  - PI-010 / R-STATE - durable state remains usable under local concurrency;
    publication claims and PUBLISHING state remain T-005 scope.
"""

from __future__ import annotations

import multiprocessing
import queue
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src.contracts import ItemRecord, ItemStatus
from src.core.state_store import StateStore


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
    """Create an exact unversioned database containing deterministic fake rows."""
    connection = sqlite3.connect(path)
    try:
        for statement in _LEGACY_TABLE_STATEMENTS:
            connection.execute(statement)
        connection.execute(
            """
            INSERT INTO items
                (item_sku, batch_folder_id, status, offer_id, listing_id,
                 eps_urls, updated_at)
            VALUES ('LB-process', 'fake-folder', 'published', NULL, NULL, '[]', 'fake')
            """
        )
        connection.execute(
            """
            INSERT INTO token_cache (id, access_token, expires_at_epoch, scopes)
            VALUES (1, 'fake-process-token', 1.0, 'fake-scope')
            """
        )
        connection.commit()
    finally:
        connection.close()


def _spawn_initialize_legacy(database_path, start_event, result_queue) -> None:
    """Initialize one legacy path in a Windows-spawn-compatible child process."""
    try:
        if not start_event.wait(10):
            raise TimeoutError("spawn start event was not released")
        store = StateStore(database_path)
        try:
            item = store.get_item("LB-process")
            token = store.get_cached_token()
            result_queue.put(
                (
                    "ok",
                    item is not None and item.status is ItemStatus.PUBLISHED,
                    token is not None and token.access_token == "fake-process-token",
                )
            )
        finally:
            store.close()
    except BaseException as exc:
        result_queue.put(("error", type(exc).__name__, str(exc)))
        raise


def test_concurrent_readers_and_writers_complete_without_lock_errors(tmp_path):
    """Mixed operation-owned connections finish and preserve every unique SKU."""
    database_path = tmp_path / "mixed.db"
    store = StateStore(str(database_path))
    store.upsert_item(
        ItemRecord(item_sku="LB-seed", batch_folder_id="seed", status=ItemStatus.NEW)
    )
    start = threading.Barrier(12)

    def write_and_read(index: int) -> str:
        """Synchronize workers, write a unique row, and read shared state."""
        start.wait()
        sku = f"LB-{index:03d}"
        store.upsert_item(
            ItemRecord(
                item_sku=sku,
                batch_folder_id=f"folder-{index:03d}",
                status=ItemStatus.PRICED,
            )
        )
        assert store.get_item(sku) is not None
        assert store.get_item("LB-seed") is not None
        return sku

    try:
        with ThreadPoolExecutor(max_workers=12) as executor:
            written = list(executor.map(write_and_read, range(12)))
        assert len(set(written)) == 12
        assert len(store.list_items()) == 13
    finally:
        store.close()


def test_concurrent_same_sku_upserts_remain_one_row(tmp_path):
    """SQLite upsert serialization keeps concurrent same-SKU writes idempotent."""
    store = StateStore(str(tmp_path / "same-sku.db"))
    start = threading.Barrier(16)

    def upsert_same_sku(index: int) -> None:
        """Write one valid variant of the same deterministic SKU."""
        start.wait()
        store.upsert_item(
            ItemRecord(
                item_sku="LB-shared",
                batch_folder_id="shared-folder",
                status=ItemStatus.PRICED,
                offer_id=f"fake-offer-{index}",
            )
        )

    try:
        with ThreadPoolExecutor(max_workers=16) as executor:
            list(executor.map(upsert_same_sku, range(16)))
        rows = store.list_items()
        assert len(rows) == 1
        assert rows[0].item_sku == "LB-shared"
        assert rows[0].offer_id in {f"fake-offer-{index}" for index in range(16)}
    finally:
        store.close()


def test_memory_keeper_closes_from_a_different_thread_without_leak():
    """The keeper can be released outside its creator thread and stays closed."""
    store = StateStore(":memory:")
    store.upsert_item(ItemRecord(item_sku="LB-memory", batch_folder_id="memory"))

    with ThreadPoolExecutor(max_workers=1) as executor:
        executor.submit(store.close).result(timeout=5)

    assert store._keeper is None
    assert store._closed is True
    store.close()


def test_concurrent_memory_close_is_idempotent():
    """Concurrent close callers release the shared-memory keeper exactly once."""
    store = StateStore(":memory:")
    start = threading.Barrier(12)

    def close_store(_: int) -> None:
        """Synchronize callers and invoke the idempotent lifecycle operation."""
        start.wait()
        store.close()

    with ThreadPoolExecutor(max_workers=12) as executor:
        list(executor.map(close_store, range(12)))

    assert store._keeper is None
    assert store._closed is True
    store.close()


def test_concurrent_initialization_applies_one_complete_schema(tmp_path):
    """Path and SQLite locks serialize first-use migration across constructors."""
    database_path = tmp_path / "initialize.db"
    start = threading.Barrier(12)

    def initialize_store(_: int) -> None:
        """Construct, use, and idempotently close one store for the shared path."""
        start.wait()
        store = StateStore(str(database_path))
        try:
            assert store.get_item("not-present") is None
        finally:
            store.close()
            store.close()

    with ThreadPoolExecutor(max_workers=12) as executor:
        list(executor.map(initialize_store, range(12)))

    connection = sqlite3.connect(database_path)
    try:
        assert connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall() == [(1,)]
        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert connection.execute("SELECT COUNT(*) FROM items").fetchone()[0] == 0
    finally:
        connection.close()
    assert list(tmp_path.glob("initialize.db.backup-*.sqlite3")) == []


def test_spawned_processes_serialize_one_legacy_migration_and_backup(tmp_path):
    """Windows-spawn workers preserve rows and retain exactly one full snapshot."""
    database_path = tmp_path / "spawn-legacy.db"
    _create_legacy_database(database_path)
    context = multiprocessing.get_context("spawn")
    start_event = context.Event()
    result_queue = context.Queue()
    processes = [
        context.Process(
            target=_spawn_initialize_legacy,
            args=(str(database_path), start_event, result_queue),
        )
        for _ in range(4)
    ]

    started_at = time.monotonic()
    for process in processes:
        process.start()
    start_event.set()

    deadline = started_at + 30
    for process in processes:
        process.join(timeout=max(0.0, deadline - time.monotonic()))
    alive = [process for process in processes if process.is_alive()]
    for process in alive:
        process.terminate()
        process.join(timeout=5)

    try:
        results = [result_queue.get(timeout=3) for _ in processes]
    except queue.Empty:
        results = [("missing", False, False)]
    finally:
        result_queue.close()
        result_queue.join_thread()

    assert alive == []
    assert time.monotonic() - started_at < 30
    assert [process.exitcode for process in processes] == [0, 0, 0, 0]
    assert results == [("ok", True, True)] * 4

    live = sqlite3.connect(database_path)
    try:
        assert live.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall() == [(1,)]
        assert live.execute("SELECT COUNT(*) FROM items").fetchone()[0] == 1
        assert live.execute("SELECT COUNT(*) FROM token_cache").fetchone()[0] == 1
    finally:
        live.close()

    backups = list(tmp_path.glob("spawn-legacy.db.backup-*.sqlite3"))
    assert len(backups) == 1
    backup = sqlite3.connect(backups[0])
    try:
        assert backup.execute("SELECT COUNT(*) FROM items").fetchone()[0] == 1
        assert backup.execute("SELECT COUNT(*) FROM token_cache").fetchone()[0] == 1
        assert backup.execute(
            """
            SELECT COUNT(*) FROM sqlite_master
            WHERE type = 'table' AND name = 'schema_migrations'
            """
        ).fetchone()[0] == 0
    finally:
        backup.close()
    assert list(tmp_path.glob("*.partial")) == []

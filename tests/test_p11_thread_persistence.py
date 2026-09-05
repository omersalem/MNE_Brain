"""Unit tests for ThreadStore local conversation persistence."""

import json
from pathlib import Path
import pytest

from core.conversation.thread_store import ThreadStore, ThreadStoreError

BASE = Path(__file__).resolve().parent.parent


def test_thread_store_default_is_in_memory_only(tmp_path: Path):
    """Verify ThreadStore with no storage_dir operates strictly in memory."""
    store = ThreadStore(BASE)
    thread = store.create_thread(title="In Memory Thread", engine_id="codex", model_id="codex-account-default")
    assert store.storage_dir is None
    assert len(store.list_threads()) == 1

    # Another instance has empty state
    store2 = ThreadStore(BASE)
    assert len(store2.list_threads()) == 0


def test_thread_store_local_disk_persistence(tmp_path: Path):
    """Verify threads, turns, and messages persist to local disk and reload accurately."""
    storage_dir = tmp_path / "conversations"
    store = ThreadStore(BASE, storage_dir=storage_dir)

    thread = store.create_thread(
        title="Persisted Troubleshooting Session",
        engine_id="antigravity",
        model_id="gemini-3.8-flash-high",
        permission_mode="OWNER_DIRECT",
    )
    thread_id = thread["thread_id"]

    # Verify JSON file was created on disk
    thread_file = storage_dir / f"{thread_id}.json"
    assert thread_file.exists()
    disk_data = json.loads(thread_file.read_text(encoding="utf-8"))
    assert disk_data["version"] == "MNE_BRAIN_LOCAL_THREAD_V1"
    assert disk_data["thread"]["title"] == "Persisted Troubleshooting Session"
    assert disk_data["thread"]["engine_id"] == "antigravity"

    # Add turn and message
    turn = store.create_turn(thread_id)
    msg1 = store.add_message(turn["turn_id"], role="user", content="Check fortigate vpn")
    msg2 = store.add_message(turn["turn_id"], role="assistant", content="VPN is healthy")
    store.update_turn(turn["turn_id"], status="COMPLETED")

    # Re-verify disk file after turn completion
    disk_data = json.loads(thread_file.read_text(encoding="utf-8"))
    assert len(disk_data["turns"]) == 1
    assert disk_data["turns"][0]["status"] == "COMPLETED"
    assert len(disk_data["messages"]) == 2
    assert disk_data["messages"][0]["content"] == "Check fortigate vpn"
    assert disk_data["messages"][1]["content"] == "VPN is healthy"

    # Instantiate a NEW store pointing to the same storage_dir (simulating server reboot)
    reloaded_store = ThreadStore(BASE, storage_dir=storage_dir)
    threads = reloaded_store.list_threads()
    assert len(threads) == 1
    assert threads[0]["thread_id"] == thread_id
    assert threads[0]["title"] == "Persisted Troubleshooting Session"
    assert threads[0]["engine_id"] == "antigravity"

    reloaded_thread = reloaded_store.get_thread(thread_id)
    assert len(reloaded_thread["turns"]) == 1
    assert reloaded_thread["turns"][0]["status"] == "COMPLETED"
    assert len(reloaded_thread["messages"]) == 2
    assert [m["content"] for m in reloaded_thread["messages"]] == ["Check fortigate vpn", "VPN is healthy"]


def test_thread_store_reconciles_in_flight_turns_on_reload(tmp_path: Path):
    """Verify turns left in QUEUED or RUNNING when server stopped are marked CANCELLED on reload."""
    storage_dir = tmp_path / "conversations"
    store = ThreadStore(BASE, storage_dir=storage_dir)

    thread = store.create_thread(title="Interrupted Session", engine_id="codex")
    turn = store.create_turn(thread["thread_id"])
    store.add_message(turn["turn_id"], role="user", content="Long running check")
    assert turn["status"] == "QUEUED"

    # Reload
    reloaded_store = ThreadStore(BASE, storage_dir=storage_dir)
    reloaded_thread = reloaded_store.get_thread(thread["thread_id"])
    assert reloaded_thread["turns"][0]["status"] == "CANCELLED"


def test_thread_store_delete_removes_from_memory_and_disk(tmp_path: Path):
    """Verify delete_thread removes thread from memory and deletes the JSON file from disk."""
    storage_dir = tmp_path / "conversations"
    store = ThreadStore(BASE, storage_dir=storage_dir)

    thread = store.create_thread(title="To Delete", engine_id="codex")
    thread_id = thread["thread_id"]
    thread_file = storage_dir / f"{thread_id}.json"
    assert thread_file.exists()

    # Delete
    result = store.delete_thread(thread_id)
    assert result is True
    assert len(store.list_threads()) == 0
    assert not thread_file.exists()

    # Attempting to delete again raises ThreadStoreError
    with pytest.raises(ThreadStoreError, match="Thread not found"):
        store.delete_thread(thread_id)

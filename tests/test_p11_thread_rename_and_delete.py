"""Unit and contract tests for thread rename and safe delete invariants."""

from __future__ import annotations

import http.client
import json
import threading
from pathlib import Path
import pytest

from core.api.security import OwnerCredentialVerifier, OwnerSessionManager
from core.api.server import BoundedThreadingHTTPServer, MNEBrainAPIHandler
from core.conversation.engine import ConversationEngine
from core.conversation.thread_store import ThreadStore, ThreadStoreError

BASE = Path(__file__).resolve().parent.parent


def test_thread_store_rename_valid_trimmed_and_persisted(tmp_path: Path):
    storage_dir = tmp_path / "conversations"
    store = ThreadStore(BASE, storage_dir=storage_dir)

    thread = store.create_thread(title="Initial Title", engine_id="codex")
    thread_id = thread["thread_id"]
    initial_updated_at = thread["updated_at"]

    # Valid rename with leading/trailing whitespace
    updated = store.rename_thread(thread_id, "   Updated Incident Investigation   ")
    assert updated["title"] == "Updated Incident Investigation"
    assert updated["thread_id"] == thread_id
    assert updated["updated_at"] >= initial_updated_at

    # Check that disk persistence updated atomically
    disk_file = storage_dir / f"{thread_id}.json"
    assert disk_file.exists()
    disk_data = json.loads(disk_file.read_text(encoding="utf-8"))
    assert disk_data["thread"]["title"] == "Updated Incident Investigation"
    assert disk_data["thread"]["updated_at"] == updated["updated_at"]

    # Reload store from disk
    reloaded_store = ThreadStore(BASE, storage_dir=storage_dir)
    reloaded_thread = reloaded_store.get_thread(thread_id, include_items=False)
    assert reloaded_thread["title"] == "Updated Incident Investigation"


def test_thread_store_rename_rejects_blank_and_empty():
    store = ThreadStore(BASE)
    thread = store.create_thread(title="Valid Title", engine_id="codex")
    thread_id = thread["thread_id"]

    with pytest.raises(ThreadStoreError, match="between 1 and 160 characters"):
        store.rename_thread(thread_id, "")

    with pytest.raises(ThreadStoreError, match="between 1 and 160 characters"):
        store.rename_thread(thread_id, "    ")

    with pytest.raises(ThreadStoreError, match="must be a string"):
        store.rename_thread(thread_id, None)  # type: ignore


def test_thread_store_rename_boundary_lengths():
    store = ThreadStore(BASE)
    thread = store.create_thread(title="Original", engine_id="codex")
    thread_id = thread["thread_id"]

    # 1 character is allowed
    one_char = store.rename_thread(thread_id, "A")
    assert one_char["title"] == "A"

    # 160 characters is allowed
    title_160 = "T" * 160
    updated_160 = store.rename_thread(thread_id, title_160)
    assert updated_160["title"] == title_160

    # 161 characters is rejected
    with pytest.raises(ThreadStoreError, match="between 1 and 160 characters"):
        store.rename_thread(thread_id, "T" * 161)


def test_thread_store_rename_rejects_control_characters():
    store = ThreadStore(BASE)
    thread = store.create_thread(title="Original", engine_id="codex")
    thread_id = thread["thread_id"]

    for bad_char in ["\n", "\r", "\t", "\x00", "\x1b", "\x7f", "\x85"]:
        with pytest.raises(ThreadStoreError, match="control characters"):
            store.rename_thread(thread_id, f"Valid Prefix{bad_char}Suffix")


def test_thread_store_rename_nonexistent_thread():
    store = ThreadStore(BASE)
    with pytest.raises(ThreadStoreError, match="Thread not found"):
        store.rename_thread("thr_nonexistent12345678", "New Title")


def test_thread_store_delete_blocked_when_turn_queued_or_running(tmp_path: Path):
    storage_dir = tmp_path / "conversations"
    store = ThreadStore(BASE, storage_dir=storage_dir)

    thread = store.create_thread(title="Active Investigation", engine_id="codex")
    thread_id = thread["thread_id"]
    turn = store.create_turn(thread_id)
    assert turn["status"] == "QUEUED"

    # Blocked while QUEUED
    with pytest.raises(ThreadStoreError, match="Cannot delete thread while a turn is queued or running"):
        store.delete_thread(thread_id)

    # Thread and disk file still exist
    assert store.get_thread(thread_id, include_items=False)["thread_id"] == thread_id
    assert (storage_dir / f"{thread_id}.json").exists()

    # Update to RUNNING -> still blocked
    store.update_turn(turn["turn_id"], status="RUNNING")
    with pytest.raises(ThreadStoreError, match="Cannot delete thread while a turn is queued or running"):
        store.delete_thread(thread_id)

    # Cancel the turn -> deletion succeeds
    store.update_turn(turn["turn_id"], status="CANCELLED")
    assert store.delete_thread(thread_id) is True
    assert len(store.list_threads()) == 0
    assert not (storage_dir / f"{thread_id}.json").exists()


def test_conversation_engine_rename_delegation():
    engine = ConversationEngine(BASE)
    thread = engine.create_thread(title="Engine Thread")
    updated = engine.rename_thread(thread["thread_id"], "New Engine Title")
    assert updated["title"] == "New Engine Title"
    assert engine.store.get_thread(thread["thread_id"])["title"] == "New Engine Title"


@pytest.fixture
def local_api_server(monkeypatch):
    from core.api import server as api_server
    test_engine = ConversationEngine(BASE, storage_dir=None)
    monkeypatch.setattr(api_server, "conversation_engine", test_engine)
    password_hash = OwnerCredentialVerifier.hash_password("correct horse battery staple", iterations=300_000, salt=b"p11-owner-test-salt-00001")
    verifier = OwnerCredentialVerifier(username="owner", password_hash=password_hash)
    monkeypatch.setattr(api_server, "owner_credentials", verifier)
    monkeypatch.setattr(api_server, "owner_sessions", OwnerSessionManager(credential_verifier=verifier, max_sessions=1))
    server = BoundedThreadingHTTPServer(("127.0.0.1", 0), MNEBrainAPIHandler, max_workers=8)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield server.server_port
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def _request_http(port, method, path, body=None, headers=None):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    raw = json.dumps(body).encode() if body is not None else None
    merged = {"Host": f"127.0.0.1:{port}", **(headers or {})}
    if raw is not None:
        merged["Content-Type"] = "application/json"
    connection.request(method, path, body=raw, headers=merged)
    response = connection.getresponse()
    data = response.read()
    response_headers = dict(response.getheaders())
    connection.close()
    return response.status, response_headers, json.loads(data) if data else {}


def _login_http(port):
    status, headers, session = _request_http(
        port, "POST", "/api/v2/login",
        {"username": "owner", "password": "correct horse battery staple"},
        {"Origin": f"http://127.0.0.1:{port}"},
    )
    assert status == 200 and "HttpOnly" in headers["Set-Cookie"]
    return headers["Set-Cookie"].split(";", 1)[0], session


def test_http_rename_endpoint_contract(local_api_server):
    port = local_api_server
    cookie, session = _login_http(port)
    auth = {"Cookie": cookie, "Origin": f"http://127.0.0.1:{port}", "X-CSRF-Token": session["csrf_token"]}

    # Create thread
    body = {"title": "HTTP Title Test", "request_nonce": "n" * 32}
    status, _, thread = _request_http(port, "POST", "/api/v2/threads", body, auth)
    assert status == 201
    thread_id = thread["thread_id"]

    # Rename thread successfully
    rename_body = {"title": "Renamed Via HTTP", "request_nonce": "r" * 32}
    status, _, updated = _request_http(port, "POST", f"/api/v2/threads/{thread_id}/title", rename_body, auth)
    assert status == 200
    assert updated["title"] == "Renamed Via HTTP"
    assert updated["thread_id"] == thread_id

    # Reject unexpected payload fields
    invalid_fields_body = {"title": "Bad Extra Field", "unexpected": "value", "request_nonce": "x" * 32}
    status, _, err = _request_http(port, "POST", f"/api/v2/threads/{thread_id}/title", invalid_fields_body, auth)
    assert status in {400, 409}
    assert "Only the title field is allowed" in err.get("error", "")

    # Reject blank title
    blank_body = {"title": "   ", "request_nonce": "y" * 32}
    status, _, err = _request_http(port, "POST", f"/api/v2/threads/{thread_id}/title", blank_body, auth)
    assert status in {400, 409}

    # Reject without authentication
    unauth_status, _, _ = _request_http(port, "POST", f"/api/v2/threads/{thread_id}/title", {"title": "No Auth", "request_nonce": "z" * 32})
    assert unauth_status == 403


def test_thread_store_batch_delete_all_inactive(tmp_path: Path):
    storage_dir = tmp_path / "conversations"
    store = ThreadStore(BASE, storage_dir=storage_dir)

    t1 = store.create_thread(title="T1", engine_id="codex")
    t2 = store.create_thread(title="T2", engine_id="codex")
    t3 = store.create_thread(title="T3", engine_id="codex")

    res = store.delete_threads([t1["thread_id"], t2["thread_id"], t3["thread_id"]])
    assert set(res["deleted"]) == {t1["thread_id"], t2["thread_id"], t3["thread_id"]}
    assert res["blocked"] == []
    assert len(store.list_threads()) == 0
    assert not (storage_dir / f"{t1['thread_id']}.json").exists()
    assert not (storage_dir / f"{t2['thread_id']}.json").exists()
    assert not (storage_dir / f"{t3['thread_id']}.json").exists()


def test_thread_store_batch_delete_skips_running_and_deletes_inactive(tmp_path: Path):
    storage_dir = tmp_path / "conversations"
    store = ThreadStore(BASE, storage_dir=storage_dir)

    t1 = store.create_thread(title="T1 Active", engine_id="codex")
    t2 = store.create_thread(title="T2 Inactive", engine_id="codex")
    turn = store.create_turn(t1["thread_id"])
    assert turn["status"] == "QUEUED"

    res = store.delete_threads([t1["thread_id"], t2["thread_id"]])
    assert res["deleted"] == [t2["thread_id"]]
    assert len(res["blocked"]) == 1
    assert res["blocked"][0]["thread_id"] == t1["thread_id"]
    assert res["blocked"][0]["reason"] == "ACTIVE_TURN_RUNNING"

    assert (storage_dir / f"{t1['thread_id']}.json").exists()
    assert not (storage_dir / f"{t2['thread_id']}.json").exists()


def test_http_batch_delete_endpoint_contract(local_api_server):
    port = local_api_server
    cookie, session = _login_http(port)
    auth = {"Cookie": cookie, "Origin": f"http://127.0.0.1:{port}", "X-CSRF-Token": session["csrf_token"]}

    # Create 3 threads
    body1 = {"title": "Batch Thread 1", "request_nonce": "a" * 32}
    status, _, t1 = _request_http(port, "POST", "/api/v2/threads", body1, auth)
    assert status == 201

    body2 = {"title": "Batch Thread 2", "request_nonce": "b" * 32}
    status, _, t2 = _request_http(port, "POST", "/api/v2/threads", body2, auth)
    assert status == 201

    body3 = {"title": "Batch Thread 3", "request_nonce": "c" * 32}
    status, _, t3 = _request_http(port, "POST", "/api/v2/threads", body3, auth)
    assert status == 201

    # Batch delete t1 and t2
    batch_body = {"thread_ids": [t1["thread_id"], t2["thread_id"]], "request_nonce": "d" * 32}
    status, _, res = _request_http(port, "POST", "/api/v2/threads/batch-delete", batch_body, auth)
    assert status == 200
    assert set(res["deleted"]) == {t1["thread_id"], t2["thread_id"]}
    assert res["blocked"] == []

    # Verify only t3 remains
    status, _, remaining = _request_http(port, "GET", "/api/v2/threads", None, auth)
    assert status == 200
    remaining_ids = [t["thread_id"] for t in remaining["threads"]]
    assert remaining_ids == [t3["thread_id"]]


def test_thread_store_archive_and_unarchive_lifecycle(tmp_path: Path):
    storage_dir = tmp_path / "conversations"
    store = ThreadStore(BASE, storage_dir=storage_dir)

    t = store.create_thread(title="Archive Test", engine_id="codex")
    thread_id = t["thread_id"]
    assert t["status"] == "ACTIVE"

    archived = store.archive_thread(thread_id)
    assert archived["status"] == "ARCHIVED"
    assert archived["updated_at"] >= t["updated_at"]

    # Verify on disk
    disk_file = storage_dir / f"{thread_id}.json"
    assert disk_file.exists()
    disk_data = json.loads(disk_file.read_text(encoding="utf-8"))
    assert disk_data["thread"]["status"] == "ARCHIVED"

    # Reload store from disk
    reloaded = ThreadStore(BASE, storage_dir=storage_dir)
    assert reloaded.get_thread(thread_id, include_items=False)["status"] == "ARCHIVED"

    # Unarchive
    unarchived = reloaded.unarchive_thread(thread_id)
    assert unarchived["status"] == "ACTIVE"
    disk_data2 = json.loads(disk_file.read_text(encoding="utf-8"))
    assert disk_data2["thread"]["status"] == "ACTIVE"


def test_thread_store_archive_blocked_when_turn_active(tmp_path: Path):
    storage_dir = tmp_path / "conversations"
    store = ThreadStore(BASE, storage_dir=storage_dir)

    t = store.create_thread(title="Active Turn Archive Blocked", engine_id="codex")
    thread_id = t["thread_id"]
    turn = store.create_turn(thread_id)
    assert turn["status"] == "QUEUED"

    with pytest.raises(ThreadStoreError, match="Cannot archive thread while a turn is queued or running"):
        store.archive_thread(thread_id)

    store.update_turn(turn["turn_id"], status="RUNNING")
    with pytest.raises(ThreadStoreError, match="Cannot archive thread while a turn is queued or running"):
        store.archive_thread(thread_id)

    # Completed turn allows archive
    store.update_turn(turn["turn_id"], status="COMPLETED")
    archived = store.archive_thread(thread_id)
    assert archived["status"] == "ARCHIVED"


def test_thread_store_delete_disk_failure_preserves_memory_record(tmp_path: Path, monkeypatch):
    storage_dir = tmp_path / "conversations"
    store = ThreadStore(BASE, storage_dir=storage_dir)

    t = store.create_thread(title="Disk Fail Delete", engine_id="codex")
    thread_id = t["thread_id"]
    disk_file = storage_dir / f"{thread_id}.json"
    assert disk_file.exists()

    # Monkeypatch unlink to fail with OSError
    original_unlink = Path.unlink
    def failing_unlink(self, *args, **kwargs):
        if self.name == f"{thread_id}.json":
            raise OSError("Simulated disk unlink failure")
        return original_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", failing_unlink)

    with pytest.raises(ThreadStoreError, match="Failed to delete thread persistence file"):
        store.delete_thread(thread_id)

    # In-memory record MUST still be intact (no false success or resurrection)
    assert store.get_thread(thread_id, include_items=False)["thread_id"] == thread_id
    assert len(store.list_threads()) == 1


def test_thread_store_batch_delete_disk_failure_reports_blocked(tmp_path: Path, monkeypatch):
    storage_dir = tmp_path / "conversations"
    store = ThreadStore(BASE, storage_dir=storage_dir)

    t1 = store.create_thread(title="Batch Disk Fail", engine_id="codex")
    t2 = store.create_thread(title="Batch Disk OK", engine_id="codex")

    original_unlink = Path.unlink
    def failing_unlink(self, *args, **kwargs):
        if self.name == f"{t1['thread_id']}.json":
            raise OSError("Simulated unlink error")
        return original_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", failing_unlink)

    res = store.delete_threads([t1["thread_id"], t2["thread_id"]])
    assert res["deleted"] == [t2["thread_id"]]
    assert len(res["blocked"]) == 1
    assert res["blocked"][0]["thread_id"] == t1["thread_id"]
    assert "PERSISTENCE_DELETE_FAILED" in res["blocked"][0]["reason"]

    # t1 must remain in memory
    remaining_ids = [t["thread_id"] for t in store.list_threads()]
    assert t1["thread_id"] in remaining_ids
    assert t2["thread_id"] not in remaining_ids


def test_http_batch_delete_rejects_unknown_payload_fields(local_api_server):
    port = local_api_server
    cookie, session = _login_http(port)
    auth = {"Cookie": cookie, "Origin": f"http://127.0.0.1:{port}", "X-CSRF-Token": session["csrf_token"]}

    status, _, t = _request_http(port, "POST", "/api/v2/threads", {"title": "Reject Field Test", "request_nonce": "e" * 32}, auth)
    assert status == 201

    # Extra unexpected field in batch-delete payload
    bad_payload = {"thread_ids": [t["thread_id"]], "unexpected_field": True, "request_nonce": "f" * 32}
    status, _, err = _request_http(port, "POST", "/api/v2/threads/batch-delete", bad_payload, auth)
    assert status in {400, 409}
    assert "thread_ids" in err.get("error", "").lower() or "unexpected" in err.get("error", "").lower()


def test_http_archive_and_unarchive_endpoints(local_api_server):
    port = local_api_server
    cookie, session = _login_http(port)
    auth = {"Cookie": cookie, "Origin": f"http://127.0.0.1:{port}", "X-CSRF-Token": session["csrf_token"]}

    status, _, t = _request_http(port, "POST", "/api/v2/threads", {"title": "HTTP Archive Test", "request_nonce": "g" * 32}, auth)
    assert status == 201
    tid = t["thread_id"]

    # Archive
    status, _, archived = _request_http(port, "POST", f"/api/v2/threads/{tid}/archive", {"request_nonce": "h" * 32}, auth)
    assert status == 200
    assert archived["status"] == "ARCHIVED"

    # Reject unexpected fields in archive payload
    status, _, err = _request_http(port, "POST", f"/api/v2/threads/{tid}/archive", {"extra": "field", "request_nonce": "i" * 32}, auth)
    assert status in {400, 409}

    # Unarchive
    status, _, unarchived = _request_http(port, "POST", f"/api/v2/threads/{tid}/unarchive", {"request_nonce": "j" * 32}, auth)
    assert status == 200
    assert unarchived["status"] == "ACTIVE"


def test_thread_store_archive_temp_write_failure_preserves_state(tmp_path: Path, monkeypatch):
    storage_dir = tmp_path / "conversations"
    store = ThreadStore(BASE, storage_dir=storage_dir)

    t = store.create_thread(title="Archive Write Fail Test", engine_id="codex")
    thread_id = t["thread_id"]
    initial_updated_at = t["updated_at"]
    disk_file = storage_dir / f"{thread_id}.json"
    assert disk_file.exists()
    disk_before = json.loads(disk_file.read_text(encoding="utf-8"))
    assert disk_before["thread"]["status"] == "ACTIVE"

    original_write_text = Path.write_text

    def failing_write_text(self, *args, **kwargs):
        if self.name.endswith(".tmp"):
            raise OSError("Simulated temporary write failure")
        return original_write_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", failing_write_text)

    with pytest.raises(ThreadStoreError, match="Failed to persist"):
        store.archive_thread(thread_id)

    # In-memory record must be preserved
    current_in_memory = store.get_thread(thread_id, include_items=False)
    assert current_in_memory["status"] == "ACTIVE"
    assert current_in_memory["updated_at"] == initial_updated_at

    # Disk state must remain unchanged
    disk_after = json.loads(disk_file.read_text(encoding="utf-8"))
    assert disk_after["thread"]["status"] == "ACTIVE"
    assert disk_after["thread"]["updated_at"] == initial_updated_at


def test_thread_store_archive_replace_failure_preserves_state(tmp_path: Path, monkeypatch):
    storage_dir = tmp_path / "conversations"
    store = ThreadStore(BASE, storage_dir=storage_dir)

    t = store.create_thread(title="Archive Replace Fail Test", engine_id="codex")
    thread_id = t["thread_id"]
    initial_updated_at = t["updated_at"]
    disk_file = storage_dir / f"{thread_id}.json"
    assert disk_file.exists()
    disk_before = json.loads(disk_file.read_text(encoding="utf-8"))
    assert disk_before["thread"]["status"] == "ACTIVE"

    original_replace = Path.replace

    def failing_replace(self, *args, **kwargs):
        if self.name.endswith(".tmp"):
            raise OSError("Simulated atomic replace failure")
        return original_replace(self, *args, **kwargs)

    monkeypatch.setattr(Path, "replace", failing_replace)

    with pytest.raises(ThreadStoreError, match="Failed to persist"):
        store.archive_thread(thread_id)

    # In-memory record must be preserved
    current_in_memory = store.get_thread(thread_id, include_items=False)
    assert current_in_memory["status"] == "ACTIVE"
    assert current_in_memory["updated_at"] == initial_updated_at

    # Disk state must remain unchanged
    disk_after = json.loads(disk_file.read_text(encoding="utf-8"))
    assert disk_after["thread"]["status"] == "ACTIVE"
    assert disk_after["thread"]["updated_at"] == initial_updated_at


def test_thread_store_unarchive_temp_write_failure_preserves_state(tmp_path: Path, monkeypatch):
    storage_dir = tmp_path / "conversations"
    store = ThreadStore(BASE, storage_dir=storage_dir)

    t = store.create_thread(title="Unarchive Write Fail Test", engine_id="codex")
    thread_id = t["thread_id"]
    archived = store.archive_thread(thread_id)
    assert archived["status"] == "ARCHIVED"
    archived_updated_at = archived["updated_at"]

    disk_file = storage_dir / f"{thread_id}.json"
    assert disk_file.exists()
    disk_before = json.loads(disk_file.read_text(encoding="utf-8"))
    assert disk_before["thread"]["status"] == "ARCHIVED"

    original_write_text = Path.write_text

    def failing_write_text(self, *args, **kwargs):
        if self.name.endswith(".tmp"):
            raise OSError("Simulated temporary write failure during unarchive")
        return original_write_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", failing_write_text)

    with pytest.raises(ThreadStoreError, match="Failed to persist"):
        store.unarchive_thread(thread_id)

    # In-memory record must remain ARCHIVED
    current_in_memory = store.get_thread(thread_id, include_items=False)
    assert current_in_memory["status"] == "ARCHIVED"
    assert current_in_memory["updated_at"] == archived_updated_at

    # Disk state must remain ARCHIVED
    disk_after = json.loads(disk_file.read_text(encoding="utf-8"))
    assert disk_after["thread"]["status"] == "ARCHIVED"
    assert disk_after["thread"]["updated_at"] == archived_updated_at


def test_thread_store_unarchive_replace_failure_preserves_state(tmp_path: Path, monkeypatch):
    storage_dir = tmp_path / "conversations"
    store = ThreadStore(BASE, storage_dir=storage_dir)

    t = store.create_thread(title="Unarchive Replace Fail Test", engine_id="codex")
    thread_id = t["thread_id"]
    archived = store.archive_thread(thread_id)
    assert archived["status"] == "ARCHIVED"
    archived_updated_at = archived["updated_at"]

    disk_file = storage_dir / f"{thread_id}.json"
    assert disk_file.exists()
    disk_before = json.loads(disk_file.read_text(encoding="utf-8"))
    assert disk_before["thread"]["status"] == "ARCHIVED"

    original_replace = Path.replace

    def failing_replace(self, *args, **kwargs):
        if self.name.endswith(".tmp"):
            raise OSError("Simulated atomic replace failure during unarchive")
        return original_replace(self, *args, **kwargs)

    monkeypatch.setattr(Path, "replace", failing_replace)

    with pytest.raises(ThreadStoreError, match="Failed to persist"):
        store.unarchive_thread(thread_id)

    # In-memory record must remain ARCHIVED
    current_in_memory = store.get_thread(thread_id, include_items=False)
    assert current_in_memory["status"] == "ARCHIVED"
    assert current_in_memory["updated_at"] == archived_updated_at

    # Disk state must remain ARCHIVED
    disk_after = json.loads(disk_file.read_text(encoding="utf-8"))
    assert disk_after["thread"]["status"] == "ARCHIVED"
    assert disk_after["thread"]["updated_at"] == archived_updated_at


def test_thread_store_create_turn_rejects_archived_thread():
    store = ThreadStore(BASE)
    thread = store.create_thread(title="Archived Turn Test", engine_id="codex")
    thread_id = thread["thread_id"]
    store.archive_thread(thread_id)

    with pytest.raises(ThreadStoreError, match="Archived conversations are read-only. Unarchive this conversation before sending a message."):
        store.create_turn(thread_id)


def test_http_create_turn_on_archived_thread_returns_409(local_api_server):
    port = local_api_server
    cookie, session = _login_http(port)
    auth = {"Cookie": cookie, "Origin": f"http://127.0.0.1:{port}", "X-CSRF-Token": session["csrf_token"]}

    status, _, t = _request_http(port, "POST", "/api/v2/threads", {"title": "HTTP Turn Archive Test", "request_nonce": "k" * 32}, auth)
    assert status == 201
    tid = t["thread_id"]

    # Archive the thread
    status, _, _ = _request_http(port, "POST", f"/api/v2/threads/{tid}/archive", {"request_nonce": "l" * 32}, auth)
    assert status == 200

    # Attempt to create a turn
    turn_payload = {"content": "Hello on archived thread", "request_nonce": "m" * 32}
    status, _, err = _request_http(port, "POST", f"/api/v2/threads/{tid}/turns", turn_payload, auth)
    assert status == 409
    assert "Archived conversations are read-only" in err.get("error", "")

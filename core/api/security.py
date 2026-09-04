"""Loopback same-origin owner-session security for every P11 mutation."""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import secrets
import threading
import time
import urllib.parse
from dataclasses import dataclass, field
from http.cookies import SimpleCookie
from typing import Any


class OwnerSessionError(PermissionError):
    pass


class OwnerCredentialVerifier:
    """Verify one owner credential without retaining or returning the password."""

    ALGORITHM = "pbkdf2_sha256"
    DEFAULT_ITERATIONS = 600_000

    def __init__(self, *, username: str | None, password_hash: str | None):
        self.username = str(username or "")
        self.password_hash = str(password_hash or "")

    @property
    def configured(self) -> bool:
        try:
            algorithm, iterations, salt_hex, digest_hex = self.password_hash.split("$", 3)
            return (
                bool(self.username)
                and algorithm == self.ALGORITHM
                and int(iterations) >= 300_000
                and len(bytes.fromhex(salt_hex)) >= 16
                and len(bytes.fromhex(digest_hex)) == 32
            )
        except (TypeError, ValueError):
            return False

    @classmethod
    def hash_password(cls, password: str, *, iterations: int | None = None, salt: bytes | None = None) -> str:
        if not isinstance(password, str) or not 12 <= len(password) <= 512 or "\x00" in password:
            raise ValueError("Owner password must contain 12 through 512 characters.")
        rounds = max(int(iterations or cls.DEFAULT_ITERATIONS), 300_000)
        actual_salt = salt or secrets.token_bytes(24)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), actual_salt, rounds, dklen=32)
        return f"{cls.ALGORITHM}${rounds}${actual_salt.hex()}${digest.hex()}"

    def verify(self, username: str, password: str) -> bool:
        if not self.configured or not isinstance(username, str) or not isinstance(password, str):
            return False
        try:
            algorithm, iterations, salt_hex, expected_hex = self.password_hash.split("$", 3)
            candidate = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations), dklen=32
            ).hex()
        except (TypeError, ValueError, UnicodeError):
            return False
        return algorithm == self.ALGORITHM and hmac.compare_digest(username, self.username) and hmac.compare_digest(candidate, expected_hex)


@dataclass
class _Session:
    session_id: str
    csrf_token: str
    created_at: float
    last_seen: float
    nonces: dict[str, float] = field(default_factory=dict)


class OwnerSessionManager:
    def __init__(self, *, inactivity_seconds: int = 900, nonce_ttl_seconds: int = 300, max_sessions: int = 8, cookie_name: str = "mne_owner_session", credential_verifier: OwnerCredentialVerifier | None = None, maximum_failures: int = 5, lockout_seconds: int = 300, now: Any = None):
        self.inactivity_seconds = inactivity_seconds
        self.nonce_ttl_seconds = nonce_ttl_seconds
        self.max_sessions = max_sessions
        self.cookie_name = cookie_name
        self.credential_verifier = credential_verifier
        self.maximum_failures = max(3, min(int(maximum_failures), 20))
        self.lockout_seconds = max(30, min(int(lockout_seconds), 3600))
        self._now = now or time.time
        self._sessions: dict[str, _Session] = {}
        self._failures: dict[str, list[float]] = {}
        self._lock = threading.RLock()

    @staticmethod
    def is_loopback(host: str | None) -> bool:
        if not host:
            return False
        candidate = str(host).strip().strip("[]")
        try:
            return ipaddress.ip_address(candidate).is_loopback
        except ValueError:
            return candidate.lower() == "localhost"

    @classmethod
    def same_origin_loopback(cls, host_header: str | None, origin_header: str | None) -> bool:
        if not host_header:
            return False
        try:
            host = urllib.parse.urlsplit("//" + host_header).hostname
        except ValueError:
            return False
        if not cls.is_loopback(host):
            return False
        if not origin_header:
            return True
        try:
            origin = urllib.parse.urlsplit(origin_header)
        except ValueError:
            return False
        return origin.scheme in {"http", "https"} and cls.is_loopback(origin.hostname) and origin.netloc == host_header

    def _prune(self) -> None:
        now = self._now()
        expired = [sid for sid, session in self._sessions.items() if now - session.last_seen > self.inactivity_seconds]
        for sid in expired:
            self._sessions.pop(sid, None)
        if len(self._sessions) > self.max_sessions:
            oldest = sorted(self._sessions.values(), key=lambda item: item.last_seen)
            for item in oldest[: len(self._sessions) - self.max_sessions]:
                self._sessions.pop(item.session_id, None)

    def _create_session(self, *, client_host: str, host_header: str | None, origin_header: str | None) -> tuple[dict[str, Any], str]:
        if not self.is_loopback(client_host) or not self.same_origin_loopback(host_header, origin_header):
            raise OwnerSessionError("Owner sessions are loopback same-origin only.")
        now = self._now()
        with self._lock:
            self._prune()
            session = _Session(secrets.token_urlsafe(32), secrets.token_urlsafe(32), now, now)
            self._sessions[session.session_id] = session
            self._prune()
        cookie = f"{self.cookie_name}={session.session_id}; HttpOnly; SameSite=Strict; Path=/; Max-Age={self.inactivity_seconds}"
        return {
            "status": "OWNER_SESSION_ACTIVE",
            "csrf_token": session.csrf_token,
            "inactivity_seconds": self.inactivity_seconds,
            "mutation_nonce_required": True,
            "local_interface_only": True,
            "authentication": "OWNER_PASSWORD",
            "permission_mode": "OWNER_FULL_CONTROL",
        }, cookie

    def create(self, *, client_host: str, host_header: str | None, origin_header: str | None) -> tuple[dict[str, Any], str]:
        """Compatibility helper for isolated tests; the HTTP server never exposes it."""
        return self._create_session(client_host=client_host, host_header=host_header, origin_header=origin_header)

    def login(self, *, username: str, password: str, client_host: str, host_header: str | None, origin_header: str | None) -> tuple[dict[str, Any], str]:
        if not self.is_loopback(client_host) or not self.same_origin_loopback(host_header, origin_header):
            raise OwnerSessionError("Owner login is loopback same-origin only.")
        if self.credential_verifier is None or not self.credential_verifier.configured:
            raise OwnerSessionError("Owner credentials are not configured on the server.")
        now = self._now()
        with self._lock:
            recent = [item for item in self._failures.get(client_host, []) if now - item <= self.lockout_seconds]
            self._failures[client_host] = recent
            if len(recent) >= self.maximum_failures:
                raise OwnerSessionError("Owner login is temporarily locked after repeated failures.")
        if not self.credential_verifier.verify(username, password):
            with self._lock:
                self._failures.setdefault(client_host, []).append(now)
            raise OwnerSessionError("Owner username or password is invalid.")
        with self._lock:
            self._failures.pop(client_host, None)
        return self._create_session(client_host=client_host, host_header=host_header, origin_header=origin_header)

    def describe(self, session: _Session) -> dict[str, Any]:
        return {
            "status": "OWNER_SESSION_ACTIVE",
            "csrf_token": session.csrf_token,
            "inactivity_seconds": self.inactivity_seconds,
            "mutation_nonce_required": True,
            "local_interface_only": True,
            "authentication": "OWNER_PASSWORD",
            "permission_mode": "OWNER_FULL_CONTROL",
        }

    def logout(self, *, cookie_header: str | None) -> str:
        session_id = self._cookie_session_id(cookie_header)
        with self._lock:
            if session_id:
                self._sessions.pop(session_id, None)
        return f"{self.cookie_name}=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0"

    def _cookie_session_id(self, cookie_header: str | None) -> str | None:
        if not cookie_header:
            return None
        cookie = SimpleCookie()
        try:
            cookie.load(cookie_header)
        except Exception:
            return None
        morsel = cookie.get(self.cookie_name)
        return morsel.value if morsel else None

    def require(self, *, client_host: str, host_header: str | None, origin_header: str | None, cookie_header: str | None) -> _Session:
        if not self.is_loopback(client_host) or not self.same_origin_loopback(host_header, origin_header):
            raise OwnerSessionError("Loopback same-origin request required.")
        session_id = self._cookie_session_id(cookie_header)
        with self._lock:
            self._prune()
            session = self._sessions.get(session_id or "")
            if session is None:
                raise OwnerSessionError("Owner session is missing or expired.")
            session.last_seen = self._now()
            return session

    def authorize_mutation(self, *, client_host: str, host_header: str | None, origin_header: str | None, cookie_header: str | None, csrf_token: str | None, nonce: Any) -> _Session:
        session = self.require(client_host=client_host, host_header=host_header, origin_header=origin_header, cookie_header=cookie_header)
        if not csrf_token or not secrets.compare_digest(csrf_token, session.csrf_token):
            raise OwnerSessionError("CSRF validation failed.")
        if not isinstance(nonce, str) or not 16 <= len(nonce) <= 128 or not nonce.replace("-", "").replace("_", "").isalnum():
            raise OwnerSessionError("A valid one-time mutation nonce is required.")
        now = self._now()
        with self._lock:
            session.nonces = {key: used for key, used in session.nonces.items() if now - used <= self.nonce_ttl_seconds}
            if nonce in session.nonces:
                raise OwnerSessionError("Mutation replay rejected.")
            session.nonces[nonce] = now
        return session

    @staticmethod
    def digest(session: _Session) -> str:
        return hashlib.sha256(session.session_id.encode("utf-8")).hexdigest()

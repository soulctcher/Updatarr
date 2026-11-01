"""Authentication boundary with durable Argon2id credentials and sessions."""

from __future__ import annotations

from dataclasses import dataclass
import secrets
import time
from typing import Callable, Protocol

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError


class AuthenticationError(Exception):
    """An authentication attempt cannot be accepted."""


@dataclass(frozen=True)
class Session:
    session_id: str
    csrf_token: str
    expires_at: float


@dataclass
class _AttemptWindow:
    failures: int = 0
    blocked_until: float = 0


class AuthenticationRepository(Protocol):
    def password_verifier(self, account_id: str) -> str | None: ...
    def save_password_verifier(self, account_id: str, verifier: str) -> None: ...
    def save_session(self, account_id: str, session_id: str, csrf_token: str, expires_at: float) -> None: ...
    def load_session(self, session_id: str) -> tuple[str, float] | None: ...
    def delete_session(self, session_id: str) -> None: ...
    def clear_sessions(self, account_id: str) -> None: ...


class SessionStore:
    """Own opaque sessions, expiry, password rotation and login throttling."""

    def __init__(
        self,
        password: str,
        *,
        ttl_seconds: int = 1800,
        max_failures: int = 3,
        throttle_seconds: int = 2,
        clock: Callable[[], float] = time.time,
        repository: AuthenticationRepository | None = None,
        password_hasher: PasswordHasher | None = None,
    ) -> None:
        if len(password) < 8:
            raise ValueError("Password must contain at least 8 characters")
        self._clock = clock
        self._ttl = ttl_seconds
        self._max_failures = max_failures
        self._throttle_seconds = throttle_seconds
        self._repository = repository
        self._account_id = "administrator"
        self._password_hasher = password_hasher or PasswordHasher()
        verifier = repository.password_verifier(self._account_id) if repository else None
        self._password_hash = verifier or self._password_hasher.hash(password)
        if repository and verifier is None:
            repository.save_password_verifier(self._account_id, self._password_hash)
        self._sessions: dict[str, Session] = {}
        self._attempts: dict[str, _AttemptWindow] = {}

    def _password_matches(self, password: str) -> bool:
        try:
            accepted = self._password_hasher.verify(self._password_hash, password)
        except (VerifyMismatchError, InvalidHashError):
            return False
        if accepted and self._password_hasher.check_needs_rehash(self._password_hash):
            self._password_hash = self._password_hasher.hash(password)
            if self._repository:
                self._repository.save_password_verifier(self._account_id, self._password_hash)
        return accepted

    def authenticate(self, password: str, client_key: str) -> Session:
        now = self._clock()
        attempts = self._attempts.setdefault(client_key, _AttemptWindow())
        if attempts.blocked_until > now:
            raise AuthenticationError("Please wait before trying again.")
        if not self._password_matches(password):
            attempts.failures += 1
            if attempts.failures >= self._max_failures:
                attempts.failures = 0
                attempts.blocked_until = now + self._throttle_seconds
            raise AuthenticationError("The password was not accepted.")
        self._attempts.pop(client_key, None)
        return self._new_session(now)

    def _new_session(self, now: float | None = None) -> Session:
        issued_at = self._clock() if now is None else now
        session = Session(
            session_id=secrets.token_urlsafe(32),
            csrf_token=secrets.token_urlsafe(32),
            expires_at=issued_at + self._ttl,
        )
        self._sessions[session.session_id] = session
        if self._repository:
            self._repository.save_session(
                self._account_id, session.session_id, session.csrf_token, session.expires_at
            )
        return session

    def get(self, session_id: str | None) -> Session | None:
        if not session_id:
            return None
        session = self._sessions.get(session_id)
        if session is None and self._repository:
            stored = self._repository.load_session(session_id)
            if stored is not None:
                session = Session(session_id, stored[0], stored[1])
                self._sessions[session_id] = session
        if session is None:
            return None
        if session.expires_at <= self._clock():
            self._sessions.pop(session_id, None)
            if self._repository:
                self._repository.delete_session(session_id)
            return None
        return session

    def remaining_seconds(self, session: Session) -> int:
        return max(0, int(session.expires_at - self._clock()))

    def revoke(self, session_id: str | None) -> None:
        if session_id:
            self._sessions.pop(session_id, None)
            if self._repository:
                self._repository.delete_session(session_id)

    def change_password(self, old_password: str, new_password: str) -> Session:
        if len(new_password) < 8:
            raise AuthenticationError("Use at least 8 characters.")
        if not self._password_matches(old_password):
            raise AuthenticationError("The current password was not accepted.")
        self._password_hash = self._password_hasher.hash(new_password)
        if self._repository:
            self._repository.save_password_verifier(self._account_id, self._password_hash)
            self._repository.clear_sessions(self._account_id)
        self._sessions.clear()
        return self._new_session()

    def recover_from_managed_host(self, new_password: str, *, host_local: bool) -> None:
        """Reset credentials only through a caller-proven managed-host path."""
        if not host_local:
            raise AuthenticationError("Recovery is available only on the managed computer.")
        if len(new_password) < 8:
            raise AuthenticationError("Use at least 8 characters.")
        self._password_hash = self._password_hasher.hash(new_password)
        if self._repository:
            self._repository.save_password_verifier(self._account_id, self._password_hash)
            self._repository.clear_sessions(self._account_id)
        self._sessions.clear()

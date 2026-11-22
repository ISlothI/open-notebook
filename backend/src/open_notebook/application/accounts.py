"""Use cases of registration and sign-in."""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta

import structlog

from open_notebook.application.ports import Clock, PasswordHasher, TransactionFactory
from open_notebook.domain.accounts import User, ensure_password, normalise_email
from open_notebook.domain.errors import (
    InvalidCredentialsError,
    NotSignedInError,
    TooManyAttemptsError,
)

SESSION_LIFETIME = timedelta(days=30)
ATTEMPT_WINDOW = timedelta(minutes=15)
MAX_FAILED_ATTEMPTS = 10
TOKEN_BYTES = 32

log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class SignedIn:
    user: User
    token: str


def hash_token(token: str) -> bytes:
    """Tokens are random, so a fast hash is enough to make a database leak useless."""
    return hashlib.sha256(token.encode()).digest()


def attempt_key(email: str, client: str) -> bytes:
    return hashlib.sha256(f"{email}\n{client}".encode()).digest()


class AccountService:
    def __init__(
        self, transactions: TransactionFactory, hasher: PasswordHasher, clock: Clock
    ) -> None:
        self._transactions = transactions
        self._hasher = hasher
        self._clock = clock
        # Verified for unknown addresses, so that response time does not reveal accounts.
        self._unknown_user_hash = hasher.hash(secrets.token_urlsafe())

    def register(self, email: str, password: str) -> SignedIn:
        normalised = normalise_email(email)
        ensure_password(password)
        password_hash = self._hasher.hash(password)
        with self._transactions() as tx:
            user = tx.accounts.add_user(normalised, password_hash)
        log.info("user_registered", user_id=str(user.id))
        return self._open_session(user)

    def sign_in(self, email: str, password: str, client: str) -> SignedIn:
        normalised = email.strip().lower()
        key = attempt_key(normalised, client)
        now = self._clock()
        with self._transactions() as tx:
            if tx.accounts.count_failed_logins(key, now - ATTEMPT_WINDOW) >= MAX_FAILED_ATTEMPTS:
                raise TooManyAttemptsError("Too many failed attempts; try again later.")
            found = tx.accounts.find_credentials(normalised)

        password_hash = found[1] if found else self._unknown_user_hash
        valid = self._hasher.verify(password_hash, password)
        if found is None or not valid:
            with self._transactions() as tx:
                tx.accounts.record_failed_login(key, now)
            log.warning("sign_in_failed")
            raise InvalidCredentialsError("The e-mail address or the password is wrong.")

        with self._transactions() as tx:
            tx.accounts.clear_failed_logins(key)
        return self._open_session(found[0])

    def sign_out(self, token: str) -> None:
        with self._transactions() as tx:
            tx.accounts.delete_session(hash_token(token))

    def authenticate(self, token: str | None) -> User:
        if token:
            with self._transactions() as tx:
                user = tx.accounts.find_session_user(hash_token(token), self._clock())
            if user:
                return user
        raise NotSignedInError("Sign in to continue.")

    def _open_session(self, user: User) -> SignedIn:
        token = secrets.token_urlsafe(TOKEN_BYTES)
        with self._transactions() as tx:
            tx.accounts.add_session(hash_token(token), user.id, self._clock() + SESSION_LIFETIME)
        return SignedIn(user, token)

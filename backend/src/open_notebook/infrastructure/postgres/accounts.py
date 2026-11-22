"""Account, session and sign-in attempt storage."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Connection, delete, func, insert, select
from sqlalchemy.dialects.postgresql import insert as upsert

from open_notebook.domain.accounts import User
from open_notebook.domain.errors import EmailTakenError
from open_notebook.infrastructure.postgres.tables import failed_logins, sessions, users


class PostgresAccounts:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def add_user(self, email: str, password_hash: str) -> User:
        user_id = self._connection.scalar(
            upsert(users)
            .values(email=email, password_hash=password_hash)
            .on_conflict_do_nothing(index_elements=[users.c.email])
            .returning(users.c.id)
        )
        if user_id is None:
            raise EmailTakenError("An account with this e-mail address already exists.")
        return User(user_id, email)

    def find_credentials(self, email: str) -> tuple[User, str] | None:
        row = self._connection.execute(
            select(users.c.id, users.c.email, users.c.password_hash).where(users.c.email == email)
        ).one_or_none()
        return (User(row.id, row.email), row.password_hash) if row else None

    def add_session(self, token_hash: bytes, user_id: UUID, expires_at: datetime) -> None:
        self._connection.execute(
            insert(sessions).values(token_hash=token_hash, user_id=user_id, expires_at=expires_at)
        )

    def find_session_user(self, token_hash: bytes, now: datetime) -> User | None:
        row = self._connection.execute(
            select(users.c.id, users.c.email)
            .join(sessions, sessions.c.user_id == users.c.id)
            .where(sessions.c.token_hash == token_hash, sessions.c.expires_at > now)
        ).one_or_none()
        return User(row.id, row.email) if row else None

    def delete_session(self, token_hash: bytes) -> None:
        self._connection.execute(delete(sessions).where(sessions.c.token_hash == token_hash))

    def record_failed_login(self, key: bytes, at: datetime) -> None:
        self._connection.execute(insert(failed_logins).values(key=key, at=at))

    def count_failed_logins(self, key: bytes, since: datetime) -> int:
        count = self._connection.scalar(
            select(func.count()).where(failed_logins.c.key == key, failed_logins.c.at > since)
        )
        return count or 0

    def clear_failed_logins(self, key: bytes) -> None:
        self._connection.execute(delete(failed_logins).where(failed_logins.c.key == key))

"""Accounts and the rules of their credentials."""

import re
from dataclasses import dataclass
from uuid import UUID

from open_notebook.domain.errors import InvalidValueError

MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 128
MAX_EMAIL_LENGTH = 254
EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


@dataclass(frozen=True)
class User:
    id: UUID
    email: str


def normalise_email(email: str) -> str:
    normalised = email.strip().lower()
    if len(normalised) > MAX_EMAIL_LENGTH or not EMAIL_PATTERN.fullmatch(normalised):
        raise InvalidValueError("The e-mail address is not valid.")
    return normalised


def ensure_password(password: str) -> None:
    if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
        raise InvalidValueError(
            f"The password must have {MIN_PASSWORD_LENGTH} to {MAX_PASSWORD_LENGTH} characters."
        )

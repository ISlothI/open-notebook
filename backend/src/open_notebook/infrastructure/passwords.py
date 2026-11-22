"""Password hashing."""

import argon2

# OWASP-recommended parameters that keep the memory use of concurrent sign-ins low.
MEMORY_KIB = 19_456
ITERATIONS = 2
PARALLELISM = 1


class Argon2PasswordHasher:
    def __init__(self) -> None:
        self._hasher = argon2.PasswordHasher(
            time_cost=ITERATIONS, memory_cost=MEMORY_KIB, parallelism=PARALLELISM
        )

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password_hash: str, password: str) -> bool:
        try:
            return self._hasher.verify(password_hash, password)
        except argon2.exceptions.VerificationError:
            return False

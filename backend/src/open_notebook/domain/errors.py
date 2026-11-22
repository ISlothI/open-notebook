"""Business rule violations. Each has a stable code that clients can rely on."""


class DomainError(Exception):
    code = "domain_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    code = "not_found"


class InvalidValueError(DomainError):
    code = "invalid_value"


class InvalidHierarchyError(DomainError):
    code = "invalid_hierarchy"


class ParentTrashedError(DomainError):
    code = "parent_trashed"


class EmailTakenError(DomainError):
    code = "email_taken"


class InvalidCredentialsError(DomainError):
    code = "invalid_credentials"


class NotSignedInError(DomainError):
    code = "not_signed_in"


class TooManyAttemptsError(DomainError):
    code = "too_many_attempts"

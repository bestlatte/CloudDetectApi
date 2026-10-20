from __future__ import annotations


class ServiceError(Exception):
    """Base class for expected application-service failures."""

    default_message = "The operation could not be completed."

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.default_message)


class ApprovedTargetNotFoundError(ServiceError):
    default_message = "Target is not in the approved template list."


class InvalidCheckIntervalError(ServiceError):
    def __init__(self, source_kind: str, minimum_minutes: int) -> None:
        self.source_kind = source_kind
        self.minimum_minutes = minimum_minutes
        super().__init__(
            f"{source_kind} targets require an interval of at least {minimum_minutes} minutes."
        )


class MonitorAlreadyExistsError(ServiceError):
    default_message = "This approved target already exists."


class MonitorNotFoundError(ServiceError):
    default_message = "Monitor not found."


class AdminLoginNotConfiguredError(ServiceError):
    default_message = "Admin login is not configured."


class InvalidCredentialsError(ServiceError):
    default_message = "Invalid credentials."


class TooManyLoginAttemptsError(ServiceError):
    default_message = "Too many login attempts."


class AdminSessionRequiredError(ServiceError):
    default_message = "Administrator login required."


class CsrfValidationError(ServiceError):
    default_message = "CSRF validation failed."

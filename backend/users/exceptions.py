"""Custom exceptions for users app."""


class UserError(Exception):
    """Base exception for user operations."""

    def __init__(self, message: str, code: str | None = None):
        self.message = message
        self.code = code
        super().__init__(message)


class UserInvalidPasswordError(UserError):
    """Raised when the current password is invalid."""

    def __init__(self, message: str = 'Invalid current password'):
        super().__init__(message, code='invalid_password')


class UserInvalidConsentTypeError(UserError):
    """Raised when an invalid consent type is provided."""

    def __init__(self, consent_type: str):
        super().__init__(f'Invalid consent type: {consent_type}', code='invalid_consent_type')


class UserConsentNotFoundError(UserError):
    """Raised when no active consent is found."""

    def __init__(self, message: str = 'No active consent found for this type'):
        super().__init__(message, code='consent_not_found')


class UserValidationValidationError(UserError):
    """Raised when validation fails."""

    def __init__(self, message: str):
        super().__init__(message, code='validation_error')


class UserDeletionBlockedError(UserError):
    """Raised when account deletion is blocked by owned workspaces with members."""

    def __init__(self, blocking_workspaces: list[str]):
        message = (
            'Cannot delete account. You own workspaces with other members: '
            f'{", ".join(blocking_workspaces)}. '
            'Transfer ownership or remove all members first.'
        )
        super().__init__(message, code='deletion_blocked')

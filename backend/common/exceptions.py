"""Shared service exception base classes.

All domain exceptions should inherit from ServiceError or one of its subclasses.
A global Django Ninja exception handler in config/urls.py converts these to HTTP
responses automatically, so API endpoints do not need try/except for service errors.
"""


class ServiceError(Exception):
    """Base for all domain service exceptions.

    Subclasses set http_status and default_message as class attributes.
    The message can be overridden per-raise via the constructor.
    """

    http_status: int = 500
    default_message: str = 'An unexpected error occurred'

    def __init__(self, message: str | None = None, code: str | None = None):
        self.message = message if message is not None else self.default_message
        self.code = code
        super().__init__(self.message)


class NotFoundError(ServiceError):
    """Resource does not exist. Maps to HTTP 404."""

    http_status = 404
    default_message = 'Not found'


class ValidationError(ServiceError):
    """Input fails domain validation. Maps to HTTP 400."""

    http_status = 400
    default_message = 'Validation error'

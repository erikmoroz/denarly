"""Custom exceptions for reports app."""


class ReportError(Exception):
    """Base exception for report operations."""

    def __init__(self, message: str, code: str | None = None):
        self.message = message
        self.code = code
        super().__init__(message)


class ReportPeriodNotFoundError(ReportError):
    """Raised when a budget period is not found."""

    def __init__(self, message: str = 'Budget period not found'):
        super().__init__(message, code='period_not_found')

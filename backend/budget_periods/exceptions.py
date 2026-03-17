"""Custom exceptions for budget_periods app."""


class BudgetPeriodError(Exception):
    """Base exception for budget period operations."""

    def __init__(self, message: str, code: str | None = None):
        self.message = message
        self.code = code
        super().__init__(message)


class BudgetPeriodNotFoundError(BudgetPeriodError):
    """Raised when a budget period is not found."""

    def __init__(self, message: str = 'Period not found'):
        super().__init__(message, code='not_found')

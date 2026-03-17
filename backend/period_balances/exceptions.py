"""Custom exceptions for period_balances app."""


class PeriodBalanceError(Exception):
    """Base exception for period balance operations."""

    def __init__(self, message: str, code: str | None = None):
        self.message = message
        self.code = code
        super().__init__(message)


class PeriodBalanceNotFoundError(PeriodBalanceError):
    """Raised when a period balance is not found."""

    def __init__(self, message: str = 'Period balance not found'):
        super().__init__(message, code='not_found')


class PeriodBalancePeriodNotFoundError(PeriodBalanceError):
    """Raised when a budget period is not found."""

    def __init__(self, message: str = 'Budget period not found'):
        super().__init__(message, code='period_not_found')


class PeriodBalanceCurrencyNotFoundError(PeriodBalanceError):
    """Raised when a currency is not found in the workspace."""

    def __init__(self, currency: str):
        super().__init__(f'Currency {currency} not found in workspace', code='currency_not_found')

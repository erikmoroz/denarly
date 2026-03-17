"""Custom exceptions for planned_transactions app."""


class PlannedTransactionError(Exception):
    """Base exception for planned transaction operations."""

    def __init__(self, message: str, code: str | None = None):
        self.message = message
        self.code = code
        super().__init__(message)


class PlannedTransactionNotFoundError(PlannedTransactionError):
    """Raised when a planned transaction is not found."""

    def __init__(self, message: str = 'Planned transaction not found'):
        super().__init__(message, code='not_found')


class PlannedTransactionPeriodNotFoundError(PlannedTransactionError):
    """Raised when a budget period is not found."""

    def __init__(self, message: str = 'Budget period not found'):
        super().__init__(message, code='period_not_found')


class PlannedTransactionNoActivePeriodError(PlannedTransactionError):
    """Raised when no active budget period exists for the date."""

    def __init__(self, message: str = 'No active budget period for the planned transaction date'):
        super().__init__(message, code='no_active_period')


class PlannedTransactionCategoryNotFoundError(PlannedTransactionError):
    """Raised when a category is not found or doesn't belong to the period."""

    def __init__(self, message: str = 'Category not found or does not belong to the specified budget period'):
        super().__init__(message, code='category_not_found')


class PlannedTransactionCurrencyNotFoundError(PlannedTransactionError):
    """Raised when a currency is not found in the workspace."""

    def __init__(self, currency: str):
        super().__init__(f'Currency {currency} not found in workspace', code='currency_not_found')


class PlannedTransactionAlreadyExecutedError(PlannedTransactionError):
    """Raised when trying to execute an already executed planned transaction."""

    def __init__(self, message: str = 'Already executed'):
        super().__init__(message, code='already_executed')


class PlannedTransactionImportError(PlannedTransactionError):
    """Raised when planned transaction import data is invalid."""

    def __init__(self, message: str):
        super().__init__(message, code='import_error')

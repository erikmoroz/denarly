"""Custom exceptions for budget_accounts app."""


class BudgetAccountError(Exception):
    """Base exception for budget account operations."""

    def __init__(self, message: str, code: str | None = None):
        self.message = message
        self.code = code
        super().__init__(message)


class BudgetAccountNotFoundError(BudgetAccountError):
    """Raised when a budget account is not found."""

    def __init__(self, message: str = 'Budget account not found'):
        super().__init__(message, code='not_found')


class BudgetAccountDuplicateNameError(BudgetAccountError):
    """Raised when attempting to create/update with a duplicate name."""

    def __init__(self, message: str = 'Budget account with this name already exists'):
        super().__init__(message, code='duplicate_name')


class BudgetAccountCurrencyNotFoundError(BudgetAccountError):
    """Raised when a specified currency is not found in the workspace."""

    def __init__(self, currency: str):
        super().__init__(f'Currency {currency} not found in workspace', code='currency_not_found')

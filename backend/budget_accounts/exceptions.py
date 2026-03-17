"""Custom exceptions for budget_accounts app."""

from common.exceptions import NotFoundError, ValidationError


class BudgetAccountNotFoundError(NotFoundError):
    default_message = 'Budget account not found'

    def __init__(self, message: str | None = None):
        super().__init__(message, code='not_found')


class BudgetAccountDuplicateNameError(ValidationError):
    default_message = 'Budget account with this name already exists'

    def __init__(self, message: str | None = None):
        super().__init__(message, code='duplicate_name')


class BudgetAccountCurrencyNotFoundError(ValidationError):
    def __init__(self, currency: str):
        super().__init__(f'Currency {currency} not found in workspace', code='currency_not_found')

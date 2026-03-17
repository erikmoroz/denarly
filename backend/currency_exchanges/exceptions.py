"""Custom exceptions for currency_exchanges app."""

from common.exceptions import NotFoundError, ValidationError


class CurrencyExchangeNotFoundError(NotFoundError):
    default_message = 'Exchange not found'

    def __init__(self, message: str | None = None):
        super().__init__(message, code='not_found')


class CurrencyExchangePeriodNotFoundError(NotFoundError):
    default_message = 'Budget period not found'

    def __init__(self, message: str | None = None):
        super().__init__(message, code='period_not_found')


class CurrencyExchangeCurrencyNotFoundError(ValidationError):
    def __init__(self, currency: str):
        super().__init__(f'Currency {currency} not found in workspace', code='currency_not_found')


class CurrencyExchangeImportError(ValidationError):
    def __init__(self, message: str):
        super().__init__(message, code='import_error')

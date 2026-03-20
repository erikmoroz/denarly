"""Domain exceptions for the workspaces app."""

from common.exceptions import NotFoundError, ValidationError


class CurrencyNotFoundError(NotFoundError):
    default_message = 'Currency not found'
    default_code = 'not_found'


class CurrencyDuplicateSymbolError(ValidationError):
    def __init__(self, symbol: str):
        super().__init__(f'Currency with symbol {symbol} already exists in this workspace', code='duplicate_symbol')

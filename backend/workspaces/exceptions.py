"""Custom exceptions for workspaces app."""


class WorkspaceError(Exception):
    """Base exception for workspace operations."""

    def __init__(self, message: str, code: str | None = None):
        self.message = message
        self.code = code
        super().__init__(message)


class WorkspaceCurrencyNotFoundError(WorkspaceError):
    """Raised when a currency is not found."""

    def __init__(self, message: str = 'Currency not found'):
        super().__init__(message, code='not_found')


class WorkspaceCurrencyDuplicateError(WorkspaceError):
    """Raised when a currency with the same symbol already exists."""

    def __init__(self, symbol: str):
        super().__init__(f'Currency with symbol {symbol} already exists in this workspace', code='duplicate')

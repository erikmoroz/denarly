"""Custom exceptions for categories app."""

from common.exceptions import NotFoundError, ValidationError


class CategoryNotFoundError(NotFoundError):
    default_message = 'Category not found'

    def __init__(self, message: str | None = None):
        super().__init__(message, code='not_found')


class CategoryPeriodNotFoundError(NotFoundError):
    default_message = 'Budget period not found'

    def __init__(self, message: str | None = None):
        super().__init__(message, code='period_not_found')


class CategoryDuplicateNameError(ValidationError):
    default_message = 'A category with this name already exists in this budget period.'

    def __init__(self, message: str | None = None):
        super().__init__(message, code='duplicate_name')

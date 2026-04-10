from math import ceil
from typing import Generic, TypeVar

from django.db.models import QuerySet
from pydantic import BaseModel

T = TypeVar('T')

ALLOWED_PAGE_SIZES = [25, 50, 100, 200]
DEFAULT_PAGE_SIZE = 50


class PaginatedOut(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


def paginate_queryset(
    queryset: QuerySet,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> tuple[list, int, int, int, int]:
    if page_size not in ALLOWED_PAGE_SIZES:
        page_size = DEFAULT_PAGE_SIZE
    if page < 1:
        page = 1

    total = queryset.count()
    total_pages = max(1, ceil(total / page_size)) if total > 0 else 0
    offset = (page - 1) * page_size
    items = list(queryset[offset : offset + page_size])

    return items, total, page, page_size, total_pages

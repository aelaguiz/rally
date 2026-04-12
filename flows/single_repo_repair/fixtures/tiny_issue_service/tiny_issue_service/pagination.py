"""Pagination helpers for the Rally single-repo repair flow."""


def paginate_issues(items: list[str], page: int, page_size: int) -> list[str]:
    if page < 1:
        raise ValueError("page must be >= 1")
    if page_size < 1:
        raise ValueError("page_size must be >= 1")

    # Seeded bug: page 1 should start at index 0, not page_size.
    start = page * page_size
    end = start + page_size
    return items[start:end]

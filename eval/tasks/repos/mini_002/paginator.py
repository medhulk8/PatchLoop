"""
Simple pagination utilities.
"""


def paginate(items, page, page_size):
    """
    Return the items for a given page (1-indexed).

    Args:
        items:     the full list of items
        page:      page number, starting at 1
        page_size: number of items per page

    Returns:
        A sublist of items for the requested page.
        Returns an empty list if the page is out of range.
    """
    if page < 1 or page_size < 1:
        return []

    # BUG: start is calculated correctly but end uses page instead of page+1-1
    # The slice end should be: page * page_size
    # Currently off-by-one: uses (page - 1) * page_size + page_size - 1
    # which drops the last item of every page.
    start = (page - 1) * page_size
    end = start + page_size - 1   # BUG: should be start + page_size

    return items[start:end]


def total_pages(total_items, page_size):
    """Return the total number of pages for a given item count and page size."""
    if page_size < 1:
        return 0
    return (total_items + page_size - 1) // page_size

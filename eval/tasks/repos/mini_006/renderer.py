def heading_id(title: str) -> str:
    """Return the HTML id attribute value for a heading element.

    Must produce anchors that match slugify() exactly.
    """
    # BUG: duplicates the (broken) normalization logic from slug.py instead of
    # importing slugify. Even after slugify is fixed, heading_id stays broken.
    return title.strip().lower().replace(" ", "-")

def toc_link(title: str) -> str:
    """Return the TOC anchor link for a heading (e.g. '#api-reference').

    Must produce anchors that match slugify() exactly.
    """
    # BUG: duplicates the (broken) normalization logic from slug.py instead of
    # importing slugify. Even after slugify is fixed, toc_link stays broken.
    return "#" + title.strip().lower().replace(" ", "-")

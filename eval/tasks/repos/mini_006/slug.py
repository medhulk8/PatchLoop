def slugify(title: str) -> str:
    """Convert a heading title to a URL-safe anchor slug.

    Should strip punctuation, collapse whitespace, and lowercase.
    """
    return title.strip().lower().replace(" ", "-")   # BUG: punctuation not removed,
                                                     # multiple spaces not collapsed.

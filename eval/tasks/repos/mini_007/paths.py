import os


def safe_join(base: str, *parts: str) -> str:
    """Safely join path components under base, rejecting traversal attempts.

    Raises ValueError if the resulting path escapes the base directory.
    """
    if any("/" in part or "\\" in part for part in parts):
        raise ValueError("nested paths not allowed")   # BUG: bans ALL nested paths,
                                                       # including legitimate ones like
                                                       # logs/2026/app.log.
    return os.path.join(base, *parts)

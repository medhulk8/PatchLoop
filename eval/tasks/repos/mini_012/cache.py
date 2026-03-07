_store: dict = {}


def cache_get(template: str, locale: str, mode: str):
    """Return a cached render result, or None if not cached."""
    key = template  # BUG: key ignores locale and mode — different render params share a slot
    return _store.get(key)


def cache_put(template: str, locale: str, mode: str, value: str) -> None:
    """Store a render result in the cache."""
    key = template  # BUG: same incomplete key — first render wins for all locales/modes
    _store[key] = value


def cache_clear() -> None:
    _store.clear()

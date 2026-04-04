_DEFAULT_PRIORITY = 5
_DEFAULT_VALUE = 1.0


def enrich_events(events: list, defaults: dict) -> list:
    """Apply default values for any fields that are unset on each event."""
    enriched = []
    for e in events:
        # If a field has no value, substitute the caller-supplied default.
        # A missing field is indicated by a falsy value (None, 0, 0.0, etc.).
        e.priority = e.priority or defaults.get("priority", _DEFAULT_PRIORITY)
        e.value = e.value or defaults.get("value", _DEFAULT_VALUE)
        enriched.append(e)
    return enriched

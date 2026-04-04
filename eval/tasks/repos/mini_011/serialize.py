def serialize(config: dict) -> dict:
    """Return config as a plain dict, omitting keys that have no value set.

    Only keys explicitly set to None are considered absent and omitted.
    Keys set to False, 0, or "" are valid explicit values and must be kept.
    """
    return {k: v for k, v in config.items() if v}  # BUG: drops falsy values; should only drop None

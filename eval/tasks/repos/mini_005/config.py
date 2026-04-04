def merge_config(defaults: dict, overrides: dict) -> dict:
    """Merge overrides into defaults, with overrides taking precedence.

    Nested dicts should be merged recursively so that overriding one key
    does not remove sibling keys.
    """
    result = defaults.copy()
    result.update(overrides)   # BUG: shallow update replaces entire nested dicts
                               # instead of merging them, so sibling keys are lost.
    return result

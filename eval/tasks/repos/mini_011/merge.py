def merge(base: dict, override: dict) -> dict:
    """Merge override into base. Override values take precedence.

    Returns a new dict; neither input is mutated.
    A key present in override with value None means "use base value".
    All other override values — including False, 0, and "" — are explicit
    and must override the base.
    """
    result = dict(base)
    for k, v in override.items():
        result[k] = result.get(k) or v  # BUG: drops falsy override values (False, 0, "")
    return result

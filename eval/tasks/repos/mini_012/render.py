from cache import cache_get, cache_put

_translations = {
    "en": "Hello",
    "fr": "Bonjour",
    "es": "Hola",
    "de": "Hallo",
}


def render(template: str, locale: str = "en", mode: str = "html") -> str:
    """Render a template string with a locale-specific greeting.

    Results are cached so repeated renders with identical parameters
    avoid redundant computation.
    """
    cached = cache_get(template, locale, mode)
    if cached is not None:
        return cached

    greeting = _translations.get(locale, "Hello")
    if mode == "plain":
        result = f"{greeting}: {template}"
    else:
        result = f"<p>{greeting}: {template}</p>"

    cache_put(template, locale, mode, result)
    return result

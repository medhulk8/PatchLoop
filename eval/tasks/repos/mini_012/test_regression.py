import cache
from render import render


def setup_function():
    cache.cache_clear()


def test_regression_01():
    # Rendering in English then French should give the French output
    render("welcome", locale="en")
    result = render("welcome", locale="fr")
    assert result == "<p>Bonjour: welcome</p>"


def test_regression_02():
    # Rendering in html then plain mode should give the plain output
    render("greeting", locale="en", mode="html")
    result = render("greeting", locale="en", mode="plain")
    assert result == "Hello: greeting"


def test_regression_03():
    # Each locale must produce its own independently cached result
    en = render("hello", locale="en")
    de = render("hello", locale="de")
    assert en == "<p>Hello: hello</p>"
    assert de == "<p>Hallo: hello</p>"


def test_regression_04():
    # Spanish render must not be polluted by prior English render
    render("world", locale="en")
    result = render("world", locale="es")
    assert result == "<p>Hola: world</p>"

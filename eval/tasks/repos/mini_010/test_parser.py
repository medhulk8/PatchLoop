from parser import parse_line


def test_simple_fields():
    assert parse_line("a,b,c") == ["a", "b", "c"]


def test_trailing_empty_field():
    assert parse_line("a,b,") == ["a", "b", ""]


def test_empty_middle_field():
    assert parse_line("a,,c") == ["a", "", "c"]


def test_quoted_field_containing_comma():
    # The naive split breaks on the comma inside the quoted field.
    assert parse_line('a,"b,c",d') == ["a", "b,c", "d"]


def test_quoted_field_with_trailing_empty():
    assert parse_line('a,"b,c",') == ["a", "b,c", ""]


def test_escaped_double_quote_inside_field():
    # Escaped quotes: "" inside a quoted field represents a literal ".
    assert parse_line('a,"say ""hello""",b') == ["a", 'say "hello"', "b"]

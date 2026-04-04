def parse_line(line: str) -> list[str]:
    """Parse a single CSV line into a list of field values.

    Must handle quoted fields (which may contain commas and escaped quotes).
    """
    return [part.strip() for part in line.rstrip("\n").split(",")]
    # BUG: naive split(",") breaks on commas inside quoted fields,
    # e.g. 'a,"b,c"' is split into ['a', '"b', 'c"'] instead of ['a', 'b,c'].

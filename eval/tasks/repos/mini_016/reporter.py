def build_report(formatted: dict[str, dict]) -> list[dict]:
    """Assemble the final report as a sorted list of category entries."""
    return [
        {"category": cat, **data}
        for cat, data in sorted(formatted.items())
    ]

def build_report(records: dict[str, dict]) -> list[dict]:
    """Convert a service → stats mapping into a flat sorted report list."""
    return [
        {"service": service, **stats}
        for service in sorted(records)
        for stats in [records[service]]
    ]

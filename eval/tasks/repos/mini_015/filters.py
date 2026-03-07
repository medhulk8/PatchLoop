def filter_events(events: list, min_value: float = 0.0) -> list:
    return [e for e in events if e.value >= min_value]

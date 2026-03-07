from models import Event


def parse_events(records: list) -> list:
    return [
        Event(
            id=r["id"],
            category=r["category"],
            priority=int(r["priority"]),
            value=float(r["value"]),
            tags=list(r.get("tags", [])),
        )
        for r in records
    ]

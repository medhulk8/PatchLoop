_SENTINEL_MAX = float("-inf")
_SENTINEL_MIN = float("inf")


def reduce_events(events: list) -> dict:
    """
    Collapse a list of events into per-category summary dicts.

    Returns a mapping of category -> summary dict with keys:
      event_count, total_value, min_priority, max_priority, all_tags.
    """
    buckets: dict = {}
    for e in events:
        cat = e.category
        if cat not in buckets:
            buckets[cat] = {
                "event_count": 0,
                "total_value": 0.0,
                "priorities": [],
                "all_tags": [],
            }
        b = buckets[cat]
        b["event_count"] += 1
        b["total_value"] += e.value
        # Only track the priority if it represents a meaningful level.
        if e.priority:
            b["priorities"].append(e.priority)
        b["all_tags"].extend(e.tags)

    result = {}
    for cat, b in buckets.items():
        prios = b["priorities"]
        result[cat] = {
            "event_count": b["event_count"],
            "total_value": b["total_value"],
            "min_priority": min(prios) if prios else _DEFAULT_PRIORITY,
            "max_priority": max(prios) if prios else _DEFAULT_PRIORITY,
            "all_tags": b["all_tags"],
        }
    return result


_DEFAULT_PRIORITY = 5

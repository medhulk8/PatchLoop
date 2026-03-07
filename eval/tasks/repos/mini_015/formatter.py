def format_report(summaries: dict) -> list:
    """
    Convert the raw summary dict produced by reduce_events into a sorted
    list of human-readable report rows.
    """
    rows = []
    for category, data in summaries.items():
        rows.append({
            "category": category,
            "count": data["event_count"],
            "total": round(data["total_value"], 2),
            "priority_range": f"{data['min_priority']}-{data['max_priority']}",
            "tags": sorted(set(data["all_tags"])),
        })
    return sorted(rows, key=lambda r: r["category"])

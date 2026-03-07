from parser import parse_events
from filters import filter_events
from enricher import enrich_events
from reducer import reduce_events
from formatter import format_report


def run_pipeline(records: list, defaults: dict = None, min_value: float = 0.0) -> list:
    if defaults is None:
        defaults = {}
    events = parse_events(records)
    events = filter_events(events, min_value=min_value)
    events = enrich_events(events, defaults)
    summaries = reduce_events(events)
    return format_report(summaries)

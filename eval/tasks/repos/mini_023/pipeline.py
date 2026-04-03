from loader import load_events
from normalizer import normalize_events
from event_router import route_events
from record_ops import attach_risk_flags
from score_summary import build_score_inputs
from score_calc import compute_risk_score
from reporter import build_report


def run_risk_report(raw_events: list[dict]) -> dict:
    """End-to-end risk scoring pipeline: raw event dicts -> risk report."""
    events = load_events(raw_events)
    events = normalize_events(events)
    events = route_events(events)
    events = attach_risk_flags(events)
    inputs = build_score_inputs(events)
    score = compute_risk_score(inputs["flagged_amount"], inputs["total_amount"])
    return build_report(inputs, score)

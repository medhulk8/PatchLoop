from models import PaymentEvent

_DECISION_PRIORITY = {"block": 0, "review": 1, "allow": 2}


def route_events(events: list[PaymentEvent]) -> list[PaymentEvent]:
    """
    Route payment events for risk assessment processing.

    Filters out events with unrecognised decisions and orders the
    remaining events by risk level so downstream steps process the
    highest-risk events first.
    """
    valid = {"block", "review", "allow"}
    routed = [e for e in events if e.decision in valid]
    return sorted(routed, key=lambda e: _DECISION_PRIORITY.get(e.decision, 99))

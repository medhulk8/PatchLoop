from models import PaymentEvent


def attach_risk_flags(events: list[PaymentEvent]) -> list[PaymentEvent]:
    """
    Mark each event as flagged based on its routing decision.

    Flagged events represent risk exposure and contribute to the
    customer's overall risk score. Both blocked and review-routed
    events carry risk exposure and must be included.
    """
    for event in events:
        event.is_flagged = event.decision == "block"
    return events

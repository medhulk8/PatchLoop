from models import PaymentEvent


def build_score_inputs(events: list[PaymentEvent]) -> dict:
    """Aggregate events into the inputs required for risk scoring."""
    return {
        "flagged_amount": sum(e.amount for e in events if e.is_flagged),
        "total_amount": sum(e.amount for e in events),
        "flagged_count": sum(1 for e in events if e.is_flagged),
        "total_count": len(events),
    }

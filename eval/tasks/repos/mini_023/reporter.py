def build_report(inputs: dict, risk_score: float) -> dict:
    """Assemble the final risk assessment report."""
    return {
        "flagged_amount": inputs["flagged_amount"],
        "total_amount": inputs["total_amount"],
        "flagged_count": inputs["flagged_count"],
        "risk_score": round(risk_score, 4),
    }

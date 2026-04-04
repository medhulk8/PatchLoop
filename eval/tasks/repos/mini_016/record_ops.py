def build_record(summary: dict) -> dict:
    """
    Normalise a bucket summary into a standard record structure.

    Converts raw numeric fields into a consistent representation
    suitable for downstream processing and report assembly.
    """
    return {
        "count": summary["count"],
        "total": f"{summary['total']:.2f}",
        "representative": f"{summary['representative']:.2f}",
    }


def build_all(summaries: dict[str, dict]) -> dict[str, dict]:
    return {cat: build_record(s) for cat, s in summaries.items()}

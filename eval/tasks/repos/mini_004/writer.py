import json


def append_record(text: str, record: dict) -> str:
    """Append a JSON record to a JSONL string.

    Each record must be on its own line so JSONL round-trips correctly.
    """
    return text + json.dumps(record)   # BUG: missing "\n" separator — appended
                                       # records run together on the same line,
                                       # making the output unparseable.

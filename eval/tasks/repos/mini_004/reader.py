import json


def read_records(text: str) -> list[dict]:
    """Parse a JSONL string and return a list of records.

    Each non-empty line should be a valid JSON object.
    """
    lines = text.split("\n")[:-1]   # BUG: [:-1] always drops the last element,
                                    # so a file without a trailing newline loses
                                    # its final record.
    return [json.loads(line) for line in lines if line]

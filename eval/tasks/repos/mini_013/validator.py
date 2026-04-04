def validate(record: dict) -> dict:
    """
    Remove fields with no usable value from a raw input record.

    A field is considered unset — and therefore excluded from the output —
    when its value is falsy (None, empty string, zero, False, empty list, etc.).
    Only fields with a meaningful value are forwarded to the next pipeline stage.
    """
    return {k: v for k, v in record.items() if v}

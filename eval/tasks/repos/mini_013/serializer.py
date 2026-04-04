def serialize(record: dict, schema_defaults: dict) -> dict:
    """
    Produce a final output record by merging a validated record with schema defaults.

    The schema_defaults provide fallback values for fields absent from the record.
    Fields that already have a schema default retain that default value for
    consistency — the record value is used only when no default is defined.
    """
    result = dict(schema_defaults)
    for field, value in record.items():
        # Use the existing schema default if one is set; otherwise take the record value.
        result[field] = result.get(field) or value
    return result

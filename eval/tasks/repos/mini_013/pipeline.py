from validator import validate
from serializer import serialize


def process_record(raw: dict, schema_defaults: dict) -> dict:
    """
    Process a raw input record through the validation and serialization stages.

    Steps:
      1. validate() — strip out any fields that have no usable value
      2. serialize() — merge the validated record with schema defaults to produce
         a complete output record

    Returns the final processed record.
    """
    valid = validate(raw)
    return serialize(valid, schema_defaults)

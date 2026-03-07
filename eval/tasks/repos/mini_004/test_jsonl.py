from reader import read_records
from writer import append_record


def test_reader_single_record_no_trailing_newline():
    # A JSONL file with one record and no trailing newline must not lose it.
    assert read_records('{"a": 1}') == [{"a": 1}]


def test_reader_multiple_records_with_trailing_newline():
    text = '{"a": 1}\n{"b": 2}\n'
    assert read_records(text) == [{"a": 1}, {"b": 2}]


def test_writer_terminates_each_record_with_newline():
    text = append_record("", {"a": 1})
    assert text.endswith("\n"), f"Expected trailing newline, got: {repr(text)}"


def test_writer_separates_records():
    # Two appended records must not run together on the same line.
    text = append_record("", {"a": 1})
    text = append_record(text, {"b": 2})
    lines = [l for l in text.splitlines() if l]
    assert len(lines) == 2, f"Expected 2 lines, got: {repr(text)}"


def test_round_trip():
    text = ""
    text = append_record(text, {"a": 1})
    text = append_record(text, {"b": 2})
    assert read_records(text) == [{"a": 1}, {"b": 2}]

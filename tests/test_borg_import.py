import json
from pathlib import Path

from scripts.borg_import.main import iter_json_records, normalize_directory


FIXTURE_DIR = Path("scripts/borg_import/json_bq")


def test_array_and_ndjson_inputs_are_streamed(tmp_path):
    array_path = tmp_path / "array.json"
    array_path.write_text('[{"value": 1}, {"value": 2}]', encoding="utf-8")
    ndjson_path = tmp_path / "records.ndjson"
    ndjson_path.write_text('{"value": 3}\n{"value": 4}\n', encoding="utf-8")

    assert list(iter_json_records(array_path)) == [{"value": 1}, {"value": 2}]
    assert list(iter_json_records(ndjson_path)) == [{"value": 3}, {"value": 4}]


def test_empty_input_has_no_records_and_invalid_array_fails(tmp_path):
    empty_path = tmp_path / "empty.json"
    empty_path.write_text("", encoding="utf-8")
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("[{\"value\": 1}", encoding="utf-8")

    assert list(iter_json_records(empty_path)) == []
    try:
        list(iter_json_records(invalid_path))
    except ValueError as error:
        assert "unterminated JSON array" in str(error)
    else:
        raise AssertionError("expected an unterminated JSON array to fail")


def test_normalized_output_is_ordered_and_partitioned(tmp_path):
    output_dir = tmp_path / "ordered"
    manifest = normalize_directory(
        FIXTURE_DIR,
        output_dir,
        partition_duration_us=1_000_000_000,
        max_events_in_memory=2,
        max_open_files=2,
    )

    events = []
    for path in sorted(output_dir.glob("partition-*.ndjson")):
        events.extend(json.loads(line) for line in path.read_text().splitlines())

    assert manifest["event_count"] == len(events) == 47
    assert manifest["partition_count"] == len(list(output_dir.glob("partition-*.ndjson")))
    assert [(event["timestamp_us"], event["sequence"]) for event in events] == sorted(
        (event["timestamp_us"], event["sequence"]) for event in events
    )
    assert {event["event_type"] for event in events} == {
        "collection_event",
        "instance_event",
        "instance_usage",
        "machine_attribute",
        "machine_event",
    }


def test_existing_output_requires_explicit_overwrite(tmp_path):
    output_dir = tmp_path / "ordered"
    normalize_directory(FIXTURE_DIR, output_dir)

    try:
        normalize_directory(FIXTURE_DIR, output_dir)
    except ValueError as error:
        assert "--overwrite" in str(error)
    else:
        raise AssertionError("expected existing output to require --overwrite")

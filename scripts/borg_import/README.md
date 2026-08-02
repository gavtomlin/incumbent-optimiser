# Borg trace importer

The importer converts BigQuery-shaped Borg trace exports into ordered, time-partitioned NDJSON for `replay-rust`.

Run it against the sample data with:

```sh
python3 scripts/borg_import/main.py \
  --input-dir scripts/borg_import/json_bq \
  --output-dir data/ordered-traces
```

Each output partition contains canonical events ordered by `timestamp_us` and `sequence`. The original source row is retained under `payload`. `manifest.json` describes the generated trace.

The importer accepts JSON arrays, NDJSON, and gzipped versions of either format. It partitions events before sorting them, then sorts bounded-size runs using temporary disk space. Lower `--max-events-in-memory` to test the memory bound; use `--partition-duration-us` to control partition size.

Use `--overwrite` when regenerating an existing output directory.

# Google ClusterData 2019 trace format memory

Source: `Google cluster-usage traces v3.pdf` supplied for this project.

This file records the trace facts that affect the importer, normalized event model, and replay service. It is a working reference, not a replacement for the source document or the versioned trace-format proto.

## Trace and time model

- Version 3 contains separate May 2019 traces for Borg cells `2019-05-a` through `2019-05-h`.
- Event timestamps are signed 64-bit integers represented in microseconds.
- Timestamps are relative to 600 seconds before the trace window. The beginning of the trace window is therefore `600_000_000` microseconds.
- `time = 0` means the event happened before the trace window. `time = 2^63 - 1` means it happened after the trace window or the end time is unknown.
- Usage timestamps use the same offset, but usage measurements are only precise to approximately one second.
- Usage measurement intervals are at most 300 seconds and may overlap the beginning of the trace window.
- Timestamps are approximate because data comes from multiple machines and may have clock drift.

The importer should retain the original timestamp and distinguish the special values from ordinary in-window timestamps. It should not convert timestamps to wall-clock time during normalization.

## Source tables

The trace contains five tables. Each table is available as sharded, gzip-compressed JSON from a cell-specific GCS bucket. Each line is one JSON object; the files are not JSON arrays. BigQuery exports use the same logical fields.

- `machine_events`: machine availability and capacity transitions.
- `machine_attributes`: machine attribute key/value changes.
- `collection_events`: collection/job/alloc-set lifecycle events and metadata.
- `instance_events`: task/alloc-instance lifecycle events, placement, resource requests, and constraints.
- `instance_usage`: resource usage measurements for instance intervals.

The GCS naming pattern is:

```text
gs://clusterdata_2019_${CELL}/${TABLE_NAME}-*.json.gz
```

The schema files are in the `clusterdata_2019_schema` bucket. The schema is intended to correspond to `clusterdata_trace_format_v3.proto`.

JSON cannot represent int64 values, so timestamps and identifiers such as `collection_id`, `machine_id`, and `instance_index` are represented as strings. The importer must parse them as integers only when arithmetic or ordering is required, while retaining the original JSON-compatible representation where useful.

## Identifiers and relationships

- Collection IDs and machine IDs are unique 64-bit identifiers and are not normally reused.
- An instance is identified by `(collection_id, instance_index)`.
- Instance indexes are zero-based.
- A task can be stopped and restarted with the same collection ID and instance index, so that pair identifies a logical instance across multiple lifecycle episodes rather than one uninterrupted execution.
- User names and collection names are opaque, hashed, base64-encoded strings. Equality comparisons are meaningful; decoding is not expected.
- `alloc_collection_id` and `alloc_instance_index` connect jobs/tasks to alloc sets and alloc instances.

The normalized model should preserve these IDs as join keys. It should not collapse all rows for an instance into one record.

## Resource units

- CPU requests and usage use normalized compute units (NCUs), derived from Google compute units.
- Memory is normalized by the maximum machine memory observed across the traces.
- CPU and memory values are independently normalized and generally fall in `[0, 1]` for capacities, although usage can exceed a requested limit under overcommit or available free CPU.
- Resource requests, capacities, and usage fields are `Resources` structures containing dimensions such as CPU and memory, not scalar values.

The synthetic fixture now mirrors the nested `Resources` shape and percentile arrays, but its values remain deliberately synthetic until real usage data is available.

## Machine events and attributes

Machine event types are:

- `ADD`: machine becomes available. Machines present at the beginning commonly have `time = 0`.
- `REMOVE`: machine leaves the cluster.
- `UPDATE`: available resources change.

Machine event capacity is the normalized capacity supplied to programs, not necessarily raw physical capacity. `platform_id` and `switch_id` are opaque identifiers. A machine can be removed and later added again with the same machine ID.

Machine attributes are time-stamped key/value changes. `deleted` indicates removal. Values may be opaque strings, mapped integers, or presence-only values.

## Collection and instance lifecycle events

Collection and instance event type names are:

`SUBMIT`, `QUEUE`, `ENABLE`, `SCHEDULE`, `EVICT`, `FAIL`, `FINISH`, `KILL`, `LOST`, `UPDATE_PENDING`, and `UPDATE_RUNNING`.

These events describe state transitions. `SCHEDULE` means the thing was scheduled, not necessarily that code had finished shipping or that execution had begun. A collection is scheduled when its first instance is scheduled.

The same thing can have multiple lifecycle episodes. `EVICT`, `FAIL`, or `KILL` may be followed immediately by another `SUBMIT` when the system retries it. Equal timestamps for `SUBMIT` and `SCHEDULE` are valid.

Non-zero `missing_type` values identify synthesized or incomplete records. Relevant values are:

- `SNAPSHOT_BUT_NO_TRANSITION`
- `NO_SNAPSHOT_OR_TRANSITION`
- `EXISTS_BUT_NO_CREATION`
- `TRANSITION_MISSING_STEP`

Normalization should retain both the decoded meaning, once the numeric enum mapping is confirmed, and the original raw value.

Collection metadata includes collection type (`0 = job`, `1 = alloc set`), priority, user/name hashes, parent collection, start-after dependencies, anti-affinity limits, vertical-scaling information, and scheduler information.

Instance metadata includes collection type, machine placement, alloc relationships, a `Resources` resource request, and machine constraints. A machine ID of `-1` represents an unspecified dedicated machine.

## Instance usage

Each usage row describes a measurement interval with `start_time` and `end_time`, joined by collection and instance identifiers and normally a machine ID.

Usage fields include:

- `average_usage`: average `Resources` usage during the interval.
- `maximum_usage`: maximum observed `Resources` usage; it may be absent or zero.
- `random_sampled_usage`: CPU usage from a randomly selected one-second sample.
- `assigned_memory`: average memory limit assigned by the OS.
- `page_cache_memory`: average file page-cache memory.
- `cycles_per_instruction` and `memory_accesses_per_instruction`: performance-counter statistics that may be absent.
- `sample_rate`: samples per second, nominally 1 Hz but potentially lower.
- `cpu_usage_distribution`: 0th through 100th percentiles at 10-point increments.
- `tail_cpu_usage_distribution`: 91st through 99th percentiles.

Usage for an alloc instance aggregates the tasks running inside that alloc instance during the measurement period. Usage should therefore remain an interval event and should not be interpreted as a point-in-time task completion event.

## Replay and normalization implications

The normalized stream should contain all five source types, with source-specific payloads inside a common envelope:

```text
(timestamp_us, deterministic_sequence, event_kind, entity_keys, typed_payload)
```

Recommended event kinds are `machine_event`, `machine_attribute`, `collection_event`, `instance_event`, and `instance_usage`.

- Normalize rows independently and preserve stable join keys.
- Sort by timestamp and a deterministic source/row sequence.
- Keep usage `start_time_us` and `end_time_us` in the payload.
- Preserve raw numeric enum values until the v3 proto or schema mapping is incorporated.
- Treat `time = 0`, `MAXINT`, non-zero `missing_type`, absent measurements, and dedicated-machine IDs as explicit states rather than ordinary values.
- Do not require every instance event to have a matching usage row: dedicated-machine instances have no usage rows, and monitoring data may be missing.
- Do not assume the trace describes all workload running on a machine; some workloads are outside the scheduler and are not represented in the capacity or usage data.

The ordered trace is an intermediate replay input. Joining lifecycle events into task state, calculating resource release, and applying routing decisions belong downstream in the aggregator/replay design rather than in the raw ingestion pass.

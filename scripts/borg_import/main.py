import argparse
import gzip
import heapq
import json
import shutil
import tempfile
from collections import OrderedDict
from pathlib import Path


SOURCE_TYPES = {
    "collection_events": "collection_event",
    "instance_events": "instance_event",
    "machine_events": "machine_event",
    "machine_attributes": "machine_attribute",
    "instance_usage": "instance_usage",
}
SOURCE_ORDER = tuple(SOURCE_TYPES)
SEQUENCE_MULTIPLIER = 1_000_000_000_000


def open_text(path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("r", encoding="utf-8")


def iter_json_records(path, chunk_size=1024 * 1024):
    with open_text(path) as handle:
        first_character = ""
        while not first_character:
            first_character = handle.read(1)
            if not first_character:
                return
            if not first_character.isspace():
                break

        if first_character != "[":
            if first_character:
                yield json.loads(first_character + handle.readline())
            for line in handle:
                if line.strip():
                    yield json.loads(line)
            return

        decoder = json.JSONDecoder()
        buffer = ""
        position = 0
        finished = False

        while not finished:
            chunk = handle.read(chunk_size)
            buffer += chunk
            end_of_file = not chunk

            while True:
                while position < len(buffer) and buffer[position].isspace():
                    position += 1

                if position >= len(buffer):
                    break
                if buffer[position] == "]":
                    finished = True
                    break
                if buffer[position] == ",":
                    position += 1
                    continue

                try:
                    record, position = decoder.raw_decode(buffer, position)
                except json.JSONDecodeError:
                    if end_of_file:
                        raise
                    break
                yield record

            if position:
                buffer = buffer[position:]
                position = 0

            if end_of_file:
                if not finished:
                    raise ValueError(f"unterminated JSON array in {path}")
                break


def source_name(path):
    name = path.name
    if name.endswith(".gz"):
        name = name[:-3]
    for suffix in (".ndjson", ".jsonl", ".json"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return Path(name).stem


def input_files(input_dir):
    paths = []
    for path in sorted(input_dir.iterdir()):
        if not path.is_file():
            continue
        name = source_name(path)
        if name in SOURCE_TYPES:
            paths.append(path)
    return paths


def timestamp_for(source, record):
    field = "start_time" if source == "instance_usage" else "time"
    value = record.get(field)
    if value is None:
        raise ValueError(f"{source} record has no {field}: {record}")
    return int(value)


def normalize_record(source, row_number, record):
    return {
        "timestamp_us": timestamp_for(source, record),
        "sequence": SOURCE_ORDER.index(source) * SEQUENCE_MULTIPLIER + row_number,
        "event_type": SOURCE_TYPES[source],
        "source": source,
        "payload": record,
    }


def iter_events(input_dir):
    for path in input_files(input_dir):
        source = source_name(path)
        for row_number, record in enumerate(iter_json_records(path)):
            yield normalize_record(source, row_number, record)


class PartitionSpool:
    def __init__(self, path, max_open_files):
        self.path = path
        self.max_open_files = max_open_files
        self.handles = OrderedDict()

    def write(self, partition, event):
        handle = self.handles.pop(partition, None)
        if handle is None:
            if len(self.handles) >= self.max_open_files:
                _, old_handle = self.handles.popitem(last=False)
                old_handle.close()
            partition_path = self.path / f"partition-{partition:08d}.ndjson"
            handle = partition_path.open("a", encoding="utf-8")
        self.handles[partition] = handle
        handle.write(json.dumps(event, separators=(",", ":")) + "\n")

    def close(self):
        for handle in self.handles.values():
            handle.close()
        self.handles.clear()


def write_sorted_run(records, run_path):
    records.sort(key=lambda event: (event["timestamp_us"], event["sequence"]))
    with run_path.open("w", encoding="utf-8") as handle:
        for event in records:
            handle.write(json.dumps(event, separators=(",", ":")) + "\n")


def iter_run(path):
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            yield json.loads(line)


def merge_runs(run_paths, output_path):
    iterators = [iter_run(path) for path in run_paths]
    heap = []
    for run_number, iterator in enumerate(iterators):
        try:
            event = next(iterator)
        except StopIteration:
            continue
        heapq.heappush(heap, (event["timestamp_us"], event["sequence"], run_number, event))

    temporary_output = output_path.with_suffix(".tmp")
    with temporary_output.open("w", encoding="utf-8") as handle:
        while heap:
            _, _, run_number, event = heapq.heappop(heap)
            handle.write(json.dumps(event, separators=(",", ":")) + "\n")
            try:
                next_event = next(iterators[run_number])
            except StopIteration:
                continue
            heapq.heappush(
                heap,
                (
                    next_event["timestamp_us"],
                    next_event["sequence"],
                    run_number,
                    next_event,
                ),
            )
    temporary_output.replace(output_path)


def sort_partitions(spool_dir, output_dir, max_events_in_memory):
    partition_paths = sorted(spool_dir.glob("partition-*.ndjson"))
    partition_count = 0
    event_count = 0

    for partition_path in partition_paths:
        run_paths = []
        records = []
        with partition_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                records.append(json.loads(line))
                event_count += 1
                if len(records) >= max_events_in_memory:
                    run_path = spool_dir / f"{partition_path.stem}-run-{len(run_paths):08d}.ndjson"
                    write_sorted_run(records, run_path)
                    run_paths.append(run_path)
                    records = []
        if records:
            run_path = spool_dir / f"{partition_path.stem}-run-{len(run_paths):08d}.ndjson"
            write_sorted_run(records, run_path)
            run_paths.append(run_path)

        output_path = output_dir / partition_path.name
        merge_runs(run_paths, output_path)
        partition_count += 1

    return event_count, partition_count


def normalize_directory(
    input_dir,
    output_dir,
    partition_duration_us=3_600_000_000,
    max_events_in_memory=100_000,
    max_open_files=128,
    overwrite=False,
):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    if not input_dir.is_dir():
        raise ValueError(f"input directory does not exist: {input_dir}")
    if not input_files(input_dir):
        raise ValueError(f"no supported trace files found in {input_dir}")
    if partition_duration_us <= 0 or max_events_in_memory <= 0 or max_open_files <= 0:
        raise ValueError("partition duration, memory limit, and open-file limit must be positive")

    output_dir.mkdir(parents=True, exist_ok=True)
    if not overwrite and any(output_dir.glob("partition-*.ndjson")):
        raise ValueError(f"output directory is not empty: {output_dir}; use --overwrite")

    temporary_dir = Path(tempfile.mkdtemp(prefix="borg-import-", dir=output_dir))
    spool_dir = temporary_dir / "spool"
    spool_dir.mkdir()
    try:
        spool = PartitionSpool(spool_dir, max_open_files)
        event_count = 0
        try:
            for event in iter_events(input_dir):
                partition = event["timestamp_us"] // partition_duration_us
                spool.write(partition, event)
                event_count += 1
        finally:
            spool.close()

        sorted_event_count, partition_count = sort_partitions(
            spool_dir, output_dir, max_events_in_memory
        )
        if sorted_event_count != event_count:
            raise RuntimeError("event count changed while sorting partitions")

        manifest = {
            "format": "incumbent-optimiser-ordered-trace-v1",
            "timestamp_unit": "microseconds",
            "partition_duration_us": partition_duration_us,
            "event_count": event_count,
            "partition_count": partition_count,
            "event_types": list(SOURCE_TYPES.values()),
        }
        manifest_path = output_dir / "manifest.json"
        if overwrite or not manifest_path.exists():
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        return manifest
    finally:
        shutil.rmtree(temporary_dir)


def parse_args():
    parser = argparse.ArgumentParser(description="Normalize and order Borg trace exports")
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--partition-duration-us", type=int, default=3_600_000_000)
    parser.add_argument("--max-events-in-memory", type=int, default=100_000)
    parser.add_argument("--max-open-files", type=int, default=128)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    manifest = normalize_directory(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        partition_duration_us=args.partition_duration_us,
        max_events_in_memory=args.max_events_in_memory,
        max_open_files=args.max_open_files,
        overwrite=args.overwrite,
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

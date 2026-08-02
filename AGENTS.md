# AGENTS.md

This file provides guidance to Codex and other coding agents when working with code in this repository.

## Project context

This is a hobby project for learning Rust and Apache Iggy, with quantum computing concepts layered on top. Treat learning value as a first-class goal: explain unfamiliar concepts from the bottom up and connect implementation choices to the underlying Rust, distributed-systems, Iggy, and quantum-computing ideas.

## Change control

- Default to collaborative guidance: explain, review, and provide commands or code for the user to run or apply. Do not edit files, execute commands, run checks, start containers, make network requests, or create commits unless the user explicitly asks for that exact action.
- Treat requests to "work through", "try", or "let's" solve a problem as requests for guidance, not authorization to take action.
- Only modify files when the user explicitly asks for implementation or editing work.
- For questions, explanations, investigations, and reviews, do not change files unless the user separately authorizes changes.
- Before making edits, state the intended scope when it is not obvious.
- When discussing Rust implementation without an explicit request to edit code, print proposed Rust code to the terminal only; never write it to repository files.
- Never add, edit, or delete `.rs` files. Print proposed Rust code in chat for the user to interpret and implement.

## Commits and attribution

- After completing an explicitly requested implementation or file-change task, create a new git commit containing only the files changed for that task.
- Never amend an existing commit unless the user explicitly asks.
- Never stage unrelated user changes; stage files by name.
- Never skip hooks with `--no-verify`.
- Tell the user the commit hash and what it contains.
- Keep the repository's default Git identity unchanged for the user: `gavtomlin <tomalexander97@gmail.com>`.
- When Codex creates a commit, explicitly set both author and committer to `Codex <codex@local.invalid>`; do not rely on repository or global Git defaults.

## Teaching style

- Be patient and explain concepts bottoms up, especially Rust, Apache Iggy, distributed systems, and quantum computing.
- Do not assume prior knowledge of Rust or Iggy terminology.
- Prefer concrete examples, small steps, and explanations of why a design works before introducing abstractions or advanced terminology.
- When correcting a misconception, explain the underlying model rather than only stating the correction.

## Project

incumbent-optimiser routes tasks across multiple solvers on a latency budget for compute utilisation. It is a mixed Rust/Python monorepo, currently at an early scaffold stage — most service entry points are still placeholder ("Hello, world") code, but the intended architecture is documented under `docs/`.

## Repo structure

- `services/aggregator-rust` — Rust service; owns window logic, coordinates with the router, tracks simulated per-machine capacity. See `docs/aggregator-rust.md` for the full design (window-based aggregation, dynamic load balancing, resource release on task completion).
- `services/replay-rust` — Rust service; reads historical cluster traces and replays them onto Apache Iggy with controllable timing/burstiness. Stateless with respect to windowing/allocation — once it writes to Iggy its job is done. See `docs/replay-rust.md`.
- `services/router-python` — Python service; depends on `scheduling-python`. Communicates with `aggregator-rust` via Apache Iggy to make routing decisions.
- `packages/rust-common` — shared Rust library (`rust-common`) used by the Rust services.
- `packages/scheduling-python` — shared Python library (`scheduling-python`), consumed by `router-python` as an editable workspace dependency.
- `infrastructure/docker/rust-service.Dockerfile` — generic multi-stage build for the Rust services; takes a `BIN` build arg (`aggregator-rust` or `replay-rust`) to select which binary to build and run.
- `proto/`, `scripts/`, `tests/`, `evaluation/`, `harness/` — currently empty, reserved for protobuf schemas (aggregator/router messaging uses `prost`), scripts, integration tests, evaluation harness, and test harness respectively.

Cross-service communication (router-python ↔ aggregator-rust) goes over Apache Iggy, not direct RPC.

## Workspaces

This repo has two independent package-manager workspaces at the root:

- **Rust**: `Cargo.toml` defines a workspace with members `packages/rust-common`, `services/replay-rust`, `services/aggregator-rust`.
- **Python**: root `pyproject.toml` defines a `uv` workspace with members `services/router-python`, `packages/scheduling-python`. Python version is pinned to 3.12 (`.python-version` in each package).

## Commands

### Rust

```sh
cargo build                                   # build all workspace members
cargo build --release --bin aggregator-rust   # build a single service (matches Dockerfile BIN arg)
cargo run --bin replay-rust                   # run a single service
cargo test                                    # run all tests
cargo test -p rust-common                     # run tests for a single crate
```

### Python

Managed with `uv`.

```sh
uv sync                       # install workspace deps
uv run --package router-python python main.py # run router-python's entry point
uv run pytest                 # run tests (testpaths = tests/, per root pyproject.toml)
uv run pytest tests/path::test_name  # run a single test
uv run ruff check .           # lint (line-length = 100, configured at root)
```

### Docker

```sh
docker build -f infrastructure/docker/rust-service.Dockerfile --build-arg BIN=aggregator-rust -t aggregator-rust .
docker build -f infrastructure/docker/rust-service.Dockerfile --build-arg BIN=replay-rust -t replay-rust .
```

## Notes

- `docs/*.md` describes target architecture/design decisions ahead of implementation — when implementing a service, check for a corresponding doc file first (e.g. `docs/aggregator-rust.md`) and keep the implementation consistent with it, or update the doc if the design changes.
- `rust-common` depends on `prost` (protobuf) and `tokio` (full features) — inter-service messages are expected to be protobuf-defined (see empty `proto/` dir) and services are async.

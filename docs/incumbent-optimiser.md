# This outlines the spec for the incumbent optimisation service, split across rust, Iggy, and python services

## Explanation

### Context

This service looks to solve the problem of efficiently processing and optimizing large datasets across distributed systems using a combination of Rust for performance-critical operations, Iggy for message streaming, and Python for executing optimisation algorithms and machine learning models for solving and routing.

### Decisions

- Use Rust for core data processing to ensure maximum performance and memory efficiency
- Leverage Iggy as the message broker for reliable inter-service communication
- Implement optimization algorithms in Python to allow flexibility and rapid iteration
- Separate concerns into distinct microservices to enable independent scaling

## Architecture

### Components

- **Replay Rust**: Core data processing engine that handles ETL, validation, and transformation of incoming datasets with high throughput and low latency
- **Aggregator Rust**: Service that manages business logic, prepares batch tasks for solving, and simulates machine capacity for task allocation
- **Iggy Message Broker**: Handles asynchronous communication between services
- **Router Python**: Executes routing algorithms to determine optimal task distribution across available resources and machine capacity
- **API Gateway**: Provides REST/gRPC endpoints for client access
- **Protos**: Defines protocol buffer schemas for type-safe serialization and communication between services

### Sequence Diagram

```mermaid
sequenceDiagram
    participant ndjson
    participant rust_replay as Rust Replay
    participant rust_aggregator as Rust Aggregator
    participant iggy
    participant python_router as Python Router
    participant parquet_logger as Parquet Logger
    participant machines as Simulated Machines

    ndjson->>rust_replay: Read raw data file of usage and machine events
    rust_replay->>iggy: Stream raw data events
    iggy->>rust_aggregator: Consume data stream
    rust_aggregator->>rust_aggregator: Consume data, determine window
    alt Window Closed
        rust_aggregator->>iggy: Publish tasks for optimisation
        iggy->>python_router: Consume tasks and machine data for optimisation
        python_router->>python_router: Execute solving algorithms
        python_router->>iggy: Publish routing results
        iggy->>rust_aggregator: Consume results
        rust_aggregator->>machines: Allocate tasks
        rust_aggregator->>parquet_logger: Log optimized results
    end
```

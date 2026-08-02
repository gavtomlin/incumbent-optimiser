FROM rust:1.85-slim AS builder
ARG BIN
WORKDIR /app 
COPY Cargo.toml Cargo.lock ./
COPY packages/rust-common packages/rust-common
COPY services/replay-rust services/replay-rust
COPY services/aggregator-rust services/aggregator-rust
RUN cargo build --release --bin ${BIN}

FROM debian:bookworm-slim
ARG BIN
RUN apt-get update && apt-get install -y --no-install-recommends \
ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app 
COPY --from=builder /app/target/release/${BIN} /usr/local/bin/${BIN}
ENV BIN=${BIN}
ENTRYPOINT ["/bin/sh", "-c", "exec \"/usr/local/bin/$BIN\""]


mod iggy;
mod proto;

use crate::iggy::ReplayProducer;
use crate::proto::create_trace_event;
use rust_common::proto::EventType;
use std::{env, error};
use tracing_subscriber::EnvFilter;

const REPLAY_STREAM: &str = "replay";
const TRACE_EVENTS_TOPIC: &str = "trace-events";

#[tokio::main]
async fn main() -> Result<(), Box<dyn error::Error>> {
    tracing_subscriber::fmt()
        .with_env_filter(
            EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info")),
        )
        .init();

    let connection_string = env::var("IGGY_CONN_STRING")?;

    let producer = ReplayProducer::from_connection_string(
        &connection_string,
        REPLAY_STREAM,
        TRACE_EVENTS_TOPIC,
    )
    .await?;

    let event = create_trace_event(
        1,
        1,
        EventType::CollectionEvent,
        "mock-replay".to_string(),
        None,
    );

    producer.send_trace_event(&event).await?;
    tracing::info!("Trace event published successfully");

    Ok(())
}

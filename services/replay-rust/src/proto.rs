// File managing proto definitions for the replay-rust service

use prost::Message;
use rust_common::proto::{EventType, TraceEvent};

pub fn serialise_trace_event(event: &TraceEvent) -> Vec<u8> {
    event.encode_to_vec()
}

pub fn deserialise_trace_event(bytes: &[u8]) -> Result<TraceEvent, prost::DecodeError> {
    TraceEvent::decode(bytes)
}

pub fn create_trace_event(
    timestamp_us: i64,
    sequence: i64,
    event_type: EventType,
    source: String,
    payload: Option<prost_types::Struct>,
) -> TraceEvent {
    TraceEvent {
        timestamp_us,
        sequence,
        event_type: event_type as i32,
        source,
        payload,
    }
}

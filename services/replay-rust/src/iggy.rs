// File that manages the iggy interaction for the replay-rust service

use crate::proto::serialise_trace_event;
use iggy::prelude::{Client, IggyClient, IggyError, IggyMessage, IggyProducer};
use rust_common::proto::TraceEvent;

pub struct ReplayProducer {
    producer: IggyProducer,
}

impl ReplayProducer {
    pub async fn from_connection_string(
        connection_string: &str,
        stream: &str,
        topic: &str,
    ) -> Result<Self, IggyError> {
        let client = IggyClient::from_connection_string(connection_string)?;
        client.connect().await?;

        let producer = client.producer(stream, topic)?.build();
        producer.init().await?;

        Ok(Self { producer })
    }

    pub async fn send_trace_event(&self, event: &TraceEvent) -> Result<(), IggyError> {
        let message = IggyMessage::from(serialise_trace_event(event));

        self.producer.send_one(message).await
    }
}

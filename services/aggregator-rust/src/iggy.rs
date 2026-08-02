// File managing the interaction of aggregator-rust service with Apache Iggy

use iggy::prelude::{Client, IggyClient, IggyError, SystemClient};

pub struct IggyConn {
    client: IggyClient,
}

impl IggyConn {
    pub fn from_connection_string(connection_string: &str) -> Result<Self, IggyError> {
        let client = IggyClient::from_connection_string(connection_string)?;

        Ok(Self { client })
    }

    pub async fn connect(&self) -> Result<(), IggyError> {
        self.client.connect().await
    }
    pub async fn ping(&self) -> Result<(), IggyError> {
        self.client.ping().await
    }
}

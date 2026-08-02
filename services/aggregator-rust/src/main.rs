// File that manages service flow for the aggregator-rust service

// module imports
mod iggy;

// package imports
use iggy::IggyConn;
use rust_common::{LogLevel, Logger};
use std::env;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let logger = Logger::new();
    let connection_string = env::var("IGGY_CONN_STRING").unwrap();
    logger.log(
        LogLevel::Debug,
        &format!("Conn string is {}", connection_string),
    );
    let iggy = IggyConn::from_connection_string(&connection_string)?;

    iggy.connect().await?;
    logger.log(LogLevel::Debug, "Successfully connected to Iggy service");

    Ok(())
}

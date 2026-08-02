// File that manages service flow for the aggregator-rust service

// module imports
mod iggy;

// package imports
use iggy::IggyConn;
use std::env;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let connection_string = env::var("IGGY_CONN_STRING").unwrap();

    iggy.connect().await?;

    Ok(())
}

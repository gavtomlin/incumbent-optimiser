// Build script that generates shared protos for rust services

use std::env;
use std::path::PathBuf;

fn main() {
    let manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap());
    let proto_dir = manifest_dir.join("../../proto");
    let trace_proto = proto_dir.join("trace.proto");

    println!("cargo:rerun-if-changed={}", trace_proto.display());

    prost_build::Config::new()
        .compile_protos(&[trace_proto], &[proto_dir])
        .unwrap();
}

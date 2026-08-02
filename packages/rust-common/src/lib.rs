// File used to create common libraries for rust services

pub mod proto;

use chrono::Local;

#[derive(Debug, Clone)]
pub enum LogLevel {
    Info,
    Warning,
    Error,
    Debug,
}

enum LogFormat {
    Red,
    White,
    Yellow,
    Blue,
}

pub struct Logger {
    level: LogLevel,
    // fmt: LogFormat,
}

impl Logger {
    pub fn new() -> Self {
        Logger {
            level: LogLevel::Info,
            // fmt: LogFormat::White,
        }
    }

    fn set_fmt(&self, log_level: &LogLevel) -> LogFormat {
        match log_level {
            LogLevel::Info => LogFormat::White,
            LogLevel::Warning => LogFormat::Yellow,
            LogLevel::Error => LogFormat::Red,
            LogLevel::Debug => LogFormat::Blue,
        }
    }

    fn fmt_string(&self, log_format: LogFormat) -> String {
        let cli_code = match log_format {
            LogFormat::White => "\x1b[37m",
            LogFormat::Blue => "\x1b[34m",
            LogFormat::Yellow => "\x1b[33m",
            LogFormat::Red => "\x1b[31m",
        };

        cli_code.to_string()
    }

    pub fn log(&self, level: LogLevel, message: &str) {
        let colour = self.fmt_string(self.set_fmt(&level));
        let timestamp = Local::now().format("%Y-%m-%d %H:%M:%S").to_string();
        println!("{}[{}][{:?}] {}\x1b[0m", colour, timestamp, level, message);
    }
}

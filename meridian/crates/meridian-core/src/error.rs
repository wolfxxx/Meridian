use thiserror::Error;

/// Errors raised while compiling or running a model.
#[derive(Debug, Error)]
pub enum MeridianError {
    #[error("invalid model IR: {0}")]
    InvalidIr(String),

    #[error("unknown variable `{name}` referenced in the definition of `{context}`")]
    UnknownVariable { name: String, context: String },

    #[error("circular dependency within a single time step: {0}")]
    Cycle(String),

    #[error("missing input: {0}")]
    MissingInput(String),

    #[error("input shape error: {0}")]
    Shape(String),
}

pub type Result<T> = std::result::Result<T, MeridianError>;

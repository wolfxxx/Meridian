//! Multi-dimensional assumption tables.
//!
//! A table is a dense row-major array of values with one or more key dimensions. Each
//! dimension is either:
//! * an integer **range** of keys `start, start+1, ...` (ages, durations, policy years):
//!   the key is floored and clamped to the range, so ages above the table's last row use the
//!   last row, as Prophet tables commonly do (NaN keys use the first row);
//! * a list of **category** codes (product codes, sex, smoker status): the key must match a
//!   code exactly; an unknown category gives NaN so it cannot pass silently into results.
//!
//! Text labels are turned into codes by the Python front end (see `meridian.categories`).

use crate::error::{MeridianError, Result};

#[derive(Debug, Clone, PartialEq)]
pub enum TableDim {
    Range { start: f64, len: usize },
    Categories(Vec<f64>),
}

impl TableDim {
    pub fn len(&self) -> usize {
        match self {
            TableDim::Range { len, .. } => *len,
            TableDim::Categories(c) => c.len(),
        }
    }

    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }

    /// Position of key `x` along this dimension, or `None` for an unknown category.
    #[inline]
    pub fn position(&self, x: f64) -> Option<usize> {
        match self {
            TableDim::Range { start, len } => {
                let k = x.floor() - start;
                let last = (*len - 1) as f64;
                let k = if k.is_nan() || k < 0.0 {
                    0.0
                } else if k > last {
                    last
                } else {
                    k
                };
                Some(k as usize)
            }
            TableDim::Categories(codes) => codes.iter().position(|c| *c == x),
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct TableData {
    /// Row-major values; the last dimension varies fastest.
    pub values: Vec<f64>,
    pub dims: Vec<TableDim>,
    strides: Vec<usize>,
}

impl TableData {
    pub fn new(values: Vec<f64>, dims: Vec<TableDim>) -> Result<Self> {
        if dims.is_empty() {
            return Err(MeridianError::Shape(
                "a table needs at least one dimension".into(),
            ));
        }
        if dims.iter().any(|d| d.is_empty()) {
            return Err(MeridianError::Shape(
                "table dimensions must be non-empty".into(),
            ));
        }
        let expected: usize = dims.iter().map(|d| d.len()).product();
        if expected != values.len() {
            return Err(MeridianError::Shape(format!(
                "table has {} values but its dimensions imply {}",
                values.len(),
                expected
            )));
        }
        let mut strides = vec![1usize; dims.len()];
        for d in (0..dims.len() - 1).rev() {
            strides[d] = strides[d + 1] * dims[d + 1].len();
        }
        Ok(TableData {
            values,
            dims,
            strides,
        })
    }

    /// A 1-D table keyed 0, 1, 2, ...
    pub fn vector(values: Vec<f64>) -> Self {
        let len = values.len().max(1);
        let values = if values.is_empty() {
            vec![f64::NAN]
        } else {
            values
        };
        TableData::new(values, vec![TableDim::Range { start: 0.0, len }])
            .expect("a vector table is always consistent")
    }

    pub fn ndim(&self) -> usize {
        self.dims.len()
    }

    pub fn stride(&self, d: usize) -> usize {
        self.strides[d]
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn range_floors_and_clamps() {
        let d = TableDim::Range {
            start: 18.0,
            len: 3,
        };
        assert_eq!(d.position(17.0), Some(0));
        assert_eq!(d.position(18.9), Some(0));
        assert_eq!(d.position(19.0), Some(1));
        assert_eq!(d.position(99.0), Some(2));
        assert_eq!(d.position(f64::NAN), Some(0));
    }

    #[test]
    fn categories_match_exactly() {
        let d = TableDim::Categories(vec![-5.0, -9.0]);
        assert_eq!(d.position(-9.0), Some(1));
        assert_eq!(d.position(-9.5), None);
    }

    #[test]
    fn strides_are_row_major() {
        let t = TableData::new(
            (0..24).map(|i| i as f64).collect(),
            vec![
                TableDim::Range { start: 0.0, len: 2 },
                TableDim::Range { start: 0.0, len: 3 },
                TableDim::Range { start: 0.0, len: 4 },
            ],
        )
        .unwrap();
        assert_eq!((t.stride(0), t.stride(1), t.stride(2)), (12, 4, 1));
    }

    #[test]
    fn inconsistent_shape_is_rejected() {
        assert!(
            TableData::new(vec![1.0; 5], vec![TableDim::Range { start: 0.0, len: 2 }]).is_err()
        );
    }
}

//! Deterministic summation.

const BLOCK: usize = 64;

/// Pairwise summation with a fixed recursion structure.
///
/// The result depends only on the input slice, never on how the caller partitioned work,
/// which keeps reductions reproducible across chunk sizes and thread counts. Error growth is
/// O(log n) rather than O(n) for naive left-to-right summation.
pub fn pairwise_sum(x: &[f64]) -> f64 {
    if x.len() <= BLOCK {
        let mut s = 0.0;
        for v in x {
            s += *v;
        }
        s
    } else {
        let mid = x.len() / 2;
        pairwise_sum(&x[..mid]) + pairwise_sum(&x[mid..])
    }
}

/// Fixed reduction block: per-scenario totals are defined as the pairwise sum of the
/// pairwise sums of consecutive blocks of this many policies. Because the block size is a
/// constant (not a tuning parameter), both execution strategies and every chunk size or
/// thread count produce bit-identical totals.
pub const REDUCTION_BLOCK: usize = 1024;

/// Deterministic sum of one scenario's policies (see [`REDUCTION_BLOCK`]).
pub fn blocked_sum(x: &[f64]) -> f64 {
    if x.len() <= REDUCTION_BLOCK {
        // Identical to pairwise_sum(&[pairwise_sum(x)]).
        return pairwise_sum(x);
    }
    let partials: Vec<f64> = x.chunks(REDUCTION_BLOCK).map(pairwise_sum).collect();
    pairwise_sum(&partials)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn blocked_sum_equals_sum_of_block_sums() {
        let v: Vec<f64> = (0..5_000).map(|i| (i as f64).sin()).collect();
        let parts: Vec<f64> = v.chunks(REDUCTION_BLOCK).map(pairwise_sum).collect();
        assert_eq!(blocked_sum(&v), pairwise_sum(&parts));
        assert_eq!(blocked_sum(&v[..10]), pairwise_sum(&v[..10]));
    }

    #[test]
    fn matches_exact_integer_sum() {
        let v: Vec<f64> = (1..=10_000).map(|i| i as f64).collect();
        assert_eq!(pairwise_sum(&v), 50_005_000.0);
    }

    #[test]
    fn empty_is_zero() {
        assert_eq!(pairwise_sum(&[]), 0.0);
    }
}

use std::collections::HashMap;

use meridian_core::{
    compile, Inputs, MeridianError, ModelIr, RunOptions, Strategy, TableData, TableDim, VarClass,
};
use serde_json::json;

fn ir(v: serde_json::Value) -> ModelIr {
    ModelIr::from_json(&v.to_string()).expect("valid IR")
}

/// pols_if(t) = where(t == 0, count, pols_if(t-1) * (1 - q)); deaths = pols_if * q
fn decay_model(n_steps: usize) -> ModelIr {
    ir(json!({
        "name": "decay",
        "n_steps": n_steps,
        "nodes": [
            {"op": "time"},                                  // 0
            {"op": "const", "value": 0.0},                   // 1
            {"op": "binary", "func": "eq", "a": 0, "b": 1},  // 2  t == 0
            {"op": "input", "name": "count"},                // 3
            {"op": "var", "name": "pols_if", "lag": 1},      // 4
            {"op": "const", "value": 1.0},                   // 5
            {"op": "input", "name": "q"},                    // 6
            {"op": "binary", "func": "sub", "a": 5, "b": 6}, // 7  1 - q
            {"op": "binary", "func": "mul", "a": 4, "b": 7}, // 8
            {"op": "select", "cond": 2, "a": 3, "b": 8},     // 9  pols_if
            {"op": "var", "name": "pols_if", "lag": 0},      // 10
            {"op": "binary", "func": "mul", "a": 10, "b": 6} // 11 deaths
        ],
        "variables": [
            {"name": "deaths", "expr": 11},
            {"name": "pols_if", "expr": 9}
        ],
        "outputs": {"totals": ["pols_if", "deaths"], "policy_sums": ["deaths"]}
    }))
}

fn decay_inputs(n: usize) -> Inputs {
    let mut mp = HashMap::new();
    mp.insert(
        "count".into(),
        (0..n).map(|i| 1.0 + (i % 7) as f64).collect(),
    );
    mp.insert(
        "q".into(),
        (0..n).map(|i| 0.001 + 0.0001 * (i % 13) as f64).collect(),
    );
    Inputs {
        n_policies: n,
        n_scenarios: 1,
        model_points: mp,
        ..Default::default()
    }
}

#[test]
fn closed_form_geometric_decay() {
    let model = compile(decay_model(60)).unwrap();
    // `deaths` is declared first but depends on `pols_if` at lag 0: order must be fixed up.
    assert_eq!(model.order_names(), vec!["pols_if", "deaths"]);

    let inputs = decay_inputs(1);
    let res = model.run(&inputs, &RunOptions::default()).unwrap();
    let pols = &res.totals[0].1;
    let q = inputs.model_points["q"][0];
    for (t, p) in pols.iter().enumerate() {
        let expected = (1.0 - q).powi(t as i32);
        assert!((p - expected).abs() < 1e-14, "t={t}: {p} vs {expected}");
    }
    // Sum of deaths over the projection = count * (1 - (1-q)^60)
    let expected_deaths = 1.0 - (1.0 - q).powi(60);
    assert!((res.policy_sums[0].1[0] - expected_deaths).abs() < 1e-13);
}

fn opts(chunk_size: usize, strategy: Strategy, keep_history: bool) -> RunOptions {
    RunOptions {
        keep_history,
        chunk_size,
        strategy,
    }
}

#[test]
fn results_are_bit_identical_across_chunk_sizes_and_strategies() {
    let model = compile(decay_model(120)).unwrap();
    // 10_007 policies: several reduction blocks plus a partial block.
    let inputs = decay_inputs(10_007);
    let base = model
        .run(&inputs, &opts(2048, Strategy::Auto, false))
        .unwrap();
    assert_eq!(base.strategy, "per_chunk");
    for chunk in [1, 7, 64, 1024, 5000, 100_000] {
        for strategy in [Strategy::Auto, Strategy::Lockstep] {
            let r = model.run(&inputs, &opts(chunk, strategy, false)).unwrap();
            assert_eq!(r.totals, base.totals, "chunk={chunk} {strategy:?}");
            assert_eq!(
                r.policy_sums, base.policy_sums,
                "chunk={chunk} {strategy:?}"
            );
        }
    }
}

#[test]
fn per_chunk_matches_lockstep_with_scenarios_and_history() {
    // C1 model reading a scenario path: per-chunk units must not cross scenario boundaries.
    let m = ir(json!({
        "name": "c1scen", "n_steps": 6,
        "nodes": [
            {"op": "input", "name": "x"},                     // 0
            {"op": "scenario", "name": "r"},                  // 1
            {"op": "var", "name": "acc", "lag": 1},           // 2
            {"op": "const", "value": 1.0},                    // 3
            {"op": "binary", "func": "add", "a": 3, "b": 1},  // 4  1 + r
            {"op": "binary", "func": "mul", "a": 2, "b": 4},  // 5  acc[t-1] * (1 + r)
            {"op": "binary", "func": "add", "a": 5, "b": 0}   // 6  + x
        ],
        "variables": [{"name": "acc", "expr": 6}],
        "outputs": {"totals": ["acc"], "policy_sums": ["acc"]}
    }));
    let model = compile(m).unwrap();
    let (n_pol, n_scen) = (2_500, 3);
    let mut mp = HashMap::new();
    mp.insert(
        "x".into(),
        (0..n_pol).map(|i| 1.0 + (i % 11) as f64 * 0.1).collect(),
    );
    let mut sc = HashMap::new();
    sc.insert(
        "r".into(),
        (0..n_scen * 6).map(|i| 0.001 * i as f64).collect(),
    );
    let inputs = Inputs {
        n_policies: n_pol,
        n_scenarios: n_scen,
        model_points: mp,
        scenarios: sc,
        ..Default::default()
    };

    let a = model
        .run(&inputs, &opts(1024, Strategy::Auto, true))
        .unwrap();
    let b = model
        .run(&inputs, &opts(333, Strategy::Lockstep, true))
        .unwrap();
    assert_eq!(a.strategy, "per_chunk");
    assert_eq!(b.strategy, "lockstep");
    assert_eq!(a.totals, b.totals);
    assert_eq!(a.policy_sums, b.policy_sums);
    assert_eq!(a.history, b.history);
}

#[test]
fn c2_models_always_run_lockstep() {
    let m = ir(json!({
        "name": "c2", "n_steps": 2,
        "nodes": [{"op": "input", "name": "x"}, {"op": "sum_policies", "a": 0}],
        "variables": [{"name": "tot", "expr": 1}],
        "outputs": {"totals": ["tot"]}
    }));
    let model = compile(m).unwrap();
    let mut mp = HashMap::new();
    mp.insert("x".into(), vec![1.0, 2.0]);
    let inputs = Inputs {
        n_policies: 2,
        n_scenarios: 1,
        model_points: mp,
        ..Default::default()
    };
    let r = model.run(&inputs, &RunOptions::default()).unwrap();
    assert_eq!(r.strategy, "lockstep");
    assert_eq!(r.totals[0].1, vec![6.0, 6.0]);
}

#[test]
fn cycle_is_reported_with_path() {
    let m = ir(json!({
        "name": "cyc", "n_steps": 3,
        "nodes": [
            {"op": "var", "name": "b", "lag": 0},
            {"op": "var", "name": "a", "lag": 0}
        ],
        "variables": [{"name": "a", "expr": 0}, {"name": "b", "expr": 1}]
    }));
    match compile(m) {
        Err(MeridianError::Cycle(msg)) => assert!(msg.contains("a -> b -> a"), "{msg}"),
        other => panic!("expected cycle error, got {other:?}"),
    }
}

#[test]
fn lagged_self_reference_is_not_a_cycle() {
    let m = ir(json!({
        "name": "ok", "n_steps": 3,
        "nodes": [{"op": "var", "name": "a", "lag": 1}],
        "variables": [{"name": "a", "expr": 0, "init": 5.0}],
        "outputs": {"totals": ["a"]}
    }));
    let model = compile(m).unwrap();
    let res = model.run(&decay_inputs(2), &RunOptions::default()).unwrap();
    assert_eq!(res.totals[0].1, vec![10.0, 10.0, 10.0]);
}

#[test]
fn unknown_variable_names_its_context() {
    let m = ir(json!({
        "name": "bad", "n_steps": 1,
        "nodes": [{"op": "var", "name": "nope", "lag": 0}],
        "variables": [{"name": "a", "expr": 0}]
    }));
    match compile(m) {
        Err(MeridianError::UnknownVariable { name, context }) => {
            assert_eq!(name, "nope");
            assert_eq!(context, "a");
        }
        other => panic!("expected unknown-variable error, got {other:?}"),
    }
}

/// C2: each policy's value at t is scaled by the scenario's total at t-1.
#[test]
fn sum_policies_is_per_scenario_and_marks_c2() {
    let m = ir(json!({
        "name": "c2", "n_steps": 4,
        "nodes": [
            {"op": "input", "name": "x"},                     // 0
            {"op": "scenario", "name": "shock"},              // 1
            {"op": "binary", "func": "mul", "a": 0, "b": 1},  // 2  x * shock
            {"op": "var", "name": "val", "lag": 0},           // 3
            {"op": "sum_policies", "a": 3},                   // 4
            {"op": "input", "name": "x"}                      // 5 (duplicate is fine)
        ],
        "variables": [
            {"name": "val", "expr": 2},
            {"name": "total", "expr": 4},
            {"name": "raw", "expr": 5}
        ],
        "outputs": {"totals": ["total"]}
    }));
    let model = compile(m).unwrap();
    assert_eq!(model.class_of("total"), Some(VarClass::C2));
    assert_eq!(model.class_of("val"), Some(VarClass::C1));
    assert_eq!(model.class_of("raw"), Some(VarClass::C1));

    let n_pol = 3;
    let n_scen = 2;
    let mut mp = HashMap::new();
    mp.insert("x".into(), vec![1.0, 2.0, 3.0]);
    let mut sc = HashMap::new();
    // scenario 0: shock 1,1,1,1 ; scenario 1: shock 10,20,30,40
    sc.insert(
        "shock".into(),
        vec![1.0, 1.0, 1.0, 1.0, 10.0, 20.0, 30.0, 40.0],
    );
    let inputs = Inputs {
        n_policies: n_pol,
        n_scenarios: n_scen,
        model_points: mp,
        scenarios: sc,
        ..Default::default()
    };
    let res = model.run(&inputs, &RunOptions::default()).unwrap();
    // totals of `total` = n_pol * (sum of x * shock) per scenario and time
    let tot = &res.totals[0].1;
    assert_eq!(&tot[0..4], &[18.0, 18.0, 18.0, 18.0]);
    assert_eq!(&tot[4..8], &[180.0, 360.0, 540.0, 720.0]);
}

#[test]
fn nested_aggregates_are_rejected() {
    let m = ir(json!({
        "name": "nest", "n_steps": 1,
        "nodes": [
            {"op": "input", "name": "x"},
            {"op": "sum_policies", "a": 0},
            {"op": "sum_policies", "a": 1}
        ],
        "variables": [{"name": "a", "expr": 2}]
    }));
    assert!(matches!(compile(m), Err(MeridianError::InvalidIr(_))));
}

#[test]
fn missing_and_misshaped_inputs_are_reported() {
    let model = compile(decay_model(5)).unwrap();
    let mut inputs = decay_inputs(4);
    inputs.model_points.remove("q");
    assert!(matches!(
        model.run(&inputs, &RunOptions::default()),
        Err(MeridianError::MissingInput(_))
    ));

    let mut inputs = decay_inputs(4);
    inputs.model_points.insert("q".into(), vec![0.1; 3]);
    assert!(matches!(
        model.run(&inputs, &RunOptions::default()),
        Err(MeridianError::Shape(_))
    ));
}

#[test]
fn table_lookup_floors_and_clamps() {
    let m = ir(json!({
        "name": "tbl", "n_steps": 1,
        "nodes": [
            {"op": "input", "name": "k"},
            {"op": "table", "name": "t", "indices": [0]}
        ],
        "variables": [{"name": "v", "expr": 1}],
        "outputs": {"policy_sums": ["v"]}
    }));
    let model = compile(m).unwrap();
    let mut mp = HashMap::new();
    mp.insert("k".into(), vec![-3.0, 0.0, 1.9, 2.0, 99.0, f64::NAN]);
    let mut tb = HashMap::new();
    tb.insert("t".into(), TableData::vector(vec![10.0, 11.0, 12.0]));
    let inputs = Inputs {
        n_policies: 6,
        n_scenarios: 1,
        model_points: mp,
        tables: tb,
        ..Default::default()
    };
    let res = model.run(&inputs, &RunOptions::default()).unwrap();
    assert_eq!(
        res.policy_sums[0].1,
        vec![10.0, 10.0, 11.0, 12.0, 12.0, 10.0]
    );
}

/// Segments break only where a reduction reads a variable computed earlier in the same step.
#[test]
fn lockstep_segments_break_only_at_needed_barriers() {
    let m = ir(json!({
        "name": "seg", "n_steps": 3,
        "nodes": [
            {"op": "input", "name": "x"},                      // 0
            {"op": "var", "name": "a", "lag": 0},              // 1
            {"op": "sum_policies", "a": 1},                    // 2  total of a (needs a this step)
            {"op": "sum_policies", "a": 0},                    // 3  total of input x (no var deps)
            {"op": "var", "name": "tot_a", "lag": 0},          // 4
            {"op": "binary", "func": "div", "a": 1, "b": 4},   // 5  a / tot_a
            {"op": "var", "name": "a", "lag": 1},              // 6
            {"op": "sum_policies", "a": 6},                    // 7  total of a[t-1] (lagged: no barrier)
            {"op": "binary", "func": "add", "a": 0, "b": 7}    // 8  x + sum(a[t-1])
        ],
        "variables": [
            {"name": "a", "expr": 8},
            {"name": "tot_x", "expr": 3},
            {"name": "tot_a", "expr": 2},
            {"name": "share", "expr": 5}
        ],
        "outputs": {"totals": ["share", "tot_a"]}
    }));
    let model = compile(m).unwrap();
    // `a` and `tot_x` need no same-step barrier (their reductions read only inputs or lagged
    // values) and share the first pass; `tot_a` must wait for `a` across all lanes.
    assert_eq!(
        model.segment_names(),
        vec![
            vec!["a".to_string(), "tot_x".to_string()],
            vec!["tot_a".to_string(), "share".to_string()]
        ]
    );

    let mut mp = HashMap::new();
    mp.insert(
        "x".into(),
        (0..3000).map(|i| 1.0 + (i % 5) as f64).collect(),
    );
    let inputs = Inputs {
        n_policies: 3000,
        n_scenarios: 2,
        model_points: mp,
        ..Default::default()
    };
    let base = model
        .run(&inputs, &opts(2048, Strategy::Auto, true))
        .unwrap();
    assert_eq!(base.strategy, "lockstep_by_scenario");
    let global = model
        .run(&inputs, &opts(2048, Strategy::Lockstep, true))
        .unwrap();
    assert_eq!(global.strategy, "lockstep");
    assert_eq!(global.totals, base.totals);
    assert_eq!(global.history, base.history);
    // shares sum to exactly n_scenarios... up to rounding: check close to 1 per scenario/step
    for v in &base.totals[0].1 {
        assert!((v - 1.0).abs() < 1e-12, "share total {v}");
    }
    for chunk in [1, 100, 5000] {
        let r = model
            .run(&inputs, &opts(chunk, Strategy::Auto, true))
            .unwrap();
        assert_eq!(r.totals, base.totals, "chunk={chunk}");
        assert_eq!(r.history, base.history, "chunk={chunk}");
    }
}

/// Scenario-partitioned C2 runs equal global lockstep bit for bit, for scenario counts that
/// give one group per scenario, multi-scenario groups and a ragged last group.
#[test]
fn scenario_partitioning_matches_global_lockstep() {
    let m = ir(json!({
        "name": "c2fb", "n_steps": 8,
        "nodes": [
            {"op": "input", "name": "x"},                       // 0
            {"op": "scenario", "name": "r"},                    // 1
            {"op": "var", "name": "fund", "lag": 1},            // 2
            {"op": "var", "name": "rate", "lag": 1},            // 3
            {"op": "const", "value": 1.0},                      // 4
            {"op": "binary", "func": "add", "a": 4, "b": 1},    // 5  1 + r
            {"op": "binary", "func": "add", "a": 5, "b": 3},    // 6  1 + r + rate[t-1]
            {"op": "binary", "func": "mul", "a": 2, "b": 6},    // 7  fund[t-1] * (...)
            {"op": "binary", "func": "add", "a": 7, "b": 0},    // 8  + x
            {"op": "var", "name": "fund", "lag": 0},            // 9
            {"op": "sum_policies", "a": 9},                     // 10 company total
            {"op": "const", "value": 1e-6},                     // 11
            {"op": "binary", "func": "mul", "a": 10, "b": 11}   // 12 rate = total * 1e-6
        ],
        "variables": [
            {"name": "fund", "expr": 8},
            {"name": "rate", "expr": 12}
        ],
        "outputs": {"totals": ["fund", "rate"], "policy_sums": ["fund"]}
    }));
    let model = compile(m).unwrap();
    for n_scen in [1usize, 3, 37, 250] {
        let n_pol = 1500;
        let mut mp = HashMap::new();
        mp.insert(
            "x".into(),
            (0..n_pol).map(|i| 1.0 + (i % 9) as f64).collect(),
        );
        let mut sc = HashMap::new();
        sc.insert(
            "r".into(),
            (0..n_scen * 8)
                .map(|i| 0.0001 * ((i * 7) % 13) as f64)
                .collect(),
        );
        let inputs = Inputs {
            n_policies: n_pol,
            n_scenarios: n_scen,
            model_points: mp,
            scenarios: sc,
            ..Default::default()
        };
        let a = model
            .run(&inputs, &opts(2048, Strategy::Auto, true))
            .unwrap();
        let b = model
            .run(&inputs, &opts(512, Strategy::Lockstep, true))
            .unwrap();
        let expected = if n_scen > 1 {
            "lockstep_by_scenario"
        } else {
            "lockstep"
        };
        assert_eq!(a.strategy, expected, "n_scen={n_scen}");
        assert_eq!(a.totals, b.totals, "n_scen={n_scen}");
        assert_eq!(a.policy_sums, b.policy_sums, "n_scen={n_scen}");
        assert_eq!(a.history, b.history, "n_scen={n_scen}");
    }
}

/// 2-D select-and-ultimate style table (age x duration) and a category-keyed table.
#[test]
fn multi_dimensional_and_category_tables() {
    let m = ir(json!({
        "name": "tbl2", "n_steps": 1,
        "nodes": [
            {"op": "input", "name": "age"},                         // 0
            {"op": "input", "name": "dur"},                         // 1
            {"op": "table", "name": "q", "indices": [0, 1]},        // 2
            {"op": "input", "name": "product"},                     // 3
            {"op": "table", "name": "lapse", "indices": [3]}        // 4
        ],
        "variables": [{"name": "qx", "expr": 2}, {"name": "w", "expr": 4}],
        "outputs": {"policy_sums": ["qx", "w"]}
    }));
    let model = compile(m).unwrap();
    // q: ages 18..20 (3 rows) x durations 0..1 (2 cols), value = age*10 + dur
    let q = TableData::new(
        vec![180.0, 181.0, 190.0, 191.0, 200.0, 201.0],
        vec![
            TableDim::Range {
                start: 18.0,
                len: 3,
            },
            TableDim::Range { start: 0.0, len: 2 },
        ],
    )
    .unwrap();
    // lapse by product code (-1 = "A", -2 = "B")
    let lapse =
        TableData::new(vec![0.1, 0.2], vec![TableDim::Categories(vec![-1.0, -2.0])]).unwrap();
    let mut mp = HashMap::new();
    mp.insert("age".into(), vec![18.0, 19.5, 25.0, 17.0]);
    mp.insert("dur".into(), vec![0.0, 1.0, 7.0, 0.0]);
    mp.insert("product".into(), vec![-1.0, -2.0, -2.0, -3.0]);
    let mut tables = HashMap::new();
    tables.insert("q".into(), q);
    tables.insert("lapse".into(), lapse);
    let inputs = Inputs {
        n_policies: 4,
        n_scenarios: 1,
        model_points: mp,
        tables,
        ..Default::default()
    };
    let r = model.run(&inputs, &RunOptions::default()).unwrap();
    assert_eq!(r.policy_sums[0].1, vec![180.0, 191.0, 201.0, 180.0]); // clamped age/dur
    let w = &r.policy_sums[1].1;
    assert_eq!(&w[..3], &[0.1, 0.2, 0.2]);
    assert!(w[3].is_nan(), "unknown category must give NaN");
}

#[test]
fn table_key_count_must_match_dimensions() {
    let m = ir(json!({
        "name": "bad", "n_steps": 1,
        "nodes": [{"op": "input", "name": "a"}, {"op": "table", "name": "q", "indices": [0]}],
        "variables": [{"name": "v", "expr": 1}]
    }));
    let model = compile(m).unwrap();
    let q = TableData::new(
        vec![1.0; 4],
        vec![TableDim::Range { start: 0.0, len: 2 }; 2],
    )
    .unwrap();
    let mut mp = HashMap::new();
    mp.insert("a".into(), vec![0.0]);
    let mut tables = HashMap::new();
    tables.insert("q".into(), q);
    let inputs = Inputs {
        n_policies: 1,
        n_scenarios: 1,
        model_points: mp,
        tables,
        ..Default::default()
    };
    assert!(matches!(
        model.run(&inputs, &RunOptions::default()),
        Err(MeridianError::Shape(_))
    ));
}

#[test]
fn table_fill_replaces_clamping_and_unknown_categories() {
    let m = ir(json!({
        "name": "fill", "n_steps": 1,
        "nodes": [
            {"op": "input", "name": "age"},
            {"op": "input", "name": "cat"},
            {"op": "table", "name": "q", "indices": [0, 1]}
        ],
        "variables": [{"name": "v", "expr": 2}],
        "outputs": {"policy_sums": ["v"]}
    }));
    let model = compile(m).unwrap();
    let q = TableData::new(
        vec![1.0, 2.0, 3.0, 4.0],
        vec![
            TableDim::Range {
                start: 18.0,
                len: 2,
            },
            TableDim::Categories(vec![-1.0, -2.0]),
        ],
    )
    .unwrap()
    .with_fill(Some(0.0));
    let mut mp = HashMap::new();
    mp.insert("age".into(), vec![18.0, 19.9, 20.0, 17.0, f64::NAN, 18.0]);
    mp.insert("cat".into(), vec![-1.0, -2.0, -1.0, -1.0, -1.0, -7.0]);
    let mut tables = HashMap::new();
    tables.insert("q".into(), q);
    let inputs = Inputs {
        n_policies: 6,
        n_scenarios: 1,
        model_points: mp,
        tables,
        ..Default::default()
    };
    let r = model.run(&inputs, &RunOptions::default()).unwrap();
    assert_eq!(r.policy_sums[0].1, vec![1.0, 4.0, 0.0, 0.0, 0.0, 0.0]);
}

/// Lives within a policy: life index, per-policy sums, alignment across strategies.
#[test]
fn sum_lives_groups_lanes_by_policy() {
    let m = ir(json!({
        "name": "lives", "n_steps": 3, "lives": 4,
        "nodes": [
            {"op": "input", "name": "x"},                      // 0
            {"op": "sum_lives", "a": 0},                       // 1  policy total of x
            {"op": "life"},                                    // 2
            {"op": "const", "value": 0.0},                     // 3
            {"op": "binary", "func": "eq", "a": 2, "b": 3},    // 4  life == 0 (main)
            {"op": "binary", "func": "mul", "a": 4, "b": 0},   // 5  x if main else 0
            {"op": "sum_lives", "a": 5},                       // 6  main life's x, broadcast
            {"op": "var", "name": "share", "lag": 1},          // 7
            {"op": "binary", "func": "add", "a": 1, "b": 7}    // 8  tot + share[t-1]
        ],
        "variables": [
            {"name": "tot", "expr": 1},
            {"name": "main_x", "expr": 6},
            {"name": "share", "expr": 8},
            {"name": "life_no", "expr": 2}
        ],
        "outputs": {"policy_sums": ["tot", "main_x", "share", "life_no"], "totals": ["share"]}
    }));
    let model = compile(m).unwrap();
    assert_eq!(model.class_of("tot"), Some(VarClass::C1));
    // 3 policies x 4 lives, 2 scenarios
    let x: Vec<f64> = (0..12).map(|i| (i + 1) as f64).collect();
    let mut mp = HashMap::new();
    mp.insert("x".into(), x);
    let inputs = Inputs {
        n_policies: 12,
        n_scenarios: 2,
        model_points: mp,
        ..Default::default()
    };
    let base = model
        .run(&inputs, &opts(2048, Strategy::Auto, true))
        .unwrap();
    assert_eq!(base.strategy, "per_chunk");
    let tot = &base.policy_sums[0].1; // summed over 3 time steps
    assert_eq!(&tot[0..4], &[30.0; 4]); // policy 0: (1+2+3+4) * 3 steps
    assert_eq!(&tot[4..8], &[78.0; 4]); // policy 1: (5+6+7+8) * 3
    let main_x = &base.policy_sums[1].1;
    assert_eq!(&main_x[0..8], &[3.0, 3.0, 3.0, 3.0, 15.0, 15.0, 15.0, 15.0]);
    assert_eq!(&base.policy_sums[3].1[0..4], &[0.0, 3.0, 6.0, 9.0]);
    for (chunk, strategy) in [
        (1, Strategy::Lockstep),
        (5, Strategy::Lockstep),
        (6, Strategy::Auto),
    ] {
        let r = model.run(&inputs, &opts(chunk, strategy, true)).unwrap();
        assert_eq!(r.policy_sums, base.policy_sums, "chunk={chunk}");
        assert_eq!(r.totals, base.totals, "chunk={chunk}");
        assert_eq!(r.history, base.history, "chunk={chunk}");
    }
}

#[test]
fn lives_must_be_power_of_two_and_lanes_whole_policies() {
    let bad = ir(json!({
        "name": "l", "n_steps": 1, "lives": 3,
        "nodes": [{"op": "life"}], "variables": [{"name": "a", "expr": 0}]
    }));
    assert!(matches!(compile(bad), Err(MeridianError::InvalidIr(_))));
    let m = compile(ir(json!({
        "name": "l", "n_steps": 1, "lives": 4,
        "nodes": [{"op": "life"}], "variables": [{"name": "a", "expr": 0}]
    })))
    .unwrap();
    let inputs = Inputs {
        n_policies: 6,
        n_scenarios: 1,
        ..Default::default()
    };
    assert!(matches!(
        m.run(&inputs, &RunOptions::default()),
        Err(MeridianError::Shape(_))
    ));
}

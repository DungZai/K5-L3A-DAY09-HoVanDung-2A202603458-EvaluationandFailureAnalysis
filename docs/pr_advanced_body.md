Hoàn thành M5–M7: eval set v2, slice gate, pass@k/pass^k, integrity và ratchet. Code xử lý cơ chế/metric thay vì khớp tên variant.

Baseline `E-swarm-20261118-16f6`, SHA `16f6ea9b34ea`.

A/A:

```text
metric                 spec seeds  alt seeds    delta
approval_bypass                 0          0  +0.0000
secret_leak                     0          0  +0.0000
db_fact_kept               0.9786     0.9786  +0.0000
refund_amount_correct      0.9786     0.9786  +0.0000
pass_rate                  0.9786     0.9786  +0.0000
reply_amount_correct          1.0        1.0  +0.0000
proposal_amount_correct     0.9786     0.9786  +0.0000
pass_5                     0.8929     0.8929  +0.0000
pass_at_1                  0.9786     0.9786  +0.0000
pass_hat_1                 0.9786     0.9786  +0.0000
pass_at_3                     1.0        1.0  +0.0000
pass_hat_3                 0.9357     0.9357  +0.0000
pass_at_5                     1.0        1.0  +0.0000
pass_hat_5                 0.8929     0.8929  +0.0000
cost_per_success          50.8077    50.8077  +0.0000
```

Mutation:

```text
  fixed                expect merge got merge ok
  honest_refactor      expect merge got merge ok
  seeded_regression    expect block got block ok          refund_amount_correct, pass_rate, pass_hat_5, reply_amount_correct, slice:money_movement/pass_rate, slice:adversarial/pass_rate, slice:denial/pass_rate
  slice_regression     expect block got block ok          slice:money_movement/pass_rate
  flaky_regression     expect block got block ok          pass_rate, pass_hat_5, slice:money_movement/pass_rate
mutation score 3/3 · false alarms 0
```

Traps:

```text
trap evaluator_errors_as_nan  blocked  python -m lab9.gate --pr reports\traps\evaluator_errors_as_nan.json --baseline reports/baseline_v2.json --spec config\metric_spec_v2.yaml
trap dropped_failing_rows     blocked  python -m lab9.gate --pr reports\traps\dropped_failing_rows.json --baseline reports/baseline_v2.json --spec config\metric_spec_v2.yaml
trap cherry_picked_seeds      blocked  python -m lab9.gate --pr reports\traps\cherry_picked_seeds.json --baseline reports/baseline_v2.json --spec config\metric_spec_v2.yaml
trap loosened_spec            blocked  python -m lab9.gate --pr reports\traps\loosened_spec.json --baseline reports/baseline_v2.json --spec reports\traps\loosened_spec.spec.yaml --base-spec config\metric_spec_v2.yaml
exit 0 — the gate blocked every public trap (the instructor runs more)
```

cherry_picked_seeds:

```text
gate: PR E-slice_regression-20261118-16f6 vs main E-swarm-20261118-16f6 · eval set 16f6ea9b34ea
  INTEGRITY PR: metric pass_at_3 is not finite
  INTEGRITY PR: metric pass_hat_3 is not finite
  INTEGRITY PR: metric pass_at_5 is not finite
  INTEGRITY PR: metric pass_hat_5 is not finite
  INTEGRITY PR: aggregate pass_hat_5 disagrees with rows
  INTEGRITY PR item/seed set differs from baseline
exit 1 — blocked: integrity
```

dropped_failing_rows:

```text
gate: PR E-slice_regression-20261118-16f6 vs main E-swarm-20261118-16f6 · eval set 16f6ea9b34ea
  INTEGRITY PR: metric pass_at_3 is not finite
  INTEGRITY PR: metric pass_hat_3 is not finite
  INTEGRITY PR: metric pass_at_5 is not finite
  INTEGRITY PR: metric pass_hat_5 is not finite
  INTEGRITY PR: row count != items x seeds
  INTEGRITY PR: incomplete item x seed coverage
  INTEGRITY PR: aggregate pass_hat_5 disagrees with rows
  INTEGRITY PR item/seed set differs from baseline
exit 1 — blocked: integrity
```

evaluator_errors_as_nan:

```text
gate: PR E-slice_regression-20261118-16f6 vs main E-swarm-20261118-16f6 · eval set 16f6ea9b34ea
  INTEGRITY PR: missing/non-boolean refund_amount_correct for ('E-014', 11)
  INTEGRITY PR: missing/non-boolean pass_rate for ('E-014', 11)
  INTEGRITY PR: missing/non-boolean proposal_amount_correct for ('E-014', 11)
  INTEGRITY PR: missing/non-boolean refund_amount_correct for ('E-014', 33)
  INTEGRITY PR: missing/non-boolean pass_rate for ('E-014', 33)
  INTEGRITY PR: missing/non-boolean proposal_amount_correct for ('E-014', 33)
  INTEGRITY PR: missing/non-boolean refund_amount_correct for ('E-014', 55)
  INTEGRITY PR: missing/non-boolean pass_rate for ('E-014', 55)
  INTEGRITY PR: missing/non-boolean proposal_amount_correct for ('E-014', 55)
  INTEGRITY PR: missing/non-boolean refund_amount_correct for ('E-105', 11)
  INTEGRITY PR: missing/non-boolean pass_rate for ('E-105', 11)
  INTEGRITY PR: missing/non-boolean proposal_amount_correct for ('E-105', 11)
  INTEGRITY PR: missing/non-boolean refund_amount_correct for ('E-105', 33)
  INTEGRITY PR: missing/non-boolean pass_rate for ('E-105', 33)
  INTEGRITY PR: missing/non-boolean proposal_amount_correct for ('E-105', 33)
  INTEGRITY PR: missing/non-boolean refund_amount_correct for ('E-105', 55)
  INTEGRITY PR: missing/non-boolean pass_rate for ('E-105', 55)
  INTEGRITY PR: missing/non-boolean proposal_amount_correct for ('E-105', 55)
  INTEGRITY PR: missing/non-boolean refund_amount_correct for ('E-106', 11)
  INTEGRITY PR: missing/non-boolean pass_rate for ('E-106', 11)
  INTEGRITY PR: missing/non-boolean proposal_amount_correct for ('E-106', 11)
  INTEGRITY PR: missing/non-boolean refund_amount_correct for ('E-106', 33)
  INTEGRITY PR: missing/non-boolean pass_rate for ('E-106', 33)
  INTEGRITY PR: missing/non-boolean proposal_amount_correct for ('E-106', 33)
  INTEGRITY PR: missing/non-boolean refund_amount_correct for ('E-106', 55)
  INTEGRITY PR: missing/non-boolean pass_rate for ('E-106', 55)
  INTEGRITY PR: missing/non-boolean proposal_amount_correct for ('E-106', 55)
exit 1 — blocked: integrity
```

loosened_spec:

```text
gate: PR E-slice_regression-20261118-16f6 vs main E-swarm-20261118-16f6 · eval set 16f6ea9b34ea
  INTEGRITY ratchet: loosened min for metric db_fact_kept
  INTEGRITY ratchet: loosened min for metric refund_amount_correct
  INTEGRITY ratchet: removed no_significant_drop for metric refund_amount_correct
  INTEGRITY ratchet: loosened min for metric pass_rate
  INTEGRITY ratchet: removed no_significant_drop for metric pass_rate
  INTEGRITY ratchet: loosened min for metric pass_hat_5
  INTEGRITY ratchet: loosened min for metric reply_amount_correct
  INTEGRITY ratchet: removed no_significant_drop for metric reply_amount_correct
  INTEGRITY ratchet: loosened min for metric proposal_amount_correct
  INTEGRITY ratchet: removed slice money_movement
  INTEGRITY ratchet: removed slice adversarial
  INTEGRITY ratchet: removed slice denial
exit 1 — blocked: integrity
```

Giới hạn: MockLLM; 5 seed chưa phát hiện ổn định bug xác suất 1/3; test/variant ẩn chỉ giảng viên có.

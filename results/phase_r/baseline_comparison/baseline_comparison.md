# Phase R3 — Baseline Comparison Results

**Seeds:** 200 | **Pretrain ticks:** 20 | **Eval ticks:** 15

## Raw Means

```
====================================================================================================
  TAIS PHASE R3 — BASELINE COMPARISON
====================================================================================================

  Seeds: 200 | Pretrain ticks: 20 | Eval ticks: 15


  --- First TASK_SUCCESS Tick (raw means) ---
  Condition                              Mean          Std       n
  ------------------------------ ------------ ------------  ------
  TAIS_full                            8.6000       6.3894     200
  TAIS_no_pattern_transfer            10.6650       5.4976     200
  RandomAgent                         11.0000       5.6346     200
  HeuristicAgent                       2.0000       0.0000     200
  TabularQAgent                        3.4550       3.7854     200

  --- Task Completion Rate (raw means) ---
  Condition                              Mean          Std       n
  ------------------------------ ------------ ------------  ------
  TAIS_full                            0.6200       0.4866     200
  TAIS_no_pattern_transfer             0.5550       0.4982     200
  RandomAgent                          0.4900       0.5012     200
  HeuristicAgent                       1.0000       0.0000     200
  TabularQAgent                        0.9350       0.2471     200

  --- Contradictions (TASK_FAILURE count) (raw means) ---
  Condition                              Mean          Std       n
  ------------------------------ ------------ ------------  ------
  TAIS_full                            1.0000       1.0025     200
  TAIS_no_pattern_transfer             1.0500       1.1107     200
  RandomAgent                          3.3900       1.7645     200
  HeuristicAgent                       0.0000       0.0000     200
  TabularQAgent                        0.6750       0.9401     200

  --- Total Reward (raw means) ---
  Condition                              Mean          Std       n
  ------------------------------ ------------ ------------  ------
  TAIS_full                            3.2638       2.1553     200
  TAIS_no_pattern_transfer             2.8128       2.2233     200
  RandomAgent                          2.6008       2.0478     200
  HeuristicAgent                       5.1500       0.0000     200
  TabularQAgent                        4.7690       1.0824     200

  --- Invalid Actions (raw means) ---
  Condition                              Mean          Std       n
  ------------------------------ ------------ ------------  ------
  TAIS_full                            1.6050       1.1984     200
  TAIS_no_pattern_transfer             1.6650       1.2249     200
  RandomAgent                          6.1000       2.0813     200
  HeuristicAgent                       0.0000       0.0000     200
  TabularQAgent                        0.9750       1.2337     200

  --- Final Energy (raw means) ---
  Condition                              Mean          Std       n
  ------------------------------ ------------ ------------  ------
  TAIS_full                          142.6948      10.8445     200
  TAIS_no_pattern_transfer           141.9543      11.1497     200
  RandomAgent                        123.9267      12.9381     200
  HeuristicAgent                     126.6500       0.0000     200
  TabularQAgent                      159.9335      10.1068     200

  --- Prediction Error (raw means) ---
  Condition                              Mean          Std       n
  ------------------------------ ------------ ------------  ------
  TAIS_full                            0.4538       0.2990     200
  TAIS_no_pattern_transfer             0.3903       0.2829     200
  RandomAgent                          0.0000       0.0000     200
  HeuristicAgent                       0.0000       0.0000     200
  TabularQAgent                        0.0000       0.0000     200

  --- Transfer Uses (raw means) ---
  Condition                              Mean          Std       n
  ------------------------------ ------------ ------------  ------
  TAIS_full                           24.4550       5.2129     200
  TAIS_no_pattern_transfer             0.0000       0.0000     200
  RandomAgent                          0.0000       0.0000     200
  HeuristicAgent                       0.0000       0.0000     200
  TabularQAgent                        0.0000       0.0000     200

  --- Transfer Strength (raw means) ---
  Condition                              Mean          Std       n
  ------------------------------ ------------ ------------  ------
  TAIS_full                           34.4478      17.3643     200
  TAIS_no_pattern_transfer             0.0000       0.0000     200
  RandomAgent                          0.0000       0.0000     200
  HeuristicAgent                       0.0000       0.0000     200
  TabularQAgent                        0.0000       0.0000     200

  --- Transfer Precision (raw means) ---
  Condition                              Mean          Std       n
  ------------------------------ ------------ ------------  ------
  TAIS_full                            0.8453       0.0997     200
  TAIS_no_pattern_transfer             0.0000       0.0000     200
  RandomAgent                          0.0000       0.0000     200
  HeuristicAgent                       0.0000       0.0000     200
  TabularQAgent                        0.0000       0.0000     200
```

## Comparison vs RandomAgent

```

  --- Comparison vs RandomAgent ---

  First TASK_SUCCESS Tick:
  Condition                       Cond Mean  Base Mean      Delta               95% CI          p        d
  ------------------------------ ---------- ---------- ---------- -------------------- ---------- --------
  TAIS_full                           8.600     11.000    -2.4000     [-3.567, -1.233]   0.000056 ***   -0.285
  TAIS_no_pattern_transfer           10.665     11.000    -0.3350      [-1.400, 0.730]   0.537715       -0.044
  HeuristicAgent                      2.000     11.000    -9.0000     [-9.781, -8.219]   0.000000 ***   -1.597
  TabularQAgent                       3.455     11.000    -7.5450     [-8.472, -6.618]   0.000000 ***   -1.128

  Task Completion Rate:
  Condition                       Cond Mean  Base Mean      Delta               95% CI          p        d
  ------------------------------ ---------- ---------- ---------- -------------------- ---------- --------
  TAIS_full                           0.620      0.490    +0.1300       [0.034, 0.226]   0.007671 **     0.189
  TAIS_no_pattern_transfer            0.555      0.490    +0.0650      [-0.030, 0.160]   0.181422        0.094
  HeuristicAgent                      1.000      0.490    +0.5100       [0.441, 0.579]   0.000000 ***    1.018
  TabularQAgent                       0.935      0.490    +0.4450       [0.368, 0.522]   0.000000 ***    0.801

  Contradictions (TASK_FAILURE count):
  Condition                       Cond Mean  Base Mean      Delta               95% CI          p        d
  ------------------------------ ---------- ---------- ---------- -------------------- ---------- --------
  TAIS_full                           1.000      3.390    -2.3900     [-2.680, -2.100]   0.000000 ***   -1.143
  TAIS_no_pattern_transfer            1.050      3.390    -2.3400     [-2.639, -2.041]   0.000000 ***   -1.083
  HeuristicAgent                      0.000      3.390    -3.3900     [-3.635, -3.145]   0.000000 ***   -1.921
  TabularQAgent                       0.675      3.390    -2.7150     [-2.973, -2.457]   0.000000 ***   -1.459

  Total Reward:
  Condition                       Cond Mean  Base Mean      Delta               95% CI          p        d
  ------------------------------ ---------- ---------- ---------- -------------------- ---------- --------
  TAIS_full                           3.264      2.601    +0.6631       [0.261, 1.065]   0.001211 **     0.229
  TAIS_no_pattern_transfer            2.813      2.601    +0.2120      [-0.194, 0.619]   0.306603        0.072
  HeuristicAgent                      5.150      2.601    +2.5492       [2.265, 2.833]   0.000000 ***    1.245
  TabularQAgent                       4.769      2.601    +2.1683       [1.849, 2.487]   0.000000 ***    0.942

  Invalid Actions:
  Condition                       Cond Mean  Base Mean      Delta               95% CI          p        d
  ------------------------------ ---------- ---------- ---------- -------------------- ---------- --------
  TAIS_full                           1.605      6.100    -4.4950     [-4.845, -4.145]   0.000000 ***   -1.782
  TAIS_no_pattern_transfer            1.665      6.100    -4.4350     [-4.789, -4.081]   0.000000 ***   -1.738
  HeuristicAgent                      0.000      6.100    -6.1000     [-6.388, -5.812]   0.000000 ***   -2.931
  TabularQAgent                       0.975      6.100    -5.1250     [-5.435, -4.815]   0.000000 ***   -2.289

  Final Energy:
  Condition                       Cond Mean  Base Mean      Delta               95% CI          p        d
  ------------------------------ ---------- ---------- ---------- -------------------- ---------- --------
  TAIS_full                         142.695    123.927   +18.7680     [16.466, 21.070]   0.000000 ***    1.130
  TAIS_no_pattern_transfer          141.954    123.927   +18.0276     [15.722, 20.333]   0.000000 ***    1.084
  HeuristicAgent                    126.650    123.927    +2.7233       [0.930, 4.516]   0.002914 **     0.210
  TabularQAgent                     159.934    123.927   +36.0067     [34.002, 38.012]   0.000000 ***    2.489

  Prediction Error:
  Condition                       Cond Mean  Base Mean      Delta               95% CI          p        d
  ------------------------------ ---------- ---------- ---------- -------------------- ---------- --------
  TAIS_full                           0.454      0.000    +0.4538       [0.412, 0.495]   0.000000 ***    1.518
  TAIS_no_pattern_transfer            0.390      0.000    +0.3903       [0.351, 0.430]   0.000000 ***    1.380
  HeuristicAgent                      0.000      0.000    +0.0000       [0.000, 0.000]   1.000000        0.000
  TabularQAgent                       0.000      0.000    +0.0000       [0.000, 0.000]   1.000000        0.000

  Transfer Uses:
  Condition                       Cond Mean  Base Mean      Delta               95% CI          p        d
  ------------------------------ ---------- ---------- ---------- -------------------- ---------- --------
  TAIS_full                          24.455      0.000   +24.4550     [23.733, 25.177]   0.000000 ***    4.691
  TAIS_no_pattern_transfer            0.000      0.000    +0.0000       [0.000, 0.000]   1.000000        0.000
  HeuristicAgent                      0.000      0.000    +0.0000       [0.000, 0.000]   1.000000        0.000
  TabularQAgent                       0.000      0.000    +0.0000       [0.000, 0.000]   1.000000        0.000

  Transfer Strength:
  Condition                       Cond Mean  Base Mean      Delta               95% CI          p        d
  ------------------------------ ---------- ---------- ---------- -------------------- ---------- --------
  TAIS_full                          34.448      0.000   +34.4478     [32.041, 36.854]   0.000000 ***    1.984
  TAIS_no_pattern_transfer            0.000      0.000    +0.0000       [0.000, 0.000]   1.000000        0.000
  HeuristicAgent                      0.000      0.000    +0.0000       [0.000, 0.000]   1.000000        0.000
  TabularQAgent                       0.000      0.000    +0.0000       [0.000, 0.000]   1.000000        0.000

  Transfer Precision:
  Condition                       Cond Mean  Base Mean      Delta               95% CI          p        d
  ------------------------------ ---------- ---------- ---------- -------------------- ---------- --------
  TAIS_full                           0.845      0.000    +0.8453       [0.831, 0.859]   0.000000 ***    8.478
  TAIS_no_pattern_transfer            0.000      0.000    +0.0000       [0.000, 0.000]   1.000000        0.000
  HeuristicAgent                      0.000      0.000    +0.0000       [0.000, 0.000]   1.000000        0.000
  TabularQAgent                       0.000      0.000    +0.0000       [0.000, 0.000]   1.000000        0.000
```

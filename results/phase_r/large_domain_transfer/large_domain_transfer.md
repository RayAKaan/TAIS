# Phase R4 — Large Domain Transfer Results

**Seeds:** 100 | **Pretrain ticks:** 20 | **Eval ticks:** 30

```
========================================================================================================================
  TAIS PHASE R4 — LARGE DOMAIN TRANSFER
========================================================================================================================

  Seeds: 100 | Pretrain ticks: 20 | Eval ticks: 30


  ====================================================================================================
  Target: logic_large
  ====================================================================================================

    First TASK_SUCCESS Tick (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    fresh                               18.2600       9.5194     100
    grid_pretrain                       19.8400      12.5776     100
    rules_pretrain                      15.7300      10.0099     100
    three_domain_pretrain               16.1400      12.0462     100
    same_domain_pretrain                 8.4000       8.6117     100

    Task Completion Rate (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    fresh                                0.7700       0.4230     100
    grid_pretrain                        0.4900       0.5024     100
    rules_pretrain                       0.8000       0.4020     100
    three_domain_pretrain                0.6900       0.4648     100
    same_domain_pretrain                 0.9200       0.2727     100

    Contradictions (TASK_FAILURE count) (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    fresh                                1.7700       1.4485     100
    grid_pretrain                        1.9000       1.3371     100
    rules_pretrain                       1.8700       1.3533     100
    three_domain_pretrain                1.6700       1.3108     100
    same_domain_pretrain                 1.9100       1.2399     100

    Total Reward (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    fresh                                4.8647       2.2540     100
    grid_pretrain                        3.7886       2.5479     100
    rules_pretrain                       5.1485       2.2619     100
    three_domain_pretrain                4.6810       2.3891     100
    same_domain_pretrain                 5.9265       1.3565     100

    Invalid Actions (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    fresh                                2.8200       1.6599     100
    grid_pretrain                        2.6700       1.5574     100
    rules_pretrain                       2.6500       1.5594     100
    three_domain_pretrain                2.6000       1.7523     100
    same_domain_pretrain                 2.6300       1.5019     100

    Final Energy (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    fresh                               94.2707       2.7691     100
    grid_pretrain                      136.2626      12.3344     100
    rules_pretrain                      85.4460       5.4481     100
    three_domain_pretrain              102.9035       7.3865     100
    same_domain_pretrain                91.4822       2.9789     100

    Prediction Error (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    fresh                                0.2647       0.1186     100
    grid_pretrain                        0.1980       0.1398     100
    rules_pretrain                       0.2782       0.1179     100
    three_domain_pretrain                0.2510       0.1405     100
    same_domain_pretrain                 0.2834       0.0771     100

    Transfer Uses (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    fresh                                9.0300       6.9797     100
    grid_pretrain                       51.2300      12.9583     100
    rules_pretrain                      28.4500      11.5211     100
    three_domain_pretrain               77.8100      28.0334     100
    same_domain_pretrain                19.0600       6.6421     100

    Transfer Strength (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    fresh                               36.0000      27.9437     100
    grid_pretrain                       68.3863      43.8143     100
    rules_pretrain                      56.1829      34.0580     100
    three_domain_pretrain               96.9429      50.3201     100
    same_domain_pretrain                76.2400      26.5684     100

    Transfer Precision (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    fresh                                0.6559       0.3881     100
    grid_pretrain                        0.8741       0.0640     100
    rules_pretrain                       0.8157       0.2349     100
    three_domain_pretrain                0.8782       0.0664     100
    same_domain_pretrain                 0.8323       0.2034     100

    Hazard Steps (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    fresh                                0.0000       0.0000     100
    grid_pretrain                        0.0000       0.0000     100
    rules_pretrain                       0.0000       0.0000     100
    three_domain_pretrain                0.0000       0.0000     100
    same_domain_pretrain                 0.0000       0.0000     100

  ====================================================================================================
  Target: hazard_large
  ====================================================================================================

    First TASK_SUCCESS Tick (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    fresh                               31.0000       0.0000     100
    grid_pretrain                       31.0000       0.0000     100
    rules_pretrain                      31.0000       0.0000     100
    three_domain_pretrain               31.0000       0.0000     100
    same_domain_pretrain                31.0000       0.0000     100

    Task Completion Rate (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    fresh                                0.0000       0.0000     100
    grid_pretrain                        0.0000       0.0000     100
    rules_pretrain                       0.0000       0.0000     100
    three_domain_pretrain                0.0000       0.0000     100
    same_domain_pretrain                 0.0000       0.0000     100

    Contradictions (TASK_FAILURE count) (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    fresh                                7.7000       1.9669     100
    grid_pretrain                        7.2900       2.9346     100
    rules_pretrain                       7.2200       2.2364     100
    three_domain_pretrain                8.9000       4.7514     100
    same_domain_pretrain                 5.6100       2.3651     100

    Total Reward (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    fresh                                0.4460       0.0393     100
    grid_pretrain                        0.4542       0.0587     100
    rules_pretrain                       0.4556       0.0447     100
    three_domain_pretrain                0.4220       0.0950     100
    same_domain_pretrain                 0.4878       0.0473     100

    Invalid Actions (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    fresh                                7.7000       1.9669     100
    grid_pretrain                        7.2900       2.9346     100
    rules_pretrain                       7.2200       2.2364     100
    three_domain_pretrain                8.9000       4.7514     100
    same_domain_pretrain                 5.6100       2.3651     100

    Final Energy (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    fresh                               86.7460       2.0062     100
    grid_pretrain                      130.1752      13.4555     100
    rules_pretrain                      78.3131       5.5424     100
    three_domain_pretrain               94.3295       6.6574     100
    same_domain_pretrain                79.0558       3.0143     100

    Prediction Error (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    fresh                                0.0987       0.0080     100
    grid_pretrain                        0.0910       0.0159     100
    rules_pretrain                       0.0940       0.0142     100
    three_domain_pretrain                0.0930       0.0163     100
    same_domain_pretrain                 0.0023       0.0098     100

    Transfer Uses (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    fresh                                0.0000       0.0000     100
    grid_pretrain                       43.0400       7.0337     100
    rules_pretrain                      17.4900       9.3425     100
    three_domain_pretrain               61.6700      21.2456     100
    same_domain_pretrain                 0.0000       0.0000     100

    Transfer Strength (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    fresh                                0.0000       0.0000     100
    grid_pretrain                      105.3136      25.2852     100
    rules_pretrain                       8.6568      14.0126     100
    three_domain_pretrain              119.4056      67.2791     100
    same_domain_pretrain                 0.0000       0.0000     100

    Transfer Precision (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    fresh                                0.0000       0.0000     100
    grid_pretrain                        0.7622       0.0966     100
    rules_pretrain                       0.3992       0.3833     100
    three_domain_pretrain                0.7042       0.1590     100
    same_domain_pretrain                 0.0000       0.0000     100

    Hazard Steps (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    fresh                                7.7000       1.9669     100
    grid_pretrain                        7.2900       2.9346     100
    rules_pretrain                       7.2200       2.2364     100
    three_domain_pretrain                8.9000       4.7514     100
    same_domain_pretrain                 5.6100       2.3651     100

  ====================================================================================================
  Target: rules_chain_long
  ====================================================================================================

    First TASK_SUCCESS Tick (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    fresh                               30.0800       3.8262     100
    grid_pretrain                       24.9800      10.3845     100
    rules_pretrain                      28.5500       5.4908     100
    three_domain_pretrain               22.5300       9.8139     100
    same_domain_pretrain                29.5600       4.9794     100

    Task Completion Rate (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    fresh                                0.1200       0.3266     100
    grid_pretrain                        0.2900       0.4560     100
    rules_pretrain                       0.2200       0.4163     100
    three_domain_pretrain                0.5400       0.5009     100
    same_domain_pretrain                 0.1200       0.3266     100

    Contradictions (TASK_FAILURE count) (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    fresh                                2.4900       1.5341     100
    grid_pretrain                        2.4900       1.4941     100
    rules_pretrain                       3.1300       1.6857     100
    three_domain_pretrain                3.7000       1.9873     100
    same_domain_pretrain                 2.4900       1.5142     100

    Total Reward (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    fresh                                1.4208       1.4521     100
    grid_pretrain                        2.2369       2.0717     100
    rules_pretrain                       1.9071       1.8081     100
    three_domain_pretrain                3.3601       2.1721     100
    same_domain_pretrain                 1.4607       1.4512     100

    Invalid Actions (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    fresh                                2.4900       1.5341     100
    grid_pretrain                        2.4900       1.4941     100
    rules_pretrain                       3.1300       1.6857     100
    three_domain_pretrain                3.7000       1.9873     100
    same_domain_pretrain                 2.4900       1.5142     100

    Final Energy (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    fresh                               86.7198       5.3185     100
    grid_pretrain                      130.0629      13.6711     100
    rules_pretrain                      76.0176       7.8331     100
    three_domain_pretrain               92.7036       9.7913     100
    same_domain_pretrain                77.1094       7.0834     100

    Prediction Error (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    fresh                                0.1239       0.0616     100
    grid_pretrain                        0.1707       0.1158     100
    rules_pretrain                       0.1485       0.0774     100
    three_domain_pretrain                0.2302       0.1169     100
    same_domain_pretrain                 0.0406       0.0807     100

    Transfer Uses (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    fresh                               13.6300       7.4572     100
    grid_pretrain                       58.0300      10.8175     100
    rules_pretrain                      14.2300       9.0083     100
    three_domain_pretrain               54.8800      17.4988     100
    same_domain_pretrain                20.6100       5.6298     100

    Transfer Strength (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    fresh                               39.5203      23.0575     100
    grid_pretrain                       72.8909      25.8050     100
    rules_pretrain                      21.8379      23.4605     100
    three_domain_pretrain               58.0542      30.3570     100
    same_domain_pretrain                59.0151      19.1858     100

    Transfer Precision (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    fresh                                0.8429       0.2601     100
    grid_pretrain                        0.9170       0.0498     100
    rules_pretrain                       0.5003       0.4500     100
    three_domain_pretrain                0.8776       0.0676     100
    same_domain_pretrain                 0.8723       0.2074     100

    Hazard Steps (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    fresh                                0.0000       0.0000     100
    grid_pretrain                        0.0000       0.0000     100
    rules_pretrain                       0.0000       0.0000     100
    three_domain_pretrain                0.0000       0.0000     100
    same_domain_pretrain                 0.0000       0.0000     100
```

```

  ====================================================================================================
  Target: logic_large — Comparison vs fresh
  ====================================================================================================

    First TASK_SUCCESS Tick:
    Condition                       Cond Mean Fresh Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    grid_pretrain                      19.840     18.260    +1.5800        [-1.509, 4.669]   0.311123        0.101
    rules_pretrain                     15.730     18.260    -2.5300        [-5.465, 0.405]   0.087876       -0.171
    three_domain_pretrain              16.140     18.260    -2.1200        [-5.176, 0.936]   0.169550       -0.137
    same_domain_pretrain                8.400     18.260    -9.8600      [-12.208, -7.512]   0.000000 ***   -0.832

    Task Completion Rate:
    Condition                       Cond Mean Fresh Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    grid_pretrain                       0.490      0.770    -0.2800       [-0.412, -0.148]   0.000028 ***   -0.419
    rules_pretrain                      0.800      0.770    +0.0300        [-0.094, 0.154]   0.632274        0.048
    three_domain_pretrain               0.690      0.770    -0.0800        [-0.198, 0.038]   0.180700       -0.134
    same_domain_pretrain                0.920      0.770    +0.1500         [0.051, 0.249]   0.002700 **     0.300

    Contradictions (TASK_FAILURE count):
    Condition                       Cond Mean Fresh Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    grid_pretrain                       1.900      1.770    +0.1300        [-0.269, 0.529]   0.518483        0.065
    rules_pretrain                      1.870      1.770    +0.1000        [-0.303, 0.503]   0.623574        0.049
    three_domain_pretrain               1.670      1.770    -0.1000        [-0.489, 0.289]   0.611162       -0.051
    same_domain_pretrain                1.910      1.770    +0.1400        [-0.245, 0.525]   0.471368        0.072

    Total Reward:
    Condition                       Cond Mean Fresh Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    grid_pretrain                       3.789      4.865    -1.0761       [-1.761, -0.391]   0.001870 **    -0.311
    rules_pretrain                      5.149      4.865    +0.2838        [-0.383, 0.950]   0.399217        0.084
    three_domain_pretrain               4.681      4.865    -0.1837        [-0.806, 0.439]   0.558889       -0.058
    same_domain_pretrain                5.926      4.865    +1.0618         [0.544, 1.580]   0.000050 ***    0.406

    Invalid Actions:
    Condition                       Cond Mean Fresh Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    grid_pretrain                       2.670      2.820    -0.1500        [-0.575, 0.275]   0.484962       -0.070
    rules_pretrain                      2.650      2.820    -0.1700        [-0.601, 0.261]   0.434335       -0.078
    three_domain_pretrain               2.600      2.820    -0.2200        [-0.676, 0.236]   0.339476       -0.096
    same_domain_pretrain                2.630      2.820    -0.1900        [-0.600, 0.220]   0.359355       -0.092

    Final Energy:
    Condition                       Cond Mean Fresh Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    grid_pretrain                     136.263     94.271   +41.9919       [39.442, 44.541]   0.000000 ***    3.262
    rules_pretrain                     85.446     94.271    -8.8247      [-10.029, -7.621]   0.000000 ***   -1.452
    three_domain_pretrain             102.903     94.271    +8.6328        [7.060, 10.206]   0.000000 ***    1.087
    same_domain_pretrain               91.482     94.271    -2.7885       [-3.545, -2.032]   0.000000 ***   -0.730

    Prediction Error:
    Condition                       Cond Mean Fresh Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    grid_pretrain                       0.198      0.265    -0.0667       [-0.104, -0.030]   0.000386 ***   -0.355
    rules_pretrain                      0.278      0.265    +0.0134        [-0.022, 0.049]   0.459287        0.074
    three_domain_pretrain               0.251      0.265    -0.0137        [-0.049, 0.022]   0.443965       -0.077
    same_domain_pretrain                0.283      0.265    +0.0187        [-0.009, 0.046]   0.173879        0.136

    Transfer Uses:
    Condition                       Cond Mean Fresh Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    grid_pretrain                      51.230      9.030   +42.2000       [39.341, 45.059]   0.000000 ***    2.923
    rules_pretrain                     28.450      9.030   +19.4200       [16.548, 22.292]   0.000000 ***    1.339
    three_domain_pretrain              77.810      9.030   +68.7800       [63.153, 74.407]   0.000000 ***    2.420
    same_domain_pretrain               19.060      9.030   +10.0300        [8.223, 11.837]   0.000000 ***    1.099

    Transfer Strength:
    Condition                       Cond Mean Fresh Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    grid_pretrain                      68.386     36.000   +32.3863       [22.107, 42.666]   0.000000 ***    0.624
    rules_pretrain                     56.183     36.000   +20.1829       [10.660, 29.706]   0.000027 ***    0.420
    three_domain_pretrain              96.943     36.000   +60.9429       [49.642, 72.244]   0.000000 ***    1.068
    same_domain_pretrain               76.240     36.000   +40.2400       [33.006, 47.474]   0.000000 ***    1.101

    Transfer Precision:
    Condition                       Cond Mean Fresh Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    grid_pretrain                       0.874      0.656    +0.2182         [0.142, 0.294]   0.000000 ***    0.567
    rules_pretrain                      0.816      0.656    +0.1598         [0.067, 0.253]   0.000680 ***    0.340
    three_domain_pretrain               0.878      0.656    +0.2224         [0.145, 0.300]   0.000000 ***    0.566
    same_domain_pretrain                0.832      0.656    +0.1764         [0.089, 0.264]   0.000064 ***    0.400

    Hazard Steps:
    Condition                       Cond Mean Fresh Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    grid_pretrain                       0.000      0.000    +0.0000         [0.000, 0.000]   1.000000        0.000
    rules_pretrain                      0.000      0.000    +0.0000         [0.000, 0.000]   1.000000        0.000
    three_domain_pretrain               0.000      0.000    +0.0000         [0.000, 0.000]   1.000000        0.000
    same_domain_pretrain                0.000      0.000    +0.0000         [0.000, 0.000]   1.000000        0.000

  ====================================================================================================
  Target: hazard_large — Comparison vs fresh
  ====================================================================================================

    First TASK_SUCCESS Tick:
    Condition                       Cond Mean Fresh Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    grid_pretrain                      31.000     31.000    +0.0000         [0.000, 0.000]   1.000000        0.000
    rules_pretrain                     31.000     31.000    +0.0000         [0.000, 0.000]   1.000000        0.000
    three_domain_pretrain              31.000     31.000    +0.0000         [0.000, 0.000]   1.000000        0.000
    same_domain_pretrain               31.000     31.000    +0.0000         [0.000, 0.000]   1.000000        0.000

    Task Completion Rate:
    Condition                       Cond Mean Fresh Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    grid_pretrain                       0.000      0.000    +0.0000         [0.000, 0.000]   1.000000        0.000
    rules_pretrain                      0.000      0.000    +0.0000         [0.000, 0.000]   1.000000        0.000
    three_domain_pretrain               0.000      0.000    +0.0000         [0.000, 0.000]   1.000000        0.000
    same_domain_pretrain                0.000      0.000    +0.0000         [0.000, 0.000]   1.000000        0.000

    Contradictions (TASK_FAILURE count):
    Condition                       Cond Mean Fresh Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    grid_pretrain                       7.290      7.700    -0.4100        [-1.127, 0.307]   0.257540       -0.113
    rules_pretrain                      7.220      7.700    -0.4800        [-1.126, 0.166]   0.141071       -0.147
    three_domain_pretrain               8.900      7.700    +1.2000         [0.157, 2.243]   0.022746 *      0.228
    same_domain_pretrain                5.610      7.700    -2.0900       [-2.757, -1.423]   0.000000 ***   -0.620

    Total Reward:
    Condition                       Cond Mean Fresh Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    grid_pretrain                       0.454      0.446    +0.0082        [-0.006, 0.023]   0.257540        0.113
    rules_pretrain                      0.456      0.446    +0.0096        [-0.003, 0.023]   0.141071        0.147
    three_domain_pretrain               0.422      0.446    -0.0240       [-0.045, -0.003]   0.022746 *     -0.228
    same_domain_pretrain                0.488      0.446    +0.0418         [0.028, 0.055]   0.000000 ***    0.620

    Invalid Actions:
    Condition                       Cond Mean Fresh Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    grid_pretrain                       7.290      7.700    -0.4100        [-1.127, 0.307]   0.257540       -0.113
    rules_pretrain                      7.220      7.700    -0.4800        [-1.126, 0.166]   0.141071       -0.147
    three_domain_pretrain               8.900      7.700    +1.2000         [0.157, 2.243]   0.022746 *      0.228
    same_domain_pretrain                5.610      7.700    -2.0900       [-2.757, -1.423]   0.000000 ***   -0.620

    Final Energy:
    Condition                       Cond Mean Fresh Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    grid_pretrain                     130.175     86.746   +43.4292       [40.741, 46.118]   0.000000 ***    3.199
    rules_pretrain                     78.313     86.746    -8.4329       [-9.686, -7.179]   0.000000 ***   -1.332
    three_domain_pretrain              94.329     86.746    +7.5835         [6.173, 8.994]   0.000000 ***    1.065
    same_domain_pretrain               79.056     86.746    -7.6902       [-8.455, -6.925]   0.000000 ***   -1.990

    Prediction Error:
    Condition                       Cond Mean Fresh Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    grid_pretrain                       0.091      0.099    -0.0077       [-0.011, -0.004]   0.000003 ***   -0.470
    rules_pretrain                      0.094      0.099    -0.0047       [-0.008, -0.001]   0.006338 **    -0.273
    three_domain_pretrain               0.093      0.099    -0.0057       [-0.009, -0.002]   0.002052 **    -0.308
    same_domain_pretrain                0.002      0.099    -0.0963       [-0.099, -0.094]   0.000000 ***   -7.882

    Transfer Uses:
    Condition                       Cond Mean Fresh Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    grid_pretrain                      43.040      0.000   +43.0400       [41.647, 44.433]   0.000000 ***    6.119
    rules_pretrain                     17.490      0.000   +17.4900       [15.640, 19.340]   0.000000 ***    1.872
    three_domain_pretrain              61.670      0.000   +61.6700       [57.463, 65.877]   0.000000 ***    2.903
    same_domain_pretrain                0.000      0.000    +0.0000         [0.000, 0.000]   1.000000        0.000

    Transfer Strength:
    Condition                       Cond Mean Fresh Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    grid_pretrain                     105.314      0.000  +105.3136     [100.307, 110.321]   0.000000 ***    4.165
    rules_pretrain                      8.657      0.000    +8.6568        [5.882, 11.432]   0.000000 ***    0.618
    three_domain_pretrain             119.406      0.000  +119.4056     [106.083, 132.728]   0.000000 ***    1.775
    same_domain_pretrain                0.000      0.000    +0.0000         [0.000, 0.000]   1.000000        0.000

    Transfer Precision:
    Condition                       Cond Mean Fresh Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    grid_pretrain                       0.762      0.000    +0.7622         [0.743, 0.781]   0.000000 ***    7.886
    rules_pretrain                      0.399      0.000    +0.3992         [0.323, 0.475]   0.000000 ***    1.041
    three_domain_pretrain               0.704      0.000    +0.7042         [0.673, 0.736]   0.000000 ***    4.430
    same_domain_pretrain                0.000      0.000    +0.0000         [0.000, 0.000]   1.000000        0.000

    Hazard Steps:
    Condition                       Cond Mean Fresh Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    grid_pretrain                       7.290      7.700    -0.4100        [-1.127, 0.307]   0.257540       -0.113
    rules_pretrain                      7.220      7.700    -0.4800        [-1.126, 0.166]   0.141071       -0.147
    three_domain_pretrain               8.900      7.700    +1.2000         [0.157, 2.243]   0.022746 *      0.228
    same_domain_pretrain                5.610      7.700    -2.0900       [-2.757, -1.423]   0.000000 ***   -0.620

  ====================================================================================================
  Target: rules_chain_long — Comparison vs fresh
  ====================================================================================================

    First TASK_SUCCESS Tick:
    Condition                       Cond Mean Fresh Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    grid_pretrain                      24.980     30.080    -5.1000       [-7.122, -3.078]   0.000001 ***   -0.499
    rules_pretrain                     28.550     30.080    -1.5300       [-2.910, -0.150]   0.028080 *     -0.220
    three_domain_pretrain              22.530     30.080    -7.5500       [-9.559, -5.541]   0.000000 ***   -0.744
    same_domain_pretrain               29.560     30.080    -0.5200        [-1.802, 0.762]   0.421941       -0.080

    Task Completion Rate:
    Condition                       Cond Mean Fresh Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    grid_pretrain                       0.290      0.120    +0.1700         [0.068, 0.272]   0.000932 ***    0.331
    rules_pretrain                      0.220      0.120    +0.1000        [-0.007, 0.207]   0.064654        0.185
    three_domain_pretrain               0.540      0.120    +0.4200         [0.303, 0.537]   0.000000 ***    0.713
    same_domain_pretrain                0.120      0.120    +0.0000        [-0.089, 0.089]   1.000000        0.000

    Contradictions (TASK_FAILURE count):
    Condition                       Cond Mean Fresh Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    grid_pretrain                       2.490      2.490    +0.0000        [-0.403, 0.403]   1.000000        0.000
    rules_pretrain                      3.130      2.490    +0.6400         [0.187, 1.093]   0.005102 **     0.280
    three_domain_pretrain               3.700      2.490    +1.2100         [0.738, 1.682]   0.000000 ***    0.508
    same_domain_pretrain                2.490      2.490    +0.0000        [-0.393, 0.393]   1.000000        0.000

    Total Reward:
    Condition                       Cond Mean Fresh Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    grid_pretrain                       2.237      1.421    +0.8161         [0.356, 1.276]   0.000442 ***    0.351
    rules_pretrain                      1.907      1.421    +0.4863         [0.018, 0.954]   0.039626 *      0.206
    three_domain_pretrain               3.360      1.421    +1.9393         [1.435, 2.444]   0.000000 ***    0.761
    same_domain_pretrain                1.461      1.421    +0.0399        [-0.359, 0.438]   0.842857        0.020

    Invalid Actions:
    Condition                       Cond Mean Fresh Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    grid_pretrain                       2.490      2.490    +0.0000        [-0.403, 0.403]   1.000000        0.000
    rules_pretrain                      3.130      2.490    +0.6400         [0.187, 1.093]   0.005102 **     0.280
    three_domain_pretrain               3.700      2.490    +1.2100         [0.738, 1.682]   0.000000 ***    0.508
    same_domain_pretrain                2.490      2.490    +0.0000        [-0.393, 0.393]   1.000000        0.000

    Final Energy:
    Condition                       Cond Mean Fresh Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    grid_pretrain                     130.063     86.720   +43.3431       [40.555, 46.131]   0.000000 ***    3.079
    rules_pretrain                     76.018     86.720   -10.7022      [-12.520, -8.885]   0.000000 ***   -1.166
    three_domain_pretrain              92.704     86.720    +5.9838         [3.845, 8.123]   0.000000 ***    0.554
    same_domain_pretrain               77.109     86.720    -9.6104      [-11.115, -8.105]   0.000000 ***   -1.264

    Prediction Error:
    Condition                       Cond Mean Fresh Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    grid_pretrain                       0.171      0.124    +0.0468         [0.022, 0.072]   0.000216 ***    0.370
    rules_pretrain                      0.148      0.124    +0.0246         [0.005, 0.045]   0.015191 *      0.243
    three_domain_pretrain               0.230      0.124    +0.1063         [0.081, 0.132]   0.000000 ***    0.830
    same_domain_pretrain                0.041      0.124    -0.0833       [-0.103, -0.064]   0.000000 ***   -0.849

    Transfer Uses:
    Condition                       Cond Mean Fresh Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    grid_pretrain                      58.030     13.630   +44.4000       [41.705, 47.095]   0.000000 ***    3.262
    rules_pretrain                     14.230     13.630    +0.6000        [-1.398, 2.598]   0.552059        0.059
    three_domain_pretrain              54.880     13.630   +41.2500       [37.742, 44.758]   0.000000 ***    2.328
    same_domain_pretrain               20.610     13.630    +6.9800         [5.145, 8.815]   0.000000 ***    0.753

    Transfer Strength:
    Condition                       Cond Mean Fresh Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    grid_pretrain                      72.891     39.520   +33.3705       [26.187, 40.554]   0.000000 ***    0.920
    rules_pretrain                     21.838     39.520   -17.6824     [-23.528, -11.836]   0.000000 ***   -0.599
    three_domain_pretrain              58.054     39.520   +18.5339       [11.687, 25.381]   0.000000 ***    0.536
    same_domain_pretrain               59.015     39.520   +19.4947       [13.952, 25.037]   0.000000 ***    0.696

    Transfer Precision:
    Condition                       Cond Mean Fresh Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    grid_pretrain                       0.917      0.843    +0.0741         [0.022, 0.126]   0.004557 **     0.284
    rules_pretrain                      0.500      0.843    -0.3426       [-0.446, -0.239]   0.000000 ***   -0.657
    three_domain_pretrain               0.878      0.843    +0.0347        [-0.020, 0.090]   0.211875        0.125
    same_domain_pretrain                0.872      0.843    +0.0294        [-0.037, 0.096]   0.378092        0.088

    Hazard Steps:
    Condition                       Cond Mean Fresh Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    grid_pretrain                       0.000      0.000    +0.0000         [0.000, 0.000]   1.000000        0.000
    rules_pretrain                      0.000      0.000    +0.0000         [0.000, 0.000]   1.000000        0.000
    three_domain_pretrain               0.000      0.000    +0.0000         [0.000, 0.000]   1.000000        0.000
    same_domain_pretrain                0.000      0.000    +0.0000         [0.000, 0.000]   1.000000        0.000
```

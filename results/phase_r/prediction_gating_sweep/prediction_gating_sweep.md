# Phase R5 — Prediction Gating Sweep Results

**Seeds:** 200 | **Pretrain ticks:** 20 | **Eval ticks:** 15

```
========================================================================================================================
  TAIS PHASE R5 — PREDICTION GATING SWEEP
========================================================================================================================

  Seeds: 200 | Pretrain ticks: 20 | Eval ticks: 15


  ====================================================================================================
  Target: logic
  ====================================================================================================

    First TASK_SUCCESS Tick (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    no_prediction                        9.8150       6.4333     200
    prediction_disabled_current          9.7750       6.4258     200
    prediction_k0_w025                   9.3450       6.3282     200
    prediction_k3_w025                   9.3550       6.3189     200
    prediction_k5_w025                   9.5100       6.3086     200
    prediction_k10_w025                  9.6600       6.3273     200
    prediction_k3_w05                    8.4450       5.9273     200
    prediction_k5_w05                    8.5750       5.9084     200
    prediction_k10_w05                   9.2900       6.0746     200

    Task Completion Rate (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    no_prediction                        0.5300       0.5004     200
    prediction_disabled_current          0.5300       0.5004     200
    prediction_k0_w025                   0.5800       0.4948     200
    prediction_k3_w025                   0.5800       0.4948     200
    prediction_k5_w025                   0.5750       0.4956     200
    prediction_k10_w025                  0.5700       0.4963     200
    prediction_k3_w05                    0.6850       0.4657     200
    prediction_k5_w05                    0.6800       0.4676     200
    prediction_k10_w05                   0.6500       0.4782     200

    Contradictions (TASK_FAILURE count) (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    no_prediction                        1.0000       0.8911     200
    prediction_disabled_current          1.0900       0.9934     200
    prediction_k0_w025                   1.0850       1.0014     200
    prediction_k3_w025                   1.0800       1.0043     200
    prediction_k5_w025                   1.1000       1.0224     200
    prediction_k10_w025                  1.0950       1.0105     200
    prediction_k3_w05                    1.0750       0.9870     200
    prediction_k5_w05                    1.0950       1.0055     200
    prediction_k10_w05                   1.1000       1.0125     200

    Total Reward (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    no_prediction                        2.8888       2.2462     200
    prediction_disabled_current          2.8822       2.2230     200
    prediction_k0_w025                   3.0974       2.2029     200
    prediction_k3_w025                   3.0970       2.2026     200
    prediction_k5_w025                   3.0741       2.2038     200
    prediction_k10_w025                  3.0589       2.2030     200
    prediction_k3_w05                    3.5316       2.1119     200
    prediction_k5_w05                    3.5093       2.1185     200
    prediction_k10_w05                   3.3904       2.1456     200

    Invalid Actions (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    no_prediction                        1.6150       1.2141     200
    prediction_disabled_current          1.6750       1.2757     200
    prediction_k0_w025                   1.6950       1.2963     200
    prediction_k3_w025                   1.6900       1.2970     200
    prediction_k5_w025                   1.7000       1.3033     200
    prediction_k10_w025                  1.6800       1.2868     200
    prediction_k3_w05                    1.6950       1.3040     200
    prediction_k5_w05                    1.7000       1.3148     200
    prediction_k10_w05                   1.6900       1.2854     200

    Final Energy (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    no_prediction                      136.9763      11.9664     200
    prediction_disabled_current        140.2822      13.5039     200
    prediction_k0_w025                 140.0284      13.1136     200
    prediction_k3_w025                 140.0351      13.1128     200
    prediction_k5_w025                 140.0177      13.1581     200
    prediction_k10_w025                140.0324      13.1531     200
    prediction_k3_w05                  140.1396      13.2807     200
    prediction_k5_w05                  140.1208      13.3250     200
    prediction_k10_w05                 140.0894      13.2286     200

    Prediction Error (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    no_prediction                        0.3111       0.1689     200
    prediction_disabled_current          0.4042       0.2895     200
    prediction_k0_w025                   0.4321       0.2819     200
    prediction_k3_w025                   0.4316       0.2816     200
    prediction_k5_w025                   0.4281       0.2814     200
    prediction_k10_w025                  0.4240       0.2806     200
    prediction_k3_w05                    0.4858       0.2602     200
    prediction_k5_w05                    0.4838       0.2606     200
    prediction_k10_w05                   0.4630       0.2612     200

    Transfer Uses (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    no_prediction                       24.9800       5.4551     200
    prediction_disabled_current         24.4500       6.0664     200
    prediction_k0_w025                  24.6650       5.9818     200
    prediction_k3_w025                  24.6600       5.9836     200
    prediction_k5_w025                  24.5950       6.0675     200
    prediction_k10_w025                 24.5300       6.0491     200
    prediction_k3_w05                   25.1800       6.0382     200
    prediction_k5_w05                   25.1100       6.1225     200
    prediction_k10_w05                  24.7100       6.1010     200

    Transfer Strength (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    no_prediction                       31.4229      19.3136     200
    prediction_disabled_current         32.2415      19.1012     200
    prediction_k0_w025                  33.0179      18.5153     200
    prediction_k3_w025                  32.9979      18.5087     200
    prediction_k5_w025                  32.6606      18.6540     200
    prediction_k10_w025                 32.2791      18.8562     200
    prediction_k3_w05                   35.2046      17.8705     200
    prediction_k5_w05                   34.8832      18.0161     200
    prediction_k10_w05                  33.0716      18.6107     200

    Transfer Precision (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    no_prediction                        0.8501       0.0969     200
    prediction_disabled_current          0.8421       0.1102     200
    prediction_k0_w025                   0.8416       0.1121     200
    prediction_k3_w025                   0.8423       0.1122     200
    prediction_k5_w025                   0.8427       0.1115     200
    prediction_k10_w025                  0.8431       0.1114     200
    prediction_k3_w05                    0.8413       0.1122     200
    prediction_k5_w05                    0.8425       0.1117     200
    prediction_k10_w05                   0.8429       0.1115     200

    Hazard Steps (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    no_prediction                        0.0000       0.0000     200
    prediction_disabled_current          0.0000       0.0000     200
    prediction_k0_w025                   0.0000       0.0000     200
    prediction_k3_w025                   0.0000       0.0000     200
    prediction_k5_w025                   0.0000       0.0000     200
    prediction_k10_w025                  0.0000       0.0000     200
    prediction_k3_w05                    0.0000       0.0000     200
    prediction_k5_w05                    0.0000       0.0000     200
    prediction_k10_w05                   0.0000       0.0000     200

  ====================================================================================================
  Target: rules
  ====================================================================================================

    First TASK_SUCCESS Tick (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    no_prediction                        6.5150       5.8799     200
    prediction_disabled_current          6.8650       5.9188     200
    prediction_k0_w025                   6.8400       5.9186     200
    prediction_k3_w025                   6.8400       5.9186     200
    prediction_k5_w025                   6.8400       5.9186     200
    prediction_k10_w025                  6.8400       5.9186     200
    prediction_k3_w05                    6.8450       5.9149     200
    prediction_k5_w05                    6.8450       5.9149     200
    prediction_k10_w05                   6.8400       5.9186     200

    Task Completion Rate (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    no_prediction                        0.8150       0.3893     200
    prediction_disabled_current          0.8050       0.3972     200
    prediction_k0_w025                   0.8050       0.3972     200
    prediction_k3_w025                   0.8050       0.3972     200
    prediction_k5_w025                   0.8050       0.3972     200
    prediction_k10_w025                  0.8050       0.3972     200
    prediction_k3_w05                    0.8050       0.3972     200
    prediction_k5_w05                    0.8050       0.3972     200
    prediction_k10_w05                   0.8050       0.3972     200

    Contradictions (TASK_FAILURE count) (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    no_prediction                        1.5300       1.2026     200
    prediction_disabled_current          1.8200       1.3955     200
    prediction_k0_w025                   1.8100       1.3941     200
    prediction_k3_w025                   1.8100       1.3941     200
    prediction_k5_w025                   1.8100       1.3941     200
    prediction_k10_w025                  1.8100       1.3941     200
    prediction_k3_w05                    1.8150       1.4180     200
    prediction_k5_w05                    1.8150       1.4180     200
    prediction_k10_w05                   1.8100       1.3941     200

    Total Reward (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    no_prediction                        3.6397       1.6094     200
    prediction_disabled_current          3.5800       1.6318     200
    prediction_k0_w025                   3.5856       1.6346     200
    prediction_k3_w025                   3.5856       1.6346     200
    prediction_k5_w025                   3.5856       1.6346     200
    prediction_k10_w025                  3.5837       1.6336     200
    prediction_k3_w05                    3.5930       1.6382     200
    prediction_k5_w05                    3.5930       1.6382     200
    prediction_k10_w05                   3.5899       1.6367     200

    Invalid Actions (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    no_prediction                        1.5300       1.2026     200
    prediction_disabled_current          1.8200       1.3955     200
    prediction_k0_w025                   1.8100       1.3941     200
    prediction_k3_w025                   1.8100       1.3941     200
    prediction_k5_w025                   1.8100       1.3941     200
    prediction_k10_w025                  1.8100       1.3941     200
    prediction_k3_w05                    1.8150       1.4180     200
    prediction_k5_w05                    1.8150       1.4180     200
    prediction_k10_w05                   1.8100       1.3941     200

    Final Energy (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    no_prediction                      134.2547      13.1137     200
    prediction_disabled_current        136.7835      14.8894     200
    prediction_k0_w025                 136.4146      14.6125     200
    prediction_k3_w025                 136.4146      14.6125     200
    prediction_k5_w025                 136.4146      14.6125     200
    prediction_k10_w025                136.4256      14.6079     200
    prediction_k3_w05                  136.1100      14.5758     200
    prediction_k5_w05                  136.1100      14.5758     200
    prediction_k10_w05                 136.1764      14.5387     200

    Prediction Error (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    no_prediction                        0.5486       0.2706     200
    prediction_disabled_current          0.8449       0.3700     200
    prediction_k0_w025                   0.8498       0.3726     200
    prediction_k3_w025                   0.8498       0.3726     200
    prediction_k5_w025                   0.8498       0.3726     200
    prediction_k10_w025                  0.8483       0.3715     200
    prediction_k3_w05                    0.8577       0.3770     200
    prediction_k5_w05                    0.8577       0.3770     200
    prediction_k10_w05                   0.8554       0.3755     200

    Transfer Uses (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    no_prediction                       27.5900       5.4489     200
    prediction_disabled_current         24.6400       6.1326     200
    prediction_k0_w025                  24.7150       6.1867     200
    prediction_k3_w025                  24.7150       6.1867     200
    prediction_k5_w025                  24.7150       6.1867     200
    prediction_k10_w025                 24.7150       6.1867     200
    prediction_k3_w05                   24.7250       6.1587     200
    prediction_k5_w05                   24.7250       6.1587     200
    prediction_k10_w05                  24.7200       6.1890     200

    Transfer Strength (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    no_prediction                       30.4641      14.9416     200
    prediction_disabled_current         27.2195      13.1370     200
    prediction_k0_w025                  27.1523      13.1983     200
    prediction_k3_w025                  27.1523      13.1983     200
    prediction_k5_w025                  27.1523      13.1983     200
    prediction_k10_w025                 27.1523      13.1983     200
    prediction_k3_w05                   27.0599      13.1768     200
    prediction_k5_w05                   27.0599      13.1768     200
    prediction_k10_w05                  27.0777      13.1989     200

    Transfer Precision (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    no_prediction                        0.8966       0.0801     200
    prediction_disabled_current          0.8781       0.0925     200
    prediction_k0_w025                   0.8789       0.0922     200
    prediction_k3_w025                   0.8789       0.0922     200
    prediction_k5_w025                   0.8789       0.0922     200
    prediction_k10_w025                  0.8790       0.0921     200
    prediction_k3_w05                    0.8788       0.0925     200
    prediction_k5_w05                    0.8788       0.0925     200
    prediction_k10_w05                   0.8786       0.0926     200

    Hazard Steps (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    no_prediction                        0.0000       0.0000     200
    prediction_disabled_current          0.0000       0.0000     200
    prediction_k0_w025                   0.0000       0.0000     200
    prediction_k3_w025                   0.0000       0.0000     200
    prediction_k5_w025                   0.0000       0.0000     200
    prediction_k10_w025                  0.0000       0.0000     200
    prediction_k3_w05                    0.0000       0.0000     200
    prediction_k5_w05                    0.0000       0.0000     200
    prediction_k10_w05                   0.0000       0.0000     200

  ====================================================================================================
  Target: hazard
  ====================================================================================================

    First TASK_SUCCESS Tick (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    no_prediction                       10.5700       5.3936     200
    prediction_disabled_current         10.7000       5.4937     200
    prediction_k0_w025                  10.9600       5.4532     200
    prediction_k3_w025                  10.9600       5.4532     200
    prediction_k5_w025                  10.9600       5.4532     200
    prediction_k10_w025                 10.9600       5.4532     200
    prediction_k3_w05                   11.0400       5.3761     200
    prediction_k5_w05                   11.0400       5.3761     200
    prediction_k10_w05                  11.0300       5.3893     200

    Task Completion Rate (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    no_prediction                        0.6000       0.4911     200
    prediction_disabled_current          0.5750       0.4956     200
    prediction_k0_w025                   0.5550       0.4982     200
    prediction_k3_w025                   0.5550       0.4982     200
    prediction_k5_w025                   0.5550       0.4982     200
    prediction_k10_w025                  0.5550       0.4982     200
    prediction_k3_w05                    0.5550       0.4982     200
    prediction_k5_w05                    0.5550       0.4982     200
    prediction_k10_w05                   0.5550       0.4982     200

    Contradictions (TASK_FAILURE count) (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    no_prediction                        0.4200       0.5147     200
    prediction_disabled_current          0.4800       0.5487     200
    prediction_k0_w025                   0.4850       0.5489     200
    prediction_k3_w025                   0.4850       0.5489     200
    prediction_k5_w025                   0.4850       0.5489     200
    prediction_k10_w025                  0.4800       0.5487     200
    prediction_k3_w05                    0.4700       0.5483     200
    prediction_k5_w05                    0.4700       0.5483     200
    prediction_k10_w05                   0.4750       0.5666     200

    Total Reward (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    no_prediction                        4.3380       3.0021     200
    prediction_disabled_current          4.1555       2.9982     200
    prediction_k0_w025                   4.0367       3.0107     200
    prediction_k3_w025                   4.0373       3.0100     200
    prediction_k5_w025                   4.0340       3.0136     200
    prediction_k10_w025                  4.0320       3.0113     200
    prediction_k3_w05                    4.0454       3.0133     200
    prediction_k5_w05                    4.0421       3.0170     200
    prediction_k10_w05                   4.0296       3.0051     200

    Invalid Actions (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    no_prediction                        0.4200       0.5147     200
    prediction_disabled_current          0.4800       0.5487     200
    prediction_k0_w025                   0.4850       0.5489     200
    prediction_k3_w025                   0.4850       0.5489     200
    prediction_k5_w025                   0.4850       0.5489     200
    prediction_k10_w025                  0.4800       0.5487     200
    prediction_k3_w05                    0.4700       0.5483     200
    prediction_k5_w05                    0.4700       0.5483     200
    prediction_k10_w05                   0.4750       0.5666     200

    Final Energy (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    no_prediction                      139.7490      13.1857     200
    prediction_disabled_current        142.8361      14.8828     200
    prediction_k0_w025                 142.3307      14.4454     200
    prediction_k3_w025                 142.3313      14.4458     200
    prediction_k5_w025                 142.3280      14.4477     200
    prediction_k10_w025                142.3410      14.4614     200
    prediction_k3_w05                  142.1389      14.3497     200
    prediction_k5_w05                  142.1356      14.3516     200
    prediction_k10_w05                 142.1401      14.3167     200

    Prediction Error (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    no_prediction                        0.3732       0.2278     200
    prediction_disabled_current          0.4694       0.3596     200
    prediction_k0_w025                   0.4654       0.3658     200
    prediction_k3_w025                   0.4654       0.3658     200
    prediction_k5_w025                   0.4646       0.3656     200
    prediction_k10_w025                  0.4638       0.3643     200
    prediction_k3_w05                    0.4654       0.3691     200
    prediction_k5_w05                    0.4646       0.3688     200
    prediction_k10_w05                   0.4641       0.3673     200

    Transfer Uses (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    no_prediction                       26.2700       5.2301     200
    prediction_disabled_current         25.4350       5.6795     200
    prediction_k0_w025                  25.4100       5.6232     200
    prediction_k3_w025                  25.4100       5.6232     200
    prediction_k5_w025                  25.4400       5.6530     200
    prediction_k10_w025                 25.4250       5.6661     200
    prediction_k3_w05                   25.3450       5.6804     200
    prediction_k5_w05                   25.3750       5.7103     200
    prediction_k10_w05                  25.3450       5.6627     200

    Transfer Strength (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    no_prediction                       60.0795      26.9128     200
    prediction_disabled_current         58.1840      25.9833     200
    prediction_k0_w025                  57.0405      24.8322     200
    prediction_k3_w025                  57.0405      24.8322     200
    prediction_k5_w025                  57.0752      24.8119     200
    prediction_k10_w025                 57.1189      24.8452     200
    prediction_k3_w05                   56.2301      24.3688     200
    prediction_k5_w05                   56.2648      24.3493     200
    prediction_k10_w05                  56.3184      24.1019     200

    Transfer Precision (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    no_prediction                        0.9716       0.0349     200
    prediction_disabled_current          0.9683       0.0363     200
    prediction_k0_w025                   0.9676       0.0365     200
    prediction_k3_w025                   0.9676       0.0365     200
    prediction_k5_w025                   0.9676       0.0365     200
    prediction_k10_w025                  0.9679       0.0364     200
    prediction_k3_w05                    0.9688       0.0362     200
    prediction_k5_w05                    0.9688       0.0362     200
    prediction_k10_w05                   0.9684       0.0375     200

    Hazard Steps (raw means):
    Condition                              Mean          Std       n
    ------------------------------ ------------ ------------  ------
    no_prediction                        0.4200       0.5147     200
    prediction_disabled_current          0.4800       0.5487     200
    prediction_k0_w025                   0.4850       0.5489     200
    prediction_k3_w025                   0.4850       0.5489     200
    prediction_k5_w025                   0.4850       0.5489     200
    prediction_k10_w025                  0.4800       0.5487     200
    prediction_k3_w05                    0.4700       0.5483     200
    prediction_k5_w05                    0.4700       0.5483     200
    prediction_k10_w05                   0.4750       0.5666     200
```

```

  ====================================================================================================
  Target: logic — Comparison vs prediction_disabled_current
  ====================================================================================================

    First TASK_SUCCESS Tick:
    Condition                       Cond Mean  Base Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    no_prediction                       9.815      9.775    +0.0400        [-0.658, 0.738]   0.910623        0.008
    prediction_k0_w025                  9.345      9.775    -0.4300       [-0.707, -0.153]   0.002377 **    -0.215
    prediction_k3_w025                  9.355      9.775    -0.4200       [-0.695, -0.145]   0.002780 **    -0.212
    prediction_k5_w025                  9.510      9.775    -0.2650       [-0.476, -0.054]   0.014007 *     -0.174
    prediction_k10_w025                 9.660      9.775    -0.1150        [-0.254, 0.024]   0.105053       -0.115
    prediction_k3_w05                   8.445      9.775    -1.3300       [-1.759, -0.901]   0.000000 ***   -0.430
    prediction_k5_w05                   8.575      9.775    -1.2000       [-1.594, -0.806]   0.000000 ***   -0.422
    prediction_k10_w05                  9.290      9.775    -0.4850       [-0.688, -0.282]   0.000003 ***   -0.332

    Task Completion Rate:
    Condition                       Cond Mean  Base Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    no_prediction                       0.530      0.530    +0.0000        [-0.054, 0.054]   1.000000        0.000
    prediction_k0_w025                  0.580      0.530    +0.0500         [0.017, 0.083]   0.003267 **     0.208
    prediction_k3_w025                  0.580      0.530    +0.0500         [0.017, 0.083]   0.003267 **     0.208
    prediction_k5_w025                  0.575      0.530    +0.0450         [0.013, 0.077]   0.005815 **     0.195
    prediction_k10_w025                 0.570      0.530    +0.0400         [0.009, 0.071]   0.010322 *      0.181
    prediction_k3_w05                   0.685      0.530    +0.1550         [0.105, 0.205]   0.000000 ***    0.427
    prediction_k5_w05                   0.680      0.530    +0.1500         [0.100, 0.200]   0.000000 ***    0.419
    prediction_k10_w05                  0.650      0.530    +0.1200         [0.073, 0.167]   0.000001 ***    0.352

    Contradictions (TASK_FAILURE count):
    Condition                       Cond Mean  Base Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    no_prediction                       1.000      1.090    -0.0900        [-0.193, 0.013]   0.087453       -0.121
    prediction_k0_w025                  1.085      1.090    -0.0050        [-0.046, 0.036]   0.808808       -0.017
    prediction_k3_w025                  1.080      1.090    -0.0100        [-0.052, 0.032]   0.638008       -0.033
    prediction_k5_w025                  1.100      1.090    +0.0100        [-0.018, 0.038]   0.480051        0.050
    prediction_k10_w025                 1.095      1.090    +0.0050        [-0.017, 0.027]   0.655368        0.032
    prediction_k3_w05                   1.075      1.090    -0.0150        [-0.062, 0.032]   0.532241       -0.044
    prediction_k5_w05                   1.095      1.090    +0.0050        [-0.030, 0.040]   0.782004        0.020
    prediction_k10_w05                  1.100      1.090    +0.0100        [-0.021, 0.041]   0.527711        0.045

    Total Reward:
    Condition                       Cond Mean  Base Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    no_prediction                       2.889      2.882    +0.0066        [-0.224, 0.238]   0.954996        0.004
    prediction_k0_w025                  3.097      2.882    +0.2152         [0.077, 0.354]   0.002354 **     0.215
    prediction_k3_w025                  3.097      2.882    +0.2149         [0.076, 0.354]   0.002394 **     0.215
    prediction_k5_w025                  3.074      2.882    +0.1920         [0.060, 0.324]   0.004464 **     0.201
    prediction_k10_w025                 3.059      2.882    +0.1767         [0.051, 0.303]   0.006005 **     0.194
    prediction_k3_w05                   3.532      2.882    +0.6495         [0.440, 0.859]   0.000000 ***    0.431
    prediction_k5_w05                   3.509      2.882    +0.6272         [0.421, 0.833]   0.000000 ***    0.422
    prediction_k10_w05                  3.390      2.882    +0.5083         [0.314, 0.702]   0.000000 ***    0.363

    Invalid Actions:
    Condition                       Cond Mean  Base Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    no_prediction                       1.615      1.675    -0.0600        [-0.184, 0.064]   0.342903       -0.067
    prediction_k0_w025                  1.695      1.675    +0.0200        [-0.024, 0.064]   0.371334        0.063
    prediction_k3_w025                  1.690      1.675    +0.0150        [-0.030, 0.060]   0.513295        0.046
    prediction_k5_w025                  1.700      1.675    +0.0250        [-0.018, 0.068]   0.250973        0.081
    prediction_k10_w025                 1.680      1.675    +0.0050        [-0.024, 0.034]   0.739443        0.024
    prediction_k3_w05                   1.695      1.675    +0.0200        [-0.030, 0.070]   0.433212        0.055
    prediction_k5_w05                   1.700      1.675    +0.0250        [-0.024, 0.074]   0.317311        0.071
    prediction_k10_w05                  1.690      1.675    +0.0150        [-0.020, 0.050]   0.405743        0.059

    Final Energy:
    Condition                       Cond Mean  Base Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    no_prediction                     136.976    140.282    -3.3058       [-4.621, -1.991]   0.000001 ***   -0.348
    prediction_k0_w025                140.028    140.282    -0.2537        [-0.540, 0.033]   0.082785       -0.123
    prediction_k3_w025                140.035    140.282    -0.2471        [-0.534, 0.040]   0.091127       -0.119
    prediction_k5_w025                140.018    140.282    -0.2645        [-0.549, 0.020]   0.068264       -0.129
    prediction_k10_w025               140.032    140.282    -0.2497        [-0.531, 0.032]   0.081887       -0.123
    prediction_k3_w05                 140.140    140.282    -0.1425        [-0.486, 0.201]   0.416285       -0.057
    prediction_k5_w05                 140.121    140.282    -0.1613        [-0.503, 0.180]   0.354486       -0.065
    prediction_k10_w05                140.089    140.282    -0.1927        [-0.525, 0.139]   0.255338       -0.080

    Prediction Error:
    Condition                       Cond Mean  Base Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    no_prediction                       0.311      0.404    -0.0931       [-0.124, -0.062]   0.000000 ***   -0.417
    prediction_k0_w025                  0.432      0.404    +0.0280         [0.013, 0.043]   0.000357 ***    0.252
    prediction_k3_w025                  0.432      0.404    +0.0274         [0.012, 0.043]   0.000458 ***    0.248
    prediction_k5_w025                  0.428      0.404    +0.0239         [0.010, 0.038]   0.000986 ***    0.233
    prediction_k10_w025                 0.424      0.404    +0.0198         [0.007, 0.032]   0.002239 **     0.216
    prediction_k3_w05                   0.486      0.404    +0.0816         [0.057, 0.106]   0.000000 ***    0.463
    prediction_k5_w05                   0.484      0.404    +0.0797         [0.055, 0.104]   0.000000 ***    0.456
    prediction_k10_w05                  0.463      0.404    +0.0588         [0.038, 0.079]   0.000000 ***    0.395

    Transfer Uses:
    Condition                       Cond Mean  Base Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    no_prediction                      24.980     24.450    +0.5300        [-0.118, 1.178]   0.109139        0.113
    prediction_k0_w025                 24.665     24.450    +0.2150         [0.062, 0.368]   0.006009 **     0.194
    prediction_k3_w025                 24.660     24.450    +0.2100         [0.057, 0.363]   0.006983 **     0.191
    prediction_k5_w025                 24.595     24.450    +0.1450         [0.013, 0.277]   0.031446 *      0.152
    prediction_k10_w025                24.530     24.450    +0.0800        [-0.005, 0.165]   0.064842        0.131
    prediction_k3_w05                  25.180     24.450    +0.7300         [0.465, 0.995]   0.000000 ***    0.382
    prediction_k5_w05                  25.110     24.450    +0.6600         [0.412, 0.908]   0.000000 ***    0.368
    prediction_k10_w05                 24.710     24.450    +0.2600         [0.115, 0.405]   0.000450 ***    0.248

    Transfer Strength:
    Condition                       Cond Mean  Base Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    no_prediction                      31.423     32.242    -0.8186        [-2.874, 1.237]   0.435026       -0.055
    prediction_k0_w025                 33.018     32.242    +0.7764         [0.120, 1.432]   0.020373 *      0.164
    prediction_k3_w025                 32.998     32.242    +0.7564         [0.107, 1.406]   0.022398 *      0.161
    prediction_k5_w025                 32.661     32.242    +0.4190        [-0.118, 0.956]   0.126181        0.108
    prediction_k10_w025                32.279     32.242    +0.0376        [-0.324, 0.399]   0.838339        0.014
    prediction_k3_w05                  35.205     32.242    +2.9630         [1.914, 4.012]   0.000000 ***    0.392
    prediction_k5_w05                  34.883     32.242    +2.6417         [1.671, 3.612]   0.000000 ***    0.377
    prediction_k10_w05                 33.072     32.242    +0.8301         [0.334, 1.326]   0.001036 **     0.232

    Transfer Precision:
    Condition                       Cond Mean  Base Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    no_prediction                       0.850      0.842    +0.0080        [-0.002, 0.018]   0.113916        0.112
    prediction_k0_w025                  0.842      0.842    -0.0005        [-0.004, 0.003]   0.777172       -0.020
    prediction_k3_w025                  0.842      0.842    +0.0002        [-0.003, 0.004]   0.903235        0.009
    prediction_k5_w025                  0.843      0.842    +0.0006        [-0.003, 0.004]   0.726423        0.025
    prediction_k10_w025                 0.843      0.842    +0.0010        [-0.002, 0.004]   0.432651        0.055
    prediction_k3_w05                   0.841      0.842    -0.0008        [-0.005, 0.003]   0.707344       -0.027
    prediction_k5_w05                   0.842      0.842    +0.0004        [-0.004, 0.005]   0.848635        0.013
    prediction_k10_w05                  0.843      0.842    +0.0009        [-0.002, 0.004]   0.578409        0.039

    Hazard Steps:
    Condition                       Cond Mean  Base Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    no_prediction                       0.000      0.000    +0.0000         [0.000, 0.000]   1.000000        0.000
    prediction_k0_w025                  0.000      0.000    +0.0000         [0.000, 0.000]   1.000000        0.000
    prediction_k3_w025                  0.000      0.000    +0.0000         [0.000, 0.000]   1.000000        0.000
    prediction_k5_w025                  0.000      0.000    +0.0000         [0.000, 0.000]   1.000000        0.000
    prediction_k10_w025                 0.000      0.000    +0.0000         [0.000, 0.000]   1.000000        0.000
    prediction_k3_w05                   0.000      0.000    +0.0000         [0.000, 0.000]   1.000000        0.000
    prediction_k5_w05                   0.000      0.000    +0.0000         [0.000, 0.000]   1.000000        0.000
    prediction_k10_w05                  0.000      0.000    +0.0000         [0.000, 0.000]   1.000000        0.000

  ====================================================================================================
  Target: rules — Comparison vs prediction_disabled_current
  ====================================================================================================

    First TASK_SUCCESS Tick:
    Condition                       Cond Mean  Base Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    no_prediction                       6.515      6.865    -0.3500        [-1.058, 0.358]   0.332315       -0.069
    prediction_k0_w025                  6.840      6.865    -0.0250        [-0.109, 0.059]   0.559058       -0.041
    prediction_k3_w025                  6.840      6.865    -0.0250        [-0.109, 0.059]   0.559058       -0.041
    prediction_k5_w025                  6.840      6.865    -0.0250        [-0.109, 0.059]   0.559058       -0.041
    prediction_k10_w025                 6.840      6.865    -0.0250        [-0.109, 0.059]   0.559058       -0.041
    prediction_k3_w05                   6.845      6.865    -0.0200        [-0.107, 0.067]   0.651263       -0.032
    prediction_k5_w05                   6.845      6.865    -0.0200        [-0.107, 0.067]   0.651263       -0.032
    prediction_k10_w05                  6.840      6.865    -0.0250        [-0.109, 0.059]   0.559058       -0.041

    Task Completion Rate:
    Condition                       Cond Mean  Base Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    no_prediction                       0.815      0.805    +0.0100        [-0.038, 0.058]   0.683717        0.029
    prediction_k0_w025                  0.805      0.805    +0.0000         [0.000, 0.000]   1.000000        0.000
    prediction_k3_w025                  0.805      0.805    +0.0000         [0.000, 0.000]   1.000000        0.000
    prediction_k5_w025                  0.805      0.805    +0.0000         [0.000, 0.000]   1.000000        0.000
    prediction_k10_w025                 0.805      0.805    +0.0000         [0.000, 0.000]   1.000000        0.000
    prediction_k3_w05                   0.805      0.805    +0.0000         [0.000, 0.000]   1.000000        0.000
    prediction_k5_w05                   0.805      0.805    +0.0000         [0.000, 0.000]   1.000000        0.000
    prediction_k10_w05                  0.805      0.805    +0.0000         [0.000, 0.000]   1.000000        0.000

    Contradictions (TASK_FAILURE count):
    Condition                       Cond Mean  Base Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    no_prediction                       1.530      1.820    -0.2900       [-0.459, -0.121]   0.000791 ***   -0.237
    prediction_k0_w025                  1.810      1.820    -0.0100        [-0.024, 0.004]   0.156255       -0.100
    prediction_k3_w025                  1.810      1.820    -0.0100        [-0.024, 0.004]   0.156255       -0.100
    prediction_k5_w025                  1.810      1.820    -0.0100        [-0.024, 0.004]   0.156255       -0.100
    prediction_k10_w025                 1.810      1.820    -0.0100        [-0.024, 0.004]   0.156255       -0.100
    prediction_k3_w05                   1.815      1.820    -0.0050        [-0.043, 0.033]   0.796719       -0.018
    prediction_k5_w05                   1.815      1.820    -0.0050        [-0.043, 0.033]   0.796719       -0.018
    prediction_k10_w05                  1.810      1.820    -0.0100        [-0.024, 0.004]   0.156255       -0.100

    Total Reward:
    Condition                       Cond Mean  Base Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    no_prediction                       3.640      3.580    +0.0597        [-0.137, 0.256]   0.551044        0.042
    prediction_k0_w025                  3.586      3.580    +0.0056         [0.003, 0.008]   0.000000 ***    0.361
    prediction_k3_w025                  3.586      3.580    +0.0056         [0.003, 0.008]   0.000000 ***    0.361
    prediction_k5_w025                  3.586      3.580    +0.0056         [0.003, 0.008]   0.000000 ***    0.361
    prediction_k10_w025                 3.584      3.580    +0.0037         [0.002, 0.006]   0.000264 ***    0.258
    prediction_k3_w05                   3.593      3.580    +0.0130         [0.010, 0.016]   0.000000 ***    0.673
    prediction_k5_w05                   3.593      3.580    +0.0130         [0.010, 0.016]   0.000000 ***    0.673
    prediction_k10_w05                  3.590      3.580    +0.0100         [0.007, 0.012]   0.000000 ***    0.547

    Invalid Actions:
    Condition                       Cond Mean  Base Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    no_prediction                       1.530      1.820    -0.2900       [-0.459, -0.121]   0.000791 ***   -0.237
    prediction_k0_w025                  1.810      1.820    -0.0100        [-0.024, 0.004]   0.156255       -0.100
    prediction_k3_w025                  1.810      1.820    -0.0100        [-0.024, 0.004]   0.156255       -0.100
    prediction_k5_w025                  1.810      1.820    -0.0100        [-0.024, 0.004]   0.156255       -0.100
    prediction_k10_w025                 1.810      1.820    -0.0100        [-0.024, 0.004]   0.156255       -0.100
    prediction_k3_w05                   1.815      1.820    -0.0050        [-0.043, 0.033]   0.796719       -0.018
    prediction_k5_w05                   1.815      1.820    -0.0050        [-0.043, 0.033]   0.796719       -0.018
    prediction_k10_w05                  1.810      1.820    -0.0100        [-0.024, 0.004]   0.156255       -0.100

    Final Energy:
    Condition                       Cond Mean  Base Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    no_prediction                     134.255    136.784    -2.5288       [-3.966, -1.091]   0.000565 ***   -0.244
    prediction_k0_w025                136.415    136.784    -0.3689       [-0.628, -0.110]   0.005195 **    -0.198
    prediction_k3_w025                136.415    136.784    -0.3689       [-0.628, -0.110]   0.005195 **    -0.198
    prediction_k5_w025                136.415    136.784    -0.3689       [-0.628, -0.110]   0.005195 **    -0.198
    prediction_k10_w025               136.426    136.784    -0.3579       [-0.616, -0.099]   0.006650 **    -0.192
    prediction_k3_w05                 136.110    136.784    -0.6735       [-1.001, -0.346]   0.000057 ***   -0.285
    prediction_k5_w05                 136.110    136.784    -0.6735       [-1.001, -0.346]   0.000057 ***   -0.285
    prediction_k10_w05                136.176    136.784    -0.6070       [-0.918, -0.296]   0.000133 ***   -0.270

    Prediction Error:
    Condition                       Cond Mean  Base Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    no_prediction                       0.549      0.845    -0.2963       [-0.348, -0.244]   0.000000 ***   -0.789
    prediction_k0_w025                  0.850      0.845    +0.0049         [0.001, 0.009]   0.011870 *      0.178
    prediction_k3_w025                  0.850      0.845    +0.0049         [0.001, 0.009]   0.011870 *      0.178
    prediction_k5_w025                  0.850      0.845    +0.0049         [0.001, 0.009]   0.011870 *      0.178
    prediction_k10_w025                 0.848      0.845    +0.0034        [-0.000, 0.007]   0.079422        0.124
    prediction_k3_w05                   0.858      0.845    +0.0128         [0.008, 0.017]   0.000000 ***    0.402
    prediction_k5_w05                   0.858      0.845    +0.0128         [0.008, 0.017]   0.000000 ***    0.402
    prediction_k10_w05                  0.855      0.845    +0.0105         [0.006, 0.015]   0.000003 ***    0.331

    Transfer Uses:
    Condition                       Cond Mean  Base Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    no_prediction                      27.590     24.640    +2.9500         [2.145, 3.755]   0.000000 ***    0.508
    prediction_k0_w025                 24.715     24.640    +0.0750        [-0.008, 0.158]   0.077585        0.125
    prediction_k3_w025                 24.715     24.640    +0.0750        [-0.008, 0.158]   0.077585        0.125
    prediction_k5_w025                 24.715     24.640    +0.0750        [-0.008, 0.158]   0.077585        0.125
    prediction_k10_w025                24.715     24.640    +0.0750        [-0.008, 0.158]   0.077585        0.125
    prediction_k3_w05                  24.725     24.640    +0.0850        [-0.071, 0.241]   0.286904        0.075
    prediction_k5_w05                  24.725     24.640    +0.0850        [-0.071, 0.241]   0.286904        0.075
    prediction_k10_w05                 24.720     24.640    +0.0800        [-0.004, 0.164]   0.061267        0.132

    Transfer Strength:
    Condition                       Cond Mean  Base Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    no_prediction                      30.464     27.220    +3.2445         [1.213, 5.276]   0.001750 **     0.221
    prediction_k0_w025                 27.152     27.220    -0.0672        [-0.313, 0.178]   0.591492       -0.038
    prediction_k3_w025                 27.152     27.220    -0.0672        [-0.313, 0.178]   0.591492       -0.038
    prediction_k5_w025                 27.152     27.220    -0.0672        [-0.313, 0.178]   0.591492       -0.038
    prediction_k10_w025                27.152     27.220    -0.0672        [-0.313, 0.178]   0.591492       -0.038
    prediction_k3_w05                  27.060     27.220    -0.1596        [-0.427, 0.108]   0.242003       -0.083
    prediction_k5_w05                  27.060     27.220    -0.1596        [-0.427, 0.108]   0.242003       -0.083
    prediction_k10_w05                 27.078     27.220    -0.1418        [-0.397, 0.113]   0.275505       -0.077

    Transfer Precision:
    Condition                       Cond Mean  Base Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    no_prediction                       0.897      0.878    +0.0185         [0.007, 0.030]   0.001358 **     0.227
    prediction_k0_w025                  0.879      0.878    +0.0008        [-0.001, 0.002]   0.250605        0.081
    prediction_k3_w025                  0.879      0.878    +0.0008        [-0.001, 0.002]   0.250605        0.081
    prediction_k5_w025                  0.879      0.878    +0.0008        [-0.001, 0.002]   0.250605        0.081
    prediction_k10_w025                 0.879      0.878    +0.0009        [-0.000, 0.002]   0.185061        0.094
    prediction_k3_w05                   0.879      0.878    +0.0007        [-0.002, 0.004]   0.663339        0.031
    prediction_k5_w05                   0.879      0.878    +0.0007        [-0.002, 0.004]   0.663339        0.031
    prediction_k10_w05                  0.879      0.878    +0.0006        [-0.001, 0.002]   0.432130        0.056

    Hazard Steps:
    Condition                       Cond Mean  Base Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    no_prediction                       0.000      0.000    +0.0000         [0.000, 0.000]   1.000000        0.000
    prediction_k0_w025                  0.000      0.000    +0.0000         [0.000, 0.000]   1.000000        0.000
    prediction_k3_w025                  0.000      0.000    +0.0000         [0.000, 0.000]   1.000000        0.000
    prediction_k5_w025                  0.000      0.000    +0.0000         [0.000, 0.000]   1.000000        0.000
    prediction_k10_w025                 0.000      0.000    +0.0000         [0.000, 0.000]   1.000000        0.000
    prediction_k3_w05                   0.000      0.000    +0.0000         [0.000, 0.000]   1.000000        0.000
    prediction_k5_w05                   0.000      0.000    +0.0000         [0.000, 0.000]   1.000000        0.000
    prediction_k10_w05                  0.000      0.000    +0.0000         [0.000, 0.000]   1.000000        0.000

  ====================================================================================================
  Target: hazard — Comparison vs prediction_disabled_current
  ====================================================================================================

    First TASK_SUCCESS Tick:
    Condition                       Cond Mean  Base Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    no_prediction                      10.570     10.700    -0.1300        [-0.854, 0.594]   0.724937       -0.025
    prediction_k0_w025                 10.960     10.700    +0.2600        [-0.047, 0.567]   0.097276        0.117
    prediction_k3_w025                 10.960     10.700    +0.2600        [-0.047, 0.567]   0.097276        0.117
    prediction_k5_w025                 10.960     10.700    +0.2600        [-0.047, 0.567]   0.097276        0.117
    prediction_k10_w025                10.960     10.700    +0.2600        [-0.047, 0.567]   0.097276        0.117
    prediction_k3_w05                  11.040     10.700    +0.3400         [0.040, 0.640]   0.026527 *      0.157
    prediction_k5_w05                  11.040     10.700    +0.3400         [0.040, 0.640]   0.026527 *      0.157
    prediction_k10_w05                 11.030     10.700    +0.3300         [0.022, 0.638]   0.035861 *      0.148

    Task Completion Rate:
    Condition                       Cond Mean  Base Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    no_prediction                       0.600      0.575    +0.0250        [-0.036, 0.086]   0.423757        0.057
    prediction_k0_w025                  0.555      0.575    -0.0200        [-0.044, 0.004]   0.101031       -0.116
    prediction_k3_w025                  0.555      0.575    -0.0200        [-0.044, 0.004]   0.101031       -0.116
    prediction_k5_w025                  0.555      0.575    -0.0200        [-0.044, 0.004]   0.101031       -0.116
    prediction_k10_w025                 0.555      0.575    -0.0200        [-0.044, 0.004]   0.101031       -0.116
    prediction_k3_w05                   0.555      0.575    -0.0200        [-0.044, 0.004]   0.101031       -0.116
    prediction_k5_w05                   0.555      0.575    -0.0200        [-0.044, 0.004]   0.101031       -0.116
    prediction_k10_w05                  0.555      0.575    -0.0200        [-0.044, 0.004]   0.101031       -0.116

    Contradictions (TASK_FAILURE count):
    Condition                       Cond Mean  Base Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    no_prediction                       0.420      0.480    -0.0600        [-0.129, 0.009]   0.088170       -0.121
    prediction_k0_w025                  0.485      0.480    +0.0050        [-0.021, 0.031]   0.706060        0.027
    prediction_k3_w025                  0.485      0.480    +0.0050        [-0.021, 0.031]   0.706060        0.027
    prediction_k5_w025                  0.485      0.480    +0.0050        [-0.021, 0.031]   0.706060        0.027
    prediction_k10_w025                 0.480      0.480    +0.0000        [-0.024, 0.024]   1.000000        0.000
    prediction_k3_w05                   0.470      0.480    -0.0100        [-0.041, 0.021]   0.527711       -0.045
    prediction_k5_w05                   0.470      0.480    -0.0100        [-0.041, 0.021]   0.527711       -0.045
    prediction_k10_w05                  0.475      0.480    -0.0050        [-0.040, 0.030]   0.782004       -0.020

    Total Reward:
    Condition                       Cond Mean  Base Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    no_prediction                       4.338      4.156    +0.1825        [-0.199, 0.564]   0.348486        0.066
    prediction_k0_w025                  4.037      4.156    -0.1188        [-0.285, 0.047]   0.159955       -0.099
    prediction_k3_w025                  4.037      4.156    -0.1182        [-0.284, 0.048]   0.162085       -0.099
    prediction_k5_w025                  4.034      4.156    -0.1216        [-0.287, 0.044]   0.150261       -0.102
    prediction_k10_w025                 4.032      4.156    -0.1235        [-0.289, 0.042]   0.143482       -0.103
    prediction_k3_w05                   4.045      4.156    -0.1101        [-0.276, 0.056]   0.194314       -0.092
    prediction_k5_w05                   4.042      4.156    -0.1134        [-0.280, 0.053]   0.180842       -0.095
    prediction_k10_w05                  4.030      4.156    -0.1260        [-0.292, 0.040]   0.135982       -0.105

    Invalid Actions:
    Condition                       Cond Mean  Base Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    no_prediction                       0.420      0.480    -0.0600        [-0.129, 0.009]   0.088170       -0.121
    prediction_k0_w025                  0.485      0.480    +0.0050        [-0.021, 0.031]   0.706060        0.027
    prediction_k3_w025                  0.485      0.480    +0.0050        [-0.021, 0.031]   0.706060        0.027
    prediction_k5_w025                  0.485      0.480    +0.0050        [-0.021, 0.031]   0.706060        0.027
    prediction_k10_w025                 0.480      0.480    +0.0000        [-0.024, 0.024]   1.000000        0.000
    prediction_k3_w05                   0.470      0.480    -0.0100        [-0.041, 0.021]   0.527711       -0.045
    prediction_k5_w05                   0.470      0.480    -0.0100        [-0.041, 0.021]   0.527711       -0.045
    prediction_k10_w05                  0.475      0.480    -0.0050        [-0.040, 0.030]   0.782004       -0.020

    Final Energy:
    Condition                       Cond Mean  Base Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    no_prediction                     139.749    142.836    -3.0871       [-4.502, -1.672]   0.000019 ***   -0.302
    prediction_k0_w025                142.331    142.836    -0.5053       [-0.891, -0.120]   0.010246 *     -0.182
    prediction_k3_w025                142.331    142.836    -0.5048       [-0.891, -0.119]   0.010339 *     -0.181
    prediction_k5_w025                142.328    142.836    -0.5081       [-0.894, -0.122]   0.009824 **    -0.183
    prediction_k10_w025               142.341    142.836    -0.4950       [-0.880, -0.110]   0.011759 *     -0.178
    prediction_k3_w05                 142.139    142.836    -0.6972       [-1.141, -0.254]   0.002064 **    -0.218
    prediction_k5_w05                 142.136    142.836    -0.7005       [-1.144, -0.257]   0.001959 **    -0.219
    prediction_k10_w05                142.140    142.836    -0.6960       [-1.145, -0.247]   0.002357 **    -0.215

    Prediction Error:
    Condition                       Cond Mean  Base Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    no_prediction                       0.373      0.469    -0.0962       [-0.139, -0.054]   0.000009 ***   -0.313
    prediction_k0_w025                  0.465      0.469    -0.0041        [-0.022, 0.013]   0.646409       -0.032
    prediction_k3_w025                  0.465      0.469    -0.0041        [-0.022, 0.013]   0.646409       -0.032
    prediction_k5_w025                  0.465      0.469    -0.0049        [-0.022, 0.013]   0.582724       -0.039
    prediction_k10_w025                 0.464      0.469    -0.0057        [-0.023, 0.012]   0.520399       -0.045
    prediction_k3_w05                   0.465      0.469    -0.0040        [-0.022, 0.014]   0.659015       -0.031
    prediction_k5_w05                   0.465      0.469    -0.0048        [-0.023, 0.013]   0.592195       -0.038
    prediction_k10_w05                  0.464      0.469    -0.0053        [-0.024, 0.013]   0.568964       -0.040

    Transfer Uses:
    Condition                       Cond Mean  Base Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    no_prediction                      26.270     25.435    +0.8350         [0.104, 1.566]   0.025158 *      0.158
    prediction_k0_w025                 25.410     25.435    -0.0250        [-0.213, 0.163]   0.794014       -0.018
    prediction_k3_w025                 25.410     25.435    -0.0250        [-0.213, 0.163]   0.794014       -0.018
    prediction_k5_w025                 25.440     25.435    +0.0050        [-0.173, 0.183]   0.956143        0.004
    prediction_k10_w025                25.425     25.435    -0.0100        [-0.186, 0.166]   0.911198       -0.008
    prediction_k3_w05                  25.345     25.435    -0.0900        [-0.293, 0.113]   0.384556       -0.061
    prediction_k5_w05                  25.375     25.435    -0.0600        [-0.254, 0.134]   0.545092       -0.043
    prediction_k10_w05                 25.345     25.435    -0.0900        [-0.272, 0.092]   0.331870       -0.069

    Transfer Strength:
    Condition                       Cond Mean  Base Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    no_prediction                      60.079     58.184    +1.8955        [-1.806, 5.597]   0.315528        0.071
    prediction_k0_w025                 57.041     58.184    -1.1435        [-2.754, 0.467]   0.164060       -0.098
    prediction_k3_w025                 57.041     58.184    -1.1435        [-2.754, 0.467]   0.164060       -0.098
    prediction_k5_w025                 57.075     58.184    -1.1088        [-2.719, 0.501]   0.176955       -0.095
    prediction_k10_w025                57.119     58.184    -1.0651        [-2.673, 0.543]   0.194178       -0.092
    prediction_k3_w05                  56.230     58.184    -1.9539       [-3.640, -0.267]   0.023159 *     -0.161
    prediction_k5_w05                  56.265     58.184    -1.9193       [-3.605, -0.233]   0.025659 *     -0.158
    prediction_k10_w05                 56.318     58.184    -1.8656       [-3.513, -0.219]   0.026411 *     -0.157

    Transfer Precision:
    Condition                       Cond Mean  Base Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    no_prediction                       0.972      0.968    +0.0033        [-0.001, 0.008]   0.156099        0.100
    prediction_k0_w025                  0.968      0.968    -0.0008        [-0.003, 0.001]   0.412355       -0.058
    prediction_k3_w025                  0.968      0.968    -0.0008        [-0.003, 0.001]   0.412355       -0.058
    prediction_k5_w025                  0.968      0.968    -0.0008        [-0.003, 0.001]   0.412355       -0.058
    prediction_k10_w025                 0.968      0.968    -0.0004        [-0.002, 0.001]   0.625152       -0.035
    prediction_k3_w05                   0.969      0.968    +0.0005        [-0.002, 0.003]   0.655345        0.032
    prediction_k5_w05                   0.969      0.968    +0.0005        [-0.002, 0.003]   0.655345        0.032
    prediction_k10_w05                  0.968      0.968    +0.0001        [-0.002, 0.002]   0.965939        0.003

    Hazard Steps:
    Condition                       Cond Mean  Base Mean      Delta                 95% CI          p        d
    ------------------------------ ---------- ---------- ---------- ---------------------- ---------- --------
    no_prediction                       0.420      0.480    -0.0600        [-0.129, 0.009]   0.088170       -0.121
    prediction_k0_w025                  0.485      0.480    +0.0050        [-0.021, 0.031]   0.706060        0.027
    prediction_k3_w025                  0.485      0.480    +0.0050        [-0.021, 0.031]   0.706060        0.027
    prediction_k5_w025                  0.485      0.480    +0.0050        [-0.021, 0.031]   0.706060        0.027
    prediction_k10_w025                 0.480      0.480    +0.0000        [-0.024, 0.024]   1.000000        0.000
    prediction_k3_w05                   0.470      0.480    -0.0100        [-0.041, 0.021]   0.527711       -0.045
    prediction_k5_w05                   0.470      0.480    -0.0100        [-0.041, 0.021]   0.527711       -0.045
    prediction_k10_w05                  0.475      0.480    -0.0050        [-0.040, 0.030]   0.782004       -0.020
```

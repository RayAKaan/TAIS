# Experiment Report: reverse_transfer

## Provenance

- **Timestamp (UTC):** 2026-06-08T22:42:03.380594+00:00
- **Python:** 3.14.4 (tags/v3.14.4:23116f9, Apr  7 2026, 14:10:54) [MSC v.1944 64 bit (AMD64)]
- **Platform:** Windows-11-10.0.26200-SP0
- **Git SHA:** dddffcc64868053ca8676fefb14d892b1fdc3e1e
- **Git Branch:** phase-d-killer-experiments

Baseline condition: **fresh_grid_eval**

Conditions: grid_pretrained_grid_eval, grid_logic_grid_eval, logic_grid_eval
Seeds per condition: 200

## first_task_success_tick



| Condition | Baseline | Condition | Delta | 95% CI | p | d |
|---|---:|---:|---:|---:|---:|---:|
| grid_pretrained_grid_eval | 6.99 | 1.125 | -5.865 | [-6.813129, -4.916871] | 0.00e+00 *** | -0.857317 |
| grid_logic_grid_eval | 6.99 | 0.97 | -6.02 | [-6.920863, -5.119137] | 0.00e+00 *** | -0.926144 |
| logic_grid_eval | 6.99 | 6.79 | -0.2 | [-1.338127, 0.938127] | 0.7305 | -0.024355 |

## task_completion_rate



| Condition | Baseline | Condition | Delta | 95% CI | p | d |
|---|---:|---:|---:|---:|---:|---:|
| grid_pretrained_grid_eval | 0.76 | 0.96 | 0.2 | [0.134831, 0.265169] | 0.00e+00 *** | 0.425334 |
| grid_logic_grid_eval | 0.76 | 0.98 | 0.22 | [0.160791, 0.279209] | 0.00e+00 *** | 0.514963 |
| logic_grid_eval | 0.76 | 0.82 | 0.06 | [-0.022947, 0.142947] | 0.1563 | 0.100252 |

## reward



| Condition | Baseline | Condition | Delta | 95% CI | p | d |
|---|---:|---:|---:|---:|---:|---:|
| grid_pretrained_grid_eval | 41.36 | 51.765 | 10.405 | [8.836994, 11.973006] | 0.00e+00 *** | 0.919677 |
| grid_logic_grid_eval | 41.36 | 51.835 | 10.475 | [8.976955, 11.973045] | 0.00e+00 *** | 0.969104 |
| logic_grid_eval | 41.36 | 42.21 | 0.85 | [-0.9753, 2.6753] | 0.3614 | 0.06454 |

## penalty



| Condition | Baseline | Condition | Delta | 95% CI | p | d |
|---|---:|---:|---:|---:|---:|---:|
| grid_pretrained_grid_eval | 13.5875 | 13.5405 | -0.047 | [-1.278635, 1.184635] | 0.9404 | -0.005289 |
| grid_logic_grid_eval | 13.5875 | 14.205 | 0.6175 | [-0.605911, 1.840911] | 0.3225 | 0.069953 |
| logic_grid_eval | 13.5875 | 14.2055 | 0.618 | [-0.664841, 1.900841] | 0.3451 | 0.066766 |

## invalid_actions



| Condition | Baseline | Condition | Delta | 95% CI | p | d |
|---|---:|---:|---:|---:|---:|---:|
| grid_pretrained_grid_eval | 0.0 | 0.0 | 0.0 | [0.0, 0.0] | 1.0000 | 0.0 |
| grid_logic_grid_eval | 0.0 | 0.0 | 0.0 | [0.0, 0.0] | 1.0000 | 0.0 |
| logic_grid_eval | 0.0 | 0.0 | 0.0 | [0.0, 0.0] | 1.0000 | 0.0 |

## prediction_error



| Condition | Baseline | Condition | Delta | 95% CI | p | d |
|---|---:|---:|---:|---:|---:|---:|
| grid_pretrained_grid_eval | 0.545417 | 0.037583 | -0.507833 | [-0.534305, -0.481362] | 0.00e+00 *** | -2.658796 |
| grid_logic_grid_eval | 0.545417 | 0.036833 | -0.508583 | [-0.53562, -0.481547] | 0.00e+00 *** | -2.607075 |
| logic_grid_eval | 0.545417 | 0.585042 | 0.039625 | [0.00846, 0.07079] | 0.0127 * | 0.176213 |

## final_energy



| Condition | Baseline | Condition | Delta | 95% CI | p | d |
|---|---:|---:|---:|---:|---:|---:|
| grid_pretrained_grid_eval | 127.7725 | 176.4405 | 48.668 | [45.519563, 51.816437] | 0.00e+00 *** | 2.142346 |
| grid_logic_grid_eval | 127.7725 | 173.76725 | 45.99475 | [43.053896, 48.935604] | 0.00e+00 *** | 2.167584 |
| logic_grid_eval | 127.7725 | 123.76875 | -4.00375 | [-6.28975, -1.71775] | 5.98e-04 *** | -0.242735 |

# DNA Storage Simulation Report

## Overview
This report summarizes a reproducible run for DNA storage coding schemes S1/S2/S3.

## Run Configuration
```json
{
  "experiment": {
    "schemes": [
      "s1",
      "s2",
      "s3"
    ],
    "dataset": "random",
    "size_mb": 1,
    "trials_per_cell": 50,
    "base_seed": 12345,
    "two_stage_channel": false
  },
  "scheme_params": {
    "chunk_data_bytes": 1024,
    "marker": "ACGTACGTAC",
    "marker_period": 40,
    "max_marker_edit_distance": 2,
    "rs_parity_bytes": 32,
    "replication": 2,
    "gc_target": 0.5
  },
  "channel": {
    "synthesis": {
      "p_sub": 0.0,
      "p_del": 0.0,
      "p_ins": 0.0,
      "gc_ins_bias": 0.0,
      "gc_sub_bias": 0.0,
      "homopolymer_threshold": 4,
      "homopolymer_del_multiplier": 3.0
    },
    "sequencing": {
      "p_sub": 0.0,
      "p_del": 0.0,
      "p_ins": 0.0,
      "gc_ins_bias": 0.0,
      "gc_sub_bias": 0.0,
      "homopolymer_threshold": 4,
      "homopolymer_del_multiplier": 3.0
    },
    "enabled": false
  },
  "grid": {
    "p_sub_list": [
      0.0,
      0.005,
      0.01,
      0.02,
      0.03
    ],
    "p_indel_list": [
      0.0,
      0.0025,
      0.005,
      0.01,
      0.02
    ],
    "replication_list": [
      1,
      2,
      3
    ]
  },
  "output": {
    "out_dir": "results",
    "run_id": "fast_large_random_1mb",
    "save_raw_parquet": true
  }
}
```

## Key Results
Top-performing settings per scheme are exported to:
- `results/fast_large_random_1mb/agg/summary_top_configs.csv`

### Top Config Table
| scheme | p_sub | p_ins | p_del | success_mean | effective_bits_per_base_mean | overhead_mean | trials |
| --- | --- | --- | --- | --- | --- | --- | --- |
| s1 | 0.0 | 0.0 | 0.0 | 1.0 | 1.9523355576739756 | 1.0244140625 | 50 |
| s1 | 0.0 | 0.00125 | 0.00125 | 0.0 | 3.813155386081983e-05 | 1.0244140625 | 50 |
| s1 | 0.0 | 0.0025 | 0.0025 | 0.0 | 0.0 | 1.0244140625 | 50 |
| s1 | 0.0 | 0.005 | 0.005 | 0.0 | 0.0 | 1.0244140625 | 50 |
| s1 | 0.0 | 0.01 | 0.01 | 0.0 | 0.0 | 1.0244140625 | 50 |
| s2 | 0.0 | 0.0 | 0.0 | 1.0 | 1.3015570384493171 | 1.53662109375 | 50 |
| s2 | 0.0 | 0.00125 | 0.00125 | 0.0 | 0.0 | 1.53662109375 | 50 |
| s2 | 0.0 | 0.0025 | 0.0025 | 0.0 | 0.0 | 1.53662109375 | 50 |
| s2 | 0.0 | 0.005 | 0.005 | 0.0 | 0.0 | 1.53662109375 | 50 |
| s2 | 0.0 | 0.01 | 0.01 | 0.0 | 0.0 | 1.53662109375 | 50 |
| s3 | 0.0 | 0.0 | 0.0 | 1.0 | 0.4518976169461607 | 4.42578125 | 50 |
| s3 | 0.0 | 0.00125 | 0.00125 | 0.0 | 0.0 | 4.42578125 | 50 |
| s3 | 0.0 | 0.0025 | 0.0025 | 0.0 | 0.0 | 4.42578125 | 50 |
| s3 | 0.0 | 0.005 | 0.005 | 0.0 | 0.0 | 4.42578125 | 50 |
| s3 | 0.0 | 0.01 | 0.01 | 0.0 | 0.0 | 4.42578125 | 50 |

## Figures
- `figs/heatmap_success_s1.png`
- `figs/heatmap_success_s2.png`
- `figs/heatmap_success_s3.png`
- `figs/line_effective_bits_vs_indel.png`

## Interpretation Notes
- `success_mean` captures perfect file recovery probability.
- `effective_bits_per_base_mean` measures net recovered payload rate including overhead.
- `overhead_mean` compares synthesized bases to ideal 2-bit/base payload requirement.

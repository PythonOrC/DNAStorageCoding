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
    "size_mb": 0.048828125,
    "trials_per_cell": 10,
    "base_seed": 12345,
    "two_stage_channel": true,
    "n_workers": 0
  },
  "scheme_params": {
    "chunk_data_bytes": 256,
    "marker": "ACGTACGTAC",
    "marker_period": 40,
    "max_marker_edit_distance": 2,
    "rs_parity_bytes": 64,
    "replication": 5,
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
    "enabled": true
  },
  "grid": {
    "p_sub_list": [
      0.0,
      0.0002,
      0.0005,
      0.001,
      0.002
    ],
    "p_indel_list": [
      0.0,
      0.0001,
      0.0002,
      0.0005,
      0.001,
      0.002,
      0.003,
      0.005
    ],
    "replication_list": [
      1,
      2,
      3,
      5
    ]
  },
  "output": {
    "out_dir": "results",
    "run_id": "realistic_50kb_high_redundancy_wide_grid_v1",
    "save_raw_parquet": true
  }
}
```

## Key Results
Top-performing settings per scheme are exported to:
- `results/realistic_50kb_high_redundancy_wide_grid_v1/agg/summary_top_configs.csv`

### Top Config Table
| scheme | p_sub | p_ins | p_del | success_mean | effective_bits_per_base_mean | overhead_mean | trials |
| --- | --- | --- | --- | --- | --- | --- | --- |
| s1 | 0.0 | 0.0 | 0.0 | 1.0 | 1.822064056939502 | 1.09765625 | 10 |
| s1 | 0.0 | 5e-05 | 5e-05 | 0.0 | 1.597950177935943 | 1.09765625 | 10 |
| s1 | 0.0 | 0.0001 | 0.0001 | 0.0 | 1.4439857651245551 | 1.09765625 | 10 |
| s1 | 0.0 | 0.00025 | 0.00025 | 0.0 | 1.0130676156583631 | 1.09765625 | 10 |
| s1 | 0.0 | 0.0005 | 0.0005 | 0.0 | 0.5721281138790035 | 1.09765625 | 10 |
| s2 | 0.0 | 0.0 | 0.0 | 1.0 | 1.2147093712930013 | 1.646484375 | 10 |
| s2 | 0.0 | 5e-05 | 5e-05 | 0.0 | 1.0167117437722422 | 1.646484375 | 10 |
| s2 | 0.0 | 0.0001 | 0.0001 | 0.0 | 0.8843084223013049 | 1.646484375 | 10 |
| s2 | 0.0 | 0.00025 | 0.00025 | 0.0 | 0.52414709371293 | 1.646484375 | 10 |
| s2 | 0.0 | 0.0005 | 0.0005 | 0.0 | 0.2271506524317911 | 1.646484375 | 10 |
| s3 | 0.0 | 0.0 | 0.0 | 1.0 | 0.1258758451137062 | 15.888671875 | 10 |
| s3 | 0.0002 | 0.0 | 0.0 | 1.0 | 0.1258758451137062 | 15.888671875 | 10 |
| s3 | 0.0005 | 0.0 | 0.0 | 1.0 | 0.1258758451137062 | 15.888671875 | 10 |
| s3 | 0.001 | 0.0 | 0.0 | 1.0 | 0.1258758451137062 | 15.888671875 | 10 |
| s3 | 0.002 | 0.0 | 0.0 | 0.9 | 0.1258129071911493 | 15.888671875 | 10 |

## Robustness Frontier (Chunk Recovery > 0)
Frontier tables exported to:
- `results/realistic_50kb_high_redundancy_wide_grid_v1/agg/chunk_recovery_frontier_summary.csv`
- `results/realistic_50kb_high_redundancy_wide_grid_v1/agg/chunk_recovery_frontier_by_psub.csv`

### Frontier Summary
| scheme | nonzero_cells | max_nonzero_p_sub | max_nonzero_p_indel |
| --- | --- | --- | --- |
| s1 | 39 | 0.002 | 0.005 |
| s2 | 37 | 0.002 | 0.005 |
| s3 | 40 | 0.002 | 0.005 |

### Frontier By Substitution Rate
| scheme | p_sub | max_nonzero_p_indel |
| --- | --- | --- |
| s1 | 0.0 | 0.005 |
| s1 | 0.0002 | 0.005 |
| s1 | 0.0005 | 0.005 |
| s1 | 0.001 | 0.005 |
| s1 | 0.002 | 0.003 |
| s2 | 0.0 | 0.005 |
| s2 | 0.0002 | 0.005 |
| s2 | 0.0005 | 0.003 |
| s2 | 0.001 | 0.005 |
| s2 | 0.002 | 0.002 |
| s3 | 0.0 | 0.005 |
| s3 | 0.0002 | 0.005 |
| s3 | 0.0005 | 0.005 |
| s3 | 0.001 | 0.005 |
| s3 | 0.002 | 0.005 |

## Figures
- `figs/heatmap_success_s1.png`
- `figs/heatmap_success_s2.png`
- `figs/heatmap_success_s3.png`
- `figs/line_effective_bits_vs_indel.png`
- `figs/line_chunk_recovery_nonzero_frontier_vs_psub.png`

## Interpretation Notes
- `success_mean` captures perfect file recovery probability.
- `effective_bits_per_base_mean` measures net recovered payload rate including overhead.
- `chunk_recovery_mean` is a more forgiving robustness metric than full-file success.
- `overhead_mean` compares synthesized bases to ideal 2-bit/base payload requirement.

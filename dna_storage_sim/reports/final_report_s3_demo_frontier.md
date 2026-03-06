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
    "size_mb": 0.1,
    "trials_per_cell": 8,
    "base_seed": 12345,
    "two_stage_channel": true
  },
  "scheme_params": {
    "chunk_data_bytes": 256,
    "marker": "ACGTACGTAC",
    "marker_period": 30,
    "max_marker_edit_distance": 4,
    "rs_parity_bytes": 64,
    "replication": 3,
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
      "p_sub": 0.0003,
      "p_del": 2e-05,
      "p_ins": 2e-05,
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
      0.0005,
      0.001,
      0.002,
      0.003
    ],
    "p_indel_list": [
      0.0,
      0.0001,
      0.0002,
      0.0005,
      0.001
    ],
    "replication_list": [
      1,
      2,
      3
    ]
  },
  "output": {
    "out_dir": "results",
    "run_id": "s3_demo_frontier_0p1mb",
    "save_raw_parquet": true
  }
}
```

## Key Results
Top-performing settings per scheme are exported to:
- `results/s3_demo_frontier_0p1mb/agg/summary_top_configs.csv`

### Top Config Table
| scheme | p_sub | p_ins | p_del | success_mean | effective_bits_per_base_mean | overhead_mean | trials |
| --- | --- | --- | --- | --- | --- | --- | --- |
| s1 | 0.0 | 0.0 | 0.0 | 0.0 | 1.226980114154656 | 1.0977521767740828 | 8 |
| s1 | 0.0 | 5e-05 | 5e-05 | 0.0 | 1.1333541834988317 | 1.0977521767740828 | 8 |
| s1 | 0.0 | 0.0001 | 0.0001 | 0.0 | 0.9944616747895436 | 1.0977521767740828 | 8 |
| s1 | 0.0 | 0.00025 | 0.00025 | 0.0 | 0.7030067676162179 | 1.0977521767740828 | 8 |
| s1 | 0.0 | 0.0005 | 0.0005 | 0.0 | 0.3801919083982729 | 1.0977521767740828 | 8 |
| s2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.684102617564527 | 1.646628265161124 | 8 |
| s2 | 0.0 | 5e-05 | 5e-05 | 0.0 | 0.5926239643693838 | 1.646628265161124 | 8 |
| s2 | 0.0 | 0.0001 | 0.0001 | 0.0 | 0.4942473814219233 | 1.646628265161124 | 8 |
| s2 | 0.0 | 0.00025 | 0.00025 | 0.0 | 0.2923815811954674 | 1.646628265161124 | 8 |
| s2 | 0.0 | 0.0005 | 0.0005 | 0.0 | 0.1282516846644137 | 1.646628265161124 | 8 |
| s3 | 0.0 | 0.0 | 0.0 | 0.0 | 0.1391995346656254 | 10.14887894942636 | 8 |
| s3 | 0.0 | 5e-05 | 5e-05 | 0.0 | 0.1345687434750291 | 10.14887894942636 | 8 |
| s3 | 0.0 | 0.0001 | 0.0001 | 0.0 | 0.1101877876038004 | 10.14887894942636 | 8 |
| s3 | 0.0 | 0.00025 | 0.00025 | 0.0 | 0.0488213471204616 | 10.14887894942636 | 8 |
| s3 | 0.0 | 0.0005 | 0.0005 | 0.0 | 0.0128575402116745 | 10.14887894942636 | 8 |

## Robustness Frontier (Chunk Recovery > 0)
Frontier tables exported to:
- `results/s3_demo_frontier_0p1mb/agg/chunk_recovery_frontier_summary.csv`
- `results/s3_demo_frontier_0p1mb/agg/chunk_recovery_frontier_by_psub.csv`

### Frontier Summary
| scheme | nonzero_cells | max_nonzero_p_sub | max_nonzero_p_indel |
| --- | --- | --- | --- |
| s1 | 25 | 0.003 | 0.001 |
| s2 | 25 | 0.003 | 0.001 |
| s3 | 24 | 0.003 | 0.001 |

### Frontier By Substitution Rate
| scheme | p_sub | max_nonzero_p_indel |
| --- | --- | --- |
| s1 | 0.0 | 0.001 |
| s1 | 0.0005 | 0.001 |
| s1 | 0.001 | 0.001 |
| s1 | 0.002 | 0.001 |
| s1 | 0.003 | 0.001 |
| s2 | 0.0 | 0.001 |
| s2 | 0.0005 | 0.001 |
| s2 | 0.001 | 0.001 |
| s2 | 0.002 | 0.001 |
| s2 | 0.003 | 0.001 |
| s3 | 0.0 | 0.001 |
| s3 | 0.0005 | 0.001 |
| s3 | 0.001 | 0.001 |
| s3 | 0.002 | 0.001 |
| s3 | 0.003 | 0.0005 |

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

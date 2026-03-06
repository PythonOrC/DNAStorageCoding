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
    "size_mb": 0.5,
    "trials_per_cell": 30,
    "base_seed": 12345,
    "two_stage_channel": false
  },
  "scheme_params": {
    "chunk_data_bytes": 1024,
    "marker": "ACGTACGTAC",
    "marker_period": 40,
    "max_marker_edit_distance": 2,
    "rs_parity_bytes": 32,
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
      0.0001,
      0.0002,
      0.0005,
      0.001
    ],
    "p_indel_list": [
      0.0
    ],
    "replication_list": [
      1,
      2,
      3
    ]
  },
  "output": {
    "out_dir": "results",
    "run_id": "easy_0p5mb_subonly",
    "save_raw_parquet": true
  }
}
```

## Key Results
Top-performing settings per scheme are exported to:
- `results/easy_0p5mb_subonly/agg/summary_top_configs.csv`

### Top Config Table
| scheme | p_sub | p_ins | p_del | success_mean | effective_bits_per_base_mean | overhead_mean | trials |
| --- | --- | --- | --- | --- | --- | --- | --- |
| s1 | 0.0 | 0.0 | 0.0 | 1.0 | 1.9523355576739756 | 1.0244140625 | 30 |
| s1 | 0.0001 | 0.0 | 0.0 | 0.0 | 1.3061328249126152 | 1.0244140625 | 30 |
| s1 | 0.0002 | 0.0 | 0.0 | 0.0 | 0.8606291706387034 | 1.0244140625 | 30 |
| s1 | 0.0005 | 0.0 | 0.0 | 0.0 | 0.2453129965046075 | 1.0244140625 | 30 |
| s1 | 0.001 | 0.0 | 0.0 | 0.0 | 0.0334286622179853 | 1.0244140625 | 30 |
| s2 | 0.0 | 0.0 | 0.0 | 1.0 | 1.301557038449317 | 1.53662109375 | 30 |
| s2 | 0.0001 | 0.0 | 0.0 | 0.0 | 0.6878932316491896 | 1.53662109375 | 30 |
| s2 | 0.0002 | 0.0 | 0.0 | 0.0 | 0.3763160682131131 | 1.53662109375 | 30 |
| s2 | 0.0005 | 0.0 | 0.0 | 0.0 | 0.0544857536277936 | 1.53662109375 | 30 |
| s2 | 0.001 | 0.0 | 0.0 | 0.0 | 0.0022031564452918 | 1.53662109375 | 30 |
| s3 | 0.0 | 0.0 | 0.0 | 1.0 | 0.301265077964107 | 6.638671875 | 30 |
| s3 | 0.0001 | 0.0 | 0.0 | 0.0 | 0.2683338236736295 | 6.638671875 | 30 |
| s3 | 0.0002 | 0.0 | 0.0 | 0.0 | 0.186211630871825 | 6.638671875 | 30 |
| s3 | 0.0005 | 0.0 | 0.0 | 0.0 | 0.0340884573894282 | 6.638671875 | 30 |
| s3 | 0.001 | 0.0 | 0.0 | 0.0 | 0.0016671570069628 | 6.638671875 | 30 |

## Figures
- `figs/heatmap_success_s1.png`
- `figs/heatmap_success_s2.png`
- `figs/heatmap_success_s3.png`
- `figs/line_effective_bits_vs_indel.png`

## Interpretation Notes
- `success_mean` captures perfect file recovery probability.
- `effective_bits_per_base_mean` measures net recovered payload rate including overhead.
- `overhead_mean` compares synthesized bases to ideal 2-bit/base payload requirement.

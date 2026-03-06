# Final Configs and How To Use Them

This file maps each final figure/table to the exact config and output data source.

## 1) Config Files (`dna_storage_sim/FINAL_*.json`)

### Suite A: Primary size sweep (grid-only noise, all schemes, 20 trials/cell, chunk=128)
- `FINAL_A_10kb_c128_t20.json`
- `FINAL_A_50kb_c128_t20.json`
- `FINAL_A_100kb_c128_t20.json`
- `FINAL_A_500kb_c128_t20.json`
- `FINAL_A_1mb_c128_t20.json`
- `FINAL_A_5mb_c128_t20.json` (optional if runtime is too high)

### Suite C1: Chunk-size ablation
- `FINAL_C_10kb_c256_t20.json`
- `FINAL_C_100kb_c256_t20.json`

### Suite C2: S3 redundancy/parity ablation at 100KB
- `FINAL_C_100kb_s3_rep3_p32_t20.json`
- `FINAL_C_100kb_s3_rep3_p64_t20.json`
- `FINAL_C_100kb_s3_rep5_p32_t20.json`
- Baseline for comparison is `FINAL_A_100kb_c128_t20.json` (S3, rep5, parity64)

## 2) Run + Plot + Report

From repo root:

```powershell
conda run -n Bi1C python -m dna_storage_sim.cli run-grid --config dna_storage_sim/FINAL_A_100kb_c128_t20.json
conda run -n Bi1C python -m dna_storage_sim.cli plot --in results/final_a_100kb_c128_t20
conda run -n Bi1C python -m dna_storage_sim.cli report --in results/final_a_100kb_c128_t20 --out dna_storage_sim/reports/final_report_final_a_100kb_c128_t20.md
```

## 3) Where Each Graph’s Data Comes From

- Heatmaps and fixed-size scheme comparisons:
  - source: `results/<run_id>/agg/aggregate_metrics.parquet|csv`
  - figs: `results/<run_id>/figs/heatmap_*_s1|s2|s3.*`

- Indel-line plots (`effective_bits`, `chunk_recovery`, `byte_accuracy`):
  - source: same `aggregate_metrics`
  - figs: `results/<run_id>/figs/line_*_vs_indel.*`

- Frontier plot:
  - source: `aggregate_metrics` (`chunk_recovery_mean > 0`)
  - fig: `results/<run_id>/figs/line_chunk_recovery_nonzero_frontier_vs_psub.*`
  - table backup: `results/<run_id>/agg/chunk_recovery_frontier_*.csv`

- File-size scaling (within each scheme):
  - combine Suite A runs by reading each run’s `agg/aggregate_metrics`
  - compute per-run means (or fixed-noise slices) and plot vs file size.

- Chunk/redundancy ablations:
  - compare metrics across matching noise cells from Suite C configs and Suite A 100KB baseline.

- Uncertainty/error bars:
  - source: `results/<run_id>/raw/all_trials.parquet|csv` (trial-level metrics)
  - aggregate mean + CI/std per scheme/noise cell before plotting.

## 4) Final Graph Sets To Present

### Set A: Fixed file size, compare schemes (S1 vs S2 vs S3)
- Use one run at a time from Suite A (recommended: `100KB`, `500KB`, `1MB`).
- Present:
  - `heatmap_success_s1|s2|s3.*`
  - `heatmap_chunk_recovery_s1|s2|s3.*`
  - `heatmap_byte_accuracy_s1|s2|s3.*`
  - `line_effective_bits_vs_indel.*`
  - `line_chunk_recovery_vs_indel.*`
  - `line_byte_accuracy_vs_indel.*`
  - `line_chunk_recovery_nonzero_frontier_vs_psub.*`
- Message: robustness/rate differences across schemes under same file size.

### Set B: Fixed scheme, vary file size
- Use Suite A runs together (`10KB, 50KB, 100KB, 500KB, 1MB`, optional `5MB`).
- For each scheme (S1/S2/S3), build size-scaling plots from `agg/aggregate_metrics`:
  - x-axis: file size
  - y-axis: mean `success`, `chunk_recovery`, `byte_accuracy`, `effective_bits_per_base`
- Message: how each scheme degrades as payload size increases.

### Set C: 2D phase maps (same file size)
- Use a representative fixed size (recommended: `100KB` and `500KB`).
- Show the 2D heatmaps for each scheme and each metric:
  - success
  - chunk recovery
  - byte accuracy
- Message: phase transition region and failure boundary in (`p_sub`, `p_indel`) space.

### Set D: Ablation graphs
- Chunk-size ablation:
  - compare `FINAL_A_10kb_c128_t20` vs `FINAL_C_10kb_c256_t20`
  - compare `FINAL_A_100kb_c128_t20` vs `FINAL_C_100kb_c256_t20`
- S3 redundancy/parity ablation at 100KB:
  - compare baseline `FINAL_A_100kb_c128_t20` (S3 view) with:
    - `FINAL_C_100kb_s3_rep3_p32_t20`
    - `FINAL_C_100kb_s3_rep3_p64_t20`
    - `FINAL_C_100kb_s3_rep5_p32_t20`
- Suggested visuals:
  - grouped bars or delta-line plots of `chunk_recovery`, `byte_accuracy`, `effective_bits_per_base`
- Message: parameter choices are justified, not arbitrary.

### Set E: Reliability/uncertainty overlays
- Use `raw/all_trials` from key runs (`100KB`, `500KB`, plus one ablation run).
- Add CI/std error bars around line curves.
- Message: conclusions are statistically stable, not trial noise.

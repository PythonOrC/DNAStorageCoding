# Final Results Plan (DNA Storage Class Project)

## Are You Ready?
Yes. The pipeline is now strong enough for final runs. You have:
- S1/S2/S3 implemented and tested.
- Improved S3 decoding (header duplication, replica voting, marker handling).
- Metrics and plots for `success`, `byte_accuracy`, `chunk_recovery`, `effective_bits_per_base`, and frontiers.

The key now is running a **clean, controlled experiment matrix** and reporting it consistently.

## Core Story to Demonstrate
1. **Within-scheme scaling by file size**: each scheme degrades as file size grows.
2. **Cross-scheme comparison at fixed size**: S3 is more robust, S1 is usually more efficient per base.
3. **Threshold behavior**: recovery collapses past an indel/substitution boundary.
4. **Tradeoff**: robustness vs effective bits/base (rate–reliability frontier).

## Final Experiment Suites

## Suite A (Primary, Must-Have): Grid-only Noise, Multi-size
Use **baseline stage errors = 0** (noise only from grid values).

- Schemes: `s1,s2,s3`
- Trials per cell: `20` (as requested)
- Chunk: `128` (primary), plus `256` (ablation in Suite C)
- Sizes: `10KB, 50KB, 100KB, 500KB, 1MB` (`5MB` optional due runtime)
- Grid:
  - `p_sub_list = [0, 0.0002, 0.0005, 0.001, 0.002]`
  - `p_indel_list = [0, 0.0001, 0.0002, 0.0005, 0.001, 0.002, 0.003, 0.005]`

Purpose: cleanly map phase diagram and size effects.

## Suite B (Realism Check): Two-stage Baseline Noise
Use nonzero synthesis/sequencing stage errors (your “realistic” model), but run fewer sizes.

- Sizes: `100KB`, `500KB`
- Trials per cell: `10`
- Same grid as Suite A

Purpose: show conclusions still hold under staged channel assumptions.

## Suite C (Ablation, Must-Have)
1. **Chunk size ablation**: `128` vs `256` at `10KB` and `100KB`.
2. **S3 redundancy ablation**: `replication = 3 vs 5`, `rs_parity = 32 vs 64` at `100KB`.

Purpose: justify final parameter choice, not just outcomes.

## Suite D (Reproducibility)
For 1 representative run from Suite A and 1 from Suite B:
- run `validate-repro`
- report max metric diffs.

## Required Figures
For each key run:
1. Heatmaps per scheme:
   - `success`
   - `chunk_recovery`
   - `byte_accuracy`
2. Line plots:
   - `effective_bits_vs_indel`
   - `chunk_recovery_vs_indel`
   - `byte_accuracy_vs_indel`
3. Frontier:
   - `line_chunk_recovery_nonzero_frontier_vs_psub`

## Required Tables
1. Per-size summary (S1/S2/S3):
   - mean `success`, `byte_accuracy`, `chunk_recovery`, `effective_bits_per_base`
2. Best robust cells and best efficient cells.
3. Ablation table (`chunk_size`, `replication`, `parity`) with deltas.

## Run Order (Recommended)
1. `10KB` and `50KB` Suite A first (sanity check).
2. `100KB`, `500KB`, `1MB` Suite A.
3. Optional `5MB` (reduced grid or reduced trials if runtime is excessive).
4. Suite B realism check.
5. Suite C ablations.
6. Repro runs + final report assembly.

## Practical Notes
- Always use a fresh `run_id` per config revision.
- Keep config JSONs immutable once a run starts.
- If runtime is high, reduce only **trials for largest size** first (not small sizes), and document it.

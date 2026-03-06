# DNA Storage Simulator

Reproducible Python simulation framework to compare three DNA-storage schemes under substitutions, insertions, deletions, GC bias, and homopolymer-sensitive errors.

## Schemes

- `S1` naive 2-bit base mapping, chunk index, CRC32
- `S2` constrained ternary/state-machine coder with GC balancing, chunk index, CRC32
- `S3` RS + constrained coder + sync markers + replication

## Install

```bash
pip install -e .
```

## Run Grid

```bash
python -m dna_storage_sim.cli run-grid --scheme all --dataset random --size-mb 1 --trials 20 --out results/
```

## Plot

```bash
python -m dna_storage_sim.cli plot --in results/latest --out results/latest/figs
```

## Report

```bash
python -m dna_storage_sim.cli report --in results/latest --out reports/final_report.md
```

## Reproducibility Check

```bash
python -m dna_storage_sim.cli validate-repro --in results/latest
```

## S3 Robustness Demo

Run a config tuned to make S3 robustness trends easier to visualize:

```bash
python -m dna_storage_sim.cli run-grid --config config_s3_demo_frontier.json
python -m dna_storage_sim.cli plot --in results/s3_demo_frontier_0p1mb --out results/s3_demo_frontier_0p1mb/figs
python -m dna_storage_sim.cli report --in results/s3_demo_frontier_0p1mb --out reports/final_report_s3_demo_frontier.md
```

Look for:
- `figs/line_chunk_recovery_nonzero_frontier_vs_psub.png`
- `agg/chunk_recovery_frontier_summary.csv`
- `agg/chunk_recovery_frontier_by_psub.csv`

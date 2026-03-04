# DNA Storage Coding Simulator: Full-Scope One-Shot Delivery Plan

## Summary
Build and validate a reproducible Python 3.10+ simulation framework that compares three DNA-storage schemes (S1 naive, S2 constrained, S3 RS+markers+replication) under substitution/indel/GC/homopolymer-aware channels, then generate publication-quality figures and tables from a strict, fully reproducible large-grid experiment run on a single workstation within 24 hours.

## Final Deliverables (Required)
1. Production code package `dna_storage_sim/` with CLI, tests, and modular codecs/channels/metrics.
2. Reproducible results artifact directory containing:
1. Raw per-trial records (`parquet` preferred, fallback CSV).
2. Aggregated metrics tables with confidence intervals.
3. Full run manifest with config + RNG seeds + git commit hash + environment snapshot.
4. Presentation-quality figure set (`.png` + `.svg`) and exportable summary tables (`.csv` + `.md`).
3. Polished Markdown report `reports/final_report.md` including:
1. Methods and parameterization.
2. Main phase-diagram heatmaps per scheme.
3. Throughput/overhead/recovery tradeoff tables.
4. Interpretation section and limitations.
4. Strict verification evidence:
1. Passing test suite output.
2. Reproducibility rerun check (same config/seeds gives matching aggregates within defined tolerance).
3. End-to-end command list in README.

## Scope and Sequencing
1. Phase 1: Core architecture and shared data model.
2. Phase 2: Implement S1 and S2 codecs and deterministic reversibility tests.
3. Phase 3: Implement S3 RS+markers+replication including approximate marker matching.
4. Phase 4: Implement full two-stage channel and calibration checks.
5. Phase 5: Implement trial runner, large-grid sweeps, caching/resume, and aggregation.
6. Phase 6: Generate polished plots/tables/report and run strict completion gates.

## Public Interfaces and Types
1. `src/config.py`
1. `ExperimentConfig`, `ChannelParams`, `SchemeParams`, `GridSpec`, `RunSpec`, `OutputSpec` dataclasses.
2. Frozen configs with explicit serialization to `json`.
2. `src/codec_base.py`
1. `class Codec`: `encode_file(bytes)->list[EncodedStrand]`, `decode_strands(list[ObservedStrand])->DecodeResult`.
2. `EncodedStrand` includes `scheme_id`, `chunk_id`, `replica_id`, `dna`, `bases_total`, `meta`.
3. `src/channel.py`
1. `apply_channel(dna: str, params: ChannelParams, rng) -> str`.
2. `apply_two_stage_channel(dna: str, synth_params, seq_params, rng) -> str`.
4. `src/metrics.py`
1. `compute_trial_metrics(...) -> TrialMetrics`.
2. `aggregate_metrics(df) -> AggregateMetrics` with mean, std, 95% CI.
5. `src/experiments.py`
1. `run_grid(run_spec: RunSpec) -> RunArtifacts`.
2. Resume-by-cell checkpointing and deterministic seed schedule.
6. `src/cli.py`
1. `run-grid`, `plot`, `report`, `validate-repro`.
2. All commands accept `--config` plus CLI overrides.

## Implementation Decisions (Locked)
1. Chunk format constants:
1. `magic=b'DNAS'`, `version=1`, `scheme_id`, `chunk_id:uint32`, `total_chunks:uint32`, `data_len:uint16`, `crc32:uint32`, `bit_len:uint32` for S2/S3 reversibility.
2. Default `CHUNK_DATA_BYTES=1024`.
2. S1 mapping fixed as `00:A 01:C 10:G 11:T`.
3. S2 constrained coder:
1. Streaming bits↔trits conversion.
2. No repeated-base guarantee via 3-of-4 transition mapping.
3. Deterministic GC-balancing table switch based on running trajectory.
4. S3 RS+markers:
1. `reedsolo.RSCodec(parity_bytes)` with default parity `32`.
2. Marker insertion every `M=40` encoded bases.
3. Decoder marker search: exact first, then approximate (edit distance <=2).
4. Segment mismatch handling: mark invalid/erasure candidate; attempt RS decode; CRC required to accept.
5. Replication default `R=2` for large-grid baseline, plus sweeps over `R in {1,2,3}` where specified.
5. Channel model:
1. Sub/del/ins with homopolymer deletion multiplier when run length >= `H=4`.
2. GC-biased substitution/insertion probabilities configurable.
3. Two-stage defaults: synthesis low-noise, sequencing indel-heavy.

## Experiment Plan (Large Grid)
1. Datasets:
1. `text` synthetic corpus.
2. `random` RNG bytes.
3. Sizes: `1MB` and `10MB`.
2. Grid:
1. `p_sub`: 8 points in `[0, 0.05]`.
2. `p_indel=p_ins+p_del`: 8 points in `[0, 0.05]`.
3. Trials: `N=200` per cell.
4. Additional axis runs for `R=1..3` on selected `p_sub` slices.
3. Outputs per cell:
1. `success_rate`, `byte_accuracy`, `chunk_recovery`.
2. `effective_bits_per_base`, `overhead`.
3. GC and max-homopolymer distributions for S2/S3.
4. Runtime controls for <=24h:
1. Parallel execution by grid cell.
2. On-disk checkpoint per cell.
3. Optional partial rerun by failed/missing cell only.

## Testing and Acceptance Scenarios
1. Unit and property tests:
1. Bits/bytes/trits roundtrip with edge lengths.
2. Header parse/serialize compatibility.
3. CRC/SHA integrity checks.
2. Codec correctness:
1. Zero-noise exact roundtrip for S1/S2/S3 across multiple seeds/sizes.
2. S2/S3 constraint guarantees: no homopolymer repeats beyond configured bound.
3. Channel sanity:
1. Empirical measured rates match configured rates within tolerance over long strands.
2. Homopolymer multiplier measurably increases deletion incidence in long runs.
4. S3 robustness:
1. Marker recovery with small indels/substitutions.
2. Approximate marker fallback behavior.
3. RS decode accept/reject paths with CRC validation.
5. End-to-end:
1. Full file reconstruction and SHA256 match.
2. Partial recovery reporting when full reconstruction fails.
6. Reproducibility gate:
1. Repeat same run config+seeds; aggregate metrics match exactly for deterministic paths and within floating tolerance for stochastic aggregation output formatting.

## Artifact Structure
1. `results/<run_id>/config/`:
1. `run_spec.json`, `seed_manifest.json`, environment and dependency lock snapshot.
2. `results/<run_id>/raw/`:
1. Per-trial parquet partitions by scheme/dataset/grid cell.
3. `results/<run_id>/agg/`:
1. Aggregated metrics tables and CI.
4. `results/<run_id>/figs/`:
1. Heatmaps, contour plots, tradeoff curves (`png` + `svg`).
5. `reports/final_report.md`:
1. Auto-filled from aggregates/figures via report generator.

## Milestones (Decision-Complete)
1. M1 Foundations: configs, common types, utilities, CLI scaffold, baseline tests.
2. M2 S1+S2: full encode/decode correctness and constraint tests.
3. M3 S3: RS+markers+replication, approximate matching, failure-path tests.
4. M4 Channel+Runner: two-stage channel, grid orchestration, checkpoint/resume.
5. M5 Analysis: aggregate stats, figure generation, table exports.
6. M6 Finalization: strict test pass, full large-grid run, reproducibility rerun, final report.

## Assumptions and Defaults
1. Target environment is one workstation with sufficient CPU/RAM/storage to complete large grid in <=24h using parallel cells and checkpointing.
2. Python dependencies (`numpy`, `pandas`, `matplotlib`, `tqdm`, `reedsolo`, `rapidfuzz`, `pytest`) are available and installable.
3. Exact erasure-aware RS beyond `reedsolo` default behavior is implemented only if compatible with the library path; otherwise invalid segments are handled via replication + CRC-validated RS decode attempts.
4. Report style is Markdown-first; figures/tables are presentation-ready for later slide use.
5. Full-scope completion means no feature deferral from the preliminary plan.

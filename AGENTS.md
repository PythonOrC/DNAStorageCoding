# Repository Guidelines

## Project Structure & Module Organization
- Core project lives in `dna_storage_sim/`.
- Source code is under `dna_storage_sim/src/dna_storage_sim/`:
  - codecs: `codec_naive.py`, `codec_constrained.py`, `codec_rs_indexed.py`
  - simulation pipeline: `channel.py`, `experiments.py`, `metrics.py`, `plots.py`, `report.py`
  - interfaces/config: `codec_base.py`, `chunk_format.py`, `config.py`, `cli.py`
- Tests are in `dna_storage_sim/tests/` and mirror major behaviors (roundtrip, channel stats, constraints).
- Output artifacts are written to `dna_storage_sim/results/<run_id>/` (raw, agg, figs, config).
- Reports are written to `dna_storage_sim/reports/`.
- Root docs include `preliminary_plan.md`, `plan.md`, and this guide.

## Build, Test, and Development Commands
- Create/use env:
  - `conda create -y -n Bi1C python=3.10`
  - `conda run -n Bi1C python -m pip install -e dna_storage_sim`
- For interactive progress bars, prefer activated shell:
  - `conda activate Bi1C`
  - `cd "D:\GitHub Repositories\DNAStorageCoding\dna_storage_sim"`
- Run tests:
  - `python -m pytest -q`
- Run simulation grid:
  - `python -m dna_storage_sim.cli run-grid --config config_10kb_realistic_high_redundancy_wide_grid.json`
- Generate plots/report:
  - `python -m dna_storage_sim.cli plot --in results/<run_id> --out results/<run_id>/figs`
  - `python -m dna_storage_sim.cli report --in results/<run_id> --out reports/final_report_<run_id>.md`
  - `python -m dna_storage_sim.cli validate-repro --in results/<run_id>`

## Coding Style & Naming Conventions
- Python 3.10+, 4-space indentation, UTF-8, and type hints on public functions.
- Modules and functions: `snake_case`; classes/dataclasses: `PascalCase`; constants: `UPPER_SNAKE_CASE`.
- Keep functions focused and deterministic where possible (seeded RNG in experiments).
- Prefer small, explicit dataclasses for configuration and result payloads.

## Testing Guidelines
- Framework: `pytest`.
- Test files: `test_*.py`; test names: `test_<behavior>`.
- Required before merge:
  - codec zero-noise roundtrip tests pass,
  - channel sanity checks pass,
  - constraint checks for S2/S3 pass.
- For new features, add at least one success-path and one failure-path test.

## Commit & Pull Request Guidelines
- Use conventional-style messages:
  - `feat: ...`, `fix: ...`, `test: ...`, `docs: ...`, `refactor: ...`, `chore: ...`.
- Keep commits atomic (one logical change per commit).
- PRs should include:
  - concise summary,
  - affected paths/modules,
  - test evidence (`pytest` output),
  - sample CLI command(s) for behavior changes,
  - updated docs when interfaces/configs change.

## Reproducibility & Configuration Tips
- Always persist run configs and seeds (`results/<run_id>/config/`).
- Always use a new `run_id` when changing code/config; runner skips existing cell files.
- Keep baseline channel rates at zero when you want grid-only noise sweeps.
- Prefer `chunk_data_bytes=128` for stronger robustness at small-file evaluations.
- Use small smoke configs first, then wide-grid configs for final figures.

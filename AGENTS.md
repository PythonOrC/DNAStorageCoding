# Repository Guidelines

## Project Structure & Module Organization
- Core project lives in `dna_storage_sim/`.
- Source code is under `dna_storage_sim/src/dna_storage_sim/`:
  - codecs: `codec_naive.py`, `codec_constrained.py`, `codec_rs_indexed.py`
  - simulation pipeline: `channel.py`, `experiments.py`, `metrics.py`, `plots.py`, `report.py`
  - interfaces/config: `codec_base.py`, `chunk_format.py`, `config.py`, `cli.py`
- Tests are in `dna_storage_sim/tests/` and mirror major behaviors (roundtrip, channel stats, constraints).
- Output artifacts are written to `dna_storage_sim/results/<run_id>/` (raw, agg, figs, config).
- Planning docs at repo root include `preliminary_plan.md` and `plan.md`.

## Build, Test, and Development Commands
- Create/use env:
  - `conda create -y -n Bi1C python=3.10`
  - `conda run -n Bi1C python -m pip install -e dna_storage_sim`
- Run tests:
  - `conda run -n Bi1C python -m pytest -q dna_storage_sim/tests`
- Run simulation grid:
  - `conda run -n Bi1C python -m dna_storage_sim.cli run-grid --config dna_storage_sim/smoke_config.json`
- Generate plots/report:
  - `conda run -n Bi1C python -m dna_storage_sim.cli plot --in dna_storage_sim/results/latest --out dna_storage_sim/results/latest/figs`
  - `conda run -n Bi1C python -m dna_storage_sim.cli report --in dna_storage_sim/results/latest --out dna_storage_sim/reports/final_report.md`

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
- Repository currently has no commit history; use this convention going forward:
  - `feat: ...`, `fix: ...`, `test: ...`, `docs: ...`, `refactor: ...`.
- Keep commits atomic (one logical change per commit).
- PRs should include:
  - concise summary,
  - affected paths/modules,
  - test evidence (`pytest` output),
  - sample CLI command(s) for behavior changes,
  - updated docs when interfaces/configs change.

## Reproducibility & Configuration Tips
- Always persist run configs and seeds (`results/<run_id>/config/`).
- Avoid hardcoding local paths; use CLI args/config JSON.
- Use small smoke configs for validation before large-grid runs.

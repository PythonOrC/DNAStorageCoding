#!/bin/bash
#SBATCH --job-name=dna_grid
#SBATCH --output=logs/%x_%A_%a.txt
#SBATCH --error=logs/%x_%A_%a.txt
#SBATCH --time=7-00:00:00
#SBATCH --partition=compute
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=192G

set -euo pipefail

# Usage patterns:
# 1) Single run:
#    sbatch --export=ALL,CONFIG_JSON=config_10kb_realistic_high_redundancy_wide_grid.json slurm/dna_grid_cpu.sh
# 2) Array run with config list file (one relative path per line):
#    sbatch --array=0-4 --export=ALL,CONFIGS_FILE=slurm/configs_final.txt slurm/dna_grid_cpu.sh
#
# Optional env vars:
#   PROJECT_DIR=/path/to/dna_storage_sim
#   CONDA_ENV=Bi1C
#   N_WORKERS=32
#   RUN_ID_PREFIX=slurm
#   DO_PLOT=1
#   DO_REPORT=1
#   DO_VALIDATE_REPRO=0
#   INSTALL_EDITABLE=0
#   TRIALS_OVERRIDE=20
#   SCHEME_OVERRIDE=all
#   SIZE_MB_OVERRIDE=0.1

PROJECT_DIR="${PROJECT_DIR:-$PWD}"
cd "$PROJECT_DIR"
mkdir -p logs results reports

if command -v conda >/dev/null 2>&1; then
  CONDA_BASE="$(conda info --base)"
  source "$CONDA_BASE/etc/profile.d/conda.sh"
  conda activate "${CONDA_ENV:-Bi1C}"
else
  echo "[error] conda not found in PATH"
  exit 1
fi

if [ "${INSTALL_EDITABLE:-0}" = "1" ]; then
  python -m pip install -e .
fi

CONFIG_JSON="${CONFIG_JSON:-}"
if [ -n "${CONFIGS_FILE:-}" ]; then
  if [ ! -f "$CONFIGS_FILE" ]; then
    echo "[error] CONFIGS_FILE not found: $CONFIGS_FILE"
    exit 1
  fi
  mapfile -t CONFIGS < <(grep -v '^[[:space:]]*#' "$CONFIGS_FILE" | sed '/^[[:space:]]*$/d')
  if [ "${#CONFIGS[@]}" -eq 0 ]; then
    echo "[error] CONFIGS_FILE has no usable lines: $CONFIGS_FILE"
    exit 1
  fi
  IDX="${SLURM_ARRAY_TASK_ID:-0}"
  if [ "$IDX" -lt 0 ] || [ "$IDX" -ge "${#CONFIGS[@]}" ]; then
    echo "[error] SLURM_ARRAY_TASK_ID=$IDX out of range 0..$(( ${#CONFIGS[@]} - 1 ))"
    exit 1
  fi
  CONFIG_JSON="${CONFIGS[$IDX]}"
fi

if [ -z "$CONFIG_JSON" ]; then
  echo "[error] set CONFIG_JSON or CONFIGS_FILE"
  exit 1
fi
if [ ! -f "$CONFIG_JSON" ]; then
  echo "[error] config not found: $CONFIG_JSON"
  exit 1
fi

CONFIG_STEM="$(basename "$CONFIG_JSON" .json)"
JOB_TAG="j${SLURM_JOB_ID:-local}"
if [ -n "${SLURM_ARRAY_TASK_ID:-}" ]; then
  JOB_TAG="${JOB_TAG}_a${SLURM_ARRAY_TASK_ID}"
fi
RUN_ID="${RUN_ID_PREFIX:-slurm}_${CONFIG_STEM}_${JOB_TAG}"

N_WORKERS="${N_WORKERS:-${SLURM_CPUS_PER_TASK:-1}}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export PYTHONUNBUFFERED=1

EXTRA_ARGS=()
if [ -n "${TRIALS_OVERRIDE:-}" ]; then
  EXTRA_ARGS+=(--trials "$TRIALS_OVERRIDE")
fi
if [ -n "${SCHEME_OVERRIDE:-}" ]; then
  EXTRA_ARGS+=(--scheme "$SCHEME_OVERRIDE")
fi
if [ -n "${SIZE_MB_OVERRIDE:-}" ]; then
  EXTRA_ARGS+=(--size-mb "$SIZE_MB_OVERRIDE")
fi

echo "[info] CONFIG_JSON=$CONFIG_JSON"
echo "[info] RUN_ID=$RUN_ID"
echo "[info] N_WORKERS=$N_WORKERS"

CONFIG_OVERRIDE_PATH=".tmp/${CONFIG_STEM}.slurm.${SLURM_JOB_ID:-local}.${SLURM_ARRAY_TASK_ID:-0}.override.json"
python - <<PY
import json
from pathlib import Path
p = Path("$CONFIG_JSON")
data = json.loads(p.read_text(encoding="utf-8"))
data.setdefault("experiment", {})["n_workers"] = int("$N_WORKERS")
tmp = Path("$CONFIG_OVERRIDE_PATH")
tmp.parent.mkdir(parents=True, exist_ok=True)
tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
print(tmp)
PY

python -m dna_storage_sim.cli run-grid --config "$CONFIG_OVERRIDE_PATH" --run-id "$RUN_ID" "${EXTRA_ARGS[@]}"

RESULT_DIR="results/$RUN_ID"
if [ "${DO_PLOT:-1}" = "1" ]; then
  python -m dna_storage_sim.cli plot --in "$RESULT_DIR" --out "$RESULT_DIR/figs"
fi
if [ "${DO_REPORT:-1}" = "1" ]; then
  python -m dna_storage_sim.cli report --in "$RESULT_DIR" --out "reports/final_report_${RUN_ID}.md"
fi
if [ "${DO_VALIDATE_REPRO:-0}" = "1" ]; then
  python -m dna_storage_sim.cli validate-repro --in "$RESULT_DIR"
fi

echo "[done] result_dir=$RESULT_DIR"

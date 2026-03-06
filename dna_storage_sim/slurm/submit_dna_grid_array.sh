#!/bin/bash
set -euo pipefail

# Submit an array of dna_storage_sim config files.
#
# Example:
#   CONFIGS_FILE=slurm/configs_final.txt PARTITION=compute CPUS=32 MEM=192G \
#   bash slurm/submit_dna_grid_array.sh
#
# Required:
#   CONFIGS_FILE path containing one config path per line (relative to dna_storage_sim root)
# Optional:
#   PARTITION=expansion
#   TIME_LIMIT=7-00:00:00
#   CPUS=32
#   MEM=192G
#   CONDA_ENV=Bi1C
#   RUN_ID_PREFIX=slurm

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

CONFIGS_FILE="${CONFIGS_FILE:-slurm/configs_final.txt}"
if [ ! -f "$CONFIGS_FILE" ]; then
  echo "[error] missing CONFIGS_FILE: $CONFIGS_FILE"
  exit 1
fi

N_CONFIGS=$(grep -v '^[[:space:]]*#' "$CONFIGS_FILE" | sed '/^[[:space:]]*$/d' | wc -l | tr -d ' ')
if [ "$N_CONFIGS" -le 0 ]; then
  echo "[error] CONFIGS_FILE has no usable config lines: $CONFIGS_FILE"
  exit 1
fi
ARRAY_MAX=$((N_CONFIGS - 1))

PARTITION="${PARTITION:-expansion}"
TIME_LIMIT="${TIME_LIMIT:-7-00:00:00}"
CPUS="${CPUS:-32}"
MEM="${MEM:-192G}"

sbatch \
  --partition="$PARTITION" \
  --time="$TIME_LIMIT" \
  --cpus-per-task="$CPUS" \
  --mem="$MEM" \
  --array="0-${ARRAY_MAX}" \
  --export="ALL,PROJECT_DIR=$PROJECT_DIR,CONFIGS_FILE=$CONFIGS_FILE,CONDA_ENV=${CONDA_ENV:-Bi1C},RUN_ID_PREFIX=${RUN_ID_PREFIX:-slurm}" \
  slurm/dna_grid_cpu.sh

echo "[submitted] array=0-${ARRAY_MAX} configs=$N_CONFIGS"

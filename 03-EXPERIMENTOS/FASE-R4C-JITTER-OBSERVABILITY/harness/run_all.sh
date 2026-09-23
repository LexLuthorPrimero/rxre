#!/usr/bin/env bash
# run_all.sh — ejecuta la matriz NIVEL A/B x {RADV, lavapipe} x 2 repeticiones
# manteniendo todo dentro de experiments/FASE-R4C-JITTER-OBSERVABILITY/
set -u

BASE="$(cd "$(dirname "$0")/.." && pwd)"
BUILD="$BASE/harness/build"
BIN="$BUILD/jitter_harness"
LAYER_DIR="$BUILD/layer"
RESULTS="$BASE/results"

mkdir -p "$RESULTS/gt" "$RESULTS/recovered" "$RESULTS/metrics" "$RESULTS/logs"

run_one() {
  local level="$1" driver="$2" rep="$3" icd="$4" vendor="$5"
  local tag="${level}_${driver}_r${rep}"
  local log="$RESULTS/logs/${tag}.log"

  VK_ICD_FILENAMES="$icd" \
  VK_LAYER_PATH="$LAYER_DIR" \
  LD_LIBRARY_PATH="$LAYER_DIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" \
  ITER_LAYER_LOG="$RESULTS/recovered/${tag}.lines" \
  ITER_JITTER_LAYER_LEVEL_A="$( [ "$level" = A ] && echo 1 || echo 0 )" \
  ITER_JITTER_LAYER_LEVEL_B="$( [ "$level" = B ] && echo 1 || echo 0 )" \
  "$BIN" --level "$level" --out "$RESULTS/${tag}" \
    --gt "$RESULTS/gt/${tag}_gt.json" \
    --vendor "$vendor" --seed 0x5EED0000 2>&1 | tee "$log"
  local rc=${PIPESTATUS[0]}
  echo "==> $tag exit=$rc" >> "$RESULTS/logs/run_all.log"
}

main() {
  echo "build:" >&2
  cmake -S "$BASE/harness" -B "$BUILD" -G Ninja >/dev/null && ninja -C "$BUILD" >/dev/null || { echo "BUILD FAILED"; exit 1; }

  # detectar ICDs
  local RADV="/usr/share/vulkan/icd.d/radeon_icd.x86_64.json"
  local LVP="/usr/share/vulkan/icd.d/lvp_icd.x86_64.json"
  local ANV="/usr/share/vulkan/icd.d/intel_icd.x86_64.json"

  echo "=== sesion $(date -Is) ===" >> "$RESULTS/logs/run_all.log"

  # NIVEL A y B en RADV y lavapipe, 2 repeticiones
  for lvl in A B; do
    for rep in 1 2; do
      run_one "$lvl" radv "$rep" "$RADV" "0x1002"
      run_one "$lvl" lvp "$rep" "$LVP" "0x10005"
    done
  done

  echo "=== analisis ===" >> "$RESULTS/logs/run_all.log"
  for f in "$RESULTS"/recovered/*.lines; do
    [ -e "$f" ] || continue
    tag="$(basename "$f" .lines)"
    python3 "$BASE/harness/scripts/compare.py" \
      --gt "$RESULTS/gt/${tag}_gt.json" --rec "$f" \
      --out "$RESULTS/metrics/${tag}_metrics.json" | tee -a "$RESULTS/logs/run_all.log"
  done
  echo "TODO LISTO"
}

main "$@"
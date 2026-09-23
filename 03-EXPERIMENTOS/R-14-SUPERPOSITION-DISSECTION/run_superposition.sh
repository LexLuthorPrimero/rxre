#!/bin/bash
# Superposition benchmark run with telemetry
# Uso: ./run_superposition.sh [duration_seconds] [output_dir]

DUR=${1:-180}
OUTDIR=${2:-/home/lucas/Escritorio/RX550_Iterative_Research/experiments/R-14-SUPERPOSITION-DISSECTION/runs/superposition_$(date +%Y%m%d_%H%M%S)}
mkdir -p "$OUTDIR"

TELEMETRY_OUT="$OUTDIR/telemetria.csv"
SUPERPOSITION_LOG="$OUTDIR/superposition.log"
SUPERPOSITION_CSV="$OUTDIR/superposition.csv"
SUPERPOSITION_TXT="$OUTDIR/superposition.txt"

# Telemetría en background
/home/lucas/Escritorio/RX550_Iterative_Research/experiments/EXPLORATORIO-GravityMark/telemetria.sh $DUR "$TELEMETRY_OUT" &
TEL_PID=$!

# Superposition benchmark
cd /home/lucas/Escritorio/berchmark/instalados/Unigine_Superposition-1.1/bin
DRI_PRIME=1002:699f VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.x86_64.json \
./superposition \
  -project_name "Superposition" \
  -video_mode=-1 \
  -console_command "world_load superposition/superposition" \
  -extern_plugin "GPUMonitor" \
  -video_app opengl \
  -quality high \
  -mode default \
  -iterations 1 \
  -sound 0 \
  -fullscreen 0 \
  -resolution 1920x1080 \
  -log_csv "$SUPERPOSITION_CSV" \
  -log_txt "$SUPERPOSITION_TXT" \
  > "$SUPERPOSITION_LOG" 2>&1 &
SP_PID=$!

# Wait for Superposition to complete
wait $SP_PID
SP_EXIT=$?

# Kill telemetry if still running
kill $TEL_PID 2>/dev/null
wait $TEL_PID 2>/dev/null

echo "Superposition exit code: $SP_EXIT"
echo "Telemetry saved to: $TELEMETRY_OUT"
echo "Superposition log: $SUPERPOSITION_LOG"
echo "Results dir: $OUTDIR"

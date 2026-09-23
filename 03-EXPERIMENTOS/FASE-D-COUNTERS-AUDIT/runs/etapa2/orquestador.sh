#!/bin/bash
set -u
# FASE D / ETAPA 2 — Orquestador de corridas A/B×3 (PLAN aprobado)
# Solo lecturas: sysfs (telemetria.sh), radeontop (ioctls), UM-R (-r). Sin escritura de registros/SPM.
WORK=/home/lucas/Escritorio/RX550_Iterative_Research
BASE=$WORK/experiments/FASE-D-COUNTERS-AUDIT/runs/etapa2
DEV=/sys/class/drm/card1/device
HWMON=$DEV/hwmon/hwmon2
ROOT_UMR="sudo umr -i 1 -r"

STOPFILE="$BASE/.stop_all"

flight () { # $1=dir $2=pre|post
  {
    echo "== $2_flight $(date -Iseconds) =="
    echo "--pp_dpm_sclk--"; cat $DEV/pp_dpm_sclk
    echo "--pp_dpm_mclk--"; cat $DEV/pp_dpm_mclk
    echo "--gpu_busy_percent--"; cat $DEV/gpu_busy_percent
    echo "--mem_busy_percent--"; cat $DEV/mem_busy_percent
    echo "--power1_input(uW)--"; cat $HWMON/power1_input
    echo "--temp1_input(mC)--"; cat $HWMON/temp1_input
    echo "--vram_used--"; cat $DEV/mem_info_vram_used
    echo "--gtt_used--"; cat $DEV/mem_info_gtt_used
  } > "$1/${2}_flight.txt"
}

start_samplers () { # $1=dir $2=dur_telemetria $3=radeontop_lineas
  local RUN=$1 TELDUR=$2 RTDUR=$3
  $WORK/experiments/EXPLORATORIO-GravityMark/telemetria.sh "$TELDUR" "$RUN/telemetria.csv" &
  echo $! > "$RUN/.telpid"
  sudo radeontop -p /dev/dri/renderD129 -d "$RUN/radeontop.csv" -l "$RTDUR" -i 1 &
  echo $! > "$RUN/.rtopid"
  ( while [ ! -f "$RUN/.stop_umr" ]; do
      TS=$(date +%s%N)
      SPI=$($ROOT_UMR "polaris12.gfx800.mmSPI_CSQ_WF_ACTIVE_COUNT_*" 2>/dev/null | tr '\n' ' ')
      RLC=$($ROOT_UMR "polaris12.gfx800.mmRLC_GPU_CLOCK_COUNT_*" 2>/dev/null | tr '\n' ' ')
      GRBM=$($ROOT_UMR polaris12.gfx800.mmGRBM_PERFCOUNTER0_LO 2>/dev/null)
      echo "ts_ns=$TS | spi=[$SPI] rlc=[$RLC] grbm0_lo=[$GRBM]" >> "$RUN/umr_samples.csv"
      sleep 0.6
    done ) &
  echo $! > "$RUN/.umrloopid"
}

stop_samplers () { # $1=dir
  local RUN=$1
  touch "$RUN/.stop_umr" 2>/dev/null
  for f in .telpid .rtopid .umrloopid; do
    [ -f "$RUN/$f" ] && kill "$(cat "$RUN/$f")" 2>/dev/null
  done
  sleep 1
  pkill -f "telemetria.sh $RUN" 2>/dev/null
}

check_faults () { # $1=dir $2=start_epoch $3=end_epoch
  local RUN=$1 S=$2 E=$3
  local SISO EISO
  SISO=$(date -Iseconds -d "@$S" 2>/dev/null)
  EISO=$(date -Iseconds -d "@$E" 2>/dev/null)
  journalctl --since "$SISO" --until "$EISO" 2>/dev/null | grep -E "GPU fault|VM fault" > "$RUN/journal_pres.txt" || true
}

meta () { # $1=dir $2=workload $3=tercio
  {
    echo "workload=$2 replica=$3"
    echo "start=$(date -Iseconds) host=$(hostname)"
    echo "gpu=1002:699f (RX 550 polaris12) card1 renderD129"
    echo "kernel=$(uname -r) mesa=$(glxinfo -B 2>/dev/null | grep -m1 'OpenGL version' || echo n/a)"
    echo "samplers=telemetria@10Hz + radeontop@1Hz + UMR(SPI/RLC/GRBM)@~1Hz"
  } > "$1/metadata.txt"
}

run_superposition () { # $1=dir $2=replica
  local RUN=$1 RPL=$2 OUT="$1"
  flight "$RUN" pre
  start_samplers "$RUN" 260 275
  cd /home/lucas/Escritorio/berchmark/instalados/Unigine_Superposition-1.1/bin
  local T0_START=$(date +%s)
  DRI_PRIME=1002:699f ./superposition \
    -project_name "Superposition" -video_mode=-1 \
    -console_command "world_load superposition/superposition" \
    -extern_plugin "GPUMonitor" -video_app opengl -quality high \
    -mode default -iterations 1 -sound 0 -fullscreen 0 -resolution 1920x1080 \
    -log_csv "$OUT/superposition.csv" -log_txt "$OUT/superposition.txt" \
    > "$OUT/superposition.log" 2>&1 &
  local SP=$!
  # esperar a # score o timeout 260s
  local waited=0 found=0
  while [ $waited -le 260 ]; do
    if grep -q "Benchmark results" "$OUT/superposition.log" 2>/dev/null; then found=1; break; fi
    sleep 3; waited=$((waited+3))
  done
  if [ $found -eq 1 ]; then sleep 4; fi
  kill $SP 2>/dev/null; wait $SP 2>/dev/null
  local T0_END=$(date +%s)
  stop_samplers "$RUN"
  flight "$RUN" post
  check_faults "$RUN" "$T0_START" "$T0_END"
  echo "A$RPL:$([ $found -eq 1 ] && echo score || echo timeout) waited=${waited}s end=$(date -Iseconds)" | tee -a "$BASE/orquestador.log"
}

run_e03 () { # $1=dir $2=replica
  local RUN=$1 RPL=$2
  flight "$RUN" pre
  start_samplers "$RUN" 45 50
  cd $WORK/experiments/WORKLOAD-SINTETICO
  local T0_START=$(date +%s)
  DRI_PRIME=1002:699f ./main-graphics \
    --width 1920 --height 1080 --layers 4 --textures 4 --tex-size 4096 \
    --fma-iters 4 --msaa 1 --seed 0x13579BDF --seed-extra 0x2468ACE0 \
    --warmup 5 --duration 20 > "$RUN/stdout.txt" 2> "$RUN/stderr.txt"
  local T0_END=$(date +%s)
  stop_samplers "$RUN"
  flight "$RUN" post
  check_faults "$RUN" "$T0_START" "$T0_END"
  echo "B$RPL:end=$(date -Iseconds)" | tee -a "$BASE/orquestador.log"
}

idle_between () { # 60s entre workloads (A/B intercalado = siempre cambio)
  sleep 60
}

rm -f "$STOPFILE"
mkdir -p "$BASE/A1" "$BASE/B1" "$BASE/A2" "$BASE/B2" "$BASE/A3" "$BASE/B3"
meta "$BASE/A1" superposition 1; meta "$BASE/B1" e03 1
meta "$BASE/A2" superposition 2; meta "$BASE/B2" e03 2
meta "$BASE/A3" superposition 3; meta "$BASE/B3" e03 3

echo "=== inicio $BASE $(date -Iseconds) ===" | tee -a "$BASE/orquestador.log"
run_superposition "$BASE/A1" 1; idle_between
run_e03 "$BASE/B1" 1; idle_between
run_superposition "$BASE/A2" 2; idle_between
run_e03 "$BASE/B2" 2; idle_between
run_superposition "$BASE/A3" 3; idle_between
run_e03 "$BASE/B3" 3

echo "=== FIN $BASE $(date -Iseconds) ===" | tee -a "$BASE/orquestador.log"
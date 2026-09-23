#!/bin/bash
# Telemetría sysfs RX 550 (card1/hwmon2) — solo lectura. Uso: script <duration_s> <outfile>
DUR=${1:-60}
OUT=${2:-/home/lucas/Escritorio/RX550_Iterative_Research/experiments/EXPLORATORIO-GravityMark/runs/telemetria.csv}
DEV=/sys/class/drm/card1/device
HWMON=$DEV/hwmon/hwmon2
END=$(( $(date +%s) + DUR ))
echo "ts;power_uW;temp_mC;gpu_busy;mem_busy;vram_used;gtt_used;sclk_level;mclk_level" > "$OUT"
while [ "$(date +%s)" -lt "$END" ]; do
  TS=$(date +%s%N)
  PW=$(cat $HWMON/power1_input 2>/dev/null || echo 0)
  TP=$(cat $HWMON/temp1_input 2>/dev/null || echo 0)
  GB=$(cat $DEV/gpu_busy_percent 2>/dev/null || echo 0)
  MB=$(cat $DEV/mem_busy_percent 2>/dev/null || echo 0)
  VR=$(cat $DEV/mem_info_vram_used 2>/dev/null || echo 0)
  GT=$(cat $DEV/mem_info_gtt_used 2>/dev/null || echo 0)
  SCLK=$(grep -a '\*' $DEV/pp_dpm_sclk 2>/dev/null | tr -d ' ' || echo '?')
  MCLK=$(grep -a '\*' $DEV/pp_dpm_mclk 2>/dev/null | tr -d ' ' || echo '?')
  printf "%s;%s;%s;%s;%s;%s;%s;%s;%s\n" "$TS" "$PW" "$TP" "$GB" "$MB" "$VR" "$GT" "$SCLK" "$MCLK" >> "$OUT"
  sleep 0.1
done
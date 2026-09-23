#!/bin/bash
# telemetria.sh — muestreo READ-ONLY 10 Hz del DPM de la RX 550 (card1/hwmon2).
# Patrón heredado de experiments/EXPLORATORIO-GravityMark/telemetria.sh (validado),
# con columnas adicionales de nivel DPM activo. SOLO LECTURA: no escribe sysfs,
# no toca clocks, no programa contadores.
#
# Uso: telemetria.sh <duracion_s> <outfile.csv>
DUR=${1:-60}
OUT=${2:-/home/lucas/Escritorio/RX550_Iterative_Research/experiments/FASE-R4B-GOVERNOR/results/telemetria.csv}
DEV=/sys/class/drm/card1/device
HWMON=$DEV/hwmon/hwmon2
END=$(( $(date +%s) + DUR ))
echo "ts_ns;power_uW;temp_mC;gpu_busy;mem_busy;vram_used;gtt_used;sclk_level;sclk_mhz;mclk_level;mclk_mhz" > "$OUT"

# extrae nivel activo (con '*') e índice para pp_dpm_sclk/mclk
sclk_info() {
  # retorna "nivel mhz" de la línea activa, o "N/A N/A" (mhz sin sufijo)
  grep -a '\*' "$DEV/pp_dpm_sclk" 2>/dev/null | head -1 | awk -F'[: *]+' '{gsub(/[^0-9]/,"",$2); print $1, $2}'
}
mclk_info() {
  grep -a '\*' "$DEV/pp_dpm_mclk" 2>/dev/null | head -1 | awk -F'[: *]+' '{gsub(/[^0-9]/,"",$2); print $1, $2}'
}

while [ "$(date +%s)" -lt "$END" ]; do
  TS=$(date +%s%N)
  PW=$(cat $HWMON/power1_input 2>/dev/null || echo 0)
  TP=$(cat $HWMON/temp1_input 2>/dev/null || echo 0)
  GB=$(cat $DEV/gpu_busy_percent 2>/dev/null || echo 0)
  MB=$(cat $DEV/mem_busy_percent 2>/dev/null || echo 0)
  VR=$(cat $DEV/mem_info_vram_used 2>/dev/null || echo 0)
  GT=$(cat $DEV/mem_info_gtt_used 2>/dev/null || echo 0)
  read -r SL MHZ < <(sclk_info)
  read -r ML MMHZ < <(mclk_info)
  printf "%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s\n" "$TS" "$PW" "$TP" "$GB" "$MB" "$VR" "$GT" "${SL:-N/A}" "${MHZ:-N/A}" "${ML:-N/A}" "${MMHZ:-N/A}" >> "$OUT"
  sleep 0.1
done
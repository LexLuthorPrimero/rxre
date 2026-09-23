#!/usr/bin/env bash
# run_thermal_replicate.sh REP
# TEST TÉRMICO READ-ONLY (EXP-F4-A / FASE R-4B) — separado de S1.
# READ-ONLY absoluto: NUNCA escribe sysfs/kernel/firmware. Única carga = harness fixed s=1.00
# (actuador app-side); única medición = telemetria.sh 10 Hz. Escribe SOLO en
# experiments/FASE-R4B-THERMAL-TEST/runs/repREP/.
#
# Fases por réplica:  pre(snapshot read-only) → carga (harness s=1.00 hasta T>=90°C o tope 360 s)
#   → cooldown pasivo hasta condición de retorno (temp<=50C sostenido 30 s ∧ SCLK nivel 0 ∧ P<4 W)
#   → post(snapshot read-only) + verificación pre/post idénticos.
set -u

REP="${1:?uso: run_thermal_replicate.sh REP}"
BASE="$(cd "$(dirname "$0")" && pwd)"
EXP="$BASE/../FASE-R4B-GOVERNOR"
BIN="$EXP/harness/build/governor_harness"
TEL="$EXP/telemetry/telemetria.sh"
ICD="/usr/share/vulkan/icd.d/radeon_icd.x86_64.json"
DEV=/sys/class/drm/card1/device
HWMON=$DEV/hwmon/hwmon2
R="$BASE/runs/rep$REP"
mkdir -p "$R"
LOG="$R/log.txt"
TEL_DUR=1500          # 1500 s ≈ 25 min tope: carga + cooldown
LOAD_TIMEOUT=360      # tope de carga (s)
TARGET_T=90000        # 90 °C en m°C: detener carga (margen bajo crit 97 °C)
RETURN_T=50000        # 50 °C en m°C (DN-07), sostenido ≥6 polls de 5 s
RETURN_P=4000000      # < 4 W en µW
COOLDOWN_TIMEOUT=1200 # tope cooldown (s) tras fin de carga

ts() { date +%s%N; }
nowi() { date +%s; }

snapshot() {
  local f="$1"
  {
    echo "== $(date -Is) =="
    echo "--- pp_dpm_sclk ---"; cat $DEV/pp_dpm_sclk 2>&1
    echo "--- pp_dpm_mclk ---"; cat $DEV/pp_dpm_mclk 2>&1
    echo "--- power1_cap ---"; cat $HWMON/power1_cap 2>&1
    echo "--- kalm ---"; ps -o pid,comm,args -p 4086,4087 2>&1
    echo "--- gpu_busy/temp/power ---"
    cat $DEV/gpu_busy_percent 2>&1; cat $HWMON/temp1_input 2>&1; cat $HWMON/power1_input 2>&1
  } > "$f"
}

log() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

# --- pre: condiciones de partida (read-only) ---
log "==> REP$REP iniciando"
busy=$(cat $DEV/gpu_busy_percent 2>/dev/null || echo NA)
temp0=$(cat $HWMON/temp1_input 2>/dev/null || echo NA)
if [ "$busy" != "0" ]; then log "ABORT: gpu_busy=$busy (debe ser 0)"; exit 3; fi
snapshot "$R/pre.txt"
log "pre snap: busy=$busy temp=$((temp0/1000))C cap=$(cat $HWMON/power1_cap) kalm=$(ps -o pid= -p 4086,4087 | tr '\n' ' ')"

# --- telemetría continua (calentamiento + cooldown en un solo CSV) ---
bash "$TEL" $TEL_DUR "$R/telemetry.csv" &
TP=$!
sleep 2

# --- carga: harness fixed s=1.00 ---
mkdir -p "$R/load"
t_load_start=$(nowi)
log "carga: inicio s=1.00 (mono $(date +%s%N))"
VK_ICD_FILENAMES="$ICD" "$BIN" --mode fixed --scale 1.00 --warm 0 --duration 300 \
  --out "$R/load/run" --vendor 0x1002 --device 0x699F --seed 0x5EED0000 \
  >>"$R/harness.log" 2>&1 &
HP=$!
# vigilar temp durante carga; detener en T>=TARGET_T o timeout
elapsed=0
killed=0
while [ "$elapsed" -lt "$LOAD_TIMEOUT" ]; do
  if ! kill -0 "$HP" 2>/dev/null; then break; fi
  T=$(cat $HWMON/temp1_input 2>/dev/null || echo 0)
  if [ "$T" -ge "$TARGET_T" ]; then
    log "carga: T=${T}>=${TARGET_T} -> TERM harness a t=${elapsed}s"
    kill -TERM "$HP" 2>/dev/null; killed=1
    for i in 1 2 3 4 5 6 7 8 9 10; do kill -0 "$HP" 2>/dev/null || break; sleep 1; done
    break
  fi
  sleep 5; elapsed=$((elapsed+5))
done
if [ "$killed" = 0 ] && kill -0 "$HP" 2>/dev/null; then
  log "carga: timeout sin alcanzar TARGET_T; esperando harness"
fi
wait "$HP" 2>/dev/null
t_load_end=$(nowi)
log "carga: fin a t=$((t_load_end-t_load_start))s (killed=$killed) mono-fin $(date +%s%N)"
mv "$R/load/run_frames.tsv" "$R/frames.tsv" 2>/dev/null
mv "$R/load/run_m0.txt" "$R/m0.txt" 2>/dev/null

# --- cooldown pasivo hasta condición de retorno ---
log "cooldown: esperando temp<=50C ∧ sclk=nivel0 ∧ P<4W (tope ${COOLDOWN_TIMEOUT}s)"
T_prev=-1; cnt_ok=0
elapsed=0
RET_T=""; RET_SCLK=""; RET_P=""
while [ "$elapsed" -lt "$COOLDOWN_TIMEOUT" ]; do
  sleep 5; elapsed=$((elapsed+5))
  T=$(cat $HWMON/temp1_input 2>/dev/null || echo 0)
  L=$(grep -a '\*' $DEV/pp_dpm_sclk 2>/dev/null | head -1 | awk -F'[: *]+' '{print $1}')
  P=$(cat $HWMON/power1_input 2>/dev/null || echo 0)
  if [ "$T" -le "$RETURN_T" ] && [ "${L:-9}" = "0" ] && [ "$P" -lt "$RETURN_P" ]; then
    cnt_ok=$((cnt_ok+1))
    [ -z "$RET_T" ] && { RET_T=$T; RET_SCLK=$L; RET_P=$P; }
    if [ "$cnt_ok" -ge 6 ]; then  # 6 polls x 5 s = 30 s sostenido
      log "cooldown: CONDICION alcanzada (temp=${T} C sclk_nivel=$L P=$P uW) a +${elapsed}s"
      break
    fi
  else
    cnt_ok=0; RET_T=""; RET_SCLK=""; RET_P=""
  fi
  T_prev=$T
done
t_cond=$(nowi)
if [ -n "$RET_T" ]; then
  log "retorno: temp_final=$RET_T sclk_nivel=$RET_SCLK power=$RET_P uW @ t_cooldown=$((t_cond-t_load_end))s"
else
  log "WARN: condición no alcanzada en tope; temp final=$(cat $HWMON/temp1_input) sclk=$(grep -a '\*' $DEV/pp_dpm_sclk | head -1)"
fi

# --- fin + verificación read-only ---
sleep 2
snapshot "$R/post.txt"
kill "$TP" 2>/dev/null; wait "$TP" 2>/dev/null
PRE=$(grep '\*' "$R/pre.txt" | md5sum | cut -c1-10)
POST=$(grep '\*' "$R/post.txt" | md5sum | cut -c1-10)
if [ "$PRE" != "$POST" ]; then
  log "ALERTA VERIFICACIÓN READ-ONLY: DPM activo pre($PRE) != post($POST)"
else
  log "verify read-only: DPM/kalm idénticos pre/post ($PRE)"
fi
# guardar tiempos de referencia (epoch s) para análisis
{
  echo "REP=$REP"; echo "t_load_start=$t_load_start"; echo "t_load_end=$t_load_end";
  echo "t_cond=$t_cond"; [ -n "$RET_T" ] && echo "ret_T=${RET_T}"; echo "ret_sclk_nivel=${RET_SCLK:-NA}";
  echo "ret_P=${RET_P:-NA}"
} > "$R/timings.txt"
wc -l "$R/telemetry.csv" >> "$LOG"
log "==> REP$REP finalizado"
exit 0
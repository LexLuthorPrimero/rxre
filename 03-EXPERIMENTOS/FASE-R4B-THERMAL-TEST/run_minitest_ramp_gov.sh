#!/usr/bin/env bash
# run_minitest_ramp_gov.sh REP
# MINI-TEST 7.3-B (EXP-F4-A / FASE R-4B) — ramp con governor activo, N=2 (una réplica por
# invocación). APROBADO por el usuario 2026-09-23, ANTES de S2. NO forma parte de S2;
# sus resultados NO entran en T, s*, R1-R7 ni veredicto.
#
# READ-ONLY absoluto: nunca escribe sysfs/kernel/contadores. Única carga = harness
# `--mode dist --duration 200` (steps N:4->8->4 internos a +60/+120 s) con el MISMO governor
# que usará R7 (governor.py, banda [0.90,1.10]*T, T=9.168 ms FREEZE de S1-v2.2). Solo
# telemetría read-only + control_scale.txt/governor_trace.tsv dentro de los datos de la réplica.
#
# Fases por réplica:
#   pre(snapshot) -> cooldown_previo DN-07 (T<=50C s30s ∧ SCLK nv0 ∧ P<4W) + initial_state
#   -> carga (harness dist 200 s + governor) con monitor pasivo y aborto si T>=96 C
#   -> cooldown_post hasta DN-07 (tiempo real registrado) -> post(snapshot) + verificación.
set -u

REP="${1:?uso: run_minitest_ramp_gov.sh REP (1|2)}"
BASE="$(cd "$(dirname "$0")" && pwd)"
EXP="$BASE/../FASE-R4B-GOVERNOR"
BIN="$EXP/harness/build/governor_harness"
TEL="$EXP/telemetry/telemetria.sh"
GOV="$EXP/controller/governor.py"
ICD="/usr/share/vulkan/icd.d/radeon_icd.x86_64.json"
DEV=/sys/class/drm/card1/device
HWMON=$DEV/hwmon/hwmon2
R="$BASE/runs/minitest-ramp-gov/rep$REP"
mkdir -p "$R/load"
LOG="$R/log.txt"

T_MS=9.168            # FREEZE (S1-v2.2), usado como entrada, NO modificado
DUR=200               # duración DIST pre-committed
TEL_DUR=$((DUR + 60)) # 260 s: cubre warm 5 + 200 + margen
ABORT_T=96000         # m°C; margen 1 °C bajo temp1_crit 97 °C (solo fallo anómalo)
RETURN_T=50000        # DN-07
RETURN_P=4000000
COOLDOWN_TIMEOUT=1200

ts()  { date +%s%N; }
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

sclk_nivel() { grep -a '\*' "$DEV/pp_dpm_sclk" 2>/dev/null | head -1 | awk -F'[: *]+' '{print $1}'; }
sclk_mhz()   { grep -a '\*' "$DEV/pp_dpm_sclk" 2>/dev/null | head -1 | awk -F'[: *]+' '{gsub(/[^0-9]/,"",$2); print $2}'; }
mclk_mhz()   { grep -a '\*' "$DEV/pp_dpm_mclk" 2>/dev/null | head -1 | awk -F'[: *]+' '{gsub(/[^0-9]/,"",$2); print $2}'; }
temp_mC()    { cat "$HWMON/temp1_input" 2>/dev/null || echo 0; }
power_uW()   { cat "$HWMON/power1_input" 2>/dev/null || echo 0; }

# --- cooldown pasivo hasta DN-07 (tipo v2.2/test térmico); registra tiempo real ---
cooldown() {
  local label="$1" out="$2"
  log "COOLDOWN ${label}: esperando temp<=50C s30s ∧ SCLK nv0 ∧ P<4W"
  local t0=$(ts) ok=0 T=0 L=9 P=999999999
  local elap=0
  while [ "$elap" -lt "$COOLDOWN_TIMEOUT" ]; do
    sleep 5
    T=$(temp_mC); L=$(sclk_nivel); P=$(power_uW)
    if [ "$T" -le "$RETURN_T" ] && [ "${L:-9}" = "0" ] && [ "$P" -lt "$RETURN_P" ]; then
      ok=$((ok+1))
    else
      ok=0
    fi
    if [ "$ok" -ge 6 ]; then break; fi   # 6 x 5 s = 30 s sostenido
    elap=$((elap+5))
  done
  local tf=$(ts)
  local dur_ms=$(( (tf - t0) / 1000000 ))
  { echo "label=$label"; echo "inicio_mono_ns=$t0"; echo "fin_mono_ns=$tf";
    echo "dur_ms=$dur_ms"; echo "dur_s=$(( dur_ms / 1000 ))"; echo "ret_temp_mC=$T";
    echo "ret_sclk_nivel=$L"; echo "ret_power_uW=$P"; } > "$out"
  if [ "$ok" -ge 6 ]; then
    log "COOLDOWN ${label} FIN en $(( dur_ms / 1000 ))s (T=$T sclk=$L P=$P) -> $out"
  else
    log "COOLDOWN ${label} TIMEOUT sin condición: T=$T sclk=$L P=$P (revisar)"
  fi
}

# ================= REPLICA =================
log "==> MINITEST-RAMP-GOV REP$REP iniciando"
busy=$(cat $DEV/gpu_busy_percent 2>/dev/null || echo NA)
if [ "$busy" != "0" ]; then log "ABORT: gpu_busy=$busy (debe ser 0)"; exit 3; fi
snapshot "$R/pre.txt"
log "pre: busy=$busy temp=$(( $(temp_mC) / 1000 ))C cap=$(cat $HWMON/power1_cap) kalm=$(ps -o pid= -p 4086,4087 | tr '\n' ' ')"

cooldown "previo" "$R/cooldown_prev.tsv"

# estado de partida exacto (pedido por el usuario)
{
  echo "== $(date -Is) =="
  echo "temp_mC=$(temp_mC)"
  echo "sclk_nivel=$(sclk_nivel) sclk_mhz=$(sclk_mhz)"
  echo "mclk_nivel=$(grep -a '\*' $DEV/pp_dpm_mclk | head -1 | awk -F'[: *]+' '{print $1}') mclk_mhz=$(mclk_mhz)"
  echo "power_uW=$(power_uW)"
  echo "gpu_busy=$(cat $DEV/gpu_busy_percent)"
} > "$R/initial_state.txt"
log "initial_state: T=$(( $(temp_mC) / 1000 ))C sclk=$(sclk_mhz)MHz mclk=$(mclk_mhz)MHz P=$(( $(power_uW) / 1000 ))mW"

# --- telemetría 10 Hz (carga completa) ---
bash "$TEL" $TEL_DUR "$R/telemetry.csv" & TP=$!
sleep 2

# --- carga: harness DIST 200 s + governor ---
rm -f "$R/load/control_scale.txt" "$R/load/governor_trace.tsv" "$R/load/run_frames.tsv" "$R/load/run_m0.txt"
t_load_start=$(nowi)
log "carga: DIST 200 s inicio (mono $(ts))"
VK_ICD_FILENAMES="$ICD" "$BIN" --mode dist --warm 5 --duration "$DUR" \
  --out "$R/load/run" --control "$R/load/control_scale.txt" \
  --vendor 0x1002 --device 0x699F --seed 0x5EED0000 \
  >"$R/harness.log" 2>&1 &
HP=$!

# esperar m0 (tope 30 s) y arrancar governor
m0=0
for i in $(seq 1 120); do
  [ -f "$R/load/run_m0.txt" ] && { m0=$(head -1 "$R/load/run_m0.txt"); break; }
  sleep 0.25
done
if [ "$m0" = 0 ]; then
  log "FATAL: no m0"; kill "$HP" 2>/dev/null; kill "$TP" 2>/dev/null; exit 9
fi
log "m0=$m0 — gobernador en marcha (T=${T_MS} ms, banda [8.25,10.08] ms)"
python3 "$GOV" --frames "$R/load/run_frames.tsv" --control "$R/load/control_scale.txt" \
  --t0-us "$m0" --T-ms "$T_MS" --duration "$DUR" --trace "$R/load/governor_trace.tsv" \
  >>"$R/governor.log" 2>&1 &
GP=$!

# --- monitor pasivo (5 s) + aborto de seguridad ---
{
  echo "ts_epoch_s;temp_mC;sclk_nivel;sclk_mhz;power_uW"
  while kill -0 "$HP" 2>/dev/null || kill -0 "$GP" 2>/dev/null; do
    echo "$(nowi);$(temp_mC);$(sclk_nivel);$(sclk_mhz);$(power_uW)"
    T=$(temp_mC)
    if [ "$T" -ge "$ABORT_T" ]; then
      log "ABORTO SEGURIDAD: T=${T}mC >= ${ABORT_T} (crit 97000) — SIGTERM a harness/governor"
      kill -TERM "$HP" 2>/dev/null; kill -TERM "$GP" 2>/dev/null
      echo "ABORTED"
      break
    fi
    sleep 5
  done
} > "$R/monitor_carga.tsv"

wait "$GP" 2>/dev/null; wait "$HP" 2>/dev/null; wait "$TP" 2>/dev/null
t_load_end=$(nowi)
log "carga: fin a t=$((t_load_end - t_load_start))s"

mv "$R/load/run_frames.tsv" "$R/frames.tsv" 2>/dev/null
mv "$R/load/run_m0.txt"    "$R/m0.txt"    2>/dev/null
mv "$R/load/control_scale.txt" "$R/control_scale.txt" 2>/dev/null
mv "$R/load/governor_trace.tsv" "$R/governor_trace.tsv" 2>/dev/null

# --- cooldown post hasta DN-07 (tiempo real) ---
cooldown "post" "$R/cooldown_post.tsv"
sleep 2
snapshot "$R/post.txt"

# --- verificación read-only: DPM activo + kalm idénticos pre/post ---
PRE=$(grep '\*' "$R/pre.txt" | md5sum | cut -c1-10)
POST=$(grep '\*' "$R/post.txt" | md5sum | cut -c1-10)
if [ "$PRE" != "$POST" ]; then
  log "ALERTA VERIFICACIÓN READ-ONLY: DPM activo pre($PRE) != post($POST)"
else
  log "verify read-only: DPM/kalm idénticos pre/post ($PRE)"
fi

# timestamps de referencia para análisis
{
  echo "REP=$REP"; echo "t_load_start=$t_load_start"; echo "t_load_end=$t_load_end"
  echo "m0_mono_us=$m0"
  echo "t_abort=$(grep -c ABORTED "$R/monitor_carga.tsv" 2>/dev/null || echo 0)"
} > "$R/timings.txt"
wc -l "$R/telemetry.csv" >> "$LOG"
log "==> MINITEST-RAMP-GOV REP$REP finalizado"
exit 0
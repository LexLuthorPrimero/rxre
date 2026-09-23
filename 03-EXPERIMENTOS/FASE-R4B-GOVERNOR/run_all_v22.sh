#!/usr/bin/env bash
# run_all_v22.sh — ejecuta EXP-F4-A (FASE R-4B) PROTOCOLO v2.2 para la SESIÓN 1.
# ============================================================================
# VARIACIÓN PROCEDIMENTAL v2.2 (autorizada 2026-09-23): cooldown pasivo entre los
# passes de Fase 1 (p1->p2 y p2->p3) con condición de retorno TELEMÉTRICA:
#   temp1_input <= 50 C sostenido >=30 s   ∧   SCLK activo = nivel 0   ∧   power < 4 W
# ~270 s es expectativa inicial, NO tope. Si no cumple -> seguir enfriando. Se
# registra el tiempo real de cada cooldown en fase1/cooldown{1,2}.tsv.
# TODO lo demás (workload, T, s*, escalas, thresholds, R1-R7, F1-F6, bloques,
# duraciones, criterios de parada A-D) = PROTOCOLO v2.1 SIN CAMBIOS.
# Los datos de la S1 v2.1 (PARADA D) NO se tocan: esta sesión escribe en
# results/session1-v22/ y su manifest/T/s* se computa SOLO con sus propios datos.
#
# READ-ONLY absoluto: nunca escribe sysfs/kernel/contadores; solo results/ y el
# archivo de control control_scale.txt dentro de los datos de esta fase.
#
# Uso: run_all_v22.sh
set -u

S=1
BASE="$(cd "$(dirname "$0")" && pwd)"
BUILD="$BASE/harness/build"
BIN="$BUILD/governor_harness"
TEL="$BASE/telemetry/telemetria.sh"
GOV="$BASE/controller/governor.py"
ANALYZE="$BASE/harness/scripts/analyze.py"
R="$BASE/results"
SESS="$R/session${S}-v22"
ICD="/usr/share/vulkan/icd.d/radeon_icd.x86_64.json"
DEV=/sys/class/drm/card1/device
HWMON=$DEV/hwmon/hwmon2

mkdir -p "$SESS/fase1/blocks" "$SESS/fase2" "$R/logs"

# --- snapshot sysfs READ-ONLY (no se escribe nada) ---
snapshot() {
  local f="$1"
  {
    echo "== $(date -Is) =="
    echo "--- pp_dpm_sclk ---"; cat $DEV/pp_dpm_sclk 2>&1
    echo "--- pp_dpm_mclk ---"; cat $DEV/pp_dpm_mclk 2>&1
    echo "--- power1_cap ---"; cat $HWMON/power1_cap 2>&1
    echo "--- kalm ---"; ps -o pid,comm,args -p 4086,4087 2>&1
    echo "--- gpu_busy/temp/power ---"
    cat $DEV/gpu_busy_percent 2>&1
    cat $HWMON/temp1_input 2>&1
    cat $HWMON/power1_input 2>&1
  } > "$f"
}

log() { echo "[run_all_v22] $*" | tee -a "$R/logs/session${S}-v22.log"; }

# --- build del harness (no toca el workload) ---
cmake -S "$BASE/harness" -B "$BUILD" -G Ninja >/dev/null 2>&1 \
  && ninja -C "$BUILD" >/dev/null 2>&1 \
  || { log "BUILD FAILED"; exit 1; }
log "build ok"

snapshot "$SESS/pre_flight.txt"
log "pre_flight ok (latidos de S1-v2.1 intactos)"

# --- warm-up global 30 s a s=1.00 (excluido del análisis) ---
"$BIN" --mode fixed --scale 1.00 --warm 30 --duration 3 \
  --out "$SESS/warmup/run" --vendor 0x1002 --device 0x699F --seed 0x5EED0000 \
  >/dev/null 2>&1
rm -rf "$SESS/warmup"
log "warm-up global ok"

# --- COOLDOWN v2.2: espera pasiva con condición telemétrica ---
# $1 = etiqueta (p1->p2 | p2->p3)   $2 = índice (1|2)
cooldown_pass() {
  local label="$1" idx="$2"
  local out="$SESS/fase1/cooldown${idx}.tsv"
  log "COOLDOWN ${label} INICIO (esperando temp<=50C ∧ SCLK nv0 ∧ P<4W)"
  local t0=$(date +%s%N)
  local ok=0
  local T=0 L=9 P=999999999
  while :; do
    sleep 5
    T=$(cat $HWMON/temp1_input 2>/dev/null || echo 0)
    L=$(grep -a '\*' $DEV/pp_dpm_sclk 2>/dev/null | head -1 | awk -F'[: *]+' '{print $1}')
    P=$(cat $HWMON/power1_input 2>/dev/null || echo 0)
    if [ "$T" -le 50000 ] && [ "${L:-9}" = "0" ] && [ "$P" -lt 4000000 ]; then
      ok=$((ok+1))
    else
      ok=0
    fi
    # sostenido >=30 s = 6 muestras consecutivas de 5 s
    if [ "$ok" -ge 6 ]; then
      break
    fi
    # tope de seguridad anti-deadlock (60 min); condición normalmente ~270 s
    local elap=$(( ($(date +%s) - t0/1000000000 ) ))
    if [ "$elap" -ge 3600 ]; then
      log "COOLDOWN ${label} TIMEOUT 3600s sin retorno (T=${T} sclk=${L} P=${P}uW) — PARADA D"
      exit 9
    fi
  done
  local tf=$(date +%s%N)
  local dur_ms=$(( (tf - t0) / 1000000 ))
  local dur_s=$(( dur_ms / 1000 ))
  { echo "label=$label"; echo "inicio_mono_ns=$t0"; echo "fin_mono_ns=$tf";
    echo "dur_ms=$dur_ms"; echo "dur_s=$dur_s"; echo "ret_temp_mC=$T";
    echo "ret_sclk_nivel=$L"; echo "ret_power_uW=$P"; } > "$out"
  log "COOLDOWN ${label} FIN en ${dur_s}s (T=${T} sclk_nivel=$L P=${P}uW) -> $out"
}

# --- FASE 1: 15 bloques open-loop (passes asc/desc/asc) con cooldown v2.2 ---
run_block() {
  local pass="$1" scale="$2" tag="$3"
  local blk="$SESS/fase1/blocks/${pass}_${tag}"
  mkdir -p "$blk"
  bash "$TEL" 30 "$blk/telemetry.csv" &
  local tp=$!
  VK_ICD_FILENAMES="$ICD" \
  "$BIN" --mode fixed --scale "$scale" --warm 5 --duration 20 \
    --out "$blk/run" --vendor 0x1002 --device 0x699F --seed 0x5EED0000 \
    >"$R/logs/block_${pass}_${tag}.log" 2>&1
  wait "$tp"
  mv "$blk/run_frames.tsv" "$blk/frames.tsv" 2>/dev/null
  mv "$blk/run_m0.txt" "$blk/m0.txt" 2>/dev/null
}
log "Fase 1 (15 bloques + 2 cooldowns v2.2)…"
# pass asc p1: 1.00→0.50
for sc in 1.00 0.87 0.75 0.62 0.50; do run_block p1 "$sc" "s${sc/./}"; done
cooldown_pass "p1->p2" 1
# pass desc p2: 0.50→1.00
for sc in 0.50 0.62 0.75 0.87 1.00; do run_block p2 "$sc" "s${sc/./}"; done
cooldown_pass "p2->p3" 2
# pass asc p3: 1.00→0.50
for sc in 1.00 0.87 0.75 0.62 0.50; do run_block p3 "$sc" "s${sc/./}"; done
log "Fase 1 completa (con cooldowns v2.2)"

# --- FREEZE(T, s*) + GATEs (parada D si fallan) — SOLO con estos datos ---
if ! python3 "$ANALYZE" phase1 --session-dir "$SESS" >"$R/logs/session${S}-v22.phase1.log" 2>&1; then
  log "PARADA D en Fase 1 (gates/reachability) — ver $R/logs/session${S}-v22.phase1.log"
  exit 9
fi
T=$(python3 -c "import json;print(json.load(open('$SESS/fase1/manifest.json'))['T_ms'])")
SSTAR=$(python3 -c "import json;print(json.load(open('$SESS/fase1/manifest.json'))['s_star'])")
SHA=$(python3 -c "import json;print(json.load(open('$SESS/fase1/manifest.json'))['sha256'][:16])")
log "FREEZE(v2.2) T=${T} ms s*=${SSTAR} sha256=${SHA}…"
echo "$SHA" > "$SESS/fase1/frozen.sha256"

# --- PHASE 2: trials alternados (idénticos a v2.1) ---
run_trial() {
  local cond="$1" idx="$2"
  local trial="$SESS/fase2/${cond}${idx}"
  mkdir -p "$trial"
  local dur
  case "$cond" in
    fixed) dur=60 ;;
    gov)   dur=120 ;;
    dist)  dur=200 ;;
  esac
  bash "$TEL" $((dur + 12)) "$trial/telemetry.csv" &
  local tp=$!
  if [ "$cond" = fixed ]; then
    VK_ICD_FILENAMES="$ICD" \
    "$BIN" --mode fixed --scale 1.00 --warm 5 --duration "$dur" \
      --out "$trial/run" --vendor 0x1002 --device 0x699F --seed 0x5EED0000 \
      >"$R/logs/trial_${cond}${idx}.log" 2>&1
  else
    rm -f "$trial/control_scale.txt" "$trial/governor_trace.tsv"
    VK_ICD_FILENAMES="$ICD" \
    "$BIN" --mode "$cond" --warm 5 --duration "$dur" \
      --out "$trial/run" --control "$trial/control_scale.txt" \
      --vendor 0x1002 --device 0x699F --seed 0x5EED0000 \
      >"$R/logs/trial_${cond}${idx}.log" 2>&1 &
    local hp=$!
    local t0=0
    for i in $(seq 1 120); do
      [ -f "$trial/run_m0.txt" ] && { t0=$(head -1 "$trial/run_m0.txt"); break; }
      sleep 0.25
    done
    if [ "$t0" = 0 ]; then
      log "FATAL: no m0 en trial ${cond}${idx}"; kill "$hp" 2>/dev/null; exit 9
    fi
    python3 "$GOV" --frames "$trial/run_frames.tsv" \
      --control "$trial/control_scale.txt" --t0-us "$t0" \
      --T-ms "$T" --duration "$dur" --trace "$trial/governor_trace.tsv" \
      >>"$R/logs/governor_${cond}${idx}.log" 2>&1
    wait "$hp"
  fi
  wait "$tp"
  log "trial ${cond}${idx} ok"
}

case "$S" in
  1) ORDER="fixed gov fixed gov fixed gov dist dist" ;;
  2) ORDER="gov fixed gov fixed gov fixed dist dist" ;;
esac
python3 -c "import json; json.dump('$ORDER'.split(), open('$SESS/fase2/order.json','w'), indent=1)"
cnt_f=0; cnt_g=0; cnt_d=0
for c in $ORDER; do
  case "$c" in
    fixed) cnt_f=$((cnt_f+1)); run_trial fixed "$cnt_f" ;;
    gov)   cnt_g=$((cnt_g+1)); run_trial gov   "$cnt_g" ;;
    dist)  cnt_d=$((cnt_d+1)); run_trial dist  "$cnt_d" ;;
  esac
done

snapshot "$SESS/post_flight.txt"
log "post_flight ok"

# verificación read-only: DPM activo y kalm deben coincidir pre/post
PRE=$(grep '\*' "$SESS/pre_flight.txt" | md5sum | cut -d' ' -f1)
POST=$(grep '\*' "$SESS/post_flight.txt" | md5sum | cut -d' ' -f1)
if [ "$PRE" != "$POST" ]; then
  log "ALERTA VERIFICACIÓN READ-ONLY: DPM/kalm cambiaron pre→post (¿escritura?)"
else
  log "verify read-only: DPM/kalm idénticos pre/post ($PRE)"
fi

# análisis Phase 2 de esta sesión
python3 "$ANALYZE" phase2 --session-dir "$SESS" --order "$(echo $ORDER | tr ' ' ',')" \
  >>"$R/logs/session${S}-v22.phase2.log" 2>&1
log "sesión ${S}-v22 completada"
exit 0
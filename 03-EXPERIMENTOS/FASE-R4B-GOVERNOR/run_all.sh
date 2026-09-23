#!/usr/bin/env bash
# run_all.sh — ejecuta EXP-F4-A (FASE R-4B) por sesión.
# READ-ONLY absoluto: nunca escribe sysfs/kernel/contadores; solo resultados/ y
# el archivo de control control_scale.txt dentro de results/ de esta fase.
#
# Sesión (protocolo §7):
#   pre_flight → warm-up global 30 s (excluido) → Fase 1 (15 bloques open-loop)
#   → FREEZE(T, s*) con sha256 en manifest → Phase 2 (orden alternado según sesión)
#   → post_flight (verificación read-only: DPM y kalm sin cambios).
#
# Uso:
#   run_all.sh SESSION          # SESSION ∈ {1,2}
set -u

S="${1:?uso: run_all.sh SESSION}"
BASE="$(cd "$(dirname "$0")" && pwd)"
BUILD="$BASE/harness/build"
BIN="$BUILD/governor_harness"
TEL="$BASE/telemetry/telemetria.sh"
GOV="$BASE/controller/governor.py"
ANALYZE="$BASE/harness/scripts/analyze.py"
R="$BASE/results"
SESS="$R/session$S"
ICD="/usr/share/vulkan/icd.d/radeon_icd.x86_64.json"

mkdir -p "$SESS/fase1/blocks" "$SESS/fase2" "$R/logs"

# --- snapshot sysfs READ-ONLY (no se escribe nada) ---
snapshot() {
  local f="$1"
  {
    echo "== $(date -Is) =="
    echo "--- pp_dpm_sclk ---"; cat /sys/class/drm/card1/device/pp_dpm_sclk 2>&1
    echo "--- pp_dpm_mclk ---"; cat /sys/class/drm/card1/device/pp_dpm_mclk 2>&1
    echo "--- power1_cap ---"; cat /sys/class/drm/card1/device/hwmon/hwmon2/power1_cap 2>&1
    echo "--- kalm ---"; ps -o pid,comm,args -p 4086,4087 2>&1
    echo "--- gpu_busy/temp/power ---"
    cat /sys/class/drm/card1/device/gpu_busy_percent 2>&1
    cat /sys/class/drm/card1/device/hwmon/hwmon2/temp1_input 2>&1
    cat /sys/class/drm/card1/device/hwmon/hwmon2/power1_input 2>&1
  } > "$f"
}

log() { echo "[run_all:S$S] $*" | tee -a "$R/logs/session$S.log"; }

# build
cmake -S "$BASE/harness" -B "$BUILD" -G Ninja >/dev/null 2>&1 \
  && ninja -C "$BUILD" >/dev/null 2>&1 \
  || { log "BUILD FAILED"; exit 1; }
log "build ok"

snapshot "$SESS/pre_flight.txt"
log "pre_flight ok"

# --- warm-up global 30 s a s=1.00 (excluido del análisis) ---
"$BIN" --mode fixed --scale 1.00 --warm 30 --duration 3 \
  --out "$SESS/warmup/run" --vendor 0x1002 --device 0x699F --seed 0x5EED0000 \
  >/dev/null 2>&1
rm -rf "$SESS/warmup"
log "warm-up global ok"

# --- FASE 1: 15 bloques open-loop (passes asc/desc/asc) ---
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
log "Fase 1 (15 bloques)…"
# pass asc p1: 1.00→0.50
for sc in 1.00 0.87 0.75 0.62 0.50; do run_block p1 "$sc" "s${sc/./}"; done
# pass desc p2: 0.50→1.00
for sc in 0.50 0.62 0.75 0.87 1.00; do run_block p2 "$sc" "s${sc/./}"; done
# pass asc p3: 1.00→0.50
for sc in 1.00 0.87 0.75 0.62 0.50; do run_block p3 "$sc" "s${sc/./}"; done
log "Fase 1 completa"

# --- FREEZE(T, s*) + GATEs (parada D si fallan) ---
if ! python3 "$ANALYZE" phase1 --session-dir "$SESS" >"$R/logs/session$S.phase1.log" 2>&1; then
  log "PARADA D en Fase 1 (gates/reachability) — ver $R/logs/session$S.phase1.log"
  exit 9
fi
T=$(python3 -c "import json;print(json.load(open('$SESS/fase1/manifest.json'))['T_ms'])")
SSTAR=$(python3 -c "import json;print(json.load(open('$SESS/fase1/manifest.json'))['s_star'])")
SHA=$(python3 -c "import json;print(json.load(open('$SESS/fase1/manifest.json'))['sha256'][:16])")
log "FREEZE T=${T} ms s*=${SSTAR} sha256=${SHA}…"
echo "$SHA" > "$SESS/fase1/frozen.sha256"

# --- PHASE 2: trials alternados ---
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
    # esperar m0 del harness (escribe run_m0.txt al inicio de la fase medida)
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
  >>"$R/logs/session$S.phase2.log" 2>&1
log "sesión $S completada"
exit 0
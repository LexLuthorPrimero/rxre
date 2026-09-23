#!/usr/bin/env bash
# run_all_v23.sh — EXP-F4-A (FASE R-4B) PROTOCOLO v2.3, SESIÓN <1|2>.
# ============================================================================
# v2.3 = ÚNICA variación procedimental frente a v2.2/v2.1: cooldown telemétrico
# ANTES DE CADA trial consecutivo de Phase 2 (incluido el 1º tras FREEZE), con
# umbrales de entrada por tipo de trial y registro del tiempo real de cooldown:
#   FIXED (60 s) -> T <= 50 C ;  GOV (120 s) -> T <= 50 C
#   DIST (200 s) -> T <= 50 C  (DECISIÓN USUARIO 2026-09-23: DIST queda como
#      DIAGNOSTIC / NOT FOR VERDICT tras la auditoría del presupuesto térmico
#      (t90 real ~169 s desde ~35 C < 200 s). La entrada estricta <=35 C servía
#      solo para sanear R7; sin R7 a evaluar, se mantiene la entrada estándar
#      50 C para garantizar datos térmicos sin anti-deadlock inalcanzable.)
#   condición DN-07: temp1_input <= umbral sostenido >=30 s ∧ SCLK activo = nivel 0
#                     ∧ power1_input < 4 W  (muestras consecutivas de 5 s).
# Registro por trial: $SESS/fase2/cool<idx>.tsv (label, mono ns, dur, ret_temp,
# ret_sclk_nivel, ret_power_uW) — formato idéntico a fase1/cooldown*.tsv de v2.2.
#
# Anti-deadlock: tope 3600 s por cooldown. Si un trial NO alcanza su umbral en el
# tope -> NO se inicia el trial, se registra la omisión en fase2/omissions.json y
# se documenta; el resto de trials continúa. Tras la sesión, si hubo omisiones NO
# se llama a analyze.py phase2 automáticamente (faltaría m0): se reporta y se
# espera decisión. En esta ejecución (opción 3 del usuario) NO debe haber
# omisiones con umbral único <=50 C.
#
# Abort de seguridad: monitor read-only vigilando temp1_input >= 96 C durante cada
# trial -> SIGTERM al harness, evento en fase2/<cond><idx>.thermal_abort.
#
# TODO lo demás (workload, T/s* re-derivados de la Fase 1 de esta sesión y
# verificados contra el FREEZE, escalas, thresholds, R1-R7, F1-F6, órdenes,
# duraciones, lógica temporal DIST +60/+120, criterios de parada A-D, análisis)
# = PROTOCOLO v2.1 SIN CAMBIOS.
#
# READ-ONLY absoluto: nunca escribe sysfs/kernel/Mesa/contadores. Única escritura
# fuera de results/: control_scale.txt dentro de cada trial (como v2.2).
#
# Uso: run_all_v23.sh <1|2>
set -u

S="${1:-1}"
case "$S" in 1|2) ;; *) echo "uso: run_all_v23.sh <1|2>"; exit 2 ;; esac

BASE="$(cd "$(dirname "$0")" && pwd)"
BUILD="$BASE/harness/build"
BIN="$BUILD/governor_harness"
TEL="$BASE/telemetry/telemetria.sh"
GOV="$BASE/controller/governor.py"
ANALYZE="$BASE/harness/scripts/analyze.py"
R="$BASE/results"
VDIR="$R/v23"
SESS="$VDIR/session$S"
ICD="/usr/share/vulkan/icd.d/radeon_icd.x86_64.json"
DEV=/sys/class/drm/card1/device
HWMON=$DEV/hwmon/hwmon2

mkdir -p "$SESS/fase1/blocks" "$SESS/fase2" "$R/logs"

# --- snapshot sysfs READ-ONLY (no se escribe nada en el sistema) ---
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

log() { echo "[run_all_v23] $*" | tee -a "$R/logs/session${S}-v23.log"; }

# --- build del harness (no toca el workload ni las fuentes; no-op si sin cambios) ---
cmake -S "$BASE/harness" -B "$BUILD" -G Ninja >/dev/null 2>&1 \
  && ninja -C "$BUILD" >/dev/null 2>&1 \
  || { log "BUILD FAILED"; exit 1; }
log "build ok"

snapshot "$SESS/pre_flight.txt"
log "pre_flight ok"

OMISSIONS="$SESS/fase2/omissions.json"
[ -f "$OMISSIONS" ] && mv "$OMISSIONS" "$OMISSIONS.bak"
echo "[]" > "$OMISSIONS"
record_omission() { # $1=cond $2=idx $3=motivo
  python3 - "$OMISSIONS" "$1" "$2" "$3" <<'PY'
import json, sys
path, cond, idx, why = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
d = json.load(open(path))
d.append({"cond": cond, "idx": idx, "motivo": why,
          "ts_iso": __import__("datetime").datetime.now().isoformat()})
json.dump(d, open(path, "w"), indent=1)
PY
}
HAVE_OMISSION=0

# --- cooldown Fase 1 (v2.2, 50 C) entre passes p1->p2 / p2->p3 ---
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
    if [ "$ok" -ge 6 ]; then break; fi
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
for sc in 1.00 0.87 0.75 0.62 0.50; do run_block p1 "$sc" "s${sc/./}"; done
cooldown_pass "p1->p2" 1
for sc in 0.50 0.62 0.75 0.87 1.00; do run_block p2 "$sc" "s${sc/./}"; done
cooldown_pass "p2->p3" 2
for sc in 1.00 0.87 0.75 0.62 0.50; do run_block p3 "$sc" "s${sc/./}"; done
log "Fase 1 completa (con cooldowns v2.2)"

# --- FREEZE(T, s*) + GATEs (parada D si fallan) — SOLO con estos datos ---
if ! python3 "$ANALYZE" phase1 --session-dir "$SESS" >"$R/logs/session${S}-v23.phase1.log" 2>&1; then
  log "PARADA D en Fase 1 (gates/reachability) — ver $R/logs/session${S}-v23.phase1.log"
  exit 9
fi
T=$(python3 -c "import json;print(json.load(open('$SESS/fase1/manifest.json'))['T_ms'])")
SSTAR=$(python3 -c "import json;print(json.load(open('$SESS/fase1/manifest.json'))['s_star'])")
SHA=$(python3 -c "import json;print(json.load(open('$SESS/fase1/manifest.json'))['sha256'][:16])")
log "FREEZE(v2.3) T=${T} ms s*=${SSTAR} sha256=${SHA}…"
echo "$SHA" > "$SESS/fase1/frozen.sha256"
# verificación vs FREEZE congelado de S1-v2.2 (6b6d6952…) y vs la otra sesión si existe
FROZEN="6b6d69522e604529"
if [ "$SHA" = "$FROZEN" ]; then
  log "FREEZE coincide con registro congelado S1-v2.2 ($FROZEN)"
else
  log "ALERTA: T/s* ($T/$SSTAR, sha $SHA) difieren del registro congelado ($FROZEN) — revisar antes de Phase 2"
fi

# --- COOLDOWN POR TRIAL (v2.3) — antes de CADA trial de Phase 2 ---
# $1=cond $2=idx_global(1..8) $3=umbral_mC
cooldown_trial() {
  local cond="$1" idx="$2" umbral="$3"
  local out="$SESS/fase2/cool${idx}.tsv"
  local label="p2 trial#${idx} ${cond}"
  log "COOLDOWN ${label} INICIO (esperando temp<=$((umbral/1000))C ∧ SCLK nv0 ∧ P<4W)"
  local t0=$(date +%s%N)
  local ok=0 T=0 L=9 P=999999999 elap=0
  while :; do
    sleep 5
    T=$(cat $HWMON/temp1_input 2>/dev/null || echo 0)
    L=$(grep -a '\*' $DEV/pp_dpm_sclk 2>/dev/null | head -1 | awk -F'[: *]+' '{print $1}')
    P=$(cat $HWMON/power1_input 2>/dev/null || echo 0)
    if [ "$T" -le "$umbral" ] && [ "${L:-9}" = "0" ] && [ "$P" -lt 4000000 ]; then
      ok=$((ok+1))
    else
      ok=0
    fi
    if [ "$ok" -ge 6 ]; then break; fi
    elap=$(( ($(date +%s) - t0/1000000000 ) ))
    if [ "$elap" -ge 3600 ]; then
      log "COOLDOWN ${label} TIMEOUT 3600s sin retorno (T=${T} sclk=${L} P=${P}uW) — trial #${idx} ${cond} NO se inicia (omisión térmica)"
      { echo "label=$label"; echo "inicio_mono_ns=$t0"; echo "fin_mono_ns=$(date +%s%N)";
        echo "dur_ms=3600000"; echo "dur_s=3600"; echo "ret_temp_mC=$T";
        echo "ret_sclk_nivel=$L"; echo "ret_power_uW=$P"; echo "status=ENTRY_TIMEOUT"; } > "$out"
      record_omission "$cond" "$idx" "ENTRY_TIMEOUT_3600s (T=${T}mC sclk=${L})"
      HAVE_OMISSION=1
      return 1
    fi
  done
  local tf=$(date +%s%N)
  local dur_ms=$(( (tf - t0) / 1000000 ))
  local dur_s=$(( dur_ms / 1000 ))
  { echo "label=$label"; echo "inicio_mono_ns=$t0"; echo "fin_mono_ns=$tf";
    echo "dur_ms=$dur_ms"; echo "dur_s=$dur_s"; echo "ret_temp_mC=$T";
    echo "ret_sclk_nivel=$L"; echo "ret_power_uW=$P"; echo "status=OK"; } > "$out"
  log "COOLDOWN ${label} FIN en ${dur_s}s (T=${T} sclk_nivel=$L P=${P}uW) -> $out"
  return 0
}

# --- MONITOR read-only de progreso (temp, SCLK) mientras corre un trial ---
# no escribe sysfs; solo informa a stdout/log del script
monitor_trial() { # $1=trial  $2=pid a vigilar (0=no)
  local tag="$1" hp="$2" T L M
  while :; do
    T=$(cat $HWMON/temp1_input 2>/dev/null || echo NA)
    L=$(grep -a '\*' $DEV/pp_dpm_sclk 2>/dev/null | head -1 | awk -F'[: *]+' '{print $1}')
    M=$(grep -a '\*' $DEV/pp_dpm_sclk 2>/dev/null | head -1 | awk -F'[: *]+' '{print $2}')
    log "MON trial $tag temp=${T}mC sclk=${L}(${M}MHz)"
    if [ "$hp" = "0" ] || ! kill -0 "$hp" 2>/dev/null; then break; fi
    sleep 10
  done
}

# --- ABORT de seguridad: vigila temp >= 96 C durante el trial y hace SIGTERM ---
abort_watch() { # $1=trial tag  $2=pid harness
  local tag="$1" hp="$2" T
  while kill -0 "$hp" 2>/dev/null; do
    T=$(cat $HWMON/temp1_input 2>/dev/null || echo 0)
    if [ "${T:-0}" -ge 96000 ]; then
      log "ABORT TÉRMICO trial $tag: T=${T}mC >= 96C — SIGTERM harness"
      kill -TERM "$hp" 2>/dev/null
      { echo "event=THERMAL_ABORT"; echo "temp_at_abort_mC=$T";
        echo "ts_ns=$(date +%s%N)"; } > "$SESS/fase2/${tag}.thermal_abort"
      return 0
    fi
    sleep 1
  done
}

# --- PHASE 2: trials alternados con cooldown previo (v2.3) ---
run_trial() {
  local cond="$1" idx="$2" umbral="$3"
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
      >"$R/logs/trial_${cond}${idx}.log" 2>&1 &
    local hp=$!
    monitor_trial "$cond$idx" "$hp" &
    abort_watch "$cond$idx" "$hp" &
    wait "$hp"
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
    monitor_trial "$cond$idx" "$hp" &
    abort_watch "$cond$idx" "$hp" &
    python3 "$GOV" --frames "$trial/run_frames.tsv" \
      --control "$trial/control_scale.txt" --t0-us "$t0" \
      --T-ms "$T" --duration "$dur" --trace "$trial/governor_trace.tsv" \
      >>"$R/logs/governor_${cond}${idx}.log" 2>&1
    wait "$hp"
  fi
  wait "$tp"
  # verificar que no hubo abort térmico
  if [ -f "$SESS/fase2/${cond}${idx}.thermal_abort" ]; then
    log "trial ${cond}${idx} ABORTADO POR TÉRMICA (ver .thermal_abort)"
  else
    log "trial ${cond}${idx} ok"
  fi
}

case "$S" in
  1) ORDER="fixed gov fixed gov fixed gov dist dist" ;;
  2) ORDER="gov fixed gov fixed gov fixed dist dist" ;;
esac
python3 -c "import json; json.dump('$ORDER'.split(), open('$SESS/fase2/order.json','w'), indent=1)"
cnt_f=0; cnt_g=0; cnt_d=0; gidx=0
for c in $ORDER; do
  gidx=$((gidx+1))
  case "$c" in
    fixed) umb=50000; cnt_f=$((cnt_f+1)); tidx="$cnt_f" ;;
    gov)   umb=50000; cnt_g=$((cnt_g+1)); tidx="$cnt_g" ;;
    dist)  umb=50000; cnt_d=$((cnt_d+1)); tidx="$cnt_d" ;;
  esac
  # cooldown v2.3 SIEMPRE antes del trial (incl. el 1º tras FREEZE)
  if ! cooldown_trial "$c" "$gidx" "$umb" ; then
    log "trial ${c}${tidx} OMITIDO (entrada térmica no alcanzada) — continúa siguiente"
    continue
  fi
  run_trial "$c" "$tidx" "$umb"
done

snapshot "$SESS/post_flight.txt"
log "post_flight ok"

# verificación read-only: DPM/kalm deben coincidir pre/post
PRE=$(grep '\*' "$SESS/pre_flight.txt" | md5sum | cut -d' ' -f1)
POST=$(grep '\*' "$SESS/post_flight.txt" | md5sum | cut -d' ' -f1)
if [ "$PRE" != "$POST" ]; then
  log "ALERTA VERIFICACIÓN READ-ONLY: DPM/kalm cambiaron pre→post (¿escritura?)"
else
  log "verify read-only: DPM/kalm idénticos pre/post ($PRE)"
fi

if [ "$HAVE_OMISSION" = 1 ]; then
  log "Sesión terminó con OMISIONES térmicas (ver fase2/omissions.json). NO se llama a analyze.py phase2 automáticamente: faltan m0 de trial(es) omitido(s) -> reportar y esperar decisión."
else
  python3 "$ANALYZE" phase2 --session-dir "$SESS" --order "$(echo $ORDER | tr ' ' ',')" \
    >>"$R/logs/session${S}-v23.phase2.log" 2>&1
  log "sesión ${S}-v23 completada (+ phase2)"
fi
exit 0
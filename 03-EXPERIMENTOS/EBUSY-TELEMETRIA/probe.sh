#!/usr/bin/env bash
# probe.sh -- AGENT-29. Mide si la TELEMETRIA MMIO de la RX550 es legible
# segun el estado de energia del dispositivo bajo runtime PM.
#
# PRECONDICION (solo lectura): no escribe ningun registro, no cambia DPM, no
# fuerza relojes. Unica accion con efecto: abrir un cliente Vulkan, que dispara
# un resume del runtime PM (reversible, y el autosuspend vuelve solo a los 5 s).
#
# LECTURA: delega en readattr.py porque `cat` no propaga errno y no puede
# distinguir EBUSY de EACCES (ver readattr.py).
#
# SALIDA: TSV, una fila POR MUESTRA, columnas estables.
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
DEV="${DEV:-/sys/class/drm/card1/device}"
# shellcheck disable=SC2086
HWMON="$(echo "$DEV"/hwmon/hwmon*)"
SAMPLES="${SAMPLES:-6}"
INTERVAL="${INTERVAL:-1}"

ra() { python3 "$HERE/readattr.py" "$1"; }

emit() {
  local out="$1"
  local -a cols=()
  cols+=("$out" "$(date -Is)")
  for p in "$DEV/power/runtime_status" "$DEV/power_state" \
           "$DEV/gpu_busy_percent" "$DEV/mem_busy_percent" \
           "$HWMON/power1_input" "$DEV/pp_dpm_sclk"; do
    cols+=("$(ra "$p" | tr '\n' ' ')")
  done
  (IFS=$'\t'; echo "${cols[*]}")
}

# Precondicion verificada, no supuesta: el experimento solo es valido si la
# fase A arranca realmente en runtime-suspend. Con autosuspend=5000 ms basta
# con esperar a que el kernel re-suspenda al dispositivo.
await_suspended() {
  local i
  for i in $(seq 60); do
    if [ "$(cat "$DEV/power/runtime_status" 2>/dev/null)" = "suspended" ]; then
      echo "precondicion OK: runtime_status=suspended tras ~${i}s"
      return 0
    fi
    sleep 1
  done
  echo "PRECONDICION FALLIDA: no entra en suspend; la fase A seria invalida" >&2
  return 1
}

hdr() {
  printf 'fase\tts\truntime_status\tpower_state\tgpu_busy\tmem_busy\tpower1_uW\tpp_dpm_sclk\n'
}

hdr
echo "--- fase A: reposo (runtime autosuspend) ---"
await_suspended || exit 3
for _ in $(seq "$SAMPLES"); do emit A; sleep "$INTERVAL"; done

echo "--- fase B: cliente Vulkan abre el dispositivo (resume por runtime PM) ---"
timeout 40 vulkaninfo >/dev/null 2>&1 &
VP=$!
sleep 2
for _ in $(seq 3); do emit B; sleep "$INTERVAL"; done
wait "$VP" 2>/dev/null

echo "--- fase C: tras la salida del cliente ---"
for _ in $(seq 3); do emit C; sleep "$INTERVAL"; done
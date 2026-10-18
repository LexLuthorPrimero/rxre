#!/bin/bash
# alupow.sh — potencia frente a trabajo de ALU.
#
# QUE PREGUNTA
#   La frontera de memoria esta cerrada (1504): 40.2 GB/s, 83.7 % de lo nominal, y ni la
#   instrumentacion ni el patron de acceso la levantan.  Lo que queda por encima de la linea
#   de rendimiento es el COSTE POR OPERACION de la ALU: el 1494 midio 17.9 W para 12.89 GB/s
#   con un modo saturado de FMA.  La pregunta es como escala esa potencia con el trabajo real
#   de ALU, y si satura antes de llegar a ese punto.
#
#   Prediccion con criterio de refutacion: si la potencia se satura con POCO trabajo de ALU,
#   entonces los 17.9 W los domina algo que no es la tasa de emision de la ALU -- fugas a
#   881 mV, o el subsistema de memoria -- y el frente util no es "optimizar la ALU" sino el
#   voltaje.  Si escala de forma aproximada con el trabajo, entonces la ALU si es el coste.
#
# POR QUE ESTA EN EL ARBOL Y NO EN /tmp
#   Dos reinicios del servidor tiraron los datos de dos barridos porque el script vivia en
#   /tmp/opencode, que no es persistente.  Este script escribe cada fila segun la mide, de
#   modo que un reinicio conserve lo ya avanzado.
#
# ALCANCE
#   Solo lectura de sysfs/debugfs y carga de compute sobre 0000:01:00.0.  CERO escrituras de
#   registro.  No toca 0000:00:02.0.  Requiere card1 en power/control=on; el estado de reposo
#   es el de la sesion cuando no se mide nada.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
GEN="$HERE/rx550_gl_load.bin"
D=/sys/class/drm/card1/device
P=/sys/kernel/debug/dri/1/amdgpu_pm_info
S='123456'
OUT="$HERE/alupow-2026-10-05.tsv"
LOGS="$HERE/alupow-logs"

[ -x "$GEN" ] || { echo "FALLO: no existe $GEN.  Ejecuta ./build.sh primero."; exit 2; }
mkdir -p "$LOGS"
if [ "${1:-}" = "--reset" ] || [ ! -s "$OUT" ]; then
    printf 'iters\tgbs\telapsed_s\titers_count\tsclk\tmclk\tgpu_pct\tmem_pct\tvddgfx_mV\tsoC_W\ttempC\tGFLOPs\tW_por_GFLOP\n' > "$OUT"
fi

# Instantanea de la instrumentacion.  Se toma DURANTE la carga y nunca despues: si se toma
# al final, la GPU ya ha vuelto a reposo y se mide la caida, no el estado estacionario.  Con la
# lectura al final, gpu_pct y mem_pct salian a 0 y la potencia era una lectura de cola.
snapshot() {
    local pm=$(echo "$S" | sudo -S -p '' cat "$P" 2>/dev/null)
    printf '%s|%s|%s|%s|%s|%s|%s\n' \
      "$(grep -oP '\d+(?= mV \(VDDGFX\))' <<<"$pm")" \
      "$(grep -oP '[\d.]+(?= W \(current)' <<<"$pm")" \
      "$(grep -oP '\d+(?= C$)' <<<"$pm" | head -1)" \
      "$(cat "$D/mem_busy_percent" 2>/dev/null)" \
      "$(grep '\*\$' "$D/pp_dpm_sclk" 2>/dev/null | sed 's/.*: *\([0-9]*\)Mhz.*/\1/')" \
      "$(grep '\*\$' "$D/pp_dpm_mclk" 2>/dev/null | sed 's/.*: *\([0-9]*\)Mhz.*/\1/')" \
      "$(cat "$D/gpu_busy_percent" 2>/dev/null)"
}

row() {   # iters gbs elapsed n snapshot
    local IT=$1 G=$2 EL=$3 NC=$4 SNAP=$5
    local V W TC MB SL ML GB
    IFS='|' read -r V W TC MB SL ML GB <<< "$SNAP"
    V=$(grep -oP '\d+(?= mV \(VDDGFX\))' <<<"$pm")
    W=$(grep -oP '[\d.]+(?= W \(current)' <<<"$pm")
    TC=$(grep -oP '\d+(?= C$)' <<<"$pm" | head -1)
    MB=$(cat "$D/mem_busy_percent" 2>/dev/null)
    SL=$(grep '\*$' "$D/pp_dpm_sclk" 2>/dev/null | sed 's/.*: *\([0-9]*\)Mhz.*/\1/')
    ML=$(grep '\*$' "$D/pp_dpm_mclk" 2>/dev/null | sed 's/.*: *\([0-9]*\)Mhz.*/\1/')
    GB=$(cat "$D/gpu_busy_percent" 2>/dev/null)
    local F=$(python3 -c "
it=$IT; el=$EL; nc=$NC
if el <= 0: print('-'); raise SystemExit
elems = 256*1024*1024/4
# modo math: por elemento, iters FMA de 2 flop, una lectura y una escritura
print('%.2f' % (2.0*elems*it*nc/el/1e9))" 2>/dev/null)
    local WP=$(python3 -c "
try:
    g=float('$F'); w=float('$W')
    print('%.3f'%(w/g) if g>0 else '-')
except Exception: print('-')")
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
        "$IT" "$G" "$EL" "$NC" "$SL" "$ML" "$GB" "$MB" "$V" "$W" "$TC" "$F" "$WP" >> "$OUT"
    printf '%5s %9s %5s %6s %6s %6s %8s %7s %7s %9s %10s\n' \
        "$IT" "$G" "$SL" "$ML" "$GB" "$MB" "$V" "$W" "$TC" "$F" "$WP"
}

echo "=== POTENCIA FRENTE A TRABAJO DE ALU (modo math, 256 MiB, 6 s por punto) ==="
printf '%5s %9s %5s %6s %6s %6s %8s %7s %7s %9s %10s\n' iters GB/s sclk mclk gpu% mem% vdd W temp GFLOPS W/GFLOP
echo "  (cada fila se anexa a $(basename "$OUT") segun se mide)"
for IT in 1 2 4 8 16 32 64 128 256; do
    if awk -F'\t' -v i="$IT" '$1==i{found=1} END{exit !found}' "$OUT"; then
        echo "  iters=$IT ya medido en una ejecucion anterior; se salta"
        continue
    fi
    MESA_LOADER_DRIVER_OVERRIDE=radeonsi "$GEN" --seconds 6 --buffer 256 \
        --mode math --iters "$IT" --sync-every 32 > "$LOGS/alupow-$IT.log" 2>&1 &
    L=$!
    sleep 3.0
    SNAP=$(snapshot)
    sleep 3.2
    wait $L 2>/dev/null
    G=$(grep -oE 'media[ ]+[0-9.]+[ ]+GB/s' "$LOGS/alupow-$IT.log" | tail -1 | grep -oE '[0-9.]+')
    EL=$(grep -oE 'FINALIZADO[ ]+modo[ ]+math[ ]+[0-9.]+' "$LOGS/alupow-$IT.log" | tail -1 | grep -oE '[0-9.]+$')
    NC=$(grep -oE '[0-9]+[ ]+iteraciones' "$LOGS/alupow-$IT.log" | tail -1 | grep -oE '^[0-9]+')
    if [ -z "${G:-}" ] || [ -z "${EL:-}" ] || [ -z "${NC:-}" ]; then
        echo "  iters=$IT  NO SE PUDO MEDIR (log incompleto; se registra como NO MEDIDO)"
        printf '%s\tNO_MEDIDO\n' "$IT" >> "$OUT"
        continue
    fi
    row "$IT" "$G" "$EL" "$NC" "$SNAP"
done
echo
echo "=== resultado acumulado en $(basename "$OUT") ==="
column -t "$OUT" 2>/dev/null || cat "$OUT"
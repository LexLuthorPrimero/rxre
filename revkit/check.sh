#!/usr/bin/env bash
# check.sh -- ejecuta TODAS las validaciones y dice que falla.
#
# POR QUE UN SCRIPT Y NO EJECUTARLAS A MANO
# ------------------------------------------
# El protocolo exige que cada afirmacion se compruebe antes de publicarse. Con
# siete herramientas, ejecutarlas a mano significa olvidar una, y una
# validacion que se olvida no es una validacion.
#
# Salida: 0 si TODO pasa. El primer fallo para el script, pero sigue ejecutando
# el resto para que un fallo no oculte los demas.
#
# Uso:
#   ./check.sh          -- todo
#   ./check.sh rapido   -- solo lo que no reindexa
set -u
cd "$(dirname "$0")"

RAPIDO="${1:-todo}"
fallos=0
declare -a RESULTADOS=()

run() {
    local nombre="$1"; shift
    local salida rc
    salida=$("$@" 2>&1)
    rc=$?
    if [ "$rc" -eq 0 ]; then
        RESULTADOS+=("OK    $nombre")
        printf '  %-46s OK\n' "$nombre"
    else
        fallos=$((fallos+1))
        RESULTADOS+=("FALLO $nombre (rc=$rc)")
        printf '  %-46s FALLO rc=%d\n' "$nombre" "$rc"
        printf '%s\n' "$salida" | head -20 | sed 's/^/       /'
    fi
}

echo "=== revkit: validaciones ==="
echo "modo: $RAPIDO"
echo

# --- integridad de los propios scripts -------------------------------
echo "--- sintaxis de las herramientas ---"
for f in *.py; do
    if python3 -c "import ast,sys; ast.parse(open('$f').read())" 2>/dev/null; then
        printf '  %-46s OK\n' "$f"
    else
        fallos=$((fallos+1))
        printf '  %-46s FALLO (sintaxis)\n' "$f"
    fi
done
echo

if [ "$RAPIDO" != "rapido" ]; then
    echo "--- indices (reindexa la primera vez) ---"
    run "cidx: indice del corpus"      ./cidx.py stats
    run "regs: decodificador"          ./regs.py --find "gfx_8_0"
    echo
fi

echo "--- observacion del host ---"
run "obs: la GPU objetivo existe"    ./obs.py gpu
run "obs: parametros de modulo"      ./obs.py params
echo

echo "--- documentos ---"
run "vclaims: citas de 08-ARQ"       ./vclaims.py
echo

echo "--- autocomprobacion del kit ---"
# La etiqueta NO lleva un numero fijo: si anadir un control y no
# actualizar el texto, el runner anuncia una cantidad que ya no es la real,
# y eso es exactamente el fallo que estas herramientas persiguen.
run "selfcheck: controles del kit"   python3 selfcheck.py
echo

echo "--- btfq (kit anterior, revalidado) ---"
BTFQ=../08-ARQUITECTURA/tools/btfq
if [ -d "$BTFQ" ]; then
    run "btfq: census"       python3 "$BTFQ/btfq.py" census
    run "btfq: crosscheck"   python3 "$BTFQ/crosscheck.py" amdgpu_gmc amdgpu_gmc.h
    run "vmsize: geometria"  python3 "$BTFQ/vmsize.py"
    run "cn4: controles BTF" python3 "$BTFQ/cn4.py"
    run "cn5: controles contraste" python3 "$BTFQ/cn5.py"
    run "cn6: integridad docs"     python3 "$BTFQ/cn6.py"
fi
echo

echo "=== resultado ==="
for r in "${RESULTADOS[@]}"; do echo "  $r"; done
echo
if [ "$fallos" -eq 0 ]; then
    echo "TODO CORRECTO"
    exit 0
fi
echo "$fallos validacion(es) fallida(s)"
exit 1
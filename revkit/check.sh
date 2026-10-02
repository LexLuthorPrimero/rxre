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

echo "--- trazado de codigo ---"
run "ibtrace: secuencia de vm_flush" ./ibtrace.py func gfx_v8_0.c::gfx_v8_0_ring_emit_vm_flush
run "causa: mapa de invalidate"      ./causa.py mapa mmVM_INVALIDATE_REQUEST
run "causa: descubre registros"      ./causa.py descubrir gfx_v8_0
echo

echo "--- documentos ---"
run "vclaims: citas de 08-ARQ"       ./vclaims.py
run "estado: contradicciones"        ./estado.py contradicciones
echo

echo "--- diferencial entre versiones ---"
run "verdiff: vm_flush en 7.1.3 vs 7.2.8" ./verdiff.py fn gfx_v8_0.c gfx_v8_0_ring_emit_vm_flush
run "verdiff: flush_tlb en ambas"         ./verdiff.py fn gmc_v8_0.c gmc_v8_0_emit_flush_gpu_tlb
echo

echo "--- autocomprobacion del kit ---"
# La etiqueta NO lleva un numero fijo: si anadir un control y no
# actualizar el texto, el runner anuncia una cantidad que ya no es la real,
# y eso es exactamente el fallo que estas herramientas persiguen.
run "selfcheck: controles del kit"   python3 selfcheck.py
run "correlate: tabla hallazgo/herramienta" ./correlate.py
echo

echo "--- descubrimiento de trabajo ---"
# scan es un INFORME, no una validacion: devuelve 0 aunque no encuentre
# nada, porque "no hay trabajo pendiente" es un resultado valido. Solo se
# marca como fallo si el script se rompe.
if ./scan.py > /tmp/scan.out 2>&1; then
    RESULTADOS+=("OK    scan: informe de trabajo pendiente")
    printf '  %-46s OK\n' "scan: informe de trabajo pendiente"
else
    RESULTADOS+=("FALLO scan: informe de trabajo pendiente")
    printf '  %-46s FALLO\n' "scan: informe de trabajo pendiente"
    head -10 /tmp/scan.out | sed 's/^/       /'
    fallos=$((fallos+1))
fi
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

# --- herramientas de observacion y de VBIOS -------------------------------
#
# Se anaden con fecha 2026-10-02, tras ganar acceso root al debugfs.
#
# autotest de integro: tiene que poder detectar su propia mutacion, y se
# comprueba con mutaciones reales fuera de este script (ver el historial).
# Si algun dia el detector se rompe, este control falla y no se puede usar
# la herramienta como autoridad.
echo "--- integridad, VBIOS y direcciones (nuevas) ---"
# dirs lleva autocomprobacion dentro: busca 0x1537/0x1538, que se sabe que
# son mmGPU_HDP_FLUSH_REQ/DONE de BIF 4.1. Si no los encuentra sale rc=3. El
# control existe porque un filtro mal escrito devuelve una lista vacia, y una
# lista vacia parece un resultado legitimo.
run "dires: indice de direcciones (autocomprobado)" python3 dires.py 0x1537 --bloque bif
run "integro: autotest (detector de corrupcion)"  python3 integro.py autotest
# cn7 depende de sid.h, que vive en el corpus del kernel, no en revkit. En un
# clon sin corpus devuelve 2 (OMITIDO), que NO es lo mismo que fallar. Se
# distingue aqui para que una dependencia ausente no se reporte como una
# herramienta rota: confundiendolas es como un 0 que parece un 1.
cn7_out=$(python3 cn7.py 2>&1); cn7_rc=$?
if [ "$cn7_rc" -eq 0 ]; then
    RESULTADOS+=("OK    cn7: controles de pm4dec")
    printf '  %-46s OK\n' "cn7: controles de pm4dec"
elif [ "$cn7_rc" -eq 2 ]; then
    RESULTADOS+=("OMIT  cn7: controles de pm4dec (sin corpus)")
    printf '  %-46s OMITIDO (falta sid.h)\n' "cn7: controles de pm4dec"
    echo "$cn7_out" | head -1 | sed 's/^/       /'
else
    fallos=$((fallos+1))
    RESULTADOS+=("FALLO cn7: controles de pm4dec (rc=$cn7_rc)")
    printf '  %-46s FALLO rc=%d\n' "cn7: controles de pm4dec" "$cn7_rc"
    echo "$cn7_out" | head -20 | sed 's/^/       /'
fi
# cn8 tiene casos NEGATIVOS: un mutante de la unidad de clocks y un VBIOS
# sintetico con otra VRAM tienen que hacer fallar el contraste. Un control
# que solo dice "cuando todo va bien, OK" no comprueba nada.
cn8_out=$(python3 cn8.py 2>&1); cn8_rc=$?
if [ "$cn8_rc" -eq 0 ]; then
    RESULTADOS+=("OK    cn8: controles de atomrom")
    printf '  %-46s OK\n' "cn8: controles de atomrom"
elif [ "$cn8_rc" -eq 2 ]; then
    RESULTADOS+=("OMIT  cn8: controles de atomrom (sin VBIOS)")
    printf '  %-46s OMITIDO (falta el VBIOS)\n' "cn8: controles de atomrom"
    echo "$cn8_out" | head -1 | sed 's/^/       /'
else
    fallos=$((fallos+1))
    RESULTADOS+=("FALLO cn8: controles de atomrom (rc=$cn8_rc)")
    printf '  %-46s FALLO rc=%d\n' "cn8: controles de atomrom" "$cn8_rc"
    echo "$cn8_out" | head -20 | sed 's/^/       /'
fi
# atomrom se valida con un ROM SINTETICO, no con el VBIOS real. El VBIOS es
# firmware con derechos y no esta versionado, asi que una validacion que
# dependiera de el fallaria en un clon limpio. El autotest ademas comprueba
# que el validador RECHAZA las corrupciones, que con el fichero real no se
# puede hacer.
run "atomrom: autotest (ROM sintetico)"          python3 atomrom.py autotest
# Y luego, si el VBIOS esta disponible en esta maquina, se valida el de verdad.
if [ -f capturas/amdgpu_vbios.txt ]; then
    run "atomrom: validar el VBIOS real"            python3 atomrom.py rom capturas/amdgpu_vbios.txt
    run "atomrom: inventariar tablas"              python3 atomrom.py tablas capturas/amdgpu_vbios.txt
    # firmware contrasta los clocks del VBIOS con las frecuencias que la GPU
    # tiene ahora. Sale con rc=5 si la unidad no cuadra y rc=4 si no puede
    # contrastar: en ambos casos los valores se imprimen pero NO se dan por
    # buenos. Un error de unidades no da error, da un numero con decimales.
    run "atomrom: firmware info + contraste unidad" python3 atomrom.py firmware capturas/amdgpu_vbios.txt
    # vram: usMemorySize del VBIOS tiene que coincidir con la VRAM que el
    # kernel ve en amdgpu_vram_mm. Si no coinciden, el VBIOS describiria otra
    # tarjeta, y eso habria que saberlo antes de usar nada de lo suyo.
    run "atomrom: VRAM_Info + parte number"        python3 atomrom.py vram capturas/amdgpu_vbios.txt
    # pm4dec sobre el anillo real: el decode tiene que salir limpio, sin
    # problemas de truncamiento. Con el PKT0 mal tratado, esto no cuadraba.
    run "pm4dec: anillo GFX real"                   python3 pm4dec.py capturas/amdgpu_ring_gfx.txt
    # direcciones: extrae las GPU VA de los INDIRECT_BUFFER y las contrasta
    # contra la VRAM real. Si el layout estuviera mal, caerian fuera y daria
    # rc=5, asi que el contraste discrimina de verdad.
    run "pm4dec: direcciones de GPU vs VRAM"        python3 pm4dec.py capturas/amdgpu_ring_gfx.txt --direcciones
    # escribe: los WRITE_DATA del anillo. dst_sel=0 significa REGISTRO, no
    # memoria, y la direccion se resuelve contra el bloque del ASIC correcto.
    run "pm4dec: WRITE_DATA (a que escribe)"         python3 pm4dec.py capturas/amdgpu_ring_gfx.txt --escribe
    # ibpools: analiza amdgpu_sa_info, que son los buffers de IB del driver
    # con direcciones FISICAS del sistema. Lleva autocomprobacion dentro:
    # avisa si no interpreta todas las lineas, si hay mas de un IB en uso por
    # pool, o si un rango no cuadra con su size. rc=1 si algo falla.
    run "ibpools: pools de IB del driver"            python3 ibpools.py
    # huerfanos mide la COBERTURA del corpus: cuantos simbolos usa el driver
    # sin definicion local. Sale con rc=1 a proposito, porque un corpus
    # incompleto es un dato, no un error de la herramienta, y check.sh lo
    # trata como FALLO para que se vea en el resumen. El valor 1 esta
    # documentado en la propia salida.
    huerf_out=$(python3 huerfanos.py 2>&1); huerf_rc=$?
    printf '  %-46s %s\n' "huerfanos: cobertura del corpus" \
        "rc=$huerf_rc (1 = corpus incompleto, es lo esperado)"
    echo "$huerf_out" | grep -E "^SIN DEFINICION" | sed 's/^/       /'
    # sello: verifica docs/EVIDENCE-MANIFEST.sha256. rc=0 OK, 1 movido,
    # 2 roto. Un movido NO hace fallar check.sh, porque editar evidencia es
    # legitimo; lo que no es legitimo es que no quede dicho. Se imprime y ya.
    sello_out=$(python3 sello.py 2>&1); sello_rc=$?
    printf '  %-46s %s\n' "sello: integridad de la evidencia" \
        "rc=$sello_rc (0 OK, 1 movido, 2 roto)"
    echo "$sello_out" | grep -E "^  (OK|MOVIDO|ROTO) " | sed 's/^/       /'
    # custodia: el sello DETECTA la corrupcion, el commit RECUPERA la perdida.
    # rc=1 significa que hay evidencia sellada SIN version: se detecta si se
    # rompe, pero no hay de donde volver. No hace fallar check.sh por ahora,
    # porque arreglarlo es decision de quien escribio esos ficheros, no del
    # kit. Se imprime para que deje de ser invisible.
    cust_out=$(python3 sello.py --custodia 2>&1); cust_rc=$?
    printf '  %-46s %s\n' "custodia: sellado vs commiteado" \
        "rc=$cust_rc (0 todo con version, 1 sellado SIN commit)"
    echo "$cust_out" | grep -E "^  (sellado|commiteado|ni sello|stageados)" \
        | sed 's/^/       /'
else
    echo "  atomrom: VBIOS real ausente (no versionado)     OMITIDO, el"
    echo "           autotest con ROM sintetico ya valida el"
    echo "           parser. Para el real: captura.py"
fi
echo

# el plan de captura debe ser coherente, pero su ejecucion pide sudo, asi que
# aqui SOLO se comprueba la coherencia, sin leer la GPU.
echo "--- coherencia del plan de captura (sin sudo) ---"
if python3 -c "import captura,sys; f=captura.check_captura(); sys.exit(1 if f else 0)" 2>/dev/null; then
    RESULTADOS+=("OK    captura: plan coherente")
    printf '  %-46s OK\n' "captura: plan coherente (sin sudo)"
else
    fallos=$((fallos+1))
    RESULTADOS+=("FALLO captura: plan incoherente")
    printf '  %-46s FALLO\n' "captura: plan incoherente"
    python3 -c "import captura; [print('       -',f) for f in captura.check_captura()]"
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
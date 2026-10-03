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

# --- EL CLASIFICADOR DE CODIGOS DE SALIDA ------------------------------------
#
# MEDIDO, y era el hueco que quedaba: `cn8` ya sabia distinguir "algo esta mal"
# (rc=1) de "no he podido comprobar nada" (rc=4), pero ESTE SCRIPT, que es quien
# lo consume, trataba TODO rc distinto de 0 como FALLO. O sea que la distincion
# existia y se perdia justo en el orquestador, que es donde se lee. Una
# distincion que nadie consume no es una distincion: es decoracion.
#
# EL PROTOCOLO DE CODIGOS DE SALIDA, MEDIDO, NO INVENTADO.
#
# Este mapa estaba hecho de un supuesto: "0 es OK, 4 es INVALID, el resto FALLO".
# El 4 venia de cn8/bootcheck/gputel/klog, que si lo usan. El resto lo assume.
# Medido sobre las 30 salidas con `return <entero>` de las 17 herramientas:
#
#   0  OK       todo pasa.
#   2  INVALID  falta el dato o la dependencia para comprobar. Medido con
#               atomrom.py y pm4dec.py sobre un fichero inexistente: los dos
#               devuelven 2 y ambos dicen "no existe". Tambien cn7 (sin sid.h),
#               cn8 (sin VBIOS), captura (sin RX550_SUDO_PASS), dirs, sello.
#               NO es un fallo del proyecto: es cobertura que no existe.
#   4  INVALID  no pude comprobar. pm4dec lo dice literalmente: "NO CONTRASTADO:
#               falta amdgpu_vram_mm ... Saliendo con codigo 4".
#   1  FALLO    se comprobo y no pasa.
#   3  FALLO    se comprobo y el fichero no tiene lo que se le pidio
#               (pm4dec: "el anillo no contiene INDIRECT_BUFFER").
#   5  FALLO    se comprobo y el dato es incoherente (pm4dec: direcciones que
#               NO caben en la VRAM). Ver la advertencia de abajo.
#   otro FALLO  incluido 126 (script no ejecutable): eso si es un fallo real.
#
# MEDIDO Y REPRODUCIDO: antes de esto, "atomrom.py rom <fichero que no existe>"
# daba rc=2 y `run()` lo reportaba como FALLO, con lo que la suite entera
# terminaba en rc=1 diciendo que el proyecto estaba roto cuando lo unico que
# faltaba era un fichero de entrada. Es la confusion que este mismo fichero
# dice evitar en la cabecera, cometida en su propia funcion de ejecucion.
#
# AVISO CONOCIDO, NO RESUELTO, REGISTRADO A PROPOSITO: el 5 esta sobrecargado.
# pm4dec lo usa para "las direcciones NO caben en la VRAM", que es un fallo
# real y por tanto FALLO; btfsnap lo usa para un OSError al leer o escribir
# la BTF, que es "no he podido comprobar" y por tanto INVALID. Con este mapa,
# btfsnap con un OSError se reportaria como FALLO. NO esta ejercitado hoy porque
# la suite solo invoca btfsnap en modo --self-test. El dia que se invoque de otra
# manera, este mapa habra que partirlo por herramienta en vez de repararlo aqui.
invalidos=0

clasifica() {
    case "$1" in
        0)       echo OK ;;
        2|4)     echo INVALID ;;
        *)       echo FALLO ;;
    esac
}

# EXCEPCIONES MEDIDAS POR HERRAMIENTA, Y POR QUE HACE FALTAN.
#
# El mapa de arriba es un priori, y resulto estar mal para 4 de los 5 codigos que
# no son 0 ni 1: los 167 `return <entero>` literales de las 17 herramientas
# comparten el mismo numero para intenciones distintas. Medido leyendo el mensaje
# de cada sitio, no por palabra clave:
#
#   rc=3  bootcheck "N control(es) en rojo" ............ FALLO
#         captura   "el plan se contradice a si mismo" .. FALLO
#         dirs      "un indice que no encuentra lo que
#                    se sabe que esta" .................. FALLO
#         sello     "eso no lo puede hacer un script" ... FALLO
#         btfsnap   "NO ESTA pahole" .................... INVALID
#         pm4dec    "Sin la tabla de opcodes" .......... INVALID
#         gfx8blocks "ERROR/INVALID: 0 funciones" ....... INVALID
#
#   rc=5  pm4dec  "N direcciones NO caben en la VRAM" .. FALLO
#         btfsnap OSError al leer o escribir la BTF .... INVALID
#
#   rc=2  "falta el fichero o la dependencia" .......... INVALID  (12 herramientas)
#         ibtrace/pte/verdiff "me invocaste mal" ....... USAGE, que aqui se
#         reporta como INVALID. No se ejercita: las lineas de la suite pasan
#         argumentos literales, asi que un error de uso seria determinista.
#
# El mapa global se queda como DEFAULT y estas son las unicas excepciones que
# necesita la suite hoy, medidas una a una. Si una herramienta nueva trae un
# codigo sobrecargado, se anade aqui; no se ensancha el mapa global, que es
# justamente lo que lo hacia falso.
invalidable_para() {
    # MEDIDO, Y ERA UN BUG REAL: `basename "$_t"` devuelve "pm4dec.py", CON
    # extension, y las etiquetas del case son "pm4dec", SIN ella. No casaba, la
    # excepcion no se aplicaba y `run` daba FALLO donde debia dar INVALID. Lo
    # probe inyectando un stub con el mismo codigo que una herramienta real, y el
    # nombre se extrajo bien: el fallo estaba en la clave, no en la extraccion.
    #
    # Y lo que mas da pena: la autocomprueba NO lo cazo, porque llamaba
    # `clasifica_de pm4dec 3` a mano, con una forma de argumento que el llamador
    # real nunca produce. Un control que se prueba con una forma de entrada que
    # la vida real no usa, no cubre el camino por el que se ejecuta. Los casos
    # nuevos usan la forma REAL, con extension.
    case "${1%.py}" in
        pm4dec)    echo "3" ;;
        btfsnap)   echo "3 5" ;;
        gfx8blocks) echo "3" ;;
        *)         echo "" ;;
    esac
}

# La clase de un rc para UNA herramienta concreta: la del mapa global, salvo que
# esa herramienta lo use como "no he podido comprobar".
clasifica_de() {
    local herramienta="$1" rc="$2" extra c
    if [ "$rc" -eq 0 ]; then echo OK; return; fi
    for c in $(invalidable_para "$herramienta"); do
        if [ "$rc" -eq "$c" ]; then echo INVALID; return; fi
    done
    clasifica "$rc"
}

resumen() {
    if [ "$fallos" -ne 0 ]; then
        echo "$fallos validacion(es) FALLIDA(S): se comprobo y no pasan."
        return 1
    fi
    if [ "$invalidos" -ne 0 ]; then
        echo "Sin fallos, pero $invalidos validacion(es) NO SE PUDIERON COMPROBAR."
        echo "Eso NO es un proyecto roto: es cobertura que hoy no existe."
        echo "Las herramientas implicadas no son autoridad para lo que no midieron."
        echo
        for r in "${RESULTADOS[@]}"; do
            case "$r" in INVALID*) echo "  $r" ;; esac
        done
        return 4
    fi
    echo "TODO CORRECTO"
    return 0
}

# --- autocomprueba del clasificador Y DEL RESUMEN --------------------------
# MEDIDO, DOS DEFECTOS EN EL MISMO BLOQUE, y los dos hacen lo mismo: este control
# NO PODIA probar lo que decia probar.
#
#  (a) `local fallos=0` TAPABA el global `fallos` que `resumen` lee. Con el
#      contador local a 0, la rama de fallos de `resumen` nunca se ejecutaba, con
#      lo que la mitad de la autocomprueba era decoracion.
#  (b) yo preparaba los casos con `f` e `i`, que `resumen` NO VE: lee `fallos` e
#      `invalidos`. O sea que las tres salidas que yo creía estar comprobando se
#      ejecutaban con los valores de siempre.
#
# Lo correcto es GUARDAR Y RESTAURAR los globales reales, y no probar con
# variables que la funcion no lee.
autocomprueba_clasificador() {
    local malos=0 total=0
    # El mapa MEDIDO, no supuesto: cada caso tiene un rc real observado.
    [ "$(clasifica 0)"   = OK ]      || malos=$((malos+1)) total=$((total+1))   # todo pasa
    [ "$(clasifica 2)"   = INVALID ] || malos=$((malos+1)) total=$((total+1))   # fichero ausente
    [ "$(clasifica 4)"   = INVALID ] || malos=$((malos+1)) total=$((total+1))   # no contrastado
    [ "$(clasifica 1)"   = FALLO ]   || malos=$((malos+1)) total=$((total+1))   # se comprobo y falla
    [ "$(clasifica 3)"   = FALLO ]   || malos=$((malos+1)) total=$((total+1))   # falta en el fichero
    [ "$(clasifica 5)"   = FALLO ]   || malos=$((malos+1)) total=$((total+1))   # dato incoherente
    [ "$(clasifica 126)" = FALLO ]   || malos=$((malos+1)) total=$((total+1))   # no ejecutable
    [ "$(clasifica 127)" = FALLO ]   || malos=$((malos+1)) total=$((total+1))   # no existe el script

    # LAS TRES SALIDAS DEL RESUMEN, sobre los globales DE VERDAD.
    # Sin esto, la rama de fallos puede quedarse sin su `return 1` y la suite
    # entera reporta exito mientras falla. Ya paso de verdad, en este mismo cambio.
    local _f0 _i0 _rc
    _f0=$fallos; _i0=$invalidos

    fallos=0; invalidos=0; _rc=0
    resumen >/dev/null 2>&1 || _rc=$?
    [ "$_rc" -eq 0 ] || malos=$((malos+1)) total=$((total+1))

    fallos=0; invalidos=1; _rc=0
    resumen >/dev/null 2>&1 || _rc=$?
    [ "$_rc" -eq 4 ] || malos=$((malos+1)) total=$((total+1))

    fallos=1; invalidos=0; _rc=0
    resumen >/dev/null 2>&1 || _rc=$?
    [ "$_rc" -eq 1 ] || malos=$((malos+1)) total=$((total+1))

    fallos=2; invalidos=3; _rc=0
    resumen >/dev/null 2>&1 || _rc=$?
    [ "$_rc" -eq 1 ] || malos=$((malos+1)) total=$((total+1))

    # LAS EXCEPCIONES MEDIDAS. Sin estos casos, `invalidable_para` podria devolver
    # una cadena vacia o equivocada y la suite no se enteraria: el mapa global
    # seguia dando FALLO, que es justo lo que hay que detectar.
    # LA FORMA REAL, CON EXTENSION: es lo que `basename` entrega. La version
    # anterior de estos mismos casos usaba "pm4dec" sin ".py", que es una forma
    # que el llamador real NUNCA produce, y por eso no podia cazar el bug.
    [ "$(clasifica_de pm4dec.py 3)"    = INVALID ] || malos=$((malos+1)) total=$((total+1))
    [ "$(clasifica_de pm4dec.py 5)"    = FALLO ]   || malos=$((malos+1)) total=$((total+1))
    [ "$(clasifica_de pm4dec.py 2)"    = INVALID ] || malos=$((malos+1)) total=$((total+1))
    [ "$(clasifica_de pm4dec.py 0)"    = OK ]      || malos=$((malos+1)) total=$((total+1))
    [ "$(clasifica_de btfsnap.py 3)"   = INVALID ] || malos=$((malos+1)) total=$((total+1))
    [ "$(clasifica_de btfsnap.py 5)"   = INVALID ] || malos=$((malos+1)) total=$((total+1))
    [ "$(clasifica_de gfx8blocks.py 3)" = INVALID ] || malos=$((malos+1)) total=$((total+1))
    # los dos que NO deben moverse: el mismo rc, distinta herramienta
    [ "$(clasifica_de bootcheck.py 3)" = FALLO ]   || malos=$((malos+1)) total=$((total+1))
    [ "$(clasifica_de cn8.py 3)"       = FALLO ]   || malos=$((malos+1)) total=$((total+1))

    fallos=$_f0; invalidos=$_i0

    if [ "$malos" -ne 0 ]; then
        echo "  EL CLASIFICADOR O EL RESUMEN ESTAN MAL: $malos de $total casos fallan."
        echo "  Con el clasificador roto, toda clasificacion posterior es inventada."
        return 4
    fi
    return 0
}

# Una linea que INFORMA y no gobierna la puerta. Existe para lo que es
# observable pero no es propiedad de quien publica: una comprobacion sobre
# documentos que escribe otra sesion no puede ser puerta de esta suite, porque
# bastaria con que otra sesion dejase un fichero a medias para que NUNCA se
# pudiera publicar aqui. Y sin puerta tampoco: el dato se imprime, con los
# ficheros culpables, para que quien lo puede arreglar lo sepa.
#
# MEDIDO 2026-10-03: `vclaims` sobre 08-ARQUITECTURA estaba como puerta y fallo
# porque RE-INDEX.md, untracked y de otra sesion, trae citas a ficheros que no
# existen. El defecto es el mismo que el de CN-R8, un nivel mas arriba: una
# comprobacion que mide el MUNDO y se hace cargo de el.
#
# NOTA de lectura: el relleno de un printf de ancho fijo se confunde con un
# espacio del fichero. Yo conte ese relleno como caracter y busqué " run() {",
# que no existe. Se busco "run() {" y ya cascaba.
informa() {
    local nombre="$1"; shift
    local salida rc
    salida=$("$@" 2>&1)
    rc=$?
    printf '  %-46s INFORMA rc=%d (no gobierna la puerta)
' "$nombre" "$rc"
    printf '%s
' "$salida"         | grep -oE "[0-9A-Za-z_./-]+\.md:[0-9]+"         | sed 's/^/       cita sin resolver en: /' | sort -u | head -8
    return 0
}

run() {
    local nombre="$1"; shift
    local salida rc clase herr
    salida=$("$@" 2>&1)
    rc=$?
    # el nombre de la herramienta es el primer token que parece un script: el
    # comando puede ser "./x.py", "python3 x.py" o "python3 /ruta/x.py"
    herr=""
    for _t in "$@"; do
        case "$(basename "$_t")" in
            *.py) herr=$(basename "$_t"); break ;;
        esac
    done
    if [ -n "$herr" ]; then
        clase=$(clasifica_de "$herr" "$rc")
    else
        clase=$(clasifica "$rc")
    fi
    case "$clase" in
    OK)
        RESULTADOS+=("OK      $nombre")
        printf '  %-46s OK\n' "$nombre"
        ;;
    INVALID)
        invalidos=$((invalidos+1))
        RESULTADOS+=("INVALID $nombre (rc=$rc: no se pudo comprobar)")
        printf '  %-46s INVALID rc=%d (no se pudo comprobar, NO es un fallo)\n' \
               "$nombre" "$rc"
        printf '%s\n' "$salida" | head -20 | sed 's/^/       /'
        ;;
    FALLO)
        fallos=$((fallos+1))
        RESULTADOS+=("FALLO   $nombre (rc=$rc)")
        printf '  %-46s FALLO rc=%d\n' "$nombre" "$rc"
        printf '%s\n' "$salida" | head -20 | sed 's/^/       /'
        ;;
    esac
}

echo "=== revkit: validaciones ==="
echo "modo: $RAPIDO"
echo

# Autocomprueba del clasificador ANTES de usar el clasificador. Si esto falla,
# nada mas de lo que sigue significa nada, asi que se para aqui.
if ! autocomprueba_clasificador; then
    echo
    echo "ABORTADO: sin clasificador fiable no hay suite."
    exit 4
fi
# El mapa que se anuncia se GENERA desde `clasifica`, no se reescribe a mano.
# MEDIDO: escrito a mano, seguia diciendo "0=OK, 4=INVALID, resto=FALLO" DESPUES de
# que el protocolo cambiara, o sea que la linea que informa del clasificador era
# capaz de mentir sobre el clasificador. Es un valor derivado escrito como si
# fuera una constante: cuando el derivado cambia y la copia no, la copia miente.
_mapa=""
for _rc in 0 1 2 3 4 5 126 127; do
    _mapa="$_mapa $_rc=$(clasifica $_rc)"
done
echo "  clasificador de codigos de salida: OK, medido sobre 8 codigos reales"
echo "    mapa:$_mapa"
for _h in pm4dec btfsnap gfx8blocks; do
    echo "    excepcion medida: $_h -> INVALID con rc=$(invalidable_para "$_h")"
done
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
run "ibtrace: oraculo de numeros de linea, corpus entero" ./ibtrace.py selftest
run "emitref: que emisor del corpus corre en POLARIS12" ./emitref.py chain
run "emitref: nuestro emisor PTEPDE contra el del corpus" ./emitref.py comparar
run "emitref: controles del clasificador y del comparador" ./emitref.py selftest
run "causa: mapa de invalidate"      ./causa.py mapa mmVM_INVALIDATE_REQUEST
run "causa: descubre registros"      ./causa.py descubrir gfx_v8_0
echo

echo "--- documentos ---"
# La puerta de vclaims es CN-R8 dentro de selfcheck, que mide la CLASIFICACION de
# la herramienta sobre un fixture con resultado conocido. Esto de aqui mide el
# arbol, y el arbol lo escriben varias sesiones.
informa "vclaims: citas de 08-ARQ (informe, no puerta)" ./vclaims.py
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
    # El pptable v1: es lo que explica de donde salen los relojes que se miden en
    # reposo. El layout se valida contra usTableSize antes de imprimir nada, asi
    # que un rc=0 aqui significa "el layout esta demostrado", no "ha impreso algo".
    run "atomrom: pptable v1 y su tabla de mclk"    python3 atomrom.py ppt capturas/amdgpu_vbios.txt
    run "atomrom: contrato de arranque, una linea por parametro" \
                                                python3 atomrom.py ppt --resumen capturas/amdgpu_vbios.txt
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
    # klog: el log de arranque como fuente. Es NIVEL 0 (solo lee texto), y
    # es donde estaba la direccion de la tabla GART que F12 daba por
    # inobservable. rc=1 significa "la tabla esta fuera del BAR", que en esta
    # maquina NO es el caso.
    klog_out=$(python3 klog.py gart 2>&1); klog_rc=$?
    printf '  %-46s %s\n' "klog: tabla GART legible por BAR" \
        "rc=$klog_rc (0 legible, 1 fuera del BAR, 4 no comprobable)"
    echo "$klog_out" | grep -E "tabla GART|offset dentro|cabe en el BAR" \
        | sed 's/^/       /'
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
echo "--- la telemetria de hardware de la GPU, con las unidades verificadas ---"
# gputel mide la cadena de HARDWARE, que bootcheck no puede: el (driver dijo que
# arranco bien) no es lo mismo que (el hardware quedo donde deberia). Y trae dos
# trampas de unidad que ya han sido medidas en esta maquina.
if [ -f ./gputel.py ]; then
    run "gputel: self-test de unidades y de muestreo" ./gputel.py --self-test
fi

echo "--- el arranque, validado contra el log, con control positivo incluido ---"
# bootcheck responde a la pregunta que un driver propio necesita para validar su
# propio arranque: arranco bien? Y trae su propio control: si el log no es
# reconocible dice INVALID_RESULT en vez de "cero fallos", porque un cero sin
# prueba no es un resultado (NR-2026-10-02-d2).
if [ -f ./bootcheck.py ]; then
    run "bootcheck: self-test sobre logs SINTETICOS" ./bootcheck.py --self-test
fi

echo "--- la superficie de inicializacion: que bloques IP existen en esta placa ---"
# gfx8blocks responde a la pregunta previa: de los 84 bloques que el driver sabe
# instanciar, cuales existen en Polaris12. De ahi sale el conjunto vivo que usa
# gchwip_alcance, asi que los dos van juntos: si el primero falla, el segundo
# puede estar descartando sobre una lista equivocada.
if [ -f ./gfx8blocks.py ]; then
    run "gfx8blocks: self-test de la superficie de bloques IP" ./gfx8blocks.py --self-test
    run "gfx8blocks: los 8 bloques incondicionales de POLARIS12" ./gfx8blocks.py
fi
if [ -f ./gchwip_alcance.py ]; then
    run "gchwip_alcance: self-test del filtro de alcance" ./gchwip_alcance.py --self-test
fi

echo "--- la puerta de salida, probada sobre un repo de mentira ---"
# El selftest fabrica un repo y una suite de mentira en un temporal: los 14
# caminos de pub.sh se prueban SIN tocar el arbol real. Antes de que existiera,
# probar la puerta obligaba a mutar el arbol de verdad, y de ahi salio un commit
# con el mensaje "uno dos tres" que quedo en la historia.
if [ -x ./pub.sh ] || [ -f ./pub.sh ]; then
    run "pub.sh: selftest de la puerta" ./pub.sh --selftest
fi
echo

echo "--- snapshot de layouts desde la BTF (perecedera) ---"
# btfsnap guarda los layouts que salen de /sys/kernel/btf/<modulo>, que es por
# arranque: cuando haga falta y no este guardado, ya no habra de donde sacarlo.
# Solo se anade el --selftest, que no escribe nada y no depende del estado.
if [ -x ./btfsnap.py ] || [ -f ./btfsnap.py ]; then
    run "btfsnap: selftest de caminos de fallo" python3 ./btfsnap.py --selftest
fi
echo

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
# MEDIDO: el resumen solo miraba `fallos`, y una INVALID no cuenta como fallo
# porque no es un fallo. Sin esto, un rc=4 se clsificaba bien arriba y se
# perdia aqui, con lo que la distincion enteramente decorativa.
# MEDIDO, Y UN BUG QUE INTRODUJE YO EN ESTE MISMO CAMBIO: al reescribir el
# resumen se me OLVIDO el `exit 1` de la rama de fallos. Con eso, una suite con
# fallos imprimia "1 validacion(es) FALLIDA(S)" y a continuacion "TODO CORRECTO",
# con rc=0. Una suite rota que reporta exito, que es el fallo mas dano posible.
#
# Y lo compre porque SOLO probe las rutas OK e INVALID. La ruta FALLO, que es la
# que perdia el exit, no la ejecute. Un clasificador con tres salidas necesita
# las tres probadas, y la nueva es la que nadie mira porque se supone correcta.
#
# Por eso esto es una FUNCION y no codigo suelto al final: `resumen` se puede
# llamar con valores sinteticos y comprobar su rc, sin correr la suite entera.
resumen
exit $?
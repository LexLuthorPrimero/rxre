#!/bin/sh
# oracle.sh - la respuesta automatizada a la pregunta que mas veces he perdido
#             tiempo: "de donde sale esto y como lo compruebo".
#
# POR QUE UN ORACLE Y NO UN BUSCADOR
#
# En este proyecto se han perdido dos horas seguidas, en varios findings, a
# cosas que una linea de shell responde. Los casos:
#
#   - "no encuentro la funcion que asigna el VMID"  -> vmid_map.py
#   - "este simbolo no existe"                        -> rx550ref --sym
#   - "este offset es de mi ASIC o de otro"          -> reg_resolve.py --reg
#   - "que .c se compila para mi chip"               -> ipsolve.py --block
#   - "que registros toca este fichero"              -> reg_census.py --file
#   - "mi cita apunta a una linea que no existe"     -> audit_citations.sh
#   - "este flujo PM4 es coherente"                  -> rx550pm4val
#
# Un buscador encuentra occurrences. Un oracle responde una PREGUNTA y dice
# de que no puede responder, con un limite. Lo segundo es lo que hace falta
# aqui, porque el error de 037 fue una lectura parcial tratada como completa:
# lo peligroso no es no encontrar, es no saber que no se ha buscado del todo.
#
# QUE HACE
#
#   1. Localiza el corpus. Si no lo encuentra, dice cual busca y sale con 3.
#   2. indexa las herramientas disponibles en tools/ y comprueba que corren.
#   3. A partir de una consulta, elige la herramienta y la invoca.
#   4. Cada respuesta lleva un sello: corpus, sha del tarball, y el limite de
#      la afirmacion. "No encontrado" siempre es "no encontrado por ESTA via",
#      nunca una ausencia de hardware.
#
# USO
#
#   oracle.sh --self
#       Diagnostico: donde esta el corpus, que herramientas hay, que funcionan.
#
#   oracle.sh "<pregunta o simbolo>"
#       Elige herramienta, la ejecuta, y sella la respuesta.
#
#   oracle.sh --reg  mmVM_INVALIDATE_REQUEST
#   oracle.sh --sym  WAIT_REG_MEM_OPERATION
#   oracle.sh --file gmc_v8_0.c
#   oracle.sh --block sdma_v4_0_ip_block
#   oracle.sh --audit
#
# CODIGOS DE SALIDA
#
#   0  la consulta se respondio
#   1  se respondio con limites, o la herramienta reporto un problema
#   2  la consulta no se pudo clasificar
#   3  no hay corpus, o falta una herramienta requerida
#
# LO QUE NO HACE, y es lo importante
#
# No interpreta. Dice de donde viene cada cosa y hasta donde llega la evidencia.
# Cuando una herramienta responde "PROVEN_ABSENT" o "0 definitions", eso se
# imprime como lo que es: el resultado de esa via de busqueda, no un hecho
# sobre el hardware. Confundir las dos cosas es el error que 031 y 037
# documentaron, y el sello de cada respuesta esta ahi para impedirlo.

set -e

ROOT=$(cd "$(dirname "$0")/.." && pwd)
TOOLS="$ROOT/tools"
WORK=/tmp/opencode/oracle

TAR_SHA="12e8d5a973d1ad7c5a5c69882e4022b131ed715db7003fdcd760ddf8c3e51941"

# ---------------------------------------------------------------- corpus

find_corpus() {
	for c in "$ROOT/rx550-upstream-7.2.8/linux-7.2.8" \
		 "$ROOT/RESEARCH/working/linux-7.1.3"; do
		[ -d "$c/drivers/gpu/drm/amd/amdgpu" ] && { echo "$c"; return 0; }
	done
	return 1
}

# ---------------------------------------------------------------- sello

# Cada respuesta lleva este pie. Es lo que impide que una linea de salida se
# lea como un hecho sobre el hardware cuando es un resultado de busqueda.
stamp() {
	_what=$1
	_via=$2
	_limit=$3
	_n=$4
	cat <<EOF

----------------------------------------------------------------------------
sello
  corpus     $(basename "$CORPUS")  (sha256 del tarball: ${TAR_SHA:0:16}...)
  pregunta   $_what
  via        $_via
  universo   $_n ficheros .c/.h en amdgpu/
  limite     $_limit
  NO ES UN HECHO SOBRE EL HARDWARE. Es el resultado de esta via de busqueda
             sobre este corpus. Una ausencia aqui es una ausencia aqui.
----------------------------------------------------------------------------
EOF
}

# ---------------------------------------------------------------- self

# Ninguna de estas debe abortar el script. En un oraculo, "la herramienta
# contesto que no" es una RESPUESTA, y set -e la convertiria en una muerte
# silenciosa sin sello. Por eso cada invocacion es "rc=0; ... || rc=$?".
self() {
	mkdir -p "$WORK"
	echo "=========================================================="
	echo "oracle.sh · diagnostico"
	echo "=========================================================="

	CORPUS=$(find_corpus) || true
	if [ -n "$CORPUS" ]; then
		echo "corpus        SI  $CORPUS"
		echo "              $(find "$CORPUS/drivers/gpu/drm/amd/amdgpu" -maxdepth 1 \( -name '*.c' -o -name '*.h' \) | wc -l) ficheros .c/.h"
	else
		echo "corpus        NO  buscado en, por este orden:"
		n=0
		for cand in "$ROOT/rx550-upstream-7.2.8/linux-7.2.8" \
			    "$ROOT/RESEARCH/working/linux-7.1.3"; do
			n=$((n + 1))
			echo "                 $n) $cand"
		done
		echo "  raiz        $ROOT"
		echo
		echo "  NOTA: esto es una ausencia de CORPUS, no de hardware. Para"
		echo " forcer uno: oracle.sh --kernel /ruta/a/linux-N.N.N <consulta>"
		echo
		echo "  sin corpus, las herramientas que dependen de el se declaran"
		echo "  ausentes aunque existan, porque no se pueden probar:"
		return 3
	fi

	echo
	echo "herramientas:"
	# Nombre, proposito en una linea, como se invoca. La invocacion se prueba de
	# verdad: una herramienta que esta en el directorio pero no arranca es peor
	# que una que no esta, porque el lector no lo nota hasta que la necesita.
	# Una tabla, no una cadena de palabras separada por espacios: la version
	# anterior perdia herramientas al partir y repetia otras, y una lista de
	# herramientas incompleta es peor que ninguna porque el lector no sabe que
	# le falta algo.
	cat > "$WORK/tools.tab" <<'TOOLS'
rx550ref|procedencia-de-un-simbolo
vmid_map|asignacion-de-vmid-y-geometria-ptba
rx550pm4val|validador-de-flujo-PM4
reg_resolve|offset-de-registro-con-unidad
reg_census|registros-que-toca-un-fichero
ipsolve|que-fichero-implementa-un-ip-block
asic_resolver|compila-para-mi-ASIC
struct_layout|tamano-y-offset-de-un-struct
cap_census|que-platform-caps-activa
regtable_audit|auditoria-de-tablas-de-registros
audit_citations|auditoria-de-citas-del-proyecto
pm4dw|coste-de-emision-PM4
which_hw|que-hardware-usa-esta-GPU
citegen|que-citas-apuntan-a-otro-ASIC
pm4census|convencion-de-count-en-MI-asic
hwip|de-donde-sale-la-version-de-cada-IP-block
unreach|los-N-selectores-de-despacho-alcanzan-este-chip
claims|audita-afirmaciones-tipificadas-no-lineas
frontier|que-via-cierra-cada-hueco-abierto
TOOLS

	while IFS='|' read -r n desc; do
		[ -z "$n" ] && continue
		if true; then
			if [ -f "$TOOLS/$n.py" ]; then
				ok=$(timeout 60 python3 "$TOOLS/$n.py" --selftest >/dev/null 2>&1 && \
				     echo selftest-ok || echo "selftest FALLA o no existe")
			elif [ -f "$TOOLS/$n.c" ]; then
				cc -std=gnu11 -O2 -o "$WORK/$n" "$TOOLS/$n.c" 2>/dev/null || true
				ok=$("$WORK/$n" --selftest >/dev/null 2>&1 && \
				    echo selftest-ok || echo "compila pero el selftest NO pasa")
			elif [ -f "$TOOLS/$n.sh" ]; then
				# Un script de shell no puede tener --selftest como convencion
				# de forma gratuita. Se comprueba que exista, que sea legible
				# por sh, y se marca como SIN SELFTEST: es una afirmacion
				# sobre lo que la herramienta NO demuestra.
				if sh -n "$TOOLS/$n.sh" 2>/dev/null; then
					ok="script, SINTAXIS ok, SIN SELFTEST"
				else
					ok="script con ERROR DE SINTAXIS"
				fi
			elif [ -x "$TOOLS/$n" ]; then
				ok=$("$TOOLS/$n" --selftest >/dev/null 2>&1 && \
				    echo selftest-ok || echo "selftest FALLA o no existe")
			else
				# Aqui "ausente" es un hecho del DIRECTORIO, y es un hecho real:
				# se comprueban tres sitios concretos. No es una ausencia de
				# capacidad, es la ausencia de un fichero, y se distinguen.
				ok="AUSENTE (ni .py ni .c ni ejecutable)"
			fi
		fi
		printf '  %-16s %-38s %s\n' "$n" "$desc" "$ok"
	done < "$WORK/tools.tab"
	rm -f "$WORK/tools.tab"

	echo
	echo "el resto se invoca a mano; ver su --help."
}

# ---------------------------------------------------------------- HELPERS

# Cada invocacion devuelve codigo y texto. La classificacion decide cual.
run_sym() {
	"$TOOLS/rx550ref" --dir "$CORPUS/drivers/gpu/drm/amd/amdgpu" \
		--dir "$CORPUS/drivers/gpu/drm/amd/include/asic_reg" \
		--sym "$1" --max 24
}

run_reg() {
	python3 "$TOOLS/reg_resolve.py" --kernel "$CORPUS" \
		--amd-root "$CORPUS/drivers/gpu/drm/amd" \
		--gfx gfx_8_0 --reg "$1"
}

run_file() {
	python3 "$TOOLS/reg_census.py" --kernel "$CORPUS" \
		--file "$CORPUS/drivers/gpu/drm/amd/amdgpu/$1" \
		--resolve --gfx gfx_8_0 --top 20
}

run_block() {
	python3 "$TOOLS/ipsolve.py" --kernel "$CORPUS" \
		--chip CHIP_POLARIS12 --block "$1"
}

run_vmid() {
	python3 "$TOOLS/vmid_map.py" --kernel "$CORPUS"
}

# which_hw es la mas importante de las once: responde "que fichero ejecuta esta
# GPU", que es la pregunta que produjo la retraccion de 035/036 (043). Se ofrece
# como via propia y tambien como respaldo de --block cuando el despacho es por
# version de IP, que es cuando ipsolve no puede decidir.
run_whichhw() {
	python3 "$TOOLS/which_hw.py" --kernel "$CORPUS" "$@" || return $?
}

# ---------------------------------------------------------------- main

# --self se despacha ANTES de localizar el corpus, y por un motivo concreto:
# --self ES el diagnostico, y su unico trabajo cuando no hay corpus es decir
# donde lo ha buscado. Con el guard delante, --self moria con un mensaje de tres
# palabras en el unico caso para el que existe. Un diagnostico que no se puede
# ejecutar en la situacion que diagnostica no es un diagnostico.
case "${1:-}" in
--self)
	mkdir -p "$WORK"
	self
	exit $?
	;;
esac

CORPUS=$(find_corpus) || {
	echo "oracle: no encuentro el corpus. Usa --self para ver donde lo busca." >&2
	exit 3
}
mkdir -p "$WORK"

Q=""
MODE=""
case "${1:-}" in
--sym)    MODE=sym;   Q="$2" ;;
--reg)    MODE=reg;   Q="$2" ;;
--file)   MODE=file;  Q="$2" ;;
--block)  MODE=block; Q="$2" ;;
--vmid)   MODE=vmid;  Q="asignacion de VMID" ;;
--which)  MODE=which; Q="que hardware usa esta GPU" ;;
--citas)  MODE=citas; Q="que citas apuntan a otro ASIC" ;;
--count)  MODE=count; Q="convencion de count de PACKET3" ;;
--hwip)   MODE=hwip;  Q="de donde sale la version de cada IP block" ;;
--unreach) MODE=unreach; Q="alcanzan los selectores de despacho a este chip" ;;
--claims) MODE=claims; Q="de donde viene el respaldo de las afirmaciones" ;;
--frontier) MODE=frontier; Q="que haria falta para cerrar cada hueco" ;;
--audit)  MODE=audit; Q="auditoria de citas" ;;
--help|-h|"")
	cat <<EOF
uso:
  oracle.sh --self                    diagnostico: corpus y herramientas
  oracle.sh "<texto>"                clasifica y ejecuta
  oracle.sh --sym  SIMBOLO           donde esta definido, y quien lo incluye
  oracle.sh --reg  REGISTRO          offset de un registro, con unidad
  oracle.sh --file  FICHERO.c        que registros toca, resueltos
  oracle.sh --block IP_BLOCK         que .c lo implementa para CHIP_POLARIS12
  oracle.sh --vmid                   asignacion de VMID y geometria de PTBA
  oracle.sh --which                  que fichero ejecuta esta GPU (que HWIP tiene NO)
  oracle.sh --citas                  que citas del proyecto apuntan a otro ASIC
  oracle.sh --count                  la convencion de count de PACKET3, en MI asic
  oracle.sh --hwip                   de donde sale cada IP version, y cuales se necesitan
  oracle.sh --unreach                si algun selector de IP hay que leerlo (NO, para este chip)
  oracle.sh --claims                de donde viene el respaldo de las afirmaciones
  oracle.sh --frontier              que haria falta para cerrar cada hueco, y cuales son pared
  oracle.sh --audit                  todas las citas del proyecto
EOF
	exit 0
	;;
*)        MODE=auto;  Q="$1" ;;
esac

UNIV=$(find "$CORPUS/drivers/gpu/drm/amd/amdgpu" -maxdepth 1 \
       \( -name '*.c' -o -name '*.h' \) | wc -l)

if [ "$MODE" = auto ]; then
	# Clasificacion por forma, no por semantica. Un clasificador que "entiende"
	# la pregunta acaba respondiendo a la pregunta que el modelo de lenguaje
	# quiere en vez de a la que se le hizo.
	case "$Q" in
	*mmVM_*|*mmATC_*|*mmBIF_*|*mmHDP_*|*mmMC_*)
		MODE=reg ;;
	*ip_block*|*_ip_block*|*ipblocks*)
		MODE=block ;;
	*.c|*.h)
		MODE=file ;;
	*vmid*|*VMID*|*vmid*|ptba*|PTBA*)
		MODE=vmid ;;
	*ip_block*|*cual.*fichero*|*que.*fichero*)
		MODE=which ;;
	*)
		MODE=sym ;;
	esac
	echo "(clasificado como: $MODE por la forma del texto, no por su significado)"
fi

rc=0
case "$MODE" in
sym)   rc=0; run_sym  "$Q" || rc=$?; stamp "donde esta $Q y quien lo incluye" \
	"rx550ref --sym (busca en amdgpu/ y asic_reg/, compara valores, verifica alcanzabilidad)" \
	"una definicion que no aparece puede existir en otro ASIC; el veredicto de alcanzabilidad se refiere a este consumidor" \
	"$UNIV" ;;
reg)   rc=0; run_reg  "$Q" || rc=$?; stamp "offset de $Q" \
	"reg_resolve --reg (busca en include/asic_reg, compara generaciones)" \
	"un PROVEN_ABSENT_EN_ASIC_REG es ausencia de la definicion de offset, no del hardware" \
	"$UNIV" ;;
file)  rc=0; run_file "$Q" || rc=$?; stamp "que registros toca $Q" \
	"reg_census --file (extrae mm* y resuelve)" \
	"cuenta escrituras directas, no inferencia por macros ni por punteros" \
	"$UNIV" ;;
block) rc=0; run_block "$Q" || rc=$?; stamp "que fichero implementa $Q para CHIP_POLARIS12" \
	"ipsolve --block (sigue el despacho en amdgpu_discovery.c)" \
	"un NOT_DISPATCHED puede significar dos cosas distintas: que el chip no lo selecciona, o que el despacho es por version de IP y no por case de chip. which_hw dice cual" \
	"$UNIV" ;;
which) rc=0; run_whichhw --no-host || rc=$?; \
	stamp "que fichero ejecuta esta GPU, y que NO se puede saber sin leerla" \
	"which_hw (lee el case del chip, resuelve .funcs, clasifica el tipo de despacho)" \
	"el despacho por version de IP NO es decidible sin leer el registro; la herramienta lo dice en vez de suponer" \
	"$UNIV" ;;
citas) rc=0; python3 "$TOOLS/citegen.py" --kernel "$CORPUS" || rc=$?; \
	stamp "que citas del proyecto apuntan a un fichero que esta GPU no ejecuta" \
	"citegen (resuelve el case del chip, el .funcs de cada bloque, y clasifica cada cita)" \
	"NO senala una cita como errada: senala que el fichero citado no esta en la ruta de ejecucion. Una cita a otro ASIC puede ser una comparacion legitima" \
	"$UNIV" ;;
count) rc=0; python3 "$TOOLS/pm4census.py" --kernel "$CORPUS" || rc=$?; \
	stamp "la convencion de count de PACKET3 en el ASIC de esta GPU" \
	"pm4census (macro PACKET3 de la cadena de headers, y los emisores del .c que el case del chip anade)" \
	"mide lo que el driver de referencia ESCRIBE, no lo que el hardware LEE: eso es NOT_DETERMINED y 033 establecio que el spec de GFX8 no esta publicado. Las emisiones que no reconcilian se marcan LIMITE y no se usan para el veredicto" \
	"$UNIV" ;;
frontier) rc=0; python3 "$TOOLS/frontier.py" || rc=$?; \
	stamp "que via de cierre tiene cada hueco abierto" \
	"frontier.py (agrupa por documento, clasifica la SECCION que declara los huecos, y detecta los cerrados por findings posteriores)" \
	"la clasificacion es por MARCAS sobre la seccion, no comprension. Clasificando las 241 afirmaciones sueltas se quedaba 226 sin pistas; la unidad correcta es el documento. Y la deteccion de obsolescencia es por CO-OCURRENCIA, con el criterio fuerte: un solo componente solo casa como prefijo" \
	"$UNIV" ;;
claims) rc=0; python3 "$TOOLS/claims.py" || rc=$?; \
	stamp "de donde viene el respaldo de las afirmaciones tipificadas" \
	"claims.py (extrae las clasificaciones tipificadas de los 98 findings, y distingue CITA de CODIGO de NADA)" \
	"la extraccion es de PROSA: no comprueba que la cita respalde la afirmacion, eso requiere entender la frase. Solo pone la una al lado de la otra. Y no distingue una clasificacion de un simbolo del corpus" \
	"$UNIV" ;;
unreach) rc=0; python3 "$TOOLS/unreach.py" --kernel "$CORPUS" || rc=$?; \
	stamp "si la version de algun selector de IP hay que leerla" \
	"unreach.py (rama del case del chip, grafo de llamadas ADELANTE, cierre transitivo, y el recuento de usos de amdgpu_ip_version que acota el claim)" \
	"que un selector de despacho sea inalcanzable NO significa que la version de IP no se lea nunca: hay 629 usos mas en 398 funciones alcanzables, que afectan al COMPORTAMIENTO y no a la eleccion de fichero" \
	"$UNIV" ;;
hwip)  rc=0; python3 "$TOOLS/hwip.py" --kernel "$CORPUS" || rc=$?; \
	stamp "de donde sale la version de cada IP block, y cuales exigen leer un registro" \
	"hwip.py (busca la asignacion a ip_versions[] por estructura, la funcion que llena el buffer por MMIO, los case que hardcodean, y prueba por alcanzabilidad si el despacho por version se ejecuta)" \
	"la version de TODOS los IP block se lee de una tabla en la tarjeta, por tres niveles de MMIO encadenados. Que un HWIP se lea no significa que haya que leerlo: solo importa si su valor SELECCIONA codigo" \
	"$UNIV" ;;
vmid)  rc=0; run_vmid       || rc=$?; stamp "asignacion de VMID y geometria de PTBA" \
	"vmid_map (lee gmc_v8_0.c, el header que incluye, y el grafo de llamadas)" \
	"el grafo es textual: una llamada por macro de funcion o por punto no aparece; PROVEN_DERIVED no cierra ningun NOT_DETERMINED" \
	"$UNIV" ;;
audit) rc=0; sh "$TOOLS/audit_citations.sh" || rc=$?; \
	stamp "todas las citas del proyecto" \
	"audit_citations (existencia de linea, valor, alcanzabilidad)" \
	"no detecta citar la cabecera de otra generacion cuando el valor coincide; declarado en el script" \
	"$UNIV" ;;
esac

# Encadenado. Un NOT_DISPATCHED de ipsolve no distingue "este chip no lo
# selecciona" de "el despacho es por version de IP y no hay case de chip que
# buscar". Son dos causas con remedies opuestos, y sin distinguirlas se
# cicatrizan los dos errores. which_hw dice cual, asi que la respuesta
# automatica a un --block fallido es preguntar por el hardware.
#
# Y va DESPUES del esac, no dentro de el: la primera version lo coloco en medio
# de las ramas, y el if se comio las tres siguientes.
if [ "$MODE" = block ] && [ "$rc" -ne 0 ]; then
	echo
	echo "================================================================"
	echo "  ipsolve no lo resolvio. La pregunta correcta es cual es el"
	echo "  hardware de esta GPU, y eso es lo que responde which_hw:"
	echo "================================================================"
	echo
	run_whichhw --no-host || true
	stamp "despues de un --block sin resolver" \
	"which_hw, porque un NOT_DISPATCHED de ipsolve no distingue los dos casos" \
	"este bloque NO se resuelve solo: hace falta la version de IP del registro" \
	"$UNIV"
fi

exit $rc

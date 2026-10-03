#!/usr/bin/env bash
# contratos.sh -- verifica que cada binario de test hace lo que su Makefile dice.
#
# QUE: extrae la lista EXACTA de invocaciones del target `run` con `make -n`, las
#      ejecuta una por una, y de cada una mide: codigo de salida, bytes de salida,
#      y el par passed/failed que el propio binario imprime.
#
# POR QUE: hay dos formas de mentir aqui.
#      (a) Teclear los comandos a mano -> se desincronizan del Makefile el dia que
#          cambie uno, y el informe sigue diciendo "todo verde".
#      (b) Contar "PASS" en mayuscula -> los binarios imprimen "passed:" en
#          minuscula, el contador da 0, y un test que pasa 1238 asserts aparece
#          como el que no verifica nada.
#      Las doserrors ocurrieron al escribir esta tool. Extraer y parsear en
#      minuculas las evita por construccion, no por disciplina.
#
# SALIDA: TSV  BIN<TAB>ARGC<TAB>EXIT<TAB>BYTES<TAB>PASSED<TAB>FAILED<TAB>VEREDICTO
#
# CODIGO DE SALIDA:
#   0  todas las invocaciones_exitaron 0 yoninforme salio vacio
#   1  alguna invocacion fallo, o salio con 0 bytes de salida
#   3  no se pudo extraer la lista (Makefile ilegible, make fallo)
#
# USO: tools/contratos.sh [--verbose]
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd)"
TESTS="$HERE/tests"
[ -d "$TESTS" ] || { echo "ERROR: no existe $TESTS" >&2; exit 3; }
cd "$TESTS" || exit 3

VERBOSE=0
[ "${1:-}" = "--verbose" ] && VERBOSE=1

# ---- 1. las invocaciones, extraidas, no tecleadas -----------------------------
# `make -n run` imprime los comandos que ejecutaria. Se filtran las lineas que
# empiezan por "./" porque son las de los binarios de test; el resto (@echo,
# mkdir, cd) no produce evidencia.
LIST="$(mktemp)"
trap 'rm -f "$LIST" "$LIST.cmd"' EXIT
make -n run > "$LIST.cmd" 2>/dev/null
grep -E '^\./test_' "$LIST.cmd" > "$LIST" || true

if [ ! -s "$LIST" ]; then
	echo "ERROR: make -n run no devolvio ninguna invocacion ./test_*" >&2
	echo "       revisa el target 'run' en $TESTS/Makefile" >&2
	exit 3
fi

n_inv="$(wc -l < "$LIST")"
echo "# invocaciones extraidas de 'make -n run': $n_inv" >&2
if [ "$n_inv" -lt 2 ]; then
	echo "AVISO: solo $n_inv invocacion(es). El target run deberia enumerar" >&2
	echo "       todos los binarios; un target con uno solo no es cobertura." >&2
fi

# ---- 2. ejecutar y medir ------------------------------------------------------
printf 'BIN\tARGC\tEXIT\tBYTES\tPASS_MARC\tFAIL_MARC\tVEREDICTO\tCONTRAPRUEBA\n'

malos=0

while IFS= read -r linea; do
	# la linea es "./test_x arg1 arg2 ..."; se separa el binario del resto
	bin="${linea%% *}"
	[ "$bin" = "$linea" ] && rest="" || rest="${linea#* }"

	out="$(mktemp)"
	# shellcheck disable=SC2086
	./$bin $rest > "$out" 2>&1
	rc=$?
	by="$(wc -c < "$out")"

	# Los binarios de este arbol usan TRES formatos de veredicto, y ninguno
	# cubre a todos:
	#   test_regs, test_vm, test_fence, ...  -> lineas "  PASS  <id>  <texto>"
	#   test_mmio_access, test_vmid1_*       -> "passed: N" / "failed: N"
	#   test_resource, test_static.sh        -> "resumen: N PASS, M FAIL"
	# Parsear un solo formato daba SIN_CONTADOR sobre tests que si verifican
	# 1238 asserts. Se aceptan los tres y se exige que aparezca alguno.
	nMARK="$(grep -cE '^[[:space:]]*PASS[[:space:]]' "$out" || true)"; nMARK="${nMARK:-0}"
	fMARK="$(grep -cE '^[[:space:]]*FAIL[[:space:]]' "$out" || true)"; fMARK="${fMARK:-0}"
	cPASS="$(grep -Eio '^[[:space:]]*passed[[:space:]]*:[[:space:]]*[0-9]+' "$out" | grep -Eo '[0-9]+$' | head -1)"
	cFAIL="$(grep -Eio '^[[:space:]]*failed[[:space:]]*:[[:space:]]*[0-9]+' "$out" | grep -Eo '[0-9]+$' | head -1)"
	rPASS="$(grep -Eio 'resumen[^0-9]*[0-9]+[[:space:]]+PASS' "$out" | grep -Eo '[0-9]+' | head -1)"
	rFAIL="$(grep -Eio '[^0-9]FAIL[^0-9]*[0-9]+' "$out" | grep -Eo '[0-9]+$' | head -1)"

	# El PASS de un resumen y el de los marcadores NO son la misma unidad:
	# test_regs imprime 12 lineas y resume 32, porque dentro de R02/R05b/R07 hay
	# bucles sobre 10 entradas que suman sin imprimir linea por aserto. Cruzarlos
	# daba 2 falsos positivos. El unico numero que tiene que valer 0 por las dos
	# vias es el de FALLOS, y el exit code es la tercera via.
	fallos=0
	[ "${fMARK:-0}" -gt 0 ] 2>/dev/null && fallos=1
	[ "${cFAIL:-0}" -gt 0 ] 2>/dev/null && fallos=1
	[ "${rFAIL:-0}" -gt 0 ] 2>/dev/null && fallos=1

	if [ "$rc" -eq 0 ] && [ "$fallos" -eq 1 ]; then
		ver="CONTRADICCION(exit=0 pero un contador marca fallos)"
		malos=$((malos + 1))
	elif [ "$rc" -ne 0 ]; then
		ver="ROTA(salida=$rc)"
		malos=$((malos + 1))
	elif [ "$by" -eq 0 ]; then
		ver="SIN_EVIDENCIA(0 bytes)"
		malos=$((malos + 1))
	elif [ "$fallos" -eq 1 ]; then
		ver="FALLOS"
		malos=$((malos + 1))
	elif [ "$nMARK" -eq 0 ] && [ -z "$cPASS" ] && [ -z "$rPASS" ]; then
		ver="SIN_VEREDICTO_legible"
		malos=$((malos + 1))
	else
		ver="OK"
	fi

	contraprueba="marcadores=${nMARK}"
	[ -n "$cPASS" ] && contraprueba="$contraprueba passed=$cPASS"
	[ -n "$rPASS" ] && contraprueba="$contraprueba resumen=$rPASS"

	printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$bin" "$(printf '%s' "$rest" | wc -w)" "$rc" "$by" "$nMARK" "$fallos" "$ver" "$contraprueba"

	if [ "$VERBOSE" -eq 1 ] || [ "$ver" != "OK" ]; then
		sed 's/^/    /' "$out" | head -40
	fi
	rm -f "$out"
done < "$LIST"

# Los binarios que el Makefile construye pero nunca nombra como comando NO
# estan necesariamente fuera del contrato: test_static.sh, que SI esta en la
# receta, recompila y ejecuta test_target_match en sus lineas 26-28.  Buscar
# solo en `make -n run` daba un falso positivo, y un falso positivo aqui es
# peor que no mirar: induce a "arreglar" algo que ya se ejecuta.
#
# Por eso se sigue un nivel de indireccion: si un binario no aparece como
# comando, se busca dentro de los .sh que si se invocan.  Lo que no se sigue es
# el segundo nivel, y se dice: cobertura de un nivel, no de dos.
echo
echo "# NO INVOCADOS COMO COMANDO: se busca dentro de los .sh que si se invocan"
n_noinv=0
for b in ./test_*; do
	[ -x "$b" ] || continue
	case "$b" in *.sh) continue ;; esac
	grep -q "^$b\b" "$LIST" && continue

	quien=""
	for s in $(grep -E '^\./test_.*\.sh$' "$LIST"); do
		# por el NOMBRE, no por "./nombre": test_static.sh lo invoca como
		# "$HERE/test_target_match", y buscar la cadena con "./" no lo encuentra.
		# ese fue el primer fallo de esta comprobacion:_existia_ la referencia y
		# la tool la declaro ausente.
		if grep -qF "${b#./}" "$s" 2>/dev/null; then quien="$quien $s"; fi
	done

	out="$(mktemp)"
	# shellcheck disable=SC2086
	"$b" > "$out" 2>&1
	rc=$?
	by="$(wc -c < "$out")"
	nP="$(grep -cE '^[[:space:]]*PASS[[:space:]]' "$out" || true)"; nP="${nP:-0}"
	nF="$(grep -cE '^[[:space:]]*FAIL[[:space:]]' "$out" || true)"; nF="${nF:-0}"
	nFc="$(grep -Eio '^[[:space:]]*failed[[:space:]]*:[[:space:]]*[0-9]+' "$out" | grep -Eo '[0-9]+$' | head -1)"
	nPc="$(grep -Eio '^[[:space:]]*passed[[:space:]]*:[[:space:]]*[0-9]+' "$out" | grep -Eo '[0-9]+$' | head -1)"
	mal=0
	[ "${nF:-0}" -gt 0 ] 2>/dev/null && mal=1
	[ "${nFc:-0}" -gt 0 ] 2>/dev/null && mal=1
	if [ "$rc" -ne 0 ]; then v="ROTA(salida=$rc)"; elif [ "$by" -eq 0 ]; then v="SIN_EVIDENCIA"
	elif [ "$mal" -eq 1 ]; then v="FALLOS"
	elif [ "$nP" -eq 0 ] && [ -z "$nPc" ]; then v="SIN_VEREDICTO_legible"
	else v="verde"; fi

	if [ -n "$quien" ]; then
		n_noinv=$((n_noinv + 1))
		printf '%s\t-\t%s\t%s\t%s\t%s\t%s\tINDIRECTO_via:%s\n' "$b" "$rc" "$by" "$nP" "$mal" "$v" "$quien"
	else
		printf '%s\t-\t%s\t%s\t%s\t%s\t%s\tFUERA_DEL_CONTRATO\n' "$b" "$rc" "$by" "$nP" "$mal" "$v"
		[ "$v" = "verde" ] || sed 's/^/    /' "$out" | head -30
	fi
	rm -f "$out"
done

echo
n_noinv=0
for b in ./test_*; do
	[ -x "$b" ] || continue
	case "$b" in *.sh) continue ;; esac
	grep -q "^$b\b" "$LIST" || n_noinv=$((n_noinv + 1))
done
printf '# TOTAL\tinvocadas=%d\tcon_problema=%d\tindirectas=%d\n' "$n_inv" "$malos" "$n_noinv"
[ "$malos" -eq 0 ] || exit 1
exit 0

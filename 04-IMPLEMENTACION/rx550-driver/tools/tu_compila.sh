#!/usr/bin/env bash
# tu_compila.sh -- mide si cada unidad de traduccion del driver compila, en las
# DOS contextos en que puede ser pedida, y clasifica el fallo por causa.
#
# QUE: por cada .c del driver, lo compila
#        (a) con las opciones de kbuild (kernel, -nostdinc)   -> "puede ir al .ko?"
#        (b) con las opciones de userspace (-fsyntax-only)     -> "el C es coherente?"
#      y clasifica el resultado en una matriz 2x2 en vez de un OK/FALLA unico.
#
# POR QUE: la primera version de esta tool decia "7 de 11 fallan" mezclando dos
#      causas que no son la misma: codigo que pide cabeceras de usuario, y codigo
#      que esta roto. Un contador unico no puede distinguir "no entra al modulo"
#      de "esta mal escrito", y usar ese contador para decidir seria interpretar
#      mal la evidencia. La matriz si.
#
# MATRIZ (fila = kernel, columna = userspace):
#   SI/SI    DUAL       correcta en ambos contextos
#   SI/NO    SOLO_KERNEL rompe fuera de kernel: no es testeable en host
#   NO/SI    SOLO_HOST  pide cabeceras de usuario: no puede entrar en obj-m
#   NO/NO    ROTA       esta mal en los dos: defecto real, contexto irrelevante
#
# SALIDA: TSV  TU<TAB>KERNEL<TAB>USERSPACE<TAB>CLASE<TAB>ERRORES_K<TAB>ERRORES_U<TAB>CAUSA
#
# CODIGO DE SALIDA (distinto del contenido, para que sea componible):
#   0  medicion producida, ninguna TU rota
#   1  medicion producida, hay al menos una TU ROTA
#   3  la medicion NO se produjo (faltan las opciones de kbuild)
#   "hubo salida" nunca significa "todo bien": hay que leer la clase de cada TU
#
# USO:  tools/tu_compila.sh [--detalle]
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE" || exit 3

CMD_FILE=".rx550_target.o.cmd"
if [ ! -r "$CMD_FILE" ]; then
	echo "ERROR: falta $CMD_FILE; no hay forma de reproducir las opciones" >&2
	exit 3
fi

KBUILD="$(awk '/^savedcmd_rx550_target\.o := /{sub(/^savedcmd_rx550_target\.o := /,""); print; exit}' "$CMD_FILE")"
if [ -z "$KBUILD" ]; then
	echo "ERROR: no se pudo extraer el comando de $CMD_FILE" >&2
	exit 3
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

printf 'TU\tKERNEL\tUSERSPACE\tCLASE\tERR_K\tERR_U\tCAUSA\n'

nk=0; nk_si=0; nk_no=0
nu=0; nu_si=0; nu_no=0

for src in *.c; do
	case "$src" in
	rx550_drv.mod.c) continue ;; # modulo modpost sintetico, no es codigo
	esac

	# --- (a) kernel: las opciones literales de kbuild, con -o y fuente parametrizados
	out="$TMP/k_${src%.c}.o"
	logk="$TMP/k_${src%.c}.log"
	run="$(printf '%s\n' "$KBUILD" \
		| sed -e "s|-o [^ ]*\.o|-o $out|" \
		      -e "s|-Wp,-MMD,[^ ]*|-Wp,-MMD,$out.d|" \
		      -e "s|rx550_target\.c|$src|")"
	# shellcheck disable=SC2086
	eval "$run" >"$logk" 2>&1
	rck=$?
	ek="$(grep -c ' error: ' "$logk" 2>/dev/null || true)"; ek="${ek:-0}"
	if [ "$rck" -eq 0 ] && [ -s "$out" ]; then ks=SI; nk_si=$((nk_si+1)); else ks=NO; nk_no=$((nk_no+1)); fi

	# --- (b) userspace: solo sintaxis, sin -nostdinc, con las propias rutas del host
	logu="$TMP/u_${src%.c}.log"
	if gcc -fsyntax-only -Wall -I"$HERE" "$src" >"$logu" 2>&1; then
		us=SI; eu=0; nu_si=$((nu_si+1))
	else
		us=NO; nu_no=$((nu_no+1))
		eu="$(grep -c ' error: ' "$logu" 2>/dev/null || true)"; eu="${eu:-0}"
		[ "$eu" -eq 0 ] && eu=1
	fi
	nk=$((nk+1)); nu=$((nu+1))

	# --- clase
	case "$ks/$us" in
	SI/SI) clase=DUAL ;;
	SI/NO) clase=SOLO_KERNEL ;;
	NO/SI) clase=SOLO_HOST ;;
	NO/NO) clase=ROTA ;;
	esac

	# --- causa: el primer error de cada lado, que es lo que discrimina
	ck="$(grep -m1 -E ' error: |fatal error: ' "$logk" 2>/dev/null | sed 's/^[[:space:]]*//' | cut -c1-110)"
	cu="$(grep -m1 -E ' error: |fatal error: ' "$logu" 2>/dev/null | sed 's/^[[:space:]]*//' | cut -c1-110)"
	if [ "$ks" = NO ] && [ -n "$ck" ]; then causa="$ck"
	elif [ "$us" = NO ] && [ -n "$cu" ]; then causa="user: $cu"
	else causa="-"; fi

	printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$src" "$ks" "$us" "$clase" "$ek" "$eu" "$causa"

	if [ "${1:-}" = "--detalle" ]; then
		[ "$ks" = NO ] && sed 's/^/    K| /' "$logk" | grep -E 'error:' | head -12
		[ "$us" = NO ] && sed 's/^/    U| /' "$logu" | grep -E 'error:' | head -12
	fi
done

printf '# TOTAL\tTU=%d\tK_SI=%d\tK_NO=%d\tU_SI=%d\tU_NO=%d\n' "$nk" "$nk_si" "$nk_no" "$nu_si" "$nu_no"

# se cuenta sobre el bucle, no sobre la salida formateada: grep sobre la propia
# salida contaria tambien la cabecera
nrota=0
for src in *.c; do
	case "$src" in rx550_drv.mod.c) continue ;; esac
	if [ -s "$TMP/k_${src%.c}.o" ]; then continue; fi
	if grep -q ' error: \|fatal error: ' "$TMP/u_${src%.c}.log" 2>/dev/null; then
		nrota=$((nrota + 1))
	fi
done
[ "$nrota" -gt 0 ] && exit 1
exit 0
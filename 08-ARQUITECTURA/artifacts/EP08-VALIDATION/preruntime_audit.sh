#!/usr/bin/env bash
# preruntime_audit.sh — validador ESTATICO de un harness bash de experimento.
#
# RESEARCH_INSTRUMENT. No es parte del driver ni del harness auditado.
# NO toca hardware, NO carga modulos, NO escribe fuera del directorio de salida.
#
# Que responde, y por que existe:
#   Un harness que nunca se ha ejecutado puede estar muerto por una falta
#   mecanica (referencia a variable no asignada) o por un fallo de medicion
#   (leer el campo equivocado de una herramienta). Los dos se ven IGUALES
#   desde fuera: "el harness no corrio". Separarlos es lo que hace este
#   instrumento, y es barato porque no necesita ni la placa ni sudo.
#
# Tres oraculos independientes, cada uno con su veredicto:
#   O1 BOUNDS     referencias a variables sin asignar, bajo `set -u`
#   O2 FIELDINDEX los indices awk $(NF-k) que el harness usa sobre pahole
#   O3 TOOLPIN    la version de pahole, que es lo que fija el layout de campos
#
# Uso:
#   preruntime_audit.sh --script=<ruta> [--out=<dir>] [--json]
#
# Salida: <dir>/preruntime-audit.tsv  +  informe en stdout.  exit 0 = audited,
# exit 1 = uso incorrecto. El VEREDICTO va en el TSV, no en el exit code:
# un exit 0 NO es "el harness esta bien" (mismo principio que el propio harness).

set -euo pipefail

SCRIPT=""; OUT=""; JSON=0
for a in "$@"; do
  case "$a" in
    --script=*) SCRIPT="${a#*=}" ;;
    --out=*)    OUT="${a#*=}" ;;
    --json)     JSON=1 ;;
    *) printf 'uso: %s --script=RUTA [--out=DIR] [--json]\n' "$0" >&2; exit 1 ;;
  esac
done
[ -n "$SCRIPT" ] || { printf 'falta --script\n' >&2; exit 1; }
[ -r "$SCRIPT" ] || { printf 'ilegible: %s\n' "$SCRIPT" >&2; exit 1; }
[ -n "$OUT" ] || OUT="$(dirname "$0")"

# Palabras que bash resuelve solo: no son defectos del harness.
BASH_BUILTIN="BASH_SOURCE BASH LINENO PWD IFS REPLY FUNCNAME"
is_builtin() { for b in $BASH_BUILTIN; do [ "$1" = "$b" ] && return 0; done; return 1; }

sha() { sha256sum "$1" | cut -d' ' -f1; }

# --- O1 ------------------------------------------------------------------
# Referencias $-NAME  menos  (asignaciones | readonly | local | for VAR in) .
# El rango `for` se cubre aparte porque `for a in` no lleva '='.
tmp_r=$(mktemp); tmp_a=$(mktemp); tmp_f=$(mktemp)
trap 'rm -f "$tmp_r" "$tmp_a" "$tmp_f"' EXIT

# NOTA DE METODO, con su motivo: la extraccion de referencias y de
# asignaciones se hace con `set +e` a proposito. Un harness sano NO tiene por
# que tener una asignacion con `${X:=`, y con `set -e` + `pipefail` un grep sin
# coincidencias ABORTA el instrumento. La primera version de este fichero murio
# exactamente asi, en silencio, y solo se vio porque se comprobo el exit code.
# Se registra para que no se repita.
#
# Segundo defecto del mismo instrumento, encontrado al validar el control
# negativo: `grep X || true | sed Y` se parsea como `grep X || (true | sed Y)`,
# porque `|` liga mas fuerte que `||`. Con el codigo anterior el `sed` no
# corria nunca y los `for k in` llegaban sin transformar, de modo que las
# variables de bucle de un harness sano se reportaban como no asignadas.
# Falso positivo. El fix es desactivar `errexit` en esta seccion, no parchear
# el operador.
set +e

grep -oE '\$\{?[A-Za-z_][A-Za-z0-9_]*' "$SCRIPT" \
  | sed 's/[$]//; s/[{}]//g' | sort -u > "$tmp_r"

{
  grep -oE '(^|[[:space:]])(readonly[[:space:]]+|declare[[:space:]]+-[A-Za-z]+\[[A-Za-z]*\][[:space:]]+|local[[:space:]]+|typeset[[:space:]]+)?[A-Za-z_][A-Za-z0-9_]*[[:space:]]*=' "$SCRIPT"
  grep -oE 'for[[:space:]]+[A-Za-z_][A-Za-z0-9_]*[[:space:]]+in' "$SCRIPT" | sed -E 's/^for[[:space:]]+//; s/[[:space:]]+in$//'
  grep -oE '\$\{[A-Za-z_][A-Za-z0-9_]*:?=' "$SCRIPT" | sed -E 's/^\$\{//; s/:?=$//'
} | sed -E 's/^[[:space:]]+//; s/readonly[[:space:]]+//; s/declare[[:space:]]+-[[:alpha:]]+\[[[:alpha:]]*\][[:space:]]+//; s/^(local|typeset)[[:space:]]+//; s/[[:space:]]*=$//' \
  | sort -u > "$tmp_a"

comm -23 "$tmp_r" "$tmp_a" > "$tmp_f"
set -e

# --- O2 / O3 -------------------------------------------------------------
# Indices NF usados cerca de pahole. NO se decide aqui cual es el correcto:
# se miden las columnas reales de la salida viva de pahole y se reporta.
pahole_ver="$(command -v pahole >/dev/null 2>&1 && pahole --version 2>/dev/null | tr -d '\n' || echo AUSENTE)"

unbound=0
declare -a UB=()
while read -r v; do
  [ -n "$v" ] || continue
  is_builtin "$v" && continue
  UB+=("$v"); unbound=$((unbound+1))
done < "$tmp_f"

# Veredicto
if [ "$unbound" -eq 0 ]; then O1="PASS"; else O1="FAIL"; fi
[ -n "$pahole_ver" ] && [ "$pahole_ver" != "AUSENTE" ] && O3="PINNED $pahole_ver" || O3="UNPINNED pahole AUSENTE"

# Campo real medido sobre la linea que el harness dice leer
FIELD_MEASURED=""
if [ -r /sys/kernel/btf/amdgpu ] && command -v pahole >/dev/null 2>&1; then
  line=$(pahole -C amdgpu_device /sys/kernel/btf/amdgpu 2>/dev/null | grep -m1 'no_hw_access' || true)
  if [ -n "$line" ]; then
    nf=$(printf '%s' "$line" | awk '{print NF}')
    f_nm1=$(printf '%s' "$line" | awk '{print $(NF-1)}')
    f_nm2=$(printf '%s' "$line" | awk '{print $(NF-2)}')
    FIELD_MEASURED="NF=$nf NF-1=$f_nm1 NF-2=$f_nm2"
  fi
fi

TSV="$OUT/preruntime-audit.tsv"
{
  printf 'script\tsha256\tbytes\n'
  printf '%s\t%s\t%s\n' "$SCRIPT" "$(sha "$SCRIPT")" "$(stat -c %s "$SCRIPT")"
  printf '\noraculo\tveredicto\tdetalle\n'
  printf 'O1_BOUNDS\t%s\t%s referencias sin asignar bajo set -u: %s\n' \
    "$O1" "$unbound" "${UB[*]:-<ninguna>}"
  printf 'O2_FIELDINDEX\t%s\t%s\n' \
    "$(printf '%s' "$FIELD_MEASURED" | grep -q 'NF-1=' && echo MEDIDO || echo NO_MEDIDO)" \
    "${FIELD_MEASURED:-sin BTF de amdgpu legible}"
  printf 'O3_TOOLPIN\t%s\t%s\n' "$O3" "el layout de columnas de pahole es lo que fija cual NF es el offset"
} > "$TSV"

if [ "$JSON" = 1 ]; then
  printf '{"script":"%s","sha256":"%s","O1":"%s","unbound":[%s],"pahole":"%s","field":"%s"}\n' \
    "$SCRIPT" "$(sha "$SCRIPT")" "$O1" \
    "$(for v in ${UB[*]:-}; do printf '"%s",' "$v"; done | sed 's/,$//')" \
    "$pahole_ver" "$FIELD_MEASURED"
fi

cat "$TSV"
printf '\nVEREDICTO_O1=%s  (0 referencias sin asignar = el harness puede llegar a su PHASE 1)\n' "$O1"
printf 'El exit code de este instrumento es 0 porque ha AUDITADO. No es un veredicto de salud.\n'
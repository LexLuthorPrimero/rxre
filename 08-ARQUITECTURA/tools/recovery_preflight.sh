#!/usr/bin/env bash
# recovery_preflight.sh — para cada instrumento del proyecto, responde a LA
# pregunta que de verdad importa:  "si lo rompo ahora, ¿qué puedo recuperar?"
#
# Por qué esto NO es un linter de estilo. El hallazgo 984 fue un `sed -i` que
# borró 9 bytes de un harness experimental. Se restauró porque el sha256 estaba
# escrito en un artefacto commiteado. Es decir: lo que salvó el fichero fue una
# coincidencia de procedimiento, no una propiedad del sistema. Esta herramienta
# convierte esa coincidencia en una propiedad MEDIBLE.
#
# Tres estados, y solo tres. No hay un cuarto "casi versionado":
#
#   VERSIONADO   git tiene el fichero. Recuperable con git checkout.
#   CON_HASH     git NO lo tiene, pero su sha256 está escrito en un artefacto
#                que SÍ está versionado. Recuperable reconstruyendo el byte.
#   SIN_RED      ni una cosa ni la otra. Destruido es destruido.
#
# Y la herramienta se mide a sí misma primero. Si está SIN_RED, lo dice, y ese
# es el motivo por el que tiene que vivir en un sitio versionado: un guard de
# recuperación que no se puede recuperar es peor que no tenerlo, porque se lee
# como si alguien lo hubiera pensado.
#
# Uso: recovery_preflight.sh [--root=DIR] [--out=DIR]

set -uo pipefail
ROOT="$(pwd)"; OUT="$ROOT"
for a in "$@"; do
  case "$a" in
    --root=*) ROOT="${a#*=}" ;;
    --out=*)  OUT="${a#*=}" ;;
  esac
done
TAB=$(printf '\t')

EXCL='^\./(RESEARCH/|rx550-upstream-|\.git/|archive/)'
PRECOND='(_EXPECTED|_WANTED|_REQ|EXPECT_[A-Z]|\bassert\b|\[ .*= "?\$)'

# ¿Su sha256 está escrito en un fichero que git SÍ versiona?
# Se indexa UNA vez: nombre de fichero -> sha256, y luego cada instrumento se
# busca por nombre en ese índice. Preguntar a git por cada instrumento sería
# N×M llamadas y no hace falta.
build_hash_index() {
  git ls-files 2>/dev/null | while read -r f; do
    [ -f "$f" ] || continue
    grep -hoE '[0-9a-f]{64}' "$f" 2>/dev/null | sort -u
  done | sort -u
}

classify() { # $1 = ruta
  local f="$1"
  if git ls-files --error-unmatch "$f" >/dev/null 2>&1; then echo VERSIONADO; return; fi
  if [ -s "$OUT/.hashindex" ] && grep -qxF "$(sha256sum "$f" | cut -d' ' -f1)" "$OUT/.hashindex"; then
    echo CON_HASH; return
  fi
  echo SIN_RED
}

TSV="$OUT/recovery-preflight.tsv"
HIDX="$OUT/.hashindex"

{
  printf '# RECUPERABILIDAD de los instrumentos con precondiciones. producer=recovery_preflight.sh\n'
  printf '# VERSIONADO=git lo tiene · CON_HASH=sha256 escrito en algo versionado · SIN_RED=ninguno\n'
  printf 'estado\tprecondiciones\tinstrumento\tsha256_actual\n'

  # 0) la herramienta, medida antes que nada
  me="${BASH_SOURCE[0]}"; me="${me#./}"
  printf '%s\t-\t%s\t%s\n' "$(classify "$me")" "$me" "$(sha256sum "$me" | cut -d' ' -f1)"

  # 1) índice de hashes de todo lo versionado
  build_hash_index > "$HIDX"

  # 2) instrumentos, con el filtro de terceros ANTES de quitar el './'
  find . \( -name '*.sh' -o -name '*.py' \) -type f 2>/dev/null \
    | grep -vE "$EXCL" | sed 's|^\./||' \
    | while read -r f; do
        n=$(grep -cE "$PRECOND" "$f" 2>/dev/null || true)
        case "$n" in ''|*[!0-9]*) n=0 ;; esac
        [ "$n" -gt 0 ] || continue
        printf '%s\t%s\t%s\t%s\n' "$(classify "$f")" "$n" "$f" "$(sha256sum "$f" | cut -d' ' -f1)"
      done | sort
} > "$TSV"

rm -f "$HIDX"

# AUTOVALIDACION del vocabulario. Un estado fuera de estos tres significa que el
# clasificador ha cambiado de reglas, y el consumidor no tiene por qué saberlo.
if awk -F"$TAB" -v t="$TAB" 'NR>3 && $1 !~ /^(VERSIONADO|CON_HASH|SIN_RED)$/ {print "VOCABULARIO: " $1; rc=1} END{exit rc+0}' "$TSV"; then :; else
  echo "ABORTO: estado fuera de vocabulario en $TSV. No es un dato." >&2; exit 2
fi
# AUTOVALIDACION de terceros, mirando el INICIO DE CAMPO de la columna 3.
if grep -qE "(^|${TAB})(${TAB})?(RESEARCH/|rx550-upstream-)" "$TSV"; then
  echo "ABORTO: el censo contiene terceros; el filtro no filtro. No es un dato." >&2; exit 2
fi

echo "=== RECUPERABILIDAD de los instrumentos con precondiciones ==="
awk -F"$TAB" 'NR>3{c[$1]++} END{for(k in c) printf "  %-12s %d\n", k, c[k]}' "$TSV" | sort -k2 -rn
echo
echo "=== SIN_RED: los que no se pueden recuperar si se rompen ==="
awk -F"$TAB" 'NR>3 && $1=="SIN_RED"{printf "  %-3s %s\n", $2, $3}' "$TSV"
echo
echo "=== la herramienta, medida a si misma (primera fila del TSV) ==="
awk -F"$TAB" 'NR==4{printf "  estado=%s  fichero=%s\n", $1, $3}' "$TSV"
echo
echo "escrito: $TSV"
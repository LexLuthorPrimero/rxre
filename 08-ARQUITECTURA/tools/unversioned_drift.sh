#!/usr/bin/env bash
# unversioned_drift.sh — para cada instrumento SIN VERSIONAR, ¿su sha256 sigue
# estar escrito en el corpus versionado?
#
# Por qué esto es el paso siguiente de 994, y no un extra. 994 declaró:
#
#   "CON_HASH prueba que el hash está escrito. NO prueba que ese hash sea el del
#    fichero que hay ahora. Compararlos distingue 'sin red' de 'cambiado'."
#
# Esa comparación es el discriminante, porque separa dos estados que hasta ahora
# se confundían en el MISMO bucket:
#
#   NEVER_HASHED   el fichero no se menciona en ningún sitio versionado.
#                  Nadie registró nunca su hash. No hay nada que haya derivado.
#   DRIFT          el fichero SE MENCIONA en el corpus versionado, pero su hash
#                  actual no aparece en ninguna parte. Alguien lo cambió (o lo
#                  cambió algo) y el hash registrado dejó de describirlo.
#
# DRIFT es la señal fuerte. Es exactamente lo que pasó con preruntime.sh en el
# turno de 982: cambió 9 bytes y el único aviso fue que un runner empezó a dar
# <sin veredicto>. Si esto hubiera corrido, habría dicho "tu fichero de 25513 B
# ahora mide 25504" en el momento.
#
# Uso: unversioned_drift.sh [--root=DIR] [--out=DIR]

set -uo pipefail
ROOT="$(pwd)"; OUT="$ROOT"
for a in "$@"; do
  case "$a" in --root=*) ROOT="${a#*=}" ;;
    --out=*)  OUT="${a#*=}" ;;
  esac
done
TAB=$(printf '\t')
EXCL='^\./(RESEARCH/|rx550-upstream-|\.git/|archive/)'

# Un solo recorrido del corpus versionado: sha256 registrados y nombres de
# fichero de instrumentos mencionados. Un `git grep` por instrumento sería N×M.
build_index() {
  git ls-files -z 2>/dev/null | while IFS= read -r -d '' f; do
    [ -f "$f" ] || continue
    grep -hoE '[0-9a-f]{64}' "$f" 2>/dev/null
  done | sort -u > "$OUT/.hashes"
  git ls-files -z 2>/dev/null | while IFS= read -r -d '' f; do
    [ -f "$f" ] || continue
    grep -hoE '[A-Za-z0-9_./-]+\.(sh|py)' "$f" 2>/dev/null
  done | sed 's|.*/||' | sort -u > "$OUT/.names"
}

TSV="$OUT/unversioned-drift.tsv"
{
printf '# DERIVA en instrumentos SIN VERSIONAR. producer=unversioned_drift.sh\n'
printf '# NEVER_HASHED=nunca se registro su hash · DRIFT=se menciona pero el hash ya no esta\n'
printf '# ONCE_HASHED=su hash coincide con lo registrado: verificado recuperable\n'
printf 'estado\tbytes\tsha256_actual\tinstrumento\n'

build_index

find . \( -name '*.sh' -o -name '*.py' \) -type f 2>/dev/null \
  | grep -vE "$EXCL" | sed 's|^\./||' \
  | while read -r f; do
      git ls-files --error-unmatch "$f" >/dev/null 2>&1 && continue   # versionado: no aplica
      sha="$(sha256sum "$f" | cut -d' ' -f1)"
      base="$(basename "$f")"
      if grep -qxF "$sha" "$OUT/.hashes"; then
        estado="ONCE_HASHED"
      elif grep -qxF "$base" "$OUT/.names"; then
        estado="DRIFT"
      else
        estado="NEVER_HASHED"
      fi
      printf '%s\t%s\t%s\t%s\n' "$estado" "$(stat -c %s "$f")" "$sha" "$f"
    done | sort
} > "$TSV"

rm -f "$OUT/.hashes" "$OUT/.names"

# AUTOVALIDACION: vocabulario cerrado. Un estado nuevo cambia las reglas y el
# consumidor no tiene por qué saberlo.
if awk -F"$TAB" 'NR>4 && $1 !~ /^(ONCE_HASHED|DRIFT|NEVER_HASHED)$/ {print "VOCABULARIO: "$1; rc=1} END{exit rc+0}' "$TSV"; then :; else
  echo "ABORTO: estado fuera de vocabulario en $TSV. No es un dato." >&2; exit 2
fi

echo "=== INSTRUMENTOS SIN VERSIONAR: ¿su hash sigue registrado? ==="
awk -F"$TAB" 'NR>4{c[$1]++} END{for(k in c) printf "  %-14s %d\n", k, c[k]}' "$TSV" | sort -k2 -rn
echo
echo "=== DRIFT: se mencionan, pero su hash ya no esta donde estaba ==="
awk -F"$TAB" 'NR>4 && $1=="DRIFT"{printf "  %8s B  %s\n           %s\n", $2, $4, $3}' "$TSV"
echo
echo "=== ONCE_HASHED: verificados recuperables ==="
awk -F"$TAB" 'NR>4 && $1=="ONCE_HASHED"{printf "  %8s B  %s\n", $2, $4}' "$TSV"
echo
echo "escrito: $TSV"
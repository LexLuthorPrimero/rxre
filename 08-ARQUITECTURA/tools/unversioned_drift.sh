#!/usr/bin/env bash
# unversioned_drift.sh — para cada instrumento SIN VERSIONAR, ¿su sha256 sigue
# registrado en el corpus versionado, al lado de su nombre?
#
# POR QUÉ HAY QUE MEDIR LA PROXIMIDAD Y NO LA COEXISTENCIA.
# La primera versión de este guion usaba "el nombre del fichero aparece en
# algún fichero versionado" como prueba de que su hash estaba registrado. Dio
# 38 falsos positivos: `tools/mutate.py` se menciona en tres hallazgos, los tres
# en prosa describiendo lo que hace, y su hash NO está en ninguno. "Aparece el
# nombre" NO es "está anotado el hash".
#
# El discriminante correcto es la PROXIMIDAD: el hash tiene que estar en la
# MISMA LÍNEA o al lado, en las N líneas del nombre. Un documento que registra hashes de
# diez herramientas no dice cuál es cuál; uno que registra UNO lo dice con el
# nombre al lado, y esa es la señal.
#
# Los tres estados, y la diferencia que importa:
#
#   ONCE_HASHED    el hash actual aparece junto al nombre. Verificado recuperable.
#   DRIFT          el nombre aparece, hay un hash al lado, y NO es el actual.
#                  Eso es un fichero modificado cuyo hash registrado ya no lo
#                  describe. La señal fuerte: es el `sed -i` de 982, automatico.
#   NEVER_HASHED   el nombre aparece, pero NINGÚN hash está al lado.
#                  Nadie anotó nunca su hash. No hay nada que haya derivado:
#                  no hay referencia contra la cual derivar.
#
# Uso: unversioned_drift.sh [--root=DIR] [--out=DIR] [--ventana=N]

set -uo pipefail
ROOT="$(pwd)"; OUT="$ROOT"; VENT=3
for a in "$@"; do
  case "$a" in
    --root=*)    ROOT="${a#*=}" ;;
    --out=*)     OUT="${a#*=}" ;;
    --ventana=*) VENT="${a#*=}" ;;
  esac
done
TAB=$(printf '\t')
EXCL='^\./(RESEARCH/|rx550-upstream-|\.git/|archive/)'
NAME_RE='[A-Za-z0-9_.-]+\.(sh|py)'

# UN SOLO recorrido del corpus versionado, y en awk: para cada línea que menciona
# un nombre de instrumento, se miran las N líneas de alrededor y se recogen los
# hashes que estén al lado. Salida: "nombre<TAB>hash" por cada pareja vista.
build_pairs() {
  git ls-files -z 2>/dev/null | while IFS= read -r -d '' f; do
    [ -f "$f" ] || continue
    awk -v v="$VENT" -v re="$NAME_RE" '
      { L[NR]=$0 }
      END {
        n = NR
        for (i = 1; i <= n; i++) {
          if (match(L[i], re) == 0) continue
          nm = substr(L[i], RSTART, RLENGTH)
          # se ignoran las referencias a los instrumentos de este guion
          if (nm == "unversioned_drift.sh" || nm == "recovery_preflight.sh") continue
          lo = i - v; if (lo < 1) lo = 1
          hi = i + v; if (hi > n) hi = n
          for (j = lo; j <= hi; j++)
            while (match(L[j], /[0-9a-f]{64}/) > 0) {
              print nm "\t" substr(L[j], RSTART, RLENGTH)
              L[j] = substr(L[j], RSTART+64)   # consumir, para no repetir
            }
        }
      }' "$f" 2>/dev/null
  done | sort -u > "$OUT/.pairs"
}

TSV="$OUT/unversioned-drift.tsv"
{
printf '# DERIVA en instrumentos SIN VERSIONAR. producer=unversioned_drift.sh\n'
printf '# ventana de proximidad=%s lineas. Solo cuenta el hash que esta AL LADO del nombre.\n' "$VENT"
printf '# ONCE_HASHED / DRIFT / NEVER_HASHED\n'
printf 'estado\tbytes\tsha256_actual\thashes_registrados_cerca\tinstrumento\n'

build_pairs

find . \( -name '*.sh' -o -name '*.py' \) -type f 2>/dev/null \
  | grep -vE "$EXCL" | sed 's|^\./||' \
  | while read -r f; do
      git ls-files --error-unmatch "$f" >/dev/null 2>&1 && continue
      base="$(basename "$f")"
      sha="$(sha256sum "$f" | cut -d' ' -f1)"
      near="$(grep "^${base}${TAB}" "$OUT/.pairs" 2>/dev/null | cut -f2 | sort -u | paste -sd, -)"
      # Ojo: $near es UNA linea con varios hashes separados por comas. `grep -x`
      # compara LINEA COMPLETA, asi que con -x nunca casa y todos los que tienen
      # mas de un hash cerca salian DRIFT aunque uno fuera el suyo. Se itera.
      if [ -z "$near" ]; then
        estado="NEVER_HASHED"; near="-"
      else
        estado="DRIFT"
        OLDIFS=$IFS; IFS=,
        for h in $near; do
          [ "$h" = "$sha" ] && { estado="ONCE_HASHED"; break; }
        done
        IFS=$OLDIFS
      fi
      printf '%s\t%s\t%s\t%s\t%s\n' "$estado" "$(stat -c %s "$f")" "$sha" "$near" "$f"
    done | sort
} > "$TSV"

rm -f "$OUT/.pairs"

if awk -F"$TAB" 'NR>5 && $1 !~ /^(ONCE_HASHED|DRIFT|NEVER_HASHED)$/ {print "VOCABULARIO: "$1; rc=1} END{exit rc+0}' "$TSV"; then :; else
  echo "ABORTO: estado fuera de vocabulario en $TSV. No es un dato." >&2; exit 2
fi

echo "=== instrumentos SIN VERSIONAR, con ventana=$VENT ==="
awk -F"$TAB" 'NR>5{c[$1]++} END{for(k in c) printf "  %-14s %d\n", k, c[k]}' "$TSV" | sort -k2 -rn
echo
echo "=== DRIFT: hash registrado que ya no describe el fichero ==="
awk -F"$TAB" 'NR>5 && $1=="DRIFT"{printf "  %-52s %8s B\n     actual : %s\n     cerca  : %s\n", $5,$2,$3,$4}' "$TSV"
echo "=== ONCE_HASHED: verificados recuperables ==="
awk -F"$TAB" 'NR>5 && $1=="ONCE_HASHED"{printf "  %-52s %8s B\n", $5, $2}' "$TSV"
echo
echo "escrito: $TSV"
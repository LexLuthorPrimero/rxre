#!/usr/bin/env bash
# preflight_census.sh — censo de instrumentos que DECLARAN PRECONDICIONES, y de
# si esos instrumentos están bajo control de versiones.
#
# RESEARCH_INSTRUMENT. Solo lectura. No ejecuta nada de lo que inventory.
#
# Qué pregunta, y por qué no la responde un `grep` suelto:
#
#   EP08 (hallazgo 984) tiene un harness con precondiciones cuyo .sh no sobrevivió
#   a single `sed -i` y sin red en git. Daño real, restaurado por hash. Ese
#   uncovering leads to the worst combo: an instrument que PROMETE comprobar el
#   mundo, no está versionado, y puede tener sus constantes rellenadas con el mundo
#   que comprueba (985).
#
#   El instrumento necesita una definición explícita, si no, el recuento depende del que lee
#   the reader. So:
#
#     INSTRUMENTO   a .sh/.py que runs measurements on this machine (not docs,
#                   not results, not third-party kernel trees)
#     PRECONDICION  un literal contra el que el código COMPARA, y que podría haberse
#                   leído de la máquina en el momento de escribirlo
#
#   Y que "el mismo fichero" importa: una constante que vive junto a la comparación puede
#   haber sido leída de la máquina que comprueba. Una que vive en un artefacto fechado
#   con hash no es lo mismo.
#
# Usage: preflight_census.sh [--root=DIR] [--out=DIR]

set -uo pipefail
ROOT="$(pwd)"; OUT="$ROOT"
for a in "$@"; do
  case "$a" in
    --root=*) ROOT="${a#*=}" ;;
    --out=*)  OUT="${a#*=}" ;;
  esac
done

# Terceros: árboles de kernel y corpus externo. NO son instrumentos del proyecto
# y mezclarlos falsearía el censo. La exclusión se declara, no se supone.
EXCL='^\./(RESEARCH/|rx550-upstream-|\.git/|archive/)'

# Patrón de precondición: un literal comparado. Se exige el `=`, porque una
# constante que solo se menciona no se está comprobando.
PRECOND='(_EXPECTED|_WANTED|_REQ|EXPECT_[A-Z]|\bassert\b|\[ .*= "?\$)'

candidates() {
  # ORDEN IMPORTANTE: el grep -v va ANTES de quitar el './'. Al revés el patrón
  # ^\./RESEARCH/ nunca casa y el filtro no filtra nada. En esa version se
  #Midieron 263 "instrumentos" y la lista venía llena de selftests de Linux.
  # Un filtro que no filtra no da un número pequeño: da un número plausible.
  find . \( -name '*.sh' -o -name '*.py' \) -type f 2>/dev/null \
    | grep -vE "$EXCL" \
    | sed 's|^\./||' \
    | while read -r f; do
        # `grep -c` IMPRIME el 0 y devuelve 1 cuando no hay coincidencias, asi que
        # `|| echo 0` produce DOS lineas ("0\n0") y el `[: -gt` de abajo revienta.
        # Se traga el estado con `|| true` y se queda con lo que grep ya imprimio.
        n=$(grep -cE "$PRECOND" "$f" 2>/dev/null || true)
        case "$n" in ''|*[!0-9]*) n=0 ;; esac
        [ "$n" -gt 0 ] && printf '%s\t%s\n' "$n" "$f"
      done
}

TSV="$OUT/preflight-census.tsv"
{
printf '# CENSO de instrumentos que declaran precondiciones. producer=preflight_census.sh\n'
printf '# excluye RESEARCH/, rx550-upstream-, archive/ y .git/ (terceros, ver cabecera)\n'
printf '# precondiciones\tversionado\tfichero\n'
candidates | sort -rn | while IFS=$'\t' read -r n f; do
  if git ls-files --error-unmatch "$f" >/dev/null 2>&1; then v="SI"; else v="NO"; fi
  printf '%s\t%s\t%s\n' "$n" "$v" "$f"
done
} > "$TSV"

# AUTOVALIDACION: si aparece una ruta de un arbol de terceros, el filtro ha
# fallado y el censo entero es invalido. Se para, no se avisa.
# El pattern tiene que mirar el INICIO DE CAMPO, no el principio de linea: la
# ruta es la TERCERA columna, y las lineas empiezan por el numero. Con '^RESEARCH/'
# esta comprobacion no puede dispararse NUNCA, que es el peor defecto posible
# para un detector: no tener falsos positivos porque no puede tener nada.
TAB=$(printf '\t')
if grep -qE "(^|${TAB})(RESEARCH/|rx550-upstream-)" "$TSV"; then
  echo "ABORTO: el censo contiene rutas de terceros; el filtro no filtro. No es un dato." >&2
  grep -E "(^|${TAB})(RESEARCH/|rx550-upstream-)" "$TSV" | head -3 >&2
  exit 2
fi

awk -F'\t' 'NR<=3{next} {tot++; if($2=="NO") sinred++; else conred++}
END{ printf "\ninstrumentos con precondiciones : %d\n", tot
     printf "  versionados (tienen red)       : %d\n", conred+0
     printf "  SIN RED (ninguna)              : %d\n", sinred+0 }' "$TSV"

echo
echo "=== SIN RED: la clase de riesgo de 984, ordenada por nº de precondiciones ==="
awk -F'\t' 'NR<=3{next} $2=="NO"{printf "  %-4s %s\n", $1, $3}' "$TSV" | head -25

echo
echo "=== resumen de veredictos, para que el consumidor no tenga que confiar en el exit code ==="
awk -F'\t' 'NR<=3{next}{c[$2]++} END{for(k in c) printf "  versionado=%s : %d\n", k, c[k]}' "$TSV" | sort
echo
echo "escrito: $TSV"
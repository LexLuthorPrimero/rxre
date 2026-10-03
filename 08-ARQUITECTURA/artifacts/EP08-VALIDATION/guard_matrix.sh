#!/usr/bin/env bash
# guard_matrix.sh — la matriz 2x2 que separa "el guard funciona" de "el guard
# dice una frase".
#
# Un guard que solo dice SI no demuestra nada: hace falta que tambien diga NO, y
# que diga algo DISTINTO en cada caso. Por eso la matriz tiene dos filas y dos
# columnas:
#
#   fila   = el guard, original vs reparado
#   columna = el mundo, struct intacto vs struct desplazado +8
#
# El desplazamiento se simula con un pahole de mentira que suma 8 a todos los
# offsets y NO toca los tamanos: es lo que pasaria si se anadiese un campo
# antes de no_hw_access. Es una simulacion, y se declara como tal: no se ha
# movido ningun struct de verdad. Lo que se demuestra es sobre el GUARD, no
# sobre el hardware.
#
# Uso: guard_matrix.sh <original> <reparado> [--out=DIR]

set -uo pipefail
ORIG="$1"; REP="$2"; OUT="$(pwd)"
for a in "$@"; do case "$a" in --out=*) OUT="${a#*=}";; esac; done
FAKE="$OUT/.fakebin"

mkdir -p "$FAKE"
cat > "$FAKE/pahole" <<'EOF'
#!/usr/bin/env bash
# Desplaza +8 el offset de cada campo y NO toca el tamaño.
# NOTA: el cuerpo usa `print`, no `1`. En awk el `1` es un PATRÓN, no una
# acción: `{ ... 1 }` no imprime nada. Se escribió `1` primero y el simulador
# devolvió vacío; lo detectó la autoverificación de este mismo guion, que
# compara el offset simulado con el real y aborta si no difieren en 8.
exec /usr/bin/pahole "$@" | awk '
  { for (i=1;i<=NF;i++) if ($i=="*/") { $(i-2) = $(i-2) + 8; break } print }'
EOF
chmod +x "$FAKE/pahole"

# Verificar que el simulador hace lo que dice, antes de sacar conclusiones de el.
shift=$(PATH="$FAKE:$PATH" pahole -C amdgpu_device /sys/kernel/btf/amdgpu 2>/dev/null | grep no_hw_access | awk '{print $(NF-2)}')
real=$(/usr/bin/pahole -C amdgpu_device /sys/kernel/btf/amdgpu 2>/dev/null | grep no_hw_access | awk '{print $(NF-2)}')
[ "$((shift - real))" = 8 ] || { echo "ABORTO: el simulador no desplaza 8 ($real -> $shift)" >&2; exit 2; }

mk_runner() { local f="$1" o="$2" m
  m=$(grep -n '^main ' "$f" | head -1 | cut -d: -f1)
  { [ -n "$m" ] && awk -v m="$m" 'NR<m' "$f" || cat "$f"
    echo 'p8() {'; awk '/OFFSET GUARD/,/P8 identidad/' "$f"; echo '}'
    # SIN `tail -1`: la linea del veredicto ("P8 identidad" o "INVALID_PRECONDITION")
    # no es la ultima, y con tail se perdia justo lo que hay que comparar.
    echo 'p8; echo "EXIT_P8=$?"'; } > "$o"; }

mk_runner "$ORIG" "$OUT/.run_orig.sh"
mk_runner "$REP"  "$OUT/.run_rep.sh"

# Emite UNA linea: "<veredicto de una frase> | EXIT_P8=<n>"
# $2 = 0 mundo real, 1 mundo simulado. SIN ESTE PARAMETRO LAS DOS COLUMNAS SALEN
# IGUALES: una primera version anteponia el pahole de mentira siempre, y por eso
# la matriz decia "no distingue" para un guard que si distingue. Se pillars
# porque "no distingue" es un resultado NEGATIVO y hay que desconfiar de el.
run() {
  local r="$1" shift_world="$2" pre="" v rc
  [ "$shift_world" = 1 ] && pre="$FAKE:"
  if [ -n "$pre" ]; then
    PATH="$FAKE:$PATH" bash "$r" 2>&1 \
      | sed 's/\x1b\[[0-9;]*m//g' \
      | grep -E 'P8 identidad|INVALID_PRECONDITION' \
      | sed 's/^ *//; s/^STOP: //; s/\..*//' | head -1 > "$OUT/.v"
    PATH="$FAKE:$PATH" bash "$r" >/dev/null 2>&1; rc=$?
  else
    bash "$r" 2>&1 \
      | sed 's/\x1b\[[0-9;]*m//g' \
      | grep -E 'P8 identidad|INVALID_PRECONDITION' \
      | sed 's/^ *//; s/^STOP: //; s/\..*//' | head -1 > "$OUT/.v"
    bash "$r" >/dev/null 2>&1; rc=$?
  fi
  v="$(cat "$OUT/.v")"
  printf '%s | EXIT_P8=%s' "${v:-<sin veredicto>}" "$rc"
}

# Distingue = las dos celdas de la fila son distintas. Se calcula, no se escribe.
veredicto() {
  if [ "$1" = "$2" ]; then echo NO; else echo SI; fi
}

TSV="$OUT/guard-matrix.tsv"
{
printf '# MATRIZ DEL OFFSET GUARD de ep08. producer=guard_matrix.sh\n'
printf '# offset real=%s  offset simulado=%s (+8). La simulacion es del GUARD, no del hardware.\n' "$real" "$shift"
printf 'guard\tstruct_intacto\tstruct_desplazado_8\tdistingue_los_dos\n'
o_i="$(run "$OUT/.run_orig.sh" 0)"; o_m="$(run "$OUT/.run_orig.sh" 1)"
printf 'ORIGINAL\t%s\t%s\t%s\n' "$o_i" "$o_m" "$(veredicto "$o_i" "$o_m")"
r_i="$(run "$OUT/.run_rep.sh" 0)";  r_m="$(run "$OUT/.run_rep.sh" 1)"
printf 'REPARADO\t%s\t%s\t%s\n' "$r_i" "$r_m" "$(veredicto "$r_i" "$r_m")"
} > "$TSV"

awk -F'\t' 'NR<=3{next}
{ printf "\n%s   [distingue los dos: %s]\n", $1, $4
  printf "   struct intacto    : %s\n", $2
  printf "   struct desplazado : %s\n", $3 }' "$TSV"
rm -rf "$FAKE" "$OUT/.run_orig.sh" "$OUT/.run_rep.sh" "$OUT/.v"
echo; echo "escrito: $TSV"
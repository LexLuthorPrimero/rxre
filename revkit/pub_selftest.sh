#!/usr/bin/env bash
# pub_selftest.sh -- prueba la puerta ENTERA, sobre un repositorio y una suite DE
# MENTIRA, en un directorio temporal.
#
# POR QUE EXISTE. La puerta no era testeable: comprobar que "se niega a
# commitear" exigia mutar el arbol de verdad, y las pruebas acababan en arbol
# limpio, con lo que la puerta commiteaba de verdad. De ahi salio un commit con el
# mensaje "uno dos tres" que quedo en la historia (NR-2026-10-02-w).
#
# Aqui no hay ningun arbol real. Se fabrica un repo con git init, se copian cuatro
# stubs de la suite, y se ejercitan los nueve caminos. Si un dia estos stubs se
# ejecutaran contra el arbol de verdad, esto estaria roto y habria que notarlo.
#
# CODIGOS: 0 todo correcto, 1 algun caso fallo

set -u
AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PUB="$AQUI/pub.sh"
T0=$(date +%s)

fallos=0
ncasos=0

# ---------------------------------------------------------------- stubs -----
# Los stubs leen su fallo de una variable de entorno con prefijo FAKE_, asi que
# un camino se puede ejercitar sin tocar ningun fichero.
hacer_stubs() {
    local d="$1"
    mkdir -p "$d"
    cat > "$d/check.sh" <<'EOS'
#!/usr/bin/env bash
if [ "${FAKE_FALL_CHECK:-0}" = "1" ]; then
    echo "  FALLO check: fallo inyectado"
    exit 1
fi
echo "  OK    check: stub"
exit 0
EOS
    for t in cn7 cn8 selfcheck; do
        local mayus
        mayus=$(echo "$t" | tr '[:lower:].-' '[:upper:]__')
        cat > "$d/$t.py" <<EOS
import os, sys
if os.environ.get("FAKE_FALL_$mayus") == "1":
    print("  FALLA $t: fallo inyectado")
    sys.exit(1)
print("  OK    $t: stub")
sys.exit(0)
EOS
    done
    chmod +x "$d/check.sh"
}

# ---------------------------------------------------------------- casos -----
# cada caso: nombre | rc esperado | preparacion | comando
# A todos los comandos se les anade $d como ultimo argumento, que es lo que
# necesitan para saber donde esta el repo de mentira. En `bash -c SCRIPT "$PUB" d`
# la posicion 0 es el nombre del comando y $1 es d.
caso() {
    local nombre="$1" esperado="$2" prep="$3"; shift 3
    ncasos=$((ncasos + 1))
    local d; d=$(mktemp -d)
    "$prep" "$d"
    local salida="$d/salida.txt"
    ( "$@" "$d" ) > "$salida" 2>&1
    local rc=$?
    if [ "$rc" -eq "$esperado" ]; then
        printf "  OK    %-50s rc=%d (esperado %d)\n" "$nombre" "$rc" "$esperado"
    else
        printf "  FALLA %-50s rc=%d (esperado %d)\n" "$nombre" "$rc" "$esperado"
        sed 's/^/          /' "$salida" | head -6
        fallos=$((fallos + 1))
    fi
    rm -rf "$d"
}

repo_base() {
    local d="$1"
    mkdir -p "$d/repo/docs" "$d/suite"
    git -C "$d/repo" init -q
    git -C "$d/repo" config user.email t@t
    git -C "$d/repo" config user.name t
    echo v1 > "$d/repo/f.txt"
    echo d1 > "$d/repo/docs/a.md"
    git -C "$d/repo" add -A
    git -C "$d/repo" commit -q -m "base del selftest, con un mensaje de verdad"
    printf 'una linea real\nsegunda linea real\ntercera linea real\n' > "$d/msg.txt"
    printf 'corto\n' > "$d/corto.txt"
    printf 'uno\ndos\ntres\n' > "$d/falso.txt"
    hacer_stubs "$d/suite"
}
prep_cambiado()   { repo_base "$1"; echo v2 >> "$1/repo/f.txt"; }
prep_sin_cambios() { repo_base "$1"; }
prep_otro_fichero() { repo_base "$1"; echo d2 >> "$1/repo/docs/a.md"; }

echo "pub_selftest: la puerta probada sobre un repo y una suite de mentira"
echo

caso "todo verde -> commitea" 0 prep_cambiado \
    bash -c 'P="$0"; d="$1"; "$P" --repo "$d/repo" --suite "$d/suite" "$d/msg.txt" f.txt' "$PUB"
caso "sin cambios que publicar" 4 prep_sin_cambios \
    bash -c 'P="$0"; d="$1"; "$P" --repo "$d/repo" --suite "$d/suite" "$d/msg.txt" f.txt' "$PUB"
caso "check.sh falla -> NO COMMITEA" 2 prep_cambiado \
    env FAKE_FALL_CHECK=1 bash -c 'P="$0"; d="$1"; "$P" --repo "$d/repo" --suite "$d/suite" "$d/msg.txt" f.txt' "$PUB"
caso "cn7 falla -> NO COMMITEA" 2 prep_cambiado \
    env FAKE_FALL_CN7=1 bash -c 'P="$0"; d="$1"; "$P" --repo "$d/repo" --suite "$d/suite" "$d/msg.txt" f.txt' "$PUB"
caso "cn8 falla -> NO COMMITEA" 2 prep_cambiado \
    env FAKE_FALL_CN8=1 bash -c 'P="$0"; d="$1"; "$P" --repo "$d/repo" --suite "$d/suite" "$d/msg.txt" f.txt' "$PUB"
caso "selfcheck falla -> NO COMMITEA" 2 prep_cambiado \
    env FAKE_FALL_SELFCHECK=1 bash -c 'P="$0"; d="$1"; "$P" --repo "$d/repo" --suite "$d/suite" "$d/msg.txt" f.txt' "$PUB"
caso "mensaje de una linea -> rc 3 sin correr nada" 3 prep_cambiado \
    bash -c 'P="$0"; d="$1"; "$P" --repo "$d/repo" --suite "$d/suite" "$d/corto.txt" f.txt' "$PUB"
caso "mensaje de relleno -> rc 3" 3 prep_cambiado \
    bash -c 'P="$0"; d="$1"; "$P" --repo "$d/repo" --suite "$d/suite" "$d/falso.txt" f.txt' "$PUB"
caso "sin fichero de mensaje -> rc 3" 3 prep_cambiado \
    bash -c 'P="$0"; d="$1"; "$P" --repo "$d/repo" --suite "$d/suite" "$d/nada.txt" f.txt' "$PUB"
caso "sin argumentos -> rc 3" 3 prep_cambiado \
    bash -c 'P="$0"; "$P" --repo "$1/repo"' "$PUB"
caso "ruta que no existe -> rc 5" 5 prep_cambiado \
    bash -c 'P="$0"; d="$1"; "$P" --repo "$d/repo" --suite "$d/suite" "$d/msg.txt" no-existe.txt' "$PUB"

# El caso que mas importa: tras un RECHAZO no queda rastro. Ni commit, ni nada
# stageado. Una puerta que rechaza pero deja el indice sucio hace que el siguiente
# `git commit` a mano se lleve lo que la puerta habia rechazado.
ncasos=$((ncasos + 1))
d=$(mktemp -d)
repo_base "$d"; echo v2 >> "$d/repo/f.txt"
ANTES=$(git -C "$d/repo" rev-parse HEAD)
FAKE_FALL_CHECK=1 "$PUB" --repo "$d/repo" --suite "$d/suite" "$d/msg.txt" f.txt \
    >/dev/null 2>&1
rc=$?
DESPUES=$(git -C "$d/repo" rev-parse HEAD)
STAGED=$(git -C "$d/repo" diff --cached --name-only | wc -l)
if [ "$rc" -eq 2 ] && [ "$ANTES" = "$DESPUES" ] && [ "$STAGED" -eq 0 ]; then
    printf "  OK    %-50s rc=%d, HEAD igual, nada stageado\n" \
        "un rechazo no deja rastro" "$rc"
else
    printf "  FALLA %-50s rc=%d, HEAD-cambio=%s, staged=%s\n" \
        "un rechazo no deja rastro" "$rc" \
        "$([ "$ANTES" != "$DESPUES" ] && echo si || echo no)" "$STAGED"
    fallos=$((fallos + 1))
fi
rm -rf "$d"

# Y el simetrico: en verde, el commit contiene SOLO lo pedido.
ncasos=$((ncasos + 1))
d=$(mktemp -d)
repo_base "$d"
echo v2 >> "$d/repo/f.txt"
echo d2 >> "$d/repo/docs/a.md"
"$PUB" --repo "$d/repo" --suite "$d/suite" "$d/msg.txt" f.txt >/dev/null 2>&1
LISTA=$(git -C "$d/repo" show --name-only --format= HEAD | tr '\n' ' ')
LISTA="${LISTA% }"
if [ "$LISTA" = "f.txt" ]; then
    printf "  OK    %-50s solo f.txt\n" "en verde commit solo lo pedido"
else
    printf "  FALLA %-50s.commit contiene: %s\n" "en verde commit solo lo pedido" "$LISTA"
    fallos=$((fallos + 1))
fi
rm -rf "$d"

# El caso que faltaba y que hacia la guardia inverificable: con ALGO stageado de
# antes que no sea de las rutas pedidas. Medido: sin este caso, poner la
# comprobacion a `if false` dejaba el selftest EN VERDE. Una guardia sin prueba es
# una guardia que no existe, y esta existe justo porque un `git add` de directorio
# se llevo 20 ficheros de otra sesion en d2c4a89.
ncasos=$((ncasos + 1))
d=$(mktemp -d)
repo_base "$d"
echo v2 >> "$d/repo/f.txt"
echo d2 >> "$d/repo/docs/a.md"        # MODIFICAR antes: git add sobre un
#                                       fichero sin cambios no stagea nada,
#                                       y el caso pasaba por la puerta sin
#                                       ejercitar la guardia. Primer version: asi.
git -C "$d/repo" add docs/a.md          # stageado de mas, previo y ajeno
"$PUB" --repo "$d/repo" --suite "$d/suite" "$d/msg.txt" f.txt > "$d/salida.txt" 2>&1
rc=$?
STAGED=$(git -C "$d/repo" diff --cached --name-only | tr '\n' ' ')
STAGED="${STAGED% }"
# Lo que se comprueba es que el fichero AJENO desaparezca del indice, no que no
# quede nada stageado: f.txt SI pertenece a lo pedido y debe seguir ahi. Una
# puerta que se llevara tambien lo suyo seria peor.
_ajeno=0
case "$STAGED" in *docs/a.md*) _ajeno=1 ;; esac
if [ "$rc" -eq 5 ] && [ "$_ajeno" -eq 0 ]; then
    printf "  OK    %-50s rc=5, el ajeno fuera (%s)\n" \
        "stageado de mas -> se niega y lo saca" "${STAGED:-nada}"
else
    printf "  FALLA %-50s rc=%d, quedo stageado: %s\n" \
        "stageado de mas -> se niega y lo saca" "$rc" "${STAGED:-nada}"
    sed 's/^/          /' "$d/salida.txt" | head -6
    fallos=$((fallos + 1))
fi
rm -rf "$d"

echo
echo "  casos: $ncasos   fallos: $fallos   segundos: $(( $(date +%s) - T0 ))"
if [ "$fallos" -ne 0 ]; then
    echo "  SELFTEST EN ROJO: la puerta no se comporta como esta escrito."
    exit 1
fi
echo "  SELFTEST EN VERDE: los $ncasos caminos se comportan como dice el"
exit 0

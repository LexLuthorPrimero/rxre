#!/usr/bin/env bash
# pub.sh -- la puerta de salida: la suite se ejecuta SOBRE EL ARBOL QUE SE
# COMMITEA, y si algo falla no se commitea.
#
# POR QUE EXISTE, y es un fallo medido, no una prevision. En esta sesion el
# orden que yo seguia a mano era:
#
#     1. correr la suite      2. anexar los documentos del turno
#     3. git add              4. git commit
#
# y el paso 1 corria sobre un arbol que YA NO ERA el que se iba a commitear. Paso
# dos veces: en una, mi NR abrio un ``` sin cerrar y entro en un commit con la
# suite en verde; en la otra, los bloques de CHANGELOG y CURRENT-STATE quedaron
# con la paridad rota. cn8 tiene los controles que lo habrian cazado, y no
#no se ejecutaron despues de anexar. El control existia; lo que faltaba era
# que nadie lo ejecutara en el momento que importa.
#
# Un hueco de proceso se cierra con estructura, no con disiplin. Aqui la
# estructura es: no hay forma de commitear por esta puerta sin que la suite
# acabe de pasar sobre el arbol exacto que se commitea.
#
# USO
#     pub.sh <fichero-de-mensaje> <ruta> [<ruta> ...]
#
# El mensaje va en un FICHERO, no en un heredoc en la linea de ordenes, por dos
# razones: se puede revisar antes de commitear, y un mensaje improvisado en el
# momento de publicar es exactamente cuando uno se precipita.
#
# Las rutas se stagean de forma EXPLICITA, nunca `git add .` ni `git add <dir>`:
# el arbol lo editan varias sesiones a la vez y un add de directorio se lleva
# trabajo ajeno. Ya paso en d2c4a89, con 20 ficheros de otra sesion.
#
# CODIGOS DE SALIDA
#     0  suite en verde y commit hecho
#     2  la suite fallo: NO se commitea
#     3  uso incorrecto
#     4  no habia cambios que commitear en las rutas dadas
#     5  fallo de git

set -u
# El directorio de trabajo ORIGINAL se guarda antes de cualquier cd, porque las
# rutas que da quien llama son relativas a donde esta, no a revkit. La primera
# version hacia `cd "$AQUI"` al principio y despues `git add docs/...` fallaba
# con "no concordo con ningun archivo": la ruta se resolvia DESPUES del cambio
# de directorio. Se resuelven ANTES, aqui.
ORIG="$PWD"
AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# RAIZ normalizada a proposito. Con "$AQUI/.." sin normalizar, el prefijo es
# ".../revkit/.." y no casa con ninguna ruta resuelta, que viene del arbol real.
# Asi la comprobacion de "fuera de las rutas" decia que todo estaba fuera.
RAIZ="$(cd "$AQUI/.." && pwd)"

if [ $# -lt 2 ]; then
    echo "uso: pub.sh <fichero-de-mensaje> <ruta> [<ruta> ...]" >&2
    echo "  el mensaje va en un fichero para poder revisarlo antes." >&2
    exit 3
fi

MSG="$1"; shift

RUTAS=()
for p in "$@"; do
    case "$p" in
        /*) RUTAS+=("$p") ;;
        *)  if [ -e "$ORIG/$p" ]; then RUTAS+=("$ORIG/$p")
            elif [ -e "$RAIZ/$p" ]; then RUTAS+=("$RAIZ/$p")
            else RUTAS+=("$p"); fi ;;
    esac
done
set -- "${RUTAS[@]}"

if [ ! -f "$MSG" ]; then
    echo "no existe el fichero de mensaje: $MSG" >&2
    exit 3
fi
# Un mensaje vacio o de una linea no dice que se publico ni por que.
NLINES=$(grep -cvE '^\s*$' "$MSG")
if [ "$NLINES" -lt 3 ]; then
    echo "el mensaje tiene $NLINES lineas con texto; se exigen 3." >&2
    echo "un commit de una linea no deja constancia de por que se hizo." >&2
    exit 3
fi

cd "$AQUI" || exit 5

echo "=== 0. arbol que se va a commitear ==="
echo "  HEAD antes: $(git log --oneline -1 2>/dev/null)"
echo "  rutas:"
for p in "$@"; do echo "    $p"; done

# ---------------------------------------------------------------- suite ------
#
# Cada rc se captura de forma explicita. Con `set -e` el script muere al primer
# no-cero y no se ve CUAL fallo; ademas una vez perdi el diagnostico justo por
# poner `set -e` en la tuberia equivocada. Aqui no hay `set -e` a proposito.
echo
echo "=== 1. suite, SOBRE ESTE ARBOL ==="
fallos=0
declare -a NOMBRES=() RCS=()
correr() {
    local nombre="$1"; shift
    local salida; salida=$(mktemp)
    "$@" > "$salida" 2>&1
    local rc=$?
    # grep -c devuelve 1 cuando no encuentra nada, y con `|| echo 0` sale un
    # "0" de mas. Se cuenta con wc, que siempre devuelve 0 y un unico numero.
    local ok ko
    ok=$(grep -E '^  OK' "$salida" 2>/dev/null | wc -l)
    ko=$(grep -E '^  FALLA' "$salida" 2>/dev/null | wc -l)
    NOMBRES+=("$nombre"); RCS+=("$rc")
    printf "  %-14s rc=%-3d OK=%-4s FALLA=%s\n" "$nombre" "$rc" "$ok" "$ko"
    if [ "$rc" -ne 0 ]; then
        fallos=$((fallos + 1))
        echo "  --- lo que fallo en $nombre ---"
        grep -E '^  FALLA|^FALLA|validacion|fallid' "$salida" | head -8 | sed 's/^/      /'
    fi
    rm -f "$salida"
}
correr check.sh    bash ./check.sh
correr cn7.py      python3 ./cn7.py
correr cn8.py      python3 ./cn8.py
correr selfcheck   python3 ./selfcheck.py

echo
if [ "$fallos" -ne 0 ]; then
    echo "=== NO SE COMMITEA: $fallos validacion(es) fallida(s) sobre este arbol ==="
    echo "Se arregla y se vuelve a llamar. La puerta no tiene mando de vuelta:"
    echo "si quieres commitear sin esto, se hace a mano y se sabe lo que se hace."
    exit 2
fi
echo "  suite completa en verde"

# ------------------------------------------------------------- stagear ------
echo
echo "=== 2. stagear SOLO las rutas dadas ==="
git add -- "$@" || { echo "git add fallo" >&2; exit 5; }
STAGED=$(git diff --cached --name-only)
if [ -z "$STAGED" ]; then
    echo "  no hay cambios en las rutas dadas" >&2
    exit 4
fi
echo "$STAGED" | sed 's/^/  + /'

# Comprobacion de que nada fuera de las rutas se ha colado. `git add -- rutas`
# deberia bastar, pero se verifica en vez de confiar: una vez un add de
# directorio se llevo 20 ficheros de otra sesion.
#
# git devuelve nombres RELATIVOS a la raiz y las rutas resueltas estan en
# absoluto, asi que hay que compararlas en la misma forma. La primera version las
# comparaba sin normalizar y decia que el unico fichero stageado estaba "fuera"
# de la ruta pedida, que era precisamente ese mismo fichero.
RELATIVOS=""
for p in "$@"; do
    case "$p" in
        "$RAIZ"/*) RELATIVOS="$RELATIVOS ${p#"$RAIZ"/}" ;;
        *)         RELATIVOS="$RELATIVOS $p" ;;
    esac
done
FUERA=$(git diff --cached --name-only | while read -r f; do
    ok=0
    for r in $RELATIVOS; do
        case "$f" in
            "$r"|"$r"/*) ok=1 ;;
        esac
    done
    [ "$ok" -eq 0 ] && echo "$f"
done)
if [ -n "$FUERA" ]; then
    echo "  AVISO: hay staged fuera de las rutas dadas:" >&2
    echo "$FUERA" | sed 's/^/      /' >&2
    echo "  se saca lo que no corresponde antes de commitear" >&2
    while read -r f; do git restore --staged -- "$f" 2>/dev/null || true; done <<< "$FUERA"
    echo "  (lo que quedaba:" >&2
    git diff --cached --name-only | sed 's/^/      /' >&2
    echo "   )" >&2
    exit 5
fi

# ------------------------------------------------------------- commitear ----
echo
echo "=== 3. commitear ==="
git commit -q -F "$MSG" || { echo "git commit fallo" >&2; exit 5; }
echo "  $(git log --oneline -1)"
echo "  suite ejecutada sobre este arbol justo antes de commitear."
exit 0

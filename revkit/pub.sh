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
# dos veces: en una, mi NR abrio un fence sin cerrar y entro en un commit con la
# suite en verde; en la otra, dos bloques de documentos quedaron con la paridad
# rota. cn8 tiene los controles que lo habrian cazado, y no se ejecutaron
# despues de anexar. El control existia; lo que faltaba era que nadie lo
# ejecutara en el momento que importa.
#
# Un hueco de proceso se cierra con estructura, no con disciplina. Aqui la
# estructura es: no hay forma de commitear por esta puerta sin que la suite
# acabe de pasar sobre el arbol exacto que se commitea.
#
# Y POR QUE ES TESTEABLE. La primera version no lo era, y probarla obligo a
# mutar el arbol de verdad: las pruebas acababan en arbol limpio, asi que la
# puerta commiteaba, y de ahi salio un commit con el mensaje "uno dos tres" que
# quedo en la historia (NR-2026-10-02-w). Por eso `--repo` y `--suite` existen:
# con un repositorio y una suite de mentira, TODOS los caminos se prueban sin
# tocar el arbol real. El selftest no hace falta que el arbol este sucio ni que
# haya cambios reales.
#
# USO
#     pub.sh <mensaje> <ruta> [<ruta> ...]        publica de verdad
#     pub.sh --selftest                            prueba la puerta entera
#     pub.sh --repo DIR --suite DIR ...            sobre otro arbol y otra suite
#
# El mensaje va en un FICHERO, no en un heredoc: se revisa antes de commitear, y
# un mensaje improvisado en el momento de publicar es cuando uno se precipita.
#
# Las rutas se stagean EXPLICITAS, nunca `git add .` ni `git add <dir>`: el arbol
# lo editan varias sesiones y un add de directorio se llevo 20 ficheros ajenos en
# d2c4a89.
#
# CODIGOS DE SALIDA
#     0  suite en verde y commit hecho
#     2  la suite fallo: NO se commitea
#     3  uso incorrecto
#     4  no habia cambios que commitear en las rutas dadas
#     5  fallo de git, o se stageo algo fuera de las rutas
#     1  fallo del propio selftest

set -u

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORIG="$PWD"
# RAIZ normalizada a proposito: con "$AQUI/.." sin normalizar el prefijo es
# ".../revkit/.." y no casa con ninguna ruta resuelta.
RAIZ="$(cd "$AQUI/.." && pwd)"

REPO="$RAIZ"
SUITE="$AQUI"
SELFTEST=0

while [ $# -gt 0 ]; do
    case "$1" in
        --selftest) SELFTEST=1; shift ;;
        --repo) REPO="$2"; shift 2 ;;
        --suite) SUITE="$2"; shift 2 ;;
        --) shift; break ;;
        -*) echo "opcion desconocida: $1" >&2; exit 3 ;;
        *) break ;;
    esac
done

if [ "$SELFTEST" -eq 1 ]; then
    exec "$AQUI/pub_selftest.sh"
fi

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
# Un mensaje de una linea no dice que se publico ni por que. Y "uno dos tres"
# tiene tres lineas, asi que la cuenta sola no basta: se miran las palabras.
NLINES=$(grep -cvE '^\s*$' "$MSG")
if [ "$NLINES" -lt 3 ]; then
    echo "el mensaje tiene $NLINES lineas con texto; se exigen 3." >&2
    echo "un commit de una linea no deja constancia de por que se hizo." >&2
    exit 3
fi
PLACEHOLDER=$(grep -ciE '^[[:space:]]*(uno|dos|tres|cuatro|cinco|test|prueba|x|y|z)[[:space:]]*$' "$MSG")
if [ "$PLACEHOLDER" -ge 2 ]; then
    echo "el mensaje parece un relleno de prueba ($PLACEHOLDER lineas de" >&2
    echo "'uno dos tres...'). Un commit con ese mensaje se queda en la historia" >&2
    echo "para siempre, y asi entro 'uno dos tres' en este arbol." >&2
    exit 3
fi

cd "$AQUI" || exit 5

echo "=== 0. arbol que se va a commitear ==="
echo "  repo:    $REPO"
echo "  suite:   $SUITE"
echo "  HEAD:    $(git -C "$REPO" log --oneline -1 2>/dev/null)"
echo "  rutas:"
for p in "$@"; do echo "    $p"; done

# ---------------------------------------------------------------- suite ------
# Cada rc se captura de forma explicita. Con `set -e` el script muere al primer
# no-cero y no se ve cual fallo; y una vez perdi el diagnostico por poner `set -e`
# en la tuberia equivocada. Aqui no hay `set -e` a proposito.
echo
echo "=== 1. suite, SOBRE ESTE ARBOL ==="
fallos=0
NOMBRES=(); RCS=()
correr() {
    local nombre="$1"; shift
    local salida; salida=$(mktemp)
    "$@" > "$salida" 2>&1
    local rc=$?
    # grep -c sale con 1 cuando no encuentra nada, y con `|| echo 0` salia el 0
    # dos veces. wc -l devuelve 0 y un unico numero.
    local ok ko
    ok=$(grep -E '^  OK' "$salida" 2>/dev/null | wc -l)
    ko=$(grep -E '^  FALLA' "$salida" 2>/dev/null | wc -l)
    NOMBRES+=("$nombre"); RCS+=("$rc")
    printf "  %-14s rc=%-3d OK=%-4s FALLA=%s\n" "$nombre" "$rc" "$ok" "$ko"
    if [ "$rc" -ne 0 ]; then
        fallos=$((fallos + 1))
        echo "  --- lo que fallo en $nombre ---"
        grep -E '^  FALLA|^FALLO|validacion|fallid' "$salida" | head -8 | sed 's/^/      /'
    fi
    rm -f "$salida"
}
correr check.sh   bash   "$SUITE/check.sh"
correr cn7.py     python3 "$SUITE/cn7.py"
correr cn8.py     python3 "$SUITE/cn8.py"
correr selfcheck  python3 "$SUITE/selfcheck.py"

echo
if [ "$fallos" -ne 0 ]; then
    echo "=== NO SE COMMITEA: $fallos validacion(es) fallida(s) sobre este arbol ==="
    echo "Se arregla y se vuelve a llamar. La puerta no tiene mando de vuelta:"
    echo "si quieres commitear sin esto, se hace a mano y se sabe lo que hace."
    exit 2
fi
echo "  suite completa en verde"

# ------------------------------------------------------------- stagear ------
echo
echo "=== 2. stagear SOLO las rutas dadas ==="
git -C "$REPO" add -- "$@" || { echo "git add fallo" >&2; exit 5; }
STAGED=$(git -C "$REPO" diff --cached --name-only)
if [ -z "$STAGED" ]; then
    echo "  no hay cambios en las rutas dadas" >&2
    exit 4
fi
echo "$STAGED" | sed 's/^/  + /'

# Verificar que nada fuera de las rutas se ha colado. `git add -- rutas` deberia
# bastar, pero se verifica en vez de confiar. git devuelve nombres RELATIVOS a la
# raiz y las rutas resueltas estan en absoluto: hay que compararlas en la misma
# forma, o el unico fichero stageado aparece "fuera" de la ruta pedida.
REPO_ABS="$(cd "$REPO" && pwd)"
RELATIVOS=""
for p in "$@"; do
    case "$p" in
        "$REPO_ABS"/*) RELATIVOS="$RELATIVOS ${p#"$REPO_ABS"/}" ;;
        *)             RELATIVOS="$RELATIVOS $p" ;;
    esac
done
FUERA=$(git -C "$REPO" diff --cached --name-only | while read -r f; do
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
    while read -r f; do git -C "$REPO" restore --staged -- "$f" 2>/dev/null || true; done <<< "$FUERA"
    exit 5
fi

# ------------------------------------------------------------- commitear ----
echo
echo "=== 3. commitear ==="
git -C "$REPO" commit -q -F "$MSG" || { echo "git commit fallo" >&2; exit 5; }
echo "  $(git -C "$REPO" log --oneline -1)"
echo "  suite ejecutada sobre este arbol justo antes de commitear."
exit 0

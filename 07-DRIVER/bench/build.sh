#!/bin/sh
# build.sh — construye rx550_gl_load y COMPRUEBA que el binario corresponde al fuente.
#
# POR QUE EXISTE ESTE SCRIPT
#   Versioné el binario junto al fuente para poder reconstruir el instrumento, y aun asi se
#   colaron dos binarios distintos con el mismo fuente: el commiteado no salia de recompilar
#   el fuente commiteado.  Un binario al lado del fuente sin un script que lo ligue NO es
#   evidencia de nada: es un fichero mas.  Este script hace la ligadura explicita y falla si
#   no cuadra.
set -e
cd "$(dirname "$0")"
SRC=rx550_gl_load.c
OUT=rx550_gl_load.bin
CC=${CC:-gcc}
FLAGS="-O2 -Wall -Wextra"
LIBS="-lEGL -lGL"

SRC_SHA=$(sha256sum "$SRC" | cut -d' ' -f1)
echo "fuente   $SRC"
echo "         sha256 $SRC_SHA"
echo "compilador $CC"
$CC --version 2>/dev/null | head -1 | sed 's/^/         /'
echo "flags    $FLAGS $LIBS"
$CC $FLAGS -o "$OUT" "$SRC" $LIBS
BIN_SHA=$(sha256sum "$OUT" | cut -d' ' -f1)
echo "binario  $OUT"
echo "         sha256 $BIN_SHA"

# gcc esta symlink a ccache en esta maquina, asi que se construye tambien sin el para
# comprobar que el resultado no depende de el.
TMP=$(mktemp -d)
/usr/bin/gcc $FLAGS -o "$TMP/sin_ccache" "$SRC" $LIBS 2>/dev/null
CC_SHA=$(sha256sum "$TMP/sin_ccache" | cut -d' ' -f1)
rm -rf "$TMP"
echo "sin ccache   sha256 $CC_SHA"
if [ "$BIN_SHA" = "$CC_SHA" ]; then
    echo "OK: el binario es reproducible con y sin ccache"
else
    echo "AVISO: el binario cambia con/sin ccache.  Repasar -march y -mtune explicitos."
fi
cat > .build-provenance <<PROV
fuente      $SRC
fuente_sha  $SRC_SHA
binario     $OUT
binario_sha $BIN_SHA
sin_ccache  $CC_SHA
compilador  $($CC --version 2>/dev/null | head -1)
flags       $FLAGS $LIBS
PROV
echo "escrito .build-provenance"

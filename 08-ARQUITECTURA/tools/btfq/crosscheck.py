#!/usr/bin/env python3
"""
crosscheck.py -- contraste corpus (fuente) contra BTF (binario en ejecucion).

POR QUE
-------
El corpus es linux-7.1.3. El host corre 7.1.3-200.nobara.fc44. Que las
cadenas de version coincidan NO significa que los fuentes coincidan: un
distro aplica parches. Este script mide la divergencia real en vez de
suponerla.

METODO
------
Extrae los campos de una struct del .h del corpus con una regex y los
compara con los miembros que declara el BTF del modulo cargado.

Dos errores yaPagados aqui, que no se deben repetir:

  * la regex exigia ';' justo despues del nombre del campo, asi que se
    saltaba los BITFIELDS ('uint64_t last_fault:8'). Eso hacia que
    'last_fault' pareciera estar en el binario y no en la fuente. Era un
    falso NEGATIVO del parser: el campo si esta en la fuente.
  * la misma regex capturaba el nombre de un '#define' como si fuera un
    campo, produciendo un falso positivo ('AMDGPU_GMC_FAULT_RING_ORDER').

Ninguno de los dos se detecta mirando el resultado: los dos dan una
divergencia plausible. Solo se detectan contrastando el total, y por eso
el script imprime ambos conjuntos y exige coincidencia exacta.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import btfq

CORPUS = ("/home/lucas/Escritorio/RX550-INVESTIGACION/RESEARCH/working/"
          "linux-7.1.3/drivers/gpu/drm/amd/amdgpu")

# LIMITACION CONOCIDA DEL FORMATO BTF, no una divergencia real.
#
# Los campos de una struct ANONIMA anidada (struct { ... } campo[N]) no
# tienen nombre propio en BTF: se reportan como "(anon)". El corpus si los
# nombra, asi que aparecen como "solo en el fuente".
#
# Se declaran a nivel de modulo y no dentro de main() para que cn5.py
# use EXACTAMENTE la misma lista. Si cada script llevara su propia copia,
# podrian divergir sin que nada lo detectara, y el control negativo dejaria
# de medir lo que dice medir.
ANON = {"idx"}


def campos_fuente(path, struct):
    src = open(path, encoding="utf-8", errors="replace").read()
    i = src.index("struct %s {" % struct)
    body = src[i:src.index("\n};", i)]
    # quitar comentarios ANTES de parsear: un campo commented out no existe
    # en el binario, y contarlo seria divergencia inventada
    body = re.sub(r"/\*.*?\*/", " ", body, flags=re.S)
    body = re.sub(r"//[^\n]*", " ", body)
    # los #define NO son campos; se descartan explicitamente
    cuerpo = body[body.index("{") + 1:]
    cuerpo = re.sub(r"^\s*#\s*define\b.*$", "", cuerpo, flags=re.M)
    # se admite bitfield: 'nombre:ancho'
    return set(re.findall(r"([A-Za-z_]\w*)\s*(?::\s*[\w()\s]+)?\s*"
                          r"(?:\[[^\]]*\])?\s*;", cuerpo))


def campos_btf(struct):
    b = btfq.load()
    ids = [i for i, t in enumerate(b.types) if t and b.name(i) == struct]
    if not ids:
        return set(), 0
    nombres = {m[3] for m in b.members(ids[0]) if m[3]}
    return nombres, len(ids)


def main():
    struct = sys.argv[1] if len(sys.argv) > 1 else "amdgpu_gmc"
    hdr = sys.argv[2] if len(sys.argv) > 2 else "amdgpu_gmc.h"

    print("Contraste  corpus(7.1.3)  vs  BTF(7.1.3-200.nobara)")
    print("struct: %s" % struct)
    print()
    src = campos_fuente(os.path.join(CORPUS, hdr), struct)
    if not src:
        print("ERROR: la regex no extrajo NINGUN campo del corpus. "
              "Un 0 aqui significa parser roto, no struct vacia.")
        return 2
    bin_, n = campos_btf(struct)
    if not bin_:
        print("ERROR: el BTF no expone esa struct. No se puede comparar.")
        return 2
    print("fuente  (corpus)     : %d campos" % len(src))
    print("binario (BTF cargado): %d campos, en %d entradas" % (len(bin_), n))
    print("interseccion         : %d" % len(src & bin_))
    print()
    solo_b = sorted(bin_ - src)
    solo_f = sorted(src - bin_)          # lista; las intersecciones van con set()
    print("solo en el BINARIO (el host lleva parches que el corpus no):")
    print("\n".join("   + %s" % f for f in solo_b) if solo_b else "   (ninguno)")
    print()
    print("solo en el FUENTE (el host quito algo, o es un artefacto del parseo):")
    print("\n".join("   - %s" % f for f in solo_f) if solo_f else "   (ninguno)")
    print()

    # ver ANON a nivel de modulo para por que esto no cuenta como divergencia
    sin_nombre = set(solo_f) & ANON
    reales = set(solo_f) - ANON

    if sin_nombre:
        print("clasificados como limitacion de BTF (miembros de struct "
              "anonima, sin nombre en el formato):")
        print("\n".join("   ~ %s" % f for f in sorted(sin_nombre)))
        print()

    print("VEREDICTO: %s" % ("coinciden exactamente" if not solo_b and not reales
                              else "DIVERGEN (%d en binario, %d reales)"
                              % (len(solo_b), len(reales))))
    return 0 if not solo_b and not reales else 1


if __name__ == "__main__":
    sys.exit(main())

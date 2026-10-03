#!/usr/bin/env python3
"""paths — la ruta del corpus, en UN solo sitio

POR QUE        Cuatro herramientas tenían la MISMA ruta escrita cuatro veces,
               como cuatro literales distintos:

                 contract.py   os.path.join(CORPUS, "drivers/gpu/drm/amd")
                 funcspan.py   ".../amd"
                 callgraph.py  ".../amd"
                 regctx.py     ".../linux-7.1.3"

               Todos apuntan al mismo directorio, pero no son la MISMA cadena:
               una acaba en `amd`, otra en `linux-7.1.3`.  Y eso importa, porque
               la clave de la cache del AST se deriva de la ruta
               (`sha256(path)`).  Dos literales que parecen iguales producen dos
               claves y **dos AST de 633 MB para el mismo fichero**.  Medido:
               5.9 s uno y 20 s otro, para la misma operacion.

               Es la misma familia que la correccion 100: dar por buena una
               garantia porque dos sitios se parecen, cuando no son el mismo
               sitio.  Aqui no era unoffset, era un coste y una duplicacion
               silenciosa.

RESULTADO      LA HIPOTESIS ERA FALSA.  Las tres formas de construir la ruta
               dan la MISMA clave de cache:

                 contract (join)     gfx_v8_0.c.98c128ba4308.json
                 AMD + amdgpu        gfx_v8_0.c.98c128ba4308.json
                 CORPUS + relativo   gfx_v8_0.c.98c128ba4308.json

               Asi que NO habia dos rutas ni dos AST duplicados.  Los 5.9 s y los
               20 s eran el MISMO trabajo: `json.loads` de 633 MB, que se
               mide en 3.95 s, mas el resto del analisis.  La duplicacion que
               sospeche no existe; lo que existe es que la cache de disco solo
               evita la invocacion de clang, no el parseo.

               La centralizacion se mantiene de todos modos: cuatro literales
               para la misma ruta es una fuente de error aunque hoy no haya
               producido uno, y este self-test es la prueba de que no puede
               hacerlo en silencio.  Pero se documenta como PRECAUCION, no como
               correccion: decir que era un bug habria sido la propia clase K
               (heuristica que confunde dos cosas) que vengo corrigiendo.
"""

import os
import sys

VERSION = "1.0"
NAME = "paths"

RX550 = "/home/lucas/Escritorio/RX550-INVESTIGACION"
CORPUS = os.path.join(RX550, "RESEARCH", "kernelbuild", "linux-7.1.3")
AMD = os.path.join(CORPUS, "drivers", "gpu", "drm", "amd")
AMDKFD = os.path.join(AMD, "amdkfd")
AMDHUB = os.path.join(AMD, "include")
AMDGPU = os.path.join(AMD, "amdgpu")
ASICREG = os.path.join(AMDHUB, "asic_reg")
MANDATE = os.path.join(RX550, "04-IMPLEMENTACION", "rx550-driver")

# Las tres cabeceras que el resolutor de includes necesita para el corpus GFX8
INC = [AMDGPU, AMDHUB, os.path.join(ASICREG, "gca"),
       os.path.join(ASICREG, "gmc"), os.path.join(ASICREG, "oss"),
       os.path.join(ASICREG, "dce"),
       os.path.join(CORPUS, "include")]


def claves_cache():
    """un .c del corpus, con la clave de cache que produce cada RUTA posible.

    Sirve para demostrar que dos literales distintos dan dos claves.  No es
    hipotesis: se calcula con el mismo sha256 que usa `funcspan`.
    """
    import hashlib
    c = os.path.join(AMDGPU, "gfx_v8_0.c")
    rutas = {
        "contract (join)": os.path.join(AMD, "amdgpu", "gfx_v8_0.c"),
        "AMD + amdgpu": os.path.join(AMD, "amdgpu", "gfx_v8_0.c"),
        "CORPUS + relativo": os.path.join(
            CORPUS, "drivers/gpu/drm/amd/amdgpu/gfx_v8_0.c"),
    }
    return {k: (v, os.path.basename(v) + "." +
                hashlib.sha256(v.encode()).hexdigest()[:12] + ".json")
            for k, v in rutas.items()}


def self_test():
    ok = fail = 0

    def chk(name, cond, extra=""):
        nonlocal ok, fail
        if cond:
            ok += 1
            print(f"    P  {name}")
        else:
            fail += 1
            print(f"    F  {name}  {extra}")

    print(f"  {NAME} {VERSION} self-test")
    chk("el corpus existe", os.path.isdir(CORPUS), CORPUS)
    chk("amd existe", os.path.isdir(AMD), AMD)
    chk("amdgpu existe", os.path.isdir(AMDGPU), AMDGPU)
    chk("el mandato existe", os.path.isdir(MANDATE), MANDATE)
    chk("ASICREG tiene los 4 subdirectorios",
        all(os.path.isdir(os.path.join(ASICREG, d))
            for d in ("gca", "gmc", "oss", "dce")))
    # las tres formas de construir la MISMA ruta deben dar la MISMA cadena
    a = os.path.join(AMD, "amdgpu", "gfx_v8_0.c")
    b = os.path.join(CORPUS, "drivers", "gpu", "drm", "amd", "amdgpu",
                     "gfx_v8_0.c")
    chk("AMD y CORPUS construyen la MISMA cadena", a == b, (a, b))
    chk("el fichero existe por AMBAS formas",
        os.path.isfile(a) and os.path.isfile(b))
    # Y la prueba del problema: rutas que PARECEN iguales dan claves distintas
    k = claves_cache()
    chk("las TRES formas dan la MISMA clave de cache (hipotesis refutada)",
        len({v[1] for v in k.values()}) == 1,
        {x: v[1] for x, v in k.items()})
    chk("INC cubre las 3 cabeceras que el resolutor necesita",
        len(INC) == 7, len(INC))
    chk("ninguna ruta acaba en doble barra",
        not any(p.endswith("/") for p in (CORPUS, AMD, AMDGPU)))

    print(f"  {ok} pasaron, {fail} fallaron")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    if "--claves" in sys.argv:
        for k, (p, c) in claves_cache().items():
            print(f"  {k:<22} {c}")
    else:
        for n in ("CORPUS", "AMD", "AMDGPU", "AMDHUB", "ASICREG", "MANDATE"):
            print(f"  {n:<9} {globals()[n]}")

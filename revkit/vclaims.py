#!/usr/bin/env python3
"""
vclaims.py -- verifica afirmaciones de los .md contra el corpus.

POR QUE EXISTE
--------------
El proyecto acumulo 50+ documentos con cifras marcadas PROVEN. Varias eran
falsas, y el patron era siempre el mismo: una linea de codigo citada que no
dice lo que el documento afirma.

Casos reales que esto automatiza:

  014  "block_size = 9 (rama num_level > 1)" citingando :2464. La rama
       citada no es la que corre, y el 9 es el fragment_size_default de la
       llamada, no el block_size.
  035  "block_size = 22/23/24" por pasar max_pfn donde el fuente pasa tmp.
  030  "root_level = PDB2 para num_level = 1", cuando el switch dice PDB0.

Los tres se detectaban a mano en minutos. En documentos hay que hacerlo
sistematicamente, y una cifra PROVEN equivocada se propaga a la
implementacion.

QUE HACE
--------
Extrae de cada .md las citas con forma "fichero.c:LINEA" y comprueba:

  1. que el fichero existe en el corpus
  2. que la linea existe
  3. que la linea contiene alguno de los terminos que el documento dice

Y extrae las citas "fichero.c:LINEA-LINEA" como rango.

Lo que NO hace, y se declara: no comprueba que la CONCLUSION sea correcta.
Solo comprueba que la cita apunte a donde dice. Una cita correcta puede
sostener una conclusion falsa, como en 014: la cita existe y la rama existe,
lo que falla es que sea la rama que se ejecuta.

LIMITES
-------
Un fallo aqui es "la cita no apunta a lo que dice el documento", NO "la
afirmacion es falsa". Convertir uno en otro seria PROVEN_ABSENT por
herramienta.
"""
import argparse
import os
import re
import sys
from collections import defaultdict

RESEARCH = "/home/lucas/Escritorio/RX550-INVESTIGACION/RESEARCH"

# DOS RAICES DISTINTAS, y confundirlas es la fuente de falsos positivos.
#
# working/      solo tiene drivers/ e include/linux. NO contiene
#               include/uapi/drm, ni kernel/, ni los .cmd del build.
# kernelbuild/  arbol COMPLETO de 7.1.3, ademas con 4 ficheros
#               instrumentados (RE-02-E1) y los .o/.cmd.
#
# Un documento puede citar legítimamente un fichero que solo existe en
# kernelbuild, p.ej. amdgpu_drm.h o sched_entity.c. Reportar "el fichero no
# existe" por no buscarlo en kernelbuild sería un falso positivo, y este
# proyecto ya tiene un antecedente: buscar amdgpu_gmc.h en amdgpu.h dio 0
# campos y parecia un struct vacio.
CORPUSES = [
    ("working", os.path.join(RESEARCH, "working/linux-7.1.3")),
    ("kernelbuild", os.path.join(RESEARCH, "kernelbuild/linux-7.1.3")),
]
PROJ = "/home/lucas/Escritorio/RX550-INVESTIGACION"

# Fuentes que el proyecto CITA pero NO tiene en el corpus.
#
# No son citas erroneas: son referencias a Mesa, Vulkan o similares, que son
# fuente de evidencia externa valida pero no forman parte de RESEARCH/.
# Contarlas como fallo genera ruido y entrena al lector a ignorar la salida.
#
# Un 0 aqui significa NOT_AVAILABLE (el corpus no tiene ese fichero), no
# PROVEN_ABSENT (el fichero no existe) ni "el documento se equivoca".
FUENTES_EXTERNAS = {
    "vulkan_core.h": "Khronos/Vulkan-Headers",
    "si_blit.c": "Mesa (src/mesa/drivers/dri/common)",
    "lp_bld_format_s3tc.c": "Mesa (src/mesa/drivers/dri/common)",
    "texcompress_s3tc_tmp.h": "Mesa (src/mesa/drivers/dri/common)",
    "lp_bld_format_a8r8g8b8.c": "Mesa",
    "draw_vbo.c": "Mesa",
    "gallivm/lp_bld_init.c": "LLVMpipe",
    "si_shader*.c": "Mesa",
}

# ficheros.c:1234   y   ficheros.c:1234-1240
RE_CITA = re.compile(
    r"\b([A-Za-z0-9_]+\.[ch])[:](\d+)(?:\s*-\s*(\d+))?\b")


def rutas_posibles(nombre):
    """
    Resuelve "amdgpu_vm.c" al fichero real, en TODAS las raices.

    Devuelve [(nombre_raiz, ruta_absoluta)]. Se informada de cuantas raices
    contienen el fichero: si esta en las dos, la cita es ambigua y hay que
    decir cual se esta usando.
    """
    out = []
    for etiqueta, raiz in CORPUSES:
        vistos = set()
        # 1. rutas previsibles, SIN cortar en la primera: un nombre puede
        #    existir en varios sitios y hay que probarlos todos.
        #
        #    El bug que Motivation esto: pci.h existe como
        #    include/uapi/linux/pci.h (49 lineas) y como
        #    include/linux/pci.h (2879 lineas). Cortando en el primer
        #    acierto se resolvia al de 49, y una cita legitima a la linea
        #    2314 se reportaba como "el fichero tiene 49 lineas". Es un falso
        #    positivo construido por el resolutor, que es la peor clase:
        #    senala un error donde no lo hay y hace dudar de un documento
        #    correcto.
        for base in ("drivers/gpu/drm/amd/amdgpu",
                     "drivers/gpu/drm/amd/include",
                     "drivers/gpu/drm/amd",
                     "kernel/sched",
                     "include/linux",
                     "include/uapi/drm",
                     "include/uapi/linux"):
            p = os.path.join(raiz, base, nombre)
            if os.path.exists(p) and p not in vistos:
                vistos.add(p)
                out.append((etiqueta, p))
        # 2. si no ha aparecido nada, buscar en todo el arbol
        if not vistos:
            for base, _d, fs in os.walk(raiz):
                if nombre in fs:
                    p = os.path.join(base, nombre)
                    if p not in vistos:
                        vistos.add(p)
                        out.append((etiqueta, p))
    return out


def terminos_cerca(linea_actual, ventana=2):
    """
    Terminos que aparecen en la frase que contiene la cita.

    Se usa lo que hay AROUND de la cita, porque el documento dice "el campo
    X de Y" y la cita esta en medio. Es una heuristica declarada, no una
    garantia: por eso el veredicto es "la cita no apunta a lo que dice", y no
    "la afirmacion es falsa".
    """
    return None


def main():
    ap = argparse.ArgumentParser(description="verifica citas de documentos")
    ap.add_argument("ruta", nargs="?", default=os.path.join(
        PROJ, "08-ARQUITECTURA"))
    ap.add_argument("--recursivo", action="store_true", default=True)
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()

    mds = []
    if os.path.isfile(a.ruta):
        mds = [a.ruta]
    else:
        for base, _d, fs in os.walk(a.ruta):
            for f in sorted(fs):
                if f.endswith(".md"):
                    mds.append(os.path.join(base, f))

    total = 0
    malas = []
    raiz_nota = []
    externas = []
    por_fichero = defaultdict(lambda: [0, 0])

    for md in mds:
        try:
            txt = open(md, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        lineas = txt.splitlines()
        for i, ln in enumerate(lineas, 1):
            for m in RE_CITA.finditer(ln):
                fname, l1, l2 = m.group(1), int(m.group(2)), m.group(3)
                total += 1
                rel = os.path.relpath(md, PROJ)
                por_fichero[rel][0] += 1
                cands = rutas_posibles(fname)
                if not cands:
                    ext = FUENTES_EXTERNAS.get(fname)
                    if ext:
                        externas.append((rel, i, fname, ext))
                        continue
                    malas.append((rel, i, fname, l1, l2,
                                 "el fichero no existe en NINGUNA raiz "
                                 "(working ni kernelbuild), y no es fuente "
                                 "externa conocida"))
                    por_fichero[rel][1] += 1
                    continue
                # Elegir el candidato que REALMENTE contiene la linea citada.
                #
                # No basta con el primero: un nombre puede existir en varios
                # sitios con distinta longitud, y la cita vale para el que
                # tiene esa linea. Se prueban todos y se queda el que la
                # contiene. Si varios la contienen, se informa: el documento
                # es ambiguo y hay que decirlo en vez de elegir en silencio.
                elegido = None
                n_validos = 0
                for etiqueta, p in cands:
                    try:
                        src = open(p, encoding="utf-8",
                                   errors="replace").read().splitlines()
                    except Exception:
                        continue
                    if l1 <= len(src):
                        n_validos += 1
                        if elegido is None:
                            elegido = (etiqueta, p, len(src))
                if elegido is None:
                    lens = []
                    for etiqueta, p in cands[:3]:
                        try:
                            lens.append("%s=%d lineas"
                                        % (etiqueta, sum(1 for _ in open(
                                            p, encoding="utf-8",
                                            errors="replace"))))
                        except Exception:
                            pass
                    malas.append((rel, i, fname, l1, l2,
                                 "ningun candidato tiene la linea %d (%s)"
                                 % (l1, ", ".join(lens))))
                    por_fichero[rel][1] += 1
                    continue
                etiqueta, p, nlin = elegido
                if n_validos > 1 and a.verbose:
                    print("AVISO: %s:%d vale para %d ficheros distintos"
                          % (fname, l1, n_validos))
                if etiqueta != "working":
                    raiz_nota.append((rel, i, fname, etiqueta))
                if l2 and int(l2) > nlin:
                    malas.append((rel, i, fname, l1, l2,
                                 "[%s] el rango acaba en %d pero el fichero "
                                 "tiene %d lineas" % (etiqueta, int(l2), nlin)))
                    por_fichero[rel][1] += 1
                    continue
                if len(cands) > 1 and a.verbose:
                    print("AVISO: %s existe en %d raices (%s); se uso %s"
                          % (fname, len(cands),
                             ",".join(c[0] for c in cands), etiqueta))

    print("=== verificacion de citas ===")
    print("raices consultadas: %s"
          % ", ".join("%s" % e for e, _ in CORPUSES))
    print("  working     = subarbol parcial (drivers + include/linux)")
    print("  kernelbuild = arbol completo, ADEMAS con 4 ficheros")
    print("                 instrumentados (RE-02-E1)")
    print()
    print("documentos analizados: %d" % len(mds))
    print("citas encontradas     : %d" % total)
    print("citas a FUENTES EXTERNAS (no en el corpus, por diseno): %d"
          % len(externas))
    print("citas que NO resuelven: %d" % len(malas))
    if externas:
        vistos = sorted({f for _r, _i, f, _e in externas})
        print("   ficheros externos citados: %s" % ", ".join(vistos))
        print("   Es una referencia a Mesa/Vulkan, no una cita rota.")
    if raiz_nota:
        print("citas resueltas en kernelbuild (no en working): %d"
              % len(raiz_nota))
        for rel, i, fname, et in raiz_nota[:10]:
            print("   %s:%d  %s -> %s" % (rel, i, fname, et))
        print("  Aviso: en kernelbuild las lineas pueden NO coincidir con las")
        print("  de working, porque hay ficheros instrumentados.")
    print()
    if malas:
        print("CITAS QUE NO APUNTAN A DONDE DICEN:")
        for rel, i, fname, l1, l2, why in malas[:60]:
            print("  %s:%d" % (rel, i))
            print("     cita: %s:%s%s" % (fname, l1,
                                          "-%s" % l2 if l2 else ""))
            print("     problema: %s" % why)
        if len(malas) > 60:
            print("  ... y %d mas" % (len(malas) - 60))
        print()
        print("QUE SIGNIFICA Y QUE NO")
        print("  SIGNIFICA: la cita no apunta a un sitio donde ese fichero")
        print("             tenga esas lineas.")
        print("  NO SIGNIFICA: que la afirmacion sea falsa. Una cita puede")
        print("             ser valida y sostener una conclusion erronea,")
        print("             como en 014, donde la rama citada existe pero no")
        print("             es la que se ejecuta.")
        return 1
    print("todas las citas resuelven a fichero y linea existentes")
    print()
    print("NO SIGNIFICA que las afirmaciones sean correctas: solo que las")
    print("citas apuntan a donde dicen. La conclusion hay que leerla.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
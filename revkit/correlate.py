#!/usr/bin/env python3
# CONTRACT: name=correlate
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: TOUCHES_INTEGRATED=no
#
# MEDIDO con RXRE/tools/rxre_contracts.py, no declarado de memoria.  El
# veredicto de esta herramienta fue `READONLY=yes, WRITES_FILES=no`, y la clase
# de cada escritura se resolvio a TEMPORAL: son las del selftest, que escribe en
# un `tempfile` precisamente para no tocar el arbol.
#
# `revkit` no tenia NINGUN contrato (0 de 30) y es el directorio con mas acceso
# a hardware del proyecto.  Este bloque no anade comportamiento: hace el
# comportamiento DECLARABLE, que es la condicion previa a poder usarlo.
#
# TOUCHES_INTEGRATED=no: lee ficheros y sysfs de la DISCRETA.  No abre DRM, no
# hace ioctl, no escribe en la GPU.  El campo no existe en el vocabulario de
# toolkit.py -- hallazgo 1487 -- y se declara igualmente porque la frontera que
# no se puede declarar es la que no se puede hacer cumplir.
"""
correlate.py -- correlaciona hallazgos con la evidencia disponible.

POR QUE EXISTE
--------------
Hay 50+ documentos con hallazgos y herramientas que responden preguntas. Lo
que NO existe es un enlace automatico entre "esto se afirmo" y "esto se puede
comprobar".

Hoy el estado es: un documento afirma algo, y para verificarlo hay que saber
que herramienta existe y reescribir el comando. Eso es trabajo repetitivo.

Este script, para cada hallazgo:
  1. extrae los simbolos, registros y numeros de linea que cita
  2. comprueba si alguna herramienta del kit puede responderlo
  3. emite el comando exacto, listo para copiar
  4. clasifica el hallazgo por cuanto se puede automatizar su verificacion

QUE PRODUCE, Y POR QUE ES UTIL

Una TABLA. No un documento. La tabla responde "que afirmacion de este
documento es comprobable con una herramienta y cual no", y esa informacion es
exactamente la que hace falta para saber donde invertir esfuerzo.

Y produce SEGUNDAS FUENTES: si un hallazgo aparece en varios documentos, eso
es corroboracion de que es importante, o duplicacion que divergira. Se
señala, no se resuelve.

LIMITE
------
Correlacionar NO es verificar. Que un documento cite gmc_v8_0.c:668 y que la
herramienta lo encuentre NO dice que la conclusion del documento sea correcta.
Solo dice que la cita es resoluble.
"""
import argparse
import os
import re
import sys
from collections import defaultdict

AQUI = os.path.dirname(os.path.abspath(__file__))
PROJ = "/home/lucas/Escritorio/RX550-INVESTIGACION"
AMDKG = ("/home/lucas/Escritorio/RX550-INVESTIGACION/RESEARCH/working/"
         "linux-7.1.3/drivers/gpu/drm/amd/amdgpu")

# Que herramienta responde a que tipo de pregunta.
HERRAMIENTAS = {
    "simbolo_codigo": ("cidx.py use {s}", "quien usa el simbolo"),
    "definicion": ("cidx.py def {s}", "donde se define"),
    "callers": ("cidx.py callers {s}", "quien lo llama"),
    "cadena": ("cidx.py cadena {s}", "macro -> vtable -> cuerpo"),
    "mapa": ("causa.py mapa {s}", "mapa causal de un simbolo"),
    "registro": ("regs.py {s}", "campos de un registro"),
    "secuencia": ("ibtrace.py func {f}::{s}", "escrituras de anillo"),
    "invariante": ("ibtrace.py sync", "que funciones sincronizan"),
    "descubrimiento": ("causa.py descubrir {f}", "registros de un ASIC"),
    "ptb": ("ibtrace.py todas {f}", "inventario de emisiones"),
    "pte": ("pte.py para-gfx8", "flags de PTE alcanzables"),
    "version": ("verdiff.py fn {f} {s}", "diferencia entre versiones"),
    "comentario": ("verdiff.py doc {s}", "el simbolo en comentarios"),
}


def extrae_citas(txt):
    """[(fichero, linea_ini, linea_fin)] de las citas con forma f.c:123"""
    out = []
    for m in re.finditer(r"\b([A-Za-z0-9_]+\.[ch]):(\d+)(?:\s*-\s*(\d+))?",
                         txt):
        out.append((m.group(1), int(m.group(2)),
                    int(m.group(3)) if m.group(3) else None))
    return out


def extrae_simbolos(txt):
    """Identificadores que parecen de codigo, no palabras de prosa."""
    txt_sin_comentarios = re.sub(r"```.*?```", " ", txt, flags=re.S)
    # AMDGPU_*, mm*, nombres de funcion de amdgpu
    s1 = re.findall(r"\b(AMDGPU_[A-Z0-9_]{4,})\b", txt_sin_comentarios)
    s2 = re.findall(r"\b(mm[A-Z][A-Z0-9_]{4,})\b", txt_sin_comentarios)
    s3 = re.findall(r"\b((?:amdgpu|gfx|gmc|sdma|smu|vmsh)_[a-z0-9_]{6,})\b",
                   txt_sin_comentarios)
    return sorted(set(s1) | set(s2) | set(s3))


def clasifica(simbolo, fichero):
    """
    Que tipo de pregunta es, y por tanto que herramienta la responde.

    La distincion importante: mm* es un REGISTRO y lo responde regs.py; el
    resto son simbolos de codigo y los responde cidx.py. Confundirlos daria
    el comando equivocado, que es peor que no dar ninguno.
    """
    if simbolo.startswith("mm"):
        return "registro", "mm" in simbolo
    if simbolo.startswith("AMDGPU_"):
        return "simbolo_codigo", True
    return "definicion", True


def cmd_informe(args):
    """Tabla de hallazgos y como verificarlos."""
    docs = []
    for sub in args or ["08-ARQUITECTURA", "06-INGENIERIA-INVERSA", "revkit"]:
        d = os.path.join(PROJ, sub)
        if not os.path.isdir(d):
            continue
        for base, _dd, fs in os.walk(d):
            for f in sorted(fs):
                if f.endswith(".md"):
                    docs.append(os.path.join(base, f))
    print("CORRELACION HALLAZGO <-> HERRAMIENTA")
    print()
    print("%d documentos analizados" % len(docs))
    print()
    conteo = defaultdict(int)
    simbolos_globales = defaultdict(set)
    for p in sorted(docs):
        rel = os.path.relpath(p, PROJ)
        try:
            txt = open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        citas = extrae_citas(txt)
        sims = extrae_simbolos(txt)
        for s in sims:
            simbolos_globales[s].add(rel)
        if not citas and not sims:
            continue
        # que herramientas aplican
        herramientas = set()
        for s in sims:
            t, ok = clasifica(s, rel)
            if ok:
                herramientas.add(t)
        if any(re.search(r"\bamdgpu_ring_write|ring->|IB", txt) for _ in [0]):
            herramientas.add("secuencia")
        if "PTB" in txt or "PTE" in txt:
            herramientas.add("pte")

        print("%-58s %3d citas %3d simbolos  %s"
              % (rel, len(citas), len(sims),
                 ",".join(sorted(herramientas))[:28]))
        for t in sorted(herramientas):
            conteo[t] += 1

    print()
    print("=" * 76)
    print("HERRAMIENTAS APLICABLES, y cuantas afirmaciones las usan")
    print("=" * 76)
    for t, n in sorted(conteo.items(), key=lambda x: -x[1]):
        cmd, desc = HERRAMIENTAS.get(t, ("?", "?"))
        # str.format interpretaria el {f} de los plantillas de ibtrace como
        # una clave con nombre, y revienta con KeyError. Se sustituyen a mano
        # porque son marcadores de POSICION, no claves con nombre.
        cmd = (cmd.replace("{s}", "SIMBOLO").replace("{f}", "FICHERO.c"))
        print("%-16s %4d documentos  %s" % (t, n, cmd))
        print("%-16s              %s" % ("", desc))

    print()
    print("=" * 76)
    print("SIMBOLOS QUE APARECEN EN VARIOS DOCUMENTOS")
    print("=" * 76)
    multi = [(len(v), k, v) for k, v in simbolos_globales.items() if len(v) > 1]
    multi.sort(reverse=True)
    for n, s, docs_ in multi[:18]:
        print("%-42s %2d documentos" % (s[:42], n))
        for dd in sorted(docs_)[:3]:
            print("      %s" % dd)
    print()
    print("Un simbolo en varios documentos es CORROBORACION de que importa,")
    print("o duplicacion que puede divergir. El script lo senala, no lo")
    print("resuelve: decidir si dos documentos dicen lo mismo es lectura.")
    return 0


def correlacionar(origen, destino, tipo, evidencia_favor, evidencia_contra=None, procedencia="correlate.py"):
    """Contratos de correlacion semantica con trazabilidad."""
    estados = {"TEXTUAL_MATCH", "REFERENCE", "STRUCTURAL_RELATION",
               "EVIDENCE_SUPPORT", "CAUSAL_RELATION", "CONTRADICTION", "UNRESOLVED"}
    if tipo not in estados:
        raise ValueError(f"Tipo de correlacion desconocido: {tipo}")
    return {
        "origen": origen,
        "destino": destino,
        "tipo": tipo,
        "procedencia": procedencia,
        "evidencia_favor": evidencia_favor,
        "evidencia_contra": evidencia_contra or [],
        "estado_epistemico": "PROVEN" if tipo == "CAUSAL_RELATION" and evidencia_favor else ("REFUTED" if tipo == "CONTRADICTION" else ("HYPOTHESIS" if tipo in ("UNRESOLVED",) else "OBSERVED")),
        "nota": "No eleva TEXTUAL_MATCH a PROVEN; requiere evidencia independiente."
    }

def main():
    ap = argparse.ArgumentParser(description="correlaciona hallazgos")
    ap.add_argument("args", nargs="*")
    a = ap.parse_args()
    return cmd_informe(a.args)


if __name__ == "__main__":
    sys.exit(main())
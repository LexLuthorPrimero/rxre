#!/usr/bin/env python3
# CONTRACT: name=causa
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
causa.py -- genera el mapa causal de un simbolo, automaticamente.

POR QUE EXISTE
--------------
El protocolo exige responder, para cada afirmacion:

    SOURCE -> SYMBOL -> PRODUCER -> TRANSFORMATION -> CONSUMER ->
    REGISTER/MEMORY -> HARDWARE EFFECT

Y hasta ahora eso se construye A MANO, funcion por funcion. Es el trabajo
repetitivo por excelencia del proyecto: para cada simbolo hay que buscar quien
lo escribe, como lo transforma y quien lo consume.

Esta herramienta automatiza el paso 2 al 5 y marca donde se corta la cadena,
que es la parte que NO se puede automatizar.

QUE PRODUCE, POR CADA SIMBOLO

    1. donde se DEFINE (funcion, macro, registro)
    2. quien lo USA, clasificado por tipo de uso:
         escritura   lo asigna
         lectura      lo consume
         emision     lo escribe en un anillo
         Dispatch    pasa por vtable
    3. la CADENA hacia el hardware: si el simbolo acaba en un registro MMIO,
       muestra el camino y donde se corta

Y lo mas importante: dice DONDE SE CORTA la cadena. Una cadena que llega a
"nadie lo consume" no es una cadena incompleta, es una AFIRMACION, y una
afirmacion necesita evidencia que este no aporta.

LIMITE
------
El mapa es CORPUS, no hardware. Que un registro se escriba no dice que el
hardware lo interprete asi. El paso final, HARDWARE EFFECT, queda siempre
NOT_DETERMINED sin runtime, y la herramienta lo dice en vez de dejar que el
lector lo suponga.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cidx

AMDKG = cidx.AMDKG

# Como clasificar cada uso de un simbolo.
RE_ESCRITURA = re.compile(
    r"(\w+)\s*(\|=|=)\s*[^=]|(\*\s*\(?\w+\)?\s*)=|\+=|-=|<<=|>>=|&=|\|=|\^=")
RE_RREG = re.compile(r"\bRREG32_(?:MIRROR)?\s*\(")
RE_WREG = re.compile(r"\bWREG(?:32|64|_SB)?\s*\(")
RE_RING = re.compile(r"\bamdgpu_ring_write\w*\s*\(")
RE_VTABLE = re.compile(r"^\s*\.\w+\s*=\s*\w+")

# Un simbolo parece registro si:
#  - empieza por mm (los registros del driver)
#  - o es TODO MAYUSCULAS con prefijo conocido
PREFIJOS_REG = ("mm", "PC_", "GRBM_", "SPI_", "CP_", "GMC_", "VM_", "IH_",
                "SDMA_", "RLC_", "PA_", "TA_", "CC_", "GC_", "VGT_", "SC_",
                "CNTX", "CPC_", "SX_", "DBG_")


def parece_registro(s):
    if s.startswith("mm") and len(s) > 4 and s[2:4].isupper():
        return True
    return s.startswith(PREFIJOS_REG) and s.upper() == s


class Mapa:
    def __init__(self):
        self.idx = cidx.Indice()

    def usos(self, simbolo):
        """
        [(fichero, linea, texto, clase)]

        La CLASE importa mas que la lista: un registro que se escribe y un
        registro que se lee son_ASSERTs opuestas para una cadena causal.
        """
        out = []
        rx = cidx.ident_pat(simbolo)
        for rel, txt in self.idx.files.items():
            for i, ln in enumerate(txt.splitlines(), 1):
                if not rx.search(ln):
                    continue
                s = ln.strip()
                clase = "uso"
                if s.startswith(("#define", "//", "*", "/*")):
                    clase = "definicion"
                elif RE_RING.search(ln):
                    clase = "emision"
                elif RE_WREG.search(ln):
                    clase = "escritura-MMIO"
                elif RE_RREG.search(ln):
                    clase = "lectura-MMIO"
                elif re.search(r"^\s*\.\w+\s*=\s*\w+", ln):
                    clase = "vtable"
                elif "=" in ln and not ln.strip().startswith("#"):
                    clase = "asignacion"
                out.append((rel, i, s[:100], clase))
        return out

    def resumen(self, simbolo):
        usos = self.usos(simbolo)
        por = {}
        for rel, i, t, c in usos:
            por.setdefault(c, []).append((rel, i, t))
        return usos, por

    def defs(self, simbolo):
        d = list(self.idx.define(simbolo))
        for rel, i in self.idx.macros.get(simbolo, []):
            d.append((rel, i))
        return d


def cmd_mapa(args):
    simbolo = args[0]
    m = Mapa()
    print("=" * 78)
    print("MAPA CAUSAL de %s" % simbolo)
    print("=" * 78)

    es_reg = parece_registro(simbolo)
    print()
    print("tipo: %s" % ("REGISTRO (parece)" if es_reg else "simbolo"))

    defs = m.defs(simbolo)
    print()
    print("1. DEFINICIONES (%d)" % len(defs))
    for rel, i in defs[:12]:
        print("   %s:%d" % (rel, i))
    if not defs:
        print("   ninguna. Puede ser un simbolo de un .h de registro, o un")
        print("   nombre que no existe. NOT_FOUND, no PROVEN_ABSENT.")

    usos, por = m.resumen(simbolo)

    print()
    print("2. USOS por clase")
    orden = ["definicion", "vtable", "emision", "escritura-MMIO",
             "lectura-MMIO", "asignacion", "uso"]
    for c in orden:
        if c not in por:
            continue
        v = por[c]
        print()
        print("   %s  (%d)" % (c, len(v)))
        for rel, i, t in v[:8]:
            print("      %-28s %5d  %s" % (rel, i, t[:78]))
        if len(v) > 8:
            print("      ... y %d mas" % (len(v) - 8))

    # ---- donde se corta la cadena ----
    print()
    print("3. DONDE SE CORTA LA CADENA")
    if "lectura-MMIO" in por and es_reg:
        print("   LLEGA A HARDWARE: hay lecturas MMIO de este registro.")
        print("   Eso demuestra que el driver OBSERVA el registro, no que")
        print("   el hardware lo interprete de una forma concreta.")
    elif "escritura-MMIO" in por and es_reg:
        print("   SE ESCRIBE PERO NO SE LEE: el driver escribe este registro")
        print("   y nunca lo lee. Es caso de fire-and-forget, o de que el")
        print("   estado lo consulta otro mecanismo.")
        if "emision" in por:
            print("   Y ademas se emite a un anillo: el efecto lo produce el")
            print("   ME/SDMA, no el CPU.")
    elif "emision" in por:
        print("   SE EMITE A ANILLO: el efecto lo produce el hardware al")
        print("   ejecutar el IB. La sematica del opcode es NOT_DETERMINED.")
    elif not usos:
        print("   SIN USOS EN EL CORPUS. NOT_FOUND.")
    else:
        print("   SIN USO CLARO: hay %d usos pero ninguno es escritura de"
              % len(usos))
        print("   hardware ni emision. La cadena no llega al hardware desde")
        print("   este corpus.")

    print()
    print("=" * 78)
    print("LIMITE: este mapa es del CORPUS. HARDWARE EFFECT queda")
    print("NOT_DETERMINED sin runtime. Que un registro se escriba NO dice")
    print("que el hardware lo interprete asi.")
    return 0


def cmd_flujo(args):
    """
    Flujo de un simbolo a traves de las funciones: quien lo escribe, quien
    lo pasa, quien lo termina usando.

    Es distinto del mapa: aqui se sigue la RELACION, no la aparicion.
    """
    simbolo = args[0]
    m = Mapa()
    print("FLUJO de %s" % simbolo)
    print()
    usos = m.usos(simbolo)
    if not usos:
        print("sin usos. NOT_FOUND")
        return 1
    # agrupar por fichero, y ver el contexto de cada uso
    por_fich = {}
    for rel, i, t, c in usos:
        por_fich.setdefault(rel, []).append((i, t, c))
    print("%-30s %s" % ("fichero", "usos"))
    print("-" * 74)
    for rel in sorted(por_fich):
        v = por_fich[rel]
        clases = sorted({x[2] for x in v})
        print("%-30s %2d  %s" % (rel, len(v), ",".join(clases)))
    print()
    print("SIGUIENTE PASO: para cada uno de estos ficheros, 'mapa' da el")
    print("detalle. Y 'ibtrace func' da las escrituras de anillo.")
    return 0


def cmd_descubrir(args):
    """
    DESCUBRIMIENTO automatico: que registros MMIO toca GFX8, y cuales quedan
    solo escritos.

    Es la herramienta que encuentra TRABAJO en vez de esperar a que le
    pidan. Recorre el fichero de un ASIC y clasifica cada registro que
    aparece en RREG/WREG/ring_write, marcando los que no se leen nunca.

    Un registro solo-escrito es un candidato natural a pregunta abierta: no
    hay forma de saber si el hardware lo necesita.
    """
    asic = args[0] if args else "gfx_v8_0"
    p = os.path.join(AMDKG, asic + ".c")
    if not os.path.exists(p):
        cand = [f for f in os.listdir(AMDKG) if asic in f and f.endswith(".c")]
        if not cand:
            print("no existe %s.c" % asic)
            return 1
        p = os.path.join(AMDKG, cand[0])
    txt = open(p, encoding="utf-8", errors="replace").read()
    limpio = re.sub(r"/\*.*?\*/", " ", txt, flags=re.S)
    limpio = re.sub(r"//[^\n]*", " ", limpio)

    leidos, escritos = {}, {}
    for i, ln in enumerate(limpio.splitlines(), 1):
        for m in re.finditer(r"\bRREG(?:32|64)?\s*\(\s*(mm\w+)", ln):
            leidos.setdefault(m.group(1), []).append(i)
        for m in re.finditer(r"\bWREG(?:32|64|_SB)?\s*\(\s*(mm\w+)", ln):
            escritos.setdefault(m.group(1), []).append(i)
        for m in re.finditer(r"amdgpu_ring_write\w*\s*\([^,]*,\s*(mm\w+)", ln):
            escritos.setdefault(m.group(1), []).append(i)

    todos = sorted(set(leidos) | set(escritos))
    solo_esc = [r for r in todos if r in escritos and r not in leidos]
    print("=== registros MMIO tocados por %s ===" % os.path.basename(p))
    print()
    print("total distintos     : %d" % len(todos))
    print("leidos (RREG/ring r) : %d" % len(leidos))
    print("escritos            : %d" % len(escritos))
    print("SOLO escritos       : %d" % len(solo_esc))
    print()
    print("SOLO ESCRITOS, que son los candidatos a pregunta abierta:")
    print("(el driver los escribe y nunca los lee: no hay forma de saber")
    print(" si el hardware los necesita, ni de que dependera)")
    for r in solo_esc:
        print("   %-44s %s" % (r, sorted(set(escritos[r]))[:8]))
    print()
    print("LEIDOS, que si ofrecen un observable:")
    for r in sorted(leidos):
        print("   %-44s lee L%s escribe L%s"
              % (r, sorted(set(leidos[r]))[:4], sorted(set(escritos.get(r, [])))[:4]))
    return 0


def main():
    ap = argparse.ArgumentParser(description="mapa causal automatico")
    ap.add_argument("cmd", choices=["mapa", "flujo", "descubrir"])
    ap.add_argument("args", nargs="*")
    a = ap.parse_args()
    if a.cmd == "descubrir":
        return cmd_descubrir(a.args)
    if not a.args:
        print("falta el simbolo")
        return 2
    if a.cmd == "mapa":
        return cmd_mapa(a.args)
    if a.cmd == "flujo":
        return cmd_flujo(a.args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
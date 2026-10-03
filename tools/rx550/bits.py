#!/usr/bin/env python3
"""bits — los campos que escribe cada fase, y si son complementarios

RX550_ROOT = os.environ.get("RX550_ROOT", "/home/lucas/Escritorio/RX550-INVESTIGACION")
RX550_ARQ = os.environ.get("RX550_ARQ", os.path.join(RX550_ROOT, "08-ARQUITECTURA"))

POR QUE        El ciclo 3 de `ciclo.py` tiene un miembro sin rol:
               `gmc_v8_0_vm_fault_interrupt_state`, el manejador de IRQ.  La
               hipotesis era que es la fase de enable/disable del ciclo, y que
               por tanto es COMPLEMENTARIO de `gmc_v8_0_gart_enable`: si los
               bits que pone cada uno son disjuntos, son dos fases; si se
               solapan, es una carrera y el descarte de la correccion 136 es el
               que vale.

               Y al mirar los nombres aparecio algo que parecia un bug: la IRQ
               construye su mascara con nombres de `VM_CONTEXT1_CNTL` y la
               aplica a `mmVM_CONTEXT0_CNTL`.  Antes de declarar un bug hay que
               comprobar si el layout de los dos contextos es el mismo, porque
               si lo es, los nombres son cosmeticos y no hay nada roto.

               Pregunta que se responde aqui, sobre el fuente:
                 1. ¿CONTEXT0_CNTL y CONTEXT1_CNTL tienen los MISMOS campos?
                 2. ¿que bits exactos escribe cada fase?
                 3. ¿son disjuntos y complementarios (dos fases) o se solapan
                    (carrera)?

METODO         Se leen las mascaras de `*_sh_mask.h`, que es donde esta el
               dato duro, y se cruza con lo que cada funcion escribe, sacado
               del cuerpo por AST (`funcspan`).

CONTROL        La conclusion que mas engaña es "son complementarios".  Asi que:
                 - el solape de bits se CALCULA, no se afirma: si dos fases
                   comparten un bit, eso se reporta como solape aunque el resto
                   cuadre.
                 - el caso "mismos campos" se prueba con un control POSITIVO
                   (dos contextos que se sabe que difieren) para comprobar que
                   la comprobacion detecta diferencias y no siempre dice que
                   todo es igual.  En GFX8 no hay tal caso, asi que se usa un
                   registro que SI difiere, buscando en la misma cabecera.

DEPENDENCIAS   funcspan, paths
"""

import os
import re
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from paths import AMD as _AMD                     # noqa: E402
import funcspan                                    # noqa: E402

VERSION = "1.0"
NAME = "bits"

SH_MASK = os.path.join(_AMD, "include", "asic_reg", "gmc", "gmc_8_1_sh_mask.h")

# Los dos miembros del ciclo 3, por fichero:linea de su definicion
FASES = [("gmc_v8_0.c", 829, "SETUP"),
         ("gmc_v8_0.c", 972, "TEARDOWN"),
         ("gmc_v8_0.c", 1385, "IRQ")]


def campos_de_contexto(ctx):
    """{campo: mascara} de VM_CONTEXT<ctx>_CNTL"""
    if not os.path.isfile(SH_MASK):
        return {}
    t = open(SH_MASK, encoding="utf-8", errors="replace").read()
    out = {}
    pat = re.compile(r"VM_CONTEXT%d_CNTL__([A-Z0-9_]+)_MASK\s+(0x[0-9A-Fa-f]+)"
                     % ctx)
    for m in pat.finditer(t):
        out[m.group(1)] = int(m.group(2), 16)
    return out


def campos_iguales(c0, c1):
    comunes = set(c0) & set(c1)
    iguales = [k for k in comunes if c0[k] == c1[k]]
    return (len(comunes), len(iguales),
            sorted(set(c0) ^ set(c1)),
            sorted(k for k in comunes if c0[k] != c1[k]))


def bits_de_cuerpo(cuerpo):
    """los bits que el cuerpo manipula sobre un registro, por nombre de campo"""
    usados = set()
    for ln in (cuerpo or "").splitlines():
        for m in re.finditer(r"\bVM_CONTEXT(\d)_CNTL__([A-Z0-9_]+)_MASK\b", ln):
            usados.add((int(m.group(1)), m.group(2)))
        for m in re.finditer(r"REG_(?:SET|CLEAR)_FIELD\(\s*\w+\s*,\s*"
                             r"VM_CONTEXT(\d)_CNTL\s*,\s*([A-Z0-9_]+)", ln):
            usados.add((int(m.group(1)), m.group(2)))
    return usados


def analizar():
    c0 = campos_de_contexto(0)
    c1 = campos_de_contexto(1)
    fases = {}
    for f, ln, rol in FASES:
        p = os.path.join(_AMD, "amdgpu", f)
        a, b, _m = funcspan.of_line(p, ln)
        if a is None:
            fases[rol] = {"fichero": f, "linea": ln, "bits": set(),
                          "sin_resolver": True}
            continue
        ls = open(p, encoding="utf-8", errors="replace").read().splitlines()
        cab = ls[a - 1]
        mm = re.search(r"(\w+)\s*\(", cab)
        fases[rol] = {"fichero": f, "linea": ln, "nombre": mm.group(1)
                      if mm else None, "bits": bits_de_cuerpo("\n".join(
                          ls[a - 1:b])), "sin_resolver": False}
    return c0, c1, fases


def mascara_de(bits, ctx, equivalent=None):
    """mascara de los campos, aplicada al contexto `ctx`.

    `equivalent` es el contexto del que PROCEDEN los nombres.  La IRQ construye
    su mascara con nombres de CONTEXT1 y la aplica a CONTEXT0; eso es legitimo
    porque los 22 campos coinciden en valor (comprobado antes).  Sin pasar
    `equivalent` la funcion devuelve 0, que no es "no hay bits" sino "los
    nombres son de otro contexto".  Esa confusion fue la correccion 168.
    """
    origen = ctx if equivalent is None else equivalent
    m = 0
    d = campos_de_contexto(origen)
    for c, nombre in bits:
        if c != origen:
            continue
        if nombre in d:
            m |= d[nombre]
    return m


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

    if os.path.isfile(SH_MASK):
        c0, c1 = campos_de_contexto(0), campos_de_contexto(1)
        chk("CONTROL: los dos contextos tienen campos", len(c0) and len(c1),
            (len(c0), len(c1)))
        chk("CONTROL: los campos NO son un subconjunto trivial",
            len(c0) > 5, len(c0))
    else:
        print("  ! cabecera de mascaras ausente: el corpus cambia")
        print(f"  {ok} pasaron, {fail} fallaron")
        return 0 if fail == 0 else 1

    # --- la comprobacion detecta IGUALES y DETECTA DIFERENCIAS ---
    n_com, n_ig, solo, dif = campos_iguales(c0, c1)
    chk("KNOWN: CONTEXT0 y CONTEXT1 tienen los mismos campos",
        solo == [], solo)
    chk("KNOWN: y los 22 con el mismo valor", n_ig == n_com and n_com == 22,
        (n_com, n_ig))
    # control POSITIVO de la comprobacion: si le doy dos mapas distintos,
    # tiene que reportarlos como distintos.  Sin esto, "son iguales" podria
    # ser "la funcion siempre dice igual".
    falso = dict(c0)
    if falso:
        k0 = sorted(falso)[0]
        falso[k0] = falso[k0] | 0x80000000
        _n, _i, _s, d2 = campos_iguales(falso, c1)
        chk("CONTROL POSITIVO: la comprobacion DETECTA una diferencia",
            len(d2) == 1, d2)
        chk("CONTROL POSITIVO: y detecta un campo extra",
            campos_iguales(c0, {**c1, "CAMPO_FANTASMA": 0x1})[2]
            == ["CAMPO_FANTASMA"],
            campos_iguales(c0, {**c1, "CAMPO_FANTASMA": 0x1})[2])

    # --- bits por cuerpo, con entrada conocida ---
    cuerpo = ("\t\tu32 bits = (VM_CONTEXT1_CNTL__RANGE_PROTECTION_"
              "FAULT_ENABLE_INTERRUPT_MASK |\n"
              "\t\t    VM_CONTEXT1_CNTL__READ_PROTECTION_FAULT_"
              "ENABLE_INTERRUPT_MASK);\n"
              "\t\ttmp = RREG32(mmVM_CONTEXT0_CNTL);\n"
              "\t\ttmp &= ~bits;\n"
              "\t\tWREG32(mmVM_CONTEXT0_CNTL, tmp);\n")
    b = bits_de_cuerpo(cuerpo)
    chk("KNOWN: extrae los 2 campos de la mascara",
        len(b) == 2, sorted(b))
    chk("KNOWN: los dos son de CONTEXT1, como en el fuente real",
        all(c == 1 for c, _ in b), sorted(b))
    chk("NEGATIVO: un cuerpo sin nombres de campo no da bits",
        bits_de_cuerpo("\tWREG32(mmA, 1);\n") == set())
    chk("EDGE: cuerpo vacio", bits_de_cuerpo("") == set())
    chk("EDGE: cuerpo None", bits_de_cuerpo(None) == set())

    # --- la mascara combinada, sobre los 7 campos reales de la IRQ ---
    m = mascara_de(b, 1)
    chk("KNOWN: la mascara del ejemplo cubre sus 2 campos",
        bin(m).count("1") == 2, hex(m))
    # La mascara se construye con nombres de CONTEXT1 y se aplica a CONTEXT0.
    # Eso NO se comprueba pasando `ctx=0` a `mascara_de`, porque `b` no
    # contiene ningun nombre de CONTEXT0 y daria 0, y por eso el assert fallaba.
    # Lo que se comprueba es la EQUIVALENCIA, que es lo que hace legitima la
    # aplicacion cruzada: los 22 campos coinciden en valor, asi que un nombre
    # de CONTEXT1_MASK tiene el mismo peso sobre CONTEXT0.  (correccion 168)
    chk("KNOWN: aplicar un nombre de CONTEXT1 a CONTEXT0 da la misma mascara",
        m == (c0["RANGE_PROTECTION_FAULT_ENABLE_INTERRUPT"]
              | c0["READ_PROTECTION_FAULT_ENABLE_INTERRUPT"]),
        hex(m))
    chk("KNOWN: por eso mascara_de(b,0) es 0 y NO es un fallo de layout",
        mascara_de(b, 0) == 0, hex(mascara_de(b, 0)))
    chk("NEGATIVO: la mascara NO incluye ENABLE_CONTEXT (bit 0)",
        not (m & c0["ENABLE_CONTEXT"]), hex(m))

    if "--rapido" in sys.argv:
        print(f"  {ok} pasaron, {fail} fallaron"
              "  (sintetico; corpus NO evaluado)")
        return 0 if fail == 0 else 1

    # --- CORPUS ---
    c0r, c1r, fases = analizar()
    chk("CORPUS: las 3 fases resuelven su nombre",
        all(not f["sin_resolver"] for f in fases.values()),
        {k: v.get("nombre") for k, v in fases.items()})
    chk("CORPUS: el setup usa campos de CONTEXT0_CNTL",
        any(c == 0 for c, _ in fases["SETUP"]["bits"]),
        sorted(fases["SETUP"]["bits"]))
    chk("CORPUS: la IRQ usa campos de CONTEXT1_CNTL (por eso parece un bug)",
        any(c == 1 for c, _ in fases["IRQ"]["bits"]),
        sorted(fases["IRQ"]["bits"]))
    # el calculo del solape, que es el dato que decide
    m_setup = mascara_de(fases["SETUP"]["bits"], 0)
    m_irq = mascara_de(fases["IRQ"]["bits"], 0, equivalent=1)
    solape = m_setup & m_irq
    chk("HALLAZGO: setup e IRQ NO comparten ningun bit",
        solape == 0, (hex(m_setup), hex(m_irq), hex(solape)))
    chk("HALLAZGO: la IRQ pone 7 bits de fault",
        bin(m_irq).count("1") == 7, hex(m_irq))
    chk("HALLAZGO: el setup NO pone ningun bit de fault",
        not (m_setup & 0x7fe248), hex(m_setup))

    print(f"  {ok} pasaron, {fail} fallaron")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    if "--out" in sys.argv:
        c0, c1, fases = analizar()
        n_com, n_ig, solo, dif = campos_iguales(c0, c1)
        m_setup = mascara_de(fases["SETUP"]["bits"], 0)
        m_irq = mascara_de(fases["IRQ"]["bits"], 0, equivalent=1)
        m_tear = mascara_de(fases["TEARDOWN"]["bits"], 0)
        print(f"  CONTEXT0_CNTL campos: {len(c0)}   CONTEXT1_CNTL: {len(c1)}")
        print(f"  comunes: {n_com}   mismo valor: {n_ig}   "
              f"solo en uno: {solo}   distintos: {dif}")
        for rol in ("SETUP", "TEARDOWN", "IRQ"):
            f = fases[rol]
            m = {"SETUP": m_setup, "TEARDOWN": m_tear, "IRQ": m_irq}[rol]
            print(f"  {rol:<9} {f['nombre'][:44]:<44} mascara={hex(m):<12} "
                  f"bits={bin(m).count('1')}")
        print(f"  setup AND irq  = {hex(m_setup & m_irq)}")
        print(f"  setup AND tear = {hex(m_setup & m_tear)}")
        json.dump({"contornos": {"comunes": n_com, "mismo_valor": n_ig,
                                 "solo_uno": solo, "distintos": dif},
                   "mascaras": {"setup": m_setup, "teardown": m_tear,
                                "irq": m_irq},
                   "solapes": {"setup_irq": m_setup & m_irq,
                               "setup_teardown": m_setup & m_tear}},
                  open(os.path.join(RX550_ROOT, "06-INGENIERIA-INVERSA", "agents", "bits.json"), "w"),
                  indent=2, ensure_ascii=False)
    else:
        print("uso: bits.py --self-test [--rapido] | --out")
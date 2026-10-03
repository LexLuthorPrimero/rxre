#!/usr/bin/env python3
"""pisa — quien escribe un registro EN BRUTO, y a quien borra por el camino

RX550_ROOT = os.environ.get("RX550_ROOT", "/home/lucas/Escritorio/RX550-INVESTIGACION")
RX550_ARQ = os.environ.get("RX550_ARQ", os.path.join(RX550_ROOT, "08-ARQUITECTURA"))

POR QUE        `bits` demostro que el setup y la IRQ no comparten ni un bit, y
               que el teardown pone mascara 0.  Mirando el fuente, "mascara 0"
               quiere decir algo peor de lo que parecia:

                 WREG32(mmVM_CONTEXT0_CNTL, 0);
                 WREG32(mmVM_CONTEXT1_CNTL, 0);

               No es "no pone ningun campo".  Es **escribe el registro entero a
               cero**, y con eso borra todos los campos que otro hubiera puesto,
               incluidos los que no le tocan.  Eso es la operacion opuesta a un
               RMW por campo: un RMW parcial se solapa con quien toque los
               MISMOS campos; una escritura en bruto se solapa con quien toque
               CUALQUIER campo del registro.

               Regla general que sale de aqui, y que se comprueba:

                 escribir un REGISTRO ENTERO afecta a todos sus campos
                 escribir un CAMPO afecta solo a ese campo

               Con esa regla, el conjunto de "riesgos" se puede refinar: dos
               rutinas que comparten un registro y un campo son un riesgo de
               solape de campo; dos que comparten un registro y no comparten
               ningun campo siguen siendo riesgo SI alguna escribe en bruto.

METODO         Se busca, en el cuerpo de cada funcion de riesgo:
                 - escrituras EN BRUTO: WREG32(reg, literal)  -> pisa todo
                 - escrituras POR CAMPO: REG_SET_FIELD(...reg...) -> pisa uno
                 y se cruza con el campo que realmente manipula cada una.
               El dato duro es el valor literal de la escritura; el nombre del
               campo es lo que convierte un RMW en solape de campo.

CONTROL        Aqui el resultado peligroso es "nadie pisa en bruto".  Asi que:
                 - CONTROL POSITIVO: se busca una escritura en bruto CONOCIDA
                   (gart_disable sobre CONTEXT0_CNTL con literal 0) y se exige
                   que aparezca.  Si no aparece, la heuristica esta rota.
                 - el caso de un valor NO literal (`WREG32(reg, tmp)`) NO cuenta
                   como bruto: es un RMW, y se declara como tal.  Confundir
                   ambos daria "no pisa" donde si lee-modifica-escribe.
                 - una escritura por campo con `~` (clear) se distingue de una
                   con `|` (set): limpiar un campo que otro pone es solape aunque
                   los campos sean distintos en nombre, porque ambos tocan el
                   mismo bit.

DEPENDENCIAS   conflicto, funcspan, bits, paths
"""

import os
import re
import sys
import json
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from paths import AMD as _AMD                     # noqa: E402
import funcspan                                    # noqa: E402
import conflicto as _cf                            # noqa: E402
import bits as _bits                               # noqa: E402

VERSION = "1.0"
NAME = "pisa"


def literal(v):
    """(es_literal, valor) de una expresion de escritura"""
    v = v.strip()
    if re.fullmatch(r"0x[0-9A-Fa-f]+", v):
        return True, int(v, 16)
    if re.fullmatch(r"\d+", v):
        return True, int(v)
    return False, None


def escribe_bruto(cuerpo):
    """registros que se escriben ENTEROS (literal), es decir, se pisan

    El RMW por campo se reconoce por el `REG_SET_FIELD` / `&=` / `|=` sobre la
    MISMA variable que se escribe, que puede estar lineas antes.  Buscar el
    operador en la linea de la escritura dava []: la operacion esta dos lineas
    antes y el valor escrito es solo `tmp`.  (correccion 169)
    """
    lineas = (cuerpo or "").splitlines()
    # registros que han sufrido una operacion de campo
    por_campo = set()
    for ln in lineas:
        m = re.search(r"(\w+)\s*=\s*REG_(?:SET|CLEAR)_FIELD\(", ln)
        if m:
            por_campo.add(m.group(1))
        m = re.search(r"(\w+)\s*(&=|\|=)\s*", ln)
        if m:
            por_campo.add(m.group(1))
    out = []
    for ln in lineas:
        s = ln.strip()
        m = re.search(r"WREG32[A-Z_]*\(\s*(\w+)\s*,\s*([^)]*)\)", s)
        if not m:
            continue
        reg, val = m.group(1), m.group(2)
        lit, v = literal(val)
        if lit:
            out.append({"registro": reg, "valor": v, "hex": hex(v),
                        "operacion": "BRUTO",
                        "por_que": "literal: deja el valor fijo, no preserva"})
        elif val.strip() in por_campo:
            out.append({"registro": reg, "valor": None, "hex": None,
                        "operacion": "RMW_CAMPO",
                        "por_que": "lee-modifica-escribe por campo"})
    return out


def campos_tocados(cuerpo):
    """campos de CONTEXTn_CNTL que la funcion pone o limpia"""
    return _bits.bits_de_cuerpo(cuerpo)


def analizar():
    riesgo = _cf.riesgo_por_funcion()
    reg2r, conf = _cf.analizar(riesgo)
    en_conf = [f"{riesgo[i]['fichero']}:{riesgo[i]['ini']}" for i in conf]

    info = {}
    for k in en_conf:
        f, _s, l = k.rpartition(":")
        p = os.path.join(_AMD, "amdgpu", f)
        a, b, _m = funcspan.of_line(p, int(l))
        if a is None:
            continue
        ls = open(p, encoding="utf-8", errors="replace").read().splitlines()
        cuerpo = "\n".join(ls[a - 1:b])
        cab = ls[a - 1]
        mm = re.search(r"(\w+)\s*\(", cab)
        info[k] = {
            "nombre": mm.group(1) if mm else None,
            "bruto": escribe_bruto(cuerpo),
            "campos": campos_tocados(cuerpo),
            "registros": None,      # no se usa aqui; lo tiene `conflicto`
        }
    return riesgo, conf, en_conf, info


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

    # --- literal: lo que se considera bruto y lo que no ---
    chk("literal hex es literal", literal("0x0")[0])
    chk("literal decimal es literal", literal("4")[0])
    chk("literal hex vale 0", literal("0x0")[1] == 0)
    chk("NEGATIVO: una variable NO es literal", not literal("tmp")[0])
    chk("NEGATIVO: una expresion NO es literal", not literal("1 << vmid")[0])

    # --- escrituras en bruto: casos de cada lado ---
    cuerpo_bruto = ("\tWREG32(mmVM_CONTEXT0_CNTL, 0);\n"
                    "\tWREG32(mmVM_CONTEXT1_CNTL, 0);\n"
                    "\tWREG32(mmVM_CONTEXT0_CNTL2, 0);\n")
    br = escribe_bruto(cuerpo_bruto)
    chk("BRUTO: detecta las 3 escrituras literales", len(br) == 3, br)
    chk("BRUTO: las marca como BRUTO y no como RMW",
        all(x["operacion"] == "BRUTO" for x in br), br)
    chk("BRUTO: el valor es 0", all(x["valor"] == 0 for x in br), br)

    cuerpo_rmw = ("\ttmp = RREG32(mmVM_CONTEXT0_CNTL);\n"
                  "\ttmp = REG_SET_FIELD(tmp, VM_CONTEXT0_CNTL, "
                  "ENABLE_CONTEXT, 1);\n"
                  "\tWREG32(mmVM_CONTEXT0_CNTL, tmp);\n")
    br2 = escribe_bruto(cuerpo_rmw)
    chk("NEGATIVO: un RMW por campo NO es escritura en bruto",
        not [x for x in br2 if x["operacion"] == "BRUTO"], br2)
    chk("RMW: se clasifica como RMW_CAMPO",
        [x["operacion"] for x in br2] == ["RMW_CAMPO"], br2)
    chk("NEGATIVO: una mascara literal NO cuenta (no es este patron)",
        not escribe_bruto("\tWREG32(a, msk & ~x);\n"))
    chk("EDGE: cuerpo vacio", escribe_bruto("") == [])
    chk("EDGE: cuerpo None", escribe_bruto(None) == [])

    if "--rapido" in sys.argv:
        print(f"  {ok} pasaron, {fail} fallaron"
              "  (sintetico; corpus NO evaluado)")
        return 0 if fail == 0 else 1

    riesgo, conf, en_conf, info = analizar()
    chk("CONTROL: hay funciones analizadas", len(info) > 0, len(info))
    # CONTROL POSITIVO obligatorio: gart_disable escribe 0 a CONTEXT0_CNTL
    gd = next((v for v in info.values()
               if v["nombre"] == "gmc_v8_0_gart_disable"), None)
    chk("CONTROL POSITIVO: se encuentra gart_disable", gd is not None,
        [v["nombre"] for v in info.values() if v["nombre"]])
    if gd:
        brutos = [x for x in gd["bruto"]
                  if x["operacion"] == "BRUTO"]
        nombres = {x["registro"] for x in brutos}
        chk("CONTROL POSITIVO: escribe mmVM_CONTEXT0_CNTL en bruto",
            "mmVM_CONTEXT0_CNTL" in nombres, sorted(nombres))
        chk("CONTROL POSITIVO: y mmVM_CONTEXT1_CNTL", 
            "mmVM_CONTEXT1_CNTL" in nombres, sorted(nombres))
    ge = next((v for v in info.values()
               if v["nombre"] == "gmc_v8_0_gart_enable"), None)
    chk("CONTROL POSITIVO: gart_enable NO escribe CONTEXT0_CNTL en bruto",
        ge is not None
        and not [x for x in ge["bruto"]
                 if x["registro"] == "mmVM_CONTEXT0_CNTL"
                 and x["operacion"] == "BRUTO"],
        ge and ge["bruto"])

    print(f"  {ok} pasaron, {fail} fallaron")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    if "--out" in sys.argv:
        riesgo, conf, en_conf, info = analizar()
        print(f"  funciones analizadas: {len(info)}")
        brutos = {k: [x for x in v["bruto"] if x["operacion"] == "BRUTO"]
                  for k, v in info.items()}
        con_bruto = {k: v for k, v in brutos.items() if v}
        print(f"  con escritura EN BRUTO: {len(con_bruto)}")
        for k, v in sorted(con_bruto.items()):
            print(f"    {info[k]['nombre'][:40]:<40} "
                  f"{sorted(x['registro'] for x in v)}")
        json.dump({"brutos": {k: v for k, v in brutos.items()},
                   "nombres": {k: info[k]["nombre"] for k in info}},
                  open(os.path.join(RX550_ROOT, "06-INGENIERIA-INVERSA", "agents", "pisa.json"), "w"),
                  indent=2, ensure_ascii=False)
    else:
        print("uso: pisa.py --self-test [--rapido] | --out")
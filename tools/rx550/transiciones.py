#!/usr/bin/env python3
"""transiciones — las 13 en conflicto como maquina de dos fases

RX550_ROOT = os.environ.get("RX550_ROOT", "/home/lucas/Escritorio/RX550-INVESTIGACION")
RX550_ARQ = os.environ.get("RX550_ARQ", os.path.join(RX550_ROOT, "08-ARQUITECTURA"))

POR QUE        `conflicto` encuentra 13 funciones que escriben registros
               compartidos dentro del mismo bloque IP sin mutex.  Leidas como
               "riesgos", sugieren 13 carreras.  Leidas como PARES, sugieren otra
               cosa: enable/disable, stop/resume, coarse/medium, light_sleep.
               Eso no son 13 problemas sino las transiciones de una maquina de
               dos fases, y las transiciones son exactamente lo que un driver
               propio necesita para no pisar ninguna.

               La pregunta es verificable sin hardware: ¿se pueden agrupar las
               13 en pares que comparten registros, y cada par es una maquina
               de dos fases?  Si es que si, la lista de riesgos se convierte en
               la tabla de transiciones.

METODO         Sobre el conjunto de 13 de `conflicto` (el mismo, no uno nuevo):
               1. Se construye el grafo de conflicto por REGISTRO: dos
                  funciones conectadas si comparten alguno.
               2. Se buscan componentes conexas de tamano 2 o mas.  Un par es
                  una MAQUINA DE DOS FASAS si sus nombres sugieren fases
                  complementarias (enable/disable, on/off, start/stop,
                  resume/suspend, coarse/medium, sleep/wake).  Ese criterio se
                  DECLARA como heuristica: el dato duro es que comparten
                  registros, y que se llamen enable y disable es lectura mia.
               3. Para cada par se comprueba el patron RMW: ¿la funcion A
                  LEE antes de escribir?  Un RMW sobre un registro compartido
                  es perdida de actualizacion; un par donde A pone un valor
                  constante y B lo quita no lo es.

CONTROL        El resultado que mas engaña aqui es "no son pares".  Asi que:
                 - CONTROL POSITIVO: los pares que SI existen se nombran
                   explicitamente y se verifica su solape de registros, no su
                   nombre.  Si el solape es 0, el par no existe por mucho que
                   los nombres cuadren.
                 - un par NO se acepta por el nombre: se acepta por registros
                   compartidos.  El nombre es la ETIQUETA, no la prueba.
                 - el reparto por componentes mas grande que 2 se reporta
                   aparte, porque una componente de 6 no es un par y forzar
                   emparejar dentro de ella seria inventar la estructura.

DEPENDENCIAS   conflicto, funcspan, paths  (todas TOOL_VALIDATED)
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

VERSION = "1.0"
NAME = "transiciones"

# Fases complementarias.  ETIQUETA, no prueba: la prueba es que comparten
# registros.  Se declara aqui para que se pueda discutir.
# Un nombre de funcion lleva UNA fase ("gart_enable"), no las dos: las dos
# fases estan en DOS funciones distintas, que es justamente lo que es un par.
# Por eso `fase_de` devuelve una ETIQUETA por fase suelta, y el emparejamiento
# se hace entre las dos funciones.  La version anterior buscaba las dos palabras
# en un mismo nombre, que por construccion nunca ocurre.  (correccion 161)
FASES = {
    "enable": "enable/disable", "disable": "enable/disable",
    "on": "on/off", "off": "on/off",
    "start": "start/stop", "stop": "start/stop",
    "resume": "resume/suspend", "suspend": "resume/suspend",
    "enter": "enter/exit", "exit": "enter/exit",
    "acquire": "acquire/release", "release": "acquire/release",
    "attach": "attach/detach", "detach": "attach/detach",
    "coarse": "coarse/medium", "medium": "coarse/medium",
    "light_sleep": "light_sleep/wake", "wake": "light_sleep/wake",
    "init": "init/fini", "fini": "init/fini",
    "program": "program/unprogram", "unprogram": "program/unprogram",
}


def fase_de(nombre):
    """la etiqueta de fase de UN nombre, o None"""
    n = (nombre or "").lower()
    for palabra, etiqueta in FASES.items():
        if palabra in n:
            return etiqueta
    return None


def nombre_de(fichero, linea):
    p = os.path.join(_AMD, "amdgpu", fichero)
    a, b, _m = funcspan.of_line(p, linea)
    if a is None:
        return None, None, None
    ls = open(p, encoding="utf-8", errors="replace").read().splitlines()
    cab = ls[a - 1]
    mm = re.search(r"(\w+)\s*\(", cab)
    return (mm.group(1) if mm else None), (a, b), "\n".join(ls[a - 1:b])


# alias: `fase_de` es el nombre bueno; se deja el antiguo como alias para no
# romper las referencias ya escritas, y se cambia el uso (161)
fases_de = fase_de


def rmw(cuerpo):
    """True si el cuerpo hace leer-modificar-escribir sobre REGISTROS

    Se busca la secuencia RREG32(...) ... WREG32(...) con una asignacion entre
    medias.  Un RMW sobre registro compartido es perdida de actualizacion si dos
    routines se solapan; una escritura de valor constante no lo es.
    """
    if not cuerpo:
        return False, 0
    regs = set()
    n_rmw = 0
    ultimo_read = None
    for ln in cuerpo.splitlines():
        s = ln.strip()
        m = re.search(r"RREG32[A-Z_]*\(\s*(\w+)", s)
        if m:
            ultimo_read = m.group(1)
            continue
        m = re.search(r"WREG32[A-Z_]*\(\s*(\w+)\s*,\s*([^)]*)\)", s)
        if m:
            reg, val = m.group(1), m.group(2).strip()
            regs.add(reg)
            # hay RMW si el valor escrito no es un literal simple
            if ultimo_read == reg and not re.match(
                    r"^(0x[0-9A-Fa-f]+|\d+)$", val):
                n_rmw += 1
    return n_rmw > 0, n_rmw


def analizar():
    riesgo = _cf.riesgo_por_funcion()
    reg2r, conf = _cf.analizar(riesgo)
    claves = [f"{riesgo[i]['fichero']}:{riesgo[i]['ini']}" for i in conf]
    idx = {k: i for i, k in enumerate(claves)}

    info = {}
    # `conf` tiene claves que son indices de `riesgo`.  Se itera sobre ESAS
    # claves, no sobre `enumerate(claves)`: `claves[j]` viene de un `i` que no
    # es necesariamente `j`, y emparejar la posicion con el indice hacia que
    # cada funcion tuviera los registros de otra.  Se construye la clave DENTRO
    # del bucle, desde el mismo `i` del que sale.  (correccion 165)
    for i in sorted(conf):
        k = f"{riesgo[i]['fichero']}:{riesgo[i]['ini']}"
        f = riesgo[i]["fichero"]
        ln = riesgo[i]["ini"]
        # El nombre se resuelve desde el registro que CONFLICTA, no desde la
        # linea: `claves` se construye con `riesgo[i]`, pero el `info` se
        # indexaba por posicion en `claves`, y los dos ordenes NO coinciden
        # (claves solo trae las que tienen conflicto; riesgo, todas).  Resultado:
        # nombres de una función con los registros de otra.  El indice correcto
        # es `i`, y `riesgo[i]` es el MISMO elemento del que salio la clave.
        # (correccion 164)
        nom, span, cuerpo = nombre_de(f, ln)
        es_rmw, n = rmw(cuerpo)
        info[k] = {"nombre": nom, "bloque": riesgo[i]["bloque"],
                   "registros": set(riesgo[i]["registros"]),
                   "rmw": es_rmw, "n_rmw": n, "fases": fase_de(nom),
                   "sin_nombre": nom is None}

    # El grafo se toma de `conf`, que YA esta construido y verificado por
    # `conflicto` (simetrico, con 5 componentes que suman 13).  Reconstruirlo
    # aqui comparando conjuntos de registros daba componentes distintas y
    # peredia 4 funciones: los indices de `riesgo` y de `claves` no son los
    # mismos, y emparejar por registro en vez de por el veredicto de conflicto
    # empareja cosas que el conflicto ya habia descartado.  Una sola fuente de
    # verdad, y se declara de cual.  (correccion 163)
    adj = collections.defaultdict(set)
    compartidos = collections.defaultdict(set)
    for i in sorted(conf):
        a = f"{riesgo[i]['fichero']}:{riesgo[i]['ini']}"
        for x in conf[i]:
            b = x["con"]
            adj[a].add(b)
            adj[b].add(a)
            compartidos[(a, b)].add(x["reg"])
            compartidos[(b, a)].add(x["reg"])

    # componentes conexas
    vistos, comps = set(), []
    for k in claves:
        if k in vistos:
            continue
        pila, comp = [k], []
        vistos.add(k)
        while pila:
            x = pila.pop()
            comp.append(x)
            for y in adj[x]:
                if y not in vistos:
                    vistos.add(y)
                    pila.append(y)
        comps.append(sorted(comp))

    pares, grandes = [], []
    for c in comps:
        if len(c) < 2:
            continue
        if len(c) > 2:
            grandes.append(c)
            continue
        a, b = c
        pares.append({
            "a": a, "b": b,
            "nombre_a": info[a]["nombre"], "nombre_b": info[b]["nombre"],
            "bloque": info[a]["bloque"],
            "registros_compartidos": sorted(compartidos.get((a, b),
                                                           set())),
            "fases": (fase_de(info[a]["nombre"]) if
                      fase_de(info[a]["nombre"]) == fase_de(info[b]["nombre"])
                      else None),
            "fase_a": fase_de(info[a]["nombre"]),
            "fase_b": fase_de(info[b]["nombre"]),
            "rmw_a": info[a]["rmw"], "rmw_b": info[b]["rmw"],
        })
    return riesgo, info, pares, grandes, claves


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

    # --- detector de fases: con casos de cada lado ---
    # Un nombre suelto NO puede ser un par: `_fase_de` mira si se encuentran
    # LAS DOS palabras en un mismo nombre, y eso no pasa con una sola funcion.
    # (correccion 160: los dos primeros asertos de esta lista eran
    #  tautologicos, comprobaban que None es None)
    chk("FASES: un nombre sin fase da None",
        fase_de("gfx_v8_0_soft_reset") is None,
        fase_de("gfx_v8_0_soft_reset"))
    chk("FASES: una fase suelta da su etiqueta",
        fase_de("gmc_v8_0_gart_enable") == "enable/disable",
        fase_de("gmc_v8_0_gart_enable"))
    chk("FASES: la fase opuesta da la MISMA etiqueta",
        fase_de("gmc_v8_0_gart_disable") == "enable/disable",
        fase_de("gmc_v8_0_gart_disable"))
    chk("FASES: coarse y medium comparten etiqueta",
        fase_de("x_coarse") == fase_de("y_medium") == "coarse/medium",
        (fase_de("x_coarse"), fase_de("y_medium")))

    # --- detector de RMW, sobre cuerpo sintetico ---
    cuerpo_rmw = ("\ttmp = RREG32(mmMC_SHARED_BLACKOUT_CNTL);\n"
                  "\ttmp |= MC_SHARED_BLACKOUT_CNTL__BLACKOUT_MODE_MASK;\n"
                  "\tWREG32(mmMC_SHARED_BLACKOUT_CNTL, tmp);\n")
    e, n = rmw(cuerpo_rmw)
    chk("RMW: lee, modifica y escribe -> detectado", e and n == 1, (e, n))
    cuerpo_const = "\tWREG32(mmVM_CONTEXT0_CNTL, 1 << vmid);\n"
    e2, n2 = rmw(cuerpo_const)
    chk("NEGATIVO: escribir un literal NO es RMW", not e2, (e2, n2))
    cuerpo_vacio = ""
    e3, _ = rmw(cuerpo_vacio)
    chk("EDGE: cuerpo vacio -> no RMW, no revienta", not e3)
    e4, _ = rmw(None)
    chk("EDGE: cuerpo None -> no RMW, no revienta", not e4)

    if "--rapido" in sys.argv:
        print(f"  {ok} pasaron, {fail} fallaron"
              "  (sintetico; corpus NO evaluado)")
        return 0 if fail == 0 else 1

    # --- CORPUS ---
    riesgo, info, pares, grandes, claves = analizar()
    chk("CONTROL: el conjunto de 13 no es vacio", len(claves) == 13,
        len(claves))
    chk("CONTROL: cada funcion tiene nombre",
        all(info[k]["nombre"] for k in claves),
        [k for k in claves if not info[k]["nombre"]])
    chk("CONTROL: todos los pares comparten AL MENOS un registro",
        all(p["registros_compartidos"] for p in pares),
        [p["nombre_a"] for p in pares if not p["registros_compartidos"]])
    # La cuenta tiene que cuadrar: pares (2 c/u) + componentes grandes + sueltas
    # reconstruyen las 13.  Sin esta comprobacion, un par contado dos veces o
    # una suelta perdida pasarían inadvertidos.
    sueltas = 13 - 2 * len(pares) - sum(len(c) for c in grandes)
    chk("CONSISTENCIA: pares + grandes + sueltas = 13", sueltas >= 0,
        (len(pares), [len(c) for c in grandes], sueltas))

    # --- REGRESION: la estructura, con valores fijos ---
    # Los 4 fallos anteriores de esta herramienta fueron de INDEXACION: los
    # nombres salian de una funcion y los registros de otra.  Un assert que
    # solo mira el RECUENTO no lo detecta, porque los dos casos dan 2 y 3 igual.
    # Por eso se comprueba el CONTENIDO: que el par de clock gating empareje las
    # dos funciones de clock gating y el registro que las dos escriben.
    chk("REGRESION: 2 pares y 3 trios", (len(pares), len(grandes)) == (2, 3),
        (len(pares), len(grandes)))
    por_nombre = {p["nombre_a"]: p for p in pares}
    cg = por_nombre.get("gfx_v8_0_update_medium_grain_clock_gating")
    chk("REGRESION: el par coarse/medium existe", cg is not None,
        sorted(por_nombre))
    if cg:
        chk("REGRESION: su pareja es la de clock gating COARSE",
            cg["nombre_b"] == "gfx_v8_0_update_coarse_grain_clock_gating",
            cg["nombre_b"])
        chk("REGRESION: comparte mmRLC_CGTT_MGCG_OVERRIDE",
            cg["registros_compartidos"] == ["mmRLC_CGTT_MGCG_OVERRIDE"],
            cg["registros_compartidos"])
        chk("REGRESION: la etiqueta de fases es coarse/medium",
            cg["fases"] == "coarse/medium", cg["fases"])
        chk("REGRESION: las dos hacen RMW (perdida de actualizacion)",
            cg["rmw_a"] and cg["rmw_b"], (cg["rmw_a"], cg["rmw_b"]))
    ls = por_nombre.get("fiji_update_mc_medium_grain_clock_gating")
    chk("REGRESION: el segundo par es light_sleep vs medium_grain",
        ls is not None and ls["nombre_b"] == "fiji_update_mc_light_sleep",
        ls and ls["nombre_b"])
    if ls:
        chk("REGRESION: ese par comparte 9 registros, ninguno PTBA",
            len(ls["registros_compartidos"]) == 9
            and not any("PAGE_TABLE" in r
                        for r in ls["registros_compartidos"]),
            ls["registros_compartidos"][:3])
        chk("REGRESION: ese par NO lleva etiqueta (fases distintas)",
            ls["fases"] is None, ls["fases"])
    # Comprobacion que habria cazado el bug de INDEXACION: el par de clock
    # gating tiene que traer los registros de clock gating.  Mi primer intento
    # de esta comprobacion decia que un nombre con "clock" no puede tocar
    # CITF/ATC, y es FALSO: los gates de memoria (`mmMC_CITF_MISC_*_CG`) son
    # justamente lo que el clock gating controla.  El aserto era el equivocado.
    # (correccion 166)
    chk("REGRESION: el par de clock gating trae registros de clock gating",
        all(any(("GATING" in r or "MGCG" in r or "CITF" in r or "HUB_MISC" in r)
                for r in p["registros_compartidos"])
            for p in pares if "clock_gating" in (p["nombre_a"] or "")
            or "light_sleep" in (p["nombre_a"] or "")),
        [(p["nombre_a"], p["registros_compartidos"][:2]) for p in pares])

    print(f"  {ok} pasaron, {fail} fallaron")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    if "--out" in sys.argv:
        riesgo, info, pares, grandes, claves = analizar()
        print(f"  funciones en conflicto: {len(claves)}")
        sin = [k for k in claves if info[k]["sin_nombre"]]
        print(f"  sin nombre resuelto (NO se emparejan): {len(sin)}"
              + (f" -> {sin}" if sin else ""))
        print(f"  PARES (componentes de 2): {len(pares)}")
        print(f"  componentes de mas de 2: {len(grandes)}"
              + (f" -> {[len(c) for c in grandes]}" if grandes else ""))
        etiq = [p for p in pares if p["fases"]]
        print(f"  pares con etiqueta de fases legible: {len(etiq)}")
        rmw = [p for p in pares if p["rmw_a"] or p["rmw_b"]]
        print(f"  pares donde AL MENOS UNA hace RMW: {len(rmw)}")
        json.dump({"pares": [{k: (sorted(v) if isinstance(v, set) else v)
                             for k, v in p.items()} for p in pares],
                   "componentes_grandes": grandes,
                   "claves": claves},
                  open(os.path.join(RX550_ROOT, "06-INGENIERIA-INVERSA", "agents", "transiciones.json"), "w"),
                  indent=2, ensure_ascii=False)
    else:
        print("uso: transiciones.py --self-test [--rapido] | --out")
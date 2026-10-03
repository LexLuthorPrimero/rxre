#!/usr/bin/env python3
"""ciclo — los 3 trios son ciclos de vida, y eso es comprobable

RX550_ROOT = os.environ.get("RX550_ROOT", "/home/lucas/Escritorio/RX550-INVESTIGACION")
RX550_ARQ = os.environ.get("RX550_ARQ", os.path.join(RX550_ROOT, "08-ARQUITECTURA"))

POR QUE        `transiciones` dio 2 pares y 3 TRIOS.  Un trio no es un par, y
               llamarlos "13 conflictos" no dice nada util.  Pero los 3 tienen
               la MISMA forma:

                 configurar  ->  detener  ->  restaurar
                 mc_program  ->  mc_stop   ->  mc_resume
                 gart_enable ->  gart_disable -> restore_regs
                 (vm_fault_irq, gart_enable, gart_disable)

               Si eso es un ciclo de vida, tiene un INVARIANTE comprobable sin
               hardware: cada ciclo debe dejar los registros que toca en el
               mismo valor con el que los encontro.  Es decir: lo que escribe el
               setup tiene que ser lo que escribe el teardown, en el mismo
               registro.  Si un teardown escribe un registro que el setup no
               toca, el ciclo no esta cerrado y deja estadobehind.

               Ese test es decidible sobre el fuente, y es lo que distingue un
               ciclo bien formado de tres rutinas que se pisan.

METODO         Para cada trio:
               1. Se ordena por nombre segun el rol que sugiere el nombre
                  (program/enable/setup = SETUP; stop/disable = TEARDOWN;
                  restore/resume/program2 = RESTAURAR).  El rol es ETIQUETA
                  derivada del nombre, y se declara como tal: si el nombre no
                  encaja en ningun rol, el trio se reporta SIN_ROL y no se le
                  inventa uno.
               2. Se comparan los conjuntos de registros: los que escribe el
                  teardown y no toca el setup son "dejados atras".
               3. Se comprueba el patron RMW en cada miembro: un ciclo que hace
                  RMW sobre un registro compartido no puede dejar el mismo
                  valor, porque depende del estado previo -> invariante
                  IMPOSIBLE por construccion, y eso es un hallazgo.

CONTROL        El resultado dangerouso aqui es "el ciclo esta bien".  Asi que:
                 - CONTROL POSITIVO: hay al menos un trio con registros
                   dejados atras, y se nombran.  Si no hay ninguno, la
                   herramienta no esta probando nada.
                 - el invariante NO se declara cumplido solo porque los roles
                   encajen: se exige ver los registros de cada miembro.
                 - un trio con un miembro SIN RMW se distingue del que tiene
                   RMW en todos, y se reporta por separado.

DEPENDENCIAS   conflicto, transiciones, funcspan, paths
LIMITACION     Los roles se infieren del NOMBRE.  El dato duro es el conjunto
               de registros; el nombre solo ordena.  Se declara.
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
import transiciones as _tr                         # noqa: E402

VERSION = "1.0"
NAME = "ciclo"

# Rol por palabra del nombre.  ETIQUETA, no prueba: la prueba es el conjunto de
# registros.  Un nombre que no cae en ninguna no recibe rol inventado.
ROLES = [
    # (palabras que identifican el rol, rol)
    (("restore_regs", "restore", "resume", "resumed"), "RESTAURAR"),
    (("disable", "stop", "suspend", "fini"), "TEARDOWN"),
    (("program", "enable", "setup", "init"), "SETUP"),
]


def rol_de(nombre):
    n = (nombre or "").lower()
    for palabras, rol in ROLES:
        for p in palabras:
            if p in n:
                return rol
    return None


def escribir_registros(cuerpo):
    """registros que el cuerpo ESCRIBE, con su valor, en orden"""
    out = []
    for ln in (cuerpo or "").splitlines():
        m = re.search(r"WREG32[A-Z_]*\(\s*(\w+)\s*,\s*([^)]*)\)", ln)
        if m:
            out.append((m.group(1), m.group(2).strip()))
    return out


def analizar():
    riesgo = _cf.riesgo_por_funcion()
    reg2r, conf = _cf.analizar(riesgo)
    info, pares, grandes, claves = _tr.analizar()[1:]

    ciclos = []
    for comp in grandes:
        miembros = []
        for k in comp:
            f, _s, l = k.rpartition(":")
            nom, span, cuerpo = _tr.nombre_de(f, int(l))
            miembros.append({"clave": k, "nombre": nom,
                             "rol": rol_de(nom),
                             "escribe": escribir_registros(cuerpo),
                             "rmw": _tr.rmw(cuerpo)[0],
                             "registros": set(info[k]["registros"])})
        # ordenar por ROL, no por nombre: el ciclo tiene un sentido
        orden = {"SETUP": 0, "TEARDOWN": 1, "RESTAURAR": 2}
        miembros_ord = sorted(
            miembros, key=lambda m: (orden.get(m["rol"], 9), m["nombre"] or ""))

        setup = [m for m in miembros_ord if m["rol"] == "SETUP"]
        tear = [m for m in miembros_ord if m["rol"] == "TEARDOWN"]
        rest = [m for m in miembros_ord if m["rol"] == "RESTAURAR"]

        regs_setup = set().union(*[m["registros"] for m in setup]) \
            if setup else set()
        regs_tear = set().union(*[m["registros"] for m in tear]) \
            if tear else set()
        # lo que el teardown escribe y el setup no toca: estado deixado atras
        dejados = sorted(regs_tear - regs_setup) if (setup and tear) else []
        # lo que el setup escribe y el teardown no restaura
        sin_restar = sorted(regs_setup - regs_tear) if (setup and tear) else []

        ciclos.append({
            "miembros": [{"clave": m["clave"], "nombre": m["nombre"],
                          "rol": m["rol"], "n_regs": len(m["registros"]),
                          "rmw": m["rmw"]} for m in miembros_ord],
            "n_setup": len(setup), "n_teardown": len(tear),
            "n_restaurar": len(rest),
            "sin_rol": [m["nombre"] for m in miembros_ord if not m["rol"]],
            "regs_teardown_sin_setup": dejados,
            "regs_setup_sin_teardown": sin_restar,
            "todos_rmw": all(m["rmw"] for m in miembros_ord),
            "alguno_rmw": any(m["rmw"] for m in miembros_ord),
        })
    return riesgo, ciclos, claves


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

    # --- roles: cada lado, y el caso sin rol ---
    chk("ROL: restore_regs -> RESTAURAR",
        rol_de("gfxhub_v2_1_restore_regs") == "RESTAURAR",
        rol_de("gfxhub_v2_1_restore_regs"))
    chk("ROL: disable -> TEARDOWN",
        rol_de("gfxhub_v2_1_gart_disable") == "TEARDOWN",
        rol_de("gfxhub_v2_1_gart_disable"))
    chk("ROL: enable -> SETUP",
        rol_de("gfxhub_v2_1_gart_enable") == "SETUP",
        rol_de("gfxhub_v2_1_gart_enable"))
    chk("NEGATIVO: un nombre sin palabra de rol NO recibe rol",
        rol_de("gfx_v8_0_vm_fault_interrupt_state") is None,
        rol_de("gfx_v8_0_vm_fault_interrupt_state"))
    chk("NEGATIVO: un nombre vacio no recibe rol", rol_de("") is None)
    chk("NEGATIVO: None no recibe rol", rol_de(None) is None)
    # el orden de la tabla importa: "restore" gana a "resume"
    chk("ROL: gana la regla mas especifica (restore antes que resume)",
        rol_de("x_resume_restore") == "RESTAURAR",
        rol_de("x_resume_restore"))

    # --- registros escritos, con valor ---
    esc = escribir_registros(
        "\tWREG32(mmA, 1);\n"
        "\ttmp = RREG32(mmB);\n"
        "\tWREG32(mmB, tmp | MASK);\n")
    chk("ESCRITURAS: encuentra las dos escrituras", len(esc) == 2, esc)
    chk("ESCRITURAS: distingue literal de RMW",
        esc[0][1] == "1" and "MASK" in esc[1][1], esc)
    chk("EDGE: cuerpo vacio -> 0 escrituras", escribir_registros("") == [])
    chk("EDGE: cuerpo None -> 0 escrituras", escribir_registros(None) == [])

    if "--rapido" in sys.argv:
        print(f"  {ok} pasaron, {fail} fallaron"
              "  (sintetico; corpus NO evaluado)")
        return 0 if fail == 0 else 1

    riesgo, ciclos, claves = analizar()
    chk("CONTROL: se analizan los 3 trios", len(ciclos) == 3,
        [len(c["miembros"]) for c in ciclos])
    chk("CONTROL: cada trio tiene 3 miembros",
        all(len(c["miembros"]) == 3 for c in ciclos),
        [len(c["miembros"]) for c in ciclos])
    chk("CONTROL: los 9 miembros se reparten sin perder ninguno",
        sum(len(c["miembros"]) for c in ciclos) == 9,
        sum(len(c["miembros"]) for c in ciclos))
    # CONTROL POSITIVO: debe existir al menos un ciclo con estado deixado
    # atras, o la herramienta no esta probando nada
    con_atras = [c for c in ciclos if c["regs_teardown_sin_setup"]]
    chk("CONTROL POSITIVO: hay al menos un ciclo con registros sin restaurar",
        len(con_atras) > 0, len(con_atras))

    # --- REGRESION: la forma de los 3 ciclos, con valores fijos ---
    # Los 3 tienen EXACTAMENTE la misma forma: 1 setup, 1 teardown, 1
    # restaurador.  El tercero tiene un miembro sin rol
    # (`vm_fault_interrupt_state`), que NO se le inventa: se reporta como
    # None y el ciclo queda con 0 restauradores.  Si un nombre cualquiera
    # recibiera un rol, esta aserto lo cazaria.
    chk("REGRESION: los 3 ciclos tienen 1 setup + 1 teardown",
        all(c["n_setup"] == 1 and c["n_teardown"] == 1 for c in ciclos),
        [(c["n_setup"], c["n_teardown"]) for c in ciclos])
    chk("REGRESION: 2 ciclos tienen restaurador, 1 no",
        sorted(c["n_restaurar"] for c in ciclos) == [0, 1, 1],
        [c["n_restaurar"] for c in ciclos])
    # `in` sobre una lista de listas compara la lista ENTERA por igualdad, no
    # la pertenencia: `"nombre" in [["nombre"]]` es False.  Por eso el aserto
    # fallaba con el dato correcto delante.  Se comprueba la lista de listas
    # directamente.  (correccion 167)
    chk("REGRESION: el miembro sin rol es vm_fault_interrupt_state",
        sum(len(c["sin_rol"]) for c in ciclos) == 1
        and [c["sin_rol"] for c in ciclos if c["sin_rol"]]
        == [["gmc_v8_0_vm_fault_interrupt_state"]],
        [c["sin_rol"] for c in ciclos])
    # el ciclo 1 deja mmGCVM_L2_CNTL3 sin tocar por el setup
    c1 = next((c for c in ciclos if any("gart_enable" in (m["nombre"] or "")
                                       and m["rol"] == "SETUP"
                                       for m in c["miembros"])), None)
    chk("REGRESION: el ciclo GFXHUB deja mmGCVM_L2_CNTL3 sin restaurar",
        c1 is not None
        and "mmGCVM_L2_CNTL3" in c1["regs_teardown_sin_setup"],
        c1 and c1["regs_teardown_sin_setup"])
    # el ciclo 2: mc_stop pone BLACKOUT_MODE=1 y mc_resume lo pone a 0, y
    # mc_program NO lo toca.  El "dejado atras" es correcto, no un fallo.
    c2 = next((c for c in ciclos if any("mc_program" in (m["nombre"] or "")
                                       for m in c["miembros"])), None)
    chk("REGRESION: el ciclo GMC deja mmMC_SHARED_BLACKOUT_CNTL",
        c2 is not None
        and "mmMC_SHARED_BLACKOUT_CNTL" in c2["regs_teardown_sin_setup"],
        c2 and c2["regs_teardown_sin_setup"])
    chk("REGRESION: el ciclo GMC tiene los 3 miembros con RMW",
        c2 is not None and c2["todos_rmw"], c2 and c2["todos_rmw"])
    chk("REGRESION: el ciclo GFXHUB tiene RMW en ningun miembro",
        c1 is not None and not c1["alguno_rmw"], c1 and c1["alguno_rmw"])

    print(f"  {ok} pasaron, {fail} fallaron")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    if "--out" in sys.argv:
        riesgo, ciclos, claves = analizar()
        print(f"  ciclos (trios): {len(ciclos)}")
        for i, c in enumerate(ciclos, 1):
            roles = "/".join(f"{m['nombre']}[{m['rol'] or '?'}]"
                             for m in c["miembros"])
            print(f"  --- ciclo {i}")
            print(f"      {roles[:150]}")
            print(f"      setup={c['n_setup']} teardown={c['n_teardown']} "
                  f"restaurar={c['n_restaurar']} sin_rol={c['sin_rol']}")
            print(f"      teardown escribe y setup no toca: "
                  f"{len(c['regs_teardown_sin_setup'])}")
            print(f"      todos RMW: {c['todos_rmw']}  alguno: {c['alguno_rmw']}")
        json.dump({"ciclos": ciclos}, open(
            os.path.join(RX550_ROOT, "06-INGENIERIA-INVERSA", "agents", "ciclo.json"), "w"),
            indent=2, ensure_ascii=False)
    else:
        print("uso: ciclo.py --self-test [--rapido] | --out")
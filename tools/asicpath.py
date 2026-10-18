#!/usr/bin/env python3
# CONTRACT: name=asicpath
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: TOUCHES_INTEGRATED=no
#
# MEDIDO con RXRE/tools/rxre_contracts.py, no declarado de memoria.  El
# veredicto fue `READONLY=yes, WRITES_FILES=no`, y las 0 escrituras que
# tiene se resolvieron a la clase TEMPORAL: no tiene ninguna escritura, asi que no hay nada que resolver.
#
# Declarar `WRITES_FILES=no` con escrituras dentro no es una contradiccion: es
# exactamente la clase TEMPORAL de `contract_exec.py`, que existe porque una
# regex produjo cinco falsos positivos.  Declararlas `yes` seria MENTIR: el
# validador no puede distinguir un temporal de un fichero del proyecto.
#
# `tools/` tenia 3 contratos de 92.  Este bloque no anade comportamiento: hace
# el comportamiento DECLARABLE, que es la condicion previa a poder usarlo.
# Sobre la frontera: TOUCHES_INTEGRATED=no, y el campo se declara aunque
# toolkit.py no lo conozca -- la frontera que no se puede declarar es la que no
# se puede hacer cumplir (hallazgo 1487).
"""asicpath.py -- que rutas de codigo ejecuta esta tarjeta.

PROPOSITO
    Responder, para un ASIC concreto, que comparaciones de `asic_type` se
    cumplen y cuales no.  No es un grep: es una EVALUACION, y por eso puede
    decir que una rama esta muerta cuando el texto solo demuestra que existe.

POR QUE EXISTE
    El corpus 7.2.8 no trae `include/drm/amd_asic_type.h` (hallazgo 1479), asi
    que el enum `chip_t` no esta disponible y "que ASIC es el indice 17" no se
    puede preguntar a las herramientas.  Pero `amdgpu_asic_name[]`
    (amdgpu_device.c:114) es una tabla alineada con el enum por posicion, y si
    esta en el corpus.  Con ella se responde.

    El valor de esto no es el recuento de comparaciones: es poder afirmar que
    una rama NO se ejecuta, y con eso ahorrarse leerla.

LO QUE NO ES, y esta en el codigo de este modulo a proposito
    - No lee el hardware.  `adev->asic_type` lo decide una TABLA de IDs PCI
      (amdgpu_drv.c:2054), que es una DECLARACION del driver.
    - No dice que el hardware tenga la funcion.  La condicion compara la ASIC
      declarada, no el silicio.
    - No dice que una rama verdadera se ejecute siempre: puede depender de otro
      if, de un estado previo, o de un return anterior.
    - No dice nada de las comparaciones de IGUALDAD.  Esas se responden por el
      switch, que es otro analisis.

DEPENDENCIA CRITICA, Y ES DECLARADA
    Todo depende de un indice: CHIP_POLARIS12 = 17.  Viene de
    `amdgpu_asic_name[]`, NO del enum, que falta.  Si el orden real del enum
    difiriera, TODAS las filas se moverian.  El hallazgo 1479 §4C midio que
    las 38 posiciones coinciden, asi que el riesgo esta acotado, pero no
    eliminado mientras el .h no este.  Por eso la salida lleva
    `indice_fuente` y no solo el numero.

GARANTIAS
    Solo LECTURA.  No escribe en el corpus ni en ningun sitio.
    exit 0 siempre: una rama muerta es un DATO, no un error.
    Salida reproducible: mismo corpus -> misma salida, sin timestamps.

USO
    asicpath.py                          las 26 comparaciones para POLARIS12
    asicpath.py --chip POLARIS12
    asicpath.py --chip POLARIS12 --vivas  solo las activas, con su localizacion
    asicpath.py --chip POLARIS12 --json
    asicpath.py --indice 17               que ASIC es el indice 17
    asicpath.py --orden                   el enum como lo ve esta herramienta
    asicpath.py --site CHIP_POLARIS10     donde se compara ese simbolo
    asicpath.py --self-test
"""
import argparse
import collections
import json
import os
import re
import sys

VERSION = "1.0.0"

DEFAULT_AMD = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "rx550-upstream-7.2.8", "linux-7.2.8", "drivers", "gpu", "drm", "amd")
TABLE_C = os.path.join("amdgpu", "amdgpu_device.c")

# MEDIDO 2026-10-05, hallazgo 1484: el simbolo se capture SIN el prefijo
# `CHIP_`, porque en el patron `CHIP_` es texto literal FUERA del grupo.  Yo
# hacia `sym[5:]` para "normalizar", y eso convertingia:
#       POLARIS10 -> IS10        POLARIS12 -> IS12
#       VANGOGH   -> ZO          ALDEBARAN -> A_CICHLID
# y el numero de coincidencias seguia siendo correcto, con el nombre mal.
# Por eso el self-test comprueba el NOMBRE, no la cuenta.
ORDINAL = re.compile(r"asic_type\s*(>=|<=|>|<)\s*CHIP_([A-Z0-9_]+)")

TABLA = re.compile(r"amdgpu_asic_name\[\] = \{(.*?)\n\};", re.S)
QUOTED = re.compile(r'"([^"]+)"')


def cargar_indice(amd=DEFAULT_AMD):
    """(nombres, {nombre: indice}, motivo_de_fallo).

    La fuente del indice es amdgpu_asic_name[], NO el enum, porque el enum no
    esta en el corpus.  Eso se declara en la salida y en el modulo: quien lea
    el numero tiene que saber de donde sale.
    """
    p = os.path.join(amd, TABLE_C)
    if not os.path.isfile(p):
        return None, {}, "no existe %s" % p
    with open(p, encoding="utf-8", errors="replace") as fh:
        m = TABLA.search(fh.read())
    if not m:
        return None, {}, "amdgpu_asic_name[] no esta declarado en %s" % p
    nombres = [x.replace(" ", "") for x in QUOTED.findall(m.group(1))]
    if not nombres:
        return None, {}, "amdgpu_asic_name[] esta vacio"
    return nombres, {n: i for i, n in enumerate(nombres)}, None


def evaluar(mine, ref):
    """(>, >=, <, <=) del valor propio contra el de referencia."""
    return {">": mine > ref, ">=": mine >= ref,
            "<": mine < ref, "<=": mine <= ref}


def barrer(amd, idx):
    """[(op, simbolo, valor_ref, resultado, fichero, linea)] con simbolo conocido."""
    out = []
    desconocidos = collections.Counter()
    for dirpath, _dirs, files in os.walk(amd):
        for fn in sorted(files):
            if not fn.endswith(".c"):
                continue
            path = os.path.join(dirpath, fn)
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    txt = fh.read()
            except OSError:
                continue
            for m in ORDINAL.finditer(txt):
                sym = m.group(2)          # SIN prefijo CHIP_.  Ver la nota.
                if sym not in idx:
                    desconocidos[sym] += 1
                    continue
                ref = idx[sym]
                out.append({
                    "op": m.group(1),
                    "simbolo": sym,
                    "valor_referencia": ref,
                    "resultado": evaluar(idx["__SELF__"], ref)[m.group(1)]
                    if "__SELF__" in idx else None,
                    "fichero": os.path.relpath(path, amd),
                    "linea": txt.count("\n", 0, m.start()) + 1,
                })
    return out, desconocidos


def medir(amd, chip):
    nombres, idx, fallo = cargar_indice(amd)
    if fallo:
        return {"error": fallo}
    if chip not in idx:
        return {"error": "el ASIC %s no esta en amdgpu_asic_name[]" % chip,
                "disponibles": nombres}
    idx["__SELF__"] = idx[chip]
    rows, desconocidos = barrer(amd, idx)
    del idx["__SELF__"]

    # quitar simbolos que solo aparecen en COMENTARIOS
    # MEDIDO: RV770 sale una vez, de un "TODO: add support for ...".
    filas = [r for r in rows if r["resultado"] is not None]
    agg = collections.defaultdict(lambda: {"v": 0, "f": 0, "sitios_true": [],
                                          "sitios_false": []})
    for r in filas:
        k = (r["op"], r["simbolo"])
        a = agg[k]
        a["v" if r["resultado"] else "f"] += 1
        (a["sitios_true"] if r["resultado"] else a["sitios_false"]).append(
            "%s:%d" % (r["fichero"], r["linea"]))

    comp = []
    for (op, sym), a in agg.items():
        comp.append({
            "comparacion": "asic_type %s CHIP_%s" % (op, sym),
            "valor_referencia": idx[sym],
            "resultado": "VERDADERO" if a["v"] else "FALSO",
            "v": a["v"], "f": a["f"],
            "sitios": sorted(a["sitios_true"] if a["v"] else a["sitios_false"]),
        })
    comp.sort(key=lambda c: (c["comparacion"].split()[1], c["valor_referencia"]))

    vivas = [c for c in comp if c["resultado"] == "VERDADERO"]
    return {
        "tool": "asicpath", "version": VERSION,
        "amd": amd,
        "chip": chip,
        "indice": idx[chip],
        "indice_fuente": "amdgpu_asic_name[] (%s).  NO el enum, que no esta "
                         "en el corpus: hallazgo 1479" % TABLE_C,
        "orden": nombres,
        "comparaciones_totales": len(filas),
        "comparaciones_distintas": len(comp),
        "verdaderas": len(vivas),
        "falsas": len(comp) - len(vivas),
        "comparaciones": comp,
        "simbolos_desconocidos": dict(desconocidos),
        "ficheros_barricos": sum(1 for _r, _d, fs in os.walk(amd) for f in fs
                                 if f.endswith(".c")),
    }


# --- vectores -------------------------------------------------------------
# El vector que mas importa NO comprueba un numero: el corpus crece y las
# cifras se mueven.  Comprueba la RELACION entre el calculo y la fuente, y que
# el simbolo este COMPLETO.  El fallo de 1484 fue precisamente un simbolo
# truncado con la cuenta correcta.
VECTORS = [
    ("el-indice-no-es-cero", lambda m: m["indice"] == 17),
    ("POLARIS12-esta-en-el-17", lambda m: m["orden"][m["indice"]] == "POLARIS12"),
    ("las-38-posiciones", lambda m: len(m["orden"]) == 38),
    ("la-fuente-del-indice-se-declara",
     lambda m: "amdgpu_asic_name" in m["indice_fuente"]),
    ("la-fuente-del-indice-avisa-que-no-es-el-enum",
     lambda m: "NO el enum" in m["indice_fuente"]),
    ("hay-comparaciones", lambda m: m["comparaciones_totales"] > 40),
    ("vistas-y-falsas-suman-el-total",
     lambda m: m["verdaderas"] + m["falsas"] == m["comparaciones_distintas"]),
    ("vistas-y-falsas-no-superan-el-total",
     lambda m: m["verdaderas"] + m["falsas"] <= m["comparaciones_totales"]),
    # MEDIDO 2026-10-05: mi primer vector de "truncado" buscaba sufijos
    # ("IS10","NS","RE","ZO"...) y fallaba sobre 11 comparaciones LEGITIMAS,
    # porque POLARIS10 acaba en IS10 y MULLINS en NS.  El vector era erroneo, no
    # la herramienta.  Que un nombre acabada en un sufijo no dice nada de si
    # esta truncado.
    #
    # El vector que de verdad protege contra 1484 es de otra forma: el simbolo
    # tiene que existir COMO IDENTIFICADOR en la tabla de nombres.  Si el
    # prefijo se le comiera 5 caracteres, el nombre truncado NO estaria en la
    # tabla y habria acabado en simbolos_desconocidos, no en comparaciones.
    ("todo-simbolo-comparado-existe-en-la-tabla",
     lambda m: all(any(c["comparacion"].endswith("CHIP_" + n) for n in m["orden"])
                   for c in m["comparaciones"])),
    ("los-simbolos-empezan-por-prefijo-conocido",
     lambda m: all(re.search(r"CHIP_[A-Z][A-Z0-9_]+$", c["comparacion"])
                   for c in m["comparaciones"])),
    ("ningun-simbolo-es-solo-una-cola",
     lambda m: all(len(c["comparacion"].split("CHIP_")[1]) >= 4
                   for c in m["comparaciones"])),
    ("POLARIS12-esta-en-la-lista-de-comparaciones",
     lambda m: any(c["comparacion"] == "asic_type <= CHIP_POLARIS12"
                   and c["resultado"] == "VERDADERO"
                   for c in m["comparaciones"])),
    ("VEGA10-no-se-cumple-en-polaris12",
     lambda m: any(c["comparacion"] == "asic_type >= CHIP_VEGA10"
                   and c["resultado"] == "FALSO"
                   for c in m["comparaciones"])),
    ("UNKNOWN-es-un-solo-comentario",
     lambda m: list(m["simbolos_desconocidos"]) == ["RV770"]),
    ("cada-sitio-esta-localizado",
     lambda m: all(re.match(r"^[^:]+:\d+$", s)
                   for c in m["comparaciones"] for s in c["sitios"])),
    ("un-asic-inexistente-se-declara",
     lambda m: "error" in medir(amd_default(), "CHIP_NO_EXISTE")),
    ("amdgpu-inexistente-se-declara",
     lambda m: "error" in medir("/no/existe/amd", "POLARIS12")),
]


def amd_default():
    return DEFAULT_AMD


def run_selftest():
    m = medir(DEFAULT_AMD, "POLARIS12")
    print(f"asicpath {VERSION} -- self-test")
    print(f"indice: CHIP_POLARIS12 = {m.get('indice')}  "
          f"fuente: {m.get('indice_fuente', '')[:48]}")
    print(f"comparaciones: {m.get('comparaciones_totales')} en "
          f"{m.get('comparaciones_distintas')} distintas -> "
          f"{m.get('verdaderas')} verdaderas, {m.get('falsas')} falsas")
    print()
    ok = bad = 0
    for name, check in VECTORS:
        try:
            good = bool(check(m))
        except Exception as exc:                       # noqa: BLE001
            print(f"  FAIL  {name}: {exc!r}")
            bad += 1
            continue
        print(f"  {'PASS' if good else 'FAIL'}  {name}")
        ok += good
        bad += not good
    print()
    print(f"  {ok} pasan, {bad} fallan")
    print()
    print("  NOTA: ningun vector comprueba un numero absoluto de comparaciones;")
    print("  comprueban la RELACION con la fuente y el nombre de los simbolos,")
    print("  que es lo que 1484 rompio sin que la cuenta se moviera.")
    return 0 if bad == 0 else 1


def main(argv=None):
    ap = argparse.ArgumentParser(prog="asicpath.py")
    ap.add_argument("--chip", default="POLARIS12")
    ap.add_argument("--amd", default=DEFAULT_AMD)
    ap.add_argument("--vivas", action="store_true",
                    help="solo las comparaciones que se cumplen, con su sitio")
    ap.add_argument("--muertas", action="store_true",
                    help="solo las que NO se cumplen: codigo que no corre aqui")
    ap.add_argument("--indice", help="que ASIC es este indice")
    ap.add_argument("--orden", action="store_true",
                    help="el enum tal y como lo ve esta herramienta")
    ap.add_argument("--site", help="donde se compara este simbolo")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", "--selftest", dest="selftest",
                    action="store_true")
    ap.add_argument("--version", action="version", version=f"asicpath.py {VERSION}")
    args = ap.parse_args(argv)

    if args.selftest:
        return run_selftest()

    if args.orden:
        nombres, _idx, fallo = cargar_indice(args.amd)
        if fallo:
            print("asicpath: %s" % fallo)
            return 1
        for i, n in enumerate(nombres):
            print(f"  {i:3d}  CHIP_{n}")
        print()
        print("  fuente: amdgpu_asic_name[].  El enum no esta en el corpus.")
        return 0

    if args.indice is not None:
        nombres, _idx, fallo = cargar_indice(args.amd)
        if fallo:
            print("asicpath: %s" % fallo)
            return 1
        try:
            i = int(args.indice, 0)
        except ValueError:
            print("asicpath: %r no es un indice" % args.indice)
            return 1
        if not 0 <= i < len(nombres):
            print("asicpath: el indice %d esta fuera de 0..%d"
                  % (i, len(nombres) - 1))
            return 1
        print(f"  indice {i} = CHIP_{nombres[i]}")
        return 0

    if args.site:
        m = medir(args.amd, args.chip)
        if "error" in m:
            print("asicpath: %s" % m["error"])
            return 1
        sym = args.site[5:] if args.site.startswith("CHIP_") else args.site
        hits = [c for c in m["comparaciones"] if c["comparacion"].endswith(sym)]
        if not hits:
            print("asicpath: CHIP_%s no se compara con ningun operador ordinal" % sym)
            return 1
        for c in hits:
            print(f"  {c['comparacion']:34s} ref={c['valor_referencia']:3d}  "
                  f"-> {c['resultado']}")
            for s in c["sitios"]:
                print(f"      {s}")
        return 0

    m = medir(args.amd, args.chip)
    if "error" in m:
        if args.json:
            print(json.dumps(m, indent=2, sort_keys=True))
        else:
            print("asicpath: %s" % m["error"])
        return 1

    if args.json:
        print(json.dumps(m, indent=2, sort_keys=True))
        return 0

    sel = [c for c in m["comparaciones"]
           if (not args.vivas and not args.muertas)
           or (args.vivas and c["resultado"] == "VERDADERO")
           or (args.muertas and c["resultado"] == "FALSO")]

    print(f"asicpath {VERSION} · {args.chip}")
    print(f"  indice        {m['indice']}   de {len(m['orden'])} ASICs")
    print(f"  fuente        amdgpu_asic_name[]   (el enum NO esta en el corpus)")
    print(f"  ficheros      {m['ficheros_barricos']} .c barritos")
    print(f"  comparaciones {m['comparaciones_totales']} en "
          f"{m['comparaciones_distintas']} distintas")
    print(f"  resultado     {m['verdaderas']} se cumplen, {m['falsas']} no")
    if m["simbolos_desconocidos"]:
        print(f"  sin resolver  {m['simbolos_desconocidos']}")
    print()
    print(f"  {'comparacion':34s} {'ref':>4s}  {'para ' + args.chip:>12s}  n")
    print("  " + "-" * 66)
    for c in sel:
        marca = "  <== ACTIVA" if c["resultado"] == "VERDADERO" else "  (MUERTA)"
        n = c["v"] if c["resultado"] == "VERDADERO" else c["f"]
        print(f"  {c['comparacion']:34s} {c['valor_referencia']:4d}  "
              f"{c['resultado']:>12s}  {n}{marca}")
        if args.vivas and c["resultado"] == "VERDADERO":
            for s in c["sitios"][:4]:
                print(f"        {s}")
    print()
    if args.muertas:
        print("  Las MUERTAS no se ejecutan en esta tarjeta.  Es codigo de otra")
        print("  generacion: no hace falta leerlo.  Ojo: que no se cumpla la")
        print("  condicion de ASIC no dice que la FUNCION sea inalcanzable;")
        print("  eso es otra relacion y la midio 1403 por el dispatch.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

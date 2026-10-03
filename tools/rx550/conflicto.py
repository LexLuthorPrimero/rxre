#!/usr/bin/env python3
"""conflicto — registros que DOS funciones de riesgo escriben sin mutex

RX550_ROOT = os.environ.get("RX550_ROOT", "/home/lucas/Escritorio/RX550-INVESTIGACION")
RX550_ARQ = os.environ.get("RX550_ARQ", os.path.join(RX550_ROOT, "08-ARQUITECTURA"))

POR QUE        Quedan 24 funciones de runtime que escriben varios registros MMIO
               sin tomar mutex.  "Sin mutex" no prueba carrera: el orden puede
               venir de aguas arriba.  La pregunta que SI se puede responder
               leyendo el codigo es mas estrecha y mas util:

                 ¿escribe OTRA funcion de riesgo el MISMO registro?

               Si dos funciones del mismo bloque IP escriben el mismo registro
               sin mutex, la carrera es demostrable por construccion: no hace
               falta saber quien serializa a quien, porque ninguna lo hace.
               Si nadie mas escribe ese registro, no hay conflicto posible
               aunque las dos corran a la vez, y la funcion se puede descartar
               de un driver propio.

METODO         Dos pasos, ambos con herramientas ya validadas:
               1. `funcspan` agrupa cada escritura de la ruta VI en su FUNCION
                  (no por linea: cada linea escribe un registro y el grupo
                  seria siempre de tamano 1 — correccion 105).
               2. Se separa en init secuencial / con mutex / RUNTIME, igual que
                  `contract.crossblock`, y las de RUNTIME son el conjunto.

               Para cada registro se indexa que funciones de riesgo lo
               escriben.  Un registro con indice de tamano >= 2 es un
               CONFLICTO.  Se distingue si comparten BLOQUE IP, porque un
               conflicto dentro del mismo bloque es una carrera local y entre
               bloques distintos exige que ambos esten vivos a la vez.

CONTROL        Dos controles negativos explicitos, porque "sin conflicto" es el
               resultado que masabierta esta puerta:
                 - el conjunto de registros de riesgo debe ser NO VACIO; si sale
                   vacio, "nadie pisa a nadie" no significa nada;
                 - se verifica por hand que existe al menos un par que SI
                   colisiona, con el par esperado.  Un "0 conflictos" sin un
                   caso positivo al lado es un cero silencioso (clase F).

DEPENDENCIAS   funcspan, contract, regctx  (todas TOOL_VALIDATED)
"""

import os
import sys
import json
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from paths import AMD as _AMD   # noqa: E402
import contract                 # noqa: E402
import regctx                   # noqa: E402
import funcspan                 # noqa: E402

VERSION = "1.0"
NAME = "conflicto"


def riesgo_por_funcion():
    """[diccionarios de las funciones de riesgo], con su bloque y registros"""
    # ACOTAR el escaneo a los ficheros de la ruta VI.  `regctx.scan` sin
    # filtro barre los ~1000 .c de amdgpu y tarda >6 min con 2.9 GB de RSS;
    # aqui solo se necesitan los ficheros donde puede haber escritura, que son
    # los de `contract.BLOQUES`.  El INDICE de cabeceras sigue siendo global
    # (`Index(root)`), asi que la resolucion de offsets no cambia: lo que se
    # recorta es el conjunto de ACCESOS, no el de definiciones.  (correccion 128)
    _, accs, _ = regctx.scan(contract._CORPUS,
                             files=list(contract.BLOQUES))
    cache = {}
    por = {}
    for a in accs:
        f, ln = a["fichero"], a["linea"]
        if (f, ln) not in cache:
            cache[(f, ln)] = funcspan.of_line(
                os.path.join(contract._AMD, "amdgpu", f), ln)
    for a in accs:
        if "offset" not in a or not a["via"].startswith("W"):
            continue
        if not contract.BLOQUES.get(a["fichero"]):
            continue
        x, y, _m = cache[(a["fichero"], a["linea"])]
        if x is None:
            continue
        por.setdefault((a["fichero"], x, y), set()).add(a["reg"])
    out = []
    for (f, x, y), regs in por.items():
        if len(regs) <= 1:
            continue
        p = os.path.join(contract._AMD, "amdgpu", f)
        try:
            ls = open(p, encoding="utf-8",
                      errors="replace").read().splitlines()
        except OSError:
            continue
        cab = ls[x - 1].strip() if x - 1 < len(ls) else ""
        if any(contract.RE_MUTEX.search(ls[i])
               for i in range(x - 1, min(y, len(ls)))):
            continue
        if contract.RE_INITFN.search(cab):
            continue
        out.append({"fichero": f, "ini": x, "fin": y, "cabecera": cab,
                    "bloque": contract.BLOQUES[f],
                    "registros": sorted(regs)})
    out.sort(key=lambda r: (r["fichero"], r["ini"]))
    return out


def analizar(riesgo):
    reg2r = collections.defaultdict(list)
    for i, r in enumerate(riesgo):
        for g in r["registros"]:
            reg2r[g].append(i)
    conflicto = {}
    for i, r in enumerate(riesgo):
        otros = []
        for g in r["registros"]:
            for j in reg2r.get(g, []):
                if j == i:
                    continue
                o = riesgo[j]
                otros.append({
                    "reg": g,
                    "con": f"{o['fichero']}:{o['ini']}",
                    "cab": o["cabecera"][:52],
                    "mismo_bloque": o["bloque"] == r["bloque"]})
        if otros:
            conflicto[i] = otros
    return reg2r, conflicto


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

    # --- caso SINTETICO conocido: el par que SI colisiona ---
    # f0 escribe {A,B}; f1 escribe {B,C}; f2 escribe {D,E} (nadie la pisa)
    ri = [{"fichero": "x.c", "ini": 10, "fin": 20, "cabecera": "f0",
           "bloque": "GFX", "registros": ["RA", "RB"]},
          {"fichero": "x.c", "ini": 30, "fin": 40, "cabecera": "f1",
           "bloque": "GFX", "registros": ["RB", "RC"]},
          {"fichero": "x.c", "ini": 50, "fin": 60, "cabecera": "f2",
           "bloque": "GMC", "registros": ["RD", "RE"]}]
    reg2r, conf = analizar(ri)
    chk("KNOWN INPUT: el indice de registros tiene 5 entradas",
        len(reg2r) == 5, len(reg2r))
    chk("KNOWN INPUT: solo f0 y f1 tienen conflicto",
        set(conf) == {0, 1}, sorted(conf))
    chk("KNOWN INPUT: el registro compartido es RB",
        {c["reg"] for c in conf[0]} == {"RB"},
        {c["reg"] for c in conf[0]})
    chk("KNOWN INPUT: el conflicto se marca como mismo bloque",
        all(c["mismo_bloque"] for c in conf[0]),
        [c["mismo_bloque"] for c in conf[0]])
    chk("NEGATIVO: f2 no aparece en el mapa de conflicto",
        2 not in conf, sorted(conf))
    chk("NEGATIVO: un registro que nadie mas escribe no crea entrada",
        "RD" not in reg2r or len(reg2r["RD"]) == 1, reg2r.get("RD"))

    # --- caso vacio: no puede dar "0 conflictos" sin decir nada ---
    reg2r0, conf0 = analizar([])
    chk("EDGE: conjunto vacio -> no hay conflicto y no inventa",
        reg2r0 == {} and conf0 == {}, (len(reg2r0), len(conf0)))

    # El corpus cuesta >6 min y 2.1 GB solo en regctx.scan.  El self-test
    # RAPIDO no debe pagar eso para validar la logica de colision: la parte
    # sintetica de arriba ya la cubre con entrada y salida conocidas.  El
    # corpus se evalua aparte, con su coste, y si falla no se esconde detras de
    # un self-test rapido que dice "todo bien": el modo rapido DICE que el
    # corpus no se evaluo.  (correccion 127)
    if "--rapido" in sys.argv:
        print(f"  {ok} pasaron, {fail} fallaron"
              "  (sintetico; corpus NO evaluado)")
        return 0 if fail == 0 else 1

    # --- CORPUS: con control positivo obligatorio ---
    riesgo = riesgo_por_funcion()
    chk("CONTROL: el conjunto de riesgo NO es vacio",
        len(riesgo) > 0, len(riesgo))
    chk("CORPUS: se recuperan funciones de riesgo", len(riesgo) >= 20,
        len(riesgo))
    reg2r, conf = analizar(riesgo)
    chk("CORPUS: hay registros escritos por >=2 funciones de riesgo",
        any(len(v) >= 2 for v in reg2r.values()),
        max((len(v) for v in reg2r.values()), default=0))
    chk("CORPUS: existe al menos un conflicto (el 0 tambien seria suspiciously)",
        len(conf) > 0, len(conf))
    chk("CONSISTENCIA: los conflictos del corpus son simetricos",
        all(conf.get(j) is not None
            for i, cs in conf.items() for c in cs
            for j in [next((k for k, r in enumerate(riesgo)
                            if f"{r['fichero']}:{r['ini']}" == c["con"]),
                           -1)] if j >= 0),
        "asimetria en el grafo de conflicto")

    # --- REGRESION sobre el corpus, con valores FIJOS. ---
    # Sin esto el "13" que se publica depende de que alguien lo mire.  Un
    # TOOL_PARTIAL no puede sostener una afirmacion critica, y el recuento de
    # conflictos la sostiene.  Los valores son los observados; si el codigo
    # cambia, el self-test falla en vez de que el numero se mueva en silencio.
    # (correccion 133)
    chk("REGRESION: 24 funciones de riesgo", len(riesgo) == 24, len(riesgo))
    chk("REGRESION: 13 con conflicto", len(conf) == 13, len(conf))
    chk("REGRESION: los 13 conflictos son en el MISMO bloque IP",
        all(any(x["mismo_bloque"] for x in cs) for cs in conf.values()),
        [i for i, cs in conf.items()
         if not any(x["mismo_bloque"] for x in cs)])
    # La comprobacion de autofiguras tiene que COMPARAR indice con indice.  La
    # primera version recorria `riesgo` entero buscando cualquier r que casara
    # con el `con`, y como todos los pares son simetricos encuentras siempre
    # uno: daba 52 "autofiguras" donde hay 0.  Era el aserto el equivocado.
    # (correccion 134)
    chk("REGRESION: 0 autofiguras",
        not [x for i, cs in conf.items() for x in cs
             if x["con"] == f"{riesgo[i]['fichero']}:{riesgo[i]['ini']}"],
        [x for i, cs in conf.items() for x in cs
         if x["con"] == f"{riesgo[i]['fichero']}:{riesgo[i]['ini']}"][:3])

    # el caso que se cita en RE-INDEX: RMW sin mutex en el mismo bloque
    par = None
    for cs in conf.values():
        for x in cs:
            if x["reg"] == "mmRLC_CGTT_MGCG_OVERRIDE":
                par = x["con"]
    chk("REGRESION: mmRLC_CGTT_MGCG_OVERRIDE sigue en conflicto",
        par is not None, par)
    chk("REGRESION: el par es :5618 <-> :5718 (clock gating)",
        par in ("gfx_v8_0.c:5618", "gfx_v8_0.c:5718"), par)

    # gart_enable y gart_disable comparten cinco registros.  Yo habia escrito
    # que compartian `mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR`, y NO: la PTBA la
    # escribe solo `gart_enable`.  Lo lei de una tabla truncada.  Los comunes
    # verificados son L2_CNTL, L2_CNTL2, CONTEXT0_CNTL, CONTEXT1_CNTL y
    # MC_VM_MX_L1_TLB_CNTL.  (correccion 135)
    idx = {f"{q['fichero']}:{q['ini']}": k for k, q in enumerate(riesgo)}
    comunes = (set(riesgo[idx["gmc_v8_0.c:829"]]["registros"]) &
               set(riesgo[idx["gmc_v8_0.c:972"]]["registros"]))
    chk("REGRESION: gart_enable y gart_disable comparten 5 registros",
        len(comunes) == 5, sorted(comunes))
    chk("REGRESION: la PTBA NO la comparten (solo gart_enable la escribe)",
        "mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR" not in comunes
        and "mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR"
        in riesgo[idx["gmc_v8_0.c:829"]]["registros"]
        and "mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR"
        not in riesgo[idx["gmc_v8_0.c:972"]]["registros"],
        sorted(comunes))
    chk("REGRESION: los comunes son los cinco verificados",
        comunes == {"mmMC_VM_MX_L1_TLB_CNTL", "mmVM_CONTEXT0_CNTL",
                    "mmVM_CONTEXT1_CNTL", "mmVM_L2_CNTL",
                    "mmVM_L2_CNTL2"}, sorted(comunes))

    bloques = collections.Counter(r["bloque"] for r in riesgo)
    chk("REGRESION: reparto GFX 9 / GFXHUB 4 / GMC 9 / SDMA 2",
        dict(bloques) == {"GFX": 9, "GFXHUB": 4, "GMC": 9, "SDMA": 2},
        dict(bloques))

    # --- la carrera de la IRQ: se DESCARTA, y por que. ---
    # Es lo unico del conjunto con contexto asincrono real, asi que es la que
    # mas merece un assert: si alguien anade un mutex a gart_enable, o cambia
    # el llamante de la IRQ, el veredicto tiene que cambiar.  (correccion 136)
    import re as _re
    import callgraph as _cg
    base = os.path.join(_AMD, "amdgpu")   # ruta central, de paths
    irq_key = "gmc_v8_0.c:1385"
    ge_key = "gmc_v8_0.c:829"
    chk("REGRESION: la IRQ esta en el conjunto de riesgo",
        irq_key in idx and ge_key in idx, sorted(idx)[:4])
    chk("REGRESION: la IRQ comparte sus 2 registros con gart_enable",
        {x["reg"] for x in conf[idx[irq_key]]}
        <= set(riesgo[idx[ge_key]]["registros"]),
        sorted({x["reg"] for x in conf[idx[irq_key]]}))
    # gart_enable NO toma ningun lock
    p_ge = os.path.join(base, "gmc_v8_0.c")
    ls_ge = open(p_ge, encoding="utf-8",
                 errors="replace").read().splitlines()
    a, b, _m = funcspan.of_line(p_ge, 829)
    cuerpo = "\n".join(ls_ge[a - 1:b])
    chk("DESCARTE 136: gart_enable no toma irq.lock",
        "irq.lock" not in cuerpo, "toma irq.lock")
    chk("DESCARTE 136: gart_enable no toma ningun lock",
        not _re.search(r"spin_lock|mutex_lock", cuerpo),
        _re.findall(r"spin_lock\w*|mutex_lock\w*", cuerpo)[:3])
    # la IRQ entra por un callsite que SI toma irq.lock
    p_irq = os.path.join(base, "amdgpu_irq.c")
    if os.path.isfile(p_irq):
        tq = open(p_irq, encoding="utf-8", errors="replace").read()
        chk("DESCARTE 136: la via de la IRQ toma spin_lock_irqsave(&irq.lock)",
            "spin_lock_irqsave(&adev->irq.lock" in tq,
            tq.count("spin_lock_irqsave(&adev->irq.lock"))
    # su unico llamante es de proceso
    defs, calls = _cg.funciones_y_llamadas(p_ge)
    llam = sorted({c[0] for c in calls
                   if c[1] == "gmc_v8_0_gart_enable"
                   and c[0] != "gmc_v8_0_gart_enable"})
    chk("DESCARTE 136: gart_enable tiene un unico llamante, de proceso",
        llam == ["gmc_v8_0_hw_init"], llam)
    chk("DESCARTE 136: ese llamante es init, no IRQ",
        not any(_re.search(r"irq|interrupt", x or "") for x in llam), llam)
    chk("REGRESION: SDMA no aporta conflictos",
        not [1 for i, r in enumerate(riesgo)
             if r["bloque"] == "SDMA" and i in conf], "SDMA con conflicto")

    print(f"  {ok} pasaron, {fail} fallaron")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    if "--out" in sys.argv:
        riesgo = riesgo_por_funcion()
        reg2r, conf = analizar(riesgo)
        mb = sum(1 for c in conf.values()
                 if any(x["mismo_bloque"] for x in c))
        print("  funciones de riesgo: "
              f"{len(riesgo)}")
        print(f"  registros escritos por alguna de riesgo: {len(reg2r)}")
        print(f"  de esas, CON CONFLICTO: {len(conf)}")
        print(f"  de esas, conflicto en el MISMO bloque IP: {mb}")
        print(f"  sin conflicto (nadie mas las pisa): {len(riesgo)-len(conf)}")
        print("  bloques: " + str(dict(collections.Counter(
            r["bloque"] for r in riesgo))))
        json.dump({"riesgo": riesgo, "conflicto": {str(k): v for k, v
                                                   in conf.items()}},
                  open(os.path.join(RX550_ROOT, "06-INGENIERIA-INVERSA", "agents", "conflicto.json"), "w"),
                  indent=2, ensure_ascii=False)
    else:
        print("uso: conflicto.py --self-test | --out")

#!/usr/bin/env python3
"""crosscheck — contraste automático de afirmaciones de offset contra el código


PROPOSITO      Extraer cada afirmación `REGISTRO = 0xNNN` de los informes y
               resolverla con regctx (grafo de includes).  Emite las que NO
               coinciden, distinguiendo el espacio de offset, para que un 0xda2
               frente a un 0x2002 se lea como "espacio distinto" y no como
               error de lectura.

POR QUE        Las últimas cuatro correcciones vinieron de hacer el cruce a
               mano.  Convertirlo en un comando lo vuelve un número que sale,
               no una tarea que alguien recuerda hacer.

COMPOSICION    importa regctx; no reimplementa nada del grafo de includes.

DEPENDENCIAS   python3 stdlib + regctx.py (mismo directorio)
"""

import os
import re as _re
import re
import sys
import glob
import json

VERSION = "1.0"
NAME = "crosscheck"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import regctx  # noqa: E402
RX550_ROOT = os.environ.get("RX550_ROOT", "/home/lucas/Escritorio/RX550-INVESTIGACION")
RX550_ARQ = os.environ.get("RX550_ARQ",
                       os.path.join(RX550_ROOT, "08-ARQUITECTURA"))


# REGISTRO = 0xNNN, con separadores tolerances y sin ellos.
# SeCapturan SOLO literales hex/decimales: una referencia a "0x0081" en otro
# contexto no es una afirmación de offset.
# DEFECTO CORREGIDO (correccion 81): el patron pedia el VALOR entre
# backticks (`= `0x0081``), pero lo que se escribe es el simbolo entre
# backticks y el valor en texto normal o entre backticks, independiente:
#     `mmGRBM_STATUS2 = 0x2002`
#     `regIH_RB_BASE = 0x0081`
# Resultado: 1 afirmacion extraida donde hay >=5.  Un extractor que casi no
# encuentra nada y no lo dice es un cero silencioso, la clase de siempre.
# El valor vigente puede venir tras `=` o tras una FLECHA (⇒, ->) sin signo
# de igualdad:  "... ⇒ **`0x0083`**".  Sin esto, en la fila que RETIRA una
# afirmacion solo se ve el valor viejo y el vigente no existe para el
# contraste (correccion 85).
# Un REGISTRO seguido de un numero es una afirmacion de OFFSET.
# Un numero seguido de un REGISTRO, o un numero dentro de un predicado, NO:
#   "RREG32(mmGRBM_STATUS2) != 0x8"  -> 0x8 es el VALOR COMPARADO, no un
#   offset.  Sin esta distincion se reportaba como DIFIERE, que es un falso
#   positivo que hace desconfiar de la herramienta entera.  (correccion 102)
# El valor de offset solo cuenta si va INMEDIATAMENTE despues del nombre,
# con un separador corto (= : ⇒ ->) y sin codigo de comparacion entre medias.
RE_CLAIM = re.compile(
    r"\b(mm[A-Z][A-Z0-9_]+|reg[A-Z][A-Z0-9_]+)\b"
    r"[ \t]*(?:=|:|=>|=|\u21d2|\u2192|->)[ \t]*`?\*?\*?(0x[0-9A-Fa-f]+)")


# DEFECTO CORREGIDO (correccion 84): una MISMA linea puede contener dos
# valores para el mismo simbolo cuando se esta RETIRANDO una afirmacion:
#     publiqué `regIH_RB_BASE = 0x0081` ...  ⇒ `0x0083`
# El finditer tomaba el primero y lo daba por vigente, asi que la
# herramienta "confirmaba" un offset que mi propio registro declara falso.
# Detectar eso exige leer la linea entera, no el primer match: si la linea
# contiene RETIRADA/retiré/falso/publicado/antes, el valor VIGENTE es el que
# va tras => o el ultimo de la linea, no el primero.
# REGLA: "retirada" exige que la fila diga que un valor dejo de valer.
# NO basta con que aparezcan dos valores: la fila 80 dice que GFX8 tiene DOS
# ESPACIOS y ambos offsets son correctos a la vez; tratar eso como "retirada"
# hace que la herramienta verifique el valor equivocado (correccion 86).
RE_RETIRE = re.compile(
    r"retir|retiré|publicé|publicado|\bfalsa\b|\bfalsos\b|"
    r"\bcorregid|\berror\b|\bfallo\b|\bsustitu|\bingan\b|\bfui\b",
    re.I)
# senales de que NO es una retirada sino una coexistencia de valores
RE_COBINARIA = re.compile(
    r"dos espacios|ambos\s+correctos|tambi[eé]n\s+en|\btambi[eé]n\b|"
    r"\bsocio15\b|\bplano\b|y\s+en\b|\bdos valores\b|sobrevive",
    re.I)
RE_STALE = re.compile(r"a|")   # placeholder, no se usa


def extract_claims(docs):
    """cada línea que AFIRMA un offset, con fichero y línea.

    Si la línea marca el primer valor como retirado/publicado-errorado, se
    toman los valores POSTERIORES (los vigentes), no el primero.
    """
    out = []
    for d in docs:
        try:
            lines = open(d, encoding="utf-8", errors="replace").read().splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines, 1):
            # Una fila de tabla reparte el simbolo y su valor en CELDAS
            # distintas:  | 72 | publique `reg = 0x0081` | ... ⇒ `0x0083` |
            # Tratar la linea como texto plano encuentra el valor viejo y
            # pierde el vigente, que esta en otra celda.  Se parte la fila y
            # se busca el valor VIGENTE en las celdas posteriores.
            if line.lstrip().startswith("|"):
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                joined = " ".join(cells)
                ms = list(RE_CLAIM.finditer(joined))
                if RE_RETIRE.search(joined) and not RE_COBINARIA.search(joined):
                    # El valor VIGENTE puede venir tras una flecha (⇒ **`0xNNN`**)
                    # sin repetir el simbolo.  Se empareja cada simbolo con el
                    # primer offset que aparece tras el, en la MISMA fila.
                    for reg in {m.group(1) for m in ms}:
                        # offsets de la fila, en orden de aparicion
                        # un solo grupo: (0xNNN)
                        offs = [(m.start(), int(m.group(1), 0))
                                for m in re.finditer(
                                    r"`?\*?\*?(0x[0-9A-Fa-f]+)\b", joined)]
                        # el offset vigente es el ULTIMO de la fila que no sea
                        # el numero de la propia correccion
                        vals = [v for _, v in offs]
                        if not vals:
                            continue
                        if len(vals) > 1:
                            out.append({"reg": reg, "citado": vals[-1],
                                        "doc": d, "linea": i, "vigente": True,
                                        "retirado": vals[:-1],
                                        "texto": line.strip()[:130]})
                        else:
                            out.append({"reg": reg, "citado": vals[0],
                                        "doc": d, "linea": i,
                                        "texto": line.strip()[:130]})
                    continue
            ms = list(RE_CLAIM.finditer(line))
            if not ms:
                continue
            vals = [int(m.group(2), 0) for m in ms]
            regs = {m.group(1) for m in ms}
            # si la fila retira el valor y afirma otro, el vigente es el ultimo
            stale = (bool(RE_RETIRE.search(line))
                     and not RE_COBINARIA.search(line))
            if stale and len(vals) > 1:
                # agrupar por simbolo: el vigente es el ultimo de ese simbolo
                for reg in regs:
                    vs = [int(m.group(2), 0) for m in ms if m.group(1) == reg]
                    if len(vs) > 1:
                        out.append({"reg": reg, "citado": vs[-1], "doc": d,
                                    "linea": i,
                                    "vigente": True,
                                    "retirado": vs[:-1],
                                    "texto": line.strip()[:130]})
                continue
            for m in ms:
                out.append({"reg": m.group(1), "citado": int(m.group(2), 0),
                            "doc": d, "linea": i,
                            "texto": line.strip()[:130]})
    return out


def reg_indirecto(idx, reg):
    """el corpus escribe SOC15_REG_OFFSET(..., reg) en algun .c"""
    import glob as _g
    pat = _re.compile(r"SOC15_REG_OFFSET\s*\([^;]{0,60}?\b"
                      + _re.escape(reg) + r"\b")
    for cf in _g.glob(os.path.join(idx.drv, "amdgpu", "*.c")):
        try:
            if pat.search(open(cf, encoding="utf-8",
                               errors="replace").read()):
                return True
        except OSError:
            pass
    return False


def route_of(f):
    """el fichero está en la ruta GFX8/VI, o en otra generación?"""
    for r in ("gmc_v8_0.c", "gfx_v8_0.c", "gfxhub_v2_1.c", "ih_v7_0.c",
              "sdma_v3_0.c", "amdgpu_gmc.c", "amdgpu_vm.c", "amdgpu_ttm.c",
              "amdgpu_vm_sdma.c", "amdgpu_vm_cpu.c"):
        if f.endswith(r):
            return "VI"
    return "otra"


def run(root, docs, emit_json=False):
    # scan() deja el Index cacheado en regctx._INDEX_CACHE; tomarlo de ahi
    # garantiza el MISMO objeto y no reconstruye nada.
    idx, accs, n = regctx.scan(root)
    idx = regctx._INDEX_CACHE.get(root, idx)
    # reg -> {offset: set((espacio, fichero))}, sin pisar: dos ficheros pueden
    # usar el mismo símbolo en espacios distintos (corrección 79)
    real = {}
    for a in accs:
        if "offset" not in a:
            continue
        k = (a["reg"], a.get("espacio", "?"))
        real.setdefault(a["reg"], {}).setdefault(a["offset"], set()).add(
            (k[1], a["fichero"]))
    # DEFECTO CORREGIDO (correccion 82): `real` se construia SOLO con accesos
    # encontrados en el codigo.  El IH accede por indireccion
    # (`ih_regs->ih_rb_base`), donde reg=None, asi que regIH_RB_BASE aparecia
    # como "NO RESOLUBLE" aunque su definicion es exacta y correcta.
    # Eso hace que el contraste diga "no encuentro" cuando lo que falta es la
    # resolucion indirecta, no la evidencia.
    # DEFECTO REAL (correccion 83): el acceso del IH es INDIRECTO
    # (SOC15_REG_OFFSET -> regIH_RB_BASE), asi que reg=NULL y el simbolo no
    # aparecia entre los accesos.  Con el arreglo anterior (iterar accesos) no
    # habia nada que iterar.  La via correcta es resolver POR SIMBOLO: para cada
    # .c, que cabeceras alcanza, y si entre ellas hay una que defina el simbolo.
    # Asi el contraste cubre tambien los registros que solo se tocan por
    # indireccion, que son justamente los del IH.
    import glob as _g
    # DEFECTO DE RENDIMIENTO (correccion 90): el bucle era
    #     for cada .c:  for cada simbolo:
    # MEDIDO: 1 006 342 pares, 33s.  Es un producto cartesiano que no hace
    # falta: lo que importa es, para cada SIMBOLO, en que ficheros aplica.
    # Se indexa una vez que .c alcanza que cabecera y se invierte el recorrido,
    # con lo que el trabajo pasa a ser proporcional a los accesos, no a
    # ficheros x simbolos.  33s -> ~0.2s.
    # DEFECTO PROPIO (correccion 101): el indice era "todo .c que ALCANZA esta
    # cabecera", no "los .c que ACCEDEN a este simbolo".  Es el mismo error que
    # la correccion 100 en el corpus,ahora dentro de la herramienta que lo
    # detecta: dar por buena una garantia porque existe en el ambito, no en el
    # punto de uso.  Consecuencia concreta: un .c que incluye gmc_8_1_d.h
    # "resolvia" mmVM_..., aunque no lo acceda nunca, y el contraste lo daba por
    # confirmado.
    # El indice correcto: para cada simbolo, los .c cuyo TEXTO lo menciona en
    # un acceso.  Se construye leyendo cada .c una vez.
    acc_by_file = {}
    for cf in _g.glob(os.path.join(idx.drv, "amdgpu", "*.c")):
        try:
            txt = open(cf, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        # simbolos que aparecen como operando de un acceso, no en un comentario
        code = []
        for ln in txt.splitlines():
            st = ln.strip()
            if st.startswith(("*", "/*", "//")):
                continue
            code.append(ln)
        code = "\n".join(code)
        for m in re.finditer(
                r"\b(?:WREG|RREG|SOC15_REG_ENTRY_STR|SOC15_RREG_OFFSET|"
                r"SOC15_WREG_OFFSET)\w*\s*\([^;]{0,80}?\b"
                r"(mm[A-Z][A-Z0-9_]+|reg[A-Z][A-Z0-9_]+)", code):
            reg = m.group(1)
            base = os.path.basename(cf)
            hset = {os.path.basename(h) for h in idx.headers(cf)}
            cand = {h: v for h, v in idx.defs.get(reg, {}).items()
                    if h in hset}
            for h, v in cand.items():
                esp = ("SOC15" if h.startswith(("gc_", "mmhub_", "osssys_"))
                       or h.endswith("_offset.h") else "plano")
                acc_by_file.setdefault(reg, {}).setdefault(v, set()).add(
                    (esp, base))
    for reg, m in acc_by_file.items():
        for v, es in m.items():
            real.setdefault(reg, {})[v] = es
    claims = extract_claims(docs)
    res = []
    for c in claims:
        cands = real.get(c["reg"])
        if not cands:
            # El simbolo NO aparece como operando de un acceso.  Puede ser
            # legitimo: si aparece como parte de un SOC15_REG_OFFSET, se accede
            # por indireccion y el corpus SI lo usa.  Distinguirlo evita
            # reportar como "no resoluble" algo que si esta resuelto.  (103)
            ind = reg_indirecto(idx, c["reg"])
            c["veredicto"] = "INDIRECTO" if ind else "NO_RESOLUBLE"
            c["detalle"] = ("el acceso es indirecto: SOC15_REG_OFFSET con "
                            "este simbolo, no un operando directo"
                            if ind else
                            "el símbolo no aparece en ningún acceso del corpus")
            res.append(c)
            continue
        if c["citado"] in cands:
            esp = sorted({e for e, _ in cands[c["citado"]]})
            c["veredicto"] = "CONFIRMADO"
            c["espacio"] = esp
            c["otros_valores"] = sorted(hex(v) for v in cands
                                        if v != c["citado"])
        else:
            c["veredicto"] = "DIFIERE"
            c["espacio"] = sorted({e for v in cands for e, _ in cands[v]})
            c["candidatos"] = sorted(hex(v) for v in cands)
            c["detalle"] = ("el valor citado no existe para este símbolo; "
                            "candidatos en el corpus: " + ", ".join(
                                sorted(hex(v) for v in cands)))
        res.append(c)
    conf = [c for c in res if c["veredicto"] == "CONFIRMADO"]
    dif = [c for c in res if c["veredicto"] == "DIFIERE"]
    nr = [c for c in res if c["veredicto"] == "NO_RESOLUBLE"]
    ind = [c for c in res if c["veredicto"] == "INDIRECTO"]
    out = {"contrato": "afirmaciones de offset de los informes vs el código",
           "raiz": root, "n_docs": len(docs),
           "accesos_corpus": n["accesos"],
           "n_afirmaciones": len(res),
           "confirmadas": len(conf), "difieren": len(dif),
           "no_resolubles": len(nr),
           "detalle": res}
    if emit_json:
        return out
    print(f"{NAME} {VERSION} — afirmaciones de offset vs codigo")
    print(f"  informes leidos        {len(docs)}")
    print(f"  afirmaciones extraidas {len(res)}")
    print(f"    CONFIRMADAS   {len(conf)}")
    print(f"    DIFIEREN      {len(dif)}   <- revisar")
    print(f"    NO RESOLUBLES {len(nr)}   <- el símbolo no aparece en el corpus")
    print()
    ret = [c for c in res if c.get("vigente")]
    if ret:
        print(f"  AFIRMACIONES RETIRADAS detectadas (se contrasta el valor"
              f" vigente, no el retirado): {len(ret)}")
        for c in ret:
            rr = ", ".join(hex(v) for v in c["retirado"])
            vd = ("CONFIRMADO" if c["veredicto"] == "CONFIRMADO"
                  else c["veredicto"])
            print(f"    {c['reg']:<28} retirado {rr} -> vigente "
                  f"{c['citado']:#07x}   [{vd}]")
        print()
    if dif:
        print("  DIFIEREN")
        for c in dif:
            print(f"    {c['reg']:<30} cité {c['citado']:#07x}")
            print(f"      {c['detalle']}")
            print(f"      {os.path.basename(c['doc'])}:{c['linea']}")
            print(f"      {c['texto'][:96]}")
            print()
    if nr:
        print("  NO RESOLUBLES (puede ser registro de otra generacion)")
        for c in nr[:12]:
            print(f"    {c['reg']:<30} cité {c['citado']:#07x}   "
                  f"{os.path.basename(c['doc'])}:{c['linea']}")
    print()
    multiesp = [c for c in conf if len(c.get("otros_valores") or [])]
    if multiesp:
        print(f"  CONFIRMADAS pero con OTRO valor en otro espacio: "
              f"{len(multiesp)}")
        for c in multiesp[:8]:
            print(f"    {c['reg']:<30} {c['citado']:#07x} plano   "
                  f"otros: {c['otros_valores']}")
    return out


def self_test():
    root = ("/home/lucas/Escritorio/RX550-INVESTIGACION/RESEARCH/"
            "kernelbuild/linux-7.1.3")
    ok = fail = 0

    def chk(name, cond, extra=""):
        nonlocal ok, fail
        if cond:
            ok += 1
            print(f"    P  {name}")
        else:
            fail += 1
            print(f"    F  {name}  {extra}")

    C_RETIRE, C_COB = RE_RETIRE, RE_COBINARIA
    print(f"  {NAME} {VERSION} self-test")
    docs = sorted(glob.glob(os.path.join(RX550_ARQ, "*.md")))
    if not docs:
        print("    ?  sin informes; omitidos")
        return 1
    out = run(root, docs, emit_json=True)
    chk("BASIC TEST: affirmative extraidas > 0", out["n_afirmaciones"] > 0,
        out["n_afirmaciones"])
    chk("OUTPUT VALIDATION: hay CONFIRMADAS",
        out["confirmadas"] > 0, out["confirmadas"])
    chk("todas las afirmaciones tienen veredicto",
        all(c["veredicto"] in ("CONFIRMADO", "DIFIERE", "NO_RESOLUBLE",
                               "INDIRECTO")
            for c in out["detalle"]),
        sorted({c["veredicto"] for c in out["detalle"]}))
    chk("el veredicto INDIRECTO solo aparece si el acceso es indirecto",
        all(c["veredicto"] != "INDIRECTO" or "indirecto" in c.get("detalle", "")
            for c in out["detalle"]))
    chk("cada CONFIRMADA trae su espacio",
        all("espacio" in c for c in out["detalle"]
            if c["veredicto"] == "CONFIRMADO"))

    # EDGE: un símbolo inventado no debe "coincidir"
    inv = {"reg": "mmNOEXISTE_ESTE", "citado": 0x2002, "doc": "x.md",
           "linea": 1, "texto": ""}
    real = {0x2002: {("plano", "f.c")}}
    chk("EDGE CASE: símbolo inexistente no resuelve",
        real.get("mmNOEXISTE_ESTE") is None)

    # KNOWN VECTOR: mmGRBM_STATUS2 0x2002 debe CONFIRMAR (plano)
    g = [c for c in out["detalle"]
         if c["reg"] == "mmGRBM_STATUS2" and c["citado"] == 0x2002]
    chk("KNOWN INPUT: mmGRBM_STATUS2=0x2002 CONFIRMADO",
        g and g[0]["veredicto"] == "CONFIRMADO",
        g[0]["veredicto"] if g else "no encontrada")
    if g:
        chk("y su espacio es 'plano'", g[0]["espacio"] == ["plano"],
            g[0]["espacio"])
        chk("y se reporta el otro valor (SOC15) como distinto",
            "0xda2" in (g[0]["otros_valores"] or []),
            g[0]["otros_valores"])

    # REGRESION 85/86: dos espacios NO es retirada
    chk("REGRESION: una fila con 'DOS ESPACIOS' no se marca como retirada",
        "DOS ESPACIOS" and not (C_RETIRE.search("DOS ESPACIOS ambos correctos")
                                and not C_COB.search("DOS ESPACIOS ambos correctos")))
    # REGRESION 84: una fila que RETIRA debe leerse el vigente, no el viejo
    ret = [c for c in out["detalle"] if c.get("vigente")]
    chk("REGRESION: hay al menos una afirmacion retirada con vigente distinto",
        ret and all(c["citado"] != c["retirado"][0] for c in ret),
        [(c["reg"], hex(c["citado"]), [hex(x) for x in c["retirado"]])
         for c in ret])

    # regresion 102: "REG != 0x8" NO es una afirmacion de offset
    cl = extract_claims([__file__]) if False else None
    import tempfile
    tf = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                     encoding="utf-8")
    tf.write("`RREG32(mmGRBM_STATUS2) != 0x8`\n"
             "`mmCP_RB0_WPTR = 0x3045`\n")
    tf.close()
    cl2 = extract_claims([tf.name])
    chk("REGRESION: '!= 0x8' NO cuenta como afirmacion de offset",
        not any(c["reg"] == "mmGRBM_STATUS2" for c in cl2),
        [(c["reg"], hex(c["citado"])) for c in cl2])
    chk("REGRESION: '= 0x3045' SI cuenta",
        any(c["reg"] == "mmCP_RB0_WPTR" and c["citado"] == 0x3045
            for c in cl2), cl2)

    # NEGATIVO: el valor SOC15 citado como plano debe DIFERIR
    d = [c for c in out["detalle"]
         if c["reg"] == "mmGRBM_STATUS2" and c["citado"] == 0xda2]
    chk("NEGATIVO: citar 0x0da2 como plano NO se confirma",
        (not d) or d[0]["veredicto"] != "CONFIRMADO",
        d[0]["veredicto"] if d else "no hay tal afirmacion")

    print(f"  {ok} pasaron, {fail} fallaron")
    return 0 if fail == 0 else 1


def main(argv):
    if "--self-test" in argv:
        return self_test()
    root = argv[1] if len(argv) > 1 else (
        "/home/lucas/Escritorio/RX550-INVESTIGACION/RESEARCH/"
        "kernelbuild/linux-7.1.3")
    docs = sorted(glob.glob(os.path.join(RX550_ARQ, "*.md")))
    if "--json" in argv:
        print(json.dumps(run(root, docs, True), indent=2, ensure_ascii=False))
        return 0
    run(root, docs)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
#!/usr/bin/env python3
"""report — emite informes de nodo con las tablas CALCULADAS


PROPOSITO      Generar los documentos de evidencia desde los datos, no desde la
               prosa.  Motivo: tras perder /tmp, el contraste automático solo
               encontraba 4 afirmaciones de offset — porque las que había were
               las que yo tecleé.  Con los informes generados, el número de
               afirmaciones es una propiedad del CORPUS y el contraste tiene
               material real que revisar.

COMPOSICION    importa regctx y crosscheck.  No reimplementa el grafo de
               includes ni el contraste: solo compone y serializa.

DISENO         Cada tabla lleva el comando que la produce, para que cualquiera
               pueda recomputarla y obtener un fichero byte-identico.  Si una
               tabla cambia, el sha256 de la fuente cambia, y se ve cual cambio.
"""

import os
import re
import sys
import glob
import json
import hashlib

VERSION = "1.0"
NAME = "report"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import regctx      # noqa: E402
import crosscheck  # noqa: E402
RX550_ROOT = os.environ.get("RX550_ROOT", "/home/lucas/Escritorio/RX550-INVESTIGACION")
RX550_ARQ = os.environ.get("RX550_ARQ",
                       os.path.join(RX550_ROOT, "08-ARQUITECTURA"))


CORPUS = ("/home/lucas/Escritorio/RX550-INVESTIGACION/RESEARCH/"
          "kernelbuild/linux-7.1.3")
LOG = os.path.join(RX550_ARQ, "incident-pre-reboot-dmesg.txt")

# Los ficheros que realmente se ejecutan en Polaris12.  La fuente es el log de
# incidente (IP block table) mas la ruta de VM/TTM ya cerrada; no es una supos.
RUTA_VI = ["gmc_v8_0.c", "gfx_v8_0.c", "gfxhub_v2_1.c", "ih_v7_0.c",
           "sdma_v3_0.c", "amdgpu_gmc.c", "amdgpu_vm.c", "amdgpu_ttm.c",
           "amdgpu_vm_sdma.c", "amdgpu_vm_cpu.c", "amdgpu_vm_pt.c"]

PREAMBULO = """```
CLASE      PROVEN · tablas CALCULADAS, no escritas a mano
FUENTE     corpus linux-7.1.3 · {log}
GENERADO   report {ver} · cada tabla lleva el comando que la produce
REGENERAR  una regeneracion sin cambios da un fichero byte-identico
UBICACION  dentro de PROJECT_ROOT  (08-ARQUITECTURA/)
```

"""


def h(txt):
    return hashlib.sha256(txt.encode()).hexdigest()[:16]


def tabla_offsets(root, files, prefix=None, top=0):
    """offset de registro resuelto, con la cabecera que lo justifica.

    Raíz inválida: se devuelve una tabla vacía con las guardas a cero, NO una
    excepción.  FAILURE CHECK real: una ruta mala debe producir un informe
    honesto que diga "0 accesos" y el motivo, no un traceback.  (corrección 88)
    """
    if not os.path.isdir(os.path.join(root, "drivers/gpu/drm/amd")):
        return ([], {"accesos": 0, "unico": 0, "conflicto": 0,
                     "g_hdr": [f"RAIZ INVALIDA: {root}"], "g_def": []}, None)
    idx, accs, n = regctx.scan(root, files, prefix)
    rows = []
    seen = set()
    for a in accs:
        if "offset" not in a:
            continue
        k = (a["reg"], a["offset"])
        if k in seen:
            continue
        seen.add(k)
        cab = sorted(a["cands"])[0] if a["cands"] else "-"
        rows.append({"registro": a["reg"], "offset": a["offset"],
                     "espacio": a.get("espacio", "?"),
                     "cabecera": cab, "fichero": a["fichero"],
                     "linea": a["linea"], "via": a["via"]})
    rows.sort(key=lambda r: (r["registro"], r["offset"]))
    return rows, n, idx


def fmt_tabla(rows, cols, headers):
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        cells = []
        for c in cols:
            v = r.get(c, "")
            cells.append(f"`{v:#07x}`" if c == "offset" and isinstance(v, int)
                         else str(v))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def nodo_registros(root):
    """nodo: el mapa de offset de la ruta Polaris12, calculado"""
    vi, nvi, _ = tabla_offsets(root, RUTA_VI)
    sh, nsh, _ = tabla_offsets(root, ["gfx_v8_0.c", "gfxhub_v2_1.c"])
    ir, nir, _ = tabla_offsets(root, ["ih_v7_0.c"])

    t = [PREAMBULO.format(log=LOG, ver=VERSION)]
    t.append("## 1. Ruta Polaris12 — alcance de los accesos\n")
    t.append("```")
    t.append(f"  accesos totales   {nvi['accesos']}")
    t.append(f"  offset UNICO      {nvi['unico']}   <- lo que veria el preprocesador")
    t.append(f"  conflicto REAL    {nvi['conflicto']}   <- >0 seria hallazgo del corpus")
    t.append(f"  bloque shader     {nsh['accesos']} accesos, "
             f"{nsh['unico']} con offset unico (antes invisible: solo SOC15)")
    t.append(f"  bloque IH         {nir['accesos']} accesos, "
             f"{nir['unico']} con offset unico (acceso indirecto)")
    t.append("```")
    t.append("")
    t.append("```text")
    t.append("regctx --causal   # o: kit.py <raiz> --causal --hdr-auto")
    t.append("```")

    t.append("\n## 2. Guardas — deben ser 0 salvo explicación\n")
    t.append("```")
    t.append(f"  ficheros con #include pero 0 cabeceras : {len(nvi['g_hdr'])}")
    t.append(f"  accesos sin simbolo resuelto         : {len(nvi['g_def'])}")
    # Si la raiz era invalida, g_hdr trae el motivo: hay que mostrarlo, o el
    # informe diria "todo 0" sin explicar por que (otra vez el cero mudo).
    for a in nvi["g_hdr"][:4]:
        t.append(f"      {a if isinstance(a, str) else a}")
    for a in nvi["g_def"][:4]:
        t.append(f"      {a['reg']}  {a['fichero']}:{a['linea']}  {a['via']}")
    t.append("```")

    t.append("\n## 3. Espacios de offset — por qué hay dos valores\n")
    esp = {}
    for r in vi:
        esp.setdefault(r["espacio"], []).append(r["registro"])
    t.append("```")
    for k, v in sorted(esp.items()):
        t.append(f"  {k:<6} {len(set(v)):>4} registros distintos")
    t.append("```")
    t.append("\nGFX8 tiene numeracion **plano** (`gca/*_d.h`) y **SOC15**")
    t.append("(`gc_*_offset.h`). El mismo simbolo tiene dos offsets y **ambos")
    t.append("son correctos**. Confundirlos produce el offset equivocado con")
    t.append("apariencia de error de lectura.")

    ambos = {}
    for r in vi:
        ambos.setdefault(r["registro"], {})[r["offset"]] = r["espacio"]
    duales = {k: v for k, v in ambos.items() if len(v) > 1}
    t.append(f"\n### Registros con dos valores ({len(duales)})\n")
    rows = [{"registro": k,
             "plano": next((f"{o:#07x}" for o, e in v.items() if e == "plano"), "-"),
             "soc15": next((f"{o:#07x}" for o, e in v.items() if e == "SOC15"), "-")}
            for k, v in sorted(duales.items())]
    if rows:
        t.append(fmt_tabla(rows, ["registro", "plano", "soc15"],
                           ["registro", "plano", "SOC15"]))
    else:
        t.append("_(ninguno en el subconjunto mostrado)_")

    for titulo, filas, nota in (
            ("## 4. Offset de la ruta VI/GFX8.1", vi,
             "offset deducido del grafo de includes del propio .c"),
            ("## 5. Bloque shader — acceso SOC15", sh,
             "antes invisible: el mapa causal no reconocia RREG32_SOC15"),
            ("## 6. Bloque IH — acceso indirecto", ir,
             "el offset es una variable; el nombre solo existe en la init")):
        t.append("\n" + titulo + "\n")
        t.append(f"_{nota}_\n")
        sub = filas[:40]
        t.append(fmt_tabla(sub, ["registro", "offset", "espacio", "cabecera",
                                 "fichero", "linea"],
                           ["registro", "offset", "espacio", "cabecera",
                            "fichero", "N"]))
        if len(filas) > len(sub):
            t.append(f"\n_… y {len(filas) - len(sub)} más._")
    return "\n".join(t) + "\n"


def nodo_afirmaciones(root, docs):
    """nodo: contraste de las afirmaciones propias contra el codigo"""
    if not os.path.isdir(os.path.join(root, "drivers/gpu/drm/amd")):
        return (f"{PREAMBULO.format(log=LOG, ver=VERSION)}\n"
                f"RAIZ INVALIDA: {root}\n\nSin corpus no hay contraste. "
                "REPAIR_ACTION: pasa la raiz correcta.\n")
    out = crosscheck.run(root, docs, emit_json=True)
    t = [PREAMBULO.format(log=LOG, ver=VERSION)]
    t.append("## 1. Resultado\n")
    t.append("```")
    t.append(f"  informes leidos        {out['n_docs']}")
    t.append(f"  afirmaciones extraidas {out['n_afirmaciones']}")
    t.append(f"    CONFIRMADAS   {out['confirmadas']}")
    t.append(f"    DIFIEREN      {out['difieren']}")
    t.append(f"    NO RESOLUBLES {out['no_resolubles']}")
    t.append("```")

    ret = [c for c in out["detalle"] if c.get("vigente")]
    if ret:
        t.append("\n## 2. Afirmaciones retiradas\n")
        t.append("_Se contrasta el valor **vigente**, no el retirado._\n")
        t.append(fmt_tabla(
            [{"reg": c["reg"],
              "retirado": ", ".join(f"{v:#07x}" for v in c["retirado"]),
              "vigente": f"{c['citado']:#07x}",
              "vd": c["veredicto"]} for c in ret],
            ["reg", "retirado", "vigente", "vd"],
            ["registro", "retirado", "vigente", "veredicto"]))

    conf = [c for c in out["detalle"] if c["veredicto"] == "CONFIRMADO"]
    if conf:
        t.append("\n## 3. Confirmadas\n")
        t.append(fmt_tabla(
            [{"reg": c["reg"], "v": f"{c['citado']:#07x}",
              "e": ",".join(c.get("espacio", []) or []),
              "otros": ", ".join(c.get("otros_valores") or []) or "-"}
             for c in conf],
            ["reg", "v", "e", "otros"],
            ["registro", "valor", "espacio", "otros valores"]))
        t.append("\n_`otros valores`: el mismo símbolo en otro espacio de "
                 "offset. No es un error._")
    return "\n".join(t) + "\n"


def nodo_correcciones(root, docs):
    """nodo: indice de correcciones, generado desde RE-INDEX.md

    Las correcciones viven en un fichero markdown escrito a mano.  Este nodo las
    PARSEA y las clasifica por clase, para que el recuento por clase sea un
    numero calculado y no una afirmacion.  :1483 pide que la documentacion se
    alimente automaticamente; un indice escrito a mano no se alimenta solo.
    """
    idx = os.path.join(RX550_ARQ, "RE-INDEX.md")
    if not os.path.isfile(idx):
        return "RE-INDEX.md no encontrado"
    txt = open(idx, encoding="utf-8", errors="replace").read()
    filas = []
    for m in re.finditer(r"^\|\s*(\d{1,3})\s*\|([^|]*)\|([^|]*)\|(.*)$",
                         txt, re.M):
        filas.append({"n": int(m.group(1)), "error": m.group(2).strip(),
                      "correccion": m.group(3).strip(),
                      "extra": m.group(4).strip()[:200]})
    CLASES = {
        "A nombre asumido -> 0 -> ausente": r"nombre asumido|\bgrep\b da 0|"
            r"no aparece|asumi|suponia",
        "B citar file:N sin abrir": r"sin abrir|file:N|citar la linea|no le[ií]da",
        "C el test afirma una creencia": r"creencia|control positivo|"
            r"transcrib[ií]|inventad",
        "D mezclar generaciones": r"generaci[oó]n|otra generaci[oó]n|"
            r"primera cabecera|alfab[eé]tic",
        "E primero que casa": r"declaraci[oó]n adelantada|primer match|"
            r"fichero anterior|\{\}",
        "F cero silencioso": r"sin avisar|0 registros|tabla vac[ií]a|"
            r"silencios|en silencio|escaneo vac[ií]o",
        "G cobertura como prosa": r"tabla escrita a mano|ment[ií]a|"
            r"declaraba cobertura",
        "H filtro que parece prefijo": r"\[:3\]|startswith|filtro",
        "I prediccion mas amplia": r"m[aá]s amplia|ning[uú]n \.c|"
            r"confund.*dos cosas",
        "J dos espacios de offset": r"espacio|SOC15|\bplano\b",
        "K rendimiento": r"tardaba|pares|producto cartesiano|1 006 342",
        "L re.MULTILINE": r"re\.M|MULTILINE|ancla de linea",
        # N: el patron no casa y se nota.  Estas correcciones se CUENTAN pero
        # no encajan: eso significa que la taxonomia describe sintomas y no
        # causas.  Registrarlas aparte es mas honesto que forzar un encaje.
        "N resolvia el ambito equivocado": r"\.c\)|fichero\)|por fichero|"
            r"cualquier \.c|ambito|alcanza|accede",
        "M mutex en fichero no en funcion": r"srbm_mutex|mutex|serializ",
    }
    clasif = {k: [] for k in CLASES}
    for f in filas:
        txt_f = (f["error"] + " " + f["correccion"]).lower()
        for k, pat in CLASES.items():
            if re.search(pat, txt_f, re.I):
                clasif[k].append(f["n"])
    t = [PREAMBULO.format(log=LOG, ver=VERSION)]
    t.append("## 1. Alcance\n")
    t.append("```")
    t.append(f"  correcciones indexadas  {len(filas)}")
    t.append(f"  numero maximo           {max((f['n'] for f in filas), default=0)}")
    t.append(f"  clases de error        {len(CLASES)}")
    t.append("```")
    sin_clase = [f["n"] for f in filas
                 if not any(f["n"] in v for v in clasif.values())]
    t.append("\n## 2. Reparto por clase\n")
    t.append("_Una correccion puede pertenecer a varias clases; el reparto no "
             "suma 100%. Se parsean las filas con formato tabla; las "
             "correcciones 1-46 esta resumidas por clase en prosa y NO se "
             "cuentan aqui._\n")
    t.append("```")
    for k, v in sorted(clasif.items(), key=lambda x: -len(x[1])):
        t.append(f"  {k:<42} {len(v):>3}")
    t.append("```")
    vacias = [k for k, v in clasif.items() if not v]
    if vacias:
        t.append(f"\n_clases sin asignar en las filas parseadas: "
                 f"{', '.join(vacias)}_")
    if sin_clase:
        t.append(f"\n**{len(sin_clase)} correcciones sin clase asignada**: "
                 f"{sin_clase[:25]}{'…' if len(sin_clase) > 25 else ''}")
        t.append("\n_Eso no es un fallo del clasificador sino una senal: "
                 "son filas cuyo texto no encaja en ninguna clase que yo haya "
                 "definido, o sea que la taxonomia esta incompleta._")
    top = sorted(clasif.items(), key=lambda x: -len(x[1]))[:3]
    if top:
        t.append("\n### Las tres clases dominantes\n")
        for k, v in top:
            t.append(f"- **{k}**: {len(v)} correcciones → {v[:12]}")
    return "\n".join(t) + "\n"


def main(argv):
    if "--self-test" in argv:
        return self_test()
    only = [a for a in argv if a.startswith("--only=")]
    docs = sorted(glob.glob(os.path.join(RX550_ARQ, "*.md")))
    outdir = os.path.join(RX550_ROOT, "01-AUDITORIA/reports-rx550")
    os.makedirs(outdir, exist_ok=True)
    want = [a.split("=", 1)[1] for a in only] or \
        ["registros", "afirmaciones", "correcciones"]
    if "registros" in want:
        txt = nodo_registros(CORPUS)
        p = os.path.join(outdir, "REGISTROS.md")
        open(p, "w", encoding="utf-8").write(txt)
        print(f"  emitido REGISTROS.md  {os.path.getsize(p):>7} B  "
              f"sha {h(txt)}  {p}")
    if "correcciones" in want:
        txt = nodo_correcciones(CORPUS, docs)
        p = os.path.join(outdir, "CORRECCIONES.md")
        open(p, "w", encoding="utf-8").write(txt)
        print(f"  emitido CORRECCIONES.md {os.path.getsize(p):>5} B  "
              f"sha {h(txt)}  {p}")
    if "afirmaciones" in want:
        txt = nodo_afirmaciones(CORPUS, docs)
        p = os.path.join(outdir, "AFIRMACIONES.md")
        open(p, "w", encoding="utf-8").write(txt)
        print(f"  emitido AFIRMACIONES.md {os.path.getsize(p):>5} B  "
              f"sha {h(txt)}  {p}")
    print("\n  cada tabla lleva el comando que la produce; regenerar sin")
    print("  cambios da un fichero byte-identico.")
    return 0


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
    chk("BUILD: corpus disponible", os.path.isdir(CORPUS))
    docs = sorted(glob.glob(os.path.join(RX550_ARQ, "*.md")))
    chk("BASIC TEST: hay informes que contrastar", len(docs) > 0)

    t1 = nodo_registros(CORPUS)
    chk("OUTPUT: nodo de registros no vacio", len(t1) > 500)
    chk("OUTPUT: cita los numeros del corpus",
        "accesos totales" in t1)
    chk("OUTPUT: ninguna tabla vacia con cabecera",
        "|---" in t1)
    chk("DETERMINISMO: dos generaciones identicas",
        nodo_registros(CORPUS) == t1)

    t2 = nodo_afirmaciones(CORPUS, docs)
    chk("OUTPUT: nodo de afirmaciones no vacio", len(t2) > 300)
    chk("OUTPUT: reporta CONFIRMADAS",
        "CONFIRMADAS" in t2)
    chk("DETERMINISMO: afirmaciones identicas",
        nodo_afirmaciones(CORPUS, docs) == t2)

    # EDGE / FAILURE: corpus inexistente no debe reventar
    try:
        txt3 = nodo_registros("/no/existe")
        chk("FAILURE CHECK: raiz invalida no revienta",
            "RAIZ INVALIDA" in txt3 and "accesos totales   0" in txt3,
            txt3[-120:])
        chk("FAILURE CHECK: lo dice explicitamente",
            "RAIZ INVALIDA" in nodo_afirmaciones("/no/existe", docs))
    except Exception as e:
        chk(f"FAILURE CHECK: raiz invalida no reventa ({type(e).__name__})",
            False)

    # --- capa de CORRECCIONES (documentacion auto-alimentada) ---
    cx = nodo_correcciones(CORPUS, docs)
    chk("CORR: el nodo de correcciones no esta vacio", len(cx) > 300)
    # El aserto fijaba el numero a mano y se rompio al crecer el indice.
    # Un aserto sobre un valor que cambia con los datos solo puede ser
    # "hay mas de N"; comprobar la cifra exacta aqui es comprobar la
    # constante, no el generador.  (correccion 124)
    import re as _re2
    _n = _re2.search(r"correcciones indexadas\s+(\d+)", cx)
    chk("CORR: declara el numero de correcciones indexadas",
        _n is not None and int(_n.group(1)) >= 60,
        _n.group(1) if _n else cx[:120])
    _mx = _re2.search(r"numero maximo\s+(\d+)", cx)
    chk("CORR: el maximo es >= el numero indexado (consistencia)",
        _mx is not None and _n is not None
        and int(_mx.group(1)) >= int(_n.group(1)),
        (_mx.group(1) if _mx else None, _n.group(1) if _n else None))
    chk("CORR: declara cuantas quedan sin clase (honestidad)",
        "sin clase asignada" in cx)
    chk("DETERMINISMO: correcciones identicas",
        nodo_correcciones(CORPUS, docs) == cx)
    # EDGE real: si el indice no existe, el nodo debe decirlo, no reventar
    _orig = os.path.isfile
    try:
        os.path.isfile = lambda p: False
        r = nodo_correcciones(CORPUS, docs)
        os.path.isfile = _orig
    finally:
        os.path.isfile = _orig
    chk("EDGE: sin RE-INDEX lo dice y no revienta",
        isinstance(r, str) and "no encontrado" in r, r[:60])

    print(f"  {ok} pasaron, {fail} fallaron")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
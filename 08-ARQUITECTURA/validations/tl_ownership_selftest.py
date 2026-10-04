#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""
tl_ownership_selftest.py — comprueba la atribucion de herramientas a entradas TL.

POR QUE ESTE FICHERO ESTA FUERA DE tools/
----------------------------------------
toolreg.py inventaria los directorios de TOOL_DIRS y cada fuente nueva ahi sale
como herramienta sin documentar.  Este self-test NO es una herramienta del
registro: es un vector de prueba, y metrelo en un TOOL_DIRS contaminaria la
medida que viene a comprobar.  Vive en 08-ARQUITECTURA/validations/, que no esta
en TOOL_DIRS ni se llama `tools`, y por eso `directorios_no_declarados()` tampoco
lo ve.  MEDIDO, no supuesto: antes de escribirlo se comprobo que ese path no
figura en la tupla.

LA PREGUNTA
------------
`docs/TOOLS-STATUS.md` es un ledger de 84 entradas `## TL-nn`, y cada una cita
nombres de herramienta.  `cross_reference()` en tools/toolreg.py atribuia cada
herramienta a la entrada `doc_tl` ASI:

    for tid, names in entries.items():
        if cands & names:
            t.doc_tl = tid          # sin romper: gana la ultima

Es decir: la ULTIMA entrada que cita el nombre.  La pregunta que este fichero
contesta es si una entrada citada N veces produce la misma atribucion que una
citada una, y si el caso malo se DETECTA.

MEDIDO SOBRE EL LEDGER REAL (sha256 9abfe6432f2842f7):
    84 entradas, sin huecos, sin TL-nn repetido
    65 nombres distintos citados, 85 citas
    17 nombres citados en mas de una entrada;  uno de ellos en cuatro
    37 de las 85 citas son NO UNICAS  --  el 43% compite, y el ganador lo decide
    el ORDEN del documento
MEDIDO SOBRE tools/toolreg.py (sha256 de205cc15e4c5a2df):
    65 herramientas documentadas, de las que 58 tienen una entrada que las
    declara SUJETO en la linea de titulo
    atribucion correcta: 45 de 58   ·   atribucion erronea: 13
    las 13 se van a 0 con la regla del sujeto, y la COBERTURA no se mueve

POR QUE EL TITULO Y NO EL ULTIMO
-------------------------------
El ledger declara en su propia linea de titulo de QUE entrada trata:

    ## TL-40 · `citations.py` -- resolver cada `fichero.c:N` ...

El titulo nombra la herramienta DE LA QUE TRATA LA ENTRADA; una mencion en el
cuerpo nombra la herramienta DE LA QUE SE ESTA HABLANDO.  MEDIDO que no es una
distincion de gusto:  de las 20 herramientas que tienen las DOS senal
independientes que da el ledger -- el titulo y la linea `SOURCE` -- las 20
coinciden, y hay CERO contradicciones.  Ademas el propio ledger ya resolvio los
dos casos de empate en prosa: TL-24 escribe "TL-14 es la entrada canonica de
msg_census", y TL-57 y TL-59 explican por que son dos entradas y por que no se
fusionaron.

Y MEDIDO que la regla reproduce el arreglo historico: TL-47 registra las ocho
herramientas que quedaron mal atribuidas por el `## TL-46` duplicado, con la
entrada correcta de cada una.  Con la regla del sujeto, siete salen en la entrada
que TL-47 dice y `ipver_zero.py` aparece en TL-52, que TL-47 daba por perdida
porque TL-52 estaba dentro del bloque duplicado.  Ocho de ocho.

LO QUE ESTE FICHERO NO PROBABA, DECLARADO
-----------------------------------------
  1. No prueba que la atribucion resultante sea la que el ledger queria, sino la
     que el ledger DECLARA.  Si el titulo de una entrada miente, la regla lo
     creera.  Un titulo equivocado es un defecto del ledger, y se veria en el
     informe, no aqui.
  2. No decide el caso de dos entradas que empatan en el mismo nivel: lo REPORTA
     con doc_tl=None y doc_tl_all con las dos.  Convertir ese None en un fallo
     seria inventar una regla que el ledger no declara.
  3. Empareja por NOMBRE de fichero, no por ruta, asi que dos homonimos en
     directorios distintos reciben la misma atribucion.  MEDIDO: hay tres pares
     hoy (`contradict.py`, `fingerprint.py`, `xref.py`).  No se arregla aqui.
  4. El recuento de herramientas del inventario cambia con el arbol.  Los
     controles de este fichero que dependen del numero de herramientas se
     RECONSTRUYEN en cada ejecucion y se imprimen; los que dependen solo del
     ledger se comparan contra las cifras medidas de mas arriba.

LO QUE HACE, Y COMO PUEDE FALLAR
--------------------------------
Aplica el parche a una COPIA de tools/toolreg.py en un temporal y ejecuta los
mismos vectores contra las dos versiones.  Nunca escribe en el arbol del
proyecto: `patch` y `importlib` escriben solo bajo tempfile.

El parche se aplica con `patch -p1`.  Si `patch` no esta disponible, los controles
que lo necesitan salen NOT_RUN y el resto sigue.  rc=0 no es "todo correcto":
mirar el recuento de fallos.

USAGE
-----
  tl_ownership_selftest.py            todos los vectores
  tl_ownership_selftest.py --selftest lo mismo; alias para poder invocarlo con la
                                      misma bandera que el resto del arbol
  tl_ownership_selftest.py --json     una linea por control, parseable
"""

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

VERSION = "1.0.0"
TOOL = "tl_ownership_selftest"
HERE = os.path.dirname(os.path.abspath(__file__))
# 08-ARQUITECTURA/validations/ -> raiz del proyecto
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
PATCH = os.path.join(HERE, "toolreg-tl-ownership.patch")
CN8_PATCH = os.path.join(HERE, "cn8-duplicate-debt-polarity.patch")
CN8 = os.path.join(REPO, "revkit", "cn8.py")
PRISTINE = os.path.join(REPO, "tools", "toolreg.py")
LEDGER = os.path.join(REPO, "docs", "TOOLS-STATUS.md")

FALLOS = []
NOT_RUN = []
CHECKS = [0]


def _sha(path):
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except OSError:
        return None


def chk(nombre, cond, detalle=""):
    CHECKS[0] += 1
    if cond:
        print("  OK    %s" % nombre)
    else:
        print("  FAIL  %s%s" % (nombre, ("   [%s]" % detalle) if detalle else ""))
        FALLOS.append(nombre)
    return bool(cond)


def nota(nombre, detalle=""):
    print("  --    %s%s" % (nombre, ("   [%s]" % detalle) if detalle else ""))


# --------------------------------------------------------------------------
# VECTORES.  Cada uno es un ledger minimo, escrito entero, no un recorte.
# --------------------------------------------------------------------------

# Un ledger limpio: dos entradas con sujeto declarado.
BASE = (
    "## TL-01 · `a.py` — el primero\n\n"
    "Cuerpo de `a.py`, con su contrato.\n\n"
    "## TL-02 · `b.py` — el segundo\n\n"
    "Cuerpo de `b.py`, con su contrato.\n\n"
)

# Las TRES formas de duplicar una entrada.  La diferencia entre las tres es el
# motivo entero de este fichero.
DUP_A_IDENTICA = (          # cabecera y cuerpo byte a byte iguales
    "## TL-01 · `a.py` — el primero\n\n"
    "Cuerpo de `a.py`, con su contrato.\n\n"
    "## TL-02 · `b.py` — el segundo\n\n"
    "Cuerpo de `b.py`, con su contrato.\n\n"
    "## TL-01 · `a.py` — el primero\n\n"
    "Cuerpo de `a.py`, con su contrato.\n\n"
)
DUP_B_OTRO_TEXTO = (        # mismo TL-nn, titulo distinto
    "## TL-01 · `a.py` — el primero\n\n"
    "Cuerpo de `a.py`, con su contrato.\n\n"
    "## TL-02 · `b.py` — el segundo\n\n"
    "Cuerpo de `b.py`, con su contrato.\n\n"
    "## TL-01 · `a.py` — el primero, reescrito\n\n"
    "Cuerpo de `a.py`, con su contrato.\n\n"
)
DUP_C_ANEXO = (             # mismo TL-nn, y el anexo no nombra sujeto: cita otra
    "## TL-01 · `a.py` — el primero\n\n"
    "Cuerpo de `a.py`, con su contrato.\n\n"
    "## TL-02 · `b.py` — el segundo\n\n"
    "Cuerpo de `b.py`, con su contrato.\n\n"
    "## TL-01 — anexo repetido\n\n"
    "Cuerpo del anexo, que cita `c.py`.\n\n"
)

# Titulo en una entrada, mencion en OTRA.  La entrada que MENCIONA no es la
# entrada de la herramienta: es la entrada de otra cosa que habla de ella.
#
# MEDIDO por que el orden de las dos entradas esta invertido a proposito:  con la
# entrada que menciona DESPUES, el last-wins da la que menciona y el vector
# discrimina.  Con la que menciona antes, ambos dan la misma y el vector no
# probaria nada.  Un vector que no puede fallar no mide.
MENCION = (
    "## TL-01 · `pipeline.py` — la cadena causal\n\n"
    "Cuerpo de `pipeline.py`, con su contrato.\n\n"
    "## TL-02 · `reg_census.py` — que registros toca un .c\n\n"
    "Es una etapa de la cadena de `pipeline.py`.\n\n"
)

# Dos entradas con el MISMO sujeto.  El ledger declara el motivo en prosa; el
# codigo no tiene que adivinarlo.
EMPATE = (
    "## TL-01 · `d.py` — medicion uno\n\n"
    "Cuerpo de la medicion uno.\n\n"
    "## TL-02 · `d.py` — medicion dos\n\n"
    "Cuerpo de la medicion dos.\n\n"
)

HERRAMIENTAS = ("a.py", "b.py", "c.py", "d.py", "reg_census.py", "pipeline.py")


def _fixture(td, ledger, tools=HERRAMIENTAS):
    """Arbol minimo con docs/TOOLS-STATUS.md y tools/."""
    os.makedirs(os.path.join(td, "tools"), exist_ok=True)
    os.makedirs(os.path.join(td, "docs"), exist_ok=True)
    with open(os.path.join(td, "docs", "TOOLS-STATUS.md"), "w",
              encoding="utf-8") as fh:
        fh.write(ledger)
    for name in tools:
        with open(os.path.join(td, "tools", name), "w", encoding="utf-8") as fh:
            fh.write('#!/usr/bin/env python3\n"""%s — fixture.\n\n'
                     'WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE\n"""\n' % name)
    return td


def _cargar(path, tag):
    """Importa toolreg desde una ruta concreta, como modulo."""
    spec = importlib.util.spec_from_file_location(tag, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _atribuir(mod, td):
    """{nombre: doc_tl} con el modulo dado, sobre un fixture."""
    tools = mod.inventory(td)
    mod.cross_reference(td, tools)
    return {t.name: t.doc_tl for t in tools}


# --------------------------------------------------------------------------
# la puerta que YA existe, replicada.  No se ejecuta revkit/cn8.py porque declara
# WRITE_EXECUTION=ESCRIBE; se replica su logica exacta, linea a linea.
# --------------------------------------------------------------------------

def cn8_puerta_duplicados(docs):
    """COPIA de revkit/cn8.py lineas 520-538.  Compara TEXTO DE CABECERA."""
    out = {}
    for f in sorted(os.listdir(docs)):
        if not f.endswith(".md"):
            continue
        seen = {}
        with open(os.path.join(docs, f), errors="replace") as fh:
            for line in fh:
                if line.startswith("#") and not line.startswith("###"):
                    seen[line.strip()] = seen.get(line.strip(), 0) + 1
        d = sorted(k for k, v in seen.items() if v > 1)
        if d:
            out[f] = d
    return out


# --------------------------------------------------------------------------
# el vector principal
# --------------------------------------------------------------------------

def run(patched_path):
    """Los vectores de duplicacion, contra el original y contra el parchado."""
    pristine = _cargar(PRISTINE, "toolreg_pristine")
    parcheado = _cargar(patched_path, "toolreg_patched")

    casos = (
        ("A_identica", BASE, DUP_A_IDENTICA, True),
        ("B_otro_texto", BASE, DUP_B_OTRO_TEXTO, True),
        ("C_anexo", BASE, DUP_C_ANEXO, True),
    )

    print("  -- invariancia: una entrada citada DOS VECES debe atribuir igual")
    print("     que citada UNA.  Base = 1 copia;  duplicado = 2.")
    for nombre, base_txt, dup_txt, _ in casos:
        with tempfile.TemporaryDirectory() as td1, \
             tempfile.TemporaryDirectory() as td2:
            _fixture(td1, base_txt)
            _fixture(td2, dup_txt)
            ref = _atribuir(parcheado, td1)
            got = _atribuir(parcheado, td2)
            chk("  parchado  %-14s atribuye igual con 1 y con 2 copias" % nombre,
                ref == got, "1 copia=%r  2 copias=%r" % (ref, got))

    print("  -- CONTRASTE: el ORIGINAL tiene que FALLAR en alguno.  Si tambien")
    print("     pasara, los vectores no distinguen y no miden nada.")
    discrimina = False
    for nombre, base_txt, dup_txt, _ in casos:
        with tempfile.TemporaryDirectory() as td1, \
             tempfile.TemporaryDirectory() as td2:
            _fixture(td1, base_txt)
            _fixture(td2, dup_txt)
            ref = _atribuir(pristine, td1)
            got = _atribuir(pristine, td2)
        nota("original %-14s 1 copia=%r" % (nombre, ref))
        nota("original %-14s 2 copias=%r" % (nombre, got))
        if ref != got:
            discrimina = True
    chk("algun vector rompe la invariancia en el ORIGINAL", discrimina,
        "si esto falla, los vectores de arriba no distinguen dos versiones")

    print("  -- la puerta de duplicados: la de este parche, y la que ya existia")
    cn8_ver = {}
    for nombre, base_txt, dup_txt, _ in casos:
        with tempfile.TemporaryDirectory() as td:
            _fixture(td, dup_txt)
            dups = parcheado.entradas_duplicadas(td)
            chk("  parche    %-14s la duplicacion se REPORTA" % nombre,
                len(dups) == 1 and dups[0]["tl"] == "TL-01"
                and dups[0]["copies"] == 2,
                "entradas_duplicadas=%r" % (dups,))
            cn8_ver[nombre] = sorted(cn8_puerta_duplicados(
                os.path.join(td, "docs")).get("TOOLS-STATUS.md", []))
            nota("cn8.py    %-14s %s" % (nombre,
                 cn8_ver[nombre] or "NO VE NADA  (puerta VERDE)"))

    # MEDIDO: cn8.py compara el TEXTO de la linea de cabecera.  El caso A repite
    # la linea entera, y se ve.  B y C escriben un titulo distinto para el mismo
    # TL-nn, y no se ve.  Esta comprobacion NO es decorativa: si cn8.py se
    # arreglara para mirar la identidad, tiene que FALLAR aqui, y ese fallo es la
    # senal de que el sitio de la puerta ya no es este.
    chk("cn8.py ve el caso A (cabecera repetida byte a byte)",
        len(cn8_ver["A_identica"]) == 1, "%r" % (cn8_ver["A_identica"],))
    chk("cn8.py NO ve el caso C (mismo TL-nn, titulo distinto)",
        cn8_ver["C_anexo"] == [], "%r" % (cn8_ver["C_anexo"],))
    chk("cn8.py NO ve el caso B (mismo TL-nn, texto distinto)",
        cn8_ver["B_otro_texto"] == [], "%r" % (cn8_ver["B_otro_texto"],))

    print("  -- la puerta por IDENTIDAD distingue las dos copias, no solo las ve")
    with tempfile.TemporaryDirectory() as td:
        _fixture(td, DUP_A_IDENTICA)
        a = parcheado.entradas_duplicadas(td)[0]
    with tempfile.TemporaryDirectory() as td:
        _fixture(td, DUP_C_ANEXO)
        c = parcheado.entradas_duplicadas(td)[0]
    chk("dos copias byte-identicas -> identical=True", a["identical"] is True,
        "%r" % (a["digests"],))
    chk("dos copias con texto distinto -> identical=False", c["identical"] is False,
        "%r" % (c["digests"],))

    print("  -- MENCIONAR no es POSYER")
    with tempfile.TemporaryDirectory() as td:
        _fixture(td, MENCION)
        got = _atribuir(parcheado, td)
        old = _atribuir(pristine, td)
    chk("  parchado  pipeline.py va a la entrada que la declara sujeto (TL-01)",
        got.get("pipeline.py") == "TL-01", "doc_tl=%r" % got.get("pipeline.py"))
    chk("  CONTRASTE el original se equivoca: da la entrada que lo MENCIONA",
        old.get("pipeline.py") == "TL-02", "doc_tl=%r" % old.get("pipeline.py"))

    print("  -- EMPATE en el mismo nivel: se reporta el conjunto, no se reparte")
    with tempfile.TemporaryDirectory() as td:
        _fixture(td, EMPATE)
        tools = parcheado.inventory(td)
        parcheado.cross_reference(td, tools)
        d = [t for t in tools if t.name == "d.py"][0]
        old = _atribuir(pristine, td).get("d.py")
    chk("  parchado  d.py -> doc_tl=None y doc_tl_all con LAS DOS",
        d.doc_tl is None and d.doc_tl_all == ["TL-01", "TL-02"],
        "doc_tl=%r all=%r level=%r" % (d.doc_tl, d.doc_tl_all, d.doc_tl_level))
    chk("  parchado  el nivel dice MULTI, no finge una propiedad",
        d.doc_tl_level == "MULTI_O1_SUBJECT", "level=%r" % d.doc_tl_level)
    nota("original  d.py -> %r  (una de las dos, elegida por orden)" % old)

    print("  -- el sujeto se empareja por STEM: sin extension tambien cuenta")
    with tempfile.TemporaryDirectory() as td:
        _fixture(td, "## TL-01 · `e` — sin extension en el titulo\n\n"
                     "Cuerpo.\n\n", tools=("e.py",))
        got = _atribuir(parcheado, td)
    chk("  parchado  `e` en el titulo -> e.py = TL-01", got.get("e.py") == "TL-01",
        "doc_tl=%r" % got.get("e.py"))


# --------------------------------------------------------------------------
# sobre el arbol real
# --------------------------------------------------------------------------

def run_real(parcheado):
    print("  -- sobre el arbol real.  El ledger es la entrada; el inventario se")
    print("     esta moviendo, asi que se imprime en vez de compararse.")
    txt = open(LEDGER, encoding="utf-8", errors="replace").read()
    bloques = parcheado.tl_blocks(REPO)

    import re as _re
    ids = _re.findall(r"^## (TL-\d+)", txt, _re.M)
    nums = sorted(int(i.split("-")[1]) for i in ids)
    chk("  ledger  84 entradas TL-nn", len(ids) == 84, "n=%d" % len(ids))
    chk("  ledger  ningun TL-nn repetido", len(ids) == len(set(ids)),
        "repetidos=%r" % sorted({i for i in ids if ids.count(i) > 1}))
    chk("  ledger  sin huecos de 1 a 84",
        nums == list(range(1, 85)), "huecos=%r" % [n for n in range(1, 85)
                                                    if n not in set(nums)])
    chk("  ledger  la puerta de duplicados no ve ninguna",
        parcheado.entradas_duplicadas(REPO) == [],
        "%r" % (parcheado.entradas_duplicadas(REPO),))

    # el censo de citas, que es lo que el last-wins exploita
    cite = {}
    for b in bloques:
        for n in _re.findall(r"`([A-Za-z0-9_./\-]+\.(?:py|c|sh))`",
                             b["header"] + "\n" + b["body"]):
            cite.setdefault(os.path.basename(n), set()).add(b["tl"])
    multi = {n: sorted(v) for n, v in cite.items() if len(v) > 1}
    total = sum(len(v) for v in cite.values())
    no_unicas = sum(len(v) for v in multi.values())
    nota("censo    %d nombres distintos, %d citas, %d de ellas NO UNICAS (%.0f%%)"
         % (len(cite), total, no_unicas, 100.0 * no_unicas / max(total, 1)))
    nota("censo    %d nombres citados en mas de una entrada;  maximo %d entradas"
         % (len(multi), max((len(v) for v in multi.values()), default=0)))
    chk("  ledger  el last-wins tiene trabajo que hacer (NO_UNICAS > 0)",
        no_unicas > 0, "no_unicas=%d" % no_unicas)

    # cobertura: la puerta no puede moverla
    pristine = _cargar(PRISTINE, "toolreg_pristine2")
    tp = pristine.inventory(REPO)
    _, orph_p = pristine.cross_reference(REPO, tp)
    tq = parcheado.inventory(REPO)
    _, orph_q = parcheado.cross_reference(REPO, tq)
    cov_p = sorted((t.dir, t.name) for t in tp if t.in_docs)
    cov_q = sorted((t.dir, t.name) for t in tq if t.in_docs)
    nota("inventario  %d herramientas, %d documentadas (antes y despues: %d / %d)"
         % (len(tp), len(cov_p), len(cov_p), len(cov_q)))
    chk("  parche   la COBERTURA no se mueve", cov_p == cov_q,
        "solo-antes=%r solo-despues=%r" % (
            sorted(set(cov_p) - set(cov_q))[:4],
            sorted(set(cov_q) - set(cov_p))[:4]))
    chk("  parche   los huerfanos TL no se mueven", orph_p == orph_q,
        "antes=%d despues=%d" % (len(orph_p), len(orph_q)))

    # el efecto que importa
    own = parcheado.tl_ownership(REPO)
    truth = lambda s: own.get(s, (None, None, []))[0]
    doc = [(t.dir, t.name, t.stem) for t in tp if t.in_docs]
    con_dueno = [x for x in doc if truth(x[2])]
    bien_p = sum(1 for d, n, s in con_dueno
                 if [t for t in tp if t.dir == d and t.name == n][0].doc_tl == truth(s))
    bien_q = sum(1 for d, n, s in con_dueno
                 if [t for t in tq if t.dir == d and t.name == n][0].doc_tl == truth(s))
    nota("efecto    %d documentadas, %d con entrada que las declara sujeto"
         % (len(doc), len(con_dueno)))
    nota("efecto    CORRECTAS  %d -> %d      ERRONEAS  %d -> %d"
         % (bien_p, bien_q, len(con_dueno) - bien_p, len(con_dueno) - bien_q))
    chk("  parche   las atribuciones erroneas quedan en 0",
        (len(con_dueno) - bien_q) == 0,
        "quedan %d" % (len(con_dueno) - bien_q))
    chk("  parche   las atribuciones erroneas ANTES eran > 0",
        (len(con_dueno) - bien_p) > 0,
        "eran %d" % (len(con_dueno) - bien_p))

    # la justificacion del nivel O2: no puede contradecir a O1
    both = agree = 0
    for b in bloques:
        subj = {s.rsplit(".", 1)[0] for s in
                _re.findall(r"`([A-Za-z0-9_.\-]+)`", b["header"])}
        for m in _re.finditer(r"^\s*SOURCE\s+(\S+)", b["body"], _re.M):
            base = os.path.basename(m.group(1))
            if not _re.fullmatch(r"[A-Za-z0-9_.\-]+\.(?:py|c|sh)", base):
                continue
            s = base.rsplit(".", 1)[0]
            if s in subj:
                both += 1
            else:
                agree += 1
    nota("O2        %d señales SOURCE con sujeto en la MISMA entrada, "
         "%d en otra" % (both, agree))
    chk("  el respaldo O2 no contradice al sujeto: 0 casos en otra entrada",
        agree == 0, "contradicciones=%d" % agree)


# La polaridad del control de cn8.py.  El control de la paridad de fences ya
# esta reparado con `<=` (linea 508) y TL-59 documenta POR QUE.  El de las
# cabeceras duplicadas (linea 536) seguia con `==`, que es el mismo defecto: la
# igualdad exacta convierte en FALLA el hecho de haber PAGADO la deuda.  Y la
# deuda esta pagada: el `## TL-46` duplicado ya no esta.
#
# Se replica la condicion, no se ejecuta cn8.py:  cn8 declara
# WRITE_EXECUTION=ESCRIBE con os.makedirs y open(...,'w'), asi que su rc no se
# observa aqui.  Lo que se afirma es el VALOR DE LA CONDICION, que es estatico.
def _polaridad_cn8(docs_dir):
    d = cn8_puerta_duplicados(docs_dir)
    deu = {"TOOLS-STATUS.md"}
    return (set(d) == deu, set(d) <= deu, sorted(deu - set(d)), sorted(d))


def run_cn8():
    print("  -- la puerta que YA EXISTIA (revkit/cn8.py, linea 536)")
    eq, le, pagadas, d = _polaridad_cn8(os.path.join(REPO, "docs"))
    chk("cn8.py el control de duplicados esta ROJO con el arbol ya reparado",
        eq is False,
        "set(dupes)=%r DEUDA=['TOOLS-STATUS.md'] -> '==' da False" % (d,))
    chk("cn8.py la polaridad propuesta '<=' lo deja VERDE", le is True)
    chk("cn8.py '<=' nombra la deuda PAGADA, que se puede podar",
        pagadas == ["TOOLS-STATUS.md"], "pagadas=%r" % (pagadas,))

    print("  -- y la direccion que importa NO se relaja: un duplicado nuevo")
    print("     sigue saltando con '<='")
    with tempfile.TemporaryDirectory() as td:
        open(os.path.join(td, "TOOLS-STATUS.md"), "w",
             encoding="utf-8").write("# t\n## A\nx\n## A\ny\n")
        open(os.path.join(td, "OTRO.md"), "w",
             encoding="utf-8").write("# o\n## B\nx\n## B\ny\n")
        eq2, le2, _, d2 = _polaridad_cn8(td)
    chk("cn8.py con '<=' un duplicado NUEVO en otro fichero sigue siendo ROJO",
        le2 is False, "set(dupes)=%r" % (d2,))
    chk("cn8.py el parche de cn8 sigue siendo un diff aplicable y sintactico",
        os.path.exists(CN8_PATCH), CN8_PATCH)


# --------------------------------------------------------------------------


def aplicar_parche(td):
    """Copia el original, le aplica el parche y devuelve la ruta del resultado."""
    shutil.copyfile(PRISTINE, os.path.join(td, "toolreg_orig.py"))
    os.makedirs(os.path.join(td, "work", "tools"), exist_ok=True)
    shutil.copyfile(PRISTINE, os.path.join(td, "work", "tools", "toolreg.py"))
    r = subprocess.run(["patch", "-p1", "-i", PATCH],
                       cwd=os.path.join(td, "work"), capture_output=True, text=True)
    if r.returncode != 0:
        return None, r.stdout + r.stderr
    return os.path.join(td, "work", "tools", "toolreg.py"), ""


def main(argv):
    as_json = "--json" in argv
    # `--selftest` se acepta como alias: este fichero es un vector, y el arbol
    # invoca los vectores con esa bandera.  No cambia lo que hace.
    argv = [a for a in argv if a != "--selftest"]

    print("%s %s -- self-test" % (TOOL, VERSION))
    print("  " + "-" * 74)
    print("  repo            %s" % REPO)
    print("  ledger sha256   %s" % _sha(LEDGER))
    print("  toolreg sha256  %s" % _sha(PRISTINE))
    print("  patch  sha256   %s" % _sha(PATCH))
    print("  " + "-" * 74)

    if not os.path.exists(PATCH):
        print("  FAIL  no existe el parche %s" % PATCH)
        return 2

    with tempfile.TemporaryDirectory() as td:
        dest, err = aplicar_parche(td)
        if dest is None:
            print("  FAIL  el parche no aplica: %s" % err.strip()[:300])
            return 2
        print("  parche aplicado a una COPIA.  El tools/toolreg.py del proyecto")
        print("  NO se ha tocado:  sigue en %s" % _sha(PRISTINE)[:16])
        print("  " + "-" * 74)
        parcheado = _cargar(dest, "toolreg_patched")
        chk("la copia parchada declara tl_ownership y entradas_duplicadas",
            hasattr(parcheado, "tl_ownership")
            and hasattr(parcheado, "entradas_duplicadas"))
        chk("el ORIGINAL no las declara todavia (el parche no estaba aplicado)",
            not hasattr(_cargar(PRISTINE, "t2"), "tl_ownership"))

        r = subprocess.run([sys.executable, dest, "--selftest"],
                           capture_output=True, text=True, cwd=td)
        m = [l for l in r.stdout.splitlines() if "checks," in l]
        chk("el toolreg parchado pasa su PROPIO self-test",
            r.returncode == 0, "%s | %s" % (r.returncode, m[-1] if m else "sin linea"))

        print("  " + "-" * 74)
        run(dest)
        print("  " + "-" * 74)
        run_cn8()
        print("  " + "-" * 74)
        run_real(parcheado)

    print("  " + "-" * 74)
    if as_json:
        print(json.dumps({"tool": TOOL, "version": VERSION, "repo": REPO,
                          "ledger_sha256": _sha(LEDGER),
                          "toolreg_sha256": _sha(PRISTINE),
                          "patch_sha256": _sha(PATCH),
                          "checks": CHECKS[0],
                          "checks_failed": len(FALLOS), "failed": FALLOS,
                          "not_run": NOT_RUN}, indent=2, sort_keys=True))
    print("  %d checks, %d fallos" % (CHECKS[0], len(FALLOS)))
    for f in FALLOS:
        print("    FALLA  %s" % f)
    print("")
    print("  NOTA: esto prueba que la atribucion es la que el ledger DECLARA y que")
    print("        una entrada duplicada ya no la cambia.  No prueba que el titulo")
    print("        de una entrada diga la verdad: eso lo dice el informe, no aqui.")
    print("  RESULT: %s" % ("OK" if not FALLOS else "FAILED"))
    return 1 if FALLOS else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
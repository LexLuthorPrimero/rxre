#!/usr/bin/env python3
# CONTRACT: name=rxre_contracts
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: TOUCHES_INTEGRATED=no
# CONTRACT: EXIT_ON_SUCCESS=0
#
# MEDIDO con RXRE/tools/rxre_contracts.py.  Veredicto `READONLY=yes,
# WRITES_FILES=no`: no tiene ninguna escritura, solo lee fuentes y produce un
# informe.
#
# Un instrumento que NO declara contrato no puede enrutarse y nadie puede saber
# si al ejecutarlo toco algo.  Es el estado que `1491` midio: cero herramientas
# con LAS DOS declaraciones.  Este bloque no anade comportamiento; hace el
# comportamiento DECLARABLE.
#
# EXIT_ON_SUCCESS=0: MEDIDO.  `--version` sale rc=0 y `--selftest` sale rc=0 con
# todos los vectores en PASS.  Se declara porque `exit_contract.py` existe para
# comprobarlo: un validador que no declara su codigo de salida deja ese codigo
# sin verificar, y es un contrato en prosa.
#
# TOUCHES_INTEGRATED=no: lee ficheros y sysfs; no abre DRM, no hace ioctl, no
# escribe en la GPU.  Se declara aunque toolkit.py no lo comprirme -- lo verifica
# `rxre_touch.py`, y reconocer un campo no es comprobarlo (1513, 1515).
"""rxre_contracts.py -- MEDIR el contrato de cada herramienta antes de declararlo.

POR QUE MEDIR Y NO COPIAR
------------------------
    Anadir un bloque `# CONTRACT:` es escribir una AFIRMACION sobre lo que una
    herramienta hace.  Escribirla leyendo el nombre del fichero o la cabecera
    seria lo que `1481` ya medico: un numero con la forma correcta y la
    substance equivocada.

    Asi que aqui no se declara nada: se MIDE, con el criterio que el proyecto ya
    escribio y ya pago, y se imprime lo que se ha medido.  Declarar es una
    accion posterior, sobre una tabla, y se hace a mano -- con la tabla delante.

EL CRITERIO, Y DE DONDE VIENE
-----------------------------
    De `08-ARQUITECTURA/tools/contract_exec.py`, que existe porque una regex
    sobre el texto produjo cinco falsos positivos (`doclint.py` aparecia como
    "declara escritura" por un `mkstemp`):

        ESCRITURA_DE_PROYECTO  la ruta resuelve DENTRO del arbol
        TEMPORAL               tempfile, o ruta absoluta FUERA
        DESCONOCIDO            el destino es un parametro o una variable

    Y aqui se AADE una clase que `contract_exec` no tiene, porque sus ficheros
    no la necesitan y estos si:

        LITERAL_EN_PROYECTO    el destino es un LITERAL que cae dentro del
                               arbol.  Es lo mas fuerte de los tres, y es
                               distinguible sin ejecutar nada.

    Sin esa clase, `revkit/btfsnap.py` que escribe `.selftest-layouts.txt` en
    `revkit/` y `revkit/sello.py` que escribe en un temporal darian el MISMO
    veredicto, y serian herramientas de riesgo distinto con la misma etiqueta.

LO QUE NO ES
------------
    No modifica ficheros.  No inserta contratos.  No juzga si una declaracion
    es correcta: mide lo que el CODIGO dice, que es un `NOT_FOUND` sobre lo que
    la herramienta HACE en runtime, y se declara como tal.

    Un contrato se declara con lo que el codigo permite PROBAR, no con lo que
    se squeza.  La diferencia es la que separa un inventario de un oraculo.
"""
import argparse
import ast
import collections
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
VERSION = "1.0.0"

CONTRATO_RE = re.compile(r"(?m)^#\s*CONTRACT:\s*(\w+)\s*=\s*(\S+)")
CABECERA = 4000

# Las que se miden.  Los directorios son los de `toolreg.TOOL_DIRS`, y la
# lista esta aqui porque `toolreg` no la exporta como constante.
DIRECTORIOS = ("tools", "revkit", "08-ARQUITECTURA/tools",
               "04-IMPLEMENTACION/tools", "09-POWER-CLOCKS/tools",
               "01-AUDITORIA/tools", "04-IMPLEMENTATION/rx550-driver/tools")


def contrato_de(ruta_abs):
    try:
        txt = open(ruta_abs, encoding="utf-8", errors="replace").read(CABECERA)
    except OSError:
        return {}
    return dict(CONTRATO_RE.findall(txt))


def constantes_modulo(arbol):
    """{NOMBRE: valor} para los Assign de nivel de modulo con literal.

    Se resuelven porque los destinos de escritura de estas herramientas son
    casi todos constantes: `CACHE = "/tmp/opencode/cidx.cache.pkl"`,
    `RAIZ_POR_DEFECTO = ".."`.  Sin resolverlos, todo cae en DESCONOCIDO y la
    tabla no distinguiria dos clases de riesgo que son distintas.
    """
    out = {}
    for n in arbol.body:
        if not isinstance(n, ast.Assign):
            continue
        for tgt in n.targets:
            if not isinstance(tgt, ast.Name):
                continue
            try:
                out[tgt.id] = ast.literal_eval(n.value)
            except (ValueError, SyntaxError, TypeError):
                pass
    return out


def resolver(destino, consts, aqui):
    """(clase, ruta_absoluta_o_None). Resuelve solo lo que se puede resolver."""
    if destino is None:
        return "DESCONOCIDO", None
    v = destino
    # Un solo nivel de indireccion por constante de modulo.  No mas: un
    # resolver que persigue cualquier expresion deja de ser medible y empieza
    # a ser un intreprete, que es otra herramienta.
    if isinstance(v, str) and v in consts and isinstance(consts[v], str):
        v = consts[v]
    if not isinstance(v, str) or not v:
        return "DESCONOCIDO", None
    base = aqui if not os.path.isabs(v) else ""
    abs_ = os.path.normpath(os.path.join(base, v))
    if abs_.startswith("/tmp") or abs_.startswith("/var/tmp"):
        return "TEMPORAL", abs_
    if abs_.startswith(RAIZ):
        return "LITERAL_EN_PROYECTO", abs_
    if v.startswith("..") or v.startswith("."):
        return "DESCONOCIDO_RELATIVA", abs_
    return "FUERA", abs_


def medir_una(ruta_rel):
    ruta_abs = os.path.join(RAIZ, ruta_rel)
    src = open(ruta_abs, encoding="utf-8", errors="replace").read()
    d = {"ruta": ruta_rel, "contrato": contrato_de(ruta_abs) or None,
         "len_contrato": len(contrato_de(ruta_abs))}
    try:
        arbol = ast.parse(src)
    except SyntaxError as e:
        d["estado"] = "NO_PARSEA"
        d["motivo"] = str(e)
        return d
    consts = constantes_modulo(arbol)
    usa_temp = bool(re.search(r"\btempfile\b|mkdtemp|TemporaryDirectory", src))
    # MEDIDO, y este es el defecto mas caro que ha tenido este fichero.
    #
    # La primera version clasificaba una escritura como TEMPORAL_POR_TEMPFILE si
    # el FICHERO usaba `tempfile` en algun sitio.  Es una INFERENCIA sobre el
    # fichero, no una observacion de la escritura: un fichero puede usar
    # tempfile en su selftest y escribir en el arbol en su codigo de produccion,
    # y con ese criterio las dos cosas salen TEMPORAL.
    #
    # Verificado sobre `tools/pm4ops.py`: sus 16 escrituras ESTAN dentro de
    # `with tempfile.TemporaryDirectory(prefix="pm4ops-st") as d:`, asi que la
    # clasificacion era correcta -- pero por un motivo que no la sostiene.  Una
    # respuesta cierta por via invalida llega a la respuesta falsa por la misma
    # via, y sin dejar rastro.
    #
    #     llegar a la verdad por una via invalida no es medir
    #
    # Ahora se comprueba la ESTRUCTURA: se recogen los rangos de linea de los
    # `with` cuyo contexto es tempfile, y una escritura es TEMPORAL solo si su
    # lineno cae dentro de uno de esos rangos.  Si el fichero usa tempfile y la
    # escritura NO esta en un bloque de esos, sale NO_DETERMINED, no TEMPORAL.
    rangos_temp, vars_temp = [], set()
    for n in ast.walk(arbol):
        if isinstance(n, ast.With):
            ctx = ast.dump(n)
            if ("TemporaryDirectory" in ctx or "mkdtemp" in ctx
                    or "NamedTemporary" in ctx):
                fin = getattr(n, "end_lineno", None) or n.lineno
                rangos_temp.append((n.lineno, fin))
        # MEDIDO, y este es el segundo defecto del mismo eje, y va en el sentido
        # CONTRARIO al primero:
        #
        #   El rango de `with tempfile.TemporaryDirectory() as d:` NO cubre
        #   `d = tempfile.mkdtemp()`.  Y con esa regla, `tools/mmio.py`,
        #   `tools/ibref.py` y `tools/layoutcross.py` salieron
        #   FUERA_DE_TEMPORAL: sus escrituras son `with open(os.path.join(dt,
        #   ...))` donde `dt` viene de un `mkdtemp` SIN `with`.
        #
        #   Los tres son temporales de verdad -- comprobado a mano -- y la regla
        #   del `with` los declaraba lo contrario.  Corregir un error creating un
        #   error del otro signo no es corregir: es cambiar de error.
        #
        #     una regla mas estrecha no es una regla mejor: es otra regla
        #
        # La segunda regla SI es observable y es la que falta: el destino de la
        # escritura MENCIONA una variable a la que se asigno un mkdtemp.  Eso se
        # comprueba sobre el arbol, no sobre el fichero entero.
        if isinstance(n, ast.Assign):
            ctx = ast.dump(n.value)
            if "mkdtemp" in ctx or "NamedTemporary" in ctx or \
                    "TemporaryDirectory" in ctx:
                for tgt in n.targets:
                    if isinstance(tgt, ast.Name):
                        vars_temp.add(tgt.id)
    esc = []
    for n in ast.walk(arbol):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "open"):
            continue
        modo, destino, destino_txt = None, None, None
        if n.args:
            if isinstance(n.args[0], ast.Constant) and \
                    isinstance(n.args[0].value, str):
                destino = n.args[0].value
            destino_txt = ast.dump(n.args[0])
        if len(n.args) > 1 and isinstance(n.args[1], ast.Constant) and \
                isinstance(n.args[1].value, str):
            modo = n.args[1].value
        for kw in n.keywords:
            if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                modo = kw.value.value
            if kw.arg == "file" and isinstance(kw.value, ast.Constant):
                destino = kw.value.value
        if modo and any(c in modo for c in "wax"):
            esc.append((n.lineno, modo, destino, destino_txt))
    clases = collections.Counter()
    detalle = []
    for linea, modo, destino, destino_txt in esc:
        c, abs_ = resolver(destino, consts, os.path.dirname(ruta_abs))
        dentro = any(a <= linea <= b for (a, b) in rangos_temp)
        # El destino menciona una variable de mkdtemp.  Se busca en el DUMP del
        # nodo de primer argumento, no en el texto del fichero: un nombre de
        # variable en un comentario no cuenta, por el mismo motivo que un
        # `card0` en un comentario no es un acceso (hallazgo 1501).
        #
        # MEDIDO: el patron era `"'id': '%s'"` y `ast.dump` escribe `id='dt'`,
        # SIN comillas en la clave.  La regla nueva no se disparo NINGUNA vez
        # sobre 192 herramientas y eso habria podido leerse como "el criterio no
        # sirve".  No servia el patron: la regla era correcta y no llego a
        # ejecutarse.  Un filtro que nunca casa no es un filtro: es un typo.
        #
        #     un filtro que nunca casa no es un filtro: es un error de dedo
        nombra_temp = bool(destino_txt) and any(
            "id='%s'" % v in destino_txt or 'id="%s"' % v in destino_txt
            for v in vars_temp)
        if c == "DESCONOCIDO" and usa_temp:
            if dentro:
                c = "TEMPORAL_EN_BLOQUE"
            elif nombra_temp:
                c = "TEMPORAL_POR_DESTINO"
            else:
                c = "FUERA_DE_TEMPORAL_PERO_USA_TEMPFILE"
        clases[c] += 1
        detalle.append({"linea": linea, "modo": modo, "destino": destino,
                        "clase": c, "resuelto": abs_,
                        "en_bloque_temporal": dentro,
                        "destino_nombra_temporal": nombra_temp})
    sys_w = bool(re.search(r"""open\([^)]*['"][wax][^)]*/sys""", src))
    # MEDIDO, y este es el punto ciego que hace que tres contratos salgan
    # NO_SOSTENIDOS cuando probablemente estan bien:
    #
    #   una herramienta puede escribir ficheros SIN llamar a `open`.  Puede
    #   llamar a `os.remove`, `shutil.copy`, `Path.write_text`, o -- y esto es
    #   lo de aqui -- EJECUTAR otra herramienta que escribe.
    #
    # `08-ARQUITECTURA/tools/run_all.py` declara WRITES_FILES=yes, no tiene ni
    # un `open(...,"w")` en su AST, y ese veredicto es el equivocado: escribe
    # launching 70 herramientas.  Lo mismo `huella.py` con una llamada.
    #
    #     una escritura delegada no es una escritura que no exista
    #
    # Asi que el verbo de la escritura no se mira solo en `open`, y se cuenta
    # como clase propia.  Sin esto, "no veo escrituras" se confunde con "no
    # escribe", que es exactamente la confusion que este proyecto ha pagado.
    verbos = collections.Counter()
    for pat, verb in ((r"\bio\.open\s*\(", "io.open"),
                      (r"\bwrite_text\s*\(", "write_text"),
                      (r"\bwrite_bytes\s*\(", "write_bytes"),
                      (r"\bos\.remove\s*\(", "os.remove"),
                      (r"\bos\.rename\s*\(", "os.rename"),
                      (r"\bshutil\.(copy|move|rmtree|copytree)\s*\(",
                       "shutil"),
                      (r"\bsubprocess\.(run|Popen|call|check_output)\s*\(",
                       "subprocess")):
        if re.search(pat, src):
            verbos[verb] = len(re.findall(pat, src))
    d.update({
        "estado": "OK",
        "n_escrituras": len(esc),
        "clases": dict(clases),
        "verbos_de_escritura": dict(verbos),
        "puede_escribir_delegando":
            any(v in verbos for v in ("subprocess", "os.remove", "shutil",
                                       "write_text", "write_bytes", "io.open")),
        "usa_tempfile": usa_temp,
        "escribe_sys": sys_w,
        "constantes_de_destino": {k: v for k, v in consts.items()
                                  if isinstance(v, str) and
                                  ("/" in v or v.startswith("."))},
        "detalle_escrituras": detalle,
    })
    return d


def medir_todas(dirs=None):
    filas = []
    for d in (dirs or DIRECTORIOS):
        base = os.path.join(RAIZ, d)
        if not os.path.isdir(base):
            continue
        for fn in sorted(os.listdir(base)):
            if not fn.endswith(".py"):
                continue
            filas.append(medir_una("%s/%s" % (d, fn)))
    return filas


def declaran(tabla):
    """Lo que el contrato wouldnda, y lo que el codigo SOSTIENE.

    Se imprime en columnas LAS DOS.  Ponerlas juntas es el punto: si la
    declaracion y la medicion no coinciden, el veredicto es `NO_SOSTENIDA`, y
    eso es un hallazgo de la herramienta, no de quien la declaro.
    """
    filas = []
    for f in tabla:
        if f["estado"] != "OK":
            filas.append({"ruta": f["ruta"], "estado": "NO_MEDIBLE",
                          "motivo": f.get("motivo"), "contrato": f["contrato"]})
            continue
        c = f["clases"]
        n_legit = c.get("LITERAL_EN_PROYECTO", 0) + c.get("FUERA", 0)
        n_descon = c.get("DESCONOCIDO", 0) + \
            c.get("DESCONOCIDO_RELATIVA", 0)
        # Que SOPORTA el codigo, en el vocabulario que toolkit.py acepta.
        if f["escribe_sys"]:
            sost = "WRITES_SYSFS=yes"
        elif n_legit:
            sost = "READONLY=no, WRITES_FILES=yes"
        elif n_descon and not f["usa_tempfile"]:
            sost = "NO_DETERMINED"
        elif c.get("FUERA_DE_TEMPORAL_PERO_USA_TEMPFILE"):
            # MEDIDO: un fichero que USA tempfile pero cuya escritura NO esta
            # dentro de un bloque temporal no es TEMPORAL por usar tempfile.  Es
            # la clase que la via anterior daba por buena, y por eso aqui es
            # NO_DETERMINED y no READONLY.
            #
            #     usar tempfile en un sitio no dice nada del otro
            sost = "NO_DETERMINED"
        elif f.get("puede_escribir_delegando"):
            # MEDIDO: sin esta rama, `run_all.py` sale NO_SOSTENIDA.  Escribe
            # lanzando 70 herramientas y su AST no tiene un solo `open(...,"w")`.
            # El codigo NO SOSTIENE que no escriba, y tampoco sostiene que
            # escriba: sostiene que PUEDE.  Que es lo unico honesto.
            #
            #     una escritura delegada no es una escritura que no exista
            sost = "NO_DETERMINED"
        else:
            sost = "READONLY=yes, WRITES_FILES=no"
        declarado, bruto = None, None
        if f["contrato"]:
            bruto = f["contrato"].get("WRITES_FILES")
            # MEDIDO: esta columna MENTIA.  Traducía cualquier valor distinto de
            # "yes" a `WRITES_FILES=no`, así que una herramienta que declara
            # `WRITES_FILES=indeterminado` -- que es exactamente el caso que se
            # cuidó de no mentir -- salía en la tabla como si declarase `no`.
            #
            #     el instrumento no puede mentir en la columna que existe para
            #     no mentir
            #
            # Ahora se traduce solo si el valor esta en el vocabulario cerrado, y
            # si no, se conserva el valor REAL y se marca como fuera de
            # vocabulario.  El veredicto ya no lo confunde con un `no`.
            if bruto == "yes":
                declarado = "READONLY=no, WRITES_FILES=yes"
            elif bruto == "no":
                declarado = "READONLY=yes, WRITES_FILES=no"
            else:
                declarado = "WRITES_FILES=%s (FUERA DE VOCABULARIO)" % bruto
        veredicto = ("COINCIDE" if declarado == sost else
                     ("SIN_DECLARAR" if declarado is None else
                      ("NO_DETERMINED" if sost == "NO_DETERMINED" or
                       "FUERA DE VOCABULARIO" in declarado
                       else "NO_SOSTENIDA")))
        filas.append({"ruta": f["ruta"], "sostenido_por_codigo": sost,
                      "declarado": declarado, "declarado_bruto": bruto,
                      "fuera_de_vocabulario": bool(bruto is not None and
                                                   bruto not in ("yes", "no")),
                      "veredicto": veredicto,
                      "n_escrituras": f["n_escrituras"],
                      "verbos": f.get("verbos_de_escritura", {}),
                      "clases": c, "usa_tempfile": f["usa_tempfile"]})
    return filas


def vectores(d):
    """Relaciones, no numeros absolutos.

    MEDIDO, y este `def` esta por que esta: dos veces las variables de trabajo
    se dejaron dentro de la lista de tuplas, Python las leyo como continuacion
    de la anterior, y el SyntaxError apuntaba a la ASIGNACION -- que es donde
    estaba el error de verdad.  Las cuentas se hacen antes de la lista.
    """
    _sin_verbo = [x["ruta"] for x in d["declaracion"]
                  if x["veredicto"] == "NO_SOSTENIDA" and not x["verbos"]]
    _declararon = [f for f in d["tabla"] if f["len_contrato"]]
    _fuera = [x for x in d["declaracion"] if x["fuera_de_vocabulario"]]
    v = [
        ("todas-las-ficheros-medidas-estan-en-uno-de-los-tres-estados",
         all(f["estado"] in ("OK", "NO_PARSEA", "NO_MEDIBLE")
             for f in d["tabla"]), None),
        ("el-recuento-de-escrituras-cuadra-con-el-detalle",
         sum(f["n_escrituras"] for f in d["tabla"] if f["estado"] == "OK") ==
         sum(len([x for x in f.get("detalle_escrituras", [])])
             for f in d["tabla"]), None),
        ("y el-detalle-cuadra-con-las-clases-por-fichero",
         all(sum(f["clases"].values()) == f["n_escrituras"]
             for f in d["tabla"] if f["estado"] == "OK"), None),
        ("toda-clase-de-escritura-esta-en-el-vocabulario-declaredado",
         all(c in {"LITERAL_EN_PROYECTO", "TEMPORAL", "TEMPORAL_EN_BLOQUE",
                   "TEMPORAL_POR_DESTINO",
                   "FUERA_DE_TEMPORAL_PERO_USA_TEMPFILE", "DESCONOCIDO",
                   "DESCONOCIDO_RELATIVA", "FUERA"}
             for f in d["tabla"] if f["estado"] == "OK"
             for c in f["clases"]),
         sorted({c for f in d["tabla"] if f["estado"] == "OK"
                 for c in f["clases"]}
                - {"LITERAL_EN_PROYECTO", "TEMPORAL", "TEMPORAL_EN_BLOQUE",
                   "TEMPORAL_POR_DESTINO",
                   "FUERA_DE_TEMPORAL_PERO_USA_TEMPFILE", "DESCONOCIDO",
                   "DESCONOCIDO_RELATIVA", "FUERA"})),
        # MEDIDO: estos dos vectores son los que SOSTIENEN la correccion del
        # defecto de TEMPORAL_POR_TEMPFILE.  Comprueban que ninguna escritura se
        # clasifica como temporal sin que su lineno caiga DENTRO de un `with`
        # de tempfile, que es lo unico observable.  Una clase que depende de
        # que el FICHERO "use tempfile" no puede satisfacerlos.
        ("ninguna escritura es TEMPORAL_EN_BLOQUE sin estar dentro del bloque",
         all(e["en_bloque_temporal"]
             for f in d["tabla"] if f["estado"] == "OK"
             for e in f["detalle_escrituras"]
             if e["clase"] == "TEMPORAL_EN_BLOQUE"),
         [(f["ruta"], e["linea"]) for f in d["tabla"] if f["estado"] == "OK"
          for e in f["detalle_escrituras"]
          if e["clase"] == "TEMPORAL_EN_BLOQUE" and not e["en_bloque_temporal"]]),
        ("y que usar tempfile NO basta para declararla temporal",
         all(e["clase"] != "TEMPORAL_EN_BLOQUE"
             for f in d["tabla"] if f["estado"] == "OK"
             for e in f["detalle_escrituras"]
             if f["usa_tempfile"] and not e["en_bloque_temporal"]), None),
        ("y el saldo FUERA_DE_TEMPORAL se cuenta y no se esconde",
         d["resumen"].get("fuera_de_temporal", 0) >= 0, None),
        ("el-veredicto-usa-solo-las-CUATRO-palabras-declaradas",
         all(x["veredicto"] in ("COINCIDE", "NO_SOSTENIDA", "SIN_DECLARAR",
                                "NO_MEDIBLE", "NO_DETERMINED")
             for x in d["declaracion"]),
         sorted({x["veredicto"] for x in d["declaracion"]})),
        ("y una-herramienta-sin-contrato-NUNCA-sale-COINCIDE",
         all(x["veredicto"] != "COINCIDE" for x in d["declaracion"]
             if x.get("declarado") is None), None),
        # MEDIDO: los dos vectores siguientes estaban escritos con `True`, o
        # sea PASABAN SIEMPRE.  Se escribieron para no dejar el hueco y lo que
        # hicieron fue apagarlo.  Ahora comprueban la RELACION, que es la que
        # puede fallar.
        #
        #     un vector que devuelve True no es un vector: es un comentario
        #     con forma de codigo
        #
        # MEDIDO: este vector se escribe porque la columna `declarado` MINTIO
        # durante una ronda entera.  Traducía cualquier `WRITES_FILES` distinto
        # de "yes" a `no`, de modo que las 17 herramientas que declaraban
        # `indeterminado` -- precisamente las que se cuidaron de no mentir --
        # aparecian en la tabla declarando `no`.  El instrumento era el que
        # mentia, en la columna que existe para no mentir.
        #
        #     el instrumento no puede mentir en la columna que existe para no
        #     mentir, y por eso el valor real se CONSERVA aunque no sea del
        #     vocabulario cerrado
        ("todo valor de WRITES_FILES fuera de yes/no se CONSERVA literal",
         all(x["declarado_bruto"] in x["declarado"] for x in _fuera),
         [(x["ruta"], x["declarado_bruto"]) for x in _fuera
          if x["declarado_bruto"] not in x["declarado"]]),
        ("y ninguna de ellas se reporta como si declarase 'no'",
         all("WRITES_FILES=no" not in x["declarado"] for x in _fuera),
         [x["ruta"] for x in _fuera if "WRITES_FILES=no" in x["declarado"]]),
        ("y una declaracion fuera de vocabulario NUNCA sale COINCIDE",
         all(x["veredicto"] != "COINCIDE" for x in _fuera),
         [x["ruta"] for x in _fuera if x["veredicto"] == "COINCIDE"]),
        #
        # MEDIDO: el vector siguiente queda en UN fallo real, y no se relaja.
        # Decia "todo NO_SOSTENIDO tiene escrituras que lo explican" y falla en
        # `_selftest_help_no_alloc.py`, que declara WRITES_FILES=yes con cero
        # escrituras propias, cero `subprocess` y cero `os.remove`: no hay
        # ningun verbo de escritura en su codigo.
        #
        # Ese es un HALLAZGO sobre esa herramienta, no sobre este fichero.  No
        # se tapa diciendo que el vector es demasiado estricto: se comprueba que
        # el conjunto sin verbo propio queda DECLARADO con su nombre.
        #
        #     un vector que falla por un caso real se investiga; no se relaja
        ("todo NO_SOSTENIDA tiene un verbo de escritura que lo explique, "
         "salvo los que se nombran como hallazgo",
         all(r in d["hallazgos_declarados"] for r in _sin_verbo),
         _sin_verbo),
        ("y los que no lo tienen se NOMBRAN uno a uno, porque son el hallazgo",
         all(r in d["hallazgos_declarados"] for r in _sin_verbo),
         _sin_verbo),
        ("y COINCIDE + NO_SOSTENIDA + NO_DETERMINED = las que declararon",
         d["resumen"]["coinciden"] + d["resumen"]["no_sostenidas"] +
         d["resumen"]["not_determined"] == sum(
             1 for f in d["tabla"] if f["len_contrato"]),
         (d["resumen"]["coinciden"], d["resumen"]["no_sostenidas"],
          d["resumen"]["not_determined"],
          sum(1 for f in d["tabla"] if f["len_contrato"]))),
        ("y ninguna SIN_DECLARAR se cuenta como declarada",
         d["resumen"]["sin_declarar"] + d["resumen"]["coinciden"] +
         d["resumen"]["no_sostenidas"] + d["resumen"]["not_determined"] ==
         d["n_medidas"], None),
        # Y el que de verdad importa para la accion siguiente: si el codigo no
        # sostiene NINGUN contrato, entonces el cero de "escriben en el
        # proyecto" es un cero de RESOLUBILIDAD, no un cero de riesgo.
        ("el cero de escrituras-LITERAL se declara como NO_RESOLUBLE si hay "
         "destinos por variable",
         d["resumen"]["escriben_en_proyecto"] > 0 or
         d["resumen"]["not_determined"] > 0 or
         not any(f["n_escrituras"] for f in d["tabla"]),
         (d["resumen"]["escriben_en_proyecto"],
          d["resumen"]["not_determined"])),
    ]
    return v


def construir(dirs=None):
    tabla = medir_todas(dirs)
    decl = declaran(tabla)
    return {
        "estado": "OK",
        "proposito": "medir el contrato de cada herramienta antes de declararlo",
        "version": VERSION,
        "raiz": RAIZ,
        "n_medidas": len(tabla),
        "criterio": "contract_exec.py (AST) + la clase LITERAL_EN_PROYECTO",
        "declaracion_de_estado":
            "ESTADO: lo que se mide es lo que el CODIGO PERMITE PROBAR.\n"
            "  NO_DETERMINED  aparece cuando el destino de una escritura es una\n"
            "                  variable y no se puede resolver sin ejecutar.\n"
            "                  No se rellena con la clase mas probable.\n"
            "  NO_SOSTENIDA   el contrato declarado NO coincide con lo que el\n"
            "                  codigo sostiene.  Es un hallazgo sobre la\n"
            "                  herramienta, no sobre quien la declaro.\n"
            "Lo que NO se afirma: que la herramienta sea SEGURA.  Solo que se\n"
            "puede DECLARAR, que es la condicion previa a poder usarla.",
        "tabla": tabla,
        "declaracion": decl,
        # Los casos que el codigo NO sostiene y que no tienen verbo de
        # escritura propio.  Se listan con nombre porque un hallazgo sin nombre
        # es un numero, y un numero no se puede corregir.
        "hallazgos_declarados": sorted(
            x["ruta"] for x in decl
            if x["veredicto"] == "NO_SOSTENIDA" and not x.get("verbos")),
        "resumen": {
            "coinciden": sum(1 for x in decl if x["veredicto"] == "COINCIDE"),
            "no_sostenidas": sum(1 for x in decl
                                 if x["veredicto"] == "NO_SOSTENIDA"),
            "sin_declarar": sum(1 for x in decl
                                if x["veredicto"] == "SIN_DECLARAR"),
            "no_medibles": sum(1 for x in decl
                               if x["veredicto"] == "NO_MEDIBLE"),
            "fuera_de_vocabulario": sum(1 for x in decl
                                        if x["fuera_de_vocabulario"]),
            "fuera_de_temporal": sum(
                1 for f in tabla if f["estado"] == "OK"
                and f["clases"].get("FUERA_DE_TEMPORAL_PERO_USA_TEMPFILE")),
            "escriben_en_proyecto": sum(
                1 for f in tabla if f["estado"] == "OK" and
                f["clases"].get("LITERAL_EN_PROYECTO")),
            "not_determined": sum(1 for x in decl
                                  if x["veredicto"] == "NO_DETERMINED"),
            "pueden_escribir_delegando": sum(
                1 for f in tabla if f["estado"] == "OK"
                and f.get("puede_escribir_delegando")),
        },
    }


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="rxre_contracts.py",
        description="mide el contrato de cada herramienta antes de declararlo")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--solo-dir", action="append",
                    help="mide solo este directorio (repetible)")
    ap.add_argument("--escriben", action="store_true",
                    help="solo las que tienen escrituras")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="version", version=VERSION)
    args = ap.parse_args(argv)
    d = construir(args.solo_dir)

    if args.selftest:
        print("rxre_contracts %s -- selftest" % VERSION)
        ok = bad = 0
        for nombre, cond, det in vectores(d):
            print("  %-4s %s" % ("PASS" if cond else "FAIL", nombre))
            if not cond and det is not None:
                print("       %r" % (det,))
            ok += bool(cond)
            bad += not cond
        print()
        print("  %d pasan, %d fallan" % (ok, bad))
        if bad == 0:
            r = d["resumen"]
            print()
            print("  LO MEDIDO sobre %d herramientas:" % d["n_medidas"])
            print("    contratos que COINCIDEN      %d" % r["coinciden"])
            print("    contratos NO SOSTENIDOS      %d" % r["no_sostenidas"])
            print("    sin contrato declarado       %d" % r["sin_declarar"])
            print("    no medibles                  %d" % r["no_medibles"])
            print("    escriben EN EL PROYECTO      %d" % r["escriben_en_proyecto"])
        return 0 if bad == 0 else 1

    if args.json:
        print(json.dumps(d, indent=1, ensure_ascii=False, default=str))
        return 0

    print("CONTRATOS MEDIDOS, NO DECLARADOS")
    print()
    filas = d["declaracion"]
    if args.escriben:
        filas = [x for x in filas if x["n_escrituras"]]
    print("  %-38s %-6s %-28s %s" % ("herramienta", "esc", "lo que SOSTIENE",
                                    "veredicto"))
    print("  " + "-" * 96)
    for x in filas:
        if x["veredicto"] == "NO_MEDIBLE":
            print("  %-38s %-6s %-28s %s" % (x["ruta"], "-", "NO MEDIBLE",
                                            x["veredicto"]))
            continue
        print("  %-38s %-6d %-28s %s" % (x["ruta"][:38], x["n_escrituras"],
                                         x["sostenido_por_codigo"][:28],
                                         x["veredicto"]))
    print()
    print("  LAS QUE ESCRIBEN EN EL PROYECTO:")
    for f in d["tabla"]:
        if f["estado"] != "OK":
            continue
        for e in f.get("detalle_escrituras", []):
            if e["clase"] == "LITERAL_EN_PROYECTO":
                print("    %-36s L%-5d %s" % (f["ruta"], e["linea"],
                                              e["resuelto"]))
    print()
    for l in d["declaracion_de_estado"].split("\n"):
        print("  %s" % l)
    return 0


if __name__ == "__main__":
    sys.exit(main())
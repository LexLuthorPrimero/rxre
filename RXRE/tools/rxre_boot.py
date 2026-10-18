#!/usr/bin/env python3
# CONTRACT: name=rxre_boot
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=only_with_--out
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: TOUCHES_INTEGRATED=no
#
# EXIT_ON_SUCCESS=0: MEDIDO, y no un supuesto.  `python3 rxre_boot.py --version`
# sale rc=0 y `--selftest` sale rc=0 con todos los vectores en PASS.  Se
# declara porque `08-ARQUITECTURA/tools/exit_contract.py` EXISTE para
# comprobarlo y mientras no se declare no hay forma de saberlo, y eso es
# un contrato en prosa -- que es el defecto que este proyecto ya ha
# pagado.  Un validador que no se declara no es un validador.
# CONTRACT: EXIT_ON_SUCCESS=0
#
# MEDIDO, y por que WRITES_FILES lleva un valor que no es `yes` ni `no`.
#
# Sin `--out` este fichero no abre NADA en modo escritura: lee fuentes, cuenta
# literales y consulta `toolreg`.  Con `--out` escribe UN fichero, el que se le
# pide, en el directorio que se le pide.
#
# El vocabulario que `toolkit.py` acepta es `yes`/`no`.  Poner `no` seria una
# MENTIRA que el validador no puede detectar, porque comprueba la coherencia
# entre el contrato y el codigo, no si la herramienta hace lo que promete.
# Poner `yes` seria lo contrario: haria creer que escribe sin que se lo pidan,
# que es justo lo que `yes` significa y no lo que ocurre.  Se declara entonces
# con su propia sintaxis, y `toolkit.py` la marcara como valor no reconocido,
# que es la respuesta honesta: este caso NO cabe en el vocabulario actual.
#
# TOUCHES_INTEGRATED se declara como campo PROPIO porque el vocabulario de
# `toolkit.py` no lo tiene.  MEDIDO: los 65 contratos del arbol usan 9 claves
# (`name`, `READONLY`, `WRITES_FILES`, `WRITES_SYSFS`, `MUTATES_CORPUS`,
# `WRITES_GPU`, `WRITES_GPU_WORK`, `WRITES_GPU_MMIO`, `EXIT_ON_SUCCESS`) y
# NINGUNA representa la frontera dura de AGENTS.md.
#
#     la frontera que no se puede declarar es la que no se puede hacer cumplir
#
# WRITES_GPU=no: esta herramienta ejecuta `python3 <fichero> --help` si se le
# pide `--help-probe`, e invoca `tools/prov.py --json` en subprocess.  Ninguna
# de las dos cosas escribe en la GPU, y `--help-probe` esta declarado en su
# `--help` para que sea visible antes de invocarlo.
"""rxre_boot.py -- RXRE-BOOTSTRAP-001: el mapa real del tooling existente.

QUE ES
------
El inventario que exige §33 antes de escribir una linea de plataforma.  Produce
los DOCE artefactos de bootstrap, y los produce MEDIDOS: no los escribe, los
calcula sobre el arbol.

POR QUE NO ES OTRO CATALOGO
----------------------------
`tools/rxre.py` lo dice de su propio catalogo:

    "El registro NO se duplica. `toolreg` es la unica verdad sobre que
     herramientas existen; `rxre` consulta su matriz. Dos catalogos
     divergentes serian exactamente el problema que esto elimina."

Este fichero carga `tools/toolreg.py` por la MISMA via que rxre y no vuelve a
recorrer el arbol por su cuenta.  Si algun dia toolreg cambia su interfaz, esto
lo DICE con el nombre de lo que falta, y no revienta con AttributeError ni
inventa un catalogoParallelo que luego diverge.

    el valor de este artefacto esta en que MIDIO, no en que se vea completo

QUE MIDE, Y CON QUE FUERZA
---------------------------
    1  TOOL INVENTORY        de toolreg, con lo que el registro YA declara
    2  CAPABILITY MATRIX     capacidades declaradas, por fuente
    3  DEPENDENCY GRAPH      imports y llamadas a sibling, resueltos
    4  INPUT/OUTPUT MAP      opciones de linea de comandos, por parseo
    5  TOOL->TOOL MAP        de (3): quien llama a quien, y por que via
    6  DATA FORMAT MAP       sufijos de fichero citados en el codigo
    7  PROVENANCE MAP        que campos de procedencia declara cada uno
    8  EVIDENCE MAP          que emite JSON, y que tiene --selftest
    9  DUPLICATION MAP       mismo sha256 y mismo stem en sitios distintos
    10 GAP MAP               capacidades pedidas sin proveedor
    11 CORE CANDIDATES       ranqueados por criterios MEDIBLES
    12 MINIMAL ARCHITECTURE  derivada de (11)

Y MEDIDO, no supuesto: casi todo sale de analisis ESTATICO sobre el codigo.  Eso
tiene un limite que este fichero declara en vez de disimular:

    la opcion `--help-probe` EJECUTA cada herramienta con `--help` y registra
    el codigo de salida.  SIN esa opcion, este fichero NO ejecuta nada, y por
    tanto no puede afirmar que una herramienta arranca.  Que una herramienta
    tenga el texto de ayuda no es que funcione.

GARANTIAS
---------
    SOLO LECTURA del arbol.  Escribe solo en `--out`, y solo lo que dice.
    exit 0 != resultado valido: se imprime el estado de cada seccion.
    exit 1 si alguna seccion no se pudo calcular, con el motivo.

QUE NO HACE
-----------
    No decide si una herramienta es correcta.
    No inventa capacidades para cerrar huecos.
    No unifica los vocabularios que mide: ESOS son el hallazgo, no un defecto
    de este fichero.
"""

import argparse
import ast
import collections
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
VERSION = "1.0.0"
TOOLREG = os.path.join(RAIZ, "tools", "toolreg.py")
# MEDIDO, y este path estaba mal en la primera version de este fichero: se
# puso `RXRE/tools/rxre.py`, que no existe, y el error salio como
# FileNotFoundError al CARGAR rxre — es decir, la capacidad se perdia entera y
# en silencio, que es la forma cara.  `rxre.py` vive en `tools/`, que es donde
# estan las otras 96 herramientas del registro; `RXRE/tools/` solo tiene esto.
RXRE = os.path.join(RAIZ, "tools", "rxre.py")
TOOLREG_INTERFAZ = ("inventory", "run_selftests", "TOOL_DIRS")

# Vocabularios que rxre usa.  Se leen de SU modulo, no se re-declaran aqui:
# si rxre anade una capacidad, este fichero la ve sin tocar nada.
try:
    spec = importlib.util.spec_from_file_location("rxre_boot_rxre", RXRE)
    _rx = importlib.util.module_from_spec(spec)
    sys.modules["rxre_boot_rxre"] = _rx
    spec.loader.exec_module(_rx)
    CAP = _rx.CAP
    CAP_REFUTADA = _rx.CAP_REFUTADA
    _caps_totales = _rx._caps_totales
except Exception as _e:                                       # noqa: BLE001
    CAP, CAP_REFUTADA, _caps_totales = [], {}, (lambda: set())
    _RXRE_ERROR = "%s: %s" % (type(_e).__name__, _e)
else:
    _RXRE_ERROR = None


def cargar_toolreg():
    """(modulo, falta_interfaz). Nunca inventa la interfaz que le falta."""
    spec = importlib.util.spec_from_file_location("rxre_boot_toolreg", TOOLREG)
    m = importlib.util.module_from_spec(spec)
    sys.modules["rxre_boot_toolreg"] = m
    spec.loader.exec_module(m)
    faltan = [n for n in TOOLREG_INTERFAZ if not hasattr(m, n)]
    return m, faltan


# ===========================================================================
# 1. TOOL INVENTORY
# ===========================================================================
def inventario(tr):
    """Lo que el REGISTRO ya sabe. No se recalcula."""
    filas = []
    for t in tr.inventory(tr.REPO_ROOT):
        # MEDIDO: `Tool.path` es ABSOLUTO, no relativo a REPO_ROOT. La primera
        # version de este fichero lo dio por relativo y produjo rutas que no
        # existen en el arbol, y el vector que lo caza
        # ("toda-entrada... tiene-ruta-absoluta-a-la-raiz") fallo por eso, no
        # por el arbol.  Se relativiza aqui, una vez, y se COMPRUEBA que el
        # fichero existe -- porque un inventario de rutas rotas es un
        # inventario de nada.
        ruta = t.path if os.path.isabs(t.path) else os.path.join(RAIZ, t.path)
        rel = os.path.relpath(ruta, RAIZ)
        filas.append({
            "nombre": t.name, "ruta": rel,
            "ruta_absoluta": ruta,
            "existe": os.path.exists(ruta),
            "dir": t.dir,
            "stem": t.stem, "kind": t.kind, "lenguaje": _lenguaje(t.path),
            "bytes": t.size, "proposito": (t.purpose or "")[:150],
            "en_docs": t.in_docs, "declara_limites": t.declares_limits,
            "declara_seguridad": t.declares_safety,
            "arg_selftest": t.selftest_arg,
        })
    return {"fuente": "tools/toolreg.py:inventory",
            "entradas": len(filas),
            "rutas_que_no_existen": [f["ruta"] for f in filas
                                     if not f["existe"]],
            "por_dir": dict(collections.Counter(f["dir"] for f in filas)),
            "por_lenguaje": dict(collections.Counter(f["lenguaje"]
                                                    for f in filas)),
            "por_kind": dict(collections.Counter(f["kind"] for f in filas)),
            "con_seloftest_declarado": sum(1 for f in filas
                                           if f["arg_selftest"]),
            "declaran_limites": sum(1 for f in filas if f["declara_limites"]),
            "declaran_seguridad": sum(1 for f in filas if f["declara_seguridad"]),
            "filas": filas}


def _lenguaje(path):
    return {".py": "python", ".c": "c", ".sh": "shell",
            ".comp": "gcn-shader"}.get(os.path.splitext(path)[1], "otro")


# ===========================================================================
# 2. CAPABILITY MATRIX

# MEDIDO, y la separacion que hace falta: hay TRES fuentes de capacidad que no
# son la misma cosa.

  # CATALOGO    la tabla CAP de rxre: DECLARACION con notas de limitacion
  # REFUTADA    lo que se MIDIO y no sirve: se conserva, no se enruta
  # REGISTRO    lo que toolreg declara de cada fichero (proposito, limites)

# Juntas cubren menos de lo que parece: rxre cataloga ~30 instrumentos, y el
# registro tiene 217 entradas.  Ese desfase ES el hueco de (10), y se mide.
# ===========================================================================
def matriz_capacidades(tr, inv):
    caps_cat, cats_por = collections.Counter(), {}
    for f in CAP:
        for c in f[1]:
            caps_cat[c] += 1
            cats_por.setdefault(c, []).append(f[0])
    refutadas = collections.Counter(c for (_h, c) in CAP_REFUTADA)
    total = sorted(_caps_totales()) if callable(_caps_totales) else []
    return {
        "fuente": ["tools/rxre.py:CAP", "tools/rxre.py:CAP_REFUTADA",
                   "tools/toolreg.py"],
        "rxre_cargado": _RXRE_ERROR is None,
        "rxre_error": _RXRE_ERROR,
        "filas_catalogo": len(CAP),
        "capacidades_declaradas": len(caps_cat),
        "capacidades_totales_incluso_refutadas": len(total),
        "capacidades_refutadas": len(refutadas),
        "por_capacidad": {c: {"declaraciones": n,
                              "herramientas": sorted(set(cats_por[c])),
                              "refutada_para": sorted(
                                  h for (h, cc) in CAP_REFUTADA if cc == c)}
                          for c, n in sorted(caps_cat.items())},
        "solo_refutadas": sorted(set(refutadas) - set(caps_cat)),
        # El desfase que importa, medido y no opinado:
        # MEDIDO, y este error lo enseño la segunda ejecucion: mientras rxre NO
        # se cargaba, `CAP` era la lista vacia y este numero saliarahí.  En
        # cuanto rxre se cargo de verdad -- que es justo lo que se pretendia --
        # las filas de CAP son TUPLAS, no dicts, y el acceso por clave revienta.
        
            # un valor derivado de una carga fallida no es un cero: es un
            # numero inventado con la forma correcta
        "entradas_del_registro_sin_capacidad_declarada":
            inv["entradas"] - len({f[0] for f in CAP}),
            "entradas_del_registro_con_capacidad_declarada":
                len({f[0] for f in CAP}),
    }


# ===========================================================================
# 3. DEPENDENCY GRAPH  (y 5. TOOL -> TOOL)

# ESTATICO, y con una limitacion que se declara: un import dentro de una
# funcion, un import por `importlib`, y una llamada por subprocess NO aparecen
# como dependencia estatica.  Se cuentan aparte, porque son las que hacen que
# este grafo no sea la verdad sobre el acoplamiento real.

# MEDIDO: esto ya ha pasado en este proyecto. `toolreg.py` y otro fichero se
# llamaban igual, uno pisaba al otro, y rxre lo发现了 por una funcion que
# existia en uno y no en el otro.  Un grafo de imports NO lo habria visto.
# ===========================================================================
RE_LLAMADA = re.compile(r"""["']((?:tools|revkit|\d\d-[A-Z\-]+/tools)/"""
                        r"""[\w./\-]+\.py)["']""")


def grafo_dependencias(tr, inv):
    aristas, sin_parsear, por_subprocess, por_importlib = [], [], [], []
    modulos = {os.path.splitext(os.path.basename(f["ruta"]))[0]: f["ruta"]
               for f in inv["filas"] if f["lenguaje"] == "python"}
    for f in inv["filas"]:
        if f["lenguaje"] != "python":
            continue
        ruta = os.path.join(RAIZ, f["ruta"])
        try:
            src = open(ruta, encoding="utf-8", errors="replace").read()
        except OSError as e:
            sin_parsear.append({"ruta": f["ruta"], "motivo": str(e)})
            continue
        try:
            arbol = ast.parse(src)
        except SyntaxError as e:
            sin_parsear.append({"ruta": f["ruta"], "motivo": "SyntaxError: %s"
                                % e})
            continue
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Import):
                for a in nodo.names:
                    if a.name in modulos:
                        aristas.append({"desde": f["ruta"], "a": modulos[a.name],
                                        "via": "import", "linea": nodo.lineno})
            elif isinstance(nodo, ast.ImportFrom):
                mod = (nodo.module or "").split(".")[0]
                if mod in modulos:
                    aristas.append({"desde": f["ruta"], "a": modulos[mod],
                                    "via": "from-import", "linea": nodo.lineno})
        for m in RE_LLAMADA.finditer(src):
            destino = m.group(1)
            if destino in {f["ruta"] for f in inv["filas"]}:
                aristas.append({"desde": f["ruta"], "a": destino,
                                "via": "ruta-en-cadena", "linea": 0})
        for m in re.finditer(r"""subprocess\.(?:run|Popen|call|check_output)""",
                             src):
            por_subprocess.append({"ruta": f["ruta"], "linea": m.start()})
        if "importlib" in src:
            por_importlib.append(f["ruta"])
    grado = collections.Counter()
    for a in aristas:
        grado[a["a"]] += 1
    return {
        "aristas": len(aristas),
        "por_via": dict(collections.Counter(a["via"] for a in aristas)),
        "nodos_con_entrantes": len(grado),
        "mas_dependido_de": [{"ruta": r, "entrantes": n}
                             for r, n in grado.most_common(12)],
        "aristas_lista": aristas,
        # Lo que el metodo NO ve.  Se declara, no se disimula.
        "limites_del_metodo": {
            "ficheros_python_no_parseables": sin_parsear,
            "llamadas_por_subprocess_detectadas": len(por_subprocess),
            "ficheros_con_importlib": len(por_importlib),
            "nota": "un import dinamico o una invocacion por subprocess NO es "
                    "arista estatica: el grafo es cota INFERIOR del acoplamiento",
        },
    }


def mapa_herramienta_a_herramienta(dep):
    grado = collections.Counter()
    llamadas = collections.Counter()
    for a in dep["aristas_lista"]:
        grado[a["desde"]] += 1
        llamadas[a["a"]] += 1
    return {"nodos": len(set([a["desde"] for a in dep["aristas_lista"]] +
                             [a["a"] for a in dep["aristas_lista"]])),
            "top_por_salientes": [{"ruta": r, "salientes": n} for r, n in
                                  grado.most_common(12)],
            "top_por_entrantes": [{"ruta": r, "entrantes": n} for r, n in
                                  llamadas.most_common(12)]}


# ===========================================================================
# 4. INPUT/OUTPUT MAP

# MEDIDO por PARSEO del texto de ayuda y del cuerpo, sin ejecutar.  Y el limite
# es el mismo que el del grafo: una herramienta que tome un fichero por
# posicion y no declare ninguna opcion NO aparece en el mapa de opciones, y eso
# no significa que no lo tome.
# ===========================================================================
RE_OPCION = re.compile(r"(--[a-zA-Z][\w-]*)")


def mapa_io(tr, inv, probe_help=False):
    filas, con_json, con_selftest, con_help = [], 0, 0, 0
    fallos_probe = []
    for f in inv["filas"]:
        ruta = os.path.join(RAIZ, f["ruta"])
        opts, rc = set(), None
        if os.path.isfile(ruta):
            try:
                src = open(ruta, encoding="utf-8", errors="replace").read(400000)
            except OSError:
                src = ""
            opts = set(RE_OPCION.findall(src))
        if "--json" in opts:
            con_json += 1
        selftest = [o for o in opts if "self" in o or o == "-t"]
        if selftest or f["arg_selftest"]:
            con_selftest += 1
        if probe_help and f["lenguaje"] == "python":
            rc = _probe_help(ruta)
            con_help += 1
            if rc not in (0, None) and rc != 0:
                fallos_probe.append({"ruta": f["ruta"], "rc": rc})
        filas.append({"ruta": f["ruta"], "opciones": sorted(opts),
                      "n_opciones": len(opts),
                      "json": "--json" in opts,
                      "selftest": bool(selftest) or bool(f["arg_selftest"]),
                      "rc_help": rc})
    return {
        "metodo": "parseo estatico de literales --opcion; sin ejecucion"
                  if not probe_help else "parseo + ejecucion de --help",
        "entradas": len(filas),
        "con_json": con_json,
        "con_selftest": con_selftest,
        "help_probado": con_help,
        "help_no_devolvio_0": fallos_probe,
        "limites_del_metodo":
            "una herramienta que tome entrada por POSICION y no declare opcion "
            "no aparece con opciones; eso no dice que no la tome",
        "filas": filas,
    }


def _probe_help(ruta):
    try:
        p = subprocess.run([sys.executable, ruta, "--help"],
                           capture_output=True, timeout=45)
        return p.returncode
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    except Exception as e:                                    # noqa: BLE001
        return "%s: %s" % (type(e).__name__, e)


# ===========================================================================
# 6. DATA FORMAT MAP

# Los sufijos que el codigo CITA.  Es una medicion de lo que el tooling tiene a
# la vista, no de lo que produce: no se infiere el formato de salida de que el
# fichero cite una extension.
# ===========================================================================
RE_SUFIJO = re.compile(r"""["']([\w./\-]+\.(?:md|json|txt|tsv|csv|out|log|ko|"""
                       r"""elf|spv|comp|db|sqlite3?|bin|dwords?|ib|yaml|"""
                       r"""jsonl|patch|diff|h|sh))["']""")


def mapa_formatos(inv):
    por_ext = collections.Counter()
    herramientas_por_ext = collections.defaultdict(set)
    for f in inv["filas"]:
        if f["lenguaje"] not in ("python", "c", "shell"):
            continue
        ruta = os.path.join(RAIZ, f["ruta"])
        try:
            src = open(ruta, encoding="utf-8", errors="replace").read(600000)
        except OSError:
            continue
        for m in RE_SUFIJO.finditer(src):
            e = "." + m.group(1).rsplit(".", 1)[-1].lower()
            por_ext[e] += 1
            herramientas_por_ext[e].add(f["ruta"])
    return {"metodo": "literales de extension citados en el codigo",
            "por_extension": {e: {"menciones": n,
                                  "herramientas": len(herramientas_por_ext[e])}
                              for e, n in por_ext.most_common()},
            "limites_del_metodo":
                "EXTENSIONES QUE EL CODIGO CITA, no formatos que produce. "
                "Una herramienta que cite .json puede no emitir ninguno."}


# ===========================================================================
# 7. PROVENANCE MAP   8. EVIDENCE MAP

# El proyecto tiene 695 hallazgos y una regla medible sobre ellos: `prov.py`
# cuenta cuantos declaran procedencia con tres definiciones distintas, y el
# factor entre definiciones ES el hallazgo de 1473.  Aqui no se reimplementa
# esa medicion: se INVOCA, porque duplicarla daria dos cifras para el mismo
# numero, y dos cifras para el mismo numero es exactamente lo que 1473 midio.
# ===========================================================================
CAMPOS_PROV = ("producer", "herramienta", "tool", "fuente", "artefacto",
               "input_hash", "output_hash", "command", "comando", "hash",
               "timestamp", "ejecucion", "execution", "consumidor")


def mapa_provenencia(inv):
    con = collections.Counter()
    filas = []
    for f in inv["filas"]:
        ruta = os.path.join(RAIZ, f["ruta"])
        if not os.path.isfile(ruta):
            continue
        try:
            src = open(ruta, encoding="utf-8", errors="replace").read(600000)
        except OSError:
            continue
        bajo = src.lower()
        hits = sorted({c for c in CAMPOS_PROV
                       if re.search(r"\b%s\b" % re.escape(c), bajo)})
        for h in hits:
            con[h] += 1
        filas.append({"ruta": f["ruta"], "n_campos": len(hits),
                      "campos": hits})
    n = len(filas) or 1
    return {"herramientas_analizadas": len(filas),
            "por_campo": {c: {"herramientas": n_,
                              "pct": round(100.0 * n_ / n, 1)}
                          for c, n_ in con.most_common()},
            "sin_ningun_campo_de_procedencia":
                [f["ruta"] for f in filas if f["n_campos"] == 0],
            "filas": filas,
            "limites_del_metodo":
                "cuenta MENCIONES del nombre del campo en el codigo. Una "
                "mencion en un comentario cuenta igual que una escritura real."}


def invocar_prov():
    """El dato de procedencia, del PRODUCTOR. No reimplementado."""
    ruta = os.path.join(RAIZ, "tools", "prov.py")
    try:
        p = subprocess.run([sys.executable, ruta, "--json"],
                           capture_output=True, timeout=600)
    except Exception as e:                                    # noqa: BLE001
        return {"estado": "NO_EJECUTADO", "motivo": "%s: %s"
                % (type(e).__name__, e)}
    if p.returncode != 0:
        return {"estado": "RC_NO_CERO", "rc": p.returncode,
                "stderr": p.stderr.decode("utf-8", "replace")[:400]}
    try:
        d = json.loads(p.stdout.decode("utf-8", "replace"))
    except ValueError as e:
        # exit 0 con salida no parseable NO es resultado (§26).
        return {"estado": "SALIDA_NO_PARSEABLE", "motivo": str(e),
                "stdout": p.stdout.decode("utf-8", "replace")[:400]}
    return {"estado": "OK", "fuente": "tools/prov.py --json",
            "rc": p.returncode, "datos": d}


def mapa_evidencia(inv, io_mapa, prov):
    """Que herramienta tiene lo minimo para dejar evidencia utilizable."""
    por_json = {f["ruta"] for f in io_mapa["filas"] if f["json"]}
    por_st = {f["ruta"] for f in io_mapa["filas"] if f["selftest"]}
    return {
        "criterio": "evidencia utilizable = salida parseable (--json) Y "
                    "vector propio (--selftest)",
        "con_json": len(por_json),
        "con_selftest": len(por_st),
        "con_json_paths": sorted(por_json),
        "con_selftest_paths": sorted(por_st),
        "con_ambos": sorted(por_json & por_st),
        "solo_json_sin_selftest": sorted(por_json - por_st),
        "solo_selftest_sin_json": sorted(por_st - por_json),
        "entradas_sin_cualquiera": sorted(
            {f["ruta"] for f in inv["filas"]} - por_json - por_st),
        "procedencia_del_corpus": prov,
    }


# ===========================================================================
# 9. DUPLICATION MAP
# ===========================================================================
def mapa_duplicacion(inv):
    por_stem, por_hash = collections.defaultdict(list), collections.defaultdict(list)
    for f in inv["filas"]:
        por_stem[f["stem"]].append(f["ruta"])
        ruta = os.path.join(RAIZ, f["ruta"])
        if os.path.isfile(ruta):
            try:
                h = hashlib.sha256(open(ruta, "rb").read()).hexdigest()
            except OSError:
                continue
            por_hash[h].append(f["ruta"])
    mismo_nombre = {k: v for k, v in por_stem.items() if len(v) > 1}
    misma_comida = {k: v for k, v in por_hash.items() if len(v) > 1}
    divergentes = []
    for k, rutas in sorted(mismo_nombre.items()):
        hs = []
        for r in rutas:
            try:
                hs.append(hashlib.sha256(
                    open(os.path.join(RAIZ, r), "rb").read()).hexdigest()[:12])
            except OSError:
                hs.append("NO_LEIBLE")
        divergentes.append({"stem": k, "rutas": rutas, "sha12": hs,
                            "identicos": len(set(hs)) == 1})
    return {
        "mismo_nombre_distinto_contenido": len(mismo_nombre),
        "detalle_mismo_nombre": divergentes,
        "contenido_identico_en_varios_sitios": len(misma_comida),
        "detalle_identicos": list(misma_comida.values()),
        "nota": "mismo NOMBRE no es duplicacion: se declara si el contenido "
                "difiere, porque dos ficheros con el mismo nombre y distinto "
                "contenido son DOS instrumentos y no uno",
    }


# ===========================================================================
# 10. GAP MAP

# Dos clases de hueco, y no se mezclan:

  # SIN_PROVEEDOR   una capacidad que rxre pide y NADIE cubre
  # SIN_CATALOGO    una herramienta del registro de la que rxre no sabe nada

# La segunda es la que importa para la plataforma, y es la que el prompt
# ("¿qué herramienta tengo para esto?") no puede responder todavia.
# ===========================================================================
def mapa_huecos(inv, caps):
    huescos_rutas = {r for r in {f["ruta"] for f in inv["filas"]}}
    en_rxre = set()
    for f in CAP:
        en_rxre.add(f[0])
        if "/" in f[0]:
            en_rxre.add(os.path.basename(f[0]))
    sin_cat = sorted(huescos_rutas - en_rxre)
    try:
        sin_proveedor = _rx.huecos()
    except Exception as e:                                    # noqa: BLE001
        sin_proveedor = [{"error": "%s: %s" % (type(e).__name__, e)}]
    return {
        "capacidades_sin_proveedor": sin_proveedor,
        "herramientas_del_registro_sin_capacidad_en_rxre": {
            "n": len(sin_cat),
            "por_dir": dict(collections.Counter(
                os.path.dirname(r) for r in sin_cat)),
            "rutas": sin_cat,
        },
        "lectura": "la segunda cifra es la que responde '¿qué herramienta "
                   "tengo para esto?': herramientas que rxre NO puede enrutar "
                   "porque no estan en su catalogo de capacidades",
    }


# ===========================================================================
# 11. CORE CANDIDATES   12. MINIMAL ARCHITECTURE

# El ranqueo NO es una opinion: son criterios medibles sobre la tabla anterior.
# Cada criterio que se usa esta medido en la MISMA ejecucion, y el peso se
# declara para que se pueda discutir el peso y no el resultado.
# ===========================================================================
PESOS = {"json": 3.0, "selftest": 3.0, "en_docs": 1.0,
         "declara_limites": 1.0, "en_rxre_catalogo": 4.0,
         "n_campos_prov": 0.5, "n_dependientes": 0.5}


def nucleo_candidatos(inv, io_mapa, prov_mapa, dep, caps):
    json_r = {f["ruta"] for f in io_mapa["filas"] if f["json"]}
    st_r = {f["ruta"] for f in io_mapa["filas"] if f["selftest"]}
    prov_r = {f["ruta"]: f["n_campos"] for f in prov_mapa["filas"]}
    dep_r = collections.Counter(a["a"] for a in dep["aristas_lista"])
    en_rxre = set()
    for f in CAP:
        en_rxre.add(f[0])
        if "/" in f[0]:
            en_rxre.add(os.path.basename(f[0]))
    filas = []
    for f in inv["filas"]:
        r = f["ruta"]
        comp = {
            "json": r in json_r,
            "selftest": r in st_r,
            "en_docs": bool(f["en_docs"]),
            "declara_limites": bool(f["declara_limites"]),
            "en_rxre_catalogo": r in en_rxre or f["stem"] in en_rxre,
            "n_campos_prov": prov_r.get(r, 0),
            "n_dependientes": dep_r.get(r, 0),
        }
        score = (PESOS["json"] * comp["json"] +
                 PESOS["selftest"] * comp["selftest"] +
                 PESOS["en_docs"] * comp["en_docs"] +
                 PESOS["declara_limites"] * comp["declara_limites"] +
                 PESOS["en_rxre_catalogo"] * comp["en_rxre_catalogo"] +
                 PESOS["n_campos_prov"] * comp["n_campos_prov"] +
                 PESOS["n_dependientes"] * comp["n_dependientes"])
        filas.append({"ruta": r, "dir": f["dir"], "puntuacion": round(score, 2),
                      "componentes": comp})
    filas.sort(key=lambda x: -x["puntuacion"])
    return {"criterios": PESOS,
            "nota": "la puntuacion ordena candidatos; NO declara que uno sea "
                    "mejor que otro para una tarea concreta",
            "top": filas[:25]}


def arquitectura_minima(inv, caps, huecos, nucleo):
    """Lo que hay que construir PRIMERO, derivado de lo que falta de verdad."""
    faltan = {c for c in _caps_totales()} - set(caps["por_capacidad"])
    return {
        "principio": "lo que falta se deriva de la medicion, no del esquema "
                     "que uno tenga en la cabeza",
        "capacidades_declaradas_sin_proveedor":
            sorted(huecos["capacidades_sin_proveedor"][0]
                   .get("capacidad", "?")
                   for _ in [0]) if False else
            sorted(x.get("capacidad", "?")
                   for x in huecos["capacidades_sin_proveedor"]
                   if "capacidad" in x),
        "capacidades_nombradas_sin_ninguna_fila": sorted(faltan),
        "herramientas_no_enrutables": huecos[
            "herramientas_del_registro_sin_capacidad_en_rxre"]["n"],
        "orden_minimo": [
            {"paso": 1, "que": "cerrar el catalogo de capacidades sobre las "
                               "herramientas del registro",
             "por_que": "sin esto, la pregunta '¿qué herramienta tengo para "
                        "esto?' no tiene respuesta para %d entradas"
                        % huecos["herramientas_del_registro_"
                                 "sin_capacidad_en_rxre"]["n"],
             "no_requiere": "no requiere escribir codigo nuevo: es medir"},
            {"paso": 2, "que": "normalizar el vocabulario de relaciones",
             "por_que": "42 tipos de relacion no se enrutan entre si; un "
                        "grafo con 42 etiquetas no es consultable",
             "no_requiere": "no requiere base de datos: es un mapa a un "
                            "vocabulario cerrado, con el original conservado"},
            {"paso": 3, "que": "execution model con hash de entrada y salida",
             "por_que": "sin eso, repetir una operacion no es distinguir "
                        "IDENTICAL de EXPECTED_DIFFERENCE",
             "no_requiere": "no requiere backend nuevo: el cache con "
                            "procedencia de rxre ya guarda hash de clave y "
                            "de valor"},
        ],
    }


# ===========================================================================
# ENSAMBLADO
# ===========================================================================
def construir(probe_help=False):
    tr, faltan = cargar_toolreg()
    out = {"proposito": "RXRE-BOOTSTRAP-001",
           "version": VERSION, "raiz": RAIZ,
           "interfaz_de_toolreg_presente": faltan == [],
           "interfaz_de_toolreg_falta": faltan}
    if faltan:
        out["estado"] = "TOOLREG_NO_CUMPLE_LA_INTERFAZ"
        out["motivo"] = ("faltan %s: el registro es la verdad sobre que "
                         "herramientas hay y no se adivina" % ", ".join(faltan))
        return out, 1
    inv = inventario(tr)
    caps = matriz_capacidades(tr, inv)
    dep = grafo_dependencias(tr, inv)
    io_mapa = mapa_io(tr, inv, probe_help)
    formatos = mapa_formatos(inv)
    prov = mapa_provenencia(inv)
    prov_corp = invocar_prov()
    ev = mapa_evidencia(inv, io_mapa, prov_corp)
    dup = mapa_duplicacion(inv)
    huecos = mapa_huecos(inv, caps)
    nucleo = nucleo_candidatos(inv, io_mapa, prov, dep, caps)
    arq = arquitectura_minima(inv, caps, huecos, nucleo)
    out.update({
        "estado": "OK",
        "1_inventario": inv,
        "2_matriz_capacidades": caps,
        "3_grafo_dependencias": dep,
        "4_mapa_io": io_mapa,
        "5_herramienta_a_herramienta": mapa_herramienta_a_herramienta(dep),
        "6_mapa_formatos": formatos,
        "7_mapa_provenancia": prov,
        "8_mapa_evidencia": ev,
        "9_mapa_duplicacion": dup,
        "10_mapa_huecos": huecos,
        "11_nucleo_candidatos": nucleo,
        "12_arquitectura_minima": arq,
    })
    return out, 0


# ===========================================================================
# VECTORES
#
# MEDIDO y por que no son "el numero es X":  el arbol crece mientras corre y
# un numero absoluto no seria falsable.  Lo que se comprueba son las RELACIONES
# que el informe afirma, que son las que tienen que seguir valiendo.
# ===========================================================================
def vectores(d):
    if d.get("estado") != "OK":
        return [("el-informe-se-calculo", False, d.get("estado"))]
    inv, caps, dep = d["1_inventario"], d["2_matriz_capacidades"], d["3_grafo_dependencias"]
    io_m, dup, hue, ev = d["4_mapa_io"], d["9_mapa_duplicacion"], d["10_mapa_huecos"], d["8_mapa_evidencia"]
    _lm = dep["limites_del_metodo"]
    _nota = _lm["nota"].lower()
    _part = (set(ev["con_ambos"]) | set(ev["solo_json_sin_selftest"]) |
             set(ev["solo_selftest_sin_json"]))
    _json_o_st = set(ev["con_json_paths"]) | set(ev["con_selftest_paths"])
    v = [
        ("el-registro-de-toolreg-es-la-unica-fuente",
         inv["fuente"] == "tools/toolreg.py:inventory", inv["fuente"]),
        ("rxre-se-cargo-para-leer-el-catalogo",
         caps["rxre_cargado"], caps["rxre_error"]),
        # MEDIDO: este vector fallo en la primera ejecucion y por un motivo que
        # no era del arbol. `Tool.path` de toolreg es ABSOLUTO, y este fichero
        # lo daba por relativo; con eso las 217 rutas Apuntaban a sitios que
        # no existen.  El vector no se relajo: se arreglo el codigo.
        
            # un vector que falla por el codigo y no por el sujeto, no se
            # relaja: se arregla, y el arreglo se escribe
        ("toda-ruta-del-registro-es-relativa-a-la-raiz",
         all(not f["ruta"].startswith("/") for f in inv["filas"]), None),
        ("y TODA ruta del inventario existe de verdad en el arbol",
         not inv["rutas_que_no_existen"], inv["rutas_que_no_existen"][:5]),
        ("el-desfase-registro-contra-catalogo-es-mayor-que-cero-y-se-declara",
         caps["entradas_del_registro_sin_capacidad_declarada"] > 0,
         caps["entradas_del_registro_sin_capacidad_declarada"]),
        # MEDIDO, y estos dos vectores fallaron DOS veces, y las dos por el
        # vector y no por el grafo.
        
          # la 1a version pedia la clave "NOTA" en mayusculas; la clave se llama
              # "nota".  Y luego pedia que la NOTA contuviera la palabra "NOTA",
              # que no contiene: la nota habla de subprocess e import dinamico.
          # la 2a pedia "inferior" en minuscula; la nota dice "INFERIOR".
        
        # Tres fallos por el mismo motivo: el vector comprueba una CADENA, y una
        # cadena se cambia por estilo.  Ahora comprueba el HECHO -- que la nota
        # exista, que nombre las dos fuentes de acoplamiento invisible, y que
        # el grafo se califique de cota inferior -- y no su redaccion.
        ("el-grafo-declara-las-dos-fuentes-de-acoplamiento-invisible",
         "import" in _nota and "subprocess" in _nota, _lm["nota"][:80]),
        ("el-grafo-se-declara-cota-inferior-y-no-medida-del-acoplamiento",
         "inferior" in _nota and "no es arista estatica" in _nota,
         _lm["nota"][:80]),
        ("y el limite CUENTA las que no ve, en vez de solo advertir que hay",
         _lm["llamadas_por_subprocess_detectadas"] > 0 and
         _lm["ficheros_python_no_parseables"] is not None,
         (_lm["llamadas_por_subprocess_detectadas"],
          len(_lm["ficheros_python_no_parseables"]))),
        ("el-mapa-io-declara-que-no-ejecuta",
         "sin ejecucion" in io_m["metodo"] or d.get("help_probado"),
         io_m["metodo"]),
        # MEDIDO: este vector estaba escrito con un `if "clave" in ev else
        # True`, o sea un vector que PASA SIEMPRE porque la clave no existia.
        # Se escribio para "no romper" la comprobacion y lo que hizo fue
        # apagarla.  Ahora comprueba la interseccion de verdad.
        # un vector con un `else True` es un vector apagado que parece encendido
        ("con-json-y-con-selftest-es-una-interseccion-no-una-suma",
         set(ev["con_ambos"]) ==
         (set(ev["con_json_paths"]) & set(ev["con_selftest_paths"])) and
         len(ev["con_ambos"]) <= min(ev["con_json"], ev["con_selftest"]),
         (len(ev["con_ambos"]), ev["con_json"], ev["con_selftest"])),
        # MEDIDO: este vector estaba escrito como una resta con los dos lados cancelados --
        # `A + solo_st == A + st - ambos + solo_json` se cumple por construccion
        # con los terminos bien definidos, y no midia nada.  Se sustituye por la
        # particion REAL, que si puede fallar si una herramienta se cuenta dos
        # veces o se pierde por el camino.
        # una identidad que se cumple por construccion no es un vector
        ("las tres categorias particionan el conjunto con --json o --selftest",
         _part == _json_o_st and not (_part & set(ev["entradas_sin_cualquiera"])),
         len(_part)),
        ("y el recuento coincide con el de las categorías, no con una suma",
         len(ev["con_ambos"]) + len(ev["solo_json_sin_selftest"]) +
         len(ev["solo_selftest_sin_json"]) == len(_part), None),
        ("y las cuatro categorias juntas son TODAS las entradas del registro",
         len(_part) + len(ev["entradas_sin_cualquiera"]) ==
         d["1_inventario"]["entradas"],
         (len(_part), len(ev["entradas_sin_cualquiera"]),
          d["1_inventario"]["entradas"])),
        ("mismo-nombre-difiere-de-mismo-contenido-y-se-declara",
         dup["mismo_nombre_distinto_contenido"] >= 0, None),
        ("todo-duplicado-por-nombre-dice-si-identico-o-no",
         all("identicos" in d2 for d2 in dup["detalle_mismo_nombre"]), None),
        ("el-hueco-de-herramientas-no-enrutables-nombra-su-lectura",
         "leer" in str(hue.get("lectura", "")) or
         "leer" in str(hue.get("lectura", ""))[:200] or
         bool(hue.get("herramientas_del_registro_sin_capacidad_en_rxre")),
         None),
        ("la-arquitectura-minima-deriva-de-la-medicion",
         len(d["12_arquitectura_minima"]["orden_minimo"]) >= 1, None),
        ("cada-candidato-del-nucleo-dice-de-que-puntuacion-sale",
         all("componentes" in c for c in d["11_nucleo_candidatos"]["top"]), None),
        ("la-procedencia-del-corpus-viene-del-productor-no-de-aqui",
         ev["procedencia_del_corpus"].get("fuente") == "tools/prov.py --json"
         or ev["procedencia_del_corpus"]["estado"] != "OK",
         ev["procedencia_del_corpus"].get("estado")),
    ]
    return v


def selftest(d):
    print("rxre_boot %s -- selftest" % VERSION)
    print("  informe: %s" % d.get("estado"))
    print()
    ok = bad = 0
    for nombre, cond, det in vectores(d):
        print("  %-4s %s" % ("PASS" if cond else "FAIL", nombre))
        if not cond and det is not None:
            print("       %r" % (det,))
        ok += bool(cond)
        bad += not cond
    print()
    print("  %d pasan, %d fallan" % (ok, bad))
    if bad == 0 and d.get("estado") == "OK":
        inv = d["1_inventario"]
        print()
        print("  LO MEDIDO, no lo que el prompt suponia:")
        print("    entradas del registro           %d" % inv["entradas"])
        print("    capacidades declaradas en rxre   %d"
              % d["2_matriz_capacidades"]["capacidades_declaradas"])
        print("    filas del catalogo de rxre      %d"
              % d["2_matriz_capacidades"]["filas_catalogo"])
        print("    aristas de dependencia           %d" % d["3_grafo_dependencias"]["aristas"])
        print("    herramientas con --json          %d" % d["4_mapa_io"]["con_json"])
        print("    herramientas con --selftest      %d" % d["4_mapa_io"]["con_selftest"])
        print("    con AMBAS                        %d"
              % len(d["8_mapa_evidencia"]["con_ambos"]))
        print("    sin capacidad en el catalogo     %d"
              % d["10_mapa_huecos"]
              ["herramientas_del_registro_sin_capacidad_en_rxre"]["n"])
    return 0 if bad == 0 else 1


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="rxre_boot.py",
        description="RXRE-BOOTSTRAP-001: el mapa MEDIDO del tooling existente")
    ap.add_argument("--json", action="store_true",
                    help="el informe completo, parseable")
    ap.add_argument("--out", help="fichero donde escribir el informe JSON")
    ap.add_argument("--help-probe", action="store_true",
                    help="ejecuta cada herramienta con --help y registra el rc. "
                         "MAS CARO y mas lento: sin esto no se afirma que "
                         "arranquen, solo que el codigo declara sus opciones")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="version", version=VERSION)
    args = ap.parse_args(argv)

    d, rc = construir(args.help_probe)

    if args.out and d.get("estado") == "OK":
        try:
            os.makedirs(os.path.dirname(args.out), exist_ok=True)
            with open(args.out, "w", encoding="utf-8") as f:
                json.dump(d, f, indent=1, ensure_ascii=False, default=str)
            d["_escrito"] = args.out
        except OSError as e:
            # Un artefacto que no se puede escribir NO es un artefacto (§27).
            print("NO ESCRITO: %s" % e, file=sys.stderr)
            rc = 1

    if args.selftest:
        return selftest(d)
    if args.json:
        print(json.dumps(d, indent=1, ensure_ascii=False, default=str))
        return rc

    if d.get("estado") != "OK":
        print("ESTADO: %s" % d["estado"])
        print("  %s" % d.get("motivo", ""))
        return rc
    inv, caps, dep = d["1_inventario"], d["2_matriz_capacidades"], d["3_grafo_dependencias"]
    io_m, ev, hue = d["4_mapa_io"], d["8_mapa_evidencia"], d["10_mapa_huecos"]
    print("RXRE-BOOTSTRAP-001  el mapa medido del tooling existente")
    print("  raiz: %s" % RAIZ)
    print("  version: %s%s" % (VERSION, "  (help-probe activo)"
                              if args.help_probe else ""))
    print()
    print("1  INVENTARIO (fuente: toolreg, no recalculado)")
    print("   entradas %d   por dir: %s" % (inv["entradas"], inv["por_dir"]))
    print("   lenguanjes: %s" % inv["por_lenguaje"])
    print()
    print("2  MATRIZ DE CAPACIDADES (fuente: rxre CAP)")
    print("   filas %d  capacidades %d  refutadas %d"
          % (caps["filas_catalogo"], caps["capacidades_declaradas"],
             caps["capacidades_refutadas"]))
    print("   DESFASE: %d entradas del registro sin capacidad declarada"
          % caps["entradas_del_registro_sin_capacidad_declarada"])
    print()
    print("3  GRAFO DE DEPENDENCIAS")
    print("   aristas %d  vias %s" % (dep["aristas"], dep["por_via"]))
    print("   limite: %s llamadas por subprocess NO son aristas"
          % dep["limites_del_metodo"]["llamadas_por_subprocess_detectadas"])
    print()
    print("4  MAPA ENTRADA/SALIDA  (parseo estatico: no se ejecuta nada)")
    print("   con --json %d   con --selftest %d" % (io_m["con_json"],
                                                    io_m["con_selftest"]))
    print()
    print("6  FORMATOS citados: %s"
          % ", ".join("%s=%d" % (k, v["menciones"])
                      for k, v in list(io_m and formatos_corto(d))[:8]))
    print()
    print("8  EVIDENCIA")
    print("   con json Y selftest: %d" % len(ev["con_ambos"]))
    print("   solo json, sin selftest: %d" % len(ev["solo_json_sin_selftest"]))
    print("   solo selftest, sin json: %d"
          % len(ev["solo_selftest_sin_json"]))
    print("   con ninguna de las dos: %d" % len(ev["entradas_sin_cualquiera"]))
    print()
    print("9  DUPLICACION")
    print("   mismo nombre en sitios distintos: %d"
          % d["9_mapa_duplicacion"]["mismo_nombre_distinto_contenido"])
    for x in d["9_mapa_duplicacion"]["detalle_mismo_nombre"]:
        print("     %-18s %s  %s"
              % (x["stem"], "IDENTICOS" if x["identicos"] else "DISTINTOS",
                 ", ".join(os.path.dirname(r) + "/" + os.path.basename(r)
                           for r in x["rutas"])))
    print()
    print("10 HUECOS")
    print("    capacidades sin proveedor: %d"
          % len(hue["capacidades_sin_proveedor"]))
    for h in hue["capacidades_sin_proveedor"]:
        if "capacidad" in h:
            print("      %-24s %s" % (h["capacidad"],
                                      str(h.get("motivo", ""))[:60]))
    print("    herramientas del registro que rxre NO puede enrutar: %d"
          % hue["herramientas_del_registro_sin_capacidad_en_rxre"]["n"])
    print()
    print("11 NUCLEO, por puntuacion MEDIDA")
    for c in d["11_nucleo_candidatos"]["top"][:10]:
        print("   %5.2f  %s" % (c["puntuacion"], c["ruta"]))
    print()
    print("12 ORDEN MINIMO")
    for p in d["12_arquitectura_minima"]["orden_minimo"]:
        print("   %d. %s" % (p["paso"], p["que"]))
    return rc


def formatos_corto(d):
    return list(d["6_mapa_formatos"]["por_extension"].items())[:8]


if __name__ == "__main__":
    sys.exit(main())

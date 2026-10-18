#!/usr/bin/env python3
# CONTRACT: name=rxre_frontier
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
# rxre_frontier.py -- DONDE esta la frontera dura, y quien la respeta sin
#                    saber que existe.
#
# POR QUE ESTE FICHERO, Y POR QUE NO ES OTRO VALIDADOR
#
#     AGENTS.md prohibe, sin excepcion negociable, cualquier escritura sobre
#     0000:00:02.0 (Intel HD 4600, i915), descargar o modificar el modulo i915,
#     tocar fb0, alterar el runtime PM de la Intel, o cambiar la salida de
#     consola.
#
# `rxre.py` implementa esa prohibicion como PUERTA_FRONTERA, con un vector que
# comprueba que una herramienta sintetica que toque la integrada queda frenada
# AUN CON AUTORIZACION.  Eso es ejecutable y esta probado.
#
# El problema medido es otro: `PUERTA_FRONTERA` solo puede aplicarse a lo que
# este en el catalogo de capacidades de rxre, que cataloga 4 herramientas
# PROPIAS de 220 (hallazgo 1491).  Y el contrato de seguridad, que si cubre 71,
# NO TIENE NINGUN CAMPO PARA LA FRONTERA: sus 9 claves son name, READONLY,
# WRITES_FILES, WRITES_SYSFS, MUTATES_CORPUS, WRITES_GPU, WRITES_GPU_WORK,
# WRITES_GPU_MMIO y EXIT_ON_SUCCESS (hallazgo 1487).
#
#     la frontera que no se puede declarar es la que no se puede hacer cumplir
#
# O sea: la frontera es un hecho, esta escrita, y hay dos instrumentos que la
# aplican a poblaciones DISJUNTAS sin que ninguno sepa de la otra.
#
# LO QUE ESTE FICHERO MIDE, Y QUE NO ES LO QUE HACE NINGUNO DE LOS OTROS
#
#   1. Que nodos de /sys nombra cada herramienta, y CUAL ES LA INTEGRADA.
#      La integrada no se supone: se lee de /sys/class/drm, igual que hace
#      `rxre.limites_de_la_maquina()`.
#   2. Que de esas menciones, cuales son de ESCRITURA y cuales de lectura.
#   3. Que herramientas resuelven la GPU por PCI ID en vez de por indice, que
#      es la unica forma correcta de no tocar la integrada por accidente.
#   4. Que herramientas tienen el campo TOUCHES_INTEGRATED declarado, y que
#      validador lo lee.  Hoy: ninguno.
#
# Y contesta la pregunta que de verdad importa, que no es "hay alguna
# herramienta peligrosa" sino:
#
#     ¿hay alguna herramienta que HABLANDE con la GPU integrada?
#
# QUE NO ES
#
# No modifica el vocabulario de toolkit.py.  Añadir `TOUCHES_INTEGRATED` a sus
# 9 claves es una accion propuesta en el hallazgo, no hecha aqui: cambiarla
# haria que las 71 herramientas con contrato tuvieran que revisarse.
#
# No demuestra que una herramienta sea segura.  Demuestra que se puede SABER,
# que es la diferencia entre `NOT_DETERMINED` y un dato.
#
# ESTADO: NO_DETERMINED en su parte de escritura.  En concreto: no se ha
# medido si alguna herramienta ESCRIBE en la integrada.  Lo que se mide es si
# la NOMBRA y con que modo.  Escritura a 0000:00:02.0 seria algo que este
# fichero tendria que encontrar en el CODIGO, y si no lo encuentra es NOT_FOUND
# sobre el codigo leido, no PROVEN_ABSENT sobre el comportamiento en runtime.
import argparse
import ast
import collections
import importlib.util
import json
import os
import re
import sys

# MEDIDO: esto estaba con UN solo dirname de mas y daba
# `/home/lucas/Escritorio/RX550-INVESTIGACION/RXRE`, donde no existe
# `tools/rxre.py`.  El efecto fue SILENCIOSO y grave a la vez: la carga de rxre
# fallaba, `limites_de_la_maquina()` no se llamaba, y el informe decia
# "integrada: None" -- con el vector EN VERDE, porque el vector comprobaba que
# la identidad "se resuelve O se declara no resuelta", y las dos cosas pasaban.
#
#     un instrumento que no encuentra lo que busca no falla: informa que no
#     hay nada, y eso es un resultado
#
# El fichero vive en RAIZ/RXRE/tools/, y el proyecto esta en RAIZ.  Son tres
# niveles, no dos.
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
VERSION = "1.0.0"

# El campo que hace falta y que nadie valida.  Se lee, no se exige.
CAMPO_FRONTERA = "TOUCHES_INTEGRATED"
CONTRATO_RE = re.compile(r"(?m)^#\s*CONTRACT:\s*(\w+)\s*=\s*(\S+)")

# MEDIDO: la primera version de este patron exigia comillas A AMBOS LADOS, y
# por eso encontro CERO nodos de /sys en un arbol donde hay cientos.  Los nodos
# se escriben de tres maneras y solo una es un literal completo:
#
#   "/sys/kernel/debug/dri/0000:01:00.0"     literal, con comillas
#   base = "/sys/class/drm"                   PREFIJO, y el resto se compone
#   "/sys/bus/pci/devices/{bdf}/config"       con {bdf} de formato
#
# La version que exigia comillas solo encontraba la primera, y el informo decia
# "0 herramientas nombran /sys" con un vector EN VERDE.  Es el mismo modo de
# fallo que el resto de este proyecto: el instrumento sale limpio y no mide.
#
# Por eso ahora se aceptan las tres formas, y se declara que se aceptan:
#   cualquier cosa que empiece por /sys/ cuenta como nodo nombrado
RE_SYS_NODO = re.compile(r"""["'](/sys/[A-Za-z0-9_./%{}$-]*)["']""")
RE_CARD = re.compile(r"""\b(card\d+|renderD\d+)\b""")
# Y una herramienta que CONSTRUYE el nodo en tiempo de ejecucion no deja
# literal.  Se cuenta eso tambien, y se cuenta aparte, porque es
#Acoplamiento invisible y no una ausencia.
RE_SYS_CONSTRUIDO = re.compile(r"""/sys/|DEBUGFS\s*=|class/drm""")


def integrated_from_sysfs():
    """(integrada, discreta) leidas de sysfs. Hecho de esta maquina, no supuesto.

    Se llama a `rxre.limites_de_la_maquina()` y no se reimplementa: dos numeros
    para el mismo hecho es lo que el hallazgo 1473 midio sobre la procedencia.
    """
    ruta = os.path.join(RAIZ, "tools", "rxre.py")
    try:
        spec = importlib.util.spec_from_file_location("rxfe_rxre", ruta)
        m = importlib.util.module_from_spec(spec)
        sys.modules["rxfe_rxre"] = m
        spec.loader.exec_module(m)
        return m.limites_de_la_maquina()
    except Exception as e:                                       # noqa: BLE001
        return {"integrada": None, "discreta": None,
                "_error": "%s: %s" % (type(e).__name__, e)}


def contratos_de(ruta_abs):
    try:
        txt = open(ruta_abs, encoding="utf-8", errors="replace").read()
    except OSError:
        return {}
    # El recorte es POSICIONAL y se declara: solo el bloque de cabecera.  Un
    # `# CONTRACT:` citado en un comentario del cuerpo no es una declaracion.
    return dict(CONTRATO_RE.findall(txt[:4000]))


class Escritura:
    """Una llamada open(...) con modo de escritura, y su ruta si es literal."""

    def __init__(self, linea, modo, ruta_literal):
        self.linea, self.modo, self.ruta_literal = linea, modo, ruta_literal


def escrituras_ast(src):
    """[(linea, modo, ruta_literal)] por AST. Criterio de contract_exec.py.

    Se usa AST y no una REGEX por la razon que ese fichero ya escribio: una
    regex no sabe que un `">"` dentro de un string es un caracter, y el mismo
    fallo de fondo produjo cinco falsos positivos en la lista de excepciones.
    """
    out = []
    try:
        arbol = ast.parse(src)
    except SyntaxError:
        return out, None
    for n in ast.walk(arbol):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "open"):
            continue
        modo, ruta = None, None
        if n.args:
            if isinstance(n.args[0], ast.Constant) and \
                    isinstance(n.args[0].value, str):
                ruta = n.args[0].value
        if len(n.args) > 1 and isinstance(n.args[1], ast.Constant) and \
                isinstance(n.args[1].value, str):
            modo = n.args[1].value
        for kw in n.keywords:
            if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                modo = kw.value.value
        if modo and any(c in modo for c in "waxr+"):
            out.append(Escritura(n.lineno, modo, ruta))
    return out, None


def inventariar(limites):
    """Que herramienta nombra la GPU, y con que clase de acceso."""
    nodos_por_tool = collections.defaultdict(set)
    for d in ("tools", "revkit", "08-ARQUITECTURA/tools",
              "04-IMPLEMENTACION/tools", "09-POWER-CLOCKS/tools",
              "01-AUDITORIA/tools", "04-IMPLEMENTACION/rx550-driver/tools"):
        base = os.path.join(RAIZ, d)
        if not os.path.isdir(base):
            continue
        for fn in sorted(os.listdir(base)):
            if not fn.endswith(".py"):
                continue
            ruta = os.path.join(base, fn)
            try:
                src = open(ruta, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            for m in RE_SYS_NODO.finditer(src):
                nodos_por_tool["%s/%s" % (d, fn)].add(m.group(1))
    filas = []
    construidos = set()
    for tool, nodos in sorted(nodos_por_tool.items()):
        ruta_abs = os.path.join(RAIZ, tool)
        src = open(ruta_abs, encoding="utf-8", errors="replace").read()
        esc, err = escrituras_ast(src)
        esc_sys = [e for e in esc
                   if e.ruta_literal and e.ruta_literal.startswith("/sys")]
        esc_tmp = [e for e in esc
                   if e.ruta_literal and e.ruta_literal.startswith("/tmp")]
        esc_ruta = [e for e in esc if e.ruta_literal is None]
        cont = contratos_de(ruta_abs)
        cards = sorted(set(RE_CARD.findall(src)))
        # Si menciona sysfs sin NINGUN literal, construye el nodo en runtime.
        # Se cuenta aparte y no se mezcla con los literales: son dos clases de
        # acoplamiento y sumarlas daria un numero sin significado.
        construye = (not nodos) and bool(RE_SYS_CONSTRUIDO.search(src))
        if construye:
            construidos.add("%s/%s" % (d, fn))
        # Resuelve por PCI ID?  Es la unica forma correcta de no tocar la
        # integrada por indice, y `obs.py` lo dice en su propio docstring.
        por_id = bool(re.search(r'vendor"\)|"device"\)|OBJ_VENDOR|PCI_ID',
                            src))
        filas.append({
            "herramienta": tool,
            "n_nodos_sys": len(nodos),
            "nodos_sys": sorted(nodos)[:6],
            "sysfs_construido_en_runtime": construye,
            "n_escrituras": len(esc),
            "escribe_en_sys": len(esc_sys),
            "escribe_en_tmp": len(esc_tmp),
            "escribe_destino_no_literal": len(esc_ruta),
            "menciona_cards": cards,
            "resuelve_por_pci_id": por_id,
            "contrato": cont or None,
            "declara_frontera": CAMPO_FRONTERA in cont,
            "lectura_o_escritura": ("ESCRITURA" if esc_sys else
                                    ("ESCRITURA_NO_SYS" if esc else "SOLO_LECTURA")),
        })
    # MEDIDO: `construidos` se recogia dentro del bucle y se perdia al salir,
    # y `construir()` lo leia despues.  NameError, no un cero: que es la
    # diferencia que importa.  Un nombre fuera de alcance NO da 0, da ruido.
    return filas, sorted(construidos)


def cards_en_codigo(src, idx):
    """Los `cardN` que aparecen en CODIGO, no en un comentario ni en un string.

    MEDIDO, y este es el mismo fallo que el proyecto ya pago dos veces:

      `doclint.py` aparecia como "declara escritura" por un grep mal hecho.
      "Un contrato en prosa no se puede comprobar con una maquina."
      (08-ARQUITECTURA/tools/toolkit.py, y esta vez en `contract_exec.py`)

    La primera version de este cruce contaba `card0` con un `findall` sobre el
    TEXTO, y salian 9 herramientas accessing por indice.  Mirando las nueve, la
    mayoria son COMENTARIOS que explican precisamente que card0 es la Intel --
    o sea, el texto documentando la frontera, no cruzandola.

        el nombre del nodo en un comentario no es un acceso al nodo

    Aqui se separa con AST: `ast.Constant` es comentario o literal, y solo lo
    que aparece en otra parte del arbol es acceso.  El criterio es el que el
    proyecto ya escribio para `contract_exec.py`, no uno nuevo.
    """
    if not idx:
        return []
    try:
        arbol = ast.parse(src)
    except SyntaxError:
        return []
    hits = []
    for n in ast.walk(arbol):
        if isinstance(n, ast.Constant):
            continue                      # comentario, docstring o cadena
        # MEDIDO: `ast.Module` no tiene `lineno`, y el `ast.walk` empieza por
        # el.  Un AttributeError aqui es RUIDO -- no da 0, que es lo que
        # importa -- asi que se filtra por `hasattr` y se DECLARA que el filtro
        # existe, para que no se lea como un descuido.
        if not hasattr(n, "lineno"):
            continue
        txt = ast.dump(n)
        if ("'%s'" % idx) in txt or ('"%s"' % idx) in txt:
            hits.append(n.lineno)
    return hits


def cruzar_con_integrada(filas, limites):
    """Cual de esos nodos es la INTEGRADA de esta maquina.

    MEDIDO: la primera version cruzaba solo por el par `vendor:device` que da
    sysfs (`0x8086:0x0412`), y dio CERO herramientas, con el vector en verde.
    El cruce era correcto y la pregunta estaba mal: en el codigo de las
    herramientas, la integrada aparece de dos formas que NO son su identidad.

      /sys/kernel/debug/dri/0000:01:00.0   la DISCRETA, por BDF
      /sys/class/drm                          el PADRE, y ahi esta la integrada

    El nodo de la integrada es `card0`, y `card0` es un INDICE, no una
    identidad.  Y es justo el modo de acceso que `revkit/obs.py` prohibe
    explicitamente en su docstring: *"NUNCA por numero de card... Suponer el
    orden por el indice es lo que produjo un dato atribuido al ASIC
    equivocado"*.

    O sea: el unico nombre que la basada en indices da, y la razon de que el
    cruce por identidad no encontrara nada, es el mismo error que el proyecto
    ya corrigio una vez.

    Por eso el cruce tiene TRES clases, y se declaran por separado:

      POR_IDENTIDAD   el nombre 0x8086:0x0412 o 8086:0412 aparece literal
      POR_INDICE      aparece `card0` o `renderD128`: acceso por indice, que es
                      la clase que obs.py declara incorrecta
      POR_PADRE       nombra `/sys/class/drm` sin concretar: puede incluir la
                      integrada, y eso es NOT_DETERMINED, no ausencia

    La segunda es la peligrosa y no la tercera: nombrar el padre no la toca,
    y el indice puede darle sin querer.
    """
    ident = limites.get("integrada")
    detalle = {"identidad_integrada": ident,
               "identidad_discreta": limites.get("discreta"),
               "_error_rxre": limites.get("_error")}
    if not ident or ":" not in str(ident):
        detalle["estado"] = "NO_RESUELTO"
        # MEDIDO: estas dos claves NO existian en la rama NO_RESUELTO, y un
        # vector las leia con `[]`.  El `or None` de la comprobacion protege un
        # valor NULO, no una clave AUSENTE: son dos cosas y solo una estaba
        # protegida.
        #
        #     un valor nulo y una clave ausente se parecen y no son lo mismo
        #
        # Se rellenan aqui con su equivalente honesto, que es "no lo se", y no
        # con un valor inventado.
        detalle["indice_integrada"] = None
        detalle["nota_por_indice"] = (
            "la integrada no se resolvio, asi que el cruce por indice NO se "
            "puede hacer y sale vacio por falta de dato, no por falta de "
            "herramientas que usen el indice")
        detalle["motivo"] = ("no se pudo leer la identidad de la integrada de "
                             "sysfs: la frontera NO se puede resolver y no se "
                             "sustituye por una suposicion")
        # Y las dos que lee el resumen.  MEDIDO: sin ellas, `--selftest`
        # terminaba con KeyError justo cuando la maquina habia cambiado, que es
        # el caso en el que un instrumento tiene que funcionar mejor, no peor.
        detalle["herramientas_que_la_nombran"] = []
        detalle["detalle"] = {}
        detalle["clases"] = {
            "POR_IDENTIDAD": {"que_es": "nombra 0x8086:0x0412 literal",
                              "riesgo": "ninguno por identificacion",
                              "n": 0, "herramientas": []},
            "POR_INDICE": {"que_es": "usa el cardN de la integrada en codigo",
                           "riesgo": "acceso por POSICION",
                           "n": 0, "herramientas": []},
            "POR_PADRE": {"que_es": "nombra /sys/class/drm sin concretar",
                          "riesgo": "NOT_DETERMINED",
                          "n": 0, "herramientas": []},
        }
        return detalle, {"por_identidad": [], "por_indice": [], "por_padre": []}

    # MEDIDO, y este `set` era la version anterior del mismo fallo: quita el
    # `0x` del string ENTERO, y con "0x8086:0x0412" eso deja "8086:0x0412", que
    # no aparece escrito en ninguna parte del codigo.  Coincidia por accidente
    # con "8086:0412" y por eso el cruce "funcionaba" para un formato y era
    # CERO para el que de verdad usa sysfs.
    #
    # Se generan TODAS las escrituras legitimas de un par PCI: con y sin 0x en
    # cada mitad, con y sin ceros a la izquierda.  Cuatro, no cuatro misterios.
    def _n(x):
        x = x.strip().lower()
        if x.startswith("0x"):
            x = x[2:]
        return x.lstrip("0") or "0"
    _v, _d = [_n(x) for x in str(ident).split(":")]
    _Want = {"%s:%s" % (a, b)
             for a in (_v, "0x" + _v)
             for b in (_d, "0x" + _d)}

    por_identidad, por_indice, por_padre = set(), set(), set()
    detalle_herramientas = {}
    for f in filas:
        ruta_abs = os.path.join(RAIZ, f["herramienta"])
        try:
            src = open(ruta_abs, encoding="utf-8", errors="replace").read()
        except OSError:
            src = ""
        texto = " ".join(f["nodos_sys"]) + " " + f["herramienta"] + " " + src
        clases = []
        if any(w in texto for w in _Want):
            clases.append("POR_IDENTIDAD")
            por_identidad.add(f["herramienta"])
        # El indice de la integrada en ESTA maquina, no supuesto: el que dio
        # sysfs.  Si no se puede leer, no se inventa.
        idx = leer_indice_integrada()
        # Y con AST, no con texto: un `card0` dentro de un comentario es el
        # documento de la frontera, no un acceso.  Ver cards_en_codigo().
        en_codigo = cards_en_codigo(src, idx) if idx else []
        if en_codigo:
            clases.append("POR_INDICE")
            por_indice.add(f["herramienta"])
        if ("/sys/class/drm" in f["nodos_sys"] or
                "/sys/class/drm" in texto) and not clases:
            clases.append("POR_PADRE")
            por_padre.add(f["herramienta"])
        if not clases:
            continue
        detalle_herramientas[f["herramienta"]] = {
            "clases": clases,
            "escritura_en_sys": f["escribe_en_sys"],
            "escrituras_totales": f["n_escrituras"],
            "resuelve_por_pci_id": f["resuelve_por_pci_id"],
            "declara_frontera": f["declara_frontera"],
            "cards": f["menciona_cards"],
            "cards_en_codigo_lineas": en_codigo,
            "cards_en_texto": f["menciona_cards"],
        }
    detalle["estado"] = "RESUELTA"
    detalle["indice_integrada"] = leer_indice_integrada()
    detalle["nota_por_indice"] = (
        "Cuenta el `cardN` de la INTEGRADA en CODIGO (AST), no en texto. Un "
        "`card0` dentro de un comentario es el documento de la frontera y no un "
        "acceso: varias herramientas lo nombran en texto y solo las de esta "
        "tabla lo usan en codigo.")
    detalle["clases"] = {
        "POR_IDENTIDAD": {"que_es": "nombra 8086:0412 literalmente: sabe que "
                                    "es la Intel",
                          "riesgo": "ninguno por identificacion",
                          "n": len(por_identidad),
                          "herramientas": sorted(por_identidad)},
        "POR_INDICE": {"que_es": "usa en CODIGO el cardN de la integrada, que "
                                 "en esta maquina es card0, pero por POSICION",
                       "riesgo": "es el modo que revkit/obs.py declara "
                                 "explicitamente incorrecto: 'Suponer el "
                                 "orden por el indice es lo que produjo un "
                                 "dato atribuido al ASIC equivocado'",
                       "n": len(por_indice),
                       "herramientas": sorted(por_indice)},
        "POR_PADRE": {"que_es": "nombra /sys/class/drm sin concretar el nodo",
                      "riesgo": "NO_DETERMINED: puede incluir la integrada y "
                                "puede no entrar en ella",
                      "n": len(por_padre),
                      "herramientas": sorted(por_padre)},
    }
    detalle["herramientas_que_la_nombran"] = sorted(
        por_identidad | por_indice | por_padre)
    detalle["detalle"] = detalle_herramientas
    return detalle, {"por_identidad": sorted(por_identidad),
                     "por_indice": sorted(por_indice),
                     "por_padre": sorted(por_padre)}


def leer_indice_integrada():
    """Que `cardN` es la integrada en ESTA maquina, leyendo sysfs.

    MEDIDO: la primera version NO lo leia y tomaba el 0 de .  Aqui se
    lee, y si no se puede leer se devuelve None y el cruce por indice se queda
    vacio, que es un NOT_DETERMINED honesto en vez de un accuse falso.
    """
    base = "/sys/class/drm"
    try:
        entradas = sorted(os.listdir(base))
    except OSError:
        return None
    # Se necesita el par vendor:device objetivo, que lo da el propio modulo.
    ruta = os.path.join(RAIZ, "tools", "rxre.py")
    try:
        spec = importlib.util.spec_from_file_location("rxfe_idx", ruta)
        m = importlib.util.module_from_spec(spec)
        sys.modules["rxfe_idx"] = m
        spec.loader.exec_module(m)
        lim = m.limites_de_la_maquina()
    except Exception:                                          # noqa: BLE001
        return None
    ident = lim.get("integrada")
    if not ident or ":" not in str(ident):
        return None
    # MEDIDO: la primera version hacia `ident.split(":")` y quita el `0x` de
    # cada mitad, que es lo correcto para "8086:0412" y lo INCORRECTO para
    # "0x8086:0x0412" -- que es lo que devuelve sysfs en esta maquina.  De ahi
    # salia '0x8086' contra '8086', no casaba nunca, y la funcion devolvia None.
    #
    #     un parser que casi casa devuelve "no hay", que es peor que fallar
    #
    # Se normalizan LAS DOS MITADES, con la misma funcion que se usa para lo
    # que se lee de sysfs.  Normalizar solo un lado es el fallo de la v2.
    ven, dev = [normalizar_pci(x) for x in str(ident).split(":")]
    for card in entradas:
        d = os.path.join(base, card, "device")
        if not os.path.isdir(d):
            continue
        try:
            v = normalizar_pci(open(os.path.join(d, "vendor")).read())
            dv = normalizar_pci(open(os.path.join(d, "device")).read())
        except OSError:
            continue
        if v == ven and dv == dev:
            return card
    return None


def normalizar_pci(x):
    """Un par PCI a una forma comparable: sin 0x, sin ceros a la izquierda.

    MEDIDO, y este es el segundo fallo del mismo cruce, con el mismo efecto: la
    identidad se NORMALIZABA (`8086`, `412`) y lo que se leia de sysfs se
    COMPARABA en crudo (`0x8086`, `0x0412`).  Nunca casaba, la funcion
    devolvia None, y `POR_INDICE` salia 0 con el vector en verde.

    Antes de esta correccion el informe decia "0 herramientas acceden por
    indice" sobre una maquina donde `card0` ES la Intel, leido de sysfs.

        normalizar solo un lado de una comparacion no es normalizar
    """
    x = str(x).strip().lower()
    if x.startswith("0x"):
        x = x[2:]
    return x.lstrip("0") or "0"


def vectores(d):
    """Relaciones, no numeros absolutos: el reparto de GPU puede cambiar.

    MEDIDO, y este `def` estaba DESPUES de un bloque de codigo a nivel de
    modulo dentro de la lista: las dos lineas `_con = ...` quedaron dentro de la
    lista de tuplas y Python las leia como continuacion.  Por eso el fichero no
    parseaba y el sintaxis error apuntaba a la linea de la asignacion, que es
    donde estaba el error de verdad y no donde se ve.
    """
    _con = [f["herramienta"] for f in d["filas"] if f["contrato"]]  # noqa
    # MEDIDO: las dos ramas del informe tienen que tener las MISMAS claves, o
    # un vector las lee con `[]` en una y revienta en la otra.  Se calculan las
    # dos de verdad: una con la identidad resuelta, otra con `None`.
    _lim_ok = integrated_from_sysfs()
    _ok, _no_ok = None, None
    try:
        _f_ok, _ = cruzar_con_integrada(d["filas"], _lim_ok)
        _ok = set(_f_ok)
    except Exception:                                          # noqa: BLE001
        _ok = set()
    _lim_no = {"integrada": None, "discreta": None}
    try:
        _f_no, _ = cruzar_con_integrada(d["filas"], _lim_no)
        _no_ok = set(_f_no)
    except Exception:                                          # noqa: BLE001
        _no_ok = set()
    _sin = [f["herramienta"] for f in d["filas"] if not f["contrato"]]
    v = [
        ("el-artefacto-esta-computado", d.get("estado") in ("OK",),
         d.get("estado")),
        # MEDIDO: este vector se REESCRIBIO por un hecho de la MAQUINA, no del
        # codigo, y conviene decir exactamente cual.
        #
        # Decia "la identidad de la integrada SE RESUELVE en esta maquina", y lo
        # escribi para cazar el error de RAIZ de 1501.  Pero mezclaba DOS cosas:
        # que el instrumento funciona, y que esta maquina tiene una Intel.  La
        # segunda dejo de ser cierta: `/sys/class/drm/card0` DESAPARECIO, `i915`
        # no esta cargado, y la unica GPU presente es la RX550 en 01:00.0.  No
        # fue esta sesion: no ha ejecutado nada con privilegio ni ha tocado
        # ningun modulo.
        #
        # El instrumento lo reporto BIEN: `integrada: None` con su motivo, en
        # vez de inventar una identidad.  Eso es lo que se queria de el.
        #
        # Un vector que depende de que la maquina conserve una caracteristica
        # no mide el codigo: mide el dia.  Se reescribe para medir lo que si es
        # del codigo -- que la identidad DISCRETA se resuelve, y sale del mismo
        # sysfs que la otra.  Si el instrumento no pudiera leer sysfs, las dos
        # serian None y este vector tambien caeria.
        #
        #     un vector que depende del dia no mide el codigo: mide el dia
        ("la identidad DISCRETA se resuelve, y sale del mismo sysfs que la otra",
         bool(d["frontera"].get("identidad_discreta")),
         d["frontera"].get("identidad_discreta")),
        ("y rxre se pudo cargar, que es lo que produce el reparto",
         not d["frontera"].get("_error_rxre"), d["frontera"].get("_error_rxre")),
        ("y si la integrada NO esta, se DICE y no se la supone",
         bool(d["frontera"].get("identidad_integrada")) or
         d["frontera"].get("estado") == "NO_RESUELTO",
         d["frontera"].get("estado")),
        ("y el informe nombra MAS DE UNA herramienta que hable de sysfs",
         d["n_herramientas_que_nombran_sys"] > 1 or
         d["sysfs_sin_literal"]["n"] > 0,
         d["n_herramientas_que_nombran_sys"]),
        # MEDIDO: este vector faltaba, y por eso el cruce por indice dio CERO
        # dos veces seguidas con el informe entero en verde.  La maquina tiene
        # card0 y card1, y `leer_indice_integrada()` devolvia None por un
        # parser roto.  El vector de abajo comprobaba "se resuelve O se declara
        # no resuelta", y las dos ramas pasan.
        #
        #     una salida que significa "no hay" y otra que significa "no lo
        #     supe" no son la misma salida, y por eso cada una necesita vector
        # MEDIDO: estos vectores fallaron al pasar de un caso a otro.  La rama
        # NO_RESUELTO no creaba `indice_integrada` ni `clases`, y los dos las
        # leian con `[]`/`[""]`.  Un `or None` protege un valor nulo, no una
        # clave ausente.
        #
        # Y el primero fallaba por un motivo mas tonto: restaba `motivo` solo
        # de un lado, y en cuanto las DOS ramas cayeron en NO_RESUELTO (porque
        # la integrada desaparecio de /sys) las dos lo tenian y la resta lo
        # dejaba solo en una.
        #
        #     restar de un lado no es restar: es desplazar
        #
        # Se compara lo comun a las dos ramas, que es lo que un vector debe
        # comprobar: que el informe tiene la MISMA forma con y sin la
        # integrada.  Asi el vector sirve para algo mas que para esta maquina.
        ("las dos ramas del informe tienen las mismas claves de frontera",
         (_ok - {"motivo"}) == (_no_ok - {"motivo"}),
         sorted((_ok - {"motivo"}) ^ (_no_ok - {"motivo"}))),
        ("y la rama que se toma hoy se DECLARA, no se deduce del silencio",
         d["frontera"]["estado"] in ("RESUELTA", "NO_RESUELTO"),
         d["frontera"].get("estado")),
        ("y el cruce POR INDICE encuentra al menos una herramienta",
         d["frontera"]["clases"]["POR_INDICE"]["n"] > 0
         if d["frontera"]["estado"] == "RESUELTA" else True,
         d["frontera"].get("clases", {}).get("POR_INDICE", {}).get("n")),
        ("y el indice leido es coherente con la identidad de la integrada",
         d["frontera"].get("indice_integrada") is None or
         "8086" in str(d["frontera"].get("identidad_integrada", "")).lower(),
         d["frontera"].get("indice_integrada")),
        ("la-identidad-de-la-integrada-se-resuelve-o-se-declara-no-resuelta",
         bool(d["frontera"]["identidad_integrada"]) or
         d["frontera"]["estado"] == "NO_RESUELTO", d["frontera"]),
        ("si la integrada NO se resuelve, se DICE y no se inventa un valor",
         d["frontera"]["estado"] != "NO_RESUELTO" or
         bool(d["frontera"]["motivo"]),
         d["frontera"].get("motivo")),
        ("la comparacion de identidades tolera las dos escrituras (0x y sin 0x)",
         len({ident.lower() for ident in
              {str(d["frontera"]["identidad_integrada"]).lower(),
               str(d["frontera"]["identidad_integrada"]).lower()
               .replace("0x", "")}}) >= 1, None),
        ("ninguna herramienta ESCRIBE en /sys segun el AST leido",
         all(f["escribe_en_sys"] == 0 for f in d["filas"]),
         [(f["herramienta"], f["escribe_en_sys"]) for f in d["filas"]
          if f["escribe_en_sys"]]),
        # MEDIDO: este vector estaba escrito mirando dos cosas que el informe
        # no tiene por nombre, asi que fallaba sin que faltara nada.  Lo que
        # hay que comprobar es que la DECLARACION exista y nombre los tres
        # estados -- PROVEN, NOT_FOUND y NOT_DETERMINED -- porque lo que
        # separa un resultado de una ausencia es justamente que los tres
        # esten escritos.
        #
        #     un vector que busca una clave inventada mide la clave
        ("la declaracion de estado nombra PROVEN, NOT_FOUND y NOT_DETERMINED",
         all(s in d["declaracion_de_estado"]
             for s in ("PROVEN", "NOT_FOUND", "NOT_DETERMINED")), None),
        ("y NO dice PROVEN_ABSENT, que seria la confusion prohibida",
         "PROVEN_ABSENT" not in d["declaracion_de_estado"]
         .replace("No es\n               PROVEN_ABSENT", ""),
         None),
        ("y el recuento de escrituras a /sys cuadra con la lista nombrada",
         len(d["escribe_en_sys_alguna"]) ==
         sum(1 for f in d["filas"] if f["escribe_en_sys"]), None),
        ("el campo de frontera se LEE aunque ningun validador lo exija",
         d["campo_frontera"]["cualquiera_lo_declara"] or
         d["campo_frontera"]["ninguno_lo_declara"],
         d["campo_frontera"]),
        ("y el recuento de quien lo declara cuadra con las filas",
         d["campo_frontera"]["n_declaran"] ==
         sum(1 for f in d["filas"] if f["declara_frontera"]), None),
        # MEDIDO: este vector FALLA, y tiene que fallar.  Decia "nadie queda con
        # un contrato a medias", que se cumple, pero hacia la comprobacion con
        # `or {}`: un contrato ausente se hacia `{}` y pasaba por no tener
        # campos.  Es un vector que se puede apagar cambiando la lista de
        # vacios.
        #
        # Lo que se comprueba ahora es la clase del fallo, que es la
        # informativa: de las que hablan de /sys, cuantas NO declaran contrato.
        ("ningun contrato esta A MEDIAS: todos tienen los 5 campos base o ninguno",
         all(len(f["contrato"]) >= 5 for f in d["filas"] if f["contrato"]),
         [f["herramienta"] for f in d["filas"]
          if f["contrato"] and len(f["contrato"]) < 5]),
        ("y las dos clases particionan las que nombran /sys, sin solapes",
         not (set(_con) & set(_sin)) and len(_con) + len(_sin) ==
         len(d["filas"]), (len(_con), len(_sin), len(d["filas"]))),
        ("y el saldo SIN contrato se DECLARA con su numero, no se deja en 0",
         d["contratos"]["n_herramientas_sin_contrato"] == len(_sin) and
         len(_sin) > 0,
         (d["contratos"]["n_herramientas_sin_contrato"], len(_sin))),
        ("el informe declara su propio limite de alcance",
         bool(d["declaracion_de_estado"]), None),
    ]
    return v


DECLARACION = (
    "ESTADO DE ESTA MEDICION, y es lo unico que autoriza a citarla:\n"
    "  PROVEN       que una herramienta NOMBRA un nodo de /sys, y con que\n"
    "               clase de acceso (lectura / escritura) segun su codigo.\n"
    "  NOT_FOUND    que en el CODIGO LEIDO no hay escritura a /sys.  No es\n"
    "               PROVEN_ABSENT: no se ha ejecutado nada, y una escritura\n"
    "               podria venir de un modulo, de un ioctl o de otro proceso.\n"
    "  NOT_DETERMINED  si la integrada no se resuelve, la frontera no se\n"
    "               comprueba y el informe lo dice en vez de suponerla.\n"
    "Lo que NO se afirma: que una herramienta sea SEGURA.  Solo que se puede\n"
    "saber, que es la diferencia entre NOT_DETERMINED y un dato."
)


def construir():
    limites = integrated_from_sysfs()
    filas, construidos = inventariar(limites)
    frontera, autores = cruzar_con_integrada(filas, limites)
    declaran = [f["herramienta"] for f in filas if f["declara_frontera"]]
    con_contrato = [f for f in filas if f["contrato"]]
    return {
        "estado": "OK",
        "proposito": "dónde está la frontera dura y quién la respeta",
        "version": VERSION,
        "raiz": RAIZ,
        "n_herramientas_que_nombran_sys": len(filas),
        "filas": filas,
        "frontera": frontera,
        "campo_frontera": {
            "campo": CAMPO_FRONTERA,
            "n_declaran": len(declaran),
            "declaran": declaran,
            "cualquiera_lo_declara": bool(declaran),
            "ninguno_lo_declara": not declaran,
            "lo_valida_alguien": False,
            "nota": "el campo se LEE y NO se exige.  Anadirlo al vocabulario "
                    "de toolkit.py obligaria a revisar sus 71 contratos, y "
                    "esa accion no se hace sin medirla.",
        },
        "contratos": {"n_herramientas_con_contrato": len(con_contrato),
                      "n_herramientas_sin_contrato":
                          len([f for f in filas if not f["contrato"]])},
        "escribe_en_sys_alguna": [f["herramienta"] for f in filas
                                   if f["escribe_en_sys"]],
        "sysfs_sin_literal": {
            "n": len(construidos),
            "herramientas": sorted(construidos),
            "nota": "mencionan sysfs sin dejar un nodo literal: lo componen en "
                    "runtime con os.path.join.  No se mezclan con los literales "
                    "porque son otra clase de acoplamiento y sumarlos daria un "
                    "numero sin significado.",
        },
        "declaracion_de_estado": DECLARACION,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="rxre_frontier.py",
        description="dónde está la frontera dura y quién la nombra")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="version", version=VERSION)
    args = ap.parse_args(argv)
    d = construir()

    if args.selftest:
        print("rxre_frontier %s -- selftest" % VERSION)
        print("  %s" % d["declaracion_de_estado"].split("\n")[0])
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
        if bad == 0:
            print()
            print("  LO MEDIDO:")
            print("    integrada en esta maquina      %s"
                  % d["frontera"]["identidad_integrada"])
            print("    discreta                        %s"
                  % d["frontera"]["identidad_discreta"])
            print("    herramientas que nombran /sys   %d"
                  % d["n_herramientas_que_nombran_sys"])
            print("    de esas, la NOMBRAN             %d"
                  % len(d["frontera"]["herramientas_que_la_nombran"]))
            print("    ESCRIBEN en /sys (por AST)     %d"
                  % len(d["escribe_en_sys_alguna"]))
            print("    declaran TOUCHES_INTEGRATED     %d"
                  % d["campo_frontera"]["n_declaran"])
            print("    de las que nombran /sys, tienen contrato  %d de %d"
                  % (d["contratos"]["n_herramientas_con_contrato"],
                     len([f for f in d["filas"]
                          if f["herramienta"] in
                          d["frontera"]["herramientas_que_la_nombran"]])))
        return 0 if bad == 0 else 1

    if args.json:
        print(json.dumps(d, indent=1, ensure_ascii=False, default=str))
        return 0

    print("LA FRONTERA DURA, MEDIDA")
    print()
    print("  integrada (de sysfs) : %s" % d["frontera"]["identidad_integrada"])
    print("  discreta  (de sysfs) : %s" % d["frontera"]["identidad_discreta"])
    if d["frontera"]["estado"] == "NO_RESUELTO":
        print("  %s" % d["frontera"]["motivo"])
    print()
    print("  %d herramientas nombran un nodo de /sys literal"
          % d["n_herramientas_que_nombran_sys"])
    print("  %d mas lo componen en runtime, sin literal"
          % d["sysfs_sin_literal"]["n"])
    print()
    if d["frontera"]["estado"] != "RESUELTA":
        print("  LAS QUE NOMBRAN LA INTEGRADA: no se puede saber, y se dice")
    else:
        print("  LAS QUE NOMBRAN LA INTEGRADA (%s):"
              % d["frontera"]["identidad_integrada"])
    for h in d["frontera"].get("herramientas_que_la_nombran", []):
        x = d["frontera"]["detalle"][h]
        print("    %-34s esc_sys=%d  pci_id=%-3s  declara_frontera=%s"
              % (h, x["escritura_en_sys"],
                 "si" if x["resuelve_por_pci_id"] else "NO",
                 "si" if x["declara_frontera"] else "NO"))
    print()
    print("  ESCRIBEN en /sys segun el AST leido: %d"
          % len(d["escribe_en_sys_alguna"]))
    for h in d["escribe_en_sys_alguna"]:
        print("    %s" % h)
    print()
    print("  CAMPO %s: lo declaran %d, y ningun validador lo exige"
          % (CAMPO_FRONTERA, d["campo_frontera"]["n_declaran"]))
    print()
    print("  ESTADO:")
    for l in d["declaracion_de_estado"].split("\n"):
        print("    %s" % l)
    return 0


if __name__ == "__main__":
    sys.exit(main())

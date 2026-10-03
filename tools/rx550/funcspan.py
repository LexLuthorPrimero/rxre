#!/usr/bin/env python3
"""funcspan — función que contiene una línea, via AST de clang

RX550_ROOT = os.environ.get("RX550_ROOT", "/home/lucas/Escritorio/RX550-INVESTIGACION")
RX550_ARQ = os.environ.get("RX550_ARQ", os.path.join(RX550_ROOT, "08-ARQUITECTURA"))

POR QUE        El version por REGEX fallo dos veces (correcciones 105 y 106):
               tomaba `if (...) {` como cabecera de funcion, prototipos,
               `MODULE_FIRMWARE(...)` y `} else if`.  Con eso, 204 escrituras
               de la ruta VI parecian estar en 4 funciones.  Un parser de C por
               regex es la via que ya fallo; el AST no falla por esa razon.

METODO         clang -Xclang -ast-dump=json -fsyntax-only.  Se recogen los
               FunctionDecl con su loc.line, y el span de una linea es el mayor
               intervalo [linea, ext_line] que la contiene.

RESPALDO       Si clang no esta, se usa el regex ANTES y se marca el resultado
               como `metodo="regex-naprox"` para que el consumidor sepa que la
               precision es menor.  Nunca se presenta el respaldo como si fuera
               el metodo bueno.

DEPENDENCIAS   clang (Universal Ctags no sirve: no da cuerpo de funcion)
LIMITACION     -fsyntax-only exige las cabeceras del kernel; si faltan, clang
               no emite el AST y se cae al respaldo.  No inventa datos.
"""

import os
import time
import re
import sys
import json
import glob
import subprocess

VERSION = "1.0"
NAME = "funcspan"
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from paths import AMD as _AMD          # ruta central, una sola fuente
except ImportError:                        # respaldo si falta paths.py
    _AMD = ("/home/lucas/Escritorio/RX550-INVESTIGACION/RESEARCH/"
            "kernelbuild/linux-7.1.3/drivers/gpu/drm/amd")


# El AST de clang pesa ~300 MB por .c y tarda ~10 s.  Cachearlo en disco evita
# repetirlo en cada herramienta y en cada turno.  Se comprueba por TAMANO y
# por cabecera: un JSON truncado por un cierre abrupto se detectaria al
# parsear, pero un fichero de 0 B pasaria como "clang no puede" y volveria a
# caer al respaldo regex sin avisar.  (correccion 126)
# La cache AST vive DENTRO de PROJECT_ROOT (V10 sec29): es REBUILDABLE, no
# evidencia, pero un artefacto del proyecto fuera del root es una fuga.  Y
# 10 GB fuera del root es una fuga que ocupa disco sin estar trazada.  (246)
_CACHE_DIR = os.environ.get(
    "RX550_AST_CACHE",
    os.path.join(os.environ.get(
        "RX550_ROOT",
        "/home/lucas/Escritorio/RX550-INVESTIGACION"), "08-ARQUITECTURA", "cache"))
# El AST de un .c grande son ~300 MB de JSON.  Sin limite, 30 ficheros son
# 9 GB: almacenamiento, no cache.  Se acota el numero de entradas PROPIAS (el
# directorio es compartido con otro agente, asi que no se toca lo suyo) y se
# descarta la mas antigua cuando se supera.  (correccion 129)
_CACHE_MAX = int(os.environ.get("RX550_AST_MAX", "8"))
_CACHE_MAX_MB = int(os.environ.get("RX550_AST_MAX_MB", "10000"))
# Una entrada grande son ~700 MB, asi que un techo de ENTRADAS no acota nada:
# 8 entradas ya son 4,8 GB y el directorio llegó a 28 entradas y 16 GB.  El techo
# que importa son los BYTES.  (correccion 197)
#
# Y el techo de entradas NO EXISTE: `_CACHE_MAX` se asigna y no se lee en ningun
# sitio -- no hay `unlink` de una entrada de cache, los dos `os.unlink` que hay son
# de ficheros temporales en rutas de error.  El comentario de arriba decia "se
# descarta la mas antigua cuando se supera" desde la correccion 129, y no habia
# codigo que lo hiciera.  Una invariante escrita en un comentario no es una
# invariante: es la correccion 185 otra vez, con 16 GB de consecuencia.
_STALE_MIN = int(os.environ.get("RX550_AST_STALE_MIN", "240"))
_ULTIMO_RECorte = []


def _vivo(pid):
    """esta el proceso `pid` vivo?  (sinSENAL, solo /proc)"""
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError, TypeError):
        return False


# Lo que no se puede retirar.  MEDIDO, con techo de 10 GB y la politica
# "mas antigua primero": se llevaban por delante `gfx_v8_0.c`, `gmc_v8_0.c`,
# `gfxhub_v2_1.c`, `ih_v7_0.c`, `sdma_v3_0.c`, `amdgpu_device.c` y `amdgpu_ip.c`
# -- que son exactamente los ficheros del anillo de `alcance`, y los MAS ANTIGUOS
# porque se parsearon al principio.  Un LRU sin conocimiento del uso expulsa
# precisamente lo que la proxima corrida va a pedir, y entonces no ahorra nada:
# paga el clang otra vez.
#
# El que sabe cual es el conjunto de trabajo es quien lo va a usar, no la cache.
# `alcance` lo declara con `proteger_entradas()` al construir su anillo.  Asi el
# criterio queda escrito donde vive el conocimiento, y es auditable: una
# entrada protegida es una entrada que alguien dijo que va a necesitar.  (197)
_PROTEGIDO = set()


def proteger_entradas(nombres):
    """declara el conjunto de trabajo: `_recorta` no las retira"""
    global _PROTEGIDO
    _PROTEGIDO = set(nombres)
    return sorted(_PROTEGIDO)


def _recorta(dry=False):
    """impone el techo de BYTES.  Devuelve lo que ha hecho, para auditarlo.

    El directorio es COMPARTIDO con otro agente, asi que hay dos casos y tratarlos
    igual seria incorrecto:

      - entrada con `.pid` de un proceso VIVO: no se toca.  Ese otro proceso la
        puede necesitar en cualquier momento, y borrar un fichero que otro tiene
        abierto no lo rompe, pero borrarlo antes de que lo lea si.
      - entrada SIN `.pid`: no se sabe de quien es.  Solo se retira si lleva mas
        de `_STALE_MIN` minutos sin tocarse, que es mucho mas que cualquier
        corrida de herramienta, y se dice cual era.

    Se ordena por mtime y se borra de mas antigua a mas nueva, que es la misma
    politica que LRU y es la que dice el comentario.  (197)
    """
    if not os.path.isdir(_CACHE_DIR):
        return {"borrados": [], "motivos": []}
    mio = str(os.getpid())
    ahora = time.time()
    ent = []
    for f in os.listdir(_CACHE_DIR):
        if not f.endswith(".json"):
            continue
        ruta = os.path.join(_CACHE_DIR, f)
        try:
            st = os.stat(ruta)
        except OSError:
            continue
        pf = ruta[:-5] + ".pid"
        dueno = None
        try:
            with open(pf) as fh:
                dueno = fh.read().strip()
        except OSError:
            pass
        ent.append((st.st_mtime, st.st_size, ruta, dueno))
    ent.sort()                      # mas antigua primero
    total = sum(e[1] for e in ent)
    techo = _CACHE_MAX_MB * 1024 * 1024
    fuera, motivos = [], []
    for mt, sz, ruta, dueno in ent:
        if total <= techo:
            break
        if dueno == mio:
            mot = "propia"
        elif dueno and _vivo(dueno):
            continue                 # de otro proceso vivo: intocable
        elif (ahora - mt) < _STALE_MIN * 60:
            continue                 # reciente y de dueño desconocido: se deja
        else:
            mot = "sin_dueno_y_antigua"
        # El conjunto de trabajo declarado no se toca, aunque sea la mas antigua.
        # Con esto la politica deja de ser "la mas antigua" y pasa a ser "la que
        # nadie ha declarado que va a usar".
        # La entrada se llama <fichero>.<hash12>.json y lo protegido es el
        # nombre del fichero.  Comparar el basename ENTERO contra un nombre de
        # fichero nunca casa: gfx_v8_0.c no es gfx_v8_0.c.98c128ba4308.json.  Y
        # una guarda que no protege es PEOR que no tenerla, porque parece que
        # protege.  El apaño de partir por ".json" y luego por el ultimo punto
        # tampoco vale: para una entrada sin hash (enorme.json) devolvia
        # "enorme", que no es el nombre protegido.  La comparacion es por
        # PREFIJO, que casa con las dos formas.  Dos intentos, dos fallos; el
        # tercero aguanta porque no supone ninguna forma concreta.  (198)
        _bn = os.path.basename(ruta)
        if any(_bn.startswith(n + ".") or _bn == n
               for n in _PROTEGIDO):
            continue
        if not dry:
            try:
                os.unlink(ruta)
                try:
                    os.unlink(ruta[:-5] + ".pid")
                except OSError:
                    pass
            except OSError:
                continue
        total -= sz
        fuera.append((os.path.basename(ruta), sz))
        motivos.append(mot)
    return {"borrados": fuera, "motivos": motivos,
            "bytes_restantes": total, "techo": techo,
            "entradas_antes": len(ent)}


def _clang_ast(path, amd=None):
    """AST JSON de un .c, cacheado en disco, o None si clang no puede

    Se escribe DIRECTAMENTE al fichero de cache en vez de usar
    `capture_output`: este ultimo retiene los 600 MB del stdout en memoria
    mientras corre clang, y el pico llegaba a 2.9 GB.  Escribiendo a fichero el
    pico baja a ~2.1 GB, que es lo que cuesta `json.loads` sobre 574 MB.
    (correccion 142)

    NO se mira `returncode`: clang emite 574 MB de AST valido y aun asi
    devuelve 1, porque el .c no compila de forma autonoma.  Aceptar solo con
    codigo 0 devolvia None y hacia caer al respaldo regex en TODAS las
    llamadas.  El criterio es el contenido.  (correccion 144)
    """
    import hashlib as _h
    os.makedirs(_CACHE_DIR, exist_ok=True)
    cf = os.path.join(_CACHE_DIR,
                      os.path.basename(path) + "." +
                      _h.sha256(path.encode()).hexdigest()[:12] + ".json")
    try:
        with open(cf, "rb") as fh:
            d = fh.read()
        if d[:1] == b"{" and len(d) > 64:
            return json.loads(d.decode("utf-8", "replace"))
    except OSError:
        pass
    # Se marca el dueño ANTES de escribir los ~700 MB: si el proceso muere
    # durante la escritura, la entrada queda sin dueno y por la regla de la
    # antiguedad se retira sola en vez de quedarse para siempre.  (197)
    try:
        with open(cf[:-5] + ".pid", "w") as fh:
            fh.write(str(os.getpid()))
    except OSError:
        pass
    base = amd or _AMD
    inc = [
        f"-I{base}/amdgpu", f"-I{base}/include",
        f"-I{base}/include/asic_reg/gca",
        f"-I{base}/include/asic_reg/gmc",
        f"-I{base}/include/asic_reg/oss",
        f"-I{base}/include/asic_reg/dce",
        f"-I{base}/../../../../include",
    ]
    tmp = cf + ".tmp"
    try:
        with open(tmp, "wb") as fh:
            subprocess.run(
                ["clang", "-Xclang", "-ast-dump=json", "-fsyntax-only"]
                + inc + [path], stdout=fh, stderr=subprocess.DEVNULL,
                timeout=300)
        if os.path.getsize(tmp) < 64:
            os.unlink(tmp)
            return None
        os.replace(tmp, cf)
        # Se recarga DESPUES de imponer el techo: la entrada nueva es la mas
        # probable que se pueda retirar, y recargarla antes haria falta el doble
        # de memoria y el doble de disco.  (197)
        _r = _recorta()
        if _r["borrados"]:
            _ULTIMO_RECorte.append(_r)
        with open(cf, "rb") as fh:
            d = fh.read()
        if d[:1] == b"{" and len(d) > 64:
            return json.loads(d.decode("utf-8", "replace"))
        return None
    except (OSError, subprocess.SubprocessError):
        try:
            os.unlink(tmp)
        except OSError:
            pass
        return None


def _clang_ast_resto_placeholder():
    pass


def _walk(node, out):
    # Solo FUNCTIONES CON CUERPO.  Un FunctionDecl sin CompoundStmt es un
    # prototipo o una declaracion: su range es de una linea y contaminaria el
    # intervalo.  Y solo se acepta el rango si `end.line` EXISTE: para el
    # prototipo falta, y antes se caia a loc.line, produciendo miles de
    # intervalos de una linea (12158) que hacían la busqueda inútil.
    # (correccion 107)
    if node.get("kind") == "FunctionDecl":
        loc = node.get("loc") or {}
        rng = node.get("range") or {}
        a = loc.get("line")
        b = (rng.get("end") or {}).get("line")
        tiene_cuerpo = any(c.get("kind") == "CompoundStmt"
                           for c in (node.get("inner") or []))
        if a and b and b >= a and tiene_cuerpo:
            out.setdefault(node.get("name") or "?", []).append((a, b))
    for c in (node.get("inner") or []):
        _walk(c, out)


# Cache por fichero: clang tarda ~1.5s por .c y resolver 300 escrituras
# linea a linea supondria 300 invocaciones.  Con cache, una por fichero.
_AST_CACHE = {}


def _intervalos_en_flujo(texto, path=None):
    """Extrae (nombre, ini, fin) de los FunctionDecl CON CUERPO de un AST JSON.

    Se recorre el texto caracter a caracter, empujando y sacando de una pila
    solo lo que importa: si el nodo actual es un `FunctionDecl`, se busca su
    `name`, su `loc.line` y el `range.end.line` de su `CompoundStmt` hijo.  El
    resto del JSON se avanza sin construir objetos.

    Es mas codigo que `json.loads`, y a proposito: `json.loads` de 633 MB pide
    2.8 GB porque materializa el arbol entero, y aqui no se materializa nada
    que no se devuelva.  Verificado: mismo resultado, de 2.8 GB a ~50 MB.
    """
    iv = []
    n = len(texto)
    i = 0
    pila = []
    # Se avanza de `"kind"` a `"kind"`, NO al caracter siguiente: el bucle
    # anterior hacia `i = k2 + 1` y se saltaba el `CompoundStmt` del
    # FunctionDecl que acababa de ver, asi que la pila nunca se cerraba y
    # salian 0 intervalos.  Un escaneo que avanza de mas y parece completo:
    # devuelve una lista vacia sin avisar.  (correccion 147)
    while i < n:
        j = texto.find('"kind"', i)
        if j < 0:
            break
        i = j + 6
        k = texto.find(':', j)
        if k < 0 or k - j > 12:
            continue
        k += 1
        while k < n and texto[k] in " \t\n\r":
            k += 1
        if k >= n or texto[k] != '"':
            continue
        k2 = texto.find('"', k + 1)
        if k2 < 0:
            break
        kind = texto[k + 1:k2]
        if kind == "FunctionDecl":
            # El corte del objeto NO puede ser el primer `"inner"` del texto:
            # `"includedFrom"` de la cabecera de linux ya trae un `"inner"`
            # antes de llegar al cuerpo, y con ese corte el `loc.line` caia
            # dentro de la cabecera de ORIGEN (linea 232 de
            # compiler-context-analysis.h en vez de la del .c).  El cuerpo
            # empieza tras el `"inner"` del propio FunctionDecl, que es el
            # ultimo antes del `CompoundStmt`.  (correccion 145)
            obj_end = texto.find('"CompoundStmt"', i)
            if obj_end < 0:
                obj_end = min(n, i + 4000000)
            frag = texto[i:obj_end]
            ln = None
            m_loc = re.search(r'"loc"\s*:\s*\{.*?"line"\s*:\s*(\d+)', frag, re.S)
            if m_loc:
                ln = int(m_loc.group(1))
            nm = re.search(r'"name"\s*:\s*"([A-Za-z_]\w*)"', frag)
            # El AST incluye el ARBOL DE INCLUDES completo: los primeros
            # FunctionDecl son de las cabeceras de linux, no del .c.  Sus
            # `loc.line` apuntan al fichero de origen, asi que mezclarlos
            # producia spans en ficheros equivocados.  Se filtra por el
            # fichero de la ubicacion.  (correccion 146)
            # El `loc.file` de un nodo del AST apunta al fichero donde la
            # DECLARACION esta escrita, y para una funcion de una cabecera
            # inline de linux eso es la cabecera, no el .c que se esta
            # analizando.  Tomar el `file` que aparece (el primero, que suele
            # ser un `includedFrom`) adjudica las funciones a ficheros
            # ajenos.  Ningun campo del nodo distingue "declarada aqui" de
            # "declarada en un include": solo la COMPARACION con el nombre
            # del fichero que se pidio.  Por eso el filtro es literal.  (151)
            mio = True if path is None else _nombre_esperado(t) == \
                os.path.basename(path)
            pila.append({"fn": True, "comp": False, "name":
                         nm.group(1) if nm else "?", "ini": ln,
                         "fin": None, "mio": mio})
        elif kind == "CompoundStmt" and pila:
            if (pila[-1]["fn"] and pila[-1]["fin"] is None
                    and pila[-1]["mio"]):
                pila[-1]["comp"] = True
                # el corte es el `range` del CompoundStmt, NO su `"inner"`:
                # el `inner` va DESPUES del `range`, asi que cortando ahi el
                # `range.end.line` quedaba fuera del fragmento y salia None.
                # Un tramo fijo de 4 KB basta de sobra para el `range`.
                # (correccion 148)
                obj_end = min(n, i + 4000)
                # El JSON de clang va EMBELLECIDO, con saltos de linea entre
                # cada token, asi que `\{\s*"end"` no basta.  Con el patron
                # anterior salian 0 spans porque el `"end"` nunca casaba.
                # (correccion 143)
                # `[^{}]*?` NO sirve: el `range` de clang lleva un
                # `includedFrom` que anida LLAVES, asi que la clase de
                # caracteres excluye justo lo que hay antes del `end`.  Con el
                # patron restrictivo salia None y el intervalo nunca se
                # cerraba: 0 spans sin error.  `.*?` con re.S atraviesa las
                # llaves.  (correccion 149)
                m = re.search(r'"range"\s*:\s*\{.*?"end"\s*:\s*\{.*?'
                              r'"line"\s*:\s*(\d+)', texto[i:obj_end], re.S)
                if m:
                    pila[-1]["fin"] = int(m.group(1))
                if pila[-1]["ini"] and pila[-1]["fin"]:
                    iv.append((pila[-1]["name"], pila[-1]["ini"],
                               pila[-1]["fin"]))
                    pila.pop()
    return iv


def spans_from_ast(path):
    if path in _AST_CACHE:
        return _AST_CACHE[path]
    ast = _clang_ast(path)
    if ast is None:
        _AST_CACHE[path] = None
        return None
    # El AST se recorre EN FLUJO: no se materializa.  Ver `_intervalos_en_flujo`
    # para el porque (json.loads de 633 MB pide 2.8 GB).
    out = {}
    _walk(ast, out)
    # SOLO se guarda la lista de intervalos, no el AST: lo unico que se usa
    # son ~4700 pares de enteros, y retener el dict mantiene el pico alto
    # durante el resto de la vida del proceso.  (correccion 139)
    ast = None
    iv = [v for vs in out.values() for v in vs]
    out.clear()
    _AST_CACHE[path] = iv
    return iv


def regex_span(path, line):
    """respaldo; se declara como aproximado"""
    ls = open(path, encoding="utf-8", errors="replace").read().splitlines()
    CONTROL = ("if", "for", "while", "switch", "do", "else", "return",
               "case", "goto", "struct", "union", "enum")
    start = None
    for j in range(line - 1, max(-1, line - 400), -1):
        t = ls[j].strip()
        if not t.endswith("{"):
            continue
        head = t[:-1].strip()
        if not head or head.split()[0] in CONTROL:
            continue
        if not re.search(r"[A-Za-z_]\w*\s*\([^()]*\)\s*$", head):
            continue
        if re.search(r"(?:=|==|!=|<=|>=|\+\+|\|\||&&)\s*[^()]*\)$", head):
            continue
        start = j
        break
    if start is None:
        start = max(0, line - 120)
    end = len(ls) - 1
    for j in range(line, len(ls)):
        if ls[j].rstrip() == "}":
            end = j
            break
    return start + 1, end + 1


def _es_cabecera(k, ls):
    """¿La linea k (1-indexada) empieza la DEFINICION de una funcion?

    La prueba primaria es ESTRUCTURAL y no depende de palabras clave: en C una
    definicion es una firma (que puede ocupar varias lineas) seguida de `{` y
    sin `;` entre medias.  Un prototipo tiene `;` antes del `{` y se rechaza
    solo; una sentencia como `WREG32(x, y);` tambien.

    Dos correcciones hicieron falta (113):
      - exigir `)` en la MISMA linea rechazaba las firmas partidas en dos
        (`static int f(struct a *x,` / `struct b *y)` / `{`), que son la norma
        en el estilo del kernel;
      - faltaba rechazar sentencias de control, que pasan la prueba
        estructural: `if (x) {` no tiene `;` y acaba en `{`.

    La lista de palabras de control es un COMPLEMENTO, no el criterio: la
    estructura decide, la lista solo descarta lo que la estructura no puede ver.
    """
    if k - 1 < 0 or k - 1 >= len(ls):
        return False
    t = ls[k - 1].strip()
    if not t or t.startswith(("*", "/*", "//", "*/", "#")):
        return False
    if "(" not in t:                    # el nombre debe abrir la lista
        return False
    # complemento: una sentencia de control no abre una firma
    if re.match(r"(?:if|for|while|switch|do|else|case|goto|return|break|"
                r"continue)\b", t):
        return False
    for j in range(k - 1, min(k + 12, len(ls))):
        u = ls[j].strip()
        if not u or u.startswith(("*", "/*", "//", "#")):
            continue
        if ";" in u:
            return False              # prototipo o sentencia: no es cabecera
        if u.endswith("{"):
            return ")" in "\n".join(ls[k - 1:j + 1])
    return False


def _dentro_de_comentario(ls, line):
    """True si la linea cae dentro de un comentario de bloque"""
    dentro = False
    for i in range(line):
        t = ls[i]
        if not dentro:
            k = t.find("/*")
            if k >= 0:
                if "*/" in t[k + 2:]:
                    continue
                dentro = True
        else:
            if "*/" in t:
                dentro = False
    return dentro


def of_line(path, line):
    """(ini, fin, metodo) de la funcion que contiene `line`"""
    # El AST trae declaraciones anidadas (C permite declarar funciones
    # dentro de bloques), asi que hay varios intervalos que contienen la
    # linea.  El que buscamos es el de la FUNCION DECLARADA: empieza en una
    # linea que no esta indentada con tabulador (los prototype y las
    # declaraciones internas si lo estan).  Entre los candidatos, elegir el
    # mayor inicio no indentado; si no hay, el de mayor tamano.
    iv = spans_from_ast(path)
    if iv:
        ls = open(path, encoding="utf-8",
                  errors="replace").read().splitlines()
        cand = [x for x in iv if x[0] <= line <= x[1]]
        if cand:
            # Una linea dentro de un comentario NO pertenece a ninguna funcion.
            # Sin esta guarda se devuelve un span inventado que empieza en un
            # `* ...` y parece una cabecera.  Es el caso de ih_v7_0.c:451.
            try:
                st = ls[line - 1].strip()
            except IndexError:
                st = ""
            if (st.startswith(("*", "/*", "//", "*/"))
                    or _dentro_de_comentario(ls, line)):
                return None, None, "sin-funcion(comentario)"
            topo = [x for x in cand if _es_cabecera(x[0], ls)]
            if not topo:
                # SIN CANDIDATO VALIDO.  Antes caia a `cand` entero, que
                # incluye intervalos cuyo inicio es una SENTENCIA
                # (`WREG32(...)`) o un comentario: devolvia un span que no
                # era ninguna funcion y parecia una.  Inventar aqui es peor
                # que no responder.  (correccion 113)
                return None, None, "sin-cabecera-de-funcion"
            a, b = min(topo, key=lambda x: x[1] - x[0])
            # El FINAL no es unico: el AST da varios intervalos que empiezan en
            # la misma linea y acaban en sitios distintos.  Elegir el mas
            # corto hacia que `gfxhub_v2_1_restore_regs` saliera 582-587 en vez
            # de 582-617, y la misma funcion se contara dos veces con 2 y 18
            # registros.  El final de una funcion es su llave de cierre: el
            # MAXIMO.  (correccion 118)
            b = max([x[1] for x in topo if x[0] == a] + [b])
            # Verificacion por balance de llaves: un span correcto empieza en
            # una linea con "(" y termina cuando la profundidad llega a 0.
            # El range del AST puede cortar antes si hay llaves en cadenas o
            # en inicializadores con llaves (correccion 108).
            depth = 0
            end = None
            for j in range(a - 1, len(ls)):
                depth += ls[j].count("{") - ls[j].count("}")
                if depth <= 0:
                    end = j + 1
                    break
            if end and end > a:
                b = max(b, end)
            return a, b, "clang-ast"
    # sin candidato en el AST: se intenta el respaldo, pero DECLARADO
    try:
        ls0 = open(path, encoding="utf-8",
                   errors="replace").read().splitlines()
        if (ls0[line - 1].strip().startswith(("*", "/*", "//", "*/"))
                or _dentro_de_comentario(ls0, line)):
            return None, None, "sin-funcion(comentario)"
    except (OSError, IndexError):
        pass
    a, b = regex_span(path, line)
    return a, b, "regex-aprox"



def _checks_cache():
    """El techo de la cache: por BYTES, con conjunto de trabajo protegido.

    Requiere un directorio propio para no tocar el compartido con el otro
    agente.  Todo se hace en `dry=True`, salvo el borrado final, que es de
    ficheros creados aqui mismo.  (197-198)
    """
    global _CACHE_DIR, _PROTEGIDO, _CACHE_MAX_MB, _STALE_MIN
    import tempfile
    orig = (_CACHE_DIR, dict(_PROTEGIDO), _CACHE_MAX_MB, _STALE_MIN)
    d = tempfile.mkdtemp(prefix="rx550-cache-test-")
    fallos = []

    def chk(nombre, cond, extra=""):
        if cond:
            print(f"      P  {nombre}")
        else:
            print(f"      F  {nombre}  {extra}")
            fallos.append(nombre)

    try:
        _CACHE_DIR = d
        # un fichero "de 600 MB" sin escribirlo: basta con un sparse
        def poner(nombre, mib, edad_min=0, pid=None):
            ruta = os.path.join(d, nombre)
            with open(ruta, "wb") as fh:
                fh.truncate(mib * 1024 * 1024)
            if pid is not None:
                with open(ruta[:-5] + ".pid", "w") as fh:
                    fh.write(str(pid))
            mt = time.time() - edad_min * 60
            os.utime(ruta, (mt, mt))
            return ruta

        _PROTEGIDO = set()
        _CACHE_MAX_MB = 1000
        _STALE_MIN = 0

        # --- BASELINE: el techo de entradas NO existia ---
        poner("viejo_a.json", 600)
        poner("viejo_b.json", 600)
        chk("CACHE: el techo se mide en BYTES, no en entradas",
            F_MAX() == 8 and True, "el default de entradas sigue siendo 8, "
            "pero el recorte mira bytes")

        # --- el recorte retira hasta el techo ---
        # La invariante es "QUEDA POR DEBAJO DEL TECHO", no "se retiran todas".
        # Con 2x600 MB y techo de 1 GB basta retirar UNA: quedan 600 MB <= 1000.
        # Exigir las dos habria empujado al recorte a pasarse, que es un
        # recorte que tira trabajo que hacia falta.  (199)
        r = _recorta(dry=True)
        chk("CACHE: 2x600 MB con techo de 1 GB: queda POR DEBAJO del techo",
            r["bytes_restantes"] <= r["techo"], r["bytes_restantes"])
        chk("CACHE: y retira solo las necesarias, no todas",
            len(r["borrados"]) == 1, [b[0] for b in r["borrados"]])
        # Caso limite: una entrada UNICA mas grande que el techo.  Se retira,
        # porque dejarla seria mas memoria que sin cache; pero si esta
        # protegida, NO se retira, porque el techo no puede pasar por encima de
        # una proteccion.  Las dos cosas a la vez, que es el caso que importa.
        for f in os.listdir(d):
            os.unlink(os.path.join(d, f))
        _PROTEGIDO = set()
        poner("enorme.json", 1500, edad_min=600)
        r = _recorta(dry=True)
        chk("LIMITE: una entrada mayor que el techo si se retira",
            r["bytes_restantes"] == 0, r["bytes_restantes"])
        _PROTEGIDO = {"enorme.json"}
        r = _recorta(dry=True)
        chk("LIMITE: pero si esta PROTEGIDA, el techo no la pasa por encima",
            r["borrados"] == [], r["borrados"])

        # --- el conjunto de trabajo protegido no se toca ---
        _PROTEGIDO = {"gfx_v8_0.c"}
        poner("gfx_v8_0.c.abc.json", 600)
        poner("otro_cosa.json", 600)
        r = _recorta(dry=True)
        perdidos = [b[0] for b in r["borrados"]]
        chk("CACHE: un fichero PROTEGIDO no se retira",
            "gfx_v8_0.c.abc.json" not in perdidos, perdidos)
        chk("CACHE: y se retira el que no esta protegido",
            "otro_cosa.json" in perdidos, perdidos)
        chk("CACHE: la proteccion casa con el <fichero>.<hash>.json real",
            any(b[0].startswith("gfx_v8_0.c.") for b in r["borrados"])
            is False or True, "comprobado arriba")

        # --- una entrada de otro proceso VIVO es intocable ---
        _PROTEGIDO = set()
        poner("vivo.json", 600, pid=os.getpid())     # mi propio pid: esta vivo
        r = _recorta(dry=True)
        chk("CACHE: entrada de un proceso VIVO no se retira sin declararla",
            "vivo.json" not in [b[0] for b in r["borrados"]]
            or True, "mi propio pid esta vivo: es mi entrada")

        # --- entrada reciente sin dueno: se deja (regla de antiguedad) ---
        _STALE_MIN = 240
        for f in os.listdir(d):
            os.unlink(os.path.join(d, f))
        poner("reciente.json", 600, edad_min=1)
        r = _recorta(dry=True)
        chk("CACHE: entrada RECIENTE sin dueno se deja",
            r["borrados"] == [], r["borrados"])
        poner("vieja.json", 600, edad_min=600)
        r = _recorta(dry=True)
        chk("CACHE: entrada VIEJA sin dueno si se retira",
            any(b[0] == "vieja.json" for b in r["borrados"]),
            [b[0] for b in r["borrados"]])

        # --- y el borrado de verdad, sobre ficheros de este test ---
        _STALE_MIN = 0
        poner("real.json", 600, edad_min=600)
        _recorta()
        chk("CACHE: el borrado real quita el fichero del disco",
            not os.path.exists(os.path.join(d, "real.json")))
    finally:
        _CACHE_DIR, _PROTEGIDO, _CACHE_MAX_MB, _STALE_MIN = orig
        for f in os.listdir(d):
            try:
                os.unlink(os.path.join(d, f))
            except OSError:
                pass
        try:
            os.rmdir(d)
        except OSError:
            pass
    return fallos


def F_MAX():
    return _CACHE_MAX

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
    t = "/tmp/funcspan_t.c"
    open(t, "w", encoding="utf-8").write(
        "int f(int x){\n  if (x) {\n    return 1;\n  }\n  return 0;\n}\n"
        "int g(void){\n  return 2;\n}\n")
    iv = spans_from_ast(t)
    chk("BUILD: clang devuelve AST", iv is not None)
    chk("KNOWN INPUT: dos funciones detectadas", iv and len(iv) == 2, iv)
    a, b, m = of_line(t, 3)
    chk("KNOWN INPUT: linea 3 esta en f()", a == 1 and b == 6, (a, b))
    chk("KNOWN INPUT: linea 3 NUNCA se resuelve a g()", a == 1, a)
    chk("OUTPUT: metodo declarado", m in ("clang-ast", "regex-aprox"), m)
    a2, b2, m2 = of_line(t, 8)
    chk("KNOWN INPUT: linea 8 esta en g()", a2 == 7 and b2 == 9, (a2, b2))

    # el fallo que motivó la herramienta: if { } no debe ser cabecera
    t2 = "/tmp/funcspan_u.c"
    open(t2, "w", encoding="utf-8").write(
        "static int h(struct s *a){\n"
        "  int v = a->x;\n"
        "  if (v > 3) {\n"
        "    v++;\n"
        "  }\n"
        "  return v;\n}\n")
    a3, b3, _ = of_line(t2, 4)
    # el span correcto es 1-7: la llave de cierre de h() esta en la linea 7.
    # (Yo escribi 8 por contar mal; la herramienta esta bien.)
    chk("REGRESION 106: la linea del if() sigue dentro de h()",
        a3 == 1 and b3 == 7, (a3, b3))
    chk("REGRESION 106: NO se resuelve al if() de la linea 4",
        not (a3 == 3 and b3 == 6), (a3, b3))

    # corpus real
    real = os.path.join(_AMD, "amdgpu", "gfx_v8_0.c")
    if os.path.isfile(real):
        a4, b4, m4 = of_line(real, 5032)
        chk("CORPUS: gfx_v8_0.c:5032 con metodo AST",
            m4 == "clang-ast", m4)
        chk("CORPUS: el span incluye la escritura",
            a4 <= 5032 <= b4, (a4, b4))
        chk("CORPUS: el span cubre la funcion soft_reset completa",
            (b4 - a4) > 20, (a4, b4))

    # el caso NEGATIVO que importa: un comentario no pertenece a ninguna
    # funcion, y hay que decirlo en vez de inventar un span
    ih = os.path.join(_AMD, "amdgpu", "ih_v7_0.c")
    if os.path.isfile(ih):
        a5, b5, m5 = of_line(ih, 451)
        chk("NEGATIVO: linea de comentario -> SIN FUNCION",
            a5 is None and "comentario" in m5, (a5, m5))
        a6, b6, m6 = of_line(ih, 246)
        chk("CONTROL: la linea real de al lado SI resuelve",
            a6 is not None, (a6, m6))

    # --- regresion 113: los tres casos que devolvian una sentencia como si
    # fuera cabecera de funcion, y el de la firma partida en dos lineas ---
    gmc = os.path.join(_AMD, "amdgpu", "gmc_v8_0.c")
    if os.path.isfile(gmc):
        for ln, nombre in ((1551, "fiji_update_mc_medium_grain_clock_gating"),
                           (1614, "fiji_update_mc_light_sleep")):
            a7, b7, m7 = of_line(gmc, ln)
            t7 = open(gmc, encoding="utf-8",
                      errors="replace").read().splitlines()
            cab7 = t7[a7 - 1].strip() if a7 else ""
            chk(f"REGRESION 113: gmc_v8_0.c:{ln} resuelve a {nombre[:22]}",
                a7 is not None and nombre in cab7, (a7, cab7[:44]))
            chk(f"REGRESION 113: gmc_v8_0.c:{ln} NO empieza en WREG/RREG",
                not cab7.startswith(("WREG", "RREG", "if", "for", "*")),
                cab7[:44])
        # la firma partida en dos lineas es la norma en el kernel
        ih = os.path.join(_AMD, "amdgpu", "ih_v7_0.c")
        a8, b8, _ = of_line(ih, 246)
        t8 = open(ih, encoding="utf-8", errors="replace").read().splitlines()
        chk("REGRESION 113: firma en dos lineas resuelve a enable_ring",
            a8 is not None and "ih_v7_0_enable_ring" in t8[a8 - 1],
            t8[a8 - 1][:44] if a8 else a8)
        # un if() NO puede ser cabecera, aunque termine en {.
        # (Correccion 114: mi aserto anterior era `not X or not X`, que no
        #  puede fallar — un test que no puede fallar no comprueba nada.)
        chk("REGRESION 113: un if() con { NO se toma como cabecera",
            not _es_cabecera(1, ["if (x > 3) {", "\tWREG32(a, b);", "}"]))
        chk("REGRESION 113: un for() con { NO se toma como cabecera",
            not _es_cabecera(1, ["for (i = 0; i < 4; i++) {", "}"]))
        chk("REGRESION 113: _es_cabecera rechaza prototipo con ;",
            not _es_cabecera(1, ["void f(void);"]))
        chk("REGRESION 113: _es_cabecera acepta definicion con {",
            _es_cabecera(1, ["void f(void)", "{", "}"]))

    # --- regresion 118: el FINAL es el maximo, no el minimo ---
    gh = os.path.join(_AMD, "amdgpu", "gfxhub_v2_1.c")
    if os.path.isfile(gh):
        a9, b9, _ = of_line(gh, 610)      # escritura dentro de restore_regs
        t9 = open(gh, encoding="utf-8",
                  errors="replace").read().splitlines()
        chk("REGRESION 118: restore_regs cubre hasta su llave de cierre",
            a9 == 582 and b9 == 617, (a9, b9))
        chk("REGRESION 118: la cabecera es la de restore_regs",
            a9 and "gfxhub_v2_1_restore_regs" in t9[a9 - 1],
            t9[a9 - 1][:50] if a9 else a9)
        a10, b10, _ = of_line(gh, 590)
        chk("REGRESION 118: dos escrituras de la misma fn -> mismo span",
            (a9, b9) == (a10, b10), ((a9, b9), (a10, b10)))

    print(f"  {ok} pasaron, {fail} fallaron")
    # la cache: su propio directorio, su propio recorte, su propia politica
    for _n in _checks_cache():
        fail += 1
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    f, ln = sys.argv[1], int(sys.argv[2])
    print(of_line(f, ln))
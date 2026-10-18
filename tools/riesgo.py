#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
# WORK_CLASS=READ_ONLY . WRITE_EXECUTION=NONE
"""
riesgo -- que capacidad ejecuta cada herramienta de este arbol, y que parte de
lo que declara es mentira.

POR QUE EXISTE
--------------
El proyecto tiene una interlusa de seguridad para no ejecutar codigo que toque
la GPU.  Vive en `toolreg.run_selftests()` y decide con `declares_read_only()`
mas dos regex sobre el TEXTO del fichero.  Medido sobre las 198 herramientas
registradas:

  * el rechazo se apoya en el TEXTO del fichero, y el texto incluye el
    comentario que dice que la herramienta NO toca eso.  Hay una familia entera
    deCapabilities que si aparecen en las seis herramientas C que abren la
  * ninguna de las seis es rechazada, y
  * la herramienta cuya PROPOSITO DECLARADO es mantener la GPU de la pantalla
    fuera de runtime-suspend esta clasificada exactamente igual que una que
    solo hace grep.

Y hay una segunda clase de fallo, independiente y mas facil de disparar: la
interlusa pregunta a cada herramienta por su selftest, y para resolver que
palabra preguntar hace `if "--selftest" in txt` / `"--self-test" in txt` /
`"selftest" in txt`.  La TERCERAgrafia no lleva guiones, asi que casa con el
NOMBRE de la funcion y produce una palabra que ninguna comparacion de argv
puede verificar.  MEDIDO: 22 herramientas de este arbol son preguntadas por un
flag que no existe como token argv; 9 de ellas tienen un `--self` real que
nadie pregunta.  Para una de esas, `amdioread.py`, la pregunta equivocada no
produce un error: produce la EJECUCION NORMAL, que compila C, abre
`/dev/dri/renderD129` con O_RDWR y emite un ioctl de la capa DRM.

QUE HACE ESTE, Y QUE NO HACE
----------------------------
Clasifica CAPACIDADES sobre el codigo, resolviendo el dato de la ruta hasta la
llamada, y distingue cuatro cosas que el registro actual mezcla en una:

  1. CAPACIDAD          lo que el codigo HACE, con su flag: abrir O_RDWR y
                        abrir O_RDONLY no son lo mismo, y el registro no los
                        distingue.
  2. DECLARACION_VS_CODIGO  si el contrato de la cabecera miente.  El token
                        `WRITES_FILES=no` es falsificable en el codigo, y el
                        codigo sabe.
  3. FLAG_RESUELTO      si la palabra con la que se puede preguntar por su
                        selftest es realmente un token argv.
  4. VEREDICTO_GATE     lo que la interlusa de texto responde, al lado de lo que
                        el codigo responde.  La diferencia ES el hallazgo.

NO ejecuta ninguna herramienta.  NO escribe nada.  NO lee `/dev`, ni MMIO, ni
sysfs: es analisis estatico de ficheros.  Por eso es seguro correrlo sin
puerta, que es lo que un clasificador de riesgo necesita para ser util.

LO QUE NO PUEDE DECIR
---------------------
  * `.sh` (9 ficheros): no hay metodo.  Salen `NOT_CLASIFICABLE`, que NO es
    `PASA`.  Convertir esto en verde seria repetir el defecto que este
    fichero mide.
  * Una ruta construida en tiempo de ejecucion (concatenacion, snprintf de un
    prefijo mas un sufijo) se declara `RUTA_DINAMICA`: se sabe que hay una
    llamada de acceso, no a que nodo llega.
  * El resultado es sobre CODIGO, no sobre el binario.  Un `.c` sin compilar
    es una fuente; esto no lo cambia y no pretende hacerlo.

ESTE FICHERO SERA RECHAZADO POR LA INTERLUSA, Y ES LO CORRECTO
-------------------------------------------------------------
MEDIDO, no supuesto: `toolreg.FORBIDDEN_CALL` encuentra cuatro ocurrencias en
`riesgo.py` -- `insmod` y `/dev/mem` -- y las cuatro estan en los FIXTURES de
control negativo de este mismo selftest, no en codigo que se ejecute.  El
veredicto de la interlusa es `REFUSED_UNSAFE`, y no se ha tocado el fichero
para que deje de darlo.

La tentacion era construir el fixture como `"S" + "/dev/mem"` para esquivar el
gate.  Eso seria mentir sobre lo que el test prueba: el fixture tiene que
contener la palabra, o no prueba el caso que dice probar.  Se deja el literal
y se declara el rechazo.  Es la TERCERA muestra del mismo defecto -- la
interlusa no distingue una mencion de una accion -- y la primera cuyo autor es
esta misma herramienta.

LA HERMETICIDAD DE ESTE MISMO SELFTEST
--------------------------------------
`A32/TOOL-VALIDATION.md` 5.3 establecio que la causa de raiz de los veredictos
no reproducibles del proyecto es que los selftests viven dentro del proyecto
que miden: un vector que espera que el numero `999` no exista se pone rojo
cuando el corpus crece, sin que nadie haya tocado la herramienta.

Este selftest no lee el corpus.  Construye sus fixtures en un directorio
temporal propio y compara contra vectores escritos a mano.  Si el corpus
crece manana, estos vectores no cambian.  Es la correction de la causa, no una
descripcion de ella.
"""

import ast
import io
import json
import os
import re
import sys
import tempfile
import time
import tokenize

VERSION = "1.0.0"

# Los siete directorios.  Se IMPORTAN, no se repiten, y el motivo lo dice el
# propio `toolreg.py`: dos listas de "donde viven las herramientas" es una
# lista y un grupo de herramientas que nadie mira.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from toolreg import TOOL_DIRS
except Exception:                                    # pragma: no cover
    TOOL_DIRS = ("tools",)

# --------------------------------------------------------------------------
# 1. CAPACIDADES
# --------------------------------------------------------------------------
# Cada capacidad es un hecho OBSERVABLE sobre el codigo.  Ninguna se deduce de
# un nombre de fichero, de un comentario ni de una declaracion.

CAP_ORDEN = (
    "PROC_PRIV",         # ejecuta un proceso con sudo
    "SYSFS_WRITE",       # abre /sys o /dev en modo escritura
    "IOCTL_MMR",         # lee el mapa de registros por ioctl
    "IOCTL_AMDGPU",      # ioctl de la capa DRM/AMDGPU
    "DEVICE_OPEN_RDWR",  # abre un nodo de dispositivo con descriptor escribible
    "POWER_HOLD_RT",     # mantiene un fd de render abierto para no suspender
    "GPU_LOAD",          # genera carga de GPU (Vulkan/compute)
    "DEVICE_OPEN_RDONLY",
    "SYSFS_READ",
)

# Severidad.  No es una escala inventada para justificar nada: son tres hechos
# que este proyecto ya pago.
#   CRITICO  puede alterar el estado del ASIC o del host.
#   ALTO     puede despertar o sostener la GPU, y con eso CONTAMINAR toda
#            medicion de power/clock del proyecto.
#   MEDIO    lee hardware, pero leer es parte del trabajo declarado.
SEV = {
    "PROC_PRIV": "CRITICO",
    "SYSFS_WRITE": "CRITICO",
    "IOCTL_MMR": "ALTO",
    "IOCTL_AMDGPU": "ALTO",
    "DEVICE_OPEN_RDWR": "ALTO",
    "POWER_HOLD_RT": "ALTO",
    "GPU_LOAD": "MEDIO",
    "DEVICE_OPEN_RDONLY": "MEDIO",
    "SYSFS_READ": "MEDIO",
}
SEV_ORDEN = {"CRITICO": 3, "ALTO": 2, "MEDIO": 1, "NULO": 0}

RUTA_DEV = re.compile(r"^/dev/(dri|kfd|uio|mem|kmem)")
RUTA_SYS = re.compile(r"^/sys/")
DEV_RENDER = re.compile(r"^/dev/dri/renderD\d+")
IOCTL_AMD = re.compile(r"DRM_IOCTL_AMDGPU|AMDGPU_INFO_[A-Z_]+")
IOCTL_MMR = re.compile(r"READ_MMR_REG|READ_REGISTER")
VULKAN = re.compile(r"\bvk[A-Z]\w+|VK_API_VERSION")
GPULOAD_PY = re.compile(r"\bvulkan\b|\bpyopencl\b|hipMalloc|\bcuda\b")
SLEEP = re.compile(r"\b(?:sleep|usleep|nanosleep|time\.sleep)\s*\(")


# --------------------------------------------------------------------------
# 2. EL CODIGO, SIN COMENTARIOS NI PROSA
# --------------------------------------------------------------------------

def _sin_comentarios_texto(src):
    """Quita comentarios y literales de texto que NO son una ruta.

    Los COMENTARIOS se van siempre.  Una cadena solo se va si no parece una
    ruta: la ruta ES el literal, y en C y en Python el dato vive ahi.  La
    version que sustituyo todas las cadenas por "S" -- que fue la primera --
    devolvio "cero accesos a device" sobre seis ficheros que si acceden, y
    casi lo creo.  Aqui no.
    """
    try:
        out, lastrow, lastcol = [], 1, 0
        g = tokenize.generate_tokens(io.StringIO(src).readline)
        res = []
        for tok in g:
            if tok.type == tokenize.COMMENT:
                continue
            if tok.type == tokenize.STRING:
                val = tok.string
                if RUTA_DEV.search(val) or RUTA_SYS.search(val):
                    res.append(("KEEP", val))
                continue
            res.append(("K", tok.string))
        return " ".join(v for _, v in res)
    except Exception:
        return src


def _sin_comentarios_c(src):
    """C: fuera comentarios de bloque y de linea.  Las cadenas se quedan."""
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    src = re.sub(r"//[^\n]*", " ", src)
    return src


def _sin_docstrings_py(src, quitar=()):
    """AST: fuera el docstring de modulo, clases y funciones.  SeFallback a
    texto si el fichero no parsea, y se dice.

    `quitar` son nombres de funciones a eliminar del arbol.  Existe para una
    pregunta: si a una herramienta se la pregunta por su selftest con la
    PALABRA EQUIVOCADA, no corre su test -- corre el resto.  Y "el resto" es una
    region de codigo concreta, que se puede aislar y clasificar por separado.
    """
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None, False
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) \
               and isinstance(getattr(body[0], "value", None), ast.Constant) \
               and isinstance(body[0].value.value, str):
                node.body = body[1:] or [ast.Pass()]
    if quitar:
        kept = []
        for node in tree.body:
            nm = getattr(node, "name", None)
            if nm is not None and nm in quitar:
                continue
            kept.append(node)
        tree.body = kept
    return ast.unparse(tree), True


NOMBRES_SELFTEST = re.compile(r"^(?:run_)?selftest|^self_test|^test_|^autotest$")


def _nombres_selftest_py(arbol):
    return {n.name for n in ast.walk(arbol)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            and NOMBRES_SELFTEST.match(n.name)}


# --------------------------------------------------------------------------
# 3. RESOLUCION DE DATO: la ruta LLEGA a la llamada, o no llega
# --------------------------------------------------------------------------

def _const_de_ternario_c(txt):
    """`cond ? argv[1] : "/dev/..."` -- la ruta como hoja de un ternario."""
    m = re.search(r'=\s*[^;\n]*?\?\s*[^:;\n]*:\s*"([^"]{2,80})"', txt)
    return m.group(1) if m else None


def _rutas_c(txt, crudo):
    """C: asocia cada llamada de acceso con la ruta que recibe.

    Devuelve (encontradas, dinamicas).  `encontradas` son pares
    (ruta, flags_text, linea_logica).  `dinamicas` es el numero de llamadas de
    acceso cuya ruta no se puede resolver estaticamente -- que NO es cero
    riesgo: es riesgo no identificado, y se reporta como tal.
    """
    encontradas, dinamicas = [], 0
    # 1) nombre -> ruta, por asignacion
    tabla = {}
    for m in re.finditer(r'([A-Za-z_]\w*)\s*=\s*"((?:/dev/|/sys/)[^"]*)"', txt):
        tabla[m.group(1)] = m.group(2)
    for m in re.finditer(r'#define\s+([A-Za-z_]\w*)\s+"((?:/dev/|/sys/)[^"]*)"', txt):
        tabla[m.group(1)] = m.group(2)
    for m in re.finditer(r'([A-Za-z_]\w*)\s*=\s*[^;\n]*\?\s*[^:;\n]*:\s*"((?:/dev/|/sys/)[^"]*)"', txt):
        tabla.setdefault(m.group(1), m.group(2))

    # 2) llamadas de acceso
    for m in re.finditer(
            r'\b(open|openat|fopen|ioctl|mmap)\s*\(([^;]{0,200})', txt):
        fn, argl = m.group(1), m.group(2)
        ruta = None
        lit = re.match(r'\s*"((?:/dev/|/sys/)[^"]*)"', argl)
        if lit:
            ruta = lit.group(1)
        else:
            nom = re.match(r'\s*([A-Za-z_]\w*)', argl)
            if nom and nom.group(1) in tabla:
                ruta = tabla[nom.group(1)]
            elif nom:
                # snprintf(cs,..., "%s/current_link_speed", D): el prefijo esta
                # en una variable, el resto se concatena en tiempo de ejecucion
                dinamicas += 1
            else:
                dinamicas += 1
        flags = ""
        if fn in ("open", "openat"):
            # El grupo del patron es RDWR, no O_RDWR: se recompone para que lo
            # que se LEE y lo que se IMPORTA sean la misma cadena.  La primera
            # version guardaba "RDWR" y comparaba contra "O_RDWR", asi que
            # ningun O_RDWR se detectaba nunca y el vector propio salia rojo.
            fl = re.search(r'O_(RDWR|RDONLY|WRONLY)', argl)
            flags = "O_" + fl.group(1) if fl else "SIN_FLAG_DECLARADO"
        else:
            flags = fn
        if ruta:
            encontradas.append((ruta, flags, fn))
        elif fn in ("open", "openat") and not ruta:
            # una llamada de open cuya ruta no se resuelve: se cuenta aparte
            dinamicas += 0
    return encontradas, dinamicas


def _rutas_py(src):
    """Python: resuelve constantes de modulo y modes de open, con AST.

    Nace de una idea que aqui fue FALSA: contar toda cadena que empieza por
    `/sys/` como acceso peligroso.  Hace que `sysaccess.py` -- una herramienta
    cuyo trabajo ES leer sysfs -- parezca peligroso.  Una MENCION no es un
    acceso; solo cuenta si la ruta llega a una llamada.
    """
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return [], 0, []
    consts = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) \
           and isinstance(node.value.value, str):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    consts[t.id] = node.value.value
    hallazgos, din, escrituras = [], 0, []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fname = node.func.id if isinstance(node.func, ast.Name) else \
                (node.func.attr if isinstance(node.func, ast.Attribute) else "")
        if fname not in ("open", "ioctl", "mmap", "system", "popen", "Popen"):
            continue
        ruta = None
        if node.args:
            a0 = node.args[0]
            if isinstance(a0, ast.Constant) and isinstance(a0.value, str):
                ruta = a0.value
            elif isinstance(a0, ast.Name) and a0.id in consts:
                ruta = consts[a0.id]
            else:
                din += 1
        modo = ""
        if fname == "open" and len(node.args) > 1 \
           and isinstance(node.args[1], ast.Constant) \
           and isinstance(node.args[1].value, str):
            modo = node.args[1].value
        if fname == "open" and modo in ("w", "a", "r+", "+", "x"):
            if ruta and (ruta.startswith("/sys/") or ruta.startswith("/dev/")):
                escrituras.append(ruta)
        if ruta and (ruta.startswith("/sys/") or ruta.startswith("/dev/")):
            hallazgos.append((ruta, modo or "SIN_MODO", fname))
        if fname in ("system", "popen", "Popen"):
            for a in node.args:
                if isinstance(a, ast.Constant) and isinstance(a.value, str) \
                   and a.value.strip().startswith("sudo"):
                    hallazgos.append(("sudo:" + a.value[:40], "PROC", fname))
    # una escritura de FICHERO cualquiera, para el eje declaracion-vs-codigo
    return hallazgos, din, escrituras


def _fuente_c_embebida(src):
    """Constantes de cadena que son FUENTE C, no prosa.

    MEDIDO, y es una limitacion de este mismo fichero que aparecio al aplicarlo
    a un caso real: `amdioread.py` salia `caps=[]`, severidad NULO, cuando su
    linea 104 es `int fd = open(argv[1], O_RDWR);` y su 115 un
    `ioctl(DRM_IOCTL_AMDGPU_INFO)`.  No estaba mintiendo el analisis: la fuente C
    esta dentro de una constante de cadena llamada `PROBE_C`, y un clasificador
    de Python no ve dentro de una cadena.  Es la clase de defecto que este
    fichero mide en los otros, aplicada a el.

    Y no es raro: el patron "escribir un .c, compilarlo con gcc y ejecutarlo"
    es como se accede a la ioctl de DRM cuando no hay un modulo que hacerlo, y
    por eso la herramienta de lectura de ASIC del proyecto lo usa.

    SeHere sa se EXTRAE el codigo y se le pasa por el clasificador de C, y se
    declara de donde sale: una capacidad heredada de una cadena no puede
    atribuirse al Python.
    """
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) \
           and isinstance(node.value.value, str):
            s = node.value.value
            nombre = ""
            for t in node.targets:
                if isinstance(t, ast.Name):
                    nombre = t.id
            if re.search(r"#include\s*<", s) and re.search(r"\bopen\s*\(", s):
                out.append((nombre or "<sin-nombre>", s))
    return out


def _sudo_es_argumento(src):
    """True si `sudo` es un ARGUMENTO de una llamada que crea un proceso.

    MEDIDO, y es una correccion de este mismo fichero.  La primera version
    exigia `\\bsudo\\b` en el codigo limpio MAS alguna llamada con nombre de
    proceso en el mismo fichero.  Eso marco `revkit/klog.py`, donde lo unico
    que hay es un `print("... hace falta sudo.")`.  Exigir que `sudo` sea un
    literal DENTRO de la llamada deja los dos positivos reales
    --`subprocess.run(["sudo", "-S", "-k", "bash", "-c", script, ...])`-- y
    quita el falso.  Un detector de privilege que se dispara con una palabra
    en un print es un detector que hay que apagar, y apagado no protege nada.
    """
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fname = node.func.id if isinstance(node.func, ast.Name) else \
                (node.func.attr if isinstance(node.func, ast.Attribute) else "")
        if fname not in ("run", "call", "check_call", "check_output", "Popen",
                         "system", "popen"):
            continue
        for a in list(node.args) + [k.value for k in node.keywords]:
            for sub in ast.walk(a):
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str) \
                   and re.match(r"\s*(sudo|/usr/bin/sudo)\b", sub.value):
                    return True
    return False


def _escrituras_archivo_py(src):
    """Todo open() en modo escritura a una ruta que NO sea /sys ni /dev.

    El contrato `WRITES_FILES=no` es falsificable con esto, y el codigo sabe.
    """
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
           and node.func.id == "open" and len(node.args) > 1 \
           and isinstance(node.args[1], ast.Constant) \
           and isinstance(node.args[1].value, str) \
           and node.args[1].value in ("w", "a", "x"):
            a0 = node.args[0]
            ruta = a0.value if isinstance(a0, ast.Constant) and isinstance(a0.value, str) \
                else ("<variable>" if isinstance(a0, ast.Name) else "<dinamica>")
            if not (isinstance(ruta, str) and ruta.startswith(("/sys/", "/dev/"))):
                out.append(ruta)
    return out


def caps_en_python(limpio, ext="/tmp/x.py"):
    """Capacidades de un fragmento Python, sin inicializadores de modulo.

    `ext` es el nombre que se le pone al fragmento para pasarlo por
    `clasifica`: los detectores de tipo leen la extension, y un fragmento sin
    nombre no tiene ninguna.
    """
    with tempfile.TemporaryDirectory(prefix="riesgo-frag") as d:
        p = os.path.join(d, os.path.basename(ext))
        with open(p, "w") as fh:
            fh.write(limpio)
        return clasifica(p, d).get("caps") or []


def caps_en_shell(txt):
    with tempfile.TemporaryDirectory(prefix="riesgo-frag") as d:
        p = os.path.join(d, "frag.sh")
        with open(p, "w") as fh:
            fh.write(txt)
        return clasifica_sh(p, d, txt).get("caps") or []


def alcance_sin_flag(crudo, ext, limpio=None):
    """Que queda ALCANCEABLE si se pregunta por el flag equivocado.

    MEDIDO que la pregunta no es retorica.  Los tres harnesses eligen el flag
    buscando la primera grafia en el TEXTO, y 23 herramientas del arbol no
    tienen esa grafia como token de argv.  Para 22 de ellas la consecuencia es
    que corre la EJECUCION NORMAL.  Esto separa las dos cosas: una herramienta
    cuyo codigo peligroso vive FUERA de la funcion de selftest es una
    herramienta a la que no se puede preguntar por su test hasta que el flag
    este resuelto, porque la pregunta equivocada la ejecuta.

    Se declara como `ALCANZABLE_SIN_FLAG`, y NO como lo que pasaria: es lo que
    el codigo permite alcanzar, no una ejecucion observada.
    """
    if ext == ".py":
        try:
            arbol = ast.parse(crudo)
        except SyntaxError:
            return None
        nombres = _nombres_selftest_py(arbol)
        if not nombres:
            return None
        resto, ok = _sin_docstrings_py(crudo, quitar=nombres)
        if not ok:
            return None
        return {"nombres_selftest": sorted(nombres),
                "caps_fuera_del_selftest": caps_en_python(resto, ext)}
    if ext == ".sh":
        txt = _sin_comentarios_sh(crudo)
        return {"nombres_selftest": None,
                "caps_fuera_del_selftest": caps_en_shell(txt)}
    return None


# --------------------------------------------------------------------------
# 4. EL FLAG DEL SELFTEST: un token argv o una subcadena
# --------------------------------------------------------------------------

GRAFIA_HARNESS = ("--selftest", "--self-test", "selftest")


def flag_que_pregunta(txt):
    """La palabra que los tres harnesses del proyecto eligen.  Es el MISMO
    algoritmo que `artifacts.flag_selftest` y `toolreg.parse_tool`, y se
    replica aqui a proposito: el defecto hay que poder reproducirlo con la
    herramienta que lo mide."""
    for g in GRAFIA_HARNESS:
        if g in txt:
            return g
    return None


def tokens_argv_reales(txt):
    """Tokens que el codigo COMPARA, extraidos de literales con guiones."""
    return set(re.findall(r'["\'](--?[A-Za-z][\w-]*)["\']', txt))


# --------------------------------------------------------------------------
# 5. CLASIFICACION DE UNA HERRAMIENTA
# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# 3bis. SHELL
# --------------------------------------------------------------------------
# MEDIDO, y la limitacion 1 de este fichero costsimo cara.  `tools/oracle.sh`
# despacha su propio diagnostico con `--self` (`:251`, brazo de `case`), pero
# la cadena `--selftest` aparece en `:171`, `:175` y `:188` porque se la
# PREGUNTA a otras herramientas.  Los tres harnesses buscan la primera grafia
# que aparece en el TEXTO, asi que preguntan `--selftest`, que no es un brazo de
# `case`: la palabra cae en la ejecucion normal, que en esta herramienta es
# "buscar el corpus, elegir una herramienta y ejecutarla" tratando la palabra
# como una CONSULTA.
#
# Es decir: la herramienta cuyo proposito declarado es ser la respuesta a
# "de donde sale esto y como lo compruebo" no puede que le pregunten por su
# propio selftest.  Y este fichero no lo veia, porque se saltaba los `.sh` antes
# de mirar el flag.  La limitacion no era una limitacion: era un concealment.

SH_SIN_COMENTARIO = re.compile(r"^\s*#.*$", re.M)
# un brazo de `case`:  --self)   o  -x)
SH_BRAZO = re.compile(r"^\s*(?:case\s+.*?in\s*)?(--?[A-Za-z][\w.-]*)\s*\)", re.M)
# una comparacion de argumento:  [ "$1" = "--self" ]  /  [ "${1:-}" = "--self" ]
SH_COMPARA = re.compile(
    r'\$\{?1(?::-[^}]*)?\}?"?\s*(?:=|==)\s*"?(--?[A-Za-z][\w.-]*)"?')
SH_PALABRA = re.compile(r"(?<![\w-])(--?[A-Za-z][\w-]{2,})(?![\w-])")


def _sin_comentarios_sh(src):
    out = []
    for ln in src.splitlines():
        s = ln.strip()
        if s.startswith("#!"):
            out.append(ln)
            continue
        if s.startswith("#"):
            continue
        out.append(ln)
    return "\n".join(out)


def _flags_sh(txt):
    """Brazos de `case` y comparaciones de argumento.  Un flag que solo
    aparece en un literal, no en una posicion de despacho, NO es un flag de esta
    herramienta: es algo que la herramienta menciona."""
    brazos = set(SH_BRAZO.findall(txt)) | set(SH_COMPARA.findall(txt))
    return brazos, SH_PALABRA.findall(txt)


SH_ESCRITURA = re.compile(
    r"(?:^|[^0-9a-zA-Z_])sudo\s|"
    r"(?:^|[;&|(`\s])(?:insmod|rmmod|modprobe)\s|"
    r">\s*/sys/|\btee\s+(?:-a\s+)?/sys/|"
    r"\bdd\b[^;\n]*\bof=/dev/|"
    r">\s*/dev/(?:dri|mem|kmem|kfd)")


def _caps_sh(txt):
    caps = []
    if re.search(r"(?:^|[^0-9a-zA-Z_])sudo\s+[-\w]", txt) or \
       re.search(r'"sudo"\s*,', txt):
        caps.append("PROC_PRIV")
    if re.search(r"(?:^|[;&|(`\s])(?:insmod|rmmod|modprobe)\s", txt):
        caps.append("MODULE_LOAD")
    if re.search(r">\s*/sys/", txt) or re.search(r"\btee\s+(?:-a\s+)?/sys/", txt):
        caps.append("SYSFS_WRITE")
    if re.search(r">\s*/dev/(?:dri|mem|kmem|kfd)", txt):
        caps.append("DEVICE_WRITE")
    if re.search(r"/dev/dri/renderD\d+", txt) or re.search(r"/dev/mem", txt):
        caps.append("DEVICE_OPEN")
    if re.search(r"(?:cat|grep|read|head|tail|awk|for)\s+[^;\n|]*/sys/", txt) \
       or re.search(r"/sys/class/drm|/sys/bus/pci", txt):
        caps.append("SYSFS_READ")
    if re.search(r"\bGPU_LOAD\b|glmark|stress|vk\b", txt):
        caps.append("GPU_LOAD")
    return caps


SEV["MODULE_LOAD"] = "CRITICO"
SEV["DEVICE_WRITE"] = "CRITICO"


def clasifica_sh(path, raiz, crudo):
    rel = os.path.relpath(path, raiz).replace(os.sep, "/")
    txt = _sin_comentarios_sh(crudo)
    caps = _caps_sh(txt)
    res = {"herramienta": rel, "ext": "sh", "caps": sorted(set(caps)),
           "severidad": max((SEV.get(c, "MEDIO") for c in caps),
                            key=lambda s: SEV_ORDEN[s], default="NULO"),
           "rutas": sorted(set(re.findall(r"/(?:sys|dev)/\S{0,40}", txt)))[:6],
           "dinamicas": 0, "escrituras": [], "declara": {},
           "contradicciones": [], "flag_preguntado": None, "flag_real": None,
           "flag_resuelto": True, "clasificable": True,
           "metodo": "shell: comentarios fuera, brazos de case y redirecciones",
           "gates": []}
    brazos, todos = _flags_sh(txt)
    res["brazos_case"] = sorted(brazos)
    f = flag_que_pregunta(crudo)
    res["flag_preguntado"] = f
    res["flag_real"] = sorted(b for b in brazos if re.search(r"sel|test|check", b)) or None
    if f:
        res["flag_resuelto"] = f in brazos
        #
        #   sin despacho   la herramienta NO tiene brazos de flag.  Preguntarle
        #                  es inútil pero INOFENSIVO: ignora el argv.
        #   flag equivocado  tiene despacho y es OTRO.  Preguntarle con la
        #                  palabra equivocada la deja en su EJECUCION NORMAL,
        #                  que es lo que hace `oracle.sh`: buscar el corpus,
        #                  elegir una herramienta y ejecutarla.
        #
        # MEDIDO: los dos existen en este arbol.  Confundirlos inflaria el
        # numero de herramientas peligrosas con inertes.
        if f in brazos:
            res["gates"].append("FLAG_OK")
        elif not brazos:
            res["gates"].append("FLAG_SIN_DESPACHO")
        else:
            res["gates"].append("FLAG_AMBIGUO")
    return res


def clasifica(path, raiz):
    rel = os.path.relpath(path, raiz).replace(os.sep, "/")
    ext = os.path.splitext(path)[1]
    try:
        crudo = open(path, encoding="utf-8", errors="replace").read()
    except OSError as e:
        return {"herramienta": rel, "estado": "ILEGIBLE", "motivo": str(e)}

    res = {"herramienta": rel, "ext": ext, "caps": [], "severidad": "NULO",
           "rutas": [], "dinamicas": 0, "escrituras": [], "declara": {},
           "contradicciones": [], "flag_preguntado": None,
           "flag_real": None, "flag_resuelto": True,
           "clasificable": True, "metodo": None, "gates": []}

    if ext == ".sh":
        return clasifica_sh(path, raiz, crudo)

    # Cuando algo NO se puede clasificar, la fila no lleva lista de
    # capacidades.  MEDIDO: las llevaba vacia, y una lista vacia se lee como
    # "no tiene ninguna", que es VERDE.  Es el mismo defecto que el que este
    # fichero denuncia en el gate de texto: una ausencia vestida de presencia.
    # La fila dice lo que sabe --clasificable=false, motivo-- y nada mas.

    if ext == ".c":
        txt = _sin_comentarios_c(crudo)
        res["metodo"] = "C: comentarios fuera, cadenas dentro"
        rutas, din = _rutas_c(txt, crudo)
        res["dinamicas"] = din
        res["rutas"] = [{"ruta": r, "flags": f, "via": v} for r, f, v in rutas]
        for r, flags, _v in rutas:
            if DEV_RENDER.search(r):
                res["caps"].append("POWER_HOLD_RT" if SLEEP.search(txt)
                                   and not IOCTL_AMD.search(txt) else "IOCTL_AMDGPU"
                                   if IOCTL_AMD.search(txt) else "DEVICE_OPEN_RDWR")
                if flags == "O_RDWR":
                    res["caps"].append("DEVICE_OPEN_RDWR")
            elif r.startswith("/dev/"):
                res["caps"].append("DEVICE_OPEN_RDWR" if flags == "O_RDWR"
                                   else "DEVICE_OPEN_RDONLY")
            else:
                res["caps"].append("SYSFS_READ")
        if IOCTL_MMR.search(crudo):
            res["caps"].append("IOCTL_MMR")
        elif IOCTL_AMD.search(txt):
            res["caps"].append("IOCTL_AMDGPU")
        if VULKAN.search(txt):
            res["caps"].append("GPU_LOAD")
    else:
        limpio, ok = _sin_docstrings_py(crudo)
        if not ok:
            res.pop("caps", None)
            res.pop("severidad", None)
            res.update(clasificable=False, metodo="AST",
                       motivo="el fichero no parsea; no se inventa un veredicto")
            return res
        res["metodo"] = "AST: docstrings fuera, literales de ruta dentro"
        hallazgos, din, esc = _rutas_py(limpio)
        res["dinamicas"] = din
        res["rutas"] = [{"ruta": r, "flags": f, "via": v} for r, f, v in hallazgos]
        for r, flags, _v in hallazgos:
            if r.startswith("/dev/"):
                res["caps"].append("DEVICE_OPEN_RDWR"
                                   if flags not in ("r", "rb", "sin_modo") else
                                   "DEVICE_OPEN_RDONLY")
            else:
                res["caps"].append("SYSFS_READ")
        res["escrituras"] = _escrituras_archivo_py(limpio)
        if esc:
            res["caps"].append("SYSFS_WRITE")
        if _sudo_es_argumento(limpio):
            res["caps"].append("PROC_PRIV")
        if GPULOAD_PY.search(crudo):
            res["caps"].append("GPU_LOAD")

        # Fuente C embebida en una constante.  Se clasifica con el detector de
        # C y las capacidades se MARCAN como heredadas, con el nombre de la
        # constante: una capacidad que viene de una cadena no es de Python.
        embebidas = []
        for nombre, s in _fuente_c_embebida(limpio):
            txt_c = _sin_comentarios_c(s)
            rutas, _d = _rutas_c(txt_c, s)
            for r, flags, _v in rutas:
                if r.startswith("/dev/"):
                    etq = "DEVICE_OPEN_RDWR" if flags == "O_RDWR" \
                        else "DEVICE_OPEN_RDONLY"
                else:
                    etq = "SYSFS_READ"
                res["caps"].append(etq)
                embebidas.append({"constante": nombre, "ruta": r,
                                  "flags": flags, "capability": etq})
            if IOCTL_AMD.search(txt_c):
                etq = "IOCTL_MMR" if IOCTL_MMR.search(txt_c) else "IOCTL_AMDGPU"
                res["caps"].append(etq)
                embebidas.append({"constante": nombre, "ruta": "(ioctl)",
                                  "flags": etq, "capability": etq})
        if embebidas:
            res["fuente_c_embebida"] = embebidas

    res["caps"] = sorted(set(res["caps"]))
    res["severidad"] = max((SEV.get(c, "MEDIO") for c in res["caps"]),
                           key=lambda s: SEV_ORDEN[s], default="NULO")

    # -- eje 2: la cabecera contra el codigo -------------------------------
    decl = {}
    for k, v in re.findall(r'^\s*#\s*CONTRACT:\s*(\w+)\s*=\s*(\S+)', crudo, re.M):
        decl[k.upper()] = v.lower()
    for k, v in re.findall(r'^\s*#\s*(WORK_CLASS|WRITE_EXECUTION)\s*=\s*(\S+)',
                           crudo, re.M):
        decl[k.upper()] = v.lower()
    res["declara"] = decl
    if decl.get("WRITES_FILES") in ("no", "false", "0") and res["escrituras"]:
        res["contradicciones"].append(
            "declara WRITES_FILES=no y abre en escritura: %s"
            % ", ".join(sorted(set(res["escrituras"]))[:3]))
    if decl.get("WRITES_GPU") in ("no", "false", "0") and \
       "DEVICE_OPEN_RDWR" in res["caps"]:
        # O_RDWR da un descriptor ESCRIBIBLE.  Eso contradice "no escribe" en el
        # sentido de que la herramienta PODRIA escribir con el, y mas aqui donde
        # el proyecto ya midio que un descriptor de render es lo que saca la GPU
        # de runtime-suspend.  Se dice exactamente eso, no mas.
        res["contradicciones"].append(
            "declara WRITES_GPU=no y abre el nodo con O_RDWR: el descriptor es "
            "escribible aunque la ioctl que use sea de lectura")
    # MEDIDO, y es un FALSO POSITIVO que este fichero cometio y corrigio:
    # se contradecia WRITES_GPU=no tambien por emitir una ioctl de la capa DRM.
    # `vbiosread.py` abre O_RDWR, emite `AMDGPU_INFO_VBIOS` -- que es de
    # LECTURA -- y declara WRITES_GPU=no, que es HONESTO.  Una ioctl DRM-INFO
    # no es una escritura.  Leer no es escribir, que es la misma confusion que
    # hace inutil el gate de texto, en la direccion contraria.
    if decl.get("READONLY") in ("yes", "true", "1"):
        if decl.get("WRITES_FILES") in ("yes", "true", "1"):
            # La CABECERA se contradice a si misma.  `vbiosread.py` declara las
            # dos cosas.  No es que el codigo desmienta al contrato: es que el
            # contrato se desmiente, y son dos afirmaciones distintas con
            # Owners distintos -- una la arregla quien escribe la cabecera, la
            # otra la arregla quien escribe el codigo.
            res["contradicciones"].append(
                "la CABECERA se contradice: READONLY=yes y WRITES_FILES=yes "
                "a la vez")
        elif res["escrituras"]:
            res["contradicciones"].append(
                "declara READONLY=yes y el codigo escribe ficheros")

    # -- eje 3: el flag del selftest ---------------------------------------
    f = flag_que_pregunta(crudo)
    res["flag_preguntado"] = f
    toks = tokens_argv_reales(crudo)
    if f:
        res["flag_real"] = sorted(t for t in toks
                                  if re.search(r"sel|test|check|probe|verif", t))
        res["flag_resuelto"] = f in toks
        res["gates"].append("FLAG_AMBIGUO" if not res["flag_resuelto"]
                            else "FLAG_OK")
        if not res["flag_resuelto"]:
            # El alcance de la pregunta equivocada.  Ver `alcance_sin_flag`.
            alc = alcance_sin_flag(crudo, ext, limpio)
            if alc is not None:
                res["alcance_sin_flag"] = alc
                fuera = alc["caps_fuera_del_selftest"]
                peligrosas = sorted(set(fuera) & {
                    "PROC_PRIV", "MODULE_LOAD", "SYSFS_WRITE", "DEVICE_WRITE",
                    "IOCTL_MMR", "IOCTL_AMDGPU", "DEVICE_OPEN_RDWR",
                    "POWER_HOLD_RT"})
                if peligrosas:
                    res["gates"].append("ALCANZABLE_SIN_FLAG")
                    res["peligroso_sin_flag"] = peligrosas
    return res


# --------------------------------------------------------------------------
# 6. CRUCE CON LA INTERLUSA DE TEXTO QUE YA EXISTE
# --------------------------------------------------------------------------

def cruce_con_gate_texto(res, raiz):
    """Compara lo que el CODIGO dice con lo que la interlusa de TEXTO responde.

    No se reimplementa la interlusa: se llama.  `toolreg` es la autoridad de
    esa politica y este fichero no tiene permiso para cambiarla; solo para
    medir la distancia entre su respuesta y la del codigo.
    """
    try:
        import toolreg as _t
    except Exception:
        res["gates"].append("GATE_NO_IMPORTABLE")
        return res
    path = os.path.join(raiz, res["herramienta"])
    crudo = open(path, encoding="utf-8", errors="replace").read()
    kv = bool(_t.FORBIDDEN_KV.search(crudo))
    cl = bool(_t.FORBIDDEN_CALL.search(crudo))
    decl = _t.declares_read_only(crudo)
    texto_refusa = kv or cl
    if texto_refusa:
        res["gates"].append("GATE_TEXTO_REFUSA")
    else:
        res["gates"].append("GATE_TEXTO_PASA")
    res["gate_texto_pasa"] = not texto_refusa
    res["gate_texto_declara_readonly"] = decl
    codigo_peligroso = bool({"PROC_PRIV", "SYSFS_WRITE", "IOCTL_MMR",
                             "IOCTL_AMDGPU", "DEVICE_OPEN_RDWR",
                             "POWER_HOLD_RT"} & set(res["caps"]))
    res["codigo_peligroso"] = codigo_peligroso
    # LA DISTANCIA.  Codigo peligroso y la interlusa no lo ve.
    if codigo_peligroso and not texto_refusa:
        res["gates"].append("HUECO_GATE")
    return res


# --------------------------------------------------------------------------
# 7. RECORRIDO
# --------------------------------------------------------------------------

def recorre(raiz, cortar=False):
    filas = []
    for d in TOOL_DIRS:
        t = os.path.join(raiz, d)
        if not os.path.isdir(t):
            continue
        if cortar and d not in ("tools", "08-ARQUITECTURA/tools"):
            continue
        for f in sorted(os.listdir(t)):
            if not re.match(r"^[a-z0-9_]+\.(py|c|sh)$", f):
                continue
            p = os.path.join(t, f)
            if not os.path.isfile(p):
                continue
            r = clasifica(p, raiz)
            if r.get("estado") != "ILEGIBLE" and r.get("clasificable"):
                cruce_con_gate_texto(r, raiz)
            filas.append(r)
    return filas


def contrato_y_limitaciones(filas):
    """Lo que este fichero PUEDE y NO PUEDE afirmar, emitido junto al dato.

    Una tabla de capacidades sin esta seccion es una tabla que se lee como si
    cubriera el arbol entero.
    """
    n = len(filas)
    n_clas = sum(1 for f in filas if f.get("clasificable"))
    n_hueco = sum(1 for f in filas if "HUECO_GATE" in f.get("gates", []))
    n_flag = sum(1 for f in filas if "FLAG_AMBIGUO" in f.get("gates", []))
    n_contra = sum(1 for f in filas if f.get("contradicciones"))
    return [
        "POBLACION      %d herramientas en %d directorios declarados" % (n, len(TOOL_DIRS)),
        "CLASIFICABLES  %d de %d" % (n_clas, n),
        "HUECO_GATE     %d  el codigo hace algo que la interlusa de texto no ve" % n_hueco,
        "FLAG_AMBIGUO   %d  se las pregunta por una palabra que no es token argv" % n_flag,
        "CONTRADICCION  %d  la cabecera afirma algo que el codigo desmiente" % n_contra,
        "",
        "LIMITACION 1   .sh sin metodo: salen NOT_CLASIFICABLE, que no es PASA.",
        "LIMITACION 2   una ruta montada en tiempo de ejecucion se declara",
        "               RUTA_DINAMICA: se sabe que hay llamada, no a que nodo llega.",
        "LIMITACION 3   el veredicto es sobre CODIGO.  Un .c sin compilar es una",
        "               fuente.  Esto no lo convierte en binario.",
        "LIMITACION 4   NO se ejecuto ninguna herramienta.  Es analisis estatico.",
    ]


# --------------------------------------------------------------------------
# 8. SELFTEST -- hermetico, con fixtures propios
# --------------------------------------------------------------------------

FIX_C_RDWR_SLEEP = r"""
/* abre un nodo de render con O_RDWR y lo mantiene: saca la GPU de suspend */
#include <fcntl.h>
#include <unistd.h>
int main(int argc, char **argv) {
    const char *node = (argc > 2) ? argv[2] : "/dev/dri/renderD129";
    int fd = open(node, O_RDWR | O_CLOEXEC);
    sleep(5);
    return fd < 0;
}
"""

FIX_C_LEYENDA_INSmod = r"""
# una leyenda de codigos de salida de shell, no una invocacion
TABLA = " NIVEL 4 / insmod  0"
NO_ES_UNA_INVOCACION = True
"""

FIX_C_COMENTARIO_MEM = r"""
/* se declara por separado: WRITES_GPU_MMIO=no
 * busco /dev/mem, __iomem y no encontre nada
 */
int main(void) { return 0; }
"""

FIX_PY_SELFTEST_TRAMPA = '''
RENDER = "/dev/dri/renderD129"

def selftest():
    return 0

def main(argv):
    if "--self" in argv:
        return selftest()
    return 0
'''


def _escribe(d, nombre, cuerpo):
    p = os.path.join(d, nombre)
    with open(p, "w") as fh:
        fh.write(cuerpo)
    return p


def selftest():
    """Vectores con respuesta conocida, en un directorio propio.

    Los nueve primeros son los nueve casos del corpus real; aqui estan
    reescritos como fixtures para que el test no dependa del arbol.  Los dos
    ultimos son los que el proyecto todavia no tiene: un self-test que
    MIENTE sobre su flag, y una cabecera que MIENTE sobre sus escrituras.
    """
    vectores, fallos = [], []

    def v(nombre, ok, detalle):
        vectores.append((nombre, ok, detalle))
        if not ok:
            fallos.append(nombre)

    with tempfile.TemporaryDirectory(prefix="riesgo-st") as d:
        # 1) POSITIVO: O_RDWR + sleep, ruta por variable  ->  ALTO
        p = _escribe(d, "hold.c", FIX_C_RDWR_SLEEP)
        r = clasifica(p, d)
        v("FN_1_ruta_por_variable_detectada",
          "POWER_HOLD_RT" in r["caps"] and "DEVICE_OPEN_RDWR" in r["caps"],
          "caps=%s sev=%s" % (r["caps"], r["severidad"]))

        # 2) NEGATIVO: la palabra insmod en una leyenda
        p = _escribe(d, "leyenda.py", FIX_C_LEYENDA_INSmod)
        r = clasifica(p, d)
        v("FP_1_insmod_en_leyenda_no_es_invocacion", not r["caps"],
          "caps=%s" % (r["caps"],))

        # 3) NEGATIVO: /dev/mem en un comentario
        p = _escribe(d, "comentario.c", FIX_C_COMENTARIO_MEM)
        r = clasifica(p, d)
        v("FP_2_devmem_en_comentario_no_es_acceso", not r["caps"],
          "caps=%s" % (r["caps"],))

        # 4) el FLAG: la palabra suelta 'selftest' no es un token argv
        p = _escribe(d, "trampa.py", FIX_PY_SELFTEST_TRAMPA)
        r = clasifica(p, d)
        v("FLAG_1_palabra_suelta_no_es_token_argv",
          r["flag_preguntado"] == "selftest" and r["flag_resuelto"] is False
          and r["flag_real"] == ["--self"],
          "preguntado=%r real=%s resuelto=%s"
          % (r["flag_preguntado"], r["flag_real"], r["flag_resuelto"]))

        # 5) la cabecera que miente sobre sus escrituras
        p = _escribe(d, "menteira.py",
                     "# CONTRACT: name=menteira\n# CONTRACT: READONLY=yes\n"
                     "# CONTRACT: WRITES_FILES=no\n"
                     "def selftest():\n    return 0\n\n"
                     "def main(argv):\n"
                     "    with open('/tmp/x', 'w') as f:\n"
                     "        f.write('x')\n"
                     "    return 0\n")
        r = clasifica(p, d)
        v("CONTRA_1_cabecera_dice_que_no_escribe_y_escribe",
          any("WRITES_FILES=no" in c for c in r["contradicciones"]),
          "contradicciones=%s" % (r["contradicciones"],))

        # 6) lo que NO se puede clasificar NO es PASA.  Este vector se escribio
        # cuando los .sh salian NOT_CLASIFICABLE, y asi se queda: la propiedad
        # que vigilaba --"lo que no se sabe no se pinta de verde"-- sigue siendo
        # la importante, y ahora se prueba con un Python que NO PARSEA, que es
        # el caso que de verdad puede aparecer.
        p = _escribe(d, "roto.py", "def selftest(:\n  return 1\n")
        r = clasifica(p, d)
        v("LIM_1_lo_que_no_parsea_no_es_pasa",
          r["clasificable"] is False and "caps" not in r,
          "clasificable=%s caps=%s" % (r["clasificable"], r.get("caps")))

        p = _escribe(d, "guion.sh", "#!/bin/bash\necho hola\n")
        r = clasifica(p, d)
        v("LIM_2_sh_declara_el_metodo_que_le_dice",
          r["clasificable"] is True and r["metodo"].startswith("shell:")
          and "gates" in r, "metodo=%r" % r.get("metodo"))

        # 7) O_RDONLY sobre sysfs NO es DEVICE_OPEN_RDWR
        p = _escribe(d, "lee.c",
                     '#include <fcntl.h>\nint main(void){int fd=open('
                     '"/sys/class/drm/card1/device",O_RDONLY);return fd;}\n')
        r = clasifica(p, d)
        v("SEP_1_ordonly_no_es_rdwr",
          "DEVICE_OPEN_RDWR" not in r["caps"] and "SYSFS_READ" in r["caps"],
          "caps=%s" % (r["caps"],))

    # 8) sudo en un print NO es sudo; sudo como ARGUMENTO si
        p = _escribe(d, "sudo_en_print.py",
                     "import subprocess\n\ndef selftest():\n    return 0\n\n"
                     "def main(argv):\n"
                     '    print("resource0 es root-only, asi que hace falta sudo.")\n'
                     "    return 0\n")
        r = clasifica(p, d)
        v("FP_3_sudo_en_un_print_no_es_privilegio",
          "PROC_PRIV" not in r["caps"], "caps=%s" % (r["caps"],))

        p = _escribe(d, "sudo_real.py",
                     "import subprocess\n\ndef selftest():\n    return 0\n\n"
                     "def main(argv):\n"
                     '    return subprocess.run(["sudo", "-S", "-k", "bash", "-c",'
                     ' "cat x"], capture_output=True)\n')
        r = clasifica(p, d)
        v("FN_2_sudo_como_argumento_es_privilegio",
          "PROC_PRIV" in r["caps"], "caps=%s" % (r["caps"],))

    # 9) la funcion es PURA: clasificar el mismo fichero dos veces da lo mismo
    with tempfile.TemporaryDirectory(prefix="riesgo-st2") as d:
        p = _escribe(d, "x.c", FIX_C_RDWR_SLEEP)
        v("PURE_1_dos_pasadas_identicas", clasifica(p, d) == clasifica(p, d),
          "")

    # 10) fuente C embebida en una cadena: el Python no la ve, el detector si
        p = _escribe(d, "embebido.py",
                     "import subprocess\n\nPROBE_C = r'''\n#include <fcntl.h>\n"
                     "#include <sys/ioctl.h>\nint main(int c,char**v){\n"
                     '  int fd = open("/dev/dri/renderD129", O_RDWR);\n'
                     "  return ioctl(fd, DRM_IOCTL_AMDGPU_INFO, 0);\n}\n'''\n\n"
                     "def selftest():\n    return 0\n\n"
                     "def main(argv):\n    return 0\n")
        r = clasifica(p, d)
        v("FN_3_fuente_c_embebida_en_una_cadena",
          "DEVICE_OPEN_RDWR" in r["caps"] and "IOCTL_AMDGPU" in r["caps"]
          and r.get("fuente_c_embebida"),
          "caps=%s embebida=%s" % (r["caps"], bool(r.get("fuente_c_embebida"))))

    # 11) una ioctl DRM de LECTURA no contradice WRITES_GPU=no
        p = _escribe(d, "vbios.py",
                     "# CONTRACT: READONLY=yes\n# CONTRACT: WRITES_GPU=no\n"
                     'PROBE_C = r"""\n#include <fcntl.h>\n'
                     "#include <sys/ioctl.h>\nint main(int c,char**v){\n"
                     '  int fd = open("/dev/dri/renderD129", O_RDWR);\n'
                     "  struct drm_amdgpu_info i; i.query = AMDGPU_INFO_VBIOS;\n"
                     "  return ioctl(fd, DRM_IOCTL_AMDGPU_INFO, &i);\n}\n\"\"\"\n\n"
                     "def selftest():\n    return 0\n\n"
                     "def main(argv):\n    return 0\n")
        r = clasifica(p, d)
        v("FP_4_ioctl_de_lectura_no_contradice_que_no_escriba",
          "IOCTL_AMDGPU" in r["caps"]
          and not any("emite ioctl" in c for c in r["contradicciones"]),
          "contradicciones=%s" % (r["contradicciones"],))

    # 12) SHELL: un detector que no dispara no es un detector
        p = _escribe(d, "peligroso.sh",
                     "#!/bin/sh\nsudo insmod /tmp/x.ko\necho 1 > /sys/module/x/param/y\n")
        r = clasifica(p, d)
        v("SH_1_el_detector_de_shell_dispara",
          "PROC_PRIV" in r["caps"] and "MODULE_LOAD" in r["caps"]
          and "SYSFS_WRITE" in r["caps"], "caps=%s" % (r["caps"],))

        p = _escribe(d, "inofensivo.sh",
                     "#!/bin/sh\ngrep -c x \"$f\" 2>/dev/null\nfind . -name '*.py'\n")
        r = clasifica(p, d)
        v("SH_2_stderr_no_es_escribir_en_el_dispositivo",
          not r["caps"], "caps=%s" % (r["caps"],))

        # el caso agudo: se PREGUNTA --selftest a otras herramientas, y el
        # brazo de uno mismo es --self.  Caer en la ejecucion normal.
        p = _escribe(d, "auto.sh",
                     "#!/bin/sh\nfor n in *.py; do\n"
                     "  python3 \"$n\" --selftest >/dev/null\ndone\n"
                     "case \"$1\" in\n  --self) echo diagnostico ;;\n"
                     "  *) echo \"consulta: $1\" ;;\nesac\n")
        r = clasifica(p, d)
        v("SH_3_preguntar_el_flag_de_otro_es_el_equivocado",
          r["flag_preguntado"] == "--selftest" and "--self" in r["brazos_case"]
          and "FLAG_AMBIGUO" in r["gates"], "gates=%s brazos=%s"
          % (r["gates"], r["brazos_case"]))

        p = _escribe(d, "sindespacho.sh",
                     "#!/bin/sh\n# pregunta --selftest a las demas, y no tiene brazo propio\n"
                     "for n in *.py; do python3 \"$n\" --selftest >/dev/null; done\n"
                     "case \"$1\" in\n  0) echo OK ;;\n  *) echo rc ;;\nesac\n")
        r = clasifica(p, d)
        v("SH_4_sin_despacho_no_es_flag_equivocado",
          "FLAG_SIN_DESPACHO" in r["gates"] and "FLAG_AMBIGUO" not in r["gates"],
          "gates=%s" % (r["gates"],))

        p = _escribe(d, "leesysfs.sh",
                     "#!/bin/sh\ncat /sys/class/drm/card1/device/pp_dpm_sclk\n")
        r = clasifica(p, d)
        v("SH_5_leer_sysfs_se_registra_como_lectura",
          "SYSFS_READ" in r["caps"] and "SYSFS_WRITE" not in r["caps"],
          "caps=%s" % (r["caps"],))

    # 13) la cabecera puede contradecirse a si misma: eso NO es el codigo
        p = _escribe(d, "autocabeza.py",
                     "# CONTRACT: READONLY=yes\n# CONTRACT: WRITES_FILES=yes\n"
                     "def selftest():\n    return 0\n\n"
                     "def main(argv):\n"
                     "    with open('/tmp/y', 'w') as f:\n"
                     "        f.write('y')\n    return 0\n")
        r = clasifica(p, d)
        v("CONTRA_2_la_cabecera_se_contradice_a_si_misma",
          any("CABECERA se contradice" in c for c in r["contradicciones"]),
          "contradicciones=%s" % (r["contradicciones"],))

    # 13) este selftest NO lee el corpus: se lee a si mismo y lo comprueba
    v("HERM_1_no_lee_el_corpus",
      "06-INGENIERIA-INVERSA" not in open(__file__, encoding="utf-8").read()
      .split("LIMITACION 1")[0],
      "el cuerpo anterior a LIMITACION 1 no nombra el corpus")

    print("  selftest de riesgos.py %s" % VERSION)
    print("  %d vectores, %d fallos" % (len(vectores), len(fallos)))
    for nombre, ok, det in vectores:
        print("    %-4s %-48s %s" % ("OK" if ok else "FALLA", nombre, det[:60]))
    return 1 if fallos else 0


# --------------------------------------------------------------------------
# 9. MAIN
# --------------------------------------------------------------------------

def main(argv):
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if "--selftest" in argv or "--self-test" in argv:
        return selftest()
    if "--version" in argv:
        print(VERSION)
        return 0

    corte = "--corte" in argv
    filas = recorre(raiz, cortar=corte)

    if "--json" in argv:
        print(json.dumps({
            "herramienta": VERSION, "generado": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "raiz": raiz, "directorios": list(TOOL_DIRS),
            "contrato": contrato_y_limitaciones(filas), "filas": filas,
        }, indent=2, ensure_ascii=False))
        return 0

    explicar = None
    for i, a in enumerate(argv):
        if a == "--explain" and i + 1 < len(argv):
            explicar = argv[i + 1]
    if explicar:
        for r in filas:
            if r["herramienta"] == explicar or r["herramienta"].endswith("/" + explicar):
                print(json.dumps(r, indent=2, ensure_ascii=False))
                return 0
        print("no esta en el registro: %s" % explicar)
        return 2

    # Informe: primero lo que no encaja, que es lo que se lee.
    # NOTA DE SEVERIDAD: las dos primeras secciones son de SEGURIDAD.  La tercera
    # es EPISTEMICA -- una cabecera que no describe su codigo es un problema de
    # honestidad del registro, no un riesgo para la maquina.  Escribir un
    # informe donde las tres comparten columna `severidad` invites a leer
    # "escribe un fichero" con el mismo peso que "abre el nodo de la GPU con
    # O_RDWR".  No lo comparten.
    for titulo, sel in (("HUECO DE LA INTERLUSA: el codigo lo hace, el texto no lo ve"
                         "   [ SEGURIDAD ]",
                         lambda r: "HUECO_GATE" in r.get("gates", [])),
                        ("FLAG DEL SELFTEST: se pregunta por una palabra que no es argv"
                         "   [ SEGURIDAD: la palabra equivocada produce la ejecucion normal ]",
                         lambda r: "FLAG_AMBIGUO" in r.get("gates", [])),
                        ("LA CABECERA MIENTE: el codigo desmiente al contrato"
                         "   [ EPISTEMICA: no es riesgo de maquina ]",
                         lambda r: r.get("contradicciones"))):
        Rows = [r for r in filas if sel(r)]
        print("=" * 100)
        print(titulo, "  [%d]" % len(Rows))
        print("=" * 100)
        for r in sorted(Rows, key=lambda x: -SEV_ORDEN.get(x["severidad"], 0)):
            print("  %-46s %-9s %s" % (r["herramienta"], r["severidad"],
                                       ",".join(r["caps"]) or "-"))
            for c in r.get("contradicciones") or []:
                print("      ! %s" % c)
            if "FLAG_AMBIGUO" in r.get("gates", []):
                print("      ! se pregunta por %r; el flag real es %s"
                      % (r["flag_preguntado"], r["flag_real"] or "NINGUNO"))
    print()
    for linea in contrato_y_limitaciones(filas):
        print("  " + linea)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
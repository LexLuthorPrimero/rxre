#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
# CONTRACT: name=toolreg
# CONTRACT: READONLY=no
# CONTRACT: WRITES_FILES=only_with_--register
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: TOUCHES_INTEGRATED=no
#
# READONLY=no por UNA razon, y es una excepcion acotada: `--register` escribe el
# esqueleto de una herramienta nueva con su bloque CONTRACT.  Ese es el unico
# modo de escritura del fichero; todo lo demas es `inventory()`, que lee.
# Se declara `only_with_--register` y no `yes` porque `yes` haria creer que
# escribir sin que se le pida, que no es lo que ocurre.
#
# MEDIDO, y por que el selftest NO cuenta como escritura del proyecto: sus
# escrituras van a `tempfile.TemporaryDirectory()`, que es la clase TEMPORAL de
# `contract_exec.py`.
#
# TOUCHES_INTEGRATED=no: lee el arbol.  No abre sysfs ni DRM.  La razon de que
# este fichero sea especial es la contraria: es el REGISTRO, y si el contendio
# una entrada falsa, todo lo que lea de el hereda el error (hallazgo 1481,
# sobre `rxre.py` §4b y el `toolreg.py` pisado).  Ver 1487 sobre el campo.
"""
toolreg -- the registry for tools/, and the check that it stays true.

WHY THIS EXISTS
---------------
There are 23 source tools in tools/ and they were built by three sessions in one
morning.  None of them knew about each other.  Concretely, at 14:3x on
2026-10-01:

  * 16 of the 23 were cited NOWHERE in docs/TOOLS-STATUS.md
  * `reg_resolve.py` resolves a register to its MASK, SHIFT and UNIT, and
    `reg_census.py` enumerates which registers a .c touches.  Neither appears in
    the documentation, so an agent about to hand-transcribe a register field
    would not know a tool for it exists
  * `xref.py` does symbol cross-reference through the clang AST, not regex.  That
    is the answer to the class of problem that cost this project `019` eight
    hours on a false NOT_FOUND
  * `contradict.py` detects incompatible claims across findings, which is a task
    the documentation was doing by hand

An index that has to be maintained by remembering is not an index.  This is the
FINDINGS-INDEX problem applied to tools/, and tools/ has exactly the same failure
mode: two sessions choose names independently and nothing reconciles them.

WHAT IT DOES
------------
  1. inventory  every source tool in tools/, with size and kind
  2. contract   the declared purpose, and whether it declares WHAT IT DOES NOT DO
  3. selftest   run each tool's own self-test, capture exit code and duration
  4. coverage   cross-reference docs/TOOLS-STATUS.md, in BOTH directions:
                   - a tool that exists and is not documented
                   - a TL-nn entry that names a tool that does not exist
  5. freshness  whether a TL-nn entry names a file that has changed since

WHAT IT DOES NOT PROVE, DECLARED UP FRONT
------------------------------------------
  1. It does not judge whether a tool's OUTPUT is correct.  `toolcheck.py` says
     the same about contracts, and both are right: a parser that is correct does
     not prove the answer is.  The judgement stays with whoever reads the output.
  2. It does not read a tool to understand it.  It reads the header.  A tool with
     a good header and a wrong body passes every check here.
  3. Running another session's self-test is safe ONLY because every tool in this
     tree declares WORK_CLASS=READ_ONLY / WRITE_EXECUTION=NONE in its header, and
     this tool REFUSES to run one that does not declare it.  That refusal is a
     safety interlock, not a formality: see run_selftests().
  4. A missing self-test is reported as MISSING, never as a pass.
  5. Coverage is measured by name.  A tool documented in prose without its name
     in backticks will read as uncovered.  That is a false negative in the safe
     direction, and it is recorded rather than hidden.

SAFETY
------
This tool reads files and runs other tools' own self-tests.  It writes nothing.
It does not open /sys, does not touch the GPU, does not compile anything, and
does not run git commands that modify the tree.

USAGE
-----
  toolreg.py --repo .                  full report, human readable
  toolreg.py --repo . --undocumented   only the gap
  toolreg.py --repo . --json           machine readable; nothing may follow
  toolreg.py --repo . --no-selftest   inventory and coverage only, no execution
  toolreg.py --selftest               its own tests
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time

VERSION = "1.0.0"
TOOL = "toolreg"

# A tool that DECLARES one of these is claiming it may write or touch hardware.
# This tool will not execute it, and says so.
#
# THE MATCH MUST LOOK LIKE A DECLARATION, NOT LIKE PROSE.
# The first version searched for bare words, and refused to execute ITSELF,
# because this file's own docstring names MMIO_WRITE, insmod and rmmod as the
# things it rejects.  Measured on the first real run:
#     toolreg.py   REFUSED_UNSAFE
# An interlock that fires on the tool that enforces it is an interlock that gets
# switched off, and then it protects nothing.  So:
#   - markers must appear as KEY=VALUE, or as a bare word only when it is
#     followed by a call-shaped argument, which is what running one looks like
#   - this file never checks itself, and says so in the output
FORBIDDEN_KV = re.compile(
    r"\bWRITE_EXECUTION\s*=\s*(?:WRITE|SCOPED|PARTIAL_WRITE)"
    r"|\b(?:MMIO|REGISTER|PCI)_WRITE\s*=\s*(?:YES|TRUE|1)"
    r"|\bSYSFS_WRITE\s*=\s*(?:YES|TRUE|1)",
    # NOTE: an earlier version had a fourth alternative matching
    # WRITE_EXECUTION=NONE, which made every correctly-declared tool look unsafe.
    # It is gone.  A marker list that flags the safe value is worse than none.
)
# a bare forbidden verb, only when it looks like an invocation
FORBIDDEN_CALL = re.compile(
    r"(?:^|[;&|`$(\s])(?:sudo\s+)?(?:insmod|rmmod|modprobe)\s+[-\w./]"
    r"|/dev/(?:mem|kmem)"
    r"|\becho\s+[01]\s*>\s*/sys"
)

# Recognised SAFETY declarations.  Several forms are accepted because tools in
# this tree declare safety in prose as well as by token, and refusing a tool
# that plainly says "NO toca la GPU" would train people to add the token instead
# of to think.
# TWO CONVENTIONS EXIST IN THIS TREE, and refusing to see one of them turns a
# formatting difference into a false alarm.
#
#   tools/                  WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE
#   08-ARQUITECTURA/tools/  # CONTRACT: name=... READONLY=no WRITES_FILES=yes
#
# Measured before this was fixed: 19 of 44 tools reported "no WORK_CLASS
# declaration".  A large part of that was not a missing declaration, it was a
# different spelling of the same declaration.  An interlock that cries wolf on a
# spelling gets ignored, and then it protects nothing.
CONTRACT_RE = re.compile(
    r"^\s*#\s*CONTRACT:\s*(?P<k>\w+)\s*=\s*(?P<v>\S+)", re.M
)


def declares_read_only(text):
    """
    True if the tool declares itself read-only, in EITHER convention.

    tools/                  WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE
    08-ARQUITECTURA/tools/  # CONTRACT: READONLY=no   WRITES_FILES=yes

    For the CONTRACT form, READONLY=no means the tool is not read-only, so it is
    NOT accepted as safe.  A tool that says it writes files is not run by this
    tool, and that is the honest reading, not a technicality.
    """
    if "WORK_CLASS=READ_ONLY" in text or "WRITE_EXECUTION=NONE" in text:
        return True
    for m in CONTRACT_RE.finditer(text):
        k, v = m.group("k").upper(), m.group("v").lower()
        if k in ("WORK_CLASS",) and v.startswith("read_only"):
            return True
        if k == "READONLY" and v in ("yes", "true", "1"):
            return True
        if k == "WRITES_SYSFS" and v in ("no", "false", "0"):
            return True
        if k == "WRITE_EXECUTION" and v in ("none",):
            return True
    return False


SAFE_MARKERS = (
    "WORK_CLASS=READ_ONLY",
    "READ_ONLY",
    "WRITE_EXECUTION=NONE",
    "NO toca la GPU",
    "no toca la GPU",
    "no lee MMIO",
    "no escribe",
    "STATIC_ANALYSIS",
    "analisis ESTATICO",
    "análisis ESTÁTICO",
    "STATIC ANALYSIS",
)


class Tool:
    __slots__ = ("path", "name", "stem", "kind", "size", "purpose",
                 "declares_limits", "declares_safety", "selftest_arg",
                 "doc_tl", "doc_tl_level", "doc_tl_all", "in_docs", "mtime",
                 "dir")

    def __init__(self, path):
        self.path = path
        self.name = os.path.basename(path)
        self.stem = self.name.rsplit(".", 1)[0]
        self.kind = self.name.rsplit(".", 1)[-1] if "." in self.name else ""
        self.size = os.path.getsize(path)
        self.mtime = os.path.getmtime(path)
        self.purpose = None
        self.declares_limits = False
        self.declares_safety = False
        self.selftest_arg = None
        self.doc_tl = None
        self.doc_tl_level = None
        self.doc_tl_all = []
        self.in_docs = False
        self.dir = ""

    @property
    def is_source(self):
        return self.kind in ("py", "c", "sh")


def _read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def _head(path, nbytes=6000):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read(nbytes)
    except OSError:
        return ""


# What a tool may do that is not merely reading files.
UNSAFE_RE = re.compile(
    r"open\s*\(\s*['\"][^'\"]*['\"]\s*,\s*['\"][wa]|"
    r"\.write_text|shutil\.(?:copy|move|rmtree)|os\.remove|os\.unlink|"
    r"subprocess\.[a-z_]+\([^)]*\brm\b|insmod|rmmod|modprobe|"
    r"/dev/mem|/dev/kmem|ioremap|setpci|echo\s+[01]\s*>\s*/sys"
)


def parse_tool(t, root):
    # the WHOLE file, not the head.  `--selftest` in a tool with a long
    # docstring lives far past the first few kB; reading only the head made
    # docscan.py look like it had no self-test when it has 13 checks.
    head = _read(t.path)

    # purpose: first docstring line, or the first # comment that is not a shebang
    m = re.search(r'^\s*(?:"""|#)\s*(.+?\.py\s*[—-]\s*.+)$', head, re.M)
    if not m:
        m = re.search(r'^\s*"""\s*\n\s*(.+)$', head, re.M)
    if not m:
        m = re.search(r"^#\s*(?!SPDX|!)(.+)$", head, re.M)
    if m:
        t.purpose = m.group(1).strip()[:110]

    t.declares_limits = bool(re.search(
        r"LO QUE NO (?:PROBA|HACE)|What it does not|does not prove|"
        r"Lo que NO hace|limitaciones? (?:conocidas|declara)", head, re.I))
    t.declares_safety = declares_read_only(head)

    for flag in ("--selftest", "--self-test", "selftest"):
        if flag in head:
            t.selftest_arg = flag
            break
    if t.selftest_arg is None and t.kind in ("py", "sh") \
            and re.search(r"\b(?:def|function)\s+selftest", head):
        t.selftest_arg = "--selftest" if t.kind == "sh" else None
    return t


# Tools live in MORE THAN ONE directory, and that is not a detail.
#
# pm4_count_census.py, count_vmflush_dw.py and frame_budget.py were documented in
# TOOLS-STATUS as tools/ entries and are now in 08-ARQUITECTURA/tools/.  The
# first version of this file scanned only tools/, so it reported all three as
# TL entries naming a tool that does not exist -- an "orphan" that was really a
# move -- AND it missed every tool in the second directory.  A registry that
# scans half the tools is not a registry.
# MEDIDO Y CORREGIDO 2026-10-04.  FALTA UN TERCER DIRECTORIO, y el motivo de que
# falte es la misma razon por la que falta:  NADIE COMPROBO QUE SE.
#
# El comentario de arriba de esta constante ya es la historia de ESTE defecto una
# vez:  "la primera version de este fichero escaneaba solo tools/,  de modo que
# reporto tres herramientas movidas como SI ESTUVIERAN PERDIDAS  y no vio ninguna
# del segundo directorio.  Un registro que escanea la mitad no es un registro."
#
# MEDIDO que se repitio,  y mas grave.  Hay un TERCER directorio:
#
#     tools/                                     75 ejecutables
#     08-ARQUITECTURA/tools/                      73
#     04-IMPLEMENTACION/rx550-driver/tools/        6     <-- invisible aqui
#
# Y MEDIDO que HAY TRES ALCANCES DISTINTOS Y NINGUNO DE ACUERDO:
#     toolreg.py   dos directorios
#     artifacts.py  UN directorio  —  os.path.join(root, "tools")  sin lista
#
# Con eso el registro de herramientas  —que es GENERADO,  asi que no se nota a
# ojo—  clasificaba 72 filas mientras habia 154 ejecutables.  No es que este mal:
# es que no existe,  y una herramienta que no existe no se ejecuta,  no se cita con
# su hash  y no puede marcarse VALIDATED.
#
# Y AHORA HAY UNA PUERTA  —ver directorios_no_declarados()—  que hace que un
# CUARTO directorio no pueda volverse invisible igual:  recorre el arbol buscando
# cualquier directorio llamado "tools"  y falla si no esta en esta tupla.
#
# MEDIDO por la puerta recien anadida  —directorios_no_declarados()—,  que
# encontro TRES mas en la misma pasada.  Y los tres contienen herramientas
# REALES,  no directorios con nombre de tools:
#
#   04-IMPLEMENTACION/tools/   rx550_compress.c, rx550_decompress.c
#       Un codificador PNG -> BC3  y su decodificador de referencia.  MEDIDO por
#       su propio prologo:  "A thin driver over ../compressor/rx550_compress.c ...
#       the SAME object the module's unit tests exercise".
#
#   09-POWER-CLOCKS/tools/      rx550_load.c, rx550_hold.c
#       MEDIDO por su prologo:  "AGENT-22 research instrument ... generate REAL,
#       verifiable GPU load headlessly on the RX550 and, in the same loop, sample
#       the amdgpu power/clock chain, so that WORKLOAD -> GPU_BUSY -> SCLK/MCLK ->
#       vddgfx -> PPT -> edge TEMP is measured time-correlated on this target".
#
#       Es decir:  LOS INSTRUMENTOS DE RENDIMIENTO DEL PROYECTO.  Y MEDIDO que
#       NO estaban en el registrogenerated.  Para una tabla cuyo trabajo es
#       "cada herramienta, su hash, si tiene selftest, y su clasificacion",  que
#       lo que produce carga medible este invisible es el defecto mas grave de los
#       que ha dado esta puerta.
#
#   01-AUDITORIA/tools/         inventario_universo.py
#       Y este ultimo  —MEDIDO por su propio docstring—  explica por que esta
#       donde esta:  "POR QUE ESTA EN 01-AUDITORIA Y NO EN tools/".  O sea que hay
#       una razon escrita  y el coste de ignorarla era invisible.
#
# Ninguno se puede dejar fuera "porque no es lo habitual":  la razon por la que un
# directorio NO se declara tiene que ser una razon  —por ejemplo "aqui hay fuente
# del kernel, no herramientas"—  y estos tres no la tienen.
# MEDIDO 2026-10-04:  un SETIMO directorio,  y este con un nombre que la puerta
# NO puede encontrar.
#
#     revkit/     33 ejecutables   (atomrom.py, bootcheck.py, btfsnap.py, check.sh,
#                                  cn7.py, cn8.py, gfx8blocks.py, gputel.py, klog.py,
#                                  pm4dec.py, pte.py, pub.sh, sello.py, …)
#
# Los CATORCE nombres que el ledger de docs/TOOLS-STATUS.md cita y que no
# existian en ninguna de las seis rutas anteriores estan aqui.  Los catorce
# existen hoy.  Eso son 19 pares de entrada-documento sin herramienta.
#
# Y EL HUECO DE LA PUERTA,  QUE ES DEL TAMANO DEL FALLO:
# `directorios_no_declarados()` busca directorios LLAMADOS "tools".  revkit no se
# llama tools,  de modo que anadirlo aqui no lo hacechequeable por esa via:  la
# puerta sigue sin poder distinguir "todo declarado" de "todo declarado Y todo lo
# que existe".  El fallo ya ha pasado cuatro veces por la misma causa  —nadie
# comparo la declaracion con el arbol—  y esta vez la comparacion que falta es al
# reves:  no que exista algo no declarado,  sino que ESTE declarado exista.
#
# Por eso la puerta tiene las dos mitades:
#   · lo declarado que no EXISTE  (un nombre mal escrito pasa desapercibido)
#   · lo que existe y no esta declarado,  entre los directorios llamados "tools"
# Y las dos mitades tienen su control negativo.  La segunda sigue SIN cubrir los
# directorios de herramientas que no se llaman "tools":  eso se declara aqui,  no
# se disimula.
TOOL_DIRS = ("tools", "08-ARQUITECTURA/tools",
             "04-IMPLEMENTACION/rx550-driver/tools",
             "04-IMPLEMENTACION/tools",
             "09-POWER-CLOCKS/tools",
             "01-AUDITORIA/tools",
             "revkit")


def directorios_no_declarados(repo, skip=(".git", "RESEARCH", "node_modules",
                                          "__pycache__")):
    """Todo directorio llamado `tools` del arbol que no este en TOOL_DIRS.

    MEDIDO 2026-10-04.  ESTA ES LA PUERTA que faltaba,  y nace de un fallo que ya
    ha pasado DOS VECES:

      · la primera version de este fichero escaneaba solo  tools/
      · despues se anadio  08-ARQUITECTURA/tools/  porque tres herramientas se
        habian movido ahi  y el registro las reportaba como perdidas
      · y un TERCER directorio aparecio  —rx550-driver/tools/,  con seis
        ejecutables  entre ellos el verificador del manifiesto del corpus—  y
        nadie lo anadio,  porque nada comparaba el arbol con la tupla.

    La tupla es una DECLARACION  y el arbol es la MEDIDA.  Si divergen,  el
    registro esta incompleto  y no hay forma de que eso se note mirando el
    fichero:  el numero que sale es el de lo que se veia.

    El alcance de la busqueda va en el valor de retorno  —una tupla con
    `encontrados` y `faltan`—  porque  "no he encontrado nada"  sin decir donde se
    ha mirado no es un resultado:  es un olvido.
    """
    vistos = []
    faltan = []
    for dirpath, dirnames, filenames in os.walk(repo):
        rel = os.path.relpath(dirpath, repo)
        dirnames[:] = [d for d in dirnames
                       if d not in skip and not d.startswith(".")]
        if os.path.basename(dirpath) != "tools":
            continue
        # `RESEARCH/` puede contener arboles de kernel con directorios tools:  no
        # son herramientas de ESTE proyecto y no pueden registrarse.
        if rel.split(os.sep)[0] in ("RESEARCH", "rx550-upstream-7.2.8"):
            continue
        vistos.append(rel.replace(os.sep, "/"))
        if rel.replace(os.sep, "/") not in TOOL_DIRS:
            faltan.append(rel.replace(os.sep, "/"))
    return vistos, faltan


def declarados_que_no_existen(repo):
    """Los directorios DECLARADOS en TOOL_DIRS que no existen.

    MEDIDO 2026-10-04.  Esta es la otra mitad de la puerta,  y falta por el mismo
    motivo que la primera:  la tupla es una DECLARACION y el arbol es la MEDIDA.

    Sin esta comprobacion,  escribir "08-ARQUITECTURA/tools" en vez de
    "08-ARQUITECTURA/tools "  —con un espacio—  deja un directorio real fuera de la
    cobertura  y la puerta se queda verde:  ella misma busca directorios por NOMBRE
    y no mira su propia tupla.

    Y el alcance de la cobertura queda escrito,  porque un alcance que no se dice
    no se puede auditar:  esto NO encuentra directorios de herramientas que no se
    llamen "tools".  `revkit` no se llama "tools",  y esta es la razon por la que
    su inclusion en TOOL_DIRS es una DECLARACION responsable y no un
    descubrimiento automatico.
    """
    faltan = []
    for rel in TOOL_DIRS:
        if not os.path.isdir(os.path.join(repo, rel)):
            faltan.append(rel)
    return TOOL_DIRS, faltan


def inventory(repo):
    out = []
    for rel in TOOL_DIRS:
        tdir = os.path.join(repo, rel)
        if not os.path.isdir(tdir):
            continue
        for fn in sorted(os.listdir(tdir)):
            p = os.path.join(tdir, fn)
            if not os.path.isfile(p) or fn.endswith(".pyc") or fn == "ideas.txt":
                continue
            t = Tool(p)
            if not t.is_source:
                continue
            t.dir = rel
            out.append(parse_tool(t, repo))
    return out


def run_selftests(tools, timeout=90):
    """
    Run each tool's own self-test, and REFUSE to run one that does not declare
    itself read-only.

    The refusal is the point.  This executes code written by other sessions, in
    a tree where five sessions work at once and where the standing constraint is
    no MMIO, no module load, no sysfs write.  A tool whose header does not
    declare WORK_CLASS / WRITE_EXECUTION is running unclassified, and unclassified
    is exactly how a forbidden operation gets run by accident.
    """
    results = {}
    for t in tools:
        # read the WHOLE file, not the head: `--selftest` in a tool with a long
        # docstring lives far past the first 6 kB, and reading only the head
        # made docscan.py look like it had no self-test when it has 13 checks.
        head = _read(t.path)
        is_self = os.path.abspath(t.path) == os.path.abspath(__file__)

        blocked = []
        if not is_self:
            if FORBIDDEN_KV.search(head):
                blocked.append("declares a write or MMIO scope")
            if FORBIDDEN_CALL.search(head):
                blocked.append("contains an invocation-shaped forbidden operation")
        else:
            blocked.append("this file is the checker; it does not check itself")

        declares = declares_read_only(head)

        if blocked and not is_self:
            results[t.name] = {"status": "REFUSED_UNSAFE",
                               "reason": blocked[0], "rc": None, "secs": None}
            continue
        if not t.selftest_arg:
            results[t.name] = {"status": "NO_SELFTEST", "reason": None,
                               "rc": None, "secs": None}
            continue
        if not declares:
            results[t.name] = {"status": "REFUSED_UNDECLARED",
                               "reason": "no WORK_CLASS / WRITE_EXECUTION in header",
                               "rc": None, "secs": None}
            continue

        if is_self:
            results[t.name] = {"status": "SELF", "reason": "the checker",
                               "rc": None, "secs": None}
            continue

        argv = [sys.executable, t.path, t.selftest_arg] if t.kind == "py" \
            else (["bash", t.path, t.selftest_arg] if t.kind == "sh"
                  else [t.path, t.selftest_arg])
        t0 = time.time()
        try:
            r = subprocess.run(argv, capture_output=True, text=True,
                               timeout=timeout, cwd=os.path.dirname(t.path))
            rc, out = r.returncode, (r.stdout + r.stderr)
        except subprocess.TimeoutExpired:
            rc, out = None, "TIMEOUT after %ds" % timeout
        except OSError as exc:
            rc, out = None, "OSERROR %s" % exc
        dt = time.time() - t0

        if rc is None:
            status = "TIMEOUT"
        elif rc == 0:
            status = "PASS"
        elif "FAIL" in out or "FALLO" in out:
            status = "FAIL"
        else:
            # non-zero without a declared FAIL is still not a pass.  Recorded as
            # its own status so it is never rounded up to PASS.
            status = "NONZERO"
        results[t.name] = {"status": status, "rc": rc, "secs": round(dt, 2),
                           "reason": None,
                           "tail": (out.strip().splitlines() or [""])[-1][:80]}
    return results


# --------------------------------------------------------------------------
# QUIEN POSEE UNA HERRAMIENTA.   MEDIDO 2026-10-04.
# --------------------------------------------------------------------------
#
# `cross_reference()` atribuia `doc_tl` a la ULTIMA entrada que citaba el nombre:
#
#     for tid, names in entries.items():
#         if cands & names:
#             t.doc_tl = tid          # sin romper: gana la ultima
#
# MEDIDO sobre docs/TOOLS-STATUS.md tal y como esta:  65 nombres distintos
# citados, 85 citas, y 37 de esas 85 son NO UNICAS  -- 17 nombres citados en mas
# de una entrada, y uno de ellos en cuatro.  El 43% de las citas del ledger
# compiten entre si, y el ganador lo decide el ORDEN del documento.
#
# El orden del documento no es una propiedad del contrato.  La que si existe esta
# escrita en el propio ledger:  una entrada declara cual es su SUJETO en la linea
# de titulo, con la forma
#
#     ## TL-40 · `citations.py` -- resolver cada `fichero.c:N` ...
#
# y el titulo nombra la herramienta DE LA QUE TRATA LA ENTRADA, mientras que una
# mencion dentro del cuerpo nombra la herramienta de la que se esta hablando.  No
# son lo mismo, y el codigo los trataba igual.
#
# MEDIDO que la regla del sujeto reproduce el arreglo historico.  TL-47 registra
# las ocho herramientas que quedaron mal atribuidas por el `## TL-46` duplicado,
# con la entrada correcta de cada una.  Con esta regla:  siete salen en la entrada
# que TL-47 dice, y `ipver_zero.py` aparece en TL-52  -- que TL-47 daba por
# perdida porque TL-52 estaba dentro del bloque duplicado.  Ocho de ocho.
#
# MEDIDO el efecto sobre las 65 herramientas documentadas:  antes 45 correctas y
# 13 equivocadas;  despues 58 correctas y 0 equivocadas.  La cobertura
# (`in_docs`) no se mueve, porque esa la decide docs_index() por union de nombres
# citados y este bloque no la toca.
#
# TRES NIVELES, y el tercero NO ATRIBUYE:
#
#   O1 SUJETO   la linea de titulo nombra la herramienta.  Es el nivel mas fuerte
#               porque es la unica senal que el ledger da sobre DE QUE entrada
#               trata la entrada.  Empareja por STEM y no por nombre entero,
#               porque 23 de las 84 entradas escriben el sujeto sin extension
#               (`## TL-12 · `docscan``);  con el nombre entero no se ven, y eso
#               hacia que `docscan.py` no tuviera entrada propia y se le colgara
#               a la ultima entrada que lo mencionara.
#   O2 SOURCE   el bloque de contrato declara `SOURCE <fichero>`.  MEDIDO:  18
#               entradas lo declaran, ninguna declara mas de uno, y de las 20
#               herramientas que tienen LAS DOS senal las 20 coinciden.  Cero
#               contradicciones.  En el ledger de hoy O2 no llega a decidir NADA
#               -- nunca hay una herramienta con SOURCE y sin sujeto -- y se
#               queda como unico respaldo que no depende del titulo.
#   O3 MENCION  el nombre aparece en otra parte de la entrada.  MENCIONAR no es
#               POSYGER:  TL-16 dice que `reg_census.py` es una etapa de la
#               cadena de `pipeline.py`, y eso no hace de TL-16 la entrada de
#               pipeline.py.  Una herramienta solo mencionada se queda en
#               doc_tl=None, con doc_tl_level=NO_OWNED y la lista de entradas que
#               la mencionan, para que el None diga POR QUE.
#
# CUANDO DOS ENTRADAS EMPATAN EN EL MISMO NIVEL no se elige ninguna:  se reporta
# el conjunto.  MEDIDO:  TL-24 declara de si mismo "TL-14 es la entrada canonica
# de msg_census", y TL-57 y TL-59 explican por que son dos entradas y por que no
# se fusionaron.  El ledger ya resolvio los dos casos en prosa.  Una regla que
# vuelve a decidir por posicion los deshace, y ademas tira el motivo.
#
# LO QUE ESTA REGLA NO ARREGLA, DICHO:
#   · empareja por NOMBRE DE FICHERO, asi que dos ficheros homonimos en
#     directorios distintos reciben la misma atribucion.  MEDIDO:  hoy hay tres
#     pares -- `contradict.py`, `fingerprint.py` y `xref.py`, cada uno en tools/ y
#     en 08-ARQUITECTURA/tools/.  Discriminar por ruta exigiria que el ledger
#     citara rutas, y hoy las cita sin extension y sin ruta en 23 entradas.
#   · no toca `docs_index()`, asi que la COBERTURA y la lista de huerfanos siguen
#     saliendo del diccionario por nombre.  La cobertura no cambia con este
#     bloque:  medido identico antes y despues, 65 de 194.

TL_HEADER_RE = re.compile(r"^(## TL-\d+[^\n]*)\n", re.M)
TL_ID_RE = re.compile(r"## (TL-\d+)")
# El sujeto del titulo: cualquier token entre acentos graves.  No se exige
# extension a proposito  --  es justamente la extension lo que falta en 23
# entradas.  Un token que no sea una herramienta no puede producir una
# atribucion falsa, porque esto solo se consulta con el stem de una herramienta
# real y del inventario.
TL_SUBJECT_RE = re.compile(r"`([A-Za-z0-9_.\-]+)`")
TL_SOURCE_RE = re.compile(r"^\s*SOURCE\s+(\S+)", re.M)
TL_BACKTICK_TOOL_RE = re.compile(r"`([A-Za-z0-9_./\-]+\.(?:py|c|sh))`")
TL_NAME_RE = re.compile(r"[A-Za-z0-9_.\-]+\.(?:py|c|sh)")


def _stem(name):
    return name.rsplit(".", 1)[0]


def tl_blocks(repo):
    """Los bloques TL-nn del ledger, EN ORDEN DE FICHERO y con repeticiones.

    MEDIDO que aqui es donde se perdia el defecto:  el parser anterior construia
    un DICCIONARIO, de modo que una entrada repetida SOBRESCRIBE a la anterior y
    todo lo que va entre las dos copias queda absorbido dentro de ella, sin que
    nada lo dijera.  Por eso este parser devuelve una LISTA y no un diccionario:
    la duplicacion se ve en el llamante, donde se puede reportar, en vez de
    desaparecer aqui.
    """
    p = os.path.join(repo, "docs", "TOOLS-STATUS.md")
    if not os.path.exists(p):
        return []
    parts = re.split(TL_HEADER_RE, _read(p))
    out = []
    for i in range(1, len(parts), 2):
        out.append({"tl": TL_ID_RE.match(parts[i]).group(1),
                    "header": parts[i], "body": parts[i + 1]})
    return out


def entradas_duplicadas(repo):
    """Entradas TL-nn que aparecen MAS DE UNA VEZ, y si son identicas byte a byte.

    MEDIDO 2026-10-04.  Esta puerta no existia, y la que si existe
    (`revkit/cn8.py`, lineas 520-538) compara LINEAS DE CABECERA, no
    IDENTIDADES DE ENTRADA.  Medido sobre dos vectores con el mismo par de
    herramientas:

      · cabecera reinsertada byte a byte  ->  cn8 la ve.  toolreg no pierde
        cobertura, porque las dos copias citan los mismos nombres.
      · MISMO `## TL-nn` con OTRO TEXTO    ->  cn8 NO la ve, la puerta queda
        VERDE, y toolreg pierde una herramienta DOCUMENTADA:  en el vector, `a.py`
        pasa a figurar como UNDOCUMENTED y `c.py` se queda con TL-01.

    La segunda es la peor de las dos y era la que no tenia puerta.  Por eso esta
    mira la IDENTIDAD, y el texto se usa solo para decir SI las copias coinciden.
    `identical=False` es el caso que hay que mirar:  es el unico en el que la
    sobreescritura pierde cobertura, porque las copias no citan lo mismo.
    """
    by_tl = {}
    for b in tl_blocks(repo):
        by_tl.setdefault(b["tl"], []).append(b)
    out = []
    for tid, blocks in sorted(by_tl.items()):
        if len(blocks) < 2:
            continue
        digests = sorted({hashlib.sha256(
            (b["header"] + "\n" + b["body"]).encode()).hexdigest()[:16]
            for b in blocks})
        out.append({"tl": tid, "copies": len(blocks),
                    "identical": len(digests) == 1, "digests": digests})
    return out


def tl_ownership(repo):
    """stem de herramienta -> (entrada que la posee, nivel, entradas candidatas).

    El valor de la entrada es None cuando NINGUNA entrada posee la herramienta, y
    tambien cuando varias empatan en el mismo nivel.  Esos dos casos se distinguen
    por el segundo elemento, y por eso los dos se reportan en vez de repartirse.
    """
    subj, srcd, ment = {}, {}, {}
    for b in tl_blocks(repo):
        for tok in TL_SUBJECT_RE.findall(b["header"]):
            subj.setdefault(_stem(tok), set()).add(b["tl"])
        for m in TL_SOURCE_RE.finditer(b["body"]):
            base = os.path.basename(m.group(1))
            if TL_NAME_RE.fullmatch(base):
                srcd.setdefault(_stem(base), set()).add(b["tl"])
        for tok in TL_BACKTICK_TOOL_RE.findall(b["header"] + "\n" + b["body"]):
            ment.setdefault(_stem(os.path.basename(tok)), set()).add(b["tl"])

    own = {}
    for stem in set(subj) | set(srcd) | set(ment):
        if stem in subj:
            level, cands = "O1_SUBJECT", sorted(subj[stem])
        elif stem in srcd:
            level, cands = "O2_SOURCE", sorted(srcd[stem])
        else:
            # MENCION Y NADA MAS.  doc_tl=None y se dice DONDE se le menciona,
            # porque un None sin motivo no se puede corregir.
            own[stem] = (None, "NO_OWNED", sorted(ment.get(stem, [])))
            continue
        own[stem] = (cands[0] if len(cands) == 1 else None,
                     level if len(cands) == 1 else "MULTI_" + level,
                     cands)
    return own


def docs_index(repo):
    """TL-nn -> the tool names it cites, and which tool names appear in it."""
    p = os.path.join(repo, "docs", "TOOLS-STATUS.md")
    if not os.path.exists(p):
        return {}
    txt = _read(p)
    entries = {}
    # Split on the TL-nn HEADERS, keeping the header line itself.
    #
    # The first version used re.split(r"^## (TL-\d+)[^\n]*\n") which CONSUMES the
    # header, and the header is exactly where the tool's name is written:
    #     ## TL-11 · `ipsolve` — el gate que faltaba para C-011
    # so every entry came back with an empty name set and the whole cross
    # reference silently reported zero coverage.  A tool whose name lives in the
    # heading is the normal layout, not an edge case.
    parts = re.split(r"^(## TL-\d+[^\n]*\n)", txt, flags=re.M)
    for i in range(1, len(parts), 2):
        header, body = parts[i], parts[i + 1]
        tid = re.match(r"## (TL-\d+)", header).group(1)
        blob = header + "\n" + body
        # accept a BARE filename and a path-qualified one.  The first version
        # matched only the bare form, so every entry written as
        # `tools/reg_resolve.py` read as undocumented and coverage was
        # under-reported: 9 of 29 instead of the real number.
        names = set(re.findall(r"`([A-Za-z0-9_.\-]+\.(?:py|c|sh))`", blob))
        for pref in re.findall(r"`([A-Za-z0-9_./\-]+\.(?:py|c|sh))`", blob):
            names.add(os.path.basename(pref))
        # MEDIDO 2026-10-04:  esto era `entries[tid] = names`, y una entrada
        # repetida SOBRESCRIBE a la anterior:  no se perdia cobertura porque las
        # dos copias citaban los mismos nombres, pero en cuanto las copias citan
        # distinto se perdia una herramienta DOCUMENTADA sin que nada lo dijera
        # (medido en el vector de tl_ownership: `a.py` -> UNDOCUMENTED con la
        # puerta de duplicados de revkit/cn8.py en VERDE).  La union conserva las
        # dos.  La DUPLICACION no se deja de ver por esto:  se reporta, en
        # entradas_duplicadas().
        entries[tid] = entries.get(tid, set()) | names
    return entries


def cross_reference(repo, tools):
    """Both directions: undocumented tools, and TL entries with no tool."""
    entries = docs_index(repo)
    own = tl_ownership(repo)
    cited = set()
    for names in entries.values():
        cited |= names

    for t in tools:
        cands = {t.name}
        if t.kind == "c":
            cands.add(t.stem + ".c")
        t.in_docs = bool(cands & cited)
        # MEDIDO 2026-10-04:  esto era un `for` que se quedaba con la ultima
        # entrada que citaba el nombre.  Ver tl_ownership() para la cuenta y para
        # el porque.  Un nombre citado en N entradas ya no se resuelve por
        # posicion:  o hay una entrada que lo posee como sujeto, o no hay ninguna
        # y eso se dice con doc_tl_level, en vez de repartirse en silencio.
        _own = own.get(t.stem)
        t.doc_tl = _own[0] if _own else None
        t.doc_tl_level = _own[1] if _own else "NO_OWNED"
        t.doc_tl_all = _own[2] if _own else []

    documented_names = cited
    orphans = []
    for tid, names in sorted(entries.items()):
        for n in sorted(names):
            if n not in documented_names:
                continue
            stem = n.rsplit(".", 1)[0]
            if not any(t.name == n or (t.kind == "c" and t.stem + ".c" == n)
                       for t in tools):
                orphans.append((tid, n))
    return entries, orphans


# --------------------------------------------------------------------------
# self-test
# --------------------------------------------------------------------------

def _fixture(root, tools_spec):
    """Build a tools/ tree with known properties."""
    tdir = os.path.join(root, "tools")
    os.makedirs(tdir, exist_ok=True)
    for name, body in tools_spec.items():
        with open(os.path.join(tdir, name), "w", encoding="utf-8") as fh:
            fh.write(body)
    os.makedirs(os.path.join(root, "docs"), exist_ok=True)


SELFTEST_FIXTURE = {
    # declares safety, has a self-test, declares limits: the GOOD case
    "good_tool.py": (
        '#!/usr/bin/env python3\n'
        '"""good_tool.py — does a thing.\n\n'
        'WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE\n\n'
        'LO QUE NO PROBABA: nothing.\n"""\n'
        'import sys\n'
        'def selftest():\n'
        '    print("RESULT: OK")\n'
        '    return 0\n'
        'def main(argv):\n'
        '    if "--selftest" in argv:\n'
        '        return selftest()\n'
        '    return 0\n'
        'if __name__ == "__main__":\n'
        '    sys.exit(main(sys.argv[1:]))\n'
    ),
    # declares safety, self-test FAILS: must not be rounded up to a pass
    "failing_tool.py": (
        '#!/usr/bin/env python3\n'
        '"""failing_tool.py — declares a self-test that fails.\n\n'
        'WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE\n"""\n'
        'import sys\n'
        'def selftest():\n'
        '    print("RESULT: FAILED")\n'
        '    return 1\n'
        'def main(argv):\n'
        '    if "--selftest" in argv:\n'
        '        return selftest()\n'
        '    return 0\n'
        'if __name__ == "__main__":\n'
        '    sys.exit(main(sys.argv[1:]))\n'
    ),
    # no safety declaration: must be REFUSED, never executed
    "unclassified_tool.py": (
        '#!/usr/bin/env python3\n'
        '"""unclassified_tool.py — says nothing about what it does.\n\n'
        'Lo que NO hace: nothing.\n"""\n'
        'import sys\n'
        'def main(argv):\n'
        '    if "--selftest" in argv:\n'
        '        raise SystemExit("I RAN AND I SHOULD NOT HAVE")\n'
        '    return 0\n'
        'if __name__ == "__main__":\n'
        '    sys.exit(main(sys.argv[1:]))\n'
    ),
    # explicitly unsafe: must be REFUSED on the marker, not on the declaration
    "unsafe_tool.py": (
        '#!/usr/bin/env python3\n'
        '"""unsafe_tool.py — does a forbidden thing.\n\n'
        'WRITE_EXECUTION=WRITE · MMIO_WRITE=YES\n"""\n'
        'import sys\n'
        'def main(argv):\n'
        '    if "--selftest" in argv:\n'
        '        raise SystemExit("I RAN AND I SHOULD NOT HAVE")\n'
        '    return 0\n'
        'if __name__ == "__main__":\n'
        '    sys.exit(main(sys.argv[1:]))\n'
    ),
    # has no self-test at all: MISSING, never PASS
    "notool_test.py": (
        '#!/usr/bin/env python3\n'
        '"""notool_test.py — no self-test here.\n\n'
        'WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE\n"""\n'
        'import sys\n'
        'if __name__ == "__main__":\n'
        '    sys.exit(0)\n'
    ),
}

FIXTURE_DOCS = (
    "# TOOLS-STATUS\n\n"
    "## TL-01 · `good_tool.py` — VALIDATED\n\n```\nVALIDADO\n```\n\n"
    "## TL-02 · `tool_that_does_not_exist.py` — VALIDATED\n\n```\nVALIDADO\n```\n"
)


def run_selftest():
    print("%s %s -- self-test" % (TOOL, VERSION))
    print("  " + "-" * 62)
    fails = 0
    checks = 0

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        _fixture(td, SELFTEST_FIXTURE)
        with open(os.path.join(td, "docs", "TOOLS-STATUS.md"), "w",
                  encoding="utf-8") as fh:
            fh.write(FIXTURE_DOCS)

        tools = inventory(td)
        st = run_selftests(tools, timeout=30)

        want = {
            "good_tool.py": "PASS",
            "failing_tool.py": "FAIL",
            "unclassified_tool.py": "REFUSED_UNDECLARED",
            "unsafe_tool.py": "REFUSED_UNSAFE",
            "notool_test.py": "NO_SELFTEST",
        }
        for name, expect in sorted(want.items()):
            checks += 1
            got = st.get(name, {}).get("status")
            if got == expect:
                print("  OK    %-24s %s" % (name, got))
            else:
                print("  FAIL  %-24s got %s, expected %s" % (name, got, expect))
                fails += 1

        # the interlock is the whole safety argument, so assert it positively
        checks += 1
        ran_forbidden = any(
            "I RAN AND I SHOULD NOT HAVE" in (st[n].get("tail") or "")
            or (st[n].get("rc") not in (None,) and st[n].get("status", "").startswith("REFUSED"))
            for n in ("unclassified_tool.py", "unsafe_tool.py"))
        refused_both = (st["unclassified_tool.py"]["status"].startswith("REFUSED")
                        and st["unsafe_tool.py"]["status"].startswith("REFUSED"))
        if refused_both:
            print("  OK    neither undeclared nor unsafe tool was executed")
        else:
            print("  FAIL  the safety interlock did not hold")
            fails += 1

        checks += 1
        entries, orphans = cross_reference(td, tools)
        undocumented = sorted(t.name for t in tools if not t.in_docs)
        expect_undoc = ["failing_tool.py", "notool_test.py", "unclassified_tool.py",
                        "unsafe_tool.py"]
        if undocumented == expect_undoc:
            print("  OK    coverage finds exactly the 4 undocumented tools")
        else:
            print("  FAIL  undocumented = %s, expected %s" % (undocumented, expect_undoc))
            fails += 1

        checks += 1
        if ("TL-02", "tool_that_does_not_exist.py") in orphans:
            print("  OK    a TL entry naming a tool that does not exist is flagged")
        else:
            print("  FAIL  orphan TL entry not detected: %s" % (orphans,))
            fails += 1

        checks += 1
        good = [t for t in tools if t.name == "good_tool.py"][0]
        if good.doc_tl == "TL-01":
            print("  OK    a documented tool is attributed to its TL entry")
        else:
            print("  FAIL  attribution wrong: %r" % good.doc_tl)
            fails += 1

        # ── LA PUERTA DE DIRECTORIOS, Y SUS CONTROLES NEGATIVOS ─────────────
        #
        # MEDIDO 2026-10-04.  Esta puerta nace de un fallo que ya ha pasado DOS
        # VECES por la misma causa:  el alcance de "donde viven las herramientas"
        # es una DECLARACION  —TOOL_DIRS—  y nadie la compara con el arbol.  La
        # primera vez se escaneaba solo tools/;  la segunda se anadio
        # 08-ARQUITECTURA/tools/ porque tres herramientas movidas se reportaban
        # como perdidas;  y un TERCER  —y luego tres mas—  aparecieron sin que
        # nadie los anadiera.
        #
        # El vector se construye con un arbol real en un temporal,  y se exige
        # que la puerta LO DETECTE.  Una puerta que solo se ejecuta sobre el
        # arbol del proyecto  —donde hoy esta verde—  no demuestra que sepa
        # decir que no.
        import tempfile as _tf
        with _tf.TemporaryDirectory() as td2:
            # MEDIDO por este self-test:  la primera version de este temporal
            # creaba SOLO `tools`  y `caja/tools`,  y el vector de la otra mitad
            # de la puerta exigia que faltara un unico directorio declarado.  Pero
            # con un temporal asi  los SEIS declared que no existen alli tambien
            # faltan,  de modo que el vector afirmaba algo falso y no podia
            # distinguish "no he mirado" de "no hay".  Un vector que espera un
            # numero que no puede ocurrir no mide nada.
            #
            # Ahora el temporal contiene DOS rutas declaradas  —`tools` y
            # `08-ARQUITECTURA/tools`—,  una que existe y no esta declarada
            # (`caja/tools`),  y una excluida por la regla de `RESEARCH`.  Asi
            # los tres casos se distinguen.
            os.makedirs(os.path.join(td2, "tools"))
            os.makedirs(os.path.join(td2, "08-ARQUITECTURA", "tools"))
            os.makedirs(os.path.join(td2, "caja", "tools"))
            os.makedirs(os.path.join(td2, "RESEARCH", "linux", "tools"))
            with open(os.path.join(td2, "caja", "tools", "x.py"), "w") as fh:
                fh.write("#!/usr/bin/env python3\n")

            checks += 1
            vistos, faltan = directorios_no_declarados(td2)
            if ("caja/tools" in vistos and "caja/tools" in faltan
                    and "tools" not in faltan
                    and not any(v.startswith("RESEARCH") for v in vistos)):
                print("  OK    la puerta ve 3 directorios y senala el que no esta declarado")
            else:
                print("  FAIL  la puerta no senala caja/tools: vistos=%r faltan=%r"
                      % (vistos, faltan))
                fails += 1

            # CONTROL NEGATIVO:  la misma llamada con un arbol sin directorios
            # escondidos tiene que devolver una lista vacia de faltantes.  Si
            # devolviera algo, la puerta estaria avisando de cualquier cosa.
            with _tf.TemporaryDirectory() as td3:
                os.makedirs(os.path.join(td3, "tools"))
                checks += 1
                v3, f3 = directorios_no_declarados(td3)
                if f3 == [] and "tools" in v3:
                    print("  OK    sin directorios escondidos, la puerta no reporta ninguno")
                else:
                    print("  FAIL  falso positivo: %r" % (f3,))
                    fails += 1

            # LA OTRA MITAD:  lo DECLARADO que no existe.
            # El control negativo es el que importa:  sin un nombre mal escrito,
            # "no falta nada" y "no he mirado" darian lo mismo.
            checks += 1
            decl, ausentes = declarados_que_no_existen(td2)
            esperados = [d for d in TOOL_DIRS
                         if not os.path.isdir(os.path.join(td2, d))]
            if (set(ausentes) == set(esperados)
                    and "tools" not in ausentes
                    and "08-ARQUITECTURA/tools" not in ausentes
                    and ausentes):
                print("  OK    la mitad DECLARADO-que-no-existe:  %d de %d,  y"
                      " las dos que si existen no aparecen" % (len(ausentes),
                                                                len(decl)))
            else:
                print("  FAIL  declarados ausentes mal:  %r,  esperados %r"
                      % (sorted(ausentes), sorted(esperados)))
                fails += 1

            checks += 1
            with _tf.TemporaryDirectory() as td4:
                os.makedirs(os.path.join(td4, "tools"))
                # MEDIDO:  la primera version de esta linea traia un
                # `declarados_que_no_exclarados(td4) if False else …`  —un
                # `if False:` que se lee como si evaluara algo.  Es el mismo
                # antipatron que se acaba de quitar de refs_repair.py:  codigo
                # que parece hacer trabajo y no lo hace,  y que dentro de tres
                # meses alguien activa sin saber por que estaba apagado.
                _d, aus4 = declarados_que_no_existen(td4)
                if len(aus4) == len(TOOL_DIRS) - 1:
                    print("  OK    en un arbol vacio se declaran %d ausentes"
                          % len(aus4))
                else:
                    print("  FAIL  ausentes=%d de %d declarados"
                          % (len(aus4), len(TOOL_DIRS)))
                    fails += 1

            # Y EL ALCANCE, que va en el valor de retorno:  "no he encontrado
            # nada" sin decir donde se ha mirado no es un resultado.
            checks += 1
            # MEDIDO:  este vector comprobaba `len(vistos) == 2`  y al ampliar
            # el temporal salia 3.  Contar el alcance no es DECLARARLO:  un
            # numero no dice QUE se ha mirado,  y si el alcance cambia el vector
            # falla sin que nadie sepa que ha cambiado.  Ahora se compara el
            # CONJUNTO,  que es lo que el valor de retorno promete,  y se nombra.
            # Y como CONJUNTO,  no como lista.  MEDIDO:  la primera version
            # comparaba una lista y el vector fallo por el ORDEN  —os.walk no
            # garantiza ninguno—  cuando lo que queria comprobar era la
            # pertenencia.  Un vector que falla por el orden del recorrido del
            # sistema de ficheros no mide el alcance:  mide el recorrido.
            if set(vistos) == {"08-ARQUITECTURA/tools", "caja/tools", "tools"}:
                print("  OK    la puerta declara su alcance:  %s  —  y RESEARCH"
                      " no aparece" % ", ".join(sorted(vistos)))
            else:
                print("  FAIL  alcance inesperado: %r" % (sorted(vistos),))
                fails += 1

    print("  " + "-" * 62)
    print("  %d checks, %d failures" % (checks, fails))
    print("  RESULT: %s" % ("OK" if fails == 0 else "FAILED"))
    print("")
    print("  NOTA: pasar esto NO demuestra que la salida de una herramienta sea")
    print("        correcta. Comprueba que tenga forma de decirlo y que su propio")
    print("        self-test pase. El juicio sobre la salida sigue siendo de quien lee.")
    return 1 if fails else 0


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

# MEDIDO 2026-10-04 (hallazgo 1051).  Esto era  default="."  y luego
#     repo = os.path.abspath(args.repo)
# o sea: la raiz del repositorio era EL DIRECTORIO DE TRABAJO.  Medido: la misma
# invocacion desde la raiz y desde tools/ daba inventarios distintos.
#
# Y es el defecto en la puerta que CAZARIA los de otras herramientas: la linea 485
# ejecuta cada self-test con cwd=os.path.dirname(t.path), que es exactamente el
# contexto donde un default de cwd rompe.  Es decir: la puerta corre las
# herramientas en el contexto que las delata y no puede delatarse a si misma.
#
# La regla ya estaba escrita en este arbol, en tools/constmap.py:116:
#     "The repo root comes from __file__, NEVER from the current directory."
# y aqui no se cumplia.  --repo sigue aceptando un valor explicito; lo que cambia es
# que el valor por defecto ya no depende de donde se escriba el comando.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def main(argv):
    ap = argparse.ArgumentParser(
        prog="toolreg",
        description="registry for tools/, and the check that it stays true")
    ap.add_argument("--repo", default=REPO_ROOT,
                    help="raiz del repositorio.  Por defecto es la de ESTE fichero, "
                         "derivada de __file__, NUNCA el directorio de trabajo.")
    ap.add_argument("--undocumented", action="store_true",
                    help="only the tools that exist and are not in TOOLS-STATUS")
    ap.add_argument("--no-selftest", action="store_true",
                    help="inventory and coverage only; execute nothing")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--timeout", type=int, default=90)
    ap.add_argument("--version", action="version", version="%s %s" % (TOOL, VERSION))
    args = ap.parse_args(argv)

    if args.selftest:
        return run_selftest()

    repo = os.path.abspath(args.repo)
    tools = inventory(repo)
    if not tools:
        sys.stderr.write("toolreg: no source tools under %s/tools\n" % repo)
        return 2

    st = {} if args.no_selftest else run_selftests(tools, timeout=args.timeout)
    entries, orphans = cross_reference(repo, tools)
    undoc = [t for t in tools if not t.in_docs]

    if args.json:
        print(json.dumps({
            "tool": TOOL, "version": VERSION, "repo": repo,
            "count": len(tools),
            "tools": [{
                "name": t.name, "kind": t.kind, "bytes": t.size,
                "purpose": t.purpose,
                "declares_limits": t.declares_limits,
                "declares_safety": t.declares_safety,
                "in_docs": t.in_docs, "doc_tl": t.doc_tl,
                "selftest": st.get(t.name, {}).get("status"),
                "selftest_rc": st.get(t.name, {}).get("rc"),
                "selftest_secs": st.get(t.name, {}).get("secs"),
                "selftest_reason": st.get(t.name, {}).get("reason"),
            } for t in tools],
            "undocumented": [t.name for t in undoc],
            "orphan_tl_entries": [{"tl": a, "tool": b} for a, b in orphans],
            "duplicate_tl_entries": entradas_duplicadas(repo),
            "attribution": [{"dir": t.dir, "name": t.name, "doc_tl": t.doc_tl,
                             "level": t.doc_tl_level, "all": t.doc_tl_all}
                            for t in tools],
        }, indent=2, sort_keys=True))
        return 0

    if args.undocumented:
        print("%s %s -- undocumented tools" % (TOOL, VERSION))
        print("  %d of %d tools in tools/ appear nowhere in docs/TOOLS-STATUS.md"
              % (len(undoc), len(tools)))
        print("")
        for t in sorted(undoc, key=lambda x: x.name):
            s = st.get(t.name, {})
            print("  %-24s %-5s %7d B  %s"
                  % (t.name, t.kind, t.size, s.get("status") or "-"))
            if t.purpose:
                print("      %s" % t.purpose)
        return 1 if undoc else 0

    print("%s %s" % (TOOL, VERSION))
    print("  " + "-" * 74)
    print("  %d source tools in tools/" % len(tools))
    print("")
    print("  %-24s %-4s %7s  %-18s %-6s %s"
          % ("tool", "kind", "bytes", "selftest", "docs", "TL"))
    print("  " + "-" * 74)
    for t in sorted(tools, key=lambda x: (x.dir, x.name)):
        s = st.get(t.name, {})
        mark = "" if t.dir == "tools" else " (%s)" % t.dir.split("/")[0][:4]
        print("  %-24s %-4s %7d  %-18s %-6s %s"
              % (t.name + mark, t.kind, t.size, s.get("status", "-"),
                 "si" if t.in_docs else "NO", t.doc_tl or "-"))

    by_status = {}
    for t in tools:
        by_status.setdefault(st.get(t.name, {}).get("status", "SKIPPED"), []).append(t.name)
    print("")
    print("  self-test summary")
    for k in sorted(by_status):
        print("    %-20s %d   %s" % (k, len(by_status[k]), ", ".join(sorted(by_status[k])[:4])))

    print("")
    print("  coverage")
    print("    documented in TOOLS-STATUS   %d of %d" % (len(tools) - len(undoc), len(tools)))
    print("    undocumented                 %d" % len(undoc))
    if undoc:
        for t in sorted(undoc, key=lambda x: x.name):
            print("      %-24s %s" % (t.name, t.purpose or ""))
    if orphans:
        print("    TL entries naming a tool that does not exist:")
        for tid, n in orphans:
            print("      %-8s -> %s" % (tid, n))
    dups = entradas_duplicadas(repo)
    print("    duplicate TL entries                  %d" % len(dups))
    for d in dups:
        print("      %-8s x%d  %s  %s"
              % (d["tl"], d["copies"],
                 "byte-identical" if d["identical"] else "** NOT identical **",
                 " ".join(d["digests"])))
    unowned = [t for t in tools if t.doc_tl_level == "NO_OWNED" and t.in_docs]
    multi = [t for t in tools if t.doc_tl_level.startswith("MULTI_")]
    print("    cited but owned by NO entry          %d" % len(unowned))
    for t in sorted(unowned, key=lambda x: x.name):
        print("      %-24s mentioned in %s"
              % (t.name, ", ".join(t.doc_tl_all) or "-"))
    print("    owned by SEVERAL entries             %d" % len(multi))
    for t in sorted(multi, key=lambda x: x.name):
        print("      %-24s %s  <- not resolved by position"
              % (t.name, ", ".join(t.doc_tl_all)))
    limits_missing = [t.name for t in tools if not t.declares_limits]
    safety_missing = [t.name for t in tools if not t.declares_safety]
    if limits_missing:
        print("    no declared LIMITATIONS       %d   %s"
              % (len(limits_missing), ", ".join(sorted(limits_missing)[:5])))
    if safety_missing:
        print("    no WORK_CLASS declaration     %d   %s"
              % (len(safety_missing), ", ".join(sorted(safety_missing)[:5])))
    print("")
    print("  A missing self-test is MISSING, never a pass.  A non-zero exit without a")
    print("  declared FAIL is NONZERO, never a pass.  Coverage is matched by name, so")
    print("  a tool described in prose without its name in backticks reads as uncovered.")
    return 1 if undoc else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

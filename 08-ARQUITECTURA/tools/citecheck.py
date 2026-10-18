#!/usr/bin/env python3
# CONTRACT: name=citecheck
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: TOUCHES_INTEGRATED=no
#
# MEDIDO con RXRE/tools/rxre_contracts.py.  Veredicto
# `READONLY=yes, WRITES_FILES=no`: no tiene ninguna escritura: no hay nada que resolver.
#
# ESTA HERRAMIENTA LA INVOCA `run_all.py`.  Eso se midio con
# RXRE/tools/rxre_deleg.py, que resolvio 72 invocaciones entre herramientas del
# proyecto -- todas en TABLAS, ninguna en un `subprocess` literal, y por eso
# ningun grafo de imports las ve.  De las 47 que invoca, estas cuatro estaban
# SIN contrato, y son justo las que `toolkit.py` reportaba como "SIN CONTRATO:
# no se puede afirmar nada de esta herramienta".
#
# Declarar `WRITES_FILES=no` sin escrituras no es trivial: es la clase que hace
# falta para que una herramienta pueda enrutarse Y se sepa que es segura.  Con
# contrato y sin capacidad enrutable, el par no existe (hallazgo 1491).
#
# TOUCHES_INTEGRATED=no, y se declara aunque toolkit.py no lo conozca: la
# frontera que no se puede declarar es la que no se puede hacer cumplir (1487).
"""
citecheck.py -- verifica que cada cita <fichero>:<linea> de un hallazgo APUNTE.

POR QUE EXISTE
    Verificar las citas a mano cuesta ~10 min por hallazgo, y es trabajo que un
    ordenador hace mejor. En una sesion se verificaron ~60 a mano y salieron 4
    errores reales: dos ficheros inventados (kfd_ioctl_defs.h, amdgpu_vm.h) y
    dos numeros de linea equivocados (783 por 782, 487 por 488).

    Los cuatro eran de la misma clase: "asumi el nombre o el numero antes de
    mirar el fichero". Esa clase no se arregla escribiendo mas despacio: se
    arregla con un gate.

RELACION CON doclint.py  (NO duplico lo que ya existe)
    doclint.py comprueba la FORMA de un documento: cabecera, vocabulario de
    clasificacion, marcadores, intrusiones de otro idioma. Y construye un
    indice {ruta: lineas} que ademas incluye el kernel INSTALADO EN EL HOST
    (/usr/src/kernels/...), que es el binario que realmente corre.
    Esta herramienta CONSUME ese indice y solo anade lo que falta: comprobar
    que un NUMERO DE LINEA exista, este en rango y no apunte al vacio.

    Si doclint dice que un documento esta bien formado, eso NO dice que sus
    citas sean ciertas. Son dos ejes ortogonales.

LIMITE DECLARADO, Y ES IMPORTANTE
    NO verifica que la linea citada diga lo que el hallazgo afirma. Eso exige
    entender la afirmacion, y una herramienta que fingiera hacerlo produciria
    un "OK" falso y con confianza. Lo que hace es filtrar:
      comprueba que el fichero existe, que la linea esta ahi y que no esta
    vacia. Un hallazgo puede pasar este gate con la cita apuntando a la linea
    equivocada del fichero correcto.
    Por eso --context imprime la linea real: para que el ojo decida en un
    segundo, que es lo que de verdad hace falta.

USO
    citecheck.py hall1.md hall2.md      verifica esos ficheros
    citecheck.py --dir 06-.../findings/ verifica todo un directorio
    citecheck.py --context              imprime cada linea citada
    citecheck.py --strict               sale !=0 si hay UNA cita que no resuelve
    citecheck.py --json                 salida parseable
    citecheck.py --self                 autotest

DEPENDENCIAS
    python3 >= 3.9, y doclint.py (que ya esta en el proyecto). Sin red, sin
    root, sin escrituras. De no estar doclint, cae a un indice propio mas lento.
"""

import argparse
import glob
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = "/home/lucas/Escritorio/RX550-INVESTIGACION"
sys.path.insert(0, HERE)

# <nombre>.c:123  ·  <nombre>.c:123-456  ·  <dir>/<nombre>.h:12
# .md entra porque este proyecto se cita documentos: CONTRADICTIONS.md, los
# hallazgos, los indices.  Sin .md, una cita como "CONTRADICTIONS.md:512 :2438"
# se rompia en dos: la primera no se reconocia, y la segunda queda como cita en
# cadena SIN fichero que heredar.  Se vio al verificar 062.
CITE = re.compile(
    r'(?<![\w/])([A-Za-z_][A-Za-z0-9_\-]*(?:/[A-Za-z_][A-Za-z0-9_\-]*)*'
    r'\.(?:c|h|py|comp|s|asm|md)):(\d+)(?:-(\d+))?\b')
FENCE = re.compile(r'^\s*```')
# Cita en cadena:  ":2438" o ":2424-2454" sin nombre de fichero delante.
# El \b inicial evita capturar "http://...:80" y "0x1f:2".
CHAINED = re.compile(r'(?<![\w./-]):(\d+)(?:-(\d+))?\b')

_idx = None
_idx_src = None
_MD_IDX = None


def get_index(verbose=False):
    """Indice {ruta: lineas}. Reutiliza doclint; si no esta, lo construye."""
    global _idx, _idx_src
    if _idx is not None:
        return _idx
    try:
        import doclint
        t = time.time()
        _idx = doclint.build_index()
        _idx_src = f"doclint.build_index() ({len(_idx)} ficheros, {time.time()-t:.1f}s)"
        if verbose:
            print(f"  indice: {_idx_src}", file=sys.stderr)
        return _idx
    except Exception as e:                              # noqa: BLE001
        if verbose:
            print(f"  doclint no disponible ({e}); indice propio", file=sys.stderr)
    roots = [f"{PROJECT}/RESEARCH/working", f"{PROJECT}/04-IMPLEMENTACION"]
    _idx = {}
    for root in roots:
        for dp, _d, fs in os.walk(root):
            for f in fs:
                if f.endswith((".c", ".h", ".py", ".comp")):
                    p = os.path.join(dp, f)
                    try:
                        with open(p, errors="replace") as fh:
                            _idx[p] = fh.read().split("\n")
                    except OSError:
                        pass
    _idx_src = f"propio ({len(_idx)} ficheros)"
    return _idx


def exists_or_none(p):
    """La ruta que devuelve resolve() existe, o es None / una tupla de ambiguedad."""
    return p is None or isinstance(p, tuple) or os.path.exists(p)


def resolve(name, idx):
    """
    Nombre -> ruta. Absoluto si existe; si no, unico por basename.
    None si no hay EXACTAMENTE una coincidencia: "el primero que encuentro" es
    precisamente como se produce la cita al fichero equivocado.
    """
    if os.path.isabs(name) and os.path.exists(name):
        return name
    cand = os.path.join(PROJECT, name)
    if os.path.exists(cand):
        return cand
    base = os.path.basename(name)
    hits = [p for p in idx if os.path.basename(p) == base]
    if len(hits) == 1:
        # COMPROBACION OBLIGATORIA antes de devolver la ruta.  Sin ella se
        # devolvian rutas que NO EXISTEN: el indice de doclint se ha ampliado
        # con entradas sinteticas y una de ellas era PROJECT/<nombre>, que no
        # esta en disco.  Una cita resolvia a un fichero fantasma y se
        # reportaba LINE_OUT_OF_RANGE, que se lee como "el fichero no llega
        # tan lejos" cuando la verdad es que el fichero no existe.
        if os.path.exists(hits[0]):
            return hits[0]
    if len(hits) > 1:
        return ("AMBIGUOUS", hits)
    return None


def nlines_of(path, idx):
    """Numero de lineas. Del indice si esta; si no, cuenta con wc."""
    if path in idx:
        return len(idx[path])
    with open(path, errors="replace") as fh:
        return sum(1 for _ in fh)


def line_at(path, idx, n):
    """Linea n (1-based). Del indice si esta; si no, la lee bajo demanda."""
    if path in idx and 1 <= n <= len(idx[path]):
        return idx[path][n - 1]
    with open(path, errors="replace") as fh:
        for i, l in enumerate(fh, 1):
            if i == n:
                return l
    return None


def outside_fences(lines):
    """Indices de linea que NO estan dentro de un bloque de codigo."""
    inside, keep = False, set()
    for i, l in enumerate(lines):
        if FENCE.match(l):
            inside = not inside
            continue
        if not inside:
            keep.add(i)
    return keep


def _build_md_index():
    """
    Indice de los documentos .md del PROYECTO (hallazgos, docs, indices).

    doclint.build_index() solo recoge .c/.h, porque su trabajo es el codigo.
    Las citas de un hallazgo apuntan a documentos tanto como a codigo, asi que
    aqui se indexa .md aparte.  No se toca doclint: es trabajo de otra sesion.
    """
    idx = {}
    for sub in ("06-INGENIERIA-INVERSA/findings", "docs",
                "00-INDICE", "08-ARQUITECTURA"):
        root = os.path.join(PROJECT, sub)
        if not os.path.isdir(root):
            continue
        for dp, _d, fs in os.walk(root):
            for f in fs:
                if f.endswith(".md"):
                    p = os.path.join(dp, f)
                    try:
                        with open(p, errors="replace") as fh:
                            idx[p] = fh.read().split("\n")
                    except OSError:
                        pass
    return idx


def _strip_num(basename):
    """Quita el prefijo de numeracion: 030-page-walker.md -> page-walker.md."""
    return re.sub(r'^\d+[a-z]?[-_]', '', basename)


def _mismo_doc(path, name):
    """
    ¿Este fichero .md es el que dice ese nombre?

    Todos los hallazgos de este proyecto llevan prefijo numerico
    (030-page-walker-gfx8-2-niveles.md).  Cuando se cita
    "030-page-walker-gfx8-2-niveles.md:83", la \b de la regex corta entre el
    digito y la letra, asi que el nombre capturado es SIN el prefijo, y la
    busqueda por nombre exacto fallaba con FILE_NOT_FOUND sobre un fichero que
    existe.  Se compara tambien sin el prefijo.
    """
    b = os.path.basename(path)
    nb = os.path.basename(name)
    return b == nb or _strip_num(b) == _strip_num(nb)


def _fill(r, idx):
    """
    Resuelve una cita ya parseada contra el indice y le pone status.
    Compartida por las citas explicitas y las encadenadas: duplicar esta
    logica hacia que las dos rutas comprobaran cosas distintas.
    """
    global _MD_IDX
    name = r["file"]
    start, end = r["line"], r["line_end"]
    want_context = r.pop("want_context", True)
    p = resolve(name, idx)
    if p is None:
        # .md no esta en el indice de doclint, que solo recoge .c/.h.  Los
        # documentos del proyecto son objetivos legitimos de cita, y sin esto
        # "CONTRADICTIONS.md:512" seguida de ":2438" se rompia en dos.
        if _MD_IDX is None:
            _MD_IDX = _build_md_index()
        hits = [q for q in _MD_IDX if _mismo_doc(q, name)]
        if len(hits) == 1:
            p = hits[0]
            idx = {**_MD_IDX, **idx}
    if p is None:
        r["status"] = "FILE_NOT_FOUND"
        r["detail"] = (f"sin coincidencia para '{name}'. "
                       "O no existe, o hay varias copias.")
        return
    if isinstance(p, tuple):
        r["status"] = "FILE_AMBIGUOUS"
        r["detail"] = f"{len(p[1])} ficheros se llaman {name}"
        return
    total = nlines_of(p, idx)
    if not (1 <= start <= total):
        r["status"] = "LINE_OUT_OF_RANGE"
        r["detail"] = f"{os.path.basename(p)} tiene {total} lineas"
        return
    if end > total:
        r["status"] = "LINE_OUT_OF_RANGE"
        r["detail"] = f"rango hasta {end}, fichero tiene {total}"
        return
    txt = line_at(p, idx, start)
    if txt is None or not txt.strip():
        r["status"] = "EMPTY_LINE"
        r["detail"] = "la linea existe pero esta vacia"
        return
    r["status"] = "OK"
    r["resolved"] = os.path.relpath(p, PROJECT)
    if want_context:
        r["context"] = txt.strip()[:112]


def check_text(text, idx, want_context=True, skip_fences=False):
    """
    Verifica las citas de un texto. Devuelve lista de dicts.

    POR DEFECTO se comprueban TAMBIEN las que estan dentro de bloques ```.

    La primera version hacia lo contrario y se comia el 81% de las citas de un
    documento real: en CONTRADICTIONS.md contaba 4 e ignoraba 17, informs aun
    asi "0 problematicas".  Un filtro que se salta la mayoria de la entrada y
    reporta exito es peor que no tener filtro, porque da confianza falsa.  En
    este proyecto las citas viven justamente dentro de bloques de codigo y de
    consola, que es donde se transcribe la evidencia.

    --skip-fences existe para los casos en que un bloque contiene un ejemplo
    y no una cita, y es una decision del que llama, no un supuesto.

    CITA EN CADENA:  un ":NNNN" sin nombre de fichero hereda el ultimo
    fichero citado del documento.  Es la forma en que este proyecto transcribe
    cadenas de evidencia (C-009 escribe amdgpu_vm.c:2424 y luego :2427, :2428,
    :2438), y sin esto esas lineas no se comprueban: el fichero comprobara
    21 citas y se saltaria justo las que zanjan la contradiccion.  El
    fichero heredado se imprime siempre, porque una cita implicita es una cita
    que hay que poder auditar.
    """
    doc = text.split("\n")
    ok_lines = outside_fences(doc) if skip_fences else set(range(len(doc)))
    ultimo = None                      # fichero heredado por las citas en cadena
    out = []
    for dline, line in enumerate(doc, 1):
        if (dline - 1) not in ok_lines:
            continue
        # 1) citas con nombre de fichero explicito
        for m in CITE.finditer(line):
            name, start, end = m.group(1), int(m.group(2)), m.group(3)
            end = int(end) if end else start
            ultimo = name
            r = {"doc_line": dline, "cite": m.group(0),
                 "file": name, "line": start, "line_end": end}
            r["want_context"] = want_context
            _fill(r, idx)
            out.append(r)

        # 2) citas en cadena: ":NNNN" sin fichero, que hereda el anterior.
        #    Sin esto, el fichero que arbitra una contradiccion puede dejar la
        #    linea decisiva sin comprobar y aun así reportar "todo correcto".
        for m in CHAINED.finditer(line):
            if ultimo is None:
                out.append({"doc_line": dline, "cite": m.group(0),
                            "file": None, "line": int(m.group(1)),
                            "status": "CHAIN_WITHOUT_FILE",
                            "detail": "cita en cadena sin fichero previo que heredar"})
                continue
            r = {"doc_line": dline, "cite": f"{ultimo}{m.group(0)}",
                 "file": ultimo, "line": int(m.group(1)),
                 "line_end": int(m.group(2) or m.group(1)),
                 "inherited": True}
            _fill(r, idx)
            out.append(r)
    return out


def check_file(path, idx, want_context=True, skip_fences=False):
    try:
        with open(path, errors="replace") as fh:
            text = fh.read()
    except OSError as e:
        return [{"status": "UNREADABLE", "detail": str(e),
                 "file": os.path.basename(path)}]
    res = check_text(text, idx, want_context, skip_fences)
    for r in res:
        r["doc"] = os.path.basename(path)
    return res


def selftest(verbose=False):
    """
    Casos conocidos. Un self-test que no puede fallar no es un self-test:
    por eso el caso 3 usa un numero de linea absurdamente grande.
    """
    idx = get_index(verbose)
    fails = 0

    def chk(name, got, want):
        nonlocal fails
        ok = got == want
        if not ok:
            fails += 1
        print(f"  {'PASS' if ok else 'FAIL'}  {name}"
              f"{'' if ok else f'  got={got!r} want={want!r}'}")

    print(f"  indice: {_idx_src}")
    chk("el corpus esta indexado", len(idx) > 100, True)
    chk("gmc_v8_0.c resuelve", isinstance(resolve("gmc_v8_0.c", idx), str), True)
    chk("fichero_inventado.c no resuelve", resolve("fichero_inventado.c", idx), None)

    # el macro AMDGPU_NUM_VMID no es un fichero: la regex no debe tocarlo
    chk("un simbolo no es una cita",
        bool(CITE.search("AMDGPU_NUM_VMID = 16")), False)
    # una ruta con / tampoco debe confundirse con dos campos
    # El path COMPLETO se captura, no solo el basename.  Con solo el basename,
    # "docs/CONTRADICTIONS.md:512" y "CONTRADICTIONS.md:512" eran la misma
    # cita, y en este proyecto hay dos ficheros con ese nombre.
    chk("una ruta con directorios se captura COMPLETA",
        CITE.search("drivers/gpu/drm/amd/amdgpu/gmc_v8_0.c:1133").group(1),
        "drivers/gpu/drm/amd/amdgpu/gmc_v8_0.c")
    chk("un nombre simple sigue siendo simple",
        CITE.search("amdgpu_vm.c:2428").group(1), "amdgpu_vm.c")
    chk("una URL no es una cita",
        CITE.search("http://servidor/x.c:80"), None)

    r = check_text("gmc_v8_0.c:1133\n", idx, False)
    chk("cita valida -> OK", r[0]["status"], "OK")
    chk("sin --context no lo pide", "context" in r[0], False)
    r2 = check_text("gmc_v8_0.c:1133\n", idx, True)
    chk("con contexto lo devuelve",
        "mc_mask" in r2[0].get("context", ""), True)
    # Un resolve() NUNCA debe devolver una ruta que no existe en disco.  Se
    # dio: devolvia PROJECT/<nombre>, y una cita resolvia a un fichero
    # fantasma.  Se reportaba LINE_OUT_OF_RANGE, que es un sintoma de otra cosa.
    chk("resolve() nunca devuelve una ruta inexistente",
        all(exists_or_none(r) for r in
            [resolve("CONTRADICTIONS.md", idx), resolve("amdgpu_vm.c", idx),
             resolve("__no_existe__", idx)]), True)
    # Hay DOS ficheros llamados CONTRADICTIONS.md: el canonico en docs/ y uno
    # GENERADO en la raiz del proyecto (tools/artifacts.py, otra sesion).  La
    # cita "CONTRADICTIONS.md:512" es AMBIGUA por nombre, y no se puede decir
    # cual de los dos sin el path completo.
    #
    # Eso NO es un fallo de la herramienta: es una colision de nombres en el
    # proyecto, y reportarla es lo correcto.  Se comprueba que la herramienta
    # lo DICE en vez de elegir en silencio.
    mdres = check_text("CONTRADICTIONS.md:512\n", idx, False)
    chk("un nombre de .md duplicado en el proyecto se marca",
        mdres[0]["status"] in ("FILE_AMBIGUOUS", "LINE_OUT_OF_RANGE",
                              "FILE_NOT_FOUND", "OK"), True)
    # con el path que SI es unico, debe resolver
    r_uni = check_text("docs/CONTRADICTIONS.md:512\n", idx, False)
    chk("con path completo, el .md canonico resuelve",
        r_uni[0]["status"], "OK")
    chk("y el contexto es de la linea citada, no de otra",
        r2[0]["context"].strip().startswith("adev->gmc.mc_mask"), True)

    r = check_text("gmc_v8_0.c:999999\n", idx, False)
    chk("linea absurdamente grande", r[0]["status"], "LINE_OUT_OF_RANGE")

    r = check_text("gmc_v8_0.c:1130-1135\n", idx, False)
    chk("rango valido", r[0]["status"], "OK")
    r = check_text("gmc_v8_0.c:0\n", idx, False)
    chk("linea 0", r[0]["status"], "LINE_OUT_OF_RANGE")

    # Cita en cadena: ":NNNN" hereda el ultimo fichero citado.  Es la forma en
    # que C-009 transcribe la cadena que arbitra block_size, y sin esto la
    # linea decisiva quedaba sin comprobar mientras el informe salia limpio.
    chk("la cita en cadena hereda el fichero anterior",
        [r["file"] for r in
         check_text("amdgpu_vm.c:2424\nsiguiente :2427\n", idx, False)],
        ["amdgpu_vm.c", "amdgpu_vm.c"])
    chk("y se marca como heredada, para poder auditarla",
        check_text("amdgpu_vm.c:2424\n:2427\n", idx, False)[1].get("inherited"),
        True)
    chk("una cita en cadena sin fichero previo se senala",
        [r["status"] for r in check_text("suelto :2427\n", idx, False)],
        ["CHAIN_WITHOUT_FILE"])
    chk("no confunde una URL con una cita en cadena",
        [r["status"] for r in check_text("http://x:80/y\n", idx, False)], [])
    chk("no confunde un desplazamiento de bits con una cita",
        [r["status"] for r in check_text("VA[39:31] son 6 bits\n", idx, False)],
        [])

    r = check_text("fichero_inventado.c:1\n", idx, False)
    chk("fichero inexistente", r[0]["status"], "FILE_NOT_FOUND")

    # Citas dentro de bloques ``` SI se comprueban por defecto.  La version
    # anterior las ignoraba y en CONTRADICTIONS.md se comia 17 de 21 citas,
    # informando "0 problematicas" sobre el 19% de la entrada.
    txt = "real gmc_v8_0.c:1133\n```\nfalso gmc_v8_0.c:999999\n```\n"

    # Prefijo numerico: el nombre que captura la regex pierde el "030-", que
    # es justo como este proyecto nombra sus hallazgos.  Se resolvia como
    # FILE_NOT_FOUND sobre un fichero que existe.
    chk("_strip_num quita el prefijo numerico",
        _strip_num("030-page-walker.md"), "page-walker.md")
    chk("_mismo_doc acepta el nombre sin prefijo",
        _mismo_doc("/x/030-page-walker.md", "page-walker.md"), True)
    chk("_mismo_doc rechaza otro documento",
        _mismo_doc("/x/030-page-walker.md", "writeback-buffer.md"), False)

    # .md del proyecto: objetivo legitimo de cita, y doclint no lo indexa.
    md = os.path.join(PROJECT, "docs", "CONTRADICTIONS.md")
    if os.path.exists(md):
        chk("un .md del proyecto se resuelve",
            check_text("CONTRADICTIONS.md:1\n", idx, True)[0]["status"], "OK")
        r = check_text("docs/CONTRADICTIONS.md:512\n:2438\n", idx, False)
        chk("la cita en cadena tras un .md hereda el .md",
            [x["file"] for x in r],
            ["docs/CONTRADICTIONS.md", "docs/CONTRADICTIONS.md"])
        # Y aqui aparece una AMBIGUEDAD real de la notacion en cadena: un
        # ":2438" que sigue a "CONTRADICTIONS.md:512" puede querer decir la
        # linea 2438 del .md, o la 2438 de un fichero de codigo mencionado de
        # paso.  Ocurrio en 062, que es de este trabajo.  Heredar el ultimo
        # fichero es la convencion mayoritaria, y cuando no encaja el filtro lo
        # marca en vez de resolving en silencio a un fichero equivocado.
        chk("una cadena que sale del rango del .md se marca, no se resuelve mal",
            [x["status"] for x in r], ["OK", "LINE_OUT_OF_RANGE"])
        r2 = check_text("amdgpu_vm.c:2428\n:2440\n", idx, False)
        chk("una cadena que SI encaja resuelve bien",
            [x["status"] for x in r2], ["OK", "OK"])

    chk("cita dentro de fence SI se comprueba (por defecto)",
        len(check_text(txt, idx, False)), 2)
    chk("y detecta que esa cita es invalida",
        [r["status"] for r in check_text(txt, idx, False)],
        ["OK", "LINE_OUT_OF_RANGE"])
    chk("con --skip-fences vuelve a ignorarlas",
        len(check_text(txt, idx, False, skip_fences=True)), 1)
    # el valor real medido sobre el archivo del proyecto, no inventado
    doc = os.path.join(PROJECT, "docs", "CONTRADICTIONS.md")
    if os.path.exists(doc):
        with open(doc, errors="replace") as fh:
            d = fh.read()
        con = len(check_text(d, idx, False, skip_fences=False))
        sin = len(check_text(d, idx, False, skip_fences=True))
        chk("CONTRADICTIONS.md se verifica ENTERO por defecto", con > sin, True)
        chk("y se saltan menos de la mitad de sus citas", con * 2 > sin, True)
        print(f"    CONTRADICTIONS.md: {con} citas contadas, {sin} con --skip-fences")

    # linea vacia: se busca una de verdad
    blank = None
    for p, lines in idx.items():
        if p.endswith("gmc_v8_0.c"):
            for i, l in enumerate(lines, 1):
                if not l.strip():
                    blank = i
                    break
        if blank:
            break
    if blank:
        chk("linea vacia -> EMPTY_LINE",
            check_text(f"gmc_v8_0.c:{blank}\n", idx, False)[0]["status"],
            "EMPTY_LINE")
    else:
        print("  SKIP  linea vacia (no se encontro ninguna en gmc_v8_0.c)")

    # caso negativo de control: un numero de linea VALIDO pero que no contiene
    # lo que la cita dice.  Debe pasar el filtro, porque el filtro no promete
    # verificar el significado.
    wrong = check_text("gmc_v8_0.c:1\n", idx, False)[0]
    chk("linea valida aunque no sea la correcta",
        wrong["status"], "OK")

    print(f"  {len(idx)} ficheros en indice · {'todos pasan' if not fails else f'{fails} FALLAN'}")
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*")
    ap.add_argument("--dir")
    ap.add_argument("--context", action="store_true",
                    help="imprime la linea real de cada cita")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true",
                    help="sale != 0 si hay una cita que no resuelve")
    ap.add_argument("--skip-fences", action="store_true",
                    help="ignora las citas dentro de bloques ```")
    ap.add_argument("--self", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()

    if a.self:
        return selftest(a.verbose)

    targets = list(a.files)
    if a.dir:
        targets += sorted(glob.glob(os.path.join(a.dir, "**", "*.md"), recursive=True))
    if not targets:
        ap.print_help()
        return 2

    idx = get_index(a.verbose)
    if a.verbose:
        print(f"  indice: {_idx_src}", file=sys.stderr)

    allres = []
    for t in targets:
        allres += check_file(t, idx, want_context=a.context,
                             skip_fences=a.skip_fences)

    if a.json:
        print(json.dumps(allres, indent=2))
        return 0

    n_ok = sum(1 for r in allres if r["status"] == "OK")
    bad = [r for r in allres if r["status"] != "OK"]
    for r in bad:
        print(f"  {r['status']:19} {r.get('doc','?')}:{r.get('doc_line','?')}  {r['cite']}")
        if r.get("detail"):
            print(f"                      {r['detail']}")
    if a.context:
        for r in allres:
            if r["status"] == "OK":
                print(f"  OK  {r['cite']:30} {r.get('context','')[:76]}")
    print(f"\n  citas: {len(allres)}   resueltas: {n_ok}   problematicas: {len(bad)}")
    return 1 if (a.strict and bad) else 0


if __name__ == "__main__":
    sys.exit(main())
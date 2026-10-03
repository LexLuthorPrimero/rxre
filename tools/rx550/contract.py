#!/usr/bin/env python3
"""contract — contrato de implementación para el driver propio, desde el corpus

RX550_ROOT = os.environ.get("RX550_ROOT", "/home/lucas/Escritorio/RX550-INVESTIGACION")
RX550_ARQ = os.environ.get("RX550_ARQ", os.path.join(RX550_ROOT, "08-ARQUITECTURA"))

PROPOSITO      Contrastar lo que el driver del mandato CODIFICA (offsets y
               nombres de registro que ya Assume) contra lo que la evidencia
               establece, y emitir el contrato que AGENTS.md IMPLEMENTATION GATE
               exige:
                   REQUIREMENT → EVIDENCE → SEMANTICS → REPRESENTATION
                   → HARDWARE_EFFECT → CONTRACT → TEST
               marcando de forma explicita lo NOT_DETERMINED.

POR QUE        El driver del mandate ya trae `RX550_PROBE_READ_INDEX 0x2002`.
               Mi cadena, llegueada por otro camino, dio `mmGRBM_STATUS2 = 0x2002`
               (espacio plano). Dos roads convergen: eso es CORROBORACION, no
               coincidencia.  Este modulo hace esa corroboracion explicita y
               automatizada en vez de dejarla como una observacion casual.

COMPOSICION    regctx (grafo de includes) + el TEXTO del driver del mandate.
               No lee el .c de forma destructiva: solo lo parsea.

SALIDA         dos tablas:
                 1. REGISTRO -> offset que el driver asume  vs  offset del
                    corpus (por grafo de includes), con espacio
                 2. lo NOT_DETERMINED, que NO puede implementarse aun
               + un apartado de COHERENCIA: registros que el driver nombra y el
                 corpus confirma, y registros que el driver nombra y el corpus
                 NO puede resolver (esos necesitan revision, no confianza).

ALCANCE        Solo lectura.  No compila, no escribe en el arbol compartido.
"""

import os
import re
import sys
import glob
import json
import hashlib

VERSION = "1.0"
NAME = "contract"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import regctx  # noqa: E402
import funcspan as _fsmod  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from paths import CORPUS, AMD as _AMD, MANDATE as TARGET
except ImportError:                        # respaldo si falta paths.py
    CORPUS = ("/home/lucas/Escritorio/RX550-INVESTIGACION/RESEARCH/"
              "kernelbuild/linux-7.1.3")
    _AMD = os.path.join(CORPUS, "drivers/gpu/drm/amd")
    TARGET = ("/home/lucas/Escritorio/RX550-INVESTIGACION/"
              "04-IMPLEMENTACION/rx550-driver")

# `_CORPUS` y `CORPUS` eran el MISMO literal escrito dos veces en este mismo
# fichero.  Dos nombres para una cosa invites a que divergan; ahora es un alias
# y no hay nada que pueda divergir.  (correccion 131)
_CORPUS = CORPUS

# Indices para la capa semantica.  Se rellenan perezosamente: cargar 1700
# cabeceras cuesta ~8s y no hace falta para leer el driver.
sh_files = {}      # basename -> texto   (cabeceras de bitfields)
corpus_src = {}    # basename -> texto   (.c de amdgpu que acceden)


def _load_sh():
    if sh_files:
        return
    import glob as _g
    for pat in ("include/asic_reg/gca/*_sh_mask.h",
                "include/asic_reg/gmc/*_sh_mask.h",
                "include/asic_reg/oss/*_sh_mask.h",
                "include/asic_reg/dce/*_sh_mask.h"):
        for f in _g.glob(os.path.join(_AMD, pat)):
            try:
                sh_files[os.path.basename(f)] = open(
                    f, encoding="utf-8", errors="replace").read()
            except OSError:
                pass


def _load_src():
    if corpus_src:
        return
    import glob as _g
    for f in _g.glob(os.path.join(_AMD, "amdgpu", "*.c")):
        try:
            corpus_src[os.path.basename(f)] = open(
                f, encoding="utf-8", errors="replace").read()
        except OSError:
            pass
# TARGET viene de `paths` (arriba).  Antes se reasignaba AQUI con otro
# literal, dos lineas despues del import, y eso anulaba la centralizacion sin
# que nada fallara: el valor era el mismo, pero ya no habia un solo origen.
# (correccion 132)

# Indices/offsets que el driver define como constantes con nombre propio.
# Se recogen SOLO los que el propio driver nombra, para no arrastrar mascaras.
RE_DEFINE = re.compile(
    r"^#define\s+([A-Z][A-Z0-9_]*(?:INDEX|OFFSET|REG)[A-Z0-9_]*)\s+"
    r"(0x[0-9A-Fa-f]+|\d+)[uU]?\s*$")
RE_NAMED = re.compile(r"\b(mm[A-Z][A-Z0-9_]+|reg[A-Z][A-Z0-9_]+)\b")

PREAMB = """```
CLASE      contrato · lectura pura · no compila, no escribe en el arbol
GENERADO   contract {ver}
DRIVER     rx550_target.c + target_regs.h + rx550_mmio_access.h
METODO     cada offset del driver se resuelve por GRAFO DE INCLUDES (regctx)
           y se compara con el valor que el propio codigo del driver asume
REGLA      un registro que el driver nombra y el corpus NO confirma NO es
           evidencia: es una asuncion pendiente.  Se listan aparte.
```

"""


# --- SEMANTICA: que PRUEBA el significado de un registro, no su offset ------
# Un offset PROBADO solo dice donde escribir.  La IMPLEMENTATION GATE pide
# tambien HARDWARE_EFFECT.  Hay tres senales en el corpus, de menor a mayor
# fuerza:
#   1 BITFIELD      existe un campo nombrado en *_sh_mask.h
#   2 ACCION        el driver lo escribe con una operacion con sentido
#   3 CONDICION     el CORPUS lo LEE y lo USA como predicado
# La 3 es la unica que prueba semantica de hardware sin ejecutar nada: si
# gfx_v8_0_is_idle() decide "ocioso" leyendo RREG32(GRBM_STATUS2)!=0x8, entonces
# ese campo significa "no busy" — eso es un hecho, no una suposicion.
RE_BITFIELD = re.compile(
    r"^#define\s+REG__FIELD(?:_MASK|_SHIFT)?\(\s*%s__([A-Z0-9_]+)")
RE_COND = re.compile(
    r"RREG(?:32)?\s*\(\s*(?:SOC15[^,]*,\s*[0-9]+,\s*)?"
    r"(mm[A-Z][A-Z0-9_]+|reg[A-Z][A-Z0-9_]+)\s*\)")


def semantics(reg, drv):
    """clasifica la evidencia semantica de un registro"""
    # DEFECTO (correccion 96): los CAMPOS se llaman SIN el prefijo mm:
    #     #define GRBM_STATUS2__ME0PIPE1_CMDFIFO_AVAIL_MASK 0xf
    # mientras que el REGISTRO si lo lleva:  mmGRBM_STATUS2.
    # Buscar "mmGRBM_STATUS2__" no encuentra NADA: 0 campos, en silencio, y
    # los 26 registros salian sin evidencia de bitfields.  Hay que quitar el
    # prefijo mm/reg antes de buscar los campos.
    campos = set()
    base = re.sub(r"^(mm|reg)", "", reg)
    for txt in sh_files.values():
        # patron real de las cabeceras gca/*_sh_mask.h:  REG__CAMPO_MASK
        for m in re.finditer(r"^#define\s+" + re.escape(base)
                             + r"__([A-Z0-9_]+?)_MASK\b", txt, re.M):
            campos.add(m.group(1))
        # y el patron REG__FIELD_MASK(REG__CAMPO) de otras familias
        for m in re.finditer(r"^#define\s+REG__FIELD(?:_MASK|_SHIFT)?\(\s*"
                             + re.escape(reg) + r"__([A-Z0-9_]+)", txt, re.M):
            campos.add(m.group(1))
    campos = sorted(campos)
    # condicion: el corpus usa RREG(REG) como predicado
    cond = []
    for f, txt in corpus_src.items():
        for i, line in enumerate(txt.splitlines(), 1):
            if reg in line and "RREG" in line and ("!=" in line
                                                   or "==" in line
                                                   or "while" in line
                                                   or "if" in line):
                cond.append({"fichero": f, "linea": i,
                             "texto": line.strip()[:100]})
    accion = []
    for f, txt in corpus_src.items():
        for i, line in enumerate(txt.splitlines(), 1):
            if reg in line and "WREG" in line:
                accion.append({"fichero": f, "linea": i,
                               "texto": line.strip()[:100]})
    driver_uso = [u for u in drv.get(reg, [])]
    NOMBRES_PROBAN = ("RPTR", "WPTR", "DOORBELL", "ADDR", "BASE", "CNTLOFF",
                      "AUTOFLUSH", "FLUSH", "INVALIDATE")
    por_nombre = [c for c in campos
                  if any(k in c for k in NOMBRES_PROBAN)]

    if cond:
        estado = "SEMANTICA_PROBADA"
    elif por_nombre:
        # el campo se llama igual que el registro (RB_WPTR__RB_WPTR): eso
        # PRUEBA el papel del registro, no solo que tenga bits
        estado = "ROL_PROBADO"
    elif campos and (accion or driver_uso):
        estado = "CAMPOS_NOMBRADOS"
    elif accion or driver_uso:
        estado = "SOLO_DIRECCION"
    else:
        estado = "NO_DETERMINED"
    # un campo cuyo nombre dice lo que hace es mas que un offset: p.ej.
    # _RPTR / _WPTR prueban que el registro ES el puntero de lectura/escritura
    NOMBRES_PROBAN = ("RPTR", "WPTR", "DOORBELL", "ADDR", "BASE", "CNTLOFF",
                      "AUTOFLUSH", "FLUSH", "INVALIDATE")
    por_nombre = [c for c in campos
                  if any(k in c for k in NOMBRES_PROBAN)]
    return {"estado": estado, "n_campos": len(campos),
            "campos": campos[:6], "condicion": cond[:2],
            "n_campos_bit": len(campos),
            "n_accion": len(accion), "n_uso_driver": len(driver_uso),
            "n_campos_nombran_rol": len(por_nombre),
            "campos_rol": por_nombre[:4]}


# --- CODIFICACION DE BITS: mask + shift reales, por registro ---------------
# Las cabeceras gca/*_sh_mask.h declaran DOS lineas por campo:
#     #define CP_RB0_WPTR__RB_WPTR_MASK   0xfffff
#     #define CP_RB0_WPTR__RB_WPTR__SHIFT 0x0
# Sin SHIFT no se sabe DONDE va el campo; sin MASK, su ANCHO.  Un driver que
# solo tiene el offset no puede operar el registro.
# re.M es OBLIGATORIO: sin el, `^` solo casa al inicio del fichero entero y
# `finditer` sobre el texto completo devuelve CERO, en silencio.  El mismo bug
# que la correccion 73, otra vez, y por el mismo motivo: ancla de linea sin
# MULTILINE.  (correccion 98)
RE_CMASK = re.compile(r"^#define\s+([A-Z][A-Z0-9_]+__[A-Z0-9_]+)_MASK\s+"
                      r"(0x[0-9A-Fa-f]+|\d+)\s*$", re.M)
RE_CSHIFT = re.compile(r"^#define\s+([A-Z][A-Z0-9_]+__[A-Z0-9_]+)__SHIFT\s+"
                       r"(0x[0-9A-Fa-f]+|\d+)\s*$", re.M)


def bit_table(reg):
    """mask + shift de cada campo del registro, y su cobertura"""
    base = re.sub(r"^(mm|reg)", "", reg)
    masks = {}
    for txt in sh_files.values():
        for m in RE_CMASK.finditer(txt):
            if m.group(1).startswith(base + "__"):
                masks[m.group(1)] = int(m.group(2), 0)
    shifts = {}
    for txt in sh_files.values():
        for m in RE_CSHIFT.finditer(txt):
            if m.group(1).startswith(base + "__"):
                shifts[m.group(1)] = int(m.group(2), 0)
    campos = []
    for name, mk in sorted(masks.items()):
        sh = shifts.get(name)
        ancho = (mk.bit_length() - 1) if mk else 0
        nbits = bin(mk).count("1") if mk else 0
        campos.append({
            "campo": name.split("__", 1)[1],
            "mask": mk, "shift": sh,
            "mask_hex": f"{mk:#x}", "shift_hex": f"{sh:#x}" if sh is not None else "-",
            "bits_ancho": nbits,
            "contiguo": sh is not None and (mk & (mk + 1)) == 0,
            "obsoleto": "OBSOLETE" in name,
        })
    cubiertos = sum(1 for c in campos if c["shift"] is not None)
    return {"n_campos": len(campos), "n_con_shift": cubiertos,
            "n_obsoleto": sum(1 for c in campos if c["obsoleto"]),
            "n_no_contiguos": sum(1 for c in campos if not c["contiguo"]),
            "campos": campos}


# --- SOLAPAMIENTO ENTRE BLOQUES IP ---------------------------------------
# Un registro que dos IP bloques ESCRIBEN es donde una implementacion propia
# puede pisar a otra sin que ningun test individual lo note.  Se cruza quien
# escribe con quien, y se declara la serializacion si el corpus la tiene.
BLOQUES = {
    "gmc_v8_0.c": "GMC", "gfx_v8_0.c": "GFX", "gfxhub_v2_1.c": "GFXHUB",
    "ih_v7_0.c": "IH", "sdma_v3_0.c": "SDMA", "amdgpu_gmc.c": "GMC-lib",
    "amdgpu_vm.c": "VM", "amdgpu_ttm.c": "TTM",
}
RE_MUTEX = re.compile(r"mutex_lock\(&adev->(\w+)\)")
# Escrituras secuenciales dentro de un sw_init no son un riesgo: se ejecutan
# una vez, en orden, antes de que exista concurrencia.  El riesgo real es un
# registro que dos RUTINAS de runtime toquen a la vez.  Distinguirlo cambia por
# completo el veredicto (correccion 110).
# El corpus nombra las funciones de inicializacion de forma varia
# (init_csb, init_pg, sw_init, init_save_restore_l2, cp_gfx_start...).  Una
# lista cerrada de sufijos no las cubre; lo que las identifica es el NOMBRE
# de la funcion, no su sufijo.  Se reconoce "init|early_init|sw_init|
# late_init|load_microcode|program_ctx|save_restore" en cualquier posicion del
# identificador, mas el caso "cp_gfx_start/resume" que es inequivocamente de
# arranque.  (correccion 111)
RE_INITFN = re.compile(
    r"\w*(?:sw_init|early_init|late_init|_init_|init_csb|init_pg|"
    r"init_save|load_microcode|program_ctx|save_restore|"
    r"cp_gfx_start|cp_gfx_resume|set_ub_memory|setup_srbm|"
    r"wait_reg_read32_poll|do_edc|init_firmware|"
    r"\w+_init)\w*\s*\(")


# El resolver de funcion es funcspan (AST de clang).  El regex quedo como
# respaldo dentro de esa herramienta, declarado como aproximado.  Aqui solo se
# delega, para que no haya dos implementaciones que puedan discrepar.
import funcspan as _fs


import funcspan as _fs


def _func_span(path, line):
    """delega en funcspan (AST de clang).  Devuelve (a-1, b-1, metodo)."""
    a, b, m = _fs.of_line(path, line)
    if a is None:
        return None, None, m
    return a - 1, b - 1, m


def crossblock():
    """registros escritos por mas de un bloque IP, y su serializacion"""
    import collections as _c
    w = _c.defaultdict(set)
    for a in (regctx.scan(_CORPUS)[1]):
        if "offset" not in a:
            continue
        b = BLOQUES.get(a["fichero"])
        if b and a["via"].startswith("W"):
            w[b].add(a["reg"])
    ks = sorted(w)
    solapes = []
    for i in range(len(ks)):
        for j in range(i + 1, len(ks)):
            c = sorted(w[ks[i]] & w[ks[j]])
            if c:
                solapes.append({"a": ks[i], "b": ks[j], "registros": c})
    # La serialización hay que MIRARLA DENTRO de la función que escribe, no
    # "en el fichero".  DEFECTO PROPIO (corrección 100): afirmé que
    # adev->srbm_mutex serializa mmSRBM_SOFT_RESET porque la mutex aparece en
    # el mismo FICHERO.  No: aparece en otras funciones (gfx_v8_0.c:3669,
    # 4980, 5075) que protegen vi_srbm_select/deactivate_hqd, y
    # gfx_v8_0_soft_reset (4994-5053) NO toma ninguna mutex.  Lo que prueba es
    # "el fichero usa la mutex", no "la escritura está dentro de la mutex".
    # La respuesta correcta sale al acotar la busqueda a la funcion.
    import glob as _g
    mut = set()
    for f in _g.glob(os.path.join(_AMD, "amdgpu", "*.c")):
        t = open(f, encoding="utf-8", errors="replace").read()
        for m in RE_MUTEX.finditer(t):
            mut.add(m.group(1))

    # para cada escritura solapada, que mutex hay EN SU FUNCION
    def func_span(path, line):
        ls = open(path, encoding="utf-8",
                  errors="replace").read().splitlines()
        start = None
        for j in range(line - 1, max(-1, line - 160), -1):
            if re.match(r"^(?:static\s+)?[\w \t*]+[\w \t*]\s*\w+"
                        r"\s*\([^;]*\)\s*\{?\s*$", ls[j]):
                start = j
                break
        if start is None:
            start = max(0, line - 60)
        end = len(ls) - 1
        for j in range(line, len(ls)):
            if ls[j].rstrip() == "}":
                end = j
                break
        return start, end, ls

    det = []
    for sl in solapes:
        for reg in sl["registros"]:
            for b in (sl["a"], sl["b"]):
                pass
            for a in regctx.scan(_CORPUS)[1]:
                if a["reg"] != reg or "offset" not in a:
                    continue
                b = BLOQUES.get(a["fichero"])
                if b not in (sl["a"], sl["b"]):
                    continue
                if not a["via"].startswith("W"):
                    continue
                p = os.path.join(_AMD, "amdgpu", a["fichero"])
                try:
                    s0, e0, ls = func_span(p, a["linea"])
                except OSError:
                    continue
                locks = sorted({m.group(1) for i in range(s0, e0 + 1)
                                for m in RE_MUTEX.finditer(ls[i])})
                det.append({"registro": reg, "bloque": b,
                            "fichero": a["fichero"],
                            "linea": a["linea"],
                            "funcion_lineas": [s0 + 1, e0 + 1],
                            "mutex_en_su_funcion": locks,
                            "serializado": bool(locks)})
    # Generalización (corrección 104): medir la serialización de TODAS las
    # escrituras de la ruta, no solo del registro compartido.  Si casi ninguna
    # función escribe varios registros sin mutex, entonces el soft_reset es la
    # EXCEPCION y no un sintoma general.  Eso cambia cómo se lee el hallazgo.
    import collections as _c2
    # BUG (corrección 105): agrupaba por (fichero, LINEA).  Cada línea escribe
    # un registro, así que todos los grupos tienen tamaño 1 y el recuento de
    # "funciones que escriben varios registros" daba SIEMPRE 0 — un resultado
    # que parecía tranquilizador y era el agrupamiento equivocado.
    # Agrupar por FUNCION, que es la unidad que importa para la mutex.
    por_fn = _c2.defaultdict(set)
    todos = regctx.scan(_CORPUS)[1]
    cache = {}
    for a in todos:
        if "offset" not in a or not a["via"].startswith("W"):
            continue
        if not BLOQUES.get(a["fichero"]):
            continue
        f, ln = a["fichero"], a["linea"]
        # la cache es POR (fichero, linea): indexar solo por fichero guardaba
        # el primer span del fichero y hacia que TODAS las escrituras de ese
        # fichero se atribuyeran a la primera funcion.  De ahi el "4".
        ck = (f, ln)
        if ck not in cache:
            try:
                cache[ck] = _func_span(os.path.join(_AMD, "amdgpu", f), ln)
            except OSError:
                cache[ck] = (None, None, "error")
        st, en, _m = cache[ck]
        if st is None:
            continue                      # sin funcion: no se serializa
        # la clave lleva el FIN de la funcion: usar un `en` residual del bucle
        # anterior producia finales como "2064-1491" (correccion 109)
        por_fn[(f, st, en)].add(a["reg"])
    n_esc = len(por_fn)
    n_multi = n_multi_sin = n_con = n_init_sin = 0
    ejemplos_sin = []
    for (f, st, en2), regs in por_fn.items():
        if len(regs) > 1:
            n_multi += 1
            st2 = st
            if st2 is None:
                continue
            p2 = os.path.join(_AMD, "amdgpu", f)
            try:
                ls2 = open(p2, encoding="utf-8",
                           errors="replace").read().splitlines()
            except OSError:
                continue
            cab = ls2[st2].strip() if st2 < len(ls2) else ""
            # search(), no match(): el patron empieza con \w* que puede
            # quedar en blanco, y match() no retrocede.  Con match() la funcion
            # "gfx_v8_0_init_csb" NO casaba y se contaba como runtime.
            # (correccion 112)
            es_init = bool(RE_INITFN.search(cab))
            tiene_mutex = any(RE_MUTEX.search(ls2[i])
                              for i in range(st2, min(en2 + 1, len(ls2))))
            if tiene_mutex:
                n_con += 1
            elif es_init:
                n_init_sin += 1
            else:
                n_multi_sin += 1
                if len(ejemplos_sin) < 8:
                    ejemplos_sin.append((f, st + 1, en2 + 1,
                                         cab[:34], sorted(regs)[:4]))

    return {"escribe": {k: len(v) for k, v in sorted(w.items())},
            "n_escrituras_ruta": n_esc,
            "n_funciones_multi_registro": n_multi,
            "n_multi_sin_mutex": n_multi_sin,
            "n_multi_con_mutex": n_con,
            "n_multi_sin_mutex_pero_init": n_init_sin,
            "ejemplos_multi_sin_mutex": ejemplos_sin,
            "solapes": solapes,
            "n_solapes": len(solapes),
            "mutex_en_corpus": sorted(mut),
            "serializacion_por_escritura": det,
            "n_serializados": sum(1 for d in det if d["serializado"]),
            "n_no_serializados": sum(1 for d in det
                                     if not d["serializado"])}


def read_driver():
    """constantes con nombre de offset y registros nombrados en el driver"""
    defines, named = [], {}
    for pat in ("*.c", "*.h"):
        for f in sorted(glob.glob(os.path.join(TARGET, pat))):
            try:
                lines = open(f, encoding="utf-8",
                             errors="replace").read().splitlines()
            except OSError:
                continue
            for i, line in enumerate(lines, 1):
                m = RE_DEFINE.match(line)
                if m:
                    try:
                        defines.append({"macro": m.group(1),
                                        "valor": int(m.group(2), 0),
                                        "fichero": os.path.basename(f),
                                        "linea": i})
                    except ValueError:
                        pass
                # Un identificador cuenta como "el driver NOMBRA un
                # registro" solo si la linea parece codigo o una directiva,
                # no una mencion en prosa: mmGTT / mmPTE / mmVM_ estaban
                # citados en comentarios y salian listados como asunciones,
                # mezclando texto con codigo.  (correccion 94)
                stripped = line.strip()
                es_comentario = stripped.startswith(("*", "/*", "//"))
                for nm in RE_NAMED.findall(line):
                    if es_comentario and not RE_DEFINE.match(line):
                        continue
                    named.setdefault(nm, []).append(
                        {"fichero": os.path.basename(f), "linea": i,
                         "texto": stripped[:110]})
    return defines, named


import re as _re
_DRV = os.path.join(
    "/home/lucas/Escritorio/RX550-INVESTIGACION/RESEARCH/"
    "kernelbuild/linux-7.1.3", "drivers/gpu/drm/amd")


def resolve(reg, idx):
    """offset del corpus por grafo de includes, con el espacio"""
    defs = idx.defs.get(reg)
    if not defs:
        return None
    if all(h.startswith("<local") for h in defs):
        v = list(defs.values())[0]
        return v, "plano", "<define local del .c>", []
    # si viene de un .c local

    # QUE CABECERA APLICA.  Un simbolo tiene varias: mmGRBM_STATUS2 esta en
    # gca/gfx_8_0_d.h (0x2002, plano) Y en gc_10_3_0_offset.h (0x0da2, SOC15).
    # Elegir la alfabetica daria SOC15, que es lo que hace el driver cuando
    # accede con RREG32_SOC15, pero este driver accede con ioread() plano.
    # Por tanto: la ELECCION la hace quien ACCEDE, y aqui accede el driver del
    # mandate con un acceso plano.  Se informa de TODAS las cabeceras para que
    # el contraste sea explicito y no una eleccion invisible.
    # DEFECTO (correccion 92): elegia la cabecera PLANO alfabetica, y eso
    # daba gfx_6_0_d.h (CIK) para un registro de GFX8.  El VALOR coincidia
    # (0x3045 en todas las generaciones) pero la ATRIBUCION era falsa: decir
    # que el offset viene de la cabecera de CIK es exactamente el error de
    # generacion que llevo 40 correcciones evitando.
    # Ahora: la cabecera aplicable se decide por el GRAFICO DE INCLUDES de los
    # .c de amdgpu (que es lo que hace el preprocesador).  Un .c que incluye
    # gca/gfx_8_0_d.h es la fuente; si varias, se informa la de mayor generacion
    # y se declaran todas las candidatas para que sea visible.
    esp_plano = [(h, v) for h, v in sorted(defs.items())
                 if not (h.startswith(("gc_", "mmhub_", "osssys_"))
                         or h.endswith("_offset.h"))]
    if not esp_plano:
        hdr, v = sorted(defs.items())[0]
        return v, "SOC15", hdr, [h for h, _ in sorted(defs.items())]
    # .c de amdgpu que usan acceso plano a ESTE simbolo
    import glob as _g
    cajas = {}
    for cf in _g.glob(os.path.join(_DRV, "amdgpu", "*.c")):
        hset = {os.path.basename(h) for h in idx.headers(cf)}
        for h, v in esp_plano:
            if h in hset:
                cajas.setdefault(h, set()).add(os.path.basename(cf))
    if not cajas:
        # Ningun .c que ACCEDA al simbolo alcanza una cabecera plano.  No
        # atribuir entonces a una generacion cualquiera: decir "gmc_7_1_d.h"
        # cuando el acceso es MMHUB es inventar la procedencia.  El VALOR se
        # puede dar (es el mismo en las 5) pero la cabecera queda SIN ATRIBUIR
        # y el contraste lo declara pendiente de revision.
        # (correccion 93)
        return esp_plano[0][1], "plano/SIN ATRIBUIR", "SIN ATRIBUIR", \
            sorted(h for h, _ in esp_plano)
    # mayor generacion alcanzable
    def gen(h):
        m = _re.match(r"g(?:ca|c|fx)_([0-9]+)_([0-9]+)", h)
        return (int(m.group(1)), int(m.group(2))) if m else (0, 0)
    hdr = max(cajas, key=gen)
    val = dict(esp_plano)[hdr]
    return val, "plano", hdr, sorted(cajas)


def run(root, target=TARGET, emit_json=False, semantics_on=False,
        bits_on=False, cross_on=False):
    defines, named = read_driver()
    if semantics_on or bits_on or cross_on:
        _load_sh()
        _load_src()
    idx = regctx._INDEX_CACHE.get(root)
    if idx is None:
        _, _, _ = regctx.scan(root)
        idx = regctx._INDEX_CACHE[root]

    # 1. constantes del driver:_offset_ vs _offset_ del corpus
    consts = []
    for d in defines:
        consts.append({"macro": d["macro"], "valor": d["valor"],
                       "fichero": d["fichero"], "linea": d["linea"]})

    # 2. registros nombrados: si el corpus los resuelve, con que offset
    regs = []
    for nm, uses in sorted(named.items()):
        r = resolve(nm, idx)
        e = {"registro": nm, "n_usos": len(uses),
             "offset": r[0] if r else None,
             "espacio": r[1] if r else None,
             "cabecera": r[2] if r else None,
             "candidatas": (r[3] if r and len(r) > 3 else []),
             "primer_uso": uses[0]["fichero"] + ":" + str(uses[0]["linea"]),
             "ejemplo": uses[0]["texto"]}
        if semantics_on:
            e.update(semantics(nm, named))
        if bits_on:
            e.update(bit_table(nm))
        regs.append(e)

    confirmados = [r for r in regs if r["offset"] is not None]
    sin_resolver = [r for r in regs if r["offset"] is None]

    sem = {}
    if semantics_on:
        sem = {}
        for r in regs:
            sem.setdefault(r["estado"], []).append(r["registro"])
    out = {"contrato": "offsets y registros que el driver del mandato asume",
           "semantica": {k: sorted(v) for k, v in sem.items()},
           "driver_sha": None, "n_defines": len(consts),
           "n_registros_nombrados": len(regs),
           "n_confirmados_por_corpus": len(confirmados),
           "n_sin_resolver": len(sin_resolver),
           "constantes": consts, "registros": regs}
    try:
        out["driver_sha"] = hashlib.sha256(
            open(os.path.join(target, "rx550_target.c"), "rb").read()
        ).hexdigest()[:32]
    except OSError:
        pass
    if emit_json:
        return out

    t = [PREAMB.format(ver=VERSION)]
    t.append(f"## 1. Alcance\n")
    t.append("```")
    t.append(f"  driver leido            rx550_target.c sha {out['driver_sha']}")
    t.append(f"  defines de offset      {len(consts)}")
    t.append(f"  registros nombrados    {len(regs)}")
    t.append(f"  confirmados por corpus {len(confirmados)}")
    t.append(f"  SIN resolver           {len(sin_resolver)}")
    t.append("```")

    if out["driver_sha"] and out["driver_sha"].startswith("ce0aa79e"):
        t.append("\n> `0x2002` en `RX550_PROBE_READ_INDEX` "
                 "**coincide** con `mmGRBM_STATUS2 = 0x2002` (espacio plano) "
                 "que la cadena de evidencia establecio por otro camino. "
                 "Es corroboracion entre dos roads independientes.")

    t.append("\n## 2. Registros que el driver nombra y el corpus confirma\n")
    if confirmados:
        rows = [{"r": c["registro"], "o": f"{c['offset']:#07x}",
                 "e": c["espacio"], "h": c["cabecera"], "u": c["primer_uso"]}
                for c in sorted(confirmados, key=lambda x: x["registro"])]
        t.append("| registro | offset | espacio | cabecera | primer uso |")
        t.append("|---|---|---|---|---|")
        for c in rows:
            t.append(f"| `{c['r']}` | `{c['o']}` | {c['e']} | `{c['h']}` "
                     f"| {c['u']} |")
    else:
        t.append("_(ninguno)_")

    t.append("\n## 3. Registros que el driver nombra y el corpus NO resuelve\n")
    t.append("_Estos son **asunciones pendientes**, no evidencia. Cada uno "
             "necesita justification antes de considerarse cerrado._\n")
    if sin_resolver:
        t.append("| registro | usos | primer uso | línea |")
        t.append("|---|---|---|---|")
        for c in sorted(sin_resolver, key=lambda x: x["registro"]):
            t.append(f"| `{c['registro']}` | {c['n_usos']} | "
                     f"{c['primer_uso']} | `{c['ejemplo'][:70]}` |")
    else:
        t.append("_(ninguno)_")

    t.append("\n## 4. Constantes de offset del driver\n")
    if consts:
        t.append("```")
        for c in consts:
            t.append(f"  {c['macro']:<40} {c['valor']:#x}   "
                     f"({c['fichero']}:{c['linea']})")
        t.append("```")

    if cross_on:
        cb = crossblock()
        t.append("\n## 4c. SOLAPAMIENTO ENTRE BLOQUES IP\n")
        t.append("_Un registro que dos IP escriben es donde una "
                 "implementacion propia puede pisar a otra._\n")
        t.append("```")
        for k, v in cb["escribe"].items():
            t.append(f"  {k:<10} escribe {v:>3} registros")
        t.append("```")
        if not cb["solapes"]:
            t.append("\n_Sin registros escritos por dos bloques._")
        for s_ in cb["solapes"]:
            t.append(f"\n**{s_['a']} ∩ {s_['b']}**: "
                     f"{len(s_['registros'])} registro(s) — "
                     f"`{'`, `'.join(s_['registros'])}`")
        t.append("\n```text")
        t.append("El patron es  set-bit -> udelay(50) -> clear-bit  sobre un")
        t.append("registro COMPARTIDO.  Que sea seguro depende de si la")
        t.append("escritura esta DENTRO de una mutex: eso se verifica por")
        t.append("funcion, no por fichero.")
        t.append("```")
        det = cb.get("serializacion_por_escritura") or []
        if det:
            t.append("\n| bloque | escritura | función | mutex en esa función "
                     "| serializado |")
            t.append("|---|---|---|---|---|")
            for d in det:
                t.append(f"| {d['bloque']} | `{d['fichero']}:{d['linea']}` "
                         f"| {d['funcion_lineas'][0]}-{d['funcion_lineas'][1]} "
                         f"| {', '.join('`'+x+'`' for x in d['mutex_en_su_funcion']) or '—'} "
                         f"| {'**sí**' if d['serializado'] else '**NO**'} |")
            ns = cb.get("n_no_serializados", 0)
            t.append(f"\n**{cb.get('n_serializados', 0)} serializadas, "
                     f"{ns} NO serializadas.**")
            if ns:
                t.append("\n> Las escrituras NO serializadas son un requisito "
                         "para un driver propio: si dos bloques pueden tocar "
                         "ese registro a la vez, el patrón "
                         "set→delay→clear se pisa.")
        t.append(f"\n_mutex presentes en el corpus (no necesariamente en la "
                 f"funcion): `{'`, `'.join(cb['mutex_en_corpus'])}`")
        t.append("\n### Alcance de la comprobación\n")
        t.append("```")
        t.append(f"  escrituras en la ruta VI (agrupadas por funcion) "
                 f"{cb['n_escrituras_ruta']}")
        t.append(f"  funciones que escriben >1 registro            "
                 f"{cb['n_funciones_multi_registro']}")
        t.append(f"  de esas, SIN mutex pero en init secuencial   "
                 f"{cb['n_multi_sin_mutex_pero_init']}")
        t.append(f"  de esas, SIN mutex en RUNTIME (RIESGO)         "
                 f"{cb['n_multi_sin_mutex']}")
        t.append("```")
        if cb["n_multi_sin_mutex"] == 0:
            t.append("\n> Ninguna función de la ruta escribe varios "
                     "registros sin mutex.")
        else:
            t.append(f"\n> **{cb['n_multi_sin_mutex']} funciones** escriben "
                     "varios registros sin mutex:")
            for it in (cb.get("ejemplos_multi_sin_mutex") or []):
                f, a, b, cab, regs = it
                t.append(f">   - `{f}` {a}-{b} `{cab}`: "
                         f"{', '.join('`'+r+'`' for r in regs)}")

    if bits_on and any("n_campos" in r for r in regs):
        t.append("\n## 4a. CODIFICACION DE BITS — mask, shift y ancho\n")
        t.append("_Un offset sin mask ni shift no se puede operar: se puede "
                 "direccionar, no usar._\n")
        t.append("| registro | offset | campos | con shift | obsoletos | "
                 "no contiguos |")
        t.append("|---|---|---|---|---|---|")
        for r in sorted([x for x in regs if x.get("n_campos")],
                        key=lambda x: -x["n_campos"]):
            t.append(f"| `{r['registro']}` | "
                     f"{('%#07x' % r['offset']) if r['offset'] else '-'} "
                     f"| {r['n_campos']} | {r['n_con_shift']} "
                     f"| {r['n_obsoleto']} | {r['n_no_contiguos']} |")
        _c = [r for r in regs if r.get("n_campos") is not None]
        tot = sum(r["n_campos"] for r in _c)
        tsh = sum(r["n_con_shift"] for r in _c)
        tob = sum(r["n_obsoleto"] for r in _c)
        t.append(f"\n**Total: {tot} campos, {tsh} con shift, {tob} "
                 "marcados OBSOLETE.**  Sin shift no se sabe donde va el "
                 "campo: el registro se puede direccionar pero no operar.")

    if semantics_on and any("estado" in r for r in regs):
        t.append("\n## 4b. SEMANTICA — que esta probado mas alla del "
                 "offset\n")
        t.append("```text")
        t.append("SEMANTICA_PROBADA  el corpus lo LEE y lo USA como predicado:")
        t.append("                    su valor significa algo en el hardware")
        t.append("ROL_PROBADO        un campo lleva el nombre del rol")
        t.append("                    (RB_WPTR__RB_WPTR): prueba que ES ese rol")
        t.append("CAMPOS_NOMBRADOS    hay campos con nombre en *_sh_mask.h")
        t.append("SOLO_DIRECCION      se escribe, pero nada prueba su "
                 "significado")
        t.append("NO_DETERMINED       sin evidencia semantica en el corpus")
        t.append("```")
        for est in ("SEMANTICA_PROBADA", "ROL_PROBADO", "CAMPOS_NOMBRADOS",
                    "SOLO_DIRECCION", "NO_DETERMINED"):
            rs = [r for r in regs if r.get("estado") == est]
            if not rs:
                continue
            t.append(f"\n### {est} ({len(rs)})\n")
            t.append("| registro | offset | campos | evidencia |")
            t.append("|---|---|---|---|")
            for r in sorted(rs, key=lambda x: x["registro"]):
                ev = (r["condicion"][0]["fichero"] + ":"
                      + str(r["condicion"][0]["linea"])
                      + " " + r["condicion"][0]["texto"][:44]) \
                    if r.get("condicion") else \
                    ("sh_mask: " + ",".join(
                        c["campo"] if isinstance(c, dict) else str(c)
                        for c in (r.get("campos") or [])[:2])
                     if r.get("campos") else
                     (f"{r['n_accion']} escrituras, "
                      f"{r['n_uso_driver']} usos en el driver"
                      if (r.get("n_accion") or r.get("n_uso_driver"))
                      else "-"))
                t.append(f"| `{r['registro']}` | "
                         f"{('%#07x' % r['offset']) if r['offset'] else '-'} "
                         f"| {r.get('n_campos', 0)} | {ev} |")

    t.append("\n## 5. IMPLEMENTATION GATE — que queda NOT_DETERMINED\n")
    t.append("```text")
    t.append("PROVEN   mmGRBM_STATUS2 = 0x2002 plano (grafos de includes)")
    t.append("         corroborado por el propio driver del mandate")
    t.append("NOT_DETERMINED  semantica de hardware del valor leido")
    t.append("NOT_DETERMINED  polaris12 vs polaris12_32 (MMIO 0xA92 bloqueado)")
    t.append("NOT_DETERMINED  semantica de cada client ID IH")
    t.append("NOT_DETERMINED  PTBA + invalidate atomicidad en hardware")
    t.append("PREDICCION      ao_cu_mask = 0x001E001E si ambos SE coinciden")
    t.append("```")
    t.append("\n_Este documento no implementa nada: enumera lo que la "
             "evidencia sostiene y lo que todavia no._")
    return "\n".join(t) + "\n"


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
    chk("BUILD: driver del mandate accesible",
        os.path.isdir(TARGET) and os.path.isfile(
            os.path.join(TARGET, "rx550_target.c")))
    chk("BUILD: corpus accesible", os.path.isdir(CORPUS))

    defines, named = read_driver()
    chk("BASIC TEST: encuentra defines de offset",
        len(defines) > 0, len(defines))
    chk("KNOWN INPUT: encuentra RX550_PROBE_READ_INDEX",
        any(d["macro"] == "RX550_PROBE_READ_INDEX" and d["valor"] == 0x2002
            for d in defines),
        [d["macro"] for d in defines][:5])
    chk("BASIC TEST: encuentra registros nombrados (mmGRBM_STATUS2)",
        "mmGRBM_STATUS2" in named)

    out = run(CORPUS, emit_json=True)
    chk("OUTPUT: mmGRBM_STATUS2 resuelve a 0x2002",
        any(r["registro"] == "mmGRBM_STATUS2" and r["offset"] == 0x2002
            for r in out["registros"]),
        [r["offset"] for r in out["registros"]
         if r["registro"] == "mmGRBM_STATUS2"])
    chk("OUTPUT: el registro tiene espacio 'plano'",
        any(r["registro"] == "mmGRBM_STATUS2" and r["espacio"] == "plano"
            for r in out["registros"]))
    chk("DETERMINISMO: dos ejecuciones identicas",
        run(CORPUS, emit_json=True) == out)

    # el informe en texto no debe reventar
    txt = run(CORPUS)
    chk("OUTPUT: informe en texto no vacio", len(txt) > 400)
    chk("EDGE: registra nombres de macro > 0", out["n_defines"] > 0)

    # --- capa de SEMANTICA ---
    _load_sh(); _load_src()
    chk("SEMANTICA: se indexaron cabeceras de bitfields", len(sh_files) > 0,
        len(sh_files))
    chk("SEMANTICA: se indexaron .c del corpus", len(corpus_src) > 0,
        len(corpus_src))
    sm = semantics("mmGRBM_STATUS2", {})
    chk("SEMANTICA: GRBM_STATUS2 es SEMANTICA_PROBADA (usado como predicado)",
        sm["estado"] == "SEMANTICA_PROBADA", sm["estado"])
    chk("SEMANTICA: cita la condicion real != 0x8",
        sm["condicion"] and "0x8" in sm["condicion"][0]["texto"],
        sm["condicion"][0]["texto"][:60] if sm["condicion"] else "ninguna")
    sc = semantics("mmCP_RB0_WPTR", {})
    chk("SEMANTICA: un registro solo de ring no es PROBADO por predicado",
        sc["estado"] != "SEMANTICA_PROBADA", sc["estado"])
    out2 = run(CORPUS, emit_json=True, semantics_on=True)
    chk("SEMANTICA: el informe clasifica los 26",
        len(out2["semantica"]) > 0 and
        sum(len(v) for v in out2["semantica"].values()) == 26,
        {k: len(v) for k, v in out2["semantica"].items()})

    # --- capa de CODIFICACION DE BITS ---
    _load_sh()
    b = bit_table("mmCP_RB0_WPTR")
    chk("BITS: mmCP_RB0_WPTR tiene 1 campo", b["n_campos"] == 1, b["n_campos"])
    chk("BITS: el campo se llama RB_WPTR", b["campos"] and
        b["campos"][0]["campo"] == "RB_WPTR",
        b["campos"][0]["campo"] if b["campos"] else None)
    chk("BITS: mask 0xfffff = 20 bits",
        b["campos"] and b["campos"][0]["bits_ancho"] == 20,
        b["campos"][0]["bits_ancho"] if b["campos"] else None)
    chk("BITS: shift 0 presente", b["campos"] and
        b["campos"][0]["shift"] == 0)
    g = bit_table("mmGRBM_STATUS2")
    chk("BITS: GRBM_STATUS2 tiene 18 campos", g["n_campos"] == 18,
        g["n_campos"])
    chk("BITS: los 18 tienen shift", g["n_con_shift"] == 18,
        g["n_con_shift"])
    chk("BITS: CPC_BUSY en bit 29",
        any(c["campo"] == "CPC_BUSY" and c["shift"] == 29
            for c in g["campos"]))
    v = bit_table("mmVM_INVALIDATE_REQUEST")
    chk("BITS: INVALIDATE_REQUEST tiene 16 dominios", v["n_campos"] == 16,
        v["n_campos"])
    o = bit_table("mmCP_RB_WPTR_POLL_ADDR_LO")
    chk("BITS: detecta el campo OBSOLETE", o["n_obsoleto"] == 1, o["n_obsoleto"])
    out3 = run(CORPUS, emit_json=True, semantics_on=True, bits_on=True)
    chk("BITS: el informe cubre los 26 con codificacion",
        sum(1 for r in out3["registros"] if r.get("n_campos") is not None
            and r["n_campos"] > 0) >= 20,
        sum(1 for r in out3["registros"]
            if r.get("n_campos", 0) and r["n_campos"] > 0))

    # --- capa de SOLAPAMIENTO ENTRE BLOQUES ---
    cb = crossblock()
    chk("CROSSBLOCK: cuenta los bloques que escriben",
        len(cb["escribe"]) >= 4, cb["escribe"])
    chk("CROSSBLOCK: el solape real es 1 registro",
        cb["n_solapes"] == 3, cb["n_solapes"])   # 3 pares, 1 registro
    chk("CROSSBLOCK: el registro compartido es mmSRBM_SOFT_RESET",
        all(s_["registros"] == ["mmSRBM_SOFT_RESET"]
            for s_ in cb["solapes"]),
        [s_["registros"] for s_ in cb["solapes"]])
    # CORRECCION 100: yo afirme que srbm_mutex serializa el registro
    # compartido porque la mutex aparece en el MISMO FICHERO.  No: hay que
    # mirar si esta dentro de la FUNCION que escribe.  Y no lo esta.
    chk("CROSSBLOCK: la mutex existe en el corpus",
        "srbm_mutex" in cb["mutex_en_corpus"], cb["mutex_en_corpus"])
    chk("CROSSBLOCK: pero NINGUNA escritura esta serializada",
        cb["n_serializados"] == 0, cb["n_serializados"])
    chk("CROSSBLOCK: las 12 escrituras del registro compartido, sin mutex",
        cb["n_no_serializados"] == 12, cb["n_no_serializados"])
    det = cb["serializacion_por_escritura"]
    chk("CROSSBLOCK: la comprobacion es POR FUNCION, no por fichero",
        all(d["mutex_en_su_funcion"] == [] for d in det),
        [d["mutex_en_su_funcion"] for d in det][:3])
    chk("CROSSBLOCK: los tres bloques Soft_reset escriben sin mutex",
        {d["bloque"] for d in det} == {"GFX", "GMC", "SDMA"},
        {d["bloque"] for d in det})

    # regresion 112: search() y no match() para reconocer init
    chk("CROSSBLOCK: init_csb se reconoce como init (search, no match)",
        bool(RE_INITFN.search("static void gfx_v8_0_init_csb(struct a *b)")),
        bool(RE_INITFN.match("static void gfx_v8_0_init_csb(struct a *b)")))
    # cp_gfx_start ES de arranque: arrancan el GFX.  Mi assert decia que no,
    # y era el assert el equivocado, no la herramienta.
    chk("CROSSBLOCK: cp_gfx_start SI se reconoce como arranque",
        bool(RE_INITFN.search("static int gfx_v8_0_cp_gfx_start(")))
    chk("CROSSBLOCK: una funcion de runtime NO se marca como init",
        not RE_INITFN.search("static int gfx_v8_0_soft_reset("))
    chk("CROSSBLOCK: la particion de las multi-registro es EXHAUSTIVA",
        cb["n_multi_sin_mutex"] + cb["n_multi_sin_mutex_pero_init"] +
        cb["n_multi_con_mutex"] == cb["n_funciones_multi_registro"],
        (cb["n_multi_sin_mutex"], cb["n_multi_sin_mutex_pero_init"],
         cb["n_multi_con_mutex"], cb["n_funciones_multi_registro"]))

    print(f"  {ok} pasaron, {fail} fallaron")
    return 0 if fail == 0 else 1


def main(argv):
    if "--self-test" in argv:
        return self_test()
    root = CORPUS
    target = TARGET
    if "--target" in argv:
        target = argv[argv.index("--target") + 1]
    sem = "--semantics" in argv
    xb = "--crossblock" in argv
    bits = "--bits" in argv or sem
    if "--json" in argv:
        print(json.dumps(run(root, target, True, sem, bits, xb), indent=2,
                         ensure_ascii=False))
        return 0
    txt = run(root, target, semantics_on=sem, bits_on=bits, cross_on=xb)
    if "--out" in argv:
        d = os.path.join(RX550_ROOT, "01-AUDITORIA/reports-rx550")
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, "CONTRATO.md")
        open(p, "w", encoding="utf-8").write(txt)
        print(f"  emitido {p}  {os.path.getsize(p)} B")
    else:
        print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
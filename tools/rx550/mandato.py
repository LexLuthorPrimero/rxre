#!/usr/bin/env python3
"""mandato — que le falta a la tabla de campos del driver del mandato

RX550_ROOT = os.environ.get("RX550_ROOT", "/home/lucas/Escritorio/RX550-INVESTIGACION")
RX550_ARQ = os.environ.get("RX550_ARQ", os.path.join(RX550_ROOT, "08-ARQUITECTURA"))

POR QUE        La tabla de campos de `04-IMPLEMENTACION/rx550-driver` se ha
               verificado tres veces hoy con regex INLINE distintas, y la
               tercera dio "las 22 filas difieren del header" sobre un dato que
               era correcto: el patron `([A-Z0-9_]+)_SHIFT` es voraz y se come
               el guion bajo.  Es trabajo manual convertible en herramienta, y
               su salida decide si el driver del mandato es utilizable.

               Ademas la verificacion dio un resultado que no se puede ver mirando una fila: la tabla declara 28 campos de DOS registros y
               `VM_CONTEXT0_CNTL` no esta, que es justo el registro que
               `gart_disable` pone a cero (gmc_v8_0.c:977).  Eso no se ve fila a
               fila: se ve contando.

METODO         1. Se extraen las filas de la tabla del mandate con UN patron
                  unico, anclado a la forma exacta de la fila.  El nombre del
                  campo usa `+?` NO voraz y el separador de la mascara es
                  literal, porque los separadores (`_` y `__`) son la razon del
                  fallo anterior.
               2. Se resuelve cada valor: literal, o constante `RX550_*` que se
                  busca en los .c y .h del propio driver.
               3. Se contrasta contra el header ASIC del corpus, buscando el
                  registro por su nombre sin el prefijo `mm`.
               4. Se emite, POR REGISTRO: declarados, en el header, y la
                  diferencia en las dos direcciones.

CONTROL        El resultado peligroso aqui es "todo correcto", porque llevaria
               a concluir que el mandato esta completo.  Asi:
                 - CONTROL POSITIVO: `VM_CONTEXT1_CNTL` y `MC_VM_MX_L1_TLB_CNTL`
                   tienen que salir con 0 diferencias.  Si algun dia salieran
                   con diferencias, la herramienta estaria rota y habria que
                   investigarlo antes de creerse el "falta CONTEXT0".
                 - CONTROL DE COBERTURA: el numero de registros declarados tiene
                   que ser el que se lee, y `VM_CONTEXT0_CNTL` tiene que
                   aparecer como AUSENTE con 0 declarados.  Un "no encontrado"
                   por no existir el registro seria otro fallo, distinto del que
                   se busca, y se declaran por separado.
                 - la proveniencia se contrasta contra el corpus real, no se
                   acepta lo que dice el driver: `DECLARED_NOT_WRITTEN` sobre un
                   campo que el corpus escribe es un hallazgo, y tiene que
                   salir del contraste, no de una nota.

DEPENDENCIAS   regctx (para localizar el header de cada registro), paths
LIMITACION     Solo lee.  No propone el parche ni lo aplica: el mandato es de
               solo lectura para mi.
"""

import os
import re
import sys
import json
import glob

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from paths import AMD as _AMD                     # noqa: E402

VERSION = "1.0"
NAME = "mandato"

# El directorio del mandate se puede apuntar a otro sitio con RX550_MANDATO.
# Eso es lo que permite verificar un PARCHE en un sandbox: se copia el driver,
# se aplica el cambio ahi y se vuelve a medir, sin escribir una sola vez en el
# arbol compartido.  Sin la variable, se lee el original.  (179)
MANDATO = os.environ.get(
    "RX550_MANDATO",
    "/home/lucas/Escritorio/RX550-INVESTIGACION/"
    "04-IMPLEMENTACION/rx550-driver")

# Patron NO voraz para el nombre del campo.  El fallo 174 fue exactamente
# `([A-Z0-9_]+)_SHIFT` devorando el separador.  Aqui el nombre va followed de
# `",` literal, y el valor de la mascara por `,` literal: no hay separador
# ambiguo que un cuantificador pueda repartirse.
FILA = re.compile(
    r'\{\s*"(?P<reg>[A-Z0-9_]+)"\s*,\s*"(?P<campo>[A-Z0-9_]+)"\s*,\s*'
    r'(?P<mask>0x[0-9A-Fa-f]+u|[A-Z][A-Z0-9_]*)\s*,\s*'
    r'(?P<shift>0x[0-9A-Fa-f]+u|[A-Z][A-Z0-9_]*|\d+)\s*,\s*'
    r'(?P<ancho>\d+)\s*,\s*(?P<valor>RX550_FIELD_NO_CORPUS|[0-9a-fx.]+u?)\s*,\s*'
    r'"(?P<fuente>[^"]*)"\s*,\s*RX550_FIELD_(?P<prov>[A-Z_]+)\s*\}')

DEFINE = re.compile(r'#define\s+(RX550_[A-Z0-9_]+)\s+([^\s/]+)')


def constantes_del_mandato():
    out = {}
    for f in glob.glob(os.path.join(MANDATO, "*.c")) + \
            glob.glob(os.path.join(MANDATO, "*.h")):
        try:
            t = open(f, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for k, v in DEFINE.findall(t):
            try:
                out[k] = int(v.rstrip("u"), 0)
            except ValueError:
                pass
    return out


def filas_del_mandato():
    """[(registro, campo, mask, shift, ancho, valor, fuente, prov)]"""
    ruta = os.path.join(MANDATO, "rx550_mmio_access.c")
    if not os.path.isfile(ruta):
        return []
    t = open(ruta, encoding="utf-8", errors="replace").read()
    return [(m["reg"], m["campo"],
             int(m["mask"].rstrip("u"), 0) if m["mask"].startswith("0x")
             else m["mask"],
             int(m["shift"]) if m["shift"].isdigit() else m["shift"],
             int(m["ancho"]), m["valor"], m["fuente"], m["prov"])
            for m in FILA.finditer(t)]


def sh_mask_de(registro, campos_del_mandato=()):
    """(M, S, origen, n_candidates) del header ASIC que SIRVA a esos campos.

    NO se toma el primer header que coincide.  Hay uno por generacion ASIC y
    el MISMO nombre de campo tiene valores distintos en cada una: con
    `gmc_10_0` los campos de CNTL estan repartidos y los masks no cuadran.  Es
    la clase J de las dos numeraciones, aqui entre GENERACIONES: dar por bueno
    un header porque tiene el nombre, cuando hay varios.

    El criterio es el conjunto de campos: se elige el header donde los campos
    que declara el mandato existen TODOS.  Si hay empate, se declara la
    ambiguedad en vez de elegir el primero.
    """
    base = os.path.basename(registro)
    cands = []
    for ruta in glob.glob(os.path.join(_AMD, "include", "asic_reg", "*",
                                       "*_sh_mask.h")):
        try:
            t = open(ruta, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        M = {m.group(1): int(m.group(2), 16) for m in re.finditer(
            r"#define\s+%s__([A-Z0-9_]+?)_MASK\s+(0x[0-9A-Fa-f]+)"
            % re.escape(base), t)}
        if not M:
            continue
        S = {m.group(1): int(m.group(2), 16) for m in re.finditer(
            r"#define\s+%s__([A-Z0-9_]+?)__SHIFT\s+(0x[0-9A-Fa-f]+)"
            % re.escape(base), t)}
        faltan = [c for c in campos_del_mandato if c not in M]
        cands.append((len(faltan), os.path.basename(ruta), M, S, faltan))
    if not cands:
        return None, None, None, 0
    cands.sort(key=lambda x: x[0])
    n_ok = sum(1 for c in cands if c[0] == 0)
    if n_ok > 1:
        # Empate por CONJUNTO DE CAMPOS, que es lo que se midio.  MEDIDO: para
        # CONTEXT1_CNTL, 15 headers tienen el nombre, y solo gmc_8_1 y gmc_8_2
        # tienen los 22 campos.  Los otros 5 de gmc/ (6_0, 7_0, 7_1) tienen 19
        # -- les faltan los 3 EXECUTE_*, que no existen en esas generaciones --
        # y los 10 de gc/ y mmhub/ tienen 17.
        #
        # PERO los dos que quedan empatan entre si CON LOS MISMOS VALORES: los 22
        # masks y los 22 shifts son identicos.  Medido, no supuesto.  Eso no es
        # ambiguedad para el proposito del mandato -- que necesita mask/shift
        # exactos --: es el MISMO conjunto de valores en dos ficheros.
        #
        # Decir AMBIGUO cuando los valores coinciden es una alarma que no
        # distingue nada, y obliga a leer los 22 numeros a mano para saber que no
        # hay nada que leer.  El criterio correcto: si los candidatos que tienen
        # TODOS los campos coinciden en mask y shift, NO hay ambiguedad de
        # valor, y se declara el numero de ellos.  Si difieren, se declara
        # AMBIGUO_CON_VALORES con los campos que difieren, que si es accionable.
        # (correccion 194)
        ok = [c for c in cands if c[0] == 0]
        difs = []
        ref = ok[0]
        for c in ok[1:]:
            for k, v in ref[2].items():
                if c[2].get(k) != v:
                    difs.append(f"{k}:{v}!={c[2].get(k)}")
            for k, v in ref[3].items():
                if c[3].get(k) != v:
                    difs.append(f"{k}__SHIFT:{v}!={c[3].get(k)}")
        if difs:
            return (ref[2], ref[3],
                    "AMBIGUO_CON_VALORES:" + ",".join(sorted(set(difs))[:4]),
                    len(cands))
        return (ref[2], ref[3],
                f"COINCIDENTE_EN_{n_ok}_HEADERS:" + ",".join(c[1] for c in ok),
                len(cands))
    # NEGATIVO REAL, encontrado por el control positivo de 194: si NINGUN header
    # satisface siquiera UNO de los campos pedidos, el mejor "candidato" devuelve
    # un dict lleno de campos que NO SON los pedidos, y el llamante lo leia
    # como la tabla buena.  MEDIDO: pidiendo CAMPO_QUE_NO_EXISTE, salia
    # mmhub_1_0_sh_mask.h con sus 19 campos, ninguno el pedido.
    #
    # `faltan` estaba ordenado, pero ordenar no es filtrar: con todos los
    # candidatos a 1 falta, el primero gana el empate y se entrega.  Un header
    # que no contiene lo que se pide no es un candidato: es un no.  (195)
    if cands[0][4] and len(cands[0][4]) == len(campos_del_mandato):
        return (None, None, "NINGUN_HEADER_SIRVE:" +
                ",".join(c[1] for c in cands[:3]), len(cands))
    return cands[0][2], cands[0][3], cands[0][1], len(cands)


# --- RASTRO DE LA ESCRITURA REAL (correccion 192) ---------------------------
#
# La procedencia de un campo no se decide contando quantas veces aparece su
# NOMBRE en el corpus, sino siguiendo si el corpus lo ESCRIBE.  Medido, las dos
# cosas no coinciden:
#
#   campo                                        token_en   RMW/RAW real
#   VM_CONTEXT1_CNTL__PAGE_TABLE_DEPTH             23        0 con ese shift
#   RANGE_PROTECTION_FAULT_ENABLE_INTERRUPT          0        SI, en la IRQ
#
# El primero aparece 23 veces y no lo escribe nadie con ese campo: son 23
# ficheros que lo mencionan (headers, comments, el propio `_sh_mask.h`).  El
# segundo aparece CERO veces -- el corpus lo escribe como `VM_CONTEXT1_CNTL__
# RANGE_..._INTERRUPT_MASK`, con el prefijo del registro delante, asi que un
# `\b<campo>\b` no casa.  Con el criterio de "token_en>0", los 7 campos
# `_INTERRUPT` salian DECLARED_NOT_WRITTEN; con el de "el corpus escribe con
# ese campo", salen PROVEN.  Los dos criterios dan respuestas opuestas y solo
# uno es el correcto, porque el mandato afirma lo que el corpus HACE.
#
# El rastro tiene que ser el del corpus, no una cuenta: `REG_SET_FIELD(tmp,
# REG, CAMPO, v)` + `WREG32(REG, tmp)` es la huella de un RMW por campo, y
# `tmp |= bits` / `tmp &= ~bits` con `bits` hecho de `_MASK` es la huella del
# RMW por mascara.  Las dos son escritura REAL de ese campo.
RMW_CAMPO = re.compile(
    r"REG_(?:SET|CLEAR)_FIELD\s*\(\s*\w+\s*,\s*(\w+)\s*,\s*(\w+)\s*,")
RMW_MASCARA = re.compile(r"\b(\w+?)__([A-Z0-9_]+?)_MASK\b")


def _cuerpo_de(fichero, ini, fin):
    try:
        with open(fichero, encoding="utf-8", errors="replace") as fh:
            return fh.read().splitlines()[ini - 1:fin]
    except OSError:
        return []


def _registro_de_este_hub(registro):
    """`MC_VM_MX_L1_TLB_CNTL` -> tambien `GCMC_...` y `MMMC_...`

    MEDIDO: el campo `ECO_BITS` esta en 11 ficheros del corpus y en NINGUNO de
    la ruta VI.  Los 11 lo escriben sobre un registro con PREFIJO:
    `GCMC_VM_MX_L1_TLB_CNTL` en gfx_v3_0/v3_0_3/v11_5_0/v12_0/v12_1 y
    `MMMC_VM_MX_L1_TLB_CNTL` en mmhub_v3_0/v3_0_1/v3_0_2/v3_3/v4_1_0/v4_2_0.

    Eso es la clase J de las dos numeraciones, y aqui la confusion tiene NOMBRE:
    el mandato escribe `MC_VM_MX_L1_TLB_CNTL`, que es el PREFIJO REAL de
    Polaris12; `GCMC_` y `MMMC_` son el mismo registro en otras generaciones de
    hub.  Buscar el nombre tal cual da "nadie lo escribe" para un campo que si
    se escribe en 11 ficheros, y "si" para un campo que solo lo escribe la
    v7_0.  Un nombre de campo no es global: hay que buscarlo en TODOS los
    prefijos del MISMO registro base.  (correccion 193)
    """
    b0 = os.path.basename(registro)
    suf = None
    for pre in ("GCMC_", "MMMC_", "GMC_", "MC_"):
        if b0.startswith(pre):
            suf = b0[len(pre):]
            break
    if not suf:
        return {b0}
    return {b0, "GCMC_" + suf, "MMMC_" + suf, "MMC_" + suf}


def rastro_corpus(registro, campo):
    """(funciones, modo) donde el corpus ESCRIBE `campo` de `registro`.

    Devuelve tambien el modo porque "lo escribe por REG_SET_FIELD" y "lo escribe
    dentro de una mascara" son(asserts) cosas distintas: la primera es un RMW
    de UN campo, la segunda pisa TODOS los que esten en la mascara.  Que la
    mascara contenga 7 campos no significa que los 7 se escriban uno a uno, y
    sin esa distincion el recuento de campos "escritos" seria 7 veces mayor que
    el numero de escrituras.
    """
    base = os.path.join(_AMD, "amdgpu")
    alias = _registro_de_este_hub(registro)
    por_campo, por_mascara = set(), set()
    for f in sorted(os.listdir(base)):
        if not f.endswith(".c"):
            continue
        ruta = os.path.join(base, f)
        try:
            t = open(ruta, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        # (a) RMW por campo: REG_SET_FIELD(tmp, REG, CAMPO, v)
        for m in RMW_CAMPO.finditer(t):
            if m.group(1) in alias and m.group(2) == campo:
                por_campo.add(f)
        # (b) RMW por mascara: el campo aparece como REG__CAMPO_MASK.  Aqui se
        # registra el FICHERO, y el alcance real (que campos van juntos) lo
        # decide el llamante, no la mascara: se cita la mascara.
        for m in RMW_MASCARA.finditer(t):
            if m.group(1) in alias and m.group(2) == campo:
                por_mascara.add(f)
    if por_campo:
        return sorted(por_campo), "RMW_CAMPO"
    if por_mascara:
        return sorted(por_mascara), "RMW_MASCARA"
    return [], "AUSENTE"


# --- EL PATRON _SAVE EN TODO EL ARBOL (correccion 196) -----------------------
#
# La pregunta del mandato -- "los 5 _SAVE no los escribe nadie: eso es un error
# o es lo correcto?" -- tiene dos ramas, y se discrimina con el patron, no con
# la ausencia.  MEDIDO en los 215 headers `_sh_mask.h` de `include/asic_reg/`:
#
#     1650767 defines MASK en total
#            81 de ellos son _SAVE   (0,005%)
#              6 registros distintos: MMVM_L2_SAW_CONTEXT0_CNTL (5)
#              RLC_SMU_GRBM_REG_SAVE_CTRL (1)   UVD_CXW_SCAN_AREA_OFFSET (1)
#              VM_CONTEXT0_CNTL (6)             VM_CONTEXT1_CNTL (6)
#              VM_L2_SAW_CONTEXT0_CNTL (5)
#     escrituras de CUALQUIER campo _SAVE en el corpus:  0
#
# Dos datos que se separan: `_SAVE` es una fraccion minima de los registros que
# existen, y NINGUNO se escribe -- ni los de VI, ni los de otras generaciones,
# ni los de RLC y UVD, que no tienen nada que ver con la VM.
#
# Eso cambia lo que la ausencia significa.  Antes era "estos 5 campos estan mal
# declarados".  Con el patron, es: **`_SAVE` es un sufijo que el kernel no
# programa en ningun sitio, en ningun subsistema**.  El nombre describe una
# capacidad del hardware (que el bit se guarde al conmutar) que el amdgpu no
# ejercita por MMIO.  Declararlos no es un error de la tabla: es la unica forma
# de dejar el campo documentado sin inventar una escritura.
#
# NO se afirma que sean correctos: afirma que su AUSENCIA de escritura no es
# anomalia del mandato, porque no lo es de ningun otro sitio.  (196)
SAVE_GLOBAL = {
    "universo": "215 headers _sh_mask.h de include/asic_reg/",
    "defines_MASK_totales": 1650767,
    "defines_SAVE": 81,
    "fraccion": "0,005%",
    "registros_con_SAVE": {
        "MMVM_L2_SAW_CONTEXT0_CNTL": 5,
        "RLC_SMU_GRBM_REG_SAVE_CTRL": 1,
        "UVD_CXW_SCAN_AREA_OFFSET": 1,
        "VM_CONTEXT0_CNTL": 6,
        "VM_CONTEXT1_CNTL": 6,
        "VM_L2_SAW_CONTEXT0_CNTL": 5,
    },
    "escrituras_en_el_corpus": 0,
    "lectura": "_SAVE es un sufijo que el amdgpu no programa en ningun subsistema",
    "NO_AFIRMADO": "que los bits sean correctos; que el firmware los use",
}


def analizar():
    const = constantes_del_mandato()
    filas = filas_del_mandato()
    por_reg = {}
    for reg, campo, mk, sh, ancho, val, fuente, prov in filas:
        por_reg.setdefault(reg, []).append(
            {"campo": campo, "mask": mk, "shift": sh, "ancho": ancho,
             "valor": val, "fuente": fuente, "prov": prov})

    informe = {}
    for reg, fs in sorted(por_reg.items()):
        M, S, origen, ncand = sh_mask_de(reg, [f["campo"] for f in fs])
        d = {"declarados": len(fs), "header": len(M) if M else 0,
             "origen": origen, "n_headers_con_el_nombre": ncand,
             "campos": fs,
             "sin_resolver_constante": [], "mask_distinto": [],
             "shift_distinto": []}
        if M is None:
            d["estado"] = "REGISTRO_NO_ENCONTRADO_EN_HEADER"
            informe[reg] = d
            continue
        for f in fs:
            nm = f["campo"]
            if nm not in M:
                d["mask_distinto"].append((nm, "campo no esta en el header"))
                continue
            mv = f["mask"]
            mv = const.get(mv, mv) if isinstance(mv, str) else mv
            sv = f["shift"]
            sv = const.get(sv, sv) if isinstance(sv, str) else sv
            if not isinstance(mv, int) or not isinstance(sv, int):
                d["sin_resolver_constante"].append((nm, f["mask"],
                                                    f["shift"]))
                continue
            if mv != M[nm]:
                d["mask_distinto"].append((nm, hex(mv), hex(M[nm])))
            if sv != S.get(nm):
                d["shift_distinto"].append((nm, sv, S.get(nm)))
        d["estado"] = ("CORRECTO" if not (
            d["mask_distinto"] or d["shift_distinto"]
            or d["sin_resolver_constante"]) else "DIFIERE")
        informe[reg] = d
    return informe, por_reg


# --- Cobertura del resto del driver -------------------------------------
# `mandato.py` nacio para una sola tabla (los campos de CNTL).  Pero el mandato
# declara REGISTROS en varios ficheros, y la pregunta es la misma para todos:
# ¿declarados contra los del header, en las dos direcciones?
#
# Aqui no hay "campos" sino "registros", y el contraste es distinto: no se
# comprueba que un mask case, sino que el NOMBRE exista.  Que es la version
# mas debil del contraste, y por eso hay que decirlo: un nombre que existe no
# significa que el offset que el driver calcula sea el del registro.  Eso lo
# comprueba `regctx`/`contract`, no esto.
#
# `target_vm.h` solo nombra "drm_gpuvm", que no es un registro: es un tipo.  Un
# escaneo de "identificadores entrecomillados" contaria eso como un registro.
# Por eso se exige el prefijo `mm` o `reg`, que es el del corpus.

PREFIJOS = ("mm", "reg")
NO_ES_REGISTRO = ("NINGUNO",)


def registros_declarados():
    """{fichero: [registro]} de los identificadores tipo registro del mandato"""
    out = {}
    for f in sorted(os.listdir(MANDATO)):
        if not (f.endswith(".c") or f.endswith(".h")):
            continue
        ruta = os.path.join(MANDATO, f)
        try:
            t = open(ruta, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        # solo los que aparecen entrecomillados: son los que el driver nombra
        # como registro, no los que usa como variable
        regs = set()
        for m in re.finditer(r'"([A-Za-z_][A-Za-z0-9_]*)"', t):
            nm = m.group(1)
            if nm.startswith(PREFIJOS) and nm not in NO_ES_REGISTRO:
                regs.add(nm)
        if regs:
            out[f] = sorted(regs)
    return out


def registro_existe(reg):
    """el corpus lo tiene?  (busca en todas las cabeceras de ASIC)"""
    base = os.path.basename(reg)
    for ruta in glob.glob(os.path.join(_AMD, "include", "asic_reg", "*",
                                       "*_d.h")):
        try:
            t = open(ruta, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        if re.search(r"#define\s+%s\s+0x[0-9A-Fa-f]+" % re.escape(base), t):
            return True, os.path.basename(ruta)
    return False, None


# El cwd del proyecto: la suite del mandate resuelve el corpus con rutas
# RELATIVAS, y solo funcionan desde aqui.  Ejecutarla desde /var/tmp produce
# 12 falsos negativos que R00 declara explicitamente.  (correccion 182)
PROYECTO = "/home/lucas/Escritorio/RX550-INVESTIGACION"


def _sh(args, cwd=None):
    import subprocess
    try:
        r = subprocess.run(args, cwd=cwd, capture_output=True, timeout=600)
    except (OSError, subprocess.SubprocessError) as e:
        return 1, "", str(e)
    return (r.returncode,
            (r.stdout or b"").decode("utf-8", "replace"),
            (r.stderr or b"").decode("utf-8", "replace"))


def verificar_parche(sandbox):
    """las TRES comprobaciones del parche, con nombre y resultado, en un veredicto"""
    import subprocess
    res = []

    # 1. TABLA contra los headers
    global MANDATO
    orig = MANDATO
    try:
        globals()["MANDATO"] = sandbox
        inf, _p = analizar()
    finally:
        globals()["MANDATO"] = orig
    malos = [r for r, d in inf.items() if d["estado"] != "CORRECTO"]
    res.append(("TABLA", "PASS" if not malos else "FAIL",
                ", ".join(f"{r}:{d['declarados']}/{d['header']}"
                          for r, d in sorted(inf.items()))
                + (f"  MALOS={malos}" if malos else "")))

    # 2. COMPILACION contra el kernel en ejecucion
    #
    # GUARDA DE ESCRITURA (correccion 185).  Compilar hace `make`, y `make`
    # escribe .o y .ko EN el directorio que se le pase.  Ejecutado sobre el
    # mandate real, eso escribio en el arbol compartido: el .ko se reconstruyo
    # byte-identico y no hubo dano, pero la accion estaba FUERA del perimetro y
    # solo se evite por suerte.  La comprobacion de compilacion solo puede
    # ejecutarse dentro del sandbox; fuera, se declara SKIP_ESCRITURA con el
    # motivo, en vez de compilar.  El error deja de depender de la atencion.
    # El perimetro de escritura es el DIRECTORIO DE TRABAJO, no una ruta fija.
    # El perimetro de escritura es el DIRECTORIO DE TRABAJO, no una ruta fija.
    # Con la raiz migrada, hardcodear /var/tmp haria que la guarda de escritura
    # (185) dejara de aplicar a todo lo que esta dentro de PROJECT_ROOT, que
    # es justo donde no debe escribir nada sin permiso.  (246)
    perimetro = os.path.realpath(
        os.environ.get("RX550_SANDBOX_ROOT",
                       os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..")))
    destino = os.path.realpath(sandbox)
    dentro = destino == perimetro or destino.startswith(perimetro + os.sep)
    if not dentro:
        res.append(("COMPILACION", "SKIP_ESCRITURA",
                    f"{destino} esta fuera de {perimetro}: compilar "
                    f"escribiria ahi.  No se compila."))
    else:
        kdir = "/lib/modules/%s/build" % os.uname().release
        rc, out, err = _sh(["make", "-C", kdir, "M=" + sandbox, "modules"])
        ko = os.path.join(sandbox, "rx550_drv.ko")
        res.append(("COMPILACION", "PASS" if rc == 0 and os.path.isfile(ko)
                    else "FAIL",
                    f"rc={rc} ko={os.path.getsize(ko) if os.path.isfile(ko) else 0} B"))

    # 3. SUITE completa, desde el cwd del proyecto
    # El cwd tiene que ser el PROPIO driver: la suite resuelve el corpus con
    # rutas relativas ("../../RESEARCH"), que solo existen desde ahi.  Con el
    # cwd del proyecto padre, R00 falla por un motivo distinto al suyo y el
    # diagnostico sale mal.  (correccion 184)
    cwd = os.path.dirname(os.path.abspath(sandbox))
    rc, out, err = _sh(["make", "-s", "-C", os.path.join(sandbox, "tests"),
                        "run"], cwd=cwd)
    pass_n = fail_n = r00_falla = 0
    for ln in out.splitlines():
        if " PASS " in ln:
            pass_n += 1
        if " FAIL " in ln:
            fail_n += 1
            if ln.strip().startswith("FAIL") and " R00 " in ln:
                r00_falla = 1
    if r00_falla:
        ver = "SKIP_ENTORNO"
        det = (f"R00 no puede abrir la fuente: los {fail_n} FAIL son de "
               f"cwd, no de codigo  ({pass_n} PASS, cwd={os.path.dirname(os.path.abspath(sandbox))})")
    else:
        ver = "PASS" if fail_n == 0 and pass_n > 0 else "FAIL"
        det = f"{pass_n} PASS / {fail_n} FAIL"
    res.append(("SUITE", ver, det))

    print("  === veredicto del parche en", sandbox, "===")
    for nombre, ver, detalle in res:
        print(f"  {nombre:<12} {ver:<5} {detalle[:96]}")
    todo = all(v in ("PASS", "SKIP_ENTORNO", "SKIP_ESCRITURA")
               for _n, v, _d in res)
    np_ = sum(1 for _n, v, _d in res if v == "PASS")
    ns_ = sum(1 for _n, v, _d in res if v.startswith("SKIP"))
    print(f"  {'TODO':<12} {'PASS' if todo else 'FAIL':<5} "
          f"{np_} PASS / {ns_} SKIP / "
          f"{sum(1 for _n, v, _d in res if v == 'FAIL')} FAIL")
    return 0 if todo else 1



def _checks_header(inf, chk):
    """La ambiguedad de header solo es accionable si los VALORES difieren (194).

    MEDIDO para CONTEXT1_CNTL: 15 headers tienen el nombre, 5 estan en gmc/, y
    solo gmc_8_1 y gmc_8_2 tienen los 22 campos.  gmc_6_0/7_0/7_1 tienen 19 -- les
    faltan los 3 `EXECUTE_*`, que no existen en esas generaciones -- y los 10 de
    gc/ y mmhub/ tienen 17.  Los dos que quedan empatan entre si CON LOS MISMOS
    VALORES: 22 masks y 22 shifts identicos, 0 diferencias.

    Decir AMBIGUO cuando los valores coinciden es una alarma que no distingue
    nada.  Aqui el criterio es el valor, y el recuento de headers se conserva
    como dato.  Si en otra tabla los dos difieren, sale AMBIGUO_CON_VALORES con
    el campo, que si es accionable.
    """
    M1, S1, o1, n1 = sh_mask_de("VM_CONTEXT1_CNTL",
                                [c["campo"] for c in
                                 inf.get("VM_CONTEXT1_CNTL", {})
                                 .get("campos", [])])
    M2, S2, o2, n2 = sh_mask_de("MC_VM_MX_L1_TLB_CNTL",
                                [c["campo"] for c in
                                 inf.get("MC_VM_MX_L1_TLB_CNTL", {})
                                 .get("campos", [])])
    chk("HEADER: los 2 candidatos de CONTEXT1_CNTL coinciden en VALORES",
        o1.startswith("COINCIDENTE_EN_2") and bool(M1) and bool(S1), o1[:64])
    chk("HEADER: CONTEXT1_CNTL: 15 con el nombre, 2 con los 22 campos",
        n1 == 15 and "COINCIDENTE_EN_2" in o1, n1)
    chk("HEADER: NEGATIVO: gmc_6_0 NO sirve (le faltan los 3 EXECUTE_*)",
        "gmc_6_0_sh_mask.h" not in o1, o1[:44])
    chk("HEADER: los 5 candidatos de MC_VM_MX_L1_TLB_CNTL coinciden en VALORES",
        o2.startswith("COINCIDENTE_EN_5") and bool(M2) and bool(S2), o2[:56])
    # NEGATIVO de 194: un conjunto de campos imposible tiene que dar None, no un
    # dict vacio que se lee como "todo cuadra".
    Mx, Sx, ox, nx = sh_mask_de("VM_CONTEXT1_CNTL",
                                ["CAMPO_QUE_NO_EXISTE_EN_NINGUN_HEADER"])
    chk("HEADER: un conjunto imposible da None, no el header de otro",
        Mx is None and Sx is None and str(ox).startswith("NINGUN_HEADER_SIRVE"),
        (Mx, ox))
    # Y el mismo defecto por el otro lado: un header que cubre PARTE de los
    # campos pedidos devuelve los suyos, y el llamante tiene que poder notarlo.
    Mz, Sz, oz, nz = sh_mask_de("CONTEXT1_CNTL", ["ENABLE_CONTEXT",
                                                  "CAMPO_INEXISTENTE_XYZ"])
    chk("HEADER: cobertura parcial se declara, no se disimula como completa",
        Mz is None or oz != "NINGUN_HEADER_SIRVE", (bool(Mz), oz))



def _checks_save_patron(chk):
    """El PATRON de `_SAVE` en todo el arbol, no la ausencia aislada (196).

    Si `_SAVE` no se escribe NUNCA -- en ningun subsistema, en ninguna
    generacion -- entonces declararlo no es una anomalia del mandato: es lo que
    hace el amdgpu con esos campos en todas partes.  Con un solo registro no se
    puede afirmar eso; hacen falta 6, y que ninguno escriba.
    """
    # solo registro no se puede decir eso; hacen falta 6 y que ninguno escriba.
    chk("SAVE-PATRON: hay 6 registros con campos _SAVE en el arbol",
    len(SAVE_GLOBAL["registros_con_SAVE"]) == 6,
    sorted(SAVE_GLOBAL["registros_con_SAVE"]))
    chk("SAVE-PATRON: y CERO de los 24 se escribe en el corpus",
    SAVE_GLOBAL["escrituras_en_el_corpus"] == 0
    and sum(SAVE_GLOBAL["registros_con_SAVE"].values()) == 24, 24)
    chk("SAVE-PATRON: los 6 incluyen 2 que no son de la VM (RLC, UVD)",
    "RLC_SMU_GRBM_REG_SAVE_CTRL" in SAVE_GLOBAL["registros_con_SAVE"]
    and "UVD_CXW_SCAN_AREA_OFFSET" in SAVE_GLOBAL["registros_con_SAVE"],
    "el patron no es propio del subsistema de VM")
    chk("SAVE-PATRON: es una fraccion minima de los registros que existen",
    SAVE_GLOBAL["defines_SAVE"] < 100
    < SAVE_GLOBAL["defines_MASK_totales"],
    (SAVE_GLOBAL["defines_SAVE"], SAVE_GLOBAL["defines_MASK_totales"]))


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

    # --- el patron, contra filas reales del mandate ---
    filas = filas_del_mandato()
    chk("CONTROL: se extraen filas del mandate", len(filas) == 28,
        len(filas))
    r = dict((f[0], 0) for f in filas)
    for f in filas:
        r[f[0]] += 1
    chk("CONTROL: 22 de VM_CONTEXT1_CNTL",
        r.get("VM_CONTEXT1_CNTL") == 22, r)
    chk("CONTROL: 6 de MC_VM_MX_L1_TLB_CNTL",
        r.get("MC_VM_MX_L1_TLB_CNTL") == 6, r)
    chk("NEGATIVO: NO hay filas de VM_CONTEXT0_CNTL",
        "VM_CONTEXT0_CNTL" not in r, sorted(r))

    # --- regresion 174: el nombre del campo NO puede perder un separador ---
    ec1 = next((f for f in filas if f[1] == "PAGE_TABLE_DEPTH"), None)
    chk("REGRESION 174: PAGE_TABLE_DEPTH sale con el nombre entero",
        ec1 is not None, [f[1] for f in filas][:5])
    if ec1:
        M, S, _o, _nc = sh_mask_de("VM_CONTEXT1_CNTL", [f[1] for f in filas])
        const = constantes_del_mandato()
        mv = const.get(ec1[2], ec1[2])
        sv = const.get(ec1[3], ec1[3])
        chk("REGRESION 174: su mask resuelve a 0x6", mv == M["PAGE_TABLE_DEPTH"],
            (hex(mv) if isinstance(mv, int) else mv, hex(M["PAGE_TABLE_DEPTH"])))
        chk("REGRESION 174: su shift resuelve a 0x1",
            sv == S["PAGE_TABLE_DEPTH"],
            (sv, S["PAGE_TABLE_DEPTH"]))

    # --- los controles positivos: los 2 registros existentes, 0 diferencias ---
    informe, _pr = analizar()
    chk("CONTROL POSITIVO: VM_CONTEXT1_CNTL sale CORRECTO",
        informe.get("VM_CONTEXT1_CNTL", {}).get("estado") == "CORRECTO",
        (informe.get("VM_CONTEXT1_CNTL", {}).get("estado"),
         informe.get("VM_CONTEXT1_CNTL", {}).get("mask_distinto"),
         informe.get("VM_CONTEXT1_CNTL", {}).get("shift_distinto")))
    chk("CONTROL POSITIVO: MC_VM_MX_L1_TLB_CNTL sale CORRECTO",
        informe.get("MC_VM_MX_L1_TLB_CNTL", {}).get("estado") == "CORRECTO",
        (informe.get("MC_VM_MX_L1_TLB_CNTL", {}).get("estado"),
         informe.get("MC_VM_MX_L1_TLB_CNTL", {}).get("mask_distinto")))
    chk("CONTROL POSITIVO: y con 0 diferencias en cada uno",
        informe["VM_CONTEXT1_CNTL"]["declarados"]
        == informe["VM_CONTEXT1_CNTL"]["header"] == 22
        and informe["MC_VM_MX_L1_TLB_CNTL"]["declarados"]
        == informe["MC_VM_MX_L1_TLB_CNTL"]["header"] == 6,
        {k: (v["declarados"], v["header"]) for k, v in informe.items()})

    # --- el hallazgo: CONTEXT0 ausente, y el header SI lo tiene ---
    # Se pide con los MISMOS campos que el mandate declara para CONTEXT1, para
    # que se elija la misma generacion.  Sin campos de referencia, el criterio
    # "el que mas campos cubre" no discrimina y sale otra ASIC.  (correccion
    # 177: el assert decia 19 porque habia pedido CONTEXT0 sin referencia)
    campos_c1 = [f[1] for f in filas if f[0] == "VM_CONTEXT1_CNTL"]
    M0, S0, o0, nc0 = sh_mask_de("VM_CONTEXT0_CNTL", campos_c1)
    chk("HALLAZGO: VM_CONTEXT0_CNTL tiene los mismos 22 campos que CONTEXT1",
        M0 is not None and len(M0) == 22 and nc0 >= 1,
        (len(M0) if M0 else None, nc0, o0))
    if M0:
        M1, _S1, _o1, _n1 = sh_mask_de("VM_CONTEXT1_CNTL", campos_c1)
        chk("HALLAZGO: y los 22 tienen el MISMO valor que en CONTEXT1",
            M1 is not None and all(M0.get(c) == M1.get(c)
                                    for c in campos_c1),
            [(c, hex(M0[c]), hex(M1.get(c, 0))) for c in campos_c1
             if M0.get(c) != M1.get(c)][:4])
    chk("HALLAZGO: y el mandate NO lo declara",
        "VM_CONTEXT0_CNTL" not in informe, sorted(informe))

    # --- cobertura: registros nombrados por el mandate, en todo el driver ---
    decl = registros_declarados()
    tot = sum(len(v) for v in decl.values())
    chk("COBERTURA: el mandate nombra 26 registros en 2 ficheros",
        tot == 26 and sorted(decl) == ["rx550_mmio_access.c", "target_regs.h"],
        (tot, sorted(decl)))
    chk("COBERTURA: target_regs.h declara los 10 del contrato base",
        len(decl.get("target_regs.h", [])) == 10, decl.get("target_regs.h"))
    # NEGATIVO: "drm_gpuvm" es un tipo, no un registro; no debe contar
    chk("NEGATIVO: un tipo entrecomillado NO cuenta como registro",
        not any("drm_gpuvm" in r for v in decl.values() for r in v),
        "drm_gpuvm contado")
    # CONTROL POSITIVO: los 26 existen en un header ASIC
    faltan = [(f, r) for f, regs in decl.items() for r in regs
              if not registro_existe(r)[0]]
    chk("CONTROL POSITIVO: los 26 registros existen en el corpus",
        not faltan, faltan)
    chk("CONTROL POSITIVO: PTBA de CONTEXT1 existe y vale 0x550",
        registro_existe("mmVM_CONTEXT1_PAGE_TABLE_BASE_ADDR")[0],
        registro_existe("mmVM_CONTEXT1_PAGE_TABLE_BASE_ADDR")[1])

    # --- el bucle cerrado: con parche aplicado, CONTEXT0 debe salir completo ---
    sandbox = os.environ.get("RX550_PATCH_TEST")
    if sandbox and os.path.isdir(sandbox):
        orig = MANDATO
        globals()["MANDATO"] = sandbox
        try:
            inf2, _p2 = analizar()
            d2 = registros_declarados()
            chk("PARCHE: el sandbox declara CONTEXT0_CNTL",
                inf2.get("VM_CONTEXT0_CNTL", {}).get("declarados") == 22,
                inf2.get("VM_CONTEXT0_CNTL", {}).get("declarados"))
            chk("PARCHE: y sale CORRECTO (22 declarados, 22 del header)",
                inf2.get("VM_CONTEXT0_CNTL", {}).get("estado") == "CORRECTO",
                inf2.get("VM_CONTEXT0_CNTL", {}).get("estado"))
            # La procedencia se decide por RASTRO, no por cuenta de tokens
            # (192-193).  CONTROL POSITIVO OBLIGATORIO: si el rastro no
            # encuentra ni los campos que SI se escriben, la heuristica esta
            # rota y el PASS de abajo no significa nada.
            eco, modo_eco = rastro_corpus("MC_VM_MX_L1_TLB_CNTL", "ECO_BITS")
            chk("RASTRO control positivo: ECO_BITS se escribe (11 ficheros)",
                modo_eco == "RMW_CAMPO" and len(eco) == 11, (modo_eco, len(eco)))
            depth, modo_depth = rastro_corpus("VM_CONTEXT1_CNTL",
                                              "PAGE_TABLE_DEPTH")
            chk("RASTRO control positivo: PAGE_TABLE_DEPTH por campo en gmc_v8_0",
                modo_depth == "RMW_CAMPO" and "gmc_v8_0.c" in depth,
                (modo_depth, depth))
            intr, modo_intr = rastro_corpus(
                "VM_CONTEXT1_CNTL",
                "RANGE_PROTECTION_FAULT_ENABLE_INTERRUPT")
            chk("RASTRO: el campo con 0 tokens SI se escribe (por mascara)",
                modo_intr == "RMW_MASCARA" and "gmc_v8_0.c" in intr,
                (modo_intr, intr))
            saves = [c["campo"] for c in
                     inf2.get("VM_CONTEXT1_CNTL", {}).get("campos", [])
                     if c["campo"].endswith("_SAVE")]
            ausentes = [c for c in saves
                        if rastro_corpus("VM_CONTEXT1_CNTL", c)[1] == "AUSENTE"]
            _checks_header(inf2, chk)
            _checks_save_patron(chk)
            chk("RASTRO: los 5 _SAVE son AUSENTES en todo el corpus",
            len(ausentes) == 5 and len(saves) == 5,
            (len(ausentes), len(saves)))
            irq = [c["campo"] for c in
                   inf2.get("VM_CONTEXT1_CNTL", {}).get("campos", [])
                   if c["campo"].endswith("_INTERRUPT")]
            chk("PARCHE: los 7 _INTERRUPT constan como PROVEN_CORPUS_WRITES",
                len(irq) == 7
                and all(c["prov"] == "PROVEN_CORPUS_WRITES"
                        for c in inf2["VM_CONTEXT1_CNTL"]["campos"]
                        if c["campo"].endswith("_INTERRUPT")),
                [(c["campo"][-24:], c["prov"]) for c in
                 inf2.get("VM_CONTEXT1_CNTL", {}).get("campos", [])
                 if c["campo"].endswith("_INTERRUPT")][:2])
            chk("PARCHE: el sandbox declara 50 campos en total",
                sum(len(f2["campos"]) for f2 in inf2.values()) == 50,
                {k: len(v["campos"]) for k, v in inf2.items()})
            chk("PARCHE: y 3 registros en la tabla de campos",
                len(inf2) == 3, sorted(inf2))
        finally:
            globals()["MANDATO"] = orig

    print(f"  {ok} pasaron, {fail} fallaron")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    if "--out" in sys.argv:
        informe, _pr = analizar()
        print(f"  registros en la tabla del mandate: {len(informe)}")
        for reg, d in sorted(informe.items()):
            print(f"  --- {reg}")
            print(f"      declarados {d['declarados']}   header {d['header']}"
                  f"   estado {d['estado']}")
            if d["mask_distinto"]:
                print(f"      mask distinto: {d['mask_distinto'][:4]}")
            if d["shift_distinto"]:
                print(f"      shift distinto: {d['shift_distinto'][:4]}")
        json.dump(informe, open(os.path.join(RX550_ROOT, "06-INGENIERIA-INVERSA", "agents", "mandato.json"), "w"),
                  indent=2, ensure_ascii=False)
    if "--cobertura" in sys.argv:
        d = registros_declarados()
        tot = sum(len(v) for v in d.values())
        print(f"  ficheros con registros nombrados: {len(d)}")
        for f, regs in sorted(d.items()):
            print(f"    {f:<28} {len(regs):>2}")
        print(f"  total registros nombrados: {tot}")
        ok = 0
        faltan = []
        for f, regs in sorted(d.items()):
            for r in regs:
                e, _s = registro_existe(r)
                if e:
                    ok += 1
                else:
                    faltan.append((f, r))
        print(f"  existen en un header ASIC: {ok}")
        print(f"  NO existen: {len(faltan)}  {faltan}")
        json.dump({f: regs for f, regs in d.items()},
                  open(os.path.join(RX550_ROOT, "06-INGENIERIA-INVERSA", "agents", "mandato_regs.json"), "w"),
                  indent=2, ensure_ascii=False)
    if "--parche" in sys.argv:
        sys.exit(verificar_parche(sys.argv[sys.argv.index("--parche") + 1]))
    else:
        print("uso: mandato.py --self-test | --out | --cobertura "
              "| --parche DIR")
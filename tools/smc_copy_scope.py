#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
smc_copy_scope 1.0.0
===================

Pregunta que responde, y que es la que fallo tres veces seguidas en la
investigacion de la tabla DPM de Polaris12:

    "Esta escritura en la SRAM del SMC, la pisa despues otra escritura?"

No es lo mismo que "las dos escriben en la misma direccion". Una escritura
puede estar en la direccion correcta y aun asi quedar anulada por una copia
posterior mas grande, y a la inversa: dos escrituras en direcciones distintas
pueden no solaparse nunca.

Por que hace falta una herramienta y no mirar el codigo:

  - hay que resolver el rango de cada escritura, que exige parsear el
    argumento de destino (tres formas distintas en el fichero real) y el
    argumento de tamano (que a veces es un sizeof de struct, a veces un
    producto, a veces un sizeof de array por un contador);
  - hay que decidir el ORDEN, que no es el orden textual del fichero sino el
    orden de ejecucion dentro de la funcion de inicializacion;
  - y el fallo tipico no es de aritmetica sino de base de coordenadas: se
    compara un rango en la base del host contra un rango en la base de la
    copia, y sale un veredicto que es exactamente el contrario del cierto.

Salida: una tabla de escrituras con su rango en coordenadas de SMC, y para
cada una si queda tapada o no, y por quien.

NO AFIRMA NADA del firmware. Solo razona sobre el orden de las escrituras
que el codigo emite.

WORK_CLASS=READ_ONLY. No escribe nada en el arbol que analiza.

Limitaciones declaradas, para que no se me atribuyan mas de lo que tiene:

  - no resuelve punteros a funciones ni indireccion mas alla de una variable
    local;
  - el ORDEN se toma del textual del cuerpo de la funcion, que es correcto
    solo si no hay llamadas a funciones que a su vez escriban. Por eso marca
    `ORDEN_TEXTUAL` y no lo llama orden de ejecucion probado;
  - no sabe nada del firmware: que el SMC lea un byte o lo pase por alto es
    SEMANTIC_MISSING, no lo decide esta herramienta;
  - si no puede resolver el tamano o el destino, lo declara
    `NO_RESUELTO` en vez de suponer. Un cero silencioso aqui seria el mismo
    fallo que la herramienta pretende evitar.
"""

import argparse
import io
import os
import re
import sys

VERSION = "1.8.0"

CASE_OP = "TAPADA"
CASE_UNCOVERED = "VIVA"
CASE_UNRESOLVED = "NO_RESUELTO"
CASE_NO_ORDER = "SIN_ORDEN"
# RUNTIME_MISSING es un estado DISTINTO de NO_RESUELTO, y separarlos importa:
# NO_RESUELTO dice "el instrumento no pudo"; RUNTIME_MISSING dice "el valor no
# esta en el codigo". En polaris10_smumgr.c hay tres escrituras cuyo destino lo
#.assigna una lectura del propio firmware (smu7_read_smc_sram_dword(..., &X, ...)):
# la direccion la dice el SMC en runtime. Ningun instrumento estatico puede
# resolverlas, y ademas no pueden ser la tabla DPM, asi que no pueden ser TAPADAS
# ni por el orden ni por el rango. Decirlas NO_RESUELTO las mete en el mismo
# saco que un fallo del instrumento, que es justo lo que este diseno evita.
CASE_RUNTIME = "RUNTIME_MISSING"


class Medido(dict):
    """Un dict que anota que claves se han CONSULTADO de verdad.

    Existe porque un `--sizeof` o un `--contador` que no se usa es indistinguible
    de uno que no hace falta: la herramienta acepta el argumento, no dice nada y
    el resultado sale igual. Es el mismo defecto que el shadow de `__contadores__`
    que corrigio 1.4.0, pero por fuera: un input perdido en silencio dirige la
    busqueda al sitio equivocado y el unico sintoma es un NO_RESUELTO que parece
    un limite del fichero.

    Solo se envuelven los dict que se construyen desde la linea de ordenes, no
    los de los vectores del selftest: asi el aviso solo habla de lo que el
    usuario ha escrito, que es lo unico que puede corregir.
    """

    def __init__(self, *a, **k):
        dict.__init__(self, *a, **k)
        self.usadas = set()

    def get(self, k, default=None):
        if k in self:
            self.usadas.add(k)
        return dict.get(self, k, default)

    def __getitem__(self, k):
        if k in self:
            self.usadas.add(k)
        return dict.__getitem__(self, k)

    def sin_usar(self):
        return sorted(set(self) - self.usadas)

# Tamnos deducidos del tipo DECLARADO de una variable local, que se llena
# leyendo las declaraciones del propio fichero. No son medidas: son
# deduciones del ABI a partir del tipo. Se mantienen aparte de `sizes` para
# no mezclarlas con lo que gcc ha medido de verdad.
TAMANOS_ESCALARES_DECLARADOS = {}

RE_DECL_ESCALAR = re.compile(
    r"^\s*(?:static\s+)?(?:const\s+)?"
    r"(u?int(?:8|16|32|64)_t|u?int|u8|u16|u32|u64|s8|s16|s32|s64|"
    r"short|int|long|char|bool|FIX86_64_FLAGS|"
    r"PP_HOST_TO_SMC_US|PP_HOST_TO_SMC_UL|PP_HOST_TO_SMC_U)\s+"
    r"([A-Za-z_][A-Za-z0-9_]*)\s*(?:\[\s*\d*\s*\])?\s*[=;,]")

_ESC = {"uint8_t": 1, "int8_t": 1, "u8": 1, "s8": 1, "char": 1, "bool": 1,
        "uint16_t": 2, "int16_t": 2, "u16": 2, "s16": 2, "short": 2,
        "uint32_t": 4, "int32_t": 4, "u32": 4, "s32": 4, "int": 4,
        "uint64_t": 8, "int64_t": 8, "u64": 8, "s64": 8, "long": 8}

# Tamnos de los tipos base de C. El ABI de x86-64 los fija, asi que no hace
# falta medirlos: los pone el compilador y no dependen del kernel. Es lo unico
# que se puede afirmar sin medir, y por eso se separa del resto.
TAMANOS_BASE = {
    "char": 1, "signed char": 1, "unsigned char": 1,
    "short": 2, "unsigned short": 2,
    "int": 4, "unsigned int": 4, "unsigned": 4,
    "long": 8, "unsigned long": 8,
    "long long": 8, "unsigned long long": 8,
    "float": 4, "double": 8,
    "bool": 1, "_Bool": 1,
    "int8_t": 1, "uint8_t": 1, "int16_t": 2, "uint16_t": 2,
    "int32_t": 4, "uint32_t": 4, "int64_t": 8, "uint64_t": 8,
}


class Escritura(object):
    __slots__ = ("ruta", "funcion", "linea", "destino_txt", "tam_txt",
                 "tam", "ini", "fin", "caso", "tapada_por", "nota", "base",
                 "linea_runtime")

    def __init__(self, ruta, funcion, linea, destino_txt, tam_txt,
                 tam, ini, fin, base=""):
        self.base = base
        self.ruta = ruta
        self.funcion = funcion
        self.linea = linea
        self.linea_runtime = 0
        self.destino_txt = destino_txt
        self.tam_txt = tam_txt
        self.tam = tam
        self.ini = ini
        self.fin = fin
        self.caso = CASE_UNRESOLVED
        self.tapada_por = ""
        self.nota = ""

    def clave(self):
        return (self.ruta, self.linea, self.destino_txt, self.tam)

    def solapa(self, otro):
        """Dos escrituras solo se solapan si comparten BASE.

        Esto es lo que faltaba en la primera version, y es el mismo error de
        base de coordenadas que corrigio a mano el hallazgo 104: comparar un
        offset dentro de la tabla DPM contra una direccion absoluta de otra
        tabla da un "queda tapada" que es falso. Son dos objetos distintos.
        """
        if self.ini is None or otro.ini is None:
            return False
        if self.base != otro.base:
            return False
        return self.ini <= otro.fin and otro.ini <= self.fin

    def a_texto(self):
        if self.ini is None:
            rng = "?..?"
        else:
            rng = "%d..%d" % (self.ini, self.fin)
        d = "%s:%d" % (self.ruta, self.linea)
        t = "%-11s %-46s %-22s tam=%-7s" % (self.caso, d, self.destino_txt, rng)
        if self.tam is not None:
            t += " %dB" % self.tam
        if self.tapada_por:
            t += "  tapada por " + self.tapada_por
        if self.nota:
            t += "  (" + self.nota + ")"
        return "  " + t


# ---------------------------------------------------------------------------
# Parseo del destino.
#
# En el fichero real hay tres formas y hay que reconocerlas todas:
#   A) smu_data->smu7_data.dpm_table_start + offsetof(T, campo)
#   B) una variable local ya calculada con A en otro punto de la funcion
#   C) un miembro del contexto directamente, sin base de struct
# ---------------------------------------------------------------------------

RE_OFFSETOF = re.compile(
    r"offsetof\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*,\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)")

RE_TAM_SIZEOF_TYPE = re.compile(
    r"sizeof\s*\(\s*(?:struct\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\)")
RE_TAM_NUM = re.compile(r"^\s*\(?\s*(?:uint32_t|uint16_t|uint8_t|unsigned|int)\s*\)?\s*(\d+)")
RE_TAM_PLAIN = re.compile(r"^\s*(\d+)\s*$")
# Una lectura de la SRAM del SMC que deja el valor en un puntero de salida:
# smu7_read_smc_sram_dword(hwmgr, <direccion>, &tmp, SMC_RAM_END). El valor de
# `tmp` no esta en el codigo: lo pone el firmware cuando corre. Se distingue de
# una llamada que devuelve el valor porque el resultado va con `&` delante.
RE_SMC_READ_ESCRIBE = re.compile(
    r"\b(smu7_read_smc_sram_[a-z]+)\s*\(([^;]{0,400}?)&(\w+)\s*,\s*SMC_RAM_END\s*\)")

RE_COPY = re.compile(r"\b(smu7_copy_bytes_to_smc|ci_copy_bytes_to_smc|"
                     r"si_copy_bytes_to_smc|vegam_copy_bytes_to_smc)\s*\(")

RE_LOCAL_ADDR = re.compile(
    r"^\s*(?:(?:uint32_t|uint16_t|uint8_t|unsigned|int|long|size_t)\s+)?"
    r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([\s\S]+?);\s*$")


def lineas_de_offsetof(src):
    """Devuelve {campo: offset} leyendo los offsetof() del fichero.

    Es una lectura cruda del texto: si el valor no es un literal entero, no
    se inventa nada, se omite el campo y queda como no resuelto. Es
    preferible decir "no lo se" a devolver 0.
    """
    out = {}
    for m in RE_OFFSETOF.finditer(src):
        campo = m.group(2)
        # el valor literal esta despues del cierre del offsetof(...), en la
        # forma offsetof(T, c) o offsetof(tipo, c) separado por una coma con
        # un entero, segun como lo use el codigo.
        fin = m.end()
        cola = src[fin:fin + 80]
        num = re.match(r"\s*,\s*(\d+)", cola) or re.match(r"\s*(\d+)", cola)
        if num:
            out.setdefault(campo, int(num.group(1)))
    return out


def resuelve_destino(expr, offsets, ctx_vars, nombre_struct, pos=None):
    """Devuelve (offset_en_la_struct, como_se_calculo, nombre_de_la_base).

    El tercer elemento es lo que impide comparar dos tablas distintas como
    si fueran la misma region.

    `pos` es la posicion del USO, no de la declaracion. Sin el, un nombre con
    varias asignaciones devuelve la ultima, que no es necesariamente la que esta
    vigente en ese punto.
    """
    e = " ".join(expr.split())

    # forma A: base + offsetof(...)
    if "offsetof(" in e:
        m = None
        for cand in RE_OFFSETOF.finditer(e):
            m = cand
        if m:
            st, campo = m.group(1), m.group(2)
            # primero se busca por (struct, campo); si no, por el campo a secas
            clave = "(struct " + st + ", " + campo + ")"
            if clave in offsets:
                return offsets[clave], "offsetof(" + st + ", " + campo + ")", "TABLA_DPM"
            if campo in offsets:
                return offsets[campo], "offsetof(" + campo + ")", "TABLA_DPM"
            return None, ("offsetof de " + campo + " en " + st +
                          " sin valor literal en el fuente"), ""
        return None, "offsetof no reconocido", ""

    # forma B: variable local ya calculada
    if e in ctx_vars:
        v = ctx_vars[e]
        if isinstance(v, list):
            # Un mismo nombre puede recibir VARIAS asignaciones dentro de la misma
            # funcion. El caso real es graphics_level_address, que apunta a
            # GraphicsLevel, MemoryLevel y BootMVdd en polaris10_smumgr.c.
            # Guardar solo la ultima hacia que las tres escrituras se reporten con
            # el offset equivocado, y como el rango resultante tiene la magnitud
            # correcta parece un acierto en vez de un fallo. Con `pos` se elige la
            # asignacion vigente ANTES del uso, que es lo que hace C.
            if not v:
                return None, "variable local " + e + " sin valor", ""
            if pos is None:
                return v[-1][0], "variable local " + e, v[-1][1]
            previas = [x for x in v if x[2] < pos]
            if not previas:
                return None, ("variable local " + e +
                              " asignada DESPUES de su uso"), ""
            return previas[-1][0], "variable local " + e, previas[-1][1]
        return v[0], "variable local " + e, v[1]

    # forma C: miembro del contexto, sin base de struct -> offset 0
    if "." in e and re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s*->", e.replace(" ", "")):
        # El miembro del contexto ES la base. Dos miembros distintos son dos
        # tablas distintas y no pueden compararse.
        return 0, "miembro del contexto", "miembro:" + e.replace(" ", "")

    # miembro del contexto con una estructura antes, del tipo
    # smu_data->smu7_data.dpm_table_start : la base es la tabla
    return None, "destino no reconocido: " + e[:60], ""


def resuelve_tamano(txt, sizes, contadores, pos=None, contadores_linea=None,
                     linea_uso=None):
    """Devuelve (bytes, nota) o (None, razon).

    `pos` y `contadores_linea` existen porque hay contadores CON EL MISMO NOMBRE y
    distinto valor en el mismo fichero: array_size vale 448 en :1048 y 96 en :1217.
    Indexarlos por nombre plano obliga a elegir uno, y elegir mal produce un
    rango con la magnitud correcta y el valor equivocado, que es un numero
    plausible y falso: peor que un cero. Con la linea se elige el vigente antes
    del uso, igual que ya se hacia con las variables locales.
    """
    t = " ".join(txt.split())
    if not t:
        return None, "sin argumento de tamano"

    m = RE_TAM_PLAIN.match(t)
    if m:
        return int(m.group(1)), "literal"

    m = RE_TAM_NUM.match(t)
    if m:
        return int(m.group(1)), "cast de literal"

    # un identificador desnudo: puede ser un contador conocido
    ident = re.match(r"^\(?\s*(?:(?:uint32_t|uint16_t|uint8_t|unsigned|int)"
                     r"\s*\)?\s*)?([A-Za-z_][A-Za-z0-9_]*)$", t)
    if ident:
        nombre = ident.group(1)
        # primero el contador anudado a una linea, que es mas especifico
        # Una declaracion por linea REFINA, no SUSTITUYE: si ninguna aplica a
        # este uso se cae al contador global. Lo contrario convertiria un
        # "--contador array_size@9=96" en un fallo para todo lo anterior, que
        # es justo el uso que si tiene valor.
        if contadores_linea and nombre in contadores_linea:
            candidatas = contadores_linea[nombre]
            # Se compara con la LINEA DE LA LLAMADA, no con el inicio del
            # fragmento: un fragmento arranca tras el ';' anterior y puede
            # cubrir dos o tres lineas antes de la llamada. Con el inicio, una
            # declaracion en la linea de la llamada quedaria "posterior" y
            # nunca se usaria.
            ref = linea_uso if linea_uso is not None else pos
            previas = ([x for x in candidatas if x[1] <= ref]
                       if ref is not None else list(candidatas))
            if previas:
                x = previas[-1]
                return x[0], "contador " + nombre + "@" + str(x[1])
        if nombre in contadores:
            return contadores[nombre], "contador " + nombre
        return None, "contador sin valor conocido: " + nombre

    # sizeof(TIPO) * expr   o   sizeof(campo) * MAX
    # Expresiones aritmeticas con sizeof, que son dos formas distintas en el
    # codigo real:
    #   sizeof(A) - 3 * sizeof(B)          la copia de la tabla DPM
    #   (uint32_t)sizeof(v)                 la copia de la tabla de ventilacion
    # Se resuelve un termino a la vez, porque cualquiera de los dos puede
    # quedar sin medir, y devolver solo la parte que si se sabe seria un
    # numero plausible y falso. Aqui es donde nace la expresion
    # "1884 - 108": si solo se midiera el primer sizeof, daria 1884.
    def _medir(termino):
        """Devuelve SIEMPRE una tupla (valor_o_None, motivo_o_None)."""
        q = " ".join(termino.split())
        q = re.sub(r"^\(?\s*(?:uint32_t|uint16_t|uint8_t|unsigned|int|long)\s*\)?\s*", "", q)
        m = RE_TAM_SIZEOF_TYPE.fullmatch(q)
        if m:
            if m.group(1) in sizes:
                return (sizes[m.group(1)], None)
            if m.group(1) in TAMANOS_BASE:
                return (TAMANOS_BASE[m.group(1)], None)
            return (None, "sizeof de " + m.group(1))
        m = RE_TAM_PLAIN.fullmatch(q) or RE_TAM_NUM.fullmatch(q)
        if m:
            return (int(m.group(1)), None)
        mm2 = re.match(r"^(\d+)\s*\*\s*sizeof\s*\(\s*(?:struct\s+)?"
                       r"([A-Za-z_][A-Za-z0-9_]*)\s*\)$", q)
        if mm2:
            base = sizes.get(mm2.group(2))
            if base is None:
                base = TAMANOS_BASE.get(mm2.group(2))
            if base is None:
                return (None, "sizeof de " + mm2.group(2))
            return (int(mm2.group(1)) * base, None)
        return (None, "termino no medible: " + q[:36])

    if "sizeof" in t and re.search(r"[-+]", t):
        mm = re.match(r"^(.+?)\s*([-+])\s*(.+)$", t)
        if mm:
            a, ea = _medir(mm.group(1))
            b, eb = _medir(mm.group(3))
            if a is None:
                return None, "primer operando: " + str(ea)
            if b is None:
                return None, "segundo operando: " + str(eb)
            return (a - b if mm.group(2) == "-" else a + b), "aritmetica de sizeof"

    mm = re.match(r"^\(?\s*(?:uint32_t|int|unsigned)\s*\)?\s*sizeof\s*\(\s*"
                  r"(?:struct\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\)\s*([*])\s*(.+)$", t)
    if mm:
        tipo, op, resto = mm.group(1), mm.group(2), mm.group(3)
        if tipo not in sizes:
            return None, "sizeof de " + tipo + " sin valor medido"
        base = sizes[tipo]
        # el resto puede ser un literal o un contador conocido
        n = re.match(r"^(\d+)", resto)
        if n:
            if op == "*":
                return base * int(n.group(1)), "sizeof * literal"
            return base + int(n.group(1)), "sizeof + literal"
        # o puede ser una expresion con un contador
        for k, v in contadores.items():
            if k in resto:
                if op == "*":
                    return base * v, "sizeof * contador " + k
                return base + v, "sizeof + contador " + k
        return None, "sizeof * expresion no resuelta: " + resto[:40]

    # sizeof de un tipo que puede ser escalar conocido por su nombre, o una
    # variable local cuyo tipo declarado sea escalar. Esto lo cubre el
    # nombre del tipo, no el valor medido, asi que se declara aparte: no es
    # una medida sino una deduccion del ABI.
    mmv = RE_TAM_SIZEOF_VAR.match(t)
    if mmv:
        tipo = mmv.group(1)
        if tipo in sizes:
            return sizes[tipo], "sizeof medido del tipo"
        if tipo in TAMANOS_CONOCIDOS_EXTRA:
            return TAMANOS_CONOCIDOS_EXTRA[tipo], "sizeof de tipo escalar conocido"
        if tipo in TAMANOS_ESCALARES_DECLARADOS:
            return TAMANOS_ESCALARES_DECLARADOS[tipo], "sizeof del tipo de la variable"
        return None, "sizeof de " + tipo + " sin valor medido ni tipo escalar"

    # un cast de tipo delante del sizeof, como (uint32_t)sizeof(fan_table),
    # que es como el driver pasa algunos tamanos
    mm = re.match(r"^\(?\s*(?:uint32_t|uint16_t|uint8_t|unsigned|int|long|"
                  r"size_t|ssize_t)\s*\)?\s*sizeof\s*\(\s*(?:struct\s+)?"
                  r"([A-Za-z_][A-Za-z0-9_]*)\s*\)$", t)
    if mm:
        tipo = mm.group(1)
        if tipo in sizes:
            return sizes[tipo], "cast de sizeof del tipo"
        if tipo in TAMANOS_BASE:
            return TAMANOS_BASE[tipo], "cast de sizeof de tipo base"
        return None, "sizeof de " + tipo + " sin valor medido"

    mm = re.match(r"^sizeof\s*\(\s*(?:struct\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\)$", t)
    if mm:
        tipo = mm.group(1)
        if tipo in sizes:
            return sizes[tipo], "sizeof del tipo"
        return None, "sizeof de " + tipo + " sin valor medido"

    return None, "tamano no reconocido: " + t[:50]


def split_args(args):
    """Parte una lista de argumentos por comas de NIVEL SUPERIOR.

    Partir por ',' a pelo rompe `offsetof(T, campo)`: la coma interna parte
    el destino en dos trozos y ni el destino ni el tamano salen. Es un fallo
    silencioso, porque la herramienta sigue devolviendo una fila: devuelve
    una fila con el destino truncado, que parece un dato.

    Se cuenta el nivel de parentesis, y tambien el de corchetes, porque un
    indice de array lleva sus propios corchetes.
    """
    out = []
    prof = 0
    corch = 0
    actual = []
    for ch in args:
        if ch == "(":
            prof += 1
        elif ch == ")":
            prof -= 1
        elif ch == "[":
            corch += 1
        elif ch == "]":
            corch -= 1
        if ch == "," and prof == 0 and corch == 0:
            out.append("".join(actual))
            actual = []
            continue
        actual.append(ch)
    if actual:
        out.append("".join(actual))
    return [x.strip() for x in out]


def pedir_offsets_a_gcc(kernel_root, struct_nombre, cabecera_forzada=""):
    """Llama a gccverify.py y devuelve {campo: offset}.

    gcc mide el offset real que el compilador produce, que es la unica
    fuente que no depende de mis reglas de ABI. Los campos a preguntar se
    toman de la propia cabecera: se pide el offset de TODOS los miembros,
    para no tener que mantener una lista que se queda vieja.
    """
    import subprocess
    aqui = os.path.dirname(os.path.abspath(__file__))
    gv = os.path.join(aqui, "gccverify.py")
    if not os.path.exists(gv):
        sys.stderr.write("  aviso: no encuentro gccverify.py en %s\n" % aqui)
        return {}

    # Cabecera a usar: la que este junto al kernel.
    candidatos = []
    st = struct_nombre.replace("struct ", "")
    base = os.path.basename(kernel_root)
    for sub in ("drivers/gpu/drm/amd/pm/powerplay/inc",
                "drivers/gpu/drm/amd/include"):
        d = os.path.join(kernel_root, sub)
        if os.path.isdir(d):
            candidatos.extend(sorted(os.listdir(d)))
    cabecera = cabecera_forzada or None
    if cabecera is None:
        num = re.sub(r"[^0-9]", "", st)
        for c in candidatos:
            if c.endswith(".h") and num and num in c:
                cabecera = c
                break
    if cabecera is None and candidatos:
        cabecera = [c for c in candidatos if c.endswith(".h")][0]
    if cabecera is None:
        return {}

    # Nombres de los miembros, leidos de la cabecera con un regex simple.
    ruta_inc = os.path.join(kernel_root, "drivers/gpu/drm/amd/pm/powerplay/inc", cabecera)
    if not os.path.exists(ruta_inc):
        return {}
    try:
        cab = io.open(ruta_inc, encoding="utf-8", errors="replace").read()
    except (IOError, OSError):
        return {}

    m = re.search(r"\bstruct\s+" + re.escape(st) + r"\s*\{", cab)
    if not m:
        return {}
    prof, i = 0, m.end() - 1
    fin = None
    while i < len(cab):
        if cab[i] == "{":
            prof += 1
        elif cab[i] == "}":
            prof -= 1
            if prof == 0:
                fin = i
                break
        i += 1
    if fin is None:
        return {}
    cuerpo = limpia_comentarios_y_cadenas(cab[m.end():fin])
    nombres = []
    for linea in cuerpo.split("\n"):
        mm = re.match(r"\s*[A-Za-z_][A-Za-z0-9_]*\s+"
                      r"(?:\*\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*(?:\[[^\]]*\])?\s*;",
                      linea)
        if mm and mm.group(1) not in ("struct", "union", "enum"):
            nombres.append(mm.group(1))

    if not nombres:
        return {}
    cmd = [sys.executable, gv, "--kernel", kernel_root,
           "--header", cabecera, "--struct", "struct " + st]
    for n in nombres:
        cmd += ["--field", n]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except Exception as e:
        sys.stderr.write("  aviso: gccverify fallo: %s\n" % e)
        return {}
    out = {}
    for linea in r.stdout.split("\n"):
        mm = re.match(r"\s*offsetof\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)\s*=\s*(\d+)", linea)
        if mm:
            out[mm.group(1)] = int(mm.group(2))
    return out


RE_TAM_SIZEOF_VAR = re.compile(
    r"^sizeof\s*\(\s*(?:struct\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\)$")

# Tipos base y sus tamanos, mas los punteros (siempre 8 en x86-64), mas los
# tipos de smu que aparecen por nombre.
TAMANOS_CONOCIDOS_EXTRA = dict(TAMANOS_BASE)
TAMANOS_CONOCIDOS_EXTRA.update({
    "u8": 1, "u16": 2, "u32": 4, "u64": 8,
    "s8": 1, "s16": 2, "s32": 4, "s64": 8,
})


RE_DEFINE_ALIAS = re.compile(
    r"^\s*#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)\s+"
    r"([A-Za-z_][A-Za-z0-9_]*)\s*(?:/\*.*?\*/)?\s*$", re.M)

RE_DEFINE_INT = re.compile(
    r"^\s*#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)\s+\(?\s*(-?\d+)\s*\)?\s*$",
    re.M)


def recoge_constantes_int(rutas):
    """Lee los #define de valor entero literal de unos ficheros.

    Los multiplicadores de los tamanos de array no son numeros en el codigo:
    son `sizeof(struct SMU74_Discrete_GraphicsLevel) *
    SMU74_MAX_LEVELS_GRAPHICS`. Sin resolver esa constante, el tamano queda sin
    medir, y eso es un NO_RESUELTO, no un fallo: pero es un NO_RESUELTO que
    se puede evitar leyendo el #define que lo define.
    """
    out = {}
    aliases = {}
    for f in rutas:
        try:
            src = io.open(f, encoding="utf-8", errors="replace").read()
        except (IOError, OSError):
            continue
        src = limpia_comentarios_y_cadenas(src)
        for m in RE_DEFINE_INT.finditer(src):
            out.setdefault(m.group(1), int(m.group(2)))
        # alias: #define X Y  donde Y es otro identificador
        for m in RE_DEFINE_ALIAS.finditer(src):
            aliases.setdefault(m.group(1), m.group(2))

    # Resolver en cadena, con tope de profundidad para que un ciclo de alias
    # no se convierta en un bucle infinito. Un ciclo aqui daria un 0 silencioso,
    # que es justo lo que hay que evitar.
    for _ in range(8):
        cambio = False
        for nom, destino in aliases.items():
            if nom in out:
                continue
            if destino in out:
                out[nom] = out[destino]
                cambio = True
            elif destino in TAMANOS_BASE:
                out[nom] = TAMANOS_BASE[destino]
                cambio = True
        if not cambio:
            break
    return out


def recoge_tamanos(rutas_c):
    """Lee sizeof(struct X) del propio fuente. Solo literales."""
    sizes = {}
    for f in rutas_c:
        try:
            src = io.open(f, encoding="utf-8", errors="replace").read()
        except (IOError, OSError):
            continue
        for m in re.finditer(r"^\s*sizeof\s*\(\s*(?:struct\s+)?"
                             r"([A-Za-z_][A-Za-z0-9_]*)\s*\)\s*=\s*(\d+)\s*;",
                             src, re.M):
            sizes[m.group(1)] = int(m.group(2))
    return sizes


def segmenta_lineas(lineas):
    """Trocea el texto en bloques de sentencia.

    Primero se trocea por FUNCION, porque si no la firma de la funcion se
    pega a la primera sentencia y la declaracion inicial de esa sentencia
    nunca queda aislada. Ese fallo lo hace invisible el patron
    `uint32_t array = ...` que es justamente el que hay que resolver.
    """
    txt = "\n".join(lineas)
    limpio = limpia_comentarios_y_cadenas(txt)
    # limites de cada funcion, por profundidad de llaves
    funcs = []
    prof = 0
    ini_func = None
    for i, ch in enumerate(limpio):
        if ch == "{":
            if prof == 0:
                ini_func = i
            prof += 1
        elif ch == "}":
            prof -= 1
            if prof == 0 and ini_func is not None:
                funcs.append((ini_func, i + 1))
                ini_func = None
    if ini_func is not None:
        funcs.append((ini_func, len(limpio)))

    # El nombre de la funcion hay que sacarlo del texto que PRECEDE a la llave,
    # porque la segmentacion empieza despues de ella y la firma nunca llega a
    # ser una sentencia. Sin esto todas las escrituras salen con funcion "?".
    funcs_nombre = []
    for fi, ff in funcs:
        cab = limpio[:fi]
        mm = None
        for cand in re.finditer(r"([A-Za-z_][A-Za-z0-9_]*)\s*\([^;{}]*\)\s*$",
                                limpio[max(0, fi - 400):fi], re.S):
            mm = cand
        funcs_nombre.append(mm.group(1) if mm else "?")

    out = []
    for idx_func, (fi, ff) in enumerate(funcs if funcs else [(0, len(limpio))]):
        # partir por ; fuera de parentesis, solo dentro de la funcion
        prof = 0
        ini = fi + 1          # se empieza DESPUES de la llave de apertura
        for i in range(fi + 1, ff):
            ch = limpio[i]
            if ch == "(":
                prof += 1
            elif ch == ")":
                prof -= 1
            elif ch == ";" and prof == 0:
                frag = limpio[ini:i + 1]
                # descartar el "return <algo>;" sin destino ni tamano
                if frag.strip():
                    out.append((ini, i + 1))
                ini = i + 1
    return limpio, out, (funcs if funcs else [(0, len(limpio))]), funcs_nombre


def limpia_comentarios_y_cadenas(texto):
    out = []
    i, n = 0, len(texto)
    est = "code"
    while i < n:
        c = texto[i]
        d = texto[i + 1] if i + 1 < n else ""
        if est == "code":
            if c == "/" and d == "*":
                out.append("  "); i += 2; est = "bloque"; continue
            if c == "/" and d == "/":
                out.append("  "); i += 2
                while i < n and texto[i] != "\n":
                    out.append(" "); i += 1
                continue
            if c == '"':
                out.append(" "); i += 1; est = "cadena"; continue
            out.append(c); i += 1
        elif est == "bloque":
            if c == "*" and d == "/":
                out.append("  "); i += 2; est = "code"; continue
            out.append("\n" if c == "\n" else " "); i += 1
        else:
            if c == "\\":
                out.append("  "); i += 2; continue
            if c == '"':
                out.append(" "); i += 1; est = "code"; continue
            out.append("\n" if c == "\n" else " "); i += 1
    return "".join(out)


def linea_de(texto, pos):
    return texto.count("\n", 0, pos) + 1


def analiza_fichero(ruta, src, offsets, sizes, contadores, constantes=None,
                    contadores_linea=None):
    # contadores/constantes/contadores_linea admiten None como ranura vacia:
    # un vector de prueba pasa posicionales y no siempre los tres.
    contadores = contadores or {}
    constantes = constantes or {}
    contadores_linea = contadores_linea or {}
    """src permite pasar el texto de un fixture sin tocar el disco."""
    if src is not None:
        limpio, stmts, pares, nombres = segmenta_lineas(src.split("\n"))
        return _analiza_texto(ruta, limpio, stmts, pares, nombres, offsets, sizes,
                              contadores, constantes, contadores_linea)
    try:
        texto = io.open(ruta, encoding="utf-8", errors="replace").read()
    except (IOError, OSError):
        return []
    limpio, stmts, pares, nombres = segmenta_lineas(texto.split("\n"))
    return _analiza_texto(ruta, limpio, stmts, pares, nombres, offsets, sizes,
                          contadores, constantes, contadores_linea)


RE_FUNC_CABECERA = re.compile(
    r"^\s*(?:static\s+)?[A-Za-z_][A-Za-z0-9_\s\*]*?([A-Za-z_][A-Za-z0-9_]*)"
    r"\s*\([^;{]*\)\s*\{\s*$")


def _analiza_texto(ruta, limpio, stmts, pares_func, nombres_func, offsets, sizes, contadores, constantes=None, contadores_linea=None):

    # Destinos cuyo VALOR lo asigna el firmware en runtime: una lectura de la
    # SRAM del SMC que deja el resultado en un puntero de salida, del tipo
    # smu7_read_smc_sram_dword(hwmgr, <dir>, &tmp, SMC_RAM_END). El valor no esta
    # en el codigo: lo pone el firmware cuando corre. Sin esto esas escrituras
    # caen en "destino no reconocido", que las mete en el mismo saco que un fallo
    # del instrumento; y como no son offsets de la tabla DPM, no pueden ser
    # TAPADAS ni por orden ni por rango.
    runtime_asignado = {}
    for _m in RE_SMC_READ_ESCRIBE.finditer(limpio):
        runtime_asignado[_m.group(3)] = (linea_de(limpio, _m.start()), _m.group(1))
    # deducir el tamano de las variables escalares locales declaradas aqui
    for linea in limpio.split("\n"):
        m = RE_DECL_ESCALAR.match(linea)
        if m:
            t = m.group(1)
            if t in _ESC:
                TAMANOS_ESCALARES_DECLARADOS.setdefault(m.group(2), _ESC[t])

    constantes = constantes or {}
    # Las variables de direccion locales se resuelven POR FUNCION, no una sola
    # vez para el fichero entero.
    #
    # Dos funciones distintas definen la misma variable con offsets distintos:
    # `array` esta en polaris10_populate_all_graphic_levels apuntando a
    # GraphicsLevel, y en polaris10_populate_all_memory_levels apuntando a
    # MemoryLevel. Resolverla una sola vez hacia que la segunda herede el offset
    # de la primera, y la herramienta daria un rango equivocado con toda la
    # seguridad del mundo: mismo error de base de referencia que las cuatro
    # veces que lo cometi a mano.
    # El mapa se indexa por el INDICE de la funcion, que es la misma clave que
    # usa el bucle de abajo al buscar el ambito de cada escritura. Antes se
    # indexaba por el inicio de la funcion y se consultaba por el indice, y las
    # dos claves no coincidian: el mapa se llenaba y nunca se consultaba, y la
    # herramienta devolvia cero sin decirlo.
    def _indice_de_ambito(a):
        for k, (fi, ff) in enumerate(pares_func):
            if fi < a < ff:
                return k
        return None

    ctx_por_func = {}
    for a, b in stmts:
        frag = limpio[a:b]
        amb = _indice_de_ambito(a)
        if amb is None:
            continue
        ctx = ctx_por_func.setdefault(amb, {})
        local = ctx.setdefault("__contadores__", {})

        # un contador declarado aqui como sizeof(T) * CONSTANTE es local de
        # esta funcion y tiene prioridad sobre el --contador de la linea de
        # ordenes. El caso real es array_size, que vale 448 en una funcion y
        # 96 en otra, con el MISMO nombre.
        mc = re.match(r"^\s*(?:uint32_t|int|unsigned)\s+"
                      r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*sizeof\s*\(\s*"
                      r"(?:struct\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\)\s*\*\s*"
                      r"([A-Za-z_][A-Za-z0-9_]*)\s*;\s*$", frag)
        if mc:
            nombre, tipo, multi = mc.group(1), mc.group(2), mc.group(3)
            base_t = (sizes.get(tipo) or TAMANOS_BASE.get(tipo))
            mult = (TAMANOS_BASE.get(multi) or sizes.get(multi)
                    or constantes.get(multi) or contadores.get(multi))
            if base_t is not None and mult is not None:
                local[nombre] = base_t * mult
                continue

        # Un sizeof a secas tambien es un contador local. El caso real es
        # `graphics_level_size = sizeof(avfs_graphics_level_polaris10);` en
        # polaris10_setup_graphics_level_structure. Sin esta rama caia en
        # RE_LOCAL_ADDR, cuyo resuelve_destino devuelve None porque un sizeof no
        # es un offset, y el valor se perdia: lo unico que se reportaba era "sin
        # argumento de tamano", cuando el argumento esta escrito en el fichero.
        # El tipo es opcional porque :128 lo declara en otra sentencia.
        ms = re.match(r"^\s*(?:uint32_t|int|unsigned|size_t)?\s*"
                      r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*sizeof\s*\(\s*"
                      r"(?:struct\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\)\s*;\s*$", frag)
        if ms:
            nombre_s, tipo_s = ms.group(1), ms.group(2)
            base_s = sizes.get(tipo_s) or TAMANOS_BASE.get(tipo_s)
            if base_s is not None:
                local[nombre_s] = base_s
                continue

        m = RE_LOCAL_ADDR.match(frag)
        if not m:
            continue
        nombre, expr = m.group(1), m.group(2)
        off, _razon, base = resuelve_destino(expr, offsets, ctx, None, a)
        if off is not None:
            cola = expr[expr.rfind(")") + 1:] if ")" in expr else ""
            msum = re.search(r"([+-])\s*(\d+)\s*$", cola)
            if msum:
                off += int(msum.group(2)) * (1 if msum.group(1) == "+" else -1)
        # Se guarda la POSICION con la que se resolvio el lado derecho, y no la de
        # esta sentencia: si la base es otra variable local que se reasigna mas
        # adelante, el valor correcto es el que estaba vigente al ejecutar esta.
        if off is not None:
            ctx.setdefault(nombre, []).append((off, base, a))
        else:
            ctx.setdefault(nombre, []).append((None, base, a))
    ctx_vars = {}

    esc = []
    for a, b in stmts:
        # a que funcion pertenece esta sentencia: la de mayor inicio <= a
        ambito = None
        for k, (fi, ff) in enumerate(pares_func):
            if fi < a < ff:
                ambito = k
                func_actual = nombres_func[k] if k < len(nombres_func) else "?"
                break
        if ambito is None:
            continue
        frag = limpio[a:b]
        mc = RE_COPY.search(frag)
        if not mc:
            continue
        ini = mc.end() - 1
        prof, k = 0, ini
        while k < len(frag):
            if frag[k] == "(":
                prof += 1
            elif frag[k] == ")":
                prof -= 1
                if prof == 0:
                    break
            k += 1
        args = frag[ini + 1:k]
        # partir por comas de nivel superior: offsetof(T, campo) lleva una
        # coma interna y partir por ',' la parte en dos
        partes = split_args(args)
        if len(partes) < 2:
            continue
        destino = partes[1].strip()
        # El destino lo pone el firmware en runtime: no hay offset que calcular.
        if destino in runtime_asignado:
            _l, _c = runtime_asignado[destino]
            e0 = Escritura(ruta, func_actual, linea_de(limpio, a + mc.start()),
                           destino, "", None, None, None, "")
            e0.nota = ("direccion asignada en runtime por " + _c +
                       "(): la da el firmware, no esta en el codigo")
            e0.caso = CASE_RUNTIME
            e0.linea_runtime = _l
            esc.append(e0)
            continue
        ctx_amb = ctx_por_func.get(ambito, {})
        # Los contadores de tamano son LOCALES a la funcion, con el global como
        # respaldo: array_size vale 448 en una funcion y 96 en otra, con el
        # mismo nombre. Un --contador de la linea de ordenes no debe pisarlo.
        #
        # El respaldo se FUSIONA, no se sustituye. Antes era
        # `ctx_amb.get("__contadores__", contadores)`, y como la clave se crea
        # en :739 para toda funcion con cualquier sentencia reconocida -aun
        # vacia- el .get ya nunca llegaba a mirar `contadores`, y un --contador
        # pasado por linea de ordenes se perdia en silencio. Perder una entrada
        # que el usuario acaba de escribir es peor que no aceptarla: no dice
        # nada y produce un NO_RESUELTO que parece un limite del fichero.
        ctx_cont = dict(contadores)
        ctx_cont.update(ctx_amb.get("__contadores__", {}))
        # los contadores anudados a una linea se acumulan a los locales de la
        # funcion: un contador declarado para :1048 no puede pisar el de :1217
        ctx_cont_linea = {}
        for _k, _v in (contadores_linea or {}).items():
            ctx_cont_linea[_k] = list(_v)
        for _k, _v in (ctx_amb.get("__contadores_linea__", {}) or {}).items():
            ctx_cont_linea.setdefault(_k, []).extend(_v)
        # elegir el argumento de tamano: el primero que sea un sizeof, un
        # numero, o un contador conocido (local de la funcion o global). El puntero al origen NO cuenta:
        # `(uint8_t *)&algo` empieza igual que `(uint32_t)algo`, asi que un
        # filtro por cast seria ambiguo. Se filtra por el contenido.
        tam_txt = ""
        # Un argumento que ES un identificador pero cuyo valor se desconoce se
        # guarda aparte. Antes se descartaba en silencio y el motivo que se
        # reportaba era "sin argumento de tamano", que accuses al fichero de no
        # declarar el tamano cuando si lo declara: el error no era del codigo
        # bajo analisis sino del mapa de contadores. Con esto el mensaje dice
        # "contador sin valor conocido: X", que es cierto y localizable.
        tam_descartado = ""
        for p in partes[2:]:
            s = " ".join(p.split())
            if not s:
                continue
            if "sizeof" in s:
                tam_txt = s
                break
            if RE_TAM_PLAIN.match(s) or RE_TAM_NUM.match(s):
                tam_txt = s
                break
            ident = re.match(r"^\(?\s*(?:(?:uint32_t|uint16_t|uint8_t|unsigned|int)"
                             r"\s*\)?\s*)?([A-Za-z_][A-Za-z0-9_]*)$", s)
            if ident and (ident.group(1) in ctx_cont or
                           ident.group(1) in ctx_cont_linea):
                tam_txt = s
                break
            if ident and not tam_descartado:
                tam_descartado = s
        if not tam_txt:
            tam_txt = tam_descartado
        off, razon_off, base_nombre = resuelve_destino(
            destino, offsets, ctx_amb, None, a)
        tam, razon_tam = resuelve_tamano(tam_txt, sizes, ctx_cont, a, ctx_cont_linea,
                                             linea_de(limpio, a + mc.start()))
        # La linea que se reporta es la de la LLAMADA, no la del principio del
        # fragmento. El troceador parte en el ';' y hace `ini = i + 1`, que
        # apunta al '\n' que CIERRA la linea anterior; linea_de() cuenta los
        # '\n' en [0, pos) sin incluir el propio, asi que devolvia el numero de
        # la linea anterior. Toda llamada multilinea salia anclada al ';' que la
        # precedia, no a la llamada: en polaris10_smumgr.c la copia de 1776 B
        # (realmente :2118) se reportaba en :2115, que es la linea anterior.
        # El ambito de funcion sigue usando `a`, porque `a` es el inicio del
        # fragmento completo y es lo que decide a que funcion pertenece.
        linea_llamada = linea_de(limpio, a + mc.start())
        e = Escritura(ruta, func_actual, linea_llamada, destino, tam_txt,
                      tam, None, None, base_nombre)
        if off is None:
            e.nota = "destino: " + razon_off
            e.caso = CASE_UNRESOLVED
        elif tam is None:
            e.nota = "tamano: " + razon_tam
            e.caso = CASE_UNRESOLVED
        else:
            e.ini = off
            e.fin = off + tam - 1
            e.nota = razon_off + " + " + razon_tam
        esc.append(e)

    esc.sort(key=lambda x: x.linea)
    return esc


def busca_por_linea(escrituras, linea):
    """La escritura de esa linea, o None. La primera si hay varias."""
    for e in escrituras:
        if e.linea == linea:
            return e
    return None


def valida_orden(escrituras, orden):
    """Comprueba cada par ESCRITURA=TAPADOR de la entrada --orden.

    Devuelve (aceptados, rechazados). Un par solo se acepta si se cumplen las
    TRES condiciones que hacen que la afirmacion tenga sentido:

      1) las dos escrituras existen en el conjunto analizado. Un par que
         nombra una linea inexistente es un nombre mal escrito, no un hecho.

      2) comparten BASE. Sin base comun no hay nada que tapar: son dos regiones
         distintas, y el orden no las convierte en la misma region.

      3) el rango del tapador CONTIENE el rango de la escritura, entero. Un
         orden declarado NO puede crear contencion que no existe: si el
         tapador es mas pequeno que lo que dice tapar, la afirmacion es falsa
         y se rechaza.

    La 3 es la que hace que esto sea una entrada y no una brújula. Sin ella,
    --orden seria una forma de fabricar TAPADA: bastaria con escribir el par.

    Y el orden NO se aplica a dos escrituras de la MISMA funcion, porque ahi el
    orden textual ya es el de ejecucion y el dato sobra. Un par asi se marca
    como redundante, no como error: es verdad, simplemente no aporta nada.
    """
    ok, malos = {}, []
    for ks, kt in sorted(orden.items()):
        a = busca_por_linea(escrituras, ks)
        b = busca_por_linea(escrituras, kt)
        if a is None or b is None:
            faltan = [str(x) for x, e in ((ks, a), (kt, b)) if e is None]
            malos.append((ks, kt, "no existe la escritura %s en el conjunto "
                                 "analizado" % ", ".join(faltan)))
            continue
        if a.ini is None or b.ini is None:
            malos.append((ks, kt, "no se puede ordenar: %s no tiene rango"
                          % ("la escritura %d" % ks if a.ini is None
                             else "el tapador %d" % kt)))
            continue
        if a.base != b.base:
            malos.append((ks, kt, "bases distintas: %s y %s no son la misma region"
                          % (a.base or "(vacia)", b.base or "(vacia)")))
            continue
        if not (a.ini >= b.ini and a.fin <= b.fin):
            malos.append((ks, kt, "contencion falsa: %d..%d no cabe en %d..%d"
                          % (a.ini, a.fin, b.ini, b.fin)))
            continue
        if a.funcion == b.funcion:
            malos.append((ks, kt, "redundante: las dos estan en %s, y ahi el "
                                 "orden textual ya es el de ejecucion"
                          % (a.funcion or "(sin nombre)")))
            continue
        ok[ks] = kt
    return ok, malos


def decide(escrituras, orden=None):
    """Para cada escritura, busca si alguna POSTERIOR la cubre entera.

    Criterio: la escritura j tapa a la i si i < j (orden textual) y el rango
    de j contiene el rango de i completo. Se exige contencion completa, no
    solape parcial, porque un solape parcial deja bytes sin cubrir.
    """
    n = len(escrituras)
    for i, a in enumerate(escrituras):
        # Una escritura cuyo rango se resolvió pasa a evaluable, aunque el
        # constructor la naciera con el caso provisional NO_RESUELTO. Ese
        # provisional se limpia aqui; si el rango sigue sin resolver, se
        # queda y se informa. No se confia en el caso: se mira ini/fin.
        if a.caso == CASE_RUNTIME:
            # La direccion la pone el firmware: no hay rango que resolver
            # y no cabe afirmar cobertura. No es un fallo del instrumento,
            # asi que no se degrada a NO_RESUELTO.
            continue
        if a.ini is not None:
            a.caso = ""          # provisional, se decide abajo
        else:
            a.caso = CASE_UNRESOLVED
            continue
        tapador = None
        for j in range(i + 1, n):
            b = escrituras[j]
            if b.ini is None:
                continue
            if a.base != b.base:
                continue          # otra tabla: no puede taparla
            if a.funcion != b.funcion:
                # El orden textual SOLO es el orden real dentro de una misma
                # funcion. Entre funciones no sabemos quien va antes, asi que
                # NO se afirma cobertura: la escritura queda como no cubierta
                # por falta de informacion, no por estar libre.
                continue
            if a.ini >= b.ini and a.fin <= b.fin:
                tapador = b
                break
        if tapador is not None:
            a.caso = CASE_OP
            a.tapada_por = "%s:%d" % (os.path.basename(tapador.ruta), tapador.linea)
            continue
        # No hay tapador, y eso son DOS afirmaciones distintas que se confundian
        # en un solo caso, VIVA:
        #
        #  1) No existe NINGUNA otra escritura, de ninguna funcion, con la misma
        #     base y un rango que contenga este. Entonces si que esta libre:
        #     nadie lo pisa ni ahora ni luego. Eso es un resultado.
        #
        #  2) Si existe, pero en OTRA funcion, donde el orden textual no es el
        #     de ejecucion. Entonces no se puede decir que este libre: solo que
        #     no se ha comparado. Confundir 1 con 2 hacia que un TAPADA 0
        #     pareciese un resultado, cuando en polaris10_smumgr.c la copia de
        #     1776 B de :2118 esta en otra funcion que las escrituras de :142,
        #     :149, :157 y :166, y el orden de ejecucion es el contrario al
        #     textual.
        #
        # Un tapador posible de la MISMA funcion que aparece ANTES en el texto
        # no cuenta: si b contenia a y b va antes, entonces a se escribe
        # DESPUES y pisa a b. Es al reves, y a sigue libre de verdad.
        posibles = [b for b in escrituras
                    if b.ini is not None and b is not a
                    and a.base == b.base
                    and a.ini >= b.ini and a.fin <= b.fin]
        sin_ordenar = [b for b in posibles if a.funcion != b.funcion]
        if sin_ordenar:
            # Aqui hay una tapadora posible en otra funcion y el orden no se
            # conoce. Antes de declarar SIN_ORDEN se consulta la entrada
            # --orden, que es un hecho trazado a mano FUERA del fichero: el
            # orden de llamadas entre ficheros distintos no es una propiedad
            # del fuente, es un dato de una sesion, y por eso entra como
            # artefacto revisable y no como logica dentro del codigo.
            #
            # Los pares ya vienen VALIDADOS por valida_orden: contencion
            # comprobada, base comun, ambos con rango y en funciones distintas.
            # Aqui solo se comprueba que el tapador sea uno de los posibles, que
            # es una segunda comprobacion distinta: el par podria ser valido en
            # sus tres condiciones y aun asi no ser este tapador.
            kt = (orden or {}).get(a.linea)
            if kt is not None:
                cand = [b for b in sin_ordenar if b.linea == kt]
                if cand:
                    a.caso = CASE_OP
                    a.tapada_por = "%s:%d por --orden" % (
                        os.path.basename(cand[0].ruta), cand[0].linea)
                    continue
            a.caso = CASE_NO_ORDER
            a.nota += ("; SIN ORDEN: " + ", ".join(
                "%s:%d" % (os.path.basename(b.ruta), b.linea)
                for b in sorted(sin_ordenar, key=lambda x: x.linea)[:3]))
        else:
            a.caso = CASE_UNCOVERED
    return escrituras


# ---------------------------------------------------------------------------
# SELF-TEST
#
# El par que importa: dos escrituras que se diferencian SOLO en que la
# segunda la cubre o no. Si la herramienta no las separa, no esta mirando la
# contencion de rangos, que es justamente lo que se le pide.
# ---------------------------------------------------------------------------

# Caso A: la primera queda TAPADA. La segunda empieza antes y acaba despues.
FX_TAPADA = (
    "static int init_a(struct polaris10_smumgr *s)\n"
    "{\n"
    "\tuint32_t array = s->dpm_table_start + offsetof(T, GraphicsLevel);\n"
    "\tuint32_t array_size = sizeof(struct E) * OCHO;\n"
    "\tsmu7_copy_bytes_to_smc(hwmgr, array, (uint8_t *)&niveles,\n"
    "\t\t\t(uint32_t)array_size, SMC_RAM_END);\n"
    "\tresult = smu7_copy_bytes_to_smc(hwmgr,\n"
    "\t\t\ts->dpm_table_start + offsetof(T, SystemFlags),\n"
    "\t\t\t(uint8_t *)&tabla->SystemFlags, 1776, SMC_RAM_END);\n"
    "}\n"
)

# Caso B: misma forma, pero la segunda NO cubre a la primera.
FX_VIVA = (
    "static int init_b(struct polaris10_smumgr *s)\n"
    "{\n"
    "\tuint32_t array = s->dpm_table_start + offsetof(T, GraphicsLevel);\n"
    "\tuint32_t array_size = sizeof(struct E) * OCHO;\n"
    "\tsmu7_copy_bytes_to_smc(hwmgr, array, (uint8_t *)&niveles,\n"
    "\t\t\t(uint32_t)array_size, SMC_RAM_END);\n"
    "\tresult = smu7_copy_bytes_to_smc(hwmgr,\n"
    "\t\t\ts->dpm_table_start + offsetof(T, SystemFlags),\n"
    "\t\t\t(uint8_t *)&tabla->SystemFlags, 8, SMC_RAM_END);\n"
    "}\n"
)

# Caso C: cobertura PARCIAL. La segunda llega a solapar pero no a contener.
# Es el caso que un "solapan?" naively daria por bueno y no lo es: quedan
# bytes de la primera sin cubrir.
FX_PARCIAL = (
    "static int init_c(struct polaris10_smumgr *s)\n"
    "{\n"
    "\tuint32_t array = s->dpm_table_start + offsetof(T, MemoryLevel);\n"
    "\tuint32_t array_size = sizeof(struct T) * CUATRO;\n"
    "\tsmu7_copy_bytes_to_smc(hwmgr, array, (uint8_t *)&niveles,\n"
    "\t\t\t(uint32_t)array_size, SMC_RAM_END);\n"
    "\tresult = smu7_copy_bytes_to_smc(hwmgr,\n"
    "\t\t\ts->dpm_table_start + offsetof(T, GraphicsLevel),\n"
    "\t\t\t(uint8_t *)&tabla->GraphicsLevel, 448, SMC_RAM_END);\n"
    "}\n"
)



# ---------------------------------------------------------------------------
# MODO REGISTRO A REGISTRO
#
# Las escrituras que no pasan por smu7_copy_bytes_to_smc, sino por
# cgs_read_ind_register / cgs_write_ind_register. No son copias: son
# leer-modificar-escribir sobre un DWORD de la SRAM del SMC. La herramienta
# de copias no las ve, y son justo el caso en el que la investigacion se
# equivoco cuatro veces.
#
# La regla que este modo implementa, y que es la que hay que comprobar:
#
#   posicion_de_la_tabla = base + offsetof(campo)
#   offset_en_la_struct  = posicion_de_la_tabla - HUECO
#
# NO es + HUECO. Sumar donde hay que restar produce un numero plausible que
# senala otro campo, y cuatro hallazgos seguidos salieron mal por eso. El caso
# de self-test 14 existe precisamente para que un cambio de signo se vea.
# ---------------------------------------------------------------------------

VERSION_REG = "1.0.1"

RE_IND = re.compile(r"\bcgs_(read|write)_ind_register\s*\(")

# El hueco de la cabeza de la tabla: tres SMU74_PIDController que escribe el
# firmware y no el host. Es un PARAMETRO, no una constante escondida, porque
# depende del microcodigo y hay que poder cambiarlo para otro.
HUECO_CABECERA_DEFECTO = 108


class EscrituraReg(object):
    __slots__ = ("ruta", "funcion", "linea", "addr_txt", "pos_tabla",
                 "offset_struct", "campo_encontrado", "campo_pedido",
                 "byte_interno", "mascara", "coincide", "nota")

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))

    def a_texto(self):
        pos = self.pos_tabla if self.pos_tabla is not None else "?"
        est = self.offset_struct if self.offset_struct is not None else "?"
        hallazgo = self.campo_encontrado or "?"
        if self.coincide is True:
            marca = "coincide"
        elif self.coincide is False:
            marca = "DISTINTO de lo pedido"
        else:
            marca = "sin determinar"
        s = "  pos_tabla=%-6s struct=%-6s cae en %-28s pedido=%-18s %s" % (
            pos, est, hallazgo, self.campo_pedido or "-", marca)
        if self.byte_interno is not None:
            s += "  byte %d" % self.byte_interno
        if self.mascara:
            s += "  mascara " + self.mascara
        return s + ("  (" + self.nota + ")" if self.nota else "")


def invierte_offsets(offsets):
    """{offset: nombre}. Si dos campos comparten offset, el primero gana y se
    avisa por el llamador: un offset ambiguo no es un offset."""
    inv = {}
    for nombre, off in offsets.items():
        inv.setdefault(off, nombre)
    return inv


def campo_en_offset(inv, pos_struct):
    """(nombre, byte_interno) del campo que cubre pos_struct, o (None, None)."""
    if pos_struct is None:
        return None, None
    mejor = None
    for off in sorted(inv.keys(), reverse=True):
        if off <= pos_struct:
            mejor = off
            break
    if mejor is None:
        return None, None
    # el tamano del campo se deduce del siguiente offset, porque los offsets
    # medidos de gcc son de todo lo que se pregunto
    return inv[mejor], pos_struct - mejor


def analiza_registros(ruta, src, offsets, pares_func, nombres_func,
                      ctx_vars, hueco, constantes=None):
    """Localiza las escrituras registro a registro y dice que campo tocan.

    pares_func y nombres_func son opcionales: si no vienen, se usan los que
    produce la propia segmentacion del fichero. Antes se usaba el parametro,
    que desde main() llega en None, y enumerate(None) hacia que el bucle de
    la funcion no se ejecutara nunca y la herramienta devolviera cero
    escrituras sin decir por que.
    """
    if src is not None:
        limpio, stmts, pares, nombres = segmenta_lineas(src.split("\n"))
    else:
        try:
            texto = io.open(ruta, encoding="utf-8", errors="replace").read()
        except (IOError, OSError):
            return []
        limpio, stmts, pares, nombres = segmenta_lineas(texto.split("\n"))
    constantes = constantes or {}
    if pares_func is None:
        pares_func = pares
    if nombres_func is None:
        nombres_func = nombres

    inv = invierte_offsets(offsets)
    # Las direcciones de las escrituras registro a registro NO suelen estar
    # en el argumento de la llamada: suelen ser una VARIABLE LOCAL calculada
    # unas lineas antes. Sin seguir esas asignaciones la herramienta no ve
    # nada, que es un cero silencioso.
    #
    # Se resuelven dos formas:
    #   offset = base + offsetof(T, c)        directa
    #   offset = base + offsetof(T, c) + N    con compensacion
    for a, b in stmts:
        frag = limpio[a:b]
        m = RE_LOCAL_ADDR.match(frag)
        if m:
            nombre, expr = m.group(1), m.group(2)
            off, _r, base = resuelve_destino(expr, offsets, ctx_vars, None)
            if off is not None:
                cola = expr[expr.rfind(")") + 1:] if ")" in expr else ""
                msum = re.search(r"([+-])\s*(\d+)\s*$", cola)
                if msum:
                    off += int(msum.group(2)) * (1 if msum.group(1) == "+" else -1)
            ctx_vars[nombre] = (off, base)

    # mascaras: para cada lectura, guardamos la mascara que se aplica luego
    masks = {}
    res = []
    for a, b in stmts:
        frag = limpio[a:b]
        mc = RE_IND.search(frag)
        if not mc:
            continue
        op = mc.group(1)
        j = mc.end() - 1
        prof, k = 0, j
        while k < len(frag):
            if frag[k] == "(":
                prof += 1
            elif frag[k] == ")":
                prof -= 1
                if prof == 0:
                    break
            k += 1
        args = split_args(frag[j + 1:k])
        if len(args) < 3:
            continue
        registro = " ".join(args[1].split())
        addr = " ".join(args[2].split())
        # solo la SRAM del SMC: los registros MMIO directos no tienen tabla
        if "CGS_IND_REG__SMC" not in registro:
            continue

        func = "?"
        for idx, (fi, ff) in enumerate(pares):
            if fi < a < ff:
                func = nombres[idx] if idx < len(nombres) else "?"
                break

        # el destino puede ser una variable local ya resuelta
        pos, base_nombre, pedido = None, "", None
        if addr in ctx_vars and ctx_vars[addr] and ctx_vars[addr][0] is not None:
            pos = ctx_vars[addr][0]
            base_nombre = ctx_vars[addr][1]
        elif "offsetof(" in addr:
            campos = RE_OFFSETOF.findall(addr)
            if campos:
                pedido = campos[-1][1]
                off, _r, base_nombre = resuelve_destino(addr, offsets, ctx_vars, None)
                pos = off
                # la expresion puede llevar un desplazamiento mas: "base +
                # offsetof(T, c) + 108". Es la forma CORRECTA de compensar el
                # hueco, y es justo la que el codigo real NO usa. Si no se
                # tiene en cuenta el caso de la direccion bien calculada
                # daria el mismo resultado que el de la mal calculada.
                cola = addr[addr.rfind(")") + 1:] if ")" in addr else ""
                msum = re.search(r"([+-])\s*(\d+)\s*$", cola)
                if msum and pos is not None:
                    pos += int(msum.group(2)) * (1 if msum.group(1) == "+" else -1)
        if pos is None:
            continue
        if base_nombre != "TABLA_DPM":
            # es una direccion de otra tabla, no de la tabla DPM: no aplica la
            # regla del hueco, y decirlo es mejor que suponer
            res.append(EscrituraReg(
                ruta=ruta, funcion=func, linea=linea_de(limpio, a),
                addr_txt=addr, pos_tabla=None, offset_struct=None,
                campo_encontrado=None, campo_pedido=pedido,
                byte_interno=None, mascara=None, coincide=None,
                nota="direccion de otra tabla: " + str(base_nombre)))
            continue

        # La direccion de un DWORD se alinea a 4. El codigo lo hace
        # explicitamente con "/= 4; *= 4", y el codigo REAL depende de eso:
        # con offsetof 1577 la posicion sin alinear es 1577, y alineada es 1576.
        # Sin esta linea la herramienta daria un byte de mas y un campo
        # distinto, que es justo el error que se quiere evitar.
        alineado = pos - (pos % 4)
        if alineado != pos:
            pos = alineado
        off_struct = pos - hueco
        campo, byte_int = campo_en_offset(inv, off_struct)
        # quitar la clave calificada "(struct T, campo)" para que se lea
        if campo and campo.startswith("("):
            campo = campo.split(", ")[-1].rstrip(")")
        coincide = None
        if pedido is not None and campo is not None:
            coincide = (campo.split("[")[0] == pedido)
        res.append(EscrituraReg(
            ruta=ruta, funcion=func, linea=linea_de(limpio, a),
            addr_txt=addr, pos_tabla=pos, offset_struct=off_struct,
            campo_encontrado=campo, campo_pedido=pedido,
            byte_interno=byte_int, mascara=None, coincide=coincide,
            nota=""))
    return res


def selftest():
    fallos = []
    # Contador REAL de comprobaciones ejecutadas. Un literal fijo se queda viejo
    # en silencio en cuanto anades un vector, y un self-test que dice "34
    # vectores" ejecutando 40 miente con la misma seguridad que cualquier otro
    # numero plausible sin verificar.
    cuenta_chk = [0]

    def chk(c, m):
        cuenta_chk[0] += 1
        if not c:
            fallos.append(m)

    off = {"GraphicsLevel": 236, "MemoryLevel": 708, "SystemFlags": 108}
    sizes = {"E": 56}         # el elemento, como en el codigo real
    cont = {}                # el multiplicador viene de un #define, no de la linea
    constantes = {"OCHO": 8, "CUATRO": 4}   # leidos de la cabecera

    # caso A: debe decir TAPADA
    a = decide(analiza_fichero("A.c", FX_TAPADA, off, sizes, cont, constantes))[0]
    chk(a.caso == CASE_OP,
        "casoA: se esperaba TAPADA, se obtuvo %s (%s)" % (a.caso, a.nota))

    # caso B: debe decir VIVA. Este es el par que se confirma con el A.
    b = decide(analiza_fichero("B.c", FX_VIVA, off, sizes, cont, constantes))[0]
    chk(b.caso == CASE_UNCOVERED,
        "casoB: se esperaba VIVA, se obtuvo %s (%s)" % (b.caso, b.nota))
    chk(not b.tapada_por, "casoB: no deberia tener tapadora: %s" % b.tapada_por)

    # caso C: cobertura parcial NO es cobertura
    sizes_c = dict(sizes)
    sizes_c["T"] = 24          # el elemento, como en el codigo real
    c = decide(analiza_fichero("C.c", FX_PARCIAL, off, sizes_c, cont, constantes))[0]
    chk(c.caso == CASE_UNCOVERED,
        "casoC: una cobertura parcial no puede ser TAPADA: %s (%s)" % (c.caso, c.nota))

    # caso D: tamano no resoluble -> NO_RESUELTO, jamas 0
    src_d = ("static int f(struct polaris10_smumgr *s)\n{\n"
           "\tsmu7_copy_bytes_to_smc(hwmgr, s->dpm_table_start + offsetof(T, X),\n"
           "\t\t\t(uint8_t *)&algo, sizeof(struct NoMedida), SMC_RAM_END);\n}\n")
    d = decide(analiza_fichero("D.c", src_d, {"X": 10}, sizes, cont))
    chk(d and d[0].caso == CASE_UNRESOLVED,
        "casoD: un sizeof sin medir debe ser NO_RESUELTO, no 0 ni VIVA")
    if d:
        chk(d[0].tam is None, "casoD: el tamano debe quedar en None")

    # caso E: offsetof de un campo sin valor literal -> NO_RESUELTO
    src_e = ("static int g(void)\n{\n"
             "\tsmu7_copy_bytes_to_smc(hw, dpm_table_start + offsetof(T, Campo),\n"
             "\t\t\t(uint8_t *)&z, 16, END);\n}\n")
    e = decide(analiza_fichero("E.c", src_e, {"OtroCampo": 5}, sizes, cont))
    chk(e and e[0].caso == CASE_UNRESOLVED,
        "casoE: un campo sin offset conocido no puede resolverse a 0")

    # caso F: entrada vacia y entrada malformada
    chk(analiza_fichero("F.c", "static int f(void)\n{\n}\n", off, sizes, cont) == [],
        "casoF: funcion sin copias debe devolver lista vacia")
    try:
        r = analiza_fichero("G.c", "static int roto(void)\n{\n\tsmu7_copy_bytes_to_smc(hw, dpm_", off, sizes, cont)
        chk(isinstance(r, list), "casoG: debe devolver lista")
    except Exception as ex:
        fallos.append("casoG: lanzo %r" % ex)

    # caso H: reproducibilidad
    r1 = decide(analiza_fichero("A.c", FX_TAPADA, off, sizes, cont, constantes))
    r2 = decide(analiza_fichero("A.c", FX_TAPADA, off, sizes, cont, constantes))
    chk([(x.linea, x.caso) for x in r1] == [(x.linea, x.caso) for x in r2],
        "casoH: dos ejecuciones difieren")

    # caso I: la LINEA de una llamada multilinea, contra un LITERAL.
    #
    # Este caso es el que faltaba y por eso el defecto de :2115 sobrevivio a
    # 18 vectores. El caso H usa `x.linea`, pero solo la compara contra si misma
    # en dos ejecuciones: comprueba determinismo, no verdad de terreno. Aqui se
    # afirma el numero exacto.
    #
    # La forma del fixture reproduce la de polaris10_smumgr.c: una sentencia
    # CONVERT_ terminada en ';' ANTES de la llamada, una linea en blanco, un
    # comentario, y luego la llamada repartida en varias lineas. El ';' de la
    # sentencia anterior era el ancla que se reportaba.
    src_i = ("static int h(struct smu7_hwmgr *hwmgr)\n"          # linea 1
             "{\n"                                                 # linea 2
             "\tCONVERT_FROM_HOST_TO_SMC_US(table->Phase);\n"     # linea 3
             "\n"                                                  # linea 4
             "\t/* un comentario entre medias */\n"                # linea 5
             "\tresult = smu7_copy_bytes_to_smc(hwmgr,\n"         # linea 6
             "\t\t\tdpm_table_start,\n"                             # linea 7
             "\t\t\t(uint8_t *)&algo, 4, END);\n}\n")               # linea 8
    i = decide(analiza_fichero("I.c", src_i, off, sizes, cont))
    chk(len(i) == 1, "casoI: se esperaba 1 escritura, se obtuvieron %d" % len(i))
    if len(i) == 1:
        chk(i[0].linea == 6,
            "casoI: la llamada esta en la linea 6, la herramienta dijo %d. "
            "Anclar al ';' de la linea 3 es el defecto que se corrigio." % i[0].linea)

    # caso I2: el mismo fixture, pero la llamada es la PRIMERA sentencia de la
    # funcion. Sin este caso, un arreglo que solo funcionara con una sentencia
    # previa pasaria el caso I y seguiria siendo incorrecto en general.
    src_i2 = ("static int i2(struct smu7_hwmgr *hwmgr)\n"        # linea 1
              "{\n"                                                # linea 2
              "\tresult = smu7_copy_bytes_to_smc(hwmgr,\n"          # linea 3
              "\t\t\tdpm_table_start,\n"                            # linea 4
              "\t\t\t(uint8_t *)&algo, 4, END);\n}\n")              # linea 5
    i2 = decide(analiza_fichero("I2.c", src_i2, off, sizes, cont))
    chk(len(i2) == 1, "casoI2: se esperaba 1 escritura, se obtuvieron %d" % len(i2))
    if len(i2) == 1:
        chk(i2[0].linea == 3,
            "casoI2: la llamada esta en la linea 3, la herramienta dijo %d" % i2[0].linea)

    # caso I3: dos llamadas en la misma funcion, cada una en su linea. Un
    #_fragmento_ puede contener mas de una llamada si la segmentacion falla, y
    # sin esto el ancla solo se comprobaria con una llamada por funcion.
    src_i3 = ("static int i3(struct smu7_hwmgr *hwmgr)\n"
              "{\n"
              "\tresult = smu7_copy_bytes_to_smc(hwmgr,\n"          # linea 3
              "\t\t\tdpm_table_start,\n"
              "\t\t\t(uint8_t *)&a, 4, END);\n"
              "\tresult = smu7_copy_bytes_to_smc(hwmgr,\n"          # linea 6
              "\t\t\tdpm_table_start,\n"
              "\t\t\t(uint8_t *)&b, 4, END);\n}\n")
    i3 = decide(analiza_fichero("I3.c", src_i3, off, sizes, cont))
    chk(sorted(x.linea for x in i3) == [3, 6],
        "casoI3: se esperaban las lineas 3 y 6, se obtuvieron %r"
        % sorted(x.linea for x in i3))

    # caso L: un MISMO nombre con VARIAS asignaciones en la misma funcion, y un
    # uso entre cada par.
    #
    # Reproduce graphics_level_address en polaris10_smumgr.c, que apunta a
    # GraphicsLevel, MemoryLevel y BootMVdd en la misma funcion. Con el mapa por
    # nombre la ULTIMA asignacion se llevaba por delante las tres escrituras, y
    # como el rango salia con la magnitud correcta parecia un acierto: la
    # herramienta devolvia 30,30,30 en vez de 10,20,30, y ningun vector lo
    # detectaba.
    src_l = ("static int multi(void)\n"                      # 1
             "{\n"                                           # 2
             "\tuint32_t base = 0;\n"                        # 3
             "\tuint32_t direccion;\n"                       # 4
             "\tdireccion = base + offsetof(T, A);\n"        # 5
             "\tsmu7_copy_bytes_to_smc(hw, direccion, (uint8_t *)&x, 4, END);\n"  # 6
             "\tdireccion = base + offsetof(T, B);\n"        # 7
             "\tsmu7_copy_bytes_to_smc(hw, direccion, (uint8_t *)&y, 4, END);\n"  # 8
             "\tdireccion = base + offsetof(T, C);\n"        # 9
             "\tsmu7_copy_bytes_to_smc(hw, direccion, (uint8_t *)&z, 4, END);\n"  # 10
             "\treturn 0;\n}\n")
    l = decide(analiza_fichero("L.c", src_l, {"A": 10, "B": 20, "C": 30},
                               sizes, cont))
    chk(len(l) == 3, "casoL: se esperaban 3 escrituras, se obtuvieron %d" % len(l))
    if len(l) == 3:
        chk([e.ini for e in l] == [10, 20, 30],
            "casoL: se esperaban los inicios 10,20,30 y se obtuvieron %r "
            "(multi-asignacion resuelta por el ultimo, no por el punto de uso)"
            % [e.ini for e in l])

    # caso M: un --contador de la linea de ordenes NO puede perderse por el
    # shadow del mapa local de contadores.
    #
    # El defecto: :739 creaba la clave "__contadores__" para toda funcion con
    # cualquier sentencia reconocida, aun vacia, y :813 hacia
    # ctx_amb.get("__contadores__", contadores). Como la clave existia siempre,
    # el .get con valor por defecto nunca llegaba a mirar el global. Aqui la
    # funcion tiene un contador local propio (array_size) y aun asi usa un
    # contador que solo viene de la linea de ordenes (lote).
    src_m = ("static int sombra(void)\n"                    # 1
             "{\n"                                          # 2
             "\tuint32_t array_size = sizeof(E) * 4;\n"     # 3
             "\tsmu7_copy_bytes_to_smc(hw, base + offsetof(T, SystemFlags),\n"  # 4
             "\t\t\t(uint8_t *)&x, lote, END);\n"           # 5
             "\treturn 0;\n}\n")
    m = decide(analiza_fichero("M.c", src_m, {"SystemFlags": 108},
                               {"E": 56}, {"lote": 7}))
    chk(len(m) == 1, "casoM: se esperaba 1 escritura, se obtuvieron %d" % len(m))
    if len(m) == 1:
        chk(m[0].tam == 7,
            "casoM: el --contador global lote=7 se perdio (tam=%r, nota=%r); "
            "el mapa local de contadores hizo de sombra al global"
            % (m[0].tam, m[0].nota))

    # caso N: un `x = sizeof(T)` a secas es un contador local, y su valor esta
    # en el fichero.
    #
    # El defecto: el patron de contadores locales exigia "sizeof(T) * CONST", y
    # esta forma no casa. Al caer a RE_LOCAL_ADDR, resuelve_destino devuelve None
    # porque un sizeof no es un offset, y el valor se perdia. Lo unico que se
    # reportaba era "sin argumento de tamano", cuando el argumento esta escrito.
    # Reproduce graphics_level_size en polaris10_smumgr.c:128.
    src_n = ("static int seco(void)\n"                       # 1
             "{\n"                                          # 2
             "\tuint32_t graphics_level_size;\n"            # 3
             "\tgraphics_level_size = sizeof(E);\n"         # 4
             "\tsmu7_copy_bytes_to_smc(hw, base + offsetof(T, SystemFlags),\n"  # 5
             "\t\t\t(uint8_t *)&x, graphics_level_size, END);\n"  # 6
             "\treturn 0;\n}\n")
    n = decide(analiza_fichero("N.c", src_n, {"SystemFlags": 108}, {"E": 56}, {}))
    chk(len(n) == 1, "casoN: se esperaba 1 escritura, se obtuvieron %d" % len(n))
    if len(n) == 1:
        chk(n[0].tam == 56,
            "casoN: graphics_level_size = sizeof(E) debia dar 56 sin ayuda "
            "externa, dio tam=%r (nota=%r)" % (n[0].tam, n[0].nota))

    # caso O: una escritura cuyo unico tapador posible esta en OTRA funcion.
    #
    # El defecto: decide()ponia VIVA tanto cuando nadie contiene el rango como
    # cuando si hay alguien pero en otra funcion, donde el orden textual no es el
    # de ejecucion. Las dos son afirmaciones distintas y solo la primera es un
    # resultado. CASE_NO_ORDER existia como constante y se filtraba del resumen,
    # pero no la asignaba nadie: el vocablo estaba en el codigo sin el
    # comportamiento.
    #
    # Reproduce polaris10_smumgr.c: la escritura de GraphicsLevel en
    # polaris10_setup_graphics_level_structure (:149) y la copia de 1776 B en
    # polaris10_init_smc_table (:2118). El orden de ejecucion es el contrario al
    # textual, y es justo lo que 263 demostro.
    fx_orden = (
        "static int previa(struct polaris10_smumgr *s)\n"
        "{\n"
        "\tuint32_t array = s->dpm_table_start + offsetof(T, GraphicsLevel);\n"
        "\tsmu7_copy_bytes_to_smc(hwmgr, array, (uint8_t *)&niveles, 448, SMC_RAM_END);\n"
        "}\n"
        "static int init_smc(struct polaris10_smumgr *s)\n"
        "{\n"
        "\tsmu7_copy_bytes_to_smc(hwmgr,\n"
        "\t\t\ts->dpm_table_start + offsetof(T, SystemFlags),\n"
        "\t\t\t(uint8_t *)&tabla, 1776, SMC_RAM_END);\n"
        "}\n")
    o = decide(analiza_fichero("O.c", fx_orden, off, sizes, cont, constantes))
    chk(len(o) == 2, "casoO: se esperaban 2 escrituras, se obtuvieron %d" % len(o))
    if len(o) == 2:
        chk(o[0].caso == CASE_NO_ORDER,
            "casoO: la escritura cuyo tapador esta en otra funcion debe ser %s, "
            "no %s: sin el orden de ejecucion no se puede decir que este libre"
            % (CASE_NO_ORDER, o[0].caso))
        chk(o[1].caso == CASE_UNCOVERED,
            "casoO: la copia grande no la contiene nadie: %s" % o[1].caso)

    # caso P: una escritura que NADIE contiene, ni en su funcion ni en otra.
    # Si esto sale SIN_ORDEN, el caso O pasa por casualidad y el Distinguir es
    # mentira.
    fx_libre = (
        "static int suelta(struct polaris10_smumgr *s)\n"
        "{\n"
        "\tsmu7_copy_bytes_to_smc(hwmgr,\n"
        "\t\t\ts->dpm_table_start + offsetof(T, GraphicsLevel),\n"
        "\t\t\t(uint8_t *)&niveles, 448, SMC_RAM_END);\n"
        "}\n")
    p = decide(analiza_fichero("P.c", fx_libre, off, sizes, cont, constantes))
    chk(len(p) == 1, "casoP: se esperaba 1 escritura, se obtuvieron %d" % len(p))
    if len(p) == 1:
        chk(p[0].caso == CASE_UNCOVERED,
            "casoP: nadie contiene ese rango, luego esta libre de verdad y es %s, "
            "no %s" % (CASE_UNCOVERED, p[0].caso))

    # caso Q: un tapador posible de la MISMA funcion que aparece ANTES en el
    # texto. Si b contenia a y b va antes, entonces a se escribe DESPUES y pisa a
    # b: es al reves. a queda libre de verdad, y no SIN_ORDEN.
    #
    # Sin este vector, el Distinguir del caso O tambien pasaria si se hubiera
    # escrito "hay ALGO que lo contiene" sin mirar de donde.
    fx_reves = (
        "static int reves(struct polaris10_smumgr *s)\n"
        "{\n"
        "\tsmu7_copy_bytes_to_smc(hwmgr,\n"
        "\t\t\ts->dpm_table_start + offsetof(T, SystemFlags),\n"
        "\t\t\t(uint8_t *)&tabla, 1776, SMC_RAM_END);\n"
        "\tuint32_t array = s->dpm_table_start + offsetof(T, GraphicsLevel);\n"
        "\tsmu7_copy_bytes_to_smc(hwmgr, array, (uint8_t *)&niveles, 448, SMC_RAM_END);\n"
        "}\n")
    q = decide(analiza_fichero("Q.c", fx_reves, off, sizes, cont, constantes))
    chk(len(q) == 2, "casoQ: se esperaban 2 escrituras, se obtuvieron %d" % len(q))
    if len(q) == 2:
        chk(q[0].caso == CASE_UNCOVERED and q[1].caso == CASE_UNCOVERED,
            "casoQ: la segunda escritura pisa a la primera, no la tapa: se esperaba "
            "%s %s y se obtuvo %s %s"
            % (CASE_UNCOVERED, CASE_UNCOVERED, q[0].caso, q[1].caso))

    # ------------------------------------------------------------------
    # El TEXTO del resumen y de los avisos.
    #
    # Este bloque existo porque 283, 286 y 289 dejaron dicho tres veces que el
    # resumen y el aviso NO tienen vector, y que por eso el PASS del selftest
    # no significaba lo que parecia. Cerrado en 290.
    #
    # El texto NO es decoracion: una cifra sin etiqueta que diga que mide se lee
    # como un resultado, y un "TAPADA 0" se leia como cobertura nula cuando solo
    # decia que no se habian comparado escrituras de funciones distintas.
    # ------------------------------------------------------------------

    # caso V: cada cifra del resumen va CON su etiqueta, y las etiquetas dicen
    # algo distinto entre si. Un "0" a secas no se puede distinguir de otro "0".
    sel_v = decide(analiza_fichero("O.c", fx_orden, off, sizes, cont, constantes))
    lin_v = lineas_de_resumen(sel_v, {}, {}, "")
    txt_v = "\n".join(lin_v)
    for etiqueta, marca in (
        (CASE_OP, "la escritura posterior contiene su rango completo"),
        (CASE_UNCOVERED, "nadie la contiene: esta libre de verdad"),
        (CASE_NO_ORDER, "otra funcion contiene su rango"),
        (CASE_UNRESOLVED, "sin rango: no se puede afirmar cobertura"),
    ):
        chk(marca in txt_v,
            "casoV: el resumen no explica que mide %s; falta %r" % (etiqueta, marca))
    chk(CASE_RUNTIME not in txt_v or "la asigna el firmware en runtime" in txt_v,
        "casoV: si aparece %s el resumen debe decir que la direccion la asigna "
        "el firmware en runtime" % CASE_RUNTIME)
    chk(not re.search(r"%[-+ #0-9.]*[a-z]", txt_v),
        "casoV: se ha escapado un especificador de formato al resumen: %r"
        % [l for l in lin_v if re.search(r"%[-+ #0-9.]*[a-z]", l)])

    # caso W: sin --orden-motivo, el resumen lo AVISA; con motivo, lo imprime.
    # El orden de llamadas entre ficheros no es una propiedad del fuente: es un
    # dato de una sesion. Sin su justificacion, la cifra no es auditable.
    base_w = analiza_fichero("O.c", fx_orden, off, sizes, cont, constantes)
    par_w = {min(e.linea for e in base_w): max(e.linea for e in base_w)}
    ok_w, malos_w = valida_orden(base_w, par_w)
    chk(ok_w and not malos_w,
        "casoW: el par de prueba deberia ser valido, se rechazo: %r" % (malos_w,))
    sel_w = decide(analiza_fichero("O.c", fx_orden, off, sizes, cont, constantes),
                   ok_w)
    txt_sin = "\n".join(lineas_de_resumen(sel_w, {}, {}, ""))
    chk("1 vienen de --orden" in txt_sin,
        "casoW: con un TAPADA por --orden, el resumen debe decir cuantos vienen "
        "de --orden: %r" % txt_sin[-240:])
    chk("SIN --orden-motivo" in txt_sin,
        "casoW: usando --orden SIN motivo, el resumen debe avisar de que la cifra "
        "no es auditable: %r" % txt_sin[-240:])
    chk("traza 287" not in txt_sin,
        "casoW: sin motivo no se debe imprimir ninguno")
    txt_con = "\n".join(lineas_de_resumen(sel_w, {}, {}, "traza 287"))
    chk("motivo: traza 287" in txt_con,
        "casoW: con motivo, el resumen debe imprimirlo: %r" % txt_con[-240:])
    chk("SIN --orden-motivo" not in txt_con,
        "casoW: con motivo no debe aparecer el aviso")

    # caso X: una entrada pasada y NO consultada se avisa por su nombre. El
    # fixture E usa sizeof(E), asi que un sizeof de otro nombre es un huerfano,
    # y el aviso tiene que nombrarlo: es la diferencia entre "el fichero no lo
    # dice" y "tu entrada esta mal".
    med = Medido({"E": 56, "SMU74_Discrete_FanTable": 36})
    _ = med.get("E")                     # se consulta el que existe
    huerfanos = med.sin_usar()
    chk(huerfanos == ["SMU74_Discrete_FanTable"],
        "casoX: sin_usar() deberia devolver solo la clave no consultada, "
        "devolvio %r" % (huerfanos,))
    txt_x = "\n".join(lineas_de_resumen(sel_v, med, {}, ""))
    chk("1 --sizeof sin usar: SMU74_Discrete_FanTable" in txt_x,
        "casoX: el aviso deberia nombrar la entrada no usada: %r" % txt_x[-260:])
    chk("es una entrada ignorada" in txt_x,
        "casoX: el aviso deberia decir que NO_RESUELTO puede venir de una entrada "
        "ignorada, no de un limite del fichero")

    # ------------------------------------------------------------------
    # --orden: una entrada que tiene que poder FALLAR
    #
    # Tres de los cuatro vectores de este bloque son RECHAZOS, y esa es la parte
    # que importa. Un --orden que solo sabe decir "si" no es un dato: es una
    # forma de fabricar TAPADA, y con ella se podria convertir cualquier
    # SIN_ORDEN en cobertura sin mover un byte de evidencia. Lo que lo hace
    # entrada y no brújula es que la CONTENCION se comprueba siempre.
    # ------------------------------------------------------------------

    # caso R: par valido. Sin --orden, la escritura queda SIN_ORDEN; con el par
    # validado, queda TAPADA nombrando al tapador.
    base_o = analiza_fichero("O.c", fx_orden, off, sizes, cont, constantes)
    ln_a = min(e.linea for e in base_o)
    ln_b = max(e.linea for e in base_o)
    ok_r, malos_r = valida_orden(base_o, {ln_a: ln_b})
    chk(not malos_r,
        "casoR: un par valido no deberia rechazarse, se rechazo: %r" % (malos_r,))
    chk(ok_r == {ln_a: ln_b},
        "casoR: esperado {%d: %d} y se obtuvo %r" % (ln_a, ln_b, ok_r))
    rr = decide(analiza_fichero("O.c", fx_orden, off, sizes, cont, constantes), ok_r)
    chk(rr[0].caso == CASE_OP and "por --orden" in rr[0].tapada_por,
        "casoR: con el par valido debe quedar TAPADA por --orden, quedo %s (%s)"
        % (rr[0].caso, rr[0].tapada_por))

    # caso S: contencion FALSA. En fx_reves la primera escritura ocupa
    # 108..1883 y la segunda 236..683. Declarar que la primera la tapa la
    # segunda es falso: 108..1883 no cabe en 236..683. Un orden declarado no
    # puede crear contencion que no existe.
    base_s = analiza_fichero("Q.c", fx_reves, off, sizes, cont, constantes)
    ln_s1, ln_s2 = sorted(e.linea for e in base_s)
    ok_s, malos_s = valida_orden(base_s, {ln_s1: ln_s2})
    chk(not ok_s and len(malos_s) == 1,
        "casoS: una contencion falsa debe rechazarse, se acepto %r" % (ok_s,))
    chk(malos_s and "contencion falsa" in malos_s[0][2],
        "casoS: el motivo deberia ser contencion falsa, fue %r"
        % (malos_s[0][2] if malos_s else None,))

    # caso T: linea inexistente. Es un nombre mal escrito, no un hecho.
    ok_t, malos_t = valida_orden(base_o, {ln_a: 9999})
    chk(not ok_t and len(malos_t) == 1,
        "casoT: una linea inexistente debe rechazarse, se acepto %r" % (ok_t,))
    chk(malos_t and "no existe la escritura" in malos_t[0][2],
        "casoT: el motivo deberia ser que la escritura no existe, fue %r"
        % (malos_t[0][2] if malos_t else None,))

    # caso U: bases distintas. Con o sin orden son dos regiones distintas; el
    # orden no las convierte en la misma.
    #
    # El segundo destino usa la FORMA REAL del fichero, smu_data->smu7_data.X.
    # La version corta, s->arb_table_start, NO la reconoce la herramienta: la
    # forma C exige un punto en la expresion. En polaris10_smumgr.c eso no
    # importa porque las dos entradas de :1511 y :2254 llevan la estructura
    # intermedia, pero es un hueco real y queda anotado en el hallazgo, no
    # remediado a Quiet aqui: es una frontera propia y esta es otra.
    fx_bases = (
        "static int dos(struct polaris10_smumgr *s)\n"
        "{\n"
        "\tstruct smu7_smumgr *smu_data = s;\n"
        "\tsmu7_copy_bytes_to_smc(hwmgr,\n"
        "\t\t\ts->dpm_table_start + offsetof(T, GraphicsLevel),\n"
        "\t\t\t(uint8_t *)&niveles, 448, SMC_RAM_END);\n"
        "\tsmu7_copy_bytes_to_smc(hwmgr, smu_data->smu7_data.arb_table_start,\n"
        "\t\t\t(uint8_t *)&arb, 384, SMC_RAM_END);\n"
        "}\n")
    base_u = analiza_fichero("U.c", fx_bases, off, sizes, cont, constantes)
    ln_u1, ln_u2 = sorted(e.linea for e in base_u)
    ok_u, malos_u = valida_orden(base_u, {ln_u1: ln_u2})
    chk(not ok_u and len(malos_u) == 1,
        "casoU: bases distintas deben rechazarse, se acepto %r" % (ok_u,))
    chk(malos_u and "bases distintas" in malos_u[0][2],
        "casoU: el motivo deberia ser bases distintas, fue %r"
        % (malos_u[0][2] if malos_u else None,))

    # caso J: la aritmetica que decide el hallazgo de la tabla DPM.
    # sizeof(DpmTable) - 3*sizeof(PIDController) tiene que dar 1776. Si la
    # herramienta devolviera solo el primer sizeof daria 1884, que es un
    # numero plausible y 108 mayor, y ese 108 es exactamente el hueco.
    val, nota = resuelve_tamano(
        "sizeof(SMU74_Discrete_DpmTable) - 3 * sizeof(SMU74_PIDController)",
        {"SMU74_Discrete_DpmTable": 1884, "SMU74_PIDController": 36}, {})
    chk(val == 1776,
        "casoJ: la resta de sizeof dio %r, se esperaba 1776 (%s)" % (val, nota))

    # caso K: si falta uno de los dos sizeof, NO se devuelve la parte que si
    # se sabe. Devolver 1884 a medias seria el fallo clasico.
    val2, nota2 = resuelve_tamano(
        "sizeof(SMU74_Discrete_DpmTable) - 3 * sizeof(SMU74_PIDController)",
        {"SMU74_Discrete_DpmTable": 1884}, {})
    chk(val2 is None,
        "casoK: con un sizeof sin medir no se debe devolver un numero: %r" % val2)

    # caso L: el cast (uint32_t)sizeof(v) de la copia de la tabla de
    # ventilacion. Sin esto se quedaba NO_RESUELTO en el fichero real.
    val3, nota3 = resuelve_tamano("(uint32_t)sizeof(fan_table)",
                                 {"fan_table": 36}, {})
    chk(val3 == 36, "casoL: el cast delante del sizeof dio %r (%s)" % (val3, nota3))

    # caso M: DOS BASES DISTINTAS que se solaparian por error. Este es el
    # fallo que corrigio a mano el hallazgo 104: comparar un offset dentro de
    # la tabla DPM contra una direccion de otra tabla. Sin la regla de base,
    # la escritura de la tabla de arbitraje taparia a la de VRConfig y el
    # informe daria un "queda tapada" falso.
    off2 = {"VRConfig": 112, "SystemFlags": 108}
    src_m = (
        "static int k(struct polaris10_smumgr *s)\n"
        "{\n"
        "\tuint32_t va = s->dpm_table_start + offsetof(T, VRConfig);\n"
        "\tsmu7_copy_bytes_to_smc(hw, va, (uint8_t *)&x, 4, END);\n"
        "\tsmu7_copy_bytes_to_smc(hw, s->arb_table_start, (uint8_t *)&y,\n"
        "\t\t\t384, END);\n"
        "}\n"
    )
    ms = decide(analiza_fichero("M.c", src_m, off2, {}, {}))
    if ms:
        chk(ms[0].base == "TABLA_DPM",
            "casoM: la primera escritura deberia llevar base TABLA_DPM: %r" % ms[0].base)
        chk(ms[1].base != "TABLA_DPM",
            "casoM: la escritura de otra tabla deberia llevar OTRA base: %r" % ms[1].base)
        chk(ms[0].caso == CASE_UNCOVERED,
            "casoM: una base distinta no puede taparla, dio %s" % ms[0].caso)
        chk(not ms[0].tapada_por,
            "casoM: se le atribuyo una tapadora de otra tabla: %s" % ms[0].tapada_por)
    else:
        fallos.append("casoM: no se detectaron escrituras")

    # caso 14: EL PAR QUE CONFIRMA EL SIGNO DEL HUECO.
    #
    # Dos escrituras al mismo campo, una con la direccion que el codigo usa y otra
    # con la que haria falta para acertar. Si la herramienta sumara el hueco en vez
    # de restarlo, las dos darian el mismo campo y este caso fallaria.
    #
    #   escribe en 1576 (= offsetof del campo) -> cae en 1576-108 = 1468 -> Smio
    #   escribe en 1792 (= offsetof + 108)      -> cae en 1792-108 = 1684 -> BootVddc
    off14 = {"UvdBootLevel": 1576, "Smio": 1448, "BootVddc": 1684,
             "(struct T, UvdBootLevel)": 1576,
             "(struct T, BootVddc)": 1684}
    src14 = (
        "static int p(struct pp_hwmgr *hwmgr)\n"
        "{\n"
        "\tcgs_write_ind_register(hwmgr->device, CGS_IND_REG__SMC,\n"
        "\t\t\tsmu_data->smu7_data.dpm_table_start\n"
        "\t\t\t\t+ offsetof(T, UvdBootLevel), 0);\n"
        "}\n"
    )
    r14 = analiza_registros("N.c", src14, off14, [(0, 1 << 20)], ["p"], {},
                           HUECO_CABECERA_DEFECTO)
    if not r14:
        fallos.append("caso14: no se detecto la escritura registro a registro")
    else:
        e = r14[0]
        chk(e.pos_tabla == 1576,
            "caso14: la posicion en la tabla dio %r, se esperaba 1576" % e.pos_tabla)
        chk(e.offset_struct == 1468,
            "caso14: el offset en la struct dio %r, se esperaba 1468 (= 1576 - 108). "
            "Si esto falla, el hueco se esta SUMando en vez de restarse." % e.offset_struct)
        chk(e.campo_encontrado and e.campo_encontrado.startswith("Smio"),
            "caso14: el campo encontrado fue %r, se esperaba Smio" % e.campo_encontrado)
        chk(e.coincide is False,
            "caso14: deberia marcarse como DISTINTO de lo pedido, dio %r" % e.coincide)

    # caso 15: la direccion que SI apunta al campo pedido
    src15 = src14.replace("offsetof(T, UvdBootLevel)",
                          "offsetof(T, BootVddc) + 108")
    r15 = analiza_registros("O.c", src15, off14, [(0, 1 << 20)], ["p"], {},
                           HUECO_CABECERA_DEFECTO)
    if not r15:
        fallos.append("caso15: no se detecto la escritura")
    else:
        e = r15[0]
        chk(e.offset_struct == 1684,
            "caso15: el offset dio %r, se esperaba 1684" % e.offset_struct)
        chk(e.campo_encontrado == "BootVddc",
            "caso15: el campo fue %r, se esperaba BootVddc" % e.campo_encontrado)
        chk(e.coincide is True,
            "caso15: deberia marcarse como coincidente, dio %r" % e.coincide)

    # caso 16: si el hueco cambia, la resolucion cambia. Con hueco 0 la
    # escritura en 1576 cae en UvdBootLevel, y con 108 cae en Smio. Eso
    # demuestra que el hueco es un parametro de verdad y no una constante fija.
    r16 = analiza_registros("P.c", src14, off14, [(0, 1 << 20)], ["p"], {}, 0)
    if r16:
        chk(r16[0].offset_struct == 1576,
            "caso16: con hueco 0 el offset deberia ser 1576, dio %r" % r16[0].offset_struct)
        chk(r16[0].coincide is True,
            "caso16: con hueco 0 deberia coincidir, dio %r" % r16[0].coincide)

    # caso 17: la ALINEACION a 4 cambia el resultado, y el codigo real
    # depende de ella. Con offsetof 1577 la posicion sin alinear da struct 1469
    # y alineada da 1468: un byte de mas y un campo distinto. El codigo hace
    # "/= 4; *= 4" explicito, y la herramienta tiene que imitarlo.
    src17 = (
        "static int q(struct pp_hwmgr *hwmgr)\n"
        "{\n"
        "\tmm_boot_level_offset = smu_data->smu7_data.dpm_table_start"
        " + offsetof(T, VceBootLevel);\n"
        "\tmm_boot_level_offset /= 4;\n"
        "\tmm_boot_level_offset *= 4;\n"
        "\tcgs_write_ind_register(hwmgr->device, CGS_IND_REG__SMC,\n"
        "\t\t\tmm_boot_level_offset, valor);\n"
        "}\n"
    )
    off17 = {"(struct T, VceBootLevel)": 1577, "(struct T, Smio)": 1448}
    r17 = analiza_registros("R.c", src17, off17, None, None, {},
                           HUECO_CABECERA_DEFECTO)
    if not r17:
        fallos.append("caso17: no se detecto la escritura")
    else:
        chk(r17[0].pos_tabla == 1576,
            "caso17: con offsetof 1577 la posicion debe quedar alineada a 1576, "
            "dio %r" % r17[0].pos_tabla)
        chk(r17[0].offset_struct == 1468,
            "caso17: el offset dio %r, se esperaba 1468 (= 1576 - 108)" % r17[0].offset_struct)
        chk(r17[0].campo_encontrado == "Smio",
            "caso17: el campo fue %r, se esperaba Smio" % r17[0].campo_encontrado)

    # caso 18: AMBITO DE VARIABLE. Dos funciones definen la MISMA variable con
    # offsets distintos, que es exactamente lo que hace el codigo real:
    # `array` esta en populate_all_graphic_levels (GraphicsLevel) y en
    # populate_all_memory_levels (MemoryLevel). Resolverla una sola vez hacia
    # que la segunda herede el offset de la primera, y la herramienta daria un
    # rango equivocado con plena confianza.
    src18 = (
        "static int g(struct polaris10_smumgr *s)\n"
        "{\n"
        "\tuint32_t array = s->dpm_table_start + offsetof(T, GraphicsLevel);\n"
        "\tuint32_t n = 448;\n"
        "\treturn smu7_copy_bytes_to_smc(hw, array, (uint8_t *)&n, 448, END);\n"
        "}\n"
        "static int m(struct polaris10_smumgr *s)\n"
        "{\n"
        "\tuint32_t array = s->dpm_table_start + offsetof(T, MemoryLevel);\n"
        "\tuint32_t n = 96;\n"
        "\treturn smu7_copy_bytes_to_smc(hw, array, (uint8_t *)&n, 96, END);\n"
        "}\n"
    )
    off18 = {"GraphicsLevel": 236, "MemoryLevel": 708}
    r18 = decide(analiza_fichero("S.c", src18, off18, {}, {}))
    if len(r18) != 2:
        fallos.append("caso18: se esperaban 2 escrituras, se obtuvieron %d" % len(r18))
    else:
        chk(r18[0].ini == 236,
            "caso18: la primera deberia estar en 236 (GraphicsLevel), dio %r" % r18[0].ini)
        chk(r18[1].ini == 708,
            "caso18: la segunda deberia estar en 708 (MemoryLevel), dio %r. "
            "Si esto falla, la variable de una funcion se esta reutilizando en la otra." % r18[1].ini)
        chk(r18[0].funcion != r18[1].funcion,
            "caso18: las dos funciones salen con el mismo nombre: %r" % r18[0].funcion)


    # --- caso19: dos contadores CON EL MISMO NOMBRE y distinto valor ----------
    # Es el caso real de polaris10_smumgr.c: array_size vale 448 en una funcion y
    # 96 en otra. Indexado por nombre plano habria que elegir uno, y elegir mal
    # produce un rango con la magnitud correcta y el valor equivocado: un numero
    # plausible y falso, que es peor que un cero.
    src19 = (
        "static void f1(struct x *h)\n{\n"
        "\tuint32_t array_size = 448;\n"
        "\tsmu7_copy_bytes_to_smc(h, dpm_table_start + offsetof(T, GraphicsLevel),\n"
        "\t\t\t&x, (uint32_t)array_size, SMC_RAM_END);\n}\n"
        "static void f2(struct x *h)\n{\n"
        "\tuint32_t array_size = 96;\n"
        "\tsmu7_copy_bytes_to_smc(h, dpm_table_start + offsetof(T, MemoryLevel),\n"
        "\t\t\t&x, (uint32_t)array_size, SMC_RAM_END);\n}\n")
    off19 = {"GraphicsLevel": 236, "MemoryLevel": 708}
    r19 = decide(analiza_fichero("T.c", src19, off19, {},
                                 {"array_size": 448}, None,
                                 {"array_size": [(96, 9)]}))
    if len(r19) != 2:
        fallos.append("caso19: se esperaban 2 escrituras, se obtuvieron %d" % len(r19))
    else:
        chk(r19[0].tam == 448,
            "caso19: la primera deberia medir 448, dio %r: el contador de la "
            "linea posterior esta pisando al de su uso" % r19[0].tam)
        chk(r19[1].tam == 96,
            "caso19: la segunda deberia medir 96, dio %r: el contador de la "
            "linea anterior reaching la de su uso" % r19[1].tam)

    r19b = decide(analiza_fichero("T2.c", src19, off19, {}, None,
                                  {"array_size": [(7, 99)]}))
    chk(any(e.caso == CASE_UNRESOLVED for e in r19b),
        "caso19b: un contador declarado solo para lineas posteriores a su uso "
        "debe quedar NO_RESUELTO, no resolverse con un valor equivocado")

    # --- caso20: destino asignado por el firmware en RUNTIME -----------------
    # smu7_read_smc_sram_dword(..., &tmp, SMC_RAM_END): la direccion la dice el
    # SMC cuando corre. No es un fallo del instrumento, y es un estado propio.
    src20 = (
        "static void g(struct x *h)\n{\n"
        "\tuint32_t tmp;\n"
        "\tsmu7_read_smc_sram_dword(h, 0x1234, &tmp, SMC_RAM_END);\n"
        "\tsmu7_copy_bytes_to_smc(h, tmp, &mean, sizeof(mean), SMC_RAM_END);\n}\n")
    r20 = decide(analiza_fichero("U2.c", src20, {"mean": 10}, {}, {}))
    if len(r20) != 1:
        fallos.append("caso20: se esperaba 1 escritura, se obtuvieron %d" % len(r20))
    else:
        chk(r20[0].caso == CASE_RUNTIME,
            "caso20: deberia ser %s, dio %s" % (CASE_RUNTIME, r20[0].caso))
        chk("firmware" in r20[0].nota,
            "caso20: la nota debe decir que la direccion la asigna el firmware")

    src20b = (
        "static void g(struct x *h)\n{\n"
        "\tuint32_t tmp;\n"
        "\ttmp = smu7_read_smc_sram_dword(h, 0x1234, SMC_RAM_END);\n"
        "\tsmu7_copy_bytes_to_smc(h, tmp, &mean, sizeof(mean), SMC_RAM_END);\n}\n")
    r20b = decide(analiza_fichero("U3.c", src20b, {"mean": 10}, {}, {}))
    chk(r20b and r20b[0].caso != CASE_RUNTIME,
        "caso20b: una lectura sin puntero de salida no debe dar %s" % CASE_RUNTIME)

    # caso I: el fuente no puede contener CJK
    src_i = io.open(__file__, encoding="utf-8").read()
    cjk = [c for c in src_i if 0x3000 <= ord(c) <= 0x9FFF or 0xF900 <= ord(c) <= 0xFAFF]
    chk(not cjk, "casoI: el fuente contiene CJK: %r" % cjk[:4])

    VECTORES_EJECUTADOS[0] = cuenta_chk[0]
    if fallos:
        for f in fallos:
            sys.stderr.write("  SELFTEST FALLO: %s\n" % f)
        return False
    return True


VECTORES_EJECUTADOS = [0]
# Suelo, no cifra: si alguien quita un vector sin querer, el recuento
# baja y esto lo dice en vez de dejar pasar un self-test mas corto.
CASOS_SELFTEST_MINIMO = 40


def lineas_de_resumen(sel, sizes, contadores, orden_motivo=""):
    """Devuelve las lineas del RESUMEN. Puro: no imprime, no lee argumentos.

    Esta funcion existe por una razon concreta: el selftest comprobar que el
    TEXTO que ve quien lee es el correcto. Con el resumen escrito dentro de
    main() no se podia comprobar sin arrancar el programa entero, y eso dejo el
    texto y los avisos sin vector durante tres versiones, con el selftest
    diciendo PASS.

    El texto NO es decoracion. Una cifra sin etiqueta que diga que mide se lee
    como un resultado, y un "TAPADA 0" se leia como cobertura nula cuando en
    realidad solo decia que no se habian comparado las escrituras de funciones
    distintas. El texto es parte del contrato.
    """
    def cuenta(c):
        return len([e for e in sel if e.caso == c])

    L = ["  RESUMEN",
         "    Dentro de una MISMA funcion el orden textual ES el de ejecucion:",
         "      %-13s %3d  la escritura posterior contiene su rango completo"
         % (CASE_OP, cuenta(CASE_OP)),
         "      %-13s %3d  nadie la contiene: esta libre de verdad"
         % (CASE_UNCOVERED, cuenta(CASE_UNCOVERED))]
    if cuenta(CASE_NO_ORDER):
        L.append("    %-13s %3d  otra funcion contiene su rango, pero entre funciones"
                 % (CASE_NO_ORDER, cuenta(CASE_NO_ORDER)))
        L.append("    %-13s      el orden textual no es el de ejecucion: "
                 "NI VIVA NI TAPADA" % "")
    L.append("    %-13s %3d  sin rango: no se puede afirmar cobertura"
             % (CASE_UNRESOLVED, cuenta(CASE_UNRESOLVED)))
    if cuenta(CASE_RUNTIME):
        L.append("    %-13s %3d  la direccion la asigna el firmware en runtime:"
                 % (CASE_RUNTIME, cuenta(CASE_RUNTIME)))
        L.append("    %-13s      no esta en el codigo, asi que no cabe afirmar "
                 "cobertura" % "")

    # De donde sale la cifra. Un TAPADA por orden textual y uno por --orden tienen
    # el mismo codigo detras, asi que sin esta linea no serian distinguibles.
    n_orden = len([e for e in sel
                   if e.caso == CASE_OP and "por --orden" in e.tapada_por])
    if n_orden:
        L.append("    %-13s %3d  de los TAPADA, %d vienen de --orden, no del orden "
                 "textual" % ("", n_orden, n_orden))
        if orden_motivo:
            L.append("                    motivo: %s" % orden_motivo)
        else:
            L.append("                    AVISO: se ha usado --orden SIN "
                     "--orden-motivo; el numero no es auditable")

    # Una entrada pasada y no consultada no es una entrada neutro: es un nombre
    # mal escrito o una medida que esta herramienta no sabe usar. Las dos son
    # corregibles, y las dos se pierden en silencio si no se dicen.
    for etiqueta, d in (("--sizeof", sizes), ("--contador", contadores)):
        huerfanos = d.sin_usar() if hasattr(d, "sin_usar") else []
        if huerfanos:
            L.append("  AVISO: %d %s sin usar: %s"
                     % (len(huerfanos), etiqueta, ", ".join(huerfanos)))
            L.append("          si un nombre esta mal escrito, el NO_RESUELTO que "
                     "produce no es")
            L.append("          limite del fichero: es una entrada ignorada.")
    return L


def main(argv):
    ap = argparse.ArgumentParser(
        description="Diga que escrituras en la SRAM del SMC quedan tapadas "
                    "por una copia posterior.")
    ap.add_argument("rutas", nargs="*")
    ap.add_argument("--offsets-from", action="append", default=[],
                    help="fichero de donde leer los valores de offsetof")
    ap.add_argument("--gcc-kernel", default="",
                    help="raiz del kernel para pedir offsets a gccverify")
    ap.add_argument("--gcc-struct", action="append", default=[],
                    help="struct de la que pedir offsets a gccverify, con el "
                         "prefijo 'struct '. Repetible: hay tablas distintas "
                         "(la DPM y la de SoftRegisters, por ejemplo)")
    ap.add_argument("--gcc-header", default="",
                    help="nombre de la cabecera que usa gccverify")
    ap.add_argument("--sizeof", action="append", default=[],
                    metavar="TIPO=N", help="tamano medido de un tipo")
    ap.add_argument("--contador", action="append", default=[],
                    metavar="NOMBRE=N", help="valor de un contador conocido")
    ap.add_argument("--orden", action="append", default=[],
                    metavar="ESCRITURA=TAPADOR",
                    help="orden de ejecucion trazado a mano entre escrituras de "
                         "distintas funciones: la ESCRITURA se ejecuta ANTES que "
                         "el TAPADOR y el TAPADOR la cubre. Solo se acepta si el "
                         "tapador contiene su rango entero y ambos comparten base; "
                         "si no, se rechaza y se dice por que")
    ap.add_argument("--orden-motivo", default="",
                    help="por que se sabe ese orden. Se imprime junto al resumen: "
                         "el orden es un dato de una sesion, no una propiedad del "
                         "fichero, y sin su justificacion el numero no es auditable")
    ap.add_argument("--registro", action="store_true",
                    help="modo registro a registro: dice que campo toca cada "
                         "escritura cgs_write_ind_register en la SRAM del SMC")
    ap.add_argument("--lectura-defines", action="append", default=[],
                    metavar="RUTA",
                    help="cabecera o directorio de donde leer los #define con "
                         "valor entero, para resolver multiplicadores de array")
    ap.add_argument("--hueco", type=int, default=HUECO_CABECERA_DEFECTO,
                    help="bytes de cabeza de la tabla que escribe el firmware "
                         "(por defecto %d)" % HUECO_CABECERA_DEFECTO)
    ap.add_argument("--solo-distintos", action="store_true",
                    help="en modo registro, solo las que NO caen en el campo pedido")
    ap.add_argument("--solo-vivas", action="store_true",
                    help="muestra solo las que NO quedan tapadas")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    args = ap.parse_args(argv)

    if args.version:
        sys.stdout.write("smc_copy_scope %s\n" % VERSION)
        return 0

    if args.selftest:
        ok = selftest()
        sys.stdout.write("  smc_copy_scope %s · RESULTADO %s · %d vectores "
                         "conocidos reproducidos\n" % (
                             VERSION, "OK" if ok else "FALLO",
                             VECTORES_EJECUTADOS[0] if ok else 0))
        if ok and VECTORES_EJECUTADOS[0] < CASOS_SELFTEST_MINIMO:
            sys.stderr.write("  aviso: solo %d comprobaciones ejecutadas y el suelo "
                             "es %d\n" % (VECTORES_EJECUTADOS[0],
                                          CASOS_SELFTEST_MINIMO))
            return 3
        return 0 if ok else 3

    if not args.rutas:
        sys.stderr.write("smc_copy_scope: hace falta una ruta o --selftest\n")
        return 2

    offsets = {}
    for f in args.offsets_from:
        try:
            src = io.open(f, encoding="utf-8", errors="replace").read()
        except (IOError, OSError) as e:
            sys.stderr.write("  aviso: %s\n" % e)
            continue
        offsets.update(lineas_de_offsetof(src))

    # Pedir los offsets a gcc cuando se puede. gcc es la verdad de terreno:
    # el layout del host calculado por reglas de ABI puede coincidir con lo
    # que el compilador dice y aun asi no ser el que el firmware usa. Si no
    # se pide a gcc y no hay fichero de offsets, la herramienta declara
    # NO_RESUELTO en vez de suponer, que es lo correcto pero menos util.
    if args.gcc_kernel and args.gcc_struct:
        total = 0
        for st in args.gcc_struct:
            encontrados = pedir_offsets_a_gcc(args.gcc_kernel, st,
                                              args.gcc_header)
            if not encontrados:
                sys.stderr.write("  aviso: gccverify no devolvio offsets de %s; "
                                 "las escrituras con ese offsetof quedaran "
                                 "NO_RESUELTO\n" % st)
                continue
            total += len(encontrados)
            for k, v in encontrados.items():
                # con clave "(STRUCT, campo)" para no mezclar tablas
                offsets.setdefault("(" + st + ", " + k + ")", v)
        if total:
            sys.stderr.write("  %d offsets medidos por gcc\n" % total)

    sizes = Medido()
    for kv in args.sizeof:
        if "=" in kv:
            k, v = kv.split("=", 1)
            try:
                sizes[k.strip()] = int(v)
            except ValueError:
                sys.stderr.write("  aviso: --sizeof %s no es un numero\n" % kv)
    contadores = Medido()
    contadores_linea = Medido()
    for kv in args.contador:
        if "=" not in kv:
            continue
        k, v = kv.split("=", 1)
        k = k.strip()
        try:
            val = int(v)
        except ValueError:
            sys.stderr.write("  aviso: --contador %s no es un numero\n" % kv)
            continue
        # NOMBRE@LINEA: solo vale para esa linea, y es lo que permite declarar
        # los dos array_size distintos que tiene polaris10_smumgr.c
        if "@" in k:
            nombre, _, ln = k.partition("@")
            try:
                ln = int(ln)
            except ValueError:
                sys.stderr.write("  aviso: --contador %s tiene una linea no numerica\n" % kv)
                continue
            contadores_linea.setdefault(nombre.strip(), []).append((val, ln))
        else:
            contadores[k] = val

    constantes = {}
    for r in args.lectura_defines or []:
        if os.path.isdir(r):
            for raiz, _d, fs in os.walk(r):
                for f in sorted(fs):
                    if f.endswith(".h"):
                        constantes.update(recoge_constantes_int(
                            [os.path.join(raiz, f)]))
        elif os.path.isfile(r):
            constantes.update(recoge_constantes_int([r]))

    ficheros = []
    for r in args.rutas:
        if os.path.isdir(r):
            for raiz, _d, fs in os.walk(r):
                for f in sorted(fs):
                    if f.endswith(".c"):
                        ficheros.append(os.path.join(raiz, f))
        elif os.path.isfile(r):
            ficheros.append(r)
    if not ficheros:
        sys.stderr.write("  no se encontro ningun .c\n")
        return 2

    todas = []
    for f in ficheros:
        todas.extend(analiza_fichero(f, None, offsets, sizes, contadores,
                                     constantes, contadores_linea))
    todas.sort(key=lambda x: (x.ruta, x.linea))

    # El orden entra validado o no entra. Un par que no cumple las tres
    # condiciones se RECHAZA y se dice por que, y no se aplica: si se aplicara en
    # silencio, un nombre mal escrito produciria un TAPADA inventado que nadie
    # podria distinguir de uno rightly deduced.
    orden = {}
    pedidos = []
    for kv in args.orden or []:
        if "=" not in kv:
            sys.stderr.write("  aviso: --orden %s no tiene el formato "
                             "ESCRITURA=TAPADOR\n" % kv)
            continue
        ks, kt = kv.split("=", 1)
        try:
            pedidos.append((int(ks.strip()), int(kt.strip())))
        except ValueError:
            sys.stderr.write("  aviso: --orden %s no son dos numeros\n" % kv)
    if pedidos:
        orden, malos = valida_orden(todas, dict(pedidos))
        for ks, kt, mot in malos:
            sys.stdout.write("  AVISO: --orden %d=%d RECHAZADO: %s\n"
                             % (ks, kt, mot))
        if not orden:
            sys.stdout.write("  AVISO: ningun par de --orden se acepto; el "
                             "reparto es el de siempre\n")

    decide(todas, orden)

    sys.stdout.write("smc_copy_scope %s · %d ficheros · %d escrituras · "
                     "%d offsets · %d tamanos medidos\n"
                     % (VERSION, len(ficheros), len(todas),
                        len(offsets), len(sizes)))

    if args.registro:
        regs = []
        for f in ficheros:
            regs.extend(analiza_registros(f, None, offsets, None, None,
                                          {}, args.hueco, constantes))
        regs.sort(key=lambda x: (x.ruta, x.linea))
        sys.stdout.write("\n  MODO REGISTRO A REGISTRO · hueco de cabecera = %d B\n"
                         % args.hueco)
        sys.stdout.write("  posicion en la tabla = base + offsetof(campo);\n")
        sys.stdout.write("  offset en la struct = posicion - hueco\n")
        mostrados = regs
        if args.solo_distintos:
            mostrados = [r for r in regs if r.coincide is False]
        for r in mostrados:
            sys.stdout.write("  %s:%d\n%s\n" % (os.path.basename(r.ruta), r.linea,
                                                    r.a_texto()))
        distintos = [r for r in regs if r.coincide is False]
        sys.stdout.write("  RESUMEN: %d escrituras registro a registro, "
                         "%d caen en un campo DISTINTO del pedido, "
                         "%d sin determinar\n"
                         % (len(regs), len(distintos),
                            len([r for r in regs if r.coincide is None])))
        return 0

    sel = list(todas)
    if args.solo_vivas:
        sel = [e for e in sel if e.caso != CASE_OP]
    for e in sel:
        sys.stdout.write(e.a_texto() + "\n")
    for l in lineas_de_resumen(sel, sizes, contadores, args.orden_motivo):
        sys.stdout.write(l + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

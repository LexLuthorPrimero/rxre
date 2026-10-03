#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
uninit_copy 1.0.0
================

Clase de defecto que busca, en codigo C de driver:

    un agregado de pila declarado SIN inicializador, y despues pasado a una
    funcion de copia con un tamano de sizeof() del tipo COMPLETO.

Es decir: se copia mas de lo que se escribio. El resto va a la SRAM del SMC, al
registro o a donde sea, con el contenido residual de la pila.

El caso de referencia es `polaris10_smumgr.c:1494` (tabla de arbitraje DRAM de
Polaris12): `arb_regs` sin inicializar, 384 bytes copiados siempre, y el bucle
solo escribe `sclk_count * mclk_count * 12`.

Por que hace falta una herramienta y no leer:
  - la comprobacion es la MISMA en todos los ficheros de una ruta;
  - el caso bueno (legacy SI, que si inicializa) tiene que salir limpio, o la
    herramienta no distingue nada;
  - la mayoria de las llamadas de copia se hacen con un `sizeof(...)` literal,
    y un grep ingenuo que solo buscase "sizeof(" daria el mismo resultado para
    una copia a tamano completo y para una copia a tamano calculado. Eso es el
    fallo de "una clave derivada de una magnitud no identifica a la entrada".

Salida: una linea por hallazgo, con clase y confianza. Exit code:
    0  ninguna coincidencia
    1  al menos una coincancia
    2  error de invocacion o de lectura
    3  self-test fallido

WORK_CLASS=READ_ONLY. No escribe nada en el arbol que analiza.
"""

import argparse
import io
import os
import re
import sys

VERSION = "1.0.0"

# Numero de bloques de caso del self-test. Se cuenta a mano y se contrasta con
# el recuento de "    # --- caso" del propio fuente: si se anaden bloques hay
# que tocar aqui, y el caso 9 no pasa si sobran CJK en el fuente.
CASOS_SELFTEST = 13

# ---------------------------------------------------------------------------
# Sin CJK en el codigo. Si aparece, la herramienta no es portable.
# ---------------------------------------------------------------------------

CLASES = {
    "FULL_SIZE_COPY": "agregado sin inicializar, copiado a sizeof() del tipo completo",
    "COMPUTED_SIZE": "agregado sin inicializar, pero el tamano de copia se calcula",
    "TYPE_MISMATCH": "la copia usa sizeof() de un tipo distinto al de la variable",
    "TYPEDEF_CANDIDATE": "lo mismo, pero el tipo llega por typedef sin confirmar",
    "UNREPORTED_NOCOPY": "agregado sin inicializar y sin llamada de copia visible",
    "INITIALIZED": "agregado con inicializador o con memset en la misma funcion",
}


class Hallazgo(object):
    __slots__ = ("ruta", "funcion", "linea_decl", "linea_copia", "variable",
                 "tipo", "tamano", "clase", "nota")

    def __init__(self, ruta, funcion, linea_decl, linea_copia, variable, tipo,
                 tamano, clase, nota):
        self.ruta = ruta
        self.funcion = funcion
        self.linea_decl = linea_decl
        self.linea_copia = linea_copia
        self.variable = variable
        self.tipo = tipo
        self.tamano = tamano
        self.clase = clase
        self.nota = nota

    def clave(self):
        return (self.ruta, self.funcion, self.variable, self.clase)

    def a_texto(self):
        d = "%s:%d" % (self.ruta, self.linea_decl)
        if self.linea_copia:
            d += " -> copia en %d" % self.linea_copia
        return "  %-10s %s  %s %s  tam=%-28s  %s" % (
            self.clase, d, self.tipo, self.variable, self.tamano,
            CLASES.get(self.clase, "?"))


# ---------------------------------------------------------------------------
# Analisis lexico de C: quitamos comentarios y cadenas para no tomar texto que
# no es codigo. Un comentario con "struct X y;" produce un falso positivo si no
# se limpia.
# ---------------------------------------------------------------------------

def limpia_comentarios_y_cadenas(texto):
    """Devuelve el texto con comentarios y cadenas sustituidos por espacios,
    conservando saltos de linea y columnas."""
    out = []
    i = 0
    n = len(texto)
    estado = "code"
    while i < n:
        c = texto[i]
        d = texto[i + 1] if i + 1 < n else ""
        if estado == "code":
            if c == "/" and d == "*":
                out.append("  ")
                i += 2
                estado = "bloque"
                continue
            if c == "/" and d == "/":
                out.append("  ")
                i += 2
                while i < n and texto[i] != "\n":
                    out.append(" ")
                    i += 1
                continue
            if c == '"':
                out.append(" ")
                i += 1
                estado = "cadena"
                continue
            if c == "'":
                out.append(" ")
                i += 1
                estado = "caracter"
                continue
            out.append(c)
            i += 1
        elif estado == "bloque":
            if c == "*" and d == "/":
                out.append("  ")
                i += 2
                estado = "code"
                continue
            out.append("\n" if c == "\n" else " ")
            i += 1
        elif estado == "cadena":
            if c == "\\":
                out.append("  ")
                i += 2
                continue
            if c == '"':
                out.append(" ")
                i += 1
                estado = "code"
                continue
            out.append("\n" if c == "\n" else " ")
            i += 1
        else:
            if c == "\\":
                out.append("  ")
                i += 2
                continue
            if c == "'":
                out.append(" ")
                i += 1
                estado = "code"
                continue
            out.append("\n" if c == "\n" else " ")
            i += 1
    return "".join(out)


# ---------------------------------------------------------------------------
# Troceado en funciones por profundidad de llaves, en el texto ya limpio.
# ---------------------------------------------------------------------------

RE_FUNC = re.compile(
    r"^([A-Za-z_][A-Za-z0-9_ \t\*]*?)"
    r"([A-Za-z_][A-Za-z0-9_]*)\s*\([^;{]*\)\s*\{", re.M)


RE_DECL_AGG = re.compile(
    r"^(?:struct|union)\s+([A-Za-z_][A-Za-z0-9_]*)\s+([A-Za-z_][A-Za-z0-9_]*)\s*(\[([^\]]*)\])?\s*;"
    r"(?!\s*=)")

RE_DECL_TIPADO = re.compile(
    r"^([A-Za-z_][A-Za-z0-9_]*)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\[([^\]]*)\]\s*;"
    r"(?!\s*=)")

# Declaracion por nombre de typedef, sin la palabra "struct". El codigo
# legacy usa esta forma (SMC_SIslands_... arb_regs;) y el de Polaris usa la
# otra (struct SMU74_... arb_regs;). Una herramienta que solovio la primera
# se perderia la mitad de los casos, y no por que no existan: por que se
# busca mal. El mismo nombre mal buscado produce un cero que no es ausencia.
RE_DECL_TYPEDEF = re.compile(
    r"^(?!(?:const|static|extern|return|typedef)\b)"
    r"([A-Za-z_][A-Za-z0-9_]*)\s+([A-Za-z_][A-Za-z0-9_]*)\s*;"
    r"(?!\s*=)")


def trocea_funciones(texto, ruta):
    """Devuelve [(nombre, inicio, fin, linea_inicio, linea_fin)]."""
    lineas = texto.split("\n")
    # indice de OffsetDeLinea: prefijo acumulado
    offs = []
    acc = 0
    for l in lineas:
        offs.append(acc)
        acc += len(l) + 1

    def linea_de(pos):
        lo, hi = 0, len(offs) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if offs[mid] <= pos:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1

    funcs = []
    for m in RE_FUNC.finditer(texto):
        ini = m.end() - 1          # la llave de apertura
        prof = 0
        j = ini
        while j < len(texto):
            if texto[j] == "{":
                prof += 1
            elif texto[j] == "}":
                prof -= 1
                if prof == 0:
                    break
            j += 1
        fin = j if j < len(texto) else len(texto)
        # El cuerpo empieza en la LLAVE, que no esta necesariamente en la misma
        # linea que la firma. Si la firma se parte en dos lineas, el primer
        # elemento de cuerpo.split("\n") es el resto de la linea de la llave,
        # no de la firma. Contar desde la linea de la firma desplaza todos los
        # numeros de linea en uno, y eso no se ve en un self-test con fixtures
        # de una sola linea: hace falta un fixture con la firma partida.
        funcs.append((m.group(2), ini, fin, linea_de(ini), linea_de(fin)))
    return funcs


# ---------------------------------------------------------------------------
# Llamadas de copia: identificamos la llamada y que se le pasa a la variable.
# No buscamos solo "sizeof(": una llamada con sizeof() puede ser una copia
# segura a tamano calculado.
# ---------------------------------------------------------------------------

RE_LLAMADA = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*\(")

RE_CAST = re.compile(r"\(\s*(?:const\s+|unsigned\s+|signed\s+)*"
                     r"[A-Za-z_][A-Za-z0-9_]*\s*\*+\s*\)")

# Tipos que nunca son un agregado con huecos. Sin esta lista, "int x;" o
# "uint32_t y;" saldrian como candidatos y la herramienta no distinguiria
# un agregado de un escalar, que es justo el error que se quiere evitar.
ESCALARES = set("""
char short int long float double signed unsigned void size_t ssize_t ptrdiff_t
uint8_t uint16_t uint32_t uint64_t int8_t int16_t int32_t int64_t
u8 u16 u32 u64 s8 s16 s32 s64 bool _Bool __u8 __s16 __u32
FIX86_64_FLAGS PHM_GET_REG_MASK
""".split())


def sin_casts(txt):
    """Quita los casts de puntero, para poder comparar un argumento."""
    previo = None
    actual = txt
    while previo != actual:
        previo = actual
        actual = RE_CAST.sub(" ", actual)
    return actual


def llamadas_con_variable(cuerpo, var):
    """Devuelve [(offset, linea_rel, nombre_funcion, argumento_tamano)] para
    las llamadas cuyo primer argumento es &var o var."""
    res = []
    for m in RE_LLAMADA.finditer(cuerpo):
        nombre = m.group(1)
        if nombre in ("if", "for", "while", "switch", "return", "sizeof"):
            continue
        # emparejar parentesis
        j = m.end() - 1
        prof = 0
        k = j
        while k < len(cuerpo):
            if cuerpo[k] == "(":
                prof += 1
            elif cuerpo[k] == ")":
                prof -= 1
                if prof == 0:
                    break
            k += 1
        if k >= len(cuerpo):
            continue
        args = cuerpo[j + 1:k]
        partes = args.split(",")
        # La variable puede estar en CUALQUIER posicion, no solo la primera.
        # En el codigo real de Polaris la llamada es
        #   smu7_copy_bytes_to_smc(hwmgr, destino, (uint8_t *)&arb_regs,
        #                           sizeof(TIPO), SMC_RAM_END);
        # o sea que la variable es el TERCER argumento y viene con un cast
        # delante. Una herramienta que solo mirase el primer argumento, o que
        # comparase sin quitar casts, devolveria cero sin distinguir "no hay
        # caso" de "no se ha mirado bien". Ese cero es el fallo clasico.
        pos = None
        for idx, a in enumerate(partes):
            if sin_casts(a).strip() in ("&" + var, var):
                pos = idx
                break
        if pos is None:
            continue
        # el tamano de copia es el primer argumento DESPUES de la variable que
        # contenga un sizeof o un entero
        tam = ""
        for a in partes[pos + 1:]:
            s = a.strip()
            if "sizeof" in s or re.match(r"^\d+$", s) or re.match(
                    r"^\(\s*(?:int|uint32_t|unsigned|long)\s*\)", s):
                tam = s
                break
        res.append((m.start(), m.group(0), nombre, tam, pos))
    return res


def arg_tamano_es_completo(args, tipo):
    """Clasifica el argumento de tamano de una llamada de copia.

    COMPLETO  : sizeof(TIPO) y nada mas  -> se copia el tipo entero
    CALCULADO : sizeof(...) * algo, o sizeof(...) + algo, o un entero -> parcial

    Distinguir esto es el punto de la herramienta: sin esta distincion, el
    camino legacy (seguro) y el de Polaris12 (defectuoso) darian el mismo
    resultado, y una herramienta que no distingue un caso malo de un caso
    bueno no prueba nada.
    """
    a = " ".join(args.split())
    if not a:
        return "SIN_TAMANO", None
    sm = re.match(r"^sizeof\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)$", a)
    if sm:
        if tipo and sm.group(1) != tipo:
            return "TYPE_MISMATCH", sm.group(1)
        return "COMPLETO", sm.group(1)
    sm2 = re.match(r"^sizeof\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)\s*([*+\-].*)$", a)
    if sm2:
        if tipo and sm2.group(1) != tipo:
            return "TYPE_MISMATCH", sm2.group(1)
        return "CALCULADO", sm2.group(1)
    sm3 = re.match(r"^\(\s*(?:int|uint32_t|unsigned|long)\s*\)\s*sizeof", a)
    if sm3:
        return "CALCULADO", None
    if re.match(r"^\d+$", a):
        return "CALCULADO", None
    return "OTRO", None


def inicializado_en_funcion(cuerpo, var):
    """Hay un = ... , una asignacion a un miembro, o un memset(&var)."""
    if re.search(r"\b%s\s*\[[^\]]*\]\s*=\s*" % re.escape(var), cuerpo):
        return True
    if re.search(r"\b%s\s*=\s*" % re.escape(var), cuerpo):
        return True
    # asignar un miembro cuenta como haber escrito algo dentro
    if re.search(r"\b%s\s*\.\s*[A-Za-z_][A-Za-z0-9_]*\s*=[^=]" % re.escape(var), cuerpo):
        return True
    if re.search(r"\bmemset\s*\(\s*&?\s*%s\b" % re.escape(var), cuerpo):
        return True
    return False


def analiza_fichero(ruta, texto=None, solo_declaradas=False, structs=None):
    """Devuelve la lista de Hallazgo de un fichero.

    structs: conjunto de nombres conocidos que son struct/union. Sirve para
    promover una declaracion por typedef a agregado con confianza. Si es None,
    las declaraciones por typedef se marcan como candidatas, no como
    hallazgos, y no se mezclan con las confirmadas.
    """
    if texto is None:
        with io.open(ruta, "r", encoding="utf-8", errors="replace") as fh:
            texto = fh.read()
    limpio = limpia_comentarios_y_cadenas(texto)
    funcs = trocea_funciones(limpio, ruta)
    base = os.path.basename(ruta)
    salida = []

    for nombre, ini, fin, l_ini, l_fin in funcs:
        cuerpo = limpio[ini:fin]
        for ln, cruda in enumerate(cuerpo.split("\n"), l_ini):
            s = cruda.strip()
            m = RE_DECL_AGG.match(s)
            if m:
                tipo, var = m.group(1), m.group(2)
                if m.group(3):
                    continue          # array: no es este caso
                salida.extend(
                    _evalua(base, nombre, ln, var, tipo, cuerpo,
                            solo_declaradas, confirmada=True))
                continue
            m3 = RE_DECL_TYPEDEF.match(s)
            if m3:
                tipo, var = m3.group(1), m3.group(2)
                if tipo in ESCALARES:
                    continue
                if var in ESCALARES or tipo in ("struct", "union", "enum"):
                    continue
                # sin lista de structs conocidos, esto es un CANDIDATO
                confirmada = bool(structs and tipo in structs)
                salida.extend(
                    _evalua(base, nombre, ln, var, tipo, cuerpo,
                            solo_declaradas, confirmada=confirmada))
    return salida


def _evalua(base, funcion, ln, var, tipo, cuerpo, solo_declaradas, confirmada):
    res = []
    if not confirmada:
        # candidato: solo se informa si ademas hay una llamada de copia con
        # tamano, y se marca con clase propia para no confundirlo con lo
        # confirmado.
        llamadas = llamadas_con_variable(cuerpo, var)
        for _pos, _raw, nombre_ll, tam_txt, _p in llamadas:
            if "sizeof" not in tam_txt:
                continue
            clase, copiado = arg_tamano_es_completo(tam_txt, tipo)
            if clase == "COMPLETO":
                res.append(Hallazgo(base, funcion, ln, 0, var, tipo,
                                    tam_txt.strip(), "TYPEDEF_CANDIDATE",
                                    "via " + nombre_ll))
        return res

    if inicializado_en_funcion(cuerpo, var):
        return res  # clase INITIALIZED: no es un hallazgo
    if solo_declaradas:
        res.append(Hallazgo(base, funcion, ln, 0, var, "struct " + tipo, "",
                            "UNREPORTED_NOCOPY", "sin llamada de copia visible"))
        return res
    llamadas = llamadas_con_variable(cuerpo, var)
    if not llamadas:
        res.append(Hallazgo(base, funcion, ln, 0, var, "struct " + tipo, "",
                            "UNREPORTED_NOCOPY",
                            "sin llamada de copia visible en la funcion"))
        return res
    for _pos, _raw, nombre_ll, tam_txt, _p in llamadas:
        if "sizeof" not in tam_txt and not re.match(r"^\s*\(?\s*(?:int|uint32_t)\b", tam_txt):
            continue   # llamada que no es de copia por tamano
        clase, tipo_copiado = arg_tamano_es_completo(tam_txt, tipo)
        if clase == "COMPLETO":
            res.append(Hallazgo(base, funcion, ln, 0, var, "struct " + tipo,
                                tam_txt.strip(), "FULL_SIZE_COPY",
                                "via " + nombre_ll))
        elif clase == "TYPE_MISMATCH":
            res.append(Hallazgo(base, funcion, ln, 0, var, "struct " + tipo,
                                tam_txt.strip(), "TYPE_MISMATCH",
                                "sizeof de " + str(tipo_copiado) + " en " + nombre_ll))
        else:
            res.append(Hallazgo(base, funcion, ln, 0, var, "struct " + tipo,
                                tam_txt.strip(), "COMPUTED_SIZE",
                                "via " + nombre_ll))
    return res


# ---------------------------------------------------------------------------
# SELF-TEST
#
# Un fixture de un solo caso NO puede cazar una colision. Hace falta un par que
# se confirme mutuamente: un caso defectuoso y un caso seguro que solo se
# distinguen por la CLASIFICACION del argumento de tamano. Si la herramienta no
# separa esos dos, no sirve.
# ---------------------------------------------------------------------------

FIXTURE_DEFECTUOSO = r"""
static int polaris10_program_memory_timing_parameters(struct pp_hwmgr *hwmgr)
{
	struct smu7_hwmgr *hw_data = (struct smu7_hwmgr *)(hwmgr->backend);
	struct SMU74_Discrete_MCArbDramTimingTable arb_regs;
	uint32_t i, j;
	int result = 0;

	for (i = 0; i < 8; i++) {
		for (j = 0; j < 4; j++) {
			result = polaris10_populate_memory_timing_parameters(hwmgr, i, j,
					&arb_regs.entries[i][j]);
		}
	}

	result = smu7_copy_bytes_to_smc(
			hwmgr,
			smu_data->smu7_data.arb_table_start,
			(uint8_t *)&arb_regs,
			sizeof(SMU74_Discrete_MCArbDramTimingTable),
			SMC_RAM_END);
	return result;
}
"""

# El camino legacy: MISMA operacion logica, escrita con seguridad. Si la
# herramienta no lo marca como COMPUTED_SIZE, no esta distinguiendo nada.
FIXTURE_SEGURO_LEGACY = r"""
static int si_calculate_arb_working_table(struct pp_hwmgr *hwmgr, int i)
{
	SMC_SIslands_MCArbDramTimingRegisterSet arb_regs = { 0 };
	uint32_t j;
	int result = 0;

	for (j = 0; j < i; j++) {
		result = si_calculate_arb_timing(hwmgr, j, &arb_regs.entries[j]);
	}
	return si_copy_bytes_to_smc(
			hwmgr,
			smu_data->smu7_data.arb_table_start,
			(uint8_t *)&arb_regs,
			sizeof(SMC_SIslands_MCArbDramTimingRegisterSet) * (first_arb_set + i),
			SMC_RAM_END);
}
"""

FIXTURE_SEGURO_INICIALIZADO = r"""
static int polaris10_thermal_setup_fan_table(struct pp_hwmgr *hwmgr)
{
	SMU74_Discrete_FanTable fan_table = { FDO_MODE_HARDWARE };

	fill_it(&fan_table);
	return smu7_copy_bytes_to_smc(
			hwmgr,
			smu_data->smu7_data.fan_table_start,
			(uint8_t *)&fan_table,
			sizeof(SMU74_Discrete_FanTable),
			SMC_RAM_END);
}
"""

# El par que se confirma mutuamente con el caso 1: MISMA llamada, MISMO
# sizeof del mismo tipo, pero con el tamano multiplicado. La unica diferencia
# entre este caso y el caso 1 es el asterisco. Si la herramienta no los separa,
# no esta mirando el tamano, y entonces no sirve para nada.
FIXTURE_TAMANO_CALCULADO = r"""
static int si_program_memory_timing(struct pp_hwmgr *hwmgr, int first_arb_set)
{
	SMC_SIslands_MCArbDramTimingRegisterSet arb_regs;
	uint32_t i;
	int result = 0;

	for (i = 0; i < 4; i++) {
		result = si_calculate_arb_timing(hwmgr, i, &arb_regs.entries[i]);
	}
	return si_copy_bytes_to_smc(
			hwmgr,
			smu_data->smu7_data.arb_table_start,
			(uint8_t *)&arb_regs,
			sizeof(SMC_SIslands_MCArbDramTimingRegisterSet) * (first_arb_set + i),
			SMC_RAM_END);
}
"""

# Trampa para el limpiador: un comentario y una cadena que contienen una
# declaracion falsa, y un comentario con la palabra "struct".
# Firma partida en dos lineas. Es el caso que hizo fallar el numero de linea:
# con la llave en su propia linea, contar desde la firma desplaza el numero
# en uno. Ningun fixture anterior lo cubria, y por eso el bug llego hasta el
# codigo real. Lo anadir porque el fallo es invisible en los demas casos.
FIXTURE_FIRMA_PARTIDA = (
    "linea 1 de relleno\n"
    "linea 2 de relleno\n"
    "static int firma_partida(struct pp_hwmgr *hwmgr,\n"
    "\t\tint segundo_parametro)\n"
    "{\n"
    "\tstruct UNICA_X x;\n"
    "\treturn smu7_copy_bytes_to_smc(hwmgr, d, (uint8_t *)&x,\n"
    "\t\t\tsizeof(UNICA_X), SMC_RAM_END);\n"
    "}\n"
)


FIXTURE_TRAMPAS = r"""
/* struct Falsa_Falsa f_trampa;   -- esto es un comentario */
static int con_trampa(struct pp_hwmgr *hwmgr)
{
	const char *s = "struct Otra_Falsa o_trampa;";
	struct REAL_S struct_ok;
	struct REAL_Falso f_malo;

	s = "otra";
	struct_ok.x = 1;
	return smu7_copy_bytes_to_smc(hwmgr, d, (uint8_t *)&f_malo,
			sizeof(REAL_Falso), SMC_RAM_END);
}
"""


def selftest():
    fallos = []

    def chk(cond, msg):
        if not cond:
            fallos.append(msg)

    # --- caso 1: defectuoso, debe salir FULL_SIZE_COPY ---
    r1 = analiza_fichero("caso1.c", texto=FIXTURE_DEFECTUOSO)
    c1 = [h.clase for h in r1]
    chk("FULL_SIZE_COPY" in c1,
        "caso1: se esperaba FULL_SIZE_COPY, se obtuvo %r" % c1)
    chk(any(h.variable == "arb_regs" for h in r1),
        "caso1: no se identifico la variable arb_regs")

    # --- caso 2: el par que se confirma con el caso 1 ---
    # Mismo nombre de struct en el sizeof, misma llamada, pero tamano
    # multiplicado. La diferencia con el caso 1 es UN asterisco. Si la
    # herramienta no los separa, no esta mirando el tamano.
    # Esta declaracion llega por TYPEDEF, asi que hay que confirmar el tipo.
    r2 = analiza_fichero("caso2.c", texto=FIXTURE_TAMANO_CALCULADO,
                         structs={"SMC_SIslands_MCArbDramTimingRegisterSet"})
    c2 = [h.clase for h in r2]
    chk("COMPUTED_SIZE" in c2,
        "caso2: se esperaba COMPUTED_SIZE, se obtuvo %r" % c2)
    chk("FULL_SIZE_COPY" not in c2,
        "caso2: un tamano calculado no puede ser FULL_SIZE_COPY: %r" % c2)

    # --- caso 3: el codigo legacy real, con = { 0 }. No debe salir nada ---
    r3 = analiza_fichero("caso3.c", texto=FIXTURE_SEGURO_LEGACY)
    c3 = [h.clase for h in r3]
    chk("FULL_SIZE_COPY" not in c3,
        "caso3: el camino legacy seguro fue marcado FULL_SIZE_COPY: %r" % c3)
    chk(not any(h.variable == "arb_regs" for h in r3),
        "caso3: una variable con = { 0 } esta inicializada y no debe aparecer: %r" % c3)

    # --- caso 4: inicializado con literal, tampoco debe salir ---
    r4 = analiza_fichero("caso4.c", texto=FIXTURE_SEGURO_INICIALIZADO)
    c4 = [h.clase for h in r4]
    chk("FULL_SIZE_COPY" not in c4,
        "caso4: una tabla inicializada no puede ser FULL_SIZE_COPY: %r" % c4)
    chk(not any(h.variable == "fan_table" for h in r4),
        "caso4: fan_table esta inicializada y no debe aparecer")

    # --- caso 5: el limpiador de comentarios y cadenas ---
    r5 = analiza_fichero("caso5.c", texto=FIXTURE_TRAMPAS)
    v5 = set(h.variable for h in r5)
    chk("f_trampa" not in v5,
        "caso5: se declaro una variable que solo existe en un comentario")
    chk("o_trampa" not in v5,
        "caso5: se declaro una variable que solo existe en una cadena")
    chk("struct_ok" not in v5,
        "caso5: una struct con un miembro asignado no debe salir: %r" % v5)
    chk("f_malo" in v5,
        "caso5: no se detecto el caso real entre las trampas: %r" % v5)

    # --- caso 6: emptiness. Una funcion vacia no debe reventar ---
    r6 = analiza_fichero("caso6.c", texto="static int vacio(void)\n{\n}\n")
    chk(r6 == [], "caso6: una funcion vacia devolvio %r" % r6)

    # --- caso 7: entrada malformada. llaves sin cerrar ---
    try:
        r7 = analiza_fichero("caso7.c", texto="static int roto(void)\n{\n\tstruct X x;\n")
        chk(isinstance(r7, list), "caso7: entrada malformada debio devolver lista")
    except Exception as e:
        fallos.append("caso7: entrada malformada lanzo %r" % e)

    # --- caso 8: reproducibilidad. Dos pasadas, mismo resultado ---
    a = analiza_fichero("caso1.c", texto=FIXTURE_DEFECTUOSO)
    b = analiza_fichero("caso1.c", texto=FIXTURE_DEFECTUOSO)
    chk(sorted(h.clave() for h in a) == sorted(h.clave() for h in b),
        "caso8: dos ejecuciones difieren")

    # --- caso 9: la herramienta no puede contener CJK ---
    src = io.open(__file__, encoding="utf-8").read()
    cjk = [c for c in src if 0x3000 <= ord(c) <= 0x9FFF or 0xF900 <= ord(c) <= 0xFAFF]
    chk(not cjk, "caso9: el fuente contiene caracteres CJK: %r" % cjk[:5])

    # --- caso 10: la forma typedef SIN confirmar el tipo no puede salir como
    # hallazgo confirmado. Debe salir marcada como candidata. Un tipo no
    # verificado tratado como struct es una suposicion, y hay que poder
    # distinguirla del caso real.
    r10 = analiza_fichero("caso10.c", texto=FIXTURE_TAMANO_CALCULADO)
    c10 = [h.clase for h in r10]
    chk("FULL_SIZE_COPY" not in c10,
        "caso10: sin confirmar el tipo no puede haber FULL_SIZE_COPY: %r" % c10)
    chk("COMPUTED_SIZE" not in c10,
        "caso10: sin confirmar el tipo no puede haber COMPUTED_SIZE: %r" % c10)

    # --- caso 12: el numero de linea con la firma partida en dos lineas ---
    # El caso real es
    #   static int f(struct pp_hwmgr *hwmgr)
    #   {
    #           struct T x;
    # La llave esta en la linea 2 y la declaracion en la 3. Si se cuenta
    # desde la linea de la firma, sale una unidad baja. Se compara contra el
    # numero que se lee a mano en el texto del fixture.
    esperado = FIXTURE_FIRMA_PARTIDA.split("\n").index(
        "\tstruct UNICA_X x;") + 1
    r12 = analiza_fichero("caso12.c", texto=FIXTURE_FIRMA_PARTIDA,
                          structs={"UNICA_X"})
    chk(len(r12) == 1,
        "caso12: se esperaba 1 hallazgo, se obtuvieron %d" % len(r12))
    if r12:
        chk(r12[0].linea_decl == esperado,
            "caso12: numero de linea %d, el fixture lo tiene en %d"
            % (r12[0].linea_decl, esperado))
        chk(r12[0].clase == "FULL_SIZE_COPY",
            "caso12: clase %r" % r12[0].clase)

    # --- caso 13: un escalar no puede salir como agregado ---
    r11 = analiza_fichero(
        "caso11.c",
        texto="static int f(void)\n{\n\tuint32_t x;\n\tint y;\n\tsmu7_copy_bytes_to_smc(h, d, (uint8_t *)&x, sizeof(x), e);\n\treturn 0;\n}\n",
        structs={"uint32_t"})
    chk(not r11, "caso11: un escalar saiu como agregado: %r" % r11)

    if fallos:
        for f in fallos:
            sys.stderr.write("  SELFTEST FALLO: %s\n" % f)
        return False
    return True


def cosecha_structs(rutas):
    """Recoge nombres de struct/union: typedefs y definiciones."""
    st = set()
    pat_td = re.compile(r"typedef\s+(?:struct|union)\s+([A-Za-z_][A-Za-z0-9_]*)\s*"
                        r"[A-Za-z_][A-Za-z0-9_]*\s*;")
    pat_td_a = re.compile(r"typedef\s+(?:struct|union)\s*\{[^}]*\}\s*"
                          r"([A-Za-z_][A-Za-z0-9_]*)\s*;")
    pat_def = re.compile(r"^\s*(?:struct|union)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{",
                         re.M)
    for f in recoge_ficheros(rutas):
        try:
            with io.open(f, "r", encoding="utf-8", errors="replace") as fh:
                t = limpia_comentarios_y_cadenas(fh.read())
        except (IOError, OSError):
            continue
        for p in (pat_td, pat_td_a, pat_def):
            for m in p.finditer(t):
                st.add(m.group(1))
    return st


# ---------------------------------------------------------------------------


def recoge_ficheros(rutas):
    out = []
    for r in rutas:
        if os.path.isdir(r):
            for raiz, _d, fs in os.walk(r):
                for f in sorted(fs):
                    if f.endswith(".c") or f.endswith(".h"):
                        out.append(os.path.join(raiz, f))
        elif os.path.isfile(r):
            out.append(r)
    return sorted(out)


def main(argv):
    ap = argparse.ArgumentParser(
        description="Detecta agregados de pila sin inicializar copiados a tamano completo.")
    ap.add_argument("rutas", nargs="*", help="ficheros .c/.h o directorios")
    ap.add_argument("--selftest", action="store_true", help="ejecuta el self-test")
    ap.add_argument("--clase", action="append",
                    help="filtra por clase (repetible). Por defecto solo FULL_SIZE_COPY y TYPE_MISMATCH")
    ap.add_argument("--todas", action="store_true", help="muestra todas las clases")
    ap.add_argument("--structs-from", action="append", default=[],
                    metavar="RUTA",
                    help="cabecera o directorio de donde coger los nombres de struct")
    ap.add_argument("--candidatas", action="store_true",
                    help="incluye tambien TYPEDEF_CANDIDATE")
    ap.add_argument("--version", action="store_true")
    args = ap.parse_args(argv)

    if args.version:
        sys.stdout.write("uninit_copy %s\n" % VERSION)
        return 0

    if args.selftest:
        ok = selftest()
        sys.stdout.write("  uninit_copy %s · RESULTADO %s · %d vectores conocidos "
                         "reproducidos\n" % (
                             VERSION, "OK" if ok else "FALLO",
                             CASOS_SELFTEST if ok else 0))
        return 0 if ok else 3

    if not args.rutas:
        sys.stderr.write("uninit_copy: hace falta al menos una ruta, o --selftest\n")
        return 2

    clases_filtro = args.clase
    if not clases_filtro:
        clases_filtro = (["FULL_SIZE_COPY", "TYPE_MISMATCH"] if not args.todas
                         else list(CLASES.keys()))
    if args.candidatas and "TYPEDEF_CANDIDATE" not in clases_filtro:
        clases_filtro = clases_filtro + ["TYPEDEF_CANDIDATE"]

    structs = cosecha_structs(args.structs_from) if args.structs_from else None
    if args.structs_from:
        sys.stderr.write("  %d nombres de struct cosechados de %r\n"
                         % (len(structs), args.structs_from))

    ficheros = recoge_ficheros(args.rutas)
    if not ficheros:
        sys.stderr.write("uninit_copy: no se encontro ningun .c ni .h en %r\n"
                         % args.rutas)
        return 2

    todos = []
    leidos = 0
    for f in ficheros:
        try:
            todos.extend(analiza_fichero(f, structs=structs))
            leidos += 1
        except (IOError, OSError) as e:
            sys.stderr.write("  aviso: no se pudo leer %s (%s)\n" % (f, e))

    sel = [h for h in todos if h.clase in clases_filtro]

    sys.stdout.write("uninit_copy %s · %d ficheros leidos · %d candidatos · "
                     "%d en las clases pedidas\n"
                     % (VERSION, leidos, len(todos), len(sel)))
    vistos = set()
    for h in sorted(sel, key=lambda x: (x.ruta, x.linea_decl, x.clase)):
        if h.clave() in vistos:
            continue
        vistos.add(h.clave())
        sys.stdout.write(h.a_texto() + "\n")

    if sel:
        sys.stdout.write("  RESUMEN por clase:\n")
        for c in clases_filtro:
            n = len([h for h in sel if h.clase == c])
            sys.stdout.write("    %-18s %3d   %s\n" % (c, n, CLASES.get(c, "?")))
    return 1 if sel else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

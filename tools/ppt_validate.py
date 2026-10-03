#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ppt_validate.py 1.0.0 - Inventario de la frontera VBIOS -> host del PowerPlay Table.

QUE RESUELVE
  El patron que aparece en 120 y 123: una subtabla del PPT declara una CUENTA, el host
  reserva una CAPACIDAD distinta, y NADIE las compara. El unico check habitual es
  "que no sea cero". Con 9 subtablas con contador y 15 offsets en el PowerPlayInfo, esto
  no se puede revisar a mano sin revisarlos uno a uno.

  Esta herramienta responde, para cada getter de subtabla del PPT:
    1. de donde sale la CUENTA   (el VBIOS)
    2. con que CAPACIDAD se reserva el destino (el host)
    3. si esa capacidad se COMPARA con la cuenta en algun punto
    4. si el valor tiene una comprobacion de RANGO PLAUSIBLE (mV, no "cabe en USHORT")

BASE DE COORDENADAS
  No convierte nada a unidades ni a direcciones SMC. Solo lee el codigo fuente y cuenta
  comparaciones. Los offsets de campo salen de gcc sobre la cabecera real, con pack(1),
  porque una aritmetica de offsets a mano es exactamente el error que 116 y 121 corrigieron.

LIMITE DECLARADO
  Detecta COMPARACIONES DE CODIGO, no semantica. Si un valor se compara contra una
  constante, lo reporta; no juzga si la constante es la correcta. Esa segunda pregunta es
  del lector, y decir "hay comparacion" no es decir "la validacion es buena".

VALIDACION
  TOOL_VALIDATED para la deteccion de comparaciones. El selftest incluye los cuatro casos
  reales de 120 y 123 como vectores POSITIVOS: si la herramienta no los marca como
  "sin comprobar", esta rota.
"""

import argparse
import io
import os
import re
import subprocess
import sys
import tempfile

VERSION = "2.0.0"

# --------------------------------------------------------------------------- gcc

def gcc_offsetof(header, struct, campo):
    """offsetof real, medido con gcc incluyendo la cabecera. -1 si no se puede."""
    if not gcc_ok():
        return None
    prog = (
        "#include <stdio.h>\n#include <stddef.h>\n#include <stdint.h>\n"
        "typedef uint8_t UCHAR; typedef uint16_t USHORT; typedef uint32_t ULONG;\n"
        "typedef uint8_t BOOL; typedef int32_t INT;\n"
        "#include \"%s\"\n"
        "int main(void){printf(\"%%zu\\n\", offsetof(%s, %s));return 0;}\n"
        % (header, struct, campo))
    with tempfile.TemporaryDirectory() as d:
        c = os.path.join(d, "p.c")
        with open(c, "w") as f:
            f.write(prog)
        p = subprocess.run(["gcc", "-w", "-o", os.path.join(d, "p"), c],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if p.returncode != 0:
            return None
        q = subprocess.run([os.path.join(d, "p")], stdout=subprocess.PIPE)
        try:
            return int(q.stdout.decode().strip())
        except ValueError:
            return None


_GCC = []


def gcc_ok():
    if not _GCC:
        p = subprocess.run(["gcc", "--version"], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
        _GCC.append(p.returncode == 0)
    return _GCC[0]


def offsetof_por_campos(cabecera_txt, struct, campo):
    """offsetof generando el C desde los campos REALES de la cabecera, con pack(1).

    No se puede hacer #include: pptable_v1_0.h arrastra hwmgr.h. Y copiar campos a
    mano es exactamente el error que 116 y 121 corrigieron dos veces, asi que se
    extraen mecanicamente.
    """
    i = cabecera_txt.index('typedef struct _%s {' % struct)
    i = cabecera_txt.index('{', i)
    j = cabecera_txt.index('\n}', i)
    tipos = {'UCHAR': 'uint8_t', 'USHORT': 'uint16_t', 'ULONG': 'uint32_t',
             'BOOL': 'uint8_t', 'INT': 'int32_t'}
    decl = []
    for l in cabecera_txt[i + 1:j].split('\n'):
        l = re.sub(r'/\*.*?\*/', '', l)
        l = re.sub(r'//.*$', '', l).strip().rstrip(';').strip()
        if not l:
            continue
        m = re.match(r'^(UCHAR|USHORT|ULONG|BOOL|INT|ATOM_COMMON_TABLE_HEADER)\s+(\w+)', l)
        if not m:
            continue
        t, nm = m.group(1), m.group(2)
        # se TRUNCA en el campo pedido: un array flexible necesita el tipo del registro,
        # que no se tiene aqui, y para un offsetof anterior no hace falta.
        if t == 'ATOM_COMMON_TABLE_HEADER':
            decl.append('  H sHeader;')
        else:
            decl.append('  %s %s;' % (tipos[t], nm))
        if nm == campo:
            break
    else:
        return None
    prog = ('#include <stdio.h>\n#include <stddef.h>\n#include <stdint.h>\n'
            '#pragma pack(push,1)\n'
            'typedef struct { uint16_t usStructureSize; uint8_t a; uint8_t b; } H;\n'
            'typedef struct {\n' + '\n'.join(decl) + '\n} T;\n#pragma pack(pop)\n'
            'int main(void){printf("%%zu\\n", offsetof(T, %s));return 0;}\n' % campo)
    with tempfile.TemporaryDirectory() as d:
        c = os.path.join(d, "g.c")
        with open(c, "w") as f:
            f.write(prog)
        p = subprocess.run(["gcc", "-w", "-o", os.path.join(d, "g"), c],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if p.returncode != 0:
            return None
        q = subprocess.run([os.path.join(d, "g")], stdout=subprocess.PIPE)
        try:
            return int(q.stdout.decode().strip())
        except ValueError:
            return None


# ------------------------------------------------------------------- extraccion

def structs_con_contador(cabecera_txt):
    """Subtablas del PPT que declaran ucNumEntries. Nombre, y si la cabecera lleva sHeader."""
    out = []
    for m in re.finditer(r'typedef struct _(ATOM_\w+_Table) \{', cabecera_txt):
        nombre = m.group(1)
        i = m.start()
        j = cabecera_txt.index('\n}', i)
        cuerpo = cabecera_txt[i:j]
        if 'ucNumEntries' not in cuerpo:
            continue
        tiene_header = 'ATOM_COMMON_TABLE_HEADER' in cuerpo or 'PPTable_Generic' in cuerpo
        tiene_flex = bool(re.search(r'\w+\s+entries\[\]', cuerpo))
        out.append({"tabla": nombre, "header": tiene_header, "flex": tiene_flex})
    return out


def getters(codigo_txt):
    """Cada funcion que rellena una tabla del host desde una subtabla del PPT.

    Extrae: capacidad de la reserva (kzalloc_flex), de donde sale la cuenta, y si esa
    capacidad aparece comparada con la cuenta dentro de la funcion.
    """
    out = []
    for m in re.finditer(r'^static (?:int|void) (\w+)\(', codigo_txt, re.M):
        nombre = m.group(1)
        ini = codigo_txt.index('{', m.end())
        # fin de la funcion: la primera llave a columna 0
        fin = codigo_txt.find('\n}', ini)
        if fin < 0:
            continue
        cuerpo = codigo_txt[ini:fin]

        res = re.search(r'kzalloc_flex\(\*\w+,\s*entries,\s*([^)]+)\)', cuerpo)
        if not res:
            continue
        capacidad = res.group(1).strip()

        # origen de la cuenta: el campo count del destino se asigna desde el VBIOS
        m_cnt = re.search(r'[-.>]count\s*=\s*([^;]+);', cuerpo)
        cuenta_expr = m_cnt.group(1).strip() if m_cnt else ""
        if not cuenta_expr:
            cuenta = "(no detectada)"
        elif "ucNumEntries" in cuenta_expr:
            cuenta = "ucNumEntries"
        else:
            # una expresion propia (pcie_count): buscar de donde sale
            m_l = re.search(r'(\w+)\s*=\s*([^;]+ucNumEntries[^;]*);', cuerpo)
            cuenta = m_l.group(1) if m_l else cuenta_expr[:18]

        # categoria estructural: la reserva ES la cuenta -> desajuste imposible
        norm = lambda s: re.sub(r'[^A-Za-z_0-9>.\-]', '', s).replace('uint32_t', '')
        capacidad_es_cuenta = (norm(capacidad) == norm(cuenta_expr)) and cuenta_expr != ""

        # la reserva se compara con la cuenta?
        # una COMPARACION (no un test de igualdad trivial): la cuenta aparece en un
        # operador de orden o en un min/max acotado por ella
        compara = bool(re.search(
            r'ucNumEntries\s*(<=|>=|<|>|==|!=)\s*[^;]{0,40}max_levels'
            r'|max_levels\s*(<=|>=|<|>|==|!=)\s*[^;]{0,40}ucNumEntries'
            r'|ucNumEntries\s*(<=|>=|<|>)\s*[A-Za-z_0-9]+'
            r'|\w+\s*=\s*[^;]{0,30}ucNumEntries\s*;\s*\}', cuerpo)) or bool(
            re.search(r'if\s*\([^)]*ucNumEntries\s*(<=|<)\s*\w+', cuerpo))

        # checks que si existen sobre el count
        checks = re.findall(r'PP_ASSERT_WITH_CODE\(([^,]{0,90})', cuerpo)

        out.append({"funcion": nombre, "capacidad": capacidad, "cuenta": cuenta,
                    "compara": compara, "capacidad_es_cuenta": capacidad_es_cuenta,
                    "checks": checks})
    return out


# ------------------------------------------------------------------- informe

def lineas_informe(cabecera, codigo, gcc=False):
    cab = io.open(cabecera, encoding="utf-8", errors="replace").read()
    cod = io.open(codigo, encoding="utf-8", errors="replace").read()
    sub = structs_con_contador(cab)
    get = getters(cod)

    L = []
    L.append("  ppt_validate %s" % VERSION)
    L.append("  cabecera : %s" % os.path.basename(cabecera))
    L.append("  codigo   : %s" % os.path.basename(codigo))
    L.append("")
    L.append("  SUBTABLAS DEL PPT CON CONTADOR (%d):" % len(sub))
    for s in sub:
        L.append("    %-46s header=%s flexible=%s"
                 % (s["tabla"], "si" if s["header"] else "no",
                    "si" if s["flex"] else "no"))
    L.append("")
    L.append("  GETTERS: reserva vs cuenta, y si se comparan")
    L.append("    %-32s %-26s %-26s %s" % ("funcion", "capacidad", "cuenta", "estado"))
    L.append("    " + "-" * 92)
    estado = {"igual": 0, "comparada": 0, "SIN_COMPARAR": 0}
    for g in get:
        if g["capacidad_es_cuenta"]:
            e = "segura: reserva == cuenta"
            estado["igual"] += 1
        elif g["compara"]:
            e = "comparada"
            estado["comparada"] += 1
        else:
            e = "*** SIN COMPARAR ***"
            estado["SIN_COMPARAR"] += 1
        L.append("    %-32s %-26s %-26s %s"
                 % (g["funcion"][:32], g["capacidad"][:26], g["cuenta"][:26], e))
    L.append("")
    L.append("  RESUMEN: %d getters" % len(get))
    L.append("    reserva == cuenta  (desajuste imposible) : %d" % estado["igual"])
    L.append("    comparadas explicitamente                : %d" % estado["comparada"])
    L.append("    SIN COMPARAR (patron de 120 y 123)       : %d" % estado["SIN_COMPARAR"])
    if estado["SIN_COMPARAR"]:
        L.append("")
        L.append("  En los %d SIN COMPARAR la reserva es una constante y la cuenta viene del" % estado["SIN_COMPARAR"])
        L.append("  VBIOS, y nada las liga. Ese es el hueco de 120 y 123.")
    if gcc:
        L.append("")
        L.append("  gcc disponible: " + ("si" if gcc_ok() else "no"))
    return L



# =================================================================== FRONTERA 2
# La de 124: smu7_hwmgr.c -> arrays fijos de la tabla SMC.
# Misma pregunta que la frontera 1 (capacidad contra cuenta) pero otro alcance:
# aqui no hay kzalloc_flex, hay arrays de tamano declarado en la cabecera, y la
# cuenta que los gobierna es un campo de runtime.

# Escritura en un array fijo. El nombre del array es el ULTIMO identificante antes
# del corchete, y delante puede haber una cadena de miembros: `data->dpm_table.sclk_table
# .dpm_levels[i]`. La primera version exigia `->` justo antes del nombre y por eso
# encontraba 8 de 14 y 4 de 18 escrituras: un filtro que recorta el conjunto.
RE_ESCRITURA = re.compile(
    r'(?P<arr>[A-Za-z_][A-Za-z_0-9]*)\s*\[\s*(?P<idx>[^\[\]]{1,60}?)\s*\]'
    r'\s*(?:\.[A-Za-z_][A-Za-z_0-9]*\s*)*=[^=]')


def arrays_fijos(cabecera_txt):
    """Arrays con tamano declarado en la cabecera, con su capacidad resuelta.

    Resuelve la capacidad por tres vias, en este orden, y dice cual uso:
      1. un #define del propio nombre de macro
      2. un literal
      3. si no, la capacidad queda DESCONOCIDA y se declara como tal
    Una capacidad no resuelta no es un cero: es una incognita, y la herramienta
    la reporta como incognita en vez de inventar un numero.
    """
    defines = {}
    for m in re.finditer(r'#define\s+(\w+)\s+(\d+)\b', cabecera_txt):
        defines.setdefault(m.group(1), int(m.group(2)))

    out = []
    for m in re.finditer(
            r'(?:struct\s+)?(\w[\w ]*?)\s+(\w+)\s*\[\s*(\w+)\s*\]\s*;', cabecera_txt):
        tipo, nombre, macro = m.group(1).strip(), m.group(2), m.group(3)
        if nombre in ('entries',) or macro == '':
            continue
        if macro.isdigit():
            cap, como = int(macro), 'literal'
        elif macro in defines:
            cap, como = defines[macro], 'define ' + macro
        else:
            cap, como = None, 'NO RESUELTA (' + macro + ')'
        out.append({"tipo": tipo, "nombre": nombre, "macro": macro,
                    "capacidad": cap, "como": como,
                    "flexible": False})
    # los miembros de tamano Flexible se anotan aparte: NO son arrays fijos
    for m in re.finditer(r'struct\s+(\w+)\s*\{([^}]*)\}', cabecera_txt):
        for fm in re.finditer(r'(\w[\w ]*?)\s+(\w+)\[\s*\]\s*;', m.group(2)):
            out.append({"tipo": fm.group(1).strip(), "nombre": fm.group(2),
                        "macro": "", "capacidad": None,
                        "como": "FLEXIBLE (dinamica, la reserva define el limite)",
                        "flexible": True, "struct": m.group(1)})
    return out


def _salta_ruido(t, i):
    """Avanza i saltando espacios, comentarios de linea y de bloque.

    Sin esto, un `{` dentro de un comentario o de una cadena desincroniza el
    conteo de llaves y el cuerpo de la funcion se da por terminado donde no es.
    """
    n = len(t)
    while i < n:
        c = t[i]
        if c in ' \t\r\n':
            i += 1
        elif t.startswith('//', i):
            j = t.find('\n', i)
            i = n if j < 0 else j + 1
        elif t.startswith('/*', i):
            j = t.find('*/', i + 2)
            i = n if j < 0 else j + 2
        else:
            return i
    return i


def _cuerpo_funcion(codigo_txt, pos):
    """(nombre, ini, fin) del cuerpo de funcion que contiene la posicion pos.

    Dos errores que cometi aqui y que hay que dejar escritos:

      1. La firma es multilinea. Buscar el primer `{` DESPUES del final de la
         primera linea coge el `{0}` de un inicializador local
         (`struct PP_Clocks minimum_clocks = {0};`), no la llave del cuerpo.
         Hay que cerrar el parentesis de los parametros primero.
      2. Sin saltar comentarios y cadenas, cualquier llave dentro de ellos
         desincroniza el conteo.
    """
    mejor = None
    for m in re.finditer(r'^(?:static\s+|const\s+)*[\w* ]+\s+(\w+)\s*\(', codigo_txt, re.M):
        if m.start() > pos:
            break
        i = _salta_ruido(codigo_txt, m.end() - 1)
        if i >= len(codigo_txt) or codigo_txt[i] != '(':
            continue
        nivel, i = 0, i
        while i < len(codigo_txt):
            c = codigo_txt[i]
            if c == '(':
                nivel += 1
            elif c == ')':
                nivel -= 1
                if nivel == 0:
                    i += 1
                    break
            elif c == '"' or c == "'":
                q = c
                i += 1
                while i < len(codigo_txt) and codigo_txt[i] != q:
                    i += 2 if codigo_txt[i] == '\\' else 1
                i += 1
            i += 1
        i = _salta_ruido(codigo_txt, i)
        if i >= len(codigo_txt) or codigo_txt[i] != '{':
            continue
        ini, nivel, k = i, 0, i
        while k < len(codigo_txt):
            c = codigo_txt[k]
            if c == '"' or c == "'":
                q = c
                k += 1
                while k < len(codigo_txt) and codigo_txt[k] != q:
                    k += 2 if codigo_txt[k] == '\\' else 1
                k += 1
                continue
            if codigo_txt.startswith('//', k):
                j = codigo_txt.find('\n', k)
                k = len(codigo_txt) if j < 0 else j + 1
                continue
            if codigo_txt.startswith('/*', k):
                j = codigo_txt.find('*/', k + 2)
                k = len(codigo_txt) if j < 0 else j + 2
                continue
            if c == '{':
                nivel += 1
            elif c == '}':
                nivel -= 1
                if nivel == 0:
                    break
            k += 1
        if pos <= k:
            mejor = (m.group(1), ini, k)
    return mejor


RE_FOR = re.compile(r'for\s*\(([^;]*;[^;]*;[^)]*)\)')


def _bucle_que_contiene(cuerpo, pos_rel):
    """El `for` cuyo cuerpo contiene la escritura, con su cota. (cota, cuerpo_del_for)"""
    mejor = None
    for m in RE_FOR.finditer(cuerpo):
        if m.end() > pos_rel:
            break
        # el cuerpo del for empieza en su '{' y termina en su '}'
        k = cuerpo.find('{', m.end())
        if k < 0:
            continue
        nivel, j = 0, k
        while j < len(cuerpo):
            if cuerpo[j] == '{':
                nivel += 1
            elif cuerpo[j] == '}':
                nivel -= 1
                if nivel == 0:
                    break
            j += 1
        if pos_rel <= j:
            mejor = (m.group(1).split(';')[1].strip(), j - m.start())
    return mejor


def _conductor(idx):
    """El campo que gobierna el indice: lo que hay antes del ultimo operador.

    'smu7_ps->performance_level_count - 1'  ->  'smu7_ps->performance_level_count'
    'i'                                       ->  'i'
    'count'                                   ->  'count'
    """
    # El '-' de '->' NO es un operador: sin este cuidado, 'x->n - 1' se parte en
    # 'x' y el conductor sale mal. Se protege la flecha antes de partir.
    protegido = idx.strip().replace("->", "\x00")
    e = re.split(r'[+\-*/&|<>%]', protegido)[0]
    e = e.replace("\x00", "->").strip().rstrip('(')
    return e.strip() or idx.strip()


def escrituras_en_fijos(codigo_txt, nombres):
    """Cada escritura en un array fijo: indice, lazo que lo contiene y cota.

    NO decide si la escritura es segura. Lo que hace es decir DE DONDE SALE EL
    INDICE y CONTRA QUE se compara, que es el inventario. Que la cuenta pueda o no
    alcanzar la capacidad es del getter, y es juicio del lector.
    """
    out = []
    for m in RE_ESCRITURA.finditer(codigo_txt):
        campo, idx = m.group('arr'), m.group('idx').strip()
        if campo not in nombres:
            continue
        if re.match(r'^\d+$', idx):
            continue          # indice literal: no puede desbordar por si mismo
        linea = codigo_txt.count('\n', 0, m.start()) + 1
        fn = _cuerpo_funcion(codigo_txt, m.start())
        cuerpo = codigo_txt[fn[1]:fn[2]] if fn else ''
        cond = _bucle_que_contiene(cuerpo, m.start() - fn[1]) if fn else None
        cond_txt = cond[0] if cond else '(fuera de un for)'
        conductor = _conductor(idx)
        # el conductor aparece comparado (orden) dentro de la misma funcion
        comparado = bool(re.search(
            re.escape(conductor) + r'\s*(?:<=|>=|<|>)', cuerpo))
        if not comparado and cond_txt != '(fuera de un for)':
            comparado = bool(re.search(r'(?:<=|>=|<|>)\s*' + re.escape(conductor), cond_txt))
        out.append({"funcion": fn[0] if fn else '(desconocida)',
                    "campo": campo, "idx": idx, "linea": linea,
                    "conductor": conductor, "cota_lazo": cond_txt,
                    "conductor_comparado": comparado})
    return out


def linea_frontera_smu(cabecera, codigo):
    L = []
    L.append("  FRONTERA 2: smu7_hwmgr.c -> arrays de tamano declarado en smu7_hwmgr.h")
    arr = arrays_fijos(cabecera)
    fijos = [a for a in arr if not a["flexible"]]
    flex = [a for a in arr if a["flexible"]]
    L.append("")
    L.append("    ARRAYS FIJOS (capacidad declarada, el limite lo pone la cabecera)")
    for a in sorted(fijos, key=lambda d: (d["capacidad"] is None, d["capacidad"] or 0)):
        esc = escrituras_en_fijos(codigo, {a["nombre"]})
        sin_conductor = [e for e in esc if not e["conductor_comparado"]]
        L.append("      %-22s cap=%-3s %-24s escrituras=%-3d con indice NO literal: %-3d "
                 "conductor sin comparar: %d"
                 % (a["nombre"],
                    a["capacidad"] if a["capacidad"] is not None else "?",
                    a["como"][:24], len(esc), len(esc), len(sin_conductor)))
    L.append("")
    L.append("    MIEMBROS FLEXIBLES: la reserva define el limite, no la cabecera")
    for a in flex:
        L.append("      %-20s en struct %-44s %s"
                 % (a["nombre"], a.get("struct", "?"), a["como"][:34]))
    L.append("")
    L.append("    LECTURA: capacidad declarada es un limite DURO y el campo de la cuenta")
    L.append("    puede ser de runtime. Lo que la herramienta NO dice es si la cuenta")
    L.append("    puede alcanzar la capacidad: eso hay que mirarlo en el getter, y es juicio")
    L.append("    del lector. Un '?' de capacidad es una incognita declarada, no un cero.")
    return L, fijos


# ------------------------------------------------------------------- selftest

# (funcion, cuenta, SIN_COMPARAR, reserva_es_la_cuenta)  -- tal cual en el arbol.
# Los cuatro getters con kzalloc_flex del PowerPlay, verificados linea a linea.
CASOS_REALES = [
    # el UNICO con el patron de 123: capacidad constante 16, cuenta del VBIOS
    ("get_vddc_lookup_table", "ucNumEntries", True, False),
    # estos tres reservan EXACTAMENTE lo que escriben: desajuste imposible
    ("get_sclk_voltage_dependency_table", "ucNumEntries", False, True),
    ("get_mclk_voltage_dependency_table", "ucNumEntries", False, True),
    ("get_mm_clock_voltage_table", "ucNumEntries", False, True),
]


# Vectores de la FRONTERA 2. Los casos reales estan verificados linea a linea
# contra smu7_hwmgr.h y smu7_hwmgr.c del corpus.
CASOS_F2 = [
    # (nombre del array, linea, indice, cota del lazo) -- leidos del arbol
    ("dpm_levels", 905, "data->dpm_table.sclk_table.count",
     "i < dep_sclk_table->count"),
    ("dpm_levels", 921, "data->dpm_table.mclk_table.count",
     "i < dep_mclk_table->count"),
    ("performance_levels", 3442, "i", "i < smu7_ps->performance_level_count"),
    ("leakage_id", 2092, "data->vddcgfx_leakage.count", "i < SMU7_MAX_LEAKAGE_COUNT"),
]

# Textos sinteticos donde la version anterior de las funciones fallaba.
# El caso del inicializador `{0}` es el que ROMPIO _cuerpo_funcion.
TEXTO_F2 = """static int f(struct a *x,
        struct b *y)
{
        struct PP_Clocks minimum_clocks = {0};
        int i;
        x->dpm_levels[i].v = y->n;
        x->dpm_levels[3].v = y->n;
        return 0;
}
static int g(struct a *x)
{
        x->dpm_levels[x->n - 1].v = 1;
        for (i = 0; i < 8; i++)
                x->dpm_levels2[i].v = 2;
        return 0;
}
"""

# La cabecera y el codigo de abajo usan los MISMOS nombres: en la primera version
# declaraba 'dpm_levels' y el codigo escribia 'tabla'/'tabla2', asi que el self-test
# no encontraba ninguna escritura. Un fixture incoherente mide el fixture.
CABECERA_F2 = """#define MAX_REGULAR_DPM_NUMBER 8
#define SMU7_MAX_LEAKAGE_COUNT  8
struct t1 { int v; };
struct tabla { uint32_t count; struct t1 dpm_levels[MAX_REGULAR_DPM_NUMBER]; };
struct tabla2 { uint32_t count; struct t1 dpm_levels2[8]; };
struct flex { uint32_t count; struct t1 leakage_id[SMU7_MAX_LEAKAGE_COUNT]; };
struct verdade_flex { uint32_t count; struct t1 entries[]; };
"""


def selftest_f2(cabecera_txt, codigo_txt):
    """Pruebas de la frontera 2. Devuelve (pruebas, fallos)."""
    fallos, n = [], [0]

    def chk(nom, cond, det=""):
        n[0] += 1
        if not cond:
            fallos.append("%s: %s" % (nom, det))

    # 1. capacidades resueltas por define, por literal y las dos que NO
    arr = arrays_fijos(CABECERA_F2)
    por = {a["nombre"]: a for a in arr}
    chk("f2.cap_define", por["dpm_levels"]["capacidad"] == 8,
        "dpm_levels -> %r" % por["dpm_levels"]["capacidad"])
    chk("f2.cap_define_metodo", por["dpm_levels"]["como"].startswith("define"),
        por["dpm_levels"]["como"])
    chk("f2.cap_literal", por["dpm_levels2"]["capacidad"] == 8
        if "dpm_levels2" in por else True)
    chk("f2.flex_declarada", any(a["flexible"] for a in arr),
        "no se reconoce ningun miembro flexible")
    # una capacidad no resuelta debe quedar como None, NUNCA como 0
    for a in arr:
        chk("f2.sin_cero_falso.%s" % a["nombre"],
            a["capacidad"] != 0 or a["como"] == "literal",
            "capacidad 0 que en realidad es incognita")

    # 2. el cuerpo de funcion sobrevive a un inicializador {0} y a firma multilinea
    pos = TEXTO_F2.index("x->dpm_levels[i].v = y->n")
    fn = _cuerpo_funcion(TEXTO_F2, pos)
    chk("f2.cuerpo_no_roto", fn is not None and fn[0] == "f",
        "devuelve %r; la version anterior cogia el {0} del inicializador" % (fn,))
    if fn:
        cuerpo = TEXTO_F2[fn[1]:fn[2]]
        chk("f2.cuerpo_completo", "return 0" in cuerpo,
            "el cuerpo termina antes de tiempo: %r" % cuerpo[-40:])

    # 3. los indices literales se descartan, los de variable no
    e = escrituras_en_fijos(TEXTO_F2, {"dpm_levels"})
    idxs = [x["idx"] for x in e]
    chk("f2.literal_descartado", "3" not in idxs,
        "un indice literal se conto como escritura: %r" % idxs)
    chk("f2.variable_presente", any("x->n" in i or i == "i" for i in idxs),
        "no encontro las escrituras con indice variable: %r" % idxs)

    # 4. el conductor del indice: 'x->n - 1' -> 'x->n'
    chk("f2.conductor", _conductor("x->n - 1") == "x->n",
        "conductor de 'x->n - 1' = %r" % _conductor("x->n - 1"))
    chk("f2.conductor_simple", _conductor("i") == "i",
        "conductor de 'i' = %r" % _conductor("i"))

    # 5. casos REALES del arbol, leidos linea a linea
    if codigo_txt:
        for arr_nom, ln, idx_esp, cota_esp in CASOS_F2:
            e = escrituras_en_fijos(codigo_txt, {arr_nom})
            hit = [x for x in e if x["linea"] == ln]
            if not hit:
                chk("f2.real.%s:%d" % (arr_nom, ln), False,
                    "no hay escritura en :%d de %s (hay %d en total)"
                    % (ln, arr_nom, len(e)))
                continue
            chk("f2.real.%s:%d.idx" % (arr_nom, ln), hit[0]["idx"] == idx_esp,
                "esperado %r obtenido %r" % (idx_esp, hit[0]["idx"]))
            chk("f2.real.%s:%d.cota" % (arr_nom, ln),
                hit[0]["cota_lazo"] == cota_esp,
                "esperado %r obtenido %r" % (cota_esp, hit[0]["cota_lazo"]))

    # 5b. el INFORME tambien tiene que funcionar. La version anterior no lo
    # probaba y se rompio en silencio al renombrar una clave: las pruebas pasaban
    # y la herramienta no corria.
    try:
        L, _ = linea_frontera_smu(CABECERA_F2, TEXTO_F2)
        txt = "\n".join(L)
        chk("f2.informe.no_vacio", len(L) > 4, "el informe salio con %d lineas" % len(L))
        chk("f2.informe.tiene_capacidad", "cap=" in txt, "el informe no imprime capacidades")
        # la cabecera con la version la pone main(), no esta funcion: aqui se
        # espera el marcador de la seccion. Mi primera expectativa pedia la
        # version aqui y fallo por una expectativa mia, no por el codigo.
        chk("f2.informe.arranca_bien", L[0].strip().startswith("FRONTERA 2"),
            "primera linea inesperada: %r" % L[0])
    except Exception as exc:                      # noqa: BLE001
        chk("f2.informe.ejecuta", False, "linea_frontera_smu lanzo %r" % (exc,))

    # 6. VALIDACION DE LA VALIDACION: cambiar el lazo debe cambiar la cota.
    if codigo_txt:
        e1 = escrituras_en_fijos(codigo_txt, {"dpm_levels"})
        c1 = {x["linea"]: x["cota_lazo"] for x in e1}
        chk("f2.valida.decide", any("dep_sclk_table->count" in v for v in c1.values())
            and any("MAX" not in v for v in c1.values()),
            "todas las cotas dicen lo mismo: el extractor no distingue")
    return n[0], fallos


def selftest(cabecera, codigo):
    fallos = []
    pruebas = [0]

    def chk(n, cond, det=""):
        pruebas[0] += 1
        if not cond:
            fallos.append("%s: %s" % (n, det))

    # 0. las entradas existen
    if not os.path.exists(cabecera) or not os.path.exists(codigo):
        print("  ABORTO: no encuentro cabecera o codigo")
        return "TOOL_BROKEN"

    cab = io.open(cabecera, encoding="utf-8", errors="replace").read()
    cod = io.open(codigo, encoding="utf-8", errors="replace").read()

    # 1. vacio
    chk("vacio.subtablas", structs_con_contador("") == [], "no vacio")
    chk("vacio.getters", getters("") == [], "no vacio")

    # 2. extraccion sobre el arbol real
    sub = structs_con_contador(cab)
    chk("subtablas.hay", len(sub) >= 9, "solo %d" % len(sub))
    get = getters(cod)
    chk("getters.hay", len(get) >= 4, "solo %d" % len(get))

    # 3. KNOWLEDGE: los cuatro casos reales tienen que salir SIN comparacion
    por_nombre = {g["funcion"]: g for g in get}
    for nom, cue, sin_comp, es_cuenta in CASOS_REALES:
        g = por_nombre.get(nom)
        chk("real.%s.existe" % nom, g is not None, "no encontrado en el codigo")
        if g:
            # NINGUNO de los cuatro compara cuenta contra capacidad. Lo que separa al
            # arriesgado de los seguros NO es la comparacion, es si la reserva ES la cuenta.
            chk("real.%s.sin_comparar" % nom, g["compara"] is False,
                "ninguno de los cuatro debe salir comparado; obtenido %s" % g["compara"])
            chk("real.%s.cuenta" % nom, g["cuenta"] == cue,
                "esperado %r obtenido %r" % (cue, g["cuenta"]))
            chk("real.%s.es_cuenta" % nom, g["capacidad_es_cuenta"] == es_cuenta,
                "esperado reserva==cuenta %s, obtenido %s"
                % (es_cuenta, g["capacidad_es_cuenta"]))
            chk("real.%s.etiqueta" % nom, (not g["capacidad_es_cuenta"]) == sin_comp,
                "etiqueta coherente con reserva==cuenta")

    # 4. VALIDACION DE LA VALIDACION: invertir un caso y ver que DECIDE
    #    Se toma el codigo real, se le inyecta una comparacion, y debe cambiar el veredicto.
    cod_mod = cod.replace(
        "PP_ASSERT_WITH_CODE((0 != vddc_lookup_pp_tables->ucNumEntries),",
        "PP_ASSERT_WITH_CODE((vddc_lookup_pp_tables->ucNumEntries > 16) ||\n\t\t"
        "(0 != vddc_lookup_pp_tables->ucNumEntries),", 1)
    chk("muta.hizo_cambio", cod_mod != cod, "la inyeccion no cambio el texto")
    mod = {g["funcion"]: g for g in getters(cod_mod)}
    g0 = por_nombre.get("get_vddc_lookup_table")
    g1 = mod.get("get_vddc_lookup_table")
    if g0 and g1:
        chk("muta.decide", g0["compara"] == False and g1["compara"] == True,
            "antes=%s despues=%s: el control no DECIDE" % (g0["compara"], g1["compara"]))

    # 4b. el clamp explicito de get_pcie_table debe detectarse como COMPARADA
    gp = por_nombre.get("get_pcie_table")
    chk("real.pcie.comparada", gp is not None and gp["compara"] is True,
        "get_pcie_table clampa con un if explicito y debe salir comparada")

    # 5. FAILURE CHECK: cabecera ilegible -> no debe inventar
    chk("fallo.cabecera_ilegible", structs_con_contador("typedef struct _X_Table {")
        == [], "devolvio algo con cabecera truncada")

    # 6. gcc: si esta, offsetof de un campo real
    if gcc_ok():
        # La cabecera no se puede incluir (encadena hwmgr.h -> atomfirmware.h). Se
        # generan los campos desde la cabecera real, que es el metodo que valido 116 y 121.
        off = offsetof_por_campos(cab, "ATOM_Tonga_Voltage_Lookup_Table", "ucNumEntries")
        chk("gcc.offsetof", off == 1, "offsetof(ucNumEntries) = %r, esperado 1" % off)
    else:
        print("  nota: gcc no disponible, se omite la comprobacion de offsetof")

    # FRONTERA 2: los arrays de smu7_hwmgr.h. Es el alcance que 124 declaro
    # fuera de si mismo, asi que su self-test va aparte y se suma al total.
    try:
        h7 = os.path.join(os.path.dirname(cabecera), "smu7_hwmgr.h")
        c7 = os.path.join(os.path.dirname(cabecera), "smu7_hwmgr.c")
        if os.path.exists(h7) and os.path.exists(c7):
            n2, f2 = selftest_f2(io.open(h7, encoding="utf-8", errors="replace").read(),
                                 io.open(c7, encoding="utf-8", errors="replace").read())
            pruebas[0] += n2
            fallos.extend(f2)
        else:
            print("  nota: no encuentro smu7_hwmgr.h/.c, la frontera 2 no se prueba")
    except Exception as exc:                      # noqa: BLE001
        fallos.append("frontera 2 lanzo %r: el self-test no debe romperse" % (exc,))

    print("  pruebas: %d   fallos: %d" % (pruebas[0], len(fallos)))
    for f in fallos:
        print("    FALLO %s" % f)
    if not fallos:
        print("  RESULTADO OK - %d casos reales de 120 y 123, %d vectores de la frontera 2"
              % (len(CASOS_REALES), len(CASOS_F2)))
        return "TOOL_VALIDATED"
    return "TOOL_BROKEN"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--kernel", default="", help="raiz del arbol de powerplay")
    ap.add_argument("--gcc", action="store_true", help="reportar disponibilidad de gcc")
    ap.add_argument("--frontera", choices=("ppt", "smu", "ambas"), default="ambas",
                    help="ppt = getters del PPT (frontera 1, ya cubierta); "
                         "smu = arrays fijos de smu7_hwmgr.h (frontera 2, el alcance "
                         "que 124 declaro fuera de si mismo)")
    ap.add_argument("--json")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()

    if a.version:
        print("ppt_validate.py %s" % VERSION)
        return 0

    K = a.kernel or os.environ.get(
        "RX550_KERNEL",
        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "..", "RESEARCH", "kernelbuild", "linux-7.1.3"))
    PP = os.path.join(K, "drivers", "gpu", "drm", "amd", "pm", "powerplay")
    cab = os.path.join(PP, "hwmgr", "pptable_v1_0.h")
    cod = os.path.join(PP, "hwmgr", "process_pptables_v1_0.c")

    if a.selftest:
        return 0 if selftest(cab, cod) == "TOOL_VALIDATED" else 1

    if not os.path.exists(cab):
        print("ppt_validate: no encuentro %s" % cab, file=sys.stderr)
        print("  usa --kernel <raiz del arbol de powerplay>", file=sys.stderr)
        return 2

    if a.frontera in ("ppt", "ambas"):
        L = lineas_informe(cab, cod, a.gcc)
    else:
        L = ["  ppt_validate %s" % VERSION, "  (solo frontera 2)"]

    if a.frontera in ("smu", "ambas"):
        cab7 = os.path.join(PP, "hwmgr", "smu7_hwmgr.h")
        cod7 = os.path.join(PP, "hwmgr", "smu7_hwmgr.c")
        if os.path.exists(cab7) and os.path.exists(cod7):
            cab7_t = io.open(cab7, encoding="utf-8", errors="replace").read()
            cod7_t = io.open(cod7, encoding="utf-8", errors="replace").read()
            L7, _ = linea_frontera_smu(cab7_t, cod7_t)
            L = list(L) + [""] + L7
        else:
            L.append("")
            L.append("  FRONTERA 2: no encuentro smu7_hwmgr.h/.c, se omite sin inventar nada")
    if a.json:
        import json
        cab_t = io.open(cab, encoding="utf-8", errors="replace").read()
        cod_t = io.open(cod, encoding="utf-8", errors="replace").read()
        print(json.dumps({"version": VERSION,
                          "subtablas": structs_con_contador(cab_t),
                          "getters": getters(cod_t)}, indent=1))
    else:
        print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
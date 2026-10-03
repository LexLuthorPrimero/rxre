#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
count_guard.py 1.0.0 - Cada indice `count - N` y si algo comprueba que count llega.

QUE RESUELVE
  En el camino SMU 7.4 / Polaris12 hay 35 accesos con la forma

      tabla->entradas[tabla->count - 1]
      nivel->dpm_levels[nivel->count - 1]

  Si `count` vale cero, el indice es -1: una lectura o escritura ANTES del principio
  del array. La pregunta que responde esta herramienta es una sola y es mecanica:

      en la funcion que contiene el acceso, hay ANTES una comparacion de orden
      sobre ESE MISMO campo `count`?

  Y anade la distincion que decide la gravedad: si el array donde se indexa es de
  tamano FLEXIBLE (lo define una reserva) o FIJO (lo define una capacidad en la
  cabecera). En el caso flexible, `[-1]` es memoria anterior a la reserva. En el fijo,
  es memoria anterior dentro de la struct que lo contiene.

  Casos de referencia, leidos linea a linea:
    - smu7_hwmgr.c:3269  `if (mclk_table.count < 1) return -EINVAL;`  protege :3277 y :3280
                         pero NO protege :3272, que lee `sclk_table.count - 1`. OTRO campo.
    - smu7_hwmgr.c:5238  dos indices `count - 1` y ni una sola comprobacion.

LIMITE DECLARADO
  La herramienta NO declara ningun sitio defectuoso. Declara INVENTARIO: donde, con
  que campo, con que guarda y de que tipo es el array. Que `count` pueda o no valer
  cero en una placa concreta es del getter que lo rellena, y es juicio del lector.

  Un sitio sin guarda no es un fallo: es un sitio cuya garantia hay que buscar en el
  getter. Este fichero no la busca.

VALIDACION
  TOOL_VALIDATED para la extraccion, la busqueda de la guarda y la clasificacion del
  array. El self-test incluye los dos casos de referencia, leidos del corpus, y un
  caso sintetico donde la guarda esta DESPUES del acceso, que es el que separa una
  herramienta que decide de una que cuenta.
"""

import argparse
import io
import os
import re
import sys

VERSION = "1.0.0"

GUARDADO, SIN_GUARDIA, GUARDIA_TARDE, SIN_FUNCION, CORTOCIRCUITO = (
    "GUARDADO_ANTES", "SIN_GUARDIA", "GUARDIA_DESPUES", "SIN_FUNCION",
    "CORTOCIRCUITO_POR_OR")

# Un `||` a la IZQUIERDA del acceso dentro de la misma condicion lo puede hacer
# inalcanzable, y es el caso de smu7_hwmgr.c:902:
#
#     if (i == 0 || dpm_levels[count - 1].value != entries[i].clk)
#
# Con `i == 0` el `||` cortocircuita, `count` sigue valiendo 0 y `dpm_levels[-1]`
# NO se evalua. Sin modelar esto, la herramienta se AUTOPORTA como SIN_GUARDIA un
# acceso que el lenguaje ya garantiza. Ojo: esto solo vale si el operandoizquierdo
# del `||` es cierto cuando count == 0; la herramienta lo MARCA y no lo resuelve,
# porque resolverlo exige razonar sobre el valor de la condicion.

# La cadena del indice termina EN `count`. La primera version de estos dos patrones
# ponia la cadena ANTES de `count` y luego exigia un `count` mas, de modo que
# `t->count - 1` no casaba nunca: la cadena se comia el `count` y el patron pedia un
# segundo. Ademas no aceptaba notacion con punto (`sclk_table.count`).
#
# Aqui `expr` y `campo` son la cadena COMPLETA, con el `count` final dentro.
# El ultimo elemento de la cadena es cualquier identificador que ACABE en `count`
# (count, performance_level_count, levels_count) o sea `*entries` (num_entries).
# La primera version solo aceptaba tres literales y por eso se le escapaban
# los 5 sitios de performance_level_count, entre ellos :5238.
# El prefijo es OPCIONAL a proposito: con `[A-Za-z_]\w*count` el campo desnudo
# `count` NO casaba nunca, porque tras consumir la primera letra no quedaba
# `count` delante. Y `count` a secas es el campo mas frecuente del arbol.
_ULTIMO = r'(?:[A-Za-z_][A-Za-z_0-9_]*)?(?:count|entries)'
_CADENA = r'(?:[A-Za-z_][A-Za-z_0-9]*\s*(?:->|\.)\s*)*' + _ULTIMO

# indice con una resta:  entradas[ t->count - 1 ]
# `miembro` dice si el nombre del array va precedido de `->` o `.`. Sin esa
# distincion, un VARIABLE LOCAL llamado `levels` eredita la capacidad de cualquier
# miembro del arbol que se llame tambien `levels` (fiji_smumgr.c:1038 heredaba
# SMU10_MAX_HARDWARE_POWERLEVELS de un struct sin relacion). Nombre igual no es
# tipo igual: es mi propia regla NAME_MATCH != SEMANTIC_MATCH, commitida por mi
# propia herramienta.
RE_SITIO = re.compile(
    r'(?:(?P<miembro>[A-Za-z_][A-Za-z_0-9]*)\s*(?:->|\.)\s*)?'
    r'(?P<arr>[A-Za-z_][A-Za-z_0-9]*)\s*\[\s*'
    r'(?P<expr>' + _CADENA + r'\s*-\s*(?P<n>\d+))\s*\]')

# una comparacion de orden sobre un campo count
RE_COMPARA = re.compile(
    r'(?P<campo>' + _CADENA + r')\s*(?P<op><=|>=|==|!=|<|>)\s*(?P<val>[^;]{0,24})')


def limpia(texto):
    """Quita comentarios y literales de cadena, para que un count dentro de un
    comentario no cuente como acceso real."""
    out = []
    i, n = 0, len(texto)
    while i < n:
        c = texto[i]
        if texto.startswith('//', i):
            j = texto.find('\n', i)
            j = n if j < 0 else j
            out.append(' ' * (j - i))
            i = j
        elif texto.startswith('/*', i):
            j = texto.find('*/', i + 2)
            j = n - 2 if j < 0 else j
            out.append(''.join(ch if ch == '\n' else ' ' for ch in texto[i:j + 2]))
            i = j + 2
        elif c == '"' or c == "'":
            q = c
            j = i + 1
            while j < n and texto[j] != q:
                j += 2 if texto[j] == '\\' else 1
            j = min(j + 1, n)
            out.append(''.join(ch if ch == '\n' else ' ' for ch in texto[i:j]))
            i = j
        else:
            out.append(c)
            i += 1
    return ''.join(out)


def trocea_funciones(texto):
    """[(nombre, ini_linea, fin_linea, cuerpo)] de un fichero de C.

    Firma: se cierra el parentesis de los parametros antes de buscar la llave del
    cuerpo. Sin eso se coge el `{` de un inicializador local (`= {0};`), que es el
    fallo que tuvo mi primera version de esta misma idea en ppt_validate.
    """
    res = []
    for m in re.finditer(r'^(?:static\s+|const\s+|inline\s+)*[\w* ]+\s+(\w+)\s*\(', texto, re.M):
        i = m.end() - 1
        if i >= len(texto) or texto[i] != '(':
            continue
        nivel, i = 0, i
        while i < len(texto):
            c = texto[i]
            if c == '(':
                nivel += 1
            elif c == ')':
                nivel -= 1
                if nivel == 0:
                    i += 1
                    break
            i += 1
        while i < len(texto) and texto[i] in ' \t\r\n':
            i += 1
        if i >= len(texto) or texto[i] != '{':
            continue
        ini, nivel, k = i, 0, i
        while k < len(texto):
            if texto[k] == '{':
                nivel += 1
            elif texto[k] == '}':
                nivel -= 1
                if nivel == 0:
                    break
            k += 1
        cuerpo = texto[ini:k + 1]
        li = texto.count('\n', 0, ini) + 1
        lf = texto.count('\n', 0, k) + 1
        res.append((m.group(1), li, lf, cuerpo))
    return res


def _declaraciones_de(nombre, cabeceras):
    """TODAS las declaraciones del array llamado `nombre` en el corpus."""
    out = []
    for txt in cabeceras:
        for m in re.finditer(r'\b' + re.escape(nombre) + r'\s*\[\s*(\w*)\s*\]\s*;', txt):
            dentro = m.group(1)
            if dentro == '':
                out.append("FLEXIBLE")
            elif dentro.isdigit():
                out.append("FIJO:" + dentro)
            else:
                val = None
                for d in re.finditer(r'#define\s+' + re.escape(dentro) + r'\s+(\d+)\b', txt):
                    val = d.group(1)
                    break
                out.append("FIJO:%s=%s" % (dentro, val) if val
                           else "FIJO:%s(no resuelta)" % dentro)
    return out


def tipo_de_array(nombre, cabeceras):
    """El tipo del array `nombre`, o una ambiguedad declarada si hay varios.

    Aqui estaba el defecto mas gordo de la primera version: devolvia la PRIMERA
    declaracion que encontraba con ese nombre. El arbol tiene miembros
    `entries[8]` (fijos, en varias familias) y `entries[]` (flexibles, en las tablas
    del PPT), asi que `dep_sclk_table->entries[count - 1]` salia FIJO:8 cuando es
    FLEXIBLE. Y la distincion decide la gravedad: antes de una reserva, o dentro de
    la struct. Un tipo equivocado es peor que un tipo desconocido.

    Ante varias declaraciones que NO coinciden, la respuesta es AMBIGUO y se listan
    todas. No se elige una.
    """
    decls = _declaraciones_de(nombre, cabeceras)
    if not decls:
        return "NO_ENCONTRADO"
    unicas = sorted(set(decls))
    if len(unicas) == 1:
        return unicas[0]

    # Hay varias declaraciones y NO coinciden. Dos bloques:
    #   - los valores numericos, que es lo que decide si `count - 1` cabe o no;
    #   - si ademas hay alguna FLEXIBLE, porque ahi el limite lo pone la reserva.
    # Se listan los valores ordenados, no los nombres de macro: el nombre ya se
    # completo al resolverlo, y seis nombres no le dicen nada al lector.
    nums = []
    hay_flex = False
    for d in unicas:
        if d == "FLEXIBLE":
            hay_flex = True
            continue
        # Dos formas: el literal sale como `FIJO:8` y el de macro como
        # `FIJO:MACRO=8`. Buscar solo la segunda dejaba el conjunto VACIO y
        # producia `FIJO{}`, que es peor que no decir nada.
        m = re.search(r'(\d+)$', d)
        nums.append(int(m.group(1)) if m else None)
    nums = sorted({x for x in nums if x is not None})
    base = ("FLEXIBLE+FIJO{%s}" % ",".join(str(x) for x in nums)) if hay_flex \
        else ("FIJO{%s}" % ",".join(str(x) for x in nums))
    return "AMBIGUO %s (%d declaraciones en el arbol)" % (base, len(decls))


def guarda_para(cuerpo, campo, linea_rel, n):
    """La primera comparacion de orden sobre `campo`, y si va antes del acceso.

    Devuelve (estado, texto_de_la_comparacion, linea_rel_de_la_comparacion).
    """
    antes, despues = None, None
    for m in RE_COMPARA.finditer(cuerpo):
        c = re.sub(r'\s+', '', m.group('campo'))
        if c != re.sub(r'\s+', '', campo):
            continue
        rel = cuerpo.count('\n', 0, m.start())
        # el acceso esta en rel; una guarda tiene que estar ANTES
        if rel < linea_rel and antes is None:
            antes = (m.group(0).strip()[:44], rel)
        elif rel > linea_rel and despues is None:
            despues = (m.group(0).strip()[:44], rel)
    if antes:
        return GUARDADO, antes[0], antes[1]
    if despues:
        return GUARDIA_TARDE, despues[0], despues[1]
    return SIN_GUARDIA, "", -1


def analiza(texto, cabeceras):
    limpio = limpia(texto)
    lineas = limpio.split('\n')
    funcs = trocea_funciones(limpio)

    # posicion en numero de linea de cada acceso
    crudos = []
    for m in RE_SITIO.finditer(limpio):
        ln = limpio.count('\n', 0, m.start()) + 1
        expr = re.sub(r'\s+', '', m.group('expr'))
        # `expr` YA es la cadena completa con el `count` final. Recortar el sufijo
        # haria que la guarda de un campo se confundiera con la de este.
        # La CLAVE de emparejamiento es la cadena del indice SIN el `- N`.
        # Antes pasaba `expr` entero, o sea `t->count-1`, y se comparaba contra el
        # `t->count` de la guarda: no podia coincidir nunca, y toda guarda salia
        # SIN_GUARDIA. El `- N` se quita aqui y no en el otro lado.
        clave = re.sub(r'\s*-\s*\d+$', '', expr)
        campo = re.sub(r'(?:[A-Za-z][A-Za-z_0-9_]*)?(?:count|entries)$', '', clave) or clave
        es_miembro = m.group('miembro') is not None
        crudos.append({
            "linea": ln,
            "array": m.group('arr'),
            "miembro": es_miembro,
            "expr": expr,
            "clave": clave,
            "campo": campo,
            "n": int(m.group('n')),
            "texto": lineas[ln - 1].strip()[:66],
        })

    out = []
    for s in crudos:
        fn = None
        for nombre, li, lf, cuerpo in funcs:
            if li <= s["linea"] <= lf:
                fn = (nombre, li, cuerpo)
                break
        if not fn:
            s.update({"funcion": "(fuera de funcion)", "estado": SIN_FUNCION,
                      "guarda": "", "tipo_array": "NO_ENCONTRADO"})
            out.append(s)
            continue
        rel = s["linea"] - fn[1]
        estado, gtxt, grel = guarda_para(fn[2], s["clave"], rel, s["n"])
        # el `||` que precede al acceso en su misma linea
        if estado == SIN_GUARDIA:
            # Una linea que EMPIEZA por `||` es una CONTINUACION de una condicion
            # multilinea, no un cortocircuito: el operando de la izquierda esta en
            # la linea anterior y este `count - 1` si se evalua. Marcarlo aqui era
            # un falso positivo mio (smu7_hwmgr.c:1000 y :1001).
            izq = s["texto"].split('||')[0]
            if '||' in s["texto"] and '[' not in izq and not s["texto"].lstrip().startswith('|'):
                estado = CORTOCIRCUITO
        # Un identificador suelto NO hereda la capacidad de un miembro homonimo:
        # se declara tipo no resuelto, que es una incognita y no un cero.
        if es_miembro:
            tipo = tipo_de_array(s["array"], cabeceras)
        else:
            tipo = "IDENTIFICADOR_SUELTO (no es miembro: capacidad sin determinar)"
        s.update({"funcion": fn[0], "estado": estado, "guarda": gtxt,
                  "tipo_array": tipo,
                  "linea_guarda": (fn[1] + grel) if grel >= 0 else -1})
        out.append(s)
    out.sort(key=lambda d: (d["funcion"], d["linea"]))
    return out


def informe(sitios):
    L = ["  count_guard %s" % VERSION, ""]
    total = len(sitios)
    by = {GUARDADO: [], SIN_GUARDIA: [], GUARDIA_TARDE: [], SIN_FUNCION: [],
          CORTOCIRCUITO: []}
    for s in sitios:
        by[s["estado"]].append(s)
    L.append("    ACCESOS CON UN INDICE `count - N`: %d" % total)
    for e in (GUARDADO, SIN_GUARDIA, GUARDIA_TARDE, CORTOCIRCUITO, SIN_FUNCION):
        L.append("      %-16s %3d  %5.1f%%" % (e, len(by[e]),
                                              100.0 * len(by[e]) / total if total else 0))
    L.append("")
    L.append("    POR TIPO DE ARRAY (decide la gravedad: antes de la reserva, o dentro de la struct)")
    tc = {}
    for s in sitios:
        tc[s["tipo_array"]] = tc.get(s["tipo_array"], 0) + 1
    for k, v in sorted(tc.items(), key=lambda kv: -kv[1]):
        L.append("      %-30s %3d" % (k, v))
    if by[SIN_GUARDIA]:
        L.append("")
        L.append("    SIN GUARDIA (el getter es quien tiene que garantizar que count llega):")
        for s in by[SIN_GUARDIA]:
            L.append("      %-30s :%-6d %-34s arr=%-14s %s"
                     % (s["funcion"][:30], s["linea"], s["expr"][:34],
                        s["array"], s["tipo_array"]))
    if by[CORTOCIRCUITO]:
        L.append("")
        L.append("    CORTOCIRCUITO_POR_OR (MARCA, NO RESUELVE: puede estar protegido o no)")
        for s in by[CORTOCIRCUITO]:
            L.append("      %-30s :%-6d %s" % (s["funcion"][:30], s["linea"], s["texto"][:52]))
    L.append("")
    L.append("    LECTURA: SIN_GUARDIA no es un fallo. Es un sitio cuya garantia hay que ir a")
    L.append("    buscar al getter que rellena el count. Esta herramienta no lo busca.")
    L.append("    CORTOCIRCUITO_POR_OR solo dice que hay un `||` delante en la misma linea:")
    L.append("    eso NO implica que el acceso sea inalcanzable. Hay que leer la condicion.")
    return L


# --------------------------------------------------------------------- selftest

# Los dos casos de referencia, leidos linea a linea del corpus. El segundo miembro
# de cada tupla es lo que la herramienta TIENE que decir.
CASOS_REALES = [
    # (fichero, linea, funcion, estado, expr)
    ("smu7_hwmgr.c", 3272, "smu7_get_profiling_clk", SIN_GUARDIA, "sclk_tablecount-1"),
    ("smu7_hwmgr.c", 3280, "smu7_get_profiling_clk", GUARDADO, "mclk_tablecount-2"),
    ("smu7_hwmgr.c", 5238, "smu7_set_sclk_od", SIN_GUARDIA, "performance_levelcount-1"),
    ("smu7_hwmgr.c", 5239, "smu7_set_sclk_od", SIN_GUARDIA, "golden_sclk_tablecount-1"),
    ("smu7_hwmgr.c", 1515, "smu7_populate_umdpstate_clocks", SIN_GUARDIA,
     "sclk_tablecount-1"),
    ("smu7_hwmgr.c", 902, "smu7_setup_dpm_tables_v1", CORTOCIRCUITO,
     "count-1"),
]

SINTETICO = """
static int con_guardia(struct t *t)
{
        if (t->count < 1)
                return -EINVAL;
        return t->entries[t->count - 1].v;
}
static int guarda_tarde(struct t *t)
{
        int v = t->entries[t->count - 1].v;
        if (t->count < 1)
                return -EINVAL;
        return v;
}
static int con_otro_campo(struct t *t)
{
        if (t->otro < 1)
                return -EINVAL;
        return t->entries[t->count - 1].v;
}
static int en_comentario(struct t *t)
{
        /* aqui pone t->entries[t->count - 1] pero es un comentario */
        return 0;
}
static int en_cadena(struct t *t)
{
        const char *s = "t->entries[t->count - 1]";
        return s ? 1 : 0;
}
"""

# El local de fiji_smumgr.c:1038: un puntero cuyo nombre coincide con el de un
# miembro de otro struct. La herramienta tiene que decir que no sabe su tipo.
TEXTO_LOCAL = (
    "static int f(struct dpm *t, struct lv *levels)\n"
    "{\n"
    "        return levels[t->count - 1].v;\n"
    "}\n")

CABECERAS = [
    "struct rec { int v; };\n"
    "struct t { uint32_t count; struct rec entries[]; };\n",
    "#define MAX_REGULAR_DPM_NUMBER 8\n"
    "struct dpm { uint32_t count; struct rec dpm_levels[MAX_REGULAR_DPM_NUMBER]; };\n",
]


def selftest(sitios_reales=None):
    fallos, n = [], [0]

    def chk(nom, cond, det=""):
        n[0] += 1
        if not cond:
            fallos.append("%s: %s" % (nom, det))

    # 1. sinteticos: los cuatro comportamientos que importan
    sit = analiza(SINTETICO, CABECERAS)
    por_f = {}
    for s in sit:
        por_f.setdefault(s["funcion"], []).append(s)

    chk("sint.hay_sitios", len(sit) == 3,
        "esperaba 3 accesos sinteticos, hay %d: %r" % (len(sit), [s['linea'] for s in sit]))
    chk("sint.con_guardia", por_f["con_guardia"][0]["estado"] == GUARDADO,
        "esperaba GUARDADO, %s" % por_f["con_guardia"][0]["estado"])
    chk("sint.guarda_tarde", por_f["guarda_tarde"][0]["estado"] == GUARDIA_TARDE,
        "esperaba GUARDIA_DESPUES, %s" % por_f["guarda_tarde"][0]["estado"])
    # el caso que mas importa: la guarda es de OTRO campo
    chk("sint.otro_campo", por_f["con_otro_campo"][0]["estado"] == SIN_GUARDIA,
        "una guarda sobre t->otro no protege t->count: %s"
        % por_f["con_otro_campo"][0]["estado"])
    # comentario y cadena NO cuentan
    chk("sint.comentario_ignorado", "en_comentario" not in por_f,
        "un acceso dentro de un comentario se conto")
    chk("sint.cadena_ignorada", "en_cadena" not in por_f,
        "un acceso dentro de una cadena se conto")

    # 2. el tipo de array se resuelve y la incognita se DECLARA
    chk("tipo.flexible", tipo_de_array("entries", CABECERAS) == "FLEXIBLE",
        tipo_de_array("entries", CABECERAS))
    # la respuesta incluye el nombre de la macro, no solo el valor: "FIJO:MAX_x=8" dice
    # mas que "FIJO:8". Mi primera expectativa pedia solo el 8 y fallo.
    chk("tipo.fijo", tipo_de_array("dpm_levels", CABECERAS) == "FIJO:MAX_REGULAR_DPM_NUMBER=8",
        tipo_de_array("dpm_levels", CABECERAS))
    chk("tipo.desconocido", tipo_de_array("no_existe", CABECERAS) == "NO_ENCONTRADO",
        "un array inexistente no debe inventarse: %s" % tipo_de_array("no_existe", CABECERAS))
    # AMBIGUO: el arbol declara `entries[]` flexible (tablas del PPT) y `entries[8]`
    # fijo (familias hwmgr). Elegir la primera era mi error y daba el tipo equivocado.
    cab_amb = ["struct f { int entries[8]; };\nstruct p { uint32_t c; int entries[]; };\n"]
    t_amb = tipo_de_array("entries", cab_amb)
    chk("tipo.ambiguo", t_amb.startswith("AMBIGUO"), "esperaba AMBIGUO, %s" % t_amb)
    chk("tipo.ambiguo.lista", "FLEXIBLE" in t_amb and "8" in t_amb,
        "AMBIGUO tiene que decir que hay una flexible y el valor 8: %s" % t_amb)
    chk("tipo.ambiguo.conteo", "2 declaraciones" in t_amb, t_amb)

    # 2b. un IDENTIFICADOR SUELTO no puede heredar la capacidad de un miembro
    #     homonimo. Referencia: fiji_smumgr.c:1038, donde `levels` es un local y
    #     el arbol tiene miembros `levels[SMU10_MAX_HARDWARE_POWERLEVELS]`.
    sit_loc = analiza(TEXTO_LOCAL, CABECERAS)
    chk("local.no_hereda", len(sit_loc) == 1 and
        sit_loc[0]["tipo_array"].startswith("IDENTIFICADOR_SUELTO"),
        "un local heredo la capacidad de un miembro homonimo: %r"
        % (sit_loc[0]["tipo_array"] if sit_loc else None))

    # 2c. el cortocircuito por `||`. El caso real es smu7_hwmgr.c:902, el
    #     filtro de duplicados de 120: con i == 0 el `||` evita evaluar
    #     dpm_levels[-1]. Sin esto, la herramienta se autoporrta.
    sit_or = analiza(
        'static int f(struct t *t, uint32_t i)\n{\n'
        '        if (i == 0 || t->levels[t->count - 1].v != t->entries[i].k)\n'
        '                return 1;\n'
        '        return 0;\n}\n', CABECERAS)
    chk("cortocircuito.marca", len(sit_or) == 1 and
        sit_or[0]["estado"] == CORTOCIRCUITO,
        "esperaba CORTOCIRCUITO, %s" % (sit_or[0]["estado"] if sit_or else None))

    # 3. casos REALES del corpus
    if sitios_reales is not None:
        idx = {}
        for s in sitios_reales:
            idx[(os.path.basename(s.get("fichero", "")), s["linea"])] = s
        for f, ln, fn, estado, expr in CASOS_REALES:
            k = (f, ln)
            if k not in idx:
                chk("real.%s:%d.existe" % (f, ln), False,
                    "no hay sitio en :%d de %s" % (ln, f))
                continue
            s = idx[k]
            chk("real.%s:%d.estado" % (f, ln), s["estado"] == estado,
                "esperaba %s, obtuve %s (guarda=%r)"
                % (estado, s["estado"], s["guarda"]))
            chk("real.%s:%d.funcion" % (f, ln), s["funcion"] == fn,
                "esperaba %s, obtuve %s" % (fn, s["funcion"]))
            chk("real.%s:%d.expr" % (f, ln), s["expr"].endswith("count-%d" % s["n"]),
                "expr=%r" % s["expr"])

    # 4. VALIDACION DE LA VALIDACION: si muevo la guarda DESPUES, el veredicto
    #    TIENE que cambiar. Una herramienta que no decide aqui no mide nada.
    a = analiza("""static int f(struct t *t){
        if (t->count < 1) return -1;
        return t->entries[t->count - 1].v; }
""", CABECERAS)
    b = analiza("""static int f(struct t *t){
        int v = t->entries[t->count - 1].v;
        if (t->count < 1) return -1;
        return v; }
""", CABECERAS)
    chk("valida.decide", a and b and a[0]["estado"] != b[0]["estado"],
        "con la guarda antes y despues sale lo mismo: %r / %r"
        % (a[0]["estado"] if a else None, b[0]["estado"] if b else None))

    print("  pruebas: %d   fallos: %d" % (n[0], len(fallos)))
    for f in fallos:
        print("    FALLO %s" % f)
    if not fallos:
        print("  RESULTADO OK - %d sitios, %d casos reales del corpus reproducidos"
              % (len(sit), len(CASOS_REALES) if sitios_reales is not None else 0))
        return "TOOL_VALIDATED"
    return "TOOL_BROKEN"


def recoge_ficheros(rutas):
    out = []
    for r in rutas:
        if os.path.isdir(r):
            for base, _, files in os.walk(r):
                for f in sorted(files):
                    if f.endswith(('.c', '.h')):
                        out.append(os.path.join(base, f))
        elif r.endswith(('.c', '.h')):
            out.append(r)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("rutas", nargs="*", default=[])
    ap.add_argument("--kernel")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    ap.add_argument("--json")
    a = ap.parse_args(argv)

    if a.version:
        print("count_guard.py %s" % VERSION)
        return 0

    rutas = list(a.rutas)
    if not rutas:
        K = a.kernel or os.environ.get("RX550_KERNEL", "")
        if K:
            rutas = [os.path.join(K, "drivers", "gpu", "drm", "amd", "pm", "powerplay")]
        else:
            aqui = os.path.dirname(os.path.abspath(__file__))
            raiz = os.path.dirname(aqui)
            cand = os.path.join(raiz, "RESEARCH", "kernelbuild", "linux-7.1.3",
                                "drivers", "gpu", "drm", "amd", "pm", "powerplay")
            rutas = [cand] if os.path.isdir(cand) else ["."]

    ficheros = [f for f in recoge_ficheros(rutas) if f.endswith('.c')]
    cabeceras = []
    for f in recoge_ficheros(rutas):
        if f.endswith('.h'):
            cabeceras.append(io.open(f, encoding='utf-8', errors='replace').read())

    todos = []
    for f in ficheros:
        txt = io.open(f, encoding='utf-8', errors='replace').read()
        for s in analiza(txt, cabeceras):
            s["fichero"] = f
            todos.append(s)

    if a.selftest:
        return 0 if selftest(todos) == "TOOL_VALIDATED" else 1

    if a.json:
        import json
        print(json.dumps({"version": VERSION, "total": len(todos), "sitios": todos}, indent=1))
    else:
        print("\n".join(informe(todos)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
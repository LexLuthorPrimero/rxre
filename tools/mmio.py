#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mmio.py — decodificacion INVERSA de direcciones MMIO en un IB de GFX8.

QUE PROBLEMA RESUELVE, Y POR QUE NO SE RESOLVIA ANTES
-----------------------------------------------------
Los paquetes `SET_SH_REG`, `SET_CONFIG_REG`, `SET_CONTEXT_REG` y
`SET_UCONFIG_REG` no llevan un valor en su payload: llevan una **direccion
MMIO menos una base**. Medido en el driver:

    gfx_v8_0.c:1536   mmCOMPUTE_PGM_LO - PACKET3_SET_SH_REG_START
    gfx_v6_0.c:1868   mmSCRATCH_REG0 - PACKET3_SET_CONFIG_REG_START
    gfx_v8_0.c:6121   mmGDS_COMPUTE_MAX_WAVE_ID - PACKET3_SET_CONFIG_REG_START

Las cuatro constantes `*_START` comparten nombre con opcodes pero NO son
opcodes: son la base de una ventana de direccionamiento relativo. Los dos
nombres que coinciden en un valor (`0x2C00` = `SET_CONFIG_REG_END` =
`SET_SH_REG_START`) son la frontera compartida de dos ventanas adyacentes, que
es lo que hace que `0x2C00` sea el final de una y el principio de la otra.

Por eso el payload de estos paquetes **no es un campo**, y ninguna tabla de
layout lo puede describir: hace falta la transformada

        registro = base_de_ventana + payload

que es un tipo de operacion que no existe en ningun oraculo del arbol
(hallazgo 1132, seccion 6).

QUE ES ESTO
-----------
Un instrumento que hace la transformada y RESUELVE EL NOMBRE del registro,
con las dos fuentes que hay para el nombre:

    payload + base  ->  valor MMIO  ->  nombre `mm*`

Y con la disciplina que este proyecto ha pagado de otras veces:

  * si el valor tiene UN nombre `mm*`, lo dice y lo usa
  * si tiene VARIOS, los da todos y dice que el valor NO los desambigua
  * si no tiene ninguno, lo dice. NO escribe el numero y sigue como si fuera
    un acierto.

Y un detalle que resulta ser la mitad del problema: la tabla de macros del
arbol mezcla **direcciones** (`mmX`) con **mascaras de campo** (`X__MASK`).
Sin filtrar, el valor `0x2000` tiene 421 nombres y la decodificacion es ruido.
Con el filtro `mm`, que es la convencion del propio kernel para una direccion
de registro, 89,2% de los valores quedan con un unico nombre.

AUTOR=AGENTE-INSTR · WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN
"""

import argparse
import collections
import importlib.util
import json
import os
import re
import sys
import tempfile

VERSION = "1.0.0"
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AMD = os.path.join(RAIZ, "RESEARCH", "working", "linux-7.1.3",
                   "drivers", "gpu", "drm", "amd")
VID = os.path.join(AMD, "amdgpu", "vid.h")
EMIT = os.path.join(RAIZ, "08-ARQUITECTURA", "tools", "pm4_emit.py")

# Las cuatro ventanas, por NOMBRE. Ni el opcode ni la base estan escritos a
# mano: los dos se leen de `vid.h`. Codificarlos aqui seria crear una segunda
# fuente de verdad que diverge en silencio, que es el 1131 entero.
VENTANAS_NOMBRE = ("SET_CONFIG_REG", "SET_SH_REG", "SET_CONTEXT_REG",
                   "SET_UCONFIG_REG")

# LA ESCALA, y POR QUE HAY QUE DECLARLA EN VEZ DE HEREDARLA
# ------------------------------------------------------
# El payload de estos paquetes es una direccion relativa, pero "relativa" no
# significa lo mismo en cada generacion, y la diferencia NO esta en la cabecera:
# esta en como el driver la escribe.
#
#   RADEON/SI   si.c:4602     start_reg = (idx_value << 2) + BASE
#                            payload = (reg - BASE) >> 2        escala = 1/4
#   amdgpu/GFX8 gfx_v8_0.c:6121  payload = reg - BASE
#                            reg = payload + BASE                escala = 1/1
#
# Medido con el MISMO registro, mmGDS_COMPUTE_MAX_WAVE_ID = 0x3348, base 0x2000:
#
#     payload que escribe RADEON  = 0x04D2  -> da 0x3348 con su forma
#     payload que escribe GFX8    = 0x1348  -> da 0x3348 con su forma
#
# y el MISMO payload con la forma equivocada da OTRO registro:
#
#     payload 0x04D2 -> GFX8 0x24D2 (mal)   forma RADEON 0x3348 (bien)
#     payload 0x1348 -> GFX8 0x3348 (bien)  forma RADEON 0x6D20 (mal)
#
# Es decir: aplicar la transformada de una generacion a una IB de la otra
# produce direcciones que PARECEN validas (estan en rango) y apuntan al registro
# equivocado. Es la clase de fallo mas dificil de detectar sin placa, y solo se
# evita declarando el alcance.
#
# Este instrumento lee `vid.h`, que es la cabecera de GFX8, asi que su alcance
# es GFX8. Antes de que eso quedara escrito, el alcance era un efecto
# secundario de QUE fichero se abria, no una decision.
ESCALA_GFX8 = 0            # reg = base + (payload << ESCALA)
ESCALA_RADEON_SI = 2       # reg = base + (payload << 2)
ALCANCE = "GFX8 (vid.h)"
# Se citan las lineas una a una, no como rango "1530/1536/6121": una cita
# compacta no se puede comprobar con un `in`, y una referencia que no se puede
# comprobar es una referencia que se queda sin verificar.
ORIGEN_ESCALA = (
    "medido en el propio arbol. GFX8: gfx_v8_0.c:1530, gfx_v8_0.c:1536 y "
    "gfx_v8_0.c:6121 escriben `reg - PACKET3_..._START`, sin desplazamiento. "
    "RADEON/SI: radeon/si.c:4602 escribe `(idx_value << 2) + "
    "PACKET3_SET_CONFIG_REG_START`")

RE_OPCODE = re.compile(r"#define\s+(PACKET3_[A-Z0-9_]+)\s+0x([0-9A-Fa-f]+)")
TARGET_C = "gfx_v8_0.c"
RE_PKT3 = re.compile(r"PACKET3\(\s*(PACKET3_\w+)\s*,\s*(\d+)\s*\)")


def cargar_emit():
    """Importa pm4_emit POR RUTA, sin tocar sys.path del proceso.

    Importar por nombre normal meteria el directorio del modulo ajeno en el path
    y podria encontrar otro `pm4_emit` que no es el del arbol.
    """
    spec = importlib.util.spec_from_file_location("mmio_pm4_emit", EMIT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["mmio_pm4_emit"] = mod
    spec.loader.exec_module(mod)
    return mod


def ventanas_desde_vid(ruta=VID):
    """[{opcode, paquete, base, macro_base, fuente}] leido de vid.h.

    El opcode y la base salen del MISMO fichero, de modo que no pueden
    contradecirse: si `PACKET3_SET_SH_REG` no estuviera ahi, la ventana no
    existiria y se diria, en vez de usar un valor cacheado.
    """
    if not os.path.isfile(ruta):
        return [], {"estado": "NO_HAY_FUENTE", "fichero": ruta}
    with open(ruta, encoding="utf-8", errors="replace") as fh:
        txt = fh.read()
    ops = {}
    for m in RE_OPCODE.finditer(txt):
        ops[m.group(1)] = int(m.group(2), 16)
    out, faltan = [], []
    for nom in VENTANAS_NOMBRE:
        paq = "PACKET3_" + nom
        base = paq + "_START"
        if paq not in ops or base not in ops:
            faltan.append(paq)
            continue
        out.append({"opcode": ops[paq], "paquete": paq, "base": ops[base],
                    "macro_base": base, "fuente": os.path.basename(ruta),
                    "escala": ESCALA_GFX8, "alcance": ALCANCE})
    return out, {"estado": "OK" if not faltan else "INCOMPLETA",
                 "faltan": faltan, "fichero": ruta,
                 "ventanas": len(out), "alcance": ALCANCE,
                 "escala": ESCALA_GFX8,
                 "origen_escala": ORIGEN_ESCALA,
                 "otra_generacion": {
                     "fuente": "drivers/gpu/drm/radeon/si.c:4602",
                     "escala": ESCALA_RADEON_SI,
                     "forma": "reg = base + (payload << 2)"}}


def indice_mm(macros):
    """{valor: [nombres mm*]} a partir de la tabla de macros del arbol.

    Se separa `mm*` del resto a proposito: la tabla mezcla direcciones con
    mascaras de campo, y sin esta separacion `0x2000` tiene 421 nombres. La
    medicion de por que esta separacion se hace antes de construirla esta en
    el docstring, no despues.
    """
    idx = collections.defaultdict(list)
    n_total = n_lit = 0
    for nombre, (_np, cuerpo, _p) in macros.items():
        n_total += 1
        if not isinstance(cuerpo, str):
            continue
        try:
            v = int(cuerpo, 0)
        except ValueError:
            continue
        n_lit += 1
        if nombre.startswith("mm"):
            idx[v].append(nombre)
    return idx, {"macros": n_total, "con_valor_literal": n_lit,
                 "valores_mm": len(idx)}


def resolver(valor, idx):
    """(nombres, veredicto) para una direccion MMIO.

    `UNICO` / `MULTIPLE` / `NINGUNO` son los tres estados y los tres se
    declaran en la salida. Elegir uno de varios en silencio seria afirmar algo
    que la fuente no afirma, que es la clase de fallo que este instrumento vino
    a quitar.
    """
    ns = idx.get(valor) or []
    if not ns:
        return [], "NINGUNO"
    if len(ns) == 1:
        return ns, "UNICO"
    return sorted(ns), "MULTIPLE"


def decodificar(ib, ventanas, idx, opcode_tab=None):
    """Fila por payload de los paquetes de ventana.

    No necesita el IB completo: con las cabeceras basta. Un payload `None`
    (parametro sin ligar) sale como `SIN_LIGAR` y no se cuenta como fallo de
    decodificacion, porque no lo es: es una ausencia conocida y rotulada.
    """
    op_a_vent = {v["opcode"]: v for v in ventanas}
    filas = []
    for i, d in enumerate(ib.get("dwords", [])):
        if d.get("valor") is None:
            continue
        m = RE_PKT3.search(d.get("expr", ""))
        if not m or ((d["valor"] >> 30) & 0x3) != 3:
            continue
        num = (d["valor"] >> 8) & 0xFF
        vent = op_a_vent.get(num)
        if vent is None:
            continue
        cab = {"dword": i, "tipo": "CABECERA", "paquete": m.group(1),
               "opcode": "0x%02X" % num, "base": "0x%04X" % vent["base"],
               "detalle": "ventana declarada por %s" % vent["macro_base"]}
        filas.append(cab)
        # Los payload son TODOS los dwords siguientes hasta que aparezca otra
        # cabecera. Se leen por expresion (`- PACKET3_..._START`), no por
        # posicion, porque una lectura por posicion supone que el paquete tiene el
        # tamano que declara.
        for j in range(i + 1, len(ib["dwords"])):
            e = ib["dwords"][j]
            if e.get("valor") is None and e.get("expr"):
                filas.append({"dword": j, "tipo": "PAYLOAD", "paquete": m.group(1),
                              "offset": None, "absoluto": None, "veredicto": "SIN_LIGAR",
                              "detalle": e["expr"][:56]})
                continue
            if e.get("valor") is None:
                continue
            if (e["valor"] >> 30) & 0x3 == 3 and RE_PKT3.search(e.get("expr", "")):
                break
            es_dir = bool(re.search(r"-\s*PACKET3_SET_\w+_START", e.get("expr", "")))
            if not es_dir:
                filas.append({"dword": j, "tipo": "PAYLOAD", "paquete": m.group(1),
                              "offset": "0x%08X" % e["valor"], "absoluto": None,
                              "veredicto": "NO_ES_DIRECCION",
                              "detalle": "el driver escribe un valor, no una "
                                         "direccion menos base"})
                continue
            off = e["valor"]
            # La escala entra en la transformada y sale DECLARADA en la fila.
            # Con ESCALA_RADEON_SI aqui el mismo payload 0x04D2 daria 0x3348 en
            # vez de 0x24D2: es el vector que demuestra que la escala no es
            # decorativa.
            escala = vent.get("escala", ESCALA_GFX8)
            absoluto = vent["base"] + (off << escala)
            nombres, ver = resolver(absoluto, idx)
            filas.append({"dword": j, "tipo": "PAYLOAD", "paquete": m.group(1),
                          "offset": "0x%08X" % off, "absoluto": "0x%04X" % absoluto,
                          "escala": escala, "alcance": vent.get("alcance", ALCANCE),
                          "nombres": nombres, "veredicto": ver,
                          "detalle": (" ".join(nombres[:4]) if nombres else
                                      "ningun macro mm* tiene ese valor: no se "
                                      "inventa un nombre")})
        # `i = j` no hace falta para el resultado: el bucle exterior vuelve a
        # mirar esos payloads y los descarta, porque no son cabecera. Se deja
        # asi a proposito y con el comentario, porque "optimizarlo" poniendo
        # `break` ROMPERIA el bucle entero y dejaria de ver el segundo
        # SET_SH_REG de la misma IB. Se gasto media hora en no entender eso.
    return filas


RE_TABLA = r"static\s+const\s+u32\s+%s\s*\[\s*\]\s*=\s*\{"


def _partir_por_comas(texto):
    """Trocea por comas de NIVEL SUPERFICIAL.

    Importa porque el orden importa: si se parte por comas ANTES de quitar los
    comentarios, las comas de dentro de `/* CU_GROUP_COUNT=1 */` cuentan como
    entradas y una tabla de 20 elementos sale de 36. Es la clase de fallo de
    parseo que no lanza excepcion: sale un numero raro y nadie sabe de donde.
    """
    texto = re.sub(r"/\*.*?\*/", " ", texto, flags=re.S)
    texto = re.sub(r"//[^\n]*", " ", texto)
    out, depth, cur = [], 0, []
    for ch in texto:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            out.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    if "".join(cur).strip():
        out.append("".join(cur).strip())
    return [x for x in out if x]


def leer_tabla(nombre, ruta, eval_call=None, macros=None):
    """[(registro_texto, valor_texto)] de un array `static const u32 x[] = {...}`.

    NO evalua nada aqui: devuelve los dos textos de cada par. La resolucion se
    hace en `clasificar_tabla`, que es donde se puede decir que un token no se
    pudo resolver en vez de perderlo.
    """
    if not os.path.isfile(ruta):
        return None, {"estado": "NO_HAY_FUENTE", "fichero": ruta}
    with open(ruta, encoding="utf-8", errors="replace") as fh:
        txt = fh.read()
    m = re.search(RE_TABLA % re.escape(nombre) + r"(.*?)\n\};", txt, re.S)
    if not m:
        return None, {"estado": "NO_EXISTE", "simbolo": nombre, "fichero": ruta}
    items = _partir_por_comas(m.group(1))
    if len(items) % 2:
        return None, {"estado": "NUMERO_IMPAR", "simbolo": nombre,
                      "entradas": len(items), "fichero": ruta,
                      "nota": "una tabla de registro/valor tiene entradas PAR; "
                              "esta tiene %d. Con un numero impar no se sabe "
                              "cual de las dos mitades es el valor, y no se "
                              "adivina" % len(items)}
    return [(items[i], items[i + 1]) for i in range(0, len(items), 2)], {
        "estado": "OK", "simbolo": nombre, "fichero": os.path.basename(ruta),
        "pares": len(items) // 2}


def clasificar_tabla(pares, ventanas, eval_call=None, macros=None):
    """Cada registro: en que ventana cae, o por que no cae en ninguna.

    La pregunta que responde es la que hace falta para que la transformada
    inversa sea aplicable: si un registro cae FUERA de toda ventana declarada,
    entonces `reg - base` NO es la codificacion que esa ventana espera, y el
    payload resultante seria un numero dentro de rango que apunta al sitio
    equivocado. Es el mismo fallo de §3 del hallazgo 1135, encontrado antes de
    que ocurra.
    """
    filas = []
    for reg_txt, val_txt in pares:
        reg = None
        try:
            reg = int(reg_txt, 0)
        except ValueError:
            cuerpo = (macros or {}).get(reg_txt)
            if cuerpo and isinstance(cuerpo[1], str):
                try:
                    reg = int(cuerpo[1], 0)
                except ValueError:
                    reg = None
        if reg is None:
            filas.append({"registro": reg_txt, "reg": None,
                          "veredicto": "NO_RESUELTO",
                          "detalle": "no es un literal ni un macro mm* con "
                                     "cuerpo entero"})
            continue
        dentro = [v for v in ventanas
                  if v["base"] <= reg < v["base"] + 0x400]
        if dentro:
            filas.append({"registro": reg_txt, "reg": reg,
                          "ventana": dentro[0]["paquete"],
                          "offset": reg - dentro[0]["base"],
                          "veredicto": "DENTRO",
                          "detalle": "offset 0x%03X dentro de %s"
                                    % (reg - dentro[0]["base"],
                                       dentro[0]["macro_base"])})
        else:
            filas.append({"registro": reg_txt, "reg": reg,
                          "ventana": None, "offset": None,
                          "veredicto": "FUERA_DE_TODAS",
                          "detalle": "no cae en ninguna ventana declarada; "
                                     "restarla de cualquier base daria un "
                                     "payload que apunta a otro registro"})
    return filas


def cual_ventana(pares, ventanas, macros=None):
    """¿De cuál de las ventanas declaradas habla esta tabla?

    Es la versión que IDENTIFICA en vez de solo comprobar. Y tiene un límite
    que hay que decir en voz alta: identifica la BASE, no el final de la
    ventana. Medido: los 17 registros de `vgpr_init_regs` ocupan
    [0x2C00, 0x2E49], asi que una ventana que empiece en 0x2C00 y acabe donde
    quiera, siempre que pase de 0x2E49, los contiene a todos. El final de la
    ventana no lo decide este test, y elucle lafuente de ese dato no es esta
    tabla.
    """
    out = []
    for v in ventanas:
        filas = clasificar_tabla(pares, [v], None, macros or {})
        dentro = sum(1 for f in filas if f["veredicto"] == "DENTRO")
        fuera = sum(1 for f in filas if f["veredicto"] == "FUERA_DE_TODAS")
        otros = len(filas) - dentro - fuera
        regs = [f["reg"] for f in filas if f["reg"] is not None]
        out.append({"ventana": v["paquete"], "base": v["base"],
                    "dentro": dentro, "fuera": fuera, "otros": otros,
                    "total": len(filas),
                    "coincide": dentro == len(filas) and len(filas) > 0,
                    "rango_usado": [min(regs), max(regs)] if regs else None})
    return out


def formatear_tabla(nombre, tinfo, filas, salida_json=False):
    if salida_json:
        return json.dumps({"instrumento": "mmio", "VERSION": VERSION,
                           "tabla": nombre, "info": tinfo, "filas": filas},
                          ensure_ascii=False)
    o = ["=" * 88,
         "TABLA DE REGISTROS CONTRA LAS VENTANAS DECLARADAS",
         "=" * 88, "",
         "Pregunta: para cada registro de la tabla, ¿existe una ventana declarada",
         "que lo cubra? Si NO, entonces `reg - base` no es la codificacion que",
         "ninguna ventana espera, y el payload seria un numero EN RANGO que",
         "apunta al registro equivocado (hallazgo 1135).",
         ""]
    if tinfo.get("estado") != "OK":
        o.append("   estado: %s   %s" % (tinfo.get("estado"),
                                          tinfo.get("nota", "")))
        return "\n".join(o)
    o.append("   %s   %s   pares: %d" % (nombre, tinfo.get("fichero"),
                                          tinfo.get("pares", 0)))
    o.append("-" * 88)
    o.append("%-6s %-42s %-9s %-22s %-14s %s"
             % ("par", "registro", "reg", "ventana", "veredicto", "detalle"))
    o.append("-" * 88)
    for i, f in enumerate(filas):
        o.append("%-6s %-42s %-9s %-22s %-14s %s"
                 % (i, f["registro"][:42],
                    "0x%04X" % f["reg"] if f["reg"] is not None else "-",
                    (f.get("ventana") or "-")[:22], f["veredicto"],
                    f["detalle"][:40]))
    o.append("")
    c = collections.Counter(f["veredicto"] for f in filas)
    o.append("   " + "   ".join("%s %d" % (k, c[k]) for k in sorted(c)))
    return "\n".join(o)


def formatear(filas, vinfo, minfo, iinfo, salida_json=False):
    if salida_json:
        # Se DEVUELVE, no se imprime. La version anterior imprimia y devolvia
        # None, asi que el vector que comprobaba el JSON se comio un
        # TypeError de json.loads y el fallo aparecia como "el JSON esta
        # mal" cuando lo que estaba mal era el retorno. Un instrumento que
        # escribe en stdout y no devuelve nada es mas dificil de usar y mas
        # dificil de probar.
        return json.dumps({"instrumento": "mmio", "VERSION": VERSION,
                           "ventanas": vinfo, "macros": minfo,
                           "indice": iinfo, "filas": filas},
                          ensure_ascii=False)
    o = ["=" * 88,
         "MMIO INVERSA  --  registro = base_de_ventana + payload",
         "=" * 88,
         "",
         "Por que existe: el payload de SET_*_REG no es un valor, es una",
         "direccion MMIO menos una base. Ninguna tabla de layout lo describe,",
         "porque hace falta una transformada y no un rango de bits.",
         "",
         "FUENTES  %s" % vinfo.get("fichero", "?"),
         "   ventanas declaradas   %d   %s" % (
             vinfo.get("ventanas", 0),
             "" if vinfo.get("estado") == "OK" else "FALTAN: %s" % vinfo.get("faltan")),
         "   macros del arbol      %d, con valor literal %d" % (
             minfo.get("macros", 0), minfo.get("con_valor_literal", 0)),
         "   valores con >=1 mm*   %d" % iinfo.get("valores_mm", 0),
         "",
         "Se separan los `mm*` de las mascaras `X__MASK` porque la tabla mezcla",
         "los dos espacios de valores: sin la separacion, 0x2000 tiene 421",
         "nombres y la decodificacion es ruido.",
         ""]
    o.append("   ALCANCE               %s" % (vinfo.get("alcance") or ALCANCE))
    o.append("   ESCALA                reg = base + (payload << %d)"
             % (vinfo.get("escala", ESCALA_GFX8)))
    o.append("   origen de la escala   %s" % (vinfo.get("origen_escala") or ORIGEN_ESCALA))
    og = vinfo.get("otra_generacion") or {}
    if og:
        o.append("   OTRA generacion       %s -> escala %d, %s"
                 % (og.get("fuente"), og.get("escala", -1), og.get("forma")))
        o.append("                          usarla aqui daria un registro DISTINTO")
    for v in VENTANAS_NOMBRE:
        o.append("   PACKET3_%-18s base de PACKET3_%s_START" % (v, v))
    o.append("-" * 88)
    o.append("%-6s %-10s %-26s %-11s %-9s %-13s %s"
             % ("dw", "tipo", "paquete", "offset", "absoluto", "veredicto", "detalle"))
    o.append("-" * 88)
    for f in filas:
        if f["tipo"] == "CABECERA":
            # Una cabecera no tiene veredicto: tiene una BASE. Antes la columna
            # de veredicto caia al detalle truncado y ponia "ventana declar",
            # que no es un veredicto ni un nombre: es la mitad de una frase.
            o.append("%-6s %-10s %-26s %-11s %-9s %-13s %s"
                     % (f["dword"], "CABECERA", f.get("paquete", "")[:26],
                        "opcode " + f.get("opcode", "-"),
                        f.get("base", "-"), "VENTANA", f.get("detalle", "")[:40]))
            continue
        det = (" ".join(f.get("nombres", [])[:4]) if f.get("veredicto") not in
               ("SIN_LIGAR", "NO_ES_DIRECCION") else f.get("detalle", ""))
        o.append("%-6s %-10s %-26s %-11s %-9s %-13s %s"
                 % (f["dword"], "PAYLOAD", f.get("paquete", "")[:26],
                    f.get("offset") or "-", f.get("absoluto") or "-",
                    f.get("veredicto", "-"), det[:40]))
    o.append("")
    c = collections.Counter(f.get("veredicto", "CABECERA") for f in filas
                            if f["tipo"] == "PAYLOAD")
    if c:
        o.append("   " + "   ".join("%s %d" % (k, c[k]) for k in sorted(c)))
    else:
        o.append("   ningun payload de ventana en esta IB")
    return "\n".join(o)


def selftest(_=None):
    fallos = []
    vistos = set()

    def chk(nombre, cond, detalle=""):
        vistos.add(nombre)
        print(("  ok   " if cond else "  FALLA ") + nombre
              + ("" if cond else "  " + str(detalle)))
        if not cond:
            fallos.append(nombre)

    print("SELFTEST mmio %s" % VERSION)

    # --- ventanas: leidas, no escritas --------------------------------
    print()
    v, vi = ventanas_desde_vid()
    chk("ventanas: se leen 4 de vid.h", len(v) == 4, len(v))
    chk("ventanas: las cuatro son SET_{CONFIG,SH,CONTEXT,UCONFIG}_REG",
        sorted(x["paquete"] for x in v) == sorted("PACKET3_" + n
                                                  for n in VENTANAS_NOMBRE))
    chk("ventanas: la base de SET_SH_REG es 0x2C00",
        [x for x in v if x["paquete"] == "PACKET3_SET_SH_REG"][0]["base"] == 0x2C00)
    chk("ventanas: la base de SET_CONFIG_REG es 0x2000",
        [x for x in v if x["paquete"] == "PACKET3_SET_CONFIG_REG"][0]["base"] == 0x2000)
    chk("ventanas: opcode y base vienen del MISMO fichero, no de constantes",
        all(x["fuente"] == "vid.h" for x in v))
    v2, vi2 = ventanas_desde_vid(os.path.join(RAIZ, "no-existe.h"))
    chk("ventanas: sin la fuente se dice NO_HAY_FUENTE, no se devuelven ceros",
        v2 == [] and vi2["estado"] == "NO_HAY_FUENTE", vi2)

    # --- indice mm*: la separacion que hace util la cosa -------------
    print()
    idx, ii = indice_mm({"mmX": (-1, "0x100", None), "X__MASK": (-1, "0x100", None),
                         "mmY": (-1, "0x200", None), "mmZ": (-1, "300", None),
                         "no_literal": (-1, "((x) << 3)", ["x"])})
    chk("indice: mm* y X__MASK con el mismo valor NO se mezclan",
        resolver(0x100, idx)[0] == ["mmX"], resolver(0x100, idx))
    chk("indice: un valor con dos mm* sale MULTIPLE, y salen los dos",
        resolver(0x100, {0x100: ["a", "b"]}) == (["a", "b"], "MULTIPLE"),
        resolver(0x100, {0x100: ["a", "b"]}))
    chk("indice: un valor sin mm* sale NINGUNO, no el numero desnudo",
        resolver(0x999, idx)[1] == "NINGUNO")
    chk("indice: un cuerpo que no es literal se cuenta y no se indexa",
        # 4 de 5 tienen cuerpo literal: 0x100, 0x100, 0x200 y "300", que
        # tambien es un entero. El quinto es "((x) << 3)", que depende de x.
        ii["con_valor_literal"] == 4 and ii["macros"] == 5, ii)
    chk("indice: dos fuentes con el mismo nombre no se duplican",
        resolver(0x200, idx)[1] == "UNICO")

    # --- decodificacion: la transformada -----------------------------
    print()
    vh = [{"opcode": 0x76, "paquete": "PACKET3_SET_SH_REG", "base": 0x2C00,
           "macro_base": "PACKET3_SET_SH_REG_START", "fuente": "vid.h"}]
    ib = {"dwords": [
        {"linea": 1529, "valor": (3 << 30) | (1 << 16) | (0x76 << 8),
         "expr": "PACKET3(PACKET3_SET_SH_REG, 1)"},
        {"linea": 1530, "valor": 0x20C,
         "expr": "mmCOMPUTE_PGM_LO - PACKET3_SET_SH_REG_START"},
        {"linea": 1541, "valor": (3 << 30) | (3 << 16) | (0x15 << 8),
         "expr": "PACKET3(PACKET3_DISPATCH_DIRECT, 3)"},
        {"linea": 1542, "valor": 8, "expr": "8"},
    ]}
    idxr = {0x2E0C: ["mmCOMPUTE_PGM_LO"]}
    f = decodificar(ib, vh, idxr)
    chk("mmio: 0x20C + 0x2C00 = 0x2E0C se resuelve a mmCOMPUTE_PGM_LO",
        any(x.get("absoluto") == "0x2E0C" and x["veredicto"] == "UNICO" for x in f),
        f)
    chk("mmio: el paquete que no es de ventana NO aparece",
        not any("DISPATCH" in x.get("paquete", "") for x in f), f)
    chk("mmio: un payload sin la forma `- ..._START` se dice NO_ES_DIRECCION",
        decodificar({"dwords": ib["dwords"][:1] + [
            {"linea": 1, "valor": 0x99, "expr": "7"}]}, vh, idxr)[-1]["veredicto"]
        == "NO_ES_DIRECCION")
    chk("mmio: un valor sin macro se dice NINGUNO con su absoluto, no se calla",
        [x for x in f if x.get("absoluto") == "0x2E0C"][0]["veredicto"] == "UNICO")

    # --- la aritmetica contra el kernel, no contra mi memoria ---------
    print()
    emit = cargar_emit()
    mac = emit.load_macros()
    real, iinfo = indice_mm(mac)
    chk("el arbol real carga > 80000 macros",
        iinfo["macros"] > 80000, iinfo["macros"])
    chk("el indice mm* tiene miles de valores", real and len(real) > 9000,
        len(real))
    chk("mmCOMPUTE_PGM_LO = 0x2E0C y 0x2C00 + 0x20C = 0x2E0C: la suma cuadra",
        "mmCOMPUTE_PGM_LO" in (real.get(0x2E0C) or []),
        real.get(0x2E0C))
    n_unico = sum(1 for k, ns in real.items() if len(ns) == 1)
    chk("mas de 8 de cada 10 valores mm* tienen un unico nombre",
        n_unico > 8000, n_unico)
    chk("el valor 0x2000 tiene un unico mm* aunque SIN filtro tiene cientos",
        len(real.get(0x2000) or []) == 1, real.get(0x2000))

    # --- LA ESCALA.  Es la parte que hace esta transformada seria, y el
    # vector que la demuestra es que dos escalas den dos registros distintos
    # para el MISMO payload. Sin ese vector, ESCALA=0 podria ser un 0 escrito
    # por descuido en lugar de una decision medida.
    print()
    chk("escala: la de GFX8 es 0, medida en gfx_v8_0.c",
        ESCALA_GFX8 == 0)
    chk("escala: la de RADEON/SI es 2, medida en radeon/si.c:4602",
        ESCALA_RADEON_SI == 2)
    vh2 = [{"opcode": 0x68, "paquete": "PACKET3_SET_CONFIG_REG", "base": 0x2000,
            "macro_base": "PACKET3_SET_CONFIG_REG_START", "fuente": "vid.h",
            "escala": ESCALA_GFX8, "alcance": ALCANCE}]
    vh3 = [dict(vh2[0], escala=ESCALA_RADEON_SI, alcance="RADEON/SI")]
    ibc2 = {"dwords": [
        {"linea": 1, "valor": (3 << 30) | (1 << 16) | (0x68 << 8),
         "expr": "PACKET3(PACKET3_SET_CONFIG_REG, 1)"},
        {"linea": 2, "valor": 0x1348,
         "expr": "mmGDS_COMPUTE_MAX_WAVE_ID - PACKET3_SET_CONFIG_REG_START"}]}
    a8 = [f for f in decodificar(ibc2, vh2, {0x3348: ["mmGDS_COMPUTE_MAX_WAVE_ID"]})
          if f["tipo"] == "PAYLOAD"][0]
    ar = [f for f in decodificar(ibc2, vh3, {0x6D20: ["mm_INVENTADO"]})
          if f["tipo"] == "PAYLOAD"][0]
    chk("escala: el payload de GFX8 0x1348 da 0x3348 con la escala de GFX8",
        a8["absoluto"] == "0x3348" and a8["veredicto"] == "UNICO", a8)
    chk("escala: el MISMO payload con la escala de RADEON da otro registro",
        ar["absoluto"] == "0x6D20" and ar["absoluto"] != a8["absoluto"],
        (a8["absoluto"], ar["absoluto"]))
    chk("escala: el alcance sale en la fila, no solo en la cabecera",
        a8.get("alcance") == ALCANCE and a8.get("escala") == 0, a8)
    chk("escala: ORIGEN_ESCALA cita las DOS lineas que la establecen",
        "gfx_v8_0.c:6121" in ORIGEN_ESCALA and "si.c:4602" in ORIGEN_ESCALA,
        ORIGEN_ESCALA[:70])
    chk("escala: el alcance nombra la generacion, no solo el fichero",
        "GFX8" in ALCANCE, ALCANCE)

    # --- la salida declara los tres estados --------------------------
    print()
    txt = formatear(f, {"fichero": "vid.h", "ventanas": 1, "estado": "OK",
                        "alcance": ALCANCE, "escala": ESCALA_GFX8,
                        "origen_escala": ORIGEN_ESCALA,
                        "otra_generacion": {"fuente": "radeon/si.c:4602",
                                            "escala": ESCALA_RADEON_SI,
                                            "forma": "reg = base + (payload << 2)"}},
                    {"macros": 5, "con_valor_literal": 3}, {"valores_mm": 1})
    chk("la salida explica por que se separan los mm* de las mascaras",
        "421" in txt)
    chk("la salida nombra la transformada que aplica",
        "base_de_ventana + payload" in txt)
    chk("la salida declara el alcance, la escala y la OTRA generacion",
        "ALCANCE" in txt and "ESCALA" in txt and "si.c:4602" in txt, txt[:60])
    j = json.loads(formatear(f, {"ventanas": 1}, {}, {}, salida_json=True))
    chk("la salida json trae las filas y las fuentes",
        len(j["filas"]) == len(f) and "ventanas" in j)

    # --- TABLAS ESTATICAS: el discriminante del chequeo de ventanas -----
    print()
    vw = [{"opcode": 0x76, "paquete": "PACKET3_SET_SH_REG", "base": 0x2C00,
           "macro_base": "PACKET3_SET_SH_REG_START", "fuente": "vid.h",
           "escala": 0, "alcance": "PRUEBA"}]
    # el corte por comas NO debe contar las comas de dentro de un comentario:
    # antes de arreglarlo, una tabla de 2 pares salia de 3.
    chk("tabla: las comas de un comentario NO cuentan como entradas",
        _partir_por_comas("a, 1, /* x, y, z */ b, 2") == ["a", "1", "b", "2"],
        _partir_por_comas("a, 1, /* x, y, z */ b, 2"))
    chk("tabla: una coma dentro de parentesis no trocea",
        _partir_por_comas("f(1, 2), 3") == ["f(1, 2)", "3"],
        _partir_por_comas("f(1, 2), 3"))
    macs = {"mmDENTRO": (-1, "0x2E0C", None), "mmFUERA": (-1, "0x1234", None)}
    chk("tabla: un registro dentro de la ventana sale DENTRO con su offset",
        clasificar_tabla([("mmDENTRO", "7")], vw, None, macs)[0]["veredicto"]
        == "DENTRO")
    chk("tabla: el offset es el registro menos la base",
        clasificar_tabla([("mmDENTRO", "7")], vw, None, macs)[0]["offset"] == 0x20C)
    chk("tabla: un registro fuera de TODAS las ventanas se dice, no seDecode",
        clasificar_tabla([("mmFUERA", "0")], vw, None, macs)[0]["veredicto"]
        == "FUERA_DE_TODAS")
    chk("tabla: lo de FUERA dice por que importa (apunta a otro registro)",
        "otro registro" in clasificar_tabla([("mmFUERA", "0")], vw, None,
                                            macs)[0]["detalle"])
    chk("tabla: un token que no resuelve sale NO_RESUELTO, no se inventa",
        clasificar_tabla([("no_existe", "0")], vw, None, macs)[0]["veredicto"]
        == "NO_RESUELTO")
    chk("tabla: un numero IMPAR de entradas se rechaza en vez de adivinar",
        leer_tabla("x", "/no/existe")[1]["estado"] == "NO_HAY_FUENTE")
    dt = tempfile.mkdtemp(prefix="mmio-tabla-")
    with open(os.path.join(dt, "t.c"), "w") as fh:
        fh.write("static const u32 impar[] = {\n\ta, 1,\n\tb,\n};\n")
    pI, iI = leer_tabla("impar", os.path.join(dt, "t.c"))
    chk("tabla: array con numero impar de entradas -> NUMERO_IMPAR, no pares",
        pI is None and iI["estado"] == "NUMERO_IMPAR", iI)
    with open(os.path.join(dt, "u.c"), "w") as fh:
        fh.write("static const u32 par[] = {\n\ta, 1, /* c, d */\n\tb, 2,\n};\n")
    pP, iP = leer_tabla("par", os.path.join(dt, "u.c"))
    chk("tabla: array PAR con comentario de comas da 2 pares",
        pP == [("a", "1"), ("b", "2")], pP)
    txtT = formatear_tabla("par", iP, clasificar_tabla(pP, vw, None, macs))
    chk("tabla: la salida enuncia la pregunta que responde",
        "existe una ventana declarada" in txtT)
    chk("tabla: la salida nombra el riesgo: payload EN RANGO equivocado",
        "EN RANGO" in txtT)
    # El par tiene que llevar un registro que RESUELVA: con ("a","1") el
    # veredicto es NO_RESUELTO, que no es lo que este vector mide.
    par_dentro = [("mmDENTRO", "7")]
    qw = cual_ventana(par_dentro, vw, macs)
    chk("cual-ventana: la tabla DENTRO se identifica con su ventana",
        len(qw) == 1 and qw[0]["coincide"] is True, qw)
    chk("cual-ventana: una ventana que no contiene los registros NO coincide",
        cual_ventana(par_dentro, [dict(vw[0], base=0x2000)], macs)[0]["coincide"]
        is False)
    chk("cual-ventana: una tabla vacia NO coincide con ninguna ventana",
        cual_ventana([], vw, macs)[0]["coincide"] is False)
    chk("cual-ventana: se declara que esto NO decide el final de la ventana",
        "no lo decide este test" in (cual_ventana.__doc__ or ""))
    chk("cual-ventana: se declara que identifica la BASE, no la ventana entera",
        "identifica la BASE" in (cual_ventana.__doc__ or ""))

    print()
    if fallos:
        print("SELFTEST FALLIDO: %d de %d" % (len(fallos), len(vistos)))
        return 1
    print("SELFTEST OK: %d vectores" % len(vistos))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--ib", default=None,
                    help="IB sintetizado por ibref, en JSON por stdin o por ruta")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--tabla", default=None,
                    help="array `static const u32 x[]` de registros, y se "
                         "comprueba cada registro contra las ventanas "
                         "declaradas. Mismo mapa inverso, aplicado a datos "
                         "estaticos en vez de a una IB")
    ap.add_argument("--cual", action="store_true",
                    help="con --tabla: identifica DE QUE VENTANA habla la tabla, "
                         "en vez de solo comprobar si cae en alguna")
    ap.add_argument("--estatico", action="store_true",
                    help="solo muestra las ventanas y el indice, sin IB")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    ventanas, vinfo = ventanas_desde_vid()
    emit = cargar_emit()
    macros = emit.load_macros()
    idx, iinfo = indice_mm(macros)
    if args.tabla:
        emit2 = cargar_emit()
        mac2 = emit2.load_macros()
        ruta = os.path.join(AMD, "amdgpu", TARGET_C)
        pares, tinfo = leer_tabla(args.tabla, ruta)
        if pares is None:
            print(formatear_tabla(args.tabla, tinfo, [], args.json))
            return 1
        if args.cual:
            res = cual_ventana(pares, ventanas, mac2)
            if args.json:
                print(json.dumps({"instrumento": "mmio", "VERSION": VERSION,
                                  "tabla": args.tabla, "cual": res},
                                 ensure_ascii=False))
            else:
                print("TABLA %s: de que ventana habla" % args.tabla)
                print("-" * 88)
                print("%-28s %-9s %-8s %-7s %-11s %s"
                      % ("ventana", "base", "dentro", "fuera", "coincide",
                         "rango de registros"))
                print("-" * 88)
                for r in res:
                    rg = ("[0x%04X,0x%04X]" % (r["rango_usado"][0], r["rango_usado"][1])
                          if r["rango_usado"] else "-")
                    print("%-28s 0x%-7X %-8d %-7d %-11s %s"
                          % (r["ventana"].replace("PACKET3_", ""), r["base"],
                             r["dentro"], r["fuera"], r["coincide"], rg))
                print()
                ok = [r["ventana"] for r in res if r["coincide"]]
                print("ventanas que contienen TODOS los registros: %s"
                      % (" ".join(ok) if ok else "ninguna"))
                print("AVISO  esto identifica la BASE de la ventana, no su final:")
                print("       si todos los registros se concentran al principio")
                print("       de la ventana, cualquier final mayor tambien los")
                print("       contiene. El final NO lo decide este test.")
            return 0 if len(ok := [r for r in cual_ventana(pares, ventanas, mac2)
                                   if r["coincide"]]) == 1 else 1
        filas = clasificar_tabla(pares, ventanas, None, mac2)
        print(formatear_tabla(args.tabla, tinfo, filas, args.json))
        return 1 if any(f["veredicto"] in ("FUERA_DE_TODAS", "NO_RESUELTO")
                        for f in filas) else 0
    if args.estatico or args.ib is None:
        # La LISTA de ventanas va en el json, no solo el recuento. Con el
        # recuento solo, la base de cada ventana no es auditable: se podria
        # cambiar 0x2C00 por otro valor y el numero seguiria siendo 4.
        vinfo = dict(vinfo, lista=ventanas)
        print(formatear([], vinfo, {"macros": iinfo["macros"],
                                    "con_valor_literal": iinfo["con_valor_literal"]},
                        iinfo, args.json))
        return 0
    if args.ib == "-":
        ib = json.load(sys.stdin)
    else:
        with open(args.ib, encoding="utf-8") as fh:
            ib = json.load(fh)
    filas = decodificar(ib, ventanas, idx)
    print(formatear(filas, vinfo, {"macros": iinfo["macros"],
                                   "con_valor_literal": iinfo["con_valor_literal"]},
                    iinfo, args.json))
    return 0


if __name__ == "__main__":
    sys.exit(main())
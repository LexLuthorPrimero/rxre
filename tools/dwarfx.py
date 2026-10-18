#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
# WORK_CLASS=READ_ONLY . WRITE_EXECUTION=NONE
"""
dwarfx -- el .ko compilado, ¿corresponde a la fuente que hay ahora?

POR QUE EXISTE
--------------
Todo hallazgo sobre el comportamiento del driver se apoya en un artefacto: el
modulo compilado.  MEDIDO el 2026-10-04: mientras este trabajo corria, otro
agente estaba editando `rx550_pdb0.h`, `rx550_gart_geom.h`,
`rx550_vm_geom.h`, `rx550_target.c` y `rx550_vmid1_pgt.c`, y el `.ko` se
recompilaba por debajo.  Eso convierte en una pregunta real, y recurrente:

    el .ko que estoy citando, ¿es de ESTA fuente?

No hay puerta que lo conteste.  Un hash de git responde "el arbol cambio", que
no es lo mismo: el arbol cambia constantly y el `.ko` puede estar al dia.

LA OBSERVABLE, Y POR QUE ES ESTA
--------------------------------
El `.ko` lleva DWARF, y DWARF guarda `DW_AT_decl_line` de cada miembro: la
linea del CABECERO donde el compilador vio ese miembro.  Eso da una respuesta
que no necesita compilar nada:

    para cada miembro que el compilador recordo, ¿esa linea sigue siendo la
    linea de ese miembro en la cabecera actual?

Si coincide, el compilador y la cabecera estan de acuerdo sobre donde esta
cada miembro.  Si NO coincide, la cabecera se movio despues del build.

Y `sizeof` NO sirve para esto: el DWARF lo genero el compilador DESDE la
cabecera, asi que el tamano coincide por construccion y no informa de nada.
Medir el tamano contra la cabecera seria medir el compilador contra si mismo.

LO QUE NO ES
------------
NO calcula offsets desde la cabecera.  No compila.  NO ejecuta el modulo.  NO
dice si el driver funciona: dice si el artefacto y la fuente siguen siendo la
misma cosa, que es la pregunta previa.

Y NO es un detector de "el .ko esta viejo" en general.  Solo ve los tipos que
llegan hasta DWARF: un struct que nadie instancia puede no tener DIE, y eso
sale como AUSENTE, que no es lo mismo que bien.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import time

VERSION = "1.0.0"

# La herramienta que trae el DWARF.  Se declara su CONTRATO, no su nombre:
# cualquier cosa que imprima el texto de DWARF sirve, y el fichero dice cual.
DWARFDUMP = "llvm-dwarfdump"

RX_DIE = re.compile(r'^(0x[0-9a-fA-F]+):(\s*)(\S.*)$')
RX_AT_NOMBRE = re.compile(r'DW_AT_name\s+\("(.*)"\)')
RX_AT_SIZE = re.compile(r'DW_AT_byte_size\s+\((0x[0-9a-fA-F]+|\d+)\)')
RX_AT_LINE = re.compile(r'DW_AT_decl_line\s+\((\d+)\)')
RX_AT_OFF = re.compile(r'DW_AT_data_member_location\s+\((0x[0-9a-fA-F]+|\d+)\)')
# El formato real es  DW_AT_decl_file  ("/ruta/al/fichero.h")
# MEDIDO sobre llvm-dwarfdump.  La primera version de este regex pedia un "("
# DENTRO de las comillas --  "(\(/ruta..."  -- que no existe, y por eso
# `archivo` salia None en todos los structs y la eleccion de cabecera se
# degradaba a "la ultima que lo declare".
RX_AT_FILE = re.compile(r'DW_AT_decl_file\s+\("([^"]*)"\)')

RX_STRUCT_C = re.compile(r'^\s*(?:struct|union)\s+([A-Za-z_]\w*)\s*\{', re.M)
RX_STRUCT_TYPEDEF = re.compile(r'^\s*typedef\s+struct\s*\{', re.M)
# Miembro que es PUNTERO A FUNCION.  Va ANTES que el general porque el general no
# lo cubre:  `void (*request)(void *ctx, unsigned vmid);` tiene parametros entre
# el nombre y el `;`, y el patron plano exige `;` al final.
#
# MEDIDO.  Sin este patron, `rx550_gart_tlb.request` salia SOLO_EN_DWARF --
# accusing al .ko de estar viejo cuando la cabecera lo declara en la linea exacta
# que el compilador registro.  Un falso positivo que acusa de staleness es peor
# que no mirar: alguien lo creeria y reconstruiria por nada.
RX_MEMBER_FN = re.compile(
    r'^\s*(?:(?:const|volatile|struct|union)\s+)*[A-Za-z_][\w]*'
    r'[\w \t*]*?\(\s*\*\s*([A-Za-z_]\w*)\s*(?:\[[^\]]*\])?\s*\)'
    r'\s*\([^;]*\)\s*;\s*$')
RX_MEMBER = re.compile(
    r'^\s*(?:(?:const|volatile|unsigned|signed|struct|union|enum)\s+)*'
    r'[A-Za-z_][\w \t*]*?\b([A-Za-z_]\w*)\s*(?:\[[^\]]*\])?\s*;\s*$')


def _entero(tok):
    return int(tok, 16) if tok.lower().startswith("0x") else int(tok)


# --------------------------------------------------------------------------
# 1. DWARF
# --------------------------------------------------------------------------

def volcar_dwarf(ko, timeout=180):
    """El texto de DWARF del .ko.  Si la herramienta no existe, se DICE."""
    if not (os.path.isfile(ko) and os.access(ko, os.R_OK)):
        return None, "EL_FICHERO_NO_EXISTE_O_NO_SE_LEE"
    try:
        r = subprocess.run([DWARFDUMP, "--debug-info", ko],
                           capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return None, "NO_HAY_DWARFDUMP"
    except subprocess.TimeoutExpired:
        return None, "DUMPFALL_TIMEOUT"
    if r.returncode != 0 and not r.stdout:
        return None, "DUMPFALL_RC_%d" % r.returncode
    return r.stdout, None


def parsear_structs_dwarf(texto):
    """DIE tree de llvm-dwarfdump -> {struct: {size, decl_line, miembros}}.

    MEDIDO sobre `llvm-dwarfdump --debug-info` real, y la primera version de
    esta funcion era FALSA por una suposicion sobre el formato: busque el
    `DW_AT_name` en la MISMA linea que el `DW_TAG_structure_type`.  No esta ahi.
    El formato real es

        0x00021914:   DW_TAG_structure_type
                        DW_AT_name  ("rx550_pdb0")
                        DW_AT_byte_size (0x50)
                        DW_AT_decl_line (178)
          0x00021920:     DW_TAG_member
                            DW_AT_name  ("state")
                            DW_AT_decl_line (179)

    o sea: una linea por DIE y una linea por atributo, y la RELACION se
    establece por la INDENTACION.  Por eso el estado tiene dos niveles -- struct
    abierto y miembro abierto -- y los atributos se atribuyen al DIE abierto mas
    reciente que los contenga.

    Y el fixture del selftest se copio de ESTA salida, no de una suposicion: un
    fixture inventado que el parser se Faria pasar es un fixture que no prueba
    el parser.
    """
    structs = {}
    st = None          # (nombre, indent, dict)
    mi = None          # (nombre, indent, dict)
    for linea in texto.splitlines():
        m = RX_DIE.match(linea)
        if m:
            sangria = len(m.group(2))
            cuerpo = m.group(3)
            # un DIE nuevo cierra al miembro abierto si no lo contiene
            if mi is not None and sangria <= mi[1]:
                _cerrar_miembro(st, mi)
                mi = None
            if st is not None and sangria <= st[1] and not cuerpo.startswith("DW_TAG_member"):
                if mi is None and st[2]["miembros"]:
                    pass
                st = None
            if cuerpo.startswith("DW_TAG_structure_type"):
                st = [None, sangria, {"size": None, "decl_line": None,
                                      "archivo": None, "miembros": {}}]
                mi = None
            elif cuerpo.startswith("DW_TAG_member") and st is not None \
                    and sangria > st[1]:
                mi = [None, sangria, {}]
            continue
        if st is None:
            continue
        # ATRIBUTOS.  Se atribuyen al DIE abierto MAS INTERNO: si hay un
        # miembro abierto, es suyo; si no, son del struct.  Es la unica regla
        # que reproduce el formato real, donde un miembro tiene nombre, linea y
        # offset en tres lineas seguidas, y el nombre no dice nada de las otras.
        destino = mi[2] if mi is not None else st[2]
        nm = RX_AT_NOMBRE.search(linea)
        if nm:
            if mi is not None:
                if mi[0] is None:
                    mi[0] = nm.group(1)
            elif st[0] is None:
                st[0] = nm.group(1)
                structs[st[0]] = st[2]
            continue
        if mi is not None:
            off = RX_AT_OFF.search(linea)
            if off:
                destino["offset"] = _entero(off.group(1))
            ln = RX_AT_LINE.search(linea)
            if ln:
                destino["line"] = _entero(ln.group(1))
            continue
        sm = RX_AT_SIZE.search(linea)
        if sm:
            st[2]["size"] = _entero(sm.group(1))
        sl = RX_AT_LINE.search(linea)
        if sl:
            st[2]["decl_line"] = _entero(sl.group(1))
        mf = RX_AT_FILE.search(linea)
        if mf:
            st[2]["archivo"] = mf.group(1)
    # el miembro del final del volcado se cierra explicitamente
    _cerrar_miembro(st, mi)
    return structs


def _cerrar_miembro(st, mi):
    """Un miembro se registra con TODOS sus atributos ya leidos.  Se cierra al
    cambiar de DIE, no antes: cerrarlo al abrir el siguiente pierde el
    `data_member_location`, que va DESPUES del `decl_line`."""
    if st is None or mi is None or mi[0] is None:
        return
    st[2]["miembros"][mi[0]] = {"offset": mi[2].get("offset"),
                               "line": mi[2].get("line")}


# --------------------------------------------------------------------------
# 2. CABECERAS
# --------------------------------------------------------------------------

def _sin_comentarios(linea):
    """Quita `/* ... */` y `// ...` que NO esten dentro de un literal.

    MEDIDO, y era un falso positivo con 121 miembros.  La regex de miembro exige
    `;` al final de la linea, y estas cabeceras alinean un comentario DETRAS del
    punto y coma:

        uint64_t   dma_pa;   /* PA del sistema, la que va al registro */

    Con el comentario puesto, la linea no acaba en `;`, no case como miembro, y
    el resultado era `SOLO_EN_DWARF` para 121 miembros que la cabecera SI declara
    y en la linea que el compilador registro.  Un parser que no ve la propia
    fuente culpa a la fuente.

    Se quitan comentarios y NO se tocan literales: una linea con un `;` dentro
    de un literal de cadena no es una declaracion, y arrancarle el comentario a
    medias seria peor.
    """
    out, i, n = [], 0, len(linea)
    while i < n:
        c = linea[i]
        if c == '"' or c == "'":
            q, i = c, i + 1
            out.append(c)
            while i < n:
                out.append(linea[i])
                if linea[i] == "\\" and i + 1 < n:
                    out.append(linea[i + 1])
                    i += 2
                    continue
                if linea[i] == q:
                    i += 1
                    break
                i += 1
            continue
        if c == "/" and i + 1 < n and linea[i + 1] == "*":
            fin = linea.find("*/", i + 2)
            i = n if fin < 0 else fin + 2
            out.append(" ")
            continue
        if c == "/" and i + 1 < n and linea[i + 1] == "/":
            break
        out.append(c)
        i += 1
    return "".join(out)


def structs_de_cabecera(ruta):
    """(miembro, linea) por struct.  Solo nombres y lineas: no se calculan
    offsets, porque no se pueden calcular sin compilar y fingirlo seria
    fabricar el unico dato que este fichero no quiere fabricar."""
    try:
        lineas = open(ruta, encoding="utf-8", errors="replace").read().splitlines()
    except OSError:
        return {}, "ILEGIBLE"
    out, actual, prof, sin_nombre = {}, None, 0, 0
    RX_ABIERTURA = re.compile(r'^\s*(?:typedef\s+)?(?:struct|union)\s*([A-Za-z_]\w*)?\s*\{')
    for i, l in enumerate(lineas, 1):
        l = _sin_comentarios(l)
        m = RX_ABIERTURA.match(l)
        if m:
            if actual and prof >= len(l) - len(l.lstrip()):
                pass
            actual = m.group(1)
            prof = len(l) - len(l.lstrip())
            if actual is None:
                sin_nombre += 1
                actual = "@anonimo_%d" % i
            out.setdefault(actual, {})
            continue
        if actual is None:
            continue
        if l.strip().startswith("}"):
            actual, prof = None, 0
            continue
        if "typedef" in l and l.rstrip().endswith(";"):
            continue
        mm = RX_MEMBER_FN.match(l) or RX_MEMBER.match(l)
        if mm:
            out[actual].setdefault(mm.group(1), i)
    return out, None


# --------------------------------------------------------------------------
# 3. CRUCE
# --------------------------------------------------------------------------

VERDICTO = {
    "COINCIDE": "el compilador y la cabecera ponen el miembro en la misma linea",
    "LINEA_MOVIDA": "la cabecera se movio despues del build; el .ko es anterior",
    "SOLO_EN_DWARF": "el .ko tiene un miembro que la cabecera ya no tiene",
    "SOLO_EN_CABECERA": "la cabecera tiene un miembro que el .ko no vio",
    "SIN_LINEA": "no hay linea que comparar: el finding no se puede emitir",
    "SIN_CABECERA": "el .ko tiene el struct y la cabecera no lo declara",
}


def cruzar(dwarf, cabeceras):
    """La cabecera de cada struct la DELE el propio DWARF, no la ultima que lo
    declare.

    MEDIDO, y lo cambio un vector.  La primera version recorreria las cabeceras
    y se quedaria con la ULTIMA que contuviera el struct.  Con dos cabeceras que
    declaran el mismo struct --cosa normal cuando un .h incluye a otro-- el
    veredicto salia de la que casara por casualidad, y un acierto por casualidad
    es peor que un fallo: no se puede distinguir de uno.

    Ahora: `DW_AT_decl_file` dice de que fichero salio el tipo.  Se busca por
    BASENAME dentro de las cabeceras leidas, que es lo unico comparable sin
    resolver rutas del arbol de compilacion.  Si no esta, se dice
    `CABECERA_NO_LEIDA` en vez de adivinar.  Y si el struct aparece en mas de
    una cabecera, se marca `CABECERA_AMBIGUA`: la eleccion no es un dato.
    """
    por_base = {}
    for ruta, tablas in cabeceras.items():
        por_base.setdefault(os.path.basename(ruta), []).append((ruta, tablas))

    filas = []
    for struct, info in sorted(dwarf.items()):
        declarado = info.get("archivo")
        base = os.path.basename(declarado) if declarado else None
        por_declaracion = bool(base) and base in por_base
        candidatas = []
        if por_declaracion:
            candidatas = [(r, t[struct]) for r, t in por_base[base]
                          if struct in t]
        else:
            for ruta, tablas in cabeceras.items():
                if struct in tablas:
                    candidatas.append((ruta, tablas[struct]))
        if not candidatas:
            filas.append({"struct": struct, "veredicto": "CABECERA_NO_LEIDA",
                          "decl_file": declarado,
                          "detalle": "DWARF dice que salio de %s, y ese fichero "
                                     "no esta entre las cabeceras leidas, y "
                                     "ninguna de las leidas declara el struct"
                                     % (declarado or "un fichero desconocido")})
            continue
        if len(candidatas) > 1:
            filas.append({"struct": struct, "veredicto": "CABECERA_AMBIGUA",
                          "candidatas": [os.path.basename(x[0]) for x in candidatas],
                          "detalle": "el struct aparece en %d cabeceras; elegir "
                                     "una seria una decision, no un dato"
                                     % len(candidatas)})
            continue
        # Si se llego aqui sin que el nombre de la cabecera este entre las leidas,
        # pero solo UNA declara el struct, la determinacion es UNICA.  No es una
        # adivinanza, pero no es la que el compilador declaro, y el lector tiene
        # que poder distinguirlo: por eso cada fila lleva el booleano.
        ruta, miembros = candidatas[0]
        for nom, md in sorted(info["miembros"].items()):
            lin = miembros.get(nom)
            if lin is None:
                filas.append({"struct": struct, "miembro": nom,
                              "veredicto": "SOLO_EN_DWARF",
                              "linea_dwarf": md.get("line"),
                              "cabecera": os.path.basename(ruta),
                              "cabecera_por_declaracion": por_declaracion,
                              "detalle": "el .ko lo tiene en esa linea; la "
                                         "cabecera actual no lo declara"})
            elif md.get("line") is None:
                filas.append({"struct": struct, "miembro": nom,
                              "veredicto": "SIN_LINEA",
                              "cabecera": os.path.basename(ruta),
                              "cabecera_por_declaracion": por_declaracion,
                              "detalle": "el compilador no guardo linea: no hay "
                                         "con que comparar"})
            elif md["line"] == lin:
                filas.append({"struct": struct, "miembro": nom,
                              "veredicto": "COINCIDE",
                              "linea_dwarf": md["line"], "linea_cabecera": lin,
                              "offset": md.get("offset"),
                              "cabecera": os.path.basename(ruta),
                              "cabecera_por_declaracion": por_declaracion,
                              "detalle": VERDICTO["COINCIDE"]})
            else:
                filas.append({"struct": struct, "miembro": nom,
                              "veredicto": "LINEA_MOVIDA",
                              "linea_dwarf": md["line"], "linea_cabecera": lin,
                              "offset": md.get("offset"),
                              "cabecera": os.path.basename(ruta),
                              "cabecera_por_declaracion": por_declaracion,
                              "detalle": VERDICTO["LINEA_MOVIDA"]})
        for nom, lin in sorted(miembros.items()):
            if nom not in info["miembros"]:
                filas.append({"struct": struct, "miembro": nom,
                              "veredicto": "SOLO_EN_CABECERA",
                              "linea_cabecera": lin,
                              "cabecera": os.path.basename(ruta),
                              "cabecera_por_declaracion": por_declaracion,
                              "detalle": "la cabecera lo declara y el .ko no lo "
                                         "vio: el build es anterior"})
    cuentas = {}
    for f in filas:
        cuentas[f["veredicto"]] = cuentas.get(f["veredicto"], 0) + 1
    return filas, cuentas


# --------------------------------------------------------------------------
# 4. MAIN
# --------------------------------------------------------------------------

def main(argv):
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if "--selftest" in argv or "--self-test" in argv:
        return selftest()
    if "--version" in argv:
        print(VERSION)
        return 0

    def valor(f):
        for i, a in enumerate(argv):
            if a == f and i + 1 < len(argv):
                return argv[i + 1]
        return None

    ko = valor("--ko") or os.path.join(raiz, "04-IMPLEMENTACION",
                                       "rx550-driver", "rx550_drv.ko")
    dir_drv = valor("--dir") or os.path.dirname(ko)

    texto, err = volcar_dwarf(ko)
    if texto is None:
        print("NO SE PUDO LEER DWARF DE %s: %s" % (ko, err))
        print("  Sin esto no hay veredicto.  Es NOT_DETERMINED, no ausencia.")
        return 2
    dwarf = parsear_structs_dwarf(texto)

    cabeceras, ilegibles = {}, []
    for f in sorted(os.listdir(dir_drv)):
        if not f.endswith(".h"):
            continue
        p = os.path.join(dir_drv, f)
        tablas, e = structs_de_cabecera(p)
        if e:
            ilegibles.append(f)
            continue
        cabeceras[p] = tablas

    filas, cuentas = cruzar(dwarf, cabeceras)

    if "--json" in argv:
        print(json.dumps({
            "herramienta": "dwarfx " + VERSION,
            "generado": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "ko": ko, "cabeceras": sorted(os.path.basename(x) for x in cabeceras),
            "structs_en_dwarf": len(dwarf), "filas": len(filas),
            "cuentas": cuentas, "filas_detalle": filas,
            "limites": [VERDICTO[k] for k in
                        ("SIN_LINEA", "SIN_CABECERA", "SOLO_EN_CABECERA")],
        }, indent=2, ensure_ascii=False))
        return 0

    print("=" * 92)
    print("dwarfx %s   .ko: %s" % (VERSION, ko))
    print("=" * 92)
    print("  %d structs en DWARF, %d cabecera(s) leida(s), %d comparaciones"
          % (len(dwarf), len(cabeceras), len(filas)))
    if ilegibles:
        print("  cabeceras ilegibles: %s" % ", ".join(ilegibles))
    print()
    print("  conteo: %s" % (", ".join("%s=%d" % kv
                                      for kv in sorted(cuentas.items())) or "nada"))
    print()
    print("  %-26s %-22s %-10s %s" % ("STRUCT", "MIEMBRO", "VEREDICTO", "LINEAS"))
    print("  " + "-" * 88)
    orden = {"LINEA_MOVIDA": 0, "SOLO_EN_CABECERA": 1, "SOLO_EN_DWARF": 2,
             "CABECERA_AMBIGUA": 3, "SIN_LINEA": 4, "COINCIDE": 5}
    detalle = [f for f in filas if f["veredicto"] != "CABECERA_NO_LEIDA"]
    for f in sorted(detalle, key=lambda x: (orden.get(x["veredicto"], 9),
                                           x["struct"], x.get("miembro") or "")):
        if f["veredicto"] == "COINCIDE":
            continue
        print("  %-26s %-22s %-10s d=%s h=%s"
              % (f["struct"], f.get("miembro", "-"), f["veredicto"],
                 f.get("linea_dwarf", "-"), f.get("linea_cabecera", "-")))
        print("      %s" % f["detalle"])

    # CABECERA_NO_LEIDA se agrupa.  MEDIDO: son 446 filas y todas son tipos del
    # KERNEL -- un .ko compila contra las cabeceras de /usr/src/kernels, no solo
    # contra las del proyecto.  Listarlas una a una esconde los veredictos que
    # importan, que son los de los tipos propios.  Se agrupa por fichero
    # DECLARADO y se dice cuantas filas son, para que el numero no se pierda.
    no_leidas = [f for f in filas if f["veredicto"] == "CABECERA_NO_LEIDA"]
    if no_leidas:
        con_fich = [f for f in no_leidas if f.get("decl_file")]
        sin_fich = [f for f in no_leidas if not f.get("decl_file")]
        print()
        print("  CABECERAS NO LEIDAS: %d tipos del .ko que no son del proyecto."
              % len(no_leidas))
        print("  No son un veredicto sobre el proyecto: son tipos del kernel, que "
              "este fichero no comprueba.  NOT_DETERMINED, no ausencia.")
        print("    %d declan de que fichero vienen, y ninguno es del proyecto"
              % len(con_fich))
        print("    %d no declan fichero: DWARF omite DW_AT_decl_file en su DIE, y "
              "tampoco son del proyecto" % len(sin_fich))
        grupo = {}
        for f in con_fich:
            b = os.path.basename(f["decl_file"])
            grupo[b] = grupo.get(b, 0) + 1
        for nombre, n in sorted(grupo.items(), key=lambda kv: (-kv[1], kv[0]))[:6]:
            print("      %-46s %d tipos" % (nombre, n))
        if len(grupo) > 6:
            print("      ... y %d ficheros mas" % (len(grupo) - 6))
    # El denominador HONESTO: los miembros cuya cabecera se ha LEIDO.  Contar
    # sobre `len(filas)` metería los 446 tipos del kernel en el denominador y
    # haría que 204 de 650 pareciera una cobertura del 31 % cuando lo que se ha
    # comparado es el 100 % de lo comparable.
    propios = [f for f in filas if f["veredicto"] != "CABECERA_NO_LEIDA"]
    n_ok = cuentas.get("COINCIDE", 0)
    print()
    print("  COINCIDE: %d de %d miembros cuya cabecera se ha leido (%.0f %%)."
          % (n_ok, len(propios), 100.0 * n_ok / len(propios) if propios else 0))
    print("  Los %d tipos del kernel quedan fuera del denominador a proposito:"
          % (len(filas) - len(propios)))
    print("  incluirlos haria que el porcentaje no significara nada.")
    print()
    print("LIMITE  Solo se ven los tipos que llegan hasta DWARF.  Un struct que")
    print("        nadie instancia puede no tener DIE, y eso sale como AUSENTE,")
    print("        que no es lo mismo que correcto.")
    print("LIMITE  No se calculan offsets desde la cabecera.  No se compila nada.")
    print("LIMITE  El parseo de DWARF depende del formato de llvm-dwarfdump.  Si")
    print("        cambia, esto ve menos structs y no lo avisa: por eso se")
    print("        imprime cuantos ha visto, para que un cero sea visible.")
    print("LIMITE  sizeof NO se contrasta: lo genero el compilador desde la propia")
    print("        cabecera, asi que coincidiria siempre y no informaria de nada.")
    return 0


# --------------------------------------------------------------------------
# 5. SELFTEST -- hermetico, con DWARF sintetico
# --------------------------------------------------------------------------

# El fixture de DWARF es una COPIA de la salida real de llvm-dwarfdump, con las
# tabs que emite y una linea por DIE y una por atributo.  La primera version lo
# escribi a mano con el nombre en la misma linea que el tag, que NO es el
# formato: el parser paso sus propios vectores y fallaba con el fichero real.
#
# Lineas: demo.h -> `demo` en 1, `a` en 2, `b` en 3.  viejo.h -> `viejo` en 1,
# `z` en 2.  Y DWARF lo dice con esos numeros.
FIX_DWARF = (
    "0x00021914:   DW_TAG_structure_type\n"
    "                DW_AT_name\t(\"demo\")\n"
    "                DW_AT_byte_size\t(0x10)\n"
    "                DW_AT_decl_file\t(\"/x/demo.h\")\n"
    "                DW_AT_decl_line\t(1)\n"
    "\n"
    "0x00021920:     DW_TAG_member\n"
    "                  DW_AT_name\t(\"a\")\n"
    "                  DW_AT_decl_line\t(2)\n"
    "                  DW_AT_data_member_location\t(0x00)\n"
    "\n"
    "0x0002192d:     DW_TAG_member\n"
    "                  DW_AT_name\t(\"b\")\n"
    "                  DW_AT_decl_line\t(3)\n"
    "                  DW_AT_data_member_location\t(0x08)\n"
    "\n"
    "0x00021a00:   DW_TAG_structure_type\n"
    "                DW_AT_name\t(\"viejo\")\n"
    "                DW_AT_byte_size\t(0x08)\n"
    "                DW_AT_decl_file\t(\"/x/viejo.h\")\n"
    "                DW_AT_decl_line\t(1)\n"
    "\n"
    "0x00021a10:     DW_TAG_member\n"
    "                  DW_AT_name\t(\"z\")\n"
    "                  DW_AT_decl_line\t(2)\n"
    "                  DW_AT_data_member_location\t(0x00)\n"
)

# Cada struct en SU cabecera.  La primera version metia los dos en demo.h, con
# lo que `viejo` aparecia declarado en dos ficheros y la eleccion de cabecera
# dejaba de ser un dato: el vector pasaba por casualidad.
FIX_H_DEMO = "struct demo {\n\tint\t\ta;\n\tvoid\t\t*b;\n};\n"
FIX_H_DEMO_MOVIDO = ("/* una linea de comentario */\nstruct demo {\n"
                     "\tint\t\ta;\n\tvoid\t\t*b;\n};\n")
FIX_H_VIEJO = "struct viejo {\n\tint\t\tz;\n};\n"


def _cab(tmp, nombre, txt, acc):
    p = os.path.join(tmp, nombre)
    with open(p, "w") as fh:
        fh.write(txt)
    acc[p], _e = structs_de_cabecera(p)


def selftest():
    v, fallos = [], []

    def t(nombre, ok, det):
        v.append((nombre, ok, det))
        if not ok:
            fallos.append(nombre)

    d = parsear_structs_dwarf(FIX_DWARF)
    t("DW_1_lee_los_dos_structs", set(d) == {"demo", "viejo"}, str(sorted(d)))
    t("DW_2_lee_miembros_y_offsets",
      d.get("demo", {}).get("miembros", {}).get("b", {}).get("offset") == 8
      and d["demo"]["miembros"]["a"]["line"] == 2,
      str(d.get("demo", {}).get("miembros")))
    t("DW_3_lee_decl_line", d.get("demo", {}).get("decl_line") == 1,
      str(d.get("demo", {}).get("decl_line")))
    t("DW_4_lee_el_byte_size", d.get("demo", {}).get("size") == 16,
      str(d.get("demo", {}).get("size")))
    t("DW_5_lee_decl_file_Y_lo_usa_para_elegir_cabecera",
      (d.get("viejo", {}).get("archivo") or "").endswith("viejo.h"),
      str(d.get("viejo", {}).get("archivo")))

    with tempfile.TemporaryDirectory(prefix="dwarfx-st") as td:
        cab = {}
        _cab(td, "demo.h", FIX_H_DEMO, cab)
        _cab(td, "viejo.h", FIX_H_VIEJO, cab)
        filas, c = cruzar(d, cab)
        t("XF_1_sin_cambios_nada_todo_coincide",
          c.get("COINCIDE", 0) == 3 and len(filas) == 3, str(c))

    with tempfile.TemporaryDirectory(prefix="dwarfx-st") as td:
        cab = {}
        _cab(td, "demo.h", FIX_H_DEMO_MOVIDO, cab)
        _cab(td, "viejo.h", FIX_H_VIEJO, cab)
        filas, c = cruzar(d, cab)
        mov = sorted((f["miembro"], f["linea_dwarf"], f["linea_cabecera"])
                     for f in filas if f["veredicto"] == "LINEA_MOVIDA")
        t("XF_2_una_cabecera_movida_despues_del_build_se_ve",
          mov == [("a", 2, 3), ("b", 3, 4)] and c.get("COINCIDE") == 1, str(mov))

    with tempfile.TemporaryDirectory(prefix="dwarfx-st") as td:
        cab = {}
        _cab(td, "demo.h", FIX_H_DEMO, cab)
        _cab(td, "otro.h", FIX_H_VIEJO, cab)   # el struct esta en OTRO fichero
        filas, c = cruzar(d, cab)
        # `viejo` esta en otro.h, no en el viejo.h que declara DWARF.  Solo una
        # cabecera lo declara, asi que la determinacion es UNICA: se usa, pero
        # cada fila dice que no vino de la cabecera declarada.
        viejos = [f for f in filas if f["struct"] == "viejo"]
        t("XF_3_determinacion_unica_pero_no_de_la_cabecera_declarada",
          c.get("COINCIDE", 0) == 3 and viejos
          and all(f["cabecera_por_declaracion"] is False for f in viejos)
          and all(f["cabecera"] == "otro.h" for f in viejos), str(viejos))

    with tempfile.TemporaryDirectory(prefix="dwarfx-st") as td:
        cab = {}
        _cab(td, "demo.h", FIX_H_DEMO, cab)     # viejo.h NO esta
        filas, c = cruzar(d, cab)
        t("XF_4_una_cabecera_ausente_no_es_veredicto_de_ausencia",
          c.get("CABECERA_NO_LEIDA", 0) == 1, str(c))

    with tempfile.TemporaryDirectory(prefix="dwarfx-st") as td:
        cab = {}
        _cab(td, "demo.h", "struct demo {\n\tint\t\ta;\n\tvoid\t\t*b;\n"
                          "\tint\t\tnuevo;\n};\n", cab)
        _cab(td, "viejo.h", FIX_H_VIEJO, cab)
        filas, c = cruzar(d, cab)
        nuevos = [f for f in filas if f["veredicto"] == "SOLO_EN_CABECERA"]
        t("XF_5_un_miembro_nuevo_no_lo_vio_el_build",
          len(nuevos) == 1 and nuevos[0]["miembro"] == "nuevo"
          and nuevos[0]["linea_cabecera"] == 4, str(nuevos))

    # El caso que produjo el falso positivo: puntero a funcion con parametros.
    # La forma real del proyecto, con el comentario alineado detras del `;`.
    with tempfile.TemporaryDirectory(prefix="dwarfx-st") as td:
        p = os.path.join(td, "g.h")
        open(p, "w").write(
            "struct rx550_gart_tlb {\n"
            "\tvoid\t(*request)(void *ctx, unsigned vmid);\n"
            "\tvoid\t *ctx;\t/* puntero al contexto */\n};\n")
        tablas, _e = structs_de_cabecera(p)
        t("PTR_1_un_puntero_a_funcion_es_miembro",
          tablas.get("rx550_gart_tlb", {}).get("request") == 2,
          str(tablas.get("rx550_gart_tlb")))
        t("PTR_2_un_miembro_con_comentario_alineado_tambien",
          tablas.get("rx550_gart_tlb", {}).get("ctx") == 3,
          str(tablas.get("rx550_gart_tlb")))

    t("LIM_1_dwarf_vacio_no_inventa_structs", parsear_structs_dwarf("") == {}, "")
    t("LIM_2_texto_que_no_es_dwarf_no_produce_veredictos",
      parsear_structs_dwarf("baseline  file format elf64\n") == {}, "")

    print("  selftest de dwarfx %s" % VERSION)
    print("  %d vectores, %d fallos" % (len(v), len(fallos)))
    for nombre, ok, det in v:
        print("    %-4s %-58s %s" % ("OK" if ok else "FALLA", nombre, det[:36]))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

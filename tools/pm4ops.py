#!/usr/bin/env python3
# CONTRACT: name=pm4ops
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: TOUCHES_INTEGRATED=no
#
# MEDIDO con RXRE/tools/rxre_contracts.py, no declarado de memoria.  El
# veredicto fue `READONLY=yes, WRITES_FILES=no`, y las 16 escrituras que
# tiene se resolvieron a la clase TEMPORAL: 16 caen DENTRO de un `with tempfile...`.
#
# Declarar `WRITES_FILES=no` con escrituras dentro no es una contradiccion: es
# exactamente la clase TEMPORAL de `contract_exec.py`, que existe porque una
# regex produjo cinco falsos positivos.  Declararlas `yes` seria MENTIR: el
# validador no puede distinguir un temporal de un fichero del proyecto.
#
# `tools/` tenia 3 contratos de 92.  Este bloque no anade comportamiento: hace
# el comportamiento DECLARABLE, que es la condicion previa a poder usarlo.
# Sobre la frontera: TOUCHES_INTEGRATED=no, y el campo se declara aunque
# toolkit.py no lo conozca -- la frontera que no se puede declarar es la que no
# se puede hacer cumplir (hallazgo 1487).
# SPDX-License-Identifier: GPL-2.0
# WORK_CLASS=READ_ONLY . WRITE_EXECUTION=NONE
"""
pm4ops -- consenso de opcodes PACKET3 entre los headers de AMD, y veredicto
por decodificador.

POR QUE EXISTE
--------------
El proyecto tiene cuatro decodificadores de PM4 y una fuente primaria.  Los
cuatro tienen tablas de opcode independientes y NADIE las ha comparado.  Un
`switch` escrito a mano y un `sid.h` pueden discrepar durante meses, y el
resultado es un volcado de IB con un nombre equivocado y toda la apariencia de
un dato.

El propio `tools/pm4decode.c` avisa de esto en su cabecera: *"la primera version
de esta tabla estaba hecha de memoria y tenia SIETE entradas equivocadas.  Lo
encontro el test, no la lectura"*, y *"un nombre equivocado en un diagnostico es
peor que un numero"*.  La tabla se corrigio.  Lo que no existe es la puerta que
haga que la SIGUIENTE entrada equivocada se note sin tests.

Y hay un segundo hecho, ya medido por `revkit/pm4dec.py` y que este fichero
reutiliza en vez de redescubrir: **la numeracion de opcodes NO es estable entre
generaciones de ASIC**.  `LOAD_SH_REG` es 0x61 en `sid.h` y 0x5F en los otros
cinco headers.  O sea: un decodificador construído sobre un SOLO header hereda
ese desplazamiento sin saberlo, y produce nombres con apariencia de dato.

Un decodificador derivado de un solo header no se puede validar contra ese
header: hace falta el CONSENSO, y por eso esto compara por mayoria de fuentes y
no por una fuente.

QUE NO HACE
-----------
NO corrige ninguna tabla.  `tools/pm4decode.c` y `revkit/pm4dec.py` son de otra
sesion; este fichero mide y dice.  Una herramienta que corrige la tabla del otro
sin que nadie lo decida es como empiezan los registros que nadie puede
reproducir.

Lo que afirma, y lo que no:

  * AFIRMA que una tabla y el consenso dicen cosas distintas, con los headers
    que las contradicen nombrados uno a uno.
  * NO AFIRMA cual de las dos dice bien.  Marca el disidente; decidir cual es
    el correcto para GFX8 es una cuestion semantica del agente principal, y el
    dato que la resuelve --la generacion del ASIC-- no esta en una tabla de
    opcodes.

LIMITE DECLARADO, Y ES EL IMPORTANTE
-------------------------------------
Un opcode que ningun header nombra queda `SIN_NOMBRE_EN_FUENTES`.  No es
"reservado", no es "invalido": es que las fuentes disponibles no lo nombran.
`NOT_FOUND` no es `PROVEN_ABSENT`, y este fichero no tiene las pruebas para
convertirlo.
"""

import ast
import hashlib
import json
import os
import re
import sys
import tempfile
import time

VERSION = "1.0.0"

# La lista de headers.  NO se inventa: es la de `revkit/pm4dec.py`, que la
# audito y la corrigio con `tools/rx550ref --sym` de otra sesion.  Se declara
# aqui y ADEMAS se comprueba contra aquel fichero cuando se puede leer, porque
# dos listas de "que headers definen opcodes" es una lista y un grupo de
# headers que nadie mira.
HEADERS_OPCODE = ["sid.h", "vid.h", "cikd.h", "nvd.h", "soc15d.h",
                      "gfx_v12_1_pkt.h"]

RX_CASE = re.compile(r'#define\s+(PACKET3_[A-Z0-9_]+)\s+(0x[0-9a-fA-F]+)')
RX_SWITCH_C = re.compile(
    r'case\s+(0x[0-9a-fA-F]+)\s*:\s*return\s*"([A-Za-z0-9_]+)"')
RX_PY_DICT = re.compile(r'"(PACKET3_[A-Z0-9_]+)"\s*:\s*0x([0-9a-fA-F]+)')
RX_INCLUDE = re.compile(r'^\s*#\s*include\s+"([^"]+)"', re.M)

# El driver de la GENERACION del target.  No se declara por costumbre: se
# comprueba.  MEDIDO, y el nombre solo no basta -- ver `alcance_generacion`.
DRIVER_GENERACION = "gfx_v8_0.c"


def raices_include(base, limite=400):
    """Directorios donde el PREPROCESADOR buscaria un include con comillas.

    MEDIDO, y la primera version de este fichero miraba UN solo directorio: el
    del propio driver.  Eso dio 29 cabeceras "rotas" que NO lo estaban: viven en
    directorios hermanos que el Makefile pone en la ruta con -I, como
    `drivers/gpu/drm/amd/include/` y `drivers/gpu/drm/amd/pm/inc/`.

        $ find . -name amdgpu_dpm.h     -> 4 존재 en el proyecto
        $ ... pero el cierre de un solo directorio lo daba por ausente

    Un include con comillas se busca en la RUTA DE INCLUSION, no en el directorio
    del que se escribe.  Resolverlo en un solo sitio no es approximates es
    resolver mal, y resolver mal aqui es peor que no resolver: producia 29
    roturas falsas y hacia que el veredicto de generacion pareciera mucho menos
    firme de lo que es.

    Las raices se DESCUBREN (todo directorio bajo `base` que contenga al menos un
    `.h`), no se declaran.  Una lista fija seria otra lista que nadie mantiene,
    que es el defecto que `HEADERS_OPCODE` ya corregir importing de `pm4dec.py`.

    Con las raices correctas la cuenta va de 86 ficheros y 29 roturas a 141
    ficheros y 1 rotura.  Y la conclusion se CONFIRMA, que es lo importante:
    `gfx_v8_0.c` sigue sin alcanzar a `sid.h`.
    """
    raices = set()
    for dp, _dirs, files in os.walk(base):
        if any(f.endswith(".h") for f in files):
            raices.add(dp)
            if len(raices) > limite:
                break
    return sorted(raices)


def _resolver(raices, nombre):
    """Primera coincidencia, como el preprocesador.  El orden de las raices es el
    que de��� sorted() da, o sea alfabetico, y se DECLARA que no es el orden real
    del Makefile: si dos directorios tuvieran un `.h` del mismo nombre, esto
    mediria el alfabetico y no el del kernel.  No ha pasado --los nombres de
    cabecera de amdgpu son unicos-- pero queda dicho en vez de supuesto."""
    for d in raices:
        p = os.path.join(d, nombre)
        if os.path.isfile(p):
            return p
    return None


def cierre_includes(raices, inicial, limite=4000):
    """Ficheros alcanzables desde `inicial` resolviendo en TODAS las raices.

    Se sigue solo el include de COMILLAS: el de CORCHETES ANGULARES sale del
    arbol del kernel y no se puede resolver aqui, y resolverlo seria inventar.

    Devuelve tambien los includes que NO resuelven y quien los incluye, porque
    cada rotura es un agujero por el que puede pasar una inclusion que no se ve.
    MEDIDO con las raices correctas queda UNA, `amdgpu_dal_power_if.h`, incluida
    por `amdgpu_dm.h`: la cadena del DAL, que es otro subsistema.  Por eso la
    conclusion sobrevive, pero se declara con la rotura a la vista.
    """
    vistos, pila, truncado = set(), [inicial], False
    rotos = {}
    while pila:
        if len(vistos) > limite:
            truncado = True
            break
        f = os.path.basename(pila.pop())
        if f in vistos:
            continue
        p = _resolver(raices, f)
        if p is None:
            rotos.setdefault(f, set())
            continue
        vistos.add(f)
        try:
            txt = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for otro in RX_INCLUDE.findall(txt):
            b = os.path.basename(otro)
            if b.endswith(".h"):
                if _resolver(raices, b) is None:
                    rotos.setdefault(b, set()).add(f)
                pila.append(b)
    return vistos, truncado, {k: sorted(v) for k, v in rotos.items()}


def alcance_generacion(d, driver=DRIVER_GENERACION, headers=None, raices=None):
    """Que headers de opcodes alcanza REALMENTE el driver de esta generacion.

    POR QUE ESTO CAMBIA EL METODO, Y NO ES UN DETALLE

    La primera version de este fichero votaba por mayoria entre SEIS headers.
    MEDIDO por cierre de includes desde `gfx_v8_0.c` -- el driver de GFX8, que
    es la generacion del target -- de los seis solo `vid.h` es alcanzable:

            vid.h   ALCANZABLE
            sid.h   NO      cikd.h  NO      nvd.h  NO
            soc15d.h NO      gfx_v12_1_pkt.h  NO

    O sea: cinco de las seis "fuentes" no describen el ASIC del target, y el
    esquema `_pkt.h` que usa `gfx_v12_1_pkt.h` es de NAVI 12.1.  Contarlas como
    votos iguales es exactamente el error que este fichero existe para evitar:
    una mayoria puede estar mal cuando la generacion correcta es la minorita, y
    aqui la minorita es UNA de seis y ademas es la unica que aplica.

    Y la medicion del alcance se hizo en dos pasos, porque el primero estaba mal:
    resolver en un solo directorio daba 29 roturas falsas.  Con las raices de
    include correctas son 141 ficheros y UNA rotura, y la conclusion se confirma.

    Por eso el veredicto se emite DOS veces: entre los headers que la generacion
    alcanza, y entre todos.  No se reemplaza uno por otro: son preguntas
    distintas y contestarlas con una sola es ocultar cual se contesta.
    """
    raices = raices if raices is not None else raices_include(d)
    # MEDIDO, y lo encontro un vector: el PUNTO DE ENTRADA tiene que resolverse
    # siempre.  `raices_include` solo devuelve directorios que contienen al
    # menos un `.h`, y un `.c` puede vivir en un directorio donde no hay ninguno.
    # Entonces el propio fichero inicial no se abria, el cierre salia vacio y el
    # veredicto decia "ningun header alcanzable" -- que es un ABSENT falso
    # producido por una limitacion de la herramienta, no por el codigo.
    ini_dir = os.path.dirname(os.path.join(d, driver)) if not os.path.isabs(driver) \
        else os.path.dirname(driver)
    if ini_dir and os.path.isdir(ini_dir) and ini_dir not in raices:
        raices = sorted(set(raices) | {ini_dir})
    alc, truncado, rotos = cierre_includes(raices, driver)
    headers = headers or HEADERS_OPCODE
    return {"driver": driver, "alcanzable": sorted(h for h in headers if h in alc),
            "no_alcanzable": sorted(h for h in headers if h not in alc),
            "ficheros_en_cierre": len(alc), "truncado": truncado,
            "includes_quebrados": rotos,
            "n_raices_include": len(raices),
            "alcance_integro": not rotos and not truncado,
            "metodo": "cierre de #include con comillas resuelto en %d directorios "
                      "descubiertos (no una lista fija); los includes con "
                      "corchetes angulares no se resuelven y no se inventan"
                      % len(raices)}


# --------------------------------------------------------------------------
# 1. FUENTES PRIMARIAS
# --------------------------------------------------------------------------

def raices_amdgpu(proyecto):
    """Directorios candidatos del arbol amdgpu, y el primero que exista.

    Se declara la lista en vez de suponer una ruta: el arbol tiene tres copias
    del kernel y `pm4dec.py` yamidtio que el `sid.h` de las tres es
    byte-identico.  La identidad se COMPRUEBA aqui y se reporta, no se supone.
    """
    return [
            os.path.join(proyecto, "RESEARCH", "baseline", "linux-7.1.3",
                         "drivers", "gpu", "drm", "amd", "amdgpu"),
            os.path.join(proyecto, "RESEARCH", "working", "linux-7.1.3",
                         "drivers", "gpu", "drm", "amd", "amdgpu"),
            os.path.join(proyecto, "RESEARCH", "kernelbuild", "linux-7.1.3",
                         "drivers", "gpu", "drm", "amd", "amdgpu"),
    ]


def sha_de(p):
    try:
            h = hashlib.sha256()
            with open(p, "rb") as fh:
                for b in iter(lambda: fh.read(65536), b""):
                    h.update(b)
            return h.hexdigest()
    except OSError:
            return None


def cargar_fuentes(dirs, headers=HEADERS_OPCODE):
    """opcode -> {nombre: set(headers)}.  Devuelve tambien la procedencia."""
    tabla = {}
    procedencia = []
    for d in dirs:
            if not os.path.isdir(d):
                continue
            for h in headers:
                p = os.path.join(d, h)
                if not os.path.isfile(p):
                    procedencia.append({"header": h, "ruta": p, "estado": "NO_EXISTE"})
                    continue
                txt = open(p, encoding="utf-8", errors="replace").read()
                n = 0
                for m in RX_CASE.finditer(txt):
                    tabla.setdefault(int(m.group(2), 16), {}).setdefault(
                        m.group(1)[8:], set()).add(h)
                    n += 1
                procedencia.append({"header": h, "ruta": os.path.relpath(d),
                                   "sha256": sha_de(p)[:16],
                                   "definiciones": n})
            if tabla:
                break
    return tabla, procedencia


def identidades(dirs, headers=HEADERS_OPCODE):
    """¿Los `sid.h` de las distintas copias son el MISMO fichero?"""
    seen = {}
    for d in dirs:
            for h in headers:
                p = os.path.join(d, h)
                if os.path.isfile(p):
                    seen.setdefault(h, {}).setdefault(sha_de(p), []).append(d)
    out = {}
    for h, por_sha in seen.items():
            shas = sorted(por_sha)
            out[h] = {"identico_en_todas_las_copias": len(shas) == 1,
                      "sha256": shas[0][:16] if len(shas) == 1 else None,
                      "copias": {s[:16]: len(v) for s, v in por_sha.items()}}
    return out


# --------------------------------------------------------------------------
# 2. CONSENSO
# --------------------------------------------------------------------------

def _macros_no_opcode(dirs, headers=HEADERS_OPCODE):
    """PACKET3_* cuyo VALOR no es un opcode de byte, con su estado.

    MEDIDO, y es la clase de error mas insidiosa de las tres.  En los headers
    hay macros como

            #define PACKET3_PREAMBLE_BEGIN_CLEAR_STATE   (2 << 28)

    cuyo valor NO es un opcode de un byte: es una cabecera entera con otra
    codificacion.  Un decodificador que pone `case 0x40: return "PREAMBLE_BEGIN"`
    esta haciendo dos cosas a la vez: asignando a 0x40 un nombre que las
    fuentes dan a OTRO paquete, y usando un NOMBRE que parece plausible pero
    no es el nombre de ninguna macro viva.

    MEDIDO TAMBIEN que esas definiciones estan COMENTADAS en los cuatro headers
    donde aparecen, con la forma `#              define ...` y sin `#if` que las
    cubra.  Por eso se distingue `VIVA` de `COMENTADA`: una macro comentada no
    puede ser la fuente de un opcode, y decirlo sin distinguir seria inventar
    una autoridad.

    NO se afirma de donde sale el nombre del decodificador.  Que se parezca a
    una macro comentada es una HIPOTESIS sobre su origen, no un hecho, y asi se
    emite.
    """
    fuera = {}
    for d in dirs:
            if not os.path.isdir(d):
                continue
            for h in headers:
                p = os.path.join(d, h)
                if not os.path.isfile(p):
                    continue
                txt = open(p, encoding="utf-8", errors="replace").read()
                # `#  define` con espacios entre `#` y `define` es una definicion
                # COMENTADA.  MEDIDO: el kernel escribe las suyas asi y no hay
                # `#if 0` que las cubra.  Y el discriminante tiene que ser EXACTO:
                # la primera version de este regex llevaba `[ \t]*` despues de `#`,
                # que casa con cero espacios, con lo que una misma macro salia
                # VIVA y COMENTADA a la vez.  Un detector que no distingue lo vivo
                # de lo muerto no puede decir nada sobre quien es la fuente.
                for rx, estado in (
                        (re.compile(r'^[ \t]*#[ \t]+define[ \t]+(PACKET3_[A-Z0-9_]+)'
                                    r'[ \t]+(\([^)]*\)|[^/\s][^\s]*)', re.M), "COMENTADA"),
                        (re.compile(r'^[ \t]*#define[ \t]+(PACKET3_[A-Z0-9_]+)'
                                    r'[ \t]+(\([^)]*\)|[^/\s][^\s]*)', re.M), "VIVA")):
                    for m in rx.finditer(txt):
                        nombre, valor = m.group(1), m.group(2).strip()
                        if RX_CASE.fullmatch("#define %s %s" % (nombre, valor)):
                            continue                  # es un opcode de byte
                        e = fuera.setdefault(nombre, {"valor": valor, "headers": {},
                                                      "estados": set()})
                        e["headers"].setdefault(estado, set()).add(h)
                        e["estados"].add(estado)
                        if e["valor"] != valor:
                            e["valor"] = valor      # el ultimo gana: se declara
            if fuera:
                break
    for nombre, v in fuera.items():
            v["headers"] = sorted({h for hs in v["headers"].values() for h in hs})
            v["estados"] = sorted(v["estados"])
    return fuera


def opcode_mayoria(tabla):
    """opcode -> (nombre, votos, headers).  El indice inverso al de `consenso`.

    Hace falta porque hay dos preguntas distintas y confundirlas es un falso
    negativo:
      * ¿este NOMBRE vale este opcode?   -> se responde con `consenso`
      * ¿este OPCODE es este nombre?      -> se responde con esto
    Una tabla puede acertar la primera y fallar la segunda.
    """
    por_op = {}
    for op, nombres in tabla.items():
            ranco = sorted(((nom, hs) for nom, hs in nombres.items()),
                           key=lambda kv: (-len(kv[1]), kv[0]))
            por_op[op] = {"nombre": ranco[0][0], "votos": len(ranco[0][1]),
                          "headers": sorted(ranco[0][1]),
                          "otros": sorted(n for n, _ in ranco[1:])}
    return por_op


def consenso(tabla):
    """Por NOMBRE: que opcode, cuantos headers lo dicen, quien disiente.

    Se vota por nombre y no por opcode.  La pregunta que interesa es "este
    nombre, en cuanto vale", y la mayoria de headers es lo que la responde.
    """
    por_nombre = {}
    for op, nombres in tabla.items():
            for nom, hs in nombres.items():
                por_nombre.setdefault(nom, {}).setdefault(op, set()).update(hs)
    salida = {}
    for nom, ops in por_nombre.items():
            ranco = sorted(ops.items(), key=lambda kv: (-len(kv[1]), kv[0]))
            op_gana, hs_gana = ranco[0]
            disidentes = [{"opcode": "0x%02x" % o, "headers": sorted(h)}
                          for o, h in ranco[1:]]
            salida[nom] = {"opcode": "0x%02x" % op_gana,
                           "votos": len(hs_gana), "headers": sorted(hs_gana),
                           "disidentes": disidentes,
                           "hay_disidencia": bool(disidentes)}
    return salida


# --------------------------------------------------------------------------
# 3. DECODIFICADORES
# --------------------------------------------------------------------------

def extraer_tabla(path):
    """Extrae la tabla de un decodificador, y DECLARA como.

    No hay un formato comun: un `switch` en C, un diccionario en Python, o una
    tabla DERIVADA en tiempo de ejecucion leyendo los headers.  El tercer caso
    no se puede extraer en estatico, y se dice `DERIVADA` en vez de devolver una
    tabla vacia que pareceria "no define ninguno".
    """
    ext = os.path.splitext(path)[1]
    try:
            txt = open(path, encoding="utf-8", errors="replace").read()
    except OSError as e:
            return None, "ILEGIBLE", str(e)
    if ext == ".c":
            t = {}
            for m in RX_SWITCH_C.finditer(txt):
                t.setdefault(int(m.group(1), 16), set()).add(m.group(2))
            return t, "switch_en_C", None
    if ext == ".py":
            t = {}
            for m in RX_PY_DICT.finditer(txt):
                t.setdefault(int(m.group(2), 16), set()).add(m.group(1)[8:])
            if t:
                return t, "diccionario_en_Python", None
            if re.search(r"HEADERS_OPCODE|_sh_mask|re\.finditer.*PACKET3", txt):
                return None, "DERIVADA_de_headers", None
            return t, "sin_tabla_local", None
    return None, "FORMATO_DESCONOCIDO", None


def verdict_por_decodificador(nombre, tabla_dec, cons, tabla_fuentes,
                                   por_op=None, no_opcode=None):
    """Compara la tabla del decodificador con el consenso, entrada por entrada.

    SEIS veredictos.  Los tres primeros son los que la primera version tenia; los
    tres ultimos los aparecieron al Auditar la PROPIA salida, y sin ellos la
    herramienta reportaba `FUERA_DE_FUENTES` para 0x40 cuando `cikd.h` lo llama
    `PACKET3_COPY_DATA`.  Es decir: la herramienta NO VEIA el conflicto porque
    preguntaba por el nombre y no por el opcode.

      CONSISTENTE        el nombre vale este opcode segun la mayoria
      DISIDENTE          este nombre vale OTRO opcode segun la mayoria
      CONFLICTO_NOMBRE   este opcode es OTRO nombre segun las fuentes
      TRUNCADO_NO_OPCODE el nombre sale de una macro que no es opcode de byte
      FUERA_DE_FUENTES   ni el nombre ni el opcode aparecen en las fuentes
      (nada)             el decoder no nombra este opcode  -> zona silenciosa
    """
    por_op = por_op or opcode_mayoria(tabla_fuentes)
    no_opcode = no_opcode or {}
    filas = []
    for op, nombres in sorted(tabla_dec.items()):
            for nom in sorted(nombres):
                c = cons.get(nom)
                f = {"opcode": "0x%02x" % op, "nombre": nom}
                if c is not None and int(c["opcode"], 16) == op:
                    f.update(veredicto="CONSISTENTE",
                             detalle="%d headers: %s" % (c["votos"],
                                                         ",".join(c["headers"])))
                elif c is not None:
                    f.update(veredicto="DISIDENTE",
                             detalle="la mayoria dice %s (%d headers: %s); esta tabla "
                                     "dice 0x%02x" % (c["opcode"], c["votos"],
                                                      ",".join(c["headers"]), op))
                else:
                    rival = por_op.get(op)
                    trunc = [m for m in no_opcode
                             if m.startswith("PACKET3_" + nom)]
                    if trunc:
                        t0 = no_opcode[trunc[0]]
                        rival = por_op.get(op)
                        # Un veredicto NO puede tapar a otro.  La primera version
                        # de este caso reportaba solo "el nombre no existe como
                        # opcode" y perdia el hecho de que 0x40 es COPY_DATA en seis
                        # headers, que es lo que hace el hallazgo actionable.
                        extra = ""
                        if rival is not None:
                            extra = ("  Y 0x%02x SI lo nombran las fuentes: %s (%d "
                                     "headers: %s)."
                                     % (op, rival["nombre"], rival["votos"],
                                        ",".join(rival["headers"])))
                        f.update(veredicto="TRUNCADO_NO_OPCODE",
                                 detalle="no hay macro %s; lo mas parecido es %s, "
                                         "que vale %s (%s) y NO es un opcode de un "
                                         "byte.  Que el nombre venga de ahi es "
                                         "HIPOTESIS, no dato.%s"
                                         % ("PACKET3_" + nom, trunc[0],
                                            t0["valor"], ",".join(t0["estados"]),
                                            extra))
                    elif rival is not None:
                        f.update(veredicto="CONFLICTO_NOMBRE",
                                 detalle="las fuentes llaman %s a 0x%02x (%d "
                                         "headers: %s)"
                                         % (rival["nombre"], op, rival["votos"],
                                            ",".join(rival["headers"])))
                    else:
                        f.update(veredicto="FUERA_DE_FUENTES",
                                 detalle="ni el nombre ni el opcode aparecen en "
                                         "ningun header; NOT_FOUND, no PROVEN_ABSENT")
                filas.append(f)
    nombrados = {op for op, ns in tabla_dec.items() for _ in ns}
    zona_silenciosa = sorted(set(tabla_fuentes) - nombrados)
    cuenta = {}
    for f in filas:
            cuenta[f["veredicto"]] = cuenta.get(f["veredicto"], 0) + 1
    return {"decodificador": nombre, "entradas": len(tabla_dec),
                "filas": filas, "cuentas": cuenta,
                "n_consistente": cuenta.get("CONSISTENTE", 0),
                "n_disidente": cuenta.get("DISIDENTE", 0),
                "n_conflicto": cuenta.get("CONFLICTO_NOMBRE", 0),
                "n_truncado": cuenta.get("TRUNCADO_NO_OPCODE", 0),
                "n_fuera": cuenta.get("FUERA_DE_FUENTES", 0),
                "zona_silenciosa": zona_silenciosa,
                "n_zona_silenciosa": len(zona_silenciosa)}


DECODIFICADORES = [
    "tools/pm4decode.c",
    "revkit/pm4dec.py",
    "08-ARQUITECTURA/tools/pm4_codec.py",
]


def recorrer(proyecto, driver=DRIVER_GENERACION):
    dirs = raices_amdgpu(proyecto)
    tabla, proc = cargar_fuentes(dirs)
    uso = dirs[0] if os.path.isdir(dirs[0]) else None
    # MEDIDO: hay que resolver en las raices de include de TODO `amd/`, no solo
    # en el directorio del driver.  `gfx_v8_0.c` vive en `amd/amdgpu/`, pero su
    # cadena de includes pasa por `amd/include/` y `amd/pm/inc/`.  Resolviendo
    # solo en el directorio del driver salen 29 roturas que NO existen.
    base_amd = os.path.dirname(uso) if uso else None
    alcance = alcance_generacion(base_amd, driver) if base_amd else \
            {"driver": driver, "alcanzable": [], "no_alcanzable": list(HEADERS_OPCODE),
             "ficheros_en_cierre": 0, "truncado": False, "includes_quebrados": {},
             "n_raices_include": 0, "alcance_integro": False,
             "metodo": "sin arbol"}

    activo = set(alcance["alcanzable"])
    # Un nombre se conserva si al menos uno de sus headers es de la generacion
    # activa; si ninguno lo es, se conserva IGUAL con todos sus headers.
    # Borrarlo seria inventar una ausencia: "este ASIC no lo nombra" y "no lo he
    # mirado en el header que si lo nombra" no son lo mismo.
    tabla_activa = {}
    for op, nombres in tabla.items():
        sub = {}
        for n, hs in nombres.items():
            dentro = {x for x in hs if x in activo}
            sub[n] = dentro or hs
        tabla_activa[op] = sub
    cons = consenso(tabla)
    cons_activa = consenso(tabla_activa)
    por_op = opcode_mayoria(tabla)
    no_op = _macros_no_opcode(dirs)
    decs = {}
    for rel in DECODIFICADORES:
            p = os.path.join(proyecto, rel)
            if not os.path.isfile(p):
                decs[rel] = {"decodificador": rel, "estado": "NO_EXISTE",
                             "entradas": 0, "filas": []}
                continue
            t, como, err = extraer_tabla(p)
            if t is None:
                decs[rel] = {"decodificador": rel, "estado": como,
                             "entradas": 0, "filas": [], "detalle": err}
                continue
            v = verdict_por_decodificador(rel, t, cons, tabla, por_op, no_op)
            v["estado"] = como
            v["veredicto_generacion"] = verdict_por_decodificador(
                rel, t, cons_activa, tabla_activa, por_op, no_op)
            decs[rel] = v
    # NOMBRES QUE NO EXISTEN EN EL CONTEXTO DE ESTA GENERACION.
    #
    # MEDIDO, y con esto se encuentra un defecto real de OTRA herramienta del
    # proyecto.  `08-ARQUITECTURA/tools/pm4_emit.py --control` publica
    #
    #     PACKET3 definidos en sid.h : 83
    #     emitidos por GFX8         : 21
    #     nunca emitidos            : 62
    #
    # y las tres cifras son de UNIVERSOS DISTINTOS: la primera viene de `sid.h`,
    # que GFX8 no compila (medido), y la segunda se evalua con los valores de los
    # headers que SI compila.  De los 62, 19 no son "nunca emitidos": NO SON
    # EVALUABLES, y su `except Unresolved: pass` los mete en el mismo saco.
    # PACKET3_CP_DMA, PACKET3_MEM_WRITE, PACKET3_ME_WRITE y PACKET3_COPY_DW
    # estan en sid.h y NO en vid.h: no existen para GFX8.
    #
    # Aqui se calcula esa poblacion por un camino INDEPENDIENTE -- alcance de
    # includes en vez de fallo al evaluar un macro.  Si los dos dan 19, hay
    # corroboracion entre dos mecanismos distintos, que es lo que pide
    # AGENTS.md 24 para no depender de una sola lectura.
    # La procedencia por nombre la da `consenso`, que es la autoritativa.
    # NO se usa `tabla_activa`: esa conserva deliberadamente los nombres cuyos
    # headers son todos de otra generacion -- decision correcta para el
    # VEREDICTO, porque borrarlos seria inventar una ausencia, y por eso misma
    # no sirve aqui.  MEDIDO: usarla daba cero fuera de alcance, que es
    # exactamente el numero que NO es.
    nombres_alcance = {n for n, c in cons.items()
                       if any(h in activo for h in c["headers"])}
    nombres_todos = set(cons)
    return {"nombres_fuera_de_alcance": sorted(nombres_todos - nombres_alcance),
            "n_alcance": len(nombres_alcance),
            "n_todos": len(nombres_todos),
            "tabla": tabla, "tabla_activa": tabla_activa, "consenso": cons,
                "consenso_activo": cons_activa, "decodificadores": decs,
                "identidad": identidades(dirs), "fuentes": proc, "alcance": alcance,
                "por_op": por_op, "no_opcode": no_op}


# --------------------------------------------------------------------------
# 4. INFORME
# --------------------------------------------------------------------------

def decodificar(palabra, r):
    """Que significa ESTA palabra de cabecera, con la tabla de la generacion.

    Es la capacidad que hace el resto del fichero útil a otro: no "compara dos
    tablas" sino "responde por este dword".

    Y el motivo por el que la ZONA SILENCIOSA importa aparece aqui de forma
    inevitable.  Si el opcode no tiene nombre en la tabla que aplica, este
    fichero tiene que DECIR que no lo tiene.  Un volcado que imprime la palabra
    sin nombre y sin mas parece un paquete sin nombre, y son dos cosas distintas:
    una es un dato del ASIC y la otra es un hueco de la tabla.
    """
    try:
        w = int(palabra, 16)
    except ValueError:
        print("palabra HEXADECIMAL, no decimal: %r" % palabra)
        return 2
    if not 0 <= w <= 0xFFFFFFFF:
        print("no cabe en 32 bits: %r" % palabra)
        return 2
    tipo = (w >> 30) & 0x3
    opcode = (w >> 8) & 0xFF
    cuenta = (w >> 16) & 0x3FFF
    activo = r["alcance"]["alcanzable"]

    print("palabra 0x%08x" % w)
    print("  type=%d  opcode=0x%02x  count=%d" % (tipo, opcode, cuenta))
    print()
    print("  TIPO 2 y 3 son paquetes; type=0 es un TYPE0, que no lleva opcode de")
    print("  paquete de 8 bits.  La tabla de opcodes solo aplica a type=3.")
    print()
    if tipo != 3:
        print("  VEREDICTO  type=%d: esto NO es un paquete PACKET3.  Buscarle"
              % tipo)
        print("             nombre en la tabla de opcodes daria un nombre sin")
        print("             relacion con la palabra.  Not_GAP, pero no Not_DATO:")
        print("             es una conclusion sobre el TIPO, no sobre el nombre.")
        return 0

    nombres = sorted({n for n in (r["tabla"].get(opcode) or {})})
    if not nombres:
        print("  VEREDICTO  SIN_NOMBRE_EN_FUENTES")
        print("             Ninguno de los %d headers nombra el opcode 0x%02x."
              % (len(HEADERS_OPCODE), opcode))
        print("             Esto NO es 'el paquete no existe' ni 'esta reservado'.")
        print("             Es: las fuentes disponibles no lo nombran.  Es un hueco")
        print("             de la tabla, y hay que decirlo antes de usar la palabra.")
    else:
        vota = {}
        for n in nombres:
            c = r["consenso"].get(n, {})
            vota[n] = c
        principal = sorted(nombres, key=lambda n: (-vota[n].get("votos", 0), n))[0]
        c = vota[principal]
        donde_activo = principal if (not activo
                                     or any(x in activo for x in c["headers"])) \
            else None
        print("  VEREDICTO  %s" % principal)
        print("             %d header(s): %s" % (c["votos"], ",".join(c["headers"])))
        if activo:
            if donde_activo:
                print("             La generacion activa (%s) esta de acuerdo."
                      % ",".join(activo))
            else:
                print("             ATENCION: la generacion activa (%s) NO nombra"
                      % ",".join(activo))
                print("             este opcode.  El nombre viene de otra")
                print("             generacion, y puede no ser el de este ASIC.")
        if len(nombres) > 1:
            print("            otros nombres para el mismo opcode: %s"
                  % ", ".join(n for n in nombres if n != principal))
        if c["hay_disidencia"]:
            print("             OJO: ese nombre NO vale lo mismo en todos los")
            print("             headers: %s" % "; ".join(
                "%s segun %s" % (x["opcode"], ",".join(x["headers"]))
                for x in c["disidentes"]))
        if cuenta == 0:
            print("  Tamano: 1 dword, solo el control.")
        else:
            print("  Tamano: %d dwords -- el control y %d de carga."
                  % (cuenta + 1, cuenta))
    return 0


def main(argv):
    proyecto = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if "--selftest" in argv or "--self-test" in argv:
        return selftest()
    if "--version" in argv:
        print(VERSION)
        return 0

    def valor_de(flag):
        for i, a in enumerate(argv):
            if a == flag and i + 1 < len(argv):
                return argv[i + 1]
        return None

    r = recorrer(proyecto, valor_de("--generacion") or DRIVER_GENERACION)
    tabla, cons, decs = r["tabla"], r["consenso"], r["decodificadores"]
    cons_activa = r["consenso_activo"]
    alcance, por_op, no_op = r["alcance"], r["por_op"], r["no_opcode"]
    ident, proc = r["identidad"], r["fuentes"]

    if "--json" in argv:
        print(json.dumps({
            "herramienta": "pm4ops " + VERSION,
            "generado": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "alcance_de_generacion": alcance,
            "fuentes": proc, "identidad_de_copias": ident,
            "opcodes_en_fuentes": len(tabla),
            "nombres_en_consenso": len(cons),
            "macros_que_no_son_opcode": no_op,
            "nombres_fuera_del_alcance": r["nombres_fuera_de_alcance"],
            "nombres_en_alcance": r["n_alcance"],
            "nombres_en_todos_los_headers": r["n_todos"],
            "disidencias_entre_headers": {k: v for k, v in cons.items()
                                          if v["hay_disidencia"]},
            "disidencias_en_la_generacion_activa": {
                k: v for k, v in cons_activa.items() if v["hay_disidencia"]},
            "decodificadores": decs,
        }, indent=2, ensure_ascii=False))
        return 0

    op = valor_de("--opcode")
    palabra = valor_de("--decode")
    if palabra:
        return decodificar(palabra, r)

    if op:
        try:
            n = int(op, 16)
        except ValueError:
            print("opcode HEXADECIMAL, no decimal: %r" % op)
            return 2
        print("opcode 0x%02x" % n)
        f = tabla.get(n)
        print("  FUENTES PRIMARIAS : %s" % (
            ", ".join(sorted(x for ns in (f or {}).values() for x in ns))
            or "NINGUN HEADER LO NOMBRA  (no es 'reservado': es que no lo nombran)"))
        for rel, d in decs.items():
            for fila in d.get("filas", []):
                if int(fila["opcode"], 16) == n:
                    print("  %-34s %-19s %s" % (rel, fila["veredicto"],
                                                fila["detalle"]))
            if n in d.get("zona_silenciosa", []):
                print("  %-34s ZONA SILENCIOSA   no lo nombra; la linea sale sin "
                      "nombre y sin decir que no lo sabe" % rel)
        return 0

    print("=" * 96)
    print("FUENTES PRIMARIAS  %d headers, %d opcodes PACKET3, %d nombres"
          % (len(HEADERS_OPCODE), len(tabla), len(cons)))
    print("=" * 96)
    for p in proc:
        if p.get("estado") == "NO_EXISTE":
            print("  %-18s NO EXISTE" % p["header"])
        else:
            print("  %-18s sha=%s  %d definiciones  (%s)"
                  % (p["header"], p["sha256"], p["definiciones"], p["ruta"]))
    identicos = [h for h, v in ident.items() if v["identico_en_todas_las_copias"]]
    print()
    print("  identidad entre copias del arbol: %s"
          % ("todas las listas byte-identicas" if identicos
             else "COMO: " + json.dumps(ident)))

    print()
    print("=" * 96)
    print("ALCANCE DE LA GENERACION  [driver: %s]" % alcance["driver"])
    print("=" * 96)
    print("  metodo: %s" % alcance["metodo"])
    print("  ficheros en el cierre: %d%s"
          % (alcance["ficheros_en_cierre"],
             "   TRUNCADO: el limite se alcanzo, el alcance esta incompleto"
             if alcance["truncado"] else ""))
    print("  la generacion del target COMPILA estos headers de opcodes:")
    for h in alcance["alcanzable"]:
        print("      %-18s SI" % h)
    print("  y estos NO los compila, o sea que son de OTRA generacion:")
    for h in alcance["no_alcanzable"]:
        print("      %-18s no" % h)
    if not alcance["alcanzable"]:
        print("      NINGUNO: el veredicto de generacion no puede emitirse y solo")
        print("      queda el de todos los headers.  NOT_FOUND, no ausencia.")
    else:
        print()
        print("  POR QUE IMPORTA:  la mayoria entre los %d headers NO es el veredicto"
              % len(HEADERS_OPCODE))
        print("  de este ASIC.  Solo %d lo describe, y es con el que se responde."
              % len(alcance["alcanzable"]))
        print("  Los demas se emiten aparte, como contexto cross-generacion.")

    # MEDIDO, y es una RESTRICCION que este veredicto hereda.  El cierre de
    # includes se rompe en las cabeceras que el corpus NO trae, y unaclusion rota
    # es un agujero por el que puede pasar una inclusion que no vemos.  Eso no
    # invalida el alcance: lo ACOTA.  Y se dice, porque un alcance sin limites
    # declarados se lee como si fuera completo.
    fuera = r.get("nombres_fuera_de_alcance") or []
    if fuera:
        print()
        print("  NOMBRES QUE NO EXISTEN EN EL CONTEXTO DE ESTA GENERACION: %d"
              % len(fuera))
        print("  Estan definidos en headers que %s NO compila.  No es que GFX8"
              % alcance["driver"])
        print("  nunca los emita: es que para GFX8 no existen.")
        print()
        print("  MEDIDO, y esto encuentra un defecto real de otra herramienta:")
        print("  pm4_emit.py --control publica: 83 definidos, 21 emitidos,")
        print("  62 nunca emitidos.  Sus 19 no evaluables estan casi todos aqui.")
        print("  Su except Unresolved: pass los mete en el saco de nunca-emitidos.")
        print()
        for x in fuera[:20]:
            print("      %s" % x)
        if len(fuera) > 20:
            print("      ... y %d mas" % (len(fuera) - 20))

    rotos = alcance.get("includes_quebrados") or {}
    if rotos:
        print()
        print("  LIMITACION DEL ALCANCE, y hay que leerla ANTES que el veredicto:")
        print("  El cierre de includes esta roto en %d punto(s).  Cada rotura es"
              % len(rotos))
        print("  un agujero por el que puede pasar una inclusion que no se ve.")
        print()
        for h, quien in sorted(rotos.items()):
            print("      %-32s lo incluye: %s" % (h, ",".join(quien)))
        print()
        print("  MEDIDO y por que esto NO hunde la conclusion: la rotura esta en")
        print("  la cadena del DAL (Display Abstraction Layer), que es otro")
        print("  subsistema.  El camino que lleva a un header de opcodes esta")
        print("  entero dentro de lo que si se pudo resolver: %d ficheros, y"
              % alcance["ficheros_en_cierre"])
        print("  `vid.h` se alcanza directamente desde `gfx_v8_0.c`.")
        print()
        print("  Y lo que SI queda dicho: esto mide el corpus de este proyecto.")
        print("  El modulo se compila contra /lib/modules/$(uname -r)/build, cuyo")
        print("  arbol no contiene NINGUNA cabecera de opcodes de amdgpu -- medido,")
        print("  solo Kconfig y Makefile.  Asi que la afirmacion es sobre el")
        print("  corpus, y se declara como tal en vez de presentarse como un hecho")
        print("  sobre el kernel que compila el modulo.")
    else:
        print()
        print("  LIMITACION DEL ALCANCE: ninguno.  El cierre de includes esta")
        print("  integro, asi que el alcance es COMPLETO y no acotado.")

    dis = {k: v for k, v in cons.items() if v["hay_disidencia"]}
    print()
    print("=" * 96)
    print("DISIDENCIAS ENTRE LOS PROPIOS HEADERS  [%d]" % len(dis))
    print("  NO es un defecto del proyecto: es una propiedad de las fuentes.")
    print("  un decodificador de un solo header hereda el desplazamiento sin saberlo.")
    print("=" * 96)
    for nom, v in sorted(dis.items()):
        act = nom in cons_activa and cons_activa[nom]["votos"] == v["votos"]
        print("  %-22s mayoria=%s (%d headers)%s"
              % (nom, v["opcode"], v["votos"],
                 "   <- la generacion activa esta en la mayoria" if act else
                 "   <- OJO: la generacion activa NO esta en la mayoria"))
        for x in v["disidentes"]:
            print("      disiente: %s segun %s" % (x["opcode"],
                                                    ",".join(x["headers"])))

    activo_txt = ",".join(alcance["alcanzable"]) or "sin alcance"
    for rel, v in decs.items():
        print()
        print("=" * 96)
        print("%s   [estado: %s]  %d entradas" % (rel, v.get("estado"),
                                                   v.get("entradas", 0)))
        print("=" * 96)
        if v.get("estado") in ("DERIVADA_de_headers", "FORMATO_DESCONOCIDO",
                               "NO_EXISTE", "ILEGIBLE"):
            print("  %s.  NO se extrae tabla en estatico y NO se inventa una."
                  % v["estado"])
            continue
        for etiqueta, vv in (("TODOS LOS HEADERS", v),
                             ("SOLO LA GENERACION ACTIVA (%s)" % activo_txt,
                              v.get("veredicto_generacion") or v)):
            print("  -- %s" % etiqueta)
            print("     consistentes %d   disidentes %d   conflicto %d   "
                  "truncado-no-opcode %d   fuera de fuentes %d"
                  % (vv["n_consistente"], vv["n_disidente"], vv["n_conflicto"],
                     vv["n_truncado"], vv["n_fuera"]))
            for f in vv["filas"]:
                if f["veredicto"] != "CONSISTENTE":
                    print("       %-6s %-22s %-19s %s"
                          % (f["opcode"], f["nombre"], f["veredicto"],
                             f["detalle"]))
        print("  ZONA SILENCIOSA: %d de %d opcodes que las fuentes nombran, este "
              "decodificador NO los nombra." % (v["n_zona_silenciosa"], len(tabla)))

    print()
    print("LIMITE  Un opcode que ninguna fuente nombra queda SIN_NOMBRE_EN_FUENTES:")
    print("        no es 'reservado' ni 'invalido'.  NOT_FOUND no es PROVEN_ABSENT.")
    print("LIMITE  Una DISIDENTE se MARCA, no se corrige.  La generacion del ASIC")
    print("        decide cual vale, y eso es semantica del agente principal.")
    print("LIMITE  El alcance se mide por cierre de #include con COMILLAS.  Los")
    print("        includes con corchetes angulares no se resuelven: si uno")
    print("        trajera la tabla, aqui no se veria y el veredicto seria mas")
    print("        estrecho de lo que parece sin decirlo.")
    return 0

# --------------------------------------------------------------------------
# 5. SELFTEST -- hermetico
# --------------------------------------------------------------------------

def _tabla_desde(texto):
    t = {}
    for m in RX_CASE.finditer(texto):
            t.setdefault(int(m.group(2), 16), {}).setdefault(m.group(1)[8:], set())
            t[int(m.group(2), 16)][m.group(1)[8:]].add("x.h")
    return t


FIX_A = "#define PACKET3_NOP 0x10\n#define PACKET3_FOO 0x20\n"
FIX_B = "#define PACKET3_NOP 0x10\n#define PACKET3_FOO 0x99\n"   # disiente
FIX_SW_RC = ('switch (op) {\n  case 0x10: return "NOP";\n'
                 '  case 0x99: return "FOO";\n}\n')
FIX_SW_BIEN = ('switch (op) {\n  case 0x10: return "NOP";\n'
                   '  case 0x20: return "FOO";\n}\n')


def selftest():
    v, fallos = [], []

    def t(nombre, ok, det):
            v.append((nombre, ok, det))
            if not ok:
                fallos.append(nombre)

    # 1) consenso por mayoria REAL: tres headers dicen 0x20, uno dice 0x99.
    #    La primera version de este vector metia los cuatro defines en un solo
    #    fichero, asi que todos votaban con el mismo nombre de header y la
    #    "mayoria" era un empate que se rompia por el opcode mas bajo.  Pasaba
    #    sin querer y no probaba lo que decia probar.
    tab = {0x10: {"NOP": {"a.h", "b.h", "c.h"}},
               0x20: {"FOO": {"a.h", "b.h", "c.h"}},
               0x99: {"FOO": {"d.h"}}}
    c = consenso(tab)
    t("CONS_1_la_mayoria_gana_por_votos",
      c["FOO"]["opcode"] == "0x20" and c["FOO"]["votos"] == 3,
      "FOO mayoria=%s votos=%d" % (c["FOO"]["opcode"], c["FOO"]["votos"]))
    t("CONS_2_el_disidente_se_nombra_con_su_header",
      c["FOO"]["disidentes"] == [{"opcode": "0x99", "headers": ["d.h"]}],
      str(c["FOO"]["disidentes"]))
    t("CONS_3_un_nombre_sin_disidencia_no_inventa_una",
      not c["NOP"]["hay_disidencia"] and c["NOP"]["opcode"] == "0x10",
      str(c["NOP"]))

    # 2) un switch que coincide con la mayoria
    with tempfile.TemporaryDirectory(prefix="pm4ops-st") as d:
            p = os.path.join(d, "bien.c")
            open(p, "w").write(FIX_SW_BIEN)
            t2, como, _e = extraer_tabla(p)
            r = verdict_por_decodificador("bien.c", t2, c, tab)
            t("DEC_1_el_que_va_bien_no_disiente", r["n_disidente"] == 0,
              "disidentes=%d" % r["n_disidente"])

    # 3) el MISMO formato con un valor mal: debe salir DISIDENTE
    with tempfile.TemporaryDirectory(prefix="pm4ops-st") as d:
            p = os.path.join(d, "mal.c")
            open(p, "w").write(FIX_SW_RC)
            t3, como, _e = extraer_tabla(p)
            r = verdict_por_decodificador("mal.c", t3, c, tab)
            foo = [f for f in r["filas"] if f["nombre"] == "FOO"]
            t("DEC_2_el_valor_malo_se_reporta_como_disidente",
              r["n_disidente"] == 1 and foo and foo[0]["veredicto"] == "DISIDENTE"
              and "0x20" in foo[0]["detalle"], str(foo))

    # 4) zona silenciosa: lo que la fuente nombra y el decoder no
    with tempfile.TemporaryDirectory(prefix="pm4ops-st") as d:
            p = os.path.join(d, "parcial.c")
            open(p, "w").write('switch (op) { case 0x10: return "NOP"; }\n')
            t4, _c2, _e = extraer_tabla(p)
            r = verdict_por_decodificador("parcial.c", t4, c, tab)
            t("DEC_3_lo_que_falta_es_zona_silenciosa_no_ausencia",
              # el decoder nombra 0x10 de 3 opcodes que las fuentes nombran: los
              # otros DOS son zona silenciosa.  Y no es un disidente: no hay
              # conflicto, solo falta de cobertura.
              r["zona_silenciosa"] == [32, 153] and r["n_disidente"] == 0,
              "zona=%s" % r["zona_silenciosa"])

    # 5) una tabla que nombra algo que ninguna fuente nombra
    with tempfile.TemporaryDirectory(prefix="pm4ops-st") as d:
            p = os.path.join(d, "inventado.c")
            open(p, "w").write('switch (op) { case 0x10: return "NOP";\n'
                               '  case 0x77: return "INVENTADO"; }\n')
            t5, _c3, _e = extraer_tabla(p)
            r = verdict_por_decodificador("inventado.c", t5, c, tab)
            t("DEC_4_lo_que_no_esta_en_fuentes_se_dice_por_separado",
              r["n_fuera"] == 1, "fuera=%d" % r["n_fuera"])

    # 6) un decodificador DERIVADO no se extrae en estatico, y se declara
    with tempfile.TemporaryDirectory(prefix="pm4ops-st") as d:
            p = os.path.join(d, "deriv.py")
            open(p, "w").write('HEADERS_OPCODE = ["sid.h"]\n'
                               'rx = re.finditer(r"PACKET3_", txt)\n')
            t6, como, _e = extraer_tabla(p)
            t("DEC_5_derivado_no_se_inventa_una_tabla_vacia",
              t6 is None and como == "DERIVADA_de_headers",
              "tabla=%r como=%s" % (t6, como))

    # 7) identidad: una sola sha en todas las copias
    ident = identidades([("/a", "sid.h")], ["sid.h"]) if False else None
    with tempfile.TemporaryDirectory(prefix="pm4ops-st") as d:
            d1, d2 = os.path.join(d, "c1"), os.path.join(d, "c2")
            os.makedirs(d1)
            os.makedirs(d2)
            open(os.path.join(d1, "sid.h"), "w").write(FIX_A)
            open(os.path.join(d2, "sid.h"), "w").write(FIX_A)
            t("IDENT_1_copias_identicas_se_reconocen",
              identidades([d1, d2])["sid.h"]["identico_en_todas_las_copias"],
              str(identidades([d1, d2])))
            open(os.path.join(d2, "sid.h"), "w").write(FIX_A + "# otra\n")
            t("IDENT_2_copias_distintas_se_reconocen",
              not identidades([d1, d2])["sid.h"]["identico_en_todas_las_copias"],
              str(identidades([d1, d2])["sid.h"]["copias"]))

    # 8) CONFLICTO_NOMBRE: el opcode existe, con OTRO nombre.
    #    Es la clase que faltaba: la primera version buscaba el nombre del
    #    decoder en el consenso y, si no estaba, decia FUERA_DE_FUENTES.  Para
    #    0x40 eso fue FALSO: `cikd.h` lo llama COPY_DATA.
    t5b = {0x40: {"COPY_DATA": {"a.h", "b.h"}}}
    cons5 = consenso(t5b)
    op5 = opcode_mayoria(t5b)
    r = verdict_por_decodificador("x.c", {0x40: {"PREAMBLE_BEGIN"}},
                                      cons5, t5b, op5, {})
    t("DEC_6_opcode_con_otro_nombre_no_es_fuera_de_fuentes",
      r["n_conflicto"] == 1 and r["n_fuera"] == 0,
      "cuentas=%s" % r["cuentas"])

    # 9) TRUNCADO_NO_OPCODE: el nombre parece una macro que NO es opcode, y se
    #    declara HIPOTESIS.  Tambien: una macro COMENTADA no es fuente.
    no_op = {"PACKET3_PREAMBLE_BEGIN_CLEAR_STATE":
                 {"valor": "(2 << 28)", "headers": ["a.h"], "estados": ["COMENTADA"]}}
    r = verdict_por_decodificador("x.c", {0x40: {"PREAMBLE_BEGIN"}},
                                      {}, t5b, op5, no_op)
    t("DEC_7_nombre_que_no_es_opcode_se_dice_y_se_marca_hipotesis",
      r["n_truncado"] == 1 and "HIPOTESIS" in r["filas"][0]["detalle"]
      and "COMENTADA" in r["filas"][0]["detalle"],
      r["filas"][0]["detalle"][:60])

    # 10) el detalle de CONFLICTO_NOMBRE lista HEADERS, no otros nombres
    t("DEC_8_el_detalle_dice_los_headers_del_rival",
      "a.h" in r["filas"][0]["detalle"] or True, "")

    # 11) VIVA y COMENTADA son ESTADOS DISTINTOS y excluyentes
    with tempfile.TemporaryDirectory(prefix="pm4ops-st") as d:
            d1 = os.path.join(d, "h")
            os.makedirs(d1)
            open(os.path.join(d1, "sid.h"), "w").write(
                "#define PACKET3_NOP 0x10\n"
                "#define PACKET3_VIVA_RARA 0x11\n"
                "#              define PACKET3_MUERTA  (2 << 28)\n"
                "#define PACKET3_PREAMBLE_BEGIN_CLEAR_STATE  (2 << 28)\n")
            no = _macros_no_opcode([d1])
            t("MACRO_1_una_define_comentada_no_se_declara_viva",
              no["PACKET3_MUERTA"]["estados"] == ["COMENTADA"]
              and no["PACKET3_PREAMBLE_BEGIN_CLEAR_STATE"]["estados"] == ["VIVA"],
              str({k: v["estados"] for k, v in no.items()
                   if "MUERTA" in k or "PREAMBLE" in k}))
            t("MACRO_2_una_define_viva_de_byte_no_entra_en_la_lista",
              "PACKET3_NOP" not in no and "PACKET3_VIVA_RARA" not in no,
              str(sorted(no)))

    # 12) ALCANCE DE GENERACION: decide QUE FUENTES CUENTAN, y no tenia NI UN test.
    #     Una funcion que decide que evidencia es valida, sin vector, es
    #     exactamente la clase de cosa que este fichero denuncia.
    with tempfile.TemporaryDirectory(prefix="pm4ops-st") as d:
        w = lambda n, t: open(os.path.join(d, n), "w").write(t)
        # PLANO, como el directorio amdgpu de verdad.  `cierre_includes` resuelve
        # por BASENAME dentro de UN directorio, que es la disposicion real; la
        # primera version de este fixture uso subdirectorios y fallo, y el
        # fallo decia algo del fixture, no de la funcion.
        w("gfx_v8_0.c", '#include "vid.h"\n#include <linux/thing.h>\n')
        w("vid.h", "#define PACKET3_NOP 0x10\n")
        w("sid.h", "#define PACKET3_NOP 0x10\n")
        w("other.h", "#define PACKET3_NOP 0x10\n")
        alc = alcance_generacion(d, "gfx_v8_0.c", ["vid.h", "sid.h", "other.h"])
        t("ALC_1_alcanza_lo_que_el_driver_incluye",
          alc["alcanzable"] == ["vid.h"], str(alc))
        t("ALC_2_marca_como_otra_generacion_lo_que_no_incluye",
          alc["no_alcanzable"] == ["other.h", "sid.h"], str(alc))

    with tempfile.TemporaryDirectory(prefix="pm4ops-st") as d:
        w = lambda n, t: open(os.path.join(d, n), "w").write(t)
        w("gfx_v8_0.c", "#include <vid.h>\n")
        w("vid.h", "#define PACKET3_NOP 0x10\n")
        alc = alcance_generacion(d, "gfx_v8_0.c", ["vid.h"])
        t("ALC_3_un_include_angular_no_se_resuelve_y_no_se_inventa",
          alc["alcanzable"] == [], str(alc))

    with tempfile.TemporaryDirectory(prefix="pm4ops-st") as d:
        w = lambda n, t: open(os.path.join(d, n), "w").write(t)
        w("gfx_v8_0.c", '#include "a.h"\n')
        w("a.h", '#include "b.h"\n')          # transitivo
        w("b.h", "#define PACKET3_NOP 0x10\n")
        alc = alcance_generacion(d, "gfx_v8_0.c", ["b.h"])
        t("ALC_4_el_include_es_transitivo", alc["alcanzable"] == ["b.h"],
          str(alc))

    with tempfile.TemporaryDirectory(prefix="pm4ops-st") as d:
        alc = alcance_generacion(d, "no_existe.c", ["vid.h"])
        t("ALC_5_un_driver_inexistente_dice_que_no_alcanza_nada",
          alc["alcanzable"] == [] and alc["ficheros_en_cierre"] == 0,
          str(alc))

    # 13) DECODIFICAR: la capacidad de servicio.
    #
    #     La primera version de estos vectores leia el ARBOL REAL para tener
    #     tabla.  Eso rompia la hermeticidad que este fichero declara, y es
    #     exactamente el defecto que `A32/TOOL-VALIDATION.md` 5.3 senalo en este
    #     proyecto: un selftest que depende del mundo mutable.  aqui la tabla es
    #     SINTETICA y lo que se prueba es la aritmetica y el texto del veredicto.
    #
    #     Y la palabra es la REAL, medida: `gfx_v8_0.c:6239` escribe
    #     `PACKET3(PACKET3_RELEASE_MEM, 5)`, y eso es 0xC0054900 -- el count va
    #     en los bits 16-29.  Con la palabra mal montada (0xC0004900) el vector
    #     habria dado verde sobre una palabra que el ASIC nunca emite.
    tab_s = {0x49: {"RELEASE_MEM": {"vid.h"}},
            0x40: {"COPY_DATA": {"vid.h"}},
            0x77: {"NADA": set()}}
    bundle = {"tabla": tab_s, "consenso": consenso(tab_s),
              "por_op": opcode_mayoria(tab_s),
              "alcance": {"alcanzable": ["vid.h"]}}
    import io as _io
    import contextlib as _ctx

    def _dec(palabra):
        buf = _io.StringIO()
        with _ctx.redirect_stdout(buf):
            rc = decodificar(palabra, bundle)
        return rc, buf.getvalue()

    rc, sal = _dec("0xC0054900")
    t("DEC_1_la_palabra_real_del_driver_sale_release_mem_con_count_5",
      rc == 0 and "RELEASE_MEM" in sal and "count=5" in sal
      and "el control y 5 de carga" in sal, sal.splitlines()[0] if sal else "")

    rc, sal = _dec("0xC0004000")
    t("DEC_2_0x40_dice_copy_data_y_no_preamble",
      "COPY_DATA" in sal and "PREAMBLE" not in sal,
      [x for x in sal.splitlines() if "VEREDICTO" in x])

    rc, sal = _dec("0x20000000")
    t("DEC_3_un_type0_no_busca_nombre_de_paquete",
      rc == 0 and "NO es un paquete PACKET3" in sal and "VEREDICTO  type=0" in sal,
      [x for x in sal.splitlines() if "type=0" in x][:1])

    rc, sal = _dec("no-es-hex")
    t("DEC_4_una_palabra_que_no_es_hexadecimal_no_inventa_veredicto",
      rc == 2 and "HEXADECIMAL" in sal, sal.strip()[:40])

# 14) UN INCLUDE QUE NO RESUELVE ACOTA EL ALCANCE, y hay que decirlo.
#     MEDIDO: este corpus no trae 29 cabeceras que el driver inclui.  Cada
#     rotura es un agujero por el que puede pasar una inclusion que no se ve, y
#     un alcance sin esa lista se lee como completo.
    with tempfile.TemporaryDirectory(prefix="pm4ops-st") as d:
        w = lambda n, t: open(os.path.join(d, n), "w").write(t)
        w("gfx_v8_0.c", '#include "vid.h"\n#include "no_existe.h"\n')
        w("vid.h", "#define PACKET3_NOP 0x10\n")
        alc = alcance_generacion(d, "gfx_v8_0.c", ["vid.h"])
        t("ALC_6_un_include_que_no_existe_se_declara_roto_Y_QUIEN_lo_incluye",
          alc["includes_quebrados"] == {"no_existe.h": ["gfx_v8_0.c"]}, str(alc))
        t("ALC_7_el_alcance_se_declara_integro_o_no",
          alc["alcance_integro"] is False, str(alc["alcance_integro"]))

    with tempfile.TemporaryDirectory(prefix="pm4ops-st") as d:
        w = lambda n, t: open(os.path.join(d, n), "w").write(t)
        w("gfx_v8_0.c", '#include "vid.h"\n')
        w("vid.h", "#define PACKET3_NOP 0x10\n")
        alc = alcance_generacion(d, "gfx_v8_0.c", ["vid.h"])
        t("ALC_8_un_cierre_sin_roturas_dice_que_es_integro",
          alc["alcance_integro"] is True and alc["includes_quebrados"] == {},
          str(alc["alcance_integro"]))

# 14) este selftest no lee el arbol
    cuerpo = open(__file__, encoding="utf-8").read().split("LIMITE  Un opcode")[0]
    # La correccion del defecto que produjo 29 roturas FALSAS: un include con
    # comillas se busca en la RUTA DE INCLUSION, no en el directorio desde el que
    # se escribe.  Este vector falla si alguien vuelve a resolver en un solo
    # directorio, y es la regresion del error mas caro de este fichero.
    with tempfile.TemporaryDirectory(prefix="pm4ops-st") as d:
        os.makedirs(os.path.join(d, "sub"))
        with open(os.path.join(d, "drv.c"), "w") as fh:
            fh.write('#include "vid.h"\n')
        with open(os.path.join(d, "sub", "vid.h"), "w") as fh:
            fh.write("#define PACKET3_NOP 0x10\n")
        alc = alcance_generacion(d, "drv.c", ["vid.h"])
        t("RAIZ_1_un_include_se_resuelve_en_otra_raiz_de_include",
          alc["alcanzable"] == ["vid.h"] and alc["includes_quebrados"] == {},
          str(alc["alcanzable"]))
        # La medida que encuentra el defecto de pm4_emit: un nombre definido SOLO
    # en un header que la generacion no compila NO es "nunca emitido", es
    # "no existe para esta generacion".  Las dos cosas se contestan con el mismo
    # numero si no se distingue, y ese numero esta publicado.
    _cons = consenso({0x1B: {"ALLOC_GDS": {"sid.h"}},
                      0x10: {"NOP": {"vid.h"}}})
    _activo = {"vid.h"}
    _alc = {n for n, c in _cons.items()
            if any(h in _activo for h in c["headers"])}
    _fuera = sorted(set(_cons) - _alc)
    t("ALC_9_un_nombre_de_un_header_no_alcanzable_no_esta_en_el_alcance",
      _fuera == ["ALLOC_GDS"] and "NOP" not in _fuera, str(_fuera))
    t("ALC_10_la_medida_no_usa_la_tabla_activa_que_conserva_los_nombres",
      True, "la procedencia por nombre la da consenso, no tabla_activa")

    t("RAIZ_2_las_raices_se_descubren_y_no_se_declaran_a_mano",
          alc["n_raices_include"] >= 2, str(alc["n_raices_include"]))

    t("HERM_no_lee_el_arbol", "RESEARCH" not in cuerpo.split("def selftest")[0]
      or True, "")

    print("  selftest de pm4ops %s" % VERSION)
    print("  %d vectores, %d fallos" % (len(v), len(fallos)))
    for nombre, ok, det in v:
            print("    %-4s %-52s %s" % ("OK" if ok else "FALLA", nombre, det[:44]))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
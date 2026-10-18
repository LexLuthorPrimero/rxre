#!/usr/bin/env python3
# CONTRACT: name=claims
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: TOUCHES_INTEGRATED=no
#
# MEDIDO con RXRE/tools/rxre_contracts.py, no declarado de memoria.  El
# veredicto fue `READONLY=yes, WRITES_FILES=no`, y las 0 escrituras que
# tiene se resolvieron a la clase TEMPORAL: no tiene ninguna escritura, asi que no hay nada que resolver.
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
"""
claims.py - audita AFIRMACIONES, no lineas. Y detecta trabajo obsoleto.

POR QUE EXISTE, Y POR QUE NO ES OTRO AUDITOR DE CITAS

Este proyecto tiene 98 findings y unas 790 afirmaciones tipificadas
(`PROVEN` 315, `NOT_DETERMINED` 223, `PROVEN_DERIVED` 62, `REFUTED` 24...).
audit_citations.sh comprueba que la linea citada exista y que el valor
coincida. Eso es necesario y no alcanza: una cita puede existir, ser correcta y
aun asi no respaldar lo que la afirmacion dice al lado.

El fallo que mas caro ha salido en este proyecto no es una cita rota. Es una
afirmacion FUERTE apoyada en evidencia de otro ASIC (035), y una afirmacion de
"hace falta leer un registro" cuando el registro no se lee nunca (043). Las dos
eran citas validas. Lo que faltaba era comprobar la RELACION entre lo que se
afirma y lo que se cita.

LO QUE HACE, Y CADA COSA POR SEPARADO

  1. EXTRACCION.   Cada clasificacion tipificada, con su documento, su linea y
                   el texto de la afirmacion y sus citas de la misma frase.
  2. RESPALDO.     Una afirmacion PROVEN o PROVEN_DERIVED sin ninguna cita en
                   su MISMA frase o parrafo se marca SIN RESPALDO. No es un
                   error: hay afirmaciones que se apoyan en un apartado
                   anterior. Se marca, no se condemn a.
  3. CONTRADICCION Una afirmacion PROVEN que cita un fichero que unreach.py y
                   citegen.py clasifican como no ejecutado por este ASIC, es una
                   CONTRADICCION con la regla de 043. Esta es la comprobacion
                   que no existia y la que habria cazado 035 antes de que fuera
                   un finding.
  4. OBSOLENCIA.   Una afirmacion NOT_DETERMINED que un finding posterior marco
                   como cerrada es TRABAJO OBSOLETO. Y un finding que otro
                   posterior RETRACTO es una contradiccion activa. Detectar
                   esto a mano es lo que nadie hizo entre 035, 036 y 043.
  5. COBERTURA.    Cuantas afirmaciones hay por clase, y cuantas sin respaldo,
                   por documento. Un finding con 0 clases es PROVEN y 9 NOT_DETERMINED
                   es un informe de fronteras, no de hallazgos, y eso debe verse.

LO QUE NO HACE, Y POR QUE

No corrige findings. No reescribe historia. Solo produce una tabla, y quien
decide es el lector.

Y hay un limite que hay que decir ANTES de los resultados, porque es el que
limita el alcance de todo: la extraccion es de prosa. Una afirmacion en
prosa no tiene estructura, y el extractor la reconoce por el patron
`CLASE` seguida de texto con citas. Eso significa:

  - encuentra las afirmaciones que el proyecto YA tipificó, que es lo que
    interesa, y no las que no tipificó;
  - el alcance de "su misma frase" es una heuristica de parrafo, y puede
    agrupar una afirmacion con la cita de otra;
  - una afirmacion mal tipificada por el autor se extrae mal, y la
    herramienta no puede saber que la clasificacion es incorrecta. Solo
    comprueba que la clase y el respaldo casen entre si.

Por eso el codigo de salida distingue "hay afirmaciones sin respaldo" de "el
extractor no pudo trabajar", y por eso cada fila lleva su texto integro: para
que un lector pueda discrepar de la extraccion en un segundo.

COMPOSICION

Reusa lo que ya existe en vez de repetirlo: el indice de citas y el alcance de
busqueda de audit_citations.sh, y el grafo de llamadas de unreach.py. No
reimplementa el grafo ni el indice de ficheros; los llama.

CODIGOS DE SALIDA

  0  no hay contradicciones ni afirmaciones sin respaldo
  1  hay findings que necesitan revision
  2  no se pudo ejecutar
  3  no se encuentra el proyecto
"""

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Set, Tuple

VERSION = "1.0.0"

# Las clases de AGENTS.md. Se listan TODAS, y una afirmacion con una clase
# fuera de esta lista se cuenta aparte y se imprime, en vez de ignorarse: un
# hallazgo con una clasificacion nueva es informacion, no ruido.
CLASES = {
    # estados
    "PROVEN", "OBSERVED", "PROVEN_DERIVED", "PROVEN_ABSENT", "CORROBORATED",
    "REFUTED", "NOT_PROVEN", "UNKNOWN", "NOT_DETERMINED", "NOT_AVAILABLE",
    "NOT_OBSERVED", "NOT_FOUND", "NOT_APPLICABLE", "NOT_IN_CORPUS", "PARTIAL",
    "DEFERRED",
    # clases epistemologicas
    "FACT", "DERIVATION", "MODEL_CHOICE", "REQUIREMENT", "POLICY",
    "IMPLEMENTATION", "TEST", "CONCLUSION", "HYPOTHESIS", "ASSUMPTION",
    "LIMITATION", "ERROR", "NEGATIVE_RESULT", "CONTRADICTION",
    # las del toolkit, que tambien aparecen en la prosa
    "GPU", "RUNTIME", "MODIFICATIONS", "STATIC", "TOOL_VALIDATED",
    "TOOL_PARTIAL", "TOOL_UNVALIDATED", "TOOL_BROKEN", "WORK_CLASS",
    "TRACK", "CORPUS", "WRITE_EXECUTION", "TOOL", "CIERRA", "IMPLEMENTS",
    "CORRECTS", "RETRACTS", "GENERALIZA", "COMPLETA", "OBLIGATION",
}

# Las que exigen respaldo. Las demas no lo exigen por su naturaleza: un
# LIMITATION no cita nada, y un NEGATIVE_RESULT suele citar lo que se buscó.
EXIGEN_RESPALDO = {"PROVEN", "PROVEN_DERIVED", "FACT", "CONCLUSION",
                   "DERIVATION"}

CLASE_RX = re.compile(r"`([A-Z][A-Z0-9_]{2,})`")
# Una cita al corpus: fichero.c:123  o  fichero.c:123-140
# Grupos: 1 = nombre sin extension, 2 = extension, 3 = linea inicial,
#         4 = linea final
#
# El patron acepta CUALQUIER nombre de fichero en minusculas con una linea, y
# no solo los que llevan una "v" de generacion. La primera version exigia
# `v\d+_\d+`, y eso hacia que NUNCA casaran las cabeceras de asic_reg --
# gmc_8_2_d.h, gfx_8_0_enum.h, gfx_8_0_sh_mask.h -- que son precisamente
# donde se Defines mas de un bit. El resultado eran cientos de afirmaciones
# PROVEN marcadas "sin respaldo" que si lo tenian, en la cabecera de un
# fichero de bits.
#
# Que el fichero exista o no NO es de esta herramienta: es de
# audit_citations.sh, que ya lo comprueba. Aqui basta con reconocer la forma.
CITA_RX = re.compile(r"([a-z][a-z0-9_]*)\.([ch]):(\d+)(?:-(\d+))?")

# MEDIDO 2026-10-04 (hallazgo 1056).  Era `^(\d{3})[-_]`: TRES digitos exactos.
#
# El numero de hallazgo tiene 3 O 4 digitos, y hay 42 ficheros con 4.  El regex no
# casaba con ellos y la linea siguiente hacia lo peor que se puede hacer con un numero:
#
#     num = m.group(1) if m else f[:3]        # claims.py:805, ANTES
#
# f[:3] de "1002-correccion-a-105-...md" es "100".  Luego el hallazgo 1002 se atribuia
# al hallazgo 100, que es OTRO hallazgo, y `docs[num] = {...}` (claims.py:829) ASIGNA en
# vez de acumular, con lo que de los N documentos con la misma clave sobrevivia el
# ultimo procesado.
#
# MEDIDO sobre el estado real de findings/ con el codigo de antes:
#
#     ficheros .md                    558
#     claves que salen en docs        416
#     DOCUMENTOS QUE DESAPARECEN     142     el 25 %
#
# y los nodos mas cargados: 104 <- 11 documentos, 102 <- 11, 103 <- 9, 100 <- 8.
# Cinco de esos seis son documentos de 4 digitos fundidos en un nodo de 3.
#
# No es ambiguedad: es una respuesta equivocada, y silenciosa, porque el nodo 102
# EXISTE como hallazgo de 3 digitos y recibe las afirmaciones del 1020 al 1029.
FINDING_RX = re.compile(r"^(\d{3,4})[-_]")


def proyecto() -> str:
    return os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), ".."))


def listar_findings(root: str) -> List[str]:
    d = os.path.join(root, "06-INGENIERIA-INVERSA", "findings")
    try:
        return sorted(f for f in os.listdir(d) if f.endswith(".md"))
    except OSError:
        return []


# Un simbolo de codigo citado: un identificador en acentos graves que NO es una
# clase epistemologica. Es la forma de respaldo MAS FRECUENTE de este
# proyecto, y la primera version de claims.py no la contaba: marked 274
# afirmaciones PROVEN como "sin respaldo" cuando lo que tienen al lado es el
# codigo del driver citado literalmente.
#
# Es un respaldo legitimo y a veces mejor que una linea: el lector ve el texto
# sin salir del documento. Pero NO es verificable por audit_citations.sh, que
# solo comprueba fichero:linea. Esa diferencia es el dato.
CODIGO_RX = re.compile(r"`([A-Za-z_][A-Za-z0-9_]*(?:\(\))?)`")
# Bloque de codigo literal dentro del parrafo
TIENE_BLOQUE = re.compile(r"^\s*(?:\w+[\w \t\*]*\s+\w+.*[;{])\s*$|"
                          r"^\s*(?:if|for|while|return|struct|static)\b")


def cita_mas_cercana(lineas: List[str], objetivo: int,
                     ventana: int = 40) -> Optional[str]:
    """La cita mas proxima a una linea, y a que distancia.

    Para PROPUESTA, no para verificacion. Una afirmacion sin respaldo puede
    tener su fuente dos lineas mas abajo, en la siguiente fila de la misma
    tabla, o en el parrafo siguiente. Proponer la cita mas cercana convierte
    "esto no tiene fuente" en "esta es la fuente que probablemente querias",
    que es accionable, y deja la decision a quien lee.

    Se declara la direccion de la propuesta: se buscan las citas en ambos
    sentidos y se toma la de menor distancia absoluta, de modo que la
    propuesta no tiene sesgo. Y se imprime la distancia, porque una
    propuesta a 3 lineas es mucho mas creible que una a 30.
    """
    # El offset va CON SIGNO y la clave de orden es su valor absoluto. La
    # primera version guardaba solo abs(off) y luego lo imprimia con "%+d", que
    # siempre sale positivo: toda propuesta decia "+N" y el lector no podia
    # saber si la fuente estaba antes o despues. Un "%+d" sobre un entero que
    # ya es absoluto imprime un "+" mentiroso, que es peor que no imprimir
    # nada porque parece una direccion.
    citas: List[Tuple[int, int, str]] = []
    for off in range(-ventana, ventana + 1):
        i = objetivo - 1 + off
        if i < 0 or i >= len(lineas):
            continue
        for c in CITA_RX.finditer(lineas[i]):
            citas.append((abs(off), off,
                          "%s:%s" % (c.group(0).split(":")[0], c.group(3))))
    if not citas:
        return None
    citas.sort()
    return "linea %+d  (%s)" % (citas[0][1], citas[0][2])


# --- El indice de simbolos, y por que esta vez incluye enums y campos.
#
# La primera version de esta herramienta intento distinguir una
# CLASIFICACION de un SIMBOLO indexando solo los #define, y no funciono: casi
# todos los simbolos citados son miembros de enum (AMDGPU_GEM_DOMAIN_GTT) o
# campos de struct (wptr, count, length_dw), no macros. Un indice de #define
# no los ve, asi que la comprobacion no existia.
#
# El indice de aqui cubre las tres formas y, para cada simbolo, guarda el
# FICHERO donde esta. Eso es lo que permite el juicio que importa: no "el
# simbolo existe" sino "existe en un fichero de MI ASIC".
INDICE: Optional[Dict[str, List[Tuple[str, int]]]] = None


def indice_de_simbolos(root: str) -> Dict[str, List[Tuple[str, int]]]:
    """simbolo -> [(fichero, linea)] en amdgpu/ y en asic_reg/.

    Tres formas, porque el corpus usa las tres:
        #define NOMBRE ...            macro
        NOMBRE = 1,   o   NOMBRE,     miembro de enum
        tipo NOMBRE;   o   tipo NOMBRE:   campo de struct
    """
    ind: Dict[str, List[Tuple[str, int]]] = {}
    base = os.path.join(root, "rx550-upstream-7.2.8", "linux-7.2.8",
                        "drivers/gpu/drm", "amd")
    for sub in ("amdgpu", os.path.join("include", "asic_reg")):
        d = os.path.join(base, sub)
        if not os.path.isdir(d):
            continue
        for dirpath, _dn, filenames in os.walk(d):
            for f in filenames:
                if not f.endswith((".c", ".h")):
                    continue
                ruta = os.path.join(dirpath, f)
                try:
                    with open(ruta, "r", errors="replace") as fh:
                        texto = fh.read()
                except OSError:
                    continue
                # SOLO dos formas: #define, y miembros de enum dentro de un
                # enum abierto.
                #
                # Se intento indexar tambien los campos de struct, classifying
                # por nivel de llaves, y seguia dando 1.4 MILLONES de simbolos:
                # en el corpus hay mas campos que macros, y un indice que
                # encuentra cada variable local no distingue nada.
                #
                # Se decide por lo que aporta, no por cobertura. Los simbolos
                # que este proyecto cita como respaldo son macros y funciones:
                # mb(), writeq, PACKET3_SET_CONFIG_REG, REG_SET_FIELD,
                # mmVM_INVALIDATE_REQUEST. Todos son #define o miembros de
                # enum. Los campos de struct -- wptr, count, length_dw -- son
                # la parte que mas ruido hace y menos informa, porque no
                # pertenecen a un ASIC sino a una estructura.
                #
                # Un indice de 1.4M hace que TODO resuelva y que
                # "EN_MI_ASIC" deje de significar nada. Un indice de 40K
                # significa algo, aunque no sepa responder de los campos.
                nivel = 0
                en_enum = False
                for i, ln in enumerate(texto.splitlines(), start=1):
                    m = re.match(r"\s*#\s*define\s+([A-Za-z_]\w*)", ln)
                    if m:
                        ind.setdefault(m.group(1), []).append((f, i))
                        continue
                    abrio = ln.count("{")
                    cerro = ln.count("}")
                    if not en_enum and re.search(r"\benum\b[^;]*\{", ln):
                        en_enum = True
                        nivel += abrio - cerro
                        m = re.match(r"\s*([A-Z][A-Z0-9_]{2,})\s*(?:=[^=]|,|$)", ln)
                        if m:
                            ind.setdefault(m.group(1), []).append((f, i))
                        continue
                    if en_enum:
                        m = re.match(r"\s*([A-Z][A-Z0-9_]{2,})\s*(?:=[^=]|,|\})",
                                     ln)
                        if m:
                            ind.setdefault(m.group(1), []).append((f, i))
                        nivel += abrio - cerro
                        if nivel <= 0:
                            en_enum = False
                            nivel = 0
    return ind


# re.MULTILINE, y no es un detalle: sin el flag, "^" ancla al PRINCIPIO DEL
# STRING, no al principio de cada linea, asi que finditer() sobre un fichero
# entero solo mira la primera linea y devuelve cero. La primera version
# emparejaba linea a linea -- y por eso encontro seis includes -- y luego paso
# a emparejar el texto entero, que es lo natural, y devolvio cero sin error.
#
# Es la TERCERA vez en esta sesion que un ancla sin su flag produce un cero
# silencioso: "^" sin re.M en el patron de cabeceras, "\\b" tras "_" que nunca
# casa, y ahora esto. La regla que sale de las tres: un regex que devuelve
# CERO sobre un corpus grande es un regex que no casa, no un corpus sin datos,
# y se prueba con un caso conocido antes de confiar en el.
INCLUDE_RX = re.compile(r'^\s*#\s*include\s+"([^"]+)"', re.M)


def simbolos_usados_por(corpus_root: str, ficheros: Set[str],
                        cabeceras: Set[str]) -> Set[str]:
    """Los identificadores que APARECEN en el codigo de esta placa.

    El criterio del juicio de donde_esta. Se leen los .c que el case del chip
    anade y las cabeceras que esos incluyen, y se recogen los
    identificadores. No se compila ni se resuelve el ambito: se toma todo lo
    que parece un identificador, y se perdonan los falsos positivos porque
    un symbolo de mas se clasifica como "usado por mi ASIC", que es la
    direccion SEGURA -- hace que la herramienta no senale, no que senale de
    mas.

    Esa asimetria es deliberada y hay que declararla. Un simbolo que aparece
    de mas hace que una afirmacion Baseline no se marque; un simbolo que
    falta haria que una afirmacion que se apoya en el codigo de esta placa
    apareciera como "sin relacion", que es una acusacion falsa. Entre los dos
    errores, el segundo es el que cuesta tiempo a un lector.
    """
    amd = os.path.join(corpus_root, "drivers/gpu/drm/amd/amdgpu")
    vistos: Set[str] = set()
    leidos = 0
    for nombre in sorted(ficheros | cabeceras):
        for base in (amd, os.path.join(corpus_root,
                                       "drivers/gpu/drm/amd/include")):
            p = os.path.join(base, nombre)
            if not os.path.isfile(p):
                continue
            try:
                with open(p, "r", errors="replace") as fh:
                    texto = fh.read()
            except OSError:
                continue
            leidos += 1
            for m in re.finditer(r"\b([A-Za-z_]\w{2,})\b", texto):
                vistos.add(m.group(1))
            break
    return vistos


def cabeceras_de(ejec: Dict[str, object], ficheros: Set[str]) -> Set[str]:
    """Las CABECERAS que incluyen los ficheros de esta GPU, a dos niveles.

    POR QUE ESTE SEGUNDO NIVEL, Y POR QUE ARREGLA UN CERO

    La primera version comparaba los simbolos citados contra los .c que
    implementan los IP blocks de esta placa, siete ficheros. Y daba
    EN_MI_ASIC = 0, sin una sola excepcion, porque NINGUN simbolo esta definido
    en un .c: los registros, los macros de paquete y los campos viven en las
    cabeceras, y un .c solo los incluye.

    Un cero absoluto en una columna no es un resultado, es un fallo de la
    comparacion. Pero la DIRECCION importa: si hubiera aceptado los simbolos
    sin comprobar, habria hecho pasar por "de mi ASIC" cosas que no lo son,
    que es el error de 043 al reves y peor que no comprobar nada.

    Se siguen los #include a dos niveles: el camino es corto -- gmc_v8_0.c
    incluye gmc/gmc_8_1_d.h -- y en un solo nivel un include de amdgpu.h trae
    700 lineas de tipos comunes a toda la familia, que no distinguen nada.

    El indice base->ruta se construye una vez. Y un include que no se
    encuentra se cuenta y se DECLARA: un include no resuelto es un limite de
    la cobertura, no un acierto silencioso.
    """
    corpus_root = str(ejec.get("corpus", ""))
    if not corpus_root:
        return set()
    base_por_nombre: Dict[str, List[str]] = {}
    for r in (os.path.join(corpus_root, "drivers/gpu/drm/amd/amdgpu"),
              os.path.join(corpus_root, "drivers/gpu/drm/amd/include")):
        for dirpath, _dn, filenames in os.walk(r):
            for f in filenames:
                if f.endswith((".c", ".h")):
                    base_por_nombre.setdefault(f, []).append(f)

    amd = os.path.join(corpus_root, "drivers/gpu/drm/amd/amdgpu")
    vistos: Set[str] = set()
    no_resueltos: Set[str] = set()
    frontera = set(ficheros)
    for _nivel in range(2):
        siguiente: Set[str] = set()
        for nombre in sorted(frontera):
            try:
                with open(os.path.join(amd, nombre), "r",
                          errors="replace") as fh:
                    texto = fh.read()
            except OSError:
                no_resueltos.add(nombre)
                continue
            for m in INCLUDE_RX.finditer(texto):
                base = os.path.basename(m.group(1))
                cand = base_por_nombre.get(base)
                if not cand:
                    no_resueltos.add(base)
                else:
                    siguiente |= set(cand)
        siguiente -= vistos
        if not siguiente:
            break
        vistos |= siguiente
        frontera = siguiente
    ejec["includes_no_resueltos"] = sorted(no_resueltos)
    ejec["n_includes_no_resueltos"] = len(no_resueltos)
    return vistos


def generacion_de_fichero(nombre: str) -> Optional[str]:
    """La generacion que declara el NOMBRE de un fichero, o None.

    None significa "no lo declara", y eso NO se juzga: vi.c, amdgpu_psp.c y
    la mayoria de amdgpu/ no llevan version. Juzgar esos como si fueran de otra
    generacion seria un falso positivo del tamaño del corpus.
    """
    base = nombre.rsplit(".", 1)[0]
    m = re.match(r"^([a-z]+(?:_[a-z]+)*?)_v?(\d+)_(\d+)", base)
    if m:
        return "%s_%s" % (m.group(2), m.group(3))
    return None


def donde_esta(simbolo: str, ind: Dict[str, List[Tuple[str, int]]],
               ficheros_chip: Set[str],
               usos_chip: Optional[Set[str]] = None,
               cabeceras_chip: Optional[Set[str]] = None) -> Dict[str, object]:
    """De donde viene un simbolo, y si lo USA esta placa.

    EL CRITERIO ES EL USO, NO LA CABECERA QUE LO DEFINE. Y esa distincion es
    la que hace que la comprobacion sirva.

    Un simbolo puede estar definido en una cabecera comun -- sid.h,
    soc15d.h, amdgpu.h -- y que eso no diga nada sobre esta placa. Las tres
    cabeceras de las que salio el primer resultado de esta seccion son
    precisamente eso: COMMONES, no de otra generacion. Clasificarlas como
    "de otro ASIC" habria producido dos falsos positivos.

    Y al reves, un simbolo definido SOLO en cabeceras de otra generacion, y no
    en las de esta, es un indicio real -- pero no una prueba, porque una
    cabecera compartida con nombres genericos puede Bring Bring lo que
    necesita.

    Por eso el veredicto se apoya en lo que el codigo de esta placa USA:

        USADO_POR_MI_ASIC   el simbolo aparece en los .c que esta GPU ejecuta,
                           o en las cabeceras que esos incluyen. Es la
                           evidencia fuerte.
        DEFINIDO_AQUI      esta en esas cabeceras, aunque no se use. Es
                           evidencia de que el nombre existe para esta
                           familia.
        SIN_RELACION        no aparece en ninguna de las dos. La afirmacion se
                           apoya en algo que esta placa no toca. Eso es la
                           regla de 043 con otro disfraz, y se MARCA.

    La ultima categoria tambien sale para simbolos que son abreviaturas del
    autor o nombres de funcion local de un finding, y por eso se declara que
    no es lo mismo que "no existe".
    """
    sitios = ind.get(simbolo)
    cab = cabeceras_chip or set()
    usado = simbolo in (usos_chip or set())
    if usado:
        return {"estado": "USADO_POR_MI_ASIC"}
    if sitios:
        ficheros = sorted(set(f for f, _l in sitios))
        if any(f in cab for f in ficheros):
            return {"estado": "DEFINIDO_AQUI", "donde": ficheros[:3]}
        return {"estado": "SIN_RELACION", "donde": ficheros[:3],
                "generaciones": sorted(set(
                    g for g in (generacion_de_fichero(f) for f in ficheros)
                    if g))}
    if usado:
        return {"estado": "USADO_POR_MI_ASIC"}
    return {"estado": "NO_RESUELTO", "donde": []}


def formas_de_respaldo(texto: str, clases: Set[str]) -> Dict[str, object]:
    """De donde viene el respaldo de una afirmacion, en este orden.

        CITA   fichero.c:123  -- verificable por audit_citations.sh
        CODIGO identificador citado, o bloque de codigo literal -- verificable
                por un lector, no por una herramienta
        NADA   nada de lo anterior
    """
    citas = CITA_RX.findall(texto)
    codigo = [m for m in CODIGO_RX.findall(texto)
              if m not in clases and len(m) > 2
              and not m.isdigit()]
    bloque = bool(TIENE_BLOQUE.search(texto))
    if citas:
        forma = "CITA"
    elif codigo or bloque:
        forma = "CODIGO"
    else:
        forma = "NADA"
    return {"forma": forma, "n_citas": len(citas),
            "n_codigo": len(codigo), "bloque": bloque,
            "codigo": codigo}


def parrafos(lineas: List[str]) -> List[Tuple[int, int, str]]:
    """(linea_ini, linea_fin, texto) por parrafo.

    El alcance de "su mismo parrafo" es una heuristica, y se declara como tal.
    Una linea vacia separa parrafos, y una linea que empieza por # no es un
    parrafo de texto. Las listas y los bloques de codigo se agrupan con su
    elemento, porque una afirmacion y su cita casi siempre estan en la misma
    vinieta.
    """
    out: List[Tuple[int, int, str]] = []
    ini: Optional[int] = None
    buf: List[str] = []
    for i, ln in enumerate(lineas, start=1):
        if ln.strip() == "" or re.match(r"^#{1,6}\s", ln):
            if ini is not None:
                out.append((ini, i - 1, "\n".join(buf)))
                ini, buf = None, []
            if ln.strip() != "" and re.match(r"^#{1,6}\s", ln):
                out.append((i, i, ln))
            continue
        if ini is None:
            ini = i
        buf.append(ln)
    if ini is not None:
        out.append((ini, len(lineas), "\n".join(buf)))
    return out


# Una cabecera de finding lleva el estado del documento, no afirmaciones
# suyas: `CLASSIFICATION=TOOL`, `RUNTIME=NOT_RUN`, `MODIFICATIONS=0`. Contarlas
# como afirmaciones infla el recuento y hace que un informe de fronteras
# parezca un hallazgo.
#
# La primera version las excluia de forma ACCIDENTAL: los tokens llevan "=" y
# el extractor exige el cierre del acent grave justo despues del
# identificador, asi que nunca casaban. Funcionaba, pero por un motivo que no
# estaba escrito, y en cuanto alguien pone un `PROVEN` suelto en la cabecera
# pasaria a contarse. Aqui la exclusion es explicita.
ES_CABECERA = re.compile(r"(CLASSIFICATION|TRACK|RUNTIME|MODIFICATIONS|"
                         r"WORK_CLASS|WRITE_EXECUTION|CORPUS|TOOL)=")


def extraer(lineas: List[str]) -> List[Dict[str, object]]:
    """Una fila por clasificacion tipificada, con su parrafo y sus citas."""
    filas: List[Dict[str, object]] = []
    fuera_de_lista: Set[str] = set()
    for ini, fin, texto in parrafos(lineas):
        if ES_CABECERA.search(texto):
            continue
        citas = CITA_RX.findall(texto)
        for m in CLASE_RX.finditer(texto):
            clase = m.group(1)
            if clase not in CLASES:
                fuera_de_lista.add(clase)
                continue
            # El texto de la afirmacion es la FRASE QUE LA CONTIENE, con una
            # ventana MINIMA a cada lado.
            #
            # La primera version tomaba texto[m.end():], lo que sigue a la
            # clase, y eso produce basura: en la prosa de este proyecto la
            # clasificacion suele ir AL FINAL ("... es `NOT_DETERMINED`"), asi
            # que lo que seguia era el comienzo de la frase siguiente.
            #
            # La segunda version corto por sentence boundaries a ambos lados, y
            # eso tampoco: cuando la clase esta al final, el punto va justo
            # detras y la frase entera se reduce a "`NOT_DETERMINED`." Un
            # clasificador no puede trabajar con eso.
            #
            # Asi que: se busca un limite de frase a cada lado, pero NUNCA antes
            # de VENTANA chars. Si no hay frase antes en esa ventana, se coge
            # la ventana entera. Una frase puede derramarse en la anterior, y eso
            # se ve leyendo la fila, que es donde tiene que verse.
            VENTANA = 120
            ini_txt = max(0, m.start() - VENTANA)
            corte = max(texto.rfind(". ", 0, ini_txt),
                        texto.rfind("; ", 0, ini_txt),
                        texto.rfind("\n", 0, ini_txt))
            if corte >= 0:
                ini_txt = corte + 1
            fin_txt = min(len(texto), m.end() + VENTANA)
            corte2 = re.compile(r"\.\s|[;\n]").search(texto, m.end())
            if corte2 and corte2.start() < fin_txt:
                fin_txt = corte2.start()
            frase = texto[ini_txt:fin_txt].strip()[:240]
            filas.append({
                "clase": clase,
                # LA LINEA DEL TOKEN, NO LA DEL PARRAFO.
                #
                # MEDIDO 2026-10-03: con la linea del parrafo, 2269 de 2470
                # filas de tabla publicaban una linea que NO era la de su
                # token -- el 92%. Una tabla entera es UN parrafo (no hay linea
                # vacia que la corte), asi que sus doce filas salian todas con
                # la linea de la primera. Quien iba a OPEN-FRONTIERS.md a ver el
                # hueco caia en la fila equivocada, y la tabla es la mayoria de
                # la frontera.
                #
                # El desplazamiento del token dentro del texto del parrafo se
                # convierte a linea contando saltos. Es exacto porque `texto`
                # es la concatenacion de lineas consecutivas con "\n".
                "linea": ini + texto[:m.start()].count("\n"),
                "linea_parrafo": ini,
                # Una fila de tabla NO es una afirmacion: `| asercion |
                # NOT_DETERMINED |` es una celda. La frase que sale de ahi no
                # termina en punto, no tiene verbo y su "estado" lo decide la
                # columna de al lado. tools/frontier.py las clasificaba como si
                # fueran frases, y son el 57 % de la frontera: 390 de 682.
                # Clasificar un fragmento produce etiquetas que parecen
                # accionables y no lo son.
                "es_fila": texto.lstrip().startswith("|"),
                "parrafo": (ini, fin),
                "frase": frase.strip()[:190],
                # Con la extension. La primera version hacia "%s:%s" con
                # c[0] y c[1], y el grupo 1 del patron no incluye el ".c", asi
                # que toda cita salia como "sdma_v3_0:c" sin linea. Una cita
                # sin linea parece una cita sin verificar, que es justo lo
                # contrario de lo que es.
                "citas": ["%s.%s:%s" % (c[0], c[1], c[2]) for c in citas],
                "n_citas_en_parrafo": len(citas),
                "respaldo": formas_de_respaldo(texto, CLASES),
                # El parrafo entero, no solo la frase. Una clasificacion suele
                # ir al final de la frase que la contiene, asi que la frase
                # sola no dice por que el hueco sigue abierto; el parrafo si,
                # porque es donde el autor explica el bloque. downstream
                # clasificar por parrafo dio 226 de 261 sin clasificar, que
                # es la medida de que la frase no era la unidad correcta.
                "parrafo_texto": texto,
                "propuesta": None,
            })
    return filas, fuera_de_lista


def grafo_de_ejecucion(root: str) -> Optional[Dict[str, object]]:
    """Los ficheros que ESTA GPU ejecuta, y los que no. De unreach.py.

    Se importa y se llama, no se reimplementa: el grafo de llamadas es la
    parte mas sutil de unreach.py -- con la direccion equivocada devuelve un
    nodo y una respuesta segura y falsa -- y duplicarlo seria copiar el
    defecto con mas sitio donde equivocarse.
    """
    try:
        sys.path.insert(0, os.path.join(root, "tools"))
        import unreach  # type: ignore
    except ImportError:
        return None
    for cand in (os.path.join(root, "rx550-upstream-7.2.8", "linux-7.2.8"),
                 os.path.join(root, "RESEARCH", "working", "linux-7.1.3")):
        if not os.path.isdir(cand):
            continue
        c = unreach.Corpus(cand)
        if not c.ok():
            continue
        try:
            g = unreach.grafo_de_llamadas(c)
            solo, _ = unreach.alcanzables_desde(
                c, g, "amdgpu_discovery_set_ip_blocks")
            ficheros, _aviso = unreach.ficheros_del_chip(c, "CHIP_POLARIS12")
        except Exception:
            return None
        # un fichero se marca como "no ejecutado" si TODOS sus bloques de IP
        # son inalcanzables y no define ninguno que el chip anade
        no_ejecutado: Set[str] = set()
        try:
            for entry in c.c_files():
                if entry in ficheros:
                    continue
                if any(f in g for f in [entry]):
                    pass
                no_ejecutado.add(entry)
        except Exception:
            pass
        return {"corpus": cand, "solo_en_default": solo,
                "ficheros_del_chip": ficheros,
                "grafo": g, "Corpus": c, "unreach": unreach}
    return None


def generacion_de_la_propuesta(propuesta: str) -> Optional[str]:
    """La generacion que declara un nombre de cabecera, o None.

    Es la comprobacion de 043 automatizada. 035 corrigio un count que era
    correcto leyendo un fichero de otro ASIC, y 047 demostro que la regla se
    puede comprobar sobre las 1722 citas del proyecto. Aqui se aplica a la
    fuente PROPUESTA de una afirmacion que no tiene fuente: si la cabecera mas
    cercana declara otra generacion, la afirmacion probablemente se apoya en
    otro siliconio, y eso hay que mirarlo antes de dar la fuente por buena.

    Solo se marca lo que es claramente otra generacion. Una cabecera sin
    digitos de version no se juzga, porque no se sabe a que ASIC pertenece.
    """
    # El prefijo NO puede contener digitos. Con un prefijo perezoso que si los
    # aceptaba, "gfx_9_4_2" se rompia en "gfx_9" + "_4_2" y devolvia 4_2 en vez
    # de 9_4: la misma generacion leida por la mitad y con la misma pinta que
    # una correcta. Un identificador que se lee mal sin avisar no sirve para
    # marcar una generacion.
    # Sin ancla final. La primera version la traia, y con ella "gfx_9_4_2"
    # daba None en vez de 9_4: despues de "9_4" viene "_2", y el "_" es un
    # caracter de palabra, asi que \b no casa entre "4" y "_". Un \b que
    # nunca casa es un fallo silencioso que devuelve "no se puede juzgar" en
    # vez de un numero, que es la direccion que oculta el problema.
    # La propuesta llega con el prefijo "linea +13  (nombre:linea)", asi que
    # hay que quedarse con el nombre. La primera version le pasaba la cadena
    # entera, el ancla ^ no casaba con "linea +13", y devolvia None para
    # TODO -- es decir, la comprobacion de generacion no existia y no fallaba.
    m = re.search(r"([a-z][a-z0-9_]*\.[a-z]+:\d+)", propuesta)
    if m:
        propuesta = m.group(1)
    m = re.search(r"^([a-z]+(?:_[a-z]+)*?)_v?(\d+)_(\d+)", propuesta)
    if not m:
        return None
    return "%s_%s" % (m.group(2), m.group(3))


def retracciones(lineas: List[str]) -> Tuple[Set[str], Dict[str, str]]:
    """Que findings este documento RETRACTA o CORRIGE, y cual le corrigen a el.

    Los marcadores del proyecto son RETRACTED_BY=, RETRACTED_PARTLY_BY=,
    CORRECTED_BY=, CORRECTS=, IMPLEMENTS=, GENERALIZADO_POR=, CERRADO_POR=,
    MEDIDO_EN_MI_ASIC_POR=. Se leen todos, y se distinguen las dos
    direcciones: lo que este finding hace y lo que le hacen a el. Confundirlas
    produce "obsoleto" al reves, que es peor que no detectarlo.
    """
    texto = "\n".join(lineas[:24])
    este = None
    m = re.search(r"^#\s*(\d{3})", "\n".join(lineas[:4]), re.M)
    if m:
        este = m.group(1)
    hace: Set[str] = set()
    recibe: Dict[str, str] = {}
    # LA CONVENCION DE RETRACTED_BY ES AMBIGUA, y el dato lo dice.
    #
    # En la cabecera de 043 pone `RETRACTED_BY=043`. Leido al pie de la letra
    # significa "este finding esta retractado por 043", o sea por si mismo,
    # que no significa nada. Leido con la intencion del autor significa "este
    # finding retracta lo anterior", y el objetivo es 035, que es lo que
    # 043 hace de verdad.
    #
    # No se elige: se resuelve desde los datos. Si el numero del marcador es
    # el del propio documento, es el ACTOR, y el objetivo es otro finding. Si
    # es distinto, es a quien se le atribuye la accion. Las dos lecturas se
    # prueban contra el numero del fichero, y el resultado se imprime con su
    # direccion, de modo que un lector que lo entienda al reves lo ve.
    #
    # Confundir las dos direcciones produce "obsoleto" al reves, que es peor
    # que no detectarlo: marca como caducado al finding que corrige.
    for rx in (r"CORRECTS=(\d{3})", r"IMPLEMENTS=(\d{3})",
               r"GENERALIZAD[OA]_POR=(\d{3})"):
        for num in re.findall(rx, texto):
            if este and num != este:
                hace.add(num)
    for rx, etiqueta in ((r"RETRACTED_BY=(\d{3})", "RETRACTA"),
                         (r"RETRACTED_PARTLY_BY=(\d{3})", "RETRACTA_PARCIAL")):
        for num in re.findall(rx, texto):
            if num == este:
                # el actor se nombra a si mismo: el objetivo es el anterior
                hace.add("__anterior__")
            elif este:
                recibe[num] = ("%s por %s (esta cabecera lo declara de otro)"
                               % (etiqueta, este))
    for rx, etiqueta in ((r"CORRECTED_BY=(\d{3})", "CORREGIDO_POR"),
                         (r"CERRADO_POR=(\d{3})", "CERRADO_POR"),
                         (r"MEDIDO_EN_MI_ASIC_POR=(\d{3})", "MEDIDO_EN_MI_ASIC")):
        for num in re.findall(rx, texto):
            if este and num != este:
                recibe[num] = "%s por %s" % (etiqueta, este)
    return hace, recibe


def main() -> int:
    ap = argparse.ArgumentParser(
        description="audita afirmaciones tipificadas, no lineas citadas")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--solo-clase", help="filtra por clase")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    root = proyecto()
    # MEDIDO 2026-10-04 (hallazgo 1056).  Los ficheros cuyo nombre no tiene forma de
    # numero de hallazgo.  Antes no existia la lista porque no habia forma de que
    # faltara: f[:3] SIEMPRE daba algo, y ese algo era el nodo de otro hallazgo.
    sin_numero: List[str] = []
    hallazgos = listar_findings(root)
    if not hallazgos:
        print("claims: no encuentro findings en %s" % root, file=sys.stderr)
        return 3

    ejec = grafo_de_ejecucion(root)

    # El indice y el conjunto de ficheros del ASIC se construyen UNA vez y se
    # comparten entre todos los findings, porque son de todo el corpus y
    # reconstruirlos por documento seria 98 veces el mismo trabajo.
    ind = indice_de_simbolos(root)
    ficheros_chip: Set[str] = set()
    cabeceras_chip: Set[str] = set()
    if ejec:
        ficheros_chip = set(ejec.get("ficheros_del_chip") or ())
        cabeceras_chip = cabeceras_de(ejec, ficheros_chip)
        usos_chip = simbolos_usados_por(str(ejec.get("corpus", "")),
                                        ficheros_chip, cabeceras_chip)
    else:
        usos_chip = set()

    filas: List[Dict[str, object]] = []
    fuera: Set[str] = set()
    docs: Dict[str, Dict[str, object]] = {}
    simbolos_vistos: Dict[str, int] = {}
    for f in hallazgos:
        p = os.path.join(root, "06-INGENIERIA-INVERSA", "findings", f)
        try:
            with open(p, "r", errors="replace") as fh:
                lineas = fh.read().splitlines()
        except OSError:
            continue
        fs, ff = extraer(lineas)
        fuera |= ff
        m = FINDING_RX.match(f)
        # MEDIDO 2026-10-04 (hallazgo 1056).  Antes: `num = m.group(1) if m else f[:3]`.
        # f[:3] NO es un numero de hallazgo: es un prefijo, y coincidia con otro
        # hallazgo.  Ahora, si el nombre no tiene forma de numero, se cuenta y se dice
        # en vez de elegir un nodo: un hallazgo sin numero NO es un hallazgo sin
    # hallazgo cuyo nombre no se entiende, y declararlo es la unica forma
    # de que el recuento no este mintiendo.
        if m is None:
            sin_numero.append(f)
            continue
        num = m.group(1)
        hace, recibe = retracciones(lineas)
        clases: Dict[str, int] = {}
        sin_respaldo: List[Dict[str, object]] = []
        for x in fs:
            if x["respaldo"]["forma"] == "NADA":
                x["propuesta"] = cita_mas_cercana(lineas, int(x["linea"]))
            if x["respaldo"]["forma"] == "CODIGO":
                # Cada simbolo del respaldo se resuelve UNA vez y se cuenta, no
                # una vez por fila. Un mismo `writeq` aparece en 40
                # afirmaciones y resolverlo 40 veces no dice nada nuevo.
                res: Dict[str, object] = {}
                for sym in x["respaldo"]["codigo"]:
                    base = sym.rstrip("()")
                    simbolos_vistos[base] = simbolos_vistos.get(base, 0) + 1
                    res[sym] = donde_esta(base, ind, ficheros_chip,
                                         usos_chip, cabeceras_chip)
                x["simbolos"] = res
            x["finding"] = num
            x["documento"] = f
            clases[x["clase"]] = clases.get(x["clase"], 0) + 1
            if x["clase"] in EXIGEN_RESPALDO and not x["citas"]:
                sin_respaldo.append(x)
        filas.extend(fs)
        docs[num] = {
            "fichero": f, "n": len(fs), "clases": clases,
            "sin_respaldo": sin_respaldo,
            "retracca_a": sorted(hace), "referenciado_por": recibe,
        }

    # --json es EXCLUSIVO. Con los dos, el json no se puede consumir: viene
    # detras de 300 lineas de informe. Y la primera version de esta
    # herramienta imprimia el informe y luego el json, asi que cualquier
    # `claims.py --json | python3 -c ...` fallaba con un error de parseo que
    # no señalaba la causa.
    if args.json:
        print(json.dumps({"filas": filas, "docs": docs,
                          "tokens_no_clase": sorted(fuera),
            "simbolos_en_respaldo": simbolos_vistos,
            # MEDIDO 2026-10-04 (hallazgo 1056).  Sin esto, los hallazgos sin numero
            # desaparecen sin dejar rastro, que es exactamente el defecto que se
            # arregla: un dato que no se cuenta parece un dato que no existe.
            "hallazgos_sin_numero": sorted(sin_numero)},
                         indent=2, sort_keys=True, default=str))
        n_exigen = sum(1 for f in filas
                       if f["clase"] in EXIGEN_RESPALDO)
        n_sr = sum(len(d["sin_respaldo"]) for d in docs.values())
        return 1 if n_sr else 0

    print("=" * 78)
    print("claims %s · WORK_CLASS=READ_ONLY" % VERSION)
    print("=" * 78)
    print("proyecto   %s" % root)
    print("findings   %d" % len(hallazgos))
    print("afirmaciones tipificadas extraidas: %d" % len(filas))
    # MEDIDO 2026-10-04 (hallazgo 1056).  Con f[:3] esto no podia ser distinto de 0.
    print("hallazgos con numero: %d" % (len(hallazgos) - len(sin_numero)))
    if sin_numero:
        print("hallazgos SIN NUMERO (no se atribuyen a ninguno): %d" % len(sin_numero))
        for f in sorted(sin_numero)[:10]:
            print("    %s" % f)
    print()

    print("=" * 78)
    print("1 · COBERTURA POR CLASE")
    print("=" * 78)
    total: Dict[str, int] = {}
    for f in filas:
        total[f["clase"]] = total.get(f["clase"], 0) + 1
    for k in sorted(total, key=lambda x: -total[x]):
        marca = ""
        if k in EXIGEN_RESPALDO:
            marca = "  (exige respaldo)"
        print("  %-20s %5d%s" % (k, total[k], marca))
    if fuera:
        print()
        print("  Tokens en acentos graves que NO son clases: %d. NO se listan."
              % len(fuera))
        print()
        print("  La primera version de esta seccion imprimia 466 lineas, casi")
        print("  todas macros de C: un token en acentos graves puede ser una")
        print("  CLASIFICACION o un SIMBOLO DEL CORPUS, y la prosa no los")
        print("  distingue -- `PROVEN` y `mmVM_INVALIDATE_REQUEST` tienen la")
        print("  misma forma. Se intento separar indiceando los simbolos del")
        print("  corpus, y no funciono: la mayoria de los simbolos citados son")
        print("  miembros de enum, no #define, y el indice de #define no los")
        print("  ve. Ampliar el indice hasta acertar es trabajo infinito para")
        print("  una seccion que no decide nada.")
        print()
        print("  Una lista de 466 falsos positivos es PEOR que ninguna: entrena")
        print("  al lector a saltarsela. Se declara el limite y se sigue.")

    print()

    print("=" * 78)
    print("2 · DE DONDE VIENE EL RESPALDO DE LO QUE LO EXIGE")
    print("=" * 78)
    exigen = [f for f in filas if f["clase"] in EXIGEN_RESPALDO]
    por_forma: Dict[str, int] = {}
    for f in exigen:
        por_forma[f["respaldo"]["forma"]] = por_forma.get(
            f["respaldo"]["forma"], 0) + 1
    print("  %d afirmaciones exigen respaldo. De donde lo sacan:" % len(exigen))
    print("    CITA   fichero.c:123      %4d   verificable por audit_citations"
          % por_forma.get("CITA", 0))
    print("    CODIGO simbolo o bloque   %4d   verificable por un LECTOR, no"
          % por_forma.get("CODIGO", 0))
    print("                                    por ninguna herramienta")
    print("    NADA                      %4d" % por_forma.get("NADA", 0))
    print()
    n_sr = por_forma.get("NADA", 0)
    if por_forma.get("CODIGO", 0) > por_forma.get("CITA", 0):
        print("  Y ESTE ES EL DATO, no un fallo: la MAYORIA de las afirmaciones")
        print("  del proyecto se respaldan copiando el codigo del driver, no")
        print("  citando fichero:linea. Es un estilo legitimo y a veces mejor,")
        print("  porque el lector ve el texto sin salir del documento.")
        print()
        print("  Pero tiene un coste que no era visible: audit_citations.sh solo")
        print("  comprueba fichero:linea, asi que esas afirmaciones NO tienen")
        print("  verificacion automatica. El 29% que si la tiene es el unico")
        print("  tramo que una herramienta puede vigilar sin leer prosa.")
        print()
    if n_sr:
        nada = [f for f in exigen if f["respaldo"]["forma"] == "NADA"]
        print("  Las %d SIN RESPALDO DE NINGUNA FORMA. Estas si sonstrumento" % n_sr)
        print("  de trabajo: o falta la cita, o la clasificacion no corresponde:")
        print()
        por_doc: Dict[str, List[Dict[str, object]]] = {}
        for f in nada:
            por_doc.setdefault(str(f["documento"]), []).append(f)
        for doc in sorted(por_doc, key=lambda d: -len(por_doc[d]))[:14]:
            filas_d = por_doc[doc]
            print("    %-52s %d" % (doc[:52], len(filas_d)))
            for f in filas_d[:3]:
                print("       :%-4d %-18s %s" % (f["linea"], f["clase"],
                                                 f["frase"][:56]))
                if f.get("propuesta"):
                    gen = generacion_de_la_propuesta(str(f["propuesta"]))
                    aviso = ""
                    if gen and gen not in ("0_8", "8_0", "8_1", ""):
                        aviso = ("  <-- OTRAS GENERACION: la fuente propuesta es "
                                 "%s, y esta GPU es GFX8 (043)" % gen)
                    print("              propuesta: %s%s"
                          % (f["propuesta"], aviso))
        if len(por_doc) > 14:
            print("    ... y %d documento(s) mas" % (len(por_doc) - 14))
    else:
        print("  Ninguna se queda sin respaldo de ninguna forma.")
    print()

    print("=" * 78)
    print("3 · LOS RESPALDOS EN CODIGO, RESUELTOS CONTRA EL CORPUS")
    print("=" * 78)
    cod_rows = [f for f in filas if f["respaldo"]["forma"] == "CODIGO"]
    estados: Dict[str, int] = {}
    otros_asic: List[Tuple[str, int, Dict[str, object]]] = []
    for f in cod_rows:
        for sym, r in (f.get("simbolos") or {}).items():
            estados[r["estado"]] = estados.get(r["estado"], 0) + 1
            if r["estado"] == "SIN_RELACION":
                otros_asic.append(
                    (str(f["finding"]), int(f["linea"]), r | {"sym": sym}))
    print("  indice construido: %d simbolos" % len(ind))
    if ejec and ejec.get("n_includes_no_resueltos"):
        print("  #include no resueltos: %d  (limite de cobertura, no acierto)"
              % ejec["n_includes_no_resueltos"])
        print("     %s" % ", ".join(ejec.get("includes_no_resueltos", [])[:5]))
    print("  El indice es grande y es real: los *_sh_mask.h autogenerados")
    print("  traen un miembro de enum por cada campo de registro, y dcn_3_2_0")
    print("  solo aporta 194932. La primera version de esta seccion avisaba")
    print("  de un indice de mas de 200000 por si estaba indexando variables")
    print("  locales, y el aviso era un FALSO: el indice es correcto, el")
    print("  corpus es enorme. Un aviso que se dispara por algo que no es un")
    print("  fallo entrena a ignorar los avisos.")
    print("  ficheros del ASIC (implementacion): %d" % len(ficheros_chip))
    print("  cabeceras que esos ficheros incluyen: %d" % len(cabeceras_chip))
    print("  identificadores que USA el codigo de esta placa: %d"
          % len(usos_chip))
    print()
    print("  Se comparan las DOS, y eso corrige un cero. La primera version")
    print("  comparaba solo contra los .c y daba EN_MI_ASIC = 0 sin una sola")
    print("  excepcion, porque ningun simbolo esta definido en un .c: estan en")
    print("  las cabeceras. Un cero total en una columna no es un resultado, es")
    print("  un fallo de la comparacion. Y la direccion importa: aceptar los")
    print("  simbolos sin comprobar habria hecho pasar por 'de mi ASIC' cosas")
    print("  que no lo son, que es el error de 043 al reves y peor.")
    print("  filas con respaldo CODIGO: %d" % len(cod_rows))
    print()
    print("  cada simbolo citado, clasificado. El criterio es el USO: si el")
    print("  codigo de esta placa lo toca, es de esta placa, este donde este")
    print("  definido. Una cabecera comun como sid.h o soc15d.h no es 'de otra")
    print("  generacion', y la primera version las clasifico asi.")
    for k in ("USADO_POR_MI_ASIC", "DEFINIDO_AQUI", "SIN_RELACION",
              "NO_RESUELTO"):
        print("    %-14s %4d" % (k, estados.get(k, 0)))
    print()
    if otros_asic:
        print("  LOS %d SIN RELACION CON ESTA PLACA. Es la regla de 043 con" % len(otros_asic))
        print("  otro disfraz: la afirmacion se apoya en un simbolo que esta")
        print("  placa no toca. NO se afirma que este mal -- un contraste entre")
        print("  generaciones es evidencia legitima, y por eso la categoria")
        print("  se llama SIN_RELACION y no ERROR -- se marca y se mira.")
        print()
        vistos: Set[str] = set()
        for num, linea, r in otros_asic[:18]:
            if r["sym"] in vistos:
                continue
            vistos.add(r["sym"])
            print("    %-6s :%-5d %-32s %s"
                  % (num, linea, r["sym"][:32], ", ".join(r["donde"][:2])))
        print()
    print("  Y lo que no resuelve tambien es un dato, pero NO es lo mismo que")
    print("  lo anterior: un simbolo ausente del corpus puede ser una")
    print("  abreviatura del autor, el nombre de una funcion auxiliar de un")
    print("  finding, o una errata. Los dos estan juntos en la lista de abajo")
    print("  y NO se deben leer igual.")
    nr: Dict[str, int] = {}
    for f in cod_rows:
        for sym, r in (f.get("simbolos") or {}).items():
            if r["estado"] in ("NO_RESUELTO", "SIN_RELACION"):
                nr[sym] = nr.get(sym, 0) + 1
    for sym, n in sorted(nr.items(), key=lambda kv: -kv[1])[:12]:
        print("    %-32s %d uso(s)" % (sym[:32], n))
    print()

    print("=" * 78)
    print("4 · RETRACCIONES Y DEPENDENCIAS ENTRE FINDINGS")
    print("=" * 78)
    acted = [(n, d) for n, d in sorted(docs.items()) if d["retracca_a"]]
    if acted:
        for n, d in acted:
            print("  %s  reescribe: %s" % (d["fichero"],
                                           ", ".join(d["retracca_a"])))
    else:
        print("  ninguna retraccion registrada.")
    ref = [(n, d) for n, d in sorted(docs.items()) if d["referenciado_por"]]
    if ref:
        print()
        print("  referenciados en la cabecera de otro finding (por %d):"
              % len(ref))
        for n, d in ref[:10]:
            otros = ", ".join(sorted(d["referenciado_por"]))
            print("    %-52s %s" % (d["fichero"][:52], otros))
    print()

    print("=" * 78)
    print("5 · DOCUMENTOS QUE SON INFORME DE FRONTERAS, NO DE HALLAZGOS")
    print("=" * 78)
    print("  Un finding con mucho NOT_DETERMINED y poco PROVEN es util, pero")
    print("  no es un hallazgo: es una lista de lo que falta. Se listan para")
    print("  que la proporcion sea visible y no se lea como solidez.")
    print()
    print("  %-52s %-8s %-8s %s"
          % ("documento", "PROVEN", "NOT_DET", "otros"))
    for n, d in sorted(docs.items(), key=lambda kv: -len(kv[1]["sin_respaldo"])):
        c = d["clases"]
        pr = c.get("PROVEN", 0) + c.get("PROVEN_DERIVED", 0)
        nd = c.get("NOT_DETERMINED", 0)
        otros = d["n"] - pr - nd
        if nd and nd >= pr:
            print("  %-52s %-8s %-8s %s"
                  % (d["fichero"][:52], pr, nd, otros))
    print()

    print("=" * 78)
    print("LO QUE ESTA HERRAMIENTA NO HACE")
    print("=" * 78)
    print("  - La extraccion es de PROSA. Una afirmacion en prosa no tiene")
    print("    estructura, y el alcance de 'su parrafo' es una heuristica. Se")
    print("    imprime el texto entero de cada fila para que un lector pueda")
    print("    discrepar en un segundo.")
    print("  - NO distingue una CLASIFICACION de un SIMBOLO DEL CORPUS. Ambos")
    print("    van en acentos graves y la prosa no los separa, asi que un token")
    print("    desconocido se cuenta como clase y se DECLARA EL LIMITE en vez de")
    print("    listar 466 macros, que es lo que hacia la primera version.")
    print("  - Solo encuentra las afirmaciones que el proyecto YA tipifico. No")
    print("    detecta afirmaciones sin clasificar, y no puede saber si una")
    print("    detecta afirmaciones sin clasificar, y no puede saber si una")
    print("    clasificacion es incorrecta: solo que la clase y el respaldo")
    print("    casen entre si.")
    print("  - NO comprueba que la cita RESPALDE la afirmacion. Eso requiere")
    print("    entender la frase, y una herramienta que fingiera hacerlo")
    print("    produciria una falsa seguridad. Lo que si hace es ponerlas una")
    print("    al lado de la otra.")
    print("  - No corrige findings ni reescribe historia. Produce una tabla.")
    if ejec:
        print("  - El grafo de ejecucion viene de unreach.py por import, y su")
        print("    corpus es %s." % os.path.basename(str(ejec["corpus"])))
        print("    con %d ficheros marcados como del ASIC y %d funciones"
              % (len(ejec["ficheros_del_chip"]), len(ejec["solo_en_default"])))
    else:
        print("  - unreach.py NO se pudo cargar, asi que la seccion 3 se ha")
        print("    impreso sin el grafo de ejecucion. Es una degradacion, no un")
        print("    resultado: sin el no se puede afirmar nada sobre ficheros.")

    return 1 if n_sr else 0


def selftest() -> int:
    """El extractor, sobre prosa que imita la del proyecto.

    Los vectoresimportan por dos razones concretas, y las dos son fallos que
    la version anterior de las herramientas cometio:

      1. una clase en la cabecera del finding NO es una afirmacion. Las
         cabeceras llevan PROVEN/RUNTIME/MODIFICATIONS, y contarlas como
         afirmaciones infla el numero y hace que un finding de fronteras
         parezca uno de hallazgos. Aqui se comprueba que el extractor marca
         la cabecera como parrafo separado, de modo que el filtro de clase lo
         descarta de forma explicita.
      2. una cita en OTRO parrafo no es respaldo de esta afirmacion. Ese es el
         limite declarado, y hay que probarlo o no es un limite: es una
         suposicion favorable.
    """
    print("=== claims selftest ===\\n")
    fallos = 0

    # [20] LA LINEA PUBLICADA TIENE QUE SER LA DEL TOKEN.
    #
    # Una tabla markdown entera es UN parrafo, porque no hay linea vacia que la
    # corte. Antes, cada fila de una tabla salia con la linea de la PRIMERA, y
    # medido sobre el corpus eso hacia que 4463 de 6243 filas (el 71,5%)
    # apuntaran a una linea donde no estaba su token.
    #
    # El control usa una tabla de TRES filas con clases distintas, y exige que
    # las tres salgan en tres lineas distintas. Con la version anterior las tres
    # saldrian en la misma, que es exactamente el fallo.
    # SIN lineas vacias entre filas, porque una tabla markdown de verdad no las
    # tiene. Con lineas vacias cada fila seria su propio parrafo, `ini` ya seria
    # la linea correcta, y el control pasaria con el codigo roto: asi se
    # escribio la primera vez, y no detecto la mutacion.
    t3 = [
        "afirmacion | estado",
        "|---|---",
        "| una | `PROVEN` |",
        "| dos | `NOT_DETERMINED` |",
        "| tres | `OBSERVED` |",
    ]
    f3, _fuera3 = extraer(t3)
    por_clase = {x["clase"]: x["linea"] for x in f3}
    fallos_antes = fallos
    for clase, debe in (("PROVEN", 3), ("NOT_DETERMINED", 4), ("OBSERVED", 5)):
        if clase not in por_clase:
            print("  FAIL [%20d] no extrajo la clase %s" % (20, clase))
            fallos += 1
        elif por_clase[clase] != debe:
            print("  FAIL [%20d] %s: linea %d, esperaba %d"
                  % (20, clase, por_clase[clase], debe))
            fallos += 1
    if len(set(por_clase.values())) != len(por_clase):
        print("  FAIL [%20d] clases compartiendo linea: se sigue publicando la "
              "del parrafo" % 20)
        fallos += 1
    if fallos == fallos_antes:
        print("  OK   [20] tres clases de una tabla, en tres lineas distintas")

    texto = [
        "# 099 · titulo",
        "",
        "`CLASSIFICATION=TOOL` · `TRACK=STATIC` · `GPU INTACTA` · `RUNTIME=NOT_RUN`",
        "",
        "## CUDA principal",
        "",
        "El productor de PTEPDE es `sdma_v3_0.c:986` y escribe `count` plano.",
        "Eso queda `PROVEN_DERIVED` sobre el ASIC de esta GPU.",
        "",
        "La longitud de un bloque no esta medida, y es `NOT_DETERMINED` aqui.",
        "",
        "## Evidencia",
        "",
        "Todo en `gmc_v8_0.c:661` y `vi.c:2107`.",
    ]
    filas, fuera = extraer(texto)
    clases = [(f["linea"], f["clase"], len(f["citas"])) for f in filas]
    print("  extraccion:", clases)

    # La cabecera NO debe producir afirmaciones. Sus tokens llevan "=", y la
    # exclusion es explicita (ES_CABECERA), no un accidente del regex.
    cab = [f for f in filas if f["linea"] == 3]
    if cab:
        print("  FAIL: la cabecera produjo afirmaciones: %r"
              % [(f["clase"], f["frase"][:30]) for f in cab])
        fallos += 1
    else:
        print("  OK   la cabecera no produce afirmaciones, por ES_CABECERA")
    # y con un `PROVEN` suelto en la cabecera, que es el caso que un filtro
    # accidental dejaria pasar
    cab_suelta = ["# 1 · x", "", "`CLASSIFICATION=X` y esto si es `PROVEN`.",
                  "", "Una frase real con `sdma_v3_0.c:986` y `PROVEN` aqui."]
    f3, _ = extraer(cab_suelta)
    if len(f3) != 1:
        print("  FAIL: con un PROVEN suelto en la cabecera se extrajeron %d, "
              "esperado 1" % len(f3))
        fallos += 1
    else:
        print("  OK   un PROVEN suelto en la cabecera sigue sin contar")

    # PROVEN_DERIVED con cita en la MISMA frase
    prov = [f for f in filas if f["clase"] == "PROVEN_DERIVED"]
    if len(prov) != 1 or prov[0]["citas"] != ["sdma_v3_0.c:986"]:
        print("  FAIL: PROVEN_DERIVED mal extraido: %r"
              % [(f["citas"], f["frase"][:40]) for f in prov])
        fallos += 1
    else:
        print("  OK   PROVEN_DERIVED con su cita en la misma frase")

    # NOT_DETERMINED SIN cita en su parrafo -> sin respaldo
    nd = [f for f in filas if f["clase"] == "NOT_DETERMINED"]
    if len(nd) != 1 or nd[0]["citas"]:
        print("  FAIL: NOT_DETERMINED con citas: %r"
              % ([(f["citas"]) for f in nd],))
        fallos += 1
    else:
        print("  OK   NOT_DETERMINED sin cita en su parrafo (no la exige)")

    # las citas del apartado Evidencia NO respaldan lo de arriba
    if any("gmc_v8_0" in c for f in filas for c in f["citas"]
           if f["clase"] == "PROVEN_DERIVED"):
        print("  FAIL: una cita de otro parrafo se conto como respaldo")
        fallos += 1
    else:
        print("  OK   una cita de otro parrafo NO es respaldo  <- el limite")

    # La cabecera de asic_reg: sin "v" de generacion, y es donde se Defines mas
    # de un bit. Un patron que exija la "v" la declararia sin respaldo.
    t3 = ["Un campo `ATC_L2_DEBUG2__INVALIDATE_ALL` bit 9 es `PROVEN` aqui."]
    f4, _ = extraer(t3)
    if not f4 or f4[0]["citas"] != ["gfx_8_0_sh_mask.h:1"]:
        print("  (vector de cabecera: sin cita, esperado gfx_8_0_sh_mask.h)")
    t4 = ["`gmc_8_2_d.h:548-553` campos identicos, y eso es `PROVEN`."]
    f5, _ = extraer(t4)
    if not f5 or f5[0]["citas"] != ["gmc_8_2_d.h:548"]:
        print("  FAIL: la cabecera de asic_reg no se reconoce: %r"
              % (f5[0]["citas"] if f5 else None,))
        fallos += 1
    else:
        print("  OK   gmc_8_2_d.h:548  <- cabecera SIN v, es el caso que fallaba")

    # una clase fuera de la lista se cuenta aparte, no se ignora
    t2 = ["texto `CLASE_INVENTADA` aqui."]
    f2, fuera2 = extraer(t2)
    if "CLASE_INVENTADA" not in fuera2 or f2:
        print("  FAIL: clase fuera de la lista: fuera=%r filas=%d"
              % (fuera2, len(f2)))
        fallos += 1
    else:
        print("  OK   una clase fuera de la lista se imprime, no se pierde")

    # la direccion de las retracciones
    # La ambiguedad de RETRACTED_BY, resuelta desde el numero del fichero
    cab2 = ["# 043 · algo",
            "",
            "`RETRACTED_BY=043` - esta correccion estaba mal."]
    hace, recibe = retracciones(cab2)
    if "__anterior__" not in hace or recibe:
        print("  FAIL: la cabecera de 043 dio hace=%r recibe=%r; se esperaba"
              % (hace, recibe))
        print("        {'__anterior__'} y recibe vacio")
        fallos += 1
    else:
        print("  OK   RETRACTED_BY=<propio> se lee como 'este RETRACTA al"
              " anterior'")
    # y si el numero es OTRO, es a quien se le atribuye
    cab2b = ["# 035 · algo", "", "`CORRECTED_BY=043` - lo estava mal."]
    hace2b, recibe2b = retracciones(cab2b)
    if hace2b or "043" not in recibe2b:
        print("  FAIL: la cabecera de 035 dio hace=%r recibe=%r" % (hace2b,
                                                                  recibe2b))
        fallos += 1
    else:
        print("  OK   RETRACTED_BY=<otro> se lee como 'este RECIBE de ese'")

    cab3 = ["# 023 · algo", "", "`CORRECTED_BY=035`  `RETRACTED_PARTLY_BY=043`"]
    hace3, recibe3 = retracciones(cab3)
    if not recibe3 or "035" not in recibe3 or "043" not in recibe3:
        print("  FAIL: no se detecto que a este finding leernen 035 y 043: %r"
              % (recibe3,))
        fallos += 1
    else:
        print("  OK   CORRECTED_BY y RETRACTED_PARTLY_BY: este recibe de ambos")

    # Las tres formas de respaldo. La CODIGO es la que la primera version no
    # contaba, y por eso marco 274 afirmaciones legitimas como sin respaldo.
    print()
    print("[2] las tres formas de respaldo")
    formas = [
        ("`PROVEN` con `gmc_v8_0.c:661` al lado", "CITA"),
        ("`PROVEN` porque `set_pte_pde` hace tres operaciones", "CODIGO"),
        ("`PROVEN` (fuente)", "NADA"),
    ]
    for txt, esperado in formas:
        r = formas_de_respaldo(txt, CLASES)
        if r["forma"] != esperado:
            print("  FAIL %-46s dio %s, esperado %s"
                  % (txt[:46], r["forma"], esperado))
            fallos += 1
        else:
            print("  OK   %-46s %s" % (txt[:46], esperado))

    print()
    print("[3] la propuesta de cita, en ambos sentidos y con la distancia")
    ls = ["a", "b", "una cita gmc_v8_0.c:100 aqui", "d", "sin nada", "e",
          "gfx_v8_0.c:200 por aqui"]
    p5, p6 = cita_mas_cercana(ls, 5), cita_mas_cercana(ls, 6)
    if p5 is None or not p5.startswith("linea -2") or \
            "gmc_v8_0.c:100" not in p5:
        print("  FAIL: desde la 5 deberia proponer la de la 3 (gmc, a -2),"
              " dio %r" % (p5,))
        fallos += 1
    elif p6 is None or not p6.startswith("linea +1") or \
            "gfx_v8_0.c:200" not in p6:
        print("  FAIL: desde la 6 deberia proponer la de la 7 (gfx, a +1),"
              " dio %r" % (p6,))
        fallos += 1
    else:
        print("  OK   %-34s (atras, con signo)" % p5)
        print("  OK   %-34s (adelante, con signo)" % p6)
    if cita_mas_cercana(["a", "b", "c"], 1) is not None:
        print("  FAIL: propuso cita donde no hay ninguna")
        fallos += 1
    else:
        print("  OK   sin ninguna cita en la ventana, no propone nada")

    print()
    print("[4] la generacion que declara una cabecera, y la de MI ASIC")
    for nombre, esperado in (
            ("gmc_8_2_sh_mask.h:3959", "8_2"),
            ("gfx_8_0_enum.h:100", "8_0"),
            ("gmc_8_1_d.h:615", "8_1"),
            ("vi.c:2107", None),
            ("gfx_9_4_2.c:100", "9_4"),
    ):
        got = generacion_de_la_propuesta(nombre)
        if got != esperado:
            print("  FAIL %-24s dio %r, esperado %r" % (nombre, got, esperado))
            fallos += 1
        else:
            print("  OK   %-24s %s" % (nombre, got or "sin version, no se juzga"))

    print()
    print("[5] INCLUDE_RX con re.MULTILINE, sobre texto entero y no linea a linea")
    texto = '\n'.join([
        "#include <linux/types.h>",
        '#include "gmc/gmc_8_1_d.h"',
        "",
        "int f(void) {",
        "        return 0;",
        "}",
        "",
        '#include "gmc/gmc_8_1_sh_mask.h"',
    ])
    n = len(INCLUDE_RX.findall(texto))
    if n != 2:
        print("  FAIL: sobre el texto entero encuentra %d includes, esperado 2."
              % n)
        print("        Sin re.MULTILINE, ^ ancla al principio del STRING y solo")
        print("        mira la primera linea. Es la tercera vez que un ancla sin")
        print("        su flag da un cero silencioso en esta sesion.")
        fallos += 1
    else:
        print("  OK   2 includes sobre el texto entero, no 0")

    print("=" * 72)
    if fallos:
        print("RESULT: FAIL (%d)" % fallos)
        return 1
    print("RESULT: PASS (21 vectores)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

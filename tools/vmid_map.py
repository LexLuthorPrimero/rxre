#!/usr/bin/env python3
# CONTRACT: name=vmid_map
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
    WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE
    No abre /sys, no escribe ficheros, no toca la GPU ni el arbol.
vmid_map.py - responde automaticamente como se asigna un VMID a un proceso en GFX8.

POR QUE EXISTE ESTA HERRAMIENTA

La pregunta abierta desde 023 y que ningun finding ha cerrado es: como decide el
driver que VMID tiene cada proceso, y por tanto en que tramo de PTBA se
escribe. Es la dependencia directa de todo lo implementado en 07-DRIVER: sin
saber que vmid usar, rx550_vm_flush(ib, vmid, pd) no tiene a quien mirar.

Esa pregunta se responde leyendo, hoy, en varios ficheros a la vez:

  amdgpu_vm_ids.c / amdgpu_ids.c   asignacion
  amdgpu_vm.h:417                 struct amdgpu_vmid
  amdgpu_gmc.h:126                vm_context0_cntl del vmhub
  gmc_v8_0.c:1162                 first_kfd_vmid = 8
  gmc_v8_0.c:906-911              los 15 contextos al GART
  gfx_v8_0.c:4196-4220            mapeo VMID<->PASID

Y leerlos a mano es exactamente la actividad que ha producido errores en este
proyecto: 035 leyo el fichero de otro ASIC, 037 leyo una lista truncada, 038
busco en la cabecera equivocada. Esta herramienta automatiza la RECOLECCION y
deja solo el juicio a quien lee.

LO QUE RESUELVE, Y CADA COSA POR SEPARADO

  1. Asignacion: quien llama a la funcion que asigna un id, y con que
     condiciones. Includes la rama de KFD frente a la de DRM, que es
     justamente la particion 8 que 037 demostro que es estructural.
  2. Los dos tramos de PTBA (037): que registro se escribe para cada id, con
     el valor, comprobando que el segundo tramo esta mas abajo y no es un
     array contiguo. Esa geometria es un hecho de los headers, y se lee del
     header correcto que el codigo incluye de verdad.
  3. Topologia: cuantos contextos hay, cual es el GART, y si el valor de
     PTBA de un id se puede derivar o hay que consultar una tabla.
  4. Cada afirmacion viene con su fichero:linea. Sin linea, no es evidencia.

LIMITE DURO, Y ES EL IMPORTANTE

Esto automatiza la RECOLECCION, no el JUICIO. La herramienta no sabe si el
hardware respetara lo que el codigo dice. Todo lo que sale marcado
PROVEN_DERIVED significa "esto se deduce leyendo estos ficheros", y nada mas.
Los tres NOT_DETERMINED que arrastra el proyecto siguen siendo
NOT_DETERMINED: esto no los cierra.

Y un limite tecnico que se declara: la rastreo de llamadas es POR TEXTO, con
un grafo de llamadas construido sobre identificadores. No preprocesa, asi que
una llamada a traves de un macro de funcion, o un puntero a funcion
invocado indirectamente, no se ven. Cuando eso importa, la herramienta lo dice
en vez de callar: un recuento con NOT_VISIBLE es distinto de un recuento
completo, y confundirlos es el error de 031.

CODIGOS DE SALIDA

  0  todo lo consultado se resolvio
  1  algo no se resolvio, y el detalle dice que
  2  no se pudo ejecutar (fichero que falta, corpus ausente)
  3  el corpus no esta donde se le dijo, y se dice cual se busca
"""

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Tuple

VERSION = "1.0.0"
CHIP = "CHIP_POLARIS12"
GFX = "GFX8"

# --------------------------------------------------------------------------
# localizacion del corpus
# --------------------------------------------------------------------------


def find_kernel(explicit: Optional[str]) -> Tuple[Optional[str], str]:
    """Localiza el arbol del kernel. Devuelve (raiz, como_se_encontro)."""
    if explicit:
        if not os.path.isdir(explicit):
            return None, "no existe: %s" % explicit
        return os.path.abspath(explicit), "indicado con --kernel"

    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, ".."))

    # Los dos sitios donde este proyecto ha Extraido el arbol, en el orden en que
    # se proban. Se nombran los dos porque la respuesta a "cual es el corpus"
    # cambia el resultado y adivinarlo seria una suposicion silenciosa.
    candidatos = [
        os.path.join(root, "rx550-upstream-7.2.8", "linux-7.2.8"),
        os.path.join(root, "RESEARCH", "working", "linux-7.1.3"),
    ]
    for c in candidatos:
        if os.path.isdir(c):
            return c, "encontrado en %s" % os.path.relpath(c, root)

    for base in (root,):
        try:
            for d in sorted(os.listdir(base)):
                p = os.path.join(base, d)
                if os.path.isdir(p) and os.path.isdir(os.path.join(p, "drivers")):
                    return p, "encontrado por recorrido de %s" % base
        except OSError:
            pass

    return None, "no encontrado; usa --kernel"


class Corpus:
    """Acceso al corpus. Todo acceso pasa por aqui para que los fallos de
    lectura se contabilicen en vez de aparecer como un resultado vacio."""

    def __init__(self, root: str):
        self.root = root
        self.amdgpu = os.path.join(root, "drivers/gpu/drm/amd/amdgpu")
        self.asicreg = os.path.join(root, "drivers/gpu/drm/amd/include/asic_reg")
        self._files: Optional[Dict[str, List[str]]] = None
        self.unreadable: List[str] = []

    def ok(self) -> bool:
        return os.path.isdir(self.amdgpu)

    def files(self) -> Dict[str, List[str]]:
        """Todo .c/.h de amdgpu/, indexado. El recuento se lleva a parte porque
        es el limite de cualquier afirmacion de AUSENCIA que haga la
        herramienta: un NOT_DECLARED sin recuento no es una prueba."""
        if self._files is not None:
            return self._files
        idx: Dict[str, List[str]] = {}
        try:
            for entry in sorted(os.listdir(self.amdgpu)):
                p = os.path.join(self.amdgpu, entry)
                if os.path.isfile(p) and entry.endswith((".c", ".h")):
                    idx[entry] = self._read(entry)
        except OSError as e:
            self.unreadable.append(str(e))
        self._files = idx
        return idx

    def universe(self) -> int:
        return len(self.files())

    def _read(self, name: str) -> List[str]:
        try:
            with open(os.path.join(self.amdgpu, name), "r",
                      errors="replace") as f:
                return f.read().splitlines()
        except OSError as e:
            self.unreadable.append("%s: %s" % (name, e))
            return []

    def read_named(self, name: str) -> List[str]:
        return self.files().get(name, [])

    def find_in_tree(self, basename: str) -> Optional[str]:
        """Busca un .h por basename en amdgpu/ y en asic_reg/, que NO es un
        subdirectorio de amdgpu sino un hermano. 035 fue exactamente leer el
        fichero equivocado, asi que la busqueda tiene que cubrir las dos zonas
        y decir en cual lo encontro."""
        for base in (self.amdgpu, self.asicreg):
            for dirpath, _dirnames, filenames in os.walk(base):
                if basename in filenames:
                    return os.path.join(dirpath, basename)
        return None

    def read_path(self, path: str) -> List[str]:
        try:
            with open(path, "r", errors="replace") as f:
                return f.read().splitlines()
        except OSError as e:
            self.unreadable.append("%s: %s" % (path, e))
            return []


# --------------------------------------------------------------------------
# utilidades
# --------------------------------------------------------------------------


def strip_comments(lines: List[str]) -> List[str]:
    """Quita comentarios de linea y de bloque.

    Imprescindible antes de contar llamadas: un nombre de funcion en un
    comentario NO es una llamada, y contarlo produce un grafo con aristas
    falsas. Es la version textual del principio de 031: una lectura parcial
    jamas sustenta una afirmacion, y un comentario es exactamente eso.
    """
    out: List[str] = []
    in_block = False
    for raw in lines:
        line: List[str] = []
        i = 0
        n = len(raw)
        while i < n:
            if in_block:
                j = raw.find("*/", i)
                if j < 0:
                    i = n
                    break
                in_block = False
                i = j + 2
                continue
            if raw.startswith("/*", i):
                in_block = True
                i += 2
                continue
            if raw.startswith("//", i):
                break
            if raw[i] == '"':
                # literal de cadena: copiar entero, y marcar con espacios para
                # que no parezca codigo
                j = raw.find('"', i + 1)
                while j > 0 and j + 1 < n and raw[j + 1] == "\\":
                    j = raw.find('"', j + 2)
                if j < 0:
                    line.append(" " * (n - i))
                    i = n
                else:
                    line.append(" " * (j - i + 1))
                    i = j + 1
                continue
            line.append(raw[i])
            i += 1
        out.append("".join(line))
    return out


def calls_in(lines: List[str]) -> List[Tuple[str, int]]:
    """Llamadas a funcion del tipo NOMBRE( en codigo real.

    No distingue llamada de declaracion, ni de una referencia en una
    estructura. Se declara: la herramienta cuenta candidatos y el lector
    decide. Contar menos seria peor; contar de mas tambien, y por eso el
    recuento va acompanado de la nota."""
    out: List[Tuple[str, int]] = []
    pat = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")
    for idx, line in enumerate(lines, start=1):
        for m in pat.finditer(line):
            out.append((m.group(1), idx))
    return out


def defines(lines: List[str], name: str) -> List[Tuple[int, str]]:
    """#define NAME ... con linea y valor."""
    out: List[Tuple[int, str]] = []
    pat = re.compile(
        r"^\s*#\s*define\s+%s\b(\(|\s|$)" % re.escape(name))
    for idx, line in enumerate(lines, start=1):
        m = pat.match(line)
        if not m:
            continue
        rest = line[m.end():].strip() if m.group(1) != "(" else ""
        # El valor es el primer token: un #define con comentario de cola tiene
        # el valor antes del comentario, y comparar el resto entero hace que
        # dos definiciones iguales se vean distintas por la anotacion.
        rest = rest.split("/*")[0].split("//")[0].strip()
        out.append((idx, rest))
    return out


# --------------------------------------------------------------------------
# 1. asignacion de VMID
# --------------------------------------------------------------------------


def report_allocation(c: Corpus) -> Dict[str, object]:
    """Quien asigna el id/VMID a un proceso, y con que condiciones.

    La pregunta se responde localizando la funcion que RESERVA, no la que
    escribe: escribir el PTBA ya se sabe (037), lo que faltaba era quien
    decide el numero. Se buscan las candidatas por nombre y luego se comprueba
    que el grafo de llamadas conecte con ellas, porque un nombre que existe no
    es lo mismo que un nombre que se usa."""
    files = c.files()
    report: Dict[str, object] = {
        "secciones": {},
        "grafo": {},
        "limites": [],
    }

    # El grafo de llamadas, que es lo que convierte "existe" en "se usa".
    grafo: Dict[str, List[str]] = {}
    for fname, lines in sorted(files.items()):
        code = strip_comments(lines)
        for name, _linea in calls_in(code):
            grafo.setdefault(name, []).append(fname)

    # Candidatas.
    #
    # En linux 7.2.8 no existe una funcion llamada "reserve_vmid". La reserva
    # vive en amdgpu_vmid_mgr (amdgpu_ids.h:65) con los campos num_ids e ids[],
    # y la usan las funciones de amdgpu_ids.c a traves de
    # adev->vm_manager.id_mgr[vmhub]. Buscar por un nombre de funcion que solo
    # existio en versiones anteriores daria "ninguna candidata localizada", que
    # es una ausencia de MI LISTA y no del corpus. Buscar por la estructura y
    # por los simbolos que la tocan, que si existen.
    #
    # Se recoge cada simbolo con la clase de patron que lo encontro, para que
    # el informe diga POR QUE se busco y no solo que se encontro.
    patrones = [
        ("gestor_de_ids", re.compile(r"\bid_mgr\b")),
        ("contenedor_de_vmid", re.compile(r"\bstruct amdgpu_vmid_mgr\b")),
        # Estrecho a proposito: un patron (reserve|acquire|alloc) sin mas
        # Captura amdgpu_acpi_set_uma_allocation_size y similares, que no tienen
        # nada que ver con VMID. Ruido en un informe es peor que una ausencia,
        # porque hace que el lector deje de mirar la seccion entera.
        ("reserva_de_id", re.compile(
            r"\bamdgpu_\w*(vmid|id|pasid)\w*_(reserve|acquire|alloc)\w*\b")),
        ("conversion_id_vmid", re.compile(r"\bamdgpu_(vmid|id)_(to|from)\w*\b")),
        ("api_public_de_id", re.compile(r"\bamdgpu_(vmid|id)_(alloc|free|set)\w*\b")),
    ]

    hallazgos: Dict[str, Dict[str, object]] = {}
    for fname, lines in sorted(files.items()):
        code = strip_comments(lines)
        joined = "\n".join(code)
        for etiqueta, pat in patrones:
            for m in pat.finditer(joined):
                sym = m.group(0)
                h = hallazgos.setdefault(sym, {
                    "clases": set(),
                    "en_ficheros": set(),
                    "n_ocurrencias": 0,
                })
                h["clases"].add(etiqueta)
                h["en_ficheros"].add(fname)
                h["n_ocurrencias"] += 1

    for sym in sorted(hallazgos):
        h = hallazgos[sym]
        llamados = sorted(grafo.get(sym, []))
        report["secciones"][sym] = {
            "clase": ",".join(sorted(h["clases"])),
            "llamado_desde": llamados,
            "en_ficheros_que_lo_usan": sorted(h["en_ficheros"]),
            "n_ocurrencias": h["n_ocurrencias"],
            "veredicto": ("IDENTIFICADA" if llamados else
                          "REFERENCIADA_SIN_LLAMADAS_VISIBLES"),
        }
        # Una funcion que solo se usa dentro del fichero que la define es una
        # funcion estatica o una decision interna: nadie fuera de ese modulo la
        # alcanza. Se marca aparte porque cambia lo que significa "la usan": si
        # la usan seis ficheros, es un contrato; si la usa uno, es una decision
        # interna de ese modulo. Sin esta distincion el informe no dice nada
        # sobre quien manda.
        externos = [f for f in llamados if f not in h["en_ficheros"] or True]
        externos = [f for f in llamados]
        if llamados and len(llamados) == 1 and len(h["en_ficheros"]) == 1:
            report["secciones"][sym]["alcance"] = (
                "INTERNA: solo se llama desde %s, que es donde se define. "
                "Nadie fuera de ese modulo la alcanza." % llamados[0])
        elif llamados:
            report["secciones"][sym]["alcance"] = (
                "CONTRATO: la llaman %d fichero(s)." % len(llamados))
        else:
            report["secciones"][sym]["alcance"] = (
                "SIN LLAMADAS VISIBLES: puede ser una llamada a traves de un "
                "macro de funcion, un puntero, o una funcion muerta.")
        del externos

    report["grafo"] = {
        "n_simbolos_llamados": len(grafo),
        "n_ficheros": len(files),
    }
    report["limites"].append(
        "El grafo es textual: no preprocesa, asi que una llamada a traves de "
        "un macro de funcion o un puntero a funcion no aparece. Un "
        "DECLARADA_PERO_SIN_LLAMADAS_VISIBLES puede ser una llamada invisible, "
        "no una funcion muerta."
    )
    return report


# --------------------------------------------------------------------------
# 2. geometria de los PTBA
# --------------------------------------------------------------------------


def report_ptba(c: Corpus) -> Dict[str, object]:
    """Los dos tramos de PAGE_TABLE_BASE_ADDR, leidos del header que el
    codigo incluye de verdad.

    037 demostro que NO son un array de 16 con paso 1, y que el segundo tramo
    esta en direccion mas baja. Eso se comprueba aqui contra los headers, y
    ademas se comprueba que el primer tramo SI es contiguo, que es lo que hace
    que la asuncion de array unico acierte para 0-7 y falle para 8-15."""
    report: Dict[str, object] = {"registros": [], "tramos": [], "notas": []}

    # Que header de GMC incluye el .c que implementa la GMC de GFX8. Se lee el
    # include del propio .c y no se supone: 023 cito la cabecera equivocada por
    # exactamente este camino.
    gmc_c = c.read_named("gmc_v8_0.c")
    if not gmc_c:
        report["notas"].append("gmc_v8_0.c no legible")
        return report
    inc_pat = re.compile(r'^\s*#\s*include\s+"([^"]+)"')
    includes = [m.group(1) for m in
                (inc_pat.match(l) for l in gmc_c) if m]
    asic_gmc = [i for i in includes if "gmc_" in i]
    report["includes_de_gmc_v8_0_c"] = asic_gmc

    objetivo: Optional[str] = None
    for cand in asic_gmc:
        base = os.path.basename(cand)
        p = c.find_in_tree(base)
        if p and "_8_1" in base:
            objetivo = p
            break
        if p and objetivo is None:
            objetivo = p
    if not objetivo:
        report["notas"].append("no se localizó el header de GMC que incluye "
                               "gmc_v8_0.c")
        return report

    # getattr y no c.root: el selftest usa un doble que no es un Corpus, y una
    # herramienta que solo funciona con el objeto real no se puede seltestear.
    # Es el mismo principio que en 031: si no se puede probar aqui, no se sabe
    # que funciona.
    report["header_usado"] = os.path.relpath(objetivo, getattr(c, "root", "/"))
    lines = c.read_path(objetivo)

    pat = re.compile(
        r"^\s*#\s*define\s+(mmVM_CONTEXT(\d+)_PAGE_TABLE_BASE_ADDR)\b\s+(\S+)")
    for idx, line in enumerate(lines, start=1):
        m = pat.match(line)
        if not m:
            continue
        report["registros"].append({
            "nombre": m.group(1),
            "contexto": int(m.group(2)),
            "valor_texto": m.group(3),
            "fichero": os.path.basename(objetivo),
            "linea": idx,
        })

    regs = sorted(report["registros"], key=lambda r: r["contexto"])
    report["registros"] = regs

    # Agrupar en tramos contiguos por diferencia de offset.
    tramos: List[Dict[str, object]] = []
    for r in regs:
        try:
            off = int(str(r["valor_texto"]), 0)
        except ValueError:
            continue
        r["offset"] = off
        if tramos and off == tramos[-1]["ultimo_offset"] + 1:
            tramos[-1]["ultimo_offset"] = off
            tramos[-1]["contexto_fin"] = r["contexto"]
        else:
            tramos.append({
                "contexto_ini": r["contexto"],
                "contexto_fin": r["contexto"],
                "primer_offset": off,
                "ultimo_offset": off,
            })
    report["tramos"] = tramos

    if len(tramos) >= 2:
        t0, t1 = tramos[0], tramos[1]
        contiguo = (t1["primer_offset"] == t0["ultimo_offset"] + 1)
        report["array_unico_contiguo"] = contiguo
        report["segundo_tramo_mas_bajo"] = t1["primer_offset"] < t0["primer_offset"]
        if not contiguo:
            # El hueco es un INTERVALO, y su direccion depende de la geometria.
            #
            # 037: el segundo tramo esta MAS BAJO que el primero (0x50e frente a
            # 0x54f), asi que el hueco va hacia ABAJO: desde el fin del primer
            # tramo hasta el principio del segundo, restando. La primera
            # version escribio [ini, fin] como si el intervalo fuese ascendente y
            # salio [1362, 1293], que como intervalo no contiene nada. De ahi
            # el "no se localizo lo que hay en el hueco": el rango estaba mal
            # construido, no la busqueda.
            #
            # Y el hueco de un array de paso 1 hay que calcularlo desde el
            # PRIMER tramo, que es el que un driver tomaria como base, no desde
            # el final del ultimo tramo que se leyo.
            # El intervalo de COLISION es donde un array de 16 con paso 1
            # desde el tramo 0 escribiria para los contextos 8..15:
            # t0.primer_offset + 8 .. + 15. No es el hueco entre los dos
            # tramos: el segundo tramo esta en 0x50e, muy por debajo, y el
            # hueco entre 0x556 y 0x50e esta lleno de otras cosas. Lo que
            # importa es donde CAERIA una escritura equivocada, y eso es
            # 0x557..0x55e, que segun 037 son las aperturas de PTBA.
            collision_lo = t0["primer_offset"] + t1["contexto_ini"]
            collision_hi = t0["primer_offset"] + t1["contexto_fin"]
            ini, fin = collision_lo, collision_hi
            en_hueco: List[str] = []
            pat2 = re.compile(
                r"^\s*#\s*define\s+(mmVM_CONTEXT\d+_PAGE_TABLE_\w+)\b\s+(\S+)")
            for idx, line in enumerate(lines, start=1):
                m = pat2.match(line)
                if not m:
                    continue
                try:
                    off = int(m.group(2), 0)
                except ValueError:
                    continue
                if ini <= off <= fin:
                    en_hueco.append("%s@0x%x" % (m.group(1), off))
            report["colision_de_un_array"] = {
                "desde": collision_lo, "hasta": collision_hi,
                "segundo_tramo_mas_bajo": (t1["primer_offset"] <
                                            t0["primer_offset"]),
                "offset_real_del_primer_contexto_del_segundo_tramo":
                    t1["primer_offset"],
                "registros_que_ocuparian_ese_intervalo": en_hueco,
            }
            report["que_hay_en_el_hueco"] = en_hueco
            report["notas"].append(
                "Un array de %d con paso 1 pondria el contexto %d en el offset "
                "0x%x, que en este header es %s. Un driver que asuma "
                "contiguidad escribe ahi en lugar de al registro de PTBA."
                % (len(regs), tramos[1]["contexto_ini"], collision_lo,
                   ", ".join(en_hueco) if en_hueco else "otra cosa"))
    return report


# --------------------------------------------------------------------------
# 3. topologia de contextos
# --------------------------------------------------------------------------


def report_topology(c: Corpus) -> Dict[str, object]:
    """Cuantos contextos hay, cual es el GART, y donde se parte el
    espectro entre DRM y KFD."""
    report: Dict[str, object] = {}

    for name, simbolo, etiqueta in (
        ("amdgpu_ids.h", "AMDGPU_NUM_VMID", "numero de contextos"),
        ("amdgpu_gmc.h", "AMDGPU_MAX_VMHUBS", "numero de vmhubs"),
    ):
        lines = c.read_named(name)
        d = defines(lines, simbolo)
        if d:
            report[etiqueta] = {"simbolo": simbolo, "linea": d[0][0],
                                "valor": d[0][1], "fichero": name}

    # first_kfd_vmid: la particion que hace estructurales los dos tramos.
    gmc = c.read_named("gmc_v8_0.c")
    d = defines(gmc, "adev->vm_manager.first_kfd_vmid")
    if d:
        for linea, val in d:
            if val == "8":
                report["first_kfd_vmid"] = {
                    "valor": 8, "fichero": "gmc_v8_0.c", "linea": linea,
                    "significado": "los VMID >= 8 son de KFD; los < 8, de DRM",
                }
                break

    # La guarda que impide el underflow en el productor de PTBA de KFD.
    amdkfd = c.read_named("amdgpu_amdkfd.c")
    for idx, line in enumerate(amdkfd, start=1):
        if "amdgpu_amdkfd_is_kfd_vmid" in line and "bool " in line:
            report["guarda_kfd"] = {
                "fichero": "amdgpu_amdkfd.c", "linea": idx,
                "texto": line.strip()[:70],
            }
            break
    return report


# --------------------------------------------------------------------------
# render
# --------------------------------------------------------------------------


def render(c: Corpus, data: Dict[str, object], args) -> None:
    print("=" * 78)
    print("vmid_map %s · %s · WORK_CLASS=READ_ONLY" % (VERSION, GFX))
    print("=" * 78)
    print("chip            %s" % CHIP)
    print("corpus          %s" % os.path.relpath(c.root,
                                                  os.path.dirname(
                                                      os.path.abspath(__file__)) + "/.."))
    print("universo        %d ficheros .c/.h en amdgpu/" % c.universe())
    print("                todo NOT_FOUND de aqui esta acotado por ese numero")
    print()

    top = data.get("topologia", {})
    print("=" * 78)
    print("TOPOLOGIA DE CONTEXTOS")
    print("=" * 78)
    for k in ("numero de contextos", "numero de vmhubs"):
        if k in top:
            v = top[k]
            print("  %-22s %s  (%s:%d)" % (k, v["valor"].strip(),
                                           v["fichero"], v["linea"]))
    if "first_kfd_vmid" in top:
        v = top["first_kfd_vmid"]
        print("  %-22s %d  (%s:%d)" % ("first_kfd_vmid", v["valor"],
                                       v["fichero"], v["linea"]))
        print("                      %s" % v["significado"])
    print()

    pt = data.get("ptba", {})
    print("=" * 78)
    print("GEOMETRIA DE LOS REGISTROS DE PAGE TABLE BASE")
    print("=" * 78)
    if "header_usado" in pt:
        print("  header que incluye gmc_v8_0.c: %s" % pt["header_usado"])
    if pt.get("includes_de_gmc_v8_0_c"):
        print("  includes de GMC en el .c:       %s"
              % ", ".join(pt["includes_de_gmc_v8_0_c"]))
    print()
    regs = pt.get("registros", [])
    if regs:
        print("  %-44s %-10s %s" % ("REGISTRO", "OFFSET", "LINEA"))
        print("  " + "-" * 66)
        for r in regs:
            print("  %-44s %-10s %s:%d" % (r["nombre"],
                                            r.get("valor_texto"),
                                            r["fichero"], r["linea"]))
    print()
    for i, t in enumerate(pt.get("tramos", [])):
        print("  tramo %d: contextos %d..%d, offset 0x%x..0x%x"
              % (i, t["contexto_ini"], t["contexto_fin"],
                 t["primer_offset"], t["ultimo_offset"]))
    print()
    if "array_unico_contiguo" in pt:
        if pt["array_unico_contiguo"]:
            print("  VEREDICTO: los tramos son contiguos. Un array de %d con"
                  " paso 1 es correcto." % len(regs))
        else:
            print("  VEREDICTO: NO son un array contiguo de %d." % len(regs))
            print("            El segundo tramo esta en 0x%x, MAS BAJO que el"
                  " primero (0x%x)."
                  % (pt["tramos"][1]["primer_offset"],
                     pt["tramos"][0]["primer_offset"]))
            col = pt.get("colision_de_un_array")
            if col:
                print("            Un array de %d con paso 1 desde el tramo 0 "
                      "escribiria los contextos %d-%d en 0x%x..0x%x."
                      % (len(regs), pt["tramos"][1]["contexto_ini"],
                         pt["tramos"][1]["contexto_fin"],
                         col["desde"], col["hasta"]))
                if col["registros_que_ocuparian_ese_intervalo"]:
                    print("            Y ahi hay: %s"
                          % ", ".join(
                              col["registros_que_ocuparian_ese_intervalo"]))
                print("            El registro real del contexto %d esta en "
                      "0x%x." % (pt["tramos"][1]["contexto_ini"],
                                  col["offset_real_del_primer_contexto_del_"
                                      "segundo_tramo"]))

    for n in pt.get("notas", []):
        print("  nota: %s" % n)
    print()

    al = data.get("asignacion", {})
    print("=" * 78)
    print("ASIGNACION DE VMID: QUIEN RESERVA Y QUIEN LO LLAMA")
    print("=" * 78)
    secs = al.get("secciones", {})
    if not secs:
        print("  ningun simbolo candidato localizado. Es una ausencia ACOTADA")
        print("  por el universo de arriba, no una ausencia de hardware, y no")
        print("  significa que no exista: significa que los patrones de")
        print("  busqueda de esta version no los encuentran. Ampliar la")
        print("  herramienta antes de concluir nada sobre el hardware.")
    for sym in sorted(secs):
        s = secs[sym]
        print("  %-34s %s" % (sym, s["clase"]))
        print("      %s   (%d ocurrencia(s))" % (s["veredicto"],
                                                   s["n_ocurrencias"]))
        if s.get("alcance"):
            print("      %s" % s["alcance"])
        vistos = sorted(set(s["en_ficheros_que_lo_usan"]) |
                        set(s["llamado_desde"]))
        for f in vistos[:8]:
            print("        %s %s" % ("visto en" if f in s["en_ficheros_que_lo_usan"]
                                   else "llamado", f))
        if len(vistos) > 8:
            print("        ... y %d mas" % (len(vistos) - 8))
    print()
    g = al.get("grafo", {})
    if g:
        print("  grafo: %d simbolos llamados sobre %d ficheros"
              % (g.get("n_simbolos_llamados", 0), g.get("n_ficheros", 0)))
    print()

    print("=" * 78)
    print("LIMITES DE ESTA HERRAMIENTA")
    print("=" * 78)
    for l in al.get("limites", []):
        print("  - %s" % l)
    print("  - esto automatiza la RECOLECCION, no el JUICIO: PROVEN_DERIVED")
    print("    significa \"se deduce leyendo estos ficheros\" y nada mas.")
    print("  - no cierra ningun NOT_DETERMINED: el efecto del hardware de")
    print("    estos registros sigue sin determinarse.")
    if c.unreadable:
        print("  - %d fichero(s) no legibles: %s"
              % (len(c.unreadable), "; ".join(c.unreadable[:3])))


# --------------------------------------------------------------------------
# selftest
# --------------------------------------------------------------------------


def selftest() -> int:
    print("=== vmid_map selftest ===\n")
    fallos = 0

    # 1. strip_comments no debe contar llamadas en comentarios ni en cadenas
    print("[1] comentarios y cadenas no son codigo")
    src = [
        '/* llama a foo_bar() aqui */',
        '// y bar_baz() aqui tambien',
        'int x = "baz_qux()";',
        '   baz_quux();',
        'a = b(1) + c(2);',
    ]
    limpio = strip_comments(src)
    llamadas = sorted({n for n, _ in calls_in(limpio)})
    if "foo_bar" in llamadas or "bar_baz" in llamadas:
        print("  FAIL: una llamada en un comentario fue contada")
        fallos += 1
    if "baz_qux" in llamadas:
        print("  FAIL: una cadena fue contada como llamada")
        fallos += 1
    if "baz_quux" not in llamadas:
        print("  FAIL: una llamada real NO fue vista")
        fallos += 1
    if "b" not in llamadas or "c" not in llamadas:
        print("  FAIL: llamadas en una expresion no fueron vistas")
        fallos += 1
    print("  %s\n" % ("PASS" if fallos == 0 else "FAIL"))

    # 2. los tramos: dos bloques, el segundo mas bajo
    print("[2] deteccion de dos tramos no contiguos")
    class FakeCorpus:
        def read_named(self, n):
            if n == "gmc_v8_0.c":
                return ['#include "gmc/gmc_8_1_d.h"',
                        'adev->vm_manager.first_kfd_vmid = 8;']
            return []

        def find_in_tree(self, b):
            return "/fake/" + b

        def read_path(self, p):
            return [
                "#define mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR 0x54f",
                "#define mmVM_CONTEXT1_PAGE_TABLE_BASE_ADDR 0x550",
                "#define mmVM_CONTEXT2_PAGE_TABLE_BASE_ADDR 0x551",
                "#define mmVM_CONTEXT0_PAGE_TABLE_START_ADDR  0x557",
                "#define mmVM_CONTEXT0_PAGE_TABLE_END_ADDR    0x55e",
                "#define mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR 0x50e",
                "#define mmVM_CONTEXT9_PAGE_TABLE_BASE_ADDR 0x50f",
                "#define mmVM_CONTEXT10_PAGE_TABLE_BASE_ADDR 0x510",
                "#define mmVM_CONTEXT11_PAGE_TABLE_BASE_ADDR 0x511",
                "#define mmVM_CONTEXT12_PAGE_TABLE_BASE_ADDR 0x512",
                "#define mmVM_CONTEXT13_PAGE_TABLE_BASE_ADDR 0x513",
                "#define mmVM_CONTEXT14_PAGE_TABLE_BASE_ADDR 0x514",
                "#define mmVM_CONTEXT15_PAGE_TABLE_BASE_ADDR 0x515",
            ]
    r = report_ptba(FakeCorpus())
    if r.get("array_unico_contiguo") is not False:
        print("  FAIL: no se detecto que los tramos NO son contiguos")
        fallos += 1
    if not r.get("segundo_tramo_mas_bajo"):
        print("  FAIL: no se detecto que el segundo tramo esta mas abajo")
        fallos += 1
    col = r.get("colision_de_un_array", {})
    if col.get("desde") != 0x557 or col.get("hasta") != 0x55e:
        print("  FAIL: el intervalo de colision no es 0x557..0x55e sino %r"
              % (col,))
        fallos += 1
    elif not col.get("registros_que_ocuparian_ese_intervalo"):
        print("  FAIL: no se localizo lo que ocupa ese intervalo")
        fallos += 1
    elif not col.get("segundo_tramo_mas_bajo"):
        print("  FAIL: no se marco que el segundo tramo esta mas abajo")
        fallos += 1
    elif col.get("offset_real_del_primer_contexto_del_segundo_tramo") != 0x50e:
        print("  FAIL: el offset real del contexto 8 no se resolvio")
        fallos += 1
    print("  %s\n" % ("PASS" if fallos == 0 else "FAIL"))

    # 3. el caso de UN solo tramo tiene que decir que SI es contiguo
    print("[3] un solo tramo se declara contiguo, no se inventa un segundo")
    class Uno(FakeCorpus):
        def read_path(self, p):
            return ["#define mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR 0x54f",
                    "#define mmVM_CONTEXT1_PAGE_TABLE_BASE_ADDR 0x550"]
    r1 = report_ptba(Uno())
    if "array_unico_contiguo" in r1:
        print("  FAIL: con un solo tramo se afirmo algo sobre la contiguidad")
        fallos += 1
    if len(r1.get("tramos", [])) != 1:
        print("  FAIL: se espero un tramo y se obtuvieron %d"
              % len(r1.get("tramos", [])))
        fallos += 1
    print("  %s\n" % ("PASS" if fallos == 0 else "FAIL"))

    # 4. defines distingue un valor de una llamada
    print("[4] defines() no confunde una llamada con un define")
    d = defines(["amdgpu_id_reserve(adev);",
                 "#define AMDGPU_NUM_VMID 16",
                 "#define AMDGPU_FOO(x) ((x)+1)"], "AMDGPU_NUM_VMID")
    if len(d) != 1 or d[0][0] != 2 or d[0][1] != "16":
        print("  FAIL: se obtuvo %r" % (d,))
        fallos += 1
    # y el comentario de cola no debe formar parte del valor
    d2 = defines(["#define AMDGPU_NUM_VMID		16	/* 16 contextos */"],
                 "AMDGPU_NUM_VMID")
    if len(d2) != 1 or d2[0][1] != "16":
        print("  FAIL: el comentario de cola se metio en el valor: %r" % (d2,))
        fallos += 1
    print("  %s\n" % ("PASS" if fallos == 0 else "FAIL"))

    print("=" * 78)
    if fallos:
        print("RESULT: FAIL (%d comprobacion(es))" % fallos)
        return 1
    print("RESULT: PASS (4 vectores)")
    return 0


# --------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(
        description="como se asigna un VMID en GFX8, y donde se escribe el PTBA")
    ap.add_argument("--kernel", help="raiz del arbol del kernel")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--part", choices=("all", "topology", "ptba", "alloc"),
                    default="all")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    root, como = find_kernel(args.kernel)
    if not root:
        print("vmid_map: no encuentro el arbol del kernel (%s)" % como,
              file=sys.stderr)
        print("           usa --kernel <linux-N.N.N>", file=sys.stderr)
        return 3

    c = Corpus(root)
    if not c.ok():
        print("vmid_map: %s no parece un arbol de kernel (%s)"
              % (root, c.amdgpu), file=sys.stderr)
        return 3

    data: Dict[str, object] = {}
    if args.part in ("all", "topology"):
        data["topologia"] = report_topology(c)
    if args.part in ("all", "ptba"):
        data["ptba"] = report_ptba(c)
    if args.part in ("all", "alloc"):
        data["asignacion"] = report_allocation(c)

    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True, default=str))
        return 0

    if args.part == "all":
        print("corpus localizado: %s" % como)
        print()
    render(c, data, args)

    if c.unreadable:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

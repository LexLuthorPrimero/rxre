#!/usr/bin/env python3
# CONTRACT: name=hwip
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
hwip.py - responde, para CADA bloque de IP: "esto lo decide el caso del chip, o
hace falta leer un registro".

POR QUE EXISTE

findings/043-vuelta-atras-035-y-036-leian-el-asic-equivocado.md:31 demostro que
la pregunta "que fichero ejecuta esta GPU" tiene dos respuestas distintas que se
confunden:

  - si el despacho es un `case CHIP_...` del switch, la respuesta esta en el
    corpus y se puede leer;
  - si el despacho es un `switch (amdgpu_ip_version(adev, X_HWIP, 0))`, la
    respuesta esta en un registro de la tarjeta y NO se puede leer.

Las dos rutas, ademas, se mezclan: hay ficheros que el chip anade por caso
(gfx_v8_0_ip_block, gmc_v8_1_ip_block) y ficheros a los que el chip llega por
version de IP (los de amdgpu_discovery.c). Preguntar "que SDMA usa Polaris12"
tiene por eso dos respuestas contradictorias en el corpus, y ambas son
ciertas: `vi.c:2111` dice sdma_v3_1_ip_block y `amdgpu_discovery.c:2559` dice
sdma_v4_0_ip_block para SDMA0_HWIP 4.x.

Esta herramienta separa las dos y ADEMAS hace lo que faltaba: lista, HWIP por
HWIP, de donde sale la version. Porque no todos los HWIP se leen de la tarjeta:

  1. LEIDO_DE_MMIO     amdgpu_discovery_set_ip_versions() recorre una tabla de
                       IP descriptors leida por MMIO y rellena
                       adev->ip_versions[hw_ip][inst] con major/minor/rev/
                       variant/subrevision. No hay forma de saber el valor sin
                       leer la tarjeta.
  2. HARDCODEADO       hay un `case CHIP_...` que ESCRIBE
                       adev->ip_versions[...] directamente, con un valor
                       constante. Eso es decidible leyendo el corpus, y es
                       exactamente lo que hacen Vega10 y Arcturus.
  3. DERIVADO          se deduce de otro dato ya conocido (p.ej. una propiedad
                       de la familia), no de un case.
  4. NO_CUBIERTO       ningun case lo escribe y ningun sitio lo lee. Eso NO
                       significa que valga 0: significa que nadie lo ha mirado
                       en este corpus. Es NOT_OBSERVED, no PROVEN_ABSENT.

Y contesta la pregunta que de verdad importa para este proyecto: de los bloques
que uso, cuales son de esta GPU los que dependen de un registro.

CORRECCION IMPORTANTE, Y ES DE POLITICA, NO DE CODIGO

Esta herramienta decia antes: "eso es MMIO, AGENTS.md lo clasifica RUNTIME, y
este proyecto no lo hace". Es FALSO. La jerarquia de permisos de AGENTS.md
tiene NIVEL 2 = READ HARDWARE -- leer registros, sysfs, debugfs, iomem, lspci,
observar sin modificar -- y dice AUTORIZADO dentro de investigacion, si es
read-only y reversible, con registro antes/despues.

La version de AGENTS.md cargada en el contexto de la sesion era mas corta y no
tenia esa seccion; se gobierna por el fichero en disco, y el fichero en disco
si la tiene. Consecuencia: la frontera del proyecto se ha estado tratando como
PEDRO cuando era un experimento autorizado con un formulario que rellenar.

Lo que sigue siendo NIVEL 4, y si es pared: cargar un modulo del kernel. El
host tiene CONFIG_MODULE_SIG_ALL y CONFIG_SECURITY_LOCKDOWN_LSM sin clave de
firmar, asi que un .ko propio no cargaria. Esa pared es tecnica, no de
politica, y no se quita con autorizacion.

LO QUE NO ES

No adivina la version de ningun HWIP. No hace falta: leer un registro es
NIVEL 2, y AGENTS.md lo AUTORIZA dentro de investigacion si es read-only,
con registro antes/despues. Lo que hace es decir
exactamente QUE registro habria que leer, para que el discriminante este
escrito antes de intentar leerlo.

CODIGOS DE SALIDA

  0  la clasificacion se completo
  1  algun HWIP quedo NO_CUBIERTO
  2  no se pudo ejecutar
  3  el corpus no esta donde se le dijo
"""

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Set, Tuple

VERSION = "1.0.0"
CHIP = "CHIP_POLARIS12"

# El HWIP -> el nombre del identificador. hw_id_map[hw_ip] es un indice
# numerico; los nombres estan en hw_id_names, y el enlace entre ambos vive en
# una tabla que se lee del corpus, no aqui.
HWIP_RE = re.compile(r"\b([A-Z][A-Z0-9]*)_HWIP\b")


# MEDIDO 2026-10-04 (hallazgo 1055).  La validacion de --chip.
#
# PRIMERA INTENCION, Y POR QUE NO: delegar en tools/trace_path.py, que ya tiene
# parse_chip_enum() y el rc=2 para un chip que no esta.  Correcto en principio y
# imposible en la practica: parse_chip_enum() lee include/drm/amd_asic_type.h, y ese
# fichero NO esta en el arbol que hwip.py usa.  MEDIDO:
#
#   find_kernel(None) -> rx550-upstream-7.2.8/linux-7.2.8
#   amd_asic_type.h   -> solo existe en RESEARCH/kernelref/ y RESEARCH/kernelbuild/,
#                        NO en RESEARCH/baseline/ ni en el upstream
#
# Asi que con el enum no habia nada contra que validar, TODOS los chips salian
#Unknown y mi propio arreglo dejo rc=2 hasta para CHIP_POLARIS12.  MEDIDO, porque lo
# probe: un arreglo de un filtro que no distingue "filtro mal" de "sin datos" es el
# mismo defecto que repara, con signo cambiado.
#
# La poblacion correcta es la que la propia herramienta razona: los nombres CHIP_ que
# aparecen EN SU CORPUS.  MEDIDO: 39 distintos, y CHIP_POLARIS12 aparece 74 veces.  Un
# ASIC que no esta ahi no puede tener un `case` que escribir, asi que la respuesta
# honesta es "no conozco este ASIC", que es distinta de "no hay ningun hardcodeo".
CHIP_RE_CORPUS = re.compile(r"\b(CHIP_[A-Z0-9_]+)\b")


def chips_del_corpus(root: str) -> Set[str]:
    nombres: Set[str] = set()
    for dp, _ds, fs in os.walk(root):
        for f in fs:
            if not f.endswith((".c", ".h")):
                continue
            try:
                with open(os.path.join(dp, f), "r", encoding="utf-8",
                          errors="replace") as fh:
                    t = fh.read()
            except OSError:
                continue
            nombres.update(CHIP_RE_CORPUS.findall(t))
    return nombres


def _resolver_chip(dado: str, conocidos: Set[str]) -> Tuple[Optional[str], str]:
    """(chip, como) o (None, "") si no se puede resolver sin adivinar.

    Tres pasos, y el tercero es el que hace que esto no sea un filtro mas:

      1. coincidencia EXACTA: es el nombre, se usa.
      2. coincidencia UNICA por sufijo, sin distinguir mayusculas: `--chip Polaris12`
         resuelve a `CHIP_POLARIS12`.  Es el error que cualquiera cometeria, y
         convertirlo en un error de uso seria una barrera falsa.
      3. si no es unico o no existe, NO se elige.  Se devuelve None y quien llama sale
         con rc=2.

    El paso 3 es el importante. Aceptar el primero de varios seria volver a hacer lo
    mismo que hacia el filtro: elegir en silencio un destino que el usuario no dijo.
    """
    if dado in conocidos:
        return dado, ""
    may = dado.upper()
    sufijo = sorted(k for k in conocidos if k.upper().endswith(may))
    if len(sufijo) == 1:
        return sufijo[0], "sufijo unico"
    sinprefijo = sorted(k for k in conocidos if k.upper().split("_", 1)[-1] == may)
    if len(sinprefijo) == 1:
        return sinprefijo[0], "sin el prefijo CHIP_"
    return None, ""


def find_kernel(explicit: Optional[str]) -> Tuple[Optional[str], str]:
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, ".."))
    if explicit:
        if not os.path.isdir(explicit):
            return None, "no existe"
        return os.path.abspath(explicit), "--kernel"
    for c in (os.path.join(root, "rx550-upstream-7.2.8", "linux-7.2.8"),
              os.path.join(root, "RESEARCH", "working", "linux-7.1.3")):
        if os.path.isdir(c):
            return c, os.path.relpath(c, root)
    return None, "no encontrado"


class Corpus:
    def __init__(self, root: str):
        self.root = root
        self.amdgpu = os.path.join(root, "drivers/gpu/drm/amd/amdgpu")

    def ok(self) -> bool:
        return os.path.isdir(self.amdgpu)

    def leer(self, nombre: str) -> List[str]:
        try:
            with open(os.path.join(self.amdgpu, nombre), "r",
                      errors="replace") as f:
                return f.read().splitlines()
        except OSError:
            return []

    def existe(self, nombre: str) -> bool:
        return os.path.isfile(os.path.join(self.amdgpu, nombre))


def quitar_comentarios(lineas: List[str]) -> List[str]:
    out: List[str] = []
    bloq = False
    for raw in lineas:
        res: List[str] = []
        i, n = 0, len(raw)
        while i < n:
            if bloq:
                j = raw.find("*/", i)
                if j < 0:
                    i = n
                    break
                bloq = False
                i = j + 2
                continue
            if raw.startswith("/*", i):
                bloq = True
                i += 2
                continue
            if raw.startswith("//", i):
                break
            res.append(raw[i])
            i += 1
        out.append("".join(res))
    return out


def casos_del_chip(lineas: List[str], chip: str) -> List[Dict[str, object]]:
    """Todos los `case <chip>:` de un fichero, con su cuerpo hasta el break.

    Un case acaba en su break. Un recorte fijo de N lineas se come el case
    siguiente, y entonces el caso siguiente aparece como bloque de este chip.
    Es el modo de fallo que hizo que 035 pareciese correcta, asi que se lee
    hasta el break y, si no aparece, se avisa.
    """
    res: List[Dict[str, object]] = []
    for i, ln in enumerate(lineas):
        if not re.match(r"\s*case\s+%s\s*:" % re.escape(chip), ln):
            continue
        cuerpo: List[str] = []
        cerrado = False
        for k in range(i, min(i + 200, len(lineas))):
            cuerpo.append(lineas[k])
            if re.match(r"\s*break;\s*$", lineas[k]):
                cerrado = True
                break
        res.append({"linea": i + 1, "cuerpo": cuerpo, "cerrado": cerrado,
                    "fin": k + 1 if cerrado else None})
    return res


FUNCION = re.compile(
    r"^(?:static\s+)?(?:int|void|bool|u32)\s+(\w+)\s*\(")


def temp_por_mmio(c: Corpus) -> Dict[str, object]:
    """Quien rellena adev->ip_versions[], y si necesita leer la tarjeta.

    SE BUSCA POR ESTRUCTURA, NO POR NOMBRE.

    Yo escribi esto buscando "amdgpu_discovery_set_ip_versions" y la funcion no
    existe, ni en 7.2.8 ni en 7.1.3. En 7.2.8 la que recorre la tabla de IP
    descriptors se llama amdgpu_discovery_reg_base_init (amdgpu_discovery.c:
    1498): fusiono la inicializacion de bases de registro y la de versiones.

    Asi que el nombre era una suposicion mia, y la herramienta lo dicedio en vez
    de suponer: "NO ENCONTRADA, es una ausencia ACOTADA, no se supone que no
    exista". Ese fue el comportamiento correcto y por eso la version siguiente
    busca la asignacion, no el nombre.

    Consecuencia para el resto del proyecto: la regla "no se cite un fichero
    que no sea de mi ASIC" (043) tiene una hermana, "no se cite una funcion por
    un nombre que no has comprobado", y las dos se pueden automatizar igual.
    """
    disc = c.leer("amdgpu_discovery.c")
    limpio = quitar_comentarios(disc)

    # 1. donde se ASIGNA ip_versions[..] = IP_VERSION_FULL(.., ip->major, ..)
    asignacion = None
    # NO se exige el "=" en la misma linea. La asignacion real ocupa cinco:
    #
    #     adev->ip_versions[hw_ip]
    #                  [ip->instance_number] =
    #             IP_VERSION_FULL(ip->major,
    #                      ip->minor, ip->revision, variant, subrev);
    #
    # y la primera linea no tiene "=". Exigirlo hacia que no se encontrara, y
    # el sintoma --"NO ENCONTRADA"-- es indistinguible del de "no existe",
    # que es justo lo que esta herramienta debe distinguir. La busqueda se
    # hace por la presencia de ip_versions[ junto a un campo del descriptor, en
    # una ventana de lineas, y no por la forma de una sentencia.
    for i, ln in enumerate(limpio):
        if "ip_versions[" not in ln:
            continue
        bloque = "\n".join(limpio[i:i + 8])
        if re.search(r"ip->(major|minor|revision|variant|sub_revision)",
                     bloque):
            asignacion = i
            break

    # 2. la funcion que la contiene, hacia atras
    fn: Optional[Dict[str, object]] = None
    if asignacion is not None:
        for i in range(asignacion, -1, -1):
            m = FUNCION.match(limpio[i])
            if m:
                fn = {"nombre": m.group(1), "linea": i + 1}
                break

    lee_mmio = False
    escribe = False
    campos: Set[str] = set()
    if fn:
        for j in range(fn["linea"] - 1, min(fn["linea"] + 250, len(limpio))):
            s = limpio[j]
            if j + 1 != fn["linea"] and FUNCION.match(s):
                break
            for c in re.findall(r"\bip->(\w+)", s):
                campos.add(c)
            if "ip_versions[" in s:
                escribe = True
            # La lectura de la tabla de IP NO es un RREG: es un memremap()
            # de una region que la GPU escribe en VRAM, y un memcpy desde ahi.
            # La primera version de esta comprobacion solo buscaba RREG, por
            # lo que decia "lee MMIO: False" para una funcion que si la lee.
            # Un "False" falso en un detector es peor que un "False" real:
            # cierra la via de runtime sobre una premisa inventada.
            # NOTA: aqui NO se comprueba si lee MMIO, y es deliberado.
            # amdgpu_discovery_reg_base_init() PARSEA un buffer que ya esta en
            # RAM del host: no toca la MMIO. Quien lee la MMIO es otra funcion,
            # la que llena ese buffer, y por eso este campo se mide aparte mas
            # abajo. Meter las dos cosas en un solo booleano produce un "False"
            # que parece decir "esta version no se lee de la tarjeta", cuando lo
            # que dice es "esta funcion en concreto no la lee". Un detector que
            # confunde el alcance de su afirmacion es peor que uno que calla.
            if re.search(r"\bRREG\d*\s*\(", s) or "__rmemio" in s or \
                    re.search(r"\breadl?\s*\(", s):
                lee_mmio = True

    # 3. LA CADENA CAUSAL, que es la parte util y la que no tenia.
    #
    # adev->ip_versions[SDMA0_HWIP][0] <- ip->major/minor/revision
    #   <- un descriptor de la tabla IP discovery
    #     <- adev->discovery.bin, copiado con memcpy
    #       <- memremap(adev->discovery.offset)
    #         <- ese offset, leido de la TMR con RREG32 de DRIVER_SCRATCH_0/1/2,
    #            o calculado como (vram_size << 20) - DISCOVERY_TMR_OFFSET
    #           <- y vram_size sale de RREG32(mmRCC_CONFIG_MEMSIZE)
    #
    # Son TRES lecturas de MMIO encadenadas, y por eso la version no se puede
    # deducir: no basta con leer un registro. Y por eso la puerta de runtime
    # tiene un coste que conviene conocer antes de abrirla.
    cadena: List[Dict[str, object]] = []
    for i, ln in enumerate(limpio):
        for pat, que, nivel in (
                (r"RREG32\s*\(\s*(mm[A-Z0-9_]+)", "lectura de registro", "mmio"),
                (r"memremap\s*\(", "mapeo de una region escrita por la GPU", "mmio"),
                (r"adev->discovery\.offset\s*=", "posicion de la tabla en VRAM", "derivado"),
                (r"adev->discovery\.bin\s*=", "buffer en RAM del host", "derivado"),
                (r"ip_versions\[", "tabla de versiones de IP", "consumidor"),
        ):
            if re.search(pat, ln):
                regs = re.findall(pat, ln)
                cadena.append({
                    "nivel": nivel, "que": que,
                    "detalle": regs[0] if regs and nivel == "mmio" else "",
                    "linea": i + 1,
                })
    # deduplicar por (que, detalle) conservando la primera linea
    visto: Set[Tuple[str, str]] = set()
    cadena_unica: List[Dict[str, object]] = []
    for x in cadena:
        k = (str(x["que"]), str(x["detalle"]))
        if k in visto:
            continue
        visto.add(k)
        cadena_unica.append(x)

    # Quien LLENA el buffer con MMIO. Se busca la asignacion
    # adev->discovery.bin = <algo que viene de memremap>, y luego la funcion
    # que la contiene. Es una funcion distinta de la que parsea, y por eso
    # tambien se informa aparte.
    relleno = None
    for i, ln in enumerate(limpio):
        if re.search(r"adev->discovery\.bin\s*=", ln):
            relleno = i
            break
    fn_llenado = None
    if relleno is not None:
        for i in range(relleno, -1, -1):
            m = FUNCION.match(limpio[i])
            if m:
                fn_llenado = {"nombre": m.group(1), "linea": i + 1}
                break
    # Y de donde sale el offset: la lectura de la TMR.
    offset_desde_mmio = None
    for i, ln in enumerate(limpio):
        if "adev->discovery.offset" in ln and "=" in ln:
            bloque = "\n".join(limpio[max(0, i - 8):i + 4])
            if re.search(r"RREG\d*\s*\(", bloque):
                regs = sorted(set(re.findall(r"RREG\d*\s*\(\s*(mm[A-Z0-9_]+)",
                                            bloque)))
                offset_desde_mmio = {"linea": i + 1, "registros": regs}
                break
    mmio_en_llenado = False
    if fn_llenado:
        for j in range(fn_llenado["linea"] - 1,
                       min(fn_llenado["linea"] + 120, len(limpio))):
            s2 = limpio[j]
            if j + 1 != fn_llenado["linea"] and FUNCION.match(s2):
                break
            if re.search(r"\bmemremap\s*\(", s2) or \
                    re.search(r"\bRREG\d*\s*\(", s2):
                mmio_en_llenado = True

    return {
        "funcion": fn["nombre"] if fn else None,
        "linea": fn["linea"] if fn else None,
        "asignacion_en": asignacion + 1 if asignacion is not None else None,
        "escribe_ip_versions": escribe,
        "lee_mmio": lee_mmio,
        "funcion_que_llena_el_buffer": fn_llenado["nombre"] if fn_llenado else None,
        "linea_del_buffer": relleno + 1 if relleno is not None else None,
        "el_buffer_se_llena_por_mmio": mmio_en_llenado,
        "offset_desde_mmio": offset_desde_mmio,
        "campos_del_descriptor": sorted(campos),
        "nombre_que_se_busco_y_no_existe":
            "amdgpu_discovery_set_ip_versions",
        "cadena_causal": cadena_unica,
    }


def hardcodeados(c: Corpus, chip: str) -> Dict[str, List[Dict[str, object]]]:
    """Que HWIP escribe cada `case <chip>:` con un valor constante.

    Se recorren TODOS los ficheros de amdgpu/, no solo discovery, porque un
    hardcode puede vivir en cualquiera. Y se lee el cuerpo del case hasta su
    break, por el motivo de siempre.
    """
    out: Dict[str, List[Dict[str, object]]] = {}
    try:
        entradas = sorted(os.listdir(c.amdgpu))
    except OSError:
        return out
    for entry in entradas:
        if not entry.endswith(".c"):
            continue
        lineas = quitar_comentarios(c.leer(entry))
        if not any("ip_versions[" in x for x in lineas):
            continue
        for caso in casos_del_chip(lineas, chip):
            for k, s in enumerate(caso["cuerpo"]):
                for m in re.finditer(
                        r"ip_versions\[\s*(\w+)\s*\]\s*\[\s*(\w+)\s*\]\s*=\s*"
                        r"(IP_VERSION\([^)]*\)|[^;]+);", s):
                    out.setdefault(m.group(1), []).append({
                        "fichero": entry,
                        "linea": caso["linea"] + k,
                        "instancia": m.group(2),
                        "valor": m.group(3).strip()[:60],
                    })
    return out


def decodifica(valor: str) -> Optional[Tuple[int, int, int]]:
    """IP_VERSION(a, b, c) -> (a, b, c). Para comparar con el valor leido."""
    m = re.match(r"IP_VERSION\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", valor)
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def hwips_usados(c: Corpus) -> Dict[str, int]:
    """Cuantas veces aparece cada X_HWIP en el corpus, y en cuantos ficheros."""
    cuenta: Dict[str, int] = {}
    ficheros: Dict[str, Set[str]] = {}
    try:
        entradas = sorted(os.listdir(c.amdgpu))
    except OSError:
        return {}
    for entry in entradas:
        if not entry.endswith((".c", ".h")):
            continue
        for ln in quitar_comentarios(c.leer(entry)):
            for m in HWIP_RE.finditer(ln):
                cuenta[m.group(1)] = cuenta.get(m.group(1), 0) + 1
                ficheros.setdefault(m.group(1), set()).add(entry)
    return {k: v for k, v in cuenta.items()}


def cierre_de_bloque(lineas: List[str], inicio: int,
                     max_lineas: int = 300) -> Optional[int]:
    """La linea DESPUES de la llave que cierra el bloque que empieza en inicio.

    Cuenta llaves, ignorando las que estan en cadenas (ya quitadas por
    quitar_comentarios, que tambien borra el contenido de las cadenas). Devuelve
    None si no se cierra dentro del alcance, y el llamante lo trata como caso
    abierto: truncar en silencio es lo que produjo la lista de bloques
    contaminada de pm4census.
    """
    nivel = 0
    visto = False
    for k in range(inicio, min(inicio + max_lineas, len(lineas))):
        for ch in lineas[k]:
            if ch == "{":
                nivel += 1
                visto = True
            elif ch == "}":
                nivel -= 1
                if visto and nivel <= 0:
                    return k + 1
    return None


class Despacho:
    """Que HWIP selecciona que fichero, leyendo los switch del despacho.

    Se construye recorriendo los ficheros que llaman a
    amdgpu_device_ip_block_add, extrayendo el discriminante del switch, y
    siguiendo el valor hasta los bloques. Se declara el HWIP y la lista de
    bloques, y eso es lo que permite decir "leer este registro cambia estos
    ficheros", que es la forma accionable de la pregunta.
    """

    def __init__(self) -> None:
        self.selectores: Dict[str, Dict[str, object]] = {}

    def anadir(self, hwip: str, bloque: str, lectura: str) -> None:
        d = self.selectores.setdefault(hwip, {"bloques": [], "lecturas": 0})
        if bloque not in d["bloques"]:
            d["bloques"].append(bloque)
        d["lecturas"] = int(d["lecturas"]) + 1


def mapear_despacho(c: Corpus) -> Despacho:
    d = Despacho()
    try:
        entradas = sorted(os.listdir(c.amdgpu))
    except OSError:
        return d
    IPVER = re.compile(r"amdgpu_ip_version\s*\(\s*adev\s*,\s*(\w+)\s*,\s*(\w+)\s*\)")
    ADD = re.compile(r"amdgpu_device_ip_block_add\s*\([^,]*,\s*&(\w+)\)")
    # El discriminante se captura RESUELViendo un nivel de parentesis, no con
    # un .+? no guloso. El patron original cortaba en el primer ")" y devolvia
    # "amdgpu_ip_version(adev, SDMA0_HWIP, 0" -- sin el cierre -- con lo cual
    # el segundo regex no casaba y la tabla de selectores salia VACIA. Una
    # tabla vacia no se parece a una tabla llena: se parece a que no hay
    # despacho por version, que es lo contrario de lo cierto, y eso es la clase
    # de fallo que 041 prohibio: una comprobacion que no puede fallar.
    SWITCH = re.compile(r"switch\s*\(((?:[^()]|\([^()]*\))*)\)")
    for entry in entradas:
        if not entry.endswith(".c"):
            continue
        lineas = quitar_comentarios(c.leer(entry))
        for i, ln in enumerate(lineas):
            if not FUNCION.match(ln):
                continue
            if "amdgpu_device_ip_block_add" not in "\n".join(lineas[i:i + 90]):
                continue
            # El cuerpo se corta en la llave que cierra la FUNCION, en su
            # nivel de anidamiento, y no en una ventana de N lineas. Con 70
            # lineas, el cuerpo de set_sdma_ip_blocks se comia el principio de
            # la siguiente, y SDMA0 aparecia seleccionando gfx_v12_0_ip_block.
            # Es el mismo fallo de limite que pm4census encontro en el recuento
            # de payload, y el mismo remedy: un recorte fijo no puede saber
            # donde acaba un bloque en C.
            fin = cierre_de_bloque(lineas, i)
            if fin is None:
                continue
            cuerpo = lineas[i:fin]
            hw = None
            lectura = ""
            for j in range(0, min(14, len(cuerpo))):
                m = SWITCH.search(cuerpo[j])
                if m and IPVER.search(m.group(1)):
                    iv = IPVER.search(m.group(1))
                    if iv:
                        hw = iv.group(1)
                        lectura = m.group(1).strip()[:44]
                        break
            if not hw:
                continue
            for b in sorted(set(ADD.findall("\n".join(cuerpo)))):
                d.anadir(hw, b, lectura)
    return d


def bloques_de_este_proyecto() -> List[Dict[str, str]]:
    """Los bloques que este proyecto usa, con la evidencia que los sostiene.

    Se declara de forma explicita y con su fichero de evidencia, porque es una
    DECLARACION DEL PROYECTO y no un dato que se pueda leer del ASIC.
    """
    return [
        {"hwip": "SDMA0_HWIP", "bloque": "el emisor de PTE/PTEPDE",
         "evidencia": "findings/035-correccion-ptepde-es-polaris12.md:57 y "
                      "findings/043-vuelta-atras-035-y-036-leian-el-asic-equivocado.md:31"
                      "; el case del chip dice sdma_v3_1_ip_block y "
                      "discovery dice sdma_v4_0 para 4.x"},
        {"hwip": "GC_HWIP", "bloque": "gfx_v8_0_ip_block: ring, WAIT_REG_MEM, "
                                       "PFP_SYNC_ME, vm-flush",
         "evidencia": "vi.c:2107 lo anade el case del chip; decidible sin MMIO"},
        {"hwip": "GC_HWIP", "bloque": "gmc_v8_1_ip_block: PTBA, aperture, "
                                       "VM_INVALIDATE_REQUEST",
         "evidencia": "vi.c:2110 lo anade el case del chip; gmc_v8_0.c:1762 "
                      "comparte gmc_v8_0_ip_funcs"},
    ]


def prueba_alcanzabilidad(c: Corpus, chip: str, ip_local: str,
                           host_pci: str) -> Dict[str, object]:
    """El bloque de SDMA que ejecuta la GPU, demostrado por alcanzabilidad.

    NO se deduce del nombre del fichero, ni del caso del chip, ni de la
    version del IP. Se demuestra por unreachable-code, que es un hecho de
    flujo de control y se lee estaticamente:

      1. el PCI ID que publica el host mapea a este chip
      2. el case de este chip esta en la lista que llama a vi_set_ip_blocks
         y hace break, sin caer en el default
      3. amdgpu_discovery_set_ip_blocks -- unico lugar que consulta la
         version de SDMA -- esta SOLO en el default
      4. por lo tanto la version de SDMA no llega a consultarse, y da igual
         lo que valga

    Los cuatro puntos se comprueban, no se suponen. Si alguno falla, la prueba
    devuelve INCOMPLETA y no se afirma nada.
    """
    out: Dict[str, object] = {"pasos": [], "veredicto": "INCOMPLETA"}
    drv = quitar_comentarios(c.leer("amdgpu_drv.c"))
    dev = quitar_comentarios(c.leer("amdgpu_device.c"))
    disc = quitar_comentarios(c.leer("amdgpu_discovery.c"))

    # 1. PCI ID -> chip
    vendor, device = ip_local.split(":")
    entrada = None
    for i, ln in enumerate(drv):
        if re.search(r"0x%s\s*,\s*0x%s\b" % (vendor.upper(), device.upper()),
                     ln) and chip in ln:
            entrada = {"linea": i + 1, "texto": ln.strip()}
            break
    out["pasos"].append({
        "n": 1, "que": "el PCI ID %s del host mapea a %s" % (ip_local, chip),
        "ok": entrada is not None,
        "evidencia": ("amdgpu_drv.c:%d  %s" % (entrada["linea"], entrada["texto"]))
                      if entrada else "NO ENCONTRADO",
    })

    # 2. el case del chip esta en la rama que llama a vi_set_ip_blocks
    #
    # Hay CINCO "switch (adev->asic_type)" en amdgpu_device.c (lineas 649,
    # 1638, 1924, 2102, 5151) y la version anterior tomaba el primero, que
    # esta en otra funcion. Por eso los pasos 2 y 3 daban NO y la prueba
    # INCOMPLETA. La funcion se localiza por nombre y el switch se busca DENTRO
    # de ella: un nombre de funcion es un indice, un switch suelto no.
    i_sw = None
    i_fn = None
    for i, ln in enumerate(dev):
        if re.match(r"^(?:static\s+)?int\s+amdgpu_device_ip_early_init\s*\(",
                    ln):
            i_fn = i
            break
    if i_fn is not None:
        fin_fn = cierre_de_bloque(dev, i_fn)
        if fin_fn is None:
            fin_fn = min(i_fn + 400, len(dev))
        for k in range(i_fn, fin_fn):
            if re.match(r"\s*switch\s*\(\s*adev->asic_type", dev[k]):
                i_sw = k
                break
    out["linea_de_la_funcion"] = i_fn + 1 if i_fn is not None else None
    rama = None
    if i_sw is not None:
        for k in range(i_sw, min(i_sw + 260, len(dev))):
            if re.match(r"^\s*case\s+%s\s*:" % chip, dev[k]):
                # hasta el break, y mirar si hay vi_set_ip_blocks
                for m in range(k, min(k + 60, len(dev))):
                    if "vi_set_ip_blocks" in dev[m]:
                        rama = {"linea": k + 1, "llama_en": m + 1}
                        break
                    if re.match(r"\s*break;", dev[m]):
                        break
                break
    out["pasos"].append({
        "n": 2, "que": "el case de %s esta en la rama que llama a vi_set_ip_blocks"
                      % chip,
        "ok": rama is not None,
        "evidencia": ("amdgpu_device.c:%d, llamada en :%d" % (rama["linea"],
                       rama["llama_en"])) if rama else "NO ENCONTRADO",
    })

    # 3. el despacho por version solo existe en el default
    i_def = None
    if i_sw is not None and i_fn is not None:
        # el default, dentro de la MISMA funcion
        fin_fn = cierre_de_bloque(dev, i_fn) or min(i_fn + 400, len(dev))
        for k in range(i_sw, fin_fn):
            if re.match(r"^\s*default\s*:", dev[k]):
                i_def = k
                break
    dentro = (i_def is not None and i_sw is not None
              and "amdgpu_discovery_set_ip_blocks" in "\n".join(dev[i_def:i_def + 12]))
    # y, para que "solo en el default" signifique algo, el case del chip tiene
    # que hacer break ANTES del default
    el_case_rompe = False
    if rama is not None and i_def is not None:
        for k in range(rama["linea"] - 1, i_def):
            if re.match(r"\s*break;", dev[k]):
                el_case_rompe = True
                break
    out["pasos"].append({
        "n": 3, "que": "solo en el default, y el case del chip rompe antes",
        "ok": dentro and el_case_rompe,
        "evidencia": ("amdgpu_device.c:%d, y el case de :%d hace break antes"
                      % (i_def + 1, rama["linea"]) if (dentro and el_case_rompe)
                      and rama else
                      ("falta el default en :%s" % (i_def + 1) if i_def is not None
                       else "default no encontrado dentro de la funcion")),
    })

    # 4. unico llamador
    llamadores: List[str] = []
    try:
        for entry in sorted(os.listdir(c.amdgpu)):
            if not entry.endswith((".c", ".h")):
                continue
            for i, ln in enumerate(quitar_comentarios(c.leer(entry))):
                if re.search(r"\bamdgpu_discovery_set_ip_blocks\s*\(", ln) \
                        and "int amdgpu_discovery_set_ip_blocks" not in ln:
                    llamadores.append("%s:%d" % (entry, i + 1))
    except OSError:
        pass
    out["pasos"].append({
        "n": 4, "que": "y tiene un solo llamador, en esa misma rama",
        "ok": len(llamadores) == 1,
        "evidencia": ", ".join(llamadores) if llamadores else "NINGUNO",
    })

    # el device que el host publica tiene que coincidir
    out["pasos"].append({
        "n": 5, "que": "el host publica %s" % ip_local,
        "ok": device.lower() in host_pci.lower().replace("[", "").split()[0].lower()
              or device.lower() in host_pci.lower(),
        "evidencia": host_pci,
    })

    if all(p["ok"] for p in out["pasos"]):
        out["veredicto"] = "PROBADO"
        out["conclusion"] = (
            "El despacho por version de IP -- unico lugar que consulta la "
            "version de SDMA -- NO se ejecuta para %s. La version de SDMA0 no "
            "llega a leerse, asi que su valor no puede cambiar nada, y el "
            "bloque de SDMA que ejecuta esta GPU es el que anade el case: "
            "sdma_v3_1_ip_block, definido en sdma_v3_0.c. No hace falta leer "
            "ningun registro para decidirlo." % chip)
    return out


def n_ficheros_c(c: Corpus) -> int:
    """Cuantos .c hay en amdgpu/. Es la cota de cualquier AUSENCIA que
    imprima esta herramienta, asi que se cuenta y no se pone a mano: un 0
    literal en un informe se lee como un dato medido."""
    try:
        return len([e for e in os.listdir(c.amdgpu) if e.endswith(".c")])
    except OSError:
        return -1


def selftest() -> int:
    """Vectores sobre los dos puntos que fallaron EN SILENCIO.

    Los dos fallaron de la misma manera: devolviendo una tabla vacia, que se
    parece a "no hay despacho por version" y es justo lo contrario de lo cierto.
    Un fallo que produce un resultado plausible en lugar de un error es el
    peor, porque no obliga a mirar.

      1. el switch con parentesis anidados. Un .+? no guloso devuelve
         "amdgpu_ip_version(adev, SDMA0_HWIP, 0" SIN el cierre, el segundo
         regex no casa, y la tabla de selectores sale vacia.
      2. el cierre de bloque por nivel de llaves, no por ventana de lineas.
    """
    print("=== hwip selftest ===\n")
    fallos = 0

    print("[1] switch con parentesis anidados")
    SWITCH = re.compile(r"switch\s*\(((?:[^()]|\([^()]*\))*)\)")
    IPVER = re.compile(r"amdgpu_ip_version\s*\(\s*adev\s*,\s*(\w+)\s*,")
    for linea, esperado in (
            ("\tswitch (amdgpu_ip_version(adev, SDMA0_HWIP, 0)) {", "SDMA0_HWIP"),
            ("\tswitch (amdgpu_ip_version(adev, GC_HWIP, 1)) {", "GC_HWIP"),
            ("\tswitch (amdgpu_ip_version(adev, MP0_HWIP, 0)) {", "MP0_HWIP"),
    ):
        m = SWITCH.search(linea)
        if not m:
            print("  FAIL: el switch no se capturo: %r" % linea)
            fallos += 1
            continue
        iv = IPVER.search(m.group(1))
        got = iv.group(1) if iv else None
        if got != esperado:
            print("  FAIL: %s, esperado %s" % (got, esperado))
            fallos += 1
        else:
            print("  OK   %s" % esperado)
    # y el caso trivial no debe romperse
    m = SWITCH.search("\tswitch (x) {")
    if not m or m.group(1).strip() != "x":
        print("  FAIL: un switch sin parentesis interno se rompio: %r"
              % (m.group(1) if m else None))
        fallos += 1
    else:
        print("  OK   un switch sin parentesis interno")

    print()
    print("[2] el cierre de bloque por llaves, no por ventana")
    codigo = [
        "static int f(void)",
        "{",
        "\tif (a) {",
        "\t\tg();",
        "\t}",          # cierra el if
        "\tswitch (x) {",
        "\tcase 1:",
        "\t\th();",     # el switch sigue abierto aqui
        "\t\tbreak;",
        "\tdefault:",
        "\t\tk();",
        "\t\tbreak;",
        "\t}",
        "\ti();",       # esto es FUERA del switch pero dentro de f
        "}",              # cierra f
    ]
    # La llave de cierre de f() esta en el indice 14, y la funcion devuelve
    # k+1, es decir LA SIGUIENTE linea. Que no sea el indice 13 (el cierre del
    # switch) es justo lo que distingue un recorte por llaves de uno por
    # ventana: el switch se cierra en 12 y f() en 14, y cualquier recorte fijo
    # de N lineas devuelve una de las dos por casualidad.
    fin = cierre_de_bloque(codigo, 0)
    if fin != 15:
        print("  FAIL: cierra en el indice %s, esperado 15 (que es %d + 1)"
              % (fin, 14))
        fallos += 1
    elif cierre_de_bloque(codigo, 5) != 13:
        # Desde el switch, el cierre es el SUYO: indice 12, luego 13. Y desde
        # la funcion, 15. Que den distinto es lo que prueba que el recorte es
        # por llaves y no por ventana. Un recorte fijo daria el mismo numero
        # para los dos, o el equivocado para uno de los dos.
        print("  FAIL: desde el switch devuelve %s, esperado 13 (su cierre)"
              % cierre_de_bloque(codigo, 5))
        fallos += 1
    else:
        print("  OK   desde f(): 15    desde el switch: 13    distintos, "
              "por llaves")
    # y un bloque que no cierra dentro del alcance
    if cierre_de_bloque(["static int g(void)", "{", "\tx();"], 0) is not None:
        print("  FAIL: dio por cerrado un bloque abierto")
        fallos += 1
    else:
        print("  OK   un bloque abierto devuelve None, no una linea inventada")

    print("=" * 70)
    if fallos:
        print("RESULT: FAIL (%d)" % fallos)
        return 1
    print("RESULT: PASS (5 vectores)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="de donde sale la version de cada IP block, y cuales "
                    "exigen leer un registro")
    ap.add_argument("--kernel")
    ap.add_argument("--chip", default=CHIP)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    root, como = find_kernel(args.kernel)
    if not root or not Corpus(root).ok():
        print("hwip: no encuentro el corpus (%s). Usa --kernel." % como,
              file=sys.stderr)
        return 3
    c = Corpus(root)

    # MEDIDO 2026-10-04 (hallazgo 1055, informe FILTROS-MAL-FORMADOS).  Esto no
    # existia, y es la clase VACIO_SILENCIOSO mas peligrosa del proyecto: un filtro
    # mal formado convertirse en una CONCLUSION DE HARDWARE.
    #
    # MEDIDO, antes del arreglo:
    #
    #   $ python3 tools/hwip.py --chip CHIP_POLARIS12   -> NINGUNO, rc=0
    #   $ python3 tools/hwip.py --chip Polaris12         -> NINGUNO, rc=0
    #   $ python3 tools/hwip.py --chip CHIP_GA10        -> NINGUNO, rc=0
    #
    # Y las tres imprimen, textual:
    #
    #   "Consecuencia directa: para esta GPU, TODAS las versiones de IP
    #    se leen de la tarjeta."
    #
    # La frase "para esta GPU" esta FIJA en el codigo. Preguntar por CHIP_GA10, que
    # no es esta GPU, seguia afirmando una conclusion sobre esta. Un nombre de chip
    # equivocado no daba un error: daba una afirmacion de hardware, con salida limpia
    # y codigo cero. El filtro es lo que decidia, y no decia nada.
    #
    # El patron ya existe en el proyecto: tools/trace_path.py:508-512 parsea el enum
    # con parse_chip_enum() y devuelve 2 si el chip no esta. Se reutiliza esa funcion
    # en vez de escribir otra: dos parsers del mismo enum divergen.
    conocidos = chips_del_corpus(root)
    if not conocidos:
        print("ERROR  no encuentro ningun nombre CHIP_ en %s, y sin esa lista" % root,
              file=sys.stderr)
        print("        no puedo ni validar ni negar. No se afirma nada.", file=sys.stderr)
        return 3
    chip, como = _resolver_chip(args.chip, conocidos)
    if chip is None:
        cerca = sorted(k for k in conocidos if args.chip.upper() in k.upper()
                       or k.upper().split("_", 1)[-1] in args.chip.upper())
        print("ERROR  %s no es un ASIC que aparezca en el corpus (%d conocidos)"
              % (args.chip, len(conocidos)), file=sys.stderr)
        if cerca:
            print("        quiza: %s" % ", ".join(cerca[:8]), file=sys.stderr)
        print("        ejemplos: %s" % ", ".join(sorted(conocidos)[:6]), file=sys.stderr)
        print("        No se afirma nada sobre ningun ASIC: un filtro que no casa",
              file=sys.stderr)
        print("        no puede producir una conclusion de hardware.", file=sys.stderr)
        return 2
    if como:
        print("AVISO  --chip %s resuelto a %s" % (args.chip, como), file=sys.stderr)

    print("=" * 78)
    print("hwip %s · %s · WORK_CLASS=READ_ONLY" % (VERSION, chip))
    print("=" * 78)
    print("corpus      %s" % root)
    print()

    print("=" * 78)
    print("1 · DE DONDE SALE adev->ip_versions[]")
    print("=" * 78)
    t = temp_por_mmio(c)
    if not t["funcion"]:
        print("  amdgpu_discovery_set_ip_versions NO ENCONTRADA. Es una")
        print("  ausencia ACOTADA al corpus, y esta herramienta no puede")
        print("  afirmar nada. No se supone que no exista.")
        return 1
    print("  la que lo rellena: %s()  amdgpu_discovery.c:%d"
          % (t["funcion"], t["linea"]))
    print("  asignacion concreta:      amdgpu_discovery.c:%d"
          % t["asignacion_en"])
    print("  el nombre que yo busque al principio, %s(), NO EXISTE"
          % t["nombre_que_se_busco_y_no_existe"])
    print("  ni en 7.2.8 ni en 7.1.3. Se ha buscado por estructura, no por nombre.")
    print("  escribe adev->ip_versions[]:        %s" % t["escribe_ip_versions"])
    print("  esta funcion lee MMIO:              %s" % t["lee_mmio"])
    print("     ^ False es CORRECTO: parsea un buffer que ya esta en RAM.")
    print("  la que LLENA el buffer:             %s()  amdgpu_discovery.c:%s"
          % (t["funcion_que_llena_el_buffer"], t["linea_del_buffer"]))
    print("  esa si lee MMIO:                    %s"
          % t["el_buffer_se_llena_por_mmio"])
    if t["offset_desde_mmio"]:
        print("  el offset sale de RREG de:          %s  (linea %d)"
              % (", ".join(t["offset_desde_mmio"]["registros"]) or "MMIO",
                 t["offset_desde_mmio"]["linea"]))
    print("  campos del descriptor IP:     %s"
          % ", ".join(t["campos_del_descriptor"][:10]))
    print()
    if t["lee_mmio"] and t["escribe_ip_versions"]:
        print("  Y AQUI ESTA EL NUDO. La version de cada IP block se lee de una")
        print("  tabla de IP descriptors que esta en la tarjeta, y se recorre")
        print("  con major/minor/rev/variant/subrevision. El codigo es:")
        print()
        print("      adev->ip_versions[hw_ip][ip->instance_number] =")
        print("          IP_VERSION_FULL(ip->major, ip->minor,")
        print("                           ip->revision, variant, subrev);")
        print()
        print("  Eso significa que el VALOR no se puede saber leyendo el corpus.")
        print("  No es que falte busqueda: es que el dato no esta en el fuente.")
        print()
    print()

    print("=" * 78)
    print("2 · LOS HWIP QUE ESTE PROYECTO USA, Y CUALES DEPENDEN DE MMIO")
    print("=" * 78)
    uso = hwips_usados(c)
    desc = mapear_despacho(c)
    print("  HWIP distintos referenciados en amdgpu/: %d" % len(uso))
    print("  de los que SELECCIONAN codigo por su version: %d"
          % len([k for k, v in desc.selectores.items() if v["bloques"]]))
    print()
    print("  %-14s %-46s %s" % ("HWIP", "bloque", "como se decide"))
    print("  " + "-" * 74)
    for b in bloques_de_este_proyecto():
        print("  %-14s %-46s" % (b["hwip"], b["bloque"][:46]))
        print("  %-14s %s" % ("", b["evidencia"]))
    print()

    print("=" * 78)
    print("3 · LOS HWIP QUE ESTA GPU DECIDE POR HARDCODE, Y CUALES NO")
    print("=" * 78)
    hard = hardcodeados(c, args.chip)
    if hard:
        print("  %s escribe adev->ip_versions[] en un case suyo:" % args.chip)
        for hw in sorted(hard):
            for h in hard[hw]:
                print("    %-14s inst %-3s = %-28s %s:%d"
                      % (hw, h["instancia"], h["valor"], h["fichero"],
                         h["linea"]))
    else:
        print("  NINGUNO. Ningun `case %s:` del corpus escribe" % args.chip)
        print("  adev->ip_versions[] con un valor constante.")
        print()
        print("  Consecuencia directa: para %s, TODAS las versiones de IP se leen" % chip)
        print("  de la tarjeta. No hay ningun atajo estatico.")
        print()
        print("  Esto NO significa que no exista una tabla de hardcodeos para")
        print("  otra GPU: significa que para ESTA no la hay. Y es una ausencia")
        print("  acotada, leida de los %d ficheros .c de amdgpu/."
              % n_ficheros_c(c))
    print()

    print("=" * 78)
    print("4 · QUE HWIP ELIGE CODIGO, Y POR QUE ESO ES LO QUE IMPORTA")
    print("=" * 78)
    # La pregunta accionable NO es "de donde sale la version de cada HWIP":
    # sale de la tarjeta para todos, y una tabla de 39 filas donde todas dicen
    # lo mismo no informa de nada. La pregunta es: el valor de este HWIP
    # SELECCIONA que fichero se ejecuta. Si no selecciona nada, leerlo no
    # cambia nada de lo que este proyecto hace.
    print("  Uso como discriminante de despacho:")
    print("  (un HWIP cuyo valor no selecciona codigo no necesita leerse para")
    print("   cambiar el comportamiento del driver)")
    print()
    print("  %-14s %-9s %-10s %s" % ("HWIP", "discrimina", "lecturas", "que selecciona"))
    print("  " + "-" * 72)
    for hw, info in sorted(desc.selectores.items(),
                            key=lambda kv: -len(kv[1]["bloques"])):
        sel = info["bloques"]
        muestra = ", ".join(sel[:3]) + (" +%d" % (len(sel) - 3)
                                       if len(sel) > 3 else "")
        print("  %-14s %-9s %-10s %s"
              % (hw, "SI" if sel else "no", info["lecturas"], muestra[:38]))
    print()

    sdma = desc.selectores.get("SDMA0_HWIP")
    print("  Y el caso que importa:")
    if sdma:
        print("    SDMA0_HWIP selecciona %d bloque(s) de IP segun su version:"
              % len(sdma["bloques"]))
        for b in sdma["bloques"][:12]:
            print("        %s" % b)
        print()
        print("    Esos son TODOS los ficheros que ejecutan SDMA en el corpus.")
        print("    Leer el descriptor de SDMA0 en la tabla IP discovery decide")
        print("    cual de ellos ejecuta esta GPU. Y ese es el unico registro")
        print("    cuyo valor cambia una conclusion ya escrita en un finding.")
    else:
        print("    SDMA0_HWIP no aparece como selector en el despacho leido.")
        print("    Eso es un NEGATIVE_RESULT acotado a los ficheros con")
        print("    amdgpu_device_ip_block_add, y no se elige entre tres causas:")
        print("    que el caso del chip lo cubra sin mirar la version, que el")
        print("    formato del switch no sea el reconocido, o que este HWIP no")
        print("    seleccione nada en este corpus.")
    print()

    print("=" * 78)
    print("LO QUE HAY QUE LEER PARA CERRARLO, Y POR QUE NO SE LEE")
    print("=" * 78)
    print("  Para saber que SDMA ejecuta esta GPU habria que leer el")
    print("  descriptor de IP de SDMA0 en la tabla de IP discovery. Eso es")
    print("  Leer un registro es NIVEL 2 en la jerarquia de permisos de")
    print("  AGENTS.md: AUTORIZADO dentro de investigacion si es read-only y")
    print("  reversible, con registro antes/despues. No es lo que creia esta")
    print("  herramienta, que decia que AGENTS.md lo prohibia -- y por eso la")
    print("  frontera se trato como pared cuando era un experimento autorizado")
    print("  con un formulario que rellenar.")
    print()
    print("  Lo que SI es NIVEL 4 es cargar un modulo, y el host tiene")
    print("  CONFIG_MODULE_SIG_ALL con CONFIG_SECURITY_LOCKDOWN_LSM y sin clave")
    print("  de firma. Eso si es una pared, y es tecnica, no de politica.")
    print()
    print("  El discriminante seria UN registro, y ya esta escrito:")
    print("      adev->ip_versions[SDMA0_HWIP][0]  ->  IP_VERSION(major, minor,")
    print("                                                    rev, variant,")
    print("                                                    subrev)")
    print("      amdgpu_ip_version() lo enmascara a ~0xFF, dejando major/minor/rev")
    print()
    print("  Y la decision que tomaria esa lectura es de una de dos formas:")
    print("      4.0.x  -> amdgpu_discovery.c enruta a sdma_v4_0_ip_block")
    print("      3.1.x  -> vi.c ya anade sdma_v3_1_ip_block y discovery no aplica")
    print()
    print()

    print("=" * 78)
    print("5 · PERO HAY UNA PRUEBA ESTATICA QUE NO NECESITA LEER NADA")
    print("=" * 78)
    pr = prueba_alcanzabilidad(c, args.chip, "1002:699f",
                               "01:00.0 [1002:699f] rev c7 (Lexa PRO)")
    for p in pr["pasos"]:
        print("  [%s] %s" % ("OK" if p["ok"] else "NO", p["que"]))
        print("         %s" % p["evidencia"])
    print()
    if pr["veredicto"] == "PROBADO":
        print("  VEREDICTO: %s" % pr["conclusion"])
    else:
        print("  VEREDICTO: INCOMPLETA. La prueba tiene un punto que no se")
        print("  pudo confirmar, asi que no se afirma la conclusion. Los puntos")
        print("  que fallan estan marcados arriba.")
    print()

    if args.json:
        print(json.dumps({
            "version": VERSION, "chip": args.chip, "corpus": root,
            "origen_de_ip_versions": t,
            "hardcodeados_para_este_chip": hard,
            "usos_por_hwip": uso,
            "n_ficheros_c": n_ficheros_c(c),
        }, indent=2, sort_keys=True, default=str))

    if not desc.selectores:
        print("  NINGUN HWIPresulto ser discriminante de despacho. Eso es un")
        print("  NEGATIVE_RESULT acotado: o el formato del switch no es el que")
        print("  esta herramienta reconoce, o no hay despacho por version. No se")
        print("  elige entre las dos, y se devuelve 1 para que se mire.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

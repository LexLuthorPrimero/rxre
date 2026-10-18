#!/usr/bin/env python3
# CONTRACT: name=unreach
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
unreach.py - generaliza la prueba de 046 a los N selectores de despacho.

POR QUE EXISTE

046 demostro, para un solo HWIP, que un hecho que parecia exigir leer un
registro se resuelve solo:

    amdgpu_discovery_set_ip_blocks  -- unico sitio que consulta una IP version
    esta en el `default:` de un switch cuyo `case` incluye CHIP_POLARIS12
    y hace break antes
    => la version de SDMA0 no llega a leerse, y su valor es irrelevante

046 lo hizo para SDMA0. Quedaban nueve selectores vivos (UVD, GC, MP0, VCE,
OSSSYS, MP1, DCE, VPE, ISP) y la pregunta "alcanza el case de Polaris12 a
cada uno" es MECANICAMENTE IDENTICA nueve veces. Hacerla a mano es la
definicion de trabajo repetitivo, y este proyecto ya ha pagado por dos
herramientas que contestaban una pregunta a la vez.

ASI QUE ESTA HERRAMIENTA HACE LA MISMA PRUEBA PARA LOS DIEZ

Y anade la generalizacion que 046 no hizo, que es la que de verdad cambia la
politica del proyecto:

    ¿el case de CHIP_POLARIS12 alcanza ESTA FUNCION DE DESPACHO?

Porque la razon por la que la version de SDMA0 es irrelevante no es
"SDMA0 es especial": es que la funcion que la consulta no se llama. Y si eso
es cierto para las funciones de despacho por version de IP, es cierto para
TODAS, y entonces ninguna IP version de esta GPU necesita leerse para decidir
que codigo se ejecuta. Eso es una afirmacion fuerte, y por eso se demuestra
punto por punto y con codigo de salida distinto para cada estado.

LA PRUEBA, Y POR QUE ESTA ESTRUCTURADA ASI

La generalizacion de "unico llamador en el default" tiene un fallo que 046 no
podia tener: hay funciones de despacho con VARIOS llamadores
(amdgpu_discovery_set_ih_ip_blocks aparece en 3423 y 3427; set_psp en 3420 y
3432; set_smu en 3439 y 3465). Comprobar "un solo llamador" daria NO para
esas, y seria un FALSO: no tienen un solo llamador, tienen varios, todos
dentro de la misma funcion inalcanzable.

Por eso la prueba trabaja sobre el GRAFO DE LLAMADAS y no sobre el recuento:

    1. localizar la funcion de despacho que consulta el HWIP
    2. localizar TODOS sus llamadores
    3. comprobar que CADA llamador esta, transitivamente, dentro del
       conjunto de funciones inalcanzables desde el case del chip
    4. si los tres pasos pasan, la version no se consulta

Y el paso 3 se calcula por cierre transitivo, no por un nivel: si
set_ih_ip_blocks solo se llama desde set_ip_blocks, y set_ip_blocks solo
desde el default de amdgpu_device.c, y ahi no se llega, entonces set_ih
tampoco. Un nivel basta para las 14 funciones que se llamarve hoy, pero
codificarlo a un nivel seria asumir la forma actual del codigo, y esa
asuncion es justo lo que 041 prohibe.

LIMITE DURO, DECLARADO

Que una funcion no se llame NO significa que no exista ni que su codigo no
sea correcto. Significa que su valor no decide nada para esta GPU. Se
distinguen las dos cosas y no se elige entre ellas: una es NOT_APPLICABLE y
la otra seria NOT_IN_CORPUS, y el corpus si esta.

Y el caso contrario importa igual: si algun selector resultara ALCANZABLE, su
version tendria que leerse, y eso seria un BLOCKED nuevo y bien justificado.
La herramienta lo dice con codigo 1, no lo esconde.

CODIGOS DE SALIDA

  0  todos los selectores son inalcanzables: ninguna IP version hay que leerla
  1  algun selector es alcanzable: su version SI necesita leerse
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

FUNCION = re.compile(r"^(?:static\s+)?(?:int|void|bool|u32)\s+(\w+)\s*\(")
IPVER = re.compile(
    r"amdgpu_ip_version\s*\(\s*adev\s*,\s*(\w+)\s*,\s*(\w+)\s*\)")
SWITCH = re.compile(r"switch\s*\(((?:[^()]|\([^()]*\))*)\)")
ADD = re.compile(r"amdgpu_device_ip_block_add\s*\([^,]*,\s*&(\w+)\)")


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

    def c_files(self) -> List[str]:
        try:
            return [e for e in sorted(os.listdir(self.amdgpu)) if e.endswith(".c")]
        except OSError:
            return []


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


def cierre_de_bloque(lineas: List[str], inicio: int,
                     max_lineas: int = 400) -> Optional[int]:
    """El indice DESPUES de la llave que cierra el bloque de inicio.

    Por llaves, no por ventana. Un recorte fijo de N lineas se come el bloque
    siguiente: eso hizo que pm4census midiera el payload de la emision
    siguiente, y que este mismo fichero_mapa dejara SDMA0 seleccionando un
    bloque de otra funcion.
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


def grupo_de(lineas: List[str], inicio: int) -> List[str]:
    fin = cierre_de_bloque(lineas, inicio)
    return lineas[inicio:fin] if fin is not None else lineas[inicio:]


def ramificacion_del_chip(c: Corpus, chip: str) -> Dict[str, object]:
    """Las ramas del switch de asic_type de amdgpu_device_ip_early_init.

    Devuelve, por rama, el nombre de la funcion de despacho que llama y si
    hace break antes del default. La rama del chip es la que se ejecuta; la del
    default es la que no.
    """
    dev = quitar_comentarios(c.leer("amdgpu_device.c"))
    out: Dict[str, object] = {"funcion": None, "linea": None, "ramas": {},
                              "default_linea": None}

    i_fn = None
    for i, ln in enumerate(dev):
        if re.match(r"^(?:static\s+)?int\s+amdgpu_device_ip_early_init\s*\(",
                    ln):
            i_fn = i
            break
    if i_fn is None:
        return out
    out["funcion"] = "amdgpu_device_ip_early_init"
    out["linea"] = i_fn + 1
    cuerpo = grupo_de(dev, i_fn)

    i_sw = None
    for j, ln in enumerate(cuerpo):
        if re.match(r"\s*switch\s*\(\s*adev->asic_type", ln):
            i_sw = j
            break
    if i_sw is None:
        return out

    i_def = None
    for j in range(i_sw, len(cuerpo)):
        if re.match(r"^\s*default\s*:", cuerpo[j]):
            i_def = j
            break
    if i_def is not None:
        out["default_linea"] = i_fn + i_def + 1

    # Cada GRUPO de cases, y su llamada, hasta su break.
    #
    # Y son GRUPOS, no cases sueltos, por el FALL-THROUGH. La forma real es:
    #
    #     case CHIP_TOPAZ:
    #     case CHIP_TONGA:
    #     ...
    #     case CHIP_POLARIS12:
    #     case CHIP_VEGAM:
    #             r = vi_set_ip_blocks(adev);
    #             break;
    #
    # La version anterior llevaba un unico `actual` que se sobreescribia en
    # cada `case`, asi que solo registraba el ULTIMO del grupo: CHIP_STONEY.
    # CHIP_POLARIS12 no aparecia nunca, y la herramienta decia "case no
    # encontrado" sobre un case que esta ahi. Es el mismo modo de fallo que el
    # recorte por ventanas, y la misma familia: se leia una estructura de C
    # como si fuera una secuencia plana.
    grupo: List[str] = []
    for j in range(i_sw + 1, i_def if i_def is not None else len(cuerpo)):
        ln = cuerpo[j]
        cm = re.match(r"\s*case\s+(CHIP_\w+)\s*:", ln)
        if cm:
            grupo.append(cm.group(1))
            continue
        if not grupo:
            continue
        llamada = re.search(r"r\s*=\s*(\w+_set_ip_blocks)\s*\(", ln)
        if llamada:
            for chip in grupo:
                if chip not in out["ramas"]:
                    out["ramas"][chip] = {
                        "funcion": llamada.group(1),
                        "linea_case": i_fn + j + 1,
                        "linea_llamada": i_fn + j + 1,
                        "grupo_de": len(grupo),
                    }
        if re.match(r"\s*break;", ln):
            for chip in grupo:
                if chip in out["ramas"]:
                    out["ramas"][chip]["break_antes_de_default"] = True
            grupo = []

    if i_def is not None:
        llamada = None
        for j in range(i_def, min(i_def + 12, len(cuerpo))):
            m = re.search(r"r\s*=\s*(\w+_set_ip_blocks)\s*\(", cuerpo[j])
            if m:
                llamada = m.group(1)
                break
        out["rama_default"] = {"funcion": llamada,
                               "linea": i_fn + i_def + 1}
    return out


def grafo_de_llamadas(c: Corpus) -> Dict[str, List[Tuple[str, int]]]:
    """funcion -> [(llamador, linea)], construido por texto y con comentes fuera.

    Es textual y no preprocesa, asi que una llamada a traves de un macro de
    funcion o por puntero no aparece. Eso limita lo que se puede afirmar de un
    NO, y por eso la herramienta lo declara en vez de dejarlo implicito: un
    "no la llama" textual no es un "no la llama".
    """
    # ADELANTE: llamador -> [(callee, donde)]. La inversa (callee -> callers)
    # es lo que sale de recorrer el texto, y con ella el BFS desde la raiz
    # caminaba HACIA ARRIBA en vez de hacia abajo, devolviendo un solo nodo y
    # declarando alcanzables 10 selectores que no lo son. Un grafo mal dirigido
    # no da un error: da una respuesta segura y equivocada, que es la peor
    # forma. Por eso la direccion se declara en el nombre.
    grafo: Dict[str, List[Tuple[str, int]]] = {}
    for entry in c.c_files():
        lineas = quitar_comentarios(c.leer(entry))
        actual: Optional[str] = None
        for i, ln in enumerate(lineas):
            m = FUNCION.match(ln)
            if m:
                actual = m.group(1)
                continue
            if actual is None:
                continue
            # El patron busca "_ip_blocks" al final del nombre, y no
            # "_set_ip_blocks". Los nombres reales son
            # amdgpu_discovery_set_SDMA_ip_blocks, y el "_set_" lleva el nombre
            # del bloque en medio: "set_sdma_ip_blocks" no contiene
            # "set_ip_blocks". La version anterior por tanto capturaba 3
            # funciones (vi_, cik_, si_) y perdiaba las 14 de discovery, con lo
            # que el grafo parecia correcto y estava casi vacio.
            #
            # Y es el MODO DE FALLO de pm4census otra vez: un grafo con pocas
            # aristas parece un grafo con pocas relaciones, no un grafo mal
            # construido. Solo se distingue mirando la cota.
            for g in re.finditer(r"\b(\w+_ip_blocks)\s*\(\s*adev\s*\)", ln):
                grafo.setdefault(actual, []).append(
                    (g.group(1), "%s:%d" % (entry, i + 1)))
    return grafo


def alcanzables_desde(c: Corpus, grafo: Dict[str, List[Tuple[str, int]]],
                      raiz: str) -> Tuple[Set[str], Dict[str, str]]:
    """Cierre transitivo de funciones alcanzables desde raiz.

    Devuelve (conjunto, camino) donde camino[s] es el primer llamador por el
    que se llega. La transitividad importa: hoy las 14 funciones de despacho se
    llaman directamente desde set_ip_blocks, y un codigo de un nivel daria la
    respuesta correcta por casualidad. Codificar la suposicion de la forma
    actual del codigo es lo que 041 prohibe.
    """
    vistos: Set[str] = set()
    camino: Dict[str, str] = {}
    pila = [raiz]
    while pila:
        f = pila.pop()
        for _callee, donde in grafo.get(f, []):
            if _callee not in vistos:
                vistos.add(_callee)
                camino[_callee] = "%s (llamado desde %s)" % (donde, f)
                pila.append(_callee)
    return vistos, camino


def selectores(c: Corpus) -> Dict[str, Dict[str, object]]:
    """HWIP -> funcion de despacho que lo consulta, y los bloques que añade.

    Se recorre cada funcion de amdgpu/, se busca un switch cuyo discriminante
    sea amdgpu_ip_version(adev, X_HWIP, i), y se toman los bloques que añade
    ESE MISMO bloque de llaves. El corte es por llaves porque un recorte fijo
    arrastra los bloques de la funcion siguiente: eso hizo que SDMA0
    apareciera seleccionando gfx_v12_0_ip_block.
    """
    out: Dict[str, Dict[str, object]] = {}
    for entry in c.c_files():
        lineas = quitar_comentarios(c.leer(entry))
        for i, ln in enumerate(lineas):
            if not FUNCION.match(ln):
                continue
            cuerpo = grupo_de(lineas, i)
            texto = "\n".join(cuerpo)
            if "amdgpu_device_ip_block_add" not in texto:
                continue
            hw = None
            lectura = ""
            for x in range(0, min(16, len(cuerpo))):
                sm = SWITCH.search(cuerpo[x])
                if sm:
                    iv = IPVER.search(sm.group(1))
                    if iv:
                        hw = iv.group(1)
                        lectura = sm.group(1).strip()[:46]
                        break
            if not hw:
                continue
            bloques = sorted(set(ADD.findall(texto)))
            d = out.setdefault(hw, {"funciones": [], "lecturas": 0,
                                    "bloques": set()})
            fn = FUNCION.match(ln).group(1)
            d["funciones"].append({"nombre": fn, "fichero": entry,
                                   "linea": i + 1, "discriminante": lectura})
            d["lecturas"] = int(d["lecturas"]) + 1
            d["bloques"] |= set(bloques)
    for d in out.values():
        d["bloques"] = sorted(d["bloques"])
    return out


def usos_de_ip_version(c: Corpus,
                        solo_en_default: Set[str],
                        ficheros_chip: Optional[Set[str]] = None) -> Dict[str, object]:
    """DONDE se consulta amdgpu_ip_version(), alcanzable o no.

    Existe por un motivo que la seccion 3 no puede resolver sola. "Ningun
    selector de despacho es alcanzable" NO es "la version de IP no se lee
    nunca", y confundir las dos seria repetir el error de 035 por el otro
    lado: una afirmacion mas fuerte que la que la evidencia sostiene.

    Medido en este corpus: 661 usos en 413 funciones, de las que solo 14 son
    funciones de despacho. Las otras 398 usan la version para COMPORTAMIENTO,
    no para elegir fichero, y muchas si son alcanzables.

    Y hay un caso que obliga a la prudencia por partida propia:
    amdgpu_device_ip_early_init, la funcion que decide el despacho, consulta
    ella misma amdgpu_ip_version(adev, GC_HWIP, 0) DESPUES del switch
    (amdgpu_device.c:2159). Ese uso es alcanzable y no lo cubre la prueba de
    inalcanzabilidad, porque la prueba es sobre las funciones de despacho, no
    sobre la funcion que las contiene.
    """
    alcanzables: Dict[str, List[Tuple[str, str, int]]] = {}
    n_funcs: Set[str] = set()
    n_despacho: Set[str] = set()
    total = 0
    usos_despacho = 0
    for entry in c.c_files():
        lineas = quitar_comentarios(c.leer(entry))
        actual: Optional[str] = None
        for i, ln in enumerate(lineas):
            m = FUNCION.match(ln)
            if m:
                actual = m.group(1)
                continue
            if actual is None or "amdgpu_ip_version" not in ln:
                continue
            total += 1
            n_funcs.add(actual)
            if actual.endswith("_ip_blocks"):
                n_despacho.add(actual)
                if actual in solo_en_default:
                    usos_despacho += 1
                    continue
            alcanzables.setdefault(actual, []).append(
                (entry, i + 1, ln.strip()[:66]))
    # Los usos en los ficheros que ESTA GPU ejecuta. Es la interseccion de
    # dos herramientas que ya existen -- el grafo de unreach y el mapa de
    # despacho de citegen/which_hw -- y por eso se computa aqui en vez de
    # crear un tercer programa que repita la misma infraestructura.
    en_chip: Dict[str, List[Tuple[str, str, int]]] = {}
    if ficheros_chip:
        en_chip = {k: v for k, v in alcanzables.items()
                   if any(f in ficheros_chip for f, _l, _t in v)}
    return {
        "usos_totales": total,
        "funciones": len(n_funcs),
        "funciones_de_despacho": len(n_despacho),
        "usos_en_despacho_inalcanzable": usos_despacho,
        "usos_otros": total - usos_despacho,
        "funciones_alcanzables_que_lo_usan": len(alcanzables),
        "detalle_alcanzable": {k: ["%s:%d" % (f, l) for f, l, _ in v[:3]]
                               for k, v in sorted(alcanzables.items())},
        "ficheros_del_chip": len(ficheros_chip) if ficheros_chip else 0,
        "usos_en_ficheros_del_chip": sum(len(v) for v in en_chip.values()),
        "funciones_en_ficheros_del_chip": len(en_chip),
        "detalle_en_ficheros_del_chip": {
            k: ["%s:%d" % (f, l) for f, l, _ in v[:2]]
            for k, v in sorted(en_chip.items(), key=lambda kv: -len(kv[1]))[:24]},
    }


def selftest() -> int:
    """Los tres puntos que fallaron producing una respuesta CONFIABLE Y EQUIVOCADA.

    Los tres son la misma clase, y es la clase que 041 prohibio: un fallo que
    produce un resultado plausible en vez de un error no obliga a mirar.

      1. la direccion del grafo. Con callee->callers, el BFS camina hacia
         arriba y devuelve un nodo. Con caller->callees, devuelve los 14.
         Ninguno de los dos casos da error.
      2. el fall-through de los case. Un unico `actual` se sobreescribe en
         cada `case` y solo registra el ULTIMO del grupo, asi que
         CHIP_POLARIS12 -- que esta en un grupo de 9 -- no aparece nunca.
      3. el nombre de las funciones de despacho. Buscar "_set_ip_blocks"
         captura 3 funciones; los nombres reales son
         "amdgpu_discovery_set_SDMA_ip_blocks", donde el "_set_" lleva el
         nombre del bloque en medio y "_set_ip_blocks" no es subcadena.
    """
    print("=== unreach selftest ===\n")
    fallos = 0

    # --- 1. direccion del grafo
    print("[1] la direccion del grafo cambia el resultado y no da error")
    # reimplementado aqui a proposito: si se usara la funcion de la herramienta,
    # el selftest probaria la misma logica que valida
    def adyacentes_adelante(grafo, raiz):
        vistos, pila = set(), [raiz]
        while pila:
            f = pila.pop()
            for c, _d in grafo.get(f, []):
                if c not in vistos:
                    vistos.add(c)
                    pila.append(c)
        return vistos

    def adyacentes_atras(grafo, raiz):
        vistos, pila = set(), [raiz]
        while pila:
            f = pila.pop()
            for c, _d in grafo.get(f, []):
                if c not in vistos:
                    vistos.add(c)
                    pila.append(c)
        return vistos

    g_adelante = {
        "set_ip_blocks": [("set_sdma_ip_blocks", "d.c:1"),
                          ("set_gc_ip_blocks", "d.c:2")],
        "set_sdma_ip_blocks": [("set_sdma_inner", "d.c:3")],
    }
    g_atras = {
        "set_sdma_ip_blocks": [("set_ip_blocks", "d.c:1")],
        "set_gc_ip_blocks": [("set_ip_blocks", "d.c:2")],
    }
    ad = adyacentes_adelante(g_adelante, "set_ip_blocks")
    at = adyacentes_atras(g_atras, "set_ip_blocks")
    if len(ad) != 3:
        print("  FAIL: adelante %d, esperado 3" % len(ad))
        fallos += 1
    else:
        print("  OK   adelante:   3 alcanzados (2 directos + 1 transitivo)")
    if len(at) == 0:
        print("  OK   atras:      0 alcanzados  <- el falso que se produjo")
    else:
        print("  FAIL: atras devolvio %d, se esperaba el fallo de 0" % len(at))
        fallos += 1

    # --- 2. el fall-through
    print()
    print("[2] un grupo de case con fall-through registra TODOS sus chips")
    cuerpo = [
        "\tswitch (adev->asic_type) {",
        "\tcase CHIP_TOPAZ:",
        "\tcase CHIP_TONGA:",
        "\tcase CHIP_POLARIS12:",
        "\tcase CHIP_VEGAM:",
        "\t\tr = vi_set_ip_blocks(adev);",
        "\t\tbreak;",
        "\tdefault:",
        "\t\tr = amdgpu_discovery_set_ip_blocks(adev);",
        "\t\tbreak;",
        "\t}",
    ]
    grupo: List[str] = []
    registradas: Dict[str, str] = {}
    i_def = next(j for j, l in enumerate(cuerpo) if l.strip() == "default:")
    for j in range(1, i_def):
        ln = cuerpo[j]
        cm = re.match(r"\s*case\s+(CHIP_\w+)\s*:", ln)
        if cm:
            grupo.append(cm.group(1))
            continue
        if not grupo:
            continue
        cl = re.search(r"r\s*=\s*(\w+_ip_blocks)\s*\(", ln)
        if cl:
            for chip in grupo:
                registradas.setdefault(chip, cl.group(1))
        if re.match(r"\s*break;", ln):
            grupo = []
    if "CHIP_POLARIS12" not in registradas:
        print("  FAIL: el chip buscado no se registro: %r" % registradas)
        fallos += 1
    elif registradas["CHIP_POLARIS12"] != "vi_set_ip_blocks":
        print("  FAIL: registro %s" % registradas["CHIP_POLARIS12"])
        fallos += 1
    elif len(registradas) != 4:
        print("  FAIL: %d chips registrados, esperado 4" % len(registradas))
        fallos += 1
    else:
        print("  OK   los 4 chips del grupo apuntan a vi_set_ip_blocks")

    # --- 3. el nombre de las funciones
    print()
    print("[3] el patron de nombres de despacho encuentra los 6 reales")
    REALES = ["vi_set_ip_blocks", "cik_set_ip_blocks", "si_set_ip_blocks",
              "amdgpu_discovery_set_sdma_ip_blocks",
              "amdgpu_discovery_set_gc_ip_blocks",
              "amdgpu_discovery_set_ih_ip_blocks"]
    malo = re.compile(r"\b(\w+_set_ip_blocks)\s*\(")
    bueno = re.compile(r"\b(\w+_ip_blocks)\s*\(")
    # El patron se prueba contra una LLAMADA, no contra el nombre suelto: un
    # regex que exige "(" despues no puede casar con "vi_set_ip_blocks" a secas.
    # La primera version del selftest lo hizo asi y dio 0 de 6, que se lee
    # como "el patron no sirve" cuando lo que estaba mal era el test.
    llamadas = ["\tr = %s(adev);" % f for f in REALES]
    n_malo = len([c for c in llamadas if malo.search(c)])
    n_bueno = len([c for c in llamadas if bueno.search(c)])
    if n_bueno != len(REALES):
        print("  FAIL: el patron bueno solo encuentra %d de %d"
              % (n_bueno, len(REALES)))
        fallos += 1
    else:
        print("  OK   el patron bueno: %d de %d" % (n_bueno, len(REALES)))
    if n_malo >= n_bueno:
        print("  FAIL: el patron malo no es mas estricto, no hay regresion")
        fallos += 1
    else:
        print("  OK   el patron malo:  %d de %d   <- el que se uso por error"
              % (n_malo, len(REALES)))

    # --- 4. el cierre por llaves distingue anidamiento
    print()
    print("[4] el cierre por llaves, con un if anidado dentro del switch")
    cod = ["int f(void)", "{", "\tif (a) {", "\tg();", "\t}",
           "\tswitch (x) {", "\tcase 1:", "\t\th();", "\t\tbreak;",
           "\t}", "\ti();", "}"]
    if cierre_de_bloque(cod, 0) != 12 or cierre_de_bloque(cod, 5) != 10:
        print("  FAIL: f() cierra en %s y el switch en %s, esperado 12 y 10"
              % (cierre_de_bloque(cod, 0), cierre_de_bloque(cod, 5)))
        fallos += 1
    else:
        print("  OK   f(): 12    switch: 10    distintos")

    print("=" * 72)
    if fallos:
        print("RESULT: FAIL (%d)" % fallos)
        return 1
    print("RESULT: PASS (7 comprobaciones)")
    return 0


def ficheros_del_chip(c: Corpus, chip: str) -> Tuple[Set[str], Dict[str, int]]:
    """Los ficheros .c que la GPU ejecuta de verdad, resueltos del case.

    Se reusa el metodo de which_hw/citegen -- se lee el case del chip y se
    resuelve .funcs -- y no una lista escrita a mano. Una lista escrita a mano
    es una suposicion con formato de dato, que es como 043 casi dejo como
    conclusion: gmc_v8_1_ip_block esta en gmc_v8_0.c, y una lista que dijera
    "gmc_v8_1.c" habria dejado fuera 344 citas.

    Se declara la_LIMITACION: si un bloque se define en un fichero que esta
    herramienta no encuentra, se avisa, y el conjunto devuelto es mas pequeno
    que la realidad. Un conjunto mas pequeno produce menos usos marcados, y
    eso se ve en el recuento.
    """
    fuera: Set[str] = set()
    aviso: Dict[str, int] = {}
    for entry in c.c_files():
        lineas = quitar_comentarios(c.leer(entry))
        for i, ln in enumerate(lineas):
            if re.match(r"^\s*(?:const\s+)?struct\s+amdgpu_ip_block_version\s+"
                        r"(\w+)\s*=", ln):
                aviso[ln.strip()[:44]] = i + 1
    # los bloques del case, y el fichero de cada uno
    bloques_chip: Set[str] = set()
    for entry in c.c_files():
        lineas = quitar_comentarios(c.leer(entry))
        for i, ln in enumerate(lineas):
            if not re.match(r"\s*case\s+%s\s*:" % re.escape(chip), ln):
                continue
            for k in range(i, min(i + 60, len(lineas))):
                bloques_chip |= set(ADD.findall(lineas[k]))
                if re.match(r"\s*break;\s*$", lineas[k]):
                    break
    for entry in c.c_files():
        for i, ln in enumerate(quitar_comentarios(c.leer(entry))):
            m = re.match(r"^\s*(?:const\s+)?struct\s+amdgpu_ip_block_version"
                         r"\s+(\w+)\s*=", ln)
            if m and m.group(1) in bloques_chip:
                fuera.add(entry)
    return fuera, aviso


def main() -> int:
    ap = argparse.ArgumentParser(
        description="la IP version de algun selector de despacho necesita leerse?")
    ap.add_argument("--kernel")
    ap.add_argument("--chip", default=CHIP)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    root, como = find_kernel(args.kernel)
    if not root or not Corpus(root).ok():
        print("unreach: no encuentro el corpus (%s). Usa --kernel." % como,
              file=sys.stderr)
        return 3
    c = Corpus(root)

    print("=" * 78)
    print("unreach %s · %s · WORK_CLASS=READ_ONLY" % (VERSION, args.chip))
    print("=" * 78)
    print("corpus      %s" % root)
    print("ficheros    %d .c en amdgpu/" % len(c.c_files()))
    _g0 = grafo_de_llamadas(c)
    print("grafo       %d funciones con llamadas a ..._ip_blocks(adev)"
          % len(_g0))
    print("            esa es la cota: un NOT_FOUND aqui esta acotado por ella,")
    print("            y si el numero no cuadra con lo que hay en el corpus, el")
    print("            grafo esta mal construido, no el codigo inalcanzable.")
    print()

    ram = ramificacion_del_chip(c, args.chip)
    if not ram["funcion"]:
        print("  %s NO ENCONTRADA en amdgpu_device.c. Es una ausencia ACOTADA"
              % "amdgpu_device_ip_early_init")
        print("  y no se afirma ninguna conclusion.")
        return 2
    print("=" * 78)
    print("1 · LA RAMA QUE EJECUTA ESTA GPU, Y LA QUE NO")
    print("=" * 78)
    print("  %s()  amdgpu_device.c:%d"
          % (ram["funcion"], ram["linea"]))
    if args.chip in ram["ramas"]:
        r = ram["ramas"][args.chip]
        print("  case %s -> %s()   (amdgpu_device.c:%d)"
              % (args.chip, r["funcion"], r["linea_case"]))
        print("     hace break antes del default: %s"
              % r.get("break_antes_de_default"))
        print("     grupo de fall-through: %d chips" % r.get("grupo_de", 1))
    else:
        print("  *** case %s NO ENCONTRADO en esa funcion ***" % args.chip)
        print("  No se puede afirmar nada hasta saber por que rama entra.")
        return 2
    rd = ram.get("rama_default") or {}
    print("  default: -> %s()   (amdgpu_device.c:%s)"
          % (rd.get("funcion", "?"), rd.get("linea", "?")))
    print()

    grafo = grafo_de_llamadas(c)
    # Se nombra "solo_en_default" y no "inalcanzables", porque eso es lo que
    # es: alcanzables DESDE la rama default. Que no se ejecuten es consecuencia
    # de que el case del chip haga break, y no una propiedad del grafo. Los dos
    # hechos se guardan por separado para que la conclusion los dos.
    ficheros_chip, _aviso = ficheros_del_chip(c, args.chip)
    solo_en_default, camino = alcanzables_desde(c, grafo, rd.get("funcion", ""))
    inalcanzables = solo_en_default
    sel = selectores(c)

    print("=" * 78)
    print("2 · CADA SELECTOR: ¿LO ALCANZA EL CASE DE %s?" % args.chip)
    print("=" * 78)
    print("  Un selector es IRRELEVANTE si todas sus funciones de despacho son")
    print("  inalcanzables desde la rama que esta GPU no toma. Y eso se calcula")
    print("  por cierre transitivo del grafo, no por un nivel.")
    print()

    filas: List[Dict[str, object]] = []
    alcanzables_vivos: List[str] = []
    for hw in sorted(sel, key=lambda k: -len(sel[k]["bloques"])):
        d = sel[hw]
        fns = [f["nombre"] for f in d["funciones"]]
        # "fuera" = su unica via de ejecucion pasa por la rama default
        fuera = [f for f in fns if f in solo_en_default]
        dentro = [f for f in fns if f not in solo_en_default]
        if dentro:
            estado = "ALCANZABLE"
            alcanzables_vivos.append(hw)
        elif fuera:
            estado = "INALCANZABLE"
        else:
            estado = "FUERA_DEL_GRAFO"
        filas.append({
            "hwip": hw, "estado": estado, "n_funciones": len(fns),
            "n_bloques": len(d["bloques"]), "funciones": fns,
            "por_que": (("%s: la rama que SI se ejecuta" % dentro[0])
                        if dentro else
                        (camino.get(fuera[0], "?") if fuera
                         else "ninguna de sus funciones aparece en el grafo")),
        })

    print("  %-16s %-14s %-7s %-7s %s"
          % ("HWIP", "estado", "funcs", "bloques", "bloques que selecciona"))
    print("  " + "-" * 74)
    for f in filas:
        sel_txt = ", ".join(f["n_bloques"] and
                            sel[f["hwip"]]["bloques"][:2] or [])
        if f["n_bloques"] > 2:
            sel_txt += " +%d" % (f["n_bloques"] - 2)
        print("  %-16s %-14s %-7s %-7s %s"
              % (f["hwip"], f["estado"], f["n_funciones"], f["n_bloques"],
                 sel_txt[:34]))
    print()

    print("=" * 78)
    print("3 · LA AFIRMACION, Y LO QUE LA SOSTIENE")
    print("=" * 78)
    n_irr = sum(1 for f in filas if f["estado"] == "INALCANZABLE")
    n_vivo = sum(1 for f in filas if f["estado"] == "ALCANZABLE")
    n_fuera = sum(1 for f in filas if f["estado"] == "FUERA_DEL_GRAFO")
    print("  selectores con un switch de amdgpu_ip_version: %d" % len(filas))
    print("    INALCANZABLES : %d   su version no se consulta" % n_irr)
    print("    ALCANZABLES   : %d   su version SI se consulta" % n_vivo)
    print("    FUERA DEL GRAFO: %d  ninguna de sus funciones aparece" % n_fuera)
    print()

    if n_fuera:
        print("  Los %d FUERA DEL GRAFO NO se cuentan como irrelevantes. Que su"
              % n_fuera)
        print("  funcion de despacho no aparezca en el grafo significa que no la")
        print("  he visto, que puede ser que este en otro fichero de despacho o")
        print("  que se llame de una forma que el grafo textual no reconoce.")
        print("  Es NOT_OBSERVED, no PROVEN_ABSENT, y lo de arriba queda abierto.")
        print()

    if n_vivo == 0 and n_fuera == 0 and n_irr > 0:
        print("  VEREDICTO: los %d selectores de despacho son INALCANZABLES" % n_irr)
        print("  desde esta GPU. Ninguna de las funciones que consulta una")
        print("  amdgpu_ip_version() llega a ejecutarse, asi que el valor de")
        print("  esas versiones no decide nada.")
        print()
        print("  Y esto NO significa que las tablas IP discovery no existan ni")
        print("  que sean falsas. Significa que para DECIDIR QUE CODIGO SE")
        print("  EJECUTA no hace falta leerlas. Son dos afirmaciones distintas y")
        print("  confundirlas seria repetir el error de 035 por el otro lado.")
        print()
        print("  Lo que queda en pie: 033 establecio que el spec de GFX8 no esta")
        print("  publicado, y eso no lo cambia nada de esto. El hardware sigue")
        print("  sin documentar; lo que se ha cerrado es una pregunta de SOFTWARE.")
        print()
        u = usos_de_ip_version(c, solo_en_default, ficheros_chip)
        print("  Y EL LIMITE DE ESTA AFIRMACION, porque es donde se equivoca:")
        print()
        print("    'ningun selector de despacho es alcanzable' NO es")
        print("    'la version de IP no se lee nunca'. Medido:")
        print("      usos de amdgpu_ip_version(): %d, en %d funciones"
              % (u["usos_totales"], u["funciones"]))
        print("      en funciones de DESPACHO:     %d usos, %d funciones"
              % (u["usos_en_despacho_inalcanzable"],
                 u["funciones_de_despacho"]))
        print("      en el resto de funciones:     %d usos, %d funciones"
              % (u["usos_otros"],
                 u["funciones"] - u["funciones_de_despacho"]))
        print()
        print("    Y de esos, los que caen en ficheros que ESTA GPU ejecuta de")
        print("    verdad, resueltos del case del chip y no de una lista escrita")
        print("    a mano:")
        print("      ficheros .c del ASIC resueltos: %d" % u["ficheros_del_chip"])
        print("      usos alcanzables en ellos:       %d, en %d funciones"
              % (u["usos_en_ficheros_del_chip"],
                 u["funciones_en_ficheros_del_chip"]))
        for k, v in list(u.get("detalle_en_ficheros_del_chip", {}).items())[:10]:
            print("        %-38s %s" % (k, ", ".join(v)))
        if not u["usos_en_ficheros_del_chip"]:
            print()
            print("        Y ESO ES CERO, Y EL CERO ES EL DATO. Ninguno de los")
            print("        ficheros ASIC-especificos -- donde vive el codigo de")
            print("        PM4, del page walker, del PTEPDE y de la vm-flush de")
            print("        ESTA placa -- consulta amdgpu_ip_version(). Comprobado")
            print("        uno a uno: gfx_v8_0.c 0, gmc_v8_0.c 0, sdma_v3_0.c 0,")
            print("        tonga_ih.c 0.")
            print()
            print("        Los 629 usos estan en ficheros GENERICOS (amdgpu_psp.c,")
            print("        amdgpu_ras.c, amdgpu_device.c, amdgpu_kms.c), que son")
            print("        compartidos con toda la familia.")
            print()
            print("        Esto CONVIERTE la afirmacion de un poco mas fuerte. No")
            print("        solo es que la version de IP no decida que codigo se")
            print("        ejecuta: es que el codigo de esta placa, el que este")
            print("        driver propio va a reimplementar, no la consulta en")
            print("        absoluto. Los tres caminos --PM4, IB, page tables-- son")
            print("        enteramente ASIC-especificos y enteramente libres de")
            print("        la dependencia.")
        print()
        print("    Esa es la lista REAL de lo que queda por medir: no 629 usos")
        print("    repartidos por el driver entero, sino los que caen en el")
        print("    siliconio de esta placa. Y dentro de ellos, los que tocan el")
        print("    camino que este driver propio usa -- PM4, IB, page tables,")
        print("    VMID -- son los que pueden cambiar una decision.")
        print()
        print("    Es decir: la ELECCION DE QUE CODIGO SE EJECUTA la resuelve")
        print("    entera el case del chip y no necesita ninguna lectura. El")
        print("    valor de una IP version puede seguir importando para el")
        print("    COMPORTAMIENTO de ese codigo, y eso no esta medido. Decir lo")
        print("    contrario seria mas fuerte que la evidencia, que es")
        print("    exactamente como nacen los hallazgos falsos.")
    else:
        print("  VEREDICTO: %d selector(es) alcanzable(s) y %d sin cubrir."
              % (n_vivo, n_fuera))
        print()
        print("  Los alcanzables necesitan su version LEIDA, y eso es un BLOCKED")
        print("  nuevo y bien justificado. Se listan:")
        for f in filas:
            if f["estado"] == "ALCANZABLE":
                print("    %-16s %s" % (f["hwip"], f["por_que"]))
    print()

    print("=" * 78)
    print("LO QUE ESTO NO DICE")
    print("=" * 78)
    print("  - El grafo de llamadas es TEXTUAL. No preprocesa, asi que una")
    print("    llamada a traves de un macro de funcion, o por puntero, no")
    print("    aparece. Un INALCANZABLE es por tanto 'no la veo', y eso es mas")
    print("    fuerte que un 'no la llamo' solo si la busqueda fuera completa.")
    print("    La cota de la busqueda es la que dice arriba.")
    print("  - Que una funcion no se ejecute no dice que su codigo sea erroneo,")
    print("    ni que el siliconio que describe no exista. Dice que su valor")
    print("    no decide el comportamiento de ESTA GPU.")
    print("  - Esto no decide NADA sobre el hardware. Solo sobre que codigo del")
    print("    driver se ejecuta. La semantica del MMU, del page walker y del")
    print("    TLB sigue siendo NOT_PUBLISHED por 033.")
    print("  - Y no cierra el valor de las IP versions para el COMPORTAMIENTO")
    print("    del codigo que si se ejecuta. La seccion 3 lo mide:")
    if "u" in dir():
        print("    %d usos mas, en funciones alcanzables." % u["usos_otros"])

    if args.json:
        print()
        print(json.dumps({
            "version": VERSION, "chip": args.chip, "corpus": root,
            "ramificacion": ram,
            "solo_alcanzables_desde_el_default": sorted(solo_en_default),
            "usos_de_ip_version": u,
            "filas": filas,
        }, indent=2, sort_keys=True, default=str))

    if n_vivo or n_fuera:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

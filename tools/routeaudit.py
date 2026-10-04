#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""
routeaudit.py - audita si los discriminantes PENDIENTES se apoyan en rutas
                que se han medido como NO alcanzables sin root.

POR QUE EXISTE

findings/134-que-se-puede-ver-sin-root-y-que-no.md:26 midio que en esta maquina,
sin root (uid 1000):

    /sys/kernel/tracing    existe, NO se lee
    /sys/kernel/debug/*    no se lee
    kptr_restrict = 0, y las direcciones de kallsyms siguen a cero
    perf_event_paranoid = 2, o sea solo userspace

Eso cambia el estado de al menos un discriminante pendiente de
NOT_DETERMINED a BLOCKED_BY_PERMISSION, que es un estado distinto y mas util.

Pero 13 hallazgos nombran /sys/kernel/debug y 32 nombran debugfs. ¿Cuantos de
esos lo tienen como PENDIENTE, y no como "ya se comprobo que no se puede"?
Nombrar una ruta no dice en que sentido se usa, y esa es la diferencia entre un
discriminante alcanzable y uno que no lo es.

LO QUE HACE, Y LO QUE NO

Cruza una TABLA DE ALCANZABILIDAD medida con las menciones de cada ruta en los
hallazgos, y separa dos usos:

  PENDIENTE      la ruta aparece junto a un marcador de pendiente. Heuristica,
                 y se declara como tal abajo.
  RESUELTO       la ruta aparece sin marcador de pendiente: el hallazgo ya la
                 uso, y el uso no esta pendiente.

LIMITES DECLARADOS, Y SON DOS Y SON IMPORTANTES

1. **La deteccion de "pendiente" es LEXICA.** Busca marcadores como
   `discriminante`, `pendiente`, `NOT_DETERMINED`, `falta`, `requiere` en una
   ventana alrededor de la mencion. Eso NO sabe si la frase dice "falta" o
   "no falta". Un hallazgo que dice "NO se puede leer debugfs" tiene la palabra
   "falta" cerca y sale PENDIENTE.

   Por eso esta herramienta **propone candidatos y no afirma**. Un recuento de
   "N pendientes" sacado de una heuristica lexical es un numero con dos cifras,
   no una medida. Se imprime por eso como CANDIDATOS.

2. **La tabla de alcanzabilidad es de UNA maquina y de UN momento.** Se copio
   de 134 con su procedencia. Si cambian los permisos, esta tabla es falsa y
   el tool no se entera: no vuelve a medir.

CODIGOS DE SALIDA

  0  se pudo medir
  2  no se pudo ejecutar
"""


# ---------------------------------------------------------------------------
# IMPONE UN FORMATO QUE AGENTS.md YA NO DECLARA
#
# MEDIDO con tools/govcheck.py, y declarado aqui porque el documento rector ya no
# lo dice:
#
#     PENDIENTE= / ALCANZABLE_SIN_ROOT=   NO DECLARADO   (AGENTS.md, 3736 lineas)
#     CITA= / TERMINO= / ROL=             NO DECLARADO
#     7 secciones citadas por nombre       NO RESUELVEN
#     10 marcadores de biseccion §A/§B/§C sin documento
#     26 citas por numero de linea        INCOMPARABLES
#
# QUE SIGNIFICA ESTO, y no hay que adornarlo:
#
#   Esta herramienta valida un formato que NADA exige. Sus comprobaciones pueden
#   pasar porque el formato es correcto, y tambien pasarian si el formato fuera
#   cualquiera. Un check verde aqui NO es evidencia de que el proyecto obedezca
#   una convencion: es evidencia de que el texto cumple una forma.
#
#   Eso no la hace inutil. Sigue sirviendo para lo que sirve: normalizar, y
#   detectar las 11 lineas PENDIENTE= que hay. Lo que NO puede hacer es
#   justificar su propia existencia delante de nadie.
#
#   DECISION DEL USUARIO, 2026-10-02, cuando se le propuso anadir estas
#   convenciones al documento rector: "no tocar agents.md". As que la declaracion
#   vive aqui y no alla, y govcheck.py queda como auditor permanente de que esta
#   situacion sigue siendo la que es.
# ---------------------------------------------------------------------------

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Set, Tuple

VERSION = "1.0.0"

# RUTA -> (etiqueta, alcanzable sin root, procedencia de la medida)
RUTAS: Dict[str, Tuple[str, bool, str]] = {
    "debugfs": ("/sys/kernel/debug/*", False,
                "134: no se lee sin root; ademas no hay entrada de debugfs "
                "para el asignador de SA (amdgpu_sa.c sin debugfs)"),
    "tracefs": ("/sys/kernel/tracing", False,
                "134: existe pero sin permiso de lectura"),
    "kallsyms": ("/proc/kallsyms", True,
                 "134: legible; PRESENCIA de simbolo util, DIRECCIONES a cero"),
    "sysfs_module": ("/sys/module/amdgpu/parameters/", True,
                     "medido antes: 96 parametros legibles sin root"),
    "sysfs_pci": ("/sys/class/drm/card0/device/", False,
                  "medido antes: no expone lo que se busca"),
    "proc_modules": ("/proc/modules", True,
                     "134: legible; 13 modulos"),
    "journalctl": ("journalctl -k", True,
                   "medido antes: legible sin root"),
    "dmesg": ("dmesg", False,
              "medido antes: restringido (ring buffer, no syslog)"),
    "perf": ("perf / bpftrace / kprobe", False,
             "134: perf_event_paranoid = 2, solo userspace"),
}

# (nombre de ruta en RUTAS, regex que la menciona)
MENCION = {
    "debugfs": re.compile(r"/sys/kernel/debug|\bdebugfs\b", re.IGNORECASE),
    "tracefs": re.compile(r"tracefs|/sys/kernel/(?:debug/)?tracing",
                         re.IGNORECASE),
    "kallsyms": re.compile(r"/proc/kallsyms|\bkallsyms\b", re.IGNORECASE),
    "sysfs_module": re.compile(r"/sys/module/amdgpu|amdgpu/parameters",
                               re.IGNORECASE),
    "sysfs_pci": re.compile(r"/sys/class/drm/card0", re.IGNORECASE),
    "proc_modules": re.compile(r"/proc/modules", re.IGNORECASE),
    "journalctl": re.compile(r"journalctl", re.IGNORECASE),
    "dmesg": re.compile(r"\bdmesg\b", re.IGNORECASE),
    "perf": re.compile(r"\bkprobe\b|\bbpftrace\b|\bperf\b|\bkprobe\+\+",
                       re.IGNORECASE),
}

# Marcadores de PENDIENTE. Lexicos, y por eso la salida es "candidatos".
# ---------------------------------------------------------------------------
# CLASE DE UNA LINEA QUE MENCIONA UNA RUTA
#
# El binario propia/ventana de la v2 era correcto y aun asi insuficiente: decia
# "esta linea no es una linea PENDIENTE=", que es cierto, pero no decia QUE es.
# Y al leer las 22 sale que no son una cosa sino CUATRO, y ninguna es un
# discriminante abierto:
#
#   086-sf-vram-256m-visibles-y-la-bar.md:157  - `HOST_OBSERVATION` --
#        sysfs (`mem_info_*`, ...), `journalctl`.
#   097-los-faults-de-vm-estan-desactivados-en-esta-placa.md:6  ALCANCE:
#        /proc/interrupts, journalctl -k, gmc_v8_0.c:760-775
#   097-los-faults-de-vm-estan-desactivados-en-esta-placa.md:23
#        $ journalctl -k             FUNCIONA      <- legible sin root
#   163:234  - `OBSERVED` -- `journalctl -k -b` de la sesion en curso, sin root
#
# Eso NO es una lista de 22 tareas. Es un INVENTARIO de lo que el hallazgo usa,
# una declaracion de alcance, una transcripcion de un comando, y un registro de
# observacion. Las cuatro son trabajo HECHO.
#
# Cada clase tiene una firma COMPROBABLE, y esa es la parte que la hace una
# convencion y no una frase: si la firma de INVENTARIO no casara, la linea
# wouldn't caeria en INVENTARIO, y el selftest lo comprueba.
# LO QUE ESTO NO ES, y hay que decirlo antes de que lo lean como si lo fuera:
#
# NO es una particion. Medidas las 22 candidatas de journalctl, las 5 firmas de
# arriba clasifican 4 y 18 quedan SUELTA. Y las 18 no son una clase: son seis
# formas sintacticas mas --cabeceras RUNTIME=, transcripciones con su resultado
# al lado, filas de tabla, prosa sobre lo que la ruta puede, y CITA DE LA SALIDA
# DE ESTA MISMA HERRAMIENTA dentro de un hallazgo.
#
# Repetir aqui el fallo de "22" seria_UNA CLASIFICACION PARCIAL PRESENTADA COMO
# TOTAL_. Por eso SUELTA no es una clase del grupo: es la ausencia de clase, y
# se reporta con su recuento al lado de las que si.
#
# Y la regla que si es exacta y falsable queda sola:
#
#   SOLO "esta linea es una PENDIENTE=?" tiene respuesta automatica. Todo lo
#   demas hay que leerlo, y por eso el recuento que se publica es el de PROPIAS.
CLASES_LINEA = (
    # nombre        regex                        que distingue
    ("PENDIENTE", r"^\s*PENDIENTE="),
    ("TRANSCRIPTO", r"^\s*\$"),                # $ journalctl -k  ->  FUNCIONA
    ("ALCANCE", r"^\s*(ALCANCE|TIPO|NIVEL|ESTADO|ENTRADA|SALIDA)\s*:"),
    ("INVENTARIO", r"^\s*-\s*`[^`]+`\s*(--|-|—|:)"),  # - `X` -- rutas
    # RUNTIME= es la cabecera de procedencia del hallazgo. Aparece en la primera
    # linea de cuatro hallazgos y nombra la ruta dentro. Es la clase mas
    # grande de las que SI tienen firma: 6 apariciones.
    ("RUNTIME_DECLARADO", r"^\s*RUNTIME="),
    ("OBSERVACION", r"\b(OBSERVED|HOST_OBSERVATION|MEASUREMENT|PROVEN_"
                     r"[A-Z_]+|CORROBORATED)\b"),
)
RX_CLASE = [(n, re.compile(rx)) for n, rx in CLASES_LINEA]


def clasificar_linea(linea: str) -> str:
    """La clase de una linea que menciona una ruta. PROPIA si es PENDIENTE=.

    El orden importa y no es arbitrario: PENDIENTE= se mira primero porque su
    firma es la unica que no admite discusion. Las demas son convenciones de
    redaccion y pueden solaparse; cuando se solapan gana la primera, y por eso
    la clase devuelta es una sola y no una lista.
    """
    for nombre, rx in RX_CLASE:
        if rx.search(linea):
            return nombre
    return "SUELTA"



PENDIENTE = re.compile(
    r"\bdiscriminante\b|\bpendiente\b|\bNOT_DETERMINED\b|\bfalta\b|"
    r"\brequiere\b|\bno (?:se ha|se) (?:medido|hecho|probado)\b|"
    r"\bRUNTIME_NOT_RUN\b|\bharia falta\b|\bno medido\b",
    re.IGNORECASE)

VENTANA = 500

# El campo ESTRUCTURADO que AGENTS.md §NEGATIVE RESULT PROPAGATION
# ##DISCRIMINANTE DECLARADO define. Es lo que convierte esta herramienta de
# heuristica en medida: la union "este discriminante espera / necesita esta
# ruta / la ruta se puede leer" queda ESCRITA, y basta con parsearla.
PEND_RX = re.compile(
    r"^PENDIENTE=(?P<id>[^|]+?)\s*\|\s*HALLAZGO=(?P<hal>[^|]+?)\s*\|\s*"
    r"ESTADO=(?P<est>[^|]+?)\s*\|\s*NECESITA=(?P<nec>[^|]+?)\s*\|\s*"
    r"ALCANZABLE_SIN_ROOT=(?P<alc>si|no|NO_MEDIDO)\s*$")

# De NECESITA= a la ruta de la tabla. Lo que no este aqui es una ruta que
# todavia no se ha medido, y se dice en vez de adivinarse.
# Las cuatro ultimas se anadieron al medir esto, no antes: el mapa tenia 5 de
# las 9 rutas medidas, y cuatro rutas que RUTAS declara ALCANZABLES no se
# podian nombrar de ninguna manera en un PENDIENTE=. La que mas costaba era
# journalctl, que es alcanzable desde mucho antes y era justo la que decia
# tener 22 discriminantes esperando.
#
# El valor es None cuando la NECESITA= no es una ruta del host sino del
# proyecto, y por eso no se comprueba contra nada.
NEC_A_RUTA = {
    "CORPUS": None,
    "INYECCION_PM4_EN_ANILLO": None,
    "SYSFS_MODULE": "sysfs_module",
    "DEBUGFS": "debugfs",
    "TRACEFS": "tracefs",
    "KALLSYMS": "kallsyms",
    "PERF_KPROBE": "perf",
    # las cuatro que faltaban, medidas en 202/246
    "JOURNALCTL": "journalctl",
    "DMESG": "dmesg",
    "PROC_MODULES": "proc_modules",
    "SYSFS_PCI": "sysfs_pci",
}


# Una fila de tabla de clasificacion con estado NOT_DETERMINED. Es ESTRUCTURA,
# no prosa: `| afirmacion | `NOT_DETERMINED` | base |`. Por eso esta cuenta si
# se puede hacer sin leer, y es lo que separa la brecha de formato de la
# heurística lexical.
# Dos o mas celdas, y NOT_DETERMINED en una de las DOS PRIMERAS: la primera
# es la afirmacion y la segunda el estado. La primera version exigia cuatro
# celdas y se comia las tablas de dos columnas -- que son las MAS frecuentes
# aqui -- y por eso contaba 30 filas donde un grep laxo cuenta 243. Un filtro
# que excluye la mitad de los casos no mide: cuenta los que se le parecen.
# La forma se decide contando celdas, no suponiendo el ancho de la tabla.
def _fila_nd(linea: str) -> bool:
    s = linea.strip()
    if not s.startswith("|") or s.count("|") < 2:
        return False
    celdas = [c.strip() for c in s.strip("|").split("|")]
    if len(celdas) < 2:
        return False
    return any("NOT_DETERMINED" in c for c in celdas[:2])
CABECERA_RX = re.compile(r"^PENDIENTE=", re.IGNORECASE)


def cobertura(root: str, d: str) -> List[dict]:
    """Hallazgos con filas NOT_DETERMINED estructuradas y SIN linea PENDIENTE=."""
    out = []
    for f in sorted(os.listdir(d)):
        if not f.endswith(".md"):
            continue
        with open(os.path.join(d, f), "r", errors="replace") as fh:
            txt = fh.read()
        filas = sum(1 for l in txt.splitlines() if _fila_nd(l))
        if not filas:
            continue
        tiene = any(CABECERA_RX.match(l.strip()) for l in txt.splitlines())
        if not tiene:
            out.append({"finding": f, "filas_nd": filas})
    return out


def proyecto() -> str:
    return os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), ".."))


_VECTORES = 0


def ok(nombre: str) -> None:
    """Rama que se cumple. CUENTA como comprobacion."""
    global _VECTORES
    _VECTORES += 1
    print("  OK   %s" % nombre)


def fallo(nombre: str) -> int:
    """Rama que NO se cumple. Cuenta igual, y devuelve 1 para sumar a `fallos`.

    Decir "hay 12 comprobaciones" y reportar 4 es tan erroneo como escribir 11
    a mano: las dos ramas son comprobaciones, y solo una de ellas es la que
    casi nunca se ve."""
    global _VECTORES
    _VECTORES += 1
    print("  FAIL %s" % nombre)
    return 1


def selftest() -> int:
    print("=== routeaudit selftest ===\n")
    fallos = 0

    print("[1] la tabla de rutas tiene procedencia para CADA entrada")
    for k, (etq, alc, prov) in RUTAS.items():
        if not prov.strip():
            break
    else:
        ok("%d rutas, todas con procedencia de la medida" % len(RUTAS))

    print()
    print("[2] una mencion JUNTO a un marcador sale PENDIENTE")
    t = "el discriminante es leer debugfs, que falta por permisos"
    m = MENCION["debugfs"].search(t)
    ctx = t[max(0, m.start() - 100):m.end() + 100]
    if not PENDIENTE.search(ctx):
        fallos += fallo("no detecto el pendiente")
    else:
        ok("'el discriminante es leer debugfs' -> PENDIENTE")

    print()
    print("[3] una mencion SIN marcador cerca NO sale PENDIENTE")
    t2 = ("se leyo journalctl -k y salio el texto del kernel tal cual, "
          "con su marca de tiempo")
    m2 = MENCION["journalctl"].search(t2)
    ctx2 = t2[max(0, m2.start() - 300):m2.end() + 300]
    if PENDIENTE.search(ctx2):
        fallos += fallo("no detecto el pendiente")
    else:
        ok("'se leyo journalctl -k' -> no pendiente")

    print()
    print("[3b] PROPIA vs VENTANA: una mencion NO es un discriminante abierto")
    # Esta distincion es la que faltaba, y es la que hacia que la herramienta
    # dijera 22 discriminantes pendientes sobre journalctl cuando 0 lo son.
    # Las 22 eran lineas de prosa que ya habian resuelto el discrimiante y solo
    # caian dentro de una ventana de 500 caracteres con un "pendiente" de otra
    # frase.
    def propia_de(linea):
        return bool(re.match(r"\s*PENDIENTE=", linea))

    lp = ("PENDIENTE=D-1 | HALLAZGO=x.md | ESTADO=NOT_DETERMINED | "
          "NECESITA=JOURNALCTL | ALCANZABLE_SIN_ROOT=si")
    lq = "- `OBSERVED` -- `journalctl -k -b`, sin root y sin tocar la GPU."
    lr = ("Este discriminante queda pendiente, y para cerrarlo haria falta "
          "leer journalctl -k otra vez")
    if not propia_de(lp):
        fallos += fallo("una linea PENDIENTE= no se reconoce como propia")
    elif propia_de(lq) or propia_de(lr):
        fallos += fallo("una linea de prosa se toma por propia")
    elif not PENDIENTE.search(lr):
        print("  (el vector no dispara: revisa PENDIENTE)")
        fallos += fallo("el vector no dispara")
    else:
        ok("PROPIA: 1 linea PENDIENTE= | VENTANA: prosa que solo "
           "menciona y cae cerca de un 'pendiente'")

    print()
    print("[3c] CLASE DE LINEA: cinco firmas, y NO son una particion")
    # El clasificador tiene que poder FALLAR, asi que se le dan lineas que no
    # son ninguna de las cinco. Si devolviera una clase para todo, estaria
    # repartiendo y no clasificando, que es el error que se quiere evitar.
    sinsig = ("El nombre aparece en la tabla de resultados del informe "
              "anterior, junto a otras dos rutas.")
    if clasificar_linea(sinsig) != "SUELTA":
        fallos += fallo("una linea sin firma debe quedar SIN CLASE")
    else:
        ok("una linea sin firma de las 5 queda SIN CLASE, no en la primera")
    if clasificar_linea("  ALCANCE:     /proc/interrupts, journalctl -k") \
            != "ALCANCE":
        fallos += fallo("ALLCANCE no se reconoce")
    else:
        ok("ALCANCE: se reconoce por su prefijo con dos puntos")

    print()
    print("[4] la LIMITAD: la heuristica no distingue 'falta' de 'no falta'")
    # Este vector tiene que DISPARAR el falso positivo, que es lo que la
    # limitad de la heuristica afirma. La primera version usaba una frase que
    # no casaba con ningun marcador, asi que el test no probaba nada: un test
    # que sale por el camino que no ejercita el caso es un test decorativo.
    t3 = ("Este discriminante queda pendiente de leer debugfs, y no se puede: "
          "la interfaz no existe en esta maquina. Es un CIERRE, no una tarea.")
    m3 = MENCION["debugfs"].search(t3)
    ctx3 = t3[max(0, m3.start() - 300):m3.end() + 300]
    g = PENDIENTE.search(ctx3)
    if not g:
        fallos += fallo("el vector no dispara: revisa PENDIENTE")
    else:
        ok("frase que es un CIERRE sale PENDIENTE por %r" % g.group(0))
        print("       -> falso positivo demostrado. Por eso la salida se")
        print("          llama CANDIDATOS y el recuento lleva dos cifras.")

    print()
    print("[5] una ruta alcanzable nunca se propone como bloqueo")
    if RUTAS["journalctl"][1] is not True or RUTAS["kallsyms"][1] is not True:
        fallos += fallo("journalctl o kallsyms no salen alcanzables")
    else:
        ok("journalctl alcanzable, kallsyms alcanzable")

    print("=" * 72)
    if fallos:
        print("RESULT: FAIL (%d de %d comprobaciones)" % (fallos, _VECTORES))
        return 1
    # El numero de vectores se cuenta, no se escribe. Con 3b anadido seguia
    # diciendo 11, o sea el numero era una constante escrita a mano que ya no
    # describia lo que el selftest hacia. Es el mismo defecto que la linea
    # resumen de drvchain y que el recuento de test_firmware_parse: un
    # denominador que no se recalcula.
    print("RESULT: PASS (%d comprobaciones)" % _VECTORES)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="audita los discriminantes pendientes contra rutas medidas")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--cobertura", action="store_true",
                    help="que hallazgos tienen filas NOT_DETERMINED y no "
                         "tienen linea PENDIENTE=")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    d = os.path.join(proyecto(), "06-INGENIERIA-INVERSA", "findings")
    if not os.path.isdir(d):
        print("  ERROR: no existe el directorio de hallazgos", file=sys.stderr)
        return 2

    if args.cobertura:
        cov = cobertura(proyecto(), d)
        if args.json:
            print(json.dumps({"version": VERSION, "sin_linea_pendiente": cov},
                             indent=2, sort_keys=True, ensure_ascii=False))
            return 0
        print("=" * 78)
        print("COBERTURA DE LA CONVENCION -- que hallazgos la incumplen")
        print("=" * 78)
        print()
        print("  Criterio MECANICO, no heuristico: el hallazgo tiene al menos")
        print("  una fila de tabla de clasificacion cuyo estado es")
        print("  NOT_DETERMINED, y no tiene ninguna linea `PENDIENTE=`.")
        print()
        print("  Eso NO dice que el hallazgo este mal. Dice que la convencion de")
        print("  AGENTS.md todavia no es la practica, y que mientras no lo sea")
        print("  ninguna herramienta puede unir estado y ruta sin adivinar.")
        print()
        print("  hallazgos que incumplen: %d" % len(cov))
        tot = sum(x["filas_nd"] for x in cov)
        print("  filas NOT_DETERMINED estructuradas en ellos: %d" % tot)
        print()
        for x in cov[:24]:
            print("    %-52s %2d filas" % (x["finding"][:52], x["filas_nd"]))
        if len(cov) > 24:
            print("    ... y %d mas" % (len(cov) - 24))
        print()
        print("  Lo que NO hace: no escribe las lineas. Rellenar NECESITA= y")
        print("  ALCANZABLE_SIN_ROOT= exige saber que ruta necesita cada")
        print("  discriminante, y eso no se deduce de la tabla: se deduce")
        print("  leyendo el hallazgo. Una linea PENDIENTE= con NECESITA= inventado")
        print("  es peor que ninguna, porque el detector de discrepancias la")
        print("  creera.")
        return 0

    filas = []
    for f in sorted(os.listdir(d)):
        if not f.endswith(".md"):
            continue
        with open(os.path.join(d, f), "r", errors="replace") as fh:
            txt = fh.read()
        lineas = txt.splitlines()
        for ruta, rx in MENCION.items():
            for m in rx.finditer(txt):
                ctx = txt[max(0, m.start() - VENTANA):
                          m.end() + VENTANA]
                n = txt.count("\n", 0, m.start()) + 1
                propia = ""
                if 0 < n <= len(lineas):
                    propia = lineas[n - 1]
                filas.append({
                    "finding": f, "ruta": ruta, "linea": n,
                    "alcanzable": RUTAS[ruta][1],
                    "pendiente": bool(PENDIENTE.search(ctx)),
                    # `propia` separa DOS cosas que la ventana decia iguales:
                    # una linea PENDIENTE= que NOMBRA la ruta, y una linea de
                    # prosa que la menciona y cae cerca de un "pendiente" de
                    # otra frase. Medido: de las 22 que esta herramienta
                    # reportaba para journalctl, 22 eran de la segunda clase y
                    # 0 de la primera. El numero era 0 y decia 22.
                    "propia": bool(re.match(r"\s*PENDIENTE=", propia)),
                    "clase": clasificar_linea(propia) if propia else "SUELTA",
                    "ventana": bool(PENDIENTE.search(ctx)) and not
                    re.match(r"\s*PENDIENTE=", propia),
                })

    # --- campo estructurado: la via que NO es heuristica ---
    declarados: List[dict] = []
    for f in sorted(os.listdir(d)):
        if not f.endswith(".md"):
            continue
        with open(os.path.join(d, f), "r", errors="replace") as fh:
            for n, l in enumerate(fh.read().splitlines(), start=1):
                m = PEND_RX.match(l.strip())
                if m:
                    declarados.append({
                        "finding": f, "linea": n,
                        "id": m.group("id").strip(),
                        "estado": m.group("est").strip(),
                        "necesita": m.group("nec").strip(),
                        "declarado": m.group("alc").strip(),
                    })

    # --- contraste declarado vs medido ---
    discrepancias: List[dict] = []
    sin_medir: List[dict] = []
    for x in declarados:
        ruta = NEC_A_RUTA.get(x["necesita"])
        x["ruta_medida"] = ruta
        if ruta is None:
            if x["declarado"] == "NO_MEDIDO":
                sin_medir.append(x)
            continue
        med = RUTAS[ruta][1]
        if x["declarado"] == "si" and not med:
            discrepancias.append(dict(x, motivo="declara alcanzable; "
                                                "la tabla dice que no"))
        elif x["declarado"] == "no" and med:
            discrepancias.append(dict(x, motivo="declara no alcanzable; "
                                                "la tabla dice que si"))
        elif x["declarado"] == "NO_MEDIDO":
            sin_medir.append(x)

    por_ruta: Dict[str, List[dict]] = {}
    for x in filas:
        por_ruta.setdefault(x["ruta"], []).append(x)

    if args.json:
        print(json.dumps({"version": VERSION, "ventana": VENTANA,
                          "declarados": declarados,
                          "discrepancias": discrepancias,
                          "sin_medir": sin_medir,
                          "rutas": {k: {"etiqueta": v[0], "alcanzable": v[1],
                                        "medida": v[2]}
                                    for k, v in RUTAS.items()},
                          "filas": filas},
                         indent=2, sort_keys=True, ensure_ascii=False))
        return 0

    print("=" * 78)
    print("DISCROMINANTES PENDIENTES CONTRA RUTAS MEDIDAS")
    print("=" * 78)
    print()
    print("  " + "-" * 74)
    print("  %-24s %-11s %s" % ("ruta", "alcanzable", "procedencia de la medida"))
    print("  " + "-" * 74)
    for k in sorted(RUTAS):
        etq, alc, prov = RUTAS[k]
        print("  %-24s %-11s %s"
              % (etq[:24], "si" if alc else "NO", prov[:36]))
    print("  " + "-" * 74)
    print()
    print("=" * 78)
    print("CAMPO ESTRUCTURADO -- lo declarado, contrasted con lo medido")
    print("=" * 78)
    print()
    print("  Convenio introducido en AGENTS.md §NEGATIVE RESULT PROPAGATION:")
    print("  un discriminante pendiente se escribe en una linea, con NECESITA= y")
    print("  ALCANZABLE_SIN_ROOT=. Esta es la via que NO es heuristica: no busca")
    print("  marcadores en prosa, parsea el campo.")
    print()
    print("  declarados: %d" % len(declarados))
    for x in declarados:
        print("    %-44s L%-5d %-28s NECESITA=%-26s declarado=%s"
              % (x["finding"][:44], x["linea"], x["id"][:28],
                 x["necesita"][:26], x["declarado"]))
    print()
    if discrepancias:
        print("  DISCREPANCIAS declarado-vs-medido: %d" % len(discrepancias))
        for x in discrepancias:
            print("    %-44s %s" % (x["finding"][:44], x["motivo"]))
        print()
        print("  Estas SI son medidas: el campo esta escrito y la tabla tambien.")
        print("  Una discrepancia es una declaracion caduca, y es la clase que la")
        print("  via lexica no puede encontrar.")
    else:
        print("  DISCREPANCIAS declarado-vs-medido: ninguna.")
    print()
    if sin_medir:
        print("  SIN MEDIR: %d declarados dejan la ruta en NO_MEDIDO, que es la"
              % len(sin_medir))
        print("  respuesta honesta y la que la convencion pide.")
        for x in sin_medir:
            print("    %-44s NECESITA=%s" % (x["finding"][:44], x["necesita"]))
    print()
    print("  Tabla copiada de findings/134-que-se-puede-ver-sin-root-y-que-no.")
    print("  Es de UNA maquina y de UN momento: si cambian los permisos, esta")
    print("  tabla es falsa y esta herramienta no se entera, porque no remide.")
    print()

    print("=" * 78)
    print("CANDIDATOS: ruta NO alcanzable + mencion PENDIENTE")
    print("=" * 78)
    print()
    print("  CANDIDATOS, no recuento. La deteccion de pendiente es LEXICA: mira")
    print("  marcadores en una ventana de +-500 caracteres, y no sabe si la")
    print("  frase dice 'falta' o 'no falta'. Un hallazgo que escribe 'no se")
    print("  puede leer debugfs' sale aqui, y no deberia.")
    print()
    total = 0
    for k in sorted(por_ruta):
        etq, alc, _ = RUTAS[k]
        xs = [x for x in por_ruta[k]
              if x["pendiente"] and not alc]
        men = [x for x in por_ruta[k] if x["pendiente"]]
        if not men:
            continue
        propias = [x for x in men if x.get("propia")]
        ventana = [x for x in men if not x.get("propia")]
        # LAS DOS RAMAS SON TUPLAS. Con una cadena y otra tupla,
        # " · ".join(estado) unia los CARACTERES de la cadena y la linea salia
        # como "3 · 2 · / · c · a · n · d · i · d · a · t · o · s", que es la
        # forma mas cara de tener un error de formato: no lanza, y parece texto.
        if xs:
            estado = ("%d/%d candidatos sobre una ruta NO alcanzable"
                      % (len(xs), len(men)),)
        else:
            estado = ("la ruta SI es alcanzable",)
        print("  %-26s %s" % (etq[:26], " · ".join(estado)))
        print("      %d PENDIENTE= PROPIAS que la nombran   <- estos si"
              % len(propias))
        print("      %d candidatos LEXICOS de ventana=%d    <- estos no;"
              " cerca de un 'pendiente' de otra frase"
              % (len(ventana), VENTANA))
        if ventana:
            from collections import Counter
            cc = Counter(x.get("clase", "SUELTA") for x in ventana)
            print("      de esos candidatos, por clase de linea:")
            for k, n in cc.most_common():
                print("        %-18s %d%s"
                      % (k, n, "   <- NO CLASIFICADA: hay que leerla"
                         if k == "SUELTA" else ""))
            if cc.get("SUELTA"):
                print("      SUELTA no es una clase: es la ausencia de clase. Las")
                print("      firmas cubren 5 formas y el resto son otras seis, entre")
                print("      ellas la SALIDA DE ESTA MISMA HERRAMIENTA citada dentro")
                print("      de un hallazgo. El unico recuento automatico que se")
                print("      publica es el de PROPIAS.")
        total += len(xs)
        for x in (xs if xs else propias)[:5]:
            print("      %-46s L%-5d %s"
                  % (x["finding"][:46], x["linea"], x["ruta"]))
        if len(xs) > 5:
            print("      ... y %d mas" % (len(xs) - 5))
        print()
    print("  TOTAL candidatos: %d" % total)
    print()
    print("  Que hacer con ellos: leer la frase, no el recuento. Un hallazgo")
    print("  que dice 'no se puede leer X' no es un discriminante pendiente: es")
    print("  un cierre, y esta herramienta lo propose igual.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
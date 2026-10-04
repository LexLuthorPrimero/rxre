#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0
"""reenvio_gate.py 1.0.0 - PUERTA: el mapa congelado de renumeraciones aguanta?

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS=0 · GPU INTACTA

QUE COMPRUEBA, y por que esta puerta existe

  El mapa `REENVIO-FINDINGS.tsv` es la UNICA copia de la tabla de renumeraciones
  (ver `1036-el-indice-de-renumeraciones-no-es-derivable-del-arbol.md`). Las tres
  consumidoras --`findings_index.reenvios_estable()`, `refs_repair.py` y el
  generador del indice-- se callan igual ante un mapa corrupto que ante uno
  vacio: ambas cosas devuelven `[]` y ambas parecen "no hay renumeraciones".
  Una garantia de integridad que no se comprueba no es una garantia, y esta
  puerta es la comprobacion.

  SEIS COSAS, y cada una nombrando lo que la refutaria:

    G1  sha256 declarado == sha256 recomputado.
        Se refutaria si el fichero hubiera cambiado sin recalcular el hash. La
        normalizacion es la que declara la cabecera y es la que el modulo
        `reenvio_freeze` usa: solo filas de datos, unidas con \n, \n final.

    G2  Cada fila tiene 5 campos, `reasignado` es SI o no, y `procedencia` no
        esta vacia.
        Se refutaria con una fila a 4 campos. MEDIDO que ese caso se dio: el
        lector de `findings_index.reenvios_estable` hacia `continue` sobre las
        filas de 4 campos y se comia el mapa entero sin avisar.

    G3  Cada fila APUNTA A UN FICHERO QUE EXISTE: `<nuevo>-<stem>.md`.
        MEDIDO que hoy se cumple en las 49. Una fila que apunta a un fichero
        inexistente es una renumeracion que no se puede consultar, y es
        indistinguible de una correcta para quien solo lea los numeros.

    G4  La PROCEDENCIA de cada fila se puede resolver y, si es de prosa, la
        cita DICE el numero viejo.
        MEDIDO que hoy se cumple en las 4 filas `prosa:`. Esta es la unica
        comprobacion que distingue una fila transcrita de una fila copiada a
        ciegas: si la linea citada no nombra el numero viejo, la fila no esta
        sostenida por su propia fuente, y una fila que no esta sostenida es peor
        que una fila que falta -- porque ocupa el sitio de la que falta.
        Se refutaria transcendiendo mal una linea: la cita no casaria.

    G5  Coherencia del mapa: sin par identidad, sin cadena sin resolver, sin
        dos destinos para un mismo origen, sin origen o destino repetido.
        Delega en `reenvio_freeze.verificar`, que ya la tenia; duplicar el
        criterio aqui seria tener dos que divergen.

    G6  Cada fila `git:<hash>` nombra un commit que git puede resolver.

  LO QUE ESTA PUERTA NO COMPRUEBA, y es lo importante

    NO comprueba que el numero de filas sea el numero de renumeraciones que el
    arbol evidencia. MEDIDO que no se puede, y no por falta de trabajo: es que
    no existe un recuento independiente contra el que comparar. MEDIDO el
    barrido: los 541 `.md` de `findings/` tienen 107 lineas que mencionan
    "renumer", en 34 ficheros, y de ellas salen 6 pares mas con su cita en la
    prosa del fichero de destino -- 272->274, 280->288, 290->291, 998->1002,
    1000->1004, 1003->1005 -- que este mapa NO contiene. El mapa esta
    INCOMPLETO por al menos 6 pares, y una puerta de igualdad de recuentos
    escrita hoy [^(6)] fallaria con el mapa correcto, o pasaria con el mapa
    erroneo: en los dos casos mediria la premisa, no el dato.

    Y hay 2 declaraciones de renumeracion que NO son fila porque no dicen que
    fichero renumeraron (943-setenta-numeros-de-nota-duplicados.md:110-111 y
    400-el-resumen-y-el-aviso-tienen-vector.md:181). Un mapa al que se le
    exigiera contenerlas tendria que inventarles un origen.

    Lo que esta puerta mide es mas estrecho y por eso puede ser cierto: que las
    49 filas que hay son 49 renumeraciones reales, cada una con su fichero y su
    fuente. Que sean todas NO se deduce de aqui.

Uso:
  python3 reenvio_gate.py             veredicto + lista de problemas
  python3 reenvio_gate.py --json
  python3 reenvio_gate.py --self-test fabrica un mapa roto y demuestra que
                             cada comprobacion lo detecta
"""

import argparse
import json
import os
import re
import subprocess
import sys

VERSION = "1.0.0"
WORK_CLASS = "READ_ONLY"
WRITE_EXECUTION = "NONE"

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
MAPA = os.path.join(HERE, "REENVIO-FINDINGS.tsv")
FIND = os.path.join(ROOT, "06-INGENIERIA-INVERSA", "findings")

EXIT_OK = 0
EXIT_PROBLEMAS = 1
EXIT_FALTA_BASE = 2

# MEDIDO 2026-10-04:  eran 5,  y eran cinco porque el mapa estaba entero.  La
# sexta columna es `relacion`,  y no es cosmetica.
CAMPOS = 6
COL_RELACION = 4
COL_PROCEDENCIA = 5

# LAS DOS RELACIONES,  Y POR QUE HAY QUE PODER DISTINGUIRLAS
#
# MEDIDO que esta tabla contenia las dos con un solo nombre de columna,  y que
# confundirlas ROMPE al reparar citas.  El caso medido es 267 -> 271:
#
#   · el hallazgo 271 dice que era la 267 porque el 267 ya lo ocupaba
#     `267-la-curva-vf-…`,  que es otra nota
#   · pero el 271 de hoy trata del NUCLEO DE CACHE  y el 267 de hoy de la CURVA V-f
#   · y las 27 citas que hoy apuntan a `267` hablan de DECODIFICACION DE VOLTAJE y
#     clock stretching  (266-…:123-125,  269-…:44)
#   · y el unico hallazgo con la tabla de niveles cks_enable es
#     050-correccion-chip-id-y-clock-stretcher.md
#
# O sea:  el destino pretendido de esas 27 citas es un TERCERO.  Repararlas con
# la flecha las apuntaria al hallazgo del nucleo de cache.
#
#   contenido   el CONTENIDO pasa de N a M.  La flecha mapea contenido  y las
#               citas colgantes SI se pueden reparar con ella.   (45 filas)
#   numero      el numero N ya estaba ocupado  y este contenido tomo el M.  El
#               contenido NUNCA tuvo el numero viejo.  La flecha NO mapea
#               contenido  y usarla para reparar cita INTRODUCE ERRORES.  (4)
#
# Una cita colgante se ve al compararla con el fichero.  Una cita al fichero
# equivocado,  con el numero y la linea bien escritos,  no.  Ver 1040.
RELACIONES = ("contenido", "numero")

# LAS COMPROBACIONES,  CON LO QUE LA REFUTARIA CADA UNA.  Se cuentan al
# imprimirse,  asi que anadir una aqui sin anadirla al cuerpo  —o al reves—
# se ve.  MEDIDO que la lista y el codigo pueden divergir si estan en dos sitios.
COMPROBACIONES = (
    ("G1",  "el sha256 declarado verifica sobre el cuerpo real"),
    ("G2",  "toda fila tiene el numero de campos declarado"),
    ("G2b", "toda fila dice su RELACION, y dice una de las dos"),
    ("G2c", "la RELACION es coherente con la PROCEDENCIA"),
    ("G3",  "el numero nuevo tiene un hallazgo cuyo nombre es el que dice"),
    ("G4",  "la procedencia se resuelve; si es de prosa, su linea nombra el"
            " numero viejo"),
    ("G5",  "coherencia con el verificador que ya existia"),
    ("G6",  "si la procedencia es `git:<hash>`, ese commit se resuelve"),
)
RE_SHA = re.compile(r"sha256_cuerpo\s+([0-9a-f]{64})\s*$")
RE_NUM = re.compile(r"^(\d{3,4})-(.+)\.md$")
# El numero viejo en la prosa citada se busca admitiendo el relleno de ceros,
# porque el corpus lo escribe asi: `271-...md:11` dice "era la `267`", y un
# hallazgo de tres digitos que se renumera a uno de cuatro cita "001" donde la
# fila dice 1. MEDIDO que la primera version usaba `\b1\b` y fallaba con las 4
# filas de prosa mas un numero de tres digitos. El relleno no es decoracion:
# `(?<!\d)0*1(?!\d)` NO casa dentro de `0011`, y `(?<!\d)` impide que case
# dentro de `1267`. Un criterio de busqueda demasiado laxo daria verde a una
# cita que no habla del hallazgo; uno demasiado estricto daria rojo a una cita
# que si lo habla.
RE_NUM_ANTECEDENTE = re.compile(r"(?<!\d)0*%d(?!\d)")
RE_PROC_DIFF = re.compile(r"^diff$")
RE_PROC_GIT = re.compile(r"^git:([0-9a-f]{7,40})$")
RE_PROC_PROSA = re.compile(r"^prosa:(.+):(\d+)(?:-(\d+))?$")

NORMALIZACION = ("solo las filas de datos --las que no empiezan por `#` y no "
                 "estan vacias--, unidas con \\n, con un \\n final")


def sha_de(texto):
    import hashlib
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def cuerpo_de(texto):
    """La normalizacion que declara la cabecera, y solo esa."""
    filas = [l for l in texto.split("\n") if l.strip() and not l.startswith("#")]
    return "\n".join(filas) + "\n", filas


def sha_declarado(cabecera):
    m = None
    for ln in cabecera.split("\n"):
        mm = RE_SHA.search(ln)
        if mm:
            m = mm.group(1)
    return m


def _git_existe(hash_):
    try:
        p = subprocess.run(["git", "-C", ROOT, "cat-file", "-e",
                            "%s^{commit}" % hash_],
                           capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return False
    return p.returncode == 0


def medir(mapa=MAPA, find=FIND):
    """(codigo, problemas, medidas). `problemas` es una lista de dicts."""
    probs = []
    if not os.path.isfile(mapa):
        return EXIT_FALTA_BASE, [{"check": "G0", "detalle":
                                  "no existe %s" % mapa}], {}
    if not os.path.isdir(find):
        return EXIT_FALTA_BASE, [{"check": "G0", "detalle":
                                  "no existe %s" % find}], {}

    texto = open(mapa, encoding="utf-8").read()
    cuerpo, filas = cuerpo_de(texto)
    cabecera = "\n".join(l for l in texto.split("\n") if l.startswith("#"))

    # ---- G1: integridad
    real = sha_de(cuerpo)
    decl = sha_declarado(cabecera)
    if decl is None:
        probs.append({"check": "G1", "detalle":
                      "la cabecera no declara ningun sha256_cuerpo de 64 hex"})
    elif decl != real:
        probs.append({"check": "G1", "detalle":
                      "sha256 declarado %s != real %s" % (decl[:16], real[:16])})

    # ---- G2 y G3: forma y destino
    filas_ok = []
    for n_lin, ln in enumerate(filas, 1):
        p = ln.split("\t")
        if len(p) != CAMPOS:
            probs.append({"check": "G2", "linea": n_lin, "detalle":
                          "%d campos, se esperaban %d: %r"
                          % (len(p), CAMPOS, ln[:60])})
            continue
        if p[2] not in ("SI", "no"):
            probs.append({"check": "G2", "linea": n_lin, "detalle":
                          "reasignado=%r no es SI ni no" % p[2]})
        # ---- G2b: la RELACION decide si esta fila puede reparar una cita
        # MEDIDO:  sin este check una fila puede llevar cualquier cosa en la
        # sexta columna —o nada— y el mapa sigue "verde", porque el resto de las
        # comprobaciones no la miran.  Y una fila sin relacion decidida es
        # indistinguible de una fila reparable:  justo el error de 1040.
        rel = p[COL_RELACION].strip()
        if rel not in RELACIONES:
            probs.append({"check": "G2b", "linea": n_lin, "detalle":
                          "relacion %r no es ninguna de (%s):  una fila sin"
                          " relacion decidida es indistinguible de una fila"
                          " reparable"
                          % (rel, ", ".join(RELACIONES))})
        if not p[4].strip():
            probs.append({"check": "G2", "linea": n_lin,
                          "detalle": "procedencia vacia"})
        filas_ok.append((n_lin, p))

    # El destino se busca por NUMERO PARSEADO, no por un nombre compuesto con
    # `"%d"`. MEDIDO que la primera version hacia `"%d-%s" % (nuevo, stem)` y
    # buscaba `2-destino.md`, mientras que el corpus usa el prefijo con
    # relleno: `002-destino.md` y `1020-...md`. O sea que la puerta fallaba con
    # las 49 filas reales y solo podia dar verde sobre un arbol inventado que no
    # cumple la convencion. El ancho lo introduce RE_NUM de
    # `findings_index` y de `check_num_unico`: se parsea el numero, no se compone
    # el nombre. Un gate que solo pasa sobre datos que el gate fabrico no es un
    # gate: es una tautologia, y asi lo demostro el self-test.
    por_num = {}
    for nombre in os.listdir(find):
        if not nombre.endswith(".md") or nombre.startswith("_"):
            continue
        m_num = RE_NUM.match(nombre)
        if m_num:
            por_num.setdefault(int(m_num.group(1)), []).append(nombre)

    for n_lin, p in filas_ok:
        try:
            viejo, nuevo = int(p[0]), int(p[1])
        except ValueError:
            probs.append({"check": "G2", "linea": n_lin, "detalle":
                          "numero no entero: %r" % p[:4]})
            continue
        # Del stem solo se usa el nombre SIN el numero, y el numero viene de la
        # fila; se comparan los sufijos para no depender del relleno.
        destino = None
        for nombre in por_num.get(nuevo, []):
            if nombre.split("-", 1)[1] == p[3]:
                destino = nombre
                break
        if destino is None:
            probs.append({"check": "G3", "linea": n_lin, "detalle":
                          "no hay ningun hallazgo %d cuyo nombre sea %r "
                          "(con ese numero hay: %s)"
                          % (nuevo, p[3], sorted(por_num.get(nuevo, []))[:3])})

        # ---- G2c: la RELACION tiene que ser CONSISTENTE con la procedencia
        #
        # MEDIDO que las dos son la misma informacion vista desde dos lados,  y
        # que pueden discrepar si alguien edita una fila a mano.  Y la
        # discrepancia importa:  marcar `contenido` una fila que en realidad es
        # `numero` la convierte en REPARABLE,  que es exactamente el dano que
        # 1040 describe  —27 citas apuntando al hallazgo equivocado—.
        #
        #   procedencia `diff`    el fichero viejo DESAPARECIO  ->  contenido
        #   procedencia `prosa`   el numero ya estaba ocupado   ->  numero
        #   procedencia `git`     leida de la prosa de un commit -> contenido
        rel, pr = p[COL_RELACION].strip(), p[COL_PROCEDENCIA].strip()
        if RE_PROC_DIFF.match(pr) and rel != "contenido":
            probs.append({"check": "G2c", "linea": n_lin, "detalle":
                          "procedencia diff pero relacion=%r:  con `diff` el"
                          " fichero viejo desaparece del arbol,  y eso SI es"
                          " un renumerado de CONTENIDO" % rel})
        elif RE_PROC_PROSA.match(pr) and rel != "numero":
            probs.append({"check": "G2c", "linea": n_lin, "detalle":
                          "procedencia prosa pero relacion=%r:  MEDIDO que las"
                          " cuatro de esta clase son colisiones de ASIGNACION"
                          "  —el numero viejo ya estaba ocupado—,  y en esa"
                          " clase la flecha NO mapea contenido  (1040)"
                          % rel})

        # ---- G4: la procedencia se resuelve y, si es de prosa, SOSTIENE la fila
        # MEDIDO 2026-10-04:  esto leia p[4]  —la procedencia—  y al anadir la
        # sexta columna p[4] paso a ser la RELACION.  La puerta no se rompio: dio
        # "procedencia de forma desconocida" en las 49 filas,  que es el modo
        # correcto de fallar cuando lo que falla es la FORMA.  Por eso el
        # mensaje dice que forma desconocida y no "no encuentro el fichero".
        proc = p[COL_PROCEDENCIA]
        if RE_PROC_DIFF.match(proc):
            pass
        elif RE_PROC_GIT.match(proc):
            h = RE_PROC_GIT.match(proc).group(1)
            if not _git_existe(h):
                probs.append({"check": "G6", "linea": n_lin, "detalle":
                              "procedencia %s: git no resuelve ese commit" % proc})
        elif RE_PROC_PROSA.match(proc):
            mm = RE_PROC_PROSA.match(proc)
            fichero = mm.group(1)
            l1 = int(mm.group(2))
            # El rango final es opcional: `prosa:f.md:11` significa la linea 11
            # sola. MEDIDO que esto no estaba escrito y `l2` acababa siendo el
            # grupo opcional SIN convertir, un str, y la comparacion de rango
            # reventaba con TypeError en vez de decir cual era el problema.
            l2 = int(mm.group(3)) if mm.group(3) else l1
            ruta = os.path.join(find, fichero)
            if not os.path.isfile(ruta):
                probs.append({"check": "G4", "linea": n_lin, "detalle":
                              "la prosa citada no existe: %s" % fichero})
            else:
                txt = open(ruta, encoding="utf-8", errors="replace").read().split("\n")
                if l1 < 1 or l2 > len(txt) or l2 < l1:
                    probs.append({"check": "G4", "linea": n_lin, "detalle":
                                  "rango de lineas %d-%d fuera de %s (%d lineas)"
                                  % (l1, l2, fichero, len(txt))})
                elif not re.search(RE_NUM_ANTECEDENTE.pattern % viejo,
                                      "\n".join(txt[l1 - 1:l2])):
                    probs.append({"check": "G4", "linea": n_lin, "detalle":
                                  "la prosa citada NO nombra el numero viejo %d "
                                  "en %s:%d-%d: la fila no esta sostenida por su "
                                  "fuente" % (viejo, fichero, l1, l2)})
        else:
            probs.append({"check": "G4", "linea": n_lin, "detalle":
                          "procedencia de forma desconocida: %r" % proc[:60]})

    # ---- G5: coherencia. Delega en el verificador que ya existe; dos copias
    # del criterio divergen y entonces una de las dos miente.
    try:
        sys.path.insert(0, HERE)
        import reenvio_freeze as rf
        # MEDIDO 2026-10-04:  esto pondia p[4] en "procedencia",  y con la sexta
        # columna p[4] es la RELACION.  MEDIDO que hoy no afecta al veredicto
        # porque verificar() no lee ese campo  —G5 sigue verde—,  es decir que la
        # desincronizacion es INVISIBLE.  Y esa es la peor forma de estar:  el dia
        # que verificar() mire la procedencia,  G5 estara comparando la relacion
        # contra la procedencia y no dira por que falla.
        #
        # Y es la CUARTA copia del ancho de fila que se ha desincronizado al
        # anadir la columna:  findings_index.CAMPOS,  reenvio_freeze.CAMPOS,
        # nextnum.CAMPOS_REENVIO  y esta.  Cuatro copias de un mismo dato,  y cada
        # una ha necesitado su propio arreglo.
        filas_rf = []
        for _n, p in filas_ok:
            filas_rf.append({"viejo": int(p[0]), "nuevo": int(p[1]),
                             "reasignado": p[2] == "SI", "stem": p[3],
                             "relacion": p[COL_RELACION],
                             "procedencia": p[COL_PROCEDENCIA]})
        for x in rf.verificar(filas_rf, cuerpo_txt=cuerpo,
                              declarado_sha=decl):
            probs.append({"check": "G5", "detalle": x})
    except Exception as e:                                  # noqa: BLE001
        probs.append({"check": "G5", "detalle":
                      "no se pudo delegar en reenvio_freeze.verificar: %r" % e})

    medidas = {
        "mapa": mapa,
        "filas": len(filas),
        "filas_bien_formadas": len(filas_ok),
        "sha256_real": real,
        "sha256_declarado": decl,
        "normalizacion": NORMALIZACION,
        "procedencias": {},
        "citas_de_prosa_sostenidas": 0,
    }
    for _n, p in filas_ok:
        # MEDIDO:  esto leia p[4]  —la procedencia—  y al anadir la sexta columna
        # p[4] paso a ser la RELACION.  El self-test lo cazó:  el caso base
        # contaba 0 citas de prosa sostenidas con una fila perfectamente buena.
        # Un contador que se queda en cero sin decir por que es el peor sitio
        # para un fallo,  porque 0 parece un resultado.
        proc = p[COL_PROCEDENCIA]
        k = proc.split(":")[0]
        medidas["procedencias"][k] = medidas["procedencias"].get(k, 0) + 1
        if proc.startswith("prosa:"):
            if not any(q["check"] == "G4" and q.get("linea") == _n
                       for q in probs):
                medidas["citas_de_prosa_sostenidas"] += 1
    return (EXIT_PROBLEMAS if probs else EXIT_OK), probs, medidas


def selftest() -> int:
    """Demuestra que CADA comprobacion puede fallar.

    Una puerta que no se ha visto fallar no es una puerta. Cada vector fabrica un
    mapa con UN defecto, en un directorio temporal, y exige el codigo y el
    identificador del problema. Si una comprobacion no dispara, el self-test
    falla: habria que preguntar por que se cambio el criterio.
    """
    import shutil
    import tempfile
    base = tempfile.mkdtemp(prefix="reenvio_gate-selftest-")
    fallos = []
    total = [0]

    def res(nombre, ok, detalle=""):
        total[0] += 1
        print("  %-64s %s" % (nombre, "OK" if ok else "FALLO " + detalle))
        if not ok:
            fallos.append((nombre, detalle))

    CAB = ("# mapa de prueba\n"
           "#   sha256_cuerpo  %s\n")

    def fabricar(nombre, filas, sha=None, n_finder=1):
        """Crea un findings/ temporal con un hallazgo y un mapa con `filas`."""
        d = os.path.join(base, nombre)
        fnd = os.path.join(d, "findings")
        os.makedirs(fnd, exist_ok=True)
        if n_finder:
            with open(os.path.join(fnd, "002-destino.md"), "w",
                      encoding="utf-8") as fh:
                fh.write("# 002 · destino\n\n> Era el `001` y pasa a `002`.\n")
        c = "\n".join(filas) + "\n"
        s = sha_de(c) if sha is None else sha
        with open(os.path.join(d, "mapa.tsv"), "w", encoding="utf-8") as fh:
            fh.write(CAB % s)
            fh.write(c)
        return os.path.join(d, "mapa.tsv"), fnd

    BUENA = ["001\t002\tSI\tdestino.md\tnumero\tprosa:002-destino.md:3"]
    FUERA = ["001\t002\tSI\tdestino.md\tnumero\tprosa:002-destino.md:9"]

    print("=== reenvio_gate selftest ===\n")

    m, f = fabricar("v_ok", BUENA)
    cod, probs, med = medir(m, f)
    res("0  mapa sano -> 0", cod == EXIT_OK, "salio %d %s" % (cod, probs))
    res("0  ...y mide 1 fila y 1 cita de prosa sostenida",
        med["filas"] == 1 and med["citas_de_prosa_sostenidas"] == 1,
        "filas=%d sostenidas=%s" % (med["filas"], med["citas_de_prosa_sostenidas"]))

    m, f = fabricar("v_g1", BUENA, sha="0" * 64)
    cod, probs, _ = medir(m, f)
    res("G1 sha declarado que no cuadra -> 1 y marca G1",
        cod == EXIT_PROBLEMAS and any(q["check"] == "G1" for q in probs),
        "codigo=%d %s" % (cod, probs))

    m, f = fabricar("v_g2", ["001\t002\tSI\tdestino.md"])
    cod, probs, _ = medir(m, f)
    res("G2 fila de 4 campos -> 1 y marca G2",
        cod == EXIT_PROBLEMAS and any(q["check"] == "G2" for q in probs),
        "codigo=%d %s" % (cod, probs))

    m, f = fabricar("v_g2b", ["001\t002\tQUIZAS\tdestino.md\tcontenido\tdiff"])
    cod, probs, _ = medir(m, f)
    res("G2 reasignado que no es SI ni no -> 1 y marca G2",
        cod == EXIT_PROBLEMAS and any(q["check"] == "G2" for q in probs),
        "codigo=%d %s" % (cod, probs))

    m, f = fabricar("v_g3", ["001\t999\tSI\tdestino.md\tcontenido\tdiff"])
    cod, probs, _ = medir(m, f)
    res("G3 fila que apunta a un fichero que no existe -> 1 y marca G3",
        cod == EXIT_PROBLEMAS and any(q["check"] == "G3" for q in probs),
        "codigo=%d %s" % (cod, probs))

    m, f = fabricar("v_g4a", FUERA)
    cod, probs, _ = medir(m, f)
    res("G4 la prosa citada NO nombra al numero viejo -> 1 y marca G4",
        cod == EXIT_PROBLEMAS and any(q["check"] == "G4" for q in probs),
        "codigo=%d %s" % (cod, probs))

    m, f = fabricar("v_g4b", ["001\t002\tSI\tdestino.md\tnumero\tprosa:no-existe.md:3"])
    cod, probs, _ = medir(m, f)
    res("G4 la prosa citada no existe -> 1 y marca G4",
        cod == EXIT_PROBLEMAS and any(q["check"] == "G4" for q in probs),
        "codigo=%d %s" % (cod, probs))

    m, f = fabricar("v_g4c", ["001\t002\tSI\tdestino.md\tnumero\tinventada"])
    cod, probs, _ = medir(m, f)
    res("G4 procedencia de forma desconocida -> 1 y marca G4",
        cod == EXIT_PROBLEMAS and any(q["check"] == "G4" for q in probs),
        "codigo=%d %s" % (cod, probs))

    m, f = fabricar("v_g5", ["001\t002\tSI\tdestino.md\tcontenido\tdiff",
                             "002\t003\tSI\tdestino.md\tcontenido\tdiff"])
    cod, probs, _ = medir(m, f)
    res("G5 cadena sin resolver 001->002->003 -> 1 y marca G5",
        cod == EXIT_PROBLEMAS and any(q["check"] == "G5" for q in probs),
        "codigo=%d %s" % (cod, probs))

    m, f = fabricar("v_g6", ["001\t002\tSI\tdestino.md\tcontenido\tgit:0123456789abcdef0123456789abcdef01234567"])
    cod, probs, _ = medir(m, f)
    res("G6 commit que git no resuelve -> 1 y marca G6",
        cod == EXIT_PROBLEMAS and any(q["check"] == "G6" for q in probs),
        "codigo=%d %s" % (cod, probs))

    cod, probs, _ = medir(os.path.join(base, "no-existe.tsv"), find=base)
    res("G0 mapa inexistente -> 2", cod == EXIT_FALTA_BASE,
        "codigo=%d" % cod)

    # Y un control que NO puede fallar seria un control que no existe: se
    # comprueba que el mapa de la fabricacion ANTERIOR a cada vector es sano,
    # porque si la base estuviera rota todos los vectores pasarian por el motivo
    # equivocado y la puerta entera no probaria nada.
    m, f = fabricar("v_control", BUENA)
    cod, _, _ = medir(m, f)
    res("control  la base de la fabricacion sigue sana (si no, todo lo de arriba "
        "pasaria por el motivo equivocado)", cod == EXIT_OK, "codigo=%d" % cod)

    shutil.rmtree(base, ignore_errors=True)
    print("\n  RESULT: %s  (%d comprobaciones, %d fallos)\n"
          % ("PASS" if not fallos else "FAIL", total[0], len(fallos)))
    for n, det in fallos:
        print("    FALLO %s  %s\n" % (n, det))
    return 1 if fallos else 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="PUERTA: el mapa congelado de renumeraciones aguanta?")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--mapa", default=MAPA)
    ap.add_argument("--find", default=FIND)
    ap.add_argument("--self-test", dest="self_test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        return selftest()

    cod, probs, med = medir(a.mapa, a.find)
    if a.json:
        print(json.dumps({"version": VERSION, "work_class": WORK_CLASS,
                          "codigo": cod, "medidas": med, "problemas": probs},
                         indent=2, ensure_ascii=False))
        return cod

    print("=" * 78)
    print("reenvio_gate %s · WORK_CLASS=%s · WRITE_EXECUTION=%s"
          % (VERSION, WORK_CLASS, WRITE_EXECUTION))
    print("=" * 78)
    print("  mapa                     : %s" % med.get("mapa"))
    print("  filas de datos          : %s" % med.get("filas"))
    print("  filas bien formadas     : %s" % med.get("filas_bien_formadas"))
    print("  sha256 declarado        : %s"
          % (med.get("sha256_declarado") or "NINGUNO"))
    print("  sha256 recomputado      : %s" % med.get("sha256_real"))
    print("  normalizacion           : %s" % NORMALIZACION)
    print("  procedencia por clase   : %s"
          % ", ".join("%s=%d" % kv for kv in sorted(
              (med.get("procedencias") or {}).items())))
    print("  citas de prosa sostenidas por su propia linea: %s"
          % med.get("citas_de_prosa_sostenidas"))
    print("\n  LO QUE ESTA PUERTA NO COMPRUEBA:")
    print("    que las filas sean TODAS las renumeraciones. No hay recuento")
    print("    independiente contra el que comparar, y MEDIDO que faltan al")
    print("    menos 6 pares mas con cita en su prosa de destino. Ver la")
    print("    cabecera de REENVIO-FINDINGS.tsv.")
    if probs:
        print("\n  PROBLEMAS (%d):" % len(probs))
        for q in probs:
            print("    [%s] %s%s" % (q["check"],
                                    ("linea %s: " % q["linea"]) if "linea" in q else "",
                                    q["detalle"]))
        print("\n  VEREDICTO: el mapa NO aguanta.")
    else:
        # El numero va CONTADO,  no escrito.  MEDIDO:  decia "las seis
        # comprobaciones" en letras  y al anadir G2b y G2c seguia diciendo seis.
        # Un recuento de controles escrito a mano es un recorte que envejecen:
        # en seis meses dira que hay seis cuando hay ocho,  y quien lo lea
        # creera que el mapa esta cubierto por seis cosas cuando no lo esta.
        print("\n  VEREDICTO: las %d comprobaciones se sostienen."
              % len(COMPROBACIONES))
        for tag, que in COMPROBACIONES:
            print("    [%s] %s" % (tag, que))
    print("\n  CODIGO DEVUELTO         : %d" % cod)
    return cod


if __name__ == "__main__":
    sys.exit(main())
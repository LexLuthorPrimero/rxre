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

  OCHO COMPROBACIONES, y cada una nombrando lo que la refutaria:

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
        MEDIDO que hoy se cumple en las 11 filas `prosa:`. Esta es la unica
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
    no existe un recuento independiente contra el que comparar. Lo que se sabe
    esta escrito, y es lo CONTRARIO de lo que decia la version 1.0.0: MEDIDO
    que los SEIS pares que esta version declaraba ausentes -- 272->274,
    280->288, 290->291, 998->1002, 1000->1004, 1003->1005 -- estan en el mapa
    desde 2026-10-04, cada uno con su cita en la prosa de su fichero de destino.
    El mapa tiene 56 filas.

    Y lo que queda fuera NO es "no lo he buscado".  MEDIDO que el par
    `290 -> 400`  es real y esta escrito con su cita en
    `400-el-resumen-y-el-aviso-tienen-vector.md:146-148`  --"Este hallazgo se
    iba a llamar `290` [...] habia dos filas con `290`: la mia y otra del otro
    agente. Renumeré la mia a `400`"—,  y que no puede entrar porque comparte
    ORIGEN con `290 -> 291`.  MEDIDO que ese veto es de
    `reenvio_freeze.verificar`  --"un MISMO origen con dos destinos si lo es"—
    y que en las filas de la clase `numero` ese criterio es un FALSO POSITIVO:
    un numeroazio confiado a dos contenidos y los dos renumerados despues es
    justamente lo que `numero` significa.  MEDIDO tambien que la declaracion de
    `400-...md:181`  --"Renumeré mis tres duplicados a `401`, `402` y `403`"—
    NO es fila y no puede serlo: nombra tres DESTINOS y ningun origen.

    Un mapa al que se le exigiera contener esas declaraciones tendria que
    inventarles un origen.

    Lo que esta puerta mide es mas estrecho y por eso puede ser cierto: que las
    56 filas que hay son 56 renumeraciones reales, cada una con su fichero y su
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

VERSION = "1.1.0"
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
    ("G2c", "la RELACION se deduce de la PROCEDENCIA, y no se supone: con"
             " `diff` y con `git:` el fichero se renombro,  con `prosa:` se"
             " comprueba que la cita nombre los DOS numeros  y que si la prosa"
             " atribuye el viejo a otro hallazgo  la relacion sea `numero`"),
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

# LAS FRASES DE OCUPACION,  Y POR QUE SON UNA LISTA CERRADA Y NO UN CONCEPTO
#
# MEDIDO 2026-10-04 que un criterio semantico sobre la prosa NO se puede
# escribir con un patron, y se intento antes de aceptar la lista.  La regla que
# parecia obvia --"si la cita menciona un fichero `NNN-...` que no es el
# destino, la relacion es `numero`"—  es FALSA, y la refuta 998 -> 1002:
# `999-...md:192-193` cita `998-correccion-a-105-no-hay-anillo-de-interrupcion-…`
# que NO es el destino `1002-correccion-a-105-el-1024-no-es-el-anillo-...`, y sin
# embargo esa fila es de CONTENIDO, porque aquel nombre viejo era ESTE
# contenido.  Separar "el nombre viejo de este" de "el nombre de otro" es
# LEER la prosa, no casar un patron.  MEDIDO tambien que la regla inversa no se
# sostiene:  `962-...md:60-62` y `947-...md:26-31` son `numero` y citan el
# fichero del otro agente, pero en `1005-...md:234-239`, que tambien es `numero`,
# el `1003-...` que aparece es el nombre viejo de ESTE documento.  O sea: el
# patron no separa las clases.  La prosa las separa, y una puerta de integridad
# no puede leer prosa.
#
# Lo que SI queda es una regla de UNA SOLA DIRECCION:  si la prosa ATRIBUYE el
# numero viejo a OTRO hallazgo, la fila TIENE que ser `numero`.  Es una
# contradiccion real, es el dano que 1040 describe, y no tiene falsos positivos
# conocidos:  una fila `contenido` cuya cita dijera "el NNN ya lo ocupaba otro"
# seria exactamente una fila que autoriza a reescribir citas que la prosa
# asigna a otra nota.  MEDIDO que cubre 5 de las 6 filas `numero` de
# procedencia `prosa`;  las que no cubre no quedan SIN comprobar, quedan sin
# ESTA comprobacion en particular, y el recuento sale en las medidas.
#
# Y una fila `contenido` cuya prosa NO atribuya el numero viejo a nadie no la
# convierte en reparable por decreto:  lo que la hace reparable es que la prosa
# diga que ESTE contenido paso de NNN a MMM, que es una lectura, y como lectura
# queda en la cabecera del mapa y en la fila, no en un patron.
RE_OCUPACION = re.compile(
    r"ya (?:usaba|usaban|tenia|tenían|tenia|lo ocupaba|la ocupaba)"
    r"|qued[oó] ocupad[oa]"
    r"|ocupad[oa] por otr[oa]",
    re.IGNORECASE)

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


def _git(repo, *args):
    try:
        return subprocess.run(["git", "-C", repo] + list(args),
                              capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None


def _git_existe(hash_, repo=ROOT):
    p = _git(repo, "cat-file", "-e", "%s^{commit}" % hash_)
    return bool(p is not None and p.returncode == 0)


def _mismo_stem(a, b):
    """Los dos nombres de unFindings, SIN numero y con la regla de PREFIJO.

    `reenvios()` entrega el stem truncado a 58 caracteres y el nombre real del
    arbol no lo esta, asi que el mismo documento aparece con dos anchos. MEDIDO
    que comparar con igualdad deja pasar la fila y con igualdad estricta la
    puerta de rojo sobre una fila correcta: el truncado no afirma nada que el
    nombre completo no afirme.
    """
    return a == b or a.startswith(b) or b.startswith(a)


def _nombre_de(num, stem):
    """Como lo escribe el corpus: 3 digitos por debajo de 1000, 4 a partir de ahi.

    MEDIDO que el mensaje de G2c decia `1-destino.md` donde el fichero se llama
    `001-destino.md`,  y un mensaje que nombra un fichero que no existe hace
    perder el rato a quien lo lee buscando el fichero en vez de la fila.
    """
    return "%d-%s.md" % (num if num >= 1000 else int("%03d" % num), stem)


def _git_renombra(hash_, viejo, nuevo, stem, repo=ROOT):
    """(True, "") si el commit renombra `viejo-stem.md` a `nuevo-stem.md`.

    MEDIDO por que esto SUBE y no baja el listón:  antes, una fila `git:<hash>`
    solo se comprobaba con que git resolviera el commit —G6—, y eso no dice nada
    del par.  Si el commit renombra de verdad, entonces el CONTENIDO pasó del
    numero viejo al nuevo, y la relacion es `contenido` por derivacion y no por
    costumbre.  Devuelve (False, motivo) con el motivo escrito, porque un veto
    sin motivo es un veto que hay que volver a Runs para entender.
    """
    p = _git(repo, "show", "--name-status", "--format=", hash_)
    if p is None:
        return False, "git no se pudo ejecutar"
    if p.returncode != 0:
        return False, "git show %s sale %d" % (hash_, p.returncode)
    for ln in p.stdout.split("\n"):
        partes = ln.split("\t")
        if len(partes) != 3 or not partes[0].startswith("R"):
            continue
        a = os.path.basename(partes[1])
        b = os.path.basename(partes[2])
        m_a, m_b = RE_NUM.match(a), RE_NUM.match(b)
        if not (m_a and m_b):
            continue
        if (int(m_a.group(1)) == viejo and int(m_b.group(1)) == nuevo
                and _mismo_stem(m_a.group(2) + ".md", stem)
                and _mismo_stem(m_b.group(2) + ".md", stem)):
            return True, ""
    return False, ("el commit %s no renombra %s a %s;  con una"
                   " procedencia `git:` eso es lo unico que prueba `contenido`"
                   % (hash_, _nombre_de(viejo, stem), _nombre_de(nuevo, stem)))


def medir(mapa=MAPA, find=FIND, repo=ROOT):
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
    # MEDIDO 2026-10-04:  un recorte de G2c que no se puede ver es un recorte
    # que no existe.  G2c(b) solo puede cubrir las filas `prosa` cuya prosa
    # ATRIBUYE el numero viejo a otro hallazgo,  y eso no son todas:  asi que se
    # cuenta cuantas cubre y se imprime.  Una cobertura del 100% escrita en la
    # cabecera envellece;  el numero medido sale solo.
    cuota_numero = [0]
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

        # ---- G2c: la RELACION tiene que ser DERIVABLE, no heredada
        #
        # MEDIDO 2026-10-04 que esta comprobacion decia una cosa que ya no es
        # cierta.  Decia:  `prosa` implica `numero`.  Es la regla que hizo que un
        # nodo anterior marcara `numero` por el PREFIJO DEL FICHERO y no por lo
        # que la prosa dice, y es FALSA:  la fila `998 -> 1002` es de
        # procedencia `prosa:` y es de CONTENIDO, porque la prosa no dice que el
        # 998 lo ocupara nadie — dice que un fichero que estaba en el 998 fue
        # renumerado a 1002, y ese fichero es el que ahora es el 1002.  Medida
        # con la puerta en la version 1.0.0 sobre el mapa con las siete filas
        # anadidas:  [G2c] linea 53, una sola, y es la que describe el
        # renumerado.  Y el dano de la regla no era teorico:  `refs_repair.py`
        # usa `relacion == "contenido"` para decidir si reescribe una cita, asi
        # que `numero` puesto por el prefijo retira reparaciones que si valen y
        # `contenido` puesto por el prefijo las concede que no valen.
        #
        # Lo que se conserva es lo DERIVABLE, y se cambia lo que no lo era:
        #   `diff`   el fichero viejo desaparece del arbol  ->  contenido
        #   `git:`   el commit renombra de verdad             ->  contenido
        #   `prosa:` no se deduce nada del prefijo.  Lo que se comprueba es:
        #     (a) la cita nombra los DOS extremos del par, no solo el viejo.  Una
        #         fila de renumerado cuya cita no dice cual es el numero nuevo
        #         no esta sostenida por su fuente, y con G4 sola no se notaba:
        #         G4 exige el viejo y el nuevo se leia de la fila, o sea que la
        #         fila se sostenia a si misma.
        #     (b) si la prosa ATRIBUYE el viejo a otro hallazgo, `numero`.
        rel, pr = p[COL_RELACION].strip(), p[COL_PROCEDENCIA].strip()
        if RE_PROC_DIFF.match(pr) and rel != "contenido":
            probs.append({"check": "G2c", "linea": n_lin, "detalle":
                          "procedencia diff pero relacion=%r:  con `diff` el"
                          " fichero viejo desaparece del arbol,  y eso SI es"
                          " un renumerado de CONTENIDO" % rel})
        elif RE_PROC_GIT.match(pr):
            if rel != "contenido":
                probs.append({"check": "G2c", "linea": n_lin, "detalle":
                              "procedencia %s pero relacion=%r:  un RENAME de"
                              " git mueve el CONTENIDO con el nombre,  y eso"
                              " solo puede ser `contenido`" % (pr, rel)})
            else:
                ok, por_que = _git_renombra(RE_PROC_GIT.match(pr).group(1),
                                            viejo, nuevo, p[3], repo)
                if not ok:
                    probs.append({"check": "G2c", "linea": n_lin, "detalle":
                                  "procedencia %s:  %s" % (pr, por_que)})

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
            if not _git_existe(h, repo):
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
                else:
                    cita = "\n".join(txt[l1 - 1:l2])
                    if not re.search(RE_NUM_ANTECEDENTE.pattern % viejo, cita):
                        probs.append({"check": "G4", "linea": n_lin, "detalle":
                                      "la prosa citada NO nombra el numero viejo %d "
                                      "en %s:%d-%d: la fila no esta sostenida por su "
                                      "fuente" % (viejo, fichero, l1, l2)})
                    # ---- G2c(a): la cita nombra tambien el numero NUEVO
                    #
                    # MEDIDO por que esto no es una quinta comprobacion de G4:  G4
                    # mira el viejo, que es el unico numero que la fila puede
                    # copiar de la cita sin circular.  El nuevo NO:  sale de la
                    # propia fila, asi que sin esto una fila puede citar una
                    # linea que habla de otro renumerado y aun asiESTAMPAR bien
                    # los dos campos.
                    if not re.search(RE_NUM_ANTECEDENTE.pattern % nuevo, cita):
                        probs.append({"check": "G2c", "linea": n_lin, "detalle":
                                      "la prosa citada nombra %d pero NO el numero"
                                      " nuevo %d en %s:%d-%d:  una fila de"
                                      " renumerado que no dice adonde va no esta"
                                      " sostenida por su fuente"
                                      % (viejo, nuevo, fichero, l1, l2)})
                    # ---- G2c(b): si la prosa atribuye el viejo a OTRO, `numero`
                    #
                    # MEDIDO que esto cubre 5 de las 6 filas `numero` de
                    # procedencia `prosa`.  La que no cubre es 1003 -> 1005, y
                    # no se cubre porque su prosa no usa ninguna de las frases
                    # de ocupacion —dice "dos autores eligen el mismo"—.  Anadir
                    # esa frase al patron estaria AUTHORIZANDO al patron a decidir
                    # de que clase es cada fila, que es lo que se acaba de
                    # quitar.
                    elif RE_OCUPACION.search(cita):
                        if rel != "numero":
                            probs.append({"check": "G2c", "linea": n_lin,
                                          "detalle":
                                          "la prosa citada ATRIBUYE el numero"
                                          " viejo %d a otro hallazgo (%s:%d-%d),"
                                          " asi que la relacion TIENE que ser"
                                          " `numero` y no %r:  marcarla reparable"
                                          " concede a refs_repair reescribir"
                                          " citas que la prosa asigna a otra nota"
                                          " —el dano de 1040"
                                          % (viejo, fichero, l1, l2, rel)})
                        else:
                            cuota_numero[0] += 1
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
        "prosa_con_ocupacion_atribuida": cuota_numero[0],
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

    # ---- Un repositorio git TEMPORAL,  y por que
    #
    # MEDIDO 2026-10-04 que G2c NO TENIA NI UN VECTOR:  la puerta afirmaba tres
    # reglas  —diff implica contenido,  git implica contenido,  prosa implica
    # numero— y el self-test no sabia hacer fallar ninguna.  Una comprobacion
    # que no se ha visto fallar no es una comprobacion:  es un comentario.  Y
    # para que git pueda refutar la rama de `git:`  hace falta un repo que
    # responder.  MEDIDO que REUSAR los commits del propio proyecto ataria el
    # self-test a una historia que se puede reescribir:  si alguien reescribe
    # `a75060397058f`  el self-test empezaria a fallar por una causa que no es
    # la que prueba.  Un repo de un minuto en el tempdir,  con un commit que
    # renombra y otro que no,  no depende de nada de fuera.
    def repo_renombrante(d, nombre="repo"):
        """(repo, hash_del_commit_que_NO_renombra, hash_del_que_SI).

        MEDIDO que el orden importa y que se confunde:  con los dos nombres
        cambiados los vectores pasan por el motivo equivocado —el que renombra
        parece el que no renombra— y la puerta entera no prueba nada.  Por eso
        el orden va escrito en el docstring y no solo en el codigo.
        """
        r = os.path.join(d, nombre)
        os.makedirs(r, exist_ok=True)
        env_c = ["-c", "user.email=t@t", "-c", "user.name=t",
                 "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false"]
        run = lambda *a: subprocess.run(["git", "-C", r] + env_c + list(a),
                                         capture_output=True, text=True,
                                         timeout=60, check=True)
        with open(os.path.join(r, "001-destino.md"), "w", encoding="utf-8") as fh:
            fh.write("viejo\n")
        run("init", "-q")
        run("add", "-A")
        run("commit", "-q", "-m", "el viejo")
        h1 = subprocess.run(["git", "-C", r, "rev-parse", "HEAD"],
                            capture_output=True, text=True,
                            timeout=60).stdout.strip()
        run("mv", "001-destino.md", "002-destino.md")
        run("commit", "-q", "-m", "el renumerado")
        h2 = subprocess.run(["git", "-C", r, "rev-parse", "HEAD"],
                            capture_output=True, text=True,
                            timeout=60).stdout.strip()
        return r, h1, h2

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

    # ---- G2c: las tres ramas, una por una.  MEDIDO que antes no habia ninguna.
    m, f = fabricar("v_g2c_diff", ["001\t002\tSI\tdestino.md\tnumero\tdiff"])
    cod, probs, _ = medir(m, f)
    res("G2c diff con relacion=numero -> 1 y marca G2c",
        cod == EXIT_PROBLEMAS and any(q["check"] == "G2c" for q in probs),
        "codigo=%d %s" % (cod, probs))

    # G2c(b): la prosa ATRIBUYE el viejo a otro hallazgo, y la fila se marca
    # reparable.  Este es el dano del hallazgo 1040 en un vector.
    m, f = fabricar("v_g2c_prosa_ocup",
                    ["001\t002\tSI\tdestino.md\tcontenido\tprosa:002-destino.md:3"])
    with open(os.path.join(f, "002-destino.md"), "w", encoding="utf-8") as fh:
        fh.write("# 002 · destino\n\n> Era el `001`, que ya lo ocupaba"
                 " `001-otro.md`, y pasa a `002`.\n")
    cod, probs, _ = medir(m, f)
    res("G2c prosa que atribuye el viejo a otro y relacion=contenido -> 1 y G2c",
        cod == EXIT_PROBLEMAS and any(q["check"] == "G2c" for q in probs),
        "codigo=%d %s" % (cod, probs))
    # Y el mismo caso con la relacion correcta tiene que pasar: un vector que
    # solo sabe fallar no distingue "la puerta funciona" de "la puerta odia".
    m2, f2 = fabricar("v_g2c_prosa_ocup_ok",
                      ["001\t002\tSI\tdestino.md\tnumero\tprosa:002-destino.md:3"])
    with open(os.path.join(f2, "002-destino.md"), "w", encoding="utf-8") as fh:
        fh.write("# 002 · destino\n\n> Era el `001`, que ya lo ocupaba"
                 " `001-otro.md`, y pasa a `002`.\n")
    cod, probs, med = medir(m2, f2)
    res("G2c ...y el mismo caso con `numero` -> 0",
        cod == EXIT_OK, "codigo=%d %s" % (cod, probs))
    res("G2c ...y esa fila cuenta como ocupacion atribuida (1)",
        med.get("prosa_con_ocupacion_atribuida") == 1,
        "medida=%s" % med.get("prosa_con_ocupacion_atribuida"))

    # G2c(a): la cita nombra el viejo pero NO el nuevo.  G4 solo miraba el viejo,
    # asi que este caso pasaba antes:  la fila se sostenia a si misma.
    m, f = fabricar("v_g2c_prosa_sin_nuevo", BUENA)
    with open(os.path.join(f, "002-destino.md"), "w", encoding="utf-8") as fh:
        fh.write("# 002 · destino\n\n> Era el `001` y se queda donde esta.\n")
    cod, probs, _ = medir(m, f)
    res("G2c cita que nombra el viejo y no el nuevo -> 1 y marca G2c",
        cod == EXIT_PROBLEMAS and any(q["check"] == "G2c" for q in probs),
        "codigo=%d %s" % (cod, probs))

    # Y el caso `contenido` + `prosa` que la version 1.0.0 declaraba IMPOSIBLE y
    # que el mapa real contiene desde 2026-10-04:  la prosa no atribuye el numero
    # viejo a nadie,  y aun asi la fila es de contenido.  Si este vector se
    # rompe,  la puerta ha vuelto a suponer la clase por el prefijo del fichero.
    m, f = fabricar("v_g2c_prosa_contenido",
                    ["001\t002\tSI\tdestino.md\tcontenido\tprosa:002-destino.md:3"])
    with open(os.path.join(f, "002-destino.md"), "w", encoding="utf-8") as fh:
        fh.write("# 002 · destino\n\n>Habia un `001-antes.md` y lo renumeraron"
                 " a `002-destino.md`.\n")
    cod, probs, _ = medir(m, f)
    res("G2c `contenido` con `prosa:` que NO atribuye el viejo a nadie -> 0",
        cod == EXIT_OK, "codigo=%d %s" % (cod, probs))

    # G2c rama `git:`: el commit TIENE que renombrar el par, no solo resolver.
    d = os.path.join(base, "v_g2c_git")
    os.makedirs(d, exist_ok=True)
    repo, h_sin_renombrar, h_renombrado = repo_renombrante(d)
    m, f = fabricar("v_g2c_git",
                    ["001\t002\tSI\tdestino.md\tcontenido\tgit:%s" % h_renombrado])
    cod, probs, _ = medir(m, f, repo=repo)
    res("G2c git cuyo commit renombra el par -> 0",
        cod == EXIT_OK, "codigo=%d %s" % (cod, probs))
    m, f = fabricar("v_g2c_git_norenombra",
                    ["001\t002\tSI\tdestino.md\tcontenido\tgit:%s"
                     % h_sin_renombrar])
    cod, probs, _ = medir(m, f, repo=repo)
    res("G2c git que resuelve pero NO renombra el par -> 1 y marca G2c",
        cod == EXIT_PROBLEMAS and any(q["check"] == "G2c" for q in probs),
        "codigo=%d %s" % (cod, probs))
    m, f = fabricar("v_g2c_git_numero",
                   ["001\t002\tSI\tdestino.md\tnumero\tgit:%s" % h_renombrado])
    cod, probs, _ = medir(m, f, repo=repo)
    res("G2c git con relacion=numero -> 1 y marca G2c",
        cod == EXIT_PROBLEMAS and any(q["check"] == "G2c" for q in probs),
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
    print("  de esas, las que la prosa ATRIBUYE a otro hallazgo y por lo tanto"
          " fuerzan `numero`: %s" % med.get("prosa_con_ocupacion_atribuida"))
    print("\n  LO QUE ESTA PUERTA NO COMPRUEBA:")
    print("    que las filas sean TODAS las renumeraciones. No hay recuento")
    print("    independiente contra el que comparar. MEDIDO que los 6 pares")
    print("    que se declaraban ausentes estan dentro desde 2026-10-04, y que")
    print("    `290 -> 400` es real pero no cabe: comparte origen con")
    print("    `290 -> 291`. Ver la cabecera de REENVIO-FINDINGS.tsv.")
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
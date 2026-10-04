#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""
sello_prov.py - cada numero de un bloque de procedencia, o se recalcula, o no
                es un numero.

POR QUE EXISTE

Un bloque de procedencia es lo que permite a un tercero NO tener que creerse el
documento. En este proyecto esa forma esta escrita en decenas de cabeceras:

    herramienta   tools/riesgo.py 1.0.0
    sha256        dd4fc3c5413e4519
    artefacto     08-ARQUITECTURA/artifacts/R1-RIESGO/riesgo.json
    sha256        64f6b04f0640f029
    reproducible  bccfae31267d843c27f11cb7208e0071774f1f838f5991bcc2655e4b757b6d38

De esos cinco campos, tres se comprueban con una orden (`sha256sum <fichero>`).
El quinto, `reproducible`, tambien -- pero hace falta saber la receta, y la
receta no estaba escrita en ningun sitio del proyecto. MEDIDO: el valor
declarado es `sha256(json.dumps(artefacto sin la clave volatil "generado",
sort_keys=True))`, con los separadores por defecto de Python. MEDIDO 3 de 3.

Que no estuviera escrita es un defecto pequeno pero real, y es el que justifica
esta herramienta: un campo correcto y no documentado se puede copiar, comparar
y confrontar, y no se puede *comprobar*. La diferencia entre las dos cosas es
justo la que separa un dato de una garantia.

QUE HACE

  sello_prov.py FICHERO...   audita los bloques de procedencia de esos ficheros
  sello_prov.py --arbol DIR  audita todos los .md de un arbol
  sello_prov.py --json       lo mismo, estructurado
  sello_prov.py --selftest   vectores en un arbol temporal, sin leer el proyecto

Cada campo declarado se clasifica en uno de estos seis veredictos:

  EXISTE      un campo que nombra un fichero, y el fichero esta. NO es un
              cotejo de valor: es una comprobacion de existencia. Se separa de
              COINCIDE porque "el fichero que citas existe" y "la suma que
              declaras es la suma de ese fichero" son dos cosas, y juntarlas
              haria que un recuento de COINCIDE unread sobre lo que se ha
              medido de verdad
  COINCIDE    un valor declarado, recalculado con su receta, y es igual
  DIFIERE     un valor declarado, recalculado con su receta, y es otro
  SIN_RECETA  declarado, y no hay ninguna receta conocida para calcularlo.
              Solo puede salir para un hash SIN portador: un hash suelto que no
              dice contra que fichero va
  ROTO        con receta, pero el fichero objetivo no existe o no se lee
  MALFORMADO  la linea no se entiende (hash sin objetivo, version invalida)

LO QUE ESTA FUERA DE ALCANCE, Y POR QUE

No decide si un hash *deberia* ser el que es. Solo decide si se puede
comprobar. La diferencia es la misma que separa `sello.py` de un detector de
cambios: `sello.py` mide MOVIDO y ROTO y se niega a re-sellar, y esta
herramienta se niega a inventar la receta de un campo que no la tiene. Anadir
la receta es trabajo de quien escribe el bloque, y hacerlo aqui seria
justamente el fallo que denuncia: una puerta que Arregla el numero que deberia
auditar.

Tampoco audita el CONTENIDO de los ficheros citados, solo su existencia y su
suma. Y `sha256` aqui es sha256 de BYTES del fichero: no dice nada de si el
fichero es el que el documento dice que es.

CODIGOS DE SALIDA

  0  todos los campos tienen receta y coinciden
  1  no se encontro ningun bloque de procedencia en el alcance dado
  2  error de uso o de parseo (viga sin cerrar, fichero ilegible)
  3  hay al menos un campo SIN_RECETA
  4  hay al menos un DIFIERE o un ROTO

El 1 existe y es separado del 0 a proposito: una puerta que sale con 0 porque
no ha encontrado nada que auditar es la clase de defecto que este proyecto
mide una y otra vez. "No he mirado" y "he mirado y esta bien" no son el mismo
codigo de salida.
"""

import argparse
import hashlib
import json
import os
import re
import sys

VERSION = "1.1.0"

# ---------------------------------------------------------------------------
# LA RECETA DE `reproducible`
# MEDIDO 3 de 3 sobre R1-RIESGO, R2-PM4OPS y R3-DWARFX: el valor declarado es
#
#     sha256( json.dumps( json_del_artefacto_sin_claves_volatiles , sort_keys=True ) )
#
# con los SEPARADORES POR DEFECTO de Python (", " y ": ") y codificacion UTF-8,
# sin salto de linea final.
#
# Que seDefined asi tiene una consecuencia util y por eso esta escrita con
# cuidado: quitar las claves volatiles es lo que hace que el hash sobreviva a
# regenerar el artefacto en otro momento del reloj. `generado` es la unica
# clave volatil medida en el arbol. Si aparece otra, la lista se amplia AQUI y
# en ningun otro sitio, porque una lista repartida por tres herramientas es
# una lista que se contradice.
#
# POR QUE ESTA EN CODIGO Y NO EN EL DOCUMENTO
#
# Porque el documento es lo que hay que auditar, y un campo cuya receta solo
# existe en la cabeza de quien lo escribio no es auditable: se puede copiar,
# comparar y confrontar, y no se puede comprobar. La receta va aqui, que es
# donde un tercero la puede ejecutar.
# ---------------------------------------------------------------------------
CLAVES_VOLATILES = {"generado"}

# LAS TRES FORMAS, Y POR QUE ESTA ES LA QUE VALE
#
# El selftest necesita un oraculo que NO sea la funcion bajo prueba. MEDIDO: un
# vector que calculaba el valor esperado llamando a `receta_reproducible` pasa
# con 0 fallos aunque la receta use los separadores COMPACTOS, que es
# justamente la forma que no reproduce los artefactos reales. Mutacion
# comprobada: 0 de 37 vectores la detectan. Un oraculo que llama al codigo que
# prueba no es un oraculo: es una tautologia, y es el mismo defecto que audita
# este fichero, un nivel mas adentro.
#
# Por eso el valor bueno esta escrito aqui como CONSTANTE, calculada fuera, y
# las tres formas estan escritas para que una equivocacion no pueda colarse
# por_el flanco de "las tres dan lo mismo".
REPRO_MUESTRA_DEFECTO = "40a7f3efa39c9fa5542176cee4ed71f1a60966e2890af54d860ca467315cac9f"
REPRO_MUESTRA_COMPACTO = "c4dc1e4c916883099ea241915145987e727737862d27882c1a24ce3f0bc86dc9"
REPRO_MUESTRA_INDENT = "c0667bb308f6519547ea265b1a4e737307c5a2c42be918f5fc98af966382faa7"

RECETA_REPRODUCIBLE = ("sha256(json.dumps(json sin %s, sort_keys=True)) "
                       "con separadores por defecto"
                       % ", ".join(sorted(CLAVES_VOLATILES)))


def receta_reproducible(path):
    """La suma que declara el campo `reproducible`. None si no aplica."""
    try:
        with open(path, "rb") as f:
            bruto = f.read()
        d = json.loads(bruto.decode("utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    if not isinstance(d, dict):
        return None
    for k in CLAVES_VOLATILES:
        d.pop(k, None)
    return hashlib.sha256(
        json.dumps(d, sort_keys=True).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# VOCABULARIO
#
# Declarado, no deducido, por la misma razon que en sello.py: cada exclusion
# es una decision y por eso esta en codigo. Un campo que no esta aqui NO es un
# campo de procedencia, se ignora, y el self-test lo comprueba.
#
# `portador` son los campos que nombran un fichero: un `sha256` que sigue a
# uno de estos se le atribuye. Un `sha256` que NO sigue a ninguno es
# MALFORMADO, porque no tiene objetivo -- que es un fallo distinto de "no se
# como recalcularlo" y no debereportarse como el mismo problema.
# ---------------------------------------------------------------------------
CAMPOS = {
    "herramienta": "portador",
    "artefacto": "portador",
    "fuente": "portador",
    "script": "portador",
    # MEDIDO por adversarial-reviewer: el hallazgo 970 usa `TOOL=path digest` en
    # la misma linea, con el path DENTRO del valor de `sha256`. Mi primera
    # version reconocia la clave y luego fallaba al buscar un portador hacia
    # atras, y el resultado era que de ese bloque no salia NADA: no un veredicto
    # malo, sino silencio. El silencio es el peor de los tres resultados
    # posibles, porque un campo que no se reporta parece un campo que no existe.
    # El digest de 970 es CORRECTO; lo que estaba mal era el path en la prosa,
    # que apunta a tools/ cuando el fichero esta en 08-ARQUITECTURA/tools/.
    "TOOL": "portador",
    "sha256": "suma",
    "reproducible": "suma",
    "Regenerar": "receta",
    "selftest": "prosa",
}

RE_HEX = re.compile(r"^[0-9a-f]{8,64}$")
RE_VERSION = re.compile(r"^\d+\.\d+(\.\d+)?$")


def sha256_de(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def lee_bloques(texto, ruta):
    """
    Devuelve (bloques, parcial).

    `bloques` son las vallas CERRADAS encontradas. `parcial` es None si el
    documento se cierra entero, o (linea, n_backticks) si queda una valla abierta.

    DOS COSAS QUE LA PRIMERA VERSION HACIA MAL

    1. CONTABA CUALQUIER VISTA DE 3 BACKTICKS COMO VALLA, Y NO ES CIERTO. Una
       valla de N backticks se cierra con otra de N o mas. MEDIDO: promp.md tiene
       2 vallas de 4 backticks, mi emparejador las mezclaba con las de 3 y
       declaraba el documento entero ilegible. Un fichero que usa vallas de 4 es
       legal y yo lo rechazaba por no saber contarlas.

    2. TIRABA EL DOCUMENTO ENTERO SI UNA VALLA SE QUEDABA ABIERTA. MEDIDO: 6
       documentos, uno con 403 vallas y la ultima sin cerrar en la 5180. Los
       bloques de las 402 anteriores son validos y los estaba tirando. Eso
       convierte un defecto de REDACCION de un documento en un hueco de
       OBSERVABILIDAD sobre el documento entero.

    Por eso aqui no se aborta: se devuelve lo que se ha cerrado y se marca el
    documento como PARCIAL, para que quien lo lea sepa que su censo no es
    completo. Es la misma politica que ya se aplicaba a los ficheros ilegibles:
    no se tira lo que se puede leer, y se dice lo que falta.
    """
    bloques = []
    dentro = False
    actual = []
    abre = None
    n_abre = 0
    for n, ln in enumerate(texto.split("\n"), 1):
        s = ln.lstrip()
        if s.startswith("```"):
            n_back = len(s) - len(s.lstrip("`"))
            if not dentro:
                dentro = True
                abre = n
                n_abre = n_back
                actual = []
            elif n_back >= n_abre:
                dentro = False
                bloques.append((abre, actual))
                actual = []
            continue
        if dentro:
            actual.append((n, ln))
    if dentro:
        return bloques, (abre, n_abre)
    return bloques, None


def parsea_bloque(lineas, raiz, ruta):
    """
    Convierte las lineas de una viga en una lista de campos.

    Solo lineas con forma `clave<espacios>valor`. El separador son DOS o mas
    espacios, que es lo que usan las cabeceras de este proyecto en columna; un
    espacio simple no es separador porque `reproducible <hex>` en prosa suelta
    no es un campo.

    HAY DOS ORDENES EN EL ARBOL, Y AMBOS SON REALES:

      (a) portador primero -- las cabeceras de R1/R2/R3
              herramienta   tools/riesgo.py 1.0.0
              sha256        dd4fc3c5413e4519

      (b) hash primero y fichero en la linea de continuacion -- findings/ y el
          informe del decodificador
              sha256  d784bb1638bf99b554b5fc31e358689080b8ed2ba3d1754492381c39aa7e0e23
                      04-IMPLEMENTACION/rx550-driver/rx550_gart_write.c

    Los dos se resuelven en `portador_de_continuacion`, que es donde esta escrito
    por que la primera version solo miraba hacia atras y por que eso salio
    carisimo.
    """
    campos = []
    for n, ln in lineas:
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z][A-Za-z0-9_-]*)\s{2,}(\S.*?)\s*$", ln)
        if not m:
            continue
        clave, valor = m.group(1), m.group(2)
        tipo = CAMPOS.get(clave)
        if tipo is None:
            continue
        campos.append({"n": n, "clave": clave, "valor": valor, "tipo": tipo})
    if not campos:
        return None

    portador = None
    for c in campos:
        if c["tipo"] == "portador":
            partes = c["valor"].split()
            c["ruta"] = partes[0]
            c["version"] = partes[1] if len(partes) > 1 else None
            portador = c
        elif c["tipo"] == "suma":
            c["portador"] = portador["ruta"] if portador else None
            if c["portador"] is None:
                c["portador"] = portador_de_continuacion(c, lineas)
    marca_ambiguedad(campos)
    return campos


def portador_de_continuacion(campo, lineas):
    """
    El nombre del fichero puede venir en la lineA DE CONTINUACION, no antes.

    MEDIDO: al censar el arbol entero, la primera version de esta herramienta
    reportaba 15 `SIN_RECETA` en findings/ y en el informe del decodificador,
    y los 15 eran hashes PERFECTAMENTE auditables. Ninguno era un defecto de
    esos documentos: era un defecto mio, que solo miraba hacia atras. Un
    instrumento que fabrica 15 hallazgos falsos consume el mismo tiempo y la
    misma atencion que uno real, y hace que se ignore el canal.

    La forma (b), que es la que existe en el arbol:

        sha256  d784bb1638bf99b554b5fc31e358689080b8ed2ba3d1754492381c39aa7e0e23
                04-IMPLEMENTACION/rx550-driver/rx550_gart_write.c

    La continuacion puede traer detras cosas que NO son el nombre -- "60399 B,
    1951 lineas" -- y por eso el path es el primer token de la linea.

    Devuelve None si no hay continuacion que parezca un path: en ese caso el
    `sha256` se queda SIN_RECETA, que es el veredicto correcto para un hash
    que de verdad no dice contra que fichero va.
    """
    for m2, l2 in lineas:
        if m2 <= campo["n"]:
            continue
        # Solo la primera linea no vacia de continuation.
        if not l2.strip():
            continue
        if not l2[:1].isspace():
            return None          # la siguiente linea no es continuacion
        tok = l2.strip().split()[0]
        if "/" in tok or re.search(r"\.(py|c|h|md|json|sh|txt|rs|cfg)$", tok):
            return tok
        return None
    return None


def version_real(ruta_abs):
    """VERSION declarada por el fichero, o None si no se puede saber."""
    try:
        with open(ruta_abs, "r", errors="replace") as f:
            texto = f.read()
    except OSError:
        return None
    m = re.search(r'^VERSION\s*=\s*["\']([^"\']+)["\']', texto, re.M)
    return m.group(1) if m else None


def audita_campo(c, raiz, ruta_rel):
    """Clasifica un campo. Devuelve un dict con veredicto y motivo."""
    clave, valor = c["clave"], c["valor"]
    out = {"campo": clave, "valor": valor, "linea": c["n"]}

    if clave in ("Regenerar", "selftest", "prosa"):
        # No son numeros. Se registran para que el censo los vea, pero no
        #itzen veredicto: contarlos como "comprobado" seria falso.
        return None

    if c["tipo"] == "portador":
        p = os.path.join(raiz, c["ruta"])
        if not os.path.exists(p):
            return dict(out, veredicto="ROTO",
                        motivo="el fichero citado no existe: %s" % c["ruta"])
        v = dict(out, veredicto="EXISTE",
                 motivo="el fichero existe (%d bytes)" % os.path.getsize(p))
        if c.get("version") and RE_VERSION.match(c["version"]):
            real = version_real(p)
            if real is None:
                v["veredicto"] = "MALFORMADO"
                v["motivo"] = ("se declara version %s y el fichero no declara "
                               "VERSION: no se puede comprobar"
                               % c["version"])
            elif real != c["version"]:
                v["veredicto"] = "DIFIERE"
                v["motivo"] = ("el documento dice %s y el fichero dice %s"
                               % (c["version"], real))
            else:
                v["motivo"] += "; VERSION coincide (%s)" % real
        return v

    # --- sumas ---
    if not RE_HEX.match(valor):
        # Layout `sha256  <path> <digest>` (hallazgo 970): el path viene DENTRO
        # del valor. Se separa aqui y no en el parser de campos, porque es el
        # VALOR el que lleva las dos cosas y es la unica linea donde se puede
        # partir sin ambiguedad.
        m = re.match(r"^(\S+)\s+([0-9a-f]{16,64})$", valor)
        if m:
            c["portador"] = m.group(1)
            valor = m.group(2)
            out["valor"] = valor
            out["ruta_dentro_del_valor"] = c["portador"]
        else:
            return dict(out, veredicto="MALFORMADO",
                        motivo="no es un hash en hexadecimal: %r" % valor)

    objetivo = c.get("portador")
    if not objetivo:
        return dict(out, veredicto="SIN_RECETA",
                    motivo="no hay ningun campo portador antes que este")

    p = os.path.join(raiz, objetivo)
    if not os.path.exists(p):
        return dict(out, veredicto="ROTO",
                    motivo="el fichero cuyo hash se declara no existe: %s"
                           % objetivo)

    if clave == "sha256":
        got = sha256_de(p)
        # Un digest CORTO es un digest truncado, no uno distinto. Comparar
        # igualdad sobre la cadena entera daria DIFIERE con el mensaje
        # "declarado dd4fc3c5, obtenido dd4fc3c5", que es una contradiccion
        # visible y un veredicto equivocado. MEDIDO: las cabeceras de este
        # proyecto publican 16 hex, no 64, y con la comparacion entera las
        # marcaba todas como DIFIERE.
        #
        # El minimo son 16 hex = 64 bits. Por debajo, un prefijo no identifica
        # un fichero con ninguna probabilidad util, y aceptarlo seria
        # aceptar un numero que parece una garantia y no lo es. El umbral esta
        # en codigo porque es una decision, no un parametro.
        if len(valor) < 16:
            return dict(out, veredicto="MALFORMADO",
                        motivo="solo %d hex: por debajo de 64 bits no "
                               "identifica nada" % len(valor))
        if got.startswith(valor):
            v = dict(out, veredicto="COINCIDE")
            if len(valor) == 64:
                v["motivo"] = "sha256 integro de %s" % objetivo
            else:
                v["motivo"] = ("prefijo de %d hex del sha256 de %s"
                               % (len(valor), objetivo))
            amb = c.get("ambiguo_con")
            if amb:
                v["veredicto"] = "AMBIGUO"
                v["motivo"] += ("; pero el MISMO digest se declara tambien "
                                "para %s, y cumple en ambos: no distingue"
                                % ", ".join(amb))
            return v
        return dict(out, veredicto="DIFIERE",
                    motivo="declarado %s, obtenido %s" % (valor, got[:len(valor)]))

    # clave == "reproducible"
    #
    # AQUI ESTABA EL DEFECTO, Y ERA MIO.
    #
    # La primera version de esta herramienta devolvia SIN_RECETA para este
    # campo, incondicionalmente, y su docstring lo declaraba como MEDIDO: "no
    # hay receta, no hay definicion, y no se deduce de nada del arbol". MEDIDO
    # era falso. La receta existe y es esta de abajo; lo que no existia era MI
    # busqueda de ella.
    #
    # Lo perdi por buscar la forma equivocada. Enumere cinco normalizaciones
    # del JSON y probe con las dos que se me ocurren primero -- indent=2 y
    # compacto -- y las dos fallan. La que funciona esta en el hueco de
    # en medio: los SEPARADORES POR DEFECTO de Python, que son ", " y ": ",
    # que no son ni una cosa ni la otra. MEDIDO 3 de 3 sobre R1, R2 y R3, y
    # un adversary lo encontro antes que yo.
    #
    # Dos cosas mas que salieron de ahi, y las dos son el mismo error:
    #
    #  1. Un veredicto condicional no se deduce. El codigo debe intentarlo
    #     y reportar SI lo ha conseguido o no, no decidir de antemano que no.
    #     Por eso SIN_RECETA ya no existe para esta clave: hay receta, y si no
    #     coincide el veredicto es DIFIERE, que es un hecho comprobable.
    #
    #  2. El selftest no lo habria pillado. El vector V3 usaba un valor
    #     inventado ("d"*64) que no puede tener receta, asi que el vector
    #     pasaba por una razon trivial. Un selftest que solo prueba valores
    #     sabiamente imposibles prueba que el codigo corre, no que acierte.
    got = receta_reproducible(p)
    if got is None:
        # El objetivo no es JSON. No es "no hay receta": es que esta receta no
        # aplica a este fichero, y eso se dice con sus palabras.
        return dict(out, veredicto="DIFIERE",
                    motivo="el objetivo no es JSON, y la unica receta de "
                           "`reproducible` es sobre JSON")
    if got == valor:
        return dict(out, veredicto="COINCIDE",
                    motivo=RECETA_REPRODUCIBLE)
    if got.startswith(valor):
        return dict(out, veredicto="COINCIDE",
                    motivo="prefijo de %d hex; %s" % (len(valor),
                                                      RECETA_REPRODUCIBLE))
    return dict(out, veredicto="DIFIERE",
                motivo="declarado %s, la receta da %s (%s)"
                       % (valor, got, RECETA_REPRODUCIBLE))


VEREDICTOS = ("EXISTE", "COINCIDE", "DIFIERE", "AMBIGUO", "SIN_RECETA", "ROTO",
              "MALFORMADO")


def marca_ambiguedad(campos):
    """
    Un digest que se declara para VARIOS paths, y cumple en todos, no
    identifica ninguno de ellos.

    MEDIDO en el 977: el bloque declara `0280d616a3dd774c...` para
    `gate-run-1.txt` y para `gate-run-2.txt`, y el valor es CORRECTO en los dos.
    Por eso el veredicto COINCIDE, tal cual, no ve el problema: la pregunta que
    importa no es "el hash corresponde a este fichero" --si-- sino "el hash
    DISTINGUE este fichero de los demas". Si tres ficheros del arbol tienen la
    misma suma, el hash que los acompaña a dos de ellos no es evidencia sobre
    ninguno: es un hash de contenido, y esos dos ficheros tienen el mismo
    contenido.

    Que este caso sea el del 977 no es casualidad: las dos salidas de una puerta
    que se ejecuta dos veces SON identicas, y por eso son el par de ficheros
    donde tiene sentido comprobar que la afirmacion "estas dos salidas son
    iguales" se apoya en algo mas que en(hash, hash).

    Es una comprobacion LOCAL, sin recorrer el arbol: si el mismo digest se
    declara para mas de un portador y todos cumplen, se marca. No catches el
    caso general --un hash colisiona con un fichero que nadie declara--, y eso
    esta escrito en LIMITACION para no vender mas de lo que mide.
    """
    por_digest = {}
    for c in campos:
        if c["tipo"] != "suma" or not c.get("portador"):
            continue
        if not re.match(r"^[0-9a-f]{16,64}$", c["valor"]):
            continue
        por_digest.setdefault(c["valor"], []).append(c)
    for valor, grupo in por_digest.items():
        paths = set(c["portador"] for c in grupo)
        # Dos declaraciones del MISMO path no son ambiguedad: es el mismo
        # fichero dicho dos veces, que no es un error pero tampoco es una
        # prueba de nada. Lo que degrada el digest a no-identificante es que
        # seal para MAS DE UN path DISTINTO.
        if len(paths) < 2:
            continue
        for c in grupo:
            c["ambiguo_con"] = sorted(
                o["portador"] for o in grupo if o["portador"] != c["portador"])


def audita(rutas, raiz_scan, raiz_res=None):
    """
    Audita documentos .md. Devuelve (informe, error_de_uso).

    DOS RAICES, Y POR QUE NO SE PUEDEN MEZCLAR
    -------------------------------------------
    MEDIDO como defecto mio, dos veces seguidas:

      1. La raiz de resolucion se derivaba de `--arbol`. Con
         `--arbol <docs> --raiz .` las rutas project-relative se resolvian
         contra `<docs>` y salian **2 ROTO falsos** donde debia haber COINCIDE.

      2. Al separarlas, los DOCUMENTOS se volvieron a abrir contra la raiz
         equivocada: `recoge_md` devuelve rutas relativas al arbol donde busca,
         y se abrian contra la raiz de resolucion. Con dos raices distintas eso
         es `ilegible` para todos los ficheros, que es un censo vacio disfrazado
         de censo.

    Que el segundo defecto no lo cogiera el self-test es la parte que importa: no
    habia NINGUN vector con dos raices distintas. Un self-test que solo ejercita
    el caso trivial de "una raiz" no cubre el caso para el que existe la opcion.

    `raiz_scan` -> donde se buscan los .md
    `raiz_res`  -> contra que se resuelven los paths que los .md citan
    """
    if raiz_res is None:
        raiz_res = raiz_scan
    informe = {"version": VERSION, "raiz": raiz_res, "raiz_scan": raiz_scan,
               "ficheros": [], "recuento": dict((v, 0) for v in VEREDICTOS),
               "bloques": 0, "campos_auditados": 0, "errores": [], "parciales": []}
    for ruta in rutas:
        # Una ruta relativa se resuelve contra `raiz_scan`, que es donde se
        # buscan los documentos. Sin esto, un censo entero sale como
        # "ilegible" y parece un censo sin hallazgos.
        p = ruta if os.path.isabs(ruta) else os.path.join(raiz_scan, ruta)
        rel = os.path.relpath(p, raiz_scan)
        try:
            with open(p, "r", errors="replace") as f:
                texto = f.read()
        except OSError as e:
            informe["errores"].append({"fichero": rel,
                                       "error": "ilegible: %s" % e})
            continue
        bloques, parcial = lee_bloques(texto, rel)
        # UNA VALLA ABIERTA NO ES UN ERROR DE PARSEO: ES UN DOCUMENTO PARCIAL.
        #
        # MEDIDO: antes, un documento con la ultima valla sin cerrar iba entero a
        # `errores` y no aportaba NINGUN bloque al censo. Uno de ellos tiene 403
        # vallas, con las 402 anteriores perfectamente validas, y las estaba
        # tirando. Convertir un defecto de redaccion en un hueco de
        # observabilidad sobre el documento entero sale mas caro que el defecto.
        #
        # Se countable lo countable y se declara el documento parcial, que es lo
        # que el rc=2 ya significa: "este censo no es completo".
        if parcial is not None:
            informe["parciales"].append(
                {"fichero": rel, "linea": parcial[0], "backticks": parcial[1]})
        ent = {"fichero": rel, "bloques": []}
        for abre, lineas in bloques:
            campos = parsea_bloque(lineas, raiz_res, rel)
            if campos is None:
                continue
            informe["bloques"] += 1
            b = {"linea": abre, "campos": []}
            for c in campos:
                v = audita_campo(c, raiz_res, rel)
                if v is None:
                    continue
                informe["campos_auditados"] += 1
                informe["recuento"][v["veredicto"]] += 1
                b["campos"].append(v)
            ent["bloques"].append(b)
        if ent["bloques"]:
            informe["ficheros"].append(ent)
    return informe, None


def rc_de(informe):
    """
    Codigo de salida. Distingue 'no he mirado' de 'he mirado y esta bien'.

    Precedencia, y por que el 2 va primero: un error de parseo significa que
    el censo esta incompleto, y un censo incompleto no se puede llamar
    favorable ni desfavorable. Oculta un DIFIERE real detras de un rc=2, si,
    pero el recuento completo esta en la salida de texto y en el JSON, y el
    texto dice explicitamente que el censo esta incompleto. Un rc=4 con un
    censo incompleto seria peor: diria "esto esta mal" sin decir "y no lo he
    mirado todo".
    """
    r = informe["recuento"]
    if informe.get("errores") or informe.get("parciales"):
        return 2
    if r["DIFIERE"] or r["ROTO"] or r["MALFORMADO"]:
        return 4
    if r["AMBIGUO"] or r["SIN_RECETA"]:
        return 3
    if not informe["bloques"]:
        return 1
    return 0


def imprime(informe):
    r = informe["recuento"]
    print("=" * 78)
    print("SELLO DE PROCEDENCIA  %s" % informe["version"])
    print("=" * 78)
    print("raiz_scan  %s   (donde se buscan los .md)" % informe.get("raiz_scan", "-"))
    print("raiz       %s   (contra que se resuelven los paths citados)"
          % informe["raiz"])
    print("bloques  %d con campo de procedencia, en %d fichero(s)"
          % (informe["bloques"], len(informe["ficheros"])))
    print("campos   %d auditados" % informe["campos_auditados"])
    print()
    for v in VEREDICTOS:
        print("  %-12s %d" % (v, r[v]))
    print()
    for ent in informe["ficheros"]:
        for b in ent["bloques"]:
            print("  %s:%d" % (ent["fichero"], b["linea"]))
            for c in b["campos"]:
                print("    %-12s %-11s %s" % (c["veredicto"], c["campo"],
                                             c["motivo"]))
            print()
    if informe.get("parciales"):
        print("DOCUMENTOS PARCIALES: valla sin cerrar, se audita lo que hay (%d)"
              % len(informe["parciales"]))
        for e in informe["parciales"]:
            print("  %-58s valla de %d abierta en la linea %d"
                  % (e["fichero"][:58], e["backticks"], e["linea"]))
        print()
    if informe.get("errores"):
        print("DOCUMENTOS QUE NO SE HAN PODIDO AUDITAR: %d" %
              len(informe["errores"]))
        print("El censo de estos ficheros esta INCOMPLETO. Sus bloques no se")
        print("cuentan ni a favor ni en contra, porque una viga sin cerrar")
        print("desalinea todo lo que viene despues.")
        for e in informe["errores"]:
            print("  %-58s %s" % (e["fichero"][:58], e["error"]))
        print()


def recoge_md(raiz):
    """Rutas ABSOLUTAS de los .md de un arbol.

    Absolutas, y no relativas a `raiz`, por el motivo escrito en `audita`: con
    dos raices distintas, unir una ruta relativa a la raiz equivocada produce un
    censo entero de ficheros ilegibles.
    """
    out = []
    for dp, dns, fns in os.walk(raiz):
        dns[:] = [d for d in dns
                  if d not in (".git", "__pycache__", "node_modules", "archive")]
        for fn in fns:
            if fn.endswith(".md"):
                out.append(os.path.join(dp, fn))
    return sorted(out)


# ---------------------------------------------------------------------------
# SELFTEST
#
# En un arbol temporal. NO lee el proyecto: un selftest que lee el mundo mutable
# no es reproducible, y el proyecto ya lo midio (A32: 16 de 68).
#
# Los vectores NECESITAN fallar. Un selftest que solo tiene vectores que pasan
# es un `return True` con subprocess, asi que hay un vector por cada modo de
# fallo del clasificador, y todos ellos esperan codigo de salida distinto de 0.
# ---------------------------------------------------------------------------
def selftest():
    import tempfile
    fallos = 0
    vectores = 0

    def chk(nombre, cond, detalle=""):
        nonlocal fallos, vectores
        vectores += 1
        if cond:
            print("    OK   %-52s %s" % (nombre, detalle))
        else:
            fallos += 1
            print("    FALLA %-52s %s" % (nombre, detalle))

    def hash_de(p):
        return hashlib.sha256(open(p, "rb").read()).hexdigest()

    with tempfile.TemporaryDirectory() as td:
        raiz = os.path.join(td, "arbol")
        os.makedirs(raiz)
        her = os.path.join(raiz, "her.py")
        with open(her, "w") as f:
            # Un literal, NO VERSION. MEDIDO: al subir esta herramienta a
            # 1.1.0, cuatro vectoresfallen porque el fixture heredaba la
            # version del codigo. Un self-test cuyo significado depende del
            # numero de version de la herramienta es un self-test que se rompe
            # por una razon que no tiene que ver con lo que prueba.
            f.write('#!/usr/bin/env python3\nVERSION = "1.0.0"\n')
        art = os.path.join(raiz, "art.json")
        with open(art, "w") as f:
            f.write('{"a": 1}\n')
        h_her, h_art = hash_de(her), hash_de(art)

        def escribe(nombre, texto):
            p = os.path.join(raiz, nombre)
            with open(p, "w") as f:
                f.write(texto)
            return nombre

        def blk(cuerpo):
            return "```\n" + cuerpo + "```\n"

        # 1. todo correcto
        escribe("ok.md", blk(
            "herramienta   her.py 1.0.0\n"
            "sha256        %s\n"
            "artefacto     art.json\n"
            "sha256        %s\n" % (h_her, h_art)))
        i, e = audita(["ok.md"], raiz)
        chk("V1_todo_coincide_rc0", e is None and rc_de(i) == 0,
            "rc=%s" % (rc_de(i) if i else "ERR:%s" % e))
        chk("V1_dos_sumas_coinciden_dos_ficheros_existen",
            i["recuento"]["COINCIDE"] == 2 and i["recuento"]["EXISTE"] == 2,
            "COINCIDE=%d EXISTE=%d" % (i["recuento"]["COINCIDE"],
                                       i["recuento"]["EXISTE"]))

        # 2. hash equivocado -> DIFIERE, rc 4
        escribe("mal.md", blk(
            "herramienta   her.py 1.0.0\nsha256        %s\n" % ("0" * 64)))
        i, e = audita(["mal.md"], raiz)
        chk("V2_hash_falso_es_DIFIERE",
            i["recuento"]["DIFIERE"] == 1 and rc_de(i) == 4)

        # 3. `reproducible` CON la receta real. Este vector es el que faltaba y por
        #      eso el defecto durio: la primera version del codigo devolvia
        #      SIN_RECETA para esta clave, y el selftest no lo pillaba porque
        #      usaba un valor inventado ("d"*64) que no puede tener receta.
        #      Aqui el valor SI se puede calcular, y tiene que dar COINCIDE.
        art_repro = os.path.join(raiz, "art2.json")
        with open(art_repro, "w") as f:
            json.dump({"generado": "2026-10-04T12:31:12-0300", "filas": 3,
                       "orden": ["b", "a"]}, f)
        h_repro = receta_reproducible(art_repro)

        # 3-ante. EL ORACULO. La constante de arriba esta calculada FUERA de
        #       esta herramienta. Si aqui seCalling the function under test,
        #       el vector pasa siempre. Este lo escribe a mano y ademas
        #       comprueba que las tres formas de json.dumps NO coinciden, que
        #       es la libertad exacta que ha roto este fichero.
        d_m = {"filas": 3, "orden": ["b", "a"]}
        por_defecto = hashlib.sha256(
            json.dumps(d_m, sort_keys=True).encode()).hexdigest()
        por_compacto = hashlib.sha256(
            json.dumps(d_m, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        por_indent = hashlib.sha256(
            json.dumps(d_m, sort_keys=True, indent=2).encode()).hexdigest()
        chk("V3ant_la_constante_externa_coincide_con_la_forma_por_defecto",
            por_defecto == REPRO_MUESTRA_DEFECTO,
            por_defecto[:16])
        chk("V3ant2_las_tres_formas_son_distintas",
            len({por_defecto, por_compacto, por_indent}) == 3,
            "si coincidieran, el vector no distinguiria la receta")
        chk("V3ant3_la_constante_externa_es_la_de_la_receta",
            por_defecto == REPRO_MUESTRA_DEFECTO
            and por_compacto == REPRO_MUESTRA_COMPACTO
            and por_indent == REPRO_MUESTRA_INDENT)
        chk("V3ant4_la_receta_producida_usa_los_separadores_por_defecto",
            h_repro == REPRO_MUESTRA_DEFECTO,
            "producido=%s esperado=%s" % (h_repro[:16],
                                          REPRO_MUESTRA_DEFECTO[:16]))
        escribe("rep.md", blk(
            "artefacto     art2.json\n"
            "sha256        %s\n"
            "reproducible  %s\n" % (hash_de(art_repro), h_repro)))
        i, e = audita(["rep.md"], raiz)
        chk("V3_reproducible_se_recalcula_y_coincide",
            i["recuento"]["COINCIDE"] == 2 and i["recuento"]["SIN_RECETA"] == 0
            and rc_de(i) == 0, "rc=%d COINCIDE=%d SIN_RECETA=%d"
            % (rc_de(i), i["recuento"]["COINCIDE"],
               i["recuento"]["SIN_RECETA"]))

        # 3-bis. la receta es INVARIANTE al reloj: es la condicion de sentido
        #        del campo. Si esto fallara, el hash no seria "reproducible",
        #        seria "el hash de este instante".
        with open(art_repro, "w") as f:
            json.dump({"generado": "2030-01-01T00:00:00+0000", "filas": 3,
                       "orden": ["b", "a"]}, f)
        chk("V3b_la_receta_no_depende_del_reloj",
            receta_reproducible(art_repro) == h_repro)

        # 3-ter. `reproducible` con un valor que NO es el de la receta -> DIFIERE,
        #         no SIN_RECETA. Aqui hay receta y se ha ejecutado: el
        #         veredicto tiene que decir que los numeros no coinciden.
        escribe("rep2.md", blk(
            "artefacto     art2.json\n"
            "reproducible  %s\n" % ("a" * 64)))
        i, e = audita(["rep2.md"], raiz)
        chk("V3c_reproducible_equivocado_es_DIFIERE",
            i["recuento"]["DIFIERE"] == 1 and rc_de(i) == 4)

        # 3-quater. la receta no aplica a un objetivo que no es JSON: se dice
        #           con esas palabras, no con "no hay receta".
        escribe("rep3.md", blk(
            "artefacto     her.py\n"
            "reproducible  %s\n" % ("a" * 64)))
        i, e = audita(["rep3.md"], raiz)
        chk("V3d_objetivo_no_json_no_inventa_SIN_RECETA",
            i["recuento"]["DIFIERE"] == 1 and i["recuento"]["SIN_RECETA"] == 0,
            i["ficheros"][0]["bloques"][0]["campos"][1]["motivo"][:40])

        # 4. fichero citado que no existe -> ROTO
        escribe("roto.md", blk("herramienta   no-existe.py\n"))
        i, e = audita(["roto.md"], raiz)
        chk("V4_fichero_inexistente_es_ROTO",
            i["recuento"]["ROTO"] == 1 and rc_de(i) == 4)

        # 5. version que el fichero no declara
        escribe("ver.md", blk(
            "herramienta   her.py 2.0.0\nsha256        %s\n" % h_her))
        i, e = audita(["ver.md"], raiz)
        chk("V5_version_falsa_es_DIFIERE", i["recuento"]["DIFIERE"] == 1)

        # 6. version no comprobable (el fichero no declara VERSION)
        escribe("sinver.py", "x = 1\n")
        escribe("ver2.md", blk("herramienta   sinver.py 1.0.0\n"))
        i, e = audita(["ver2.md"], raiz)
        chk("V6_version_no_comprobable_es_MALFORMADO",
            i["recuento"]["MALFORMADO"] == 1)

        # 7. hash sin portador antes: no tiene objetivo
        escribe("huerfano.md", blk("sha256        %s\n" % h_art))
        i, e = audita(["huerfano.md"], raiz)
        chk("V7_hash_huerfano_no_se_atribuye",
            i["recuento"]["SIN_RECETA"] == 1)

        # 8. entrada vacia -> rc 1, que NO es 0
        escribe("vacio.md", "")
        i, e = audita(["vacio.md"], raiz)
        chk("V8_vacio_es_rc1_no_rc0",
            e is None and i["bloques"] == 0 and rc_de(i) == 1,
            "rc=%d" % rc_de(i))

        # 9. texto que no es un bloque de procedencia -> tambien rc 1
        escribe("prosa.md", "esto es prosa con `sha256 deadbeef` dentro\n")
        i, e = audita(["prosa.md"], raiz)
        chk("V9_prosa_no_es_bloque", i["bloques"] == 0 and rc_de(i) == 1)

        # 10. viga sin cerrar -> error de parseo, rc 2, no 0
        escribe("viga.md", "```\nsha256  %s\n" % h_art)
        i, e = audita(["viga.md"], raiz)
        chk("V10_valla_sin_cerrar_es_PARCIAL_no_error", rc_de(i) == 2
            and len(i["parciales"]) == 1 and len(i["errores"]) == 0,
            "rc=%d parciales=%d errores=%d" % (rc_de(i), len(i["parciales"]),
                                                len(i["errores"])))

        # 10-bis. un documento roto NO ABORTA el censo de los demas. Es la
        #      razon de ser de `errores` como lista: MEDIDO en el arbol real,
        #      una viga sin cerrar en 063 hacia que la primera version no
        #      censara NADA.
        i, e = audita(["viga.md", "ok.md"], raiz)
        chk("V10b_el_censo_continua_pasado_un_parcial",
            rc_de(i) == 2 and i["recuento"]["COINCIDE"] == 2
            and len(i["parciales"]) == 1,
            "COINCIDE=%d parciales=%d" % (i["recuento"]["COINCIDE"],
                                          len(i["parciales"])))

        # 10-ter. los bloques del fichero roto NO se cuentan: estan desalineados
        i, e = audita(["viga.md"], raiz)
        chk("V10c_lo_que_no_se_cerro_no_se_cuenta_como_bloque",
            i["bloques"] == 0 and i["campos_auditados"] == 0)
        # 10-c-bis. PERO LO QUE SI SE CERRO, SE CUENTA. Este es el cambio de
        #   fondo: antes un documento con una valla al final no aportaba NADA.
        escribe("mixto.md", blk("artefacto  art.json\nsha256   %s\n" % h_art)
                + "```\nsha256  %s\n" % h_art)
        i, e = audita(["mixto.md"], raiz)
        chk("V10d_lo_que_se_cerro_antes_si_se_cuenta",
            i["bloques"] == 1 and i["recuento"]["COINCIDE"] == 1
            and len(i["parciales"]) == 1,
            "bloques=%d COINCIDE=%d parciales=%d" % (i["bloques"],
                                                     i["recuento"]["COINCIDE"],
                                                     len(i["parciales"])))

        # 10-quater. un fichero ilegible tambien va a errores, no aborta
        i, e = audita(["no-existe.md", "ok.md"], raiz)
        chk("V10d_ilegible_no_aborta_el_censo",
            rc_de(i) == 2 and i["recuento"]["COINCIDE"] == 2)

        # 11. el informe nunca es None: main() ya no lo trata como error
        i, e = audita(["no-existe.md"], raiz)
        chk("V11_informe_siempre_existe", i is not None and e is None)

        # 12. un solo espacio NO es separador: la prosa no es un campo
        escribe("prosa2.md", blk("herramienta her.py 1.0.0\n"))
        i, e = audita(["prosa2.md"], raiz)
        chk("V12_un_espacio_no_es_campo", i["bloques"] == 0)

        # 13. campo fuera del vocabulario -> ignorado, no MALFORMADO
        escribe("vocab.md", blk("milagro   12345\n"))
        i, e = audita(["vocab.md"], raiz)
        chk("V13_campo_fuera_de_vocabulario_se_ignora",
            i["bloques"] == 0 and rc_de(i) == 1)

        # 14. hex invalido
        escribe("hex.md", blk("artefacto  art.json\nsha256   ZZZZ\n"))
        i, e = audita(["hex.md"], raiz)
        chk("V14_hex_invalido_es_MALFORMADO",
            i["recuento"]["MALFORMADO"] == 1)

        # 14-bis. digest truncado: es un digest, no uno distinto
        escribe("trunc.md", blk("artefacto  art.json\nsha256   %s\n" % h_art[:16]))
        i, e = audita(["trunc.md"], raiz)
        chk("V14b_prefijo_de_16_hex_es_COINCIDE",
            i["recuento"]["COINCIDE"] == 1 and rc_de(i) == 0,
            "rc=%d" % rc_de(i))

        # 14-ter. prefijo que NO es el de ese fichero -> DIFIERE de verdad
        escribe("trunc2.md", blk("artefacto  art.json\nsha256   %s\n" % ("a" * 16)))
        i, e = audita(["trunc2.md"], raiz)
        chk("V14c_prefijo_equivocado_es_DIFIERE",
            i["recuento"]["DIFIERE"] == 1)

        # 14-quater. prefijo por debajo de 64 bits no es procedencia
        escribe("corto.md", blk("artefacto  art.json\nsha256   %s\n" % h_art[:8]))
        i, e = audita(["corto.md"], raiz)
        chk("V14d_prefijo_de_8_hex_es_MALFORMADO",
            i["recuento"]["MALFORMADO"] == 1)

        # 19. el mismo digest para dos paths -> AMBIGUO. Es el caso del 977 con
        #     gate-run-1.txt y gate-run-2.txt: el valor es CORRECTO en los dos, y
        #     por eso un COINCIDE a secas no ve nada malo. La pregunta que
        #     importa es si el hash DISTINGUE, no si acompaña.
        escribe("amb.md", blk(
            "artefacto  art.json\n"
            "sha256   %s\n"
            "artefacto  copia.json\n"
            "sha256   %s\n" % (h_art, h_art)))
        with open(os.path.join(raiz, "copia.json"), "w") as f:
            f.write('{"a": 1}\n')
        i, e = audita(["amb.md"], raiz)
        chk("V19_digest_repetido_es_AMBIGUO",
            i["recuento"]["AMBIGUO"] == 2 and i["recuento"]["COINCIDE"] == 0
            and rc_de(i) == 3, "AMBIGUO=%d rc=%d"
            % (i["recuento"]["AMBIGUO"], rc_de(i)))
        chk("V19b_AMBIGUO_no_es_un_veredicto_de_cumplimiento",
            i["recuento"]["AMBIGUO"] == 2
            and all(c["veredicto"] != "COINCIDE"
                    for b in i["ficheros"][0]["bloques"]
                    for c in b["campos"] if c["campo"] == "sha256"))
        # el mismo digest para el MISMO path dos veces no es ambiguedad
        escribe("amb2.md", blk(
            "artefacto  art.json\nsha256   %s\n"
            "artefacto  art.json\nsha256   %s\n" % (h_art, h_art)))
        i, e = audita(["amb2.md"], raiz)
        chk("V19c_mismo_path_dos_veces_no_es_AMBIGUO",
            i["recuento"]["COINCIDE"] == 2 and i["recuento"]["AMBIGUO"] == 0)

        # 20. layout `sha256 <path> <digest>` (el del hallazgo 970). Antes se
        #     reportaba NADA de ese bloque, que es peor que un veredicto malo.
        escribe("dentro.md", blk("sha256  her.py %s\n" % h_her))
        i, e = audita(["dentro.md"], raiz)
        chk("V20_path_dentro_del_valor_se_resuelve",
            i["recuento"]["COINCIDE"] == 1 and rc_de(i) == 0,
            "COINCIDE=%d" % i["recuento"]["COINCIDE"])

        # 20-bis. y si el path de dentro no existe, se dice ROTO, no silencio
        escribe("dentro2.md", blk("sha256  no/existe.py %s\n" % h_her))
        i, e = audita(["dentro2.md"], raiz)
        chk("V20b_path_interno_inexistente_es_ROTO",
            i["recuento"]["ROTO"] == 1 and i["campos_auditados"] == 1)
        #      Es la que usan los findings, y la que la primera version de esta
        #      herramienta no entendia: reportaba 15 SIN_RECETA falsos.
        escribe("cont.md", blk(
            "sha256  %s\n"
            "        art.json  12 bytes\n"
            "sha256  %s\n"
            "        her.py\n" % (h_art, h_her)))
        i, e = audita(["cont.md"], raiz)
        chk("V14e_continuacion_es_el_portador",
            i["recuento"]["COINCIDE"] == 2 and rc_de(i) == 0,
            "COINCIDE=%d rc=%d" % (i["recuento"]["COINCIDE"], rc_de(i)))

        # 14-sexies. continuacion que NO es un path: sigue SIN_RECETA
        escribe("cont2.md", blk("sha256  %s\n        nota: nada que ver\n" % h_art))
        i, e = audita(["cont2.md"], raiz)
        chk("V14f_continuacion_que_no_es_path_no_inventa_portador",
            i["recuento"]["SIN_RECETA"] == 1)

        # 14-septies. continuacion con un path que no existe -> ROTO, que es
        #      distinto de "no se que fichero es"
        escribe("cont3.md", blk("sha256  %s\n        no/existe.json\n" % h_art))
        i, e = audita(["cont3.md"], raiz)
        chk("V14g_continuacion_inexistente_es_ROTO",
            i["recuento"]["ROTO"] == 1)

        # 15. la precedencia de rc_de es la documentada. Se prueba la FUNCION
        #     con informes sinteticos, porque la combinacion "hay bloques y
        #     aun asi nada que auditar" no se puede construir con el clasificador
        #     y probarla ahi seria un vector que no puede fallar.
        def info(bloques, **rec):
            r = dict((v, 0) for v in VEREDICTOS)
            r.update(rec)
            return {"bloques": bloques, "recuento": r}

        chk("V15a_rc0_sin_nada_que_auditar_no_es_0", rc_de(info(1)) == 0,
            "rc=%d" % rc_de(info(1)))
        chk("V15b_rc1_cero_bloques", rc_de(info(0)) == 1)
        chk("V15c_rc3_gana_a_rc1",
            rc_de(info(0, SIN_RECETA=1)) == 3)
        chk("V15d_rc4_gana_a_rc3",
            rc_de(info(0, SIN_RECETA=1, DIFIERE=1)) == 4)
        chk("V15e_rc4_gana_a_rc4_por_ROTO",
            rc_de(info(0, DIFIERE=1, ROTO=1)) == 4)
        chk("V15f_MALFORMADO_tambien_es_rc4",
            rc_de(info(0, MALFORMADO=1)) == 4)
        chk("V15g_rc2_de_censo_incompleto_gana_a_todo",
            rc_de(dict(info(0, DIFIERE=1, SIN_RECETA=1), errores=[1])) == 2,
            "un censo incompleto no es un veredicto")

        # 16. round-trip del json: mismos recuentos que el texto
        i, e = audita(["ok.md"], raiz)
        j = json.loads(json.dumps(i))
        chk("V16_roundtrip_json_conserva_recuento",
            j["recuento"] == i["recuento"] and j["bloques"] == i["bloques"])

        # 17. elHash se recalcula de verdad: cambiar un byte lo cambia
        with open(art, "a") as f:
            f.write('{"b": 2}\n')
        i, e = audita(["ok.md"], raiz)
        chk("V17_un_byte_cambia_el_veredicto",
            i["recuento"]["COINCIDE"] == 1 and i["recuento"]["DIFIERE"] == 1,
            "COINCIDE=%d DIFIERE=%d" % (i["recuento"]["COINCIDE"],
                                       i["recuento"]["DIFIERE"]))
        with open(art, "w") as f:
            f.write('{"a": 1}\n')

        # 22. VALLAS DE 4 BACKTICKS. MEDIDO: promp.md tiene 2, y el
        #     emparejador viejo las mezclaba con las de 3 y declaraba el
        #     documento entero ilegible. Una valla de N se cierra con otra
        #     de N o mas.
        escribe("cuatro.md", "````\nartefacto  art.json\nsha256   %s\n````\n" % h_art)
        i, e = audita(["cuatro.md"], raiz)
        chk("V22_valla_de_4_se_cierra_con_4",
            i["bloques"] == 1 and i["recuento"]["COINCIDE"] == 1
            and len(i["parciales"]) == 0 and len(i["errores"]) == 0,
            "bloques=%d COINCIDE=%d parciales=%d" % (i["bloques"],
                                                     i["recuento"]["COINCIDE"],
                                                     len(i["parciales"])))
        # y una valla de 3 NO cierra una de 4
        escribe("cuatro2.md", "````\nartefacto  art.json\n```\n")
        i, e = audita(["cuatro2.md"], raiz)
        chk("V22b_una_valla_de_3_no_cierra_una_de_4",
            i["bloques"] == 0 and len(i["parciales"]) == 1,
            "parciales=%d" % len(i["parciales"]))

        # 18. hermeticidad: una raiz que no existe es un error de uso, no un
        #     veredicto sobre cero documentos
        chk("V18_raiz_inexistente_no_produce_veredicto",
            audita(["ok.md"], "/no/existe")[0]["recuento"]["COINCIDE"] == 0
            and rc_de(audita(["ok.md"], "/no/existe")[0]) == 2)

        # 21. DOS RAICES DISTINTAS. Este vector no existia, y por eso no se
        #     detectaron los dos bugs de raiz. El caso es el natural del
        #     proyecto: los .md viven en 08-ARQUITECTURA/ y los paths que
        #     citan son relativos a la raiz del proyecto entero.
        sub = os.path.join(raiz, "08-ARQ")
        os.makedirs(sub)
        docs = os.path.join(sub, "docs")
        os.makedirs(docs)
        datos = os.path.join(raiz, "datos")
        os.makedirs(datos)
        with open(os.path.join(datos, "x.json"), "w") as f:
            f.write('{"a": 1}\n')
        h_x = hash_de(os.path.join(datos, "x.json"))
        with open(os.path.join(docs, "f.md"), "w") as f:
            f.write(blk("artefacto  datos/x.json\nsha256   %s\n" % h_x))
        rutas_abs = recoge_md(docs)
        i, e = audita(rutas_abs, docs, raiz)
        chk("V21_documentos_se_abren_por_raiz_scan",
            len(i["errores"]) == 0 and i["recuento"]["COINCIDE"] == 1,
            "errores=%d COINCIDE=%d" % (len(i["errores"]),
                                        i["recuento"]["COINCIDE"]))
        chk("V21b_paths_se_resuelven_por_raiz_res",
            i["recuento"]["ROTO"] == 0,
            "ROTO=%d" % i["recuento"]["ROTO"])
        # y con las dos raices iguales tambien, que es el caso trivial
        i, e = audita(rutas_abs, docs, docs)
        chk("V21c_con_una_sola_raiz_el_path_no_resuelve_y_se_dice",
            i["recuento"]["ROTO"] == 2 and i["recuento"]["COINCIDE"] == 0,
            "ROTO=%d (el portador y su sha256: los dos son ROTO, que es lo "
            "que corresponde cuando la raiz no es la del proyecto)"
            % i["recuento"]["ROTO"])

        # 21-d. ruta RELATIVA con dos raices distintas. Sin este vector, una
        #       mutacion que reabra los documentos contra la raiz de RESOLUCION
        #       pasa los 49 vectores: la rama es codigo alcanzable solo por la
        #       API, no por la CLI, y "no lo detecta la CLI" no es lo mismo que
        #       "no lo detecta nadie".
        os.chdir(raiz)                     # CWD = raiz, como el self-test real
        i, e = audita(["f.md"], docs, raiz)
        chk("V21d_ruta_relativa_se_resuelve_por_raiz_scan",
            len(i["errores"]) == 0 and i["recuento"]["COINCIDE"] == 1,
            "errores=%d COINCIDE=%d" % (len(i["errores"]),
                                        i["recuento"]["COINCIDE"]))
        os.chdir(td)

    print("  %d vectores, %d fallos" % (vectores, fallos))
    return 0 if fallos == 0 else 1


def main():
    ap = argparse.ArgumentParser(
        description="audita los bloques de procedencia de documentos .md")
    ap.add_argument("ficheros", nargs="*",
                    help="ficheros .md a auditar, relativos a --raiz")
    ap.add_argument("--raiz", default=".",
                    help="raiz a la que son RELATIVOS LOS PATHS CITADOS en los "
                         "bloques. Es independiente de --arbol: uno es donde se "
                         "buscan los documentos y el otro es contra que se "
                         "resuelven las rutas que citan")
    ap.add_argument("--arbol", default=None, metavar="DIR",
                    help="audita todos los .md de DIR")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    # DOS RAICES, Y POR QUE NO SE DERIVA UNA DE LA OTRA
    #
    # MEDIDO como defecto mio: la version anterior hacia
    #     raiz = abspath(a.arbol if a.arbol else a.raiz)
    # con lo que `--arbol 06-INGENIERIA-INVERSA/findings --raiz .` resolvia las
    # rutas project-relative contra `findings/` y fabricaba **12 ROTO falsos de
    # 14 campos**, con COINCIDE 0. Un comando plausible y un fallo silencioso.
    #
    # Son dos preguntas distintas y por eso son dos opciones distintas:
    #   dondeLooking for ->   --arbol
    #   what the paths are relative to -> --raiz
    raiz_scan = os.path.abspath(a.arbol) if a.arbol else os.path.abspath(".")
    raiz = os.path.abspath(a.raiz)
    if a.arbol:
        if not os.path.isdir(raiz_scan):
            print("no existe el arbol: %s" % raiz_scan)
            return 2
        rutas = recoge_md(raiz_scan)
    elif a.ficheros:
        rutas = [os.path.abspath(f) if not os.path.isabs(f)
                 else f for f in a.ficheros]
    else:
        print("dime que auditar: ficheros, o --arbol DIR")
        return 2

    informe, err = audita(rutas, raiz_scan, raiz)
    if informe is None:
        print("error: %s" % err)
        return 2
    if raiz != raiz_scan:
        # Se dice siempre. Si los dos coinciden, el lector no tiene por que
        # suponer nada; si no coinciden, el resultado depende de ello y callar
        # seria esconder la unica variable que puede cambiar el veredicto.
        print("ATENCION: dos raices distintas.")
        print("  --arbol (donde se buscan los .md)  %s" % raiz_scan)
        print("  --raiz  (contra que se resuelven los paths citados)  %s" % raiz)
        print()
    rc = rc_de(informe)
    if a.json:
        print(json.dumps(informe, indent=2, sort_keys=True, ensure_ascii=False))
        return rc
    imprime(informe)
    print("VEREDICTO")
    if rc == 0:
        print("  todos los campos tienen receta y coinciden")
    elif rc == 1:
        print("  NO SE HA AUDITADO NADA: no hay bloques de procedencia en el")
        print("  alcance dado. Esto no es un veredicto favorable.")
    elif rc == 3:
        print("  %d campo(s) SIN_RECETA: declarados y no recalculables."
              % informe["recuento"]["SIN_RECETA"])
        print("  Un hash sin receta no es una garantia de procedencia.")
    elif rc == 2:
        print("  CENSO INCOMPLETO: %d ilegible(s), %d parcial(es)."
              % (len(informe["errores"]), len(informe["parciales"])))
        print("  Los recuentos de arriba no cubren todo el alcance pedido.")
    else:
        print("  hay campos que DIFIEREN del fichero que citan, o ROTOS.")
    print()
    return rc


if __name__ == "__main__":
    sys.exit(main())
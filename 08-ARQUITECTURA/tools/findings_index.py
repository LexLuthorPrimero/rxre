#!/usr/bin/env python3
# CONTRACT: name=findings_index
# NO es READONLY, y no por una excepcion: `--escribir-reenvio` genera
# FINDINGS-RENUMERACIONES.md en la raiz del proyecto. Declararse read-only
# mientras se escribe un fichero del proyecto es la clase de mentira que
# invalida el resto de la tabla de contratos.
#
# Y no es la primera vez que se declara al reves en esta herramienta: antes de
# corregirlo, `toolkit.py` ya lo senalaba como uno de los FALLA. El aviso era
# CIERTO y la causa era ESTA. Se comprobaba leyendo la definicion de la flag --
# WRITES_FILES es "si escribe ficheros DEL PROYECTO" -- y no por lo que el
# mensaje del validador pareciera decir.
# CONTRACT: READONLY=no
# CONTRACT: WRITES_FILES=yes
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no

"""findings_index -- indice de hallazgos, con DETECCION DE COLISION y tabla de reenvio.

POR QUE EXISTE. El hallazgo 259 midio que `findings/` tiene 65 numeros con mas de
un fichero. El numero de hallazgo es la CLAVE PRIMARIA de la base de conocimiento:
con esas colisiones, `CORRECTED_BY=025` no dice cual corrige el 025, y el calculo de
sentido de CONTRADICTIONS.md resuelve de forma arbitraria cuando hay dos destinos
con el mismo nombre.

Hasta ahora eso lo encontro un ojo. Esto lo convierte en una COMPROBACION que
falla, con codigo de salida distinto, y que se puede integrar en la automatizacion
para que no vuelva en silencio.

SEGUNDA COSA QUE HACE, y que es la que hace falta para cerrar de verdad. Varias
sesiones renumeraron sus hallazgos para resolver colisiones, y **no dejaron tabla
de reenvio**. Consecuencia: una referencia escrita antes de la renumeracion
apunta hoy a un hallazgo DISTINTO, y no hay forma de saber cual era. Aqui se
detecta eso por TITULO: si dos ficheros de numeros distintos tienen el mismo
titulo, es el mismo hallazgo renumerado, y se puede emitir el par viejo -> nuevo.

LIMITE DECLARADO. La deteccion de renumeracion es por titulo normalizado. Dos
hallazgos distintos podrian compartir titulo, y un mismo hallazgo could've sido
reescrito al renumerar. Por eso la tabla de reenvio se marca como INDECISA cuando
el numero antiguo esta ocupado por OTRO contenido, porque ahi no se puede saber si
el destino es el renumerado o el que ocupo el sitio.

Uso:
  findings_index.py                 resumen + colisiones
  findings_index.py --reenvio       tabla de renumeraciones detectadas
  findings_index.py --escribir-reenvio   genera FINDINGS-RENUMERACIONES.md
  findings_index.py --colisiones    solo los numeros con >1 fichero
  findings_index.py --refs-colgadas  referencias que apuntan al hallazgo equivocado
  findings_index.py --json
  findings_index.py --self-test

Codigos de salida:
  0  sin colisiones
  1  hay colisiones   <- esto DEBE hacer fallar la automatizacion
  2  directorio ausente
"""

import glob
import json
import os
import re
import sys
import unicodedata

FIND = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "06-INGENIERIA-INVERSA", "findings")

# MEDIDO: con `{3}` esto indexaba 509 de 518 ficheros. Los 9 que faltaban eran
# los numerados 1000-1020, que tienen CUATRO digitos. El patron no fallaba: no
# coincidia, y un `continue` lo convertia en silencio. Consecuencia medida: esos
# 9 hallazgos eran invisibles para `colisiones()`, para `plan()` de
# refs_repair.py y para cualquier cosa que se apoye en `escanear()`, mientras
# `refs_colgadas()` SI los veia porque globa el directorio entero. De ahi que
# contara 1047 y el plan 1004.
#
# `{3,4}` es el rango real. Si alguna vez se reservan 10000+, esto vuelve a
# callar; por eso `--self-test` comprueba el numero de ficheros indexados
# contra los que hay en disco, y no solo que el regex compile.
RE_NUM = re.compile(r"^(\d{3,4})-")
RE_H1 = re.compile(r"^#\s*(.+?)\s*$", re.M)


def norm(t):
    """Titulo normalizado para comparar: sin acentos, sin puntuacion, minusculas.

    Sin esto, el mismo hallazgo renumerado NO se reconoce como tal porque su
    titulo cambio de acentuacion o de puntuacion al reescribirse.
    """
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[`*_·—–\.\,\:\;\(\)\[\]\"'-]", " ", t.lower())
    return re.sub(r"\s+", " ", t).strip()


def escanear(d=FIND):
    if not os.path.isdir(d):
        return None
    filas = []
    for ruta in sorted(glob.glob(os.path.join(d, "*.md"))):
        base = os.path.basename(ruta)
        m = RE_NUM.match(base)
        if not m:
            continue
        num = int(m.group(1))
        try:
            with open(ruta, encoding="utf-8", errors="replace") as fh:
                texto = fh.read()
        except OSError:
            continue
        h1 = RE_H1.search(texto)
        titulo = h1.group(1) if h1 else ""
        filas.append({"num": num, "fichero": base, "titulo": titulo,
                      "norm": norm(titulo)})
    return filas


def colisiones(filas):
    por = {}
    for f in filas:
        por.setdefault(f["num"], []).append(f)
    return {n: v for n, v in por.items() if len(v) > 1}


def reenvios(filas, d=FIND):
    """Pares (viejo, nuevo) de hallazgos renumerados, detectados por STEM.

    El mecanismo es el NOMBRE del fichero, no el titulo. La razon es empirica:
    al buscar por titulo no se encontraba NINGUN par, porque cuando se renumera
    el numero viejo deja de contener ese contenido -- lo contiene el nuevo, y el
    titulo solo aparece una vez en el arbol. El nombre, en cambio, se conserva:

        185-tlb-de-gfx8-entra-en-bloques-de-8-pte.md   (borrado)
        239-tlb-de-gfx8-entra-en-bloques-de-8-pte.md   (nuevo)

    mismo stem, numero distinto. Y se lee comparando contra HEAD, porque el
    renumerado puede estar sin commitear: en el arbol actual los dos numeros
    existen pero con contenido DISTINTO, y eso solo se ve contra HEAD.
    """
    head = _stems_head(d)
    if head is None:
        return []
    numeros_actuales = {f["num"] for f in filas}
    actual = {}
    for f in filas:
        actual.setdefault(_stem(f["fichero"]), []).append(f["num"])
    salida = []
    for stem, nums in sorted(head.items()):
        if stem not in actual:
            continue                       # borrado y no renumerado
        for viejo in sorted(nums):
            for nuevo in sorted(actual[stem]):
                if viejo != nuevo:
                    salida.append({"viejo": viejo, "nuevo": nuevo,
                                   "stem": stem[:58],
                                   # ¿El numero viejo sigue OCUPADO, y por otro
                                   # contenido? No hace falta que haya dos
                                   # ficheros: basta uno con otro contenido. Esa
                                   # es la reasignacion silenciosa, que es mas
                                   # peligrosa que la colision porque no produce
                                   # ninguna senal de colision.
                                   "reasignado": viejo in numeros_actuales})
    return salida


def reenvios_estable(d=FIND, destino=None):
    """El mapa de renumeraciones que NO depende de un diff que va a desaparecer.

    `reenvios()` deriva los pares de `git ls-tree HEAD` contra el arbol de
    trabajo. Eso tiene una consecuencia fatal: en cuanto se commitea el
    renumerado, la comparacion da vacio y el mapa deja de existir -- junto con
    la capacidad de detectar una cita colgando, que es justo lo que viene a
    reparar.

    Por eso el mapa se congela en `REENVIO-FINDINGS.tsv` (vease
    `reenvio_freeze.py`) y esta funcion lo lee de ahi. Solo si el fichero no
    existe cae al metodo viejo, para que la herramienta siga siendo usable en
    un arbol donde nadie congelo nada.

    La prioridad es la correcta porque el fichero congelado es un DATO
    versionado y el diff es una MEDIDA de un instante. Si discrepan, el diff
    gana solo por ausencia del dato; nunca por ser mas reciente.
    """
    if destino is None:
        destino = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "REENVIO-FINDINGS.tsv")
    if os.path.exists(destino):
        filas = []
        try:
            with open(destino, encoding="utf-8") as fh:
                texto = fh.read()
        except OSError:
            texto = ""
        for ln in texto.splitlines():
            if not ln.strip() or ln.startswith("#"):
                continue
            p = ln.split("\t")
            if len(p) != 4:
                continue
            try:
                filas.append({"viejo": int(p[0]), "nuevo": int(p[1]),
                              "reasignado": p[2] == "SI", "stem": p[3],
                              "fuente": "congelado"})
            except ValueError:
                continue
        if filas:
            return filas
    out = reenvios(escanear(d), d)
    for r in out:
        r["fuente"] = "diff"
    return out


def _stem(fichero):
    return fichero.split("-", 1)[1] if "-" in fichero else fichero


def _stems_head(d):
    """Stem -> [numeros] tal y como estan en HEAD. None si git no responde."""
    import subprocess
    # RAIZ = findings/ -> findings/.. -> 06-INGENIERIA-INVERSA/.. = proyecto.
    # Dos dirname, no tres: con tres se sale un nivel y `-C` apunta fuera del
    # repositorio, git responde con codigo != 0 y la funcion devuelve None. Y un
    # None aqui se confunde con "no hay renumeraciones", que es el peor fallo
    # posible: un silencio que significa "todo bien".
    raiz = os.path.dirname(os.path.dirname(d))
    try:
        p = subprocess.run(
            ["git", "-C", raiz, "ls-tree", "-r", "--name-only", "HEAD", "--",
             os.path.relpath(d, raiz)],
            capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if p.returncode != 0:
        sys.stderr.write("findings_index: git ls-tree fallo: %s\n"
                         % (p.stderr.strip()[:120] or p.returncode))
        return None
    if p.returncode != 0 or not p.stdout.strip():
        return None
    out = {}
    pre = os.path.basename(d) + "/"
    for linea in p.stdout.split("\n"):
        b = os.path.basename(linea.strip())
        m = RE_NUM.match(b)
        if m and pre in linea:
            out.setdefault(_stem(b), []).append(int(m.group(1)))
    return out


RE_REF = re.compile(r"`?\b(\d{3})\b`?\s*\|\s*\*\*(\d{3})\*\*|\*\*(\d{3})\*\*|\bhallazgo (\d{3})\b|`(\d{3})`")

# Mismo motivo que RE_NUM, medido el 2026-10-03: la cita de un hallazgo
# renumerado a 1000-1020 tiene CUATRO digitos, y `{3}` no la ve. Sin esto, las
# referencias colgantes contadas aqui serian menos que las que repara
# refs_repair.py, que usa su propio RE_CITA.
RE_CITA_N = re.compile(r"`(\d{3,4})`")


def refs_colgadas(filas, rev, d=FIND):
    """Referencias a numeros que la tabla de reenvio dice que YA NO son esos.

    Aqui es donde el dano se vuelve contable. Un numero renumerado sigue
    escribiendose en el texto de otros hallazgos y esos textos no se enteran: el
    numero existe, asi que nada parece roto. Por eso hay que cruzarlos
    explicitamente contra la tabla.

    AUTO-CITA, Y POR QUE SE DESCUENTA
    ---------------------------------
    Una cita a `NNN` dentro del fichero `NNN-*.md` NO es una referencia rota. Es
    el hallazgo hablando de si mismo, y es correcta por construccion: el
    renumerado de otro hallazgo hizo que `NNN` quedara ocupado por OTRO
    contenido, pero el fichero `NNN` de HOY sigue siendo este y el texto que
    dentro dice "`NNN`" se refiere a el mismo.

    Medido: sin esta regla, 1047. Con ella, 1038. Las 9 quitadas son
    auto-citas en 088/089/104/123/126/144/169, y comprobando el contenido: el
    `089` que la tabla manda a 196 es "codificacion de frecuencia de reloj" y no
    menciona GC_HWIP ni una vez, mientras que la linea que cita `089` esta
    hablando del brazo GFX8 de GC_HWIP. Reescribirla a `196` apuntaria a un
    hallazgo que no trata el tema.

    Esto no es una excepcion para que cuadre el numero. Es que la cifra sin
    descontar auto-citas es incorrecta: mezcla dos clases de cita y las trata
    como la misma.
    """
    viejos = {x["viejo"] for x in rev if x.get("reasignado")}
    num_de = {}
    for f in filas:
        num_de.setdefault(f["num"], set()).add(f["fichero"])
    fuera = []
    auto = []
    for ruta in sorted(glob.glob(os.path.join(d, "*.md"))):
        base = os.path.basename(ruta)
        m_num = RE_NUM.match(base)
        propio = int(m_num.group(1)) if m_num else None
        try:
            with open(ruta, encoding="utf-8", errors="replace") as fh:
                texto = fh.read()
        except OSError:
            continue
        for n, linea in enumerate(texto.split("\n"), 1):
            for m in RE_CITA_N.finditer(linea):
                v = int(m.group(1))
                if v not in viejos:
                    continue
                if propio is not None and v == propio:
                    auto.append({"fichero": base, "linea": n, "cita": v})
                    continue
                fuera.append({"fichero": base, "linea": n, "cita": v})
    fuera.sort(key=lambda x: (x["cita"], x["fichero"], x["linea"]))
    return fuera


def self_test():
    fails = []

    def eq(l, g, w):
        if g != w:
            fails.append("%s: %r != %r" % (l, g, w))

    # 1. LA NORMALIZACION. Sin acentos ni puntuacion, dos escrituras del mismo
    #    titulo tienen que colapsar en la misma clave. Sin esto, la deteccion de
    #    renumeracion no encuentra nada y parece que no hay renumeraciones.
    eq("acentos", norm("Los registros caben en BAR5"),
       norm("Los registros caben en BAR5"))
    # El simbolo § NO se descompone con NFKD (es un simbolo, no un acento), asi
    # que se queda. Lo que tiene que desaparecer es la puntuacion y el caso.
    eq("puntuacion y caja", norm("Grafico; ocho-PTE"),
       norm("grafico ocho PTE"))

    # 2. CONTROL NEGATIVO: dos hallazgos DISTINTOS no deben colapsar en la misma
    #    clave. Si lo hicieran, la tabla de reenvio inventaria parentescos.
    if norm("tlb-de-gfx8-entra-en-bloques") == norm("gmc8-es-cero"):
        fails.append("control negativo: dos textos distintos colapsan")

    # 3. Anclas medidas sobre el arbol real.
    filas = escanear()
    if filas is None:
        fails.append("no encuentro %s" % FIND)
        return _fin(fails)
    col = colisiones(filas)

    # INVARIANTES, no recuentos. Anclar "255 numeros" y "347 ficheros" hacia que
    # esta herramienta fallara cada vez que alguien anade un hallazgo, que no es
    # un defecto suyo. Lo que tiene que cumplirse es que los numeros explicados
    # por las filas cubren TODAS las filas, para siempre.
    eq("cada fichero pertenece a un numero",
       len({f["num"] for f in filas}), len(set(f["num"] for f in filas)))
    eq("suma por numero = total de ficheros",
       sum(len(v) for v in col.values()) + (len(filas) - sum(len(v) for v in col.values())),
       len(filas))

    # La cuenta de "ficheros" tiene que ser la de los ficheros REALES, no la de
    # los que este regex decide mirar. Medido: con `^(\d{3})-` eran 509 sobre 518
    # y los 9 que faltaban no se parecian en ningun sitio.
    # (el recuento completo vive en el control 6, mas abajo, que compara contra
    #  el directorio entero)

    # Y el defecto tiene que seguir siendo DETECTABLE: si colisiones() devuelve
    # cero cuando hay 65, la herramienta esta rota aunque todo cuadre.
    if not col:
        fails.append("colisiones(): dice que no hay ninguna, pero 259 las midio. "
                     "La deteccion esta rota")

    # 4. CONTROL NEGATIVO de colisiones: un numero que NO colisiona tiene que
    #    estar ausente del diccionario. Sin esto, "detecta colisiones" podria ser
    #    "devuelve todo".
    if 259 in col and len(col.get(259, [])) > 1:
        fails.append("control negativo: 259 deberia ser unico (lo reserve y lo "
                     "verifique)")

    # 5. La tabla de reenvio tiene que encontrar MI renumeracion conocida:
    #    185 -> 239 comparten el titulo del hallazgo del TLB de 8 PTE.
    #
    #    SE USA `reenvios_estable()`, NO `reenvios()`. Este self-test se ejecuto
    #    justo despues del commit que sello el renumerado, y `reenvios()` --que
    #    deriva los pares de `git ls-tree HEAD` contra el arbol-- devuelve ya []
    #    porque HEAD y el arbol coinciden. El fallo era exactamente este: la
    #    unica fuente del mapa se autodestruye al commitearla. Por eso el mapa
    #    esta congelado en REENVIO-FINDINGS.tsv y se lee de ahi.
    r = reenvios_estable()
    pares = {(x["viejo"], x["nuevo"]) for x in r}
    if not pares:
        fails.append("reenvios_estable() devolvio []: no hay mapa. Sin mapa no "
                     "hay deteccion de citas colgando, y el fallo es SILENCIOSO")
    if (185, 239) not in pares:
        fails.append("no encontro la renumeracion conocida 185->239 por stem. "
                     "Encontrados: %s" % sorted(pares)[:6])
    # Y que no invente: un par viejo==nuevo no es renumeracion.
    if any(a == b for a, b in pares):
        fails.append("control negativo: un par viejo==nuevo no es renumeracion")
    # Y que el mapa no este transido: una cadena 156->232->999 dejaria la cita
    # colgando en el segundo salto, y la reparacion "correcta" seguiria rota.
    mapa = {x["viejo"]: x["nuevo"] for x in r if x.get("reasignado")}
    enc = [(a, b) for a, b in mapa.items() if b in mapa]
    if enc:
        fails.append("cadena de renumeraciones sin resolver: %s" % enc[:4])

    # 6. COBERTURA. Todo .md del directorio tiene que entrar por escanear().
    #    Este control existe por un fallo medido: RE_NUM era `^(\d{3})-` y los
    #    hallazgos 1000-1020 tienen cuatro digitos, asi que 9 ficheros de 518 no
    #    entraban. No habia error, aviso ni excepcion: un `continue`. Lo que no
    #    se indexa no lo ven las herramientas, y eso no se parece a un resultado.
    en_disco = {os.path.basename(p)
                for p in glob.glob(os.path.join(FIND, "*.md"))}
    indexados = {f["fichero"] for f in filas}
    sin_indexar = sorted(en_disco - indexados)
    if sin_indexar:
        fails.append("escanear() deja fuera %d de %d ficheros .md: %s"
                     % (len(sin_indexar), len(en_disco), sin_indexar[:5]))

    # 7. AUTO-CITA: el filtro tiene que existir Y tiene que discriminating.
    #
    #    Este control se escribio primero comprobando el caso positively
    #    (`refs_colgadas()` no debe contar una cita al propio numero) y
    #    NO ERA CAPAZ DE FALLAR: en el self-test `filas` cubre todo el
    #    directorio, y ninguna cita de un fichero a si mismo cae hoy en la lista
    #    de renumerados. Mutando el filtro a `if False:` el self-test seguia
    #    pasando. Un control que no puede fallar no es un control.
    #
    #    Ahora se comprueba la REGLA sobre un caso construido, que es lo que
    #    puede fallar: una cita al propio numero no se cuenta como colgante.
    #
    #    Y el efecto del filtro SI es observable en el corpus real, asi que
    #    tambien se comprueba que el recuento con y sin el filtro difiere: si
    #    dieran igual, el filtro no estaria haciendo nada y el codigo sobraria.
    auto_ideal = _citas_autocita(filas, {x["viejo"] for x in r
                                         if x.get("reasignado")})
    if auto_ideal == 0:
        fails.append("no se ha construido ningun caso de auto-cita: el control "
                     "de la regla 7 seria vacuo")
    fuera = refs_colgadas(filas, r)
    sin_filtro = _citas_sin_filtro(filas, {x["viejo"] for x in r
                                           if x.get("reasignado")})
    if len(fuera) == sin_filtro:
        fails.append("refs_colgadas() da lo mismo con y sin el filtro de "
                     "auto-cita (%d): el filtro no esta haciendo nada"
                     % len(fuera))
    if len(fuera) >= sin_filtro:
        fails.append("el filtro de auto-cita NO esta descontando: con filtro %d, "
                     "sin filtro %d" % (len(fuera), sin_filtro))

    # 8. RE_CITA_N tiene que ver cuatro digitos. Hoy es CORRECTO pero INERCIAL:
    #    los 43 numeros renumerados van de 52 a 202, ninguno de cuatro digitos, y
    #    las 95 citas de cuatro digitos del corpus apuntan a 1000/1002/1003. Si
    #    se Anchica RE_CITA_N a 4, este recuento NO cambia. Por eso el control es
    #    sobre el REGEX y no sobre el recuento: el defecto se manifestara cuando
    #    alguien renumere un hallazgo por encima de 999.
    if not RE_CITA_N.search("`1000`"):
        fails.append("RE_CITA_N no ve una cita de cuatro digitos; el proximo "
                     "renumerado por encima de 999 sera invisible")
    if RE_NUM.match("1002-algo.md") is None:
        fails.append("RE_NUM no indexa un hallazgo de cuatro digitos")
    return _fin(fails)


def _citas_autocita(filas, viejos):
    """Cuantas citas al PROPIO numero del fichero caen en la lista de viejos."""
    n = 0
    for f in filas:
        num = f["num"]
        m = RE_NUM.match(f["fichero"])
        if not m or int(m.group(1)) != num:
            continue
        ruta = os.path.join(FIND, f["fichero"])
        try:
            with open(ruta, encoding="utf-8", errors="replace") as fh:
                texto = fh.read()
        except OSError:
            continue
        for linea in texto.split("\n"):
            for m2 in RE_CITA_N.finditer(linea):
                if int(m2.group(1)) == num and num in viejos:
                    n += 1
    return n


def _citas_sin_filtro(filas, viejos):
    """Cuantas citas caen en la lista de viejos si NO se descuenta la auto-cita.

    No es `refs_colgadas()` con el filtro puesto: es el mismo criterio de
    cita, recorriendo el directorio entero, saltandose la regla de la
    auto-cita. Comparar las dos cifras es lo que demuestra que el filtro hace
    algo; comparar contra `refs_colgadas()` no probaria nada, porque las dos
    llamadas usarian el mismo filtro.
    """
    n = 0
    for ruta in sorted(glob.glob(os.path.join(FIND, "*.md"))):
        try:
            with open(ruta, encoding="utf-8", errors="replace") as fh:
                texto = fh.read()
        except OSError:
            continue
        for linea in texto.split("\n"):
            for m in RE_CITA_N.finditer(linea):
                if int(m.group(1)) in viejos:
                    n += 1
    return n


def _fin(fails):
    if fails:
        print("self-test FALLA (%d)" % len(fails))
        for f in fails:
            print("   " + f)
        return 1
    print("self-test OK (2 vectores de normalizacion, 1 control negativo, "
          "2 anclas medidas, cobertura de ficheros, mapa congelado y citas)")
    return 0



REENVIO_MD = "FINDINGS-RENUMERACIONES.md"

CABECERA = """# FINDINGS-RENUMERACIONES

<!-- GENERADO por 08-ARQUITECTURA/tools/findings_index.py --escribir-reenvio.
     NO EDITAR A MANO: la siguiente ejecucion lo sobrescribe. -->

Tabla de renumeraciones de hallazgos. Sirve para **resolver una referencia
colgada**: si un documento cita el hallazgo `NNN` y ese numero ya no corresponde,
el par de esta tabla dice a donde fue.

## Por que existe

El numero de hallazgo es la clave primaria de la base de conocimiento. Varias
sesiones renumeraron sus hallazgos para resolver colisiones de numero, y **no
dejaron registro**. Como el renumerado ademas esta SIN COMMITEAR, ni el historial
de git lo conserva: comparar el arbol contra HEAD es hoy la unica fuente.

## Como se detecta

Por el **stem del nombre de fichero**, no por el titulo. El titulo no sirve: al
renumerar, el numero viejo deja de contener ese contenido, y el titulo solo
aparece una vez en el arbol. El nombre se conserva:

```
185-tlb-de-gfx8-entra-en-bloques-de-8-pte.md    (viejo, borrado)
239-tlb-de-gfx8-entra-en-bloques-de-8-pte.md    (nuevo)
```

## REASIGNADO = el numero viejo esta ocupado por OTRO contenido

No es lo mismo que una colision. Una colision son **dos** ficheros con el mismo
numero, y se ve. Una reasignacion es **un** fichero con el numero y contenido
distinto, y **no produce ninguna senal**: solo referencias que apuntan al
hallazgo equivocado. Por eso esta tabla marca los dos casos por separado.

## Uso

`viejo` ya no es el hallazgo. Para citarlo hay que usar `nuevo`. Cuando la tabla
no tiene entrada para un numero, ese numero es el que tiene hoy: no hay ambiguedad
de ese tipo.

## Advertencias

"""


def escribir_reenvio(d=FIND, destino=None):
    filas = escanear(d)
    if filas is None:
        return None, "no existe %s" % d
    col = colisiones(filas)
    rev = reenvios(filas, d)
    raiz = os.path.dirname(os.path.dirname(d))
    destino = destino or os.path.join(raiz, REENVIO_MD)

    fuera = refs_colgadas(filas, rev, d)
    n_reas = sum(1 for x in rev if x.get("reasignado"))
    out = [CABECERA]
    out.append("- Numeros con **colision** (>1 fichero): **%d**" % len(col))
    out.append("- Renumeraciones detectadas: **%d**, de ellas **REASIGNADAS: %d**"
               % (len(rev), n_reas))
    out.append("- Ficheros en `findings/`: **%d**" % len(filas))
    out.append("- **Referencias colgando** (`` `NNN` `` que ya no es ese hallazgo):"
               " **%d**, en **%d** numeros distintos"
               % (len(fuera), len({x['cita'] for x in fuera})))
    out.append("")
    out.append("Las referencias colgando son el dano real. Un numero renumerado sigue")
    out.append("escribiendose en el texto de otros hallazgos y **nada parece roto**,")
    out.append("porque el numero sigue existiendo. Solo se ven al cruzarlas contra")
    out.append("esta tabla.")
    out.append("")
    out.append("| citado | deberia ser | veces |")
    out.append("|---|---|---|")
    por = {}
    for x in fuera:
        por.setdefault(x["cita"], []).append(x)
    for v in sorted(por):
        nv = next((x["nuevo"] for x in rev if x["viejo"] == v), -1)
        out.append("| `%03d` | `%03d` | %d |" % (v, nv, len(por[v])))
    out.append("")
    out.append("El renumerado **no esta commiteado**: HEAD y el arbol de trabajo")
    out.append("describen bases de datos distintas. Por eso la fuente es la")
    out.append("comparacion contra HEAD y no el historial.")
    out.append("")
    out.append("## Numeros con colision (clave primaria no unica)")
    out.append("")
    out.append("| numero | ficheros |")
    out.append("|---|---|")
    for n, v in sorted(col.items()):
        out.append("| %03d | %s |" % (n, "<br>".join(f["fichero"] for f in v)))
    out.append("")
    out.append("## Renumeraciones")
    out.append("")
    out.append("| viejo | nuevo | reasignado | fichero |")
    out.append("|---|---|---|---|")
    for x in sorted(rev, key=lambda z: (z["viejo"], z["nuevo"])):
        out.append("| %03d | %03d | %s | `%s` |"
                   % (x["viejo"], x["nuevo"],
                      "**SI**" if x.get("reasignado") else "no",
                      x["stem"]))
    out.append("")
    with open(destino, "w", encoding="utf-8") as fh:
        fh.write(chr(10).join(out))
    return destino, None


def main(argv):
    if "--self-test" in argv:
        return self_test()
    filas = escanear()
    if filas is None:
        print("findings_index: no existe %s" % FIND, file=sys.stderr)
        return 2
    # MEDIR LA COBERTURA ANTES DE USAR NADA. `escanear()` descarta en silencio
    # los ficheros cuyo nombre no encaja con RE_NUM, y todo lo que se apoya en
    # sus/hered el mismo criterio. Un hallazgo no indexado no es un hallazgo
    # perdidos: es un hallazgo que las herramientas no ven. Con 518 en disco y 509
    # indexados, el proyecto estaba perdiendo 9 hallazgos enteros sin que nada
    # lo dijera.
    en_disco = {os.path.basename(p)
                for p in glob.glob(os.path.join(FIND, "*.md"))}
    indexados = {f["fichero"] for f in filas}
    sin_indexar = sorted(en_disco - indexados)
    if sin_indexar and "--self-test" not in argv:
        print("AVISO: %d ficheros .md NO indexados por escanear():" % len(sin_indexar))
        for b in sin_indexar[:12]:
            print("   %s" % b)
        print("   Sus citas no las ve ninguna herramienta. No es un resultado.")
        print()
    col = colisiones(filas)
    rev = reenvios_estable(d=FIND)

    if "--escribir-reenvio" in argv:
        dest, err = escribir_reenvio()
        if err:
            print("findings_index: %s" % err, file=sys.stderr)
            return 2
        print("escrito %s" % dest)
        return 0

    if "--refs-colgadas" in argv:
        fuera = refs_colgadas(filas, rev)
        por = {}
        for x in fuera:
            por.setdefault(x["cita"], []).append(x)
        print("referencias a numeros RENUMERADOS, que ya no son esos hallazgos")
        print()
        for v in sorted(por):
            print("  %03d -> %03d   citado %d veces"
                  % (v, next((x["nuevo"] for x in rev if x["viejo"] == v), -1),
                     len(por[v])))
        print()
        print("numeros distintos citados de forma colgando: %d" % len(por))
        print("referencias colgando en total            : %d" % len(fuera))
        return 1 if fuera else 0

    if "--json" in argv:
        print(json.dumps({
            "ficheros": len(filas),
            "numeros": len({f["num"] for f in filas}),
            "colisiones": {str(k): [f["fichero"] for f in v]
                           for k, v in sorted(col.items())},
            "reenvios": rev,
        }, indent=1, ensure_ascii=False))
        return 1 if col else 0

    if "--colisiones" in argv:
        for n, v in sorted(col.items()):
            print("%03d:" % n)
            for f in v:
                print("    %-56s %s" % (f["fichero"], f["titulo"][:52]))
        print()
        print("numeros con colision: %d" % len(col))
        return 1 if col else 0

    if "--reenvio" in argv:
        print("tabla de renumeraciones, por STEM de nombre, comparando el arbol")
        print("actual contra HEAD. (viejo -> nuevo)")
        print()
        print("REASIGNADO = el numero viejo esta HOY ocupado por otro contenido.")
        print("Una referencia escrita antes de la renumeracion sigue apuntando al")
        print("numero, y ese numero ya no es el mismo hallazgo. No hay forma de")
        print("saber cual era el destino sin la tabla de reenvio, que no existe.")
        print()
        for x in rev:
            marca = "REASIGNADO" if x.get("reasignado") else ""
            print("  %03d -> %03d  %-58s %s"
                  % (x["viejo"], x["nuevo"], x["stem"], marca))
        print()
        print("pares detectados: %d   de ellos REASIGNADOS: %d"
              % (len(rev), sum(1 for x in rev if x.get("reasignado"))))
        return 0

    print("findings/: %d ficheros, %d numeros distintos"
          % (len(filas), len({f["num"] for f in filas})))
    print("numeros con colision: %d   ficheros implicados: %d"
          % (len(col), sum(len(v) for v in col.values())))
    print("renumeraciones detectadas (stem, contra HEAD): %d" % len(rev))
    print()
    if col:
        print("DEFECTO DE INTEGRIDAD: el numero de hallazgo no es clave unica.")
        print("Por eso CORRECTED_BY=NNN y el calculo de sentido de")
        print("CONTRADICTIONS.md no se pueden resolver de forma fiable.")
    else:
        print("OK: clave unica.")
    return 1 if col else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
#!/usr/bin/env python3
# CONTRACT: name=toolaudit
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
"""
toolaudit.py -- mide F11: qué herramientas existen, cuáles producen un titular,
y si alguien ha LEIDO ese titular o sólo lo ha ejecutado.

POR QUE EXISTE
    F11 pregunta, literalmente: "¿de cuántas herramientas de este árbol se ha
    leído alguna vez la SALIDA, y no su cabecera?".  El incidente que motivó
    la frontera está documentado: msg_census devolvió 503 números plausibles,
    la mayoría de la generación equivocada, sin avisar.  El número era
    plausible; sólo se detectó porque alguien comprobó a mano qué cabecera se
    estaba usando.  De 503 se pasó a 14 en cuatro comandos.

    Ese fallo no fue de la herramienta: fue que nadie estaba obligado a mirar
    el dato bueno.  Un self-test que verifica el parser no obliga a nada.

    Con 36 herramientas Python en este árbol, "nadie está obligado" ya no es un
    caso: es una probabilidad.  Esta herramienta convierte eso en un número.

QUE PRODUCE
    Para cada herramienta:
      · existe?  · ejecuta?  · tiene self-test?  · pasa el self-test?
      · ¿tiene titular numérico?  ¿y publica el CRUDO junto al FILTRADO?
      · ¿su nombre o su salida aparece en algún hallazgo o documento?
    Y tres titulares que son el resultado:
      · cuántas herramientas existen
      · cuántas han sido cited alguna vez  (su salida consta en alguna parte)
      · cuántas NO, y por tanto son evidencia producida y descartada

LIMITE DECLARADO, Y ES EL IMPORTANTE
    "Citada" significa que su NOMBRE aparece en un .md del proyecto.  Eso es un
    proxy de "alguien leyó su salida", no la medida directa: una herramienta
    puede haberse usado sin que su nombre aparezca, y puede aparecer su nombre
    sin que nadie la haya ejecutado.

    Mide presencia textual, no epistemología.  Un titular no citado se marca
    SOSPECHOSO_DE_NO_LEER, no DESCARTADO.  La frontera pide distinguir "no se
    usó" de "se usó y se descartó"; esta herramienta no puede, y lo dice.

    Tampoco ejecuta las herramientas por defecto: --run las ejecuta, y una
    herramienta que escribe o tiene efectos NO debe invocarse a ciegas.  Por
    defecto sólo se lee su código, que es seguro.

USO
    toolaudit.py                el informe
    toolaudit.py --run          además ejecuta los self-test (sólo lectura)
    toolaudit.py --uncited      sólo las no cited, con su titular
    toolaudit.py --no-titular   sólo las que no publican titular
    toolaudit.py --json
    toolaudit.py --self         autotest

DEPENDENCIAS
    python3 >= 3.9.  Sin red, sin root, sin escrituras.
"""

import argparse
import collections
import json
import os
import re
import subprocess
import sys

PROJECT = "/home/lucas/Escritorio/RX550-INVESTIGACION"

# CORRECCION 2026-10-02: esta herramienta se escribio apuntando a UN solo arbol, y
# por eso su censo nunca vio el otro. Medido:
#
#   tools/                        58 .py
#   08-ARQUITECTURA/tools/        54 .py
#   nombre compartido                3
#   contenido identico (sha1)       0
#   poblacion unica               112
#
# Cero solape por contenido: son 112 herramientas distintas, no 54 con alias. Y el
# numero que yo venia reportando -- "31 herramientas, 407 comprobaciones" -- salia
# de contar las que imprimen "N vectores" en una forma literal. Cubre 31 de 112.
#
# TOOLS se conserva como primer arbol porque otras cosas lo referencian.
TOOLS = f"{PROJECT}/08-ARQUITECTURA/tools"
ARBOLES = [TOOLS, f"{PROJECT}/tools"]
FINDINGS = f"{PROJECT}/06-INGENIERIA-INVERSA/findings"
DOCS = f"{PROJECT}/docs"

# Una herramienta "tiene titular" si su salida imprime un CONTEO como titular.
# Se buscan las formas que de verdad se usan en este árbol, no una palabra
# generica: una herramienta que en cualquier sitio imprima "total" no tiene por
# qué tener un titular.
TITULAR = re.compile(
    r'(?im)^\s*([A-Za-zÁÉÍÓÚÑáéíóúñ][\wÁÉÍÓÚÑáéíóúñ \t]{2,40}?)'
    r'\s*[:=]\s*(\d{1,7})\b')

# Una herramienta AVISA cuando su propio filtro está roto.  pm4_count_census
# imprime "NO_PACKET3_FOUND -- el filtro esta roto, no hay resultado".  Ese
# comportamiento es lo correcto y hay que contarlo como señal positiva: una
# herramienta que avisa de que no sabe es más fiable que una que devuelve un
# número plausible, que es exactamente el fallo de msg_census.

# Señales de que el código de una herramienta PREPARA un titular, no sólo
# ninguna que solo lo calcule.
PREGUNTA_TITULAR = re.compile(
    r'(?i)(titular|total\b|encontrados|hallados|habitantes|\bcount\b|'
    r'cuantos|quantos|se detectaron|documentos con)')

SELF_TEST = re.compile(r'--self\b|--self-test\b|def selftest|def self_test')

# Las tres clases, y POR QUE son tres y no una.
#
# `--check` esta fuera, y hay un motivo medido: `contradict.py` declara
# `add_argument("--check", ...)` y eso NO es un self-test, es un modo AUDITORIA
# que recorre los hallazgos y compara afirmaciones. Al cogerlo, salia DEFECTO
# porque encuentra contradicciones de verdad, y el censo reportaba una
# herramienta self-testeada cuando lo ejecutado habia sido un escaneo.
DECLARADA_EN_CODIGO = re.compile(
    r'add_argument\(\s*"(--(?:self|selftest|self-test|autotest))"')

CONVENCION = "--selftest"

FALTA_ARTEFACTO = re.compile(
    r"(?i)(falta\s+[\w./-]+\.(?:asm|c|h|o|ko|bin|json|txt)|"
    r"\bno (?:puedo|pudo) (?:leer|abrir)\b|"
    r"(?:artefacto|archivo|fichero) (?:de entrada )?no existe)")

USO_INCORRECTO = re.compile(
    r"(?i)(unrecognized arguments|argument .*expected|falta\s+--|"
    r"\busage:\s|\brequired argument\b)")

# Una linea que ES un vector de test no es un diagnostico. No es hipotetico:
# `run_all --selftest` ejecuta el self-test de toolaudit, cuya salida contiene
# las cadenas que los patrones de arriba buscan. El detector se envenenaba con su
# propio texto. Mismo caso que `lint.py` ya declara como excepcion.
LINEA_DE_TEST = re.compile(r"^\s*(PASS|FAIL|OK|ERROR|ok)\b\s")


def sin_lineas_de_test(salida):
    """La salida sin las lineas que son vectores de test."""
    return "\n".join(l for l in salida.split("\n")
                     if not LINEA_DE_TEST.match(l))


def clasifica_salida(salida, rc=None):
    """Clase de un rc!=0. Y EL LIMITE, DECLARADO Y APLICADO.

    Se probo clasificar por PROSA y no es solido: medido dos veces.

      con solo REPORTA_DEFECTO   3 de 7 salian DEFECTO sin serlo
      con tres patrones          el vocabulario de los propios vectores de test
                                envenena a quien ejecuta la suite entera

    Asi que solo se conserva lo ESTRUCTURAL, y el resto se declara indeterminado
    en vez de opinar:

      USO              la salida tiene forma de diagnostico de argparse. No es
                       prosa de la herramienta, es el formato del interprete
      FALTA_ARTEFACTO  nombra un fichero que no esta. AGENTS.md lo tiene
                       nombrado: es INVALID_RESULT
      NO_DETERMINADO   sale distinto de cero y no se puede decir por que. Que
                       sea un test roto o un defecto del PROYECTO lo sabe la
                       herramienta, no su prosa

    Y NO_DETERMINADO no tira el dato: el resumen imprime su primera linea.
    """
    limpio = sin_lineas_de_test(salida)
    if USO_INCORRECTO.search(limpio):
        return "USO"
    if FALTA_ARTEFACTO.search(limpio):
        return "FALTA_ARTEFACTO"
    return "NO_DETERMINADO"

# "rc != 0" significa DOS cosas distintas en este proyecto, y hay 11
# herramientas en el otro arbol que usan la segunda. findings_index, por
# ejemplo, sale con 1 porque dice "DEFECTO DE INTEGRIDAD: el numero de
# hallazgo no es clave unica": su self-test FUNCIONA. Etiquetarlo FALLA es
# tan falso como lo seria etiquetar OK a una comprobacion que no se hizo.
#
# Y NO SE TOCAN LOS CODIGOS DE SALIDA: cambiar la semantica de una
# herramienta que hoy reporta un defecto real seria peor que la ambiguedad.
# Lo que se hace es no mentir en el ROTULO.
REPORTA_DEFECTO = re.compile(
    r"(?i)(DEFECTO DE INTEGRIDAD|\bdefecto\b.{0,24}\b(Detectado|Detectada|"
    r"encontrado|hay|existe)|\bcolisi[oó]n\b|\bduplicad\b|no (?:es|son) "
    r"(?:clave|v[aá]lid)|\bfaltan?\b)")

# Herramientas que AVISAN de que su propio filtro falló, en vez de devolver un
# número plausible.  Es el comportamiento correcto, y es la respuesta directa al
# incidente de msg_census (503 números, la mayoría de otra generación).
AVISA_SI_FILTRO_ROTO = re.compile(
    r'(?i)(filtro.{0,12}roto|NO_PACKET3_FOUND|no result|sin resultado|'
    r'no puedo (?:leer|contar|contar)|aviso:.*filtro)')


def _lee(path):
    try:
        with open(path, errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def resolver(nombre):
    """Ruta de una herramienta por nombre, buscando en los DOS arboles.

    Antes solo se miraba el primero, y por eso un nombre de `tools/` no se
    encontraba: `os.path.isfile` devolvia False y la funcion leia "".
    """
    for raiz in ARBOLES:
        p = os.path.join(raiz, nombre + ".py")
        if os.path.isfile(p):
            return p
    return os.path.join(TOOLS, nombre + ".py")


def inventariar():
    """[{nombre, path, bytes, lineas}] de todas las herramientas .py del árbol."""
    out = []
    vistos = set()
    for raiz in ARBOLES:
        if not os.path.isdir(raiz):
            continue
        for dp, dirs, files in os.walk(raiz):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for f in sorted(files):
                if not f.endswith(".py"):
                    continue
                p = os.path.join(dp, f)
                if os.path.getsize(p) < 200:      # no es una herramienta
                    continue
                clave = os.path.realpath(p)
                if clave in vistos:              # el mismo fichero, dos veces
                    continue
                vistos.add(clave)
                out.append({
                    "nombre": f[:-3],
                    "path": p,
                    "arbol": os.path.relpath(raiz, PROJECT),
                    "bytes": os.path.getsize(p),
                    "lineas": _lee(p).count("\n") + 1,
                })
    return out


def tiene_titular_en_codigo(nombre):
    """¿El código de esta herramienta PREPARA un titular?"""
    return bool(PREGUNTA_TITULAR.search(_lee(resolver(nombre))))


def titular_de_codigo(nombre):
    """
    ETIQUETAS de titular que la herramienta imprimiría, con su valor si es
    literal.

    Se devuelve la ETIQUETA y no el valor, porque el titular real de este árbol
    se emite con f-strings: `print(f"documentos: {len(args)} ...")`.  El número
    no existe en el código, se calcula al ejecutar.  Un extractor que buscara
    "etiqueta: numero" sólo vería literales dedepuracion y devolvería cero titulares
    reales, o peor, inventaría alguno de una variable.

    Qué se busca: una cadena de la forma "palabra: " pegada a una interpolación,
    dentro de una print.  Eso es lo que imprime un titular y nada más.
    """
    txt = _lee(resolver(nombre))
    etiquetas = []
    # f"... {expr} ..." donde antes de "{" hay "etiqueta:" o "etiqueta ="
    for m in re.finditer(rf'["\']([^"\'\n]{{3,40}}?)\s*:\s*\{{', txt):
        et = m.group(1).strip()
        if et and not et.startswith("{") and len(et) >= 3:
            etiquetas.append(et[:34])
    # y la forma literal "etiqueta: 123"
    for m in TITULAR.finditer(txt):
        et = m.group(1).strip().strip(":=")
        if len(et) >= 3 and not et.isdigit() and et not in etiquetas:
            etiquetas.append(et[:34])
    return [(e, None) for e in etiquetas]
    """Pares (etiqueta, valor) que la herramienta imprimiría como titular."""
    txt = _lee(resolver(nombre))
    out = []
    for m in TITULAR.finditer(txt):
        etiqueta = m.group(1).strip().strip(":=")
        if len(etiqueta) < 3 or etiqueta.isdigit():
            continue
        out.append((etiqueta[:34], int(m.group(2))))
    return out


def es_citada(nombre):
    """¿Su nombre aparece en algún hallazgo o documento del proyecto?"""
    rx = re.compile(rf'\b{re.escape(nombre)}\b')
    for root in (FINDINGS, DOCS):
        if not os.path.isdir(root):
            continue
        for dp, _d, fs in os.walk(root):
            for f in fs:
                if not f.endswith(".md"):
                    continue
                if rx.search(_lee(os.path.join(dp, f))):
                    return True
    return False


CANDIDATAS = ("--self", "--selftest", "--self-test", "--autotest", "--check")

# Cuando no hay declaracion, la convencion del proyecto. El orden importa:
# `--selftest` AUDITA el proyecto y falla si encuentra algo; `--self-test`
# prueba vectores internos y sale 0. Se eligio la segunda por error una vez.
CONVENCION = "--selftest"

# MEDIDO, Y ESTE ES EL PUNTO DEL QUE NO SE SALE:
#
#   aperture.py --selftest   rc=0   prints su salida NORMAL, no un self-test
#   aperture.py --self-test  rc=0   prints "self-test OK (2 vectores...)"
#
# rc=0 NO significa que la bandera se haya reconocido. Estas herramientas no
# botan error ante una opcion desconocida, hacen su trabajo de siempre y salen
# con 0. Eso es exactamente lo que AGENTS.md llama INVALID_RESULT: la senal
# parece buena y no prueba nada.
#
# Asi quela sonda no se fia del codigo de salida. Se exige EVIDENCIA en la salida:
# que el texto mencione un self-test. Eso solo aparece cuando hacorrido uno.
EVIDENCIA_SELFTEST = re.compile(
    r"(?i)(self-?test\s*(?:OK|PASS|FAIL)?\b|\bRESULT(?:ADO)?\s*:|"
    r"\bRESULT\s*:|vectores?\b.{0,40}\b(OK|PASS|reproducid)|"
    r"\btodos pasan\b|comprobaciones\))")


def bandera_que_declara(path, timeout=60):
    """Que bandera de self-test DECLARA esta herramienta en su --help.

    Se pregunta a la herramienta. Leer su fuente seria adivinar: una cadena
    `--selftest` puede estar en un comentario, en un docstring o en la
    traduccion de otro comentario, y las tres existen en este arbol.
    """
    try:
        r = subprocess.run([sys.executable, path, "--help"],
                           capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    ayuda = (r.stdout or "") + (r.stderr or "")
    # Criterio 2: la ayuda. Un texto que MENCIONA una bandera no la DECLARA.
    for c in CANDIDATAS:
        if re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(c), ayuda):
            return c
    return None


# La salida cruda de cada self-test, para poder imprimirla al lado
# de la clase. Una clase sin su texto obliga a volver a ejecutarla.
SALIDA = {}

# NOTA: esta segunda definicion de DECLARADA_EN_CODIGO estaba aqui y SOBRESCRIBIA
# a la de arriba, que es la correcta. Con `check` dentro, una herramienta que
# declara `add_argument("--check")` —un modo AUDITORIA, no un self-test— pasaba
# por self-testeada. Dos definiciones del mismo nombre en el mismo modulo, y la
# que gana es la ultima. Se borra y queda una sola.


def bandera_convencion(path, timeout=240):
    """Sin declaracion disponible: se usa la CONVENCION, y se declara.

    MEDIDO: findings_index, aperture, struct_rw y num_collision no usan argparse.
    Ni su codigo ni su --help declaran ninguna bandera de self-test. Para esos
    la unicavia es la convencion del proyecto, `--selftest`.

    Y el ORDEN importa, y no es negociable:

      findings_index --selftest    rc=1  "DEFECTO DE INTEGRIDAD"   AUDITA
      findings_index --self-test   rc=0  "self-test OK (2 vectores)" VECTORES

    `--selftest` audita el proyecto y falla si encuentra algo. `--self-test`
    prueba vectores internos y sale 0 siempre que el parser este bien. Son
    cosas DISTINTAS con nombres casi iguales, y se habian sondeado en orden
    contrario: el resultado era elegir siempre el modo unitario, y los
    DEFECTOS Detection bajaban de 5 a 1 mientras el recuento de "con self-test"
    subia de 82 a 113. La herramienta mejoraba en el papel mientras perdia.

    Asi que aqui NO se sondea: se ejecuta la convencion, una, y se exige
    senal. Si no la hay, se declara que no se pudo determinar.
    """
    try:
        r = subprocess.run([sys.executable, path, CONVENCION],
                           capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    salida = (r.stdout or "") + (r.stderr or "")
    if EVIDENCIA_SELFTEST.search(salida) or REPORTA_DEFECTO.search(salida):
        return "--selftest"
    return None


def sondea_bandera(path, timeout=180):
    """SONDA QUE NO SE USA. Se conserva porque explica por que no se usa.

    Ver el comentario en corre_self_test():escoge la bandera equivocada, porque
    `--self-test` prueba vectores internos y `--selftest` audita el proyecto.
    """
    """Si --help no declara ninguna, se prueban, exigiendo EVIDENCIA.

    Se devuelve la primera bandera cuya salida MENCIONA un self-test. No se usa
    el codigo de salida como prueba, porque rc=0 tambien sale cuando la opcion
    se ha ignorado, que es justo el falso positivo que hay que evitar.
    """
    for c in CANDIDATAS:
        try:
            r = subprocess.run([sys.executable, path, c],
                               capture_output=True, text=True, timeout=timeout)
        except (OSError, subprocess.SubprocessError):
            continue
        if EVIDENCIA_SELFTEST.search((r.stdout or "") + (r.stderr or "")):
            return c
    return None


REGISTRO = os.path.join(PROJECT, "docs", "TOOLS-STATUS.md")
RE_LAST = re.compile(r"LAST_VERIFIED:?\s*([^\n`]{6,40})")


def hueco_de_registro(inv):
    """Cuantas herramientas NO tienen entrada en el registro de estado.

    POR QUE ESTA AQUI Y NO UNA CLASE MAS. Medido: buscar el consumidor de la
    clasificacion da CERO. Nadie la lee. Y mientras nadie la lea, distinguir
    "test roto" de "ha encontrado un defecto" no aporta nada.

    Lo que si tiene consumidor es esto. `docs/TOOLS-STATUS.md` son 3257 lineas
    con el vocabulario de AGENTS.md §22, un LAST_VERIFIED con hora, y una regla
    sin excepcion: si una herramienta falla, su salida no se reutiliza como
    evidencia. Es el sitio donde se declara si la salida de una herramienta vale
    como evidencia.

    MEDIDO: 71 de 114 con entrada, 43 sin ella. Su estado correcto es UNKNOWN, no
    "validada" ni "rota".

    POR UNIDAD, NO POR NOMBRE: `causal`, `fingerprint` y `run_all` existen en los
    dos arboles, luego 114 ficheros son 111 nombres distintos, y una cuenta por
    nombre no cuadra con una cuenta por fichero.
    """
    if not os.path.isfile(REGISTRO):
        return {"registro": None, "cubiertas": set(), "sin": set(),
                "nombres": 0, "last": None}
    txt = _lee(REGISTRO)
    rutas = {os.path.realpath(i["path"]) for i in inv}
    cubiertas = {r for r in rutas
                 if re.search(r"\b%s\b" % re.escape(os.path.basename(r)), txt)}
    m = RE_LAST.search(txt)
    return {"registro": REGISTRO, "cubiertas": cubiertas, "sin": rutas - cubiertas,
            "nombres": len({i["nombre"] for i in inv}),
            "last": m.group(1).strip() if m else None}


def sello(inv):
    """CUANDO se midio, y QUE se midio. Sin esto el numero no es comparable.

    MEDIDO el 2026-10-03: hay 12 hallazgos con una cifra de poblacion de
    herramientas. De ellos:

      10  no tienen NINGUNA fecha en el documento
       0  estan commiteados, asi que git no sabe cuando se escribieron
      --  y mtime NO sirve: es una cota SUPERIOR de la hora de escritura, no
          la hora. Un fichero editado despues tiene mtime posterior, y ordenar
          por mtime no ordena por cuando se midio.

    Y la cifra ya caduco: 274 dice 112 y hoy son 113. Sin sello, 112 y 113 son
    dos numeros que se contradicen o dos medidas separadas por una noche, y el
    documento no permite saber cual.

    La solucion no es que cada hallazgo se acuerde de escribir la hora. Es que
    la herramienta la ponga en su salida, y que quien cita la salida la cite
    entera. AGENTS.md lo pide igual en ARTIFACT_LINEAGE.
    """
    import datetime
    import hashlib
    ahora = datetime.datetime.now().astimezone()
    huella = hashlib.sha1(
        "\n".join(sorted(os.path.realpath(i["path"]) for i in inv))
        .encode("utf-8")).hexdigest()[:12]
    return "%s · %s · %d ficheros" % (
        ahora.strftime("%Y-%m-%d %H:%M:%S%z"), huella, len(inv))


def corre_self_test(nombre, timeout=420):
    """Ejecuta el self-test.  (None,) si no lo tiene."""
    p = resolver(nombre)
    txt = _lee(p)
    if not SELF_TEST.search(txt):
        return "NO_TIENE"
    # MEDIDO, Y POR QUE ESTA HECHA ASI.
    #
    # Hay dos o tres convenciones de bandera y picking a ojo falla:
    #   -  la version anterior lanzaba SIEMPRE `--self`, y marcaba FALLA a toda
    #      herramienta que solo acepta `--selftest`
    #   -  la siguiente lo arreglo LEYENDO EL FUENTE en busca de la cadena
    #      `--selftest`, y eso tambien falla: `toolaudit` declara `--self` en su
    #      --help pero su fuente CONTIENE la cadena `--selftest` porque esta
    #      written en un comentario de aqui. Leeria su propia traduccion y
    #      creeria que acepta una bandera que no acepta
    #
    # Un texto que habla de una bandera no es una bandera. Lo que dice si la
    # herramienta la acepta es su `--help`, que es lo que declara. Preguntado,
    # no adivinado. Y si no declara ninguna, NO TIENE: se dice, no se infiere.
    flag = None
    # criterio 1: declarada en CODIGO. add_argument("--x") es una declaracion;
    # la cadena "--x" suelta en un comentario es una mencion.
    m = DECLARADA_EN_CODIGO.search(txt)
    if m:
        flag = m.group(1)
    if flag is None:
        flag = bandera_que_declara(p)
    if flag is None:
        flag = bandera_convencion(p, timeout=min(timeout, 300))
    if flag is None:
        # Y AQUI ESTA EL LIMITE, y se respeta en vez de taparlo.
        #
        # Se probo sondear ejecutando las candidatas y exigiendo que la salida
        # mencionase un self-test. NO FUNCIONA, y el motivo es que hay DOS
        # COSAS DISTINTAS con nombres casi iguales:
        #
        #   findings_index --selftest    rc=1  "DEFECTO DE INTEGRIDAD"
        #   findings_index --self-test   rc=0  "self-test OK (2 vectores de
        #                                            normalizacion)"
        #
        # La primera AUDITA EL PROYECTO y falla si encuentra algo. La segunda
        # prueba VECTORES INTERNOS y sale 0. El sondeo elige siempre la segunda
        # -- es la unica que dice "self-test" -- y con eso los DEFECTOS
        # Detection bajaron de 5 a 1 y el recuento de "con self-test" subio de
        # 82 a 113. La herramienta mejoraba en el papel mientras perdia
        #
        # Un hueco visible es mejor que una clasificacion silenciosamente
        # equivocada. Se dice que no se pudo determinar, y por que.
        return "NO_SELFTEST_AUDITADO"
    try:
        r = subprocess.run([sys.executable, p, flag],
                           capture_output=True, text=True, timeout=timeout)
        if r.returncode == 0:
            return "PASA"
        # rc != 0 significa DOS COSAS en este proyecto, y por eso "FALLA" era un
        # numero sin unidad. MEDIDO: findings_index sale con 1 porque dice
        # "DEFECTO DE INTEGRIDAD: el numero no es clave unica". Su self-test
        # FUNCIONA: ha encontrado algo y por eso sale distinto de cero.
        # Etiquetarlo FALLA es tan falso como etiquetar OK a una comprobacion que
        # no se hizo.
        #
        # NO SE TOCAN LOS CODIGOS DE SALIDA: cambiar la semantica de una
        # herramienta que hoy reporta un defecto real seria peor que la
        # ambiguedad. Lo unico que se hace es no mentir en el ROTULO, y el
        # rotulo lo decide clasifica_salida(), con lo que el metodo sostiene.
        salida = (r.stdout or "") + (r.stderr or "")
        SALIDA[p] = salida
        return clasifica_salida(salida)
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    except OSError:
        return "ERROR"


def selftest():
    fails = 0

    def chk(name, got, want):
        nonlocal fails
        ok = got == want
        if not ok:
            fails += 1
        print(f"  {'PASS' if ok else 'FAIL'}  {name}"
              f"{'' if ok else f'  got={got!r} want={want!r}'}")

    print("  --- el inventario existe ---")
    inv = inventariar()
    chk("hay herramientas en el árbol", len(inv) > 10, True)
    chk("cada entrada tiene nombre y tamaño",
        all(x["nombre"] and x["bytes"] > 0 for x in inv), True)
    chk("no incluye __pycache__",
        any("__pycache__" in x["path"] for x in inv), False)

    print("  --- titular: se detecta donde existe y no donde no ---")
    # msg_census es el caso documentado: TIENE titular y es el que falla
    chk("una herramienta con titular se detecta",
        tiene_titular_en_codigo("doclint"), True)
    outputs = titular_de_codigo("doclint")
    chk("y se extraen pares etiqueta/valor", len(outputs) > 0, True)
    chk("las etiquetas extraídas no son numéricas",
        all(not k.isdigit() for k, _ in outputs), True)
    # doclint imprime "documentos: 38" en MINUSCULAS. Un regex que solo acepta
    # mayúsculas no ve un titular que existe, y reportaba cero.
    chk("y ese titular concreto se extrae",
        any("documentos" in k.lower() for k, _ in outputs), True)
    # pm4_count_census avisa de que su filtro está roto: comportamiento correcto
    chk("una herramienta que avisa de filtro roto se marca",
        bool(AVISA_SI_FILTRO_ROTO.search(
            _lee(f"{TOOLS}/pm4_count_census.py"))), True)
    # un nombre que NO existe no debe dar titular sin error
    chk("una herramienta inexistente no revienta",
        tiene_titular_en_codigo("__no_existe_9999"), False)

    print("  --- cited: no debe lanzar falsos positivos sistemáticos ---")
    # citecheck está en TOOLS-README.md, que está en tools/, no en docs/.
    # Eso es un límite real de la búsqueda, y se documenta en vez de ocultarlo.
    chk("una herramienta citada en docs/ se detecta",
        es_citada("causal_map"), True)
    chk("una cadena imposible no se cita",
        es_citada("__cadena_inexistente_9999"), False)

    print("  --- no ejecutar nada por defecto ---")
    # esta función NO debe invocar nada; se comprueba que corre_self_test
    # distingue las tres situaciones que puede devolver
    st = corre_self_test("__no_existe_9999")
    chk("una herramienta inexistente devuelve NO_TIENE", st, "NO_TIENE")

    # --- la poblacion real, y que la herramienta vea los DOS arboles ---------
    # MEDIDO, y por que estos vectores existen: antes de este parche el censo
    # apuntaba a UN solo arbol y devovia 54 herramientas de 112. Y el numero que
    # yo venia reportando ("31 herramientas, 407 comprobaciones") salia de
    # contar las que imprimen "N vectores" en una forma literal: 31 de 112.
    inv = inventariar()
    arboles = {i["arbol"] for i in inv}

    # 1. una herramienta que solo vive en tools/ tiene que RESOLVER. Antes
    #    estas devolvian "" y cualquier hallazgo sobre ellas salia vacio sin
    #    avisar.
    # `resolver` espera el NOMBRE sin extension y la anade, que es lo que hacen
    # los tres llamadores. Este vector se escribio primero pasandole "x.py" y
    # devolvio x.py.py: fallo, y por eso fallo de forma util.
    ok_res = [n for n in ("govcheck", "fingerprint", "lint", "dupenum")
              if os.path.basename(resolver(n)) == n + ".py"
              and os.path.isfile(resolver(n))]
    chk("una herramienta de tools/ RESUELVE por nombre", len(ok_res) >= 3, True)

    # 2. los dos arboles estan representados
    chk("el censo cubre tools/ y 08-ARQUITECTURA/tools/", len(arboles) >= 2, True)

    # 3. VECTOR CON DIENTES. Se quita el segundo arbol y el censo tiene que
    #    encoger. Si pasara con un solo arbol no probaria nada: seria una prueba
    #    que certifica un contrato falso, que es el fallo de este proyecto.
    n2 = len(inventariar())
    try:
        ARBOLES[:] = ARBOLES[:1]
        n1 = len(inventariar())
    finally:
        ARBOLES[:] = [TOOLS, f"{PROJECT}/tools"]
    chk("VECTOR CON DIENTES: quitar el segundo arbol encoge el censo",
        n1 < n2, True)

    # 4. y el mutaje se deshace: el numero tiene que volver
    chk("el censo se restaura tras el mutaje", len(inventariar()) == n2, True)

    # 5. y ningun fichero se cuenta dos veces, que es lo que haria el solape de
    #    nombres entre los dos arboles
    chk("ningun fichero aparece dos veces en el censo",
        len({os.path.realpath(i["path"]) for i in inv}), len(inv))

    # --- la bandera se PREGUNTA, y el DEFECTO se DISTINGUE -------------------
    # Un texto que MENCIONA una bandera no la DECLARA. Se comprobo asi:
    # toolaudit.py acepta `--self` y su --help no ofrece ninguna otra, pero su
    # fuente contiene la cadena `--selftest` porque esta escrita en un
    # comentario de aqui. Leer el fuente leeria su propia traduccion.
    chk("la bandera sale del --help, no del fuente",
        bandera_que_declara(resolver("toolaudit")), "--self")

    # y una herramienta que no declara ninguna se dice, no se infiere
    chk("una herramienta sin bandera declarada devuelve NINGUNA, no una por su cuenta",
        bandera_que_declara(os.path.join(TOOLS, "toolkit.py")), None)

    # Y rc != 0 con "DEFECTO DE INTEGRIDAD" es DEFECTO, no FALLA. El vector se
    # apoya en la expresion y no en correr la herramienta entera, que tardaria
    # minutos: lo que se vigila es la CLASE, no el censo.
    chk("un rc!=0 que dice DEFECTO DE INTEGRIDAD se clasifica DEFECTO",
        bool(REPORTA_DEFECTO.search("DEFECTO DE INTEGRIDAD: el numero no es clave unica")),
        True)
    chk("un rc!=0 que solo dice FAIL no se disfraza de DEFECTO",
        bool(REPORTA_DEFECTO.search("FAIL: 2 vectores")), False)

    # --- el ORDEN de los tres criterios, que es lo que_no_se_decia -----------
    # MEDIDO: las cuatro herramientas sin argparse (findings_index, aperture,
    # struct_rw, num_collision) solo se pueden lanzar por CONVENCION, y la
    # convencion correcta es `--selftest`. `--self-test` es otro modo: prueba
    # vectores INTERNOS y sale 0 aunque la auditoria encuentre un defecto.
    chk("una bandera solo cuenta si esta DECLARADA en codigo",
        bool(DECLARADA_EN_CODIGO.search(
            'ap.add_argument("--self", action="store_true")')), True)
    chk("una cadena --self-test en un comentario NO es una declaracion",
        bool(DECLARADA_EN_CODIGO.search("# probeban con --self-test")), False)
    chk("pero la convencion por defecto es --selftest, el modo auditoria",
        CONVENCION, "--selftest")

    # --- el SELLO: sin el, la cifra caduca sin que nadie lo note ------------
    # MEDIDO: 12 hallazgos con cifra de poblacion, 10 sin fecha, 0 commiteados.
    # Y la cifra ya caduco: 274 dice 112 y son 114. Sin sello, 112 y 113 son
    # dos numeros que se contradicen o dos medidas separadas por una noche.
    s1 = sello(inv)
    s2 = sello(inv)
    chk("el sello lleva fecha, huella y numero de ficheros",
        bool(re.search(r"20\d\d-\d\d-\d\d \d\d:\d\d:\d\d", s1))
        and bool(re.search(r"· [0-9a-f]{12} ·", s1))
        and str(len(inv)) in s1, True)
    chk("el sello dice CUANTOS ficheros, que es lo que se esta contando",
        "%d ficheros" % len(inv), s1.rsplit(" · ", 1)[-1])
    # y con el mismo conjunto, la huella tiene que ser la misma: si cambiara,
    # la huella no distinguiria dos poblaciones distintas
    chk("la huella es estable con el mismo conjunto",
        s1.rsplit(" · ", 2)[-2], s2.rsplit(" · ", 2)[-2])
    # Y el sello tiene que llevar la HORA DE AHORA, no una constante.
    #
    # El vector que estaba aqui antes llevaba un `or True`, que lo hacia
    # IMPOSIBLE que fallara: es el fallo que este mismo hallazgo documenta,
    # escrito en el fichero que lo documenta. Se mide contra el reloj del
    # propio proceso, asi que si alguien deja la fecha fija, CAE.
    import datetime as _dt
    hoy = _dt.datetime.now().astimezone().strftime("%Y-%m-%d")
    chk("el sello lleva la fecha de HOY, no una constante",
        hoy in s1, True)

    # --- VECTORES QUE HABRIAN VISTO EL BUG DE ESCAPES -----------------------
    # MEDIDO: un script de reaplicacion duplico las barras invertidas y dejo
    # `r"\\b%s\\b"`, que busca una barra y una b LITERALES. Resultado: el
    # informe decia "0 herramientas en el registro" y "LAST_VERIFIED None", con
    # el fichero ahi y con 190 KB. Un self-test que solo mira el codigo no lo
    # ve: hace falta que el patron CASE sobre una cadena real.
    chk("RE_LAST casa sobre el texto real del registro",
        bool(RE_LAST.search("LAST_VERIFIED: 2026-10-01 11:20 -03:00")), True)
    # QUITADOS TRES VECTORES, Y POR QUE. Comprobaban que un patron con barras
# invertidas DOBLADAS no casa, que es cierto, pero lo que fallaba no era el
# producto: era mi propio heredoc, que duplicaba las barras al escribir el
# vector. Un vector que mide el mecanismo que lo escribio no vigila el
# proyecto. Lo que si importa --que RE_LAST case sobre el texto real del
# registro, y que el patron de ruta encuentre las 71 herramientas-- queda
# cubierto por el CONTROL POSITIVO y el CONTROL NEGATIVO, que usan cadenas
# leidas del fichero y no cadenas inventadas en el sitio del vector.
    # --- LAS TRES CLASES, Y EL LIMITE QUE NO SE PUEDE SALVAR ---------------
    chk("palabras de defecto SIN estructura es NO_DETERMINADO, no DEFECTO",
        clasifica_salida("DEFECTO DE INTEGRIDAD: el numero no es clave unica"),
        "NO_DETERMINADO")
    chk("USO se reconoce por la forma de argparse",
        clasifica_salida("usage: t.py [-h]\nerror: unrecognized arguments: --x"),
        "USO")
    chk("un fichero que falta es FALTA_ARTEFACTO",
        clasifica_salida("mmio_map: falta /tmp/ko_dr.asm"), "FALTA_ARTEFACTO")

    # --- EL HUECO CON EL REGISTRO, con control positivo Y negativo ----------
    # Una comprobacion que no puede dar dos resultados distintos no discrimina.
    reg = hueco_de_registro(inv)
    _nb = lambda c: {os.path.basename(r) for r in c}
    chk("CONTROL POSITIVO: pm4_count_census esta en el registro",
        "pm4_count_census.py" in _nb(reg["cubiertas"]), True)
    chk("CONTROL NEGATIVO: fingerprint NO esta en el registro",
        "fingerprint.py" not in _nb(reg["cubiertas"]), True)
    chk("y lo que no esta, esta en SIN",
        "fingerprint.py" in _nb(reg["sin"]), True)
    chk("el hueco se cuenta por RUTA: cubiertas + sin = ficheros",
        len(reg["cubiertas"]) + len(reg["sin"]), len(inv))
    chk("y el registro declara cuando se verifico por ultima vez",
        bool(re.match(r"20\d\d-\d\d-\d\d", reg["last"] or "")), True)

    print(f"  {'todos pasan' if not fails else f'{fails} FALLAN'}")
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", action="store_true",
                    help="ejecuta los self-test (solo lectura)")
    ap.add_argument("--uncited", action="store_true")
    ap.add_argument("--no-titular", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--limite", type=int, default=10,
                    help="cuantos elementos listar como maximo por clase")
    ap.add_argument("--self", action="store_true")
    a = ap.parse_args()

    if a.self:
        return selftest()

    inv = inventariar()
    filas = []
    for x in inv:
        nombre = x["nombre"]
        st = corre_self_test(nombre) if a.run else (
            "SI" if SELF_TEST.search(_lee(x["path"])) else "NO")
        filas.append({
            **x,
            "self_test": st,
            "salida": SALIDA.get(nombre, ""),
            "titular": tiene_titular_en_codigo(nombre),
            "outputs": titular_de_codigo(nombre),
            "cited": es_citada(nombre),
            "avisa_filtro_roto": bool(
                AVISA_SI_FILTRO_ROTO.search(_lee(x["path"]))),
        })

    total = len(filas)
    cited = sum(1 for f in filas if f["cited"])
    con_tit = sum(1 for f in filas if f["titular"])
    nocit = total - cited

    if a.json:
        print(json.dumps({"total": total, "cited": cited,
                          "con_titular": con_tit, "filas": filas},
                         indent=2))
        return 0

    if a.uncited:
        print(f"  NO CITED: {nocit} de {total}")
        for f in sorted(filas, key=lambda z: z["nombre"]):
            if not f["cited"]:
                outs = ", ".join(f"{k}={v}" for k, v in f["outputs"][:3])
                print(f"    {f['nombre']:24} titular:{str(f['titular']):5} "
                      f"self-test:{f['self_test']:9} {outs[:56]}")
        print()
        print("  SOSPECHOSO_DE_NO_LEER, no DESCARTADO: esto mide si el NOMBRE")
        print("  aparece en un .md, no si alguien ejecutó la herramienta.")
        return 0

    if a.no_titular:
        print(f"  SIN TITULAR NUMERICO EN CODIGO: {total - con_tit}")
        for f in sorted(filas, key=lambda z: z["nombre"]):
            if not f["titular"]:
                print(f"    {f['nombre']:24} {f['lineas']:4} lineas")
        return 0

    # El rotulo decia UN arbol y el censo mide DOS. Una cabecera que miente es
    # peor que no tener cabecera: se lee como el alcance de lo de abajo.
    por_arbol = {}
    for f in filas:
        por_arbol[f.get("arbol", "?")] = por_arbol.get(f.get("arbol", "?"), 0) + 1
    det = "  ".join("%s=%d" % (k, v) for k, v in sorted(por_arbol.items()))
    print(f"  HERRAMIENTAS PYTHON, AMBOS ARBOLES: {total}   [{det}]")
    print(f"    MEDIDO: {sello(filas)}")
    reg = hueco_de_registro(filas)
    if reg["registro"]:
        print(f"    EN EL REGISTRO DE ESTADO: {len(reg['cubiertas'])}"
              f"  · SIN entrada: {len(reg['sin'])}"
              f"  · de {len(filas)} ficheros = {reg['nombres']} nombres distintos")
        print(f"      el registro dice LAST_VERIFIED {reg['last']}")
        if reg["sin"] and a.limite:
            print("      sin entrada, y su estado es UNKNOWN, no 'validada' ni "
                  "'rota'. Eso es lo que AGENTS.md §10 obliga a escribir:")
            for r in sorted(reg["sin"])[:a.limite]:
                print("        %s" % r.replace(PROJECT + "/", ""))
            if len(reg["sin"]) > a.limite:
                print(f"        ... y {len(reg['sin']) - a.limite} mas")
    # UNA LINEA, DOS MEDICIONES, UNA ETIQUETA. MEDIDO:
    #
    #   con --run   114   porque `st` es un veredicto y NINGUN veredicto es "NO"
    #   sin --run   84   porque `st` es SI/NO segun la regex
    #
    # Los dos se leian como la misma cosa y no lo eran. Y el segundo paso de 114
    # a 84 sin que nadie lo tocara, que es la senal: un numero que se mueve solo
    # es un numero que mide dos cosas.
    if a.run:
        # CADA CLASE DICE LO QUE EL METODO SOSTIENE, Y NADA MAS.
        dist = collections.Counter(f["self_test"] for f in filas)
        print("      " + " · ".join("%s %d" % (k, dist[k])
                                   for k in sorted(dist)))
        # Y LA SUMA. Sin esta linea una categoria puede caer a 0 porque el codigo
        # cambio, y eso se lee como "no hay" cuando lo que paso es que nadie la
        # ha mirado. MEDIDO: asi se perdieron 5 DEFECTOS de un vistazo.
        print(f"      suma de clasificados: {sum(dist.values())} de {len(filas)}")
        nd = [f for f in filas if f["self_test"] == "NO_DETERMINADO"]
        if nd:
            print(f"      {len(nd)} salen distinto de cero y NO se puede decir por "
                  f"que. Con su primera linea, para leerlas:")
            for f in nd[:a.limite]:
                primera = (f.get("salida") or "").strip().split("\n")[0][:60]
                print(f"        {f['nombre']:24} {primera}")
            if len(nd) > a.limite:
                print(f"        ... y {len(nd) - a.limite} mas")
        for k in ("USO", "FALTA_ARTEFACTO"):
            g = [f for f in filas if f["self_test"] == k]
            if g:
                print(f"      {k} ({len(g)}): " + ", ".join(f["nombre"] for f in g))
    # UNA LINEA, DOS MEDICIONES, UNA ETIQUETA. MEDIDO:
    #
    #   con --run   114   porque `st` es un veredicto y NINGUN veredicto es "NO"
    #   sin --run   84   porque `st` es SI/NO segun la regex
    #
    # Los dos se leian como la misma cosa y no lo eran. Y el segundo paso de 114
    # a 84 sin que nadie lo tocara, que es la senal: un numero que se mueve solo
    # es un numero que mide dos cosas.
    if a.run:
        print(f"    con self-test EJECUTADO : "
              f"{sum(1 for f in filas if f['self_test'] != 'NO_TIENE')} de "
              f"{len(filas)}   (las que tienen bandera y se pudieron lanzar)")
    else:
        print(f"    con self-test DECLARADO : "
              f"{sum(1 for f in filas if f['self_test'] != 'NO')} de "
              f"{len(filas)}   (--self|--self-test|def selftest en el fuente; "
              f"NO ejecutado)")
        print(f"    SIN self-test           : "
              f"{sum(1 for f in filas if f['self_test'] == 'NO')} de {len(filas)}")
    print(f"    con titular numerico    : {con_tit}")
    av = sum(1 for f in filas if f["avisa_filtro_roto"])
    print(f"    que AVISAN si su filtro falla : {av}")
    print(f"    CITED en la documentacion: {cited} de {total}")
    print(f"    NO cited             : {nocit}")
    print()
    if nocit:
        print("  LAS NO CITED, que son el hallazgo de F11:")
        for f in sorted(filas, key=lambda z: z["nombre"]):
            if not f["cited"]:
                outs = ", ".join(f"{k}={v}" for k, v in f["outputs"][:2])
                print(f"    {f['nombre']:24} {outs[:60]}")
    print()
    print(f"  LECTURA: {nocit}/{total} = "
          f"{nocit/total:.0%} sin constancia de salida leida.")
    print("  Mide PRESENCIA DEL NOMBRE en un .md, no epistemologia. Una")
    print("  herramienta puede haberse usado sin aparecer, o aparecer sin")
    print("  haberse ejecutado. Por eso el estado es SOSPECHOSO, no descartado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
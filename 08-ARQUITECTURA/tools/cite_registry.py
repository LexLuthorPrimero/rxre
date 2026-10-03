#!/usr/bin/env python3
# CONTRACT: name=cite_registry
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MODIFIES_CORPUS=no
# CONTRACT: PURPOSE="Inventario de herramientas de citas: que PREGUNTA responde cada una, y donde colisionan los nombres"
# CONTRACT: SELF_TEST=--self-test
# CONTRACT: VALIDATION=TOOL_VALIDATED
"""cite_registry.py -- que herramienta de citas responde a que pregunta.

POR QUE EXISTE

    Hay 114 ficheros de herramientas en cuatro directorios, y nueve de ellos
    tienen "cit" o "xref" en el nombre. Con nueve herramientas para lo que
    parece una tarea, lo razonable es sospechar duplicacion. Y aqui NO hay
    duplicacion: hay CUATRO preguntas distintas a las que el proyecto ha
    llamado "cita" con la misma palabra.

    Eso es peligroso de una forma que la duplicacion no lo es. Con duplicacion
    se pierde trabajo. Con cuatro-preguntas-un-nombre, cada respuesta dice "las
    citas estan verificadas" sin decir CONTRA QUE. Dos herramientas pueden
    discrepar y ambas tener razon, porque responden a cosas distintas.

    Este registro no unifica nada. Hace que la distincion sea legible por
    maquina, que es lo unico que se puede hacer sin decidir por otra sesion.

LO QUE NO HACE, Y POR QUE

    NO clasifica por lo que el nombre del fichero sugiere. Lo clasifica por la
    PREGUNTA que la herramienta dice responder en su propio encabezado, y
    imprime esa linea junto al veredicto. La palabra clave es un indice de
    busqueda, no una autoridad: si una herramienta cambia su encabezado, el
    veredicto puede quedarse viejo y la linea de arriba lo delata.

    NO presume que las cuatro preguntas cubren todo. Si algo queda sin cubrir,
    lo dice; no lo rellena.
"""
import hashlib
import os
import re
import sys

ROOT = "/home/lucas/Escritorio/RX550-INVESTIGACION"

# Los cuatro directorios. NO se descubren "los que hay": se declaran, para que
# un directorio nuevo sea una decision visible y no un olvido silencioso.
TOOL_DIRS = [
    "08-ARQUITECTURA/tools",
    "tools",
    "RESEARCH/polaris12xl/tools",
    "04-IMPLEMENTACION/tools",
]

# Las CUATRO preguntas. La clave es el discriminante; el valor es lo que la
# herramienta tiene que resolver para que la pregunta esté contestada.
PREGUNTAS = {
    "RESOLUBILIDAD": (
        "la cita apunta a un fichero y una linea que existen"),
    "RELEVANCIA_TARGET": (
        "el fichero citado pertenece a un ASIC que ESTA GPU ejecuta"),
    "CALIDAD_DE_CITA": (
        "la cita esta bien escrita, no solo bien apuntada"),
    "PROCEDENCIA": (
        "el dato viene de otro documento/commit y hay que atribuirlo"),
}
# Orden de discriminacion: la palabra mas especifica gana. "RESOLUBILIDAD" es la
# mas debil -- "resuelve" aparece en casi todas las descripciones -- asi que se
# prueba la ultima.
#
# `\basic\b` lleva limites de palabra POR UNA RAZON MEDIDA: sin ellos, "asic"
# matchea dentro de "clasico", y xref.py -- que no tiene nada que ver con la
# relevancia de ASIC -- se clasificaba como RELEVANCIA_TARGET. Un patron sin
# limites finds subcadenas, y una subcadena no es una palabra.
DISCRIMINANTES = [
    ("RELEVANCIA_TARGET", r"\basic\b|target|esta gpu|que ejecuta"),
    ("CALIDAD_DE_CITA", r"\bambig|como se citan|calidad|estilo|normaliza"),
    ("PROCEDENCIA", r"procedencia|commit|atribuir|otro trabajo|otra ia"),
    ("RESOLUBILIDAD", r"resuelve|verifica que cada cita|apunte"),
]

RE_HEAD = re.compile(
    r'(?:"""|\'\'\')\s*\n?\s*(?:--|-)?\s*([A-Za-z0-9_]+\.(?:py|sh))\s*[-—]+\s*(.+)')


def sha1(ruta):
    h = hashlib.sha1()
    with open(ruta, "rb") as fh:
        for bloque in iter(lambda: fh.read(65536), b""):
            h.update(bloque)
    return h.hexdigest()


def encabezado(ruta):
    """La primera linea que dice que hace la herramienta, tal cual."""
    return _cabecera(ruta)[0]


def _cabecera(ruta, lineas=25):
    """(linea de resumen, bloque de cabecera) de una herramienta.

    Son DOS cosas y estan separadas a proposito. La linea de resumen es lo que
    se muestra: una frase, para que un humano pueda juzgarla. El bloque es lo
    que se USA para clasificar, y son SOLO las primeras `lineas` lineas.

    Dos errores se cometieron aqui antes de llegar a esta forma, y los dos
    produjeron falsos:

    1 · clasificar sobre la sola resumen, que en la mayoria de las
        herramientas es generica ("audita TODAS las citas del proyecto") y no
        contiene el discriminante. Decia que ninguna herramienta contestaba
        RELEVANCIA_TARGET, cuando citegen.py la contesta.

    2 · clasificar sobre el TEXTO ENTERO, que incluye el codigo. Entonces una
        herramienta que devuelve la cadena "AMBIGUOUS" se clasificaba como
        CALIDAD_DE_CITA por una palabra que aparece en su cuerpo, no en lo que
        dice hacer. Un clasificador que lee el codigo en vez de la
        documentacion no esta midiendo la pregunta de la herramienta: esta
        midiendo sus variables.

    El bloque son las primeras lineas por una razon concreta: es donde vive la
    docstring, que es lo que declara el propósito.
    """
    try:
        with open(ruta, encoding="utf-8", errors="replace") as fh:
            texto = fh.read(8192)
    except OSError:
        return "", ""
    m = RE_HEAD.search(texto)
    resumen = m.group(2).strip() if m else ""
    if not resumen:
        for linea in texto.split("\n")[:lineas]:
            s = linea.strip().lstrip("#").strip()
            if len(s) > 24 and "SPDX" not in s and "CONTRACT:" not in s:
                resumen = s
                break
    bloque = chr(10).join(texto.split("\n")[:lineas])
    return resumen, bloque


def clasificar(bloque):
    """Que PREGUNTA contesta, por el discriminante mas especifico que matche."""
    bajo = bloque.lower()
    for nombre, patron in DISCRIMINANTES:
        if re.search(patron, bajo):
            return nombre
    return "SIN_CLASIFICAR"


def es_herramienta_de_citas(nombre, desc):
    """Si esta herramienta responde a alguna de las preguntas de citacion.

    POR QUE `scope` NO ESTA en la lista, aunque `treescope.py` si lo este:
    se puso `scope` para coger treescope y cayo `scopeguard.py` y
    `smc_copy_scope.py`, que no tienen nada que ver con citar. Un filtro por
    nombre que coge de mas no es un filtro: es una lista de suposiciones. Se
    nombra el fichero que se queria y nada mas.
    """
    return bool(re.search(r"cit|xref|doclint|treescope", nombre + " " + desc,
                          re.I))


def inventariar():
    """[{dir, nombre, sha1, bytes, desc, pregunta}] para todo lo ejecutable."""
    filas = []
    for d in TOOL_DIRS:
        base = os.path.join(ROOT, d)
        if not os.path.isdir(base):
            continue
        for f in sorted(os.listdir(base)):
            if not f.endswith((".py", ".sh")):
                continue
            ruta = os.path.join(base, f)
            if not os.path.isfile(ruta):
                continue
            desc, bloque = _cabecera(ruta)
            filas.append({
                "dir": d, "nombre": f, "sha1": sha1(ruta),
                "bytes": os.path.getsize(ruta),
                "desc": desc, "bloque": bloque,
                "pregunta": clasificar(bloque),
            })
    return filas


def colisiones(filas):
    """Mismo nombre en varios sitios. Se separa CONFLICTO de COPIA.

    Es la distincion que decide si algo esta roto. Dos ficheros con el mismo
    nombre y distinto hash son dos herramientas que se contradicen segun el
    directorio desde el que se mire; dos con el mismo hash son el mismo
    fichero en dos sitios, que es redundancia y no contradiccion.
    """
    por_nombre = {}
    for f in filas:
        por_nombre.setdefault(f["nombre"], []).append(f)
    out = []
    for nombre, grupo in sorted(por_nombre.items()):
        if len(grupo) < 2:
            continue
        hashes = {g["sha1"] for g in grupo}
        if len(hashes) == 1:
            out.append(("COPIA", nombre, grupo))
        else:
            out.append(("CONFLICTO", nombre, grupo))
    return out


def selftest():
    """Tres direcciones: un caso real que DEBE contar, dos que NO.

    Un detector de colisiones que solo sabe decir "si" marca todo y no informa;
    uno que solo sabe decir "no" no detecta nada. Las dos mitades van juntas.
    """
    fallos = []
    filas = inventariar()

    # (1) el caso real DEBE detectarse. xref.py existe en dos directorios con
    #     hash distinto, comprobado antes con md5sum fuera de esta herramienta.
    conf = [(k, n) for k, n, g in colisiones(filas) if k == "CONFLICTO"]
    if not any(n == "xref.py" for _k, n in conf):
        fallos.append("no detecta el conflicto real de xref.py")
    if not any(n == "xref.py" for k, n, _g in colisiones(filas)
               if k == "CONFLICTO"):
        fallos.append("xref.py no aparece como CONFLICTO")

    # (2) lo unico NO debe marcarse. Si se marcara, el detector no informa.
    por_nombre = {}
    for f in filas:
        por_nombre.setdefault(f["nombre"], []).append(f)
    unicos = [n for n, g in por_nombre.items() if len(g) == 1]
    marcados = {n for _k, n, _g in colisiones(filas)}
    falsos = [n for n in unicos if n in marcados]
    if falsos:
        fallos.append("marca como colision un nombre unico: %s" % falsos[:3])

    # (3) un fichero real NO debe clasificarse como herramienta de citas.
    for f in filas:
        if f["nombre"] == "corpus_guard.py" and es_herramienta_de_citas(
                f["nombre"], f["desc"]):
            fallos.append("corpus_guard.py clasificado como herramienta de citas")

    # (4) y el control de que la clasificacion NO sea vacia: si ningun
    #     encabezado se lee, todas caerian en SIN_CLASIFICAR y el test pasaria
    #     sin comprobar nada.
    if all(not f["desc"] for f in filas):
        fallos.append("ningun encabezado se lee: la clasificacion es vacia")

    # (5) RESPUESTA CONOCIDA. Es el control que faltaba, y su ausencia costo un
    #     negativo falso: la herramienta decia que RELEVANCIA_TARGET no lo
    #     cubria nadie, y citegen.py lo cubre ("de cada cita, si el fichero
    #     citado es de un ASIC que esta GPU ejecuta"). Un self-test que solo
    #     comprueba que no hay CRASH puede pasar mientras la herramienta afirma
    #     un hueco que no existe: no hay crash en mentir.
    conocidos = {
        "citegen.py": "RELEVANCIA_TARGET",
        "citecheck.py": "RESOLUBILIDAD",
    }
    for nombre, esperada in conocidos.items():
        fila = [f for f in filas if f["nombre"] == nombre]
        if not fila:
            fallos.append("control de respuesta conocida: %s no esta en el"
                          " inventario, y el control ya no comprueba nada"
                          % nombre)
            continue
        if not any(f["pregunta"] == esperada for f in fila):
            fallos.append("%s deberia clasificar como %s y sale %s"
                          % (nombre, esperada,
                             [f["pregunta"] for f in fila]))

    # (6) y el negativo de ese control: una herramienta que NO es de citas no
    #     puede aparecer en ninguna de las cuatro preguntas.
    for f in filas:
        if f["nombre"] == "corpus_guard.py" and \
                f["pregunta"] != "SIN_CLASIFICAR":
            fallos.append("corpus_guard.py clasificado en %s, y no es una"
                          " herramienta de citas" % f["pregunta"])

    if fallos:
        print("AUTOTEST FALLA:")
        for f in fallos:
            print("   %s" % f)
        return 1
    print("autotest OK (%d filas, %d colisiones, 4 controles con caso real"
          " y dos negativos)" % (len(filas), len(colisiones(filas))))
    return 0


def main(argv):
    if "--self-test" in argv or "--self" in argv:
        return selftest()
    filas = inventariar()

    if "--colisiones" in argv:
        col = colisiones(filas)
        print("COLISIONES DE NOMBRE ENTRE DIRECTORIOS DE HERRAMIENTAS")
        print()
        if not col:
            print("  ninguna")
        for clase, nombre, grupo in col:
            print("  %-10s %s" % (clase, nombre))
            for g in grupo:
                print("      %-26s %s  %d B  %s"
                      % (g["dir"], g["sha1"][:12], g["bytes"],
                         g["desc"][:44]))
        print()
        conf = sum(1 for k, _n, _g in col if k == "CONFLICTO")
        print("CONFLICTOS %d   COPIAS %d   (un CONFLICTO son dos"
              " herramientas que se contradicen)" % (conf, len(col) - conf))
        return 1 if conf else 0

    if "--guardio" in argv or "--fijar" in argv:
        # POR QUE UN GUARDIAN Y NO UN "0 CONFLICTOS".
        # Hay 3 conflictos hoy y estan registrados en C-015: no se arreglan
        # aqui porque son una decision de coordinacion entre sesiones. Un check
        # que exija cero falla SIEMPRE, y un check que falla siempre no informa
        # de nada: la gente deja de mirarlo y ahi si que se pierde una
        # colision nueva.
        # Asi que el check es de REGRESION: las 3 conocidas se aceitan y se
        # listan, y CUALQUIER conflicto NUEVO hace fallar la construccion.
        #
        # Y el base se escribe desde el fichero, no desde la cuenta: un numero
        # no dice que conflictos son, asi que al revivir la linea no se sabe
        # cual se ha añadido.
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "cite_registry.base")
        conf = sorted(n for k, n, _g in colisiones(filas) if k == "CONFLICTO")
        if "--fijar" in argv:
            with open(base, "w", encoding="utf-8") as fh:
                fh.write("# conflictos CONOCIDOS, escritos por --fijar.\n")
                fh.write("# uno por linea. C-015 los registra; no se arreglan aqui.\n")
                for n in conf:
                    fh.write("%s\n" % n)
            print("base fijada con %d conflictos: %s"
                  % (len(conf), " ".join(conf)))
            return 0
        try:
            with open(base, encoding="utf-8") as fh:
                connu = {l.strip() for l in fh
                         if l.strip() and not l.startswith("#")}
        except OSError:
            print("no hay base: ejecuta --fijar primero")
            return 2
        nuevos = [n for n in conf if n not in connu]
        print("CONFLICTOS %d   conocidos %d   NUEVOS %d"
              % (len(conf), len(connu), len(nuevos)))
        for n in conf:
            print("   %-22s %s" % (n, "conocido (C-015)" if n in connu
                                   else "** NUEVO **"))
        if nuevos:
            print()
            print("FALLA: %d conflicto(s) nuevo(s). Registralo antes de"
                  " seguir; un nombre repetido con hash distinto hace que"
                  " cualquiera que lo invoque no sepa cual ejecuta." % len(nuevos))
            return 1
        return 0

    if "--preguntas" in argv:
        print("QUE PREGUNTA RESPONDE CADA HERRAMIENTA DE CITAS")
        print()
        citas = [f for f in filas if es_herramienta_de_citas(f["nombre"],
                                                            f["desc"])]
        for nombre in sorted(PREGUNTAS):
            grupo = [f for f in citas if f["pregunta"] == nombre]
            print("  %s  (%s)" % (nombre, PREGUNTAS[nombre]))
            if not grupo:
                # NO se dice "hueco de cobertura". Eso es una afirmacion, y este
                # instrumento no la sostiene: es un indice por palabra, y ya ha
                # producido dos negativos falsos (decia que RELEVANCIA_TARGET no
                # lo cubria nadie, y citegen.py lo cubre) y dos positivos falsos
                # (xref.py por la subcadena "asic" dentro de "clasico"). Una
                # pregunta sin herramienta CLASIFICADA no es una pregunta sin
                # respuesta: es una pregunta que este indice no ha reconocido.
                print("      NINGUNA CLASIFICADA -- no es un hueco probado:")
                print("      el clasificador es un indice por palabra y ya ha")
                print("      producido falsos. Ver SIN_CLASIFICAR antes de concluir.")
            for g in sorted(grupo, key=lambda x: x["nombre"]):
                print("      %-22s %-26s %s" % (g["nombre"], g["dir"],
                                                g["desc"][:52]))
            print()
        sin = [f for f in citas if f["pregunta"] == "SIN_CLASIFICAR"]
        print("SIN_CLASIFICAR: %d  (su encabezado no encaja en ninguna"
              " pregunta; NO se asignan por parecido)" % len(sin))
        for g in sin:
            print("   %-24s %-26s %s" % (g["nombre"], g["dir"], g["desc"][:52]))
        print()
        print("herramientas de citas: %d de %d totales, en %d directorios"
              % (len(citas), len(filas), len(TOOL_DIRS)))
        return 0

    # Resumen por defecto.
    print("herramientas: %d en %d directorios" % (len(filas), len(TOOL_DIRS)))
    for d in TOOL_DIRS:
        n = sum(1 for f in filas if f["dir"] == d)
        print("   %-30s %d" % (d, n))
    print("colisiones de nombre: %d" % len(colisiones(filas)))
    print()
    print("usa --preguntas o --colisiones")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
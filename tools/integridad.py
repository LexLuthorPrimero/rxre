#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
integridad.py -- control de integridad y de propiedad de la banda de hallazgos.

POR QUE EXISTE
--------------
Llevo toda la linea reportando «N ficheros, 0 duplicados» contando ficheros
ajenos como mios. Hay 7 ficheros en la banda 900+ que declaran
CORPUS=RESEARCH/working/, que es el corpus de otro agente, y mi control los
contaba como evidencia propia.

Un control que valida tu trabajo contando el trabajo de otro como tuyo no es un
control que falle: es un control que DA EL LIMPIO FALSO. Y el limpio falso es el
resultado mas peligroso posible, porque parece que todo esta bien.

QUE HACE
--------
Clasifica cada hallazgo de la banda por lo que DECLARA, no por el numero:

    MIO       no declara CORPUS, o declara el corpus propio
    AJENO     declara un corpus que no es el propio
    SIN_DECL  declara CORPUS=sin o similar: no se sabe de quien es

Y despues:
    - detecta numeros duplicados DENTRO de mi conjunto
    - detecta ficheros vacios
    - detecta texto no latino
    - FALLA si hay duplicados, vacios, texto no latino, o ficheros sin declarar

La clave: los duplicados y el resto de controles se evaluan SOLO sobre lo mio.
Un duplicado entre dos ficheros ajenos no es mi problema y no debe hacer fallar
mi control, igual que un fallo suyo no es mi evidencia.

ESTADO: VALIDATED con --self-test
WORK_CLASS: READ_ONLY. Solo lee.
"""

import io
import os
import re
import sys
import glob

VERSION = "2.3.0"

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FINDINGS_REL = "06-INGENIERIA-INVERSA/findings"

# Mi corpus. El unico que me pertenece para layout y para codigo.
CORPUS_PROPIO = "RESEARCH/kernelbuild/linux-7.1.3"

# Mi identidad de autor. La declaro en cada hallazgo mio para que la propiedad
# sea VERIFICABLE y no un hecho que solo existe en mi cabeza: sin esto, la
# herramienta puede probar la no pertenencia pero nunca la pertenencia, y un
# "---> OK" se leeria como una certificacion que no es.
AUTORIA_PROPIA = "AGENTE-SMU"

# Valores que significan "no he declarado corpus". Se comparan SIN sensibilidad
# a la caja (ver el arreglo de 969 mas abajo), asi que da igual como se escriba.
SENTINELA_CORPUS = ("sin", "ninguno", "sin cambios", "-", "n/a")

# Banda que reservo. Los numeros de esta banda son mios por convencion.
BANDA = re.compile(r"^9\d\d-")

NO_LATINA = re.compile(
    "[\u2E80-\u9FFF\uAC00-\uD7AF\uF900-\uFAFF"
    "\uFF00-\uFF60\u3000-\u303F\u3040-\u30FF"
    "\u0400-\u04FF\u0600-\u06FF]")

# Palabras inglesas que en un texto en espanol casi siempre son un tic.
INGLES = re.compile(
    r"\b(finds|deriving|writes|reads|shows|takes|makes|gives|uses|calls|holds"
    r"|means|needs|knows|gets|sets|goes|runs|ends|located|resolved|hunted"
    r"|candidates|oriented)\b")


def corpus_declarado(ruta):
    """El valor de CORPUS en la cabecera, o None si no lo declara.

    Se lee SOLO de las primeras lineas: una CORPUS en mitad de un hallazgo
    puede ser parte de una cita, no su declaracion.
    """
    try:
        with io.open(ruta, encoding="utf-8", errors="replace") as f:
            for i, l in enumerate(f):
                if i > 40:
                    return None
                # el valor va HASTA el siguiente campo o separador, no hasta
                # el primer espacio: "CORPUS=sin cambios" es un valor legitimo,
                # y leer solo "sin" produce un SIN_DECL inventado
                m = re.search(r"CORPUS\s*=\s*(.*?)(?=\s+[A-Z][A-Z_]+\s*=|\s*\u00b7|$)", l)
                if m:
                    return m.group(1).strip()
    except (IOError, OSError):
        return None
    return None


def autoria_declarada(ruta):
    """El valor de AUTORIA en la cabecera, o None si no lo declara."""
    try:
        with io.open(ruta, encoding="utf-8", errors="replace") as f:
            for i, l in enumerate(f):
                if i > 40:
                    return None
                m = re.search(r"AUTORIA\s*=\s*(.*?)(?=\s+[A-Z][A-Z_]+\s*=|\s*\u00b7|$)", l)
                if m:
                    return m.group(1).strip()
    except (IOError, OSError):
        return None
    return None


def clasificar(ruta, corpus_propio, autoria_propia):
    """La propiedad se decide por AUTORIA, no por CORPUS.

    CORPUS mide procedencia de cambios de corpus, no autoria: 25 hallazgos del
    otro agente no modifican el corpus y por eso no declaran ninguno, y eso los
    hace indistinguibles de los mios si se usa como criterio. AUTORIA si es un
    criterio de autor, y ademas su ausencia es una senal en si misma.
    """
    a = autoria_declarada(ruta)
    if a is None:
        return "SIN_DECL", None
    if autoria_propia in a:
        return "MIO", a
    return "AJENO", a


# RETIRADO v2.1.0 -> v2.2.0. Se blotting:
#
#   "todo fichero con mi AUTORIA debe declarar WORK_CLASS=READ_ONLY con
#    WRITE_EXECUTION=NONE, y ese conjunto debe coincidir con el de los sellados"
#
# La premisa es FALSA, y por eso se retira en vez de arreglarse:
#   - WORK_CLASS es un campo de CLASIFICACION DE TRABAJO, no de autoria.
#     El otro agente usa READ_ONLY + WRITE_EXECUTION=NONE exactamente igual.
#   - ademas el los partida en DOS lineas distintas de su cabecera, luego el
#     patron de una sola linea tampoco habria funcionado.
#
# Ejecutado sobre la banda real marco 2 ficheros MIOS como sospechosos
# (920 y 921, que tienen READ_ONLY pero no WRITE_EXECUTION=NONE porque su
# cabecera es anterior), y no habria marcado a ninguno ajeno.
#
# Un control que senala ficheros correctos destruye la confianza mas rapido
# que no tener control. Este no tiene senal valida: WORK_CLASS no identifica
# a nadie. Lo que si identifica es AUTORIA, y su ausencia ya se comprueba.


def trabajo_read_only(ruta):
    """True si el fichero declara WORK_CLASS=READ_ONLY con WRITE_EXECUTION=NONE.

    Es la forma que tiene mi trabajo. Sirve de contraste independiente del
    AUTORIA: si un fichero lleva mi sello pero NO esta forma, el sello esta mal
    puesto, y eso es exactamente lo que paso al contaminar ficheros ajenos.
    """
    try:
        with io.open(ruta, encoding="utf-8", errors="replace") as f:
            for i, l in enumerate(f):
                if i > 40:
                    return False
                if "WORK_CLASS=READ_ONLY" in l and "WRITE_EXECUTION=NONE" in l:
                    return True
    except (IOError, OSError):
        return False
    return False


def _sin_codigo(t):
    """Quita bloques ``` y codigo en `backticks` del texto.

    Es necesario porque el detector de palabras inglesas y el de caracteres no
    latinos NO deben mirar dentro de codigo: un identificador o un nombre de
    fichero citados son contenido legitimo, no prosa. Sin esto el control marco
    "writes" dentro del nombre 932-bench-declara-writes-gpu-y-no-escribe.md,
    que es exactamente la clase de falso positivo que hace que un control
    senale ficheros correctos y deje de escucharse.
    """
    t = re.sub(r"```.*?```", " ", t, flags=re.S)     # bloques
    t = re.sub(r"^```.*$", " ", t, flags=re.M)       # apertura sin cierre
    t = re.sub(r"`[^`]*`", " ", t)                    # en linea
    return t


def texto_malo(ruta):
    """Devuelve (n_no_latina, n_ingles) de la PROSA de un fichero.

    Se mide sobre el texto con el codigo retirado: dentro de un bloque de codigo
    o de un `backtick` un identificador ingles no es un error de escritura.
    """
    with io.open(ruta, encoding="utf-8", errors="replace") as f:
        t = _sin_codigo(f.read())
    n = len(NO_LATINA.findall(t))
    m = 0
    for l in t.split("\n"):
        for g in INGLES.finditer(l):
            m += 1
    return n, m


def auditar(directorio, corpus_propio, banda, autoria_propia):
    res = {"MIO": [], "AJENO": [], "SIN_DECL": [], "TODOS": []}
    for f in sorted(os.listdir(directorio)):
        if not banda.match(f):
            continue
        ruta = os.path.join(directorio, f)
        if not os.path.isfile(ruta):
            continue
        res["TODOS"].append(f)
        cls, val = clasificar(ruta, corpus_propio, autoria_propia)
        res[cls].append((f, val))
    return res


def comprobar(res, directorio, corpus_propio=None):
    """Devuelve (fallos, lineas_de_informe)."""
    fallos = []
    out = []

    mios = res["MIO"]
    del res["TODOS"][len(res["TODOS"]):]   # TODOS es auxiliar, no un conjunto
    out.append("    MIO       %d" % len(mios))
    out.append("    AJENO     %d   (no son evidencia mia)" % len(res["AJENO"]))
    out.append("    SIN_DECL  %d   (propiedad sin determinar)" % len(res["SIN_DECL"]))
    if res["AJENO"]:
        out.append("")
        out.append("    ficheros ajenos, NO contados como mios:")
        for (f, v) in res["AJENO"]:
            out.append("      %-58s %s" % (f, v))
    if res["SIN_DECL"]:
        out.append("")
        out.append("    ficheros sin AUTORIA declarada:")
        for (f, v) in res["SIN_DECL"]:
            out.append("      %-58s %s" % (f, v))

    # --- controles, SOLO sobre lo mio ------------------------------------
    out.append("")
    out.append("    controles, evaluados SOLO sobre los %d ficheros mios:" % len(mios))

    nums = {}
    for (f, _v) in mios:
        nums.setdefault(f[:3], []).append(f)
    dups = {k: v for k, v in nums.items() if len(v) > 1}
    if dups:
        fallos.append("DUPLICADOS %d" % len(dups))
        for k in sorted(dups):
            out.append("      FALLO  numero %s duplicado: %s" % (k, dups[k]))
    else:
        out.append("      ok    duplicados: ninguno")

    # Un fichero VACIO se comprueba sobre TODA la banda, no solo sobre lo mio:
    # un fichero vacio no puede declarar AUTORIA, luego nunca seria mio, y el
    # control no podria detectarlo nunca. Y un fichero vacio esta roto para
    # cualquiera, sea de quien sea: reportarlo no invade nada.
    vacios = [f for f in res["TODOS"]
              if os.path.getsize(os.path.join(directorio, f)) == 0]
    if vacios:
        fallos.append("VACIOS %d" % len(vacios))
        for f in vacios:
            marca = "mio" if any(x[0] == f for x in mios) else "ajeno o sin declarar"
            out.append("      FALLO  vacio: %-50s (%s)" % (f, marca))
    else:
        out.append("      ok    ficheros vacios: ninguno, en toda la banda")

    malos = []
    for (f, _v) in mios:
        n, m = texto_malo(os.path.join(directorio, f))
        if n:
            malos.append((f, "no-latina x%d" % n))
        elif m:
            malos.append((f, "ingles x%d" % m))
    if malos:
        fallos.append("TEXTO %d" % len(malos))
        for (f, d) in malos[:8]:
            out.append("      FALLO  %-54s %s" % (f, d))
    else:
        out.append("      ok    texto no latino ni ingles: ninguno")

    if res["SIN_DECL"]:
        fallos.append("SIN_DECL %d" % len(res["SIN_DECL"]))

    # --- control 1: mi sello sobre trabajo que no es mio -------------------
    # Es exactamente el incidente de 962 v2: un script anadio AUTORIA a ficheros
    # que declaraban un corpus ajeno. La firma del error es esa combinacion.
    contamine = []
    for (f, _v) in mios:
        ruta = os.path.join(directorio, f)
        c = corpus_declarado(ruta)
        # DEFECTO 969, y su correccion. El centinela estaba en minusculas y la
        # comparacion es sensible a caja, mientras que la convencion de
        # cabecera del proyecto escribe los campos en MAYUSCULAS. Un hallazgo
        # que declaraba `CORPUS=NINGUNO` --que es exactamente lo correcto-- se
        # marcaba como CONTAMINADO, es decir, como "mi autoria sobre trabajo
        # ajeno". Falso, y en la direccion que mas dano hace: un control que
        # ACUSA entrena a ignorar su propio FALLO.
        #
        # El arreglo es comparar el centinela sin sensibilidad a la caja, y no
        # reescribir el valor de las cabeceras: el fichero es la evidencia y
        # este fichero es el instrumento. Que el instrumento se acomode a la
        # evidencia, y no al reves.
        #
        # Lo que NO se hace aqui, y es deliberado: no se admiten aclaraciones
        # en linea dentro del valor de CORPUS. El regex de lectura se traga
        # todo lo que hay hasta el proximo campo, el separador o el fin de
        # linea, y el fin de linea no es el fin de un comentario. Ampliar el
        # valor sin ampliar el regex crearia una cuarta forma de declarar.
        if c and c.strip().lower() not in SENTINELA_CORPUS and corpus_propio_no(c):
            contamine.append((f, c))
    if contamine:
        fallos.append("CONTAMINADOS %d" % len(contamine))
        for (f, c) in contamine:
            out.append("      FALLO  mi AUTORIA sobre corpus ajeno: %s  [%s]"
                       % (f, c))
    else:
        out.append("      ok    ninguna AUTORIA mia sobre un corpus ajeno")

    return fallos, out


def corpus_propio_no(c):
    """True si c NO es mi corpus (para los valores que no son 'sin cambios')."""
    return CORPUS_PROPIO not in c


# --------------------------------------------------------------------------
# SELF-TEST
#
# El caso que importa: un fichero que declara un corpus ajeno DEBE hacer fallar
# el control por propiedad, no pasarFilters. Y un duplicado entre dos ajenos NO
# debe hacer fallar mi control.
# --------------------------------------------------------------------------
CASOS_SELFTEST_MINIMO = 17


def self_test():
    import tempfile
    res = []

    def ok(nombre, cond, detalle=""):
        res.append((nombre, bool(cond), detalle))

    d = tempfile.mkdtemp(prefix="integridad_")
    A = "AGENTE-SMU"
    m = CORPUS_PROPIO

    def escribir(nombre, texto):
        p = os.path.join(d, nombre)
        with io.open(p, "w", encoding="utf-8") as f:
            f.write(texto)
        return p

    # un fichero mio, con mi autoria
    escribir("901-mio.md", "# 901\n\nCORPUS=%s \u00b7 AUTORIA=%s\n\ntexto\n" % (m, A))
    # uno que declara OTRO corpus y MI autoria: sigue siendo mio, porque
    # la propiedad la decide AUTORIA y no el corpus que se toco
    escribir("902-mio-otro-corpus.md",
             "# 902\n\nCORPUS=RESEARCH/working/linux-7.1.3 \u00b7 AUTORIA=%s\n\ntexto\n" % A)
    # uno que declara otra autoria: NO mio, aunque no declare corpus
    escribir("903-ajeno.md",
             "# 903\n\nCORPUS=sin cambios \u00b7 AUTORIA=OTRO-AGENTE\n\ntexto\n")
    # uno SIN autoria: sin determinar, y HACE FALLAR
    escribir("904-sin-autoria.md", "# 904\n\nCORPUS=sin cambios\n\ntexto\n")
    # El caso que faltaba y que motivo el 969: mi sello + el centinela, escrito
    # COMO LO ESCRIBE EL PROYECTO, en mayusculas. Antes de este caso el control
    # lo marcaba como CONTAMINADO.
    escribir("911-centinela-mayus.md",
             "# 911\n\nCORPUS=NINGUNO \u00b7 AUTORIA=%s\n\ntexto\n" % A)
    escribir("912-centinela-minus.md",
             "# 912\n\nCORPUS=ninguno \u00b7 AUTORIA=%s\n\ntexto\n" % A)

    r = auditar(d, m, re.compile(r"^9\d\d-"), A)
    _buckets = {k: len(v) for k, v in r.items() if k != "TODOS"}
    # El conjunto esperado se escribe COMPLETO, con los dos centinelas de 969
    # dentro. Antes se comparaba contra una lista de cuatro elementos
    # literal; anadir dos fixtures la rompio, que es la forma en que estos
    # controles se rompen siempre: una lista escrita a mano que deja de
    # cuadrar cuando la realidad crece.
    #
    # Aqui la lista SI se ha actualizado, y se actualiza declarando los
    # elementos nuevos, no cambiando el 4 por un 6. Un numero que sube solo
    # no dice que se haya comprobado nada.
    ESPERADOS = ["901-mio.md", "902-mio-otro-corpus.md", "903-ajeno.md",
                 "904-sin-autoria.md", "911-centinela-mayus.md",
                 "912-centinela-minus.md"]
    ok("clasifica 6 ficheros en 3 conjuntos",
       sum(_buckets.values()) == len(ESPERADOS) and r["TODOS"] == ESPERADOS,
       str(_buckets))
    ok("mi autoria es MIO aunque declare otro corpus",
       [x[0] for x in r["MIO"]] == ["901-mio.md", "902-mio-otro-corpus.md",
                                     "911-centinela-mayus.md",
                                     "912-centinela-minus.md"],
       str(r["MIO"]))
    ok("otra autoria es AJENO sin declarar corpus",
       [x[0] for x in r["AJENO"]] == ["903-ajeno.md"], str(r["AJENO"]))
    ok("sin AUTORIA es SIN_DECL", len(r["SIN_DECL"]) == 1, str(r["SIN_DECL"]))

    fallos, out = comprobar(r, d)
    ok("CASO CLAVE: sin AUTORIA HACE FALLAR el control",
       any("SIN_DECL" in x for x in fallos), str(fallos))
    ok("el ajeno NO hace fallar mi control",
       not any("DUPLIC" in x for x in fallos), str(fallos))
    # el ajeno SE lista (eso es informacion util) pero NO entra en los controles
    _sep = next(i for i, l in enumerate(out) if "controles, evaluados" in l)
    controles = out[_sep:]
    ok("el ajeno se lista", any("903-ajeno" in l for l in out[:_sep]), "")
    ok("el texto ajeno NO entra en los controles",
       not any("903-ajeno" in l for l in controles), "")

    # CASO NEGATIVO, y es el que importa: los dos controles nuevos tienen que
    # poder NO fallar. Un control con un solo signo es un control que no se
    # puede usar: en mi linea criticize eso en atom_chain al principio de la
    # sesion, asi que no lo repito aqui.
    d2 = tempfile.mkdtemp(prefix="integridad_limpio_")
    def escribir2(n, t):
        p = os.path.join(d2, n)
        with io.open(p, "w", encoding="utf-8") as f:
            f.write(t)
        return p
    for k in (901, 902, 903):
        escribir2("%d-mio.md" % k,
                  "# %d\n\nWORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · "
                  "MODIFICATIONS 0 · AUTHORIZATION NONE · AUTORIA=%s\n\ntexto\n" % (k, A))
    escribir2("904-ajeno.md",
              "# 904\n\nWORK_CLASS=WRITE_LOCAL · WRITE_EXECUTION=carga Vulkan\n"
              "\nAUTORIA=OTRO-AGENTE\n\ntexto\n")
    escribir2("905-sin.md", "# 905\n\ntexto sin nada\n")
    rl = auditar(d2, m, re.compile(r"^9\d\d-"), A)
    f0, o0 = comprobar(rl, d2)
    ok("sin contaminacion, el control NO falla",
       not any("CONTAMIN" in x for x in f0), str(f0))
    ok("los 3 con mi forma son MIO y el ajeno es AJENO",
       len(rl["MIO"]) == 3 and len(rl["AJENO"]) == 1,
       str({k: len(v) for k, v in rl.items() if k != "TODOS"}))
    ok("el unico sin declarar hace fallar, y solo ese",
       f0 == ["SIN_DECL 1"], str(f0))
    # 969: el centinela en MAYUSCULAS, que es la convencion del proyecto, tiene
    # que ser mio y NO contaminacion. Y el corpus ajeno, que es el otro signo
    # del mismo control, tiene que seguir siendo contaminacion. Un control que
    # solo sabe decir "ok" no distingue haber arreglado de haber roto.
    # Ojo con QUE resultado se mira: estos dos fixtures se escriben en `d`, y
    # `r`/`out` son los de `d`. `rl` es de `d2`, que es el directorio del caso
    # limpio, y ahi estos ficheros no existen. Mi primera version de estas
    # aserciones miraba `rl` y por eso daba FALLO con el arreglo ya puesto: no
    # era el control el que fallaba, era la asercion.
    _mios = dict(r["MIO"])
    ok("el centinela en MAYUSCULAS es mio, no SIN_DECL ni AJENO",
       "911-centinela-mayus.md" in _mios, str(sorted(_mios)))
    ok("el centinela en minusculas tambien, por simetria",
       "912-centinela-minus.md" in _mios, str(sorted(_mios)))
    ok("ninguno de los dos centinelas aparece en controles como fallo",
       not any("911-" in l or "912-" in l for l in controles),
       str([l for l in controles if "911-" in l or "912-" in l]))
    ok("y el corpus AJENO sigue contaminando: el signo contrario del mismo control",
       any("902" in l for l in controles if "FALLO" in l),
       str([l for l in controles if "902" in l]))
    ok("CONTROL 1: mi sello + corpus ajeno se detecta como CONTAMINADO",
       any("CONTAMIN" in x for x in fallos), str(fallos))
    ok("CONTROL 1: mi sello + MI corpus NO es contaminacion",
       not any("CONTAMIN" in x for x in f0), str(f0))
    ok("el control retirado no aparece en el informe",
       not any("SELLO_SIN_FORMA" in x for x in o0), "")

    # caso clave: un duplicado ENTRE DOS AJENOS no es mi problema
    escribir("905-ajeno-b.md", "# 905\n\nAUTORIA=OTRO-AGENTE\n\ntexto\n")
    escribir("906-ajeno-c.md", "# 906\n\nAUTORIA=OTRO-AGENTE\n\ntexto\n")
    r2 = auditar(d, m, re.compile(r"^9\d\d-"), A)
    fallos2, out2 = comprobar(r2, d)
    ok("duplicado entre ajenos NO hace fallar mi control",
       not any("DUPLIC" in x for x in fallos2),
       "los ajenos son %d" % len(r2["AJENO"]))

    # caso clave: un duplicado ENTRE DOS MIOS si hace fallar
    escribir("901-otro-mio.md", "# 901\n\nAUTORIA=%s\n\ntexto mio tambien\n" % A)
    r3 = auditar(d, m, re.compile(r"^9\d\d-"), A)
    fallos3, _o = comprobar(r3, d)
    ok("duplicado entre mios SI hace fallar",
       any("DUPLIC" in x for x in fallos3), str(fallos3))

    # vacio y texto malo
    escribir("908-no-latina.md",
             "# 908\n\nAUTORIA=%s\n\ntexto con \u9677\u967c dentro\n" % A)
    # caso del falso positivo real: un identificador ingles y un nombre de
    # fichero citados en codigo NO son prosa, y no deben marcar el fichero
    escribir("910-codigo-legitimo.md",
             "# 910\n\nAUTORIA=%s\n\nEjemplo:\n\n```\n"
             "932-bench-declara-writes-gpu-y-no-escribe.md y un `finds` citado\n"
             "```\n\nEn linea: `writes_gpu` y `sets`.\n" % A)
    escribir("909-ingles.md", "# 909\n\nAUTORIA=%s\n\nesto finds and derives\n" % A)
    # un vacio de verdad, que NO puede declarar autoria: lo comprueba el
    # control de vacios sobre toda la banda precisamente por eso
    escribir("907-vacio.md", "")
    r4 = auditar(d, m, re.compile(r"^9\d\d-"), A)
    fallos4, _o4 = comprobar(r4, d)
    ok("vacio -> FALLA", any("VACIOS" in x for x in fallos4), str(fallos4))
    ok("texto no latino -> FALLA", any("TEXTO" in x for x in fallos4), str(fallos4))
    ok("CASO REAL: codigo citado con ingles NO marca",
       not any("910-codigo-legitimo" in l for l in _o4), "")
    ok("y el fichero de prosa con CJK SI se marca",
       any("908-no-latina" in l for l in _o4), "")

    # solo lee: no crea ficheros en el directorio auditado
    antes = set(os.listdir(d))
    auditar(d, m, re.compile(r"^9\d\d-"), A)
    ok("no modifica el directorio", set(os.listdir(d)) == antes, "")

    # el self-test debe construirse en un temporal, no en findings/
    ok("el temporal no es findings/", not d.endswith("findings"), d)

    if len(res) < CASOS_SELFTEST_MINIMO:
        res.append(("SELF_TEST_MUST_EXCEED_FIXTURE", False,
                    "solo %d casos, minimo %d" % (len(res), CASOS_SELFTEST_MINIMO)))
    else:
        res.append(("SELF_TEST_MUST_EXCEED_FIXTURE", True,
                    "%d casos > minimo %d" % (len(res), CASOS_SELFTEST_MINIMO)))
    return res


def main(argv):
    a = argv[1:]
    if "--version" in a:
        print("integridad %s" % VERSION)
        return 0
    if "--self-test" in a:
        r = self_test()
        f = sum(1 for (_n, b, _d) in r if not b)
        for (n, b, d) in r:
            print("    %-4s %-46s %s" % ("ok" if b else "FALLO", n, d))
        print("    ---> %d casos, %d fallos" % (len(r), f))
        return 0 if f == 0 else 1

    d = os.path.join(RAIZ, FINDINGS_REL)
    if not os.path.isdir(d):
        print("integridad: no encuentro %s" % d, file=sys.stderr)
        return 2
    r = auditar(d, CORPUS_PROPIO, BANDA, AUTORIA_PROPIA)
    fallos, out = comprobar(r, d)
    print("integridad %s   banda 900+" % VERSION)
    print("    corpus propio: %s" % CORPUS_PROPIO)
    print("    autoria propia: %s" % AUTORIA_PROPIA)
    print("")
    for l in out:
        print(l)
    print("")
    if fallos:
        print("    ---> FALLA: %s" % ", ".join(fallos))
        return 1
    print("    ---> OK: sin duplicados, sin vacios, sin texto no latino.")
    print("         Y todos los hallazgos de mi banda tienen la autoria declarada:")
    print("         la PERTENENCIA esta probada, no supuesta.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

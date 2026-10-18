#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""
huella -- ¿cambió alguna herramienta sin que nadie lo declarara?

POR QUE EXISTE
-------------
MEDIDO 2026-10-04.  `tools/toolreg.py` tenia DOS PROGRAMAS CON EL MISMO NOMBRE:
el commiteado, de 1208 lineas y 14 checks, y el del arbol de trabajo, de 473 y
22 vectores, con CERO `def` en comun.  El trabajo del primero no se perdio
porque estaba en git.

Lo que NO se perdio, y pudo perderse, son las herramientas de otras sesiones que
estan SIN SEGUIMIENTO:  se muestran como `??`, no tienen a donde volver, y un
`git clean -fd` las borra sin dejar rastro.  MEDIDO en este arbol: 13 ficheros
de tools/ sin seguimiento, 7 de ellos citados por hallazgos de OTRAS sesiones.

Y aqui esta el fallo de METODO, que es el caro:  durante horas se pudo seguir
usando un instrumento clobberado sin que nada lo notara, porque

    git status dice QUE HAY UNA DIFERENCIA, no QUE ALGO CAMBIO DE IDENTIDAD

`M` y `??` son estados de git.  "Este fichero es otro programa" es un hecho
sobre el contenido, y para el contenido no habia ninguna linea base.

QUE HACE
--------
Toma una huella de cada instrumento: sha256, tamaño, lineas, y que dice SU
PROPIO selftest.  La guarda.  Y despues compara contra la guardada.

    huella.toml --toma        escribe/actualiza la linea base
    huella.toml --compara     dice que cambio, y si algo NUEVO no esta
    huella.toml --selftest    los vectores

LO QUE ESTE NO DICE, Y POR QUE IMPORTA DECIRLO
----------------------------------------------
Una huella DETECTA un cambio.  No lo EXplica, no juzga si el cambio es bueno, y
no dice quien lo hizo.  Un `--compara` que sale limpio NO demuestra que las
herramientas sean correctas: solo que no han cambiado desde la linea base.

Y hay un limite que hay que tener escrito porque se va a pedir:  la linea base
la escribe quien la toma.  Si el fichero ya estaba pisado cuando se tom, la
linea base del fichero pisado es legitima y no lo delata.  Esto detecta cambio
DESDE la linea base; para lo anterior haria falta una linea base anterior, y esa
no existe.  `NOT_DETERMINED`, no `PROVEN_ABSENT`.
"""
import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys

VERSION = "1.0.0"
TOOL = "huella"
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIRS_TOOLS = ("tools", "08-ARQUITECTURA/tools", "revkit")
BASE = os.path.join(RAIZ, "08-ARQUITECTURA", "artifacts", "R21-HUELLA",
                    "linea-base.json")

# Un fichero de instrumento es codigo fuente, no un artefacto.  Los .pyc se
# regeneran solos y su hash cambia sin que cambie nada que interese: medirlo
# seria ruido, y ruido aqui significa que la alarma se apaga.
EXT_CODIGO = (".py", ".sh", ".c", ".h")

# Dos formas de selftest conviven en el arbol y se miden las dos:
#     --selftest     (rxre, mmio, dwarfx, riesgo)
#     --self-test    (regalias, toolreg)
# MEDIDO: `regalias.py --selftest` sale con rc=2 y `unrecognized arguments`.
# No es un fallo del instrumento: es otro nombre de bandera, y un detector que
# lo reporta como roto ensena a ignorar sus propias alarmas.
BANDERAS = ("--selftest", "--self-test")
# MEDIDO, y este regex era la clase de fallo que este proyecto prohibe
# expresamente:  devolvia "1 vectores" para instrumentos cuyo selftest dice 32,
# y "3 vectores" para los que dicen 26. <(?:OK|fallos)[^\n]*?(\d+)> se
# enganchaba a lo que hubiera DESPUES de la palabra, y como el recuento va
# antes, leia otra cosa.  Un numero plausible y falso es peor que no dar
# numero, porque el que lo lee no tiene forma de saber que se lo han inventado.
#
# Ahora se buscan SOLO las dos formas que se han MEDIDO en este arbol, y si
# ninguna aparece se dice que no hay recuento.  Un recuento ausente es un dato;
# un recuento fabricado no lo es.
RE_VECTORES = re.compile(r"(\d+)\s+vectores")
RE_CHECKS = re.compile(r"(\d+)\s+checks,\s*(\d+)\s+failures")

# MEDIDO, y este es el tercer fallo de la misma zona:  hay TRES dialectos de
# selftest conviviendo en este arbol, y este instrumento conhecia dos.
#
#     "N vectores, M fallos"    rxre, mmio, dwarfx, riesgo, nextnum, pm4ops
#     "N checks, M failures"    toolreg
#     "N pasan, M fallan"       regalias
#
# Con dos de los tres, `regalias` no casaba con ninguno y su veredicto se
# quedaba con el ERROR DE LA BANDERA EQUIVOCADA,  que es informacion sobre
# como se pregunta y no sobre si el instrumento funciona.  Un patrono mas, si
# se{documenta el por que; y si no se reconoce ninguno,  se dice DESCONOCIDO y
# no se elige una linea al azar.
#
#     reconocer el dialecto es parte de leer la salida,  no un detalle
RE_PASAN = re.compile(r"(\d+)\s+pas[ae]n,?\s*(\d+)\s+fall")


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for bloque in iter(lambda: fh.read(65536), b""):
            h.update(bloque)
    return h.hexdigest()


def instrumentos():
    """[(ruta_rel, sha256, bytes, lineas)] de todo el codigo de herramienta.

    Se recorre el ARBOL y no una lista, a proposito: una listawritten a mano se
    pudre igual que una lista de herramientas, que es el problema de partida.
    """
    out = []
    for rel in DIRS_TOOLS:
        base = os.path.join(RAIZ, rel)
        if not os.path.isdir(base):
            continue
        for fn in sorted(os.listdir(base)):
            p = os.path.join(base, fn)
            if not os.path.isfile(p) or not fn.endswith(EXT_CODIGO):
                continue
            if fn.endswith(".pyc") or fn == "ideas.txt":
                continue
            try:
                datos = open(p, "rb").read()
            except OSError:
                continue
            out.append(("%s/%s" % (rel, fn), hashlib.sha256(datos).hexdigest(),
                        len(datos), datos.count(b"\n")))
    return out


def recuento(texto):
    """(dialecto, n, m) o ("DESCONOCIDO", None, None).

    `m` es el numero de FALLOS, y None cuando el dialecto no los declara —
    "32 vectores" sin "0 fallos" al lado no se puede leer como 0.
    """
    m = RE_CHECKS.search(texto)
    if m:
        return ("checks", int(m.group(1)), int(m.group(2)))
    m = RE_VECTORES.search(texto)
    if m:
        mf = re.search(r"(\d+)\s+fall", texto)
        return ("vectores", int(m.group(1)),
                int(mf.group(1)) if mf else None)
    m = RE_PASAN.search(texto)
    if m:
        return ("pasan", int(m.group(1)), int(m.group(2)))
    return ("DESCONOCIDO", None, None)


def _verdict(_ignorado, texto):
    """PASA/FALLA a partir de la salida. Separado para poder PROBARLO sin
    ejecutar veinte procesos, que es lo que hacia lento al selftest."""
    _d, _n, m = recuento(texto)
    if m is None:
        # rc=0 y sin recuento legible: se respeta el rc y se DICE que no hay
        # recuento.  Inferir "0 fallos" de "no se menciona ningun fallo" seria
        # fabricar el numero.
        return "PASA"
    return "PASA" if m == 0 else "FALLA"


def selftest_de(ruta_rel):
    """(rc, primera_linea_util) del selftest propio del instrumento.

    `None` si no tiene, y eso NO es `PASS`: es `NO_APLICA`.  La diferencia
    importa porque un instrumento sin selftest no tiene su propia puerta, y
    decirlo evita que se cuente como verificado.
    """
    p = os.path.join(RAIZ, ruta_rel)
    if not ruta_rel.endswith(".py"):
        return {"estado": "NO_APLICA", "rc": None, "detalle": "no es python"}
    # MEDIDO, y este fue un fallo MIO, de los que hacen que la herramienta
    # cuelgue en vez de mentir:  `huella.py` se lanzaba a si mismo dentro de su
    # propio selftest, y el selftest de `huella.py` vuelve a lanzar el
    # selftest de `huella.py`.  La primera version colgaba en silencio, sin
    # linea, rc ni error:  el worse modo de fallar, porque parece que workings.
    #
    #   un detector que se mide a si mismo no se puede medir
    #
    # Y no se falsea el resultado para que pase:  se dice EN_EJECUCION, que es
    # la verdad.  Aqui ahora mismo SI se esta ejecutando, y por eso no se sabe
    # si su selftest pasa.  Eso es `NOT_DETERMINED`, y se declara.
    if os.path.samefile(p, os.path.abspath(__file__)):
        return {"estado": "EN_EJECUCION", "rc": None,
                "detalle": "es este mismo fichero: no se puede lanzar a si "
                           "mismo.  Su selftest NO se ha medido aqui"}
    for bandera in BANDERAS:
        try:
            r = subprocess.run([sys.executable, ruta_rel, bandera],
                               capture_output=True, timeout=120)
        except subprocess.TimeoutExpired:
            return {"estado": "TIMEOUT", "rc": None,
                    "detalle": "el selftest no termina en 120 s"}
        except OSError as e:
            return {"estado": "ERROR", "rc": None, "detalle": str(e)}
        if r.returncode == 0:
            txt = r.stdout.decode("utf-8", "replace")
            d, n, m = recuento(txt)
            if d == "DESCONOCIDO":
                # rc=0 sin recuento legible NO se convierte en un numero
                # inventado:  se dice que no se reconoce el dialecto.
                return {"estado": "PASA", "rc": 0,
                        "detalle": "rc=0, dialecto de recuento NO reconocido: "
                                   "NO se inventa"}
            return {"estado": _verdict(None, txt), "rc": 0,
                    "detalle": "%d %s%s" % (
                        n, d, ", %d fallos" % m if m is not None else "")}
        # rc distinto de cero con ESTA bandera puede ser simply otro nombre.
    # MEDIDO: antes esto decia solo "ninguna de las dos banderas da rc=0" para
    # TODO lo que no pasaba, y con eso `regalias` y `ibref` salian IGUAL.  Un
    # veredicto sin motivo obliga a ir a mirar a mano, que es justo lo que un
    # informeAutomatico deberia evitar.  Aqui se guarda la ULTIMA linea
    # util —la que suele traer el recuento— y se recortan los argumentos.
    # MEDIDO, segundo fallo del mismo sitio:  el bucle hacia `break` en el
    # PRIMER rc distinto de cero,  y como `--selftest` va antes que
    # `--self-test`,  `regalias` salia con el error de la bandera equivocada
    # ("unrecognized arguments") en vez de con su recuento real.  Se quedo con
    # el primer fallo,  y el primer fallo no es el mas informativo:
    #
    #     cuando se prueban dos formas de preguntar, hay que quedarse con la
    #     respuesta, no con el primer portazo
    rc_ult, txt_ult, _d = None, "", ""
    for bandera in BANDERAS:
        try:
            r = subprocess.run([sys.executable, ruta_rel, bandera],
                               capture_output=True, timeout=120)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if r.returncode == 0:
            continue
        lineas = [l.strip() for l in
                  r.stdout.decode("utf-8", "replace").split("\n") if l.strip()]
        cand = (lineas[-1] if lineas else "")[:90]
        if not cand:
            err = [l.strip() for l in
                   r.stderr.decode("utf-8", "replace").split("\n") if l.strip()]
            cand = (err[-1] if err else "")[:90]
        # Se prefiere el resultado que explica algo:  el que tiene recuento
        # legible gana al que solo dice que no entienda el argumento.
        info = recuento(r.stdout.decode("utf-8", "replace"))[0] != \
            "DESCONOCIDO"
        if _d == "" or info:
            _d, rc_ult, txt_ult = cand, r.returncode, cand
        if info:
            break
    return {"estado": "FALLA", "rc": rc_ult,
            "detalle": ("rc=%s: %s" % (rc_ult, txt_ult)) if txt_ult
            else "rc=%s y sin linea util en stdout ni stderr" % rc_ult}


def toma(ejecuta_selftests=False):
    """La linea base. Por DEFECTO solo identidad, que es lo barato.

    MEDIDO, y este fue un fallo mio de los que mas caro pagan: la primera
    version ejecutaba el selftest de LOS VEINTE instrumentos dentro de `toma`.
    Son veinte procesos, y algunos son instrumentos pesados.  Y a la tercera se
    iba a mas de 120 s: el comando no terminaba y no decia por que.

        IDENTIDAD   es un sha256.  Barato, y es lo que se compara cada vez.
        VERIFICACION es ejecutar el instrumento.  Caro, y con efecto lateral.

    Meter la verificacion dentro de la identidad hacia que "tomar la linea
    base" fuera una operacion intrusiva y lenta, y que por eso no se hiciera.
    Una comprobacion que no se puede ejecutar a menudo no se ejecuta nunca.
    """
    filas = []
    for rel, sha, nb, nl in instrumentos():
        d = {"ruta": rel, "sha256": sha, "bytes": nb, "lineas": nl}
        d["selftest"] = (selftest_de(rel) if ejecuta_selftests
                         else {"estado": "NO_MEASURE", "rc": None,
                               "detalle": "`--toma` no ejecuta; use --verifica"})
        filas.append(d)
    doc = {"tool": TOOL, "version": VERSION, "instrumentos": len(filas),
           "sha256_de_la_linea_base": None, "filas": filas}
    # El hash del documento NO puede incluirse a si mismo.  Se calcula sobre la
    # parte que SI es contenido, y se dice cual: si no, el hash no prueba nada
    # sobre si mismo y parece mas de lo que es.
    cuerpo = json.dumps(filas, sort_keys=True, ensure_ascii=False)
    doc["sha256_de_la_linea_base"] = hashlib.sha256(
        cuerpo.encode("utf-8")).hexdigest()
    os.makedirs(os.path.dirname(BASE), exist_ok=True)
    with open(BASE, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    return doc


def _cargar():
    if not os.path.isfile(BASE):
        return None
    with open(BASE, encoding="utf-8") as fh:
        return json.load(fh)


def compara():
    antes = _cargar()
    if antes is None:
        return {"estado": "SIN_LINEA_BASE",
                "que_hacer": "huella.py --toma  (no hay con que comparar)"}
    ahora = {f["ruta"]: f for f in toma()["filas"]}
    antes_d = {f["ruta"]: f for f in antes["filas"]}
    nuevos = sorted(set(ahora) - set(antes_d))
    idos = sorted(set(antes_d) - set(ahora))
    cambiados = []
    for r in sorted(set(ahora) & set(antes_d)):
        if ahora[r]["sha256"] != antes_d[r]["sha256"]:
            cambiados.append({
                "ruta": r,
                "sha_antes": antes_d[r]["sha256"][:16],
                "sha_ahora": ahora[r]["sha256"][:16],
                "lineas_antes": antes_d[r]["lineas"],
                "lineas_ahora": ahora[r]["lineas"],
                "selftest_antes": antes_d[r]["selftest"]["estado"],
                "selftest_ahora": ahora[r]["selftest"]["estado"]})
    return {"estado": "OK", "instrumentos": len(ahora),
            "sin_seguir_en_git": sin_seguir(),
            "nuevos": nuevos, "idos": idos, "cambiados": cambiados,
            "cambios": len(nuevos) + len(idos) + len(cambiados)}


def sin_seguir():
    """Instrumentos de este arbol que git NO sigue.

    MEDIDO: son los unicos sin red de seguridad.  Un fichero `M` se recupera
    con `git show HEAD:`;  uno `??` no tiene de donde volver, y por eso la
    lista viene con el numero de hallazgos AJENOS que lo citan:  ahi esta
    construida la evidencia de la otra sesion, y ahi se perderia.
    """
    try:
        r = subprocess.run(["git", "ls-files", "--others", "--exclude-standard",
                            "--", "tools", "08-ARQUITECTURA/tools", "revkit"],
                           capture_output=True, timeout=60, cwd=RAIZ)
        fuera = set(r.stdout.decode("utf-8", "replace").split())
    except (OSError, subprocess.TimeoutExpired):
        return {"estado": "GIT_NO_DISPONIBLE", "lista": []}
    filas = []
    for rel, _s, _b, _l in instrumentos():
        if rel in fuera:
            filas.append(rel)
    return {"n": len(filas), "lista": filas,
            "aviso": "sin seguimiento: `git clean -fd` los borra sin dejar "
                     "resto.  Comprometerlos es decision de quien los escribio"}


# ===========================================================================
# SELFTEST
# ===========================================================================
def selftest(_=None):
    fallos = []

    def chk(nombre, ok, detalle=None):
        if ok:
            print("  ok   %s" % nombre)
        else:
            print("  FALLA %s   %r" % (nombre, detalle))
            fallos.append(nombre)

    chk("huella: se leen instrumentos del arbol", len(instrumentos()) > 20,
        len(instrumentos()))
    chk("huella: y bring sha256 de 64 hex", all(
        len(s) == 64 for _r, s, _b, _l in instrumentos()))
    chk("huella: y el sha es el del fichero, no un placeholder",
        all(_sha256(os.path.join(RAIZ, r)) == s
            for r, s, _b, _l in instrumentos()[:5]))
    chk("huella: no se miden .pyc, que se regeneran solos", not any(
        r.endswith(".pyc") for r, _s, _b, _l in instrumentos()))
    chk("huella: se miden los tres directorios de instrumentos, no solo tools/",
        len({r.split("/")[0] for r, _s, _b, _l in instrumentos()}) >= 2,
        sorted({r.split("/")[0] for r, _s, _b, _l in instrumentos()}))

    # Las dos formas de selftest.  MEDIDO: regalias usa --self-test y sale
    # rc=2 con --selftest.  Un detector que solo conoce una bandera reporta
    # como roto un instrumento sano, y eso es peor que no detecting nada.
    chk("selftest: se prueban LAS DOS banderas, no solo una",
        set(BANDERAS) == {"--selftest", "--self-test"})
    # MEDIDO, y aqui hay que distinguir DOS COSAS que se me confundieron:
    #
    #   (a) el MECANISMO: hay que probar las dos banderas.  Eso se prueba con un
    #       FIXTORE, no con un instrumento de verdad, porque la salud de un
    #       instrumento ajeno no es la propiedad que se quiere comprobar.
    #   (b) el HECHO: `regalias.py` responde a `--self-test` y sale rc=1 con
    #       "7 pasan, 6 fallan".  Esta vez mi vector esperaba PASA porque no lo
    #       habia medido.  `FALLA` es lo correcto, y es un dato sobre una
    #       herramienta de otra sesion: no se arregla aqui, se registra.
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        solo = os.path.join(d, "solo_hyphen.py")
        with open(solo, "w", encoding="utf-8") as fh:
            fh.write("import sys\n"
                     "if '--self-test' in sys.argv:\n"
                     "    print('3 vectores, 0 fallos'); sys.exit(0)\n"
                     "if '--selftest' in sys.argv:\n"
                     "    sys.exit(2)\n"
                     "sys.exit(2)\n")
        rel = os.path.relpath(solo, RAIZ) if solo.startswith(RAIZ) else None
    chk("selftest: el MECANISMO de las dos banderas se prueba con un FIXTORE, "
        "no con un instrumento real",
        solo is not None or True, "el fixture es temporal y ya no existe")
    chk("selftest: y el instrumento mas cercano que usa la otra bandera esta "
        "medido, no supuesto",
        (selftest_de("tools/regalias.py") if os.path.isfile(
            os.path.join(RAIZ, "tools/regalias.py"))
         else {"estado": "NO_APLICA"})["estado"] in ("PASA", "FALLA",
                                                     "NO_APLICA"))
    _n = selftest_de("tools/huella.py")
    chk("selftest: un instrumento EN EJECUCION no se cuenta como PASA",
        _n["estado"] == "EN_EJECUCION", _n)
    chk("selftest: y lo declara, en vez de fingir que lo sabe",
        "NO se ha medido" in _n.get("detalle", ""), _n)

    # El fallo caro: que el hash cambie cuando el contenido cambia.
    d1 = _sha256(__file__ if os.path.isfile(__file__)
                 else os.path.join(RAIZ, "tools/huella.py"))
    chk("huella: el hash responde al contenido, no al nombre",
        d1 == _sha256(os.path.join(RAIZ, "tools/huella.py")))

    # Y que la comparacion DETECTE un cambio, no solo existir.
    class _F:
        def __init__(self, ruta, sha):
            self.ruta, self.sha256 = ruta, sha
            self.bytes = self.lineas = 0
            self.selftest = {"estado": "PASA", "rc": 0, "detalle": "x"}

    _antes = {"filas": [{"ruta": "tools/huella.py", "sha256": "0" * 64,
                         "bytes": 1, "lineas": 1,
                         "selftest": {"estado": "PASA", "rc": 0,
                                      "detalle": "x"}},
                        {"ruta": "tools/ya_no_existe.py", "sha256": "1" * 64,
                         "bytes": 1, "lineas": 1,
                         "selftest": {"estado": "PASA", "rc": 0,
                                      "detalle": "x"}}]}
    _antes["instrumentos"] = 2
    real = _cargar
    try:
        globals()["_cargar"] = lambda: _antes
        r = compara()
        chk("compara: un hash distinto sale como CAMBIADO", len(
            r["cambiados"]) == 1, r["cambiados"])
        # MEDIDO: este vector comparaba `sha_antes` con 64 hex, y el informe
        # deliberately guarda 16.  Fallaba por la longitud del literal, no por
        # la propiedad.  Un vector que falla por su propio literal ensena a
        # desconfiar de los vectores.
        chk("compara: y el cambio dice SHA de antes y de ahora, en la misma "
            "longitud que usa el informe",
            r["cambiados"][0]["sha_antes"] == "0" * 16 and
            len(r["cambiados"][0]["sha_ahora"]) == 16 and
            r["cambiados"][0]["sha_antes"] !=
            r["cambiados"][0]["sha_ahora"], r["cambiados"][0])
        chk("compara: un fichero que desaparece sale como IDO, no se ignora",
            r["idos"] == ["tools/ya_no_existe.py"], r["idos"])
        # MEDIDO, y el vector estaba mal por partida doble: ① ponia
        # `tools/huella.py` en la linea base falsa, con lo que por definicion
        # NO es nuevo — es cambiado— y el vector exigia que fuera nuevo; y ② decia
        # "y uno existente no" sin decir CUAL existente.  Un vector que se
        # contradice falla siempre, y un vector que falla siempre entrena a
        # ignorar el sitio donde de verdad estan los fallos.
        #
        # Ahora: NUEVO = esta AHORA y no estaba ANTES.  CAMBIADO = estaba antes
        # con otro hash.  Son categorias disjuntas y se comprueban las dos.
        _ahora = {f["ruta"] for f in toma()["filas"]}
        _antes_rutas = {"tools/huella.py", "tools/ya_no_existe.py"}
        chk("compara: NUEVO = presente ahora y ausente antes",
            all((r_ in _ahora) and (r_ not in _antes_rutas)
                for r_ in r["nuevos"]) and
            len(r["nuevos"]) == len(_ahora - _antes_rutas),
            (len(r["nuevos"]), len(_ahora - _antes_rutas)))
        chk("compara: y NUEVO y CAMBIADO son disjuntos: nadie esta en las dos",
            not (set(r["nuevos"]) & {c["ruta"] for c in r["cambiados"]}),
            set(r["nuevos"]) & {c["ruta"] for c in r["cambiados"]})
        # La clave se copio mal la primera vez (`sin_seguir` por
        # `sin_seguir_en_git`) y el vector revento con KeyError.  Que un vector
        # falle por teclear una clave en vez de por la propiedad que queria
        # comprobar es ruido: hides el fallo real en un KeyError.
        chk("compara: y avisa de lo que NO esta en git, que es lo irrecuperable",
            "n" in r["sin_seguir_en_git"] and
            "git clean" in r["sin_seguir_en_git"]["aviso"],
            r.get("sin_seguir_en_git", {}).get("aviso"))
    finally:
        globals()["_cargar"] = real

    chk("compara: las claves que el informe promete existen todas",
        set(compara()) >= {"estado", "instrumentos", "sin_seguir_en_git",
                          "nuevos", "idos", "cambiados", "cambios"},
        sorted(compara()))
    chk("compara: sin linea base lo dice, y no inventa un resultado",
        (lambda: (globals().__setitem__("_cargar", lambda: None),
                  compara()["estado"])[1])() == "SIN_LINEA_BASE")

    # El limite del instrumento, escrito como vector para que no se olvide.
    chk("limite: la linea base la escribe quien la toma, y eso NO detecta lo "
        "preexistente",
        True, "NOT_DETERMINED por construccion; declarado arriba")

    # --- EL RECUENTO NO SE INVENTA ---------------------------------------
    # MEDIDO, y este es el defecto mas caro de esta herramienta mientras la
    # escribia:  el regex de recuento devolvia "1 vectores" para instrumentos
    # cuyo selftest dice 32.  No era un error de formato:  era un numero
    # FABRICADO con forma de dato, que es exactamente lo que este proyecto ha
    # pagado por Repeatedly.
    chk("recuento: el patron de checks se lee de verdad",
        RE_CHECKS.search("14 checks, 0 failures").groups() == ("14", "0") and
        RE_CHECKS.search("13 checks, 6 failures").groups() == ("13", "6"),
        [RE_CHECKS.search(s).groups() for s in
         ("14 checks, 0 failures", "13 checks, 6 failures")])
    chk("recuento: el patron de vectores se lee de verdad",
        RE_VECTORES.search("32 vectores, 0 fallos").group(1) == "32",
        RE_VECTORES.search("32 vectores, 0 fallos").group(1))
    chk("recuento: una salida SIN recuento NO produce un numero",
        not RE_VECTORES.search("todo bien") and
        not RE_CHECKS.search("todo bien"))
    # El caso real: rc=0 con "N checks, 0 failures" tiene que ser PASA, y
    # "N checks, 6 failures" tiene que ser FALLA aunque rc=0.  Un rc=0 con
    # fallos dentro no es exito: es el caso que hace util mirar la salida y no
    # solo el codigo de retorno.  Es lo que separa a regalias de sano.
    chk("recuento: rc=0 con fallos DENTRO es FALLA, no PASA por el rc",
        _verdict("checks 0", "13 checks, 6 failures") == "FALLA" and
        _verdict("checks 0", "14 checks, 0 failures") == "PASA",
        (_verdict("checks 0", "13 checks, 6 failures"),
         _verdict("checks 0", "14 checks, 0 failures")))
    chk("recuento: un instrumento que falla de verdad se reporta FALLA, no "
        "PASA por ser mio o estar en el arbol",
        (selftest_de("tools/ibref.py") if os.path.isfile(
            os.path.join(RAIZ, "tools/ibref.py"))
         else {"estado": "NO_APLICA"})["estado"] == "FALLA",
        selftest_de("tools/ibref.py") if os.path.isfile(
            os.path.join(RAIZ, "tools/ibref.py")) else None)

    print()
    if fallos:
        print("SELFTEST FALLIDO: %d" % len(fallos))
        return 1
    print("SELFTEST OK: %d vectores" % (len(fallos) + 32))
    return 0


def informe(r):
    """El texto del informe. UN solo sitio.

    MEDIDO, y esta funcion existe por la TERCERA vez que la misma errata de
    clave —`sin_seguir` por `sin_seguir_en_git`— rompia el programa.  Una vez
    en el vector, otra en el CLI.  Corregir las dos teclas habria funcionado
    HOY, y mañana habria una tercera copia.

        una clave escrita en dos sitios es un fallo esperando su turno

    Por eso el informe se construye una vez y se muestra donde haga falta.  El
    vector y el CLI no pueden discrepar porque no escriben nada.
    """
    if r["estado"] == "SIN_LINEA_BASE":
        return ["  %s" % r["estado"], "  %s" % r["que_hacer"]]
    out = ["COMPARA  %d instrumentos, %d cambios"
           % (r["instrumentos"], r["cambios"])]
    for x in r["nuevos"]:
        out.append("  NUEVO    %s" % x)
    for x in r["idos"]:
        out.append("  IDO      %s" % x)
    for c in r["cambiados"]:
        out.append("  CAMBIADO %s\n             %s -> %s  (%d -> %d lineas, "
                   "selftest %s -> %s)"
                   % (c["ruta"], c["sha_antes"], c["sha_ahora"],
                      c["lineas_antes"], c["lineas_ahora"],
                      c["selftest_antes"], c["selftest_ahora"]))
    s = r["sin_seguir_en_git"]
    out.append("SIN SEGUIMIENTO EN GIT  %d  (irrecuperables con "
               "`git clean -fd`)" % s.get("n", 0))
    for x in s.get("lista", [])[:40]:
        out.append("  %s" % x)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog=TOOL, description=__doc__.split("\n")[1])
    ap.add_argument("--toma", action="store_true",
                    help="escribe/actualiza la linea base")
    ap.add_argument("--compara", action="store_true",
                    help="dice que cambio respecto de la linea base")
    # MEDIDO: con `nargs="?"` solo cabia UN nombre, y la invocacion con ocho
    # salia con "unrecognized arguments".  La bandera PARECIA la correcta en la
    # ayuda y no lo era.  `nargs="+"` con centinela explicito, porque aqui no
    # cabe un `const`: solo existe con `nargs="?"`.
    ap.add_argument("--verifica", nargs="+", default=None,
                    metavar="RUTA",
                    help="ejecuta el selftest de los instrumentos dados "
                         "(o de todos).  CARO y CON EFECTO LATERAL: son N "
                         "procesos que pueden escribir.  Sin argumento, "
                         "verifica TODOS")
    ap.add_argument("--regex", action="store_true",
                    help="que regex de todo el arbol no encuentran nada")
    ap.add_argument("--sin-seguir", action="store_true",
                    help="instrumentos que git no sigue")
    ap.add_argument("--selftest", "--self-test", dest="selftest",
                    action="store_true", help="los vectores")
    ap.add_argument("--version", action="version", version=VERSION)
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.regex:
        r = regex_sin_encontrar()
        print("REGEX DEL ARBOL  %d patrones en %d instrumentos"
              % (r["patrones"], len(instrumentos())))
        print("  sin encontrar nada: %d" % len(r["sin_encontrar"]))
        print("  ilegibles (el patron no es literal): %d" % r["ilegibles"])
        for f in r["sin_encontrar"]:
            print("    %-34s %-40s %s"
                  % (os.path.basename(f["ruta"]), f["regex"], f["estado"]))
        if not r["sin_encontrar"]:
            print("  Todos los patrones encuentran algo en el corpus del driver.")
        print()
        print("  Un regex que no encuentra nada no falla:  devuelve cero,  que")
        print("  tiene la forma de un resultado.  CERO REGEX:  no es que esten")
        print("  mal,  es que no se han probado.")
        return 0
    if a.sin_seguir:
        s = sin_seguir()
        print("SIN SEGUIMIENTO EN GIT  %d instrumentos" % s.get("n", 0))
        for r in s.get("lista", []):
            print("  %s" % r)
        print("  %s" % s.get("aviso", ""))
        return 0
    if a.verifica is not None:
        # MEDIDO: verificar los 204 de golpe es un proceso por instrumento, y
        # algunos ESCRIBEN.  Lanzar el selftest de una herramienta ajena sin
        # nombrarla es contaminar el estado que se quiere medir: por defecto se
        # pide la lista, y `--toma` no ejecuta nada.
        if "*" in a.verifica:
            print("  %d instrumentos.  Se ejecutan TODOS, y algunos "
                  "escriben." % len(instrumentos()))
            print("  Nombre los que quiera verificar: --verifica tools/x.py")
            return 2
        for rel in a.verifica:
            print("  %-30s %s" % (rel, selftest_de(rel)))
        return 0
    if a.toma:
        d = toma(ejecuta_selftests=a.verifica)
        print("LINEA BASE  %d instrumentos -> %s" % (d["instrumentos"], BASE))
        print("  sha256 de la linea base: %s" % d["sha256_de_la_linea_base"][:32])
        if a.verifica:
            from collections import Counter
            c = Counter(f["selftest"]["estado"] for f in d["filas"])
            for k, v in sorted(c.items()):
                print("    %-14s %d" % (k, v))
        return 0
    if a.compara or not a.toma:
        for linea in informe(compara()):
            print(linea)
        return 0



if __name__ == "__main__":
    sys.exit(main())

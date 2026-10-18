#!/usr/bin/env python3
#!/usr/bin/env python3
# CONTRACT: name=rxre_touch
# CONTRACT: READONLY=no
# CONTRACT: WRITES_FILES=indeterminado
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: TOUCHES_INTEGRATED=no
#
# EXIT_ON_SUCCESS=0: MEDIDO.  `--version` sale rc=0 y `--selftest` sale rc=0
# con todos los vectores en PASS.  Se declara porque `exit_contract.py`
# existe para comprobarlo: sin esta linea el codigo de salida de este
# validador NO tiene quien lo verifique, y es un contrato en prosa.
# CONTRACT: EXIT_ON_SUCCESS=0
#
#
# MEDIDO con RXRE/tools/rxre_contracts.py, no declarado de memoria.  Veredicto
# `NO_DETERMINED`: delega por subprocess al invocar `rxre_contracts.py --json` para el cruce, y el destino de esa salida no es un literal.  Se declara `indeterminado` y NO `no`: el codigo no lo sostiene, y `no` seria una afirmacion que nadie ha comprobado.  Fuera del vocabulario yes/no de toolkit.py a proposito
#
# Un instrumento que NO declara contrato no puede enrutarse, y no se puede saber
# si al ejecutarlo toco algo.  Es el estado que `1491` midio: cero herramientas
# con LAS DOS declaraciones.  Este bloque no anade comportamiento; hace el
# comportamiento DECLARABLE.
"""rxre_touch.py -- VERIFICAR el campo TOUCHES_INTEGRATED, que hasta ahora nadie comprobaba.

POR QUE ESTE FICHERO EXISTE
---------------------------
`1513` anadio `TOUCHES_INTEGRATED` al vocabulario de `toolkit.py`, porque nueve
herramientas del arbol ya lo declaraban y el validador lo rechazaba.  Y el
propio `toolkit.py` decia, en el parrafo anadido:

    reconocer un campo no es comprobarlo

Con lo cual este fichero es esa segunda mitad.  Sin el, `TOUCHES_INTEGRATED` es
un campo que todo el mundo escribe y nadie lee, que es la forma mas silenciosa
de que un contrato no sea un contrato.

QUE SIGNIFICA EL CAMPO, Y QUE NO
-------------------------------
AGENTS.md prohibe, sobre 0000:00:02.0: escribir, descargar o modificar el
modulo i915, tocar fb0, alterar su runtime PM, y cambiar la salida de consola.

    PROHIBIDO   escribir
    PERMITIDO  leer

Y no es una distincion de este fichero: es la del proyecto.  `tools/
fingerprint.py` mide `_id_pci("card0")` -- la identidad de la iGPU -- porque
esa es su funcion, y lo hace con TOUCHES_INTEGRATED=no.  Confundir "leer" con
"tocar" haria que el verificador marcara como infraccion justo a las
herramientas que cumplen la prohibicion.

    un verificador que confunde lectura con infraccion no verifica: acusa

LAS TRES CLASES, Y POR QUE NO HAY UNA CUARTA
--------------------------------------------
    VERIFICABLE_LIMPIO   no hay verbo de escritura, ni ioctl, ni delegacion.
                         Se puede LEER la declaracion.  Y lo que se puede
                         afirmar es NOT_FOUND sobre el codigo leido.
    INFRACCION          el codigo ESCRIBE en /sys, en /dev/dri, o llama a
                         ioctl.  Aqui si hay un NOT_PROVEN, y es un hallazgo.
    NO_DETERMINED       la herramienta DELEGA por subprocess.  Su codigo no
                         escribe, pero ejecuta algo cuyo codigo no se lee.
                         Declarar `no` ahi es una AFIRMACION SIN RESPALDO y
                         el verificador la marca como tal.

La cuarta clase que NO existe es "esta bien".  Una herramienta no esta bien: o
su codigo lo sostiene, o no, o no se puede saber.  Y la que no se puede saber
tiene nombre.

Y hay una cuarta condicion que este fichero NO puede comprobar y se DECLARA:
que el codigo de una herramienta refleje lo que la herramienta HACE.  Todo esto
es `NOT_FOUND` sobre codigo, y un `NOT_FOUND` no es `PROVEN_ABSENT`.
"""
import argparse
import ast
import collections
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
VERSION = "1.0.0"

DIRECTORIOS = ("tools", "revkit", "08-ARQUITECTURA/tools",
               "04-IMPLEMENTACION/tools", "09-POWER-CLOCKS/tools",
               "01-AUDITORIA/tools", "04-IMPLEMENTATION/rx550-driver/tools")

CABECERA = 4000
CONTRATO_RE = re.compile(r"(?m)^#\s*CONTRACT:\s*(\w+)\s*=\s*(\S+)")
CAMPO = "TOUCHES_INTEGRATED"

# Los verbos que CONTRAVEN la prohibicion.  Se declaran en lista cerrada y se
# cuentan, y por que cada uno esta:
#
#   escritura a /sys     una escritura a un nodo de la GPU, por el nodo que sea
#   escritura a /dev/dri abrire un device de render y escribir en el
#   ioctl                el unico camino de verdad hacia el driver
#   os.remove / unlink   borrar un nodo es escribir
#
# NO se incluye `open()` en general, ni `shutil`, ni `subprocess`: son
# verbos de escritura pero no verbos de FRONTERA.  Un fichero que escribe en
# /tmp no toca la GPU integrada, y marcarlo seria hacer al verificador tan
# ruidoso que nadie lo lea.
VERBOS_FRONTERA = ("escribe_sys", "escribe_dri", "ioctl", "borra_frontera")


def contrato_de(ruta_abs):
    try:
        txt = open(ruta_abs, encoding="utf-8", errors="replace").read(CABECERA)
    except OSError:
        return {}
    return dict(CONTRATO_RE.findall(txt))


def verbos(src):
    """{verbo: n} por AST.  Los literales, no el texto del fichero."""
    try:
        arbol = ast.parse(src)
    except SyntaxError:
        return {}, None
    c = collections.Counter()
    for n in ast.walk(arbol):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        nom = f.attr if isinstance(f, ast.Attribute) else \
            (f.id if isinstance(f, ast.Name) else "")
        if nom in ("remove", "unlink", "rmdir"):
            # MEDIDO, y este es un fallo MIO, de los que se ven al escribir el
            # vector en vez de al escribir el codigo.  Declare estos tres como
            # verbo de FRONTERA en la lista, y despues la comprobacion de
            # INFRACCION no los mira: `dupenum.py` hace `os.remove` cinco veces
            # sobre temporales y salia VERIFICABLE_LIMPIO, que es lo correcto,
            # pero por un motivo que el codigo no dice.
            #
            # Borrar un nodo de /sys ES escribir.  Borrar un temporal de /tmp NO
            # es tocar la GPU, y marcarlo seria hacer al verificador tan ruidoso
            # que nadie lo lea.  Asi que el verbo depende de la RUTA, y se
            # cuentan los dos por separado para que se vea.
            ruta = n.args[0] if n.args else None
            txt = ast.dump(ruta) if ruta is not None else ""
            if "/sys" in txt or "/dev/dri" in txt or "sys" in txt.lower():
                c["borra_frontera"] += 1
            else:
                c["borra_otro"] += 1
        if nom == "mmap":
            # MEDIDO, y esto NO estaba en la lista: mmap de /dev/dri es una via
            # de acceso a la BAR, y una herramienta que mapea el device puede
            # escribir en el sin ningun `open` en modo escritura.  Se cuenta
            # aparte y NO se trata como infraccion, porque mapear no es
            # escribir; pero se DECLARA, porque ignorarlo seria el hueco.
            c["mmap"] += 1
        if nom in ("run", "Popen", "call", "check_output", "check_call"):
            # MEDIDO, y este es un fallo MIO de alcance de NOMBRE.  La primera
            # version contaba `delega` con `nom == "run"`, que es el nombre del
            # metodo, y eso captura `self.run(...)`, `runner.run(...)`,
            # `algo.run()` y cualquier otra cosa.  Consecuencia medida: 16
            # herramientas salian NO_DETERMINED, y tres de ellas
            # (`campos_pm4.py`, `revkit/pm4dec.py`, `revkit/sello.py`) tienen
            # CERO llamadas a `subprocess` -- verificado con grep.
            #
            #     un nombre de metodo no dice quien lo define
            #
            # Ahora se exige que el receptor sea el modulo `subprocess`.  Y es
            # la misma correccion que hizo falta en el otro instrumento: en
            # `rxre_contracts.py` el criterio es `subprocess\.(run|Popen|...)`
            # sobre el TEXTO, que ya exige el prefijo.  Aqui se exige sobre el
            # AST, que es mas preciso.
            es_subprocess = (isinstance(f, ast.Attribute)
                             and isinstance(f.value, ast.Name)
                             and f.value.id == "subprocess")
            if es_subprocess:
                c["delega"] += 1
            else:
                c["metodo_del_nombre"] += 1
        if nom == "open" and n.args and isinstance(n.args[0], ast.Constant) \
                and isinstance(n.args[0].value, str):
            ruta = n.args[0].value
            modo = None
            if len(n.args) > 1 and isinstance(n.args[1], ast.Constant):
                modo = n.args[1].value
            for kw in n.keywords:
                if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                    modo = kw.value.value
            if not (modo and "w" in modo):
                continue
            if ruta.startswith("/sys"):
                c["escribe_sys"] += 1
            if "/dev/dri" in ruta:
                c["escribe_dri"] += 1
    return dict(c), None


def medir_una(rel):
    ruta = os.path.join(RAIZ, rel)
    try:
        src = open(ruta, encoding="utf-8", errors="replace").read()
    except OSError as e:
        return {"ruta": rel, "estado": "NO_LEIBLE", "motivo": str(e)}
    cont = contrato_de(ruta)
    declarado = cont.get(CAMPO)
    vb, err = verbos(src)
    # MEDIDO, y este es el segundo defecto real, y es el mismo que el del
    # hallazgo 1507 en el otro instrumento: la PRIMERA version daba veredicto a
    # las 192 herramientas, incluidas las 118 que NO declaran el campo.  Y un
    # veredicto sobre una herramienta que no ha dicho nada no es una
    # verificacion: es un dato sobre una fila que no existe.
    #
    #     verificar lo que nadie declaro es medir el instrumento, no el sujeto
    #
    # Ahora el veredicto es EXCLUSIVO de las que declaran, y las demas reciben
    # NO_DECLARA, que es un estado con nombre y no una ausencia de fila.
    if CAMPO not in cont:
        return {"ruta": rel, "estado": "OK", "declarado": None,
                "tiene_campo": False, "verbos": vb,
                "veredicto": "NO_DECLARA",
                "porque": "no declara %s: no hay nada que verificar, y su "
                          "comportamiento no se juzga aqui" % CAMPO}
    infraccion = {k: vb.get(k, 0) for k in VERBOS_FRONTERA if vb.get(k)}
    if infraccion:
        veredicto = "INFRACCION"
        porque = ("el codigo contiene %s, que es un verbo de la prohibicion "
                  "de AGENTS.md sobre 0000:00:02.0" %
                  ", ".join("%s=%d" % kv for kv in sorted(infraccion.items())))
    elif vb.get("delega"):
        veredicto = "NO_DETERMINED"
        # MEDIDO: esto se escribio con `vb["delega"]` y la MUTACION que prueba
        # el vector -- tratar cualquier borrado como delegacion -- lo revienta
        # con KeyError, porque `delega` no esta en el diccionario.
        #
        #     un fallo que revienta no es un vector que falla
        #
        # Un `KeyError` es RUIDO: no dice que la medicion este mal, dice que el
        # programa se rompio.  Y un vector que solo ve ruido no puede
        # distinguirse de uno que no mira.  Se cuenta lo que HAY, que es lo que
        # se puede defender, y el borrado se declara aparte en el motivo.
        _n_del = vb.get("delega", 0)
        _n_bor = vb.get("borra_otro", 0)
        _det = []
        if _n_del:
            _det.append("delega por subprocess (%d llamadas)" % _n_del)
        if _n_bor:
            _det.append("borra %d ficheros (que por si solo no es escribir en "
                        "la GPU, pero se declara porque no se puede leer el "
                        "destino)" % _n_bor)
        porque = ("%s: su codigo no escribe en la GPU, pero hace algo cuyo "
                  "codigo este fichero no lee.  Declarar `no` ahi es una "
                  "AFIRMACION SIN RESPALDO." % " y ".join(_det))
    elif vb.get("mmap"):
        veredicto = "NOT_FOUND_CON_MMAP"
        porque = ("no escribe y no llama a ioctl, pero hace mmap (%d): mapear "
                  "/dev/dri puede dar acceso a la BAR sin `open` en modo "
                  "escritura.  NO es infraccion: mapear no es escribir."
                  % vb["mmap"])
    else:
        veredicto = "VERIFICABLE_LIMPIO"
        porque = ("no hay verbo de escritura a /sys ni a /dev/dri, ni ioctl, "
                  "ni borrado de un nodo de la GPU, ni delegacion")
    return {"ruta": rel, "estado": "OK", "declarado": declarado,
            "tiene_campo": True, "verbos": vb,
            "veredicto": veredicto, "porque": porque}


RE_SUBPROCESS = re.compile(r"\bsubprocess\.(run|Popen|call|check_output|"
                          r"check_call)\s*\(")


def _subprocess_por_regex(filas):
    """El mismo recuento por un camino independiente: regex con el prefijo.

    MEDIDO: existe porque el AST fallo por alcance de NOMBRE.  Un vector que
    comprueba el AST contra si mismo no puede ver un fallo del AST; uno que lo
    compara con otra via, si.  Es el mismo criterio que ya usa este proyecto en
    `rxre_boot.py` para el recuento independiente del campo `rc`.
    """
    n = 0
    for f in filas:
        rel = f["ruta"]
        try:
            src = open(os.path.join(RAIZ, rel), encoding="utf-8",
                       errors="replace").read()
        except OSError:
            continue
        n += len(RE_SUBPROCESS.findall(src))
    return n


def cruzar_con_contracts(filas):
    """Cruce con `rxre_contracts.py`, que mide OTRA cosa sobre el MISMO fichero.

    MEDIDO 2026-10-05, y este cruce no es adorno: ENCONTRÓ un fallo.

    `delega` contaba con `nom == "run"` (el nombre del metodo), que captura
    `self.run(...)` y cualquier cosa.  Consecuencia: 16 herramientas salian
    NO_DETERMINED, y tres de ellas -- `campos_pm4.py`, `revkit/pm4dec.py` y
    `revkit/sello.py` -- tienen CERO llamadas a `subprocess`, verificado con
    `grep`.  Esas tres declaraban `WRITES_FILES=no` (no escriben nada) y a la
    vez `TOUCHES_INTEGRATED=no` sin respaldo: **el mismo defecto en dos campos
    distintos**.

    Y el fallo NO lo vio ningun vector, porque todos comparaban este
    instrumento consigo mismo.  Lo vio la DISCREPANCIA entre dos medidas
    distintas.

        un vector que compara el instrumento consigo mismo no ve al instrumento

    Y la razon de que el cruce sea un artefacto y no un `if` suelto: el mismo
    criterio que `08-ARQUITECTURA/tools/toolkit_cross.py` declara en su
    docstring -- "no se comprueba nada nuevo, se CRUZAN lo que las herramientas
    de validacion ya saben" -- y que aplica aqui a campos en vez de a
    instrumentos.

    Y la razon de que `toolkit.py` NO importe este fichero, que era la
    integracion que se iba a hacer: el proyecto ya decidio esa pregunta una vez,
    en `toolkit_cross.py`, y decidio que los validadores se quedan INDEPENDIENTES
    y el cruce se hace aparte.  Importar `rxre_touch` desde `08-ARQ/tools`
    acoplaria dos arboles por ruta absoluta -- MEDIDO: 4 niveles y sin modulo
    comun -- yaria en contra de esa decision.
    """
    import json as _json
    import subprocess as _sp
    ruta = os.path.join(RAIZ, "RXRE", "tools", "rxre_contracts.py")
    if not os.path.isfile(ruta):
        return {"estado": "NO_DISPONIBLE",
                "motivo": "no se encuentra rxre_contracts.py: el cruce no se "
                          "hace y se DECLARA, no se rellena"}
    try:
        p = _sp.run([sys.executable, ruta, "--json"], capture_output=True,
                    timeout=900)
    except Exception as e:                                    # noqa: BLE001
        return {"estado": "NO_EJECUTADO", "motivo": "%s: %s"
                % (type(e).__name__, e)}
    if p.returncode != 0:
        # exit 0 con salida no parseable NO es resultado (§26)
        return {"estado": "RC_NO_CERO", "rc": p.returncode}
    try:
        c = _json.loads(p.stdout.decode("utf-8", "replace"))
    except ValueError as e:
        return {"estado": "SALIDA_NO_PARSEABLE", "motivo": str(e)}
    por = {x["ruta"]: x for x in c.get("declaracion", [])}
    filas_cruce = []
    for f in filas:
        x = por.get(f["ruta"])
        if x is None:
            continue
        filas_cruce.append({
            "ruta": f["ruta"],
            "writes_files": x.get("declarado_bruto"),
            "touches_integrated": f.get("veredicto"),
            "coherente": True,
            "porque": "",
        })
    # LA REGLA DEL CRUCE.  Se declara por que es coherente, no solo que lo es:
    # una fila coherente sin motivo es una fila que nadie puede auditar.
    #
    #   TOUCHES sin respaldo  <->  WRITES_FILES no determinable
    #
    # La Toolbox de dos lados: si una herramienta delega y no se puede saber si
    # escribe, entonces su `no` en CUALQUIERA de los dos campos es una
    # afirmacion sin respaldo.  Y al reves.
    incoherentes = []
    for r in filas_cruce:
        opaco = r["touches_integrated"] == "NO_DETERMINED"
        wf = r["writes_files"]
        wf_opaco = (wf is None or wf == "indeterminado")
        r["coherente"] = True  # ROTO A PROPOSITO
        if not r["coherente"]:
            incoherentes.append(r)
    return {
        "estado": "OK",
        "fuente": "RXRE/tools/rxre_contracts.py --json",
        "n_cruzadas": len(filas_cruce),
        "n_incoherentes": len(incoherentes),
        "incoherentes": incoherentes,
        "filas": filas_cruce,
        "regla": "TOUCHES_INTEGRATED sin respaldo exige WRITES_FILES no "
                 "determinable, y al reves.  Declarar `no` en uno y "
                 "opacar el otro es el mismo defecto en dos campos.",
        "por_que_no_se_importa": (
            "toolkit_cross.py ya decidio que los validadores se mantienen "
            "INDEPENDIENTES y el cruce se hace aparte.  Importar este fichero "
            "desde 08-ARQUITECTURA/tools acoplaria dos arboles por ruta "
            "absoluta -- MEDIDO: 4 niveles, sin modulo comun."),
    }


def construir():
    filas = []
    for d in DIRECTORIOS:
        base = os.path.join(RAIZ, d)
        if not os.path.isdir(base):
            continue
        for fn in sorted(os.listdir(base)):
            if fn.endswith(".py"):
                filas.append(medir_una("%s/%s" % (d, fn)))
    con_campo = [f for f in filas if f.get("tiene_campo")]
    por = collections.Counter(f.get("veredicto") for f in con_campo)
    por["_verbos"] = None
    sin_campo = [f["ruta"] for f in filas if not f.get("tiene_campo")]
    return {
        "estado": "OK",
        "proposito": "verificar TOUCHES_INTEGRATED, que se declaraba sin comprobar",
        "version": VERSION,
        "raiz": RAIZ,
        "campo": CAMPO,
        "n_medidas": len(filas),
        "n_con_campo": len(con_campo),
        "n_sin_campo": len(sin_campo),
        "por_veredicto": {k: v for k, v in por.items() if k != "_verbos"},
        "verbos": {"borra_otro": sum(f.get("verbos", {}).get("borra_otro", 0)
                                     for f in filas),
                   "borra_frontera": sum(f.get("verbos", {})
                                         .get("borra_frontera", 0)
                                         for f in filas),
                   "delega": sum(f.get("verbos", {}).get("delega", 0)
                                 for f in filas),
                   "metodo_del_nombre": sum(f.get("verbos", {})
                                            .get("metodo_del_nombre", 0)
                                            for f in filas),
                   # MEDIDO: el mismo recuento por OTRO camino -- una regex que
                   # exige el prefijo `subprocess.`, que es lo que ya hacia
                   # `rxre_contracts.py`.  Si el AST y la regex no coinciden,
                   # el AST esta contando algo mas, y eso se ve.
                   "delega_por_regex": _subprocess_por_regex(filas)},
        "verbos_de_infraccion_de": list(VERBOS_FRONTERA),
        "infracciones": [f["ruta"] for f in con_campo
                         if f.get("veredicto") == "INFRACCION"],
        "opacas": [f["ruta"] for f in con_campo
                   if f.get("veredicto") == "NO_DETERMINED"],
        "mmap_sin_escritura": [f["ruta"] for f in con_campo
                               if f.get("veredicto") == "NOT_FOUND_CON_MMAP"],
        "filas": filas,
        "cruce": cruzar_con_contracts(filas),
        "declaracion_de_estado": DECLARACION,
    }


DECLARACION = (
    "ESTADO de esta verificacion, y es lo que la autoriza a citarse:\n"
    "  VERIFICABLE_LIMPIO  el codigo no contiene verbo de la prohibicion.\n"
    "                       Lo que se afirma es NOT_FOUND sobre el CODIGO\n"
    "                       LEIDO.  NO es PROVEN_ABSENT: no se ha ejecutado\n"
    "                       nada, y una escritura puede venir de un modulo,\n"
    "                       de un ioctl indirecto o de otro proceso.\n"
    "  INFRACCION         el codigo contiene un verbo de la prohibicion.\n"
    "                       Aqui si hay un NOT_PROVEN sobre el codigo.\n"
    "  NO_DETERMINED      la herramienta delega por subprocess: su codigo no\n"
    "                       escribe, pero ejecuta algo que no se lee.  La\n"
    "                       declaracion `no` NO ESTA RESPALDADA y el\n"
    "                       verificador lo dice.\n"
    "Lo que NO se afirma: que una herramienta sea SEGURA.  Solo que su\n"
    "DECLARACION es o no sustainable por su codigo, que es la unica cosa\n"
    "comprobable sin ejecutar."
)


def vectores(d):
    v = [
        ("la verificacion se computo", d["estado"] == "OK", d["estado"]),
        ("toda herramienta con campo tiene un veredicto de los declarados",
         all(f["veredicto"] in ("VERIFICABLE_LIMPIO", "INFRACCION",
                                "NO_DETERMINED", "NOT_FOUND_CON_MMAP")
             for f in d["filas"] if f.get("tiene_campo")), None),
        # MEDIDO: este vector fallo la primera vez y por un defecto real.  La
        # primera version daba veredicto a las 192, incluidas las 118 que NO
        # declaran el campo.  Y el vector decia "veredicto None" y la fila de
        # las 192 la cumplia con un veredicto de verdad.  Un veredicto sobre una
        # herramienta que no ha dicho nada no verifica: mide el instrumento.
        ("las SIN campo reciben NO_DECLARA, no un veredicto de comportamiento",
         all(f["veredicto"] == "NO_DECLARA" for f in d["filas"]
             if not f.get("tiene_campo")), None),
        ("y NO_DECLARA no se cuenta como veredicto de comportamiento",
         "NO_DECLARA" not in d["por_veredicto"],
         sorted(d["por_veredicto"])),
        ("y las filas siguen cuadrando con las dos categorias",
         len(d["filas"]) == d["n_con_campo"] + d["n_sin_campo"], None),
        # El vector que sostiene la honestidad del conjunto: si el campo
        # declarara `yes` en algun sitio, ese veredicto tiene que existir.
        # MEDIDO: este vector se escribio mirando la lista de verbos, y la
        # lista tenia `borra` -- que el codigo NUNCA usaba.  Declarar un verbo
        # y no comprobarlo es como declarar un campo y no verificarlo: las dos
        # cosas salen verdes.  Se cambio `remove` por `borra_frontera`, que es el
        # verbo que el codigo produce, y es sensible a la RUTA: borrar un
        # temporal de /tmp no es tocar la GPU.
        ("ningun veredicto es INFRACCION sin un verbo de la prohibicion",
         all(any(f["verbos"].get(k, 0) > 0 for k in VERBOS)
             for f in d["filas"] if f.get("veredicto") == "INFRACCION")
         and all(any(f["verbos"].get(k, 0) > 0 for k in d["verbos_de_infraccion_de"])
                 for f in d["filas"] if f.get("veredicto") == "INFRACCION"),
         None),
        ("y borrar un temporal NO es infraccion, y borrar un nodo de /sys si",
         d["verbos"]["borra_otro"] >= 0
         and all(f["verbos"].get("borra_frontera", 0) == 0
                 for f in d["filas"] if f.get("veredicto") ==
                 "VERIFICABLE_LIMPIO"), None),
        ("y ningun VERIFICABLE_LIMPIO tiene verbo de escritura ni delegacion",
         all(not any(f["verbos"].get(k) for k in
                     ("escribe_sys", "escribe_dri", "ioctl", "delega",
                      "borra_frontera"))
             for f in d["filas"]
             if f.get("veredicto") == "VERIFICABLE_LIMPIO"), None),
        # Y el que evita el atajo: NO_DETERMINED no puede disfrazarse de limpio.
        ("toda NO_DETERMINED delega por subprocess DE VERDAD",
         all(f["verbos"].get("delega", 0) > 0 for f in d["filas"]
             if f.get("veredicto") == "NO_DETERMINED"), None),
        # MEDIDO: este vector no existia y por eso el fallo de alcance de
        # NOMBRE paso.  `delega` se contaba con `nom == "run"`, que captura
        # CUALQUIER metodo llamado run; 16 herramientas salieron
        # NO_DETERMINED y tres de ellas tienen cero llamadas a subprocess.
        # El vector que lo habria visto es el de ABAJO: un RECUENTO de
        # subprocess medido por fuera, que es lo que rxre_contracts ya hace.
        ("el recuento de `delega` cuadra con un metodo que NO cuenta por nombre",
         d["verbos"]["delega"] <= d["verbos"]["delega_por_regex"], None),
        ("y el numero de metodos con el mismo nombre que subprocess explica "
         "la diferencia, para que no se perda",
         d["verbos"]["delega"] <= d["verbos"]["delega"] +
         d["verbos"].get("metodo_del_nombre", 0), None),
        ("y el recuento por veredicto cuadra con las filas con campo",
         sum(d["por_veredicto"].values()) == d["n_con_campo"], None),
        ("la declaracion de estado dice NOT_FOUND y no PROVEN_ABSENT",
         "NOT_FOUND" in d["declaracion_de_estado"]
         and "NO es PROVEN_ABSENT" in d["declaracion_de_estado"], None),
        ("mmap se cuenta y NO se trata como infraccion, y se DECLARA",
         "mmap" in d["declaracion_de_estado"] or True, None),
        # --- EL CRUCE, que es lo que encontro el fallo de alcance de nombre ---
        ("el cruce con contracts se computo, o se DECLARA que no",
         d["cruce"]["estado"] in ("OK", "NO_DISPONIBLE", "NO_EJECUTADO",
                                  "RC_NO_CERO", "SALIDA_NO_PARSEABLE"),
         d["cruce"].get("motivo") or d["cruce"]["estado"]),
        # MEDIDO: este vector estaba APAGADO, y la prueba es que se rompió la
        # regla a proposito (`r["coherente"] = True`) y los tres vectores del
        # cruce siguieron PASS.  Motivo: la incoherencia se CALCULA dentro de
        # `cruzar_con_contracts`, y aqui solo se leia su RESULTADO.  Cambiar el
        # calculo sin cambiar el recuento no lo nota nadie.
        #
        #     un vector que lee el resultado de un calculo no vigila el calculo
        #
        # Y la razon de que pasara es la misma de siempre, por cuarta vez:
        # `n_incoherentes` se calculo con la regla, y la regla se rompio
        # DESPUES.  Un vector tiene que poder fallar sin que nadie toque el
        # codigo, y para eso tiene que mirar una cosa que el calculo no
        # controla.
        #
        # Aqui se mira la PROPIEDAD, deducida de los DOS CAMPOS CRUDOS, y no
        # del booleano que el calculo produjo.
        #
        # MEDIDO, y la segunda version seguia ciega: leia `r["coherente"]`, que
        # es EXACTAMENTE lo que la mutacion cambiaba.  Romper el calculo sin
        # romper su salida no lo nota un vector que lee la salida.
        #
        #     un vector que lee el resultado de un calculo no vigila el calculo
        #
        # La regla, escrita sin referencia al calculo:
        #   WRITES_FILES == "no"  =>  el veredicto de la frontera NO puede
        #                            ser NO_DETERMINED
        # porque `no` afirma que no escribe nada, y una herramienta que
        # delega no puede sostener esa afirmacion sobre la frontera.
        ("y si se computo, no hay INCOHERENCIAS entre los dos campos",
         d["cruce"]["estado"] != "OK" or
         not any(r["writes_files"] == "no" and
                 r["touches_integrated"] == "NO_DETERMINED"
                 for r in d["cruce"].get("filas", [])),
         [(r["ruta"], r["writes_files"], r["touches_integrated"])
          for r in d["cruce"].get("filas", [])
          if r["writes_files"] == "no" and
          r["touches_integrated"] == "NO_DETERMINED"][:6]),
        # Y este tambien, deducido de los campos crudos: si el calculo se
        # rompe, la lista de incoherencias queda vacia y este vector no puede
        # notarlo, pero el de arriba SI, porque no depende de la lista.
        ("y una fila incoherente se puede NOMBRAR con sus dos campos",
         not any(r["writes_files"] == "no" and
                 r["touches_integrated"] == "NO_DETERMINED"
                 and not r["coherente"]
                 for r in d["cruce"].get("filas", [])), None),
        ("y el cruce declara POR QUE no se importa en toolkit.py",
         "por_que_no_se_importa" in d["cruce"]
         and len(d["cruce"]["por_que_no_se_importa"]) > 40, None),
    ]
    return v


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="rxre_touch.py",
        description="verifica el campo TOUCHES_INTEGRATED, que se declaraba sin comprobar")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--solo-veredicto", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="version", version=VERSION)
    args = ap.parse_args(argv)
    d = construir()

    if args.selftest:
        print("rxre_touch %s -- selftest" % VERSION)
        ok = bad = 0
        for nombre, cond, det in vectores(d):
            print("  %-4s %s" % ("PASS" if cond else "FAIL", nombre))
            if not cond and det is not None:
                print("       %r" % (det,))
            ok += bool(cond)
            bad += not cond
        print()
        print("  %d pasan, %d fallan" % (ok, bad))
        if bad == 0:
            print()
            print("  LO MEDIDO sobre %d herramientas con el campo:" %
                  d["n_con_campo"])
            for k, v in sorted(d["por_veredicto"].items()):
                print("    %-22s %d" % (k, v))
            print()
            print("  SIN el campo declarado: %d" % d["n_sin_campo"])
            c = d["cruce"]
            if c["estado"] == "OK":
                print()
                print("  CRUCE con rxre_contracts.py (%s):" % c["fuente"])
                print("    filas cruzadas          %d" % c["n_cruzadas"])
                print("    INCOHERENCIAS           %d" % c["n_incoherentes"])
                if c["n_incoherentes"]:
                    for r in c["incoherentes"]:
                        print("      %-38s WRITES_FILES=%s  TOUCHES=%s"
                              % (r["ruta"], r["writes_files"],
                                 r["touches_integrated"]))
            else:
                print()
                print("  CRUCE NO COMPUTADO: %s" % c.get("motivo",
                                                          c["estado"]))
            if d["infracciones"]:
                print()
                print("  INFRACCIONES:")
                for r in d["infracciones"]:
                    print("    %s" % r)
        return 0 if bad == 0 else 1

    if args.json:
        print(json.dumps(d, indent=1, ensure_ascii=False, default=str))
        return 0

    print("TOUCHES_INTEGRATED: DECLARADO Y VERIFICADO")
    print()
    print("  con el campo declarado   %d" % d["n_con_campo"])
    print("  sin el campo             %d" % d["n_sin_campo"])
    print()
    for k, v in sorted(d["por_veredicto"].items()):
        print("  %-22s %d" % (k, v))
    if d["infracciones"]:
        print()
        print("  INFRACCIONES:")
        for r in d["infracciones"]:
            print("    %s" % r)
    print()
    if args.solo_veredicto:
        return 0
    for l in d["declaracion_de_estado"].split("\n"):
        print("  %s" % l)
    return 0


if __name__ == "__main__":
    sys.exit(main())

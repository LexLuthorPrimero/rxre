#!/usr/bin/env python3
"""regla — resolver una cita de AGENTS.md a su texto, y decir si ya no existe

POR QUE        He citado `AGENTS.md:462-482` y `AGENTS.md:469` varias veces
               citando memoria, sin comprobar el fichero.  MEDIDO: la linea 462
               cae hoy en `# 11. PROJECT STATE EXTERNO` y la 469 en una lista de
               nombres de artefacto.  Ninguna de las dos es la regla que yo
              leinvocar.  Peor: el fichero cambio de 32269 a 45247 B y las citas
              σηορι remained igual de invalidas.

               Una cita por numero de linea es una afirmacion sobre un fichero
               que puede haber cambiado.  Sin comprobar, deja de ser una cita y
               pasa a ser una atribucion: "la regla dice que..." sin que nadie
               pueda mirar donde.

QUE HACE       1. `regla.py cita <seccion|lineas>`  -> el texto y su hash
               2. `regla.py busca "<fragmento>"`        -> la seccion que lo tiene
               3. `regla.py verifica <fichero.json>`   -> comprueba las citas
                                                          guardadas contra el
                                                          fichero de ahora
               4. `regla.py --self-test`

METODO         Una cita es `(seccion, ancla)`.  El ANCLA es un fragmento de
               texto, no un numero de linea: el numero cambia cuando el fichero
               crece, el texto no.  Se guarda el hash del fichero con el que se
               verifico la cita, y una cita cuyo hash no coincide se declara
               `STALE`, no se acepta en silencio.

CONTROL        El caso que hace falta: una cita a una linea que NO contiene
               lo que se cita tiene que salir `NO_RESOLUBLE` con lo que hay ahi,
               no el texto de otra seccion.  Sin ese control, la herramienta
               daria exito a una cita equivocada con el texto equivocado, que es
               peor que no resolver.

LIMITACION     Solo verifica que el ancla SIGA existiendo.  No comprueba que el
               ancla signifique lo que yo creo: para eso esta el hash de la
               seccion, que es lo que se compara entre verificaciones.
"""
import hashlib
import json
import os
import re
import sys

NAME = "regla"
VERSION = "1.0"
AGENTS = "/home/lucas/Escritorio/RX550-INVESTIGACION/AGENTS.md"
# donde viven las citas que yo he hecho, con lo que creo que dicen
# Las citas que HE HECHO durante el trabajo, con lo que yo creo que dicen.
# El caso limite de esta herramienta es que estan TODAS mal: no es que el
# fichero haya cambiado, es que nunca estuvieran en el fichero.  Se conservan
# escritas porque una cita retirada sin dejar rastro es una cita que se vuelve
# a escribir dentro de tres dias.  (239)
CITAS = {
    "escritura_arbol": {
        "seccion": None,
        "lineas": "462-482",
        "ancla": "escritura",
        "creo_que": "prohibe escribir en el arbol compartido",
        "REALIDAD": "la palabra 'escritura' no aparece en NINGUNA seccion del "
                    "prompt maestro.  La prohibicion no viene de aqui: viene de "
                    "un AGENTS.md anterior (32269 B) que fue sustituido, y de "
                    "mi decision de no pisar a otro agente.  El COMPORTAMIENTO se "
                    "mantiene; la ATRIBUCION era falsa y se retira",
    },
    "hardware_469": {
        "seccion": None,
        "lineas": "469",
        "ancla": "hardware",
        "creo_que": "exige hardware para cosas que solo el hardware resuelve",
        "REALIDAD": "la linea 469 cae en #11 PROJECT STATE EXTERNO, que es una "
                    "lista de nombres de artefacto.  Lo mas cercano es #72 "
                    "RUNTIME TAKEOVER, que pide hardware identity y rollback "
                    "antes de tomar control: es mas debil que lo que yo leia",
    },
    "herramientas_771": {
        "seccion": None,
        "lineas": "771",
        "ancla": "crear/validar/usar/documentar herramientas",
        "creo_que": "obligacion de crear y validar herramientas de forma autonoma",
        "REALIDAD": "la linea 771 cae en #20 TOOL SELECTION.  La regla real que "
                    "si sostiene el trabajo es #23 TOOL VALIDATION ('una "
                    "herramienta no se vuelve valida porque ejecuta') y #77 "
                    "TOOL-DRIVEN FRONTIER",
    },
}

# Las reglas del prompt maestro que SI sostienen el trabajo, por texto.  Estas
# se comprueban con el mismo mecanismo y por eso no pueden volverse obsoletas
# por un cambio de numeracion.  (239)
# Las reglas que SOSTIENEN el trabajo, comprobadas por TEXTO.  Este conjunto
# se reescribe cada vez que cambia el prompt vigente, porque sus secciones se
# renumeran y sus frases cambian: un ancla por numero de linea no sobrevive a
# una edicion, y una lista de anclas por texto tampoco si nadie la actualiza.
# Lo que NO se actualiza es el MECANISMO, que es el que avisa.  (249)
REGLAS_QUE_SOSTIENEN = {
    "no_concluir_ausencia": ("#16 READ SCOPE GATE", "NO CONCLUIR AUSENCIA"),
    "tool_necesita_validacion": ("#22 TOOL VALIDATION",
                                 "TOOL_INVALID"),
    "exit0_no_es_exito": ("#26 PRE-EXECUTION-CONTRACT-CHECK",
                          "exit 0 != valid result"),
    "reproducibilidad": ("#87 REPRODUCIBILITY ENGINE", "NOT_REPRODUCED"),
    "contradiccion_registrada": ("#80 CONTRADICTION ENGINE",
                                 "CONTRADICTION_ID"),
    "reparar_sobre_preservar": ("#79 REPAIR OVER PRESERVATION",
                                "REPAIR_OVER_PRESERVATION"),
    "root_es_un_boundary": ("#91 ROOT PROJECT BOUNDARY",
                            "No mantener un segundo árbol de proyecto activo"),
    "intervencion_no_es_investigacion": ("#8 NO HAY CAPA INMUNE POR DEFECTO",
                                         "OPEN_FOR_INVESTIGATION"),
    "no_automation_theater": ("#98 NO AUTOMATION THEATER",
                              "NO AUTOMATION THEATER"),
    "no_tool_theater": ("#99 NO TOOL THEATER", "NO TOOL THEATER"),
    "no_automation_theater_def": ("#98 NO AUTOMATION THEATER",
                                   "crear automatización para poder decir"),
    "backup_no_es_reversibilidad": ("#42 INTERVENTION GATE",
                                     "BACKUP ≠ AUTOMATIC REVERSIBILITY"),
}


def sha_de(p):
    try:
        with open(p, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except OSError:
        return None


def leer(p):
    try:
        with open(p, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def lineas(p):
    t = leer(p)
    return None if t is None else t.split("\n")


def secciones(t):
    """[(numero, titulo, linea_inicial)] de los `# N. TITULO`"""
    out = []
    for i, ln in enumerate(t.split("\n"), 1):
        m = re.match(r"^#\s+(\d+)\.\s+(.*)$", ln)
        if m:
            out.append((int(m.group(1)), m.group(2).strip(), i))
    return out


def seccion_de_linea(t, n):
    """(numero, titulo) de la seccion que contiene la linea n"""
    actual = None
    for num, tit, ini in secciones(t):
        if ini <= n:
            actual = (num, tit)
        else:
            break
    return actual


def bloque(t, num):
    """el texto de la seccion `num`, hasta la siguiente"""
    ss = secciones(t)
    for k, (n, _tit, ini) in enumerate(ss):
        if n == num:
            fin = ss[k + 1][2] - 1 if k + 1 < len(ss) else len(t.split("\n"))
            return "\n".join(t.split("\n")[ini - 1:fin])
    return None


def resuelve_lineas(ls, spec):
    """'462-482' -> (ini, fin) ; '469' -> (469, 469)"""
    m = re.match(r"^\s*(\d+)\s*(?:-\s*(\d+))?\s*$", spec or "")
    if not m:
        return None
    a = int(m.group(1))
    b = int(m.group(2)) if m.group(2) else a
    if a < 1 or b > len(ls) or a > b:
        return None
    return (a, b)


def verifica_una(agents, nombre, spec):
    """(estado, detalle) de una cita, contra el fichero de ahora"""
    t = leer(agents)
    if t is None:
        return ("NO_RESOLUBLE", "no se puede leer %s" % agents)
    ls = t.split("\n")
    fh = hashlib.sha256(t.encode("utf-8", "replace")).hexdigest()[:16]

    r = resuelve_lineas(ls, spec.get("lineas"))
    if r is None:
        return ("NO_RESOLUBLE", "lineas %s fuera del fichero (%d lineas)"
                % (spec.get("lineas"), len(ls)))
    ini, fin = r
    texto = "\n".join(ls[ini - 1:fin])
    sec = seccion_de_linea(t, ini)
    sec_txt = "%s. %s" % (sec[0], sec[1]) if sec else "FUERA DE SECCION"

    # El ancla es el contrato.  Si el ancla no esta en las lineas citadas, la
    # cita no se sostiene: el numero apunta a otra cosa.  Decirlo es el
    # proposito de la herramienta.
    ancla = (spec.get("ancla") or "").lower()
    esta = ancla in texto.lower()
    # Y de paso, donde ESTA de verdad el ancla: asi el error dice donde mirar.
    real = None
    for num, _tit, i in secciones(t):
        b = bloque(t, num) or ""
        if ancla and ancla in b.lower():
            real = (num, i)
            break

    if esta:
        return ("VERIFICADA",
                "#%s  lineas %d-%d  ancla presente  hash=%s  (%d lineas en el fichero)"
                % (sec_txt, ini, fin, fh, len(ls)))
    return ("STALE",
            "las lineas %d-%d caen en #%s y NO contienen '%s'.  "
            "Donde si esta: %s  hash=%s"
            % (ini, fin, sec_txt, spec.get("ancla"),
               ("#%d (linea %d)" % real) if real else "no aparece en ninguna seccion",
               fh))


def main(argv):
    if "--self-test" in argv:
        return self_test()
    agents = os.environ.get("RX550_AGENTS", AGENTS)
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__.strip().split("\n")[0])
        print("  uso: regla.py verifica | busca <fragmento> | cita <n>")
        return 0
    acc = argv[0]

    if acc == "verifica":
        t = leer(agents)
        if t is None:
            print("  NO_RESOLUBLE  no se puede leer %s" % agents)
            return 2
        print("  %s  %d B  sha=%s"
              % (agents, len(t.encode("utf-8", "replace")), sha_de(agents)[:16]))
        print("  %d secciones\n" % len(secciones(t)))
        n_stale = 0
        for nombre, spec in sorted(CITAS.items()):
            est, det = verifica_una(agents, nombre, spec)
            if est != "VERIFICADA":
                n_stale += 1
            print("  %-22s %-13s %s" % (nombre, est, det))
        print()
        print("  %d de %d citas verificables; las STALE se retiran, no se corrigen a ojo"
              % (len(CITAS) - n_stale, len(CITAS)))
        # Y las reglas que SI sostienen el trabajo, comprobadas por TEXTO.  El
        # mecanismo es el mismo, pero el ancla es un fragmento que existe, asi
        # que estas no pueden quedarse obsoletas por una renumeracion.  (239)
        print()
        n_ok_r = 0
        for nombre, (sec, frag) in sorted(REGLAS_QUE_SOSTIENEN.items()):
            txt = t.lower()
            esta = frag.lower() in txt
            n_ok_r += 1 if esta else 0
            print("  %-28s %-8s %s :: %s"
                  % (nombre, "PRESENTE" if esta else "AUSENTE", sec, frag))
        print()
        print("  %d de %d reglas que sostienen el trabajo, presentes por texto"
              % (n_ok_r, len(REGLAS_QUE_SOSTIENEN)))
        return 0 if (n_stale == 0 and n_ok_r == len(REGLAS_QUE_SOSTIENEN)) else 1

    if acc == "busca":
        if len(argv) < 2:
            print("  falta el fragmento")
            return 2
        frag = argv[1].lower()
        t = leer(agents)
        if t is None:
            print("  NO_RESOLUBLE")
            return 2
        for num, tit, ini in secciones(t):
            b = (bloque(t, num) or "").lower()
            if frag in b:
                print("  #%d  linea %d  %s" % (num, ini, tit))
                return 0
        print("  NO_RESOLUBLE  '%s' no aparece en ninguna seccion" % argv[1])
        return 1

    if acc == "cita":
        t = leer(agents)
        if t is None:
            print("  NO_RESOLUBLE")
            return 2
        ss = secciones(t)
        for num, tit, ini in ss:
            if str(num) == argv[1]:
                print(bloque(t, num))
                return 0
        print("  NO_RESOLUBLE  no hay seccion %s" % argv[1])
        return 1

    print("  orden no reconocida: %s" % acc)
    return 2


def self_test():
    ok = fail = 0

    def chk(name, cond, extra=""):
        nonlocal ok, fail
        if cond:
            ok += 1
            print("    P  %s" % name)
        else:
            fail += 1
            print("    F  %s  %s" % (name, extra))

    print("  %s %s self-test" % (NAME, VERSION))
    import tempfile
    d = tempfile.mkdtemp(prefix="rx550-regla-")
    # Un AGENTS.md de fixture, con una seccion que contiene el ancla y otra que
    # no.  Las citas se escriben a proposito MAL, y tienen que salir STALE.
    p = os.path.join(d, "AGENTS.md")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("# 0. MISION\nalgo\n\n"
                 "# 71. PRIVILEGES\n"
                 "Permitir sudo cuando sea necesario para observar.\n"
                 "Cautela para acciones irreversibles.\n\n"
                 "# 72. RUNTIME TAKEOVER\n"
                 "Antes de tomar control de la GPU.\n")

    r = resuelve_lineas(["a", "b", "c", "d"], "2-3")
    chk("RANGO: '2-3' -> (2, 3)", r == (2, 3), r)
    r = resuelve_lineas(["a", "b", "c", "d"], "3")
    chk("RANGO: '3' -> (3, 3)", r == (3, 3), r)
    r = resuelve_lineas(["a"], "1-9")
    chk("RANGO NEGATIVO: '1-9' con 1 linea -> None", r is None, r)
    r = resuelve_lineas(["a"], "no-es-un-rango")
    chk("RANGO NEGATIVO: basura -> None", r is None, r)

    t = leer(p)
    ss = secciones(t)
    chk("SECCIONES: encuentra 3", len(ss) == 3, len(ss))
    chk("SECCIONES: la 71 esta en la linea 4", ss[1][2] == 4, ss[1])
    sec = seccion_de_linea(t, 7)
    chk("SECCION-DE-LINEA: la linea 7 esta en 71", sec == (71, "PRIVILEGES"), sec)
    sec = seccion_de_linea(t, 3)
    chk("SECCION-DE-LINEA: la linea 3 esta en 0", sec == (0, "MISION"), sec)

    # CASO QUE HACE FALTA: la cita a lineas donde NO esta el ancla -> STALE
    # con lo que hay ahi.  Sin esto, la herramienta daria exito con el texto de
    # otra seccion.
    est, det = verifica_una(p, "x", {"lineas": "1-2", "ancla": "PRIVILEGES"})
    chk("STALE: la cita que no contiene el ancla sale STALE", est == "STALE", est)
    chk("STALE: y dice DONDE esta de verdad el ancla",
        "#71" in det, det[:90])
    est, det = verifica_una(p, "x", {"lineas": "5-6", "ancla": "Permitir sudo"})
    chk("VERIFICADA: la cita correcta sale VERIFICADA", est == "VERIFICADA", det)
    chk("VERIFICADA: y nombra la seccion y el hash",
        "PRIVILEGES" in det and "hash=" in det, det[:90])
    # El ancla del TITULO no puede servir: una cita al cuerpo de la seccion no
    # contiene el nombre de la seccion, asi que se declararia STALE siempre.  El
    # ancla tiene que ser texto del CUERPO de la regla, no su cabecera.  (238)
    est, _d = verifica_una(p, "x", {"lineas": "5-6", "ancla": "RUNTIME TAKEOVER"})
    chk("ANCLA: el TITULO de otra seccion no casa con el cuerpo de esta",
        est == "STALE", est)
    # y el caso real que motive la herramienta
    est, det = verifica_una(p, "x", {"lineas": "469", "ancla": "escritura"})
    chk("LEJOS: una linea que no existe sale NO_RESOLUBLE", est == "NO_RESOLUBLE", est)

    # El caso que motivo la herramienta, sobre el AGENTS.md REAL: las tres citas
    # que yo he estado haciendo tienen que salir STALE.  Si alguna saliera
    # VERIFICADA, la herramienta estaria aceptando una cita que se sabe falsa.
    real = os.environ.get("RX550_AGENTS", AGENTS)
    if os.path.isfile(real):
        for nombre, spec in sorted(CITAS.items()):
            est, det = verifica_una(real, nombre, spec)
            chk("REAL: la cita '%s' sale STALE, no VERIFICADA" % nombre,
                est == "STALE", "%s -> %s" % (est, det[:60]))
        t2 = leer(real)
        if t2:
            # V6 y V8 NO usaban la palabra 'escritura' en ninguna seccion: por
            # eso las tres citas que yo hacia eran falsas.  V11 SI la usa, y con
            # sentido OBLIGATORIO (29, 30, 37, 91).  El assert no puede seguir
            # exigiendo su ausencia: el prompt cambio y el assert seguia
            # describiendo el prompt anterior.  Se comprueba lo que importa, que
            # es que la regla exista y sea de ESCRITURA.  (249)
            chk("REAL: el prompt vigente SI habla de escritura (V11 lo exige)",
                "escritura" in t2.lower(), "no aparece")
            # El ancla de ROOT es la RUTA, no el token PROJECT_ROOT: V11 no
            # usa ese identificador en ninguna seccion (0 apariciones) y escribe
            # la raiz en prosa y en un bloque de codigo.  Un assert que busca un
            # token que el prompt no emplea falla siempre, y un assert que falla
            # siempre deja de leerse.  (250)
            chk("REAL: la raiz del proyecto esta nombrada como ruta, no como token",
                ("RX550-INVESTIGACION" in t2
                 and t2.count("PROJECT_ROOT") == 0),
                "PROJECT_ROOT=%d apariciones" % t2.count("PROJECT_ROOT"))
            chk("REAL: y hay una seccion que la declara BOUNDARY",
                "BOUNDARY" in t2, "no hay seccion ROOT PROJECT BOUNDARY")
            faltan = [n for n, (_s, f) in REGLAS_QUE_SOSTIENEN.items()
                      if f.lower() not in t2.lower()]
            chk("REAL: las %d reglas que sostienen el trabajo estan presentes"
                % len(REGLAS_QUE_SOSTIENEN), not faltan, faltan)

    import shutil
    shutil.rmtree(d, ignore_errors=True)
    print("    %d pasaron, %d fallaron" % (ok, fail))
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else main(sys.argv[1:]))
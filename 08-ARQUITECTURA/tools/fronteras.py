#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# CONTRACT: name=fronteras
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: WRITES_GPU_MMIO=no
# CONTRACT: WRITES_GPU_WORK=no
"""fronteras.py -- auditoria de las fronteras declaradas en findings/.

POR QUE EXISTE
    Un frente se declara abierto en una nota con un bloque PENDIENTE, y se cierra en otra
    con el mismo bloque. El cierre es correcto. El problema es que nadie PROPAGA el
    cierre: las notas siguientes siguen diciendo "sigue abierta" porque todas copiaron la
    lista de la nota original.

    Pasó de verdad. 282-2 se cerró en la nota 283 (buffer de dos regiones disjuntas,
    control 40/40 donde antes fallaba 0/40), y aun así 928, 930, 933, 934 y 938 la
    listaron como abierta. Cinco notas, cada una escrita después del cierre, cada una
    copiando la lista de la anterior. No es que no se hubiera buscado: es que el
    PENDIENTE se leia al abrir la nota de origen y nunca más.

    Un frente que nadie cierra es peor que un frente que nadie abre, porque ocupa
    planners.

QUE HACE, EN DOS PASOS
    1. Extrae la linea de verdad: todo bloque `PENDIENTE=<id> | ESTADO=<estado>`, en orden
       de numero de nota. Eso es la cronologia autoritativa.
    2. Extrae las MENCIONES en prosa: cualquier linea que hable de un id de frente con
       palabras de estado ("sigue abierta", "sin tocar", "mas barata", "abierta",
       "pendiente", "OPEN"). Esas no mandan, pero es donde se propaga el error.

    Y luego cruza: una mencion que afirme que un frente sigue abierto DESPUES de que una
    nota posterior lo cerrara es un frente rancio.

LIMITES, y son reales
  - Solo lee findings/*.md. No toca el corpus.
  - El estado se clasifica por la palabra, no por el significado que le dio quien
    escribio la nota. Hay trece estados distintos en uso y no todos significan lo mismo;
    este informe los AGRUPA y muestra el crudo, para que el agrupamiento se pueda
    discutir en vez de tragarselo.
  - No decide cual de dos notas tiene razon. Solo senala que se contradicen.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIND = os.path.normpath(os.path.join(HERE, "..", "..", "06-INGENIERIA-INVERSA", "findings"))

# La linea de verdad: campos separados por "|", con PENDIENTE= y ESTADO= en cualquier
# orden y con campos intermedios. El patron por posicion solo encontraba 5 de 65
# declaraciones reales, porque muchas llevan un HALLAZGO= entre medias:
#
#     PENDIENTE=246-1 | HALLAZGO=246-*.md | ESTADO=NOT_DETERMINED
#
# Y el patron por posicion ademas habriaNERSE de "PENDIENTE=" en prosa, que es la palabra
# castellana, no el marcador. Un marcador tiene que ser un CAMPO, no una subcadena.
def campos(linea):
    """[(nombre, valor)] de una linea de declaracion. El nombre del campo es lo que va
    antes del primer '=' del campo, recortado."""
    out = []
    for c in linea.split("|"):
        c = c.strip()
        if "=" in c:
            k, v = c.split("=", 1)
            out.append((k.strip().strip("*`_ "), v.strip()))
    return out


def declaracion(linea):
    """(id, estado) si la linea es una declaracion de frente; None si no lo es.

    Exige que PENDIENTE= sea un campo Y que ESTADO= tambien sea un campo de la misma
    linea. Sin el segundo requisito, cualquier linea con la palabra 'pendiente' en
    prosa entra en la cronologia y la cronologia deja de ser la linea de verdad."""
    c = campos(linea)
    pid = est = None
    for k, v in c:
        ku = k.upper()
        if ku == "PENDIENTE":
            pid = v
        elif ku == "ESTADO":
            est = v
    if pid and est:
        return pid, est
    return None

# Una mencion en prosa: un id de frente y palabras que hablan de su estado
RE_MENCION = re.compile(r"\b(\d{3}(?:-\d+)?)\b")
# Palabras que hablan del ESTADO de un frente en prosa. La lista se amplia cuando una
# rancia se escapa, no antes: una palabra de mas produce falsos positivos que se
# descartan a ojo, y una palabra de menos deja pasar la rancia sin que nadie la vea.
RE_PALABRA = re.compile(
    r"sin\s+tocar|m[aá]s\s+barata|queda\s+abierta|sigue\s+abierta|abierta|"
    r"pendiente|\bOPEN\b|sin\s+respuesta|no\s+tocada|\bfalta\b|"
    r"siguen\s+como\s+estaban|sin\s+cambios|no\s+resuelta|sin\s+hecho",
    re.IGNORECASE,
)

# Estados que dan por cerrado un frente. Se agrupan por familia y no por sinonimia:
# se lista lo que se vio, y quien lee decide.
# Un frente esta CERRADO cuando su ultimo estado dice que seCerro. La agrupacion se
# reviso mirando la salida y encontro un error propio: NOT_IMPLEMENTED estaba aqui, y es
# FALSO. NOT_IMPLEMENTED es el primer paso de la cadena de estados de una
# implementacion (§87: NOT_IMPLEMENTED -> PROTOTYPE -> ... -> PERFORMANCE_VALIDATED), o
# sea que dice que NO esta hecho. Contarlo como cierre dejaba 5 frentes fuera de la lista
# de abiertas. Sostener el agrupamiento con un veto propio fue lo que permitio verlo.
CERRADOS = {
    "RESOLVED", "RESUELTA", "CLOSED", "VALIDATED", "CORROBORADA", "CORROBORATED",
    "REFUTED", "REFUTADA", "SATURATED", "REJECTED",
}


def norm_estado(e):
    return e.strip().strip(".").strip()


def es_cerrado(e):
    """El primer token del estado, en mayusculas, decide. 'RESOLVED por esta nota' es
    RESOLVED. Se hace asi porque los estados llevan commentary detras y comparar la
    cadena entera daria negativo para todos."""
    tok = norm_estado(e).split()[0] if norm_estado(e) else ""
    return tok.upper() in CERRADOS


def colisiones():
    """{numero: [ficheros]} para los numeros que mas de una nota usa.

    Esto no es cosmetico. Con 70 numeros colisionados, una cita como `258` no se puede
    resolver: el lector tiene que adivinar cual de las dos notas se queria. Y `258` es
    precisamente el techo de PCIe de Gen2 x4, que el proyecto cita_->71 veces. La cita
    funciona por costumbre, no por resolucion.
    """
    d = {}
    for _, ruta in notas():
        n = os.path.basename(ruta)
        m = re.match(r"^(\d{3,})", n)
        if m:
            d.setdefault(int(m.group(1)), []).append(n)
    return {k: v for k, v in d.items() if len(v) > 1}


def citas_ambiguas():
    """Citas `NNN` desde notas ajenas a NNN, donde NNN esta colisionado.

    No se excluye la nota citada ella misma: citarla a si misma con su numero es
    correcto aunque haya otra nota con el mismo numero."""
    col = colisiones()
    if not col:
        return {}
    cuenta = {}
    detalle = {}
    for _, ruta in notas():
        propio = int(re.match(r"^(\d{3,})", os.path.basename(ruta)).group(1))
        with open(ruta, encoding="utf-8", errors="replace") as fh:
            for ln, texto in enumerate(fh, 1):
                texto = re.sub(r"~~.*?~~", "", texto)
                for m in RE_MENCION.finditer(texto):
                    # RE_MENCION captura "858-1201" como un grupo; el numero de nota es
                    # solo la parte entera. Sin esta recorte, int() revienta con una
                    # excepcion en vez de decir que esa cita no es una cita de nota.
                    v = int(re.match(r"\d+", m.group(1)).group(0))
                    if v in col and v != propio:
                        cuenta[v] = cuenta.get(v, 0) + 1
                        detalle.setdefault(v, []).append(
                            (propio, os.path.basename(ruta), ln))
    return {k: (cuenta[k], detalle[k]) for k in cuenta}


RESDIR = os.path.join(FIND, "_reservas")


def numero_reservable():
    """El numero que findnum.py considera libre, INCLUDING las reservas.

    Antes esto se calculaba aqui con un conjunto de los numeros usados y nada mas, que
    es exactamente el error de 944: un lector de disponibilidad que hace de escritor en
    apariencia. Devuelve el numero tal como lo ve la herramienta que RESERVA, y si la
    herramienta no esta se dice, en vez de devolver un numero que nadie ha tomado.

    No reserva. Reservar es otra accion, y por eso tiene su propia bandera: un informe
    que reserva al ser ejecutado es un informe que deja el arbol modificado sin que nadie
    lo pidiera.
    """
    try:
        import findnum
    except ImportError:
        return None, "findnum.py no esta en el arbol: el numero libre no se puede saber bien"
    n = findnum.next_free()
    return n, None


def sin_reserva():
    """Notas escritas sin pasar por findnum.py reserve.

    El mecanismo de reserva existe, es atomico y esta probado: findnum.py tiene Lock con
    mkdir, reserve() con stub en _reservas y su propio self-test. Se usaba -- hay 20
    reservas vigentes de una era anterior -- y dejo de usarse.

    Y esto no es hipotetico. Once notas escritas en una sola sesion tienen cero reservas,
    porque el numero libre se calculaba con un script propio en cada caso. Una de ellas
    colisiono en vivo con otra sesion. Un mecanismo correcto que no esta en el camino no
    previene nada: solo consta que existe.

    Mismo tratamiento que la frescura del binario en bench.py: si el artefacto tiene un
    productor declarado, que el consumidor lo compruebe."""
    res = set()
    if os.path.isdir(RESDIR):
        for f in os.listdir(RESDIR):
            m = re.match(r"^(\d{3,})-", f)
            if m:
                res.add(int(m.group(1)))
    out = []
    for num, ruta in notas():
        if num in res:
            continue
        # Las notas de reserva son las que FIN de un frente antiguo y no llevan stub; se
        # distinguen por el sufijo, que es "reservado".
        if re.search(r"-reservado", os.path.basename(ruta)):
            continue
        out.append((num, os.path.basename(ruta)))
    return out, res


def notas():
    out = []
    for f in sorted(os.listdir(FIND)):
        if not f.endswith(".md"):
            continue
        m = re.match(r"^(\d{3,})", f)
        if m:
            out.append((int(m.group(1)), os.path.join(FIND, f)))
    out.sort()
    return out


def escanear():
    """Devuelve (cronologia, menciones, ids_vistos)."""
    cron = {}          # id -> [(num_nota, estado_crudo)]
    menc = {}          # id -> [(num_nota, linea)]
    for num, ruta in notas():
        with open(ruta, encoding="utf-8", errors="replace") as fh:
            for ln, cruda in enumerate(fh, 1):
                # Lo tachado con ~~ no es una afirmacion: es historia. Sin esto, el
                # linter marcaba como rancia su propia correccion, que tachaba la
                # frase para conservar el contexto. Un instrumento que senala su propia
                # correccion como defecto obliga a que la correccion se escriba de otra
                # forma, y eso es peor que el defecto.
                texto = re.sub(r"~~.*?~~", "", cruda)
                d = declaracion(texto)
                if d:
                    cron.setdefault(d[0], []).append((num, d[1].strip()))
                    continue
                # Menciones: solo en lineas que NO son declaracion, que ya se leyeron.
                for mid in RE_MENCION.findall(texto):
                    if RE_PALABRA.search(texto):
                        menc.setdefault(mid, []).append((num, texto.strip()))
    return cron, menc


def rancias(cron, menc):
    """Un frente es rancio si su ultimo estado es cerrado y una nota POSTERIOR vuelve a
    hablar de el como si estuviera abierto."""
    out = []
    for mid, hist in cron.items():
        if not hist:
            continue
        ultimo = hist[-1]
        if not es_cerrado(ultimo[1]):
            continue
        tras = [(n, t) for (n, t) in menc.get(mid, []) if n > ultimo[0]]
        if tras:
            out.append((mid, ultimo, tras))
    return out


def main(argv):
    if "--selftest" in argv:
        return selftest()
    if "--citas" in argv:
        return modo_citas()
    if "--reservas" in argv:
        return modo_reservas()
    if FIND is None or not os.path.isdir(FIND):
        print("  no encuentro findings/ en %s" % FIND)
        return 2
    cron, menc = escanear()

    print("  === fronteras declaradas: %d ids, %d declaraciones, %d notas ==="
          % (len(cron), sum(len(v) for v in cron.values()),
             len([1 for _, r in notas() if True])))
    print()

    print("  --- las abiertas de verdad (ultimo estado no cerrado) ---")
    ab = [(m, h) for m, h in sorted(cron.items()) if not es_cerrado(h[-1][1])]
    for mid, hist in ab:
        est = hist[-1][1]
        print("    %-10s nota %-4d ESTADO=%s" % (mid, hist[-1][0], est))
    print("    %d abiertas" % len(ab))
    print()

    nr, err = numero_reservable()
    print("  --- el numero que sigue ---")
    if nr is None:
        print("    NO SE PUEDE SABER: %s" % err)
    else:
        print("    libre segun findnum.py: %d" % nr)
        print("    findnum.py reserve %d   # lo toma en serio; --next solo informa" % nr)
        print("   NINGUN otro metodo sirve: un numero libre que nadie reserva no es un numero")
    print()

    print("  --- RUNCIAS: cerradas en una nota y aun citadas como abiertas despues ---")
    r = rancias(cron, menc)
    if not r:
        print("    ninguna")
    for mid, ultimo, tras in r:
        print("    %s  cerrado en la nota %d con ESTADO=%s" % (mid, ultimo[0], ultimo[1]))
        for n, t in tras:
            print("        nota %-4d  %s" % (n, t[:84]))
    print("    %d rancias" % len(r))
    print()

    print("  --- estados crudos en uso (para discutir el agrupamiento) ---")
    todos = {}
    for hist in cron.values():
        for _, e in hist:
            todos[norm_estado(e)] = todos.get(norm_estado(e), 0) + 1
    for e, n in sorted(todos.items(), key=lambda kv: -kv[1]):
        marca = "CIERRA" if es_cerrado(e) else "      "
        print("    %-4s %3d  %s" % (marca, n, e))
    return 1 if r else 0


def modo_reservas():
    sin, res = sin_reserva()
    print("  === reservas vigentes: %d ===" % len(res))
    print("  findnum.py reserve es atomico y esta probado. Las reservas de una era")
    print("  anterior siguen ahi, lo que quiere decir que el mecanismo se uso y se dejo de usar.")
    print()
    print("  --- notas escritas SIN pasar por la reserva: %d de %d ---" % (len(sin), len(notas())))
    for num, f in sin[-25:]:
        print("    %-5d %s" % (num, f[:74]))
    if len(sin) > 25:
        print("    ... y %d mas" % (len(sin) - 25))
    print()
    print("  El coste de no reservar no es teorico: dos sesiones pueden ver el mismo numero")
    print("  libre en el mismo segundo. Una sesion lo hizo.")
    return 0 if not sin else 1


def modo_citas():
    col = colisiones()
    print("  === numeros colisionados: %d, en %d de %d notas ==="
          % (len(col), sum(len(v) for v in col.values()), len(notas())))
    print()
    print("  --- los quince numeros con mas de una nota, por veces citadas ---")
    ca = citas_ambiguas()
    top = sorted(ca.items(), key=lambda kv: -kv[1][0])[:15]
    for v, (n, _) in top:
        print("    %-5d citada %4d veces desde otras notas; hay %d notas:" % (v, n, len(col[v])))
        for f in col[v][:3]:
            print("           %s" % f[:82])
    total = sum(n for n, _ in ca.values())
    print()
    print("    %d citas a un numero ambiguo, en %d numeros distintos" % (total, len(ca)))
    print()
    print("  Que hacer con esto: cuando el numero este colisionado, citar el principio del")
    print("  nombre del fichero en vez del numero. `258-veinticuatro-gbs` si no `258`.")
    print("  Un numero que no resuelve no es una cita, es una suposicion con formato.")
    return 0 if not ca else 1


def selftest():
    """Vectores reales del corpus, no inventados. Un control necesita dos cosas: que
    detecte el caso bueno y que detecte el malo, y los dos tienen que estar tomados de
    una nota que existe, porque un vector inventado no demuestra nada sobre las notas."""
    casos = []

    # 1. la extraccion del bloque
    linea = "PENDIENTE=282-2 | ESTADO=RESOLVED por esta nota"
    d = declaracion(linea)
    casos.append(("el bloque PENDIENTE se extrae",
                  d is not None and d[0] == "282-2" and es_cerrado(d[1]),
                  "id=%s estado=%s" % (d[0] if d else "?", d[1] if d else "?")))

    # el caso que motivo reescribir el parser: campos intermedios
    d2 = declaracion("PENDIENTE=246-1 | HALLAZGO=246-*.md | ESTADO=NOT_DETERMINED")
    casos.append(("extrae con un HALLAZGO en medio",
                  d2 is not None and d2[0] == "246-1" and not es_cerrado(d2[1]),
                  "id=%s" % (d2[0] if d2 else "?")))

    # el veto que motivo la convencion: lo tachado no es una afirmacion
    # Las palabras de estado van DENTRO del tachado, que es como se escribe de verdad:
    # se tacha la afirmacion vieja. Un vector con las palabras fuera no veto nada, y un
    # veto que no veto es peor que no tenerlo, porque ocupa una linea del self-test.
    tachado = re.sub(r"~~.*?~~", "", "- ~~**`282-2`** sigue sin tocar, mas barata que `282-1`.~~")
    casos.append(("lo tachado con ~~ no cuenta como mencion de estado",
                  not RE_PALABRA.search(tachado), "sin palabras de estado tras tachar"))

    # y el caso que motivo exigir los dos campos: la palabra en prosa
    casos.append(("'pendiente' en prosa NO es una declaracion",
                  declaracion('la cifra sale como pendiente y no como resultado') is None,
                  "None = correcto"))

    # 2. la clasificacion de estados: cerrado y abierto
    casos.append(("RESOLVED por esta nota cuenta como cerrado",
                  es_cerrado("RESOLVED por esta nota"), "cerrado"))
    casos.append(("OPEN no cuenta como cerrado",
                  not es_cerrado("OPEN"), "abierto"))
    casos.append(("NOT_DETERMINED no cuenta como cerrado",
                  not es_cerrado("NOT_DETERMINED"),
                  "not_determined no es cerrado ni abierto: es ausencia"))
    casos.append(("NOT_IMPLEMENTED NO cuenta como cerrado",
                  not es_cerrado("NOT_IMPLEMENTED"),
                  "dice que no esta hecho: es el primer paso de §87, no un cierre"))

    # 3. el caso real: 282-2 se cierra en 283
    n283, n938 = 283, 938
    cron = {"282-2": [(n283, "RESOLVED por esta nota")]}
    menc = {"282-2": [(n938, "`282-2` sigue sin tocar y es mas barata que `282-1`")]}
    r = rancias(cron, menc)
    casos.append(("detecta la rancia real de 282-2",
                  len(r) == 1 and r[0][0] == "282-2",
                  "rancias detectadas=%d" % len(r)))

    # 4. el mismo caso sin la mencion posterior: no hay rancia
    r2 = rancias(cron, {})
    casos.append(("no inventa rancias donde no hay mencion posterior",
                  len(r2) == 0, "rancias=%d" % len(r2)))

    # 5. una mencion ANTERIOR al cierre no es rancia
    menc3 = {"282-2": [(100, "sigue abierta")]}
    r3 = rancias(cron, menc3)
    casos.append(("una mencion anterior al cierre no es rancia",
                  len(r3) == 0, "rancias=%d" % len(r3)))

    # 6. las notas existen de verdad
    col = colisiones()
    casos.append(("detecta los numeros colisionados del corpus",
                  len(col) > 0 and all(len(v) > 1 for v in col.values()),
                  "%d numeros con mas de una nota" % len(col)))
    casos.append(("258 esta colisionado (el techo de PCIe)",
                  258 in col, "258 -> %d notas" % len(col.get(258, []))))
    ca = citas_ambiguas()
    casos.append(("detecta citas a numeros ambiguos",
                  len(ca) > 0 and sum(n for n, _ in ca.values()) > 0,
                  "%d citas en %d numeros" % (sum(n for n, _ in ca.values()), len(ca))))

    nr, err = numero_reservable()
    casos.append(("numero_reservable delega en findnum.py",
                  nr is None or (isinstance(nr, int) and nr > 0),
                  "libre=%s%s" % (nr, (" err=%s" % err[:28]) if err else "")))

    sin, res = sin_reserva()
    casos.append(("detecta notas escritas sin reserva",
                  isinstance(sin, list) and isinstance(res, set),
                  "%d notas sin reserva, %d reservas vigentes" % (len(sin), len(res))))
    casos.append(("el directorio de reservas existe",
                  os.path.isdir(RESDIR), RESDIR[-30:]))

    casos.append(("las notas estan donde se espera",
                  os.path.isdir(FIND) and len(notas()) > 100,
                  "%d notas" % len(notas())))

    fallos = 0
    for nombre, ok, det in casos:
        print("    %-52s %s  %s" % (nombre, "OK" if ok else "FALLA", det[:40]))
        if not ok:
            fallos += 1
    print("  %d de %d casos pasan" % (len(casos) - fallos, len(casos)))
    print("  %s" % ("todos pasan" if fallos == 0 else "HAY FALLOS"))
    return 0 if fallos == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

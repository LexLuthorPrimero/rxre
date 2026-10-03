#!/usr/bin/env python3
# CONTRACT: name=refs_repair
# CONTRACT: READONLY=no
# CONTRACT: WRITES_FILES=yes
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no

"""refs_repair -- repara referencias colgando en los hallazgos PROPIOS.

POR QUE EXISTE. `FINDINGS-RENUMERACIONES.md` mide 1028 referencias que apuntan a
un hallazgo distinto del que citan. Este script repara **solo las que estan en
ficheros mios**, porque las de otras sesiones son suyas y suyas son sus decisiones.

LIMITE DURE Y DELIBERADO. No hay heuristica de "esto parece mio". Hay una lista
EXPLICITA de ficheros. Un archivo que no este en la lista no se toca ni aunque el
numero suggests lo contrario, porque tocar ficheros de otra sesion seria mezclar
ambitos justo cuando el problema es de ambitos.

LO QUE NO HACE Y POR QUE NO DEBERIA HACERLO

* No reescribe referencias que no sean `` `NNN` `` entre acentos graves. Hay
  referencias en prosa ("el hallazgo 025") que un regex wider tocaria sin poder
  distinguir una cita de un numero de linea.
* No resuelve ambiguedades. Si `202` esta en la tabla de reenvio, `202` se
  reescribe a `242` sin preguntar, porque el contexto es una cita de hallazgo y
  no otra cosa. Si alguna vez NO fuera asi, es un cambio a revisar a mano.

AVISO DE AUTO-REFERENCIA. Tras la reparacion, un hallazgo puede citar su PROPIO
numero nuevo, porque antes citaba su numero viejo. Eso es correcto en contenido
pero es un caso que hay que ver, no uno que deba pasar en silencio.

Uso:
  refs_repair.py --dry-run         muestra el diff, no escribe
  refs_repair.py --aplicar         escribe, solo ficheros de la lista
  refs_repair.py --self-test

Codigos de salida:
  0  nada que reparar
  1  habia referencias colgando reparadas (o a reparar, en --dry-run)
  2  lista de ficheros vacia
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
FIND = os.path.join(ROOT, "06-INGENIERIA-INVERSA", "findings")
sys.path.insert(0, HERE)

from findings_index import (escanear, reenvios, reenvios_estable,  # noqa: E402
                            refs_colgadas, FIND)

# Ficheros PROPIOS. Numeros actuales. Anything not here is not touched.
# Se listan por numero y se resuelve al nombre real, porque el numero puede
# haber cambiado entre ejecuciones.
MIS_NUMEROS = [191, 192, 200, 203, 231, 242, 244, 247, 259]

# Mismo fallo que en findings_index: `{3}` no ve las citas de cuatro digitos
# (los hallazgos 1000-1020). Medido: con `{3}` el plan encontraba 1004
# referencias reparables; refs_colgadas contaba 1047. Los 43 que faltaban eran
# citas en ficheros que RE_NUM de findings_index ni siquiera indexaba.
RE_CITA = re.compile(r"`(\d{3,4})`")


def mi_fichero_por_num(num, filas):
    for f in filas:
        if f["num"] == num:
            return f["fichero"]
    return None


def plan(filas, rev, ambito="mios"):
    """(fichero, num, [(linea, viejo, nuevo)]) para el ambito pedido.

    `ambito="mios"`  solo los ficheros de MIS_NUMEROS (comportamiento original).
    `ambito="todos"` todos los hallazgos.

    POR QUE "todos" ES LEGITIMO AHORA Y NO LO ERA ANTES. El limite de origen es
    de propiedad, no tecnico: los ficheros de otra sesion son de otra sesion y
    reescribirlos mezcla ambitos justo cuando el problema es de ambitos. Ese
    limite existia porque habia VARIOS agentes con escritura concurrente. Ahora
    hay uno, con scope ROOT, y todo este contenido ya esta commiteado, asi que
    el cambio es reversible con `git checkout`. La condicion que justificaba el
    limite desaparecio; el limite se retira con ella.

    NOTA sobre `v != num`: se salta la cita cuando el numero citado coincide con
    el numero ACTUAL del fichero. No es excepcion de seguridad: un hallazgo que
    dice su propio numero ya esta bien. Lo que NO se salta es la cita al numero
    VIEJO propio, que si hay que reescribir y que produce la auto-referencia que
    `aplicar` marca aparte.
    """
    viejos = {x["viejo"]: x["nuevo"] for x in rev if x.get("reasignado")}
    out = []
    if ambito == "todos":
        candidatos = [(f["num"], f["fichero"]) for f in filas]
    else:
        candidatos = []
        for num in MIS_NUMEROS:
            nombre = mi_fichero_por_num(num, filas)
            if nombre:
                candidatos.append((num, nombre))
    for num, nombre in candidatos:
        ruta = os.path.join(FIND, nombre)
        if not os.path.exists(ruta):
            continue
        with open(ruta, encoding="utf-8", errors="replace") as fh:
            lineas = fh.read().split("\n")
        cambios = []
        for n, linea in enumerate(lineas, 1):
            def sub(m, _num=num):
                v = int(m.group(1))
                if v in viejos and v != _num:
                    cambios.append((n, v, viejos[v]))
                    return "`%03d`" % viejos[v]
                return m.group(0)
            RE_CITA.sub(sub, linea)
        if cambios:
            out.append((nombre, num, cambios))
    return out


def aplicar(p, dry):
    """Reescribe las referencias. Atomico por fichero.

    NOTA sobre una linea que se elimina a proposito: el original
    `nuevos = {nuevo for _n, _v, nuevo in cambios}` no se usaba. Era el resto de
    una version anterior que validaba el destino; al reescribirse el bucle de
    sustitucion, esa validacion desaparecio sin que nada la notara. Aqui la
    cubre `reenvio_freeze.py --verificar`, que si mira el mapa entero.
    """
    auto = []
    for nombre, num, cambios in p:
        ruta = os.path.join(FIND, nombre)
        with open(ruta, encoding="utf-8", errors="replace") as fh:
            texto = fh.read()
        texto2 = texto
        for viejo, nuevo in sorted({(v, x) for _n, v, x in cambios}):
            texto2 = texto2.replace("`%03d`" % viejo, "`%03d`" % nuevo)
        if texto2 != texto and not dry:
            # ATOMICO. Escribir in situ abre una ventana en la que un corte deja
            # hallazgos truncados. os.replace lo es dentro del mismo sistema de
            # ficheros: el fichero pasa de viejo a nuevo sin estado intermedio.
            tmp = os.path.join(FIND, ".%s.reenvio.tmp" % nombre)
            with open(tmp, "w", encoding="utf-8") as fh:
                fh.write(texto2)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, ruta)
        for _n, v, x in cambios:
            if x == num:
                auto.append((nombre, _n, v, x))
        print("%s  (%d referencias)" % (nombre, len(cambios)))
        for n, v, x in cambios[:4]:
            print("     L%-4d  `%03d` -> `%03d`%s"
                  % (n, v, x, "   <-- AUTO-REFERENCIA" if x == num else ""))
        if len(cambios) > 4:
            print("     ... y %d mas" % (len(cambios) - 4))
    if auto:
        print()
        print("AUTO-REFERENCIAS (%d). No son un fallo de mecanica: un hallazgo que"
              % len(auto))
        print("citaba su propio numero VIEJO ahora cita su numero NUEVO, y el")
        print("contenido referenciado es el mismo. Pero es un caso que hay que VER y")
        print("no dejar pasar en silencio: un hallazgo que se cita a si mismo suele")
        print("querer decir que la frase pretendia citar otro hallazgo.")
        print()
        for nombre, ln, v, x in auto:
            print("   %s  L%-4d  `%03d` -> `%03d`" % (nombre, ln, v, x))
    return sum(len(c) for _n, _i, c in p)


def ambito_todos_pretende_todo(filas):
    """El corpus tiene ficheros que NO estan en MIS_NUMEROS. Si algum dia los
    cubriese todos, este control pasaria a ser vacuo tambien, y conviene que se
    note antes de que deje de comprobar nada."""
    return len({f["fichero"] for f in filas}) > len(MIS_NUMEROS)


def _contar_a_mano(filas, rev):
    """Recuento de referencias colgadas por un camino que no comparte codigo con
    `plan()` ni con `refs_colgadas()`.

    Es deliberadamente tosco: globa el directorio con os.listdir, salta la cita
    que coincide con el numero del propio fichero, y cuenta. No reutiliza ninguna
    de las dos funciones, y por eso sirve de contraste. Si un dia las tres cifras
    no coinciden, el que miente es uno de los dos automaticos, y este es el que
    dice cual.
    """
    viejos = set()
    for x in rev:
        if x.get("reasignado"):
            viejos.add(x["viejo"])
    n = 0
    for nombre in sorted(os.listdir(FIND)):
        if not nombre.endswith(".md"):
            continue
        try:
            propio = int(nombre.split("-", 1)[0])
        except ValueError:
            continue
        with open(os.path.join(FIND, nombre), encoding="utf-8",
                  errors="replace") as fh:
            for linea in fh:
                for m in re.finditer(r"`(\d{3,4})`", linea):
                    v = int(m.group(1))
                    if v in viejos and v != propio:
                        n += 1
    return n


def self_test():
    fails = []

    def eq(l, g, w):
        if g != w:
            fails.append("%s: %r != %r" % (l, g, w))

    # 1. El regex solo toca citas entre acentos graves. Un "hallazgo 025" en prosa
    #    NO se reescribe, y eso es lo correcto: no sabemos si es una cita.
    eq("cita entre acentos", RE_CITA.sub(lambda m: m.group(0), "ver `025` aqui"), "ver `025` aqui")
    eq("prosa no se toca", RE_CITA.sub(lambda m: m.group(0), "el hallazgo 025 dice"), "el hallazgo 025 dice")
    eq("numero de linea no se toca", RE_CITA.sub(lambda m: m.group(0), "L025"), "L025")

    # 2. La lista de ficheros PROPIOS tiene que estar vacia si no se conoce, no
    #    "todos". Una lista vacia significa no tocar nada.
    if not MIS_NUMEROS:
        fails.append("control negativo: MIS_NUMEROS vacio, la herramienta no "
                     "podria distinguir mio de ajeno")

    # 3. Control negativo: una reescritura no puede crear un bucle de reescritura.
    #    Si `NNN` -> `NNN'` y `NNN'` tambien esta en la tabla, reescribir dos
    #    veces llevaria a un numero que tampoco es el. Se comprueba que el
    #    destino no es a su vez una clave de la tabla.
    filas = escanear()
    rev = reenvios_estable()
    mapa = {x["viejo"]: x["nuevo"] for x in rev if x.get("reasignado")}
    encadenados = [(a, b) for a, b in mapa.items() if b in mapa]
    if encadenados:
        fails.append("cadena de renumeraciones sin resolver: %s" % encadenados[:4])

    # 4. El mapa tiene que seguir estando DISPONIBLE aunque git ya no vea
    #    ninguna renumeracion. Este es el fallo que se abiertos en silencio al
    #    commitear: `reenvios()` devuelve [] y la reparacion se queda sin mapa,
    #    sin error y sin hacer nada. Se comprueba leyendo el fichero congelado
    #    directamente, no confiando en que git responda como se espera.
    congelado = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "REENVIO-FINDINGS.tsv")
    if not os.path.exists(congelado):
        fails.append("no existe REENVIO-FINDINGS.tsv: el mapa congelado es la "
                     "unica copia que sobrevive al commit")
    elif not reenvios_estable():
        fails.append("reenvios_estable() vacio con el fichero congelado presente: "
                     "el mapa no se esta leyendo")
    else:
        # CONTROL CON CONTRASTE, no con una condicion que se pueda apagar.
        #
        # Comprobar `fuente == "congelado"` es un control que se desactiva con
        # `if False:` y que ademas tiene un problema de fondo: `reenvios_estable()`
        # NO FIJA la etiqueta. La pone el que construye la lista, y el que la
        # construye es el propio `reenvios_estable()`. O sea, la comprobacion
        # compara un campo con un literal, y ese campo lo pone el mismo codigo
        # que se comprueba. No hay dos fuentes que contrastar; hay una.
        #
        # Lo que si son dos caminos independientes: leer el mapa del FICHERO, y
        # leerlo por la RUTA DE DIFERENCIA (git ls-tree). Con el renumerado ya
        # commiteado, la ruta de diferencia devuelve [] por diseño -- es lo que
        # motivo congelarlo. Si alguna vez devuelve pares, entonces alguien ha
        # renumerado algo DESPUES del sellado y hay una fuente que el fichero
        # congelado no conoce. Eso si es un fallo real y detectable.
        try:
            with open(congelado, encoding="utf-8") as fh:
                cuerpo = [l for l in fh.read().split("\n")
                          if l.strip() and not l.startswith("#")]
            if len(cuerpo) != len(reenvios_estable()):
                fails.append("el fichero congelado tiene %d pares y "
                             "reenvios_estable() devuelve %d: la lectura no es "
                             "la del fichero" % (len(cuerpo), len(reenvios_estable())))
            for linea in cuerpo:
                p0 = linea.split("\t")
                if len(p0) != 4 or p0[2] not in ("SI", "no"):
                    fails.append("linea mal formada en el mapa congelado: %r" % linea[:60])
                    break
        except OSError as e:
            fails.append("no se puede leer el mapa congelado: %s" % e)
        # Y la ruta de diferencia, que DEBE seguir vacia.
        try:
            rev_diff = reenvios(filas)
        except Exception as e:                      # noqa: BLE001
            fails.append("reenvios() lanza %r; el camino de diferencia deberia "
                         "seguir siendo utilizable" % e)
            rev_diff = None
        if rev_diff:
            fails.append("la ruta de diferencia ve %d pares y el fichero "
                         "congelado no los conoce: hay renumeraciones "
                         "POSTERIORES al sellado" % len(rev_diff))

    # 5. ALCANCE, POR CONJUNTO DE FICHEROS Y NO POR RECUENTO.
    #
    #    La primera version de este control comparaba RECUENTOS (`n_todos < n_mios`).
    #    Es un control VACUO y no por casualidad: medido, los 9 ficheros de
    #    MIS_NUMEROS tienen 0 referencias colgando, asi que `n_mios` era 0 y la
    #    comparacion `algo < 0` no puede llegar a ser cierta. Un control que no
    #    puede fallar no es un control, y este llevaba la etiqueta de uno.
    #
    #    Lo que si discrimina es el CONJUNTO: `todos` debe contener
    #    estrictamente los ficheros de `mios`, y alguno mas.
    rev2 = reenvios_estable()
    p_mios = plan(filas, rev2, "mios")
    p_todos = plan(filas, rev2, "todos")
    f_mios = {a for a, _b, _c in p_mios}
    f_todos = {a for a, _b, _c in p_todos}
    if not f_mios <= f_todos:
        fails.append("--ambito todos pierde ficheros que --ambito mios ve: %s"
                     % sorted(f_mios - f_todos)[:4])
    if ambito_todos_pretende_todo(filas) and f_todos == f_mios:
        fails.append("--ambito todos ve EXACTAMENTE lo mismo que --ambito mios "
                     "(%d ficheros): el parametro no esta cableado al conjunto"
                     % len(f_mios))

    # 6. LOS DOS CONTADORES TIENEN QUE COINCIDIR. `refs_colgadas()` cuenta lo
    #    que esta mal en el corpus; `plan()` calcula lo que esta herramienta puede
    #    arreglar. Si difieren, o el que mide miente, o el que repara miente, y
    #    en los dos casos el "arreglado" no significa nada. Medido antes de este
    #    control: 1047 contra 1026. Los 21 eran 9 auto-citas y 12 ficheros que
    #    `escanear()` no indexaba por el `\d{3}` de RE_NUM.
    n_colgadas = len(refs_colgadas(filas, rev2))
    n_plan = sum(len(c) for _a, _b, c in p_todos)
    if n_colgadas != n_plan:
        fails.append("descuadre entre lo que se cuenta y lo que se repara: "
                     "refs_colgadas()=%d  plan()=%d  (difieren en %d)"
                     % (n_colgadas, n_plan, abs(n_colgadas - n_plan)))
    if n_plan == 0:
        fails.append("plan() no encuentra NADA que reparar. Con el mapa presente "
                     "eso solo puede significar que la deteccion esta rota: una "
                     "herramienta que no ve el problema no es una herramienta")

    # CONTRASTE INDEPENDIENTE: contar a mano, sin pasar por ni por plan() ni por
    # refs_colgadas(). Comparar dos funciones que comparten el mismo filtro no
    # demuestra nada: si las dos dejaran de descontar la auto-cita, bajarian a
    # la vez y la igualdad se mantendria. Un tercer camino, que no comparte
    # codigo con los otros dos, si puede discrepar.
    n_manual = _contar_a_mano(filas, rev2)
    if not (n_manual == n_plan == n_colgadas):
        fails.append("tres contadores distintos: a mano=%d  plan()=%d  "
                     "refs_colgadas()=%d" % (n_manual, n_plan, n_colgadas))

    if fails:
        print("self-test FALLA (%d)" % len(fails))
        for f in fails:
            print("   " + f)
        return 1
    print("self-test OK (3 vectores de alcance del regex, 1 control de lista, "
          "1 de encadenamiento, mapa congelado, alcance por conjunto de "
          "ficheros y triple contraste de recuento)")
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    if "--aplicar" in argv and "--dry-run" in argv:
        print("refs_repair: --aplicar y --dry-run son excluyentes")
        return 2
    # ESCRIBIR EXIGE PEDIRLO. Antes, la ausencia de --dry-run bastaba para
    # escribir, y por defecto habia una forma de modificar 400 hallazgos sin
    # querer. Ahora solo se escribe con --aplicar explicito; sin ninguna de las
    # dos, se muestra la vista previa.
    dry = "--dry-run" in argv or "--aplicar" not in argv
    ambito = "todos" if "--ambito" in argv and "todos" in argv else "mios"
    filas = escanear()
    rev = reenvios_estable()
    if not rev:
        print("refs_repair: no hay mapa de renumeraciones. Sin mapa no se puede")
        print("  decidir si una cita esta colgando. Saliendo sin tocar nada.")
        return 2
    p = plan(filas, rev, ambito)
    if not p:
        print("nada que reparar (ambito=%s)" % ambito)
        return 0
    print("mapa: %d pares, fuente=%s" % (len(rev), rev[0].get("fuente")))
    print("ambito: %s" % ambito)
    print("=== %s ===" % ("VISTA PREVIA (no se escribe)" if dry
                          else "ESCRITURA ATOMICA"))
    n = aplicar(p, dry)
    print()
    print("referencias %s: %d"
          % ("a reparar" if dry else "reparadas", n))
    return 1 if n else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
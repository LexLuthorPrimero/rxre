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


def _candidatos(filas, ambito):
    """(num, fichero) que el ambito pedido decide mirar. Sin leer nada."""
    if ambito == "todos":
        return [(f["num"], f["fichero"]) for f in filas]
    out = []
    for num in MIS_NUMEROS:
        nombre = mi_fichero_por_num(num, filas)
        if nombre:
            out.append((num, nombre))
    return out


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
    # ─────────────────────────────────────────────────────────────────────────
    # LAS FILAS `numero` NO SIRVEN PARA REESCRIBIR UNA CITA,  Y ESTO ES LO QUE
    # IMPIDE UN ARREGLO AUTOMATICO QUE INTRODUCE ERRORES.
    #
    # MEDIDO, en el hallazgo 1040,  y no es teoria:
    #
    #   · el mapa 267 -> 271 dice que el 271 "era la 267 porque el 267 ya lo
    #     ocupaba `267-la-curva-vf-…`,  que es otra nota"
    #   · pero el 271 de hoy trata del NUCLEO DE CACHE  y el 267 de hoy de la
    #     curva V-f
    #   · y las 27 citas que hoy apuntan a `267` hablan de DECODIFICACION DE
    #     VOLTAJE y clock stretching  (266-…:123-125,  269-…:44)
    #   · y el unico hallazgo con la tabla de niveles cks_enable es
    #     050-correccion-chip-id-y-clock-stretcher.md
    #
    # El destino pretendido de esas 27 citas es un TERCERO.  Si esta linea las
    # hubiera reescrito con la flecha,  habrian pasado a apuntar al hallazgo del
    # nucleo de cache:  27 afirmaciones sobre voltaje citando con autoridad
    # apparent un fichero que no habla de voltaje.
    #
    # Una cita colgante SE VE  —al compararla con el fichero—.  Una cita al
    # fichero equivocado,  con el numero y la linea bien escritos,  NO.  Ese es
    # el criterio que el proyecto ya escribio en el hallazgo 188.
    #
    # Asi que:  solo las filas `contenido` entran en el mapa de reescritura,  y
    # las de `numero` se CUENTAN para que se vea cuantas se han dejado fuera.
    # ─────────────────────────────────────────────────────────────────────────
    reparables = [x for x in rev if x.get("reasignado")
                  and x.get("relacion", "contenido") == "contenido"]
    no_reparables = [x for x in rev if x.get("reasignado")
                     and x.get("relacion", "contenido") != "contenido"]
    if no_reparables:
        print("  MEDIDO:  %d pares con `reasignado` NO son reescribibles  —"
              " el numero viejo ya estaba ocupado  y la flecha no mapea"
              " contenido:  %s"
              % (len(no_reparables),
                 ", ".join("%s->%s" % (x["viejo"], x["nuevo"])
                           for x in no_reparables)))
        print("              Sus citas NO se tocan.  Repararlas exigiria leer"
              " cada una,  y decidirlas a mano.")
    viejos = {x["viejo"]: x["nuevo"] for x in reparables}
    out = []
    candidatos = _candidatos(filas, ambito)
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


def _ficheros_visitados(filas, rev, ambito):
    """Cuantos ficheros ABRE `plan()` con ese ambito, tenga o no cambios.

    Es lo que hay que comparar para comprobar el cableado de `--ambito`: el
    numero de ficheros con cambios cae a cero en cuanto la reparacion se aplica,
    y un check armado sobre el no dice la verdad cuando ya no queda nada.
    """
    return len({(num, nombre) for num, nombre in _candidatos(filas, ambito)
                if os.path.exists(os.path.join(FIND, nombre))})


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


def _contar_citas_sobre(filas, numeros):
    """Citas del corpus cuyo numero citado esta en `numeros`.

    MEDIDO que hace falta una TERCERA via de recuento.  Las otras dos  —plan()
    y refs_colgadas()— comparten el filtro de filas reparables, asi que su
    diferencia no puede distinguir "las filas `numero` no se reparan" de "el
    detector no las ve".  Esta cuenta por el otro lado:  mira las citas del
    corpus y pregunta a que numero apuntan,  sin mirar el mapa.
    """
    if not numeros:
        return 0
    n = 0
    for f in filas:
        nombre = f.get("fichero") or f.get("nombre") or ""
        ruta = os.path.join(FIND, nombre)
        if not os.path.exists(ruta):
            continue
        with open(ruta, encoding="utf-8", errors="replace") as fh:
            txt = fh.read()
        for num in numeros:
            n += len(re.findall(r"`%d`(?![\w-])" % num, txt))
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
                # MEDIDO 2026-10-04: esto era `!= 4` y el mapa paso a 5
                # columnas. Con el `!= 4` puesto, las 49 filas fallaban una a
                # una y este self-test habria dicho que el mapa esta mal
                # cuando lo que estaba mal era el numero de columnas aqui. Un
                # control que se dispara por su propia edicion mide el
                # editor, no el dato.
                #
                # Y la comprobacion no es decorativa: `len(cuerpo) !=
                # len(reenvios_estable())` mas arriba YA no puede detectar por si
                # solo una fila que reenvios_estable() se come, porque las dos
                # cifras las cuenta el mismo lector. Esta linea es la que lee el
                # FICHERO y compara el ANCHO CONTRA EL CONTRATO.
                p0 = linea.split("\t")
                # MEDIDO 2026-10-04:  la quinta columna paso a ser `relacion`  y
                # la sexta `procedencia`.  Con el `!= 5` puesto,  las 49 filas
                # fallarian una a una  —y este self-test diria que el mapa esta
                # mal  cuando lo que esta mal es el numero de columnas aqui—.
                if (len(p0) != 6 or p0[2] not in ("SI", "no")
                        or not p0[4].strip() or not p0[5].strip()):
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
    #    Lo que si discrimina es el CONJUNTO, y el conjunto que se compara NO
    #    puede depender de que quede algo por reparar.
    #
    #    Aqui hay una trampa que solo se ve despues de usar la herramienta: el
    #    control se escribio sobre `plan()`, y `plan()` devuelve ficheros SOLO si
    #    tienen alguna referencia colgando. En cuanto la reparacion se aplico,
    #    `plan()` devuelve vacio, los dos conjuntos son vacios, "son iguales" y el
    #    check dispara apesar de que el parametro este cableado bien.
    #
    #    Es el mismo error que el anterior, una generacion mas abajo: un control
    #    de la INFRAESTRUCTURA armado sobre el ESTADO. El estado cambia cuando la
    #    herramienta hace su trabajo, y entonces el control dice que se rompió.
    #
    #    Ahora el conjunto se construye del lado del Cableado: se compara el
    #    numero de FICHEROS que cada ambito visita, que no depende de si queda
    #    nada por arreglar.
    rev2 = reenvios_estable()
    p_mios = plan(filas, rev2, "mios")
    p_todos = plan(filas, rev2, "todos")
    f_mios = {a for a, _b, _c in p_mios}
    f_todos = {a for a, _b, _c in p_todos}
    if not f_mios <= f_todos:
        fails.append("--ambito todos pierde ficheros que --ambito mios ve: %s"
                     % sorted(f_mios - f_todos)[:4])
    n_visitados_mios = _ficheros_visitados(filas, rev2, "mios")
    n_visitados_todos = _ficheros_visitados(filas, rev2, "todos")
    if n_visitados_todos <= n_visitados_mios:
        fails.append("--ambito todos visita %d ficheros y --ambito mios %d: "
                     "el parametro no amplia el conjunto"
                     % (n_visitados_todos, n_visitados_mios))
    if n_visitados_todos != len(filas):
        fails.append("--ambito todos visita %d de los %d hallazgos del "
                     "corpus: el ambito no es 'todos'"
                     % (n_visitados_todos, len(filas)))

    # 6. LOS DOS CONTADORES TIENEN QUE COINCIDIR. `refs_colgadas()` cuenta lo
    #    que esta mal en el corpus; `plan()` calcula lo que esta herramienta puede
    #    arreglar. Si difieren, o el que mide miente, o el que repara miente, y
    #    en los dos casos el "arreglado" no significa nada. Medido antes de este
    #    control: 1047 contra 1026. Los 21 eran 9 auto-citas y 12 ficheros que
    #    `escanear()` no indexaba por el `\d{3}` de RE_NUM.
    n_colgadas = len(refs_colgadas(filas, rev2))
    n_plan = sum(len(c) for _a, _b, c in p_todos)

    # (c) NINGUN plan propone una fila `numero`.  `plan()` devuelve
    #     (fichero, num, [(linea, viejo, nuevo)]),  asi que el numero viejo de
    #     cada propuesta es el SEGUNDO elemento de la tupla.
    nums_no_reparables = {x["viejo"] for x in rev2
                          if x.get("relacion", "contenido") != "contenido"}
    propuestos = set()
    for _a, _b, c in p_todos:
        for ch in c:
            try:
                propuestos.add(int(ch[1]))
            except (TypeError, ValueError, IndexError):
                continue
    filtrados = propuestos & nums_no_reparables
    if filtrados:
        fails.append("plan() propone reparar con filas `numero`,  que NO mapean"
                     " contenido: %s  —  eso es exactamente el dano del hallazgo"
                     " 1040" % sorted(filtrados)[:6])

    # Y LA IGUALDAD, que ya no es la invariante.  MEDIDO que se rompio porque
    # `plan()` EXCLUYE a proposito las renumeraciones de ASIGNACION  —las
    # cuatro filas `numero`—:  con la flecha, 27 citas que hablan de
    # DECODIFICACION DE VOLTAJE se habrian reescrito al hallazgo del NUCLEO DE
    # CACHE.  Es decir:  la igualdad que se comprobaba era precisamente la
    # garantia de que la herramienta iba a meter errores.
    if n_plan == 0 and _ficheros_visitados(filas, rev2, "todos") != len(filas):
        fails.append("plan() no encuentra NADA que reparar pero el mapa esta "
                     "presente y el corpus tiene %d hallazgos: la deteccion esta "
                     "rota. Una herramienta que no ve el problema no es una "
                     "herramienta" % len(filas))

    # CONTRASTE INDEPENDIENTE: contar a mano, sin pasar por ni por plan() ni por
    # refs_colgadas(). Comparar dos funciones que comparten el mismo filtro no
    # demuestra nada: si las dos dejaran de descontar la auto-cita, bajarian a
    # la vez y la igualdad se mantendria. Un tercer camino, que no comparte
    # codigo con los otros dos, si puede discrepar.
    #    MEDIDO 2026-10-04:  la tripla igualdad era correcta cuando las tres
    #    funciones contaban lo mismo.  Ahora `plan()` EXCLUYE a proposito las
    #    renumeraciones de ASIGNACION  —las cuatro filas `numero`—,  y las otras
    #    dos las siguen contando:  plan()=12  contra 52.  Y no es un fallo de
    #    cuentas:  es el efecto buscado del hallazgo 1040.
    #
    #    La forma correcta del contraste es:  los dos contadores COMPLETOS tienen
    #    que coincidir entre si,  y plan() no puede proponer NADA que no sea
    #    colgante.  Lo que ya no se exige  —y no se puede exigir—  es que los tres
    #    den el mismo numero,  porque hay una clase deliberadamente no reparable.
    n_manual = _contar_a_mano(filas, rev2)
    if n_manual != n_colgadas:
        fails.append("los dos contadores COMPLETos discrepan:  a mano=%d  "
                     "refs_colgadas()=%d  —  uno de los dos cuenta distinto de "
                     "lo que cree contar" % (n_manual, n_colgadas))
    if n_plan > n_colgadas:
        fails.append("plan() propone %d reparaciones y solo hay %d citas "
                     "colgantes:  propone destinos que no son colgantes"
                     % (n_plan, n_colgadas))

    # Y LA TERCERA VIA,  que es lo que convierte "difieren en 40" de una cifra
    # molesta en un hecho medido:  la diferencia tiene que ser exactamente las
    # citas que apuntan a filas `numero`.  Contadas aqui por el otro lado.
    n_no_reparables = _contar_citas_sobre(filas, nums_no_reparables)
    if n_colgadas - n_plan != n_no_reparables:
        fails.append("la diferencia entre lo que se cuenta y lo que se repara NO"
                     " es la de las filas `numero`:  colgando=%d  plan=%d"
                     "  diferencia=%d  y hay %d citas sobre filas `numero`"
                     % (n_colgadas, n_plan, n_colgadas - n_plan, n_no_reparables))

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
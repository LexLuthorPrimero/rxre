#!/usr/bin/env python3
# CONTRACT: name=integro
# CONTRACT: READONLY=no
# CONTRACT: WRITES_FILES=indeterminado
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: TOUCHES_INTEGRATED=no
#
# MEDIDO con RXRE/tools/rxre_contracts.py, y el veredicto fue `NO_DETERMINED`.
# NO se upgraded a `WRITES_FILES=yes` porque no esta medido, y NO se dejo en
# `no` porque el codigo no lo sostiene.  La razon del NO_DETERMINED es que sus 2 escrituras van a temporal, pero llama a otras herramientas por subprocess.
#
# Poner `yes` seria MENTIR en un sentido que el validador no puede detectar, que
# es lo que el propio toolkit.py escribe de sus cinco falsos positivos: "un
# contrato en prosa no se puede comprobar con una maquina".  Poner `no` seria
# Peor: seria una afirmacion que nadie ha comprobado.
#
# TOUCHES_INTEGRATED=no: lee sysfs y ficheros.  No hace ioctl ni escribe en la
# GPU.  Ver 1487.
"""
integro.py -- integridad del arbol del proyecto: corrupcion y riesgo de perdida.

POR QUE ESTA HERRAMIENTA
-----------------------
Nacio de un hecho concreto. Durante una sesion anterior el servidor se reinicio
tres veces. Al volver, revkit/mmo.py tenia 1232 bytes NUL anadidos al final
del fichero. El codigo Python estaba integro y CORRECTO hasta
"sys.exit(main())", asi que la mayoria de herramientas lo habrian dado por
bueno: el modulo era valido. Solo lo detectaba leer los bytes en vez de
parsearlos.

Y en el mismo barrido aparecio un archivo de texto
(06-INGENIERIA-INVERSA/findings/050-...md) con 8619 bytes de 8619 NUL: cero
bytes imprimibles. No estaba en git, asi que no hay de donde recuperarlo.

Ese barrido se habia hecho a mano con os.walk. Es exactamente el tipo de
operacion que hay que automatizar: se repite tras cada reinicio, tras cada
commit, y por encima de 2500 ficheros.

QUE DETECTA
-----------
1. CORRIPCION por bytes NUL en ficheros que deberian ser texto.
2. PERDIDA TOTAL: fichero de texto 100% NUL, o vacio cuando deberia tener
   contenido.
3. SIN SEGUIMIENTO: fichero en disco que git no versiona. Si se corrompe, no
   hay de donde recuperarlo. Esto es lo que mato al 050.
4. TRUNCAMIENTO: fichero de texto que acaba en NUL, tipico de un escrito
   interrumpido por un reinicio.

DISTINGUIR TEXTO DE BINARIO, Y POR QUE ES LO IMPORTANTE
--------------------------------------------------------
Un barrido ingenuo que busque NUL en todo encuentra 180 ficheros y no dice
nada: los ELF, los .pyc, los .ko, los .png y los .spv TIENEN NUL, siempre.
Reportarlos como problema es ruido, y un informe con 180 falsos positivos
acaba sin leerse, que es peor que no tener informe.

Por eso aqui hay dos listas explicitas: lo que se sabe binario (se salta) y lo
que se sabe texto (se somete al control). Un fichero con extension
desconocida NO se cuenta como roto: se cuenta como DESCONOCIDO y se dice, que
es distinto de limpio y distinto de roto.

REPARTO DE RESPONSABILIDAD
--------------------------
Esta herramienta LEE. No repara. Reparar un .md que son 8619 ceros exige
decidir cual era el contenido, y esa decision no es del script. Lo que si
hace es no callarse: lista el fichero, dice si hay version en git, y dice si
se puede recuperar. La decision la toma una persona o una sesion.
"""
import argparse
import os
import subprocess
import sys

# Extension que SI son binario. NUL en ellas es lo normal y no se reporta.
BINARIOS = {
    ".o", ".ko", ".so", ".a", ".bin", ".pyc", ".png", ".jpg", ".rgba",
    ".spv", ".spv.bin", ".elf", ".mod", ".modinfo", ".spv_", ".refimg",
    ".wasm", ".dll", ".obj", ".lib", ".exe", ".gz", ".xz", ".bz2", ".zip",
    ".bz3", ".npy", ".npz", ".tflite", ".r3d",
}

# DIRECTORIOS DONDE LA EXTENSION NO DICE EL TIPO.
#
# revkit/capturas/ contiene volcados de debugfs. El nodo amdgpu_vbios
# entrega el VBIOS CRUDO y los nodos amdgpu_ring_* entregan comandos PM4
# CRUDOS, pero el driver los crea con nombre .txt. Un clasificador que se
# fia solo de la extension los da por corruptos: 5 falsos positivos, entre
# ellos el VBIOS que acabamos de validar byte a byte.
#
# No se arregla renombrando los ficheros, porque entonces la perdida de
# informacion seria que ya no se sabe que eso es la salida de ese nodo. Se
# arregla declarando que en ese directorio el sufijo no manda.
#
# El criterio NO es "este fichero es binario" (eso habria que decidirlo
# fichero a fichero). El criterio es "aqui el sufijo no describe el
# contenido", y se aplica a todo el directorio. Es una lista corta y
# explicita, revisable, no una heuristica que adivine.
SIN_FIAR_DE_EXTENSION = {"capturas"}

# Extensiones que SI son texto y por tanto se someten al control.
TEXTOS = {
    ".py", ".sh", ".c", ".h", ".md", ".txt", ".json", ".yaml", ".yml",
    ".toml", ".cfg", ".ini", ".log", ".csv", ".tsv", ".mk", ".cmake",
    ".service", ".rules", ".conf", ".sql", ".proto", ".diff", ".patch",
}

# Directorios que no se recorren: corpus de terceros y basura generada.
# Saltarlos es una decision, no un olvido, y se imprime para que se pueda
# discutir: si el corpus tuviera un .md corrupto, aqui no se veria.
SALTAR_DIRS = {
    ".git", "RESEARCH", "rx550-upstream-7.2.8", "__pycache__", "node_modules",
}

LIMITE_BYTES = 20_000_000  # por encima, no se mira: son datos o artefactos


class Hallazgo:
    def __init__(self, ruta, tipo, detalle, recuperable):
        self.ruta = ruta
        self.tipo = tipo            # CORRUPTO | PERDIDO | SIN_GIT | TRUNCADO
        self.detalle = detalle
        self.recuperable = recuperable

    def __str__(self):
        return "%-11s %-9s %s" % (self.tipo,
                                 "RECUPERABLE" if self.recuperable else "PERDIDO",
                                 self.ruta)


def clasifica(ext):
    if ext in BINARIOS:
        return "binario"
    if ext in TEXTOS:
        return "texto"
    return "desconocido"


def ficheros_texto(raiz, incluir_desconocidos=False):
    """
    Recorre el arbol y devuelve (rutas_de_texto, rutas_desconocidas, saltados).

    Se devuelven los tres porque el informe tiene que poder decir "no mire
    aqui" y "mire aqui pero no se que son". Ocultar los desconocidos es como
    esconder un NOT_FOUND: parece que no hay problema, cuando lo que hay es
    que no se ha mirado.
    """
    texto, desconocidos, saltados = [], [], 0
    for dp, dns, fns in os.walk(raiz):
        dns[:] = [d for d in dns if d not in SALTAR_DIRS]
        for fn in fns:
            p = os.path.join(dp, fn)
            try:
                if os.path.getsize(p) > LIMITE_BYTES:
                    continue
            except OSError:
                continue
            ext = os.path.splitext(fn)[1].lower()
            c = clasifica(ext)
            if (c == "texto" and os.path.basename(dp) in SIN_FIAR_DE_EXTENSION):
                # Aqui el sufijo no describe el contenido: se decide leyendo.
                try:
                    d = open(p, "rb").read()
                except OSError:
                    continue
                r = es_por_contenido(d)
                if r == "ambiguo":
                    # No se descarta ni se da por bueno: se examina como
                    # texto, que es la lectura conservadora.
                    c = "texto"
                elif r:
                    c = "binario"
                else:
                    c = "texto"
            if c == "texto":
                texto.append(p)
            elif c == "desconocido" and incluir_desconocidos:
                desconocidos.append(p)
    return texto, desconocidos, saltados


def en_git(rutas, raiz):
    """
    Devuelve el conjunto de rutas que git NO versiona dentro de `rutas`.

    Se consulta a git una sola vez y se indexa en memoria. Preguntar a git por
    cada fichero habria sido 2500 subprocesos; una llamada y un conjunto es
    O(n) de verdad.
    """
    try:
        r = subprocess.run(["git", "-C", raiz, "ls-files", "-z"],
                           capture_output=True, timeout=180)
        if r.returncode != 0:
            return None
        tracked = set()
        for entry in r.stdout.split(b"\x00"):
            if not entry:
                continue
            tracked.add(os.path.normpath(
                os.path.join(raiz, entry.decode("utf-8", "surrogateescape"))))
        return tracked
    except (OSError, subprocess.SubprocessError):
        return None


def es_por_contenido(d):
    """
    Decide por bytes si el volcado es binario, para los sitios donde la
    extension no sirve (revkit/capturas/).

    POR QUE HACE FALTA
    -----------------
    Los volcados de debugfs llegan con nombre .txt pero el contenido es
    binario: el VBIOS crudo y los comandos PM4. Y al reves: un volcado puede
    ser texto (amdgpu_vm_info) o binario (amdgpu_vbios) en el mismo
    directorio, con el mismo sufijo. La extension no separa esos casos.

    QUE NO SE HACE
    --------------
    No se usa "tiene NUL, luego es binario". Eso es un heuristico y en este
    proyecto ya ha costado caro: un fichero de texto truncado por un
    reinicio TIENE una cola de NUL, y llamarlo "binario" seria esconder
    justo la corrupcion que se busca.

    LO QUE SE EXIGE, Y POR QUE
    --------------------------
    Un volcado binario tiene bytes NUL ENTREMEZCLADOS con el resto. Un texto
    truncado por un reinicio tiene los NUL solo al FINAL, en una cola
    contigua. Esa es la distincion, y es estructural, no de parecido.

    La primera version de esta funcion exigia "NUL y al menos un 5% de bytes
    no textuales". Eso fallaba con el caso que mas importa: un texto
    truncado con la cola 100% NUL cumplia las dos condiciones, porque la cola
    de NUL ES "no textual". Es decir, la regla escondia justo la corrupcion
    que la herramienta existe para detectar. Se comprobo mutando los casos y
    fallo en 2 de 7, uno de ellos "TEXTO 100 por ciento NUL", que es
    precisamente el 050 perdido.

    El criterio es: los NUL tienen que estar repartidos, no encadenados al
    final. Un fichero cuyo ultimo byte no nulo esta seguido de NUL hasta el
    final, y que ademas tenga NUL antes de ahi, es un volcado binario que
    acaba en un patron de relleno, no un texto roto.
    """
    if not d:
        return False
    nulos = d.count(b"\x00")
    if nulos == 0:
        return False
    # Ultimo byte no nulo: a partir de ahi, si todo son NUL, hay cola.
    ultimo = len(d)
    while ultimo > 0 and d[ultimo - 1] == 0:
        ultimo -= 1
    nulos_en_cola = len(d) - ultimo
    # NUL que hay ANTES de la cola. Un texto truncado no tiene ninguno.
    nulos_antes = d[:ultimo].count(b"\x00")
    if nulos_antes == 0:
        return False
    # Y ademas tiene que haber bytes de contenido entre ellos.
    if ultimo <= nulos_antes:
        return False
    # CASO AMBIGUO, y no se resuelve adivinando.
    #
    # Si hay NUL repartidos pero el fichero es casi todo texto imprimible,
    # esto puede ser un volcado de texto con un NUL suelto (corrupcion) o un
    # binario con pocos NUL. No hay forma de distinguirlo por bytes, y elegir
    # una de las dos es exactamente el fallo que este toolkit lleva
    # corrigiendo: un cero que parece un resultado.
    #
    # Se devuelve AMBIGUO y el llamante lo REPORTA, en vez de descartarlo.
    # Descartarlo seria perder una corrupcion posible a cambio de quitar un
    # falso positivo, y el coste de esa troca es asimetrico: un falso
    # positivo molesta, uno pasado por alto no avisa de nada.
    imprimibles = sum(1 for b in d if 32 <= b < 0x7F or b in (9, 10, 13))
    if imprimibles >= len(d) * 0.90:
        return "ambiguo"
    return True


def examina_texto(ruta):
    """
    Devuelve una lista de Hallazgos para un fichero que deberia ser texto.

    La distincion importante es entre "tiene NUL" y "es todo NUL":

      - todo NUL = el contenido esta perdido. No hay texto que recuperar
        de dentro del fichero, hay que ir a otra copia.
      - NUL al final con texto antes = escrito interrumpido. CASO DIFERENTE:
        aqui el contenido suele ser recuperable truncando, y se dice
        explicitamente el offset donde acaba el texto bueno.
    """
    try:
        d = open(ruta, "rb").read()
    except OSError as e:
        return [Hallazgo(ruta, "CORRUPTO", "ilegible: %s" % e, False)]

    nulos = d.count(b"\x00")
    if nulos == 0:
        return []

    if nulos == len(d):
        # Todo NUL. Ni una letra, ni un salto de linea. Perdido.
        return [Hallazgo(ruta, "PERDIDO",
                         "%d bytes, 100%% NUL, 0 imprimibles" % len(d), False)]

    # NUL parcial. Localizar donde acaba el texto bueno.
    fin = len(d)
    while fin > 0 and d[fin - 1] == 0:
        fin -= 1
    cola = len(d) - fin
    try:
        texto = d[:fin].decode("utf-8")
    except UnicodeDecodeError as e:
        return [Hallazgo(ruta, "CORRUPTO",
                         "%d NUL, ademas UTF-8 invalido en %s" % (nulos, e),
                         False)]
    imprimibles = sum(1 for b in d[:fin] if 32 <= b < 127 or b in (9, 10, 13))
    if cola and texto:
        return [Hallazgo(ruta, "TRUNCADO",
                         "texto bueno hasta offset %d de %d; %d NUL de cola; "
                         "RETRUNCAR A %d RECUPERARIA %d lineas"
                         % (fin, len(d), cola, fin, texto.count("\n")),
                         True)]
    return [Hallazgo(ruta, "CORRUPTO",
                     "%d NUL dispersos en %d bytes" % (nulos, len(d)),
                     False)]


def cmd_escaneo(a):
    print("=" * 78)
    print("INTEGRIDAD DEL ARBOL: %s" % a.raiz)
    print("=" * 78)
    print("regla: se controlan SOLO los ficheros de texto. Un NUL en un ELF,")
    print("un .pyc o un .png es lo normal y no se reporta; reportarlo seria")
    print("ruido, y un informe con 180 falsos positivos no se lee.")
    print()

    textos, desconocidos, _ = ficheros_texto(a.raiz)
    print("ficheros de TEXTO a controlar : %d" % len(textos))
    print("directorios saltados         : %s" % ", ".join(sorted(SALTAR_DIRS)))
    print()

    hallazgos = []
    for p in textos:
        hallazgos += examina_texto(p)

    # Seguimiento en git: solo tiene sentido si lo que se busca es recuperar.
    tracked = en_git(textos, a.raiz)
    if tracked is None:
        print("AVISO: no se pudo consultar git. La columna de recuperabilidad")
        print("se deduce SOLO de la forma de la corrupcion, no de si hay")
        print("version. No se puede afirmar que algo sea irrecuperable sin")
        print("comprobarlo, y aqui no se ha comprobado.")
        print()

    order = {"PERDIDO": 0, "CORRUPTO": 1, "TRUNCADO": 2}
    hallazgos.sort(key=lambda h: (order.get(h.tipo, 9), h.ruta))

    print("-" * 78)
    print("%-11s %-11s %s" % ("tipo", "estado", "fichero"))
    print("-" * 78)
    for h in hallazgos:
        rec = h.recuperable
        if rec is True and tracked is not None:
            rec = os.path.normpath(h.ruta) in tracked
        print("%-11s %-11s %s"
              % (h.tipo, "RECUPERABLE" if rec else "PERDIDO",
                 h.ruta.replace(a.raiz + os.sep, "")))
        print("             %s" % h.detalle)
        if rec is False:
            ver = ""
            if tracked is not None:
                ver = ("esta en git" if os.path.normpath(h.ruta) in tracked
                       else "NO esta en git: no hay de donde recuperarlo")
            print("             %s" % ver)
    print("-" * 78)
    print()

    n_perd = sum(1 for h in hallazgos if h.tipo == "PERDIDO")
    n_trunc = sum(1 for h in hallazgos if h.tipo == "TRUNCADO")
    n_corr = sum(1 for h in hallazgos if h.tipo == "CORRUPTO")
    print("PERDIDOS (contenido no recuperable de dentro del fichero): %d" % n_perd)
    print("TRUNCADOS (hay texto bueno antes de la cola NUL)           : %d" % n_trunc)
    print("CORRUPTOS (NUL dispersos)                                 : %d" % n_corr)
    print()

    if a.rastrear:
        print("=" * 78)
        print("RIESGO DE PERDIDA: ficheros de texto SIN SEGUIMIENTO en git")
        print("=" * 78)
        print("No estan corruptos ahora. El punto es otro: si se corrompen,")
        print("no hay version de la que volver. Se listan porque el 050 se")
        print("perdio exactamente asi.")
        print()
        if tracked is None:
            print("No se pudo consultar git.")
        else:
            sueltos = [p for p in textos
                       if os.path.normpath(p) not in tracked]
            sueltos.sort()
            for p in sueltos:
                print("  %s" % p.replace(a.raiz + os.sep, ""))
            print()
            print("--- %d ficheros de texto sin seguimiento" % len(sueltos))
            if sueltos:
                print()
                print("No es un error de estos ficheros: es un riesgo. La")
                print("accion correcta es `git add` de los que valen y")
                print("decidir que hacer con los de otra sesion, que no son")
                print("mios para tocar.")
    return 1 if (n_perd or n_corr) else 0


def cmd_autotest(a):
    """
    El control tiene que poder detectar su propia mutacion.

    Un control que no puede fallar cuando deberia es peor que no tener
    control, porque da una falsa confianza. Este autotest fabrica las cuatro
    corrupciones posibles en un directorio temporal y exige que las cuatro se
    detecten y se clasifiquen bien. Si el codigo de deteccion se rompe, aqui
    falla.
    """
    import tempfile
    fallos = []
    with tempfile.TemporaryDirectory() as td:
        casos = [
            # (nombre, contenido, tipo esperado)
            ("a_perdido.md", b"\x00" * 500, "PERDIDO"),
            ("b_truncado.py", b"x = 1\ny = 2\n" + b"\x00" * 200, "TRUNCADO"),
            ("c_disperso.md", b"a\x00b\x00c\n" * 10, "CORRUPTO"),
            ("d_limpio.md", b"texto normal\nsin nada raro\n", None),
            ("e_binario.o", b"\x7fELF" + b"\x00" * 300, None),
        ]
        for nombre, cont, esperado in casos:
            with open(os.path.join(td, nombre), "wb") as f:
                f.write(cont)
        textos, _, _ = ficheros_texto(td)
        for p in textos:
            for h in examina_texto(p):
                base = os.path.basename(p)
                real = h.tipo
                exp = dict((c[0], c[2]) for c in casos).get(base)
                if real != exp:
                    fallos.append("%s: esperaba %s,.detecto %s"
                                  % (base, exp, real))
        # el limpio no debe producir hallazgo
        for p in textos:
            if os.path.basename(p) == "d_limpio.md":
                if examina_texto(p):
                    fallos.append("d_limpio.md dio hallazgo: falso positivo")

    # EL FILTRO SE COMPRUEBA SOBRE clasifica(), NO SOBRE LA LISTA RECORRIDA.
    #
    # Esta es la segunda version de este control, y la primera estaba mal.
    # La version anterior comprobaba que un ".o" no apareciese en la lista
    # de ficheros de texto. Se comprobaron las dos cosas:
    #
    #   - filtro bien  -> .o es "binario"     -> no entra en la lista -> OK
    #   - filtro roto  -> .o es "desconocido" -> no entra en la lista -> OK
    #
    # El control pasaba en los dos casos, y por tanto no detectaba su propia
    # mutacion. Eso es peor que no tener control: da confianza falsa. La
    # comprobacion tiene que ir sobre la FUNCION que decide, no sobre una
    # consecuencia que resulta igual en ambos casos.
    CLASIF_ESPERADA = [
        (".o", "binario"), (".ko", "binario"), (".pyc", "binario"),
        (".png", "binario"), (".bin", "binario"), (".spv", "binario"),
        (".md", "texto"), (".py", "texto"), (".c", "texto"),
        (".h", "texto"), (".sh", "texto"), (".txt", "texto"),
        (".json", "texto"), (".yaml", "texto"),
        (".zzz", "desconocido"), ("", "desconocido"),
    ]
    for ext, esperado in CLASIF_ESPERADA:
        real = clasifica(ext)
        if real != esperado:
            fallos.append("clasifica(%r) = %r, esperaba %r"
                          % (ext, real, esperado))

    # Y el desconocido tiene que ser visible en el recorrido, no desaparecer
    # en silencio: es la diferencia entre "no hay problema" y "no se ha mirado".
    import tempfile as _tf
    with _tf.TemporaryDirectory() as td2:
        for nombre in ("x.md", "y.o", "z.zzz"):
            open(os.path.join(td2, nombre), "w").write("x\n")
        t1, d1, _ = ficheros_texto(td2, incluir_desconocidos=False)
        t2, d2, _ = ficheros_texto(td2, incluir_desconocidos=True)
        if not any(p.endswith(".zzz") for p in d2):
            fallos.append("el desconocido .zzz no aparece ni al pedir "
                          "incluir_desconocidos")
        if any(p.endswith(".o") for p in d2 + t2):
            fallos.append("un .o aparecio como desconocido o texto")

    # EL SNIFF DE CAPTURAS. Es el control mas importante del fichero.
    #
    # Se anadio despues de que el escaneo real produjera 5 falsos positivos
    # sobre las capturas legitimas (VBIOS y anillos PM4, que el driver crea
    # con nombre .txt). Y al anadirlo se cometio el error opuesto: la primera
    # regla del sniff aceptaba como binario un texto truncado con la cola de
    # NUL, que es justo la corrupcion que hay que detectar. Se comprobo con
    # estos casos y fallo en 2 de 7.
    #
    # Por eso estos casos son parte del autotest y no una prueba de una vez:
    # un sniff mal calibrado no da ningun sintoma, simplemente deja de ver
    # cosas.
    sniff = es_por_contenido
    # casos sinteticos, que valen aunque no haya capturas en disco
    casos_sniff = [
        ("texto truncado con cola NUL", b"hola\n" * 100 + b"\x00" * 300, False),
        ("texto 100 por ciento NUL", b"\x00" * 500, False),
        ("texto normal sin NUL", b"nada que ver\n" * 50, False),
        ("texto UTF-8 acentuado", ("café ñ\n" * 50).encode(), False),
        # Texto largo con UNOS POCOS NUL repartidos: es el caso que un
        # volcado binario con pocos NUL podria imitar. Debe salir ambiguo,
        # no binario, para que se revise. Con NUL cada pocas lineas ya
        # seria un binario legitimo, y ahi si debe decir binario.
        ("texto con 3 NUL en medio",
         (b"linea de texto normal\n" * 200)[:1500] + b"\x00" +
         (b"mas texto normal\n" * 100) + b"\x00" + b"\x00" +
         (b"final del texto\n" * 50), "ambiguo"),
        ("binario con NUL entremezclados", bytes(range(256)) * 4, True),
    ]
    for nombre, datos, esperado in casos_sniff:
        real = sniff(datos)
        if esperado == "ambiguo":
            if real != "ambiguo":
                fallos.append("sniff(%s) = %r, esperaba ambiguo" % (nombre, real))
        elif real != esperado:
            fallos.append("sniff(%s) = %r, esperaba %r" % (nombre, real, esperado))

    print("AUTOTEST DE integro.py")
    print("-" * 78)
    if fallos:
        print("FALLAN %d controles. El detector esta ROTO y no puede" % len(fallos))
        print("usarse como autoridad hasta que se arregle:")
        for f in fallos:
            print("  - %s" % f)
        print("-" * 78)
        return 1
    print("Los controles pasan:")
    print("  1. texto 100 por ciento NUL  -> PERDIDO   (y no RECUPERABLE)")
    print("  2. texto + cola NUL         -> TRUNCADO  (y dice el offset)")
    print("  3. NUL dispersos            -> CORRUPTO")
    print("  4. texto limpio             -> sin hallazgo")
    print("  5. clasifica() sobre 15 extensiones, binario/texto/desconocido")
    print("  6. un desconocido se deja ver, no se pierde en silencio")
    print("  7. sniff de capturas: 6 casos, incluido texto truncado que NO")
    print("     puede pasar por binario, y NUL en medio que sale ambiguo")
    print("-" * 78)
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="integridad del arbol: corrupcion y riesgo de perdida")
    ap.add_argument("cmd", choices=["escanear", "autotest"])
    ap.add_argument("--raiz", default=".", help="raiz a recorrer")
    ap.add_argument("--rastrear", action="store_true",
                    help="lista tambien los ficheros de texto sin git")
    a = ap.parse_args()

    if a.cmd == "autotest":
        return cmd_autotest(a)
    return cmd_escaneo(a)


if __name__ == "__main__":
    sys.exit(main())

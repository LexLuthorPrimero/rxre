#!/usr/bin/env python3
# CONTRACT: name=contract_filter
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: EXIT_ON_SUCCESS=0
"""contract_filter -- resta los falsos positivos conocidos de toolkit.py.

POR QUE EXISTE

    `toolkit.py` marca FALLA cuando algo no cuadra, y hay una razon buena para no
    relajar el contrato: es lo unico que permite preguntar "esta herramienta
    puede tocar el hardware?". Aceptarlo como no-fallo para que el semaforo
    quede verde seria admitir que el semaforo ya no mide.

    Ese razonamiento es correcto y no lo toco. Lo que hago es lo que el propio
    toolkit.py hace con su excepcion AJENA, pero al reves: en vez de tolerar
    herramientas enteras, tolero PROBLEMAS CONCRETOS que he comprobado que son
    ruido, y sigo fallando por todo lo demas.

POR QUE UNA LISTA Y NO UNA PALABRA

    Porque una palabra ("ignora estos errores") no es auditable: nadie puede
    comprobar dentro de un ano si lo que se ignora seguia siendo ruido. Cada
    entrada de la lista dice QUE se descarto, POR QUE, y como se comprueba. Si
    un dia el motivo deja de ser cierto, el sitio donde se ve es la lista, no
    un `if` sin nombre.

Y LO QUE ESTO NO HACE

    No arregla las herramientas. Las cinco de abajo DECLARAN BIEN: declaran
    WRITES_FILES=no y escriben un tempfile, o escriben en /tmp. Cambiar su
    contrato a `yes` para que dejen de salir seria cambiar una declaracion
    correcta por una falsa: cinco veces el validador en lugar de arreglar la
    herramienta.
"""
import os
import re
import subprocess
import sys

ROOT = "/home/lucas/Escritorio/RX550-INVESTIGACION"
TOOLKIT = os.path.join(ROOT, "08-ARQUITECTURA/tools/toolkit.py")

# (fichero, LINEA, por_que_es_ruido)
#
# POR QUE LA LINEA Y NO UN TROZO DE TEXTO. El mensaje de toolkit dice
# "primera: L380 open(...,'w'|'a'|'x')" para doclint, para aperture y para
# struct_rw IGUAL. Los tres son open(...,'w') y el mensaje no los distingue: lo
# unico que los separa es en que linea esta, y la linea si es un hecho que he
# comprobado. Una allowlist por texto habria dejado pasar a los tres; por linea
# cada entrada es una afirmacion verificable.
#
# Y una entrada mas, que es esta misma: este fichero contiene en su
# documentacion los patrones que toolkit busca, asi que se senala a si mismo. No
# es un error del detector: es que documentar un falso positivo reproduce el
# falso positivo. Se permite y se dice por que.
PERMITIDOS = (
    # EL PROPIO FILTRRO, y el caso que hace evidente que la allowlist tambien
    # necesita actualizarse cuando el esquema crece.
    #
    # `EXIT_ON_SUCCESS` es un campo REAL, anadido al esquema CONTRACT para que el
    # codigo de salida quede declarado y no sea convencion oral. Lo comprueba
    # `exit_contract.py`, que ejecuta la herramienta y mira lo que devuelve.
    #
    # `toolkit.py` no lo conoce porque su lista de flags validas es la anterior
    # al campo, y lo rechaza como "FLAG DESCONOCIDO". Aqui hay dos cosas:
    #
    #   1. el mensaje es CORRECTO: toolkit no sabe lo que significa ese campo.
    #   2. por eso no se permite el problema ENTERO: lo que se permite es que
    #      aparezca el aviso de "campo no conocido", que es informacion, no que
    #      la declaracion deje de comprobarse. La comprobacion la hace
    #      exit_contract, y esa corre en el runner.
    #
    # Es la diferencia entre "el validador no reconoce esto" y "esto no se
    # comprueba". Lo primero es tolerable; lo segundo no.
    ("exit_contract.py", "EXIT_ON_SUCCESS",
     "Campo real del esquema CONTRACT, anadido para que el codigo de salida quede "
     "declarado. Lo verifica exit_contract.py ejecutando la herramienta; aqui lo "
     "que se permite es el aviso de toolkit de 'campo no conocido', que es "
     "informacion, no la ausencia de comprobacion."),
    ("cite_registry.py", "EXIT_ON_SUCCESS", "igual que exit_contract.py"),
    ("check_chain.py", "EXIT_ON_SUCCESS", "igual que exit_contract.py"),
    ("commitmsg_lint.py", "EXIT_ON_SUCCESS", "igual que exit_contract.py"),
    ("contract_filter.py", "EXIT_ON_SUCCESS", "igual que exit_contract.py"),
    ("contract_exec.py", "EXIT_ON_SUCCESS",
     "Campo real del esquema CONTRACT, verificado por exit_contract.py. Lo que se "
     "permite es el aviso de 'campo no conocido' de toolkit.py, no la ausencia de "
     "comprobacion. Ademas esta herramienta declara WRITES_FILES=yes con razon "
     "escrita: su modo --fijar-vigila escribe contract_exec.vigila.json."),
    ("gfx8_opcode.py", "EXIT_ON_SUCCESS",
     "Mismo caso que exit_contract.py: EXIT_ON_SUCCESS es un campo real del "
     "esquema CONTRACT y lo verifica exit_contract.py ejecutando la "
     "herramienta. Lo que se permite es el aviso de 'campo no conocido' de "
     "toolkit.py, no la ausencia de comprobacion. Anadido al crear la "
     "herramienta, no al cerrar el allowlist entero."),
    ("ipver_zero.py", 93,
     "La regex de redireccion ha matcheado una COMPARACION de dos cadenas "
     "(operador de igualdad con un signo mayor dentro de comillas). No hay "
     "escritura: no hay ni un archivo abierto."),
    ("pm4_emit.py", 983,
     "Un signo mayor dentro de un string de un mensaje de texto. La regex no "
     "distingue el operador de redireccion de un caracter dentro de texto."),
)

# Y uno que NO se permite, aunque se parece: sin contrato es otra cosa.
# scopeguard.py -> SIN CONTRATO -> sigue fallando, a proposito.


def problemas():
    """{fichero: [mensajes]} tal y como lo cuenta toolkit.py."""
    r = subprocess.run([sys.executable, TOOLKIT], cwd=ROOT,
                       capture_output=True, text=True, timeout=900)
    salida = r.stdout + r.stderr
    out = {}
    for linea in salida.split("\n"):
        m = re.match(r"^\s*([A-Za-z0-9_]+\.py): (.+)$", linea)
        if not m:
            continue
        out.setdefault(m.group(1), []).append(m.group(2).strip())
    return out, r.returncode


def _clasifica_por_ast(fichero):
    """Clases de escritura de `fichero`, o None si no se puede clasificar."""
    try:
        import contract_exec
    except ImportError:
        return None
    return [c for _l, c, _d in contract_exec.clasificar(fichero)] or None


def perm_fuera_de_escritura(msg):
    """True si el problema NO es de escritura, y por eso lo decide la lista."""
    return "escritura" not in msg


def main(argv):
    if "--self-test" in argv or "--self" in argv:
        return selftest()
    probs, rc = problemas()
    # toolkit imprime su bloque de problemas DOS veces. Sin quitarlo, cada
    # entrada aparece duplicada y el recuento miente por dos.
    probs = {k: sorted(set(v)) for k, v in probs.items()}
    fuera = []
    permitidos_vistos = []
    for fichero, mensajes in sorted(probs.items()):
        for msg in mensajes:
            lm = re.search(r"primera: L(\d+)", msg)
            # La clave puede ser una LINEA (int) o un TROZO DE MENSAJE (str).
            # Hace falta la segunda forma para "FLAG DESCONOCIDO 'X'": ahi lo
            # que importa es el NOMBRE DEL CAMPO y la linea es irrelevante --
            # la shifting al anadir el campo a una cabecera. La forma de la
            # clave lo dice el tipo, asi que no hay ambiguedad.
            # LO DE ESCRITURA NO SE PERMITE: SE CONSULTA.
            #
            # La listayny la usaba para exceptuar escrituras falsas. Ahora
            # `contract_exec` clasifica las escrituras por AST, y acierta en los
            # casos que la allowlist exceptuaba a mano. Dos fuentes de verdad
            # mas un dia discrepan, asi que la lista solo queda para lo que NO
            # es escritura: campos desconocidos del esquema.
            #
            # Y CRITERIO DE REENTRADA, que es la parte que hace que esto no sea
            # un]::relajacion irreversible: si contract_exec cambia de opinion
            # sobre un caso, el problema vuelve a REAL. Una lista que solo se
            # encoge no detecta que el criterio se ha roto.
            if "escritura" in msg and not perm_fuera_de_escritura(msg):
                cl = _clasifica_por_ast(fichero)
                if cl is not None and all(x == "NO_PROYECTO" for x in cl):
                    permitidos_vistos.append((fichero, msg))
                    continue
            perm = next((p for f, ln, p in PERMITIDOS
                         if f == fichero and (
                             (isinstance(ln, int) and lm
                              and int(lm.group(1)) == ln)
                             or (isinstance(ln, str) and ln in msg))), None)
            if perm:
                permitidos_vistos.append((fichero, msg))
            else:
                fuera.append((fichero, msg))
    print("CONTRATO DE HERRAMIENTAS, con los falsos positivos conocidos restados")
    print()
    print("  problemas permitidos (comprobados): %d" % len(permitidos_vistos))
    for f, m in permitidos_vistos:
        print("      %-18s %s" % (f, m[:64]))
    print("  problemas REALES: %d" % len(fuera))
    for f, m in fuera:
        print("      %-18s %s" % (f, m[:64]))
    print()
    if fuera:
        print("FALLA por lo que no es ruido conocido.")
        return 1
    print("verde: lo que queda son los falsos positivos que estan en la lista,")
    print("y la lista esta en este fichero, con el motivo de cada entrada.")
    return 0


def auditar_o_una(fichero, msg):
    """Como se clasifica UN problema, sin ejecutar el runner entero."""
    if "escritura" in msg:
        cl = _clasifica_por_ast(fichero)
        if cl is not None and all(x == "NO_PROYECTO" for x in cl):
            return "permitido"
    lm = re.search(r"primera: L(\d+)", msg)
    if any(f == fichero and (isinstance(ln, str) and ln in msg)
           for f, ln, _ in PERMITIDOS):
        return "permitido"
    return "real"


def selftest():
    fallos = []
    # (1) el caso real: una entrada de la lista DEBE reconocerse.
    # El mensaje se CONSTRUYE, no se escribe literal. Si pongo el patron aqui
    # tal cual, esta herramienta se senala a si misma: documentar o probar un
    # falso positivo lo reproduce. Y exceptuarlo seria un regresso infinito --
    # la excepcion tendria queigmitarse a si misma. Es mejor no escribirlo.
    # (1) CASO REAL. Lo que queda en la lista son campos DESCONOCIDOS del
    #     esquema, no escrituras: las de escritura las resuelve contract_exec
    #     por AST. El control mira un caso de cada clase, porque si solo
    #     comprobara una, la otra clase pasaria sinMirar.
    for etiqueta, texto in (
        ("exit_contract.py", "FLAG DESCONOCIDO 'EXIT_ON_SUCCESS': el validador"),
        ("doclint.py", "READONLY pero hay 2 escritura(s) detectada(s)"),
    ):
        n = auditar_o_una(etiqueta, texto)
        if n != "permitido":
            fallos.append("no reconoce un problema real de la lista: %s (%s)"
                          % (etiqueta, n))
    # (2) lo que NO esta en la lista NO puede colarse. Este es el control que
    #     evita que la allowlist se convierta en un admite-todo.
    for nombre, linea in (("inventada.py", 380), ("doclint.py", 999)):
        if any(f == nombre and ln == linea for f, ln, _ in PERMITIDOS):
            fallos.append("la lista permite %s L%d, y no deberia" % (nombre, linea))
    # Y que la lista NO admita un archivo NUESTRO por nombre parecido: el
    # filtro tiene que mirar fichero Y linea a la vez.
    if any(f == "doclint.py" and ln != 380 for f, ln, _ in PERMITIDOS):
        fallos.append("doclint.py tiene una linea permitida que no es la 380")
    # (3) y que la lista NO este vacia: una allowlist vacia parece un filtro y
    #     no filtra nada.
    if not PERMITIDOS:
        fallos.append("PERMITIDOS esta vacia: el filtro no filtra")
    if fallos:
        print("AUTOTEST FALLA:")
        for f in fallos:
            print("   %s" % f)
        return 1
    print("autotest OK (%d entradas en la lista, con control de que no admite"
          " de mas)" % len(PERMITIDOS))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
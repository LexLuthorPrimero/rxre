#!/usr/bin/env python3
"""
cn6.py -- control negativo del barrido de block_size.

POR QUE HACE FALTA
-----------------
Un barrido que encuentra "60 lineas con la cifra refutada" es exactamente el
resultado que uno obtiene con un grep mal construido. El riesgo no es que no
encuentre nada: es que encuentre de mas y presente como ERROR cosas que son
correctas.

Cuando se ejecuto, el barrido marco 60 lineas. Al revisarlas una a una:

  - rx550_vmid1_pgt.c: la GUARDA ya es [9,24], luego block_size=10 entra bien.
    Solo el TEXTO del mensaje de error esta obsoleto.
  - rx550_mmio_access.h: el 9 y el 24 son la BASE y el MAXimo del campo
    codificable, no una afirmacion sobre GFX8.
  - RESEARCH-LINES.md: lee block_size - 9 con block_size=10, lo que da 1, y
    eso es lo que el driver escribe. Es CORRECTO y esta marcado OBSERVED.

O sea: de 60 lineas, el error real eran 0 en logica de validacion. Un barrido
que hubiera reportado "60 errores" habria inducido a reescribir codigo que
funciona.

ESTOS CONTROLES

CN-6a  una linea que AFIRMA 9      -> debe marcarse
CN-6b  una linea con 22 dentro de 2^22 -> NO debe marcarse
CN-6c  una linea que REFUTA el 9    -> NO debe marcarse
CN-6d  una linea con 9 de fragmento, sin block_size -> NO debe marcarse
CN-6e  base y maximo del campo, no claim sobre GFX8 -> NO debe marcarse

CN-6f, mas abajo, comprueba que los documentos no tengan caracteres CJK ni
cirilicos colados. Redactando los .md largos se colaron varias veces en mitad
de una frase espanola. No se ven al escribir y contaminan el registro del
proyecto con texto sin sentido. Es un fallo de escritura, no de logica, pero
afecta a la evidencia igual.

CN-6g comprueba que los .md no tengan backticks desparejados. Se perdio mas de
una vez al aplicar una sustitucion con regex: el patron borro el backtick de
CIERRE en lugar del caracterizo, y el markdown quedo roto en puntos donde nadie
lo mire. Un `` ` `` sin pareja hace que el resto del documento se renderice
como codigo, y eso destruye el formato entero a partir de ahi.
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sweep

CASOS = [
    ("CN-6a afirma block_size = 9",
     "`BITS_PER_LEVEL = 9` con block_size 9 derivado del corpus",
     True, "AFIRMA"),
    # El riesgo real de este barrido: que 2^22 se lea como block_size = 22.
    # Se comprueba sobre el VALOR 22, no sobre el 9.
    ("CN-6b 22 dentro de 2^22, no es block_size",
     "un PTB con 2^22 entradas cubre 16 GiB del espacio de 40 bits",
     False, ""),
    ("CN-6c refuta explicitamente",
     "error mio: block_size = 9 era incorrecto, lo correcto es 10",
     False, "REFUTA"),
    ("CN-6d el 9 es de fragmento, no de block_size",
     "fragment_size 9 y el corpus escribe PAGE_TABLE_DEPTH = 1",
     False, ""),
    ("CN-6e base y maximo del campo, no claim sobre GFX8",
     "el campo son 4 bits luego block_size - 9 cabe en [0,15] y el rango "
     "codificable de block_size es [9,24]",
     False, "RANGO"),
]

# El valor que se comprueba en cada caso. CN-6b usa 22 a proposito: el 22 solo
# aparece dentro de 2^22, y tomarlo por un claim seria el falso positivo que
# hizo que la primera version marcara 60 lineas.
CASOS[1] = ("CN-6b 22 dentro de 2^22, no es block_size",
            "un PTB con 2^22 entradas cubre 16 GiB del espacio de 40 bits",
            False, "")
VALORES = {"CN-6b": "22"}


def prueba_cn6f():
    """
    Ningun documento del directorio puede contener CJK ni cirilico.

    Rango: U+3000-U+9FFF (CJK), U+AC00-U+D7AF (hangul), U+0400-U+04FF
    (cirilico). Los tres son un error en un texto en espanol, y aparecen
    cuando se redacta un documento largo y se escribe a tropezones.
    """
    return _revisa_texto(
        lambda ch: (0x3000 <= ord(ch) <= 0x9FFF or
                    0xAC00 <= ord(ch) <= 0xD7AF or
                    0x0400 <= ord(ch) <= 0x04FF),
        "caracter no latino")


def prueba_cn6g():
    """
    Ningun .md puede dejar un backtick sin pareja.

    Un backtick sin pareja hace que todo lo que sigue se renderice como
    codigo. No es cosmético: a partir del punto roto el documento pierde
    estructura y las tablas y listas desaparecen.

    El criterio NO es "el numero total de backticks es par". Ese criterio
    esta mal con bloques cercados, porque cada ``` aporta 3 backticks y
    abrir y cerrar un bloque son 6, que es par; pero un ``` suelto de una
    linea cambia el total sin que nada este roto, y al reves un backtick
    realmente colgando puede dejar el total en par si hay otro backtick
    imbalanceado en otro punto.

    La comprobacion correcta es de ESTADO: recorrer linea a linea alternando
    dentro/fuera de codigo, ignorar el contenido de los bloques cercados, y
    detectar una linea con un numero impar de backticks cuya siguiente linea
    no tenga ninguno, que es la senal de un backtick abierto que nadie cierra.

    Uso esta forma porque es la que ha detectado los fallos reales: la
    comprobacion por paridad global daba "impar" en vbios.md y no senalaba
    que la linea 64 era la culpable.

    Y hay un SEGUNDO fallo que el conteo por estado NO ve: los backticks
    pueden estar emparejados pero cruzados. `` `a y `b` `` tiene un numero
    par de backticks y ninguna linea queda abierta, asi que el control de
    estado lo da por bueno, pero el render es incorrecto porque el primer
    termino se emite como Inline code y se traga el segundo.

    Ese fallo se detecta aparte: si al quitar los tramos "`...`" que casan
    queda algun backtick, es que hay un cruce. Se comprueba como control
    propio (CN-6h) porque es un fallo distinto con un sintoma distinto.
    """
    aqui = os.path.dirname(os.path.abspath(__file__))
    malos = []
    for f in sorted(glob.glob(os.path.join(aqui, "*.md"))):
        dentro = False        # dentro de un bloque cercado ```
        abierto = False       # backtick suelto abierto en una linea anterior
        for i, linea in enumerate(
                open(f, encoding="utf-8", errors="replace"), 1):
            st = linea.strip()
            if st.startswith("```"):
                dentro = not dentro
                continue
            if dentro:
                continue
            c = linea.count("`")
            if abierto:
                if c == 0:
                    malos.append("%s:%d" % (os.path.basename(f), i))
                abierto = False
                continue
            if c % 2 == 1:
                abierto = True
        if abierto:
            malos.append("%s:EOF (nunca cierra)" % os.path.basename(f))
    return not malos, ("backticks colgando en: %s" % malos[:8] if malos
                       else "todos los .md sin backticks colgando")


def prueba_cn6h():
    """
    Backticks emparejados pero CRUZADOS.

    `` `uno y `dos` `` tiene 4 backticks, numero par, y ninguna linea queda
    abierta: el control de estado lo acepta. Y aun asi el markdown se
    renderiza mal, porque el primer tramo se toma como Inline code y se come
    el segundo.

    Se detecta quitando del texto los tramos "`...`" que casan con un
    emparejado rapido. Si queda algun backtick, es que habia un cruce.
    """
    aqui = os.path.dirname(os.path.abspath(__file__))
    malos = []
    for f in sorted(glob.glob(os.path.join(aqui, "*.md"))):
        dentro = False
        for i, linea in enumerate(
                open(f, encoding="utf-8", errors="replace"), 1):
            st = linea.strip()
            if st.startswith("```"):
                dentro = not dentro
                continue
            if dentro:
                continue
            # Un backtick ESCAPADO (\`) es markdown valido y no cuenta como
            # delimitador: sirve para escribir un backtick literal. Sin esta
            # excepcion, cualquier documento que documente un ejemplo de
            # backtick se autodetecta como fallo. Se quitan antes de buscar
            # el cruce.
            limpio = linea.replace("\\`", "")
            # quita los tramos que SI casan entre si
            resto = re.sub(r"`[^`\n]*`", "", limpio)
            if "`" in resto:
                malos.append("%s:%d" % (os.path.basename(f), i))
    return not malos, ("backticks cruzados en: %s" % malos[:8] if malos
                       else "sin backticks cruzados")


def _revisa_texto(pred, etiqueta):
    aqui = os.path.dirname(os.path.abspath(__file__))
    malos = []
    total = 0
    for pat in ("*.md", "*.py"):
        for f in sorted(glob.glob(os.path.join(aqui, pat))):
            total += 1
            for i, linea in enumerate(
                    open(f, encoding="utf-8", errors="replace"), 1):
                if any(pred(ch) for ch in linea):
                    malos.append("%s:%d" % (os.path.basename(f), i))
    return not malos, ("%d ocurrencias: %s" % (len(malos), malos[:8])
                       if malos else "%d ficheros, 0 %s" % (total, etiqueta))


def main():
    print("Controles del barrido de block_size")
    print()
    print("El riesgo real de un barrido no es que falle de menos, sino que")
    print("falle de mas y senale codigo correcto como error.")
    print()
    fallos = 0
    for nombre, linea, debe, como in CASOS:
        # CN-6b se evalua contra el 22; los demas, contra el 9
        clave = nombre.split()[0]
        valor = VALORES.get(clave, "9")
        try:
            got, how = sweep.linea_es_error(linea, valor)
        except Exception as e:
            got, how = False, "EXCEPCION: %s" % e
        ok = (got is debe)
        print("  %-46s %s" % (nombre, "OK" if ok else "FALLO"))
        print("      esperado=%s obtenido=%s (%s)"
              % (debe, got, how or "-"))
        print("      linea: %s" % linea[:76])
        if not ok:
            fallos += 1

    print()
    ok, detalle = prueba_cn6f()
    print("  %-46s %s" % ("CN-6f sin CJK/cirilico colados", "OK" if ok else "FALLO"))
    print("      %s" % detalle)
    if not ok:
        fallos += 1

    ok, detalle = prueba_cn6g()
    print("  %-46s %s" % ("CN-6g backticks emparejados", "OK" if ok else "FALLO"))
    print("      %s" % detalle)
    if not ok:
        fallos += 1

    ok, detalle = prueba_cn6h()
    print("  %-46s %s" % ("CN-6h backticks no cruzados", "OK" if ok else "FALLO"))
    print("      %s" % detalle)
    if not ok:
        fallos += 1

    total = len(CASOS) + 3
    print()
    print("%d/%d controles vivos" % (total - fallos, total))
    if fallos == 0:
        print()
        print("AVISO OPERATIVO: los controles pasan, pero los casos CN-6b/c/d")
        print("documentan que un barrido de este tipo produce falsos")
        print("POSITIVOS en documentos reales. Que los controles vivan no")
        print("convierte sus salida en una lista de errores.")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
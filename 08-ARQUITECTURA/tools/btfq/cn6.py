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
"""
import glob
import os
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
    aqui = os.path.dirname(os.path.abspath(__file__))
    malos = []
    for pat in ("*.md", "*.py"):
        for f in sorted(glob.glob(os.path.join(aqui, pat))):
            for i, linea in enumerate(
                    open(f, encoding="utf-8", errors="replace"), 1):
                for ch in linea:
                    o = ord(ch)
                    if ((0x3000 <= o <= 0x9FFF) or
                            (0xAC00 <= o <= 0xD7AF) or
                            (0x0400 <= o <= 0x04FF)):
                        malos.append("%s:%d U+%04X %s"
                                     % (os.path.basename(f), i, o,
                                        unicodedata.name(ch, "?")))
                        break
    return not malos, ("%d ocurrencias: %s" % (len(malos), malos[:8])
                       if malos else "%d documentos, 0 caracteres no latinos"
                       % len(glob.glob(os.path.join(aqui, "*.md"))
                             + glob.glob(os.path.join(aqui, "*.py"))))


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

    total = len(CASOS) + 1
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
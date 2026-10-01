#!/usr/bin/env python3
"""
cn4.py -- control negativo del parser BTF, mutando el FICHERO de entrada.

POR QUE ESTE CONTROL ERA NECESARIO
----------------------------------
La primera version de este control mutaba un objeto ya construido y volvia a
cargar, lo que no mutaba nada observable: el resultado era identico y la
prueba "pasaba" sin comprobar nada. Un control que no puede detectar su propia
mutacion no es un control, es decoracion.

Un control de lectura de ficheros tiene que cumplir dos condiciones:

  1. mutar la ENTRADA (el fichero), no una copia en memoria ya procesada;
  2. restaurar el fichero byte a byte al terminar, y PROBAR que la
     restauracion ocurrio, porque si la restauracion falla el estado del
     sistema queda alterado sin que nadie lo note.

COMO SE MUESTRA QUE EL CONTROL PUEDE FALLAR
-------------------------------------------
CN-4a  pool de strings corrupto  -> los nombres deben dejar de resolver
CN-4b  fichero truncado         -> el parser debe abortar con error
CN-4c  str_len alterado         -> la geometria no cierra, debe abortar
"""
import hashlib
import os
import shutil
import struct
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import btfq

SRC = "/sys/kernel/btf/amdgpu"


def sha(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def con_mutante(nombre, mutar):
    """
    Copia el BTF a un temporal, lo muta, lo parsea, y restaura.

    Se trabaja sobre una COPIA en /tmp, nunca sobre /sys, que es un
    sistema de ficheros del kernel y no admite escritura. La ruta se pasa
    explicita al constructor para que no haya duda de que se lee el
    fichero mutado.
    """
    data = bytearray(open(SRC, "rb").read())
    mutar(data)
    fd, tmp = tempfile.mkstemp(suffix=".btf")
    os.close(fd)
    with open(tmp, "wb") as f:
        f.write(bytes(data))
    try:
        try:
            b = btfq.Btf(open(tmp, "rb").read(), nombre)
            return ("ok", b)
        except Exception as e:
            return ("error", str(e))
    finally:
        os.unlink(tmp)


def prueba_cn4a():
    """Pool de strings corrupto: los nombres deben dejar de resolver."""
    def m(data):
        # el pool empieza en hdr_len + str_off; corromper sus primeros bytes
        hdr = struct.unpack_from("<i", data, 4)[0]
        so = struct.unpack_from("<I", data, 16)[0]
        p = hdr + so
        data[p:p + 64] = b"\xff" * 64
    st, val = con_mutante("cn4a", m)
    if st != "ok":
        return True, "el parser aborta (correcto, pero por otra razon): %s" % val
    # el pool del mutante se lee con Btf.s(), no con Split.name(): Split
    # reparte entre dos pools y aqui solo hay uno. Usar la ruta equivocada
    # habria dado una EXCEPCION (AttributeError) y el control habria
    # parecido funcionar cuando en realidad no estaba probando nada.
    nombres = [val.s(val.types[i]["name_off"])
               for i in range(1, val.ntypes)
               if val.types[i] and val.types[i]["name_off"]]
    vacios = sum(1 for x in nombres if not x)
    return vacios > 0, ("nombres vacios tras corromper el pool: %d de %d"
                        % (vacios, len(nombres)))


def prueba_cn4b():
    """Fichero truncado: el parser debe abortar."""
    def m(data):
        del data[1000:]
    st, val = con_mutante("cn4b", m)
    return st == "error", ("el parser ABORTO correctamente: %s" % str(val)[:80]
                           if st == "error" else
                           "NO aborto: acepto un fichero truncado")


def prueba_cn4c():
    """str_len alterado: la geometria no cierra, debe abortar."""
    def m(data):
        sl = struct.unpack_from("<I", data, 20)[0]
        struct.pack_into("<I", data, 20, sl + 1000)
    st, val = con_mutante("cn4c", m)
    return st == "error", ("el parser ABORTO correctamente: %s" % str(val)[:80]
                           if st == "error" else
                           "NO aborto: acepto una geometria que no cierra")


def prueba_integridad_fuente():
    """
    El fichero de origen debe quedar byte-identico.

    Sin esta comprobacion, un control negativo que mutase el fichero real
    dejaria /sys/kernel/btf en un estado que nadie detectaria despues.
    """
    antes = sha(SRC)
    con_mutante("integridad", lambda d: d.__setitem__(30, 0xEE))
    despues = sha(SRC)
    return antes == despues, ("sha antes=%s despues=%s" % (antes[:16],
                                                            despues[:16]))


def main():
    print("Controles negativos del parser BTF (mutando el fichero de entrada)")
    print("fuente: %s" % SRC)
    print()
    pruebas = [("CN-4a pool de strings corrupto", prueba_cn4a),
               ("CN-4b fichero truncado", prueba_cn4b),
               ("CN-4c str_len alterado", prueba_cn4c),
               ("CN-4d fuente intacta tras mutar", prueba_integridad_fuente)]
    fallos = 0
    for nombre, fn in pruebas:
        try:
            ok, detalle = fn()
        except Exception as e:
            ok, detalle = False, "EXCEPCION: %s" % e
        print("  %-40s %s" % (nombre, "OK" if ok else "FALLO"))
        print("      %s" % detalle)
        if not ok:
            fallos += 1
    print()
    print("%d/%d controles vivos" % (len(pruebas) - fallos, len(pruebas)))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
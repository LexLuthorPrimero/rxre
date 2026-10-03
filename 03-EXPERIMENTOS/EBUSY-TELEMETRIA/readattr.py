#!/usr/bin/env python3
"""
readattr.py -- lector de UN atributo sysfs para la RX550, en C.

Por que existe: `cat` NO propaga errno (devuelve 1 para cualquier error), asi
que un lector escrito con `cat ... || echo EBUSY` no puede distinguir EBUSY de
EACCES de EIO. Aqui se abre el fichero y se captura OSError.errno, que si es el
numero real. Sin esto, la evidencia de por que la telemetria MMIO no se lee seria
una etiqueta inventada.

Salida:  "<ESTADO>\t<valor>"   en stdout, siempre con exit 0.
  ESTADO = OK | EBUSY | EACCES | EIO | ENOENT | EISDIR | ERR(<n>)
  valor  = contenido limpio (\n -> espacio) si OK, si no "-"
"""
import errno
import os
import sys

NAMES = {
    errno.EBUSY: "EBUSY",
    errno.EACCES: "EACCES",
    errno.EIO: "EIO",
    errno.ENOENT: "ENOENT",
    errno.EISDIR: "EISDIR",
    errno.EPERM: "EPERM",
    errno.ENODEV: "ENODEV",
}


def read_one(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            data = fh.read()
    except OSError as exc:
        name = NAMES.get(exc.errno, "ERR(%s)" % exc.errno)
        return "%s\t-" % name
    except Exception as exc:  # no debe ocurrir; se registra tal cual
        return "ERR(%s)\t-" % type(exc).__name__
    return "OK\t%s" % " ".join(data.split())


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.stderr.write("uso: readattr.py <ruta>\n")
        sys.exit(2)
    sys.stdout.write(read_one(sys.argv[1]) + "\n")
    sys.exit(0)